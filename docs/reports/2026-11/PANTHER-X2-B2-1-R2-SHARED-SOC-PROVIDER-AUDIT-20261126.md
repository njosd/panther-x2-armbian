# Panther X2 B2-1 / R2：共享 SoC provider 配置与构建核验（2026-11-26）

## 1. 本阶段目标与结论

R2 的目标是：只补充 GMAC 路径实际需要、且 R0/B1 最终配置中确实缺失的共享 SoC provider。候选重点为 `MFD_SYSCON`、`GPIO_ROCKCHIP`；已经在 B1 启用的时钟、CRU、pinctrl、GPIOLIB、reset、GRF 不得重复加入。

**当前结论：R2 已完成并通过本阶段验收（零增量复用，现有 R1 最终镜像实机只读验证通过）。** 6.1.65 黄金基线的相关最终配置对照已补齐，所比较符号与 6.18.63 均为 y、未发现配置值差异；R1 最终镜像实测 pinctrl 成功绑定、五个 GPIO bank 全部绑定 `rockchip-gpio`，五个 gpiochip 均已注册。6.1.65 精确源码来源仍未达到二进制级绑定，此限制保留，但不影响本阶段对 6.18 默认 provider 功能的实机验收。

对 B1 和 R1 两份真实构建 artifact 的最终 `.config`、built-in 清单和 System.map 进行核验后，确认：
- `MFD_SYSCON=y`、`GPIO_ROCKCHIP=y` 已存在于 B1 最终配置；
- R1 最终配置仍为 `y`，R1 的配置差异没有增加、删除或改写这两个 provider；
- 两者所需的关键依赖 `REGMAP_MMIO`、`GENERIC_IRQ_CHIP`、`GPIOLIB_IRQCHIP`、`OF_GPIO`、`PINMUX`、`GENERIC_PINCONF` 均已为 `y`；
- R1 构建成功，System.map 包含 syscon 与 Rockchip GPIO 实现符号，`modules.builtin` 包含 `kernel/drivers/gpio/gpio-rockchip.ko`；
- Panther GMAC1、MDIO1、RTL8211F PHY 节点仍为 `disabled`。

因此本阶段不应再增加任何 provider 配置。R2 的“缺失 provider”集合为空；不通过人为重复配置制造一个无意义的增量构建。

## 2. 冻结构建证据

### 2.1 B1 基线 artifact

- Actions run：`45309219886`
- Kernel/DTB artifact ID：`14884706818`
- B1 最终 `kernel.config` SHA256：`7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731`
- 源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 版本：Linux `6.18.63`

### 2.2 R1 最终构建 artifact

- Actions run：`45611898629`
- job：`139197305317`（Configure, build and audit R1 network core）
- branch / source revision：`project-a/b2-1-r1-network-core-build` / `5f0ee9b04f2ce7987cdd85170c8235ee29c8116f`
- artifact：`b2-1-r1-network-core`，ID `15023630465`
- artifact ZIP SHA256：`80bd2d33d0e85d8fd4c10fdd33a60c159393db3a45ae5f6e95dd0bf490cc656c`
- R1 最终 `kernel.config` SHA256：`480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`
- Image SHA256：`63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`
- modules archive SHA256：`4f403cac59809616cf4de36a8e89520ecffc13965597be4b8d88845fb3ce3787`
- Panther DTB SHA256：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`
- R1 kernel source commit 与 B1 相同：`aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 工具链：`aarch64-linux-gnu-gcc 13.3.0-6ubuntu2~24.04.1`

R1 build job 的最终配置和模块审计通过；R1 构建没有重写或替换 R0/B1 的共享 SoC provider。

## 3. 最终配置逐项对照

