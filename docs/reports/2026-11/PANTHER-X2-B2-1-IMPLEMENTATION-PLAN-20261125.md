# Panther X2 项目 A：B2-1 实施计划与执行归档基准（2026-11-25）

- 阶段：B2-1（B2-0 决策落地的实施计划编制与冻结）
- 文档性质：后续执行依据；本文件本身不授权任何设备操作
- 上位依据：
  - `PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md`
  - `PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md`
  - `PANTHER-X2-B2-0-VERSION-AND-COMPONENT-RECOVERY-DECISION-PROGRESS-20261125.md`
- 当前状态：计划已建立；B2-1 的计划审查/冻结尚待后续逐项确认；B2.1 实机/网络组件引入未启动
- 适用范围：Panther X2 板载 GMAC1 千兆 Ethernet；不包括 Wi-Fi、蓝牙、USB/PCIe 外接网卡

> **重要命名边界：** 本文件的 B2-1 是 B2-0 决策后的“实施计划准备与冻结”工作阶段，不等同于原分阶段实施计划中的 B2.1 网络连通性实测子阶段。只有 B1 完整通过、B2-1 计划冻结、相关静态审查完成并取得逐次授权后，才可另行启动 B2.1。不得因本文件归档而自动开始实机操作。

---

## 1. B2-1 目标与交付

B2-1 不重新开展 B2-0 已完成的多版本审计，而是把其结论转换成可执行、可审计、可暂停和可恢复的步骤。

交付物必须包括：

1. 版本与源码输入冻结规则；
2. B1 基线资产清单及差异盘点表；
3. R0–R8 组件引入的精确 Kconfig/Makefile/对象依赖清单，以及 R7 真实网络双向收发验收矩阵；
4. 每一步唯一变量、构建产物、静态验收、实机验收和停止条件；
5. 失败后的回退点及证据保留要求；
6. 进入原计划 B2.1 的放行清单；
7. 后续每次执行可复用的记录模板。

本阶段不追求“尽快把所有网络组件打开”，而是确保每次变化可归因、可复现，任何失败都能准确定位到最近一次引入的组件边界。

## 2. 继承的版本决策

### 2.1 版本角色

| 版本/源码端点 | 在 B2-1/B2.1 中的角色 | 禁止误用 |
|---|---|---|
| Linux 6.18.63，`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f` | 当前 B1 连续基线候选；后续首轮网络配置变化尽量保持同一源码端点 | 不得称为已验证网络正常版本；不得与首次网络组件引入同时升级源码 |
| 6.1.65 | 第一黄金行为参照，已有原版系统有线网络正向实机证据 | 不整套复制其旧内核实现或补丁 |
| 6.1.116 | 第二黄金行为参照，历史稳定运行与配置证据 | 不作为 6.18 新系统底座 |
| 6.1.174-rk35xx | 已确认故障源码对照 | 不把它误称为首次回归点 |
| 6.12.81-rk35xx | 跨系列故障源码对照 | 不作为 6.18 目标底座 |

首轮保持 6.18.63 的源码 commit、工具链、补丁输入、架构、编译器及其他构建输入不变；任何必须变化的输入都要独立记录，并判断是否破坏单变量原则。若确需更换 6.18.y commit，必须先单独形成版本变更决策，不得与 R1–R8 的某一组件引入捆绑。

### 2.2 首轮补丁策略

首轮不主动回移以下历史差异：
- JL2xx1 PHYCR2/BMCR 四次 MDIO 写入或整字 `0x1801`；
- DMA reset 前 1500ms delay；
- Rockchip clock bulk enable、错误处理及 settle delay 历史实现；
- RGMII GRF 写入顺序；
- MDC CSR clock source 修改；
- PHY EEE、soft reset、speed status 读取等本地改动。

这些项目只进入“候选差异观察表”。只有对应阶段产生了明确、可复核的运行证据，才允许另立单变量补丁试验；不得一次性合并多个候选补丁。

## 3. 开始 B2.1 前置放行门

以下各项是进入网络组件实机引入的必要条件。未满足时停留在计划或静态审计阶段。

