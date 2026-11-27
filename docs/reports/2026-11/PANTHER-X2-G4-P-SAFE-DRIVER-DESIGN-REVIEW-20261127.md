# Panther X2 项目 A — G4-P-SAFE 驱动事务性设计审查（2026-11-27）

- 范围：固定 Linux 6.18.63 io-domain.c 与 regulator core 的源码级设计审查
- 结论：**可形成独立的 G4-P-SAFE build-only 候选，但当前尚不具备 runtime 放行条件**
- 硬件状态：未启动设备；未访问 PMU GRF/PMIC；未执行任何寄存器写入
- 介质状态：SU08G TF only；SN64G/eMMC 均未触碰
- 依据源码：ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f

## 1. 本轮确认的原始实现缺口

固定源码 drivers/soc/rockchip/io-domain.c：

1. rk3568_iodomain_write() 对 VSEL0/VSEL1/VSEL2 的每次 regmap_write() 均未检查返回值，最终对有效 supply index 返回 0。
2. rockchip_iodomain_probe() 对每路 supply 逐一执行：获取 regulator → regulator_get_voltage() → 立即写 selector → 注册 notifier。若后续 supply 或 notifier 失败，清理路径只注销已注册 notifier，不恢复此前 selector。
3. 写入失败时，当前代码把 supply->reg 置 NULL 后跳转清理；这只能避免注销一个尚未成功注册的 notifier，不能撤销该 supply 已发生的 GRF 写入。
4. rockchip_iodomain_remove() 只注销 notifier，不恢复 probe 前 selector。
5. rockchip_iodomain_notify() 在 PRE voltage-change 时可通过 NOTIFY_BAD 阻止调压；在 VOLTAGE_CHANGE/ABORT 事件中，供电变化已经发生或正在结束，写失败不能再通过 notifier 返回值撤销外部 rail 状态。

因此，不能把 driver bind、probe success 或单一 dmesg 结果当作 14 次写入成功的证明，也不能把当前 unbind 当作回退手段。

## 2. 新确认的并发约束：regulator notifier 锁顺序

固定 drivers/regulator/core.c 显示：

- regulator_register_notifier() / regulator_unregister_notifier() 通过 blocking notifier chain 注册/注销回调。
- regulator 电压变化路径在持有 regulator 内部锁时调用 _notifier_call_chain()；源码注释也明确该调用点要求调用者持有 regulator mutex。
- notifier callback 因而可能在 regulator 锁持有期间运行。

**设计约束：不能在持有 IO-domain 自身 mutex 时调用 regulator_get_voltage()、regulator_register_notifier()、regulator_unregister_notifier() 等 regulator core API。** 否则可能形成锁顺序反转：一个 regulator 事件持有 regulator lock 并等待 IO-domain mutex，而 probe/remove 持有 IO-domain mutex 又等待 regulator lock。

因此，简单地“给所有 probe/rollback/notifier 代码外包一把 mutex”不是安全实现。

## 3. G4-P-SAFE 候选必须满足的事务模型

本节是实现约束，不是已完成代码或授权。

### 3.1 写入前准备阶段（零 GRF 写入）

1. 获取 PMU GRF regmap，并确认是 fdc20000 对应的 PMU GRF，不得误用主 GRF fdc60000。
2. 对全部 DTS supplies 获取 regulator handle；允许按原 API 语义处理明确的 -ENODEV optional supply，但 -EPROBE_DEFER、其他错误均停止。
3. 在任何 GRF 写入前完成 notifier 注册和所需的软件电压读取；每个供电读数必须可追溯到 supply 名称。vcc_3v3 的软件 3.3V 读数不得标注为 SWITCH_REG1 实体输出电压。
4. 读取将涉及的 VSEL0/VSEL1/VSEL2 原始 32-bit 值。任何一项预读失败，必须零 selector 写入退出。
5. 建立每个寄存器的 affected-bit mask 和本次实际解析到的 supply/电压分类清单；不能把“预期 14 次调用”写成未经实测的实际发生次数。

### 3.2 初始写入事务

