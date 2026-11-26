# Panther X2 项目 A — R4 MDIO/PHY 框架与 RTL8211F Kconfig/对象审计（2026-11-26）

## 1. 阶段边界

R3 已完成静态审计并条件结项。本报告开始 R4，按原实施计划只审查 MDIO/PHY 通用框架、设备树 MDIO 支持、PHYLINK/PHYLIB 和 RTL8211F 驱动的 Kconfig/Makefile 依赖。当前仍为源码只读审计：

- GMAC1、MDIO1、RTL8211F DT 节点继续 disabled；
- 不构建/加载 R4 驱动，不恢复网络节点；
- 不执行 MDIO 事务、不读写 PHY 寄存器、不触发 reset/link flap；
- 不修改内核配置、DTB、initramfs 或设备；
- 比较固定源码：6.1.65 黄金候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`；6.18.63 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

项目 B 中 6.1.116/6.1.174/6.12 的 RTL8211F/MDIO 历史审计报告已回读并作为已有成果复用，本轮不重复其历史 PHYCR2 读写/trace 方案研究：
- `116-JL2XX1-MDIO-TRANSACTION-AND-ORDER-AUDIT-20261118.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`
- `116-RTL8211F-MDIO-TRACE-AND-PAGED-READ-SAFETY-20261118.md`
- `116-RTL8211F-KERNEL-PAGED-READ-INTERFACE-AUDIT-20261118.md`
- `116-RTL8211F-PHYCR2-REFCOUNTED-PHY-LOOKUP-AND-TEARDOWN-AUDIT-20261118.md`

这些报告的适用源码版本并非本轮 6.1.65/6.18.63 固定端点；它们作为历史风险输入，不替代本轮版本对照。

## 2. Kconfig 差异：PHYLIB / MDIO_BUS

### 2.1 PHYLIB 的依赖结构发生变化

| 项目 | 6.1.65 | 6.18.63 |
|---|---|---|
| PHYLIB depends | `NETDEVICES` | Kconfig 中未见该 depends |
| PHYLIB selects | `MDIO_DEVICE`、`MDIO_DEVRES` | `MDIO_BUS` |
| MDIO_BUS 定义 | `drivers/net/mdio/Kconfig`，位于 `if MDIO_DEVICE` 内部的内部 tristate；默认跟随 PHYLIB/MDIO_DEVICE | `drivers/net/phy/Kconfig` 中独立 tristate “MDIO bus consumer layer” |
| MDIO bus 对象 | PHYLIB 条件下与 MDIO device 对象合并进 libphy | 单独 `mdio-bus.o` 对象 |

这是结构性变化。6.18 不能照搬 6.1.65 的 MDIO_DEVICE/MDIO_DEVRES 推理；应以 6.18 的 PHYLIB → MDIO_BUS 依赖和独立对象映射为准。

### 2.2 OF_MDIO / FWNODE_MDIO

| 项目 | 6.1.65 | 6.18.63 |
|---|---|---|
| OF_MDIO | `def_tristate PHYLIB`，depends OF 和 PHYLIB，select FIXED_PHY | 位于 `if PHYLIB` 内，`def_tristate OF`，select FIXED_PHY |
| FWNODE_MDIO | `def_tristate PHYLIB`，depends (ACPI || OF) || COMPILE_TEST，select FIXED_PHY | 位于 `if PHYLIB` 内，`def_tristate (ACPI || OF) || COMPILE_TEST`，select FIXED_PHY |

对 Panther 的 OF/DT MDIO 描述，两版均需 OF_MDIO 路径。6.18 的 OF_MDIO 仍依赖其外层 PHYLIB 条件块，但不再重复写 `depends on PHYLIB`。不能因 6.18 Kconfig 文本更短而认为 OF_MDIO 不再需要 PHYLIB。

### 2.3 PHYLINK

两版 PHYLINK 均 select PHYLIB 和 SWPHY；6.1.65 另有 `depends on NETDEVICES`，6.18.63 该依赖已不在 PHYLINK 条目中。STMMAC_ETH 在两版均 select PHYLINK，因此后续 R5/R6 依赖闭包会引入 PHYLIB/MDIO 基础设施。R4 仍需单独核实最终 built-in 对象和 RTL8211F 驱动，不能仅凭 PHYLINK 被 select 就推定 Realtek 驱动已启用。

## 3. RTL8211F 驱动：必须显式纳入

两版 `drivers/net/phy/Kconfig` 均有独立配置项：

```kconfig
config REALTEK_PHY
    tristate "Realtek PHYs"
