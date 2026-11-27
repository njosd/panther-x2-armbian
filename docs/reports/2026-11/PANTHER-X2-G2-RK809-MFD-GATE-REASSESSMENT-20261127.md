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


## 8. G2-S 静态源码对照结果（2026-11-27，补充）

### 8.1 固定源码与对象身份

- 黄金 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`；`drivers/mfd/rk808.c` blob `e00da7c7e3b11c83530c211f62271c4251a8d80b`。
- 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`；`drivers/mfd/rk8xx-core.c` blob `21182df45d1b6b75f25c3aaf41bc8a14f36b3deb`；`drivers/mfd/rk8xx-i2c.c` blob `161b25fbe146ec9b652822a44896013c581e3500`。
- 两版本 `drivers/input/misc/rk805-pwrkey.c` blob 完全相同：`76873aa005b419b0c1644b9eee7f886c389cabd7`。

### 8.2 IRQ mapping / mask / ACK：没有发现 6.18 新增差异

两版 RK817 IRQ chip 定义一致：
- 24 个 logical IRQ；
- 3 组 status/mask register，stride 2；
- status/ack base 0xF8，mask base 0xF9；
- `init_ack_masked = true`；
- IRQ id 0–23 以 `REGMAP_IRQ_REG_LINE(id, 8)` 对应三组 8-bit status/mask。

6.1.116 黄金实机 `/proc/interrupts` 已有 RK817 parent IRQ 与 PWRKEY 子 IRQ 记录：IRQ 38/39 分别登记 `rk805_pwrkey_rise` / `rk805_pwrkey_fall`，RTC alarm 子 IRQ 也已登记。计数为 0，因此这是 MFD/IRQ domain/child request 注册的运行证据，不是按键事件已实际触发的证据。

此前报告指出的 0xFA/0xFC datasheet reserved/W1C/RC 位与 Linux 24-bit mapping 不一致，确实是两版共有的历史实现疑点，不是 6.18 regression。黄金 IRQ 子设备注册成功降低了“整个 IRQ 框架不兼容”的风险，但没有提供初始化时 0xFA/0xFC 原始状态及 ACK 写入轨迹，故仍保留为证据限制；不应把它表述成已证明会造成故障。

### 8.3 RK809 pre-init 写入集合：两版完全相同

6.1.116 `rk808.c` 对 RK809/RK817 选择同一 `rk817_pre_init_reg[]`；6.18 `rk8xx-core.c` 对 RK809/RK817 选择同一表。此前 R3 §21–§26 已逐项核验数组内容逐字节相同。

两版 probe 顺序相同：先注册 regmap IRQ，再逐项执行 `regmap_update_bits()` pre-init，随后创建 MFD cells。没有发现 6.18 为 RK809 新增一组 PMIC pre-init 写入。写入涉及 RTC_STOP、codec 初始化、GPIO IRQ polarity 和 thermal threshold 等；不是网络供电 enable/selector 操作，但属于真实 PMIC 写入，不能称为只读。

### 8.4 识别、MFD cells 与 system-power-controller 差异

| 项目 | 6.1.116 黄金 | 6.18.63 | 影响 |
|---|---|---|---|
| 芯片 variant | 先读 0xED/0xEE，再按 masked ID 选 RK809/RK817 | 由 OF compatible 直接选择 RK809 variant，不在该 probe 中重读 ID | 6.18 缺少 driver 内身份复核；R1 已有独立 RO 实测 0xED=0x80、0xEE=0x94，能补充身份依据，不重复读取 |
| IRQ 初始化 API | `regmap_add_irq_chip()`，显式 remove 时 delete | `devm_regmap_add_irq_chip()` | 资源生命周期不同；IRQ chip 配置和初始化语义相同 |
| pre-init | RK817 表 | 同一 RK817 表 | 无新增写入集合 |
| MFD cells | clkout、regulator、pwrkey、RTC、codec、charger | 相同集合 | G2 不启用 regulator child driver 时不会注册 regulator provider；MFD cell 本身仍会被创建 |
| power controller 属性 | 检查 `rockchip,system-power-controller` | 同时接受标准与 vendor-prefixed 属性 | Panther DT 使用 vendor-prefixed 属性，兼容 |
| poweroff/restart handler | 全局旧式 handler | devm sys-off handler | 注册路径改变；G2 期间禁止主动 poweroff/restart |

