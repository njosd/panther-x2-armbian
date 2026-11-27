# Panther X2 Project-A — G2-PROBE 副作用、RTC 子设备与 IRQ 语义复核（2026-11-27）

- 状态：**静态审计补充完成；G2-PROBE 继续 HOLD / NOT AUTHORIZED。**
- 范围：固定 Linux 6.18.63 G2-B artifact、RK8xx MFD/IRQ/RTC 源码、RK809 Rev 2.4/2.5 数据手册及黄金运行记录的只读对照。
- 本轮没有访问 Panther X2、执行 I2C/PMIC 事务、构建新镜像、写 TF/eMMC、启用驱动或发送网络帧。

## 1. 本轮新增的关键结论

**当前 G2 runtime/G2-B 配置不能原样作为 G2-PROBE 配置。**

固定 G2-B 最终配置 SHA256：
`ffa99212686a1347145628fd50ecf3341437efe4a4f130002e4b27003c4f553b`

从实际 artifact `15167050233` 的 `output/kernel.config` 核实，下列子驱动均未启用：

- `CONFIG_REGULATOR_RK808`
- `CONFIG_INPUT_RK805_PWRKEY`
- `CONFIG_RTC_DRV_RK808`
- `CONFIG_SND_SOC_RK817`
- `CONFIG_CHARGER_RK817`
- `CONFIG_COMMON_CLK_RK808`

RK8xx MFD core/I2C transport 为 built-in。RK809 节点在该 artifact DTB 中 disabled；这只是 build-only 隔离，不会发生 probe。

RK809 的 `rk817_pre_init_reg[]` 会先设置 RTC_CTRL 的 `RTC_STOP` 位（地址 0x0D bit0）。RK809 Rev 2.4/2.5 明确说明该位为 1 时 RTC frozen、为 0 时 RTC running。MFD cell 列表虽然创建 `rk808-rtc` 子设备，但由于 `RTC_DRV_RK808` 未启用，该子设备不会绑定 RTC 驱动，也就不会执行 RTC 驱动 probe 中清除 STOP 位的动作。

因此，若仅把当前 G2 DTB 中 RK809 节点改为 enabled，而不改变上述配置，MFD probe 可能使 PMIC RTC 保持冻结。这与黄金系统中已观察到 RTC alarm 子 IRQ 注册的完整软件路径不等价。**不能把当前 G2 runtime artifact 直接升级为“只启用 RK809 节点”的 G2-PROBE 镜像。**

## 2. MFD parent probe 的确定执行顺序

固定源码：
- Linux：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- `drivers/mfd/rk8xx-i2c.c`
- `drivers/mfd/rk8xx-core.c`
- `drivers/base/regmap/regmap-irq.c`

RK809 I2C probe 通过 OF compatible 选择 RK809 variant，建立 I2C regmap，再调用 `rk8xx_probe()`；6.18 该路径不在 probe 中重新读取 0xED/0xEE。此前 0xED=0x80、0xEE=0x94 的只读证据仅用于身份交叉核验，不授权额外寄存器访问。

RK809/RK817 共用以下顺序：

1. 选择 RK817-family IRQ chip、pre-init table 和 MFD cells。
2. 检查 parent IRQ 是否存在。
3. `devm_regmap_add_irq_chip()`：建立默认 IRQ mask、读取状态寄存器、按条件 ACK、创建 IRQ domain 并请求 parent threaded IRQ。
4. 遍历 `rk817_pre_init_reg[]`，执行 `regmap_update_bits()`。
5. 创建 MFD child devices。
6. Panther DTB 含 `rockchip,system-power-controller` 属性；启用 RK809 节点后，6.18 会注册 power-off/restart sys-off handler。注册本身不立即关机或重启。

## 2.1 重要身份字段更正：0xEE 低 nibble 是 reserved，不是版本号

此前项目报告将 `0xEE=0x94` 的低 nibble 记录为“版本字段 4/含义未知”。回看历史手册并核对 RK809 Datasheet Rev 2.5 后，准确边界是：
- `PMIC_CHIP_NAME (0xED)` 全 8 位为 CHIP_NAME，默认 `0x80`；
- `PMIC_CHIP_VER (0xEE)` 的 bit[7:4] 是 CHIP_NAME code[3:0]，默认 `0x9`；
- 早期 Rev 1.01 曾将 bit[3:0] 定义为 CHIP_VER code（reset default `0x2`）；Rev 1.7、1.8、2.4、2.5 的公开手册则将 bit[3:0] 改为 RESV，reset default 仍为 `0x2`。
- Panther X2 已有只读值 `0xED=0x80`、`0xEE=0x94`：高 nibble `0x9` 与 RK809 CHIP_NAME code 一致；低 nibble `0x4` 在早期 Rev 1.01 语义下可对应 CHIP_VER code 4，但按 Rev 1.7 及以后定义则是 reserved 非默认值。

