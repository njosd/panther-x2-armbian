# Panther X2 B2-0：Linux 6.18.63 精确源码 Kconfig / Makefile 依赖审计（2026-11-24）

## 1. 审计对象与边界

本报告完成 B2-0 组件源码差异账本中尚未结项的 6.18.63 Kconfig / Makefile 静态依赖审计。

**6.18.63 精确源码快照：**
- Repository：`ophub/linux-6.18.y`
- Commit：`aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 根目录 Makefile：`VERSION=6`、`PATCHLEVEL=18`、`SUBLEVEL=63`

用于版本差异比较的两个历史源码端点：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。这是本次源码文件对照端点，不将其误写成已由原始 build log 闭环的安装包源码身份。
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。

只读检查 Kconfig、Makefile、Panther X2 DTS 及相关驱动源码调用点。没有运行 Kconfig/build，没有生成 .config，没有修改源码，没有制作补丁，没有访问 Panther X2，也没有执行设备、MDIO、寄存器或网络测试。

本报告只审查 Panther X2 实际板载 GMAC1、RGMII、外置 RTL8211F 及其时钟、复位、GPIO、PHY 电源提供链。Linux 网络核心内部实现留给 B2-1；STMMAC/DWMAC4 DMA 行为留给 B2-2；Rockchip glue/CCF/CRU 代码行为留给 B2-3；MDIO/PHYLIB/PHYLINK/RTL8211F 运行逻辑留给 B2-4。这里仅记录它们在 Kconfig/Makefile 中的接入和依赖关系，不重复上述专题已经完成的代码行为审计。

## 2. Panther X2 DTS 锁定的实际硬件资源

6.18.63 同一源码树中的 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts` 对 GMAC1 给出：

- `compatible` 命中 `rockchip,rk3568-gmac`；
- `phy-mode = "rgmii"`；
- `phy-handle = <&rgmii_phy1>`，MDIO PHY address 0；
- 外置 PHY 的 `phy-supply = <&vcc_3v3>`；
- `snps,reset-gpio = <&gpio3 RK_PA1 GPIO_ACTIVE_LOW>`；
- RGMII pinctrl groups；
- `clock_in_out = "input"`，以及 CRU / 125MHz external fixed-clock assignments。

另外，`vcc_3v3` 并非 `regulator-fixed`：它是 DTS 中 RK809 PMIC 的 `SWITCH_REG1` regulator。故 GMAC PHY 电源依赖实际 RK809 PMIC provider 链，而不能只因板上存在固定电源 regulator 就认为 supply 链已满足。

## 3. Kconfig 顶层门控：网络设备到 Rockchip GMAC

6.18.63 的实际 Kconfig 包含关系为：

```text
NET
└─ NETDEVICES                    depends on NET
   └─ ETHERNET                   depends on NET
      └─ NET_VENDOR_STMICRO     default y; depends on HAS_IOMEM
         └─ STMMAC_ETH
            └─ STMMAC_PLATFORM
               └─ DWMAC_ROCKCHIP
```

精确条件：
- `NETDEVICES` 位于 `drivers/net/Kconfig`，`depends on NET`。
- `drivers/net/Kconfig` 在 `if NETDEVICES` 环境下 source Ethernet、PHY、MDIO、PCS 等 Kconfig。因此 6.18.63 的 `PHYLINK` / `PHYLIB` 不再重复写 `depends on NETDEVICES`，并不表示它们脱离 NETDEVICES 门控。
- `ETHERNET` 位于 `drivers/net/ethernet/Kconfig`，`depends on NET`、`default y`。
- `NET_VENDOR_STMICRO` 位于 `drivers/net/ethernet/stmicro/Kconfig`，`depends on HAS_IOMEM`、`default y`。
- `STMMAC_ETH` 位于 `drivers/net/ethernet/stmicro/stmmac/Kconfig`，要求 `HAS_IOMEM && HAS_DMA`、`PTP_1588_CLOCK_OPTIONAL` 和 **`ETHTOOL_NETLINK`**。
- `STMMAC_PLATFORM` 在 `if STMMAC_ETH` 内，默认 y，并 select `MFD_SYSCON`。
- `DWMAC_ROCKCHIP` 在 `if STMMAC_PLATFORM` 内，默认 `ARCH_ROCKCHIP`，要求 `OF && (ARCH_ROCKCHIP || COMPILE_TEST)`，并 select `MFD_SYSCON` 与 `PCS_XPCS_ROCKCHIP`。

