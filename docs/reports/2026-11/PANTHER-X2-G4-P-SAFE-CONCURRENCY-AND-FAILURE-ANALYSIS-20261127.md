# Panther X2 项目 A — G4-P-SAFE 并发与失败路径深化审查（2026-11-27）

- 基线：Linux 6.18.63，ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f
- 工作分支：g4-iodomain-safe-design
- 类型：源码设计审查；非补丁、非 build-only、非硬件测试
- 实机/寄存器/介质访问：无
- 项目介质边界：SU08G TF only；SN64G 与 eMMC 冻结

## 1. 先前设计的一个必要补充：notifier 与初始电压采样的竞态

仅仅把 GRF 写入串行化，仍不足以保证 probe 初始值不会覆盖刚发生的 regulator voltage-change 事件。

固定源码的顺序是：
- probe 调用 regulator_get_voltage() 获取当前电压；
- 随后调用 iod->write() 更新 selector；
- 再注册该 regulator notifier。

这意味着 stock driver 在初始 get_voltage 和 notifier 注册之间存在未被 notifier 覆盖的窗口；同时，若 SAFE 版本先注册 notifier、再采样电压，也必须处理采样和 notifier callback 的并发交错。

## 2. 可供后续实现评审的 generation-counter 思路（尚未验证）

每个 supply 增加单调递增的 event generation。notifier callback 在 IO-domain mutex 下：
1. 根据 PRE / VOLTAGE_CHANGE / ABORT 事件计算目标 selector；
2. 通过同一 PMU GRF regmap 更新 selector；
3. 成功后递增该 supply generation；失败则记录 fault 状态。PRE 写失败返回 NOTIFY_BAD；POST/ABORT 写失败必须置 faulted。

probe 侧不在 IO-domain mutex 内调用任何 regulator core API：
1. 在 mutex 外读取全部 supply 的 generation 快照。
2. 在 mutex 外逐路调用 regulator_get_voltage()，保存电压结果。
3. 获取 IO-domain mutex，比较所有 generation 是否仍与快照一致。
4. 若任何 generation 已变化，释放 mutex，重新采样（必须有有界重试策略；超过上限则零初始写入退出）。
5. 若全部一致，在持锁期间执行整批初始 selector transaction；callback 在此期间等待 mutex，待 probe transaction 结束后继续更新。
6. 对所有 selector 完成读回验证后，释放 mutex。

该顺序的意图是：若 regulator 事件在 get_voltage 前/期间完成，generation mismatch 会使 probe 丢弃旧采样；若事件在 probe 获取 mutex 后才进入 callback，则 callback 会在 probe transaction 结束后执行，并在 rail 实际改变前完成 PRE selector 更新。

**重要：这只是并发控制候选，不是已经证明无竞态的实现。** 必须针对 regulator core 的精确锁持有范围、notifier PRE/POST/ABORT 时序、generation 原子性和所有错误路径写 KUnit/fake-regmap 测试；还要审查多个 regulator 并发事件。

## 3. 仍未闭合的根本问题：probe 失败后的 notifier 与 rollback 生命周期

上面的 generation 方案解决的是“probe 初始采样是否覆盖已完成事件”的候选竞态，不自动解决 probe 失败：

- 若在 transaction 失败后先注销 notifier，再恢复旧快照，注销后 rail 仍可能变化，selector 会失去同步。
- 若先恢复旧快照，再注销 notifier，恢复到注销之间可能发生 PRE/POST/ABORT callback，可能把 selector 改到当前 rail 对应状态；但注销完成后，未来 rail 变化不再被该 driver 跟踪。
- 若在持有 IO-domain mutex 时调用 regulator_unregister_notifier()，callback 可能正等待同一 mutex，产生死锁。
- 若不注销 notifier 就让 probe 返回失败，devm regulator handle、notifier block 与供电 consumer 生命周期无法安全保留；不能把这种方式当作可行方案。
- 恢复 probe 前旧快照也不一定安全：如果 rail 在失败期间发生过电压变化，旧 selector 可能不再匹配当前 rail。

因此，**“probe failure 时无条件恢复初始 selector 并返回错误”目前没有被证明安全。** 必须明确选择并证明一种生命周期策略，不能只实现一个 rollback label 就宣称事务安全。

## 4. 可能的架构方向与决策门

### 方向 A：完整事务与受控 regulator freeze

要求在整个 prepare / initial write / failure rollback / notifier teardown 期间，能通过 regulator framework 提供可验证的 rail freeze 或等效约束。当前没有发现可直接用于所有这些 consumer 的通用 freeze API；不能假定“当前没有电压变化”就是冻结。

### 方向 B：将失败后的安全状态定义为 fail-stop，而非恢复旧快照

任何 GRF 写入或读回失败时：
- 停止后续 selector 写入；
- 保持 notifier 继续管理所有可管理的 rail，避免失去事件同步；
- 将 driver/设备置于明确 faulted 状态并禁止后续硬件阶段；
- 但要解决 probe 无法成功返回且 notifier 生命周期随 devm 释放的问题。可能需要更高层 supervisor / persistent owner / driver architecture redesign，而非简单 platform probe。

