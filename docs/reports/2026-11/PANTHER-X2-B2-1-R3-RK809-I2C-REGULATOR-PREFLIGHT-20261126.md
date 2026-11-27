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
2. `0xED=0x80`，`0xEE=0x94`。原始值 `0x8094` 满足 Linux RK809 masked ID 判定：MSB 为 `0x80` 且 `PMIC_CHIP_VER` 高 nibble CHIP_NAME code 为 `0x9`；低 nibble `0x4` 是手册定义的 RESV，不是版本号。
3. Datasheet Rev 2.4/2.5 的 `PMIC_CHIP_VER` 默认完整字节为 `0x92`；实测 `0x94`，所以 exact-default-match 为 NO。不能把实测值改写为默认值，也不能将这个 NO 误判为身份失败；当前证据支持 RK809 CHIP_NAME 匹配。低 nibble `4` 是 reserved 非默认值，不是 silicon revision；其含义待 Rockchip 说明。
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
- **PASS-BUILD / PASS-INITRAMFS：** R3.7 固定范围只读探测程序及手动执行的 RAM-only initramfs 已通过独立构建、静态 ELF、QEMU self-test 和 initramfs round-trip 验证；实际硬件读取仍待执行。
- **BLOCKED：** R3.3 MFD/regmap parent、R3.4 regulator provider、R3.5 现有 regulator consumer、R3.6 PHY supply consumer。当前 6.18.63 MFD probe 和 regulator registration 并非只读，且 R3.6 依赖 R7-A GMAC probe，不能在 R3 提前执行。
- **阶段决定：** 不为取得 MFD/regulator 注册证据而启用当前驱动，不重建/刷写内核镜像，不恢复 GMAC/MDIO/PHY。R3 整体继续 HOLD/BLOCKED，不放行 R4。


### 15.5 R3.7 专用探测程序与 RAM-only initramfs 构建验证（2026-11-26）

用户已明确授权的硬件访问范围为 I2C0、RK809 地址 `0x20`，仅读取 `0xF0` 和 `0xF6` 各一次。为保持最小范围，新增独立探测程序，不复用可读取其他寄存器的 R3.2 命令行接口。

