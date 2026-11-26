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

## 7. RTL8211F 驱动实现对照（R4 第二子项，2026-11-26）

固定源码：
- 黄金候选 6.1.65：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`，`drivers/net/phy/realtek.c`；
- 目标 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`，`drivers/net/phy/realtek/realtek_main.c`（Realtek driver 已拆分目录）。

### 7.1 PHY ID 匹配：核心 RTL8211F ID 未变化

两版均以 `PHY_ID_MATCH_EXACT(0x001cc916)` 匹配 RTL8211F，均保留 RTL8211F-VD 的 `0x001cc878` 独立条目。6.1.65 的 RTL8211F probe 指向 `rtl821x_probe`；6.18.63 的普通 RTL8211F 条目改为专用 `rtl8211f_probe`。因此 PHY ID 匹配本身不是 6.18 回归，但 probe 副作用发生变化。

### 7.2 Probe 阶段从读取配置变成明确写寄存器

6.1.65 的 `rtl821x_probe()`：
- 读取 page `0xa43` / PHYCR1 `0x18`；
- 读取 page `0xa43` / PHYCR2 `0x19`（VD 变体除外）；
- 将 ALDPS 相关位和 CLKOUT_EN 位缓存到私有数据；
- DT 属性存在时才调整缓存目标值；
- probe 阶段没有对上述寄存器执行写操作。

6.18.63 的通用 `rtl821x_probe()`：
- 分配私有数据；
- `devm_clk_get_optional_enabled()` 获取并可能使能 PHY clock；
- 读取 `realtek,aldps-enable` 和 `realtek,clkout-disable` 属性；
- 不再读取/缓存 PHYCR1、PHYCR2。

随后 6.18.63 专用 `rtl8211f_probe()` 会无条件执行：
`phy_write_paged(RTL8211F_WOL_PAGE=0xd8a, RTL8211F_WOL_SETTINGS_EVENTS=16, 0)`，
即清除 PHY 的 PME/WoL event 配置。该动作是明确的 MDIO 写操作，即使设备树没有 `wakeup-source` 也会执行。

**结论：6.18 RTL8211F 的 PHY driver probe 不是只读操作。** PHY/MDIO 节点仍必须保持 disabled；不得把“只加载驱动观察 probe”当作无副作用的验证。6.1.65 probe 也会做两次 paged MDIO 读取，且可能 enable optional clock，但没有上述 WOL register write。

### 7.3 ALDPS 配置策略变化

6.1.65：
- probe 先读出现有 PHYCR1；
- 缺少 `realtek,aldps-enable` 时保留硬件当前 ALDPS 三个位；
- 属性存在时将三个位设为 1；
- config_init 通过 `phy_modify_paged_changed()` 将缓存值写回掩码位。

6.18.63：
- probe 不读 PHYCR1；
- 缺少 `realtek,aldps-enable` 时 config helper 直接返回，不改寄存器；
- 属性存在时才将三个 ALDPS 位设为 1。

对“属性缺失时保留现状”而言，两版目标一致，但实现方式不同；6.18 去掉了 probe read + config_init write-back 的往返。

### 7.4 RGMII TX/RX delay：寄存器位置与接口映射一致

两版都按 `phydev->interface` 选择 2ns delay：
- RGMII：TX=0、RX=0；
- RGMII_RXID：TX=0、RX=1；
- RGMII_TXID：TX=1、RX=0；
- RGMII_ID：TX=1、RX=1；
- 其他 interface：不调整 delay。

寄存器/位定义也一致：
- page `0xd08`，TXCR `0x11)，TX delay bit 8；
- page `0xd08`，RXCR `0x15)，RX delay bit 3。

6.18 将页号/寄存器抽成常量并将逻辑移入 `rtl8211f_config_rgmii_delay()`，行为基本保持。两版都使用 paged modify helper 并传播负错误码。6.18 还在 resume 路径重新应用 RGMII delay；6.1.65 的 RTL8211F resume 仅走通用 resume 延时流程，没有该专用重应用步骤。

**当前不判定 Panther 应使用 RGMII / RGMII-ID / RXID / TXID。** 必须以 Panther X2 原始 DTS 与 6.1.65 黄金 DTB 的 `phy-mode`、MAC delay 属性、PHY 节点配置做联合核验后才能决定；不能由芯片型号猜测。

### 7.5 CLKOUT 与 soft reset 行为变化

6.1.65 在 RGMII delay 配置后，若变体支持 PHYCR2，会将缓存的 CLKOUT_EN 位写回；最后执行 `genphy_soft_reset()`。对非 RGMII interface，函数在 delay switch default 分支提前返回，因此后续 PHYCR2 写回和 soft reset 不执行。

6.18.63：
- `realtek,clkout-disable` 缺省时保留 CLKOUT，不访问 CLKOUT 控制寄存器；
- 属性存在时才清除 CLKOUT；对普通 RTL8211F 使用 PHYCR2，对 RTL8211F-VD 使用独立 undocumented page/register；
- 只有执行 CLKOUT disable 修改成功后才调用 `genphy_soft_reset()`；
- 正常默认配置下 config_init 不再无条件 soft reset。

因此 6.18 默认启动路径比 6.1.65 少一次 PHY soft reset；这是实质性生命周期差异，需在后续 PHY bring-up 时纳入观察，但不能据此推断哪版更适合 Panther。

### 7.6 新增 EEE 配置写入

6.18.63 的 `rtl8211f_config_init()` 最后无条件调用 `rtl8211f_config_phy_eee()`，通过 page `0xa43` / PHYCR2 `0x19` 清除 `RTL8211F_PHYCR2_PHY_EEE_ENABLE`（bit 5），注释说明目的是关闭 PHY-mode EEE，让 LPI 由 MAC 处理。