1. RK3568 每一条 hiword-mask regmap_write() 都必须检查并传播错误；在写之前标记该 bit 为“可能已触及”，因为总线错误返回不应被假定为绝对零副作用。
2. 写完后对三个寄存器执行 regmap_read()，只比较驱动负责的 selector bits；非目标 bits 必须保持不变。
3. 所有预读、写入、读回操作都必须使用同一 iod->grf regmap。不得通过 /dev/mem 或另一个 syscon 地址绕开 regmap。
4. 任一写入或读回失败，立即停止后续 selector 写入；执行受限 masked restore，并逐寄存器读回验证。回退失败必须标记为 **STATE UNKNOWN / STOP**，不能报告 PASS。

### 3.3 notifier 与并发

1. notifier callback 只能使用 IO-domain 内部状态和 regmap read/write；不得在 callback 内调用 regulator core API。
2. notifier 和初始写入必须有明确状态机，处理 probe 期间到达的 PRE/POST/ABORT 事件；不能发生“先读取旧电压、后覆盖新事件 selector”的竞态。
3. 可考虑 probing / active / faulted / voltage_change_seen 状态及受限 pending-event 缓冲；但实现必须通过锁顺序审查，禁止在持有 IO-domain mutex 时调用 regulator API。
4. PRE 事件写入失败必须返回 NOTIFY_BAD；POST/ABORT 事件写入失败必须记录硬错误并置 faulted，因为 rail 变化可能已完成，不能伪装为成功。
5. regulator_unregister_notifier() 必须在释放 IO-domain mutex 之前完成，避免 callback 与 teardown 互相等待。

### 3.4 Probe 失败与 remove 回退

1. probe 失败时，先在不持有 IO-domain mutex 的情况下注销所有已注册 notifier；再进入内部临界区执行 masked restore。
2. 只有在没有观察到任何 regulator voltage-change 事件、没有 faulted 状态且快照完整时，才允许恢复 probe 前 selector bits。
3. 如果已发生电压变化或状态不确定，不能盲目恢复旧 selector（旧值可能已不匹配当前 rail）；必须报告 STATE UNKNOWN 并停止后续硬件阶段。
4. 正常 remove/unbind 也遵守相同条件：注销 notifier 后，只有“无 voltage-change event、无 fault、快照有效”才恢复原 selector 并读回验证。
5. platform_driver.remove 在该固定 6.18.63 API 中返回 void，因此 remove 回退失败无法阻止解绑；必须通过高等级日志报告，操作流程还需独立只读核验结果。不能把 remove 回调的执行本身当作回退成功。
6. 该方案无法保证 CPU hang、kernel panic、突然断电、PMU GRF 总线不可访问时自动回退。此限制必须写入任何后续 runtime 风险声明。

## 4. selector masks 与回退参数

固定 DTS 全部 9 路 supply 的预期影响位：

- VSEL0 / offset 0x0140：bits 1, 3, 4, 5, 6, 7
- VSEL1 / offset 0x0144：bits 1, 3, 4, 5, 6, 7
- VSEL2 / offset 0x0148：bits 1, 5

Rockchip hiword-mask restore 的参数形式为：

restore_word = (mask << 16) | (pre_value & mask)

其中 mask 仅包含本 driver 实际触及的 selector bits。不得写回完整 32-bit 快照，也不得覆盖非目标字段。若只有部分 supplies resolve，实际 mask 必须按本轮成功解析/尝试写入的 supply 动态计算。

## 5. CI 纯软件测试要求

G4-P-SAFE 必须先作为独立 patch/build-only 候选，不覆盖 G4-B frozen artifact，不生成实机运行授权。最低测试矩阵：

