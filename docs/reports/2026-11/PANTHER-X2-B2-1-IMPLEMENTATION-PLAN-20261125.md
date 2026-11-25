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
3. R0–R8 组件引入的精确 Kconfig/Makefile/对象依赖清单，以及 R7 最小 TX-only 原始 Ethernet 广播帧验收及 R8 后续逐层网络功能放行矩阵；
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
- **TX 测试夹具（R7 前置）：** R7 前只准备专用 AF_PACKET 原始帧发送程序和对端抓包工具；不提前加入 ping、完整 iproute2、DHCP/DNS 或其他上层工具。原先 R8-test-harness 的综合工具准备表述由 4B TX-first 规则取代。

### 4A.2 分层网络验收原则（由 4B TX-first 顺序具体化）

4A 的通用原则不再要求首轮做双向网络矩阵。第一项真实网络验收严格采用 4B 定义的 TX-only 原始 Ethernet 广播帧；只有 TX-PASS 后才逐项验证 RX、ARP、IPv4、ICMP、路由、TCP/UDP、DHCP/DNS。

每个阶段的证据必须匹配当前层级：TX 阶段以对端逐帧捕获为决定性证据；后续阶段才逐渐加入对应的接收端观察、协议报文和两端计数器。不能用后续层的工具或协议作为前置依赖，也不能用更高层测试失败倒推最底层 TX 故障。

### 4A.3 每次修改/替换的 A/B 规则

当实际网络测试失败时：
1. 冻结失败现场：源码 commit、配置、DTB、补丁、启动日志、link/PHY 状态、TX counters、驱动发送完成/错误统计、对端逐帧抓包及序列号结果；仅在进入相应后续层后才保存 ARP/ping/TCP/UDP 结果。
2. 根据失败所在层级选择唯一候选组件（TX 阶段例如 packet injection/net_device、STMMAC TX queue/descriptor/DMA、Rockchip clock/glue、RGMII/PHY；后续层才考虑 RX、ARP、IPv4 等）；候选优先级必须引用 B2-0 已归档的 A/B 级差异和适用条件。
3. 只对一个组件做修改或替换，明确代码 diff、配置 diff、理论作用路径和可证伪预期；禁止同时回移多个历史 workaround。
4. 使用完全相同的网络测试矩阵、端点和参数复测；同时保留改动前失败证据和改动后结果。
5. 只有实际双向数据与目标连通性改善且可重复，才能将该修改标记为“有实测收益”；否则回退并记录为未证实/无效，不得继续叠加。

### 4A.4 允许的诊断边界

- MAC loopback 只能证明 MAC/DMA 内部路径，不能替代 RGMII/PHY/线侧网络测试。
- PHY loopback 可覆盖 MAC↔RGMII↔PHY 内部回环，但不能证明 PHY MDI 线侧、磁性器件、网线和对端收包正常；而且会停止接口、reset GMAC/PHY，属于主动硬件操作，须单独授权。
- `phy_lb_scan` 会写入 GRF RGMII delay，不作为常规首测，只有前序证据指向时钟/时序边界且获得单独授权后才考虑。
- 不以 U-Boot 网络结果替代 Linux 网络验收，也不把 U-Boot 的异常直接推断为 Linux GMAC 根因。



## 4B. 实施方法再次修订：先 TX-only、逐项向外证明（2026-11-25）

用户明确要求网络组件不得一次性全部加入。第一项实机网络验收不是 DHCP、IP、ARP、ping 或双向网络，而是在最小必要网络组件集合下，Panther X2 发出的特定 Ethernet 测试帧/广播帧必须被局域网另一终端真实接收。该项通过后，才允许逐步引入后续网络组件。

**采用 TX-first、one-component-at-a-time 原则：**
1. 按 Kconfig/Makefile 依赖闭包逐个引入组件；每次构建差异只增加一个组件或不可拆分的最小依赖闭包。
2. 最小发送路径未闭合前，只做静态依赖和构建验收，不虚称已经验证网络发送。
3. 最小 TX 路径闭合后，第一项实机网络测试必须是无 IP 依赖的原始 Ethernet 测试帧发送；对端真实抓到正确帧才算 TX 通过。
4. TX 未通过时，不加入 ARP、IPv4、ICMP、DHCP、DNS、路由或其他更高层协议。先冻结证据，针对最近引入的唯一组件做单变量修正/替换，再重复相同 TX 测试。
5. TX 通过后，才按单组件增量顺序引入 RX 上层处理、ARP、IPv4、ICMP、路由、TCP/UDP，最后才考虑 DHCP/DNS。每一层均设置独立放行门。

