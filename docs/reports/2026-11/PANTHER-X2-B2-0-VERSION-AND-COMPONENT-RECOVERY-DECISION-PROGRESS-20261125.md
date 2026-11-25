# Panther X2 B2-0：版本选择与组件恢复顺序决策（第一轮，2026-11-25）

- 文档阶段：B2-0 最终决策阶段
- 本轮范围：跨方向一至方向五的证据汇总、内核版本决策原则、故障候选排序、组件依赖与恢复顺序建议
- 当前状态：第一轮决策建议已形成；尚待逐项审议和最终冻结
- 权威上位文档：PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md
- 本文不授权：B2.1、设备访问、构建、安装、修改系统/内核/驱动/DTB/Kconfig/网络配置、读写寄存器或写入 TF/eMMC

## 1. 决策目标与约束

B2-0 原定最后阶段是：在方向一至方向五静态审计完成后，进行版本决策与组件恢复顺序整合。当前五个方向均已按证据边界完成归档，因此进入该阶段。

本阶段要回答：
1. 哪个内核版本/源码端点适合作为项目 A 后续网络验证的首轮候选；
2. 哪些历史版本只作为黄金基准或故障对照，不应直接作为新系统底座；
3. 各方向发现的真实差异，哪些应保留、哪些不应回移、哪些只能列为待验证候选；
4. B1 干净基线通过后，Linux 网络核心、板级共享依赖、MDIO/PHY、STMMAC/DWMAC4、Rockchip glue 和用户空间工具按什么顺序逐项引入；
5. 如何确保每次引入只有一个组件或最小依赖闭包发生变化。

### 1.1 强制原则

- 遵循项目 A 总路线和分阶段实施计划，尤其 B1.6“组件级分批验收与故障隔离门”。
- 只针对 Panther X2 板载有线千兆 Ethernet；Wi-Fi、蓝牙、USB/PCIe 外接网卡永久排除。
- 先驱动依赖、后用户空间工具；不预置 DHCP、DNS、SSH、NetworkManager、systemd、udev。
- 每次只引入一个组件或一个最小依赖闭包；失败即停，回到最近已验证基线。
- 不把静态源码差异写成硬件因果，不把源码候选端点写成历史 Image 精确构建来源。
- B2-0 决策只形成选择原则、风险排序和后续阶段门；不提前执行 B2.1。
- B1 尚未取得完整实机验收前，不允许进入任何网络组件的实机引入。

## 2. 证据基线：版本角色不变

### 2.1 四个固定历史比较样本

| 版本 | 历史角色 | 已知实机事实 | 源码证据等级 | 决策用途 |
|---|---|---|---|---|
| 6.1.65 | 黄金基准 A | 已确认正常；有原始镜像与 2026-11-24 有线 IPv4 正向实测 | unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc 为高置信度候选，未与历史 Image 精确绑定 | 早期正常行为参照；不能冒充精确构建源码 |
| 6.1.116 | 黄金基准 B | 历史稳定运行；网络基线、配置和日志已归档 | unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e 为固定比较端点；历史 Image 精确 source commit 绑定仍有限 | 主要正常行为参照；不直接复制整套代码 |
| 6.1.174-rk35xx | 故障基准 A | 已确认实机网络故障 | ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633，原始 Actions run #296/job #129816642520 的 source_hash 已闭环 | 6.1.y 已知故障源码对照；不是首次回归版本证明 |
| 6.12.81-rk35xx | 故障基准 B | 已确认实机网络故障 | ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c，原始构建来源已锁定 | 跨系列故障对照；不作为 6.18 目标源码替代 |

辅助正常实机样本 6.1.79、6.1.112 继续保留为历史行为证据；其源码/构建来源没有锁定前，不补造源码端点。

### 2.2 6.18.63 目标候选的特殊定位

项目 A 首轮 B1 精确源码候选：
- Repository：ophub/linux-6.18.y
- Commit：aee4e352a15d636cbc484f56819c6e59474dfd9f
- Makefile：Linux 6.18.63