- 每个初始 regmap_write() 位置分别注入失败，验证停止后续写入并恢复所有可能触及的目标 bits。
- VSEL0/1/2 任一预读失败：验证写入次数为 0。
- 每个寄存器 post-write readback 失败或目标 bit mismatch：验证进入 rollback。
- 每个 rollback write/readback 失败：验证最终状态标记为 STATE UNKNOWN，后续步骤停止。
- notifier PRE 写失败：验证返回 NOTIFY_BAD。
- notifier POST/ABORT 写失败：验证 faulted 状态及错误日志。
- probe 期间并发 voltage-change 事件：验证 pending/active 状态机不会让旧快照覆盖新 selector。
- remove：分别覆盖无 voltage-change、已发生 voltage-change、faulted、rollback failure 四种情况。
- 对非 RK3568 SoC 的现有行为做编译与静态回归检查，确保改动不扩大到其他 Rockchip IO-domain 路径。

测试应优先使用 fake regmap/KUnit 或等价可注入测试层，不得为了故障注入而在真实 Panther X2 上制造总线错误或寄存器写失败。

## 6. 当前阻塞与下一步

已确认的静态信息：
- G4-S：PASS。
- G4-B：PASS（Actions run 45997129528）。
- G4-P 原始 stock driver：不具备可验证事务回退。
- regmap debugfs registers 在固定源码中为只读；不得改用 debugfs write 或 /dev/mem。
- regulator notifier 在 regulator lock 持有期间运行，必须避免锁顺序反转。

尚未完成：
- G4-P-SAFE patch 尚未实现。
- fake-regmap/KUnit 故障注入测试尚未实现。
- 新 patch 尚未 build-only。
- 9 路 consumer 软件电压/enable 状态尚无 Panther X2 runtime 只读采集证据。
- PMU GRF readback 接口在目标 RAM-only runtime 尚未实测确认。
- 受限 rollback helper 尚未实现、编译或测试。

**结论：继续保持 G4-P NO-GO / HOLD / NOT AUTHORIZED。** 下一步只允许在独立分支完成 patch 设计与 fake-regmap 测试实现，再进行 CI build-only 审计。任何代码通过、构建通过或单元测试通过，都不自动授权实机 probe/GRF 写入。

项目 A 继续 TF-only：SU08G 是唯一实验介质；SN64G 与 eMMC 冻结。本文没有执行硬件、PMIC、PMU GRF、存储介质或网络操作。


## 7. 重要修正：remove/unbind 自动恢复不能作为默认方案

进一步对 regulator core 锁和 notifier 生命周期进行交叉审查后，不能把“注销 notifier 后无条件恢复 probe 前快照”视为普遍安全的 remove 策略：

- notifier 注销后，regulator consumer 仍可能继续改变 rail；如果 IO-domain notifier 已撤销，后续电压变化将不再同步更新 selector。
- 若在 unregister 前恢复，正在进行或随后到来的 PRE/POST/ABORT 回调可能再次改变 selector；若在 unregister 后恢复，则必须证明恢复窗口内 regulator voltage 不会变化。
- 因此，仅凭“历史上未观察到 voltage-change event”不足以证明 remove 时可安全恢复；还必须证明 regulator 在 teardown/restore 整个窗口内被外部约束为不变，且该约束本身可验证。
- 目前项目没有这项约束证据，也没有验证过 regulator notifier unregister 与运行时 rail 调整之间的全生命周期协调。

**设计修订：G4-P-SAFE 第一版不应承诺普通 driver unbind/remove 自动恢复初始 selector。** 更安全的候选边界是：probe 成功后保持 driver 绑定；任何正常 remove/unbind 默认拒绝或被测试流程禁止，除非后续实现并证明“先冻结 regulator 变化、再停止/同步 notifier、最后恢复和读回”的完整协议。Linux platform_driver.remove 返回 void，也使 remove 失败无法向 driver core 阻止解绑，因此不能依靠 remove callback 报错来拒绝 unbind。

probe 中途失败的恢复仍可设计为：标记 quiescing → 在不持有 IO-domain mutex 时注销/同步 notifier → 确认 rail 未发生实际变化且快照有效 → 执行受限 masked restore → readback；任何条件不满足则 STATE UNKNOWN / STOP。对于已成功 probe 的运行态，不把 driver unbind 当作实验回退按钮。

这项修订不改变当前 NO-GO / HOLD / NOT AUTHORIZED 结论。CPU hang、kernel panic、断电、总线失联等仍无法保证自动回退。