### 4B.1 第一项外部发送测试

- Panther 不配置 IPv4 地址；不依赖 DHCP、DNS、ARP、ICMP 或默认路由。
- 使用专用最小发送程序通过 Linux packet socket（AF_PACKET/SOCK_RAW）发送自定义 EtherType 测试帧；建议使用本地实验 EtherType 0x88B5，payload 放入固定项目标识、递增序列号、长度和校验字段。
- 首轮目标 MAC 使用 Ethernet 广播地址 ff:ff:ff:ff:ff:ff，使同一二层广播域内的测试终端可观察；指定单播另作独立测试，不混在首轮。
- iMac 或另一台局域网终端使用现有抓包能力，在指定接口观察并过滤该 EtherType，记录时间、源/目标 MAC、序列号、长度及帧数量。对端抓包不要求 Panther 启用 promiscuous mode。
- 每个序列号必须由对端实际捕获并核对；仅 Panther TX counter 增长、驱动返回发送成功、DMA descriptor 完成或 PHY link up 均不构成通过。
- 先用另一台已知正常设备向同一对端发送相同格式测试帧，确认对端抓包路径、交换机广播域和过滤规则有效；这是测试夹具校验，不改变 Panther。
- 发送进程须具备 `CAP_NET_RAW`（测试 RAM 系统以 root 运行即可），优先单独构建专用静态 C 测试程序；确认 libc/静态链接依赖后再冻结产物，不为此引入完整 iproute2、DHCP/DNS 客户端、NetworkManager 或 tcpdump 到 Panther。

### 4B.2 TX-only 的技术边界

Linux 标准网卡发送路径至少需要网络核心、net_device、Ethernet framing、packet socket 或等价最小帧注入机制，以及 STMMAC/DWMAC4、Rockchip platform glue、DMA、时钟/复位、MDIO/PHY 和 DTB 硬件资源闭包。准确 Kconfig 符号和对象依赖必须以冻结的 6.18.63 源码逐项审计为准。

“TX-only”指测试目标和验收范围只考核发出帧能否到达对端，不代表驱动可以完全不初始化 RX descriptor：标准 net_device 的 open 路径可能同时准备 TX/RX ring，须通过源码确认。测试阶段不配置 IP，不要求 Panther 处理入站上层协议；对端抓包独立验证线侧发送。

组件静态准备仍按 R1–R6 依赖关系逐项推进，但这些阶段的构建通过不等于 TX 通过。硬件 DTB 节点恢复后先做 TX-only 实测；TX 通过之前，不得引入更高层网络协议组件。

### 4B.3 TX-PASS 与后续逐层放行

**TX-PASS 必须同时满足：**
- PHY 线侧 link、协商速率/双工及对端交换机端口状态有证据；
- 对端捕获 Panther 发出的自定义 EtherType 广播帧；
- 源/目标 MAC、EtherType、payload 标识、序列号、长度均正确；
- 多轮发送 N 帧，对端捕获数与预期一致；丢帧为零或差异已解释；
- Panther TX counters、驱动发送完成/错误统计与对端捕获相互印证；
- 全程无需 IPv4、ARP、ICMP、DHCP 或 DNS。

失败时按证据边界定位 net_device/packet injection → ndo_start_xmit → TX queue/descriptor/DMA mapping → MAC TX → RGMII → PHY → MDI/网线/交换机 → 对端抓包。此为定位框架，不预设根因；每轮只改一个组件。

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

**目标配置范围：** 以 6.18.63 精确 Kconfig 为准，先审查并逐步满足最小 Ethernet 发送路径所需的 `NET`、`NETDEVICES`、Ethernet 核心和 `PACKET`（AF_PACKET）依赖。`INET`/IPv4 不属于首轮 TX 测试前置项，必须留到 TX-PASS 后的 R8-IPv4 子阶段单独引入。

