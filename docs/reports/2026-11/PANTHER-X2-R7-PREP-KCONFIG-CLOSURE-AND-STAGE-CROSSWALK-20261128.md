# Panther X2 Project A — R7-prep 静态配置闭包与阶段编号统一记录

- 日期：2026-11-28
- 状态：**静态设计审计 PASS；build-only 尚未执行；无硬件授权**
- 目标源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`（Linux 6.18.63）
- 冻结输入：G4-P0 build-only run `46091659151` / artifact `15242113092`
- 上位依据：R2–R7 详细实施计划 §3、G0–G10 硬件激活计划 §4–§5、R4/R5 审计报告、G0.5 ABCD sender 规格

## 1. 本阶段目标与严格边界

R7-prep 是 R7-A 前置的**云端 build-only 资产准备**，不是新的硬件激活门。它从已通过实机验证的 G4-P0 frozen config 派生，预先构建后续 R7-A 至 R7-D 所需的板载 Ethernet 软件闭包，使 R7-A 的硬件候选只需修改 GMAC1 parent DTB status。

本轮应做到：
- 启用 Linux generic network core、Ethernet framing、AF_PACKET；
- 预编译 STMMAC core、STMMAC platform wrapper、Rockchip DWMAC glue；
- 预编译 MDIO/PHYLIB/PHYLINK/OF-MDIO 框架及 RTL8211F 驱动，为 R7-B 准备，但不触发 PHY probe；
- 保留 G4-P0 IO-domain binding-only 配置和 DTB：IO-domain child okay，九个 supply 属性全部缺失；
- GMAC1、MDIO child、RTL8211F PHY 节点继续 disabled；
- 保留当前 RAM initramfs/BusyBox/bootargs 架构，不引入持久化 rootfs；
- 云端编译、配置/对象/符号审计和 artifact 归档；不接触 Panther X2。

明确不做：
- 不改 DTB，不启用 GMAC1/MDIO/PHY 节点；
- 不运行 platform probe，不执行 clock enable、main-GRF 写入、regulator_enable 或 PMIC 写入；
- 不 open interface，不执行 MDIO 事务、PHY reset、link negotiation 或 TX/RX；
- 不写 SU08G，不触碰 SN64G/eMMC，不改变任何设备配置。

## 2. 冻结输入

G4-P0 build-only artifact：
- Actions run：`46091659151`
- Artifact：`panther-x2-g4-p0-binding-only-build-only`，ID `15242113092`
- Image SHA256：`b34b8faaa34bcb843d82f11423489b434c1e2f329fedab1d81754fd192723090`
- DTB SHA256：`c967aff4bb99748828fdf083a8e1701b915966e47c6828375399bef5e0048ff8`
- kernel.config SHA256：`c990c913b283a7042a81be12369886e1faa95bbf5b2cc031fd9e1155a4357be2`

R7-prep 必须以该 artifact 的最终 `.config` 为 merge_config 输入，不从 Ophub seed 重建配置，不从 G3 或其他历史 fragment 重新拼接。固定复用同一 Linux source commit 和已审计的 B1 compatibility patch。DTB 必须从 G4-P0 artifact 原样复制，哈希仍为上面的冻结值。

## 3. Kconfig / Makefile 依赖审计

### 3.1 已有网络核心（继承 R1，不重新研究）

R1 的最终配置和运行时 AF_PACKET API 证据已归档：
- `CONFIG_NET=y`
- `CONFIG_NETDEVICES=y`
- `CONFIG_NET_CORE=y`
- `CONFIG_ETHERNET=y`
- `CONFIG_PACKET=y`

R1 实机只证明 AF_PACKET 软件 API 与 loopback outgoing tap，不证明目标网卡 TX。R7-prep 保留 PACKET，为后续独立 ABCD sender 使用；`INET`、IPv6、NETFILTER 等高层协议仍不引入。

### 3.2 STMMAC core

**额外的顶层门控核验：** `drivers/net/ethernet/stmicro/Kconfig` 将 STMMAC Kconfig 放在 `if NET_VENDOR_STMICRO` 内；因此 R1 的“全部 vendor group 关闭”策略不能原样继承到 R7-prep。必须只重新启用 `CONFIG_NET_VENDOR_STMICRO=y`，否则 STMMAC 子菜单不可见/目标符号无法按预期配置。该 vendor group 只包含本目标所需 STMMAC 子树；其余 NET_VENDOR_* 仍保持关闭，尤其 `NET_VENDOR_REALTEK`（独立 Realtek Ethernet MAC/网卡厂商组）继续关闭，不能与 PHY 驱动 `REALTEK_PHY` 混淆。

固定 6.18.63 `drivers/net/ethernet/stmicro/stmmac/Kconfig`：
- `STMMAC_ETH` depends on `HAS_IOMEM && HAS_DMA`、`PTP_1588_CLOCK_OPTIONAL`、`ETHTOOL_NETLINK`；
- select `MII`、`PCS_XPCS`、`PAGE_POOL`、`PHYLINK`、`CRC32`、`RESET_CONTROLLER`、`NET_DEVLINK`；
- 6.18 的 `ETHTOOL_NETLINK` 是相对 6.1.65 新增的硬依赖，不能漏检；
- `STMMAC_SELFTESTS` 依赖 `INET`，TX-first 不需要，必须保持关闭。

Makefile 将核心聚合为 `stmmac.o`，含 `stmmac_main.o`、`stmmac_mdio.o`、DWMAC4 DMA/descriptor、ring/chain、PTP/MMC 等对象；6.18 还包含 EST/FPE/VLAN/PCS 等对象。对象存在不代表这些可选硬件功能会被 Panther 启用。

### 3.3 Platform / Rockchip glue

固定 Kconfig/Makefile 结论：
- `STMMAC_PLATFORM` 生成 `stmmac-platform.o`，并 select `MFD_SYSCON`；
- `DWMAC_ROCKCHIP` depends on `OF && (ARCH_ROCKCHIP || COMPILE_TEST)`，select `MFD_SYSCON` 和 `PCS_XPCS_ROCKCHIP`；
- `DWMAC_ROCKCHIP` 生成 `dwmac-rk.o`；
- 6.18 的 `DWMAC_GENERIC` default 为 `STMMAC_PLATFORM`。若不显式关闭，启用 platform wrapper 可能顺带构建不需要的 generic glue；R7-prep fragment 明确关闭它。

### 3.4 MDIO / PHY / RTL8211F

固定 6.18.63 Kconfig/Makefile 结论：
- `STMMAC_ETH` select `PHYLINK`；`PHYLINK` select `PHYLIB`；`PHYLIB` select 独立 `MDIO_BUS`；
- OF-MDIO helper 由 `OF_MDIO` 对应 `drivers/net/mdio/of_mdio.o`；
- `PHYLIB`、`MDIO_BUS`、`PHYLINK` 分别对应 `libphy.o`、`mdio-bus.o`、`phylink.o`；
- `REALTEK_PHY` 是独立配置，不由 PHYLIB、PHYLINK 或 DWMAC_ROCKCHIP 自动 select，必须显式设为 y；6.18 对应 `drivers/net/phy/realtek/realtek.o`（聚合 `realtek_main.o`）。

将 REALTEK_PHY 预编译进内核只代表对象存在。因为 DTB 中 MDIO 与 PHY 节点仍 disabled，本阶段不会创建 PHY device，也不会执行 RTL8211F probe 的 WOL event 写入或 config_init 的 EEE/RGMII delay MDIO 写入。PHY 的真实 probe 留到 R7-B，并另行授权。

## 4. R7-prep 配置片段

已新增 `scripts/panther-x2-r7-prep/r7-prep.fragment`。用户选择项仅限：
- R1 网络核心符号显式确认保持 y；
- `CONFIG_NET_VENDOR_STMICRO=y`（STMMAC Kconfig 顶层可见性的必要 gate）
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_PLATFORM=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_REALTEK_PHY=y`
- 显式关闭 `CONFIG_DWMAC_GENERIC` 与 `CONFIG_STMMAC_SELFTESTS`。