6.18.63 曾有 Panther X2 实机启动及网络故障记录，但该历史预编译系统不等同于项目 A 从上述精确源码 commit、独立配置和最小组件集重新构建的系统。

**第一轮建议：**
- 继续以 Linux 6.18.y 为项目 A 目标系列；
- B1 继续使用已锁定的 6.18.63 精确源码候选，除非 B1 的构建/启动证据提出明确理由；
- B1 完整通过后，若进入 B2 首轮组件引入，优先保持同一源码 commit、同一 Kernel/DTB/启动链，只改变网络配置/组件；
- 不把 6.18.63 宣称为已知网络正常版本，也不因历史预编译包故障而直接放弃它；
- 更换到更新的 6.18.y commit 必须作为独立版本决策和单独变量，不与首次网络组件引入捆绑。

这项建议的目的，是固定可归因的实验基线，而不是断言 6.18.63 的网络驱动已经合格。

## 3. 跨方向真实差异与决策分类

### 3.1 A 级：必须保留为首轮风险输入，但不直接回移

| 差异 | 已确认事实 | 未验证事实 | 当前决策 |
|---|---|---|---|
| JL2xx1 四次 MDIO 写入 | 6.1.65/6.1.116 有；实际 6.1.174 c2f148d/6.12.81 无；位于 MDIO bus 注册后、后续 PHY setup/attach/config_init 前 | 写入是否成功、reset 后 PHYCR2 值、RXC/CLKOUT 波形 | 记录为高优先级候选；不恢复 magic writes，不制作 0x1801 补丁 |
| DMA reset 前 1500ms delay | 6.1.65/6.1.116 有；实际 6.1.174/6.12.81 无；与四次 MDIO 写入来自同一历史补丁族，但属于另一处调用 | 延时的硬件依据、reset 完成时间、时钟 ready 状态 | 独立记录为高优先级时序候选；不与 MDIO 写入捆绑恢复，不直接加入补丁 |
| Rockchip GMAC clocks enable 重构 | 黄金版本 bulk get/enable、检查错误并等待 5ms；故障源码逐项 get/enable、错误检查弱化并等待 100–200µs | 历史 clock enable 返回值、实际 rate/gate、硬件稳定时间 | 作为高优先级平台初始化候选；保留 6.18 上游实现，不盲目回移黄金 glue |
| RGMII GRF 写入顺序 | 黄金版本先写 CON0 delay value，再写 CON1 interface/enable；故障源码顺序反转；最终配置值相同 | 实际 MMIO 写事务、寄存器值和 RGMII 波形 | 保留为条件性时序候选；不只凭顺序不同认定错误 |

### 3.2 B 级：保留差异，等待对应证据

| 差异 | 已确认事实 | 适用性/限制 | 当前决策 |
|---|---|---|---|
| MDC CSR clock source | 黄金版本动态选择 stmmac_clk；6.1.174/6.12 选择 pclk_mac；Panther DTS 未固定 snps,clk-csr，动态分支会执行 | pclk_mac 频率、MDC divider 和实际波形未知 | 不改写目标配置；作为 MDIO 时序候选记录 |
| PCLK_USB critical / ACLK_USB parent chain | 后期 CRU provider 将 PCLK_USB 标为 critical；其 parent ACLK_USB 与 GMAC1 共用；若 parent 为 GPLL 且 enable ref 为 0，存在条件性 callback 联动 | 历史 mux parent、enable_count、provider 注册顺序未知；HCLK_USB 不在 GMAC1 parent chain | 不改 CRU flags；只保留条件链，禁止推断为根因 |
| TX queue/watchdog 内存序 | 6.1.116 相对 6.1.65 增加配对 WRITE_ONCE/READ_ONCE 与 memory barrier；6.1.174/6.12 延续 | 需要 queue stop/STACK_XOFF/DRIVER_XOFF、trans_start、watchdog 时间序列才可判断历史命中 | 保留较新的内存序实现；不回退到 6.1.65 |
| PHY 初始化与 EEE | 四个历史版本普通 CG config_init 主体相近；6.18.63 单独清 PHYCR2 bit5，不等同整字 0x1801 | 6.18 实际 PHYCR2、LPI 与 MAC 配合效果未知 | 首轮不增加本地 PHY patch，保留 6.18 上游默认行为 |