| 配置符号 | B1 最终 .config | R1 最终 .config | R2 判断 |
|---|---:|---:|---|
| `MFD_SYSCON` | y | y | 已存在，无需增加 |
| `GPIO_ROCKCHIP` | y | y | 已存在，无需增加 |
| `REGMAP_MMIO` | y | y | MFD_SYSCON 依赖已满足 |
| `GENERIC_IRQ_CHIP` | y | y | GPIO provider 依赖已满足 |
| `GPIOLIB_IRQCHIP` | y | y | GPIO provider 依赖已满足 |
| `OF_GPIO` | y | y | OF GPIO 依赖已满足 |
| `PINMUX` | y | y | Rockchip pinctrl 依赖已满足 |
| `GENERIC_PINCONF` | y | y | Rockchip pinctrl 依赖已满足 |
| `COMMON_CLK` | y | y | B1 已有，保持不变 |
| `COMMON_CLK_ROCKCHIP` | y | y | B1 已有，保持不变 |
| `CLK_RK3568` | y | y | B1 已有，保持不变 |
| `PINCTRL` | y | y | B1 已有，保持不变 |
| `PINCTRL_ROCKCHIP` | y | y | B1 已有，保持不变 |
| `GPIOLIB` | y | y | B1 已有，保持不变 |
| `RESET_CONTROLLER` | y | y | B1 已有，保持不变 |
| `ROCKCHIP_GRF` | y | y | B1 已有，保持不变 |

上述配置值分别从 artifact 内的实际 `output/kernel.config` 读取；不是从 fragment、Kconfig default 或 `select` 推断。R1 `logs/r1-config-diff.txt` 未显示这些 provider 符号被新增、删除或改写。

## 4. 6.18.63 精确源码依赖核对

源码端点统一为 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

### 4.1 MFD_SYSCON

- `drivers/mfd/Kconfig`：`MFD_SYSCON` 是 bool，select `REGMAP_MMIO`。
- `drivers/mfd/Makefile`：`CONFIG_MFD_SYSCON` 对应 `syscon.o`。
- `drivers/net/ethernet/stmicro/stmmac/Kconfig`：`STMMAC_PLATFORM` 和 `DWMAC_ROCKCHIP` 均 select `MFD_SYSCON`。
- `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`：Rockchip glue 通过 `syscon_regmap_lookup_by_phandle()` 获取 `rockchip,grf`，并在需要时获取 `rockchip,php-grf`。

R1 尚未启用 STMMAC / Rockchip glue，因此该 consumer 尚未运行；但 provider 已在 B1/R1 构建中内建。R5/R6 只需复用，不需 R2 再增加。

### 4.2 GPIO_ROCKCHIP

- `drivers/gpio/Kconfig`：`GPIO_ROCKCHIP` 依赖 `ARCH_ROCKCHIP || COMPILE_TEST`，select `GENERIC_IRQ_CHIP` 和 `GPIOLIB_IRQCHIP`。
- `drivers/gpio/Makefile`：对应对象 `gpio-rockchip.o`。
- Panther DTS 的 GMAC1 节点保留 `snps,reset-gpio = <&gpio3 RK_PA1 GPIO_ACTIVE_LOW>`；既有 6.18.63 依赖审计已确认 STMMAC MDIO reset 路径使用 GPIO descriptor / GPIOLIB。
- R1 artifact 的 `modules.builtin` 明确列出 `kernel/drivers/gpio/gpio-rockchip.ko`；R1 System.map 含 `rockchip_gpio_probe`、`rockchip_gpio_to_irq` 符号。

该 provider 已经以 built-in 形态进入基线，不需要重复启用。

### 4.3 已有共享基础设施

`PINCTRL_ROCKCHIP` 依赖 OF/ARCH_ROCKCHIP，并 select `GPIOLIB`、`PINMUX`、`GENERIC_PINCONF`、`GENERIC_IRQ_CHIP`、`MFD_SYSCON`、`OF_GPIO`；B1/R1 最终配置已满足这些符号。Rockchip clock/CRU、reset controller 和 GRF 也都已在 B1 基线内。

### 4.4 不并入 R2 的依赖

RK809 PHY supply 链（I2C、I2C_RK3X、MFD_RK8XX、MFD_RK8XX_I2C、REGULATOR、REGULATOR_RK808）属于 R3，不因本次 R2 审计而新增、改写或提前测试。

## 5. 构建对象与符号证据

从 R1 artifact 解包核验：

- `output/modules.tar.zst` 中的 `lib/modules/6.18.63+/modules.builtin` 包含 `kernel/drivers/gpio/gpio-rockchip.ko`。
- `output/System.map` 包含：
  - `syscon_regmap_lookup_by_phandle`（全局符号）；
  - `rockchip_gpio_probe`（局部符号）；
  - `rockchip_gpio_to_irq`（局部符号）。
- R1 Actions job 成功完成内核构建、built-in/module 审计及 artifact 上传。