其余依赖由固定 6.18.63 Kconfig 收敛，但 build workflow 必须核验最终 `.config`，不能仅凭 fragment 通过。若 `ETHTOOL_NETLINK`、`PTP_1588_CLOCK_OPTIONAL`、`MDIO_BUS`、`PHYLIB`、`PHYLINK`、`OF_MDIO`、`PCS_XPCS_ROCKCHIP` 或所需 provider 最终值不符，构建门失败并停留在 build-only，不允许手工掩盖差异。

## 5. 黄金基线对照

| 维度 | 6.1.65 第一黄金基线 | 6.1.116 第二行为参照 | 6.18.63 R7-prep 目标 |
|---|---|---|---|
| STMMAC_ETH / PLATFORM | 原始 Image 内嵌配置与 modules.builtin 已确认 built-in | 已归档真实配置及 GMAC 正常运行证据 | 目标为 built-in，需本轮最终 config/object 证明 |
| DWMAC_ROCKCHIP | 原始 Image 配置确认启用 | 已归档配置/对象闭环确认启用 | built-in，目标 Panther 专用 glue |
| PHYLINK / PHYLIB / MDIO | 配置与 built-in 主链证据已归档 | 真实配置闭环包含 PHYLIB、MDIO_BUS、OF_MDIO | 依赖收敛后 built-in |
| REALTEK_PHY | RTL8211F 正常系统主链的配置/对象证据 | 真实配置含 REALTEK_PHY，RTL8211F addr 0 / 1Gbps Full 运行证据 | 显式 built-in，DT 节点仍 disabled |
| generic packet path | 6.1.65 包含 PACKET 与 INET | 6.1.116 包含 PACKET 与 INET | 保留 PACKET；不引入 INET/IP 层 |
| DTB 硬件激活 | 黄金系统启用板载 Ethernet | 黄金系统启用板载 Ethernet | R7-prep 完全复用 G4-P0 DTB；GMAC/MDIO/PHY 仍 disabled |

