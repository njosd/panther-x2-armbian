# Panther X2 项目 A — G2 RK809 MFD 准入再评估（2026-11-27）

## 1. 为什么重新评估

回读原始 G0.2、R3 §11/§21–§26、6.1.116 黄金运行记录后，发现 2026-11-27 新建的 G2 计划把“黄金行为相符 + 用户单独授权”写成了可执行前提，弱化了既有 G0.2 的更严格 HOLD 决策。这是不一致，现予纠正。

本报告仅做仓库证据复核和计划修订；没有设备访问、构建、存储写入、PMIC 操作或网络发送。

## 2. 黄金基准带来的正向证据

已验证：
- 6.1.116 正常运行系统配置包含 MFD_RK808；固定源码端点为 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。
- 6.1.65 config 与 modules.builtin 已归档，`MFD_RK808=y`、`REGULATOR_RK808=y`。
- 6.1.65 候选与 6.1.116 固定源码端点的 `drivers/mfd/rk808.c` 完全相同。
- 6.1.116 实机中断日志有 IRQ 38 `rk817 / rk805_pwrkey_rise` 与 IRQ 39 `rk817 / rk805_pwrkey_fall`；说明黄金系统 MFD/PMIC PWRKEY 子设备和 IRQ 事件链确实工作。
- 6.1.65 候选与 6.18.63 的 RK809 pre-init table、24-bit IRQ mapping、SWITCH_REG1 descriptor 已在 R3 §21–§26 做过定点比较。

这些是强正向证据：同一 Panther X2、同一 RK809 类 PMIC，在黄金系统里已经运行过 MFD/regulator 软件链。不能把 PMIC/电源链当作未知硬件，也不能仅因发现驱动写寄存器就断言 6.18 一定失败。

## 3. 黄金证据仍未证明的部分

6.1.116 的 IRQ 38/39 日志证明 PWRKEY IRQ 事件被 Linux 接收；它没有记录 PMIC IRQ status/ACK 寄存器启动时的原始值、每次 mask/ACK 写入值，也没有证明所有保留位在每次启动都为零。

6.1.116 与 6.18.63 不是同一 MFD 实现：
- 黄金使用旧 `CONFIG_MFD_RK808` / `drivers/mfd/rk808.c`；
- 6.18 使用 `MFD_RK8XX_I2C` / `rk8xx-i2c.c` + `rk8xx-core.c`；
- 6.18 对 RK809 复用 RK817 IRQ layout，并在 probe 中注册 regmap IRQ、读取 status、初始化 mask/ACK；其路径与黄金旧驱动的实机行为不能仅凭 IRQ mapping 相同就认定完全等价。
- 6.18 probe 还会运行完整 RK817-family pre-init 表，其中包含 RTC、codec、GPIO interrupt polarity、thermal threshold 等网络以外寄存器写入。

Datasheet Rev 2.4 对部分 0xFA/0xFC 位标注 reserved/W1C/RC，而 Linux IRQ table 对相应位有映射。现有黄金运行记录没有给出这些寄存器的实际上电状态或 ACK 访问轨迹，故无法用 IRQ 38/39 日志消除该语义边界。

## 4. 修订后的 G2 状态

**G2 stock RK8xx MFD probe：HOLD / NOT AUTHORIZED。**

这不是硬件 FAIL，也不是确认 6.18 driver 有 bug。准确含义：
- 黄金基准已证明同板 PMIC/MFD/IRQ 功能链有正常运行历史；
- 6.18 的相关代码和黄金旧实现有明显共性，但不是完全相同的驱动入口/初始化生命周期；
- stock 6.18 probe 会产生已知 PMIC 写入，且 IRQ ACK 对部分保留位的具体硬件语义尚未闭合；
- 现有只读白名单仍仅为 0xED、0xEE、0xF0、0xF6；不能把既往 RO 读取授权扩展为 MFD probe 授权；
- 单独口头说“继续”不等于授权这组 PMIC 写入。

所以不能仅以“用户另行授权”作为唯一前置条件。必须先完成下面的只读软件证据审查，再提交精确的 G2 变更与副作用清单供用户决定。

## 5. 下一项工作：G2-S 静态对照补齐（允许继续）

仅用已锁定源码与现有黄金日志，补齐以下差异表，不访问设备：
1. 对照 6.1.116 `rk808.c` 与 6.18 `rk8xx-core.c` 的 IRQ chip 定义、regmap_irq flags、init_ack_masked、status read、mask write、ACK write 条件与顺序。
2. 对照旧驱动与 6.18 的 pre-init 表：每个寄存器地址、mask、value、芯片手册定义、是否涉及 RTC/codec/thermal/IRQ/rail。
3. 对照 MFD cell 列表与 6.1.116 实机存在的 pwrkey IRQ，确认 6.18 是否保留相同 IRQ resource mapping。
4. 明确列出 6.18 额外写入、缺少的 ID read、system-power-controller 属性处理差异。
5. 每一项结论标注：黄金实机证据、黄金源码证据、6.18 源码证据、datasheet 证据；不可互相替代。

若以上对照没有发现超出黄金行为的关键写入/IRQ 语义差异，才提交一个“有明确写入集合、预计访问条件、停止条件、失败回退和独立授权点”的 G2 实机方案；若差异无法解释，G2 继续 HOLD，不做定制驱动规避，不做 PMIC 测试。

## 6. ABCD 检查

G2-S 为纯静态软件审计，没有 netdev、interface open 或 DMA，ABCD = NOT EXECUTABLE（阶段性记录）。G2 结束仍必须重评是否已有更早可用的 AF_PACKET 目标；不能为了让 ABCD 可执行而提前启用 GMAC。

G3 regulator provider 与 G4 IO-domain 仍分别设门。首次 netdev/open/DMA 具备时立即执行单帧 A→B→C→D，并在 LAN 对端捕获同一 run_id/sequence/hash（E6）；不能等到 TCP/IP 阶段。

## 7. 结论

当前可继续的是 G2-S 静态对照，不是 G2 stock probe。无设备操作授权，无构建授权，无 PMIC 写入授权。