这证明目标构建已包含 provider 实现对象/符号，不只是 Kconfig 显示为 y。它不证明这些 provider 在 Panther 实机上已经 probe 或工作；R1 的 GMAC/MDIO/PHY 节点仍被禁用。

## 6. R2 验收矩阵

| 验收项 | 结果 | 证据边界 |
|---|---|---|
| B1 最终配置中的 MFD_SYSCON | PASS | 实际 .config：y |
| B1 最终配置中的 GPIO_ROCKCHIP | PASS | 实际 .config：y |
| R1 最终配置保留两项 provider | PASS | 实际 .config 与 R1 config diff |
| 6.1.65 黄金基线 provider/关键依赖配置对照 | PASS | 归档 config-6.1.65-ophub 与 modules.builtin；所比符号均为 y |
| provider 关键 Kconfig 依赖闭合 | PASS | 精确 6.18.63 Kconfig + 最终 .config |
| GPIO Rockchip built-in 对象 | PASS | modules.builtin |
| syscon 与 GPIO 实现符号 | PASS | 同构建 System.map |
| provider 构建 | PASS | R1 Actions build job success |
| GMAC1/MDIO1/PHY 仍隔离 | PASS | R1-VERIFICATION.txt |
| Panther 实机 pinctrl probe / main-GRF SYSCON consumer | PASS | R1 最终镜像 `/sys/bus/platform/devices/pinctrl/uevent` 显示 `DRIVER=rockchip-pinctrl`；6.18.63 probe 对 `rockchip,grf` 执行必需的 `syscon_node_to_regmap()` 并检查错误，成功返回证明 main-GRF lookup 成功；PMUGRF 是另一个 optional lookup，不能由该 PASS 自动推定 |
| 五个 GPIO bank 的 platform driver 绑定 | PASS | R1 最终镜像下 gpio0–gpio4 均出现在 `/sys/bus/platform/drivers/rockchip-gpio/`，各自 `uevent` 显示 `DRIVER=rockchip-gpio` |
| 五个 gpiochip 注册 | PASS | `/sys/class/gpio/` 与 `/sys/bus/gpio/devices/` 均列出 gpio0–gpio4；每个 `ngpio=32`，base 分别为 512/544/576/608/640 |
| 物理 Ethernet TX/RX | NOT TESTED | 仅 R7 进行真实线侧测试 |

**阶段判定：R2 PASS / 可评估放行 R3。** 已完成 6.18.63 精确 Kconfig/Makefile 依赖核验、B1/R1 最终配置及 built-in 对象/符号/构建核验、6.1.65 黄金基线配置对照，以及 R1 最终 AF_PACKET probe 镜像上的只读运行时验证。实机证据确认 `rockchip-pinctrl` 成功绑定，且其必需的 main-GRF syscon regmap 获取路径成功；GPIO0–GPIO4 五个 bank 全部绑定 `rockchip-gpio` 并注册为五个 32-line gpiochip。PMUGRF lookup 在该 probe 中属于 optional lookup，返回值未被立即检查，故本项不把 R2 结果解释为 PMUGRF regmap 已成功创建或被实际读写。未写 GPIO、未操作 reset/电源，GMAC1/MDIO1/PHY 仍保持禁用。6.1.65 精确源码构建来源仍未达到二进制级绑定，此历史来源限制如实保留，不将候选源码当作确定来源。

## 7. 安全边界与下一阶段

- 本轮只读取 GitHub 仓库、既有 Actions artifact、固定版本源码，以及 Dropbox 归档的 `kernel-config-evidence.zip`；没有访问 Panther X2。
- 没有构建新内核、修改系统、安装软件、改写驱动或设备树。
- 没有写入 SU08G、SN64G 或 eMMC；没有重启或运行设备测试。
- 不启用 GMAC1、MDIO1、RTL8211F；不做网络发送测试。
- 不触碰 Wi-Fi、蓝牙或 USB；此前约定的 USB2.0 旁线验证仍等待后续自然打包节点，不属于 R2。

**R2 实机验收已完成。** 证据来自用户在现有 R1 最终 AF_PACKET probe 镜像上的只读 sysfs 检查；期间没有重建、刷写或改变 GPIO/电源/reset 状态。GMAC1/MDIO1/PHY 继续关闭。R2 已具备进入 R3 放行评估的证据；是否开始 R3 仍按总路线图及实施计划的顺序执行。