```

该配置没有被 PHYLIB、PHYLINK 或 DWMAC_ROCKCHIP 自动 select。两版 Makefile 均通过 `CONFIG_REALTEK_PHY` 生成 Realtek PHY 驱动对象；6.1.65 映射为 `realtek.o`，6.18.63 映射到 `realtek/` 子目录。

因此，R4 的 RTL8211F 最小驱动闭包必须显式确认 `CONFIG_REALTEK_PHY=y` 及其对象确实进入最终内核。不能把 `PHYLIB=y` 或 `PHYLINK=y` 当成 RTL8211F 驱动已包含的证据。

## 4. 与 STMMAC/Rockchip glue 的依赖边界

本轮回读的 Kconfig 显示：

- 两版 `STMMAC_ETH` 都 select `PHYLINK`；
- 6.1.65 `STMMAC_ETH` 依赖 `HAS_IOMEM && HAS_DMA` 和 `PTP_1588_CLOCK_OPTIONAL`；
- 6.18.63 在以上依赖外新增 `ETHTOOL_NETLINK`；
- 两版 `DWMAC_ROCKCHIP` 都依赖 OF 与 ARCH_ROCKCHIP/COMPILE_TEST，并 select `MFD_SYSCON`；
- 6.18.63 的 `DWMAC_ROCKCHIP` 额外 select `PCS_XPCS_ROCKCHIP`，这是 R6 glue/PCS 依赖项，先登记，不在 R4 混入；
- 两版均没有看到 `DWMAC_ROCKCHIP` select `REALTEK_PHY`。

注意：STMMAC_ETH 与 DWMAC_ROCKCHIP 的差异属于后续 R5/R6；本轮只登记依赖事实，不提前构建或启用这些配置。

## 5. R4 当前结论

已完成的静态审计项：

1. PHYLIB/MDIO_BUS Kconfig 结构差异已定位；
2. OF_MDIO/FWNODE_MDIO 默认关系已对照；
3. PHYLINK 两版 select 关系已对照；
4. REALTEK_PHY 为独立配置、不会由 PHYLIB/PHYLINK/DWMAC 自动 select，已确认；
5. RTL8211F 对应对象映射已确认；
6. STMMAC/DWMAC Kconfig 变化登记到 R5/R6，未越界处理。

当前结论：**R4 Kconfig 第一子项 PASS（STATIC）；R4 整体仍 IN PROGRESS。** 尚需完成 MDIO/PHY 对象源文件及符号依赖、RTL8211F match/probe/config_init 的 6.1.65 与 6.18.63 对照、最终配置审查方法；之后才可对 R4 静态审计结项。R4 结项仍不等于实机 PHY probe 放行。

## 6. 下一步（严格顺序）

下一轮继续 R4 的第二子项：对照两版 `drivers/net/phy/realtek.c`（6.18 若已拆分则连同对应子目录文件）中 RTL8211F PHY ID、match table、probe、config_init、soft reset、RGMII delay 配置和错误传播。只审查与 Panther X2 当前 DT interface/phy-mode 相关的路径，不重新做历史 JL2xx1 workaround 专题，也不进行实机寄存器访问。

**本报告只记录固定源码的只读审计；没有构建、加载驱动、访问硬件或修改设备。**