因此不能单凭 `0x94` 宣称当前芯片就是 silicon revision 4，也不能据此判定芯片异常。手册修订历史没有解释字段为何改为 RESV，也没有说明当前器件低 nibble=4 与 RK817 IRQ map 的适用关系。该差异需由 Rockchip 正式说明；不得通过扩大 I2C 读取白名单或试写寄存器自行探查。

数据手册定位：RK809 Rev 2.5 §5.1 p.55 / §5.2 p.119，`PMIC_CHIP_NAME` 与 `PMIC_CHIP_VER`。参见 [RK809 Datasheet Rev 2.5](https://datasheet.lcsc.com/datasheet/pdf/dc4249f899d1f7640dc738c73aecc6ea.pdf?productCode=C54771187)。

## 3. IRQ mask/status/ACK：数据手册差异仍未闭合

RK817 IRQ 表定义 24 个逻辑 IRQ，按 3 组、每组 8 位映射到 status/mask registers。对应配置为：

- status/ACK base：0xF8，stride 2 → 0xF8、0xFA、0xFC；
- mask base：0xF9，stride 2 → 0xF9、0xFB、0xFD；
- `init_ack_masked=true`；
- 24 个 `REGMAP_IRQ_REG_LINE(id, 8)` 使三组默认 mask buffer 均为 0xFF。

### 3.1 parent IRQ 初始化阶段

regmap-irq 初始化会：
- 根据 24 个 `REGMAP_IRQ_REG_LINE(id, 8)` 生成三组 `mask_buf_def=0xFF`；
- 对 0xF9、0xFB、0xFD 执行 mask register update，将每组 8 位全部设为 masked。由此 0xFB[7:2]、0xFD[7:6] 与 0xFD[1:0] 这些在 Rev 2.5 标为 reserved RW 的位也会被写成 1；
- 读取 0xF8、0xFA、0xFC；
- 如果某组 status 非零，对相应 ACK/status register 写入 `status & mask`；
- 然后建立 IRQ domain 并请求 parent threaded IRQ。

`regmap_update_bits()` 是 read/modify/write；不是每次调用都无条件写入，只有目标 masked bits 与当前值不同时才会写。对 ACK 路径则按 regmap-irq 配置执行 status 写回。

### 3.2 与 RK809 Rev 2.4/2.5 的明确差异

两份公开数据手册对相关位域给出的描述一致。按 Rev 2.5 可列出的有效中断位为：0xF8 全 8 位（8 项）、0xFA bit[1:0]（2 项 plug-in/out）、0xFC bit[5:2]（4 项 codec），合计 14 项；而 Linux RK817 IRQ chip 对 RK809 也无差别地建立 24 个通用 IRQ line。**因此 24-bit Linux map 中有 10 位并非 RK809 Rev 2.5 文档定义的有效中断源**：0xFA bit[7:2] 六位，以及 0xFC bit[7:6]、bit[1:0] 四位。

| 寄存器 | 数据手册定义 | Linux 24-bit IRQ map 的影响 |
|---|---|---|
| 0xFB PMIC_INT_MSK1 | bit7:2 reserved RW | Linux 将整字节纳入 mask map，默认写 mask=0xFF |
| 0xFD PMIC_INT_MSK2 | bit7:6、bit1:0 reserved RW | Linux 将整字节纳入 mask map，默认写 mask=0xFF |
| 0xFA PMIC_INT_STS1 | bit7:2 reserved W1C | Linux 将这些位也映射为 IRQ status/ACK 位 |
| 0xFC PMIC_INT_STS2 | bit7:6 reserved RC；bit1:0 reserved W1C | Linux 将这些位也映射为 IRQ status/ACK 位 |

这不是 6.18 新引入的版本差异：黄金 6.1.65 候选和 6.1.116 源码使用相同的 RK817 24-bit mapping。但黄金 IRQ 38/39 和 RTC child IRQ 注册记录只证明部分子 IRQ 能注册/运行，不能证明额外 10 个未被 Rev 2.5 定义为有效 IRQ 的位在当前器件上的语义，也没有提供启动时这些状态位的读回值。

特别注意：0xFC 的部分位在数据手册中标为 RC。不能为了“补一个状态证据”而随意增加对 0xFC 的只读读取；读取本身可能清除状态。现有只读白名单仍仅限 0xED、0xEE、0xF0、0xF6，不扩大到 0xF8–0xFD。

### 3.3 RTC child 请求 alarm IRQ 后的额外 ACK 行为

`rk817_rtc_resources` 将 RTC alarm 映射到 `RK817_IRQ_RTC_ALARM`，其逻辑 IRQ index 为 5，即第一组 mask/status 的 bit5。

若启用 `RTC_DRV_RK808`，RTC driver probe 会请求该 alarm IRQ。regmap-irq unmask 路径会清除 mask buffer 的 bit5；随后 `regmap_irq_sync_unlock()` 会同步 mask，并按 `init_ack_masked` 对仍处于 masked 状态的 IRQ 写 ACK。按当前源码逻辑，mask buffer 预期为第一组 0xDF、第二/第三组 0xFF；ACK 路径可能向 0xF8/0xFA/0xFC 写入相应 mask 值。

因此，启用 RTC child 虽可恢复黄金系统的 RTC 生命周期，却也会触发更明确的 ACK 写入路径；不能只把它当作“加一个无副作用 RTC 驱动”。这进一步要求先解决 RK809 datasheet reserved/RC 位与 Linux RK817 mapping 的证据差异。

### 3.4 与 RK817 Rev 2.1 对照：Linux 24-line map 的来源与边界

RK817 Rev 2.1 数据手册对同一组 0xFA/0xFB、0xFC/0xFD 寄存器定义了完整的 24 个 IRQ：0xFA[7:2] 是 charger/battery 事件，0xFA[1:0] 是 plug-in/out；0xFC[7:6] 是 BAT_HI/BAT_OVP，0xFC[5:2] 是 codec，0xFC[1:0] 是 TS_GPIO/GATE_GPIO。也就是说，Linux 的 24-line `rk817_irq_chip` 与 RK817 Rev 2.1 的寄存器定义吻合；但 RK809 Rev 2.5 对应寄存器只列出 14 个有效中断位，其余 10 位（0xFA[7:2]、0xFC[7:6]、0xFC[1:0]）为 reserved/RC/W1C reserved。RK809 Rev 2.5 的产品特性列出 battery fuel gauge，但没有 RK817 集成式 charger/power-path 功能；这些额外 IRQ 的适用性必须按具体 RK809 型号/硅片由 Rockchip 确认。

6.18.63 `rk8xx_probe()` 对 `RK809_ID` 与 `RK817_ID` 使用同一个 `rk817_irq_chip`、`rk817_pre_init_reg[]` 和 `rk817s[]` MFD cell array（包括 `rk817-charger` child）。6.1.65 与 6.1.116 也使用相同的共享实现。因此这是一个**跨芯片型号共享驱动的适用性问题**，不是 6.18 新引入的差异；公开 RK809 与 RK817 数据手册对额外 IRQ 位的定义确有差异，但现有资料不足以判定这是 RK809 数据手册省略、RK809 silicon 兼容保留，还是 Linux 共用 mapping 过宽。

准入影响：不能把 RK817 datasheet 的 24 个 IRQ 定义自动套用到 Panther 的 RK809；也不能仅因 RK809 datasheet 标为 reserved 就擅自修改 Linux map。需要 Rockchip 明确 RK809 实际 silicon 对 0xFA[7:2]、0xFC[7:6]、0xFC[1:0] 的行为及共用 24-line IRQ map 的适用条件。

**MFD child IRQ resource 映射（6.18.63 源码，不等于实机已绑定）：** 若 PWRKEY child driver 绑定，它只请求 IRQ 0/1（0xF8 bit0/1）；RTC child driver 只请求 IRQ 5（0xF8 bit5）；charger child driver 只请求 IRQ 8/9（0xFA bit0/1，RK809 文档定义为 plug-in/out）；codec child 没有 MFD IRQ resource。黄金运行记录可证明 PWRKEY/RTC 子 IRQ 已注册，但不能据此推断 charger/codec child 也绑定。RK809 文档未定义的 10 个 line（IRQ 10–17、22–23）没有被上述 MFD child resource 请求，但仍留在 parent 的 24-line regmap IRQ map 中，默认 mask=1，并可能参与初始化 status read/ACK。这个事实降低了“子驱动主动使用这些 reserved IRQ”的风险，但不能消除 parent 初始化触碰这些位的兼容性问题。

资料：
- [RK809 Datasheet Rev 2.5](https://datasheet.lcsc.com/datasheet/pdf/dc4249f899d1f7640dc738c73aecc6ea.pdf?productCode=C54771187)，§5.2 pp.125–126。
- [RK817 Datasheet Rev 2.1](https://atta.szlcsc.com/upload/public/pdf/source/20240126/1D84E9BEA212072F9DD3BF1F36FC3510.pdf)，§5.2 pp.136–138。

## 4. pre-init 写入集合的精确规模与语义

`rk817_pre_init_reg[]` 在锁定的 6.18.63 源码中有：

- 77 个 `regmap_update_bits()` 表项；
- 59 个不同的寄存器符号；
- 其中 18 个寄存器符号在表中重复出现；
- 74 个 codec 初始化表项（包含重复项），覆盖 56 个不同 codec 寄存器符号；
- 其余 3 项为 RTC_CTRL、GPIO_INT_CFG、SYS_CFG1。

注意：这是 77 次 read/modify/write 请求，不等于 77 次必然发生的物理写事务；`regmap_update_bits()` 会比较目标位，只有值确实变化时才写。

关键非 codec 项：

| 地址 | 操作 | 数据手册/功能含义 |
|---|---|---|
| 0x0D | 设置 RTC_STOP bit0 | 冻结 RTC，等待 RTC child probe 再清除 |
| 0xFE | 设置 INT_POL 为 active-low | 修改 PMIC INT pin 极性配置 |
| 0xF2 | 设置 HOTDIE=105°C、TSD=140°C 对应字段 | 修改 PMIC thermal threshold 配置 |

74 个 codec 表项即使在 codec child driver 未启用时也会由 MFD parent probe 执行；关闭 codec driver 并不能跳过这些 pre-init。源码注释指出部分寄存器来自 vendor driver，公开数据手册未完整定义（例如 0x16、0x19、0x2E 对应项）。这不是网络供电 enable 操作，但是真实的 PMIC 配置读改写。

## 5. 若纳入 RTC child，额外副作用也必须列入

固定 6.18.63 `drivers/rtc/rtc-rk808.c` 的 `rk808_rtc_probe()` 对 RK809 选择 RK817 RTC register map，随后：

1. 对 0x0D 执行 update：清除 STOP_RTC bit0，并设置 RTC_READSEL bit7，使 RTC 使用 shadowed timer。
2. 对 0x0E 写入 `RTC_STATUS_MASK=0xFE`。
3. 设置 device wakeup capability。
4. 请求 RTC alarm IRQ（逻辑 index 5 / mask bit5），并注册 RTC device。

RK809 Rev 2.4/2.5 对 0x0E 的 bit7:2 定义为 W1C：POWER_UP、ALARM、EVENT_1D、EVENT_1H、EVENT_1M、EVENT_1S；bit1 为 RO RUN。写 0xFE 会清除这些已锁存状态标志（bit1 为 RO，不会改变 RTC running state），不是无影响的探测。该 RTC probe 主体在 6.1.65、6.1.116 与 6.18.63 中具有相同的关键行为，属于黄金系统的既有软件路径，但 0x0E 仍不在当前 PMIC 只读白名单中。

所以如要保持黄金 RTC 生命周期，后续专用 G2-PROBE build 必须把 RTC child 的行为纳入审查；不能沿用当前 `RTC_DRV_RK808 is not set` 的 G2-B 配置并假定行为等价。

## 6. 其他系统状态写入与退出风险

启用 RK809 节点后，`rk8xx_probe()` 会按 Panther DTB 的 system-power-controller 属性注册 poweroff/restart handler。注册动作本身不写 SYS_CFG3；但调用时：

- poweroff handler 对 SYS_CFG3（0xF4）设置 DEV_OFF；
- restart handler 对 SYS_CFG3（0xF4）设置 DEV_RST；
- I2C device shutdown callback 会对 SYS_CFG3（0xF4）设置 SLPPIN_DN_FUN；
- suspend/resume 路径会分别设置 SLPPIN_SLP_FUN / SLPPIN_NULL_FUN。

因此 G2-PROBE 不能把 `reboot`、`poweroff`、suspend/resume 或退出 PID1 shell 当作普通无副作用的结束方式。当前尚未形成经审查的安全退出/恢复流程。

## 7. 失败与回退边界

- `devm_regmap_add_irq_chip()`、IRQ domain、parent IRQ handler 和 MFD child devices 在设备解绑/失败清理时可由 devres 释放。
- 这不构成 PMIC 寄存器回滚。pre-init 若在第 N 项失败，之前已成功写入的项不会由 devres 自动恢复原值。
- probe 在 IRQ 初始化后、pre-init 中途或 MFD child 创建阶段失败，都可能留下部分 PMIC 状态变化。
- 手动 unbind/rebind 不是回滚方案；重试可能重复 IRQ mask/ACK 与 pre-init 访问。
- 当前没有已验证的 PMIC register snapshot/restore 机制，也没有确认的安全退出/断电回退路径。

## 8. G2-PROBE 当前准入决定

**HOLD / NOT AUTHORIZED。** 本轮没有发现 6.18 相比黄金源码新增一套 pre-init 表，但也发现当前 G2-B 配置与黄金运行时的 RTC child 生命周期不一致，且 RK809 Rev 2.5 的 14 个 documented IRQ 与 Linux 共用 RK817 24-line map 的适用性仍未闭合。

解除 HOLD 前至少需要：

1. 取得对当前实测身份字节（0xED=0x80、0xEE=0x94）的正式 register-map/errata 说明。RK809 Rev 2.5 将 0xEE[7:4] 定义为 CHIP_NAME=0x9，将 [3:0] 明确标为 RESV、reset default=0x2；本机读到低 nibble=0x4，不能把 0x94 称为硅片版本号，也不能自行解释该 reserved 值。需由 Rockchip 确认该差异及其与 RK817 24-bit IRQ mapping 的适用关系。不能通过额外读取 0xFC 来代替，因为读取本身可能清状态。
2. 明确 G2-PROBE 是否纳入 `RTC_DRV_RK808`；若纳入，审查并授权 0x0D、0x0E 与 RTC alarm IRQ unmask/ACK 的附加写入；若不纳入，必须另行设计并审查 RTC_STOP 的恢复方法。
3. 完成 probe 中途失败、部分寄存器写入后的处理和安全退出/回退方案。
4. 冻结专用 PMIC-enabled DTB、最终 config、Image、initramfs、boot script、全部哈希和精确写入清单；独立取得 G2-PROBE 操作授权。

在以上事项完成前：
- 不构建 PMIC-enabled 实机镜像；
- 不写 SU08G，不触碰 SN64G/eMMC；
- 不启动 Panther X2，不 probe RK809；
- 不启用 regulator、IO-domain、GMAC/MDIO/PHY；
- ABCD 仍为 NOT EXECUTABLE。

## 9. 源码与数据手册定位

- 6.18.63 `rk8xx-core.c`：`rk817_pre_init_reg[]`、`rk817_irq_chip`、`rk8xx_probe()`、sys-off、shutdown/suspend/resume。
- 6.18.63 `regmap-irq.c`：默认 mask 初始化、`init_ack_masked`、status read/ACK、unmask/sync-unlock。
- 6.18.63 `rtc-rk808.c`：`rk808_rtc_probe()` 的 RTC_CTRL 与 RTC_STATUS 操作。
- RK809 Datasheet Rev 2.4：RTC_CTRL/RTC_STATUS（§5.2，页 57–58）；PMIC_INT_STS1/2、PMIC_INT_MSK1/2、GPIO_INT_CONFIG（页 124–125）。
- RK809 Datasheet Rev 2.5：相同寄存器的后续版本复核（页 125–126），并确认 0xEE 低 nibble 为 RESV、reset default=0x2；[在线副本](https://datasheet.lcsc.com/datasheet/pdf/dc4249f899d1f7640dc738c73aecc6ea.pdf?productCode=C54771187)。
- RK809 Datasheet Rev 1.01：历史上曾将 0xEE[3:0] 定义为 CHIP_VER code 1–15；[在线副本](https://rockchip.fr/RK809%20datasheet%20V1.01.pdf)。Rev 1.7 起改标 RESV，见 R3 专项报告的历史修订对照。
- RK817 Datasheet Rev 2.1：0xFA/0xFC 完整 24 IRQ 定义（页 136–138）；[在线副本](https://atta.szlcsc.com/upload/public/pdf/source/20240126/1D84E9BEA212072F9DD3BF1F36FC3510.pdf)。

本报告仅为静态审计和计划约束，不构成任何设备操作授权。