### 3.3 C 级：不作为普通 DHCP 首发故障的首轮改动目标

- 6.1.65 的 TSO 多 descriptor DMA mapping bookkeeping 风险在 6.1.116 已修复；普通 DHCP 单 skb 不命中 TSO。
- TX coalescing timer 1000µs→5000µs 影响完成回收/调度时序，不直接改变首个 skb 的 descriptor 发布。
- 6.12 unreadable-fragment TX drop 门需要特殊 unreadable/net_iov backing；没有历史 DHCP skb 命中证据。
- 6.12 EST max-SDU、VLAN TSO、AF_XDP metadata 等需要特定配置/报文条件，当前 Panther 普通 DHCP 路径不命中。
- PHYLIB PHY_ERROR、EEE/LPI、PHYLINK link_failed、WOL、LED、optional PHY clock 主要属于错误、EEE 或 PM/可选 DT 条件路径；不能外推为普通冷启动 TX 的无条件回归。
- generic network-core 普通 IPv4 UDP 单 skb 路径未发现足以解释故障版本普通 DHCP 失败的已证实、无条件触发回归。

## 4. 第一轮内核版本决策建议

### 决策 V1：不以历史 6.1.116 作为新系统代码底座

理由：
1. 项目 A 目标系列已固定为 Linux 6.18.y。
2. 6.1.116 只提供正常行为基准，不是当前目标系列。
3. 历史 6.1.116 Image 与精确构建源码 commit 的绑定仍有限制。
4. 6.1.116 含有 0x1801 等需要谨慎解释的历史 workaround，不能把整套旧实现等同于正确实现。
5. 整体回退会同时改变网络核心、STMMAC、Rockchip glue、PHYLIB/PHYLINK 和板级依赖，破坏单变量归因。

**建议状态：采纳。** 6.1.116 作为 golden reference，不作为直接底座或整套 cherry-pick 来源。

### 决策 V2：6.18.63 精确源码作为首轮连续基线候选，最终网络版本尚不锁死

理由：
- 它是项目 A 当前 B1 精确源码候选；
- 同一 commit 可用于 B1 clean build 与后续首轮 B2 组件引入，减少 Kernel/DTB 版本变量；
- 历史 6.18.63 预编译系统的故障记录不能直接证明项目 A 精确源码与最小配置组合必然失败；
- 但它也不是网络已验证的版本。

**建议状态：暂定采纳，需以 B1 完整通过为前置条件。** 不在本轮更换 commit，不把该建议解释为允许启动 B2.1。

### 决策 V3：首轮不对 6.18.63 的 STMMAC、Rockchip glue、MDIO/PHY 驱动做历史补丁回移

尤其不：
- 恢复 0x1801 整字写入；
- 直接加入 1500ms DMA reset delay；
- 直接将 clock enable 代码改回 bulk API；
- 直接改变 glue settle delay；
- 直接调整 RGMII GRF 写入顺序；
- 直接改变 MDC CSR source；
- 直接修改 PHY EEE、soft reset 或 speed status 读取方式。

这些项目需要先在保持 6.18.63 原始上游实现的情况下，按层引入并建立实际行为边界。若后续出现明确证据，只允许针对一个差异建立独立 patch/试验。

**建议状态：采纳。**

## 5. 组件恢复顺序建议

本节是 B1.6 的依赖顺序细化建议，不是 B2.1 执行清单。所有网络组件实机引入均须在 B1 完整通过、对应静态配置审查和用户另行授权后执行。按用户 2026-11-22 已明确收敛的 eMMC 风险边界，不再把全面 eMMC WP/Rescue 或证明所有早期 bootloader 写路径绝对安全作为 B1/B2 的通用前置阻塞项；本项目仍不得擅自写入 eMMC，任何 eMMC 修改都必须另行说明并取得明确授权。