**6.18.63 新增的配置门槛：** 相比 6.1.116 / 6.12.81，`STMMAC_ETH` 新增 `depends on ETHTOOL_NETLINK`。因此未来 B2 网络配置若未满足 `ETHTOOL_NETLINK`，STMMAC 主驱动不能通过 Kconfig 正常启用。该项必须进入最终配置核验清单，不能把它误判为驱动源码缺失。

## 4. STMMAC / DWMAC4 / Rockchip glue 的 Makefile 对象闭包

6.18.63 Makefile 映射：

| Kconfig 符号 | Makefile 输出 | 实际作用 |
|---|---|---|
| `CONFIG_STMMAC_ETH` | `stmmac.o` | STMMAC core 聚合对象 |
| `CONFIG_STMMAC_PLATFORM` | `stmmac-platform.o` | platform bus wrapper |
| `CONFIG_DWMAC_ROCKCHIP` | `dwmac-rk.o` | Rockchip SoC glue |
| `CONFIG_DWMAC_GENERIC` | `dwmac-generic.o` | generic fallback，不是 Panther 专用 glue |

6.18.63 的 `stmmac.o` 静态对象列表包括：
- `stmmac_main.o`、`stmmac_ethtool.o`、`stmmac_mdio.o`；
- `ring_mode.o`、`chain_mode.o`、`dwmac_lib.o`；
- `dwmac1000_*`、`dwmac100_*`；
- `dwmac4_descs.o`、`dwmac4_dma.o`、`dwmac4_lib.o`、`dwmac4_core.o`、`dwmac5.o`、`hwif.o`；
- `dwxgmac2_*`；
- `stmmac_tc.o`、`stmmac_xdp.o`、`stmmac_est.o`、`stmmac_fpe.o`、`stmmac_vlan.o`、`stmmac_pcs.o`。

由此明确：
1. DWMAC4 DMA / descriptor / core 并不是一个单独由 `CONFIG_DWMAC4` 控制的可替换模块；它们随 `CONFIG_STMMAC_ETH` 聚合进 `stmmac.o`。
2. Rockchip glue 是另一个独立对象 `dwmac-rk.o`，由 `CONFIG_DWMAC_ROCKCHIP` 控制。
3. Platform wrapper `stmmac-platform.o` 由 `CONFIG_STMMAC_PLATFORM` 控制。
4. `DWMAC_GENERIC` 是通用 fallback 对象；Panther 的 `rockchip,rk3568-gmac` 实际专用匹配路径仍是 Rockchip glue。不能把 generic fallback 对象当成 Panther 的实际驱动。
5. 6.18.63 的 Makefile 将 generic driver 排在 Rockchip 等专用 glue 之后，文件注释明确指出 generic driver 必须最后。

## 5. PHYLINK / PHYLIB / MDIO / RTL8211F 依赖闭包

### 5.1 Kconfig 选择关系

```text
STMMAC_ETH
├─ select PHYLINK
│  └─ select PHYLIB
│     └─ select MDIO_BUS
└─ select PCS_XPCS
   └─ select PHYLINK

REALTEK_PHY 位于 if PHYLIB 内
OF_MDIO = def_tristate OF
└─ select FIXED_PHY
```