| 门 | 必须满足的条件 | 当前状态 |
|---|---|---|
| G1 B1 完整验收 | 6.18.63 Kernel、DTB、initramfs 启动链一致；`/init` 成功执行；UART BusyBox ash shell 可交互；必要基础命令可用；无 panic；B1 网络隔离条件逐项核实 | **未通过/证据不完整**。现有 Kernel banner 仅证明进入内核 |
| G2 资产锁定 | B1 Image、DTB、initramfs、bootargs、源码 commit、补丁、最终 `.config`、构建日志及 SHA256 均归档 | 构建与部分资产已有记录；完整验收包待补齐 |
| G3 B2-1 计划冻结 | R0–R8 顺序、各阶段依赖闭包、验收和停止条件经审阅，无未决的执行歧义 | 本文件已建立，待审阅冻结 |
| G4 静态依赖闭包 | 对 6.18.63 精确源码核对各阶段 Kconfig、Makefile、select/depends、对象文件及最终配置检查方法 | 已有 Kconfig/Makefile 审计报告；实施前按各阶段复核差异 |
| G5 逐次授权 | 每一次 TF 写入、启动或实机操作均有明确目标、步骤和授权 | 尚未取得任何 B2.1 操作授权 |

**eMMC 边界：** 不把全面 eMMC WP/Rescue 研究重新设为 B1/B2 阻塞项；但不得擅自写入或修改 eMMC。任何 eMMC 修改都必须单独说明目标、影响、备份/恢复方式和风险，并取得明确授权。若后续仅使用专用 TF，仍须在每次写卡前重新核对介质身份、容量、设备节点和挂载状态，并取得相应授权。

G1 未通过时，不允许用 6.1.65 的正常网络结果代替 B1 验收，也不允许以“B1 已经看到 Kernel banner”为由启动 R1。

## 4. 实施总纪律

1. 严格沿 R0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 顺序，不跳步、不并项。
2. 每个阶段开始前回读本计划、B2-0 决策报告、总路线图和该阶段涉及的原始审计报告。
3. 每次只改变一个配置项，或一个经证明无法拆分的最小依赖闭包；报告中必须列出闭包成员和不可拆分理由。
4. 除当前目标组件外，源码 commit、DTB、bootargs、工具链、initramfs、其他配置和测试环境保持不变。
5. 首轮优先 built-in（`=y`），避免模块装载顺序、modules tree 和 initramfs 模块装载成为额外变量。若确实只能使用 module，先暂停并单独论证，不得默默改变策略。
6. 每个阶段均执行“源码静态审查 → 配置差异审查 → 构建 → artifact 检查 → 经授权后实机验证”；不允许构建成功就直接宣布阶段通过。
7. 上一阶段未通过，停止后续阶段；不叠加下一组件，不通过临时补丁掩盖当前失败。
8. 失败时保留完整日志、配置、产物哈希和最后已知通过基线；回退到该基线，不覆盖唯一证据。
9. 不安装 DHCP、DNS、SSH、NetworkManager、systemd、udev、ping、tcpdump 等非当前阶段必需的服务或工具。R8 之前只使用当前 B1 已有能力。
10. 不触碰 Wi-Fi、蓝牙、USB/PCIe 外接网卡及其驱动、固件、协议或用户空间组件。


## 4A. 核心验收原则修订：网络真实连通优先（2026-11-25）

用户明确指出：此前完整安装的 Linux 6.18.63/6.18.64 系统仍出现网络不通，因此“配置启用”“内核构建成功”“驱动 probe 成功”“PHY 被识别”都不能作为项目成功标准。6.18.64 历史预编译包已知包含 NET/STMMAC/DWMAC_ROCKCHIP/PHYLIB/REALTEK_PHY 配置，但这些配置事实不证明 Panther X2 的实际数据面工作；同样，6.18.63 当前 B1 仅有 Kernel 启动早期证据，更不能推断网络能力。

**最高验收目标：Panther X2 的板载 GMAC1 必须真实完成双向 Ethernet TX/RX，并逐层通过 LAN、网关及所需外部 IP 连通性测试。** 对每个候选组件的配置、修改、替换或补丁，最终必须使用同一组固定端点、地址、报文和计数器测试进行 A/B 对照，证明改动前后实际网络行为变化；只改善日志或 probe 不算网络修复。

### 4A.1 两类验收不能混淆