该方向当前也没有可直接落地的内核生命周期方案。

### 方向 C：不让 IO-domain driver 在当前验证阶段执行写入

先保持 IO-domain node disabled，仅通过只读 syscon/regmap 获取寄存器初值和只读 regulator 状态；把 driver 的硬件写入验证推迟到完成独立安全设计之后。此方向可用于收集 G4-P 前置只读证据，但不能算作 G4-P runtime PASS。

## 5. 本轮结论

1. generation-counter + mutex 的采样/初始写入顺序值得作为后续实现候选，但尚未验证。
2. probe 失败后 notifier teardown 与 rollback 之间存在无法靠普通 mutex 解决的生命周期问题。
3. 当前尚无已证明安全的 G4-P-SAFE 完整事务架构。
4. 不能因为 G4-B build-only PASS 或后续单元测试 PASS 就执行 G4-P。
5. 目前最安全的项目推进方式是先做只读 runtime readiness 方案（不启用 IO-domain node、不执行 GRF 写入），并在源码层继续解决 driver failure lifecycle。若无法证明安全，G4-P 应保持不执行。

**状态：G4-P NO-GO / HOLD / NOT AUTHORIZED。G4-P-SAFE patch 尚未实现。**

## 6. 明确禁止事项

- 不在当前阶段启用 IO-domain node 后直接观察“是否正常”。
- 不通过 /dev/mem、debugfs write、devmem 工具或其他旁路执行 PMU GRF 写入。
- 不将 driver unbind/remove 作为 rollback。
- 不在 IO-domain mutex 持有期间调用 regulator core API。
- 不触碰 eMMC 或 SN64G；不安装软件、不改变设备配置。


## 7. 固定 regulator core 锁与 notifier chain 的精确调用关系

进一步核对固定源码 drivers/regulator/core.c，把 regulator mutex 与 notifier chain 锁区分如下：

- _notifier_call_chain() 上方源码注释明确写明：调用者必须持有 regulator mutex；该函数内部调用 blocking_notifier_call_chain()。见 core.c 约 5092–5115 行。
- 电压调整入口 regulator_set_voltage() 在调用 _regulator_do_set_voltage() 前执行 regulator_lock(rdev)，并在退出路径 regulator_unlock(rdev)。见约 4500–4520 行。其内部 _regulator_call_set_voltage() 在该锁保护路径中发出 PRE；底层 set_voltage 失败时发出 ABORT。见约 3571–3608 行。
- regulator_register_notifier() 和 regulator_unregister_notifier() 本身直接调用 blocking_notifier_chain_register/unregister()，并不在这两个 wrapper 内获取 regulator mutex。见约 5052–5090 行。
- 因此有两把不同的锁：regulator mutex（保护电压变化路径）与 blocking notifier chain 的 rwsem（保护 notifier 链表/调用同步）。不能把二者混为一谈。

### 对锁序与 teardown 的具体影响

1. callback 执行时持有 regulator mutex，并在 blocking notifier call-chain 的读侧同步区间内执行。
2. callback 若等待 IO-domain mutex，而 probe/remove 持有 IO-domain mutex 再调用 regulator API 或 notifier unregister，可能出现锁序反转/等待环。
3. 特别是 unregister：如果 callback 已进入并等待 IO-domain mutex，另一个线程持有 IO-domain mutex 调用 blocking_notifier_chain_unregister()，会等待正在执行的 callback 退出；callback 又等待 IO-domain mutex，形成确定的等待环。
4. 所以所有 regulator core API（包括 register/unregister notifier、get_voltage）均不得在持有 IO-domain mutex 时调用。notifier unregister 必须在 IO-domain mutex 外完成。
5. 但“在 mutex 外 unregister”只解决死锁，不自动解决 unregister 后 rail 继续变化与 selector 失去跟踪的问题；仍需要可证明的 rail freeze 或其他完整生命周期协议。

### 对 generation-counter 候选的修订要求

- 每个 supply 的 generation 需使用原子/锁保护，callback 在完成 selector 写入后更新 generation；不能只在事件入口递增后忽略写入失败。
- 初始采样与 notifier 必须先建立订阅关系，再在 IO-domain mutex 外调用 regulator_get_voltage()；随后在 IO-domain mutex 下比较 generation 并执行初始 transaction。
- 不得在 IO-domain mutex 内调用任何 regulator API。
- 必须证明 regulator PRE callback 与实际 rail 改变之间的顺序，以及 ABORT/POST 的回调覆盖范围；不能仅测试“callback 最终被调用”。
- 多 supply transaction 期间，任一 regulator 的 PRE callback 可能持有自己的 regulator mutex 等待 IO-domain mutex；初始 transaction 本身不能再反向请求任何 regulator mutex。
- 该候选仍不能解决 probe transaction 中途失败后的 notifier 生命周期与 devm 清理问题；不能据此声称具备安全 rollback。

以上行号以固定 commit 的源文件为准；未来 kernel commit 变更时必须重新定位与复核。