**边界：**
- GMAC1/MDIO/PHY DTB 节点继续 disabled；
- 不启用 STMMAC、DWMAC4、Rockchip GMAC glue 或 RTL8211F；
- 首轮不启用 `INET`/IPv4，不添加 ARP、ICMP、DHCP、DNS、SSH、ping、tcpdump 或完整 iproute2；
- B1 已存在的共享 SoC provider 不随网络核心一起改动。

**静态核验：** 精确记录每个新增符号的 depends/select/choice 关系、相关对象文件和最终 `.config` 差异。确认 B1 no-NET 兼容补丁在 `CONFIG_NET=y` 下的条件分支；不要把删除补丁与 NET 启用捆绑。如确需删除，另立单独变更。

**唯一变量：** 网络核心配置及其不可拆分的最小 Kconfig 依赖闭包。

**通过标准：** 配置收敛无 unmet dependency；构建成功；最小 Ethernet/packet socket 发送所需对象与预期一致；最终配置差异仅限批准闭包；`INET`/IPv4 尚未启用；GMAC/MDIO 仍未 probe。此处仅为 TX 基础组件准备通过，不是 TX 实测通过。

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

### R7 — 恢复 GMAC1/MDIO/PHY 硬件路径，并只做 TX-first 实测

**前置：** R0–R6 组件依赖闭包分别通过静态/构建验收；B1 完整验收通过；专用 TX 测试程序及对端抓包夹具准备完成；测试端点、线缆、交换机端口已确认；本步骤另行取得实机启动和发送测试授权。

**唯一变量：** 仅恢复目标 Panther X2 DTB 中 GMAC1、MDIO bus、PHY address 0 及其必要资源节点状态/引用。不得同时修改 Kernel commit、Kconfig、驱动源码、bootargs、initramfs 或发送程序。

**实施前静态核对：** GMAC1 compatible/reg/interrupt/clock/reset/GRF/pinctrl；RGMII interface/delay；MDIO bus/PHY address；PHY reset GPIO/timing；phy-supply 对 RK809 regulator 的引用；所有 phandle/provider；DTB 编译、反编译差异和哈希。

**实机步骤（严格顺序）：**
1. 只确认启动、platform probe、provider、MDIO、PHY attach 和 PHY link/协商状态；这些仅为 TX 前置条件，不是网络通过。
2. Panther 不配置 IPv4 地址、不启用 DHCP/ARP/ICMP；将接口置为驱动发送所需的最小运行状态，记录接口 MAC、carrier、TX/RX ring 初始化状态及计数器基线。
3. 对端先验证抓包夹具：另一台已知正常设备发送同格式测试帧，对端确认能捕获；随后标记 Panther 测试时间窗。
4. Panther 使用专用最小 AF_PACKET 原始帧发送程序，向 ff:ff:ff:ff:ff:ff 发送 EtherType 0x88B5 测试广播帧。payload 含固定项目标识、序列号、长度和校验字段。
5. 对端逐帧捕获并核对源 MAC、广播目标 MAC、EtherType、payload、序列号和帧数；同步采集 Panther TX counters、驱动发送完成/错误计数及对端接口计数。
6. 完成多轮、多个固定帧长度的重复发送；首轮不加入指定单播、IP 地址、ARP、ICMP、DHCP、DNS 或 TCP/UDP。

**TX-PASS 标准：** 对端真实捕获所有预期广播帧，帧内容和序列号完全匹配；多轮重复结果可复现；TX counter 与驱动完成/错误计数相符；丢帧为零或差异有可复核解释。只有对端真实收到才算发送成功。probe 成功、link up、TX counter 增长、驱动返回成功均不够。

**失败/停止：** 任一预期帧未被对端捕获或内容错误，立即停止；不得继续加入 RX 上层、ARP、IPv4、ICMP 或 DHCP。保存源码/配置/DTB 哈希、启动日志、PHY 状态、两端抓包、两端计数器和发送程序输出。依据最后成功边界只选择一个组件做修改/替换，重新执行相同发送矩阵。

### R8 — TX-PASS 后的逐层网络功能引入与验收

**执行时点：** 只有 R7 达到 TX-PASS 并归档后才允许启动。R8 不是一次性打开完整网络栈，而是后续各层的逐项放行总阶段；每个子阶段单独提交配置/构建/测试记录。

