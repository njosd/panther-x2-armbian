# 2026-11 报告

本月阶段性研究、架构决策与调查报告索引。项目 A 是当前最小系统与基础网络验证的唯一执行主线；其他历史专题继续独立归档。

## 项目拆分与成果复用规则

项目 B（此前历史故障排除与技术研究）目前封存，不再主动开展新专项调查。封存不限制项目 A 读取和使用项目 B 的历史成果：项目 A 必须优先复用相关报告、源码分析、实验记录和原始证据；项目 B 已完成且证据充分的实验不得重复。所有继承结论保留原证据等级、实验条件和适用范围；仅在旧证据不足或环境实质变化时，才提出针对性补充验证。

## 项目 A：当前权威文档

- [项目 A 全阶段黄金基线与默认配置验收规则（2026-11-26）](./PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：总路线图新增强制门；每个 R 阶段均先对照 6.1.65/6.1.116，再审计 6.18 默认配置并验证功能，默认实现通过即保留，未验证不得放行。
- [B2-1 R3 RK809/I2C/regulator 专项审计](./PANTHER-X2-B2-1-R3-RK809-I2C-REGULATOR-PREFLIGHT-20261126.md)：R3 静态审计 COMPLETE（CONDITIONAL）；含 RK809 实机只读身份/状态寄存器证据、6.1.65/6.18.63 黄金对照、MFD/regulator 副作用及 PHY supply consumer 调用链。运行时 MFD/regulator 激活仍未授权。
- [B2-1 R4 MDIO/PHY Kconfig 审计（进行中）](./PANTHER-X2-B2-1-R4-MDIO-PHY-KCONFIG-AUDIT-20261126.md)：R4 第一子项 Kconfig/Makefile 静态对照 PASS；PHYLIB/MDIO_BUS/OF_MDIO/PHYLINK 结构变化及 REALTEK_PHY 必须显式启用已记录。
  - R4 第二子项 RTL8211F 驱动源码对照 PASS（STATIC / DIFFERENCES DOCUMENTED）：6.1.65/6.18.63 PHY ID、probe 副作用、ALDPS、RGMII delay、CLKOUT/soft reset、EEE、interrupt/resume 差异已归档；实际 PHY probe 仍禁止。

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
