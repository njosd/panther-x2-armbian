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
3. R0–R8 组件引入的精确 Kconfig/Makefile/对象依赖清单；
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

### R7 — 单独恢复 Panther GMAC1/MDIO/PHY DTB 节点

**前置：** R0–R6 全部通过；B1 验收有效；对应驱动/供电/时钟依赖静态闭合；本步骤另行取得实机启动授权。

**唯一变量：** 仅目标 Panther X2 DTB 中 GMAC1、MDIO bus、PHY address 0 及其必要资源节点状态/引用的恢复。不得同时修改 Kernel commit、Kconfig、驱动源码、bootargs 或 initramfs。

**实施前静态核对：**
- GMAC1 compatible、reg、interrupt、clock/clock-names、resets、GRF、pinctrl；
- RGMII interface/delay 属性；
- MDIO bus 与 PHY address；
- PHY reset GPIO、reset timing；
- `phy-supply` 对 RK809 regulator 的引用；
- 所有 phandle/provider 均存在且状态正确；
- DTB 编译、反编译差异和哈希可复查。

**实机观察范围：** 只采集启动与 probe 证据：platform probe、deferred probe、clock/reset/provider 错误、regulator、MDIO bus 注册、PHY attach、link/carrier 状态。按日志证据逐步观察，不运行 DHCP、ARP、ICMP、TCP 或 UDP。

**通过标准：** 驱动 probe 与资源获取无未解释错误；MDIO/PHY 可被识别并完成 attach；link 状态有明确证据。若链路未建立，不得把“驱动已 probe”写成网络通过。

**失败/停止：** 任一供电、clock、reset、MDIO、PHY attach 或 link 环节失败，停止在 R7；不加入 ip 工具，不回移多个补丁，不进入网络报文测试。只允许针对失败边界提出下一轮静态分析或单变量方案。

### R8 — 最小只读网络观察工具

**前置：** R7 达到预先定义的驱动/PHY 验收标准并归档。

**候选：** 优先评估 B1 BusyBox 是否可通过单独配置提供所需 `ip` 子命令；若能力不足，再单独评估上游 iproute2 的最小构建。不可同时引入两套工具。

**严格限制：**
- 本步骤只加入只读观察能力；
- 允许范围以接口列表、链路/carrier、MAC、地址、路由读取为主；
- 不加入 DHCP client、DNS、SSH、NetworkManager、ping、tcpdump 或后台网络服务；
- `ip link set`、地址配置、路由变更等写操作不属于 R8。

**唯一变量：** BusyBox ip applet 配置，或独立 iproute2 最小构建，二者择一。

**通过标准：** 工具在目标 RAM 系统运行，读取结果与内核日志相互印证；不改变网络状态。

**失败/停止：** 工具依赖扩大或引入额外服务时停止，回到工具选择，不改变已通过的内核/驱动基线。

## 6. R8 之后与原计划 B2.1 的衔接

R0–R8 完成并不等于整个网络连通性测试完成。R8 只提供最小只读观察工具。后续必须回到原分阶段实施计划的 B2.2 单项试验顺序，按原有边界逐项执行，不得把多个动作合并：

1. 只读检查接口与 carrier；
2. 单独启用接口；
3. 单独配置静态 IPv4 地址；
4. 单独验证本地链路/ARP；
5. 单独配置路由；
6. 单独验证网关可达性；
7. 之后才讨论 DHCP 等后续能力，且须依原计划另行审查工具范围与授权。

以上仅为衔接说明，不替代原计划 B2.2 的精确步骤，也不在本文件中提前执行。任何一步失败均按原计划停止，不得升级内核/U-Boot或转入已封存的项目 B 根因排障。

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
- [ ] R7 GMAC1/MDIO/PHY DTB 恢复及 probe/link 验收通过；
- [ ] R8 最小只读 ip 工具验收通过；
- [ ] 原计划 B2.2 的逐项测试步骤已复核；
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
- R0–R8 尚未执行；
- 原计划 B2.1 尚未启动。

本次归档不授权：访问 Panther X2、运行 U-Boot 命令、写入 TF/eMMC、启动实验固件、构建/安装内核、修改 Kconfig/DTB/驱动/网络配置、读写寄存器、启用 GMAC/MDIO/PHY、运行网络连通性测试。

**后续默认起点：** 先审阅并冻结本计划；随后回到 B1 完整验收剩余事项。只有 B1 通过后，才按本计划从 R0 开始，逐项放行。不得跳到 R1，更不得直接启动 R7 或原计划 B2.1。