- **R1–R6（硬件节点保持 disabled 的准备阶段）：** 由于 GMAC/MDIO/PHY 不 probe，物理网络不可能连通。这些阶段只能通过依赖闭包、构建产物和启动稳定性检查，结论必须标记为“组件准备通过”，不得标记为“网络通过”。
- **R7（GMAC1/MDIO/PHY 恢复后）：** 首次进入真实数据面验收。此后任何驱动、配置、DTB 或补丁的修改/替换，都必须回到固定网络测试矩阵完整复测，不得只看 probe 或单向 ping。
- **R8（最小测试工具）：** 工具必须在 R7 首次启用网卡前准备好；不能等到 R7 失败后才发现缺少 ping/ip/计数器读取能力。R8 的准备工作安排在 R6 之后、R7 之前；R7 完成真实网络验收后，再做 R8 的工具/结果复核。为避免阶段编号造成误解，执行记录要注明“R8-test-harness pre-stage”。

### 4A.2 固定网络测试矩阵（每次网络相关改动后重复）

测试参数不在计划中写死，执行前从当时 LAN 实际配置读取并由用户确认。固定同一条网线、同一 hEX LAN 端口、同一局域网测试主机和同一测试窗口；除当前唯一待测变量外不同时改变线缆、端口、地址、MTU、速率或测试端点。

| 层级 | 必测内容 | 通过证据 | 失败定位方向 |
|---|---|---|---|
| L0 物理/协商 | PHY link、速率、双工、autoneg 状态；确认目标预期为 1000M Full Duplex（若硬件/对端协商条件允许） | PHY/ethtool 或可用状态源、carrier、对端端口状态相互印证 | 供电、reset、PHY、时钟、RGMII、线缆/端口；不能以接口 UP 替代 |
| L1 MAC/驱动收发 | 接口启用后观察 TX/RX packets/bytes/errors/dropped；从 Panther 发起测试、对端确认收到；对端发回、Panther 确认收到 | 两端计数器均有对应增量；TX 与 RX 分别有正向证据；无持续增长的 errors/dropped | MAC/DMA descriptor、IRQ/NAPI、DMA mapping、RGMII/PHY 数据通道 |
| L2 同网段二层 | 配置不冲突的临时静态 IPv4；检查 ARP/neigh 双向解析；同网段测试主机双向 ICMP | ARP 请求/应答及邻居项正确；Panther→peer、peer→Panther 双向 ping 成功 | TX-only、RX-only、ARP、MAC 地址、广播/单播接收过滤 |
| L3 网关 | 同网段基础通过后，单独 ping hEX LAN 网关；检查 hEX 侧是否看到请求与响应 | Panther 与 hEX 双向 ICMP；hEX 侧邻居/MAC 对应正确 | 路由、ARP、网关 ACL/防火墙或 TX/RX 单向异常 |
| L4 外部 IP 路由 | 仅在 L3 通过后，以已知公网 IP 测试，不依赖 DNS | 外部 IP 可达，路由和回包证据完整 | 默认路由、hEX 转发/WAN 或上游，不把 DNS 混入 |
| L5 TCP/UDP | 选用局域网可控端点的 TCP 连接和 UDP 请求/应答；分别确认双向 payload，而非只看 socket 建立 | 应用端/对端日志与字节计数证明双向 payload；必要时抓包由对端完成 | MTU/校验和/offload、队列、协议栈或具体传输层 |
| L6 DHCP/DNS（可选独立功能） | 静态 IP/LAN/IP 路由稳定后再独立测 DHCP；DNS 单独测域名解析 | DHCP lease、DNS query/response 证据 | DHCP/DNS 服务本身，不得反向归因 GMAC 数据面 |

**关键判据：** 仅 Panther 本机 TX counter 增长不是物理发送成功；仅 hEX 收到请求但 Panther 未收到回复不是双向连通；仅 ping 成功一次也不足以宣布稳定。必须结合两端证据、双向计数器、重复测试与错误计数。若工具条件允许，优先在 hEX/iMac 等对端采集观察，不为抓包而提前在 Panther 增加庞大工具链。

### 4A.3 每次修改/替换的 A/B 规则

当实际网络测试失败时：
1. 冻结失败现场：源码 commit、配置、DTB、补丁、启动日志、link/PHY 状态、两端 counters、ARP/ping/TCP/UDP 结果。
2. 根据失败所在层级选择唯一候选组件（例如 PHY 初始化、Rockchip clock/glue、RGMII delay、STMMAC DMA/TX/RX、网络核心）；候选优先级必须引用 B2-0 已归档的 A/B 级差异和适用条件。
3. 只对一个组件做修改或替换，明确代码 diff、配置 diff、理论作用路径和可证伪预期；禁止同时回移多个历史 workaround。
4. 使用完全相同的网络测试矩阵、端点和参数复测；同时保留改动前失败证据和改动后结果。
5. 只有实际双向数据与目标连通性改善且可重复，才能将该修改标记为“有实测收益”；否则回退并记录为未证实/无效，不得继续叠加。