### 5.1 先做 B1 基线资产差异盘点，不改变任何组件

进入网络组件引入前，先冻结：
- B1 Kernel 源码 commit、最终 .config、Image 哈希；
- Panther X2 clean-test DTB、DTB 哈希与 GMAC/MDIO 节点状态；
- initramfs、BusyBox、bootargs、JP proper 与启动链；
- 当前已启用的 SoC pinctrl、GPIO、clock、syscon、reset 等 provider；
- B1 实机验收结果。

**目的：** 防止把 B1 已有的启动依赖误算成新引入组件，也防止因网络隔离误关闭 UART/SoC 启动依赖。

B1 未通过时，停留在 B1，不开始网络组件恢复。

### 5.2 建议的实验引入顺序

| 顺序 | 组件/最小依赖闭包 | 6.18.63 配置/对象重点 | 引入时 DTB/设备状态 | 验收边界 |
|---|---|---|---|---|
| R0 | 冻结 B1 资产与当前已启用 provider 清单 | 不改 .config | GMAC/MDIO 保持隔离 | 仅静态核对与基线归档 |
| R1 | Linux 网络基础：NET、INET、NETDEVICES 及实际必要 generic core | 以 6.18.63 精确 Kconfig 为准 | GMAC 仍 disabled，不启用网卡 probe | 配置、依赖、构建闭包检查；不做收发 |
| R2 | 只补齐 B1 最终配置中确实缺失的共享 SoC provider | B1 fragment 已明确包含 COMMON_CLK、COMMON_CLK_ROCKCHIP、CLK_RK3568、PINCTRL、PINCTRL_ROCKCHIP、GPIOLIB、RESET_CONTROLLER、ROCKCHIP_GRF；GPIO_ROCKCHIP 与 MFD_SYSCON 的最终值仍须从实际最终 .config 核验 | GMAC 仍 disabled | 不重复引入已在 B1 启用的 provider；只对最终配置中缺失且 Panther GMAC 路径确实需要的符号建立最小依赖闭包 |
| R3 | PHY 电源 provider 闭包 | Panther phy-supply 指向 RK809 SWITCH_REG1；核对 I2C_RK3X、I2C、MFD_RK8XX_I2C、MFD_RK8XX、REGULATOR、REGULATOR_RK808 | GMAC 仍 disabled | 分别检查 I2C/PMIC/regulator provider；不得把 DWMAC Kconfig select 当作供电闭包已自动满足 |
| R4 | MDIO/PHY 通用基础设施与 RTL8211F 驱动 | MDIO_BUS、OF_MDIO、PHYLIB、PHYLINK、REALTEK_PHY；其中 REALTEK_PHY 必须显式核对，不能假定自动 select | GMAC 仍 disabled；暂不触发外接 PHY probe | Kconfig/Makefile/对象闭包与最终 built-in/module 状态检查 |
| R5 | STMMAC/DWMAC4 MAC/DMA core | STMMAC_ETH、DWMAC4 相关对象及其完整 Kconfig select 闭包；6.18.63 必须满足 ETHTOOL_NETLINK、PTP_1588_CLOCK_OPTIONAL、HAS_IOMEM、HAS_DMA 等门槛 | GMAC 仍 disabled | 构建对象与符号依赖检查；不执行网卡收发 |
| R6 | STMMAC platform wrapper 与 Rockchip GMAC glue | STMMAC_PLATFORM、DWMAC_ROCKCHIP；同时核对 PCS_XPCS_ROCKCHIP 编译闭包 | GMAC 仍 disabled | Panther rockchip,rk3568-gmac 驱动匹配与依赖静态核验；XPCS 被编译不等于 RGMII 运行时使用 XPCS |
| R7 | 单独恢复 Panther GMAC1/MDIO/外接 PHY DTB 节点 | 不再同时更换 Kernel/驱动/config；只改变目标 DTB 节点状态这一项 | 启用板载 GMAC1、MDIO bus、PHY address 0 与必要资源描述 | 先检查 probe/deferred-probe、供电、clock、reset、MDIO/PHY attach、link；未通过立即停止，不加入 ip 工具 |
| R8 | 最小只读 ip 工具 | 优先评估 BusyBox ip，缺功能才单独加入上游 iproute2 所需部分 | 保持已通过的 Kernel/DTB/驱动组合 | 只读接口、carrier、MAC、地址、路由查询；通过后才进入 B2.2 后续独立动作 |