## 8. 2026-11-26 黄金基线对照补充与未决项

### 8.1 第一黄金基线 6.1.65：最终配置与 built-in 对象对照

已从 Dropbox 归档文件 `/kernel-config-evidence.zip` 读取 `config-6.1.65-ophub` 与 `modules.builtin`。这是用户此前上传并归档的原始 6.1.65 配置证据，不需要重新提取整个 IMG。以下逐项与本报告 §3 中已从 6.18.63 B1/R1 artifact 的实际最终 `output/kernel.config` 读取的值对照：

| 配置/依赖 | 6.1.65 原始 config | 6.18.63 B1/R1 final config | 对照结果 |
|---|---:|---:|---|
| `MFD_SYSCON` | y | y | 相同 |
| `GPIO_ROCKCHIP` | y | y | 相同 |
| `REGMAP_MMIO` | y | y | 相同 |
| `GENERIC_IRQ_CHIP` | y | y | 相同 |
| `GPIOLIB_IRQCHIP` | y | y | 相同 |
| `OF_GPIO` | y | y | 相同 |
| `PINMUX` | y | y | 相同 |
| `GENERIC_PINCONF` | y | y | 相同 |
| `COMMON_CLK` | y | y | 相同 |
| `COMMON_CLK_ROCKCHIP` | y | y | 相同 |
| `CLK_RK3568` | y | y | 相同 |
| `PINCTRL` | y | y | 相同 |
| `PINCTRL_ROCKCHIP` | y | y | 相同 |
| `GPIOLIB` | y | y | 相同 |
| `RESET_CONTROLLER` | y | y | 相同 |
| `ROCKCHIP_GRF` | y | y | 相同 |
| `ARCH_ROCKCHIP` / `OF` | y / y | y / y | 相同 |

6.1.65 `modules.builtin` 还列出 `kernel/drivers/pinctrl/pinctrl-rockchip.ko`、`kernel/drivers/gpio/gpio-rockchip.ko` 与 `kernel/drivers/gpio/gpio-syscon.ko`，证明这些对象编译进黄金基线内核。`MFD_SYSCON` 在 config 中为 y；本轮不把 `modules.builtin` 中未列出独立 syscon 对象解释为功能缺失。

**本轮静态配置结论：** 对 R2 涉及的 provider 与关键依赖，6.1.65 与 6.18.63 的配置值完全一致；没有需要回移的配置差异。按用户原则保留 6.18 默认配置，不增加 Kconfig、不修改源码、不重建。

**实现来源限制：** 6.1.65 原始 Kernel 的精确上游构建 commit 尚未实现二进制级绑定；当前候选源码只能作为参考样本，不能冒充 6.1.65 Image 的确定构建源码。因此不能仅凭候选源码宣称两个版本实现完全相同。6.1.65 的整机有线网络成功是实际功能正向证据，但不等于 GPIO/SYSCON 每个 provider 的独立单项测试。

### 8.2 当前 6.18 默认配置结论

6.18.63 的 MFD_SYSCON、GPIO_ROCKCHIP 与依赖闭包已在 B1/R1 最终 `.config` 和实际构建产物中确认存在；与 6.1.65 对照未发现配置值差异。当前没有证据要求回移配置，也没有理由制造配置增量。保留 6.18 默认实现。

### 8.3 R2 实机只读验证范围

下一轮仅使用现有已启动 R1 镜像进行只读检查：`rockchip-pinctrl` platform driver 是否绑定；GPIO bank 子设备是否由 `gpio-rockchip` 绑定并注册 gpiochip；以及对应 probe/错误日志。源码已确认 Panther X2 pinctrl 节点带有 `rockchip,grf` / `rockchip,pmu` phandle，6.18.63 `pinctrl-rockchip` probe 调用 `syscon_node_to_regmap()` 获取对应 regmap，并通过 `of_platform_populate()` 创建 GPIO bank 子设备。因此 pinctrl 成功 probe 可作为 MFD_SYSCON 的实际 consumer 证据，GPIO bank bind/gpiochip 可作为 GPIO provider 注册证据。

不得写 GPIO、读取未文档化 MMIO、触发 reset/power、启用 GMAC/MDIO/PHY 或更改设备状态。

