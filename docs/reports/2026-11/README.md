# 2026-11 报告

本月阶段性研究、架构决策与调查报告索引。项目 A 是当前最小系统与基础网络验证的唯一执行主线；其他历史专题继续独立归档。

## 项目拆分与成果复用规则

项目 B（此前历史故障排除与技术研究）目前封存，不再主动开展新专项调查。封存不限制项目 A 读取和使用项目 B 的历史成果：项目 A 必须优先复用相关报告、源码分析、实验记录和原始证据；项目 B 已完成且证据充分的实验不得重复。所有继承结论保留原证据等级、实验条件和适用范围；仅在旧证据不足或环境实质变化时，才提出针对性补充验证。

## 项目 A：当前权威文档

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
- [B2-0 方向2：Linux 网络核心多版本静态差异评估进度](./PANTHER-X2-B2-0-DIRECTION-2-NETWORK-CORE-MULTIVERSION-DIFF-PROGRESS-20261124.md)：§3～§24、§26 既定 generic network-core 子项已完成四版本源码/配置审计；§47 补齐 6.12.81 最终配置；§50 确认 6.1.174 历史 config 在当前公开资产不可恢复；§51 解释 6.1.65 NET_DROP_MONITOR 缺行；§52 确认无额外明确专题；§53 已形成四版本综合矩阵与普通 DHCP/UDP TX 适用性判断；§54 报告内部一致性初审通过；§55 完成结项条件评估，判定技术审计范围已完成、具备证据边界明确的有条件结项条件，正式状态仍为进行中、等待用户确认。
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