说明：
- R1～R8 是实验顺序，不是 Linux 内核启动时的 driver probe 顺序；设备依赖可能触发 deferred probe，实际 probe 顺序以日志为准。
- 每个 R2/R3 provider 子项都要先与 B1 当前 .config 对照，已经存在且已验证的组件不重复引入。
- R4～R6 在构建配置上有 Kconfig select 依赖，必须保存最终 .config 与对象闭包；不能把一个 select 推断成全部 Panther DTS provider 均已具备。
- 如果某个阶段必须一次启用一个不可再拆分的最小依赖闭包，报告中须列明闭包成员、为什么不能继续拆分、唯一变量是什么。
- 首轮目标链建议优先 built-in，以避免模块加载顺序、模块版本/依赖和 initramfs 装载成为额外变量；若某组件只能作为 module，必须单独列出装载依赖和验收步骤，不能混用两种策略。
- 用户空间工具永远在网络核心和驱动闭包完成后加入；不把 ip、ping、DHCP 客户端或 tcpdump 提前放进 B1。

### 5.3 6.18.63 特别 Kconfig 决策

以下配置不能漏项或错误推断：

1. STMMAC_ETH 在 6.18.63 新增 ETHTOOL_NETLINK 依赖；最终 .config 必须显式满足。
2. REALTEK_PHY 不由 DWMAC_ROCKCHIP 自动选择；必须显式启用。
3. Panther PHY supply 是 RK809 SWITCH_REG1，PMIC/I2C/regulator provider 不会由 DWMAC Kconfig 自动闭合。
4. PHY reset GPIO 走 GPIO descriptor/GPIOLIB；GMAC CRU reset 走 RESET_CONTROLLER/softrst；二者必须分开核对。
5. DWMAC_ROCKCHIP 选择 PCS_XPCS_ROCKCHIP 是编译闭包；Panther 当前仍是 RGMII 外接 PHY，不因此变成 SGMII/PCS 数据路径。
6. 6.12 的 DWMAC_ROCKCHIP_TOOL、STMMAC_FULL 等 vendor 专有配置不能照搬到 6.18.63。
7. MFD_RK8XX_I2C / MFD_RK8XX / REGULATOR_RK808 是 6.18.63 实际 PMIC provider 依赖，不能沿用旧版 Kconfig 名称想当然。


### 5.4 B1 已有共享 provider 的复用核对（2026-11-25）

本轮直接回读当前仓库的 scripts/panther-x2-b1/kernel.config.fragment 与 scripts/panther-x2-b1/verify-b1-config.sh，发现 B1 并非把所有 SoC provider 都关闭。为保障 UART/SoC 启动，B1 已明确启用以下共享基础设施：

| 配置符号 | B1 fragment 状态 | 对后续 GMAC 依赖的意义 |
|---|---|---|
| CONFIG_COMMON_CLK | y | 通用 CCF 基础 |
| CONFIG_COMMON_CLK_ROCKCHIP | y | Rockchip clock provider |
| CONFIG_CLK_RK3568 | y | RK3568/RK3566 CRU clock provider |
| CONFIG_PINCTRL | y | 通用 pinctrl 框架 |
| CONFIG_PINCTRL_ROCKCHIP | y | Rockchip pinctrl provider |
| CONFIG_GPIOLIB | y | GPIO descriptor 基础设施 |
| CONFIG_RESET_CONTROLLER | y | CRU reset framework |
| CONFIG_ROCKCHIP_GRF | y | Rockchip GRF provider |
| CONFIG_GPIO_ROCKCHIP | fragment 未显式设置 | 最终 .config 值待核验；不能仅凭 Kconfig default 推定 |
| CONFIG_MFD_SYSCON | fragment 未显式设置 | 最终 .config 值待核验；6.18.63 STMMAC/平台驱动依赖闭包需核对 |