R1 中 GMAC/MDIO/PHY 节点保持 disabled，因此 GMAC consumer 对 GRF/reset GPIO 的独立 phandle 获取和调用无法在 R2 直接验证；这部分留到 R7-A/R7-C。它不妨碍 R2 通过 pinctrl 这一现存 consumer 验证 SYSCON 的基本功能。

### 8.4 已确认的 6.18 运行时 consumer 路径

- `rk3566-panther-x2.dts` 的 RK3566 pinctrl node 引用 `rockchip,grf = <&grf>` 与 `rockchip,pmu = <&pmugrf>`。
- `pinctrl-rockchip.c` 的 `rockchip_pinctrl_probe()` 调用 `syscon_node_to_regmap()` 获取 GRF regmap，并调用 `syscon_regmap_lookup_by_phandle_optional()` 处理可选 IOC phandle；probe 成功说明该 consumer 实际通过 syscon API 获得所需 regmap。
- `rockchip_pinctrl_probe()` 随后调用 `of_platform_populate()` 注册 GPIO bank 子设备；`gpio-rockchip.o`（构建对象名）对应 platform driver 名称为 `rockchip-gpio`；检查 `/sys/bus/platform/drivers/rockchip-gpio/` 下 GPIO bank 设备链接，并在 `/sys/class/gpio/` 确认 gpiochip 注册，可验证 GPIO provider 的运行时注册。
- 上述路径均可通过 sysfs 和 dmesg 只读观察，不需要写 GPIO、MMIO 或 PMIC 寄存器。

### 8.5 R1 最终 AF_PACKET probe 镜像的只读检查工具约束

当前 R2 实机检查使用的不是早期 R1 镜像，而是最终专用 AF_PACKET probe 镜像：Actions run `45750601995`，artifact `15084948644`。该镜像复用冻结的 R1 `Image`/DTB，并使用专用 RAM initramfs；`/init` 先挂载 procfs/sysfs，执行修正后的 AF_PACKET probe，再进入交互式 `/bin/sh`。

该 initramfs 的 BusyBox 构建/打包脚本仅创建 `ash`、`sh`、`mount`、`mkdir`、`cat`、`uname`、`printf` applet 链接；明确禁止依赖 `[`/`test`。因此后续检查不得使用 `echo`、`[`、`test`、`ls`、`grep`、`dmesg`、`readlink` 等未包含 applet。使用 `printf` 输出标题，使用 `cat` 读取已知 sysfs 文件，并利用 shell pathname expansion 枚举设备/driver 链接。

此前尝试的通用 BusyBox 检查脚本因调用未包含的 applet 而未执行；其输出不构成任何 GPIO/SYSCON 正反证据，也未改变设备状态。

### 8.6 R1 最终 AF_PACKET probe 镜像：R2 运行时验收结果（2026-11-26）

**镜像身份：** 用户确认当前启动的是 R1 最后一次专用 AF_PACKET probe 验证镜像，而非早期 R1 镜像。对应 Actions run `45750601995`，artifact ID `15084948644`。本次仅读取已有 sysfs 内容。

**pinctrl：** `/sys/bus/platform/drivers/rockchip-pinctrl/pinctrl/uevent` 与 `/sys/bus/platform/devices/pinctrl/uevent` 均显示 `DRIVER=rockchip-pinctrl`、`OF_COMPATIBLE_0=rockchip,rk3568-pinctrl`、`OF_FULLNAME=/pinctrl`，确认驱动已绑定。

**SYSCON consumer：** 精确 6.18.63 源码 `drivers/pinctrl/pinctrl-rockchip.c` 的 `rockchip_pinctrl_probe()` 对 `rockchip,grf` phandle 调用 `syscon_node_to_regmap()`，并对返回值执行 `IS_ERR()` 检查；因此 pinctrl 成功绑定证明必需的 main-GRF lookup 成功。对 `rockchip,pmu` 则调用 `syscon_regmap_lookup_by_phandle_optional()`，但该赋值结果在 probe 中没有紧接着做 `IS_ERR()` 检查；成功绑定本身不能证明 PMUGRF lookup 成功。Panther X2 RK356x DTS 的 pinctrl 节点确实同时声明 `rockchip,grf = <&grf>` 和 `rockchip,pmu = <&pmugrf>`，但 R2 没有直接验证 PMUGRF regmap 的可用性，也没有对 PMUGRF 执行读写。五个 GPIO bank 绑定和 gpiochip 注册仍是有效证据，但不补足该缺口。此项不代表 GMAC consumer 已测试。