### 4A.4 允许的诊断边界

- MAC loopback 只能证明 MAC/DMA 内部路径，不能替代 RGMII/PHY/线侧网络测试。
- PHY loopback 可覆盖 MAC↔RGMII↔PHY 内部回环，但不能证明 PHY MDI 线侧、磁性器件、网线和对端收包正常；而且会停止接口、reset GMAC/PHY，属于主动硬件操作，须单独授权。
- `phy_lb_scan` 会写入 GRF RGMII delay，不作为常规首测，只有前序证据指向时钟/时序边界且获得单独授权后才考虑。
- 不以 U-Boot 网络结果替代 Linux 网络验收，也不把 U-Boot 的异常直接推断为 Linux GMAC 根因。


## 5. R0–R8 分阶段实施卡

### R0 — B1 基线资产冻结与盘点

**目的：** 建立唯一、可复现的网络功能引入起点，不改变任何网络组件。

**操作准备：**
- 记录源码仓库、commit、Makefile 版本、补丁列表与补丁顺序；
- 记录工具链、构建参数、架构、最终 `.config`；
- 记录 Kernel Image、Panther X2 DTB、initramfs、boot.scr/bootargs 的 SHA256；
- 记录 B1 已启用的 clock、CRU、pinctrl、GPIO、GRF、reset、syscon 等 provider 的最终配置和 built-in 对象；
- 记录 GMAC1、MDIO、PHY 节点的 status、引用关系及资源状态，确认仍处于 B1 隔离状态；
- 记录 B1 完整实机验收报告和最后已知可启动资产。

**特别复核：** B1 fragment 已显式包含 `COMMON_CLK`、`COMMON_CLK_ROCKCHIP`、`CLK_RK3568`、`PINCTRL`、`PINCTRL_ROCKCHIP`、`GPIOLIB`、`RESET_CONTROLLER`、`ROCKCHIP_GRF`。不得重复加入。 `GPIO_ROCKCHIP`、`MFD_SYSCON` 必须读取最终 `.config` 和对象清单，不可只根据 fragment/default/select 推定。

**唯一变量：** 无；纯盘点。

**通过标准：** 基线资产和哈希齐全；最终配置与对象清单可复查；B1 验收通过；GMAC/MDIO 隔离状态明确。

**失败/停止：** 任一资产无法识别、哈希不一致或 B1 状态不完整，停留 R0，不进入 R1。

### R1 — Linux 网络核心

**目标配置范围：** 以 6.18.63 精确 Kconfig 为准，审查并逐步满足 `NET`、`INET`、`NETDEVICES` 及实际必要 generic network-core 依赖。

**边界：**
- GMAC1/MDIO/PHY DTB 节点继续 disabled；
- 不启用 STMMAC、DWMAC4、Rockchip GMAC glue 或 RTL8211F；
- 不添加 DHCP、DNS、SSH、ping、tcpdump 或完整 iproute2；
- B1 已存在的共享 SoC provider 不随网络核心一起改动。

**静态核验：** 精确记录每个新增符号的 depends/select/choice 关系、相关对象文件和最终 `.config` 差异。确认 B1 no-NET 兼容补丁在 `CONFIG_NET=y` 下的条件分支；不要把删除补丁与 NET 启用捆绑。如确需删除，另立单独变更。

**唯一变量：** 网络核心配置及其不可拆分的最小 Kconfig 依赖闭包。

**通过标准：** 配置收敛无 unmet dependency；构建成功；网络核心对象与预期一致；最终配置差异仅限批准闭包；GMAC/MDIO 仍未 probe。

**失败/停止：** Kconfig 无法收敛、构建失败、意外引入网卡驱动/无线功能或其他无关对象时停止，保留日志，不进入 R2。

### R2 — B1 缺失的共享 SoC provider

**目标：** 仅补充 GMAC 路径实际需要且 R0 证明 B1 最终配置中缺失的 provider。

**候选核对范围：**
- `MFD_SYSCON`；
- `GPIO_ROCKCHIP`；
- 以及经 6.18.63 精确依赖链证明确实缺失的其他共享 provider。