**固定递进顺序：**
1. RX 基础接收：先从对端向 Panther 发送带固定 EtherType/序列号的测试帧，证明帧到达 Panther MAC/RX DMA，并由驱动计数或最小内核观察点确认；不先加入 IP。
2. 二层协议处理：仅加入/验证所需 Ethernet protocol dispatch；再单独验证 ARP 请求/应答及邻居解析。
3. IPv4：此时才单独引入 `INET`/IPv4 配置，验证 IPv4 地址和本机协议处理；先同网段，不配置默认路由。
4. ICMP：单独验证同网段双向 ping；每次请求/响应都由两端证据确认。
5. 网关与路由：单独加入路由配置，再验证 hEX 网关；通过后才测已知外部 IP。
6. TCP 与 UDP：分别独立验证连接/报文及双向 payload，不能合并为一次通过。
7. DHCP、DNS：最后独立验证，不能作为底层 TX/RX 的替代证明。

**唯一变量：** 每个子阶段只引入一个网络组件、协议功能或不可拆分的最小依赖闭包。精确符号以 6.18.63 源码审计为准；不得因为某个 Kconfig select 自动打开其他功能就跳过配置 diff 和运行时验收。

**通过标准：** 当前子阶段专属测试报文/行为由对端或 Panther 端真实观察到，计数器/日志/抓包互相印证；只有当前层通过，才放行下一层。TX-PASS 作为永久回归测试，每次后续修改均须重跑 TX 广播帧测试，防止新增组件破坏已通过的发送路径。

**失败/停止：** 当前层未通过立即停止，不引入下一层；保存证据并只针对最近新增的组件提出单变量修正/替换。任何修改后至少重跑 TX 回归测试及当前层测试。

## 6. TX-first 阶段与原计划 B2.2 的衔接

R0–R6 是最小发送路径的组件依赖逐项准备；R7 是首次启用板载 GMAC 后的 TX-only 外部帧验收；R8 仅在 TX-PASS 后逐层引入 RX、ARP、IPv4、ICMP、路由、TCP/UDP、DHCP/DNS。不得将原计划 B2.2 理解为先启用完整网络再一次性综合测试。

每个层级都必须先定义专属测试报文/动作、对端观察点、计数器预期和失败边界。TX 广播帧是后续所有阶段的强制回归项。任何新组件导致 TX 回归失败，立即停止当前层并回到 TX 故障定位，不得继续叠加。

原计划 B2.2 中与家庭使用相关的 DHCP/DNS、持续传输和稳定性测试，安排在基础 Ethernet TX、RX、ARP、IPv4、ICMP 和路由逐层通过之后，仍须拆成独立测试，不得提前。

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
| MDIO/PHY/link/TX 帧发送失败 | 停止 R7 后续层级，保留双端日志、link 状态、TX counters、驱动统计及对端抓包；提出单变量下一步方案 | 越过失败层继续加入 RX/ARP/IPv4/ICMP/DHCP/TCP/UDP，或同时修改多个组件 |
| 意外触及 eMMC/其他存储 | 立即停止并报告目标设备、写入范围和影响 | 未经确认继续操作或自行进行破坏性恢复 |

回退只恢复到最后已知通过的资产，不删除失败报告、不覆盖原始日志、不改写历史证据。若构建工作流失败，应优先从失败步骤恢复并复用已验证 artifact；前提是依赖链、输入哈希和缓存身份可验证。

## 9. 进入后续网络层级的放行检查表

**TX 阶段放行门：**
- [ ] B1 完整实机验收正式归档；
- [ ] R0 基线资产及哈希冻结；
- [ ] R1–R6 各组件按最小依赖闭包逐项静态审查、构建并归档；
- [ ] 专用最小 AF_PACKET 测试发送程序构建并审计；
- [ ] 对端抓包夹具已由已知正常设备校验；
- [ ] R7 GMAC1/MDIO/PHY DTB 恢复及 probe/link 前置条件通过；
- [ ] Panther 未配置 IPv4/DHCP/ARP/ICMP 时发出 0x88B5 广播测试帧；
- [ ] 对端逐帧捕获并核验源/目标 MAC、EtherType、payload、序列号和长度；
- [ ] 多轮发送结果、TX counters、驱动统计与对端抓包一致；
- [ ] TX-PASS 证据归档，用户确认后才放行 RX 阶段。