因此，R2 不应被执行成“重新加入全部 clock/pinctrl/GPIO/reset/GRF”。正确动作是先读取 B1 构建 artifact 的最终 .config 和 built-in 对象清单，以已存在的 provider 为基线，只补实际缺项。特别是 GPIO_ROCKCHIP 与 MFD_SYSCON，不能只看 fragment，也不能把 Kconfig default/select 直接当作最终配置事实。

这也意味着：
- R1 网络核心启用时不应顺带修改上述已在 B1 存在的 provider；
- 后续 R2 若需要增加 GPIO_ROCKCHIP 或 MFD_SYSCON，必须作为单独配置闭包并说明实际 consumer；
- B1 中 GMAC/MDIO 节点仍 disabled，provider 已编入并不等于 GMAC 已 probe，也不构成网络功能已验证；
- B1 clean-test DTB 继续禁用 GMAC/MDIO，不能为了“提前验证 provider”而同时恢复网卡节点。

### 5.5 B1 no-NET 兼容补丁的过渡处理

B1 当前 6.18.63 构建输入包含 0001-kobject-uevent-config-net-n.patch，其目的仅是解决 CONFIG_NET=n 时 uevent stub 的编译依赖。进入未来 R1（启用 NET）时：
- 先核对补丁修改的条件编译分支在 CONFIG_NET=y 时是否完全不参与编译；
- 不要在同一次 R1 变更中顺手删除补丁、升级源码或调整其他组件；
- 若补丁在 CONFIG_NET=y 下为无效条件分支，可暂时保持相同源码输入，以减少变量；若源码审计证明必须移除，则把移除补丁作为独立、可审计的源代码输入变化，不与 NET 配置启用捆绑。

当前未执行上述配置转换或补丁修改。

## 6. 当前明确不采纳的方案

| 方案 | 决定 | 原因 |
|---|---|---|
| 直接回退到 6.1.116 整套内核/驱动 | 不采纳 | 与 6.18.y 目标冲突，且一次改变多个层级，破坏可归因性 |
| 把 6.1.65 当作精确源码真值 | 不采纳 | 只有高置信度候选端点，未绑定历史 Image |
| 把 6.1.174 宣称为 6.1.y 首次故障版本 | 不采纳 | 6.1.117～6.1.173 缺少逐版本实机证据 |
| 把 0x1801 当成无害 CLKOUT 修复并回移 | 不采纳 | 完整位域有 RXC/EEE/保留位副作用，且与 6.1.116 正常基线存在未解矛盾 |
| 一次性恢复所有网络栈、PHY、GMAC、工具 | 不采纳 | 违反 B1.6 单变量/失败即停原则 |
| 先加入 DHCP/DNS/SSH/tcpdump | 不采纳 | 不是 B2 基础静态连通性前置条件，会增加用户空间变量 |
| 因 6.12.81 发生故障而直接复制/排除 6.12 全部代码 | 不采纳 | 6.12 与 6.18 不是同一目标版本；必须按 Panther 实际路径和条件分支判断 |
| 将 U-Boot JP proper DHCP Data Abort 当作 Linux 网卡硬件故障证据 | 不采纳 | 该记录只证明 U-Boot EQOS DMA reset 附近异常退出，没有 DHCP 往返或 Linux 驱动证据 |

## 7. 后续仍需完成的决策项

本轮先形成了版本定位和组件引入顺序建议；下列项目尚需在 B2-0 决策阶段继续逐项冻结：

