# 2026-11 报告

本月阶段性研究、架构决策与调查报告索引。项目 A 是当前最小系统与基础网络验证的唯一执行主线；其他历史专题继续独立归档。

## 项目拆分与成果复用规则

项目 B（此前历史故障排除与技术研究）目前封存，不再主动开展新专项调查。封存不限制项目 A 读取和使用项目 B 的历史成果：项目 A 必须优先复用相关报告、源码分析、实验记录和原始证据；项目 B 已完成且证据充分的实验不得重复。所有继承结论保留原证据等级、实验条件和适用范围；仅在旧证据不足或环境实质变化时，才提出针对性补充验证。

## 项目 A：当前权威文档

- [G0–G10 硬件准入与 ABCD-TX 分层验证计划（2026-11-26）](./PANTHER-X2-G0-G10-HARDWARE-ACTIVATION-AND-ABCD-TX-PLAN-20261126.md)：冻结硬件激活门序、provider/consumer 依赖、ABCD 同帧发送验证边界及后续 RX/ARP/IP/TCP/UDP 放行步骤。
- [G0.1 Provider/Consumer 依赖矩阵（2026-11-26）](./PANTHER-X2-G0-1-PROVIDER-CONSUMER-DEPENDENCY-MATRIX-20261126.md)：归并 R2–R6 现有证据，列出已通过、静态条件通过、阻塞及未验证资源。
- [G0.2 RK809 MFD/Regulator 副作用审计（2026-11-26）](./PANTHER-X2-G0-2-RK809-MFD-REGULATOR-SIDE-EFFECTS-20261126.md)：已识别 6.18 probe 写入路径；最终决策为 HOLD，等待黄金实现对照，不再沿用“stock NO-GO”作为最终结论。
- [G0.3 IO-domain Supplier / GMAC1 VCCIO5 映射审计（2026-11-26）](./PANTHER-X2-G0-3-IODOMAIN-SUPPLIER-AND-GMAC1-VCCIO5-MAPPING-20261126.md)：静态拓扑和 GRF 写入路径完成；GMAC1 M0→VCCIO5，且与 PHY 共用 vcc_3v3/SWITCH_REG1；最终 deferred-probe 状态仍 UNKNOWN。
- [G0.4 GMAC1 Clock/Reset/PHY 125MHz 来源审计（2026-11-26）](./PANTHER-X2-G0-4-GMAC1-CLOCK-RESET-PHY-125MHZ-AUDIT-20261126.md)：CRU clock/reset、PHY reset、RGMII mode/delay 静态链完成；RTL8211F CLKOUT pin35 仅为候选，实际物理波形未验证。
- [G0.5 ABCD-TX Sender 与观测夹具审查（2026-11-26）](./PANTHER-X2-G0-5-ABCD-TX-SENDER-AND-OBSERVABILITY-FIXTURE-20261126.md)：独立 sender 规格、A/B/C/D 观测链、同帧关联和对端 pcap 规范已固定；未构建新 sender、未发送目标帧。下一项为 G0 总体准入复核。