已在 B1 中启用的 COMMON_CLK、Rockchip clock/CRU、pinctrl、GPIOLIB、reset controller、ROCKCHIP_GRF 不得重复加入或顺手改写。

**唯一变量：** 每个确实缺失的 provider，逐项引入；若依赖不可拆分，明确列出最小闭包。

**通过标准：** 最终配置和 built-in 对象与预期相符；provider 编译成功；没有恢复 GMAC/MDIO DTB 节点；不宣称网卡可用。

**失败/停止：** provider 缺乏明确 consumer、依赖来源不清或出现无关配置变化时停止，先补静态证据。

### R3 — PHY 电源 provider

**目标：** 为 Panther DTS 中 PHY 的 `phy-supply` 路径准备实际需要的 RK809 SWITCH_REG1 供电依赖。

**审查候选：** `I2C`、`I2C_RK3X`、`MFD_RK8XX`、`MFD_RK8XX_I2C`、`REGULATOR`、`REGULATOR_RK808`，最终以 6.18.63 精确 Kconfig/Makefile 为准。

**边界：**
- 不恢复 GMAC/MDIO/PHY 节点；
- 不对 PHY 进行运行时供电切换或寄存器操作；
- 不把 DWMAC Kconfig select 当作 PMIC/regulator 闭包已自动满足。

**唯一变量：** 经审计确认的 I2C/PMIC/regulator 最小依赖闭包；尽可能拆成可独立验证的子项。

**通过标准：** 配置、对象和 provider 依赖闭合；构建成功；无无关总线或外设被意外启用。

**失败/停止：** 依赖闭包无法解释、影响范围扩大或需改变 DTS/硬件供电策略时停止，另立决策。

### R4 — MDIO/PHY 通用基础设施与 RTL8211F

**目标配置候选：** `MDIO_BUS`、`OF_MDIO`、`PHYLIB`、`PHYLINK`、`REALTEK_PHY` 及其精确依赖。

**重点：**
- 明确 `REALTEK_PHY` 必须显式核对，不假定由 Rockchip DWMAC 自动 select；
- 分清 PHYLIB 与 PHYLINK 的依赖关系；
- 记录驱动对象、注册路径和 built-in/module 形态；
- 不恢复 PHY DTB 节点，不触发外接 PHY probe。

**唯一变量：** MDIO/PHY 框架或一个不可拆分的最小依赖闭包。

**通过标准：** 配置与对象闭包完整，编译成功，GMAC/MDIO 节点仍隔离。

**失败/停止：** 驱动被意外模块化、依赖缺失或出现无关 PHY 驱动时停止。

### R5 — STMMAC/DWMAC4 MAC 与 DMA core

**目标配置候选：** `STMMAC_ETH`、DWMAC4 相关配置和 6.18.63 实际选择的 core 对象。

**强制核对：**
- `STMMAC_ETH` 在该版本的 `ETHTOOL_NETLINK` 依赖；
- `PTP_1588_CLOCK_OPTIONAL`、`HAS_IOMEM`、`HAS_DMA` 等实际门槛；
- Kconfig select、Makefile 对象和最终 built-in 结果；
- 不照搬 6.12 vendor 专有的 `DWMAC_ROCKCHIP_TOOL`、`STMMAC_FULL` 等配置。

**边界：** GMAC/MDIO DTB 节点仍 disabled；不执行 TX/RX，不修改 DMA 算法或回移历史补丁。

**唯一变量：** STMMAC/DWMAC4 core 及不可拆分的精确依赖闭包。

**通过标准：** 构建成功，目标对象存在且形态符合计划，最终配置差异可解释；不以编译成功宣称 DMA 实机正常。

**失败/停止：** 缺少依赖、意外启用其他 MAC/外设或需要修改驱动源码时停止。

### R6 — STMMAC platform wrapper 与 Rockchip GMAC glue

**目标配置候选：** `STMMAC_PLATFORM`、`DWMAC_ROCKCHIP`、`PCS_XPCS_ROCKCHIP` 及其精确对象依赖。

**重点：**
- 核对 Panther 的 `rockchip,rk3568-gmac` compatible 匹配路径；
- 核对平台资源、clock/reset、GRF、pinctrl 与供电引用的依赖闭包；
- 记录 XPCS 编译依赖，但不得把 XPCS 被编译误判为 Panther RGMII 实际使用 PCS；
- 不调整 clock enable API、settle delay、GRF 写入顺序、MDC source 或 PHYCR2。