6.1.65 对应 RTL8211F config_init 没有该 EEE bit 修改。

这是一项 6.18 新增的 PHY 寄存器写行为。后续 TX 测试必须记录它，避免把 EEE/LPI 行为与基本 TX descriptor/DMA 问题混为一谈。首轮基础 TX 验证应先明确 EEE 配置状态，但不能未经测试直接改成启用或禁用的另一种策略。

### 7.7 Interrupt 配置差异

两版均在 page `0xa42` / INER `0x12` 配置 link-status interrupt，并通过 page `0xa43` / INSR `0x1d` ack 状态。6.18 将当前 INER 值缓存到私有数据，供 suspend/resume 时恢复；6.1.65 没有此缓存字段。两版对 MDIO 错误均传播负错误码。

### 7.8 R4-2 结论

- PHY ID match：PASS（核心 ID/VD ID 一致）；
- RGMII delay bit/寄存器与 interface 映射：PASS（行为一致）；
- ALDPS 默认保持现状：PASS（实现方式不同）；
- probe 副作用：有重要差异，6.18 新增 WOL event register 写，且可能 enable optional PHY clock；
- PHY config_init：有重要差异，6.18 新增 PHY EEE bit 清除；默认路径不再无条件 soft reset；
- resume：6.18 新增 RGMII delay 重应用；
- 实际 Panther interface/delay 选择：BLOCKED，等待原始 DTS/黄金 DTB 对照。

因此 **R4 第二子项源码对照 PASS（STATIC / DIFFERENCES DOCUMENTED）**。R4 整体仍 IN PROGRESS，后续还需完成 MDIO/PHY 核心对象依赖闭包与 R1 当前 config/最终 built-in object 对照。当前仍不放行任何 PHY probe。

## 8. MDIO/PHY 核心对象及链接边界（R4 第三子项，2026-11-26）

### 8.1 6.1.65 黄金基线

固定 Makefile：drivers/net/phy/Makefile、drivers/net/mdio/Makefile。

6.1.65 的 libphy 聚合对象包含 phy.o、phy-c45.o、phy-core.o、phy_device.o、linkmode.o；mdio-bus-y 包含 mdio_bus.o、mdio_device.o。当 CONFIG_PHYLIB 存在时，Makefile 将 mdio-bus-y 追加进 libphy-y，因此 MDIO bus/device 核心与 PHYLIB 合并链接；没有 PHYLIB 时，才由 CONFIG_MDIO_DEVICE 单独构建 mdio-bus.o。mdio_devres.o 由 CONFIG_MDIO_DEVRES 控制。OF_MDIO/FWNODE_MDIO/ACPI_MDIO helper 分别在 drivers/net/mdio/ 下独立构建。REALTEK_PHY 显式生成 realtek.o。

### 8.2 6.18.63 对象拆分

6.18 的 libphy 聚合对象新增 phy_link_topology.o、phy_caps.o、mdio_bus_provider.o；mdio_bus.o 和 mdio_device.o 组成独立 mdio-bus.o，由 CONFIG_MDIO_BUS 控制，不再并入 libphy。mdio_devres.o 改由 CONFIG_PHYLIB 控制。CONFIG_PHYLIB 时还加入 stubs.o。OF_MDIO/FWNODE_MDIO/ACPI_MDIO helper 仍由各自配置在 drivers/net/mdio/ 构建。REALTEK_PHY 改为生成 realtek/ 子目录对象。

这是重要的对象模型变化：6.18 必须分别核验 CONFIG_PHYLIB、CONFIG_MDIO_BUS、CONFIG_OF_MDIO 和 CONFIG_REALTEK_PHY，不能照搬 6.1.65 的 libphy 聚合假设。

### 8.3 功能调用链

源码链路为 Rockchip GMAC glue → MDIO bus 注册/使用 → OF MDIO helper 解析 PHY 子节点并创建 PHY device → MDIO bus 层访问 → PHY ID 匹配 → Realtek PHY driver probe/config_init → PHY 状态机/phylink 与 STMMAC MAC 协作。

OF PHY 发现会触发实际 MDIO 事务；RTL8211F probe/config_init 也存在前节记录的寄存器写副作用。因此这条链路只用于静态依赖审计，当前 GMAC/MDIO/PHY DT 节点仍必须 disabled。

### 8.4 R1 配置与对象证据边界

本轮取得了两个固定源码版本的 Makefile，但未取得 R1 config SHA256 480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a 对应的完整 .config 和最终 built-in.a/vmlinux 对象清单。因此不能推断当前 CONFIG_PHYLIB、CONFIG_MDIO_BUS、CONFIG_OF_MDIO 或 CONFIG_REALTEK_PHY 的实际值，也不能把 Makefile 存在对象规则当作 R1 已包含对象的证据。

R4-4 将从 R1 已归档构建产物提取原始 config 与对象清单，核验 CONFIG_PHYLIB 对应 libphy 及新增对象、CONFIG_MDIO_BUS 对应 mdio-bus.o（6.18）、CONFIG_OF_MDIO 对应 drivers/net/mdio/of_mdio.o、CONFIG_REALTEK_PHY 对应 drivers/net/phy/realtek/。STMMAC/DWMAC 对象留待 R5/R6。

### 8.5 R4-3 结论

R4-3 源码对象归属与依赖架构：PASS（STATIC）。R1 当前配置/最终对象实证：PENDING，转入 R4-4。未构建、未加载驱动、未执行 MDIO 事务、未访问硬件。
