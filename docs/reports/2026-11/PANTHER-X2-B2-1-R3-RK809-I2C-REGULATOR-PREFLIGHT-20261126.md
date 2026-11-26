# Panther X2 B2-1 / R3：RK809 / I2C / Regulator 前置审计（2026-11-26）

## 1. 状态与范围

**状态：R3.1 I2C0 controller 与 R3.2 RK809 ID 只读身份读取 PASS-RUNTIME；R3.7 的安全状态寄存器候选 PASS-STATIC，等待单独授权后实读；R3.3 MFD/regmap、R3.4 regulator provider、R3.5 consumer 与 R3.6 PHY supply consumer 仍 HOLD/BLOCKED；R3 整体不放行 R4。**

本轮只读核验：
- 复用既有 6.18.63 Kconfig/Makefile 与 GMAC PHY supply 静态审计；
- 直接解包 R1 最终 Actions artifact，核对最终 `.config`、`modules.builtin`、模块归档和实际编译 DTB；
- 解析 R1 最终 DTB 的 I2C0、RK809、SWITCH_REG1 与 GMAC1 `phy-supply` phandle；
- 从 Dropbox 原始 `kernel-config-evidence.zip` 复核 6.1.65 Golden 的最终配置和 built-in 对象；
- 复核 Linux 6.18.63 RK809 I2C/MFD/regulator 驱动 probe 路径及其副作用。

没有访问 Panther X2，没有启用 RK809 driver，没有发起 I2C/PMIC 事务，没有写 PMIC 寄存器，没有改变 regulator、reset 或电源状态；没有修改 Kconfig、源码、DTB、镜像或系统配置，没有构建或刷写新镜像。

## 2. R1 最终构建身份

R1 artifact：Actions run `45611898629`，job `139197305317`，artifact ID `15023630465`（`b2-1-r1-network-core`）。