- 源码：`scripts/panther-x2-b2-1/rk809-status-ro-probe.c`。
- init 脚本：`scripts/panther-x2-r1/init-rk809-status-probe`。
- workflow：`.github/workflows/build-panther-x2-r1-rk809-status-probe-initramfs.yml`。
- 源码/脚本/workflow 提交分别记录于 GitHub 历史；本节以成功 Actions run 与产物哈希作为构建证据。
- 成功 Actions run：[`45800613904`](https://github.com/njosd/panther-x2-armbian/actions/runs/45800613904)，job `139842557060)，所有步骤成功。
- 复用冻结输入：R1 run `45611898629` 的 Image/config/DTB；B1 run `45328201244` 的 BusyBox。工作流逐项验证 Image、config、DTB 与 BusyBox SHA256，没有重新编译内核。
- Artifact：`panther-x2-r1-rk809-r3-7-status-probe-initramfs-only`，ID `15106894148`。
- `uInitrd`：775261 bytes；SHA256 `39443dc6626ad40042a4144089afd7a6b2e9c543645deff48a854dbc55b1e663`。
- initramfs cpio.gz：775197 bytes；SHA256 `c4486cc96809447cdbe4982cdcb9cf6c5772e3d63e6a5518d07d23c5450cdb18`。
- 静态 AArch64 ELF：635072 bytes；SHA256 `bb9a52938bed32a4a812f0943e386071d205a0411c92971ea2d6c84dfa03822a`；无 `PT_INTERP`。
- QEMU 非硬件 self-test：`scope=RK809_STATUS_REGISTERS_0xF0_0xF6_ONLY`、`self_test=PASS`。
- 独立下载 artifact ZIP 后检查文件清单、ELF 类型、验证摘要与哈希；构建报告为 `result=PASS`。
- initramfs 仅含 RAM rootfs 所需目录、冻结 B1 BusyBox、探测程序与手动 shell；round-trip 解包比较通过。探测程序不在 init 中自动调用；无持久存储挂载；Image/config/DTB/U-Boot bootargs 未改变；未添加 RK8xx MFD/regulator 驱动。
- 本次构建没有访问 Panther 设备或任何物理存储。尚未替换 SU08G 的当前 R3.2 `uInitrd`，尚未进行 `0xF0/0xF6` 硬件读取。

**结论：R3.7 PASS-STATIC + PASS-BUILD + PASS-INITRAMFS；硬件读取仍 PENDING。** 只有完成 SU08G 专用 initramfs 启动并由用户手动执行 `/bin/rk809-status-ro-probe-aarch64` 后，才能给出 PASS-RUNTIME。R3.3–R3.5 仍 BLOCKED，R3.6 仍延后至 R7-A；R3 整体 HOLD/BLOCKED，不放行 R4。



## 16. R3.7 Panther X2 实机状态寄存器只读验证（2026-11-26）

### 16.1 SU08G 专用 initramfs 部署核验

用户在 9.2 临时传输主机上执行了受保护的替换流程，全部前置条件与哈希校验通过：

- 目标分区 UUID：`f77bac70-e4b3-4fec-9315-08f97ac210ec`，挂载点 `/mnt/mmcblk1p1`，确认是 SU08G 测试 TF。
- 替换前当前 R3.2 `uInitrd` SHA256：`29114171087f60dd281245f41c49de24fede51b2e3216603caaf0f5908d70a30`。
- 备份：`uInitrd.r3-2-before-r3-7-20261126`，SHA256 与替换前文件完全一致。
- 新 R3.7 `uInitrd` SHA256：`39443dc6626ad40042a4144089afd7a6b2e9c543645deff48a854dbc55b1e663`，替换后再次核验一致。
- 操作仅覆盖 SU08G 的 `uInitrd`；旧的 `uInitrd.original-20261126` 备份保留。SN64G 与 eMMC 未涉及。

### 16.2 运行时自检与硬件读取结果

新 initramfs 启动后，用户先执行：

```sh
/bin/rk809-status-ro-probe-aarch64 --self-test
```

输出：`architecture=aarch64`、`scope=RK809_STATUS_REGISTERS_0xF0_0xF6_ONLY`、`self_test=PASS`。

随后执行实际硬件读取。关键输出：

| 字段 | 实测结果 |
|---|---|
| adapter / device | `/dev/i2c-0` / `89:0` |
| target address | `0x20` |
| registers | `0xF0`、`0xF6` |
| transfer | 每个寄存器一次 I2C_RDWR 两消息 repeated-start |
| `0xF0` | `PMIC_SYS_STS`，RO，ioctl rc=2，errno=0，value=`0xC2` |
| `0xF6` | `PMIC_OFF_SOURCE`，RO，ioctl rc=2，errno=0，value=`0x00` |
| read results | `pmic_sys_sts_read=PASS`；`pmic_off_source_read=PASS` |
| node action | `CREATED_TEMPORARY_CHAR_DEVICE_89_0` |

### 16.3 安全边界与解释

- 探针报告 `write_policy=NO_PMIC_DATA_REGISTER_WRITES`、`bus_scan=DISABLED`、`driver_binding=DISABLED`、`regulator_api=NOT_USED`；实际输出与预定访问范围一致。
- `/dev/i2c-0` 是在 RAM 根文件系统中临时创建的字符设备节点；本次没有启用 RK8xx MFD/regulator 驱动。
- `0xF0=0xC2`、`0xF6=0x00` 作为原始字节记录，不在缺少逐位状态与现场条件关联分析时推断具体电源状态或关机原因。
- 两个寄存器全位 RO 的语义来自 RK809 Datasheet Rev 2.4；本次读取证明 I2C0 对这两个指定寄存器的只读事务成功。
- 这些值不是各路 regulator 输出电压遥测；不证明 SWITCH_REG1/`vcc_3v3` 的实际电压、纹波、负载能力、时序或 GMAC PHY 端供电能力。

### 16.4 更新后的分项状态

- **R3.7 PASS-RUNTIME：** `0xF0` 与 `0xF6` 各一次只读事务成功；原始值分别为 `0xC2`、`0x00`。
- **R3.1/R3.2 PASS-RUNTIME：** 维持此前 I2C0 controller/adapter 与 RK809 ID `0x8094` 只读身份验证结论。
- **R3.3–R3.5 BLOCKED：** MFD/regmap、regulator provider 与 consumer 仍受 probe/注册写寄存器副作用约束；本次没有启用它们。
- **R3.6 BLOCKED / R7-A：** GMAC PHY supply consumer 仍按原计划延后至 R7-A。
- **R3 整体 HOLD/BLOCKED：** 本次只读状态寄存器成功不构成 provider/rail/consumer 功能验收，不放行 R4。

**本次实机验证没有改变既定安全边界：不启用 RK8xx MFD/regulator，不写 PMIC，不操作 regulator，不恢复 GMAC/MDIO/PHY。**


## 17. R3.5 现有 RK809 regulator consumer 安全路径审计（2026-11-26）

### 17.1 复用证据与本轮目标

复用本报告 §4 的 R1 最终 DTB 二进制解析、§7/§11 的 RK809 MFD 与 regulator probe 副作用分析，以及 B2-0 已归档的 Panther 电源/IO-domain 拓扑审计。本轮不重复解析 DTB 或重做四版本源码比较，只确认 R3.5 是否存在不改变 PMIC/SoC 电源域状态的现有 consumer 验证路径。

### 17.2 已识别的现有 consumer 拓扑

冻结源码端点：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

Panther DTS 的 RK809 regulator consumer 引用包括：

- GMAC1 `phy-supply = <&vcc_3v3>`，指向 RK809 SWITCH_REG1；GMAC1 在 R1 最终 DTB 中 disabled，不能作为 R3 当前的现有运行 consumer。
- `pmu_io_domains` 引用 `vcc3v3_pmu`、`vcc_3v3`、`vcc_1v8`、`vccio_sd` 等 RK809 rails；该节点在板级 DTS 中启用，是候选现有 consumer。
- eMMC `sdhci` 使用 `vcc_3v3` 与 `vcc_1v8`；TF `sdmmc0` 使用 `vccio_sd`；GPU 使用 `vdd_gpu`。这些是其他潜在 consumer 路径，但不能仅凭 DTS 引用推断其 R1 运行时已 probe 或成功取得 regulator。
- CPU `vdd_cpu` 来自 I2C0 上独立的 TCS4525，不属于 RK809 regulator consumer；BT/Wi-Fi 路径按项目边界排除。

### 17.3 PMU IO-domain consumer 的精确源码行为

读取冻结 6.18.63 源码 `drivers/soc/rockchip/io-domain.c`：

1. `rockchip_iodomain_probe()` 首先获取 GRF regmap。
2. 对 RK3568 PMU IO-domain 的每个已定义 supply name，调用 `devm_regulator_get_optional()`。
3. 若 provider 尚未注册，返回 `-EPROBE_DEFER` 并退出该次 probe；不会进入后续电压处理。
4. 若 regulator 获取成功，调用 `regulator_get_voltage()`，随后调用 `iod->write(supply, uV)`。
5. RK3568 PMU IO-domain 的 `iod->write` 实现会对 PMU GRF 的 IO voltage-select 寄存器执行 `regmap_write()`；其他通用分支同样会写 GRF。之后还会注册 regulator notifier，供后续电压变化时调整 IO-domain 设置。

因此，这条现有 consumer 路径并非只读枚举：即使 regulator voltage 查询本身是读取，probe 也会根据返回电压写入 SoC GRF/PMU-GRF。若启用 RK809 provider，MFD pre-init 又会写 PMIC 寄存器；两层副作用均超出当前“不写 PMIC、不改变电源/IO-domain 状态”的授权范围。

### 17.4 R3.5 结论与状态

- 已确认存在真实 DTS regulator consumer 拓扑，且 PMU IO-domain 是优先候选；但其正常 probe 会写 GRF，不能作为当前只读约束下的安全 consumer 验证。
- GMAC PHY consumer 仍 disabled，最早按计划在 R7-A；eMMC/TF/GPU consumer 也不能替代无副作用的 RK809 provider 验收。
- R1 最终 `.config` 已从冻结 artifact 直接核验：`CONFIG_ROCKCHIP_IODOMAIN=y`，`rockchip_iodomain_probe` 等符号存在于 `System.map`，证明驱动 built-in；R1 启动日志记录 IO-domain 设备等待 RK809 regulator supplier 的 deferred-probe。结合源码控制流，`devm_regulator_get_optional()` 返回 `-EPROBE_DEFER` 后直接跳到退出路径，早于 `regulator_get_voltage()` 与 `iod->write()`，因此本次 R1 启动的该次 probe 没有执行 IO-domain GRF 写入。尚未取得该设备后续 deferred-probe 是否再次发生及最终绑定状态的完整日志，故不能据此宣布 consumer 最终 probe 成功。
- 本轮没有启用任何驱动、没有运行 consumer probe、没有读取/写入 GRF 或 PMIC、没有构建或操作设备。

**判定：R3.5 BLOCKED（安全边界阻塞），不是功能 FAIL。R3.3–R3.4 同样因 MFD/regulator probe 写寄存器副作用保持 BLOCKED。R3.1、R3.2、R3.7 的既有 PASS-RUNTIME 不受影响；R3 整体 HOLD/BLOCKED，不放行 R4。**

若未来要完成 R3.3–R3.5，必须先由用户单独决定是否允许 RK809 MFD probe 的 PMIC 写入及 PMU IO-domain consumer 的 GRF 写入，并明确可接受的电源/IO-domain 影响范围；在此之前不实施。


## 18. R3 安全边界的分阶段释放条件与面向网络验证的路线（2026-11-26）

### 18.1 原则修订：边界不是永久禁令

R3 的 BLOCKED 表示“当前证据和授权不足以安全执行”，不表示 RK809 MFD、regulator 或 IO-domain 永远不能启用。项目最终目标是验证 Panther X2 在 Linux 6.18 下的真实硬件工作状态，并为 GMAC/PHY 网络传输提供可复现的正确电源、IO 电压域和驱动参数。后续允许逐步释放边界，但每次只开放一个明确动作集合，不把一次授权扩展为其他寄存器、其他 rail、其他驱动或网络发送授权。

### 18.2 新增的 6.18.63 精确源码证据：RK809 MFD probe 写入范围

冻结源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

- RK809 在 `rk8xx_probe()` 中走 RK817 family 分支，先注册 regmap IRQ，再遍历 `rk817_pre_init_reg[]` 执行 `regmap_update_bits()`，之后创建 MFD 子设备。
- 该 pre-init 表包含 RTC_STOP、较大组 CODEC/ADC/DAC/耳机/音频 PLL/DI2S 配置、GPIO interrupt polarity，以及 SYS_CFG(1) 的 HOTDIE/TSD 温度阈值字段。它不是只读流程，也不是“仅设置 PHY 电源”。
- 本次源码核对未在该 RK817 pre-init 表中发现直接针对 RK809 SWITCH_REG1 enable/voltage selector 的条目；这只能说明该表本身没有直接切换该 rail 的动作，不能推导完整 probe 无副作用。
- `rk817_irq_chip` 使用 status/ack 与 mask 寄存器，并设置 `init_ack_masked=true`；regmap IRQ core 初始化可能读取/确认状态并写 mask/ack。其具体访问序列、W1C 语义和初始中断状态影响仍须逐项核对。
- `system-power-controller` 在 probe 中注册 poweroff/restart handler；注册本身不等于立即关机，但 handler 被调用会写 DEV_OFF/DEV_RST。驱动 shutdown、suspend、resume 路径也会写 SYS_CFG(3)。实验阶段必须禁止执行系统关机、重启、suspend/resume；退出实验镜像应采用已确认不会触发意外 PMIC shutdown 的路径。
- 因此，MFD-only probe 是可考虑的第一项主动验证，但必须先完成 IRQ mask/ack 写入范围和所有生命周期调用路径审计，再由用户对明确写入集合单独授权。

### 18.3 regulator provider 释放条件

`rk808_regulator_probe()` 会注册 RK809 全部 regulator descriptors，而不是天然只注册 `vcc_3v3`。DTS 对 DCDC、LDO 和 SWITCH_REG1 配置了多种约束：多个 rail 为 always-on/boot-on，部分带 init voltage、initial mode、suspend voltage/state；SWITCH_REG1 本身没有 always-on/boot-on 和固定电压约束，但在 GMAC DTS 中作为 PHY supply。

provider 阶段必须先完成：
1. 对 RK809 所有 regulator descriptor 建立完整表：寄存器地址、位域、读写属性、enable/disable、voltage selector、mode、ramp、suspend 操作。
2. 对 Panther DTS 每个 regulator child 的约束逐项映射到 regulator core 的注册时行为，确认哪些属性会在注册阶段触发写入，哪些只在 consumer 请求或 suspend 时触发。
3. 对 PMIC 写寄存器的地址和值建立预期变更白名单；不得把“所有 rail 都 always-on”或“注册不一定写”作为未经验证的假设。
4. 先核实实际板级电压和既有运行状态。regulator framework 的 `get_voltage` 通常反映 selector/配置值，不是物理输出测量；关键 rail 应使用合适的外部测量手段核实，尤其是 SWITCH_REG1。
5. 首次 provider 试验不启用 GMAC/MDIO/PHY，不执行任何 set_voltage/enable/disable 用户空间操作，不触发 suspend/resume；仅观察 provider 注册结果、只读 regulator 状态和受控寄存器差异。

### 18.4 IO-domain consumer 释放条件

RK3568 PMU IO-domain probe 会读取 regulator voltage 并按电压写 GRF/PMU-GRF IO voltage-select 位。它的目标不是切换 PMIC rail，而是让 SoC IO 电压域选择与外部供电相匹配；写错仍可能造成接口电平不匹配。

释放条件：
- 确认 RK3566/Panther 实际匹配的 IO-domain soc_data、bank index 与 GRF register/bit mapping。
- 把 DTS 的每个 supply 与对应物理 bank/pin group、实际供电 rail 对齐；不能只凭 `vccioN` 名称推断。
- 读取当前 GRF 选择位，并用外部测量核实对应 rail 的实际电压；确认驱动写入值与板级供电一致。
- 仅在明确授权后启用 consumer；执行后只读回同一 GRF 位并核对预期变化，不做无关 GRF 写入。
- 若驱动拟写值与实测 rail 不一致、映射有歧义或返回电压不可确定，停止，不允许 probe 继续写。

### 18.5 建议的主动验证阶段门（本节是路线，不是操作授权）

| 阶段 | 验证目标 | 允许的动作集合 | 通过证据 |
|---|---|---|---|
| G0 | 完成寄存器/配置/拓扑预审 | 源码、DTS、Kconfig、artifact 只读审计 | 精确写入白名单、风险表、回退方案 |
| G1 | MFD-only | 用户单独授权后，仅绑定 RK809 MFD；regulator driver 和 IO-domain consumer 不启用 | probe/IRQ 成功；PMIC 访问与预期写入集合一致；未改变关键 rail |
| G2 | regulator provider | G1 通过并单独授权后，启用 RK809 regulator provider；不启用网络节点 | rails 注册；约束与 selector 状态一致；关键 rail 外部实测合格 |
| G3 | PMU IO-domain | G2 通过并单独授权后，启用 IO-domain consumer | bank mapping、供电电压、GRF 选择位相互一致 |
| G4 | PHY supply path | 进入原计划 R7-A，经单独授权恢复 GMAC1/MDIO/PHY；核验 SWITCH_REG1 的实际 consumer 请求与电压 | PHY supply 获取/使能、MDIO/PHY probe/link 证据 |
| G5 | TX-first | R7-D 独立授权 | 对端真实捕获 Panther 发出的原始 Ethernet 广播帧 |
| G6 | 协议栈递进 | 仅 TX-PASS 后，按 R8 逐层放行 | RX、ARP、IPv4、ICMP、路由、TCP/UDP、DHCP/DNS 分层双端证据 |

### 18.6 回退与停止标准

- 每阶段使用独立实验镜像/专用 SU08G TF；不写 SN64G，不写 eMMC。启动前核对 Image/DTB/initramfs 哈希与介质身份。
- 每阶段开始前记录可安全读取的 PMIC/GRF 状态、关键 rail 外部电压、内核日志和相关设备状态；只对数据手册明确可读且无读副作用的寄存器执行读取。
- 不把“恢复原寄存器值”作为通用回退：某些状态位、W1C、写一触发、锁存或电源时序寄存器不可简单回写。回退必须按具体寄存器语义设计。
- 任一异常掉电、复位、PMIC 错误、rail 电压偏离、温度/中断异常、I2C 错误、设备 probe defer/error 或非预期 GRF 变化，立即停止后续阶段；保留日志与原始状态，不继续叠加驱动。
- MFD probe 后如要退出，优先正常关机路径必须事先审计；不能假定 module unbind 或直接断电可恢复 PMIC 状态。首次实验不进入 suspend/resume，不调用 poweroff/restart handler。
- 所有阶段仅为硬件验证，不授权写入生产系统、修改 eMMC、启用无线功能或执行网络传输测试。

### 18.7 当前可执行的下一步（仍为只读）

下一项只读工作是核对 R1 最终 `.config` 中 `CONFIG_ROCKCHIP_IODOMAIN`、`CONFIG_MFD_RK8XX_I2C`、`CONFIG_REGULATOR_RK808` 的实际值及对应 built-in/module 对象，并复核 R1 启动日志中 IO-domain deferred-probe 的最终状态。然后完成 RK817 IRQ mask/ack 初始化写入语义和 RK809 regulator registration constraints 的逐项审计，形成 G1/G2 写入白名单。

**本节不改变当前授权：尚未授权 MFD probe、regulator provider、IO-domain consumer、GRF/PMIC 写入或 GMAC 恢复。**


## 19. G0 补充：R1 最终 IO-domain 配置、deferred-probe 与 RK809 IRQ 写入边界（2026-11-26）

### 19.1 R1 最终 artifact 的配置与对象实证

直接下载并解包冻结 artifact `b2-1-r1-network-core`（artifact ID `15023630465`），核对 `output/kernel.config`、`output/System.map` 与 `output/modules.tar.zst`。配置文件 SHA256 再次匹配 `480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`。

| 配置/对象 | R1 最终证据 | 判定 |
|---|---|---|
| `CONFIG_ROCKCHIP_IODOMAIN` | `y` | built-in |
| `rockchip_iodomain_probe` / `rockchip_iodomain_write` | 存在于 `System.map` | built-in 代码已进入 Image |
| `CONFIG_REGULATOR` | `y` | regulator core built-in |
| `CONFIG_MFD_RK8XX_I2C` | not set | RK8xx I2C transport 未构建 |
| `CONFIG_MFD_RK8XX_SPI` | not set | RK8xx SPI transport 未构建 |
| `CONFIG_REGULATOR_RK808` | 无启用项 | RK809/RK808 regulator provider 未构建 |
| RK8xx core/I2C/regulator objects | `modules.tar.zst` 无对应对象 | 未以模块形式构建 |

注意：`CONFIG_ROCKCHIP_IODOMAIN=y` 不是 UNKNOWN；这是已验证的 R1 配置事实。与此同时，MFD transport/provider 缺失，导致 IO-domain 所需 RK809 supplies 无法取得。

### 19.2 R1 启动时 IO-domain deferred-probe 的安全意义

R3.1 实机启动日志归档已记录 MMC、SARADC、IO-domain 等设备等待 `/i2c@fdd40000/pmic@20/regulators/...` supplier 的 deferred-probe。结合冻结 6.18.63 `drivers/soc/rockchip/io-domain.c` 的精确控制流：

1. probe 先取得 GRF regmap；
2. 对每个供电 rail 调用 `devm_regulator_get_optional()`；
3. 若返回 `-EPROBE_DEFER`，直接进入清理/退出路径；
4. 只有取得 regulator 后才调用 `regulator_get_voltage()`；
5. 再之后才调用 `iod->write(supply, uV)` 执行 GRF/PMU-GRF 写入。

因此，在 R1 缺少 RK809 provider 的已记录 deferred-probe 情况下，该次 probe 不会执行 regulator voltage 查询或 IO-domain 写入。这是一个重要的安全事实：R1 的 IO-domain driver 虽然 built-in 并尝试 probe，但因供电 provider 缺失而 defer，未走到 GRF 写操作。

仍未取得 deferred-probe 后续重试的最终日志，因此最终设备绑定状态保留 UNKNOWN；不能将“曾 defer”夸大为“始终未绑定”，也不能将其解释为 consumer 已正常工作。

### 19.3 RK809 MFD IRQ 初始化写入：新的明确风险项

冻结源码 `drivers/mfd/rk8xx-core.c` 对 RK809 选择 `rk817_irq_chip`：

- `num_regs=3`；
- `irq_reg_stride=2`；
- `status_base=RK817_INT_STS_REG0`；
- `mask_base=RK817_INT_STS_MSK_REG0`；
- `ack_base=RK817_INT_STS_REG0`；
- `init_ack_masked=true`。

冻结头文件定义对应寄存器：

| 地址 | 名称 |
|---|---|
| `0xF8` | `RK817_INT_STS_REG0` |
| `0xF9` | `RK817_INT_STS_MSK_REG0` |
| `0xFA` | `RK817_INT_STS_REG1` |
| `0xFB` | `RK817_INT_STS_MSK_REG1` |
| `0xFC` | `RK817_INT_STS_REG2` |
| `0xFD` | `RK817_INT_STS_MSK_REG2` |

冻结 Linux `drivers/base/regmap/regmap-irq.c` 的 `regmap_irq_sync_unlock()` 显示：
- 初始化 mask 同步会对 mask registers 执行 `regmap_update_bits()`；
- `init_ack_masked=true` 时，会对被 mask 的 IRQ 在 ack_base 上执行 `regmap_write()`；
- RK817 的 ack_base 与 status_base 相同，因此可能对 `0xF8/0xFA/0xFC` 执行写入；这些地址是中断状态/ack 寄存器，不是普通配置寄存器。

这意味着 MFD-only probe 不只是写入 pre-init 表中的普通配置位，还会初始化 IRQ mask，并对 masked IRQ 状态执行 ack 写入。必须将 0xF8/0xFA/0xFC 的 W1C/ack 语义、当前中断锁存状态与具体写入值核对清楚；不能把它们视为无影响的普通写操作。此前 R3.7 对 `0xF0`、`0xF6` 的只读成功并不覆盖这些 IRQ registers。

### 19.4 G0 当前结论与下一项审计

- **PASS-STATIC：** R1 IO-domain built-in 配置与对象已确认；RK8xx MFD transport/provider 缺失已由真实 config 和 modules archive 交叉确认。
- **PASS-RUNTIME（有限）：** R1 IO-domain 发生 regulator supplier deferred-probe；源码控制流证明该次 defer 路径不会进入 GRF 写入。
- **UNKNOWN：** IO-domain 后续 deferred-probe 最终状态。
- **BLOCKED：** MFD-only probe 仍不能放行；IRQ mask/ack 写入已确认是必须纳入白名单的新副作用。
- **网络目标关联：** IO-domain 的作用是让 SoC IO bank 电平选择匹配实际供电 rail。只有 provider 与实际电压匹配后，才能把它纳入后续 PHY/GMAC 正常工作参数验证；但不能假设 GMAC RGMII bank 对应哪路 rail，仍需逐 pin/bank 映射。

下一项只读 G0 工作：把 RK809 IRQ 三组状态/屏蔽寄存器的位定义、W1C 行为与 Linux regmap IRQ 初始化初始 mask 值逐位对照；同时把 RK809 pre-init 表逐项映射到 datasheet 的寄存器访问属性。完成后再决定 G1 是否可按“允许的 IRQ ack + mask + pre-init 白名单”申请单独授权。

**本节未授权任何新增硬件写操作；未启用 MFD/regulator，未执行 GRF 写入或网络发包。**


## 20. G0-A：RK809 IRQ 24-bit Linux 映射与 Rev 2.4 数据手册差异（2026-11-26）

### 20.1 冻结源码的实际映射

源码端点仍为 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

- `rk8xx-i2c.c` 将 `rockchip,rk809` 选择为 `variant=RK809_ID`，但其 regmap config 复用 `rk817_regmap_config`。
- `rk8xx-core.c` 对 RK809 与 RK817 共用 `rk817_irq_chip`，配置 `num_regs=3`、`irq_reg_stride=2`、status base 0xF8、mask base 0xF9、ack base 0xF8、`init_ack_masked=true`。
- `REGMAP_IRQ_REG_LINE(id,8)` 将 24 个 Linux IRQ 编号映射为三组寄存器，每组 8 位：
  - IRQ 0–7 → STS0 0xF8 / MSK0 0xF9，bit 0–7；
  - IRQ 8–15 → STS1 0xFA / MSK1 0xFB，bit 0–7；
  - IRQ 16–23 → STS2 0xFC / MSK2 0xFD，bit 0–7。
- RK809 regmap 使用 8-bit register / 8-bit value，默认 register stride 为 1；IRQ stride 2 因而对应地址 F8/FA/FC 与 F9/FB/FD。

### 20.2 Linux IRQ 事件表

| 状态寄存器 | bit | Linux 事件名 |
|---|---:|---|
| 0xF8 | 0–7 | PWRON_FALL、PWRON_RISE、PWRON、PWMON_LP、HOTDIE、RTC_ALARM、RTC_PERIOD、VB_LO |
| 0xFA | 0–7 | PLUG_IN、PLUG_OUT、CHRG_TERM、CHRG_TIME、CHRG_TS、USB_OV、CHRG_IN_CLMP、BAT_DIS_ILIM |
| 0xFC | 0–7 | GATE_GPIO、TS_GPIO、CODEC_PD、CODEC_PO、CLASSD_MUTE_DONE、CLASSD_OCP、BAT_OVP、CHRG_BAT_HI |

### 20.3 RK809 Datasheet Rev 2.4 位属性对照

官方寄存器表对上述寄存器的定义并不完全支持 Linux 的 24 个有效事件映射：

| 地址 | Rev 2.4 定义 | Linux 映射差异 |
|---|---|---|
| 0xF8 STS0 | bit 0–7 全部 W1C，依次为 PWRON_FALL、PWRON_RISE、PWRON、PWRON_LP、HOTDIE、RTC_ALARM、RTC_PERIOD、VCC9_LO | Linux 将 bit7 命名为 VB_LO；名称差异需核实，但 bit 位及 W1C 属性一致 |
| 0xF9 MSK0 | bit 0–7 全部 RW mask | 与 Linux 8-bit mask 对应 |
| 0xFA STS1 | bit 0 PLUG_IN、bit 1 PLUG_OUT；bit 2–7 标为 W1C RESV | Linux 把 bit 2–7 定义为 CHRG_TERM/TIME/TS、USB_OV、CHRG_IN_CLMP、BAT_DIS_ILIM |
| 0xFB MSK1 | bit 0–1 为 PLUG mask；bit 2–7 标为 RW RESV | Linux 对 8 bit 全部建立 IRQ mask |
| 0xFC STS2 | bit 2–5 为 CODEC_PD、CODEC_PO、CLASSD_MUTE_DONE、CLASSD_OCP；bit 7–6 标为 RC RESV；bit 1–0 标为 W1C RESV | Linux 将 bit0–1 定义为 GATE_GPIO/TS_GPIO，将 bit2–5 定义为 CODEC/CLASSD，将 bit6–7 定义为 BAT_OVP/CHRG_BAT_HI |
| 0xFD MSK2 | bit 2–5 为 CODEC/CLASSD mask；bit 7–6 与 bit 1–0 标为 RW RESV | Linux 对 8 bit 全部建立 IRQ mask |

来源：Rockchip RK809 Datasheet Rev 2.4（2024-01-02），§5.2，PDF 页 122–125；冻结 Linux 源码中的 `rk817_irqs[]`、`rk817_irq_chip` 与 `REGMAP_IRQ_REG_LINE`。

### 20.4 probe 阶段实际写入和清状态条件

冻结 `drivers/base/regmap/regmap-irq.c` 的 `regmap_add_irq_chip_fwnode()` 初始化过程：

1. 根据 `rk817_irqs[]` 构造 `mask_buf_def`。24 个 IRQ 每个都占一个 bit，因此三组默认 mask 均为 `0xFF`。
2. 默认将全部 IRQ mask，并通过 `regmap_update_bits()` 更新 mask registers：预期目标为 `0xF9=0xFF`、`0xFB=0xFF`、`0xFD=0xFF`（实际总线写值由 regmap_update_bits 的读改写及硬件当前值决定）。
3. 因 `init_ack_masked=true`，初始化会读取 0xF8、0xFA、0xFC 的状态。
4. 若某组状态非零，则对对应 ACK/status register 写入 `status_buf & mask_buf`。由于初始 mask 为 `0xFF`，写入值等于该组读取到的状态字节；这会对该字节所有置位的 W1C 状态执行 ACK。
5. 这不是无条件写 `0xFF` 到状态寄存器；只有读取状态非零时才发生 ACK 写入。但它可能清除当时已锁存的 PMIC 事件。对于 0xFA/0xFC 中手册标为 reserved 的位，Linux 映射与数据手册定义冲突，不能保证清除语义安全。

### 20.5 G1 放行判断

- **已确认：** Linux 对 RK809 使用 RK817 的 24-bit IRQ 描述；默认 mask 三组 8-bit；初始化读取状态并可能向状态/ACK 寄存器写回当前置位值。
- **已确认：** RK809 Rev 2.4 对 STS1 bit2–7 标为 W1C reserved；对 STS2 bit0–1 标为 W1C reserved、bit6–7 标为 RC reserved。Linux 却将这些位置分配给额外 IRQ。
- **未确认：** 当前实机芯片 ID 读到 `0x8094` 对应的具体 RK809 子型号/硅版本是否使用了与 Rev 2.4 表格不同的 IRQ 布局；以及这些保留位在 Panther 实际芯片上是否存在额外功能。
- **风险：** 若按 Linux 通用映射初始化，mask registers 的 reserved bits 也可能被写 1；若 status reserved bits 读出 1，初始化 ACK 可能对其写 1 或在 RC 位上发生读副作用。不能仅凭 datasheet 的 RESV 字样断定写入一定无害，也不能假定 Linux 映射一定适用于当前硅版本。
- **结论：G0-A 静态审计发现未解决的 silicon/documentation mismatch；G1 不放行。** 不应为了让驱动 probe 成功而直接接受这项差异。

### 20.6 下一步只读核查

1. 追查 RK809/RK817 IRQ layout 的上游提交历史、Rockchip BSP 与当前 6.18 分支差异，确认 Linux 24 IRQ 定义适用的器件/版本范围。
2. 对照 RK809 Rev 2.4/2.5 和芯片身份字段；当前读到的 0xEE=0x94 保留为原始证据，明确高 nibble CHIP_NAME=0x9、低 nibble RESV=0x4，不自行推断 silicon revision。
3. 核对 RK809 I2C regmap 的 volatile/cache 行为，确认 IRQ status/mask 读写是否会经 cache 或触发读副作用。
4. 在完成上述核查前，不读取 0xF8–0xFD 实机寄存器，不做总线扫描，不进行任何 PMIC 写入；现有 R3.7 对 0xF0/0xF6 的授权不包含 IRQ register 访问。

**G1 释放条件新增：必须解释并解决 RK809 Rev 2.4 与 Linux 24 IRQ bit map 的差异，且明确保留位处理策略。**

## 21. G0-A 黄金基线回溯：6.1.65 RK809 IRQ / MFD / regulator 对照（2026-11-26）

### 21.1 6.1.65 源码身份与证据等级

复用方向二已归档的 6.1.65 源码候选端点：
`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`。

该 commit 与原版 6.1.65 Kernel build 时间及提交版本线索吻合，是高置信度源码候选，但尚未与 6.1.65 原始 Image 建立二进制级构建来源绑定。因此以下函数级比较标记为 **GOLDEN-CANDIDATE SOURCE**，不能冒充已锁定的原始构建源码。6.1.65 的实际 `.config`、`modules.builtin` 和 2026-11-24 Panther X2 正常有线网络运行结果则是已归档的直接证据。

### 21.2 IRQ 映射：6.1.65 与 6.18.63 并无新引入差异

在 6.1.65 候选源码 `drivers/mfd/rk808.c` 中：
- RK809 compatible 与 RK817 compatible 均进入 ID 读取路径，读取 `0xED`、`0xEE`，将 ID mask 后识别 variant。
- RK809 variant 与 RK817 variant 共用 `rk817_irq_chip`、`rk817_irqs[]`、`rk817_regmap_config`、`rk817_pre_init_reg[]` 与 `rk817s` MFD cells。
- IRQ 定义为 24 路，按三组 8-bit line 映射到 status/ack `0xF8/0xFA/0xFC` 和 mask `0xF9/0xFB/0xFD`。
- IRQ chip 同样设置 `num_regs=3`、`irq_reg_stride=2`、`status_base=0xF8`、`mask_base=0xF9`、`ack_base=0xF8`、`init_ack_masked=true`。

6.18.63 `rk8xx-core.c` 继续对 RK809 使用相同的 `rk817_irq_chip` 与 24 路 IRQ 表。**因此，RK809 24-bit IRQ layout 不是 6.18 新引入的变化；在可用的 6.1.65 高置信度候选源码中已经存在。**

这项对照改变了问题定性：与 RK809 Rev 2.4 对保留位的描述不一致，属于至少跨越 6.1.65 候选与 6.18.63 的历史兼容性疑点，而不是当前已证实的 6.18 regression。6.1.65 在同一 Panther X2 实机上成功运行千兆链路和 IPv4 网络，是该整机组合的正向集成行为证据；但不能单独证明 IRQ reserved bits 从未被置位、写入 ACK 无副作用，或 24 路 IRQ 全部被触发验证。

### 21.3 MFD probe 身份识别方式的版本差异

| 行为 | 6.1.65 候选源码 | 6.18.63 固定源码 |
|---|---|---|
| PMIC variant 来源 | probe 读取 ID 0xED/0xEE 并 mask 识别 | I2C OF match data 提供 variant |
| RK809 / RK817 IRQ | 共用 rk817 24-bit IRQ 表 | 共用 rk817 24-bit IRQ 表 |
| pre-init | 共用 rk817_pre_init_reg | 共用 rk817_pre_init_reg |
| MFD 子设备 | rk817s | rk817s |
| shutdown / restart | RK809 使用 RK817 SYS_CFG(3) 对应位 | 同一功能寄存器及位定义 |
| regulator provider | rk808-regulator.c | rk808-regulator.c，随 RK8xx core 拆分 |

用户在 6.18 RAM-only R1 上读到 `0xED=0x80`、`0xEE=0x94`，原始 ID `0x8094`。按 6.1.65 候选源码的 ID mask/variant 逻辑，该原始 ID 会归入 RK809 variant（mask 后为 RK809 ID）。这使旧版驱动身份识别路径与本次只读身份结果相互吻合，但没有在 6.1.65 原版系统中取得 PMIC probe 日志来证明当时实际打印的 chip ID。

### 21.4 pre-init 与 regulator descriptor 对照

6.1.65 候选源码与 6.18.63 固定源码的 RK809 pre-init 均使用 `rk817_pre_init_reg[]`。两者包含 RTC_STOP 和大量 CODEC 寄存器初始化；这些是 probe 副作用，不因驱动文件拆分而消失。

对网络相关的 `SWITCH_REG1`，两版 `rk808-regulator.c` 的 RK809 descriptor 对照一致：
- regulator name：`SWITCH_REG1`；
- supply name：`vcc9`；
- enable register：`RK817_POWER_EN_REG(3)`；
- enable mask/value：`ENABLE_MASK(2)`；
- disable value：`DISABLE_VAL(2)`；
- 属于 switch regulator，不提供可调 voltage selector。

RK809 regulator probe 的代码组织略有变化：6.1.65 从 parent drvdata 取得 regmap/client 并按 variant 选择 descriptor；6.18 通过 parent device 取得 regmap，并把 OF node 关联给 regulator child device 后注册 descriptor。两版最终仍通过 `devm_regulator_register()` 注册对应 regulator 集合。

这证明 RK809 SWITCH_REG1 的 Linux descriptor 在两个源码端点间没有发现差异，但**不能证明 Panther X2 两版 DTB 对 SWITCH_REG1 的 constraints 完全相同，也不能证明 regulator registration 没有读改写副作用或实测电压相同**。还需完成 Golden DTB regulator 子节点属性的逐项提取。

### 21.5 G0-A 修订结论

1. **PASS-COMPARISON（带源码身份限制）：** 6.1.65 候选源码与 6.18.63 的 RK809 24-bit IRQ layout、pre-init 表及 SWITCH_REG1 descriptor 一致。
2. **历史兼容性疑点仍存在：** 两版源码都复用 RK817 IRQ layout，而 RK809 Rev 2.4 对部分位标为 reserved。由于 6.1.65 实机网络成功，该疑点不能单独解释为 6.18 网络回归；仍需确认数据手册/芯片修订及实际 IRQ 状态。
3. **身份判定路径差异已确认：** 6.1.65 通过读取 0xED/0xEE 并按 masked ID 识别 RK809 variant；6.18 依赖 OF compatible match data，不在 MFD probe 中重新读取 ID。当前实测 0x8094 的高 nibble 与 RK809 CHIP_NAME code 相符；低 nibble 为 RESV 非默认值，另行保留为 UNKNOWN。
4. **G1 仍不放行：** 黄金基线的正常网络行为不等于对 PMIC IRQ ACK 写入的风险豁免。必须完成 RK809 datasheet revision/芯片 revision 适用性核实、Golden DTB regulator constraints 对照、pre-init 寄存器属性核对与 MFD IRQ 初始状态影响评估。
5. **网络目标关联：** 两版 SWITCH_REG1 descriptor 一致，为后续验证 `phy-supply` provider/consumer 关系提供了较强参照；但实际 PHY rail 电压和 PHY 工作电源链仍未验证。

### 21.6 下一步最小任务

- 从已归档 6.1.65 原始 DTB 中提取 RK809 regulator 子节点与 SWITCH_REG1 的完整属性，和 R1 最终 DTB 做逐字段比较；不访问、不写入 SN64G。
- 追溯 RK809 Rev 2.4 与芯片版本字段 0xEE=0x94 的关系，区分 datasheet default byte、silicon revision 与 reserved-bit 说明适用范围。
- 复核 6.1.65 启动日志是否留有 RK809 probe / regulator registration / IO-domain probe 记录；只复用归档资料，不重复启动黄金介质。
- 然后完成 RK809 pre-init 表逐项寄存器访问属性表。未完成前继续不读取 0xF8–0xFD 实机寄存器、不启用 MFD、不进行 PMIC 写操作。

**本节未访问实机、未读取 IRQ 状态寄存器、未执行任何硬件写入。**
## 22. G0-A 后续：RK809 pre-init 与 regulator/DT 黄金基线差异复核（2026-11-26）

### 22.1 pre-init 表逐项源文本比较

对照冻结源码端点：
- 6.1.65 高置信度候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`，`drivers/mfd/rk808.c`；
- 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`，`drivers/mfd/rk8xx-core.c`。

直接提取两端 `static const struct rk808_reg_data rk817_pre_init_reg[]` 的完整花括号数组，结果为**逐字节文本相同**（均 3,853 bytes，包含空白/注释）。因此该表不是 6.18 新增，也没有发现 6.1.65→6.18.63 的地址、mask、value 或顺序差异。

表项包括 RTC_STOP、多个 RK817 CODEC DTOP/AREF/AADC/DADC/AMIC/DMIC/ADAC/DDAC/AHP/CLASSD/APLL/DI2S 寄存器，以及 GPIO interrupt polarity 和 thermal threshold 字段。源码自身明确注释 `CODEC_AREF_RTCFG0`、`CODEC_AADC_CFG1`、`CODEC_ADAC_CFG0` 未在所引用数据手册中定义。这些条目在两版都存在，故不能将其视为 6.18 regression；但它们仍是 probe 会执行的 PMIC 写入，必须依据正确器件手册/厂商资料确认适用性，不能仅因 6.1.65 曾正常联网就推定安全。

### 22.2 RK809 regulator descriptor 的真实差异

对照两版 `drivers/regulator/rk808-regulator.c` 中完整 `rk809_reg[]` descriptor 数组。数组不是完全相同：6.18 对 RK817 DCDC_REG3 descriptor 新增：

```c
.apply_reg = RK817_POWER_CONFIG,
.apply_bit = RK817_BUCK3_FB_RES_INTER,
```

这是 DCDC_REG3（RK809 DCDC_REG3 / vcc_ddr）配置路径差异，不是 SWITCH_REG1。逐项核对 RK809 switch descriptors：

| 项目 | 6.1.65 候选 | 6.18.63 |
|---|---|---|
| SWITCH_REG1 name | `SWITCH_REG1` | 相同 |
| SWITCH_REG1 supply | `vcc9` | 相同 |
| SWITCH_REG1 enable register | `RK817_POWER_EN_REG(3)` | 相同 |
| SWITCH_REG1 enable mask | `ENABLE_MASK(2)` | 相同 |
| SWITCH_REG1 enable/disable value | `ENABLE_MASK(2)` / `DISABLE_VAL(2)` | 相同 |
| SWITCH_REG2 name/supply | `SWITCH_REG2` / `vcc8` | 相同 |
| SWITCH_REG2 enable register/mask | `RK817_POWER_EN_REG(3)` / `ENABLE_MASK(3)` | 相同 |

所以，针对 Panther GMAC `phy-supply` 指向的 SWITCH_REG1，未发现 6.1.65→6.18 descriptor 控制位差异。DCDC_REG3 的新增 apply register/bit 是真实跨版本差异，但目前没有证据表明它会影响 SWITCH_REG1 或 PHY 3.3V rail；应在后续 regulator 审计中独立记录，不能扩大解释。

### 22.3 Panther RK809 DTS regulator 子树候选源码对照

对照相同两个候选源码端点的 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`，提取完整 `rk809: pmic@20` 节点（含 regulator 子树）后归一化空白及 system-power-controller 属性写法，节点内容完全相同。唯一源文本差异为：
- 6.1.65 候选 DTS：`rockchip,system-power-controller;`（旧版 vendor 前缀写法）；
- 6.18.63 DTS：`system-power-controller;`（标准属性写法）。

regulator 子树中 DCDC_REG1–5、LDO_REG1–9、SWITCH_REG1/2 的名称、min/max/init voltage、always-on/boot-on、initial-mode、ramp-delay、suspend-state 等属性未发现差异。尤其 SWITCH_REG1 仅定义 `regulator-name = "vcc_3v3"` 与 `regulator-off-in-suspend`，未定义 `regulator-always-on`、`regulator-boot-on`、电压 selector constraints 或 init voltage。

**证据限制：** 6.1.65 源码端点仍是 GOLDEN-CANDIDATE SOURCE，不是原始 6.1.65 image 对应 DTS/DTB 的二进制级绑定。仓库原始镜像审计记录已归档 `04-device-tree.tar.gz`（Dropbox `/04-device-tree.tar.gz`，2,256,475 bytes，SHA256 `b09451c53393353de55cbd4d7074eca593fd64a21ff9bc88cab223a9cdd6f3af`），但本轮没有解包其中的原始 DTB 并解析 PMIC 节点。因此上述 DT 比较暂记 **CANDIDATE-SOURCE MATCH**，不能升级为 GOLDEN-BINARY DTB PASS。

### 22.4 对 G1 与网络 TX 路径的影响

1. **可确认的跨版本一致部分：** RK809 pre-init 表逐字节一致；SWITCH_REG1/SWITCH_REG2 descriptor 的 enable 控制定义一致；候选 Panther DTS 的 RK809 regulator constraints 子树一致。
2. **可确认的跨版本差异：** 6.18 regulator descriptor 为 DCDC_REG3 新增 apply register/bit；DTS system-power-controller 属性由 vendor-prefixed 写法改为标准写法。
3. **仍不能安全放行 MFD/regulator：** pre-init 表包含数据手册未定义的 codec registers；IRQ 初始化仍涉及 status ACK；regulator registration 会根据多路 rail constraints 执行配置/enable。黄金基线正常启动只能证明整机曾在该版本下运行，不能证明这些初始化写入对当前 RK809 revision 的全部副作用。
4. **网络链可利用的正向结论：** SWITCH_REG1 驱动描述符和候选 DTS constraints 在两版本间没有发现变化。后续 R7-A 可把它作为比较基准，重点验证 6.18 provider 是否注册、phy-supply consumer 是否成功获取/使能，以及物理 rail/PHY 上电是否正常；不能把当前静态结果当作已供电。

### 22.5 下一步

- 对归档的原始 `04-device-tree.tar.gz` 获取可解析的原始 6.1.65 DTB，验证其 RK809 节点是否与候选源码相同；这是本项尚缺的最小黄金二进制证据。
- 对 pre-init 表的 codec 未定义寄存器及 RTC/GPIO/thermal 项，核对 RK809 datasheet Rev 2.4 和可取得的 RK809/RK817 codec supplement/vendor register map；标出 documented / undocumented / not applicable，不执行寄存器访问。
- 查明 DCDC_REG3 `.apply_reg/.apply_bit` 变更的引入提交与适用 silicon 条件；当前不把它作为 PHY rail 根因。
- 维持 R3.3–R3.5 BLOCKED；不读取 IRQ status 0xF8–0xFD，不启用 MFD/regulator，不改变 PMIC 电源配置。

**本节为源码/归档元数据只读审计；未访问 Panther X2、未执行 I2C/PMIC 事务、未写入任何介质。**
## 23. RK809 codec pre-init 手册版本复核与 DCDC_REG3 差异定性（2026-11-26）

### 23.1 修订此前“未定义寄存器”的表述

进一步核对 Rockchip 官方 RK809 Datasheet Rev 1.8（2021-10）与 Rev 2.4（2024-01）后，发现此前将三个寄存器笼统称为“数据手册未定义”不够精确，现修订为：

| 驱动 pre-init 项 | 地址 | Rev 1.8 | Rev 2.4 | 精确结论 |
|---|---:|---|---|---|
| `CODEC_AREF_RTCFG0` | 0x16 | Register Summary 有条目，无详细 bit-field 说明 | Register Summary 有条目，无详细 bit-field 说明 | 地址已列出，但 bit semantics 未文档化；不能称为完全不存在 |
| `CODEC_AADC_CFG1` | 0x19 | Register Summary 未列出 | Register Summary 未列出 | 两份公开 datasheet 均无条目/bit-field 说明 |
| `CODEC_ADAC_CFG0` | 0x2E | Register Summary 未列出 | Register Summary 未列出 | 两份公开 datasheet 均无条目/bit-field 说明 |

因此 Linux 源码注释“not defined in data sheet”对 0x19 和 0x2E 符合公开手册；对 0x16 更准确的说法应为“summary listed, detailed bit definition absent”。Rev 1.8 与 Rev 2.4 在这一点上没有补充这些字段定义。不能因为 0x16 在 summary 中出现，就假设向其写 0x00 的语义已被充分定义。

还需区分：`CODEC_AREF_RTCFG1`（0x17）及 `CODEC_ADAC_CFG1`（0x2F）在两份 datasheet 中有详细 bit-field 定义；驱动写入值分别为 0x06 和 0x07。公开资料显示其字段为 RW，但包含内部使用/保留字段；这类整字节写入仍须按实际字段语义审查，而不能只以寄存器整体标注 RW 就直接判为无风险。

### 23.2 两版 pre-init 数组相同，但不等于整套初始化适用于所有 RK809 silicon

6.1.65 候选与 6.18.63 固定源码中的 pre-init 数组仍为逐字节一致。该数组对 0x16、0x19、0x2E 均使用 `MASK_ALL` 写入 0x00；因此两个内核版本对这些 undocumented/partially documented 地址具有相同写入行为。黄金基线运行成功只证明该完整系统组合曾工作，不能证明每个 codec 保留/未定义寄存器写入对所有 RK809 revision 都无副作用。

本项目的实际用途不涉及 RK809 codec/audio，因此安全放行时应优先考虑能否在后续受控构建中隔离非网络必需的 codec pre-init 写入；但不能直接改动驱动。必须先确认 RTC/GPIO/thermal 必需初始化与 codec 写入可否独立拆分、MFD 代码是否允许安全地保留必要功能，并以 6.1.65 行为作对照。

### 23.3 0xEE=0x94 的含义边界

RK809 Datasheet Rev 2.4 与 Rev 2.5 对 `PMIC_CHIP_VER` (0xEE) 的定义一致：bit[7:4] 是 CHIP_NAME code[3:0]，默认 0x9；bit[3:0] 明确标为 RO/RESV，reset value 0x2。实测 0x94 的高 nibble 0x9 与 RK809 CHIP_NAME code 一致，低 nibble 0x4 则是 reserved 非默认值。该寄存器名称虽为 CHIP_VER，但手册并未把低 nibble 定义为 silicon revision；不能把 0x94 擅自解释为“revision 4”，也不能单凭该差异断言芯片异常。应向 Rockchip/BSP 资料寻找该 reserved nibble 的 silicon/OTP 说明；在取得说明前标记为 **RO reserved nibble differs from documented reset default; interpretation UNKNOWN**。

### 23.4 DCDC_REG3 `.apply_reg/.apply_bit` 差异

6.18.63 的 RK809 DCDC_REG3 descriptor 新增 `.apply_reg = RK817_POWER_CONFIG` 与 `.apply_bit = RK817_BUCK3_FB_RES_INTER`，6.1.65 候选 descriptor 没有这两个字段。此项是 descriptor/voltage-change 应用机制差异，不是 SWITCH_REG1 enable path 差异。

当前已确认：
- DCDC_REG3 属于 vcc3 / SoC DDR 供电相关 regulator，不是 PHY 的 SWITCH_REG1/vcc9 provider；
- 该 apply bit 会改变 DCDC_REG3 电压设置提交/应用行为；
- 没有证据表明它改变 SWITCH_REG1 的使能寄存器、mask 或值；
- 尚未取得引入该字段的确切上游 commit 和针对 RK809 silicon 的适用说明，因此引入原因及硬件适用条件标记 UNKNOWN。

在取得 commit provenance 前，不将其列为 TX 故障根因，也不进行实机寄存器读写。后续若分析 SoC DDR rail 稳定性，可再独立评估；当前网络 TX 主线不扩展到此专题。

### 23.5 本轮结论与安全边界

1. 6.1.65 / 6.18 pre-init 表逐字节一致；codec pre-init 中 0x16 是 summary listed but bitfield undocumented，0x19/0x2E 在 Rev 1.8 和 Rev 2.4 均未列入 register summary。
2. 两个内核版本都执行相同的这些写入；这是历史兼容行为而非 6.18 regression，但不自动构成对当前 0x8094 器件 revision 的安全证明。
3. 0xEE=0x94 的高 nibble 符合 RK809 CHIP_NAME code；低 nibble 0x4 是 Rev 2.4/2.5 均标记为 RESV 的非默认值，不是 silicon revision，含义 UNKNOWN。
4. DCDC_REG3 apply 字段是独立的 6.18 descriptor 差异；目前不影响 SWITCH_REG1 对照结论。
5. G1 仍 HOLD。不要为了网络测试启用 codec/audio 功能；也不允许用整组 MFD probe 作为“只验证 I2C”的方法。

**本节仅复核公开 datasheet 与冻结源码；未访问实机、未执行 PMIC 事务、未写入介质。**
## 24. DCDC_REG3 上游补丁适用性与 PMIC_CHIP_VER 历史手册差异（2026-11-26）

### 24.1 DCDC_REG3 apply_bit 补丁来源已查明

找到上游补丁邮件：Mikhail Rudenko，2024-10-17，标题 `[PATCH] regulator: rk808: Add apply_bit for BUCK3 on RK809`，base commit `9852d85ec9d492ebef56dc5f229416c925758edc`。补丁解释：RK809 BUCK3（DCDC_REG3）虽然在 Linux 中被描述为 0.5–2.4V 可调 regulator，但当 `PMIC_POWER_CONFIG` bit 6 为 0（默认）时，输出实际由外部反馈电阻决定；当 regulator framework 设置电压时，驱动必须设置该 apply bit，才能切换为由内部 voltage selector 控制。补丁同时明确：设备树未指定 voltage constraints 的既有用户不会受影响，因为不会执行电压设置，也不会置位该 bit。

来源：Linux Kernel Mailing List patch，https://lkml.iu.edu/2410.2/03214.html。

### 24.2 Panther DTS 证明该补丁不会在当前板级配置中触发

对照 6.1.65 候选与 6.18.63 Panther DTS 的 `vcc_ddr: DCDC_REG3` 节点，两版一致：

```dts
vcc_ddr: DCDC_REG3 {
    regulator-always-on;
    regulator-boot-on;
    regulator-initial-mode = <0x2>;
    regulator-name = "vcc_ddr";
    regulator-state-mem {
        regulator-on-in-suspend;
    };
};
```

该节点没有 `regulator-min-microvolt`、`regulator-max-microvolt`、`regulator-init-microvolt`，也没有其他显式电压约束。它只声明 always-on、boot-on、initial mode 和 suspend 状态。按补丁自身的触发条件，当前 Panther DTS 不请求 BUCK3 电压设置，因此新增 `.apply_reg/.apply_bit` 不应在本板级配置下触发。

结论：这是 6.18 regulator driver 的真实修复，但不是当前 Panther X2 启动时的预期 PMIC 写入，也不是 SWITCH_REG1/PHY 的控制路径。将其列为 **SOURCE-DIFF / BOARD-DT NOT TRIGGERED**。除非后续修改 DTS 加入 vcc_ddr 电压约束，否则不应把它列为当前 TX 根因，也不需要为本项目单独做实机写寄存器验证。

### 24.3 PMIC_CHIP_VER 0xEE 的手册历史差异

进一步找到 Rockchip RK809 Datasheet Rev 1.01（2018-08）与 Rev 1.7/1.8/2.4 的差异：

| 手册版本 | 0xEE bit[3:0] 定义 |
|---|---|
| Rev 1.01 | `CHIP_VER`，芯片版本编码 1–15，reset value 0x2 |
| Rev 1.7 及之后公开版本 | `RESV`，保留字段，reset value 0x2 |

因此，实测 `0xEE=0x94` 的低 nibble `0x4`：
- 按早期 Rev 1.01 的定义，可以被解读为 CHIP_VER code 4；
- 按 Rev 1.7、1.8、2.4 的定义，则是一个与文档 reset default 不同的 reserved nibble；
- 目前没有 Rockchip 官方 revision history 说明该字段何时、为何从 CHIP_VER 改为 RESV，也没有对 `0x4` 的 silicon/OTP 对照表。

这修正了此前“低 nibble 含义未知”的表述：不是所有历史资料都将其定义为 reserved，而是 **datasheet revision semantics changed / undocumented transition**。仍不能仅凭 0x94 宣称芯片就是 silicon revision 4，也不能判定芯片异常。建议保留实测值，不再重复读取；若需要最终解释，应向 Rockchip/BSP vendor 获取该字段的正式说明。

### 24.4 对 G1 放行与 TX 主线的影响

1. DCDC_REG3 apply_bit 来源和触发条件已查明；当前 Panther DTS 没有 BUCK3 电压约束，因此该差异不应在当前启动流程触发。
2. SWITCH_REG1 descriptor 及其 DT 节点跨版本一致，仍是后续 PHY 供电链的重点；但 provider/consumer 的运行时行为和实际电压尚未验证。
3. PMIC_CHIP_VER 的低 nibble 存在跨版本手册定义变化，不能用 0x94 单独决定 MFD 驱动兼容性。
4. 本项降低了两个疑点对当前 TX 故障的优先级，但不改变 R3.3–R3.5 的 HOLD：MFD probe 仍会执行 IRQ 初始化和 pre-init 写入，regulator probe 仍会注册/处理多路 rail。需继续评估能否将必要网络供电功能与非必要 codec/IRQ 初始化安全分离。
5. 原始 6.1.65 DTB 二进制对照仍未完成；当前 DTS 结论仍是候选源码比较，不得标记为 golden binary PASS。

**本节为公开上游补丁、数据手册与冻结 DTS 的只读审计；未访问设备、未进行 PMIC 事务、未写入介质。**
## 25. 6.18 RK8xx MFD → regulator provider 调用链与放行边界（2026-11-26）

### 25.1 I2C probe 到 MFD core 的顺序

固定源码 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`：

1. `rk8xx_i2c_probe()` 根据 `rockchip,rk809` match data 选择 RK809 variant 与 RK817 regmap config；
2. `devm_regmap_init_i2c()` 建立 regmap；
3. 立即调用 `rk8xx_probe()`；
4. `rk8xx_probe()` 先选择 `rk817_irq_chip` 和完整 `rk817_pre_init_reg[]`；
5. 若无 IRQ，直接 `-EINVAL` 退出；
6. `devm_regmap_add_irq_chip()` 注册 regmap IRQ chip；
7. 逐项执行完整 `rk817_pre_init_reg[]` 的 `regmap_update_bits()`；
8. 最后才 `devm_mfd_add_devices()` 创建所有 RK817/RK809 MFD 子设备。

这意味着：**上游 6.18 的 RK809 MFD probe 没有“先只注册 regulator、以后再做其他初始化”的现成阶段边界。** IRQ 初始化和全部 pre-init 写入发生在 regulator 子设备创建之前；codec 写入不能通过不加载 codec 子驱动来避免。

### 25.2 MFD 子设备不是只有 regulator

`rk817s[]` 会一次性注册：
- `rk808-clkout`
- `rk808-regulator`
- `rk805-pwrkey`
- `rk808-rtc`
- `rk817-codec`
- `rk817-charger`

因此即使 Kconfig 不构建或不加载 codec 子驱动，MFD core 仍然会执行 codec pre-init 表；而 MFD core 仍会要求 IRQ 并建立 regmap IRQ chip。仅通过关闭 codec 子驱动不能达到“仅验证 SWITCH_REG1”的隔离目标。

### 25.3 regulator provider probe 的动作边界

`rk808_regulator_probe()` 会根据 variant 选择完整 `rk809_reg[]`，然后循环调用 `devm_regulator_register()` 注册所有 regulator，而不是只注册 SWITCH_REG1。

对 SWITCH_REG1：
- descriptor 使用 `rk817_switch_ops`；
- 支持 `enable`、`disable`、`is_enabled`；
- `is_enabled` 需要读取 enable 状态寄存器；
- enable/disable 会更新 `RK817_POWER_EN_REG(3)` 中 SWITCH_REG1 对应 bit；
- descriptor 本身没有 voltage selector 或 set_voltage 操作。

本板 DTS 对 SWITCH_REG1 没有 `regulator-always-on`、`regulator-boot-on` 或 voltage constraints。因而单纯 `devm_regulator_register()` 不等于已使能 SWITCH_REG1，也不证明 3.3V 输出存在。

### 25.4 延迟清理是不可忽略的电源副作用

6.18 `drivers/regulator/core.c` 在 DT 系统中默认启用 full constraints，并在约 30 秒后执行 regulator late cleanup。对未标记 always-on、没有 use_count、硬件当前又报告 enabled 且具有 STATUS control 的 regulator，core 会调用 disable。

SWITCH_REG1 descriptor 有 disable 操作，而 Panther DTS 没有 always-on。因此在 PHY consumer 未及时成功获取并 enable 该 supply、或 consumer probe 失败/延迟的情况下，SWITCH_REG1 可能被 late cleanup 关闭。这是**潜在的真实板级供电风险**，不是已经观测到的行为；必须通过正常启动下 regulator summary、consumer probe 日志和时序来验证。不能为了测试而直接添加 `regulator-always-on`，那会改变板级约束并掩盖真实消费者链。

### 25.5 6.1.65 黄金基线对照状态

已完成的黄金对照仍包括：RK809 pre-init 数组逐字节相同、SWITCH_REG1 descriptor 控制定义相同、候选 Panther DTS regulator 子树一致。但本节新梳理的完整 MFD probe 顺序、regulator core late cleanup 时序，尚未用原始 6.1.65 内核源码/镜像运行证据完成逐项绑定。因此本节的调用顺序与 late cleanup 结论标记为 **6.18.63 SOURCE VERIFIED / 6.1.65 GOLDEN COMPARISON PENDING**，不得把它表述为已证明两版完全相同。

### 25.6 对“何时安全放开边界”的结论

当前不能安全启用上游完整 RK809 MFD + regulator stack 来验证 TX。原因不是 RK809 I2C 通信未知（已实机只读通过），而是 stock probe 会组合执行 IRQ 初始化、整组 pre-init 写入、创建全部 MFD 子设备、注册全部 regulator，并可能在延迟清理阶段关闭未被消费者使用的 rail。

可考虑的后续验证路径，按风险从低到高：

1. **只读启动前置证据（不放开 MFD）：** 完成原始 6.1.65 DTB 二进制核对；静态核对 RK809 IRQ GPIO/极性/父中断链；审计 stmmac/PHY consumer 对 `phy-supply` 的实际获取和 enable 顺序；不执行 PMIC 写入。
2. **隔离式 provider 设计评审（不在本轮实现）：** 若上游 MFD 不可安全裁剪，评估独立的、仅暴露 SWITCH_REG1 的临时测试 provider。必须明确其 regmap、IRQ 依赖、enable bit、已有启动状态、失败回滚和 rail-off 风险；不能在未设计回滚前执行 enable/disable。
3. **受控实机 provider/consumer 验证：** 只有在测试内核可回滚、串口/网络之外的恢复通道明确、所有写寄存器清单经过审查、黄金基线对照完成、用户另行授权后，才可进行。首轮仅观察既有状态；后续若必须 enable，单独授权一次明确的 SWITCH_REG1 bit 操作。
4. **放开到 PHY/GMAC：** 先证明 SWITCH_REG1 consumer 成功绑定且不会被 late cleanup 关闭，再验证 PHY reset/clock/interface/delay，最后才进入 DMA/TX descriptor 和真实线缆 TX 验证。

**本节为 6.18.63 固定源码只读调用链审计；未访问实机、未加载驱动、未写 PMIC、未改变 DTB/kernel/config/bootargs 或存储介质。**
## 26. 6.1.65 黄金基线 regulator late-cleanup 与 Rockchip PHY consumer 对照（2026-11-26）

### 26.1 regulator late cleanup：不是 6.18 新增行为

分别检查固定源码端点：
- 6.1.65 候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`；
- 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

两版 `drivers/regulator/core.c` 均：
- 对 populated DT 默认设定 `has_full_constraints = true`；
- 在 `late_initcall_sync(regulator_init_complete)` 中排队延迟工作；
- 延迟时间均为 `msecs_to_jiffies(30000)`；
- 先尝试 resolve pending regulator input supplies，再遍历 regulator 执行 `regulator_late_cleanup()`；
- 对无 `always_on`、`use_count==0`、硬件状态读取为 enabled 且具有 `REGULATOR_CHANGE_STATUS` 操作的 rail 执行 disable。

所以约 30 秒 unused-regulator cleanup 是 6.1.65 黄金候选和 6.18.63 共有的行为，不是 6.18 regression。6.18 新增 `regulator_ignore_unused` 内核参数，可阻止 late cleanup；6.1.65 该固定源码端点未发现此参数。该参数只适合作为独立诊断变量，不能作为正式修复或默认放行条件，因为它会阻止所有 unused regulator cleanup，可能掩盖 supply consumer 绑定错误并留下未使用 rail 常开。

### 26.2 Rockchip GMAC PHY-supply consumer：两版都由 DWMAC glue 管理

两版 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c` 的 `rk_gmac_setup()` 均执行 `devm_regulator_get(dev, "phy")`，对应 GMAC 设备节点的 `phy-supply` 属性。Panther DTS 的 GMAC1 `phy-supply` phandle 指向 RK809 SWITCH_REG1（`vcc_3v3`）。因此 regulator consumer 是 Rockchip GMAC platform glue，不是 RTL8211F PHY driver 自己直接获取 PMIC rail。

### 26.3 发现一个重要的 6.1.65 → 6.18 错误处理差异

6.1.65 `rk_gmac_phy_power_on()` 调用 `regulator_enable()`/`regulator_disable()` 后，虽然记录错误日志，但函数末尾无条件 `return 0`。其调用者 `rk_gmac_powerup()` 检查返回值，因此无法获知 regulator 操作失败；错误可能被吞掉，随后仍继续 `pm_runtime_get_sync()` 和 MAC/PHY 后续初始化。

6.18.63 对应函数改为 `rk_phy_powerup()` 返回 `regulator_enable()` 的真实错误码；`rk_gmac_powerup()` 检查失败并跳转 `clk_disable`，避免把供电失败当作成功继续执行。powerdown 仍为 void helper 并记录 disable 错误。

这是本轮最重要的版本差异：6.18 的错误传播比黄金 6.1.65 更严格，属于正向修复，不应回退。也说明 6.1.65 黄金基线网络曾工作，不能单独证明当时 regulator_enable() 一定成功；SWITCH_REG1 可能在此前已处于 enabled 状态，或者 enable 调用成功但日志未暴露。必须依靠真实运行日志、regulator state/use_count 和后续 PHY 状态来判断。

### 26.4 两版供电调用时序差异

- 6.1.65：`rk_gmac_probe()` 直接调用 `rk_gmac_powerup()`，在调用 `stmmac_dvr_probe()` 之前完成 Rockchip glue 的 clock setup、接口 GRF 配置及 `phy-supply` enable。
- 6.18.63：设置 `plat_dat->init = rk_gmac_init`，由 stmmac platform init callback 调用 `rk_gmac_powerup()`；`stmmac_pltfr_init()` 将 callback 返回值向上传播。Rockchip probe 先建立平台数据/clock，再进入 `devm_stmmac_pltfr_probe()`/STMMAC probe 生命周期。

因此两版的供电动作都发生在 STMMAC 正常网络设备注册完成之前，但调用入口和生命周期管理方式不同。不能只比较 helper 名称或 regulator API，后续需要以实际运行日志核实 6.18 callback 是否执行及错误是否传播。

### 26.5 对 SWITCH_REG1 与 late cleanup 的准确结论

SWITCH_REG1 在 DTS 没有 `always_on`/`boot_on`；正常成功的 GMAC glue `devm_regulator_get("phy")` 取得 consumer handle 后，powerup 成功调用 `regulator_enable()`，会建立 regulator use count，late cleanup 应跳过该 rail。若 GMAC glue 未 probe、consumer get 失败，或 enable 未成功/use_count 仍为 0，而 rail 硬件状态又读为 enabled，则约 30 秒清理可能关闭它。

这一风险在 6.1.65 和 6.18.63 都存在。6.18 更正确地传播 enable 错误，使失败更容易显性化；不能将错误传播视为供电故障本身。

### 26.6 R3 收敛结论与下一阶段边界

**R3 静态审计结论：COMPLETE（STATIC / CONDITIONAL）。R3 实机 provider/consumer 激活：NOT AUTHORIZED / DEFERRED。**

已完成且有证据的内容：RK809 I2C adapter/identity/status RO runtime reads；RK809 pre-init 与 SWITCH_REG1 descriptor 跨版本对照；DCDC_REG3 apply bit 来源与当前 DTS 触发条件；MFD probe 副作用；regulator provider 注册范围；6.1.65/6.18 regulator late cleanup 对照；Rockchip GMAC PHY-supply consumer 获取/使能路径及关键错误处理差异。

尚未完成但不再阻塞 R3 静态审计结项的内容：原始 6.1.65 DTB 二进制与候选 DTS 的最终逐项对照。当前所有 DTS 结论仍按候选源码证据标记，不能称为 golden DTB binary PASS；该核验应在 R7-A 恢复 GMAC/PHY 前作为硬件准入条件完成，不再无限扩大 R3 源码专题。

本次不启用 MFD/regulator、不读写新的 PMIC 寄存器、不执行 regulator enable/disable。R3 不提供运行时 rail/PHY 正常的结论。后续 R4 只进行 MDIO/PHY 框架与 RTL8211F 的静态/Kconfig/对象审计，保持 GMAC/MDIO/PHY 节点 disabled；不得提前 probe。进入 R7-A 前，必须完成黄金 DTB 对照、R3 构建配置决策、测试镜像回滚方案和单独实机授权。

**本节为两版固定源码只读对照；未访问设备、未改变配置、未进行 PMIC/regulator 操作。**