**边界：** GMAC/MDIO DTB 仍 disabled，不允许驱动 probe。

**唯一变量：** platform wrapper/Rockchip glue 配置及必要最小闭包。

**通过标准：** 构建对象和驱动匹配静态审查通过；无 DTB 恢复；无历史 workaround 回移。

**失败/停止：** 依赖引入必须修改多处驱动行为、时钟配置或 DTB 才能继续时，停止并提交独立决策，不在 R6 混合处理。

### R7 — 单独恢复 Panther GMAC1/MDIO/PHY DTB 节点并完成首次真实网络验收

**前置：** R0–R6 组件准备通过；B1 完整验收通过；R8-test-harness 已预备；测试端点与 LAN 参数已确认；本步骤另行取得实机启动和网络测试授权。

**唯一变量：** 仅目标 Panther X2 DTB 中 GMAC1、MDIO bus、PHY address 0 及其必要资源节点状态/引用的恢复。不得同时修改 Kernel commit、Kconfig、驱动源码、bootargs 或 initramfs。

**实施前静态核对：**
- GMAC1 compatible、reg、interrupt、clock/clock-names、resets、GRF、pinctrl；
- RGMII interface/delay 属性；
- MDIO bus 与 PHY address；
- PHY reset GPIO、reset timing；
- `phy-supply` 对 RK809 regulator 的引用；
- 所有 phandle/provider 均存在且状态正确；
- DTB 编译、反编译差异和哈希可复查。

**实机验收必须按顺序逐项执行，前一项通过后才进入下一项：**
1. 启动/probe：记录 platform probe、deferred probe、clock/reset/provider、regulator、MDIO 注册、PHY ID/attach；这一项只是进入数据面前提，不是网络通过。
2. 物理链路：确认 carrier、PHY link、速率/双工/autoneg；接口 UP 但无 carrier 判失败。
3. 双向 MAC 收发：固定对端发包/回包，核对 Panther 与对端 TX/RX packets/bytes/errors/dropped 增量；必须分别证明 Panther TX 到达对端、对端 TX 到达 Panther。
4. 静态 IPv4 与 ARP：仅配置一个经现场确认不冲突的临时地址，核对邻居解析及同网段 peer 双向 ping。
5. 网关：单独 ping hEX LAN 网关，核对 hEX 侧邻居和回包。
6. 外部 IP：仅在网关双向通过后，以已知公网 IP 验证路由；不依赖 DNS。
7. TCP/UDP：使用局域网受控端点，分别验证双向 payload，不以 ping 代替传输层验收。

每个步骤单独记录命令、退出码、两端观察、counter 前后值、丢包率和重复次数。任一步失败立即停在该层，不运行后续层级；保存完整现场并根据 A/B-规则选择一个组件进行静态定位。任何组件/补丁/DTB 变更后，从第 1 项重新执行同一固定矩阵，不允许只复测曾失败的单个命令。

**通过标准分级：**
- R7-PROBE：驱动/PHY probe 成功；仅为准备状态。
- R7-LINK：物理链路稳定、速率/双工符合预期；仍非网络连通通过。
- R7-LAN：双向 MAC 收发、ARP、同网段双向 ICMP 和网关双向 ICMP 均成功，counter 与对端证据一致；这是局域网基本连通通过。
- R7-IP：外部已知 IP 可达；这是 IP 路由连通通过。
- R7-TRANSPORT：TCP 与 UDP 双向 payload 均成功；这是基础传输层通过。

只有达到用户确认的最终目标级别才可宣布网络验收通过；单纯 R7-PROBE 或 R7-LINK 不得结项。

**失败/停止：** 任一供电、clock、reset、MDIO、PHY attach、link 或数据面层级失败，立即停止后续测试。不得加入无关组件、同时回移多个补丁或宣称网络正常。

### R8 — 最小网络测试工具与证据采集工具（测试准备必须先于 R7）

**执行时点：** R6 完成后、R7 恢复 GMAC DTB 节点之前，先完成本阶段工具准备；R7 真实网络验收后再完成工具输出与证据链复核。该安排是明确的阶段依赖例外：不允许因 R8 编号在 R7 之后，就让网卡首次启用时没有验证实际连通性的工具。