- `STMMAC_ETH` 选择 `PHYLINK`。
- `PHYLINK` 选择 `PHYLIB` 与 `SWPHY`。
- 6.18.63 的 `PHYLIB` 选择 `MDIO_BUS`。
- `OF_MDIO` 在 6.18.63 改为 `def_tristate OF`，并 select `FIXED_PHY`。
- `REALTEK_PHY` 位于 `if PHYLIB` 内，但没有被 `DWMAC_ROCKCHIP` 自动 select。要支持板载 RTL8211F，**`CONFIG_REALTEK_PHY` 必须由最终配置明确启用**。
- `stmmac_mdio.c` 使用 `of_mdiobus_register()`；`drivers/net/mdio/Makefile` 将 `CONFIG_OF_MDIO` 映射为 `of_mdio.o`。

`OF_MDIO` 自动选择 `FIXED_PHY` 是 Kconfig 编译闭包，不代表 Panther 使用 fixed PHY。Panther DTS 明确使用真实外置 RTL8211F 和 `phy-handle`。

### 5.2 6.18.63 Realtek PHY 对象布局

6.1.116 / 6.12.81：
- `drivers/net/phy/Makefile` 直接以 `CONFIG_REALTEK_PHY` 构建 `realtek.o`。

6.18.63：
- `drivers/net/phy/Makefile` 改为 `obj-$(CONFIG_REALTEK_PHY) += realtek/`；
- `drivers/net/phy/realtek/Makefile` 将 `realtek_main.o` 聚合为 `realtek.o`；
- 可选 `CONFIG_REALTEK_PHY_HWMON` 才额外加入 `realtek_hwmon.o`。

这属于源码目录与对象聚合方式调整，不代表 RTL8211F PHY 驱动被删除。基础 RTL8211F 驱动仍由 `CONFIG_REALTEK_PHY` 控制；HWMON 是可选附加项，不是普通 PHY attach / RGMII 数据路径的必要条件。

## 6. PCS_XPCS 的编译依赖与 Panther RGMII 运行路径必须分开

6.18.63：
- `STMMAC_ETH` select `PCS_XPCS`；
- `DWMAC_ROCKCHIP` 新增 select `PCS_XPCS_ROCKCHIP`；
- `PCS_XPCS_ROCKCHIP` 位于 `if PCS_XPCS` 内，要求 `OF && (ARCH_ROCKCHIP || COMPILE_TEST)`，并 select `GENERIC_PHY` 与 `PM_GENERIC_DOMAINS if PM`；
- Makefile 对应 `pcs_xpcs.o`、`pcs-xpcs-rk.o`。

因此，即使 Panther 使用 RGMII，6.18.63 的 Kconfig 仍会把 Rockchip XPCS 支持纳入编译闭包。但这不等于 Panther 会 probe 或使用 XPCS：
- Panther DTS 是外置 RTL8211F + RGMII；
- 已完成的 6.18.63 Panther 资源命中审计没有发现 SGMII/QSGMII/PCS runtime 资源；
- 本次新增的 PCS_XPCS_ROCKCHIP 是**编译依赖**，不是 Panther 当前 RGMII 数据路径的运行依赖。

不得因为它被 select 就把 Panther 改判成 SGMII，也不得把 XPCS runtime driver 当作当前 TX 根因候选。

## 7. Rockchip 时钟、CRU reset、GRF、pinctrl 与 GPIO 配置链

### 7.1 时钟与 CRU reset

6.18.63：
- `COMMON_CLK_ROCKCHIP`：依赖 `ARCH_ROCKCHIP || COMPILE_TEST`，默认 `ARCH_ROCKCHIP`；
- `CLK_RK3568`：依赖 `ARM64 || COMPILE_TEST`，默认 y；
- `drivers/clk/rockchip/Makefile`：
  - `CONFIG_COMMON_CLK_ROCKCHIP` → `clk-rockchip.o`；
  - `CONFIG_CLK_RK3568` → `clk-rk3568.o`；
  - `CONFIG_RESET_CONTROLLER` → 将 `softrst.o` 纳入 `clk-rockchip.o`。
