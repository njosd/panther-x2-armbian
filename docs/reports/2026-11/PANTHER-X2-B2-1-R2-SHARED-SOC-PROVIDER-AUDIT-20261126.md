# Panther X2 B2-1 / R2：共享 SoC provider 配置与构建核验（2026-11-26）

## 1. 本阶段目标与结论

R2 的目标是：只补充 GMAC 路径实际需要、且 R0/B1 最终配置中确实缺失的共享 SoC provider。候选重点为 `MFD_SYSCON`、`GPIO_ROCKCHIP`；已经在 B1 启用的时钟、CRU、pinctrl、GPIOLIB、reset、GRF 不得重复加入。

**结论：R2 PASS（零增量复用，无需新增配置或重建）。**

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
| provider 关键 Kconfig 依赖闭合 | PASS | 精确 6.18.63 Kconfig + 最终 .config |
| GPIO Rockchip built-in 对象 | PASS | modules.builtin |
| syscon 与 GPIO 实现符号 | PASS | 同构建 System.map |
| provider 构建 | PASS | R1 Actions build job success |
| GMAC1/MDIO1/PHY 仍隔离 | PASS | R1-VERIFICATION.txt |
| provider 在 Panther 实机 probe | NOT TESTED | R1 硬件节点 disabled |
| 物理 Ethernet TX/RX | NOT TESTED | 仅 R7 进行真实线侧测试 |

**阶段判定：R2 PASS（零增量复用）。** 无新增 Kconfig 符号、无驱动源码修改、无 DTB 修改、无新构建、无设备操作。

## 7. 安全边界与下一阶段

- 本轮只读取 GitHub 仓库、既有 Actions artifact 和固定版本源码；没有访问 Panther X2。
- 没有构建新内核、修改系统、安装软件、改写驱动或设备树。
- 没有写入 SU08G、SN64G 或 eMMC；没有重启或运行设备测试。
- 不启用 GMAC1、MDIO1、RTL8211F；不做网络发送测试。
- 不触碰 Wi-Fi、蓝牙或 USB；此前约定的 USB2.0 旁线验证仍等待后续自然打包节点，不属于 R2。

R2 结束后，下一阶段按计划为 **R3 — PHY 电源 provider（RK809 SWITCH_REG1）**。本报告不自动授权 R3 配置修改、构建或任何设备操作；进入 R3 前仍须先按原计划回读 R3 所需的源码、配置和证据。