**TX 通过后的逐层放行门：**
- [ ] RX 原始帧接收通过；
- [ ] ARP 独立通过；
- [ ] IPv4 同网段独立通过；
- [ ] ICMP 双向独立通过；
- [ ] 网关/路由及外部 IP 按顺序通过；
- [ ] TCP 独立通过；
- [ ] UDP 独立通过；
- [ ] DHCP、DNS 最后分别通过；
- [ ] 每次新增组件后 TX 广播帧回归仍通过；
- [ ] 每一层失败均停止、归档并只修改最近引入的一个组件；
- [ ] 每次拟执行的设备操作已取得明确授权。

任何未完成项均不得标记为通过；每一层放行均须有单独执行记录和授权。B2-1 计划本身不授权实机操作。

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
- R0–R8 尚未执行；本次明确 TX-first、专用原始 Ethernet 广播帧外部接收为首项实机网络验收，并规定 TX-PASS 后才逐层引入 RX/ARP/IPv4/ICMP/路由/TCP/UDP/DHCP/DNS；
- 原计划 B2.1 尚未启动。

本次归档不授权：访问 Panther X2、运行 U-Boot 命令、写入 TF/eMMC、启动实验固件、构建/安装内核、修改 Kconfig/DTB/驱动/网络配置、读写寄存器、启用 GMAC/MDIO/PHY、运行网络连通性测试。

**后续默认起点：** 先审阅并冻结本计划；随后回到 B1 完整验收剩余事项。只有 B1 通过后，才按本计划从 R0 开始，逐项放行。不得跳到 R1，更不得直接启动 R7 或原计划 B2.1。


## 4C. R2–R7 分段运行验收及数据流追踪修订（2026-11-25）

本轮将 R2–R7 从“静态配置/构建为主、R7 才首次集中验证”修订为逐层运行证据和独立放行门。原 R0–R8 顺序、R2–R6 GMAC/MDIO/PHY DT disabled 边界、R7 TX-first、R8 后续协议递进均保留。

**本次新增三份正式配套交付物：**

1. [R2–R7 详细实施计划与分段验收修订](PANTHER-X2-B2-1-R2-R7-DETAILED-IMPLEMENTATION-AND-GATED-ACCEPTANCE-PLAN-20261125.md)：逐阶段实施目标、直接/间接验证、最早验证时点、通过条件、失败停止规则。
2. [R2–R7 分段验收矩阵](PANTHER-X2-B2-1-R2-R7-GATED-ACCEPTANCE-MATRIX-20261125.md)：将每个组件、资源和数据交接映射到最早验证阶段及证据等级。
3. [TX ABCD 端到端数据流追踪协议](PANTHER-X2-B2-1-TX-ABCD-END-TO-END-DATA-PATH-TRACE-PROTOCOL-20261125.md)：以唯一测试 payload、run ID、sequence 和 hash 追踪 skb、DMA mapping、descriptor、DMA completion、MAC/PHY 及对端捕获。

### 新增的核心验收规则

- 每层组件即使配置、参数和编译正确，也必须考虑内部功能故障。
- 能在当前阶段安全验证的组件，必须尽早进行实际运行验证；暂时不能验证的组件标记 BLOCKED，并注明最早可验证阶段。
- 统一区分 PASS-STATIC、PASS-BUILD、PASS-REGISTER、PASS-PROBE、PASS-FUNCTIONAL、PASS-INTEGRATED、PASS-LINE。
- 原 R7 拆为 R7-A Platform Probe、R7-B MDIO/PHY、R7-C MAC/DMA open、R7-D 对端真实捕获 TX。
- TX 数据流采用“内容身份 + 地址引用 + 所有权交接”追踪。不是要求每层寄存器都存放 ABCD 原文：skb/buffer 中核对字节，DMA mapping/descriptor 中核对 DMA 地址、长度和 OWN 状态，DMA completion 中核对完成状态，最终由对端逐帧核对原始 payload。
- DMA completion、驱动 TX counter、PHY link 均不能替代对端真实捕获。
- 任一门失败或缺乏可靠观测方法，停止当前阶段；不叠加后续组件，不把观测不足误判为功能故障。
- 本轮没有修改 R1 产物、没有构建、没有操作 Panther、没有写入任何存储介质，也没有授权后续硬件操作。

**前置门不变：** B1 完整验收仍未正式通过。该修订只完善后续计划和验收方法，不提前启动 R0–R7。