黄金配置/功能证据来自既有原始镜像审计、6.1.116 配置闭环、R4/R5 静态审计和 G0 黄金反向审计。本轮不重复提取黄金镜像、不重跑黄金系统测试。6.1.65 的精确构建源码身份限制继续保留；不把候选源码来源升级为二进制级确定事实。

## 6. Build-only 必须通过的验收项

1. 输入 G4-P0 artifact 内部 SHA256 inventory 全部通过；Image/config/DTB 哈希与冻结值一致。
2. Source commit、Linux 6.18.63 版本、B1 compatibility patch hash 固定。
3. 最终 `.config`：R1 generic core + PACKET、NET_VENDOR_STMICRO、STMMAC_ETH、STMMAC_PLATFORM、DWMAC_ROCKCHIP、REALTEK_PHY 均为 y；其余 NET_VENDOR_*（除 STMICRO）保持关闭；STMMAC_SELFTESTS、DWMAC_GENERIC、INET、IPV6、NETFILTER、无线/蓝牙、非目标网卡保持关闭。
4. 最终依赖值逐项核验，包括 HAS_IOMEM/HAS_DMA、PTP_1588_CLOCK_OPTIONAL、ETHTOOL_NETLINK、MII、PCS_XPCS、PAGE_POOL、PHYLINK、PHYLIB、MDIO_BUS、OF_MDIO、FIXED_PHY、PCS_XPCS_ROCKCHIP、MFD_SYSCON、REGULATOR_RK808。
5. 对象存在并为 built-in：`stmmac.o`、`stmmac-platform.o`、`dwmac-rk.o`、`mdio-bus.o`、`libphy.o`、`phylink.o`、`of_mdio.o`、`realtek.o`；记录各对象 SHA256。
6. 对象/vmlinux 符号审计：记录 `rk_gmac_probe`、`stmmac_dvr_probe`、`stmmac_xmit`、RTL8211F probe/config 函数等符号是否存在及其 local/global binding。不得因为 static/local 符号未进入 kallsyms 就判硬件失败；若后续 kprobe 不可用，按 G0.5 规则评估最小 tracepoint，不开启全局 function tracer。
7. DTB 与 G4-P0 完全相同，SHA256 必须仍为 `c967aff4bb99748828fdf083a8e1701b915966e47c6828375399bef5e0048ff8`；IO-domain child okay、九路 supply 缺失；GMAC1/MDIO/PHY 全部 disabled。
8. 记录 Image/config/DTB/System.map/vmlinux/对象/工具链/源码/补丁哈希与完整 config diff。
9. 仅生成 build-only artifact；不生成 SU08G raw image，不打包刷写镜像，不访问设备。