**GPIO bank：** `/sys/bus/platform/drivers/rockchip-gpio/` 实际列出 `fdd60000.gpio`、`fe740000.gpio`、`fe750000.gpio`、`fe760000.gpio`、`fe770000.gpio`；五个 `uevent` 均显示 `DRIVER=rockchip-gpio`、`OF_COMPATIBLE_0=rockchip,gpio-bank`，alias 分别为 gpio0–gpio4。

**gpiochip：** `/sys/class/gpio/` 显示五个 chip：gpio0 base 512、gpio1 base 544、gpio2 base 576、gpio3 base 608、gpio4 base 640；每个 `ngpio=32`。`/sys/bus/gpio/devices/gpiochip0` 至 `gpiochip4` 均显示 `DEVTYPE=gpio_chip`，OF_FULLNAME 与对应 GPIO bank 地址一致。

**功能证据边界：** 本次证明 pinctrl/SYSCON consumer probe、GPIO bank driver bind 和 gpiochip 注册成功；没有执行 GPIO line 读写/中断测试，没有验证 GMAC reset GPIO consumer，也没有验证 GMAC/MDIO/PHY。上述后续功能仍留在其原定阶段，不得把本次 R2 PASS 扩大解释。

**操作边界：** 检查为只读 sysfs 查询；没有写 GPIO、MMIO、reset 或电源，没有启用 GMAC/MDIO/PHY，没有重建或重刷。

### 8.7 2026-11-27 源码复核：PMUGRF 证据边界纠正

对固定源码 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9` 重新逐函数核对后，修正 §6 与 §8.6 中可能过宽的解释：

- `drivers/pinctrl/pinctrl-rockchip.c`：`rockchip_pinctrl_probe()` 对 `rockchip,grf` 调用 `syscon_node_to_regmap()`，并在返回 `ERR_PTR` 时直接失败；对 `rockchip,pmu` 调用 `syscon_regmap_lookup_by_phandle_optional()`，但该返回值没有在 probe 中立即进行 `IS_ERR()` 检查。
- 因此，R2 的 pinctrl 成功绑定确证 main-GRF lookup 成功；不能单凭 pinctrl bind 推定 PMUGRF lookup 成功。RK3568 GPIO0 的后续 IOMUX/pull/drive/schmitt 操作会使用 `info->regmap_pmu`，但 R2 没有执行这些 PMUGRF 功能读写。
- `arch/arm64/boot/dts/rockchip/rk356x-base.dtsi` 定义 `pmugrf: syscon@fdc20000`，compatible 为 `rockchip,rk3568-pmugrf`, `syscon`, `simple-mfd`；子节点 `io-domains` compatible 为 `rockchip,rk3568-pmu-io-voltage-domain`。Panther X2 DTS 将该子节点 status 设为 okay。
- `drivers/mfd/syscon.c` 中 `syscon_node_to_regmap()` 会检查 syscon 节点是否带通用 compatible `syscon`；若 syscon list 中尚无该节点且允许创建，则调用 `of_syscon_register()`，通过 `of_iomap()` 建立映射并调用 `regmap_init_mmio()`，把 regmap 存入内部 list。该机制不要求存在一个名为 `syscon` 的 platform driver。因此 platform-device 目录没有 `driver` symlink，不能用于判断 regmap 是否注册。
- `drivers/soc/rockchip/io-domain.c` 的 RK3568 IO-domain probe 先对父节点调用 `syscon_node_to_regmap(parent->of_node)`；之后逐项获取 regulator、读取软件电压，并对成功获取的供电调用 `iod->write()`。RK3568 的 VCCIO5/index 6 会写 PMU GRF VSEL0/VSEL1。因此 IO-domain child 是否 bind 是关键状态，不能从父 syscon device 的 `waiting_for_supplier=0` 推断。

**纠正后的证据等级：** PMUGRF 设备树身份已验证；syscon API 的懒创建机制已由源码确认；R2 main-GRF syscon consumer PASS；PMUGRF lookup 是否成功、当前 PMUGRF regmap 是否已建立、IO-domain child 是否 bind，均仍 UNKNOWN。G4-P 保持 NO-GO，不授权 probe 或 selector 写入。