**最小工具范围：**
- BusyBox `ip`：只需支持 link/address/route/neigh 的查询和必要的接口启用、临时地址配置；逐项核验 applet 实际功能。
- BusyBox `ping`：用于同网段、网关和已知外部 IP 的 ICMP 验证。
- `/sys/class/net/<if>/statistics/*`、carrier、operstate 等内核 sysfs：读取 packets/bytes/errors/dropped；若 BusyBox `ip` 无法读取某字段，优先用已有 shell/cat，不扩大工具链。
- `ethtool` 仅在确认 link speed/duplex/autoneg 没有其他只读来源时，另行评估最小引入；不得与 ip 工具同时作为一个不可解释的变更。
- TCP/UDP 测试优先由局域网对端提供现有测试服务；若 Panther 端缺少客户端/服务端工具，单独论证最小实现，不默认引入 netcat、完整 iproute2 或抓包套件。

**禁止默认引入：** DHCP client、DNS、SSH、NetworkManager、systemd、完整 iproute2、tcpdump 及后台网络服务。DHCP/DNS 留作基础静态 IP 网络通过后的独立功能验证。

**唯一变量：** 优先单独启用 BusyBox ip applet；再单独启用 BusyBox ping applet；其他工具逐个审查，不能把整个工具集合打包成一次无差别变化。

**通过标准：** 在 RAM 系统中实际运行并证明所需子命令可用；测试工具不会改变网络状态（除明确安排的 ip link/address/route 子测试）；所有测试输出能与内核、对端日志及 counters 对照。

**失败/停止：** 工具依赖扩大、静态链接/架构不匹配或引入后台服务时停止，保留已通过的内核/驱动基线，不以工具失败归因网卡硬件。

## 6. R7 网络真实连通验收与原计划 B2.2 的衔接

R0–R6 只建立组件准备条件；R8 提前准备最小测试工具；R7 是首次真实网络数据面验收。不能把原计划 B2.2 延后到“所有组件都通过后再测”，而应在 R7 中按固定测试矩阵逐层实测。R7 的每次代码/配置/DTB 修改后都要从 L0 重新复测。

在 R7 的基础网络测试通过后，回到原分阶段实施计划 B2.2 继续完成尚未覆盖的独立功能项，顺序为：

1. 确认 RAM 中临时配置，重启不持久化；
2. 若家庭使用场景需要 DHCP，单独验证 DHCP discover/offer/request/ack 和 lease；不能用 DHCP 失败掩盖静态 IP 数据面，也不能用静态 IP 成功宣称 DHCP 通过；
3. 若需要 DNS，单独验证 DNS query/response；
4. 依据项目目标独立验证持续 TCP/UDP 传输、双向 payload、稳定时长和计数器；
5. 所有步骤都需固定端点和参数、保留两端证据，前一项通过才进入下一项。

任何一步失败都停止在该层，先根据双端证据定位方向，再提出一个组件/补丁/配置的单变量修改方案。不得一次性改动接口状态、地址、路由、MTU、offload、PHY 参数和驱动源码。

## 7. 每一步必须保存的证据

每个 R 阶段独立建立报告，至少保存：

- 阶段编号、日期、操作者和授权范围；
- 起始基线报告及其 commit/hash；
- 源码仓库/commit、补丁列表、工具链和构建参数；
- 变更前后完整 `.config`，以及可读 diff；
- Kconfig 依赖链、Makefile 对象映射和最终 built-in/module 清单；
- 构建日志、失败步骤、artifact 文件清单及 SHA256；
- DTB 是否变化及其反编译差异（R7 以外应保持不变）；
- 实机启动日志、UART 记录和只读状态输出（仅在授权后）；
- 通过/未通过结论、证据限制、下一步放行决定；
- 最后已知通过基线的恢复方式。

不得只保存“构建成功”截图或口头结论；必须保留能重新判断配置和产物身份的文本证据。

## 8. 故障停止与回退规则

| 故障类别 | 必须动作 | 禁止动作 |
|---|---|---|
| 配置无法收敛 | 保存 Kconfig 输出与差异，停止当前 R 阶段 | 同时打开多个配置直到编译通过 |
| 编译失败 | 保留完整日志、失败目标和输入哈希；从失败步骤修复并复用前序产物的策略仅限工作流已具备可验证缓存时 | 无条件全量重构或覆盖最后已知成功产物 |
| 启动失败/Kernel panic | 停止，恢复最后已知通过的 TF 启动资产；保存 UART 日志 | 继续叠加下一组件 |
| probe/deferred probe 错误 | 只围绕失败 provider/资源链做静态核对和最小只读取证 | 直接回移 PHY/clock/DMA 多个历史补丁 |
| MDIO/PHY/link 失败 | 停止 R7，保留日志和状态；提出单变量下一步方案 | 加入 ip 工具或启动 DHCP/报文测试 |
| 意外触及 eMMC/其他存储 | 立即停止并报告目标设备、写入范围和影响 | 未经确认继续操作或自行进行破坏性恢复 |