- `STMMAC_ETH` select `RESET_CONTROLLER`。

因此，在 Rockchip common clock provider 正常纳入构建的前提下，STMMAC 的 reset framework 选择会使 CRU soft-reset 实现 `softrst.o` 进入 clock composite。它不是一个单独名为 `RESET_ROCKCHIP` 的驱动选项。

### 7.2 GRF / syscon

- `DWMAC_ROCKCHIP` 和 `STMMAC_PLATFORM` 都 select `MFD_SYSCON`；
- `ROCKCHIP_GRF` 在 6.18.63 为 bool，`default y if ARCH_ROCKCHIP`；
- `drivers/soc/rockchip/Makefile`：`CONFIG_ROCKCHIP_GRF` → `grf.o`。

注意：`MFD_SYSCON` 是驱动选择的 syscon 框架；`ROCKCHIP_GRF` 是 Rockchip GRF provider。二者不是同一个配置符号。Kconfig default 不代替最终 .config 验证。

### 7.3 pinctrl / GPIO

- `PINCTRL_ROCKCHIP` 依赖 `ARCH_ROCKCHIP || COMPILE_TEST` 和 `OF`，select `GPIOLIB`、`PINMUX`、`GENERIC_PINCONF`、`GENERIC_IRQ_CHIP`、`MFD_SYSCON`、`OF_GPIO`，默认 `ARCH_ROCKCHIP`；Makefile → `pinctrl-rockchip.o`。
- `GPIO_ROCKCHIP` 依赖 `ARCH_ROCKCHIP || COMPILE_TEST)，select `GENERIC_IRQ_CHIP`、`GPIOLIB_IRQCHIP`，默认 `ARCH_ROCKCHIP`；Makefile → `gpio-rockchip.o`。
- Panther DTS 的 `pinctrl-0` 依赖 Rockchip pinctrl provider；`gpio3 RK_PA1` 依赖 GPIO provider。
- `stmmac_mdio.c` 对 `snps,reset-gpio` 使用 `devm_gpiod_get_optional()`。

**重要区分：** Panther PHY reset GPIO 走 GPIO descriptor / GPIOLIB 路径，不是通过通用 `RESET_GPIO` reset-controller driver；也不能把它与 GMAC CRU 的 `RESET_CONTROLLER` / `softrst.o` 混为一谈。

## 8. PHY supply 的外部 provider 依赖：RK809 PMIC

驱动源码 `dwmac-rk.c`：
- 通过 `devm_regulator_get(dev, "phy")` 获取 PHY regulator；
- 通过 `regulator_enable()` / `regulator_disable()` 管理供电。

Panther DTS：
- GMAC1 设置 `phy-supply = <&vcc_3v3>`；
- `vcc_3v3` 定义在 RK809 PMIC 的 `SWITCH_REG1` regulator 节点中。

6.18.63 对应的 provider Kconfig / Makefile 链：

```text
I2C + OF
└─ MFD_RK8XX_I2C
   ├─ select MFD_CORE
   ├─ select REGMAP_I2C
   ├─ select REGMAP_IRQ
   └─ select MFD_RK8XX
      └─ MFD_RK8XX core

REGULATOR
└─ REGULATOR_RK808
   └─ depends on MFD_RK8XX