- Kernel：Linux 6.18.63
- 源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- `kernel.config` SHA256：`480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`
- Image SHA256：`63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`
- Panther DTB SHA256：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`
- `modules.tar.zst` SHA256：`4f403cac59809616cf4de36a8e89520ecffc13965597be4b8d88845fb3ce3787`

以上 hash 与 R1 artifact 内的验证清单一致。

## 3. R1 最终 .config 与对象核验

从 artifact 内实际 `output/kernel.config` 和 `output/modules.tar.zst` 提取：

| 符号/对象 | R1 最终状态 | 证据 |
|---|---|---|
| `CONFIG_I2C` | y | 最终 .config |
| `CONFIG_I2C_RK3X` | y | 最终 .config；`modules.builtin` 有 `i2c-rk3x.ko` |
| `CONFIG_REGMAP_I2C` | y | 最终 .config；`modules.builtin` 有 `regmap-i2c.ko` |
| `CONFIG_REGULATOR` | y | 最终 .config |
| `CONFIG_MFD_RK8XX_I2C` | not set | 最终 .config 明确为 not set |
| `MFD_RK8XX` core | 未构建 | `modules.builtin` 与模块归档无 `rk8xx-core` |
| `rk8xx-i2c` | 未构建 | `modules.builtin` 与模块归档无对应对象 |
| `REGULATOR_RK808` / `rk808-regulator` | 未构建 | 最终配置无启用项，`modules.builtin` 与模块归档无对应对象 |

**结论：** R1 已内建 RK3566 I2C controller 和 regmap-I2C 通用基础，但没有 RK8xx I2C/MFD parent 与 RK809 regulator driver。R1 尚不能提供完整 RK809 PMIC/regulator provider 链。

## 4. R1 最终 DTB 二进制解析结果

直接解析 artifact 内 `output/dtb/rockchip/rk3566-panther-x2.dtb`，不是仅凭源码 DTS 推断：

1. I2C0 节点：`/i2c@fdd40000`，`status = "okay"`。
2. RK809 节点：`/i2c@fdd40000/pmic@20`，`compatible = "rockchip,rk809"`，`reg = <0x20>`；节点未声明 disabled status。
3. RK809 的 regulator 子节点 `SWITCH_REG1`：`regulator-name = "vcc_3v3"`，phandle `0x19`；未声明 disabled status。
4. GMAC1：`/ethernet@fe010000`，`status = "disabled"`，`phy-supply = <0x19>`。
5. phandle 解析结果：GMAC1 的 `phy-supply` 精确指向 `/i2c@fdd40000/pmic@20/regulators/SWITCH_REG1`，不是名称相似推断。
6. `SWITCH_REG2` 仍为 `status = "disabled"`；MDIO 与 PHY 子节点也保持 disabled。

**结论：** R1 最终 DTB 中 I2C0/RK809/SWITCH_REG1 的拓扑和 phandle 引用正确；GMAC/MDIO/PHY 隔离状态保持不变。该静态证据不证明 I2C0 adapter 已在实机注册、RK809 有响应或 SWITCH_REG1 实际输出电压正常。

## 5. 6.1.65 Golden 对照

来源：Dropbox 原始归档 `/kernel-config-evidence.zip`，其中的 `config-6.1.65-ophub` 与 `modules.builtin`。

| 配置/对象 | 6.1.65 Golden | 6.18.63 R1 | 解释 |
|---|---|---|---|
| `I2C` | y | y | 相同 |
| `I2C_RK3X` | y | y | 相同，RK3x controller 已内建 |
| `REGMAP_I2C` | y | y | 相同 |
| `REGULATOR` | y | y | 相同 |
| `MFD_RK808` | y | 旧符号不再沿用 | 6.18 改为 RK8xx core + I2C transport 分层 |
| `MFD_RK8XX_I2C` | 不适用旧版符号 | not set | 6.18 新 transport driver 尚未启用 |
| `REGULATOR_RK808` | y | 未构建 | 6.18 对应驱动依赖 MFD_RK8XX |
| built-in 对象 | `rk808.ko`、`rk808-regulator.ko`、`i2c-rk3x.ko`、`regmap-i2c.ko` | `i2c-rk3x.ko`、`regmap-i2c.ko`；无 RK8xx MFD/regulator 对象 | Golden 包含完整 PMIC 链，R1 只保留 I2C 通用基础 |

6.1.65 的 Panther X2 有线网络实机成功是该整机组合的正向集成证据；它不等于已经独立执行 RK809 ID、每个 regulator 或实际 rail 电压测试。6.1.65 原始内核的精确源码构建 commit 仍未达到二进制级绑定，因此本报告只比较已归档的真实 config/built-in 证据，不宣称两版源码实现完全相同。

## 6. 6.18.63 精确依赖闭包

固定源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

- `I2C_RK3X`：依赖 `OF && COMMON_CLK`；Makefile 对象 `i2c-rk3x.o`。R1 已满足。
- `MFD_RK8XX_I2C`：依赖 `I2C && OF`，select `MFD_CORE`、`REGMAP_I2C`、`REGMAP_IRQ`、`MFD_RK8XX`；Makefile 对象 `rk8xx-i2c.o`。
- `MFD_RK8XX`：core 对象 `rk8xx-core.o`。
- `REGULATOR_RK808`：depends on `MFD_RK8XX`；Makefile 对象 `rk808-regulator.o`。
- Generic `REGULATOR`、`REGMAP_I2C`、`I2C`、`I2C_RK3X` 已在 R1 为 y。

若后续获准引入完整 provider，静态上最小的显式配置缺口为 `MFD_RK8XX_I2C=y` 与 `REGULATOR_RK808=y`；`MFD_RK8XX`、`MFD_CORE`、`REGMAP_IRQ` 等按 Kconfig select/dependency 闭合。**本轮没有应用这些配置，也没有生成新构建。**

## 7. 关键安全发现：RK809 driver probe 并非只读

源码复核发现，不能把“加载 RK809 driver”当作只读识别：

- `rk8xx_i2c_probe()` 根据 DT compatible 匹配 RK809 variant，初始化 regmap 后调用 `rk8xx_probe()`。
- 对 `RK809_ID`，`rk8xx_probe()` 选择 `rk817_pre_init_reg`。
- probe 随后循环执行 `regmap_update_bits()`，逐项写入该 pre-init 表。
- 该表至少包含 `RK817_RTC_CTRL_REG` 的 `RTC_STOP` 位写入，并包含多项 codec register 写入。

因此，若把 `MFD_RK8XX_I2C` 作为 built-in 加入当前 DTB 并启动，RK809 节点会自动匹配并进入 probe，probe 会对 PMIC 寄存器执行写操作。这与当前“禁止 I2C/PMIC 写入、不得改变电源状态”的安全边界冲突。此处尚无证据表明这些 pre-init 写入会切换 SWITCH_REG1/2 电源轨，但它们确实不是只读操作。

**停止条件：** 在没有单独批准 PMIC probe 副作用之前，不得把 RK809 MFD driver 以 built-in 方式加入 R1 启动镜像，不得启动该 driver，不得运行 regulator 操作或 PMIC 寄存器读取/写入测试。不得为了完成 R3 而弱化现有安全约束。

## 8. R3 分项状态

| 分项 | 当前状态 | 证据/限制 |
|---|---|---|
| R3 静态 DTB 拓扑与 phandle | PASS-STATIC | R1 最终 DTB 二进制已解析 |
| R3 Kconfig/Makefile 依赖 | PASS-STATIC | 6.18.63 精确源码已核对 |
| R3 R1 最终配置/对象 | PASS-STATIC | 真实 R1 artifact 已解包 |
| R3 6.1.65 Golden 配置/对象对照 | PASS-STATIC | Dropbox 原始 config 与 modules.builtin |
| R3.1 I2C0 controller bind | PASS-RUNTIME | 实机 sysfs 显示 DRIVER=rk3x-i2c；启动日志识别 0-001c 的 FAN53555，证明 I2C0 至少一个从设备完成通信；adapter class 枚举本轮未能确认 |
| R3.2 RK809 稳定通信/ID read | PASS-RUNTIME | 专用静态 AArch64 程序经 I2C_RDWR 对 0x20 仅读取 0xED/0xEE；两次 ioctl 均返回 2、errno=0；实测 0x80/0x94，符合 Linux RK809 masked ID 规则 |
| R3.3 MFD/regmap parent/child | BLOCKED | 当前 R1 未构建 driver；probe 先注册 regmap IRQ，再执行 RK817 pre-init 写入；生命周期还有 shutdown/suspend/resume 写入 |
| R3.4 regulator 注册 | BLOCKED | DTS 有多路 always-on/boot-on、initial voltage/mode 约束；regulator core 注册时可能写电压/模式/使能寄存器 |
| R3.5 现有安全 regulator consumer | BLOCKED | 当前没有安全 provider 注册路径；MFD/regulator probe 含 PMIC 写入和可能的 rail 配置副作用 |
| R3.6 GMAC PHY supply consumer | BLOCKED / R7-A | GMAC1 仍 disabled，按原计划留到 R7-A |
| R3.7 PMIC 状态寄存器只读观察 | PASS-STATIC-CANDIDATE / runtime pending | Rev 2.4 确认 0xF0、0xF6 全位 RO；尚未获准实机读取 |

**阶段结论（更新至 2026-11-26 实机只读取证）：** R3 静态审计完成；R3.1 的 I2C0 platform controller 已绑定 rk3x-i2c，并有 FAN53555@0x1c 成功识别的启动日志，证明 I2C0 总线上至少一个非 RK809 从设备完成了实际通信。RK809@0x20 仅确认 DT 创建的 client 节点存在，尚无 RK809 ID/寄存器响应证据。R3.1 controller bind 可记 PASS-RUNTIME；adapter class 目录枚举未得到有效结果（终端缺少 echo 等命令），不单独判定 adapter class 注册状态。RK809 provider/regulator 链仍未验证，R3 整体 HOLD/BLOCKED，不放行 R4。


## 10. R3.1 实机只读取证补充（2026-11-26）

### 10.1 证据来源与结果

在现有 R1 AF_PACKET probe initramfs 中执行只读 sysfs 检查，并查看启动内核日志；没有修改配置、加载模块、发起额外 I2C/PMIC 事务或改变电源状态。

1. `/sys/bus/platform/devices/fdd40000.i2c/uevent` 输出 `OF_FULLNAME=/i2c@fdd40000`、`OF_ALIAS_0=i2c0`，并从其 driver 链接读取到 `DRIVER=rk3x-i2c`。**这直接证明 I2C0 platform controller 已绑定 `rk3x-i2c` 驱动。**
2. `/sys/bus/i2c/devices/0-0020` 存在，uevent 标识 `OF_FULLNAME=/i2c@fdd40000/pmic@20`、`OF_COMPATIBLE_0=rockchip,rk809`，`/name` 为 `rk809`。这证明 DT 创建了 RK809 client 设备节点，不证明芯片应答或 ID 读取成功。
3. 启动日志出现 `fan53555-regulator 0-001c: FAN53555 Option[12] Rev[15] Detected!`。这证明 I2C bus 0 上地址 `0x1c` 的 FAN53555 完成驱动识别和实际通信；它不是 RK809，不能替代 RK809@0x20 的响应证据。
4. 启动日志出现 MMC、SARADC、IO-domain 等多个设备等待 `/i2c@fdd40000/pmic@20/regulators/...` supplier 的 deferred-probe 记录，与 R1 未构建 RK8xx MFD/regulator provider 的静态审计一致。
5. `/sys/class/i2c-adapter/*` 的枚举命令依赖 `echo`，但当前极简 shell 报 `echo: not found`；因此本轮没有取得有效的 adapter class 目录枚举结果。不能把此前通配符未显示内容误判为 adapter class 为空。
6. 当前 shell 也缺少 `command`、`dmesg`、`ls`、`grep`、`readlink` 等工具。通过 `/proc/kmsg` 可读取启动日志；`Ctrl+C` 未能退出目标端读取，最终通过 iMac UART 程序的 `Ctrl+]` 正常关闭本地串口会话。该操作没有重启设备或修改设备配置。

### 10.2 更新后的 R3.1 结论

- **PASS-RUNTIME：** I2C0 platform controller 与 `rk3x-i2c` 驱动成功绑定。
- **PASS-RUNTIME（总线通信旁证）：** FAN53555@0x1c 被识别，证明 I2C0 上至少一个从设备可通信。
- **NOT VERIFIED：** I2C adapter class 目录枚举；RK809@0x20 的芯片应答、ID/寄存器读取。
- **BLOCKED：** RK809 MFD/regmap、regulator provider 和 consumer 功能；不得为了推进这些项目直接启用有 probe 写寄存器副作用的 RK809 MFD。

本轮不执行 `i2cget`、`i2cdetect`、`/dev/i2c-*` 访问、regulator 操作、PMIC 寄存器读写或驱动启用。R3 整体仍为 HOLD/BLOCKED，不放行 R4。


## 11. R3.2–R3.4 精确源码副作用与安全访问路径审计（2026-11-26）

### 11.1 精确源码端点

以下代码均从本项目冻结的 Linux 源码端点直接读取，而非用其他版本猜测：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

- `drivers/mfd/rk8xx-i2c.c`
- `drivers/mfd/rk8xx-core.c`
- `include/linux/mfd/rk808.h`
- `drivers/regulator/rk808-regulator.c`
- `drivers/regulator/core.c`
- `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`

### 11.2 Linux 6.18.63 的 RK809 匹配并不读取芯片 ID

精确源码中 `rk809_data` 将 `variant = RK809_ID`、`regmap_cfg = &rk817_regmap_config`。`rk8xx_i2c_probe()` 的实际顺序是：

1. `device_get_match_data()` 根据 OF compatible 取得 RK809 静态 platform data；
2. `devm_regmap_init_i2c()` 建立 I2C regmap；
3. 直接调用 `rk8xx_probe(..., data->variant, client->irq, regmap)`。

该 probe 路径没有先读取 RK809 silicon ID。头文件定义 `RK817_ID_MSB=0xed`、`RK817_ID_LSB=0xee`，但这两个寄存器没有在该 I2C probe 路径中被读取。因此，即使未来 MFD probe 成功，也只能证明 compatible 匹配和后续访问可运行，不能把它误称为已独立读取并核验芯片 ID。

### 11.3 当前 Panther DTB 满足了 IRQ 描述条件，不能依赖“无 IRQ”绕过写入

冻结源码 DTS 的 RK809 节点含：
- `interrupt-parent = <&gpio0>`；
- `interrupts = <RK_PA3 IRQ_TYPE_LEVEL_LOW>`；
- `pinctrl-0 = <&pmic_int_l>`；
- `system-power-controller`。

`rk8xx_probe()` 确实在 `if (!irq) return -EINVAL` 后才继续；但 DT 已描述 GPIO0 PA3 中断。当前尚未实测该 IRQ 是否成功映射，因此不能声称 probe 一定通过 IRQ 阶段；同样也不能把它当作可安全阻断 probe 的可靠保护。若 IRQ 成功，源码会先调用 `devm_regmap_add_irq_chip()`，然后进入 pre-init register loop。

### 11.4 MFD probe 与生命周期存在多处 PMIC 写操作

RK809 与 RK817 共用 `rk817_pre_init_reg`。`rk8xx_probe()` 在 regmap IRQ chip 注册后，对 pre-init 表逐项执行 `regmap_update_bits()`。表中包括 `RK817_RTC_CTRL_REG` 的 `RTC_STOP` 位，以及多项 codec register 的整字/掩码写入。

此外，RK809 DTB 设置 `system-power-controller`，core 会注册 power-off handler 和 restart handler：
- power-off handler 对 `RK817_SYS_CFG(3)` 的 `DEV_OFF` 位执行 `regmap_update_bits()`；
- restart handler对同一配置寄存器的 `DEV_RST` 位执行写入；
- `rk8xx_shutdown()` 对 `RK817_SYS_CFG(3)` 的 sleep-pin function 写入 `SLPPIN_DN_FUN`；
- suspend/resume 分别写入 `SLPPIN_SLP_FUN` / `SLPPIN_NULL_FUN`。

因此，即使尝试仅绕过 pre-init 表，驱动仍会在系统关机、重启、挂起/恢复路径写 PMIC。当前不能将 MFD parent 视为只读探针。

### 11.5 Regulator provider 注册本身也不是被动枚举

`rk808-regulator.c` 对 RK809 选择 `rk809_reg[]` 并逐项调用 `devm_regulator_register()`。Panther DTS 中多个 regulator 明确标记 `regulator-always-on`、`regulator-boot-on`，DCDC_REG1/2/4 还包含 `regulator-init-microvolt`、`regulator-initial-mode` 和 ramp-delay 等约束。

冻结的 `drivers/regulator/core.c` 在 `set_machine_constraints()` 中会按这些约束调用 voltage/current、initial state/mode、ramp 等操作；对于 `always_on` 或 `boot_on`，还可能执行 regulator enable。RK809 regulator ops 最终通过 regmap 读写 PMIC 寄存器。因此，regulator provider probe 可能主动调整多个电源轨，不只是注册名称；即使目标 SWITCH_REG1 自身没有 `always-on`/`boot-on`，也不能把整个 regulator probe 当作无副作用测试。

### 11.6 可以安全继续的验证与当前限制

- **已完成静态验证：** 精确 6.18.63 RK809 OF match、regmap transport、IRQ 前置条件、pre-init 写入、sys-off/suspend/resume 写入、regulator 注册/约束应用路径；冻结 DTS 的 RK809 IRQ 与 `system-power-controller` 属性。
- **可考虑的独立芯片 ID 验证：** 0xed/0xee 是头文件定义的 ID 寄存器地址，但仅凭寄存器命名不足以证明读取无副作用。需要进一步核对对应芯片 datasheet 的访问语义；之后才可决定是否采用隔离的只读 I2C_RDWR 诊断程序。当前 R1 极简 initramfs 没有 `i2cget`/`i2ctransfer` 等工具；本轮没有构建/注入诊断程序，也没有执行 `/dev/i2c-*` ioctl 或 PMIC 事务。
- **adapter class 目录枚举：** 前一轮失败仅因极简 shell 的 `echo`/`command` 等工具不可用；`printf` 已证实可用，可在不访问 PMIC 的前提下用 shell builtin 完成最后一次只读枚举。

**安全结论：** 当前能不触及 PMIC 的源码/DTB/Kconfig/构建产物审计已完成。RK809 ID 读取与 MFD/regulator 实机验证不属于现有镜像可直接完成的无副作用测试；不通过启用驱动或访问 PMIC 来强行结项。


## 12. RK809 芯片 ID 只读寄存器与最小诊断路径（2026-11-26）

### 12.1 Datasheet 证据

Rockchip RK809 Datasheet Rev 2.4（2024-01）寄存器章节明确：

- `PMIC_CHIP_NAME`，地址 `0xED`，属性 `RO`，默认值 `0x80`；
- `PMIC_CHIP_VER`，地址 `0xEE`，属性 `RO`，默认值 `0x92`，其中芯片名低四位为 `0x9`，版本 nibble 为 `0x2`。

这与 Linux 6.18.63 `include/linux/mfd/rk808.h` 中 `RK817_ID_MSB=0xed`、`RK817_ID_LSB=0xee` 一致；Linux 定义 `RK809_ID=0x8090`，按 ID mask 忽略低版本 nibble。因此两个寄存器可作为独立硬件身份只读核验点。Datasheet 证据：`https://rockchip.fr/RK809%20datasheet%20V2.4.pdf`，第 117 页（寄存器地址及 RO 属性）。

### 12.2 最小安全访问方案

- 仅对 7-bit I2C address `0x20` 读取寄存器 `0xED`、`0xEE`；不扫描总线，不读状态/中断寄存器，不写任何 PMIC 数据寄存器。
- 使用单字节寄存器索引 + repeated-start 单字节读（或两条独立 SMBus BYTE_DATA read）；寄存器索引字节只是选择读地址，不是写入 PMIC 寄存器数据。
- 预期：`0xED = 0x80`；`0xEE` 高 nibble 为 `0x9`（Rev 2.4 默认完整值 `0x92`）；Linux masked ID 应归类为 `0x8090`。
- 6.18.63 RK3x I2C adapter 源码明确声明 `I2C_FUNC_I2C | I2C_FUNC_SMBUS_EMUL | I2C_FUNC_PROTOCOL_MANGLING`，支持该只读 combined transfer。
- 6.18.63 `i2c-dev.c` 的 `I2C_RDWR` 路径允许对未绑定 driver 的 DT client 传输；其地址检查注释明确说明“已注册但未绑定 driver”的地址不视为 busy。当前 RK809 client 节点无 driver 绑定，故该机制在源码层面可行。

### 12.3 当前轮可执行边界

该安全只读路径已经由 Datasheet RO 属性、Linux register definitions、RK3x adapter functionality 和 i2c-dev transfer 逻辑共同支持。**尚未在 Panther 实机执行 ID read**：现有极简 shell 没有 `i2cget`/`i2ctransfer`，当前也没有已经构建、验证并送入 RAM 的专用 ioctl 测试程序；不得用 `echo`/`cat` 伪造 ioctl，也不得用 `i2cdetect` 扫描代替精确读取。

下一步优先检查现有 JP-TvBox U-Boot 是否包含 `i2c` 只读命令，或另行构建一个仅读 `0xED`/`0xEE` 的静态 ARM64 小程序。若采用内核态 `i2c-dev`，只执行上述两个 RO 字节读取；不得加载 RK8xx MFD/regulator 驱动。ID 读取通过后，仍只证明芯片身份/总线响应，不代表 MFD/regulator provider 通过。

## 9. 复用与新增证据

### 复用既有证据
- `PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md`：RK809 PHY supply provider 的 6.18.63 Kconfig/Makefile 链。
- `PANTHER-X2-GMAC-GLUE-CLOCK-POWER-SUPPLEMENTAL-AUDIT-20261124.md`：Panther `phy-supply` 指向 RK809 SWITCH_REG1；不把静态引用当作实测供电。
- `PANTHER-X2-B2-1-R2-SHARED-SOC-PROVIDER-AUDIT-20261126.md`：R2 PASS 与现有 R1 镜像只读 provider 证据。
- Dropbox `/kernel-config-evidence.zip`：6.1.65 Golden 原始配置与 built-in 清单。

### 本轮新增
- 直接解包 R1 artifact 15023630465，提取最终 .config、modules.builtin 和 DTB。
- R3.1 实机只读取证：I2C0 platform controller 绑定 `rk3x-i2c`；FAN53555@0x1c 识别成功；RK809 client 节点存在但未证明芯片响应；记录极简 shell 工具缺失造成的 adapter class 枚举限制。
- 对 R1 最终 DTB 二进制解析 I2C0/RK809/SWITCH_REG1/GMAC1 phandle。
- 对照 6.1.65 Golden 的 RK809 相关 config 与 built-in 对象。
- 发现 6.18.63 RK809 MFD probe 会执行 `regmap_update_bits()`，确认它不能按只读步骤直接启用。
- 精确复核冻结源码的 RK809 variant 匹配路径不读取 silicon ID；核实 Panther DTS 提供 GPIO0 PA3 IRQ 与 `system-power-controller`；补充 MFD 生命周期写操作及 regulator core 对 boot-on/always-on/初始电压/模式约束的潜在写入风险。
- 复核 Rockchip RK809 Datasheet Rev 2.4：0xED/0xEE 均为 RO 芯片身份寄存器；确认 RK3x adapter 支持 I2C combined transfer，i2c-dev 对未绑定 driver 的 DT client 可进行 I2C_RDWR。形成最小只读 ID 核验方案，尚未实机执行。



## 13. R3.5 I2C-dev runtime enumeration and isolated probe preparation (2026-11-26)

### 13.1 Runtime evidence from R1 AF_PACKET initramfs

The following were read from the running R1 environment without PMIC register transactions:

- `/sys/bus/i2c/devices/i2c-0/name` returns `rk3x-i2c`.
- `/sys/bus/i2c/devices/i2c-0/uevent` identifies `/i2c@fdd40000`, compatible with `rockchip,rk3568-i2c` and `rockchip,rk3399-i2c`, alias `i2c0`.
- `/proc/devices` lists character major `89 i2c`.
- `/sys/class/i2c-dev/i2c-0/dev` returns `89:0`; its uevent reports `MAJOR=89`, `MINOR=0`, `DEVNAME=i2c-0`.
- `/sys/dev/char/89:0/uevent` independently reports the same device identity.
- `/sys/bus/i2c/devices/0-0020` exists with OF compatible `rockchip,rk809`, but this is an OF-created client object and is not proof of silicon ACK or ID.
- `/dev/i2c-*` does not match any node. `/proc/mounts` lists rootfs, proc and sysfs only; devtmpfs is not mounted.
- The shell lacks `mknod`; the attempted command returned `mknod: not found` and created no device node.

**Conclusion:** the I2C adapter and i2c-dev character-device registration are present in kernel/sysfs. The missing `/dev/i2c-0` is a userspace device-node provisioning limitation in this minimal initramfs, not evidence that the kernel lacks i2c-dev. No mount, device-node creation, I2C ioctl, or PMIC transaction has yet been performed.

### 13.2 Dedicated read-only probe source and build workflow

Added an independent source file:

- `scripts/panther-x2-b2-1/rk809-id-ro-probe.c`

Added a build-only GitHub Actions workflow:

- `.github/workflows/build-panther-x2-b2-1-r3-rk809-id-probe.yml`

The program is hard-coded to adapter character device `89:0`, 7-bit address `0x20`, and only registers `0xED` and `0xEE`. If the node is absent, it attempts to create `/dev/i2c-0` as a temporary character device with mode 0600 in the current rootfs. It verifies an existing node's type and major/minor before opening it. It then checks `I2C_FUNC_I2C` and issues two `I2C_RDWR` combined transfers, each consisting of one register-index message and one one-byte read message.

The program does not scan the bus, does not bind or load RK8xx drivers, does not call regulator APIs, and does not send PMIC register data writes. The register-index byte is the address phase of each read transfer. It prints ioctl return values, errno, and returned bytes. A failed read is reported as a failure rather than being treated as a device absence conclusion.

The workflow builds a static AArch64 ELF with a dedicated cross-toolchain, checks the ELF architecture and absence of a dynamic interpreter, runs the program's non-hardware `--self-test` under QEMU, and publishes the binary, source, SHA256 and build metadata as a 30-day artifact. It does not package or alter the R1 image.

Relevant commits:
- Probe source initial commit: `2b10201c1883dbe7e7d3cf71f476a8c0332e278a`
- Include correction: `21e7739f1ef1688edc4f47827f2387b31570381c`
- Workflow initial commit: `be75edb047752e8eeba5c25f9bd1ea441da80cd7`
- Workflow push trigger: `4eca623af657c01e27151c5c71d60aeeeb840815`

**Build status:** not yet independently confirmed from a completed Actions run or retrieved artifact in this audit. Source committed does not equal successful cross-compilation. Hardware execution and RK809 ID values remain NOT VERIFIED.

### 13.3 Updated R3.5 status

- **PASS-RUNTIME:** I2C0 adapter registered and bound to `rk3x-i2c`.
- **PASS-RUNTIME:** i2c-dev character-device major/minor registered and exposed in sysfs as `89:0`.
- **PASS-RUNTIME (bus communication corroboration):** FAN53555@0x1c was previously identified by its driver; this does not prove RK809@0x20 responds.
- **NOT VERIFIED:** static AArch64 probe build artifact and self-test.
- **NOT VERIFIED:** RK809@0x20 ACK and values at `0xED`/`0xEE`.
- **BLOCKED:** RK809 MFD/regmap and regulator-provider functional validation; no driver enablement is authorized.

R3 remains HOLD/BLOCKED. Do not proceed to R4 on the basis of adapter registration, source submission, or a successful userspace self-test alone.


### 13.4 Identity comparison correction

The probe source was refined after reviewing the Linux RK809 masked ID definition. It now reports two distinct comparisons:
- exact datasheet default byte match (`0xED=0x80`, `0xEE=0x92`);
- Linux RK809 identity match (`0xED=0x80` and high nibble of `0xEE` equals `0x9`), consistent with the kernel's masked silicon ID semantics.

This avoids treating the datasheet's default revision byte as the only acceptable identity result. Source update commit: `df6fca415f34e310d97ea15b62f4270be0beeff7`.

The source change also triggers the existing build workflow via its configured push path filter. No completed Actions run or downloadable artifact has been retrieved in this session, so build and QEMU self-test remain unverified.


### 13.5 Build run 45764956914 verified (2026-11-26)

GitHub Actions run `45764956914` completed with conclusion `success`, run attempt 1, on source commit `df6fca415f34e310d97ea15b62f4270be0beeff7`. Job `build-rk809-id-probe` (job ID `139723544670`) completed successfully; all five substantive steps passed: checkout, isolated AArch64 toolchain install, static probe build, and artifact publication (including setup).

Evidence from job log:
- Compiler: `aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2`.
- ELF: 64-bit LSB executable, ARM aarch64, statically linked; program-header check found no `PT_INTERP`.
- QEMU non-hardware self-test output includes `architecture=aarch64`, `scope=RK809_ID_REGISTERS_ONLY`, `self_test=PASS`.
- Binary size: 635,064 bytes.
- Artifact: `panther-x2-r3-rk809-id-ro-probe-static-aarch64`, artifact ID `15090758525`, ZIP size 294,327 bytes, expiry 2026-12-26.
- Artifact ZIP digest: `sha256:0a9fe5c7c59b8e07f830453f9ff47ef95dbbbbb25f4735c577161642f1601fe3`.
- Independently downloaded and inspected artifact ZIP. Binary SHA256: `4b8ff213c41250e992cf71a1f0579502d68633ae9e4de48d0a77f6b37bfa7b99`.
- Source copied into artifact SHA256: `7e575795e37494f52f0985fdcf0e3993a95c866f71489d0780907bfc63069480`.
- Local archive inspection confirmed 8 files and the same 635,064-byte AArch64 static ELF. This verifies artifact integrity and format independently of the CI log.

**Interpretation:** static AArch64 build and QEMU non-hardware self-test are PASS. This does not test actual I2C hardware, device-node creation permissions, RK809 ACK, or PMIC register values.

### 13.6 Hardware execution (superseded by Section 14)

At the time this subsection was written, hardware execution was pending. The dedicated binary was subsequently packaged into a separate RAM-only initramfs and run on Panther X2; see Section 14 for the actual runtime evidence. The previous pending status is no longer current.

A successful ID read does not authorize loading RK8xx MFD/regulator drivers or advancing to power-provider functional testing.


## 14. R3.2 RK809 实机身份寄存器只读验证（2026-11-26）

### 14.1 专用 initramfs 构建与部署

- 使用独立 GitHub Actions workflow 构建专用 initramfs；复用已冻结的 R1 Image/config/DTB、B1 BusyBox 与已验证的 RK809 probe artifact，没有重新编译内核。
- 成功构建 run：`45793983845`；job：`139819812243`；artifact ID：`15103942731`。
- Artifact：`panther-x2-r1-rk809-id-probe-initramfs-only`。
- uInitrd 大小：775382 bytes；SHA256：`29114171087f60dd281245f41c49de24fede51b2e3216603caaf0f5908d70a30`。
- 在 iMac 下载后、9.2 临时传输文件、SU08G 写入前后均核对相同 SHA256。
- SU08G 原始 uInitrd 备份：`uInitrd.original-20261126`，778739 bytes，SHA256：`fea239c50598ede90dfd6e18e7a916de454525b1e7c357baff9d85107ae50aeb`。
- 仅替换 SU08G 的 `uInitrd`；`Image`、`boot.scr`、`boot.cmd` 与 DTB 未修改。SN64G 与 eMMC 未触碰。
- 新 initramfs 实机启动成功；`/proc/mounts` 仅有 rootfs、proc、sysfs，无持久化存储挂载。探测程序位于 `/bin/rk809-id-ro-probe-aarch64`，不是 `/usr/bin`。其 `--self-test` 输出 `architecture=aarch64`、`self_test=PASS`；该自检不访问 I2C。

### 14.2 实际 I2C 只读事务结果

用户明确授权后，以 root 执行一次：

```sh
/bin/rk809-id-ro-probe-aarch64
```

程序输出的关键证据：

| 字段 | 实测值 |
|---|---|
| adapter | `/dev/i2c-0` |
| adapter_dev | `89:0` |
| node_action | `CREATED_TEMPORARY_CHAR_DEVICE_89_0` |
| adapter_open | `PASS` |
| i2c_funcs | `0xeff000d` |
| i2c_func_i2c | `SUPPORTED` |
| target_address | `0x20` |
| target_registers | `0xED,0xEE` |
| read_reg_0xED_ioctl_rc / errno / value | `2 / 0 / 0x80` |
| read_reg_0xEE_ioctl_rc / errno / value | `2 / 0 / 0x94` |
| rk809_name_read / version_read | `PASS / PASS` |
| rk809_id_raw | `0x8094` |
| datasheet_default_exact_match | `NO` |
| identity_matches_linux_rk809_id | `YES` |

### 14.3 解释与证据边界

1. 两个 `I2C_RDWR` combined transfer 均完整返回 2 条消息，errno 均为 0；说明 I2C0 对目标地址及两个指定寄存器的读取事务成功。
2. `0xED=0x80`，`0xEE=0x94`。原始值 `0x8094` 满足 Linux RK809 masked ID 判定：MSB 为 `0x80` 且版本寄存器高 nibble 为 `0x9`。
3. 数据手册 Rev 2.4 列出的版本寄存器默认完整值为 `0x92`；实测 `0x94`，所以 exact-default-match 为 NO。不能把实测值改写为默认值，也不能将这个 NO 误判为身份失败；当前证据支持 RK809 身份匹配，低 nibble 记录为实测版本字段 `4`，不在缺少更具体 silicon revision 文档时推断其市场版本/批次含义。
4. 该程序只执行对 `0xED`、`0xEE` 的两次寄存器索引+repeated-start 单字节读取；未扫描 I2C 总线、未写 PMIC 数据寄存器、未绑定/加载 RK8xx MFD、未调用 regulator API、未改变电源状态。
5. `/dev/i2c-0` 在不存在时创建为临时字符设备 89:0，位于 RAM rootfs；新 initramfs 未挂载 TF/eMMC，节点随 RAM 环境结束而消失。
6. 该结果证明 I2C0 与地址 `0x20` 的设备能完成指定身份寄存器读取，并支持 RK809 silicon identity；**不证明** RK8xx MFD probe 安全、regmap IRQ 正常、regulator provider 注册、各 rail 电压/时序正常、consumer 功能正常或 GMAC PHY supply 可用。

### 14.4 更新后的 R3 状态

- **PASS-STATIC：** Kconfig/Makefile、R1 config/objects、DTB topology/phandle、6.1.65 Golden 对照与精确源码副作用审计。
- **PASS-RUNTIME：** I2C0 controller bind、i2c-dev adapter 注册、RK809@0x20 的 `0xED/0xEE` 只读读取，以及符合 Linux masked ID 规则的 `0x8094`。
- **HOLD/BLOCKED：** RK8xx MFD/regmap parent、regulator provider、regulator consumers、GMAC PHY supply consumer 与其他 PMIC 状态观察。
- **安全决定不变：** 不启用 `MFD_RK8XX_I2C` / `REGULATOR_RK808`，不进入 R4；后续若要研究 provider 必须先单独评估并明确授权 probe、shutdown、restart、suspend/resume 和 regulator constraint 的写寄存器副作用。

**最终结论：R3.2 RK809 硬件身份只读验证 PASS；R3 整体仍 HOLD/BLOCKED，不放行 R4。**


## 15. R3.7 PMIC 状态寄存器只读候选审计（2026-11-26）

### 15.1 Datasheet Rev 2.4 精确寄存器语义

复核 Rockchip RK809 Datasheet Rev 2.4（2024-01-02）第 117–121 页的寄存器定义：

| 寄存器 | 地址 | 位属性 | 含义 | 只读候选结论 |
|---|---:|---|---|---|
| `PMIC_SYS_STS` | `0xF0` | bit 7:0 全部 RO | PWRON 状态、USB 插入、VCC9 UV/LO/OV、过热告警、热关断状态 | 可作为只读状态观察候选 |
| `PMIC_OFF_SOURCE` | `0xF6` | bit 7:0 全部 RO | SLEEP、VCC9 OV/TSD/UV、DEV_OFF、长按 PWRON、VCC9 LO 等关机来源记录 | 可作为只读关机原因观察候选 |

来源：Rockchip RK809 Datasheet Rev 2.4，寄存器描述第 117–121 页，PDF：
`https://armboard.cn/download/Rockchip_RK809_Datasheet_V2.4-20240102.pdf`。

### 15.2 明确排除的寄存器

- `0xF5 PMIC_ON_SOURCE`：不是全位 RO；bit 1 `RESTART_DEV_RST` 标为 RW。此次最小只读状态方案不读取该寄存器。
- `0xF8 PMIC_INT_STS0`：包含 W1C（write-one-to-clear）位；不纳入只读候选，避免把中断状态/清除语义混入当前验证。
- `0xF1`、`0xF3`、`0xF4` 等配置寄存器含 RW 控制位，明确不访问。

### 15.3 证据解释边界

1. `0xF0` 可提供 PMIC 的 VCC9 欠压/过压、温度告警及按键/插入状态；它不是每一路 regulator 的输出电压遥测。
2. `0xF6` 是关机来源记录；数据手册说明相关标志在 power down 或 RST 后复位/装载。它可辅助解释既往关机原因，不等于当前 rail 正常。
3. 两个寄存器的所有位均定义为 RO，适合作为下一项精确 I2C 只读事务候选；但 datasheet 属性仅支持寄存器访问语义，不证明 SWITCH_REG1 的输出电压、纹波、负载能力或 PHY 端供电。
4. 本次仅完成文档/数据手册静态审计，没有对 Panther X2 发起任何新 I2C 事务。此前用户对 `0xED/0xEE` 的授权不自动扩展到 `0xF0/0xF6`。
5. 如获单独授权，下一次探测严格限制为 I2C0、地址 `0x20`、寄存器 `0xF0` 与 `0xF6` 两次单字节 combined read；不扫描总线、不读 `0xF5`/`0xF8` 或其他寄存器、不写 PMIC 数据、不绑定驱动、不调用 regulator API。

### 15.4 当前 R3 安全放行判断

- **PASS-RUNTIME：** R3.1 I2C0 controller/adapter；R3.2 RK809 ID `0x8094` 只读身份验证。
- **PASS-STATIC-CANDIDATE：** R3.7 `PMIC_SYS_STS(0xF0)` 与 `PMIC_OFF_SOURCE(0xF6)` 全位 RO 的语义已由 Rev 2.4 数据手册核实；硬件读取尚待单独授权。
- **BLOCKED：** R3.3 MFD/regmap parent、R3.4 regulator provider、R3.5 现有 regulator consumer、R3.6 PHY supply consumer。当前 6.18.63 MFD probe 和 regulator registration 并非只读，且 R3.6 依赖 R7-A GMAC probe，不能在 R3 提前执行。
- **阶段决定：** 不为取得 MFD/regulator 注册证据而启用当前驱动，不重建/刷写内核镜像，不恢复 GMAC/MDIO/PHY。R3 整体继续 HOLD/BLOCKED，不放行 R4。