## 7. 阶段编号与归档命名统一规则

为避免把不同维度的编号误读为线性阶段，保留历史报告原编号（不批量改名、不改变引用稳定性），从本报告起采用以下规范：

| 维度 | 编号体系 | 作用 |
|---|---|---|
| 组件静态/构建审计 | R2–R6 | 分别审计 SoC provider、RK809/regulator、MDIO/PHY、STMMAC core、Rockchip glue；属于前置证据，不是硬件激活顺序 |
| 硬件准入/副作用评估 | G0–G4 | G0 统一准备与黄金对照；G1–G4 为 provider/IO-domain 准入与风险边界；不与 R2–R6 一一对应 |
| R7-prep | 独立前置资产节点 | 云端预构建完整 R7 软件闭包，GMAC/MDIO/PHY DT 节点仍 disabled；不是硬件阶段 |
| R7-A | G5-A | Rockchip glue/STMMAC platform probe、bind、netdev 注册 |
| R7-B | G5-B | MDIO bus、RTL8211F attach、link |
| R7-C | G6-A | interface open、MAC/DMA/ring/IRQ/NAPI |
| R7-D | G6-B + G7 | ABCD 同帧 TX、descriptor/completion、对端 E6 捕获 |
| 后续协议阶段 | G8–G10 | RX、ARP/IPv4/ICMP、TCP/UDP 与按需服务 |

归档规则：
- 不重编号已经引用的 R2–R6、G0–G10 报告；原编号是历史证据的稳定标识。
- 新报告标题同时标注双编号，例如“R7-A / G5-A”，不再创建第二套平行任务清单。
- R7-prep 永远标记为 build-only / NOT HARDWARE ACTIVATION。
- 任一阶段状态必须细分 STATIC、BUILD、RUNTIME BIND/PROBE、FUNCTIONAL、E6；不得用单个 PASS 覆盖后续未验证项。

## 8. 当前阶段状态

| 项目 | 状态 |
|---|---|
| G4-P0 binding-only build/config/DTB | PASS |
| G4-P0 RAM-only runtime binding | PASS（已授权的一次会话） |
| G4-P full nine-supply mapping | NO-GO |
| R7-prep static Kconfig/Makefile design | **PASS** |
| R7-prep build-only | NOT STARTED |
| R7-prep final config/object/symbol audit | NOT STARTED |
| R7-A / G5-A hardware probe | NOT AUTHORIZED / NOT RUN |
| R7-B / G5-B MDIO/PHY | NOT STARTED |
| R7-C / G6-A open/DMA | NOT STARTED |
| R7-D / G6-B/G7 physical TX | NOT STARTED |

## 9. 结论与下一步

静态依赖研究已完成，下一步是新增独立 R7-prep build-only workflow：从 G4-P0 frozen artifact 恢复输入、使用独立 fragment、增量复用 G4-P0 object cache、编译 Image 并完成 final .config/object/symbol/DTB/hash audit。构建成功后还须独立审查完整 runtime package（Image、DTB、initramfs、bootargs、U-Boot、sender、观测配置）并冻结哈希，才可提出 R7-A/G5-A 实机操作授权。

**本报告与 fragment 的新增/提交不构成 R7-A 硬件 probe 授权。** 当前没有访问 Panther X2、写 TF、触碰 SN64G/eMMC、执行 PMIC/GRF/GPIO/MDIO 操作或发送网络帧。

## 10. 2026-11-28 执行顺序修订：GMAC 最后启用

R7-prep 仅是云端软件资产准备。其后不立即进入 GMAC probe，而增加两个明确的 Pre-GMAC 硬件准入门：