1. **版本决策正式冻结：** 用户确认 6.18.63 精确源码作为 B1 与首轮 B2 连续候选；明确更新到更高 6.18.y 的独立触发条件。
2. **B1 基线状态核实：** 以当前仓库最新构建/实机报告为准，确认 /init、UART shell、DTB、initramfs、eMMC 安全门状态；不能以 Kernel banner 单独宣称 B1 通过。
3. **R2/R3 依赖分拆：** 从 6.18.63 Kconfig 与 B1 最终 .config 做差异表，识别哪些 provider 已存在、哪些必须新增、哪些是共享启动依赖。
4. **R4～R6 构建闭包冻结：** 明确每个 Kconfig 符号、Makefile 对象、built-in/module 选择和 DTB 触发关系。
5. **候选差异追踪表：** 对 A/B 级候选分别标明未来哪一个阶段可能产生证据；不得提前写补丁。
6. **B2.1 阶段门：** 只有 B1 完整通过、静态差异表归档，并对任何拟进行的 TF 写入/实机启动取得相应逐次授权后，才可另行提出 B2.1 计划。不得把已被用户明确取消的全面 eMMC WP/Rescue 研究重新设为阻塞条件。

## 8. 本轮结论与阶段状态

### 已形成的第一轮建议

- 目标系列保持 Linux 6.18.y。
- 6.18.63 精确源码继续作为 B1 基线和首轮 B2 连续候选，但不是已知网络正常版本。
- 6.1.116 只作为主要黄金行为参照，不整套回退或复制。
- 不盲目恢复历史 PHYCR2 magic write、DMA 1500ms delay、clock enable/settle 或 GRF 顺序补丁。
- 后续按“网络核心 → 缺失的共享 SoC provider → PHY/MDIO → STMMAC/DWMAC4 → Rockchip glue → 单独恢复 GMAC1 DTB → 最小只读 ip 工具”的依赖顺序形成单变量试验计划。
- 首轮优先 built-in，避免模块加载顺序引入额外变量；最终以精确 Kconfig/Makefile 和依赖审计为准。
- 不把任何静态差异认定为 TX 根因。

### 状态

**B2-0 决策阶段第一轮已完成；最终决策尚未冻结。**

本轮仅回读仓库内路线图、实施计划、方向一至方向五报告及 6.18.63 Kconfig/Makefile 审计，形成决策建议。没有访问 Panther X2，没有构建、安装、触发 Actions，没有修改系统/驱动/DTB/Kconfig/网络配置，没有读取或写入设备寄存器，没有写入 TF/eMMC，没有启动 B2.1。

下一步严格继续本决策阶段的剩余项，不提前进入 B2.1。


### 5.6 B1 当前进度与安全门边界校正（2026-11-25）

回读 B1 实施记录和 eMMC 安全报告，并结合当前对话已提供的 6.18.63 启动日志，必须区分以下状态：

| 项目 | 当前证据 | 决策状态 |
|---|---|---|
| B1 clean-RAM CI/artifact | #37/#38 构建成功；PREPARE-ONLY artifact 与文件哈希已核验 | 已完成构建/静态产物层，不等于实机通过 |
| SU08G 8GB TF | 已写入专用卡，2 GiB 镜像回读 SHA 与源镜像一致，GPT 备份表位置已修复 | 介质准备已完成；后续写卡仍需按现场目标身份重新核对 |
| 6.18.63 Kernel 启动 | 当前对话已见 Linux 6.18.63 kernel banner/早期启动日志 | 只证明已进入内核；尚不能据此宣布 /init、initramfs handoff、BusyBox ash shell 全部通过 |
| B1 完整验收 | 尚缺完整 /init 执行、UART ash shell、所有隔离条件和无 panic 的完整验收记录 | **B1 尚未正式通过** |
| eMMC 全面 WP/Rescue | 用户已于 2026-11-22 明确停止把全面 eMMC 写保护、Rescue 和早期 bootloader 写路径绝对安全研究作为 B1 阻塞项 | 不再作为 B1/B2 通用阻塞条件 |
| eMMC 修改 | 当前研究原则仍是不擅自写 eMMC；如确需修改，必须说明目标、原因、恢复方式和风险并取得明确授权 | 保持禁止，除非另行授权 |

因此，第一轮决策可以冻结版本角色和候选差异排序，但任何 R1–R8 网络组件实机引入都必须等待 B1 完整验收。下一步优先完成 B1 当前启动链的最小剩余验收，而不是恢复 eMMC WP 研究，也不是启动 B2.1。