### 8.5 新发现：PWRKEY IRQ resource 顺序差异

两版 `rk805-pwrkey.c` 完全相同，固定约定为：
- `platform_get_irq(pdev, 0)` 作为 FALL IRQ，绑定 `pwrkey_fall_irq`；
- `platform_get_irq(pdev, 1)` 作为 RISE IRQ，绑定 `pwrkey_rise_irq`。

但 MFD 的 `rk817_pwrkey_resources[]` 顺序不同：
- 6.1.116：先 `RK817_IRQ_PWRON_RISE`，再 `RK817_IRQ_PWRON_FALL`；
- 6.18.63：先 `RK817_IRQ_PWRON_FALL`，再 `RK817_IRQ_PWRON_RISE`。

header 中两版 enum 均定义 FALL=0、RISE=1。按 pwrkey driver 的 index 约定，6.18 的资源顺序与 consumer 约定一致；6.1.116 的资源顺序表面上相反。黄金 `/proc/interrupts` 标签与 hwirq 数字的组合仍需按 regmap/platform resource 映射机制谨慎解释，不能仅凭 IRQ label 断言按键物理边沿正确。此差异不影响 Ethernet TX 主链，但 G2 若启用 PWRKEY child，应记录为独立兼容性观察项；不要为了模仿旧数组顺序而回退 6.18。

### 8.6 G2-S 结论

**G2-S 静态对照：PASS（源码差异已明确）；G2 stock probe：仍待单独操作授权。**

本轮未发现 6.18 相较黄金版本增加额外 RK809 pre-init 写入或改变 IRQ chip 的 status/mask/ACK 布局。保留的差异是 ID 选择机制、资源生命周期、power handler API 与 PWRKEY resource 顺序。黄金运行记录证明 6.1.116 的 MFD/IRQ child 能注册；不能证明所有 PMIC ACK 保留位状态，也不能证明 PWRKEY 物理边沿行为。

### 8.7 下一步：G2-B build-only，不 probe

先进行纯构建验证，不接触设备：
1. 以冻结的 6.18.63 commit 为输入，单独启用 `MFD_RK8XX_I2C=y`；其 Kconfig 自动 select `MFD_CORE`、`REGMAP_I2C`、`REGMAP_IRQ`、`MFD_RK8XX`。
2. 如要验证 PWRKEY 子驱动，再加入 `INPUT_RK805_PWRKEY=y`（依赖 `MFD_RK8XX`）；不启用 `REGULATOR_RK808`，避免 G2 提前注册全部 regulator descriptors。
3. 使用 R1 原 DTB 的独立副本，将 RK809 节点临时保持/设为 `status = "disabled"`，GMAC1/MDIO/PHY 继续 disabled。这样 built-in 驱动会进入 Image，但不会匹配并 probe RK809。
4. 构建并检查 `.config`、`modules.builtin`、对象列表、Image/DTB 哈希；只做 QEMU 非硬件启动/自检。该步骤验证 Kconfig、编译、链接和产物封装，不验证 I2C、PMIC 或 MFD runtime。
5. 若 build-only 通过，再单独提交 G2-PROBE 计划：恢复 RK809 DT 节点后 stock probe 会执行第 8.3 节的黄金同款写入和 IRQ 初始化。该步骤必须由用户针对这组确切副作用另行授权；未授权不得替换 SU08G 当前 uInitrd/Image 或启动。

G2-B 阶段 ABCD = NOT EXECUTABLE：RK809/GMAC 节点 disabled，无 netdev/open/DMA。每阶段仍记录检查；一旦后续首次具备目标 netdev/open/DMA，立即执行同一帧 A→B→C→D 并由对端 pcap 验收，不等待 IP 层。