I2C_RK3X
└─ Rockchip RK3xxx I2C controller
```

Makefile：
- `CONFIG_MFD_RK8XX` → `rk8xx-core.o`；
- `CONFIG_MFD_RK8XX_I2C` → `rk8xx-i2c.o`；
- `CONFIG_REGULATOR_RK808` → `rk808-regulator.o`；
- `CONFIG_I2C_RK3X` → `i2c-rk3x.o`。

**这一条不是 DWMAC Kconfig 自动选择出来的。** `DWMAC_ROCKCHIP` 没有 select `REGULATOR`、`REGULATOR_RK808`、`MFD_RK8XX_I2C` 或 `I2C_RK3X`。它们是 Panther DTS 实际 supply provider 的独立依赖，未来 B2 配置复合时必须显式纳入并逐项检查。只启用 STMMAC / DWMAC / PHYLIB 并不能证明 `vcc_3v3` supply 链已经闭合。

## 9. 6.1.116 / 6.12.81 / 6.18.63 Kconfig 与 Makefile 差异账本

| 组件 | 6.1.116 | 6.12.81 | 6.18.63 | 判断 |
|---|---|---|---|---|
| STMMAC 顶层依赖 | HAS_IOMEM/HAS_DMA、PTP optional | 同 6.1 | 新增 `ETHTOOL_NETLINK` 依赖 | 6.18 配置门槛新增，必须满足 |
| STMMAC select | MII、PCS_XPCS、PAGE_POOL、PHYLINK、CRC32、RESET_CONTROLLER | 同 6.1 | 另 select `NET_DEVLINK` | 新增编译依赖，不等于 TX 行为回归 |
| STMMAC_PLATFORM | 显式 depends STMMAC_ETH；select MFD_SYSCON | 同 6.1 | 位于 `if STMMAC_ETH` 内，无重复 depends；select MFD_SYSCON | 语义等价的 Kconfig 嵌套重排 |
| Rockchip glue Kconfig | DWMAC_ROCKCHIP select MFD_SYSCON | 同 6.1，另有 TOOL | 新增 select PCS_XPCS_ROCKCHIP | 6.18 新增 PCS 编译依赖；RGMII 不使用其 runtime |
| Rockchip glue Makefile | `dwmac-rk.o` | `dwmac-rockchip.o` composite，内部 `dwmac-rk.o` + 可选 `dwmac-rk-tool.o` | 恢复 `dwmac-rk.o` 直接对象 | 6.12 对象包装与工具拆分为 vendor fork 差异 |
| STMMAC 功能裁剪 | 主要 core 对象静态列出 | `STMMAC_FULL` / `STMMAC_ETHTOOL` / `STMMAC_UIO` 等 vendor 选项控制部分对象 | 回到静态完整对象列表；无上述 mini-kernel 选项 | 不能把 6.12 专有裁剪符号带入 6.18 配置 |
| Rockchip 工具 | 无 `DWMAC_ROCKCHIP_TOOL` | 有 PHY/MAC loopback、RGMII delayline scan 工具对象 | 无该符号及 `dwmac-rk-tool.o` | 诊断工具能力差异；不是普通 TX 主路径缺失 |
| MDIO bus Kconfig | `MDIO_DEVICE` / `MDIO_DEVRES` 分层；PHYLIB select 二者 | 同 6.1 | 合并为 `MDIO_BUS`；PHYLIB select MDIO_BUS | 6.18 MDIO 基础设施 Kconfig 重构 |
| MDIO Makefile | `MDIO_DEVICE` / `MDIO_DEVRES` 条件构建 bus/devres | 同 6.1 | `MDIO_BUS` 构建 `mdio-bus.o`；PHYLIB 构建 `mdio_devres.o` | 代码对象归属变化，功能闭包仍在 |
| OF_MDIO | def_tristate PHYLIB，depends OF/PHYLIB | 同 6.1 | def_tristate OF，select FIXED_PHY | 6.18 放宽为 OF accessor 独立构建；Panther 仍由 PHYLIB 提供真实 PHY |
| Realtek PHY Makefile | root `realtek.o` | root `realtek.o` | `realtek/` 子目录聚合 `realtek_main.o`，HWMON 可选 | 目录与对象布局调整，RTL8211F driver 仍在 |
| Rockchip common clock Kconfig | COMMON_CLK_ROCKCHIP bool；CLK_RK3568 bool，ARM64 gate | COMMON_CLK_ROCKCHIP tristate；CLK_RK3568 tristate，CPU_RK3568 gate | 两者恢复 bool；CLK_RK3568 ARM64 gate | 6.12 vendor fork 的 tristate / CPU gate 与 6.18 不同 |
| Rockchip GRF | bool，default y if ARCH_ROCKCHIP | tristate，无同样 default | bool，default y if ARCH_ROCKCHIP | 6.12 必须核实实际 .config 是否显式启用 |
| Rockchip pinctrl / GPIO | PINCTRL_ROCKCHIP、GPIO_ROCKCHIP 默认 ARCH_ROCKCHIP | 同 | 同 | 未发现会改变 Panther GPIO/pinctrl Kconfig 链的差异 |
| PHY supply PMIC | MFD_RK808 → REGULATOR_RK808 | 保留 MFD_RK808，同时增加 RK8xx core/I2C 分层 | MFD_RK8XX_I2C → MFD_RK8XX → REGULATOR_RK808 | 6.18 PMIC provider 的 Kconfig 核心依赖已迁移 |
| CRU reset Makefile | RESET_CONTROLLER 条件加入 `softrst.o` | 同 | 同 | 与 STMMAC select RESET_CONTROLLER 的闭包保持连接 |

### 9.1 特别需要防止的错误推断

1. 6.18 新增 `ETHTOOL_NETLINK` 依赖，不等于 6.18 的 TX 数据路径一定有变化；它是 STMMAC 的 Kconfig gate。
2. 6.18 新增 `PCS_XPCS_ROCKCHIP` select，不等于 Panther RGMII 需要启动 XPCS。
3. 6.12 的 `DWMAC_ROCKCHIP_TOOL` 不能假定存在于 6.18；6.18 Makefile 已没有该对象。
4. 6.12 的 `ROCKCHIP_GRF` 是 tristate 且没有 6.1/6.18 那样的默认 y；不能只凭 `ARCH_ROCKCHIP` 推断 6.12 实际配置必然包含 GRF。
5. 6.18 的 `REGULATOR_RK808` 依赖 MFD_RK8XX，而不是沿用旧版 `MFD_RK808` 作为直接依赖；不能把 6.1/6.12 的 PMIC Kconfig 依赖树原样复制到 6.18。
6. PHY reset GPIO 和 GMAC CRU reset 是两条不同的依赖路径。
7. Kconfig default、select、depends 和 DTS runtime provider 是不同关系；必须分别记录，不能将“默认 y”写成“由 GMAC 自动 select”。

## 10. B2 配置复合时的静态核验清单（本报告不执行配置修改）

以下只是依赖核验清单，不是授权启用配置，也不是当前 .config 的实测结果。

### GMAC / STMMAC 主链
- `NET`、`NETDEVICES`、`ETHERNET`、`NET_VENDOR_STMICRO`
- `STMMAC_ETH`、`STMMAC_PLATFORM`、`DWMAC_ROCKCHIP`
- `ETHTOOL_NETLINK`、`PTP_1588_CLOCK_OPTIONAL`、架构提供的 `HAS_IOMEM` / `HAS_DMA`

### PHY / MDIO
- `PHYLINK`、`PHYLIB`、`MDIO_BUS`、`OF_MDIO`
- **`REALTEK_PHY` 必须显式确认**
- `MII`、`PCS_XPCS`、`PCS_XPCS_ROCKCHIP` 等由 select 形成的编译闭包

### Rockchip 硬件资源
- `COMMON_CLK_ROCKCHIP`、`CLK_RK3568`
- `MFD_SYSCON`、`ROCKCHIP_GRF`
- `RESET_CONTROLLER`
- `PINCTRL_ROCKCHIP`、`GPIO_ROCKCHIP`、`GPIOLIB`

### PHY 电源 provider
- `REGULATOR)、`REGULATOR_RK808`
- `MFD_RK8XX_I2C)、`MFD_RK8XX`
- `I2C)、`I2C_RK3X)、`OF`、`REGMAP_I2C` 等 PMIC provider 依赖

实际最终 .config 是否满足上述闭包，必须在后续受控配置复合时检查；本次没有构建，也没有把任何符号写入配置文件。

## 11. 结论与状态

### 已验证

1. 6.18.63 的精确源码版本为 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`，根目录 Makefile 明确为 6.18.63。
2. STMMAC / STMMAC platform / Rockchip glue 的 Kconfig gate、select、Makefile 对象归属已经闭环。
3. DWMAC4 DMA/core 对象随 `stmmac.o` 编译，Rockchip glue `dwmac-rk.o` 独立由 `DWMAC_ROCKCHIP` 控制。
4. PHYLINK → PHYLIB → MDIO_BUS 的依赖关系和 RTL8211F `REALTEK_PHY` 显式配置要求已闭环。
5. 6.18 的 PCS_XPCS_ROCKCHIP 是 Kconfig 编译闭包，不是 Panther RGMII runtime PCS 路径。
6. Rockchip clock / GRF / CRU reset / pinctrl / GPIO 的 Kconfig 和 Makefile provider 已定位。
7. Panther `phy-supply` 的实际 RK809 provider 链已从 DTS 和 6.18 Kconfig/Makefile 闭环；它不是 fixed regulator。
8. 6.1.116、6.12.81、6.18.63 在 STMMAC、Rockchip glue、MDIO、Realtek PHY、clock、GRF、PMIC Kconfig/Makefile 的关键结构差异已登记。