- [项目 A 全阶段黄金基线与默认配置验收规则（2026-11-26）](./PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：总路线图新增强制门；每个 R 阶段均先对照 6.1.65/6.1.116，再审计 6.18 默认配置并验证功能，默认实现通过即保留，未验证不得放行。
- [B2-1 R3 RK809/I2C/regulator 专项审计](./PANTHER-X2-B2-1-R3-RK809-I2C-REGULATOR-PREFLIGHT-20261126.md)：R3 静态审计 COMPLETE（CONDITIONAL）；含 RK809 实机只读身份/状态寄存器证据、6.1.65/6.18.63 黄金对照、MFD/regulator 副作用及 PHY supply consumer 调用链。运行时 MFD/regulator 激活仍未授权。
- [B2-1 R4 MDIO/PHY 静态审计（已结项，CONDITIONAL）](./PANTHER-X2-B2-1-R4-MDIO-PHY-KCONFIG-AUDIT-20261126.md)：R4-1 Kconfig/Makefile、R4-2 RTL8211F 驱动差异、R4-3 MDIO/PHY 对象组织、R4-4 R1 配置隔离核验均完成。R1 明确关闭 MDIO/PHY/PHYLIB/REALTEK_PHY/PHYLINK/STMMAC/DWMAC，符合隔离目标；实机 PHY probe 仍未放行。

- [原始 Armbian 6.1.65 镜像静态审计报告（2026-11-23）](./PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md)：原始镜像布局、启动配置、Panther X2 DTB、Kernel built-in 配置及 Dropbox 证据保留清单；Kernel/uInitrd 二进制闭包仍待补齐。

- [B1 纯 RAM 干净基线构建实施记录（2026-11-22）](./PANTHER-X2-PROJECT-A-B1-CLEAN-RAM-BUILD-IMPLEMENTATION-20261122.md)：B1 纯 RAM 构建实现、输入锁定、隔离策略与待验证事项。

- [项目 A 干净基线与网络组件隔离决策（2026-11-22）](./PANTHER-X2-PROJECT-A-CLEAN-BASELINE-AND-NETWORK-COMPONENT-ISOLATION-20261122.md)：B1 先隔离网络变量，再逐项引入的强制决策。

- [Panther X2 项目 A 总路线图（2026-11-21）](./PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：唯一权威总路线，统一项目定义、架构原则、组件选择、JP-TvBox U-Boot proper 测试基线论证、B0—B7 阶段和安全边界。
- [Panther X2 项目 A 分阶段实施计划（2026-11-21）](./PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)：将阶段拆解为 B0.1、B0.2……等可执行步骤和验收条件。
- [最小 RAM 启动与 eMMC 安全关口审计（2026-11-21）](./PANTHER-X2-MINIMAL-RAM-BOOT-PLAN-AND-EMMC-SAFETY-GATE-20261121.md)：B1 构建和实机启动前置安全证据。
- [P1 initramfs 启动链静态审计（2026-11-20）](./PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)：已有启动资产、内核 initramfs 能力与启动链静态证据。
- [P2 上游用户空间组件审计（2026-11-20）](./PANTHER-X2-P2-UPSTREAM-USERSPACE-COMPONENT-AUDIT-20261120.md)：BusyBox、网络工具等上游组件候选审计。
- [P2 启动架构与 eMMC Vendor 数据审计（2026-11-20）](./PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md)：RK3566 启动介质、Vendor 数据只读路径与长期 U-Boot 架构证据。
- [U-Boot 候选研究（2026-11-17）](./PANTHER-X2-UBOOT-CANDIDATE-RESEARCH-20261117.md)：候选固件来源和配置研究。
- [U-Boot 启动日志与混合链证据（2026-11-18）](./PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md)：实际 SPL/proper 启动顺序及 UART 证据。

## 项目 A 网络范围补充（2026-11-22）

项目 A 只验证 Panther X2 板载有线千兆 Ethernet。Wi-Fi/无线网络、蓝牙及其全部控制器、驱动、固件、协议、用户空间组件永久排除，不审计、不构建、不测试、不安排后续引入；USB/PCIe 外接网卡也排除。板载 Ethernet 的 GMAC/MDIO/PHY 则是最终目标，但必须先在 B1 干净基线隔离，再逐项引入。

- [B2-0：6.1.174-rk35xx 原始构建源码身份结项（2026-11-24）](./PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md)：从原始 Actions run #296 job log 直接确认 source_hash 与实际构建参数，关闭此前的源码身份缺口。

- [B2-0：四版本 GMAC 主链 built-in / modules 与启动资产闭包对照（2026-11-24）](./PANTHER-X2-B2-0-FOUR-VERSION-KERNEL-ASSET-CLOSURE-20261124.md)：对照 6.1.65、6.1.116、6.1.174、6.12.81 的内核主链编译形态、模块分布、initramfs 与替换边界。
- [B2-0：6.1.174-rk35xx 原始构建源码身份结项（2026-11-24）](./PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md)：从原始 Actions run #296 job log 直接确认 source_hash 与实际构建参数，关闭此前的源码身份缺口。

- [GMAC glue、时钟与电源路径补充审计（2026-11-24）](./PANTHER-X2-GMAC-GLUE-CLOCK-POWER-SUPPLEMENTAL-AUDIT-20261124.md)：汇总既有 CRU clock/reset、CSU、RK809 PHY supply 与 runtime-PM 静态证据；仅作后续对应专题的证据复用，不代表 B2-0 当前方向结项。
- [B2-0：Linux 6.18.63 精确源码 Kconfig / Makefile 依赖审计（2026-11-24）](./PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md)：闭合 STMMAC、Rockchip glue、PHYLINK/PHYLIB/MDIO、RTL8211F、CCF/CRU、GRF、GPIO、RK809 PHY supply 的构建依赖，并登记 6.1.116 / 6.12.81 差异。
- [B2-0 方向1：版本样本与构建来源追溯结项（2026-11-24）](./PANTHER-X2-B2-0-DIRECTION-1-VERSION-AND-SOURCE-PROVENANCE-20261124.md)：整理正常基线与已确认故障样本；明确 6.1.174 是目前最早有明确故障实机证据的版本，但首次回归小版本仍未证明。6.18.63 已确认实机启动及故障，属于 6.18.y，不纳入 6.1.y 首次故障点判断。
- [B2-0 方向2：Linux 网络核心多版本静态差异评估进度](./PANTHER-X2-B2-0-DIRECTION-2-NETWORK-CORE-MULTIVERSION-DIFF-PROGRESS-20261124.md)：§3～§24、§26 既定 generic network-core 子项已完成四版本源码/配置审计；§53 四版本综合矩阵、§54 一致性审校、§55 结项条件评估及 §56 用户批准后的正式结项记录均已归档。方向二现为“已结项（证据边界明确）”，历史来源/配置/运行时限制按 §55.2 保留，不重复已完成审计。
- [B2-0 方向三：STMMAC / DWMAC4 / DMA 驱动核心静态审计计划](./PANTHER-X2-B2-0-DIRECTION-3-STMMAC-DWMAC4-DMA-AUDIT-20261125.md)：方向三阶段边界、四版本样本、子项顺序及禁止重复项；当前执行 D3-1。
- [B2-0 方向三 D3-1：STMMAC platform probe / resource parsing 四版本差异](./PANTHER-X2-B2-0-DIRECTION-3-D3-1-STMMAC-PLATFORM-PROBE-DIFF-20261125.md)：已完成首轮四版本源码对照；发现 pclk/pclk_mac 名称及 MDC CSR clock source 变化，D3-1 已结项；确认 6.1.65/6.1.116 与 6.1.174/6.12.81 的 pclk/MDC CSR clock source 差异。
- [B2-0 方向三 D3-2：STMMAC MDIO / PHY attach 四版本差异](./PANTHER-X2-B2-0-DIRECTION-3-D3-2-MDIO-PHY-ATTACH-DIFF-20261125.md)：确认四版本 MDIO parser 在 Panther DTS 上的最终 bus/PHY 结果等价；发现四次 PHYCR2/BMCR 写入存在于 6.1.65/6.1.116、缺失于实际 6.1.174-rk35xx/6.12.81 源码；并记录 mac_requires_rxc 版本变化。D3-2 静态审计已结项，进入 D3-3。
- [B2-0 方向三 D3-3：DWMAC4 DMA core 初始化四版本差异](./PANTHER-X2-B2-0-DIRECTION-3-D3-3-DWMAC4-DMA-INIT-DIFF-20261125.md)：使用实际 6.1.174-rk35xx 构建源码 c2f148d 校正旧 stable 对照；发现黄金版本有 1500ms DMA reset 前延时、故障版本缺失，且 reset poll interval 从 10ms 缩短至 0.5ms。DWMAC4 DMA/AXI/channel init 算法整体相同；D3-3 静态审计已结项；硬件 addr64 实际值与 DMA reset 运行时完成时间保留为证据限制。
- [B2-0 方向三 D3-4：STMMAC TX descriptor 未覆盖分支](./PANTHER-X2-B2-0-DIRECTION-3-D3-4-TX-DESCRIPTOR-REMAINING-BRANCHES-20261125.md)：当前开始盘点既有 TSO/context/fragment/mapping failure/completion 报告，严格避免重复D3-4 已结项；确认 6.1.65 TSO 多 descriptor DMA mapping 记录位置缺陷、TX coalescing timer 1000→5000us 变化，以及 6.12 条件性 VLAN TSO/COE/EST 分支。
- [B2-0 方向三 D3-5：STMMAC RX descriptor / buffer / page-pool lifecycle](./PANTHER-X2-B2-0-DIRECTION-3-D3-5-RX-DESCRIPTOR-PAGEPOOL-DIFF-20261125.md)：当前复核既有 6.1.116/6.12.81 RX 报告，D3-5 已结项；四版本 page-pool create/refill、DMA sync 和 RX OWN/status 主路径未发现普通 DHCP RX 无条件回归。
- [B2-0 方向三 D3-6：DMA API / coherency / IOMMU 四版本交叉审计](./PANTHER-X2-B2-0-DIRECTION-3-D3-6-DMA-API-COHERENCY-IOMMU-20261125.md)：当前复用 32/32 DMA width 与无 GMAC IOMMU 既有证据，D3-6 已结项；普通 streaming cache sync 四版本一致，GMAC1 无 dma-coherent/iommus，6.12 新增 bounce 条件不命中普通 TX DMA_TO_DEVICE。
- [B2-0 方向三 D3-7：STMMAC IRQ / NAPI / watchdog / recovery 四版本审计](./PANTHER-X2-B2-0-DIRECTION-3-D3-7-IRQ-NAPI-WATCHDOG-RECOVERY-20261125.md)：当前复核既有 IRQ/NAPI 证据，D3-7 已结项；IRQ status/NAPI schedule、timeout、global reset 与 per-channel recovery 未发现普通 DHCP 的无条件阻断回归。
- [B2-0 方向三 D3-8：STMMAC/DWMAC4 四版本总矩阵与一致性审校](./PANTHER-X2-B2-0-DIRECTION-3-D3-8-SYNTHESIS-CLOSEOUT-20261125.md)：汇总 D3-1～D3-7，D3-8 已完成；D3-1～D3-7 静态审计全部结项，方向三技术审计具备证据边界明确的结项条件，等待正式归档确认。
- [B2-0 方向四：Rockchip GMAC glue / CCF / CRU / clock / reset 四版本审计进度（2026-11-25）](./PANTHER-X2-B2-0-DIRECTION-4-ROCKCHIP-GMAC-GLUE-CCF-CRU-AUDIT-PROGRESS-20261125.md)：已完成四版本 reset ID/provider、CCF/PLL、probe/setup/power handoff 与 RGMII callback 首轮核对，并形成第一轮总矩阵；已识别 clock enable API/错误检查/settle delay、GRF 写入顺序差异；补齐 HCLK_USB 与 PCLK_USB 两项 critical flag 的四版本对照，并区分二者与 GMAC1 parent chain 的关系；PCLK_USB critical 经 CCF parent recursion 保持共用 ACLK_USB 父链；若 ACLK_USB 实际选择 GPLL 且当时 GPLL enable reference 为 0，PCLK_USB critical parent recursion 可能触发后期 GPLL callback；历史 parent/reference/时序未验证；HCLK_USB 不在 GMAC1 父链。方向四已完成与方向二、方向三的跨层一致性审校：generic network-core 与 Rockchip glue 层结论不冲突；方向三 DMA reset 前 1500ms 与方向四 glue clocks 5ms/100–200µs 是不同调用层和等待对象，禁止合并归因；STMMAC pclk/pclk_mac 与 CRU PCLK_GMAC1/ACLK_GMAC1 不可混同。方向四已完成原定静态审计子项及四版本总矩阵，补齐 RGMII speed callback、powerdown/suspend/resume 与跨方向一致性核对，现按“证据边界明确的有条件结项”归档。未验证的历史 clock/PLL/GRF/PHY 电气状态继续保留，不代表已找到 TX 根因；不启动 B2.1。
- [B2-0 方向五：MDIO / PHYLIB / PHYLINK / RTL8211F 四版本静态审计进度（2026-11-25）](./PANTHER-X2-B2-0-DIRECTION-5-MDIO-PHYLIB-PHYLINK-RTL8211F-AUDIT-PROGRESS-20261125.md)：已完成四版本普通 RTL8211F-CG 驱动、PHY paged API 锁与错误恢复、PHYLIB 状态机、PHYLINK MLO_AN_PHY 路径及剩余 autoneg/link callback 覆盖；复核 15 份既有专题并形成四版本差异矩阵。明确区分 Realtek config_init 与 STMMAC 前置 JL2xx1 workaround：黄金版本有 0x1801/BMCR 写入、故障版本缺失；0x1801 会清 bit1 RXC 与 bit5 EEE，仍缺历史寄存器读回/波形，不能认定根因。另单独核对 6.18.63 EEE bit5 单 bit 清除、soft reset 与 speed status 差异。方向五原定静态审计范围已全部覆盖，用户已批准按“证据边界明确的有条件结项”归档；运行时 PHYCR2/MDIO 回读与 RXC/CLKOUT 波形仍未验证。运行时 PHYCR2/MDIO 回读与 RXC/CLKOUT 波形仍未验证；既有 PHYCR2/CLKOUT/MDIO trace 等专题只复用、不重做。
- [B2-0 决策阶段：版本选择与组件恢复顺序（第一轮，2026-11-25）](./PANTHER-X2-B2-0-VERSION-AND-COMPONENT-RECOVERY-DECISION-PROGRESS-20261125.md)：汇总方向一至五，提出 6.18.63 连续基线候选、历史候选差异分级和 B1 通过后的 R0–R8 组件依赖引入顺序；作为 B2-1 实施计划的技术决策依据。
- [B2-1：实施计划与执行归档基准（2026-11-25，2026-11-26 修订）](./PANTHER-X2-B2-1-IMPLEMENTATION-PLAN-20261125.md)：在 TX-first 与 R0–R8 顺序基础上，新增全阶段 6.1.65 第一黄金基线、6.1.116 第二黄金行为参照、6.18 默认配置优先、实际功能验证及未完成不放行规则。

- [B2-1 / R0：基线资产与 TX 前置核查（2026-11-25）](./PANTHER-X2-B2-1-R0-BASELINE-PREFLIGHT-20261125.md)：追溯 B1 Actions Kernel/DTB artifact、复用关系、分支文件差异和实机验收边界；R0 尚未通过，不放行网络组件引入。
- [B2-1 / R2：共享 SoC provider 配置与构建核验（2026-11-26）](./PANTHER-X2-B2-1-R2-SHARED-SOC-PROVIDER-AUDIT-20261126.md)：R2 已 PASS；复用 B1/R1 构建与配置、6.1.65 Golden 对照，现有 R1 镜像只读验证 pinctrl/SYSCON consumer、五个 GPIO bank 和五个 gpiochip 注册成功；零增量复用，无需重建。

- [项目 A B2-1 实施计划（R3/R4 状态更新）](./PANTHER-X2-B2-1-IMPLEMENTATION-PLAN-20261125.md)：R3 静态审计 COMPLETE（CONDITIONAL）；R4 静态审计 COMPLETE（CONDITIONAL）；下一阶段按路线进入 R5 STMMAC 核心与 TX/RX 数据路径审计。
- [B2-1 R5 STMMAC/DWMAC4 MAC 与 DMA core 审计（已结项）](./PANTHER-X2-B2-1-R5-STMMAC-DWMAC4-CORE-AUDIT-20261126.md)：R5-1 Kconfig/Makefile 静态对照 PASS；6.18 新增 ETHTOOL_NETLINK 依赖、NET_DEVLINK select，以及 EST/FPE/VLAN/PCS 对象差异已记录。
  - R5-2 STMMAC open/stop 与 DMA 初始化生命周期静态对照 PASS；R5-3 DWMAC4 descriptor/ring-chain/DMA coherency PASS；R5-4 TX submit/completion/IRQ/NAPI 增量审计 PASS。6.18 保留普通 RI/TI/TBU status decode、TPS/FBE hard-error、W1C ack、NAPI IRQ mask/schedule/complete/unmask 核心顺序；新增 safety IRQ 分流、RWT 统计条件变化、per-CPU IRQ stats、register-map helper 和 pending TX timer 协作。R5 STATIC AUDIT COMPLETE（CONDITIONAL），尚未验证 Panther 实际 MAC/DMA capability、register map、reset outcome 和 TX 线侧发送。下一阶段 R6 Rockchip DWMAC glue 与 Panther DTS/clock/reset/GRF/PHY interface 参数对照。
- [B2-1 R6 Rockchip DWMAC glue 与硬件参数审计（静态阶段完成，硬件准入条件保留）](./PANTHER-X2-B2-1-R6-ROCKCHIP-DWMAC-GLUE-AUDIT-20261126.md)：R6-1 glue/DTS 对照 PASS；R6-2 GRF/CRU clock/reset PASS（官方 TRM 确认 CON1 bit7）；R6-3 6.18.63 DTB 实物已核验，GMAC1 核心属性与 6.1.65 黄金原始解析一致，6.1.65 全 DTB 自动 diff 仍 BLOCKED；R6-4 定义 R7-A Gate 0–4；R6-5 已纠正 125MHz 时钟链：DTS fixed-clock 只是 CCF 逻辑模型，RK809 CLKOUT 与 gmac1_clkin 无连接声明，RTL8211F CLKOUT pin35 是待验证物理来源候选。R6 静态审计可 CONDITIONAL CLOSE；实际 rail/PHYCLKOUT/GMAC probe/TX 仍留在 R7 并需独立授权。
- [B2-1 / R3：RK809 / I2C / Regulator 前置审计（2026-11-26）](./PANTHER-X2-B2-1-R3-RK809-I2C-REGULATOR-PREFLIGHT-20261126.md)：R3.1 I2C0 controller/adapter、R3.2 RK809 身份读取、R3.7 状态寄存器只读观察均 PASS-RUNTIME。RK809 ID 实测 `0x8094`；`PMIC_SYS_STS(0xF0)=0xC2`、`PMIC_OFF_SOURCE(0xF6)=0x00`，两个寄存器各一次 I2C_RDWR 只读事务成功。SU08G 专用 RAM-only initramfs 已验证，旧 uInitrd 备份保留；SN64G/eMMC 未涉及。MFD/regmap 与 regulator probe 存在 PMIC 写入及可能的 rail 配置副作用，R3.3–R3.5 保持 BLOCKED，R3.6 留待 R7-A，R3 整体 HOLD/BLOCKED，不放行 R4。

- [B2-1：Linux 6.18.63 TX 追踪观测能力审计（2026-11-25）](./PANTHER-X2-B2-1-TX-TRACE-OBSERVABILITY-AUDIT-20261125.md)：直接核对 R1 实际 artifact 的 tracepoint/kprobe/tracefs/DWARF 配置、System.map 符号与 Linux 6.18.63 网络/DMA/STMMAC/DWMAC4 源码；确认 net_dev_*、dma_map_phys/unmap_phys、skb 生命周期事件可用，kprobe 可补读 skb payload 与 descriptor OWN/status，STMMAC debugfs 可只读快照 descriptor ring。明确 tracefs 挂载、目标 kprobe 注册、同构建结构偏移和硬件 TX 均未验证；未访问设备或改变 tracing 状态。

## 独立专题：历史网卡故障调查（不属于项目 A）

以下文件只保留为独立专题的历史证据、技术结论和审计记录，不构成项目 A 的路线、待办或验收条件。项目 A 不继续追踪其故障根因，不重复其专项测试。

- [GMAC TX 故障调查阶段性报告（P1–P4，2026-11-20）](./PANTHER-X2-GMAC-TX-INVESTIGATION-STAGE-1-4-SUMMARY-20261120.md)
- [GMAC 故障调查独立路线图（2026-11-19）](./PANTHER-X2-GMAC-INVESTIGATION-ROADMAP-20261119.md)
- [P2 U-Boot/Linux GMAC clock handoff 专项报告](./PANTHER-X2-P2-UBOOT-LINUX-GMAC-CLOCK-HANDOFF-20261119.md)
- [P2 PHY clock 与 U-Boot/Linux handoff 专项报告](./PANTHER-X2-P2-PHY-CLOCK-AND-UBOOT-LINUX-HANDOFF-20261119.md)\n- [GMAC1 RGMII CRU parent/gate/reset 依赖审计（2026-11-24）](./PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md)

其余 GMAC、PHY、MDIO、RGMII、STMMAC、DMA、pinctrl 专项报告继续按原路径保存；不在此处展开为项目 A 任务。

## 其他启动与系统历史报告

- [P2 RK3566 DDR/SPL/BL31 候选静态审计（2026-11-21）](./PANTHER-X2-P2-UBOOT-RK3566-DDR-SPL-BL31-CANDIDATE-AUDIT-20261121.md)
- [eMMC Vendor Storage 只读审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)
- [TF 启动故障历史调查](./TF-BOOT-FAILURE-INVESTIGATION.md)

## 归档原则

- 项目 A 的执行状态只由总路线图和分阶段实施计划定义。
- 独立专题历史报告不自动转化为项目 A 待办。
- 保留原始日志、报告和哈希，不因项目拆分而删除证据。
- 新增报告必须标注结论等级、证据来源和是否影响项目 A 当前阶段。
\n- [G0.6 Fixed-Regulator 替代路径可行性（2026-11-26）](./PANTHER-X2-G0-6-FIXED-REGULATOR-ALTERNATIVE-FEASIBILITY-20261126.md)：仅保留历史备选，不进入当前主路线，不实现。\n\n- [G0.7 Panther X2 专用 Rail/测量点资料检索（2026-11-26）](./PANTHER-X2-G0-7-PANTHER-X2-BOARD-RAIL-TESTPOINT-RESEARCH-20261126.md)：仅作为背景资料；PCB 测点不再是 G0 准入条件。\n

- [G0 Golden 基准 PMIC/Regulator 反向追踪计划（2026-11-26）](./PANTHER-X2-G0-GOLDEN-PMIC-REGULATOR-REVERSE-AUDIT-PLAN-20261126.md)：纠正 G0 优先级，先恢复 6.1.65/6.1.116 的真实配置/对象和驱动初始化行为，再对照 6.18.63；G0.6 fixed-regulator 降为备选，G0.7 PCB 测点不再作为准入条件。

- [G0 两条黄金基准 PMIC/PHY 源码共性核验（2026-11-27）](./PANTHER-X2-G0-GOLDEN-65-116-PMIC-PHY-SOURCE-COMMONALITY-20261127.md)：6.1.65 与 6.1.116 的 RK809 MFD、regulator、IO-domain、GMAC glue 和 Panther DTS 关键文件逐字节相同；regulator core 四个关键函数相同。下一项只补齐黄金 DTB binary diff。

- [G0-P4 黄金 DTB 证据复核（2026-11-27）](./PANTHER-X2-G0-P4-GOLDEN-DTB-EVIDENCE-RECONCILIATION-20261127.md)：6.1.116 与 6.18.63 完整 DTB 字节级相同；6.1.65 原始 DTB GMAC 核心解析已归档，仅 PMIC/IO-domain 子树二进制复核仍缺。
- [G0 总体复核与 G2 受控激活预案（2026-11-27）](./PANTHER-X2-G0-OVERALL-REVIEW-AND-G2-CONTROLLED-PLAN-20261127.md)：G0 CONDITIONAL PASS（仅计划层面）；G2 只拟验证 RK809 MFD/regmap，probe 需要单独授权，不启用 regulator/GMAC。

- [G2 RK809 MFD 准入再评估（2026-11-27）](./PANTHER-X2-G2-RK809-MFD-GATE-REASSESSMENT-20261127.md)：黄金与 6.18 IRQ mapping/pre-init/MFD cells 对照；识别 PWRKEY resource 顺序差异；G2-S 完成，下一步仅 build-only，不 probe。

- [项目 A 6.18 真实运行环境切换原则（2026-11-27）](./PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：B1-clean 只保留启动基线；G2-B build-only 后冻结项目 A 专用 6.18.63 minimal runtime，并从 G2-PROBE 起在 Panther X2 实机运行；R7 首次进行真实 TX 验收。

- GMAC 高风险准入与 TX 分段计划：见 [G0–G10 硬件准入与 ABCD-TX 分层验证计划](./PANTHER-X2-G0-G10-HARDWARE-ACTIVATION-AND-ABCD-TX-PLAN-20261126.md) 的“GMAC 高风险准入原则”章节。

## 项目 A：四层技术知识库与风险模型（2026-11-27）

- [四层技术知识库与风险模型](./PANTHER-X2-PROJECT-A-FOUR-LAYER-KNOWLEDGE-BASE-AND-RISK-MODEL-20261127.md)：将 Linux 公共网络栈、通用 MAC/IP 驱动、Rockchip SoC 适配、Panther X2 板级适配拆分为 K1–K4；定义风险优先级、证据标签、黄金基线复用规则及跨层接口审计重点。该分类不改变 G0–G10 阶段顺序。

- [G2-B RK8xx MFD build-only workflow](../../../.github/workflows/build-panther-x2-g2-b-rk8xx-mfd.yml)：以成功 R1 artifact（run `45611898629`）为输入，只增加 RK8xx MFD I2C transport/core built-in；RK809、regulator、PWRKEY child 和 GMAC/MDIO/PHY 保持隔离。workflow 已提交但尚未触发，不能视为 build PASS。
