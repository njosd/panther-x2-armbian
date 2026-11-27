# Panther X2 项目 A — G4-P IO-domain 运行时写入与回退准备审查（2026-11-27）

- 阶段：G4-P preflight / static operation-plan review
- 状态：**静态写入矩阵已展开；运行时执行仍 HOLD / NOT AUTHORIZED**
- 目标内核：Linux 6.18.63，`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 目标 SoC：RK3566 / RK3568 PMU GRF IO-domain driver path
- 介质边界：SU08G TF only；不触碰 SN64G；不写入、不挂载、不修改 eMMC
- 本轮范围：固定源码与 DTS 的只读复核；未启动设备、未访问 PMU GRF/PMIC、未执行任何寄存器写入

## 1. 当前结论

G4-P 不是“只设置 GMAC 所在 VCCIO5”。按固定 DTS，driver 会尝试取得 9 个 supply；若全部成功，RK3568 写函数在 probe 初始路径执行 14 次 `regmap_write()`，覆盖三个 PMU GRF 寄存器：

| 寄存器 | PMU GRF offset | 物理地址（DTS base + offset） | 写调用数 |
|---|---:|---:|---:|
| IO_VSEL0 | `0x0140` | `0xfdc20140` | 6 |
| IO_VSEL1 | `0x0144` | `0xfdc20144` | 6 |
| IO_VSEL2 | `0x0148` | `0xfdc20148` | 2 |
| **合计** | | | **14** |

地址依据：固定 DTS 的 `pmugrf: syscon@fdc20000`，reg base `0xfdc20000`、size `0x10000`；IO-domain probe 通过 parent syscon node 获取 regmap。表中是 SoC physical address 推导值，不代表本轮已读到寄存器。

## 2. 9 路 supply 与 driver 行为

| index | supply | DTS regulator | 静态电压信息 | RK3568 初始 write |
|---:|---|---|---|---|
| 0 | pmuio1 | vcc3v3_pmu | 固定约束 3.3V | 无 selector write |
| 1 | pmuio2 | vcc3v3_pmu | 固定约束 3.3V | VSEL2 两次 |
| 2 | vccio1 | vcc_3v3 / SWITCH_REG1 | switch 本身无独立 voltage selector；RK809 SWITCH_REG1 descriptor 的 upstream 为 vcc9；Panther DTS 将 vcc9-supply 指向固定 3.3V vcc3v3_sys，因此 regulator core 可递归报告约 3.3V | VSEL0、VSEL1 |
| 3 | vccio2 | vcc_1v8 | 固定约束 1.8V | 无 selector write（硬件 FLASH_VOL_SEL） |
| 4 | vccio3 | vccio_sd / LDO_REG5 | 可调范围 1.8–3.3V；实际当前 selector/读数未验证 | VSEL0、VSEL1 |
| 5 | vccio4 | vcc_1v8 | 固定约束 1.8V | VSEL0、VSEL1 |
| 6 | vccio5 | vcc_3v3 / SWITCH_REG1 | switch 电压读数可回退到 upstream vcc9（DTS 固定 3.3V vcc3v3_sys）；不证明 switch 输出端实体供电 | VSEL0、VSEL1 |
| 7 | vccio6 | vcc_3v3 / SWITCH_REG1 | 同上 | VSEL0、VSEL1 |
| 8 | vccio7 | vcc_3v3 / SWITCH_REG1 | 同上 | VSEL0、VSEL1 |

重要区别：
- regulator framework 的 `regulator_get_voltage()` 读取的是软件驱动可报告的电压；对于没有自身 `get_voltage` / selector 实现的 switch regulator，core 会沿 `rdev->supply` 递归读取上游电压。
- 因而 `vcc_3v3` 报告 3.3V 不能证明 RK809 SWITCH_REG1 已 enable 或其输出端实测为 3.3V。
- `vccio_sd` 是可调 LDO5，不能仅凭 DTS min/max 断言当前电压。其运行时读数必须在任何 IO-domain probe 之前只读采集；若读数不是明确预期的 1.8V 或 3.3V，停止 G4-P 计划，不允许按“接近值”自行分类。
- G3-P 只证明 provider bind 与 16 个 regulator objects 注册；没有验证上述 consumer 端 supply resolve、电压读数或物理 rail。

## 3. 14 次 write 的逐项值矩阵

驱动阈值：`is_3v3 = (uV > 1,980,000)`。下列值是 Linux hiword-mask 写入参数（不是寄存器最终完整值）；每次只更新对应 low-word selector bit，mask 位在 bit 16+。

| 顺序 | supply / index | register | 1.8V 分类时写值 | 3.3V 分类时写值 |
|---:|---|---|---:|---:|
| 1 | pmuio2 / 1 | VSEL2 `0x148` | `0x00020002` | `0x00020000` |
| 2 | pmuio2 / 1 | VSEL2 `0x148` | `0x00200000` | `0x00200020` |
| 3 | vccio1 / 2 | VSEL0 `0x140` | `0x00020002` | `0x00020000` |
| 4 | vccio1 / 2 | VSEL1 `0x144` | `0x00020000` | `0x00020002` |
| 5 | vccio3 / 4 | VSEL0 `0x140` | `0x00080008` | `0x00080000` |
| 6 | vccio3 / 4 | VSEL1 `0x144` | `0x00080000` | `0x00080008` |
| 7 | vccio4 / 5 | VSEL0 `0x140` | `0x00100010` | `0x00100000` |
| 8 | vccio4 / 5 | VSEL1 `0x144` | `0x00100000` | `0x00100010` |
| 9 | vccio5 / 6 | VSEL0 `0x140` | `0x00200020` | `0x00200000` |
| 10 | vccio5 / 6 | VSEL1 `0x144` | `0x00200000` | `0x00200020` |
| 11 | vccio6 / 7 | VSEL0 `0x140` | `0x00400040` | `0x00400000` |
| 12 | vccio6 / 7 | VSEL1 `0x144` | `0x00400000` | `0x00400040` |
| 13 | vccio7 / 8 | VSEL0 `0x140` | `0x00800080` | `0x00800000` |
| 14 | vccio7 / 8 | VSEL1 `0x144` | `0x00800000` | `0x00800080` |

该表由固定版本 `rk3568_iodomain_write()` 的 `b`、`val0`、`val1` 和 hiword-mask 算法逐项展开。vccio3 的实际列选择尚无运行时证据；其他 supply 的软件电压分类也须在目标运行环境采集确认后，才能形成最终 expected-value sheet。

## 4. 重要软件缺陷/风险：写入失败不可由 probe 结果直接识别

固定版本 `rk3568_iodomain_write()` 对 14 次底层 `regmap_write()` 均未检查返回值，随后对有效 supply index 返回 0。因此：
- IO-domain probe 成功或 driver symlink 出现，不等于 14 次底层 write 均成功。
- 需要独立 readback，至少核对 VSEL0/1/2 中本驱动负责的 selector bit。
- probe 若在先前 supply 已完成 write 后，后续 supply lookup、电压读取或 notifier 注册失败，cleanup 仅注销已注册 notifier；源码没有恢复已写 selector 的 rollback。
- probe 的成功/失败日志都不能替代寄存器 readback。

## 5. Readback 与 rollback 方案审查

### 5.1 只读前后读回

预期先读取完整 32-bit：
- PMU GRF `0xfdc20140` / offset `0x140`
- PMU GRF `0xfdc20144` / offset `0x144`
- PMU GRF `0xfdc20148` / offset `0x148`

至少保存三份原始值，并单独提取本 driver 会影响的低位：
- VSEL0/VSEL1：bits 1, 3, 4, 5, 6, 7
- VSEL2：bits 1, 5

probe 后再次读取完整寄存器值，比较目标 bit 是否符合当次实测 regulator 电压分类，同时确认非目标 bit 未改变。不可把只检查 driver bind 或 dmesg 当作 PASS。

### 5.2 当前发现的回退工具限制

固定 Linux 6.18 `drivers/base/regmap/regmap-debugfs.c` 中：
- `registers` 文件默认 mode 为 0400（只读）；
- 只有在源码显式定义 `REGMAP_ALLOW_WRITE_DEBUGFS` 时才变为 0600；
- `access` 文件也是 0400；
- 本项目固定内核未审计/未启用该源码调试写宏。

因此，**不能把 regmap debugfs 当成可用的寄存器回写/rollback 接口**。本轮没有发现已验证、可在当前 RAM-only 环境中安全恢复这三个 PMU GRF 寄存器目标位的工具路径。不得通过临时启用 debugfs 写权限、`/dev/mem`、猜测的 devmem 命令或未经审查的脚本替代回退设计。

### 5.3 回退设计候选（尚未实现/验证）

理论上可按 Rockchip hiword-mask 语义恢复 probe 前保存的 selector 位：对每个受影响寄存器，使用目标位 mask 写回原始 low-bit 值。其写参数形式为：

`restore_word = (mask << 16) | (pre_value & mask)`

但执行此动作本身仍是 PMU GRF 写操作，必须通过受控的内核 regmap helper/专用测试路径实现，并验证：
1. helper 绑定的是同一个 `fdc20000` PMU GRF regmap，而不是主 GRF `fdc60000`；
2. 只允许写 offset `0x140/0x144/0x148` 的上述目标 bit；
3. 写后能重新读取并验证恢复值；
4. 出错时停止，不继续执行其他硬件阶段。

该 helper 目前只是设计候选，不是已实现能力，也不构成执行授权。不要假设重启或掉电会恢复原 selector 值。

## 6. G4-P 准入条件（全部满足前保持 HOLD）

- [ ] 确认目标启动使用 G4-B 对应 Image/DTB/initramfs 的确切 SHA-256；启动环境仍是 RAM-only。
- [ ] 只读确认 RK809 provider 已绑定、16 个 regulator objects 仍注册，IO-domain consumer 尚未 probe。
- [ ] 只读采集 9 个 supply 的 consumer 解析结果/实际 `regulator_get_voltage()` 软件读数；对 vccio3 明确确认 LDO5 当前电压分类。
- [ ] 只读采集 SWITCH_REG1 状态与上游 supply 信息；明确记录该读数不能替代实体电压测量。
- [ ] 确认 PMU GRF regmap 的实际 debugfs/只读 readback 路径可用，并先做不写入的地址/offset/访问属性核对。
- [ ] 实现并审查受限 rollback helper，或提供其他经过验证的回退机制；不得使用未经验证的 `/dev/mem`/debugfs 写入。
- [ ] 固化完整 pre-value、14 项 expected write 和 post-readback 表；定义任何 mismatch、unexpected voltage、probe defer/failure 时的停止与恢复条件。
- [ ] 单独提交本次操作影响范围、目标寄存器、回退写入、验证步骤和风险，取得用户对本次 G4-P 的明确授权。

目前至少有两项未闭合：consumer 端 9 路电压/状态未采集；可验证的受限 rollback helper 尚不存在。因此当前结论为 **NO-GO / HOLD**。不启动设备、不加载 G4-P DTB、不触发 probe、不写 PMU GRF。

## 7. 运行时副作用边界

若未来获准执行：
- 只恢复 IO-domain 节点和 `CONFIG_ROCKCHIP_IODOMAIN=y`；保持 GMAC1/MDIO/PHY、eMMC、TF SDMMC0、SDIO、GPU、SARADC disabled。
- 运行期间不执行 suspend/resume，不改变 regulator voltage，不触发 notifier voltage-change 路径。
- 不启用任何 peripheral consumer；不发送网络帧。
- 若 probe defer/fail、regulator read error、GRF readback mismatch 或无法确认完整状态，立即停止后续阶段并进入预先审查的回退流程。
- 不把 G4-P 的通过解释为 rail 实测通过、GMAC 可用或网络恢复。

## 8. 当前状态

- G4-S：PASS。
- G4-B：PASS（Actions run `45997129528`，artifact `15196608755`）。
- G4-P 静态写入矩阵：已展开。
- G4-P readback：方案定义，运行时接口尚未验证。
- G4-P rollback：只有理论 masked-restore 设计，helper 未实现/未验证。
- G4-P runtime：**HOLD / NOT AUTHORIZED / NO-GO**。
- 后续 TF-rootfs DTB 与完整用户空间：等待 G4-P 决策门，不提前启动。
- eMMC：保持冻结；本报告不涉及 eMMC 操作。




补充设计审查：`PANTHER-X2-G4-P-SAFE-DRIVER-DESIGN-REVIEW-20261127.md` 进一步确认 regulator notifier 在 regulator mutex 持有期间执行；IO-domain 内部锁不得跨 regulator core API。普通 remove/unbind 自动恢复目前不安全，除非证明 teardown 全窗口 rail 冻结。G4-P-SAFE 第一版应把成功 probe 后保持绑定作为默认策略，不将 unbind 当作回退手段。

## 9. 下一阶段建议：只做代码级安全增强候选，不执行硬件

当前 G4-P 的阻塞点不是构建能力，而是 stock driver 缺少可验证的事务性恢复。下一步优先准备一个**独立的 G4-P-SAFE build-only 代码候选**，不替换当前 G4-B frozen artifact，也不运行实机：

1. 在 IO-domain probe 开始任何 selector 写入前，对 VSEL0/1/2 做 `regmap_read()`，保存原始值和目标位 mask；任一预读失败则零写入退出。
2. 为 RK3568 每一次 hiword-mask `regmap_write()` 检查并传播错误；不再无条件返回 0。
3. 任一写入、regulator notifier 注册或 post-write readback 失败时，先注销已注册 notifier，再按保存的原始 selector bits 做受限 masked restore；对恢复操作本身检查返回值并 readback 验证。
4. probe 成功时保留原始快照；在 platform driver `remove()` / 显式 unbind 路径执行同一受限 restore 并验证，以便一次性验证后恢复启动前 selector bits。
5. restore 任一项失败时必须明确报告状态未知并停止后续硬件阶段；不能把 rollback best-effort 当成成功。
6. 增加纯软件测试（例如对写入顺序、mask/value 计算、各写点故障注入和 rollback 顺序的单元测试）；CI 只验证 patch 编译、符号、测试结果与 DTB 隔离。

该候选有严格局限：软件无法保证在 CPU hang、kernel panic、突然断电或 GRF 总线不可访问时完成 rollback；remove/unbind 的可用性、regmap 锁与 notifier 生命周期还必须静态审计。即使 build-only 和软件测试通过，也不能代替 G4-P 运行时 readback，更不构成硬件操作授权。

**当前执行建议：** 先做上述 driver patch 的源码级设计审查与 build-only 验证；在确认安全增强机制可实现、可测试且不会扩展到 PMIC 写入或其他外围设备后，再提交一份独立的 G4-P runtime 操作申请。未经明确授权，继续不启动设备、不 probe、不写 GRF。