### 未验证

- 6.18.63 最终生成的 .config 是否满足上述完整闭包；本次没有构建。
- 所有 provider 是否在 Panther 实机成功 probe、绑定及供电；本次没有实机测试。
- 任何 Kconfig 差异是否造成历史网络故障；不能仅凭配置依赖审计定根因。
- 6.12.81 的 GRF 实际配置是否启用，仍以其已归档实际 .config 为准，不能用 Kconfig 默认推断。

### B2-0 子项结论

**结项：6.18.63 精确源码 Kconfig / Makefile 依赖审计及与 6.1.116、6.12.81 的关键构建接入差异登记。**

这关闭了 B2-0 组件源码差异账本中本轮明确的 6.18.63 配置接入审计缺口；不代表 B2-0 整体已自动结项，也不提前放行 B2-1。后续严格回到 B2-0 原始清单，核对其余子项状态后再决定下一项。

## 12. 精确源码文件索引

### 6.18.63
- [Root Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/Makefile)
- [STMMAC Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/ethernet/stmicro/stmmac/Kconfig)
- [STMMAC Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/ethernet/stmicro/stmmac/Makefile)
- [PHY Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/phy/Kconfig)
- [PHY Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/phy/Makefile)
- [Realtek PHY Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/phy/realtek/Kconfig)
- [Realtek PHY Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/phy/realtek/Makefile)
- [MDIO Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/mdio/Kconfig)
- [MDIO Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/mdio/Makefile)
- [PCS Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/pcs/Kconfig)
- [PCS Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/pcs/Makefile)
- [Rockchip clock Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/clk/rockchip/Kconfig)
- [Rockchip clock Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/clk/rockchip/Makefile)
- [Rockchip GRF Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/soc/rockchip/Kconfig)
- [Rockchip GRF Makefile](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/soc/rockchip/Makefile)
- [Pinctrl Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/pinctrl/Kconfig)
- [GPIO Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/gpio/Kconfig)
- [Regulator Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/regulator/Kconfig)
- [MFD Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/mfd/Kconfig)
- [I2C RK3x Kconfig](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/i2c/busses/Kconfig)
- [Panther X2 DTS](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)

### 历史对照源码
- [6.1.116 STMMAC Kconfig](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/Kconfig)
- [6.1.116 STMMAC Makefile](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/Makefile)
- [6.12.81 STMMAC Kconfig](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/Kconfig)
- [6.12.81 STMMAC Makefile](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/Makefile)