回退只恢复到最后已知通过的资产，不删除失败报告、不覆盖原始日志、不改写历史证据。若构建工作流失败，应优先从失败步骤恢复并复用已验证 artifact；前提是依赖链、输入哈希和缓存身份可验证。

## 9. 进入 B2.1 的最终检查表

只有全部满足，才可另行提出 B2.1 的具体操作计划：

- [ ] B1 完整实机验收正式归档；
- [ ] R0 基线资产清单及哈希冻结；
- [ ] R1 网络核心配置与构建验收通过；
- [ ] R2 缺失共享 provider 闭包验收通过；
- [ ] R3 PHY 电源 provider 闭包验收通过；
- [ ] R4 MDIO/PHY 框架与 RTL8211F 构建验收通过；
- [ ] R5 STMMAC/DWMAC4 core 验收通过；
- [ ] R6 Rockchip glue 验收通过；
- [ ] R8-test-harness 在 R7 前准备完成：ip/link/address/route/neigh、ping、TX/RX counters 可用；
- [ ] R7 GMAC1/MDIO/PHY DTB 恢复后，PHY link 与协商速率/双工有证据；
- [ ] R7 双向 MAC TX/RX 有 Panther 与对端 counters/日志相互印证；
- [ ] R7 同网段 ARP、双向 ICMP、网关双向 ICMP 全部通过；
- [ ] R7 已知外部 IP 路由通过（若项目验收范围要求）；
- [ ] R7 TCP/UDP 双向 payload 验证通过（若项目验收范围要求）；
- [ ] 每次网络相关修改均完成相同矩阵 A/B 复测；
- [ ] 原计划 B2.2 的 DHCP/DNS/持续传输等剩余独立项目已复核；
- [ ] 测试端点、LAN 参数、专用 TF 目标和恢复路径已确认；
- [ ] 每次拟执行的设备操作已取得明确授权。

该清单是阶段放行门，不得将未完成项标记为通过。B2.1 的实机动作必须另开执行记录，逐次报告，不由本计划自动授权。

## 10. 单阶段执行记录模板

每个 R 阶段复制以下模板，独立填写并归档：

```text
阶段编号：
阶段名称：
日期：
执行授权范围：
起始基线报告/commit：
源码 commit：
工具链/构建参数：
变更前 .config SHA256：
本阶段唯一变量：
最小依赖闭包及不可拆分理由：
Kconfig / Makefile 证据：
变更后 .config diff：
built-in/module 对象清单：
构建 workflow/run：
artifact 文件及 SHA256：
DTB 是否变化：
静态验收结果：
实机授权与测试条件：
实机日志/只读证据：
结论：PASS / FAIL / BLOCKED
证据限制：
最后已知通过基线：
回退方式：
下一阶段放行：YES / NO
```

## 11. 当前状态与明确禁止事项

截至 2026-11-25：

- B2-0 方向一至方向五静态审计及第一轮版本/组件决策已归档；
- 本文件建立 B2-1 实施计划框架，待用户审阅并冻结；
- B1 已有 6.18.63 Kernel banner/早期启动证据，但 `/init`、UART ash shell 和完整隔离验收尚未形成正式通过记录；
- B1 尚未正式通过；
- R0–R8 尚未执行；本次新增真实网络验收矩阵及 R8-test-harness 前置安排；
- 原计划 B2.1 尚未启动。

本次归档不授权：访问 Panther X2、运行 U-Boot 命令、写入 TF/eMMC、启动实验固件、构建/安装内核、修改 Kconfig/DTB/驱动/网络配置、读写寄存器、启用 GMAC/MDIO/PHY、运行网络连通性测试。

**后续默认起点：** 先审阅并冻结本计划；随后回到 B1 完整验收剩余事项。只有 B1 通过后，才按本计划从 R0 开始，逐项放行。不得跳到 R1，更不得直接启动 R7 或原计划 B2.1。