- **G4-P1 / 非 GMAC 共享基础组件就绪**：GMAC/MDIO/PHY 继续 disabled。按 R2/R3 既有证据逐项复核 clock/CRU、pinctrl/GPIO、GRF/syscon、reset、I2C0、RK809 MFD/regulator、IO-domain provider 的注册、绑定与可安全观察状态。G4-P0 已完成的 regulator provider 与 IO-domain binding 证据直接复用，不重复启动设备。仅对明确缺失的证据设计最小只读补证；不得为凑齐清单而切换 regulator、翻转未知 GPIO、触发 reset 或写 PMIC/GRF。
- **G4-P2 / 供电与 IO-domain 安全准入**：单独解决 SWITCH_REG1/vcc_3v3 PHY supply consumer enable、九路 IO-domain supply/selector 与 partial-write 风险。G4-P0 binding PASS 不代表这些功能已通过；full nine-supply mapping 仍 NO-GO。未能证明安全且与黄金基线差异可解释时，G4-P2 保持 HOLD，GMAC 不启动。
- **R7-A / G5-A**：仅在 G4-P1、G4-P2 均通过且取得独立授权后，最后启用 GMAC1 parent。MDIO/PHY disabled、interface DOWN，不 open、不发送帧。
- **R7-B / G5-B**：随后才启用 MDIO/RTL8211F。
- **R7-C / G6-A**：随后才 open interface 并验证 DMA。
- **R7-D / G6-B/G7**：最后做 ABCD 同帧 TX 和对端捕获。

R7-A 已知 probe 副作用（clocks、main-GRF RGMII mode/delay、SWITCH_REG1 regulator enable）是 GMAC 最后启用的直接理由。上述顺序不构成任何构建、写卡、启动或硬件操作授权。

## 11. 2026-11-28 G4-P2 runtime 通过后的 R7-prep 输入基线纠正（优先于本文旧表述）

本报告 §1、§2、§5、§6、§8、§9 中将 R7-prep DTB 描述为 G4-P0 binding-only（九路 supply 缺失）的旧内容，现由本节覆盖。原因：用户已完成 G4-P2 full-supply RAM-only 实机验证，IO-domain driver 成功 probe/bind；继续沿用 G4-P0 DTB 会主动丢弃刚刚验证通过的完整供电映射，没有合理性，也会令后续 R7-A 硬件候选的供电前置条件倒退。

**R7-prep 的冻结输入拆分为：**

1. Kernel config / source / compatibility patch：继续从 G4-P0 build artifact 派生，因为 G4-P2 复用同一 G4-P0 Image/config，且 G4-P2 实机已验证该 kernel config 下的完整 IO-domain probe。
2. DTB：必须从 G4-P2 PREPARE-ONLY artifact 的 boot/dtb/rockchip/rk3566-panther-x2.dtb 复制，固定 SHA256：
   41253336c0e69b7431e0d095573724c087734bb310143e1848d8da7639a7c9be。
   不得再从 G4-P0 artifact 取 DTB 作为 R7-prep 的最终 DTB。
3. R7-prep 的 DTB 必须原样保留 G4-P2 full-supply 状态：IO-domain child okay、九个 supply phandle 全部存在且与 G3 baseline 一致；GMAC1、MDIO、RTL8211F 仍 disabled；eMMC/TF SDMMC0/SDIO/GPU/SARADC 仍 disabled。
4. R7-prep 只增加 kernel config / built-in 软件对象，不改 DTB。R7-A/G5-A 以后只修改 GMAC1 parent status；九路 supply 和 IO-domain status 均保持 G4-P2 已验证值，不得删除 supply 属性或回退到 G4-P0 binding-only 状态。

因此本轮 build-only workflow 应同时下载 G4-P0 kernel build artifact 与 G4-P2 runtime package artifact，分别验证 Image/config 和 DTB 的哈希；R7-prep 输出的 Image 为新构建，最终 DTB 必须与 G4-P2 DTB 字节级相同。此修正不授权任何设备启动或 GMAC 操作。

### 更新后的状态

- G4-P2 PREPARE-ONLY：PASS。
- G4-P2 full-supply runtime：PASS-CONDITIONAL（rockchip-iodomain / rk808-regulator 绑定成功，九路 supply 可见；selector register readback 与物理 rail 未验证）。
- R7-prep static Kconfig/Makefile design：PASS。
- R7-prep build-only：NOT STARTED。
- R7-A/G5-A hardware probe：NOT AUTHORIZED / NOT RUN。
