# Panther X2 Armbian / 项目 A

本仓库用于 Panther X2（RK3566）的系统构建、启动架构与硬件能力研究。当前统一执行主线为**项目 A：最小系统与基础网络验证**；不自动部署、不操作设备。

## 当前唯一执行基线

- [项目 A 总路线图](docs/reports/2026-11/PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：唯一权威架构、决策原则、U-Boot 论证、组件边界和阶段总览。
- [项目 A 分阶段实施计划](docs/reports/2026-11/PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)：B0—B7 及 B0.1、B1.1 等可执行步骤、验收和停止条件。
- [B1 纯 RAM 干净基线构建实施记录](docs/reports/2026-11/PANTHER-X2-PROJECT-A-B1-CLEAN-RAM-BUILD-IMPLEMENTATION-20261122.md)：B1 构建输入、隔离边界、workflow 和未验证事项。
- [文档总索引](docs/README.md)：主题文档、证据与历史路线映射。

## 项目 A 当前方向

固定已实机验证的 JP-TvBox U-Boot proper 作为 B1—B3 测试入口。项目 A 的网络目标仅为 Panther X2 板载有线千兆以太网口。B1 先建立不含网络功能变量的干净 RAM Linux 基线，隔离板载 Ethernet 的 GMAC/STMMAC/DWMAC、MDIO/PHY 及网络协议和用户空间工具；基线通过后，再按单变量顺序逐项引入板载有线 Ethernet 所需组件，最后验证静态 IP/ARP/ICMP 和 TCP/UDP。Wi-Fi/无线网络、蓝牙及其控制器、驱动、固件、协议和用户空间组件永久排除在项目 A 的研究、构建、测试、验收和后续引入范围之外；USB/PCIe 外接网卡亦排除。B1—B3 不替换 U-Boot proper，不引入完整发行版服务。eMMC pre-Linux 写入安全门未通过前，不写实验卡、不启动实验固件。

项目 A 不开展项目 B 的网卡故障根因调查或 GMAC/MDIO/PHY 专项根因排障；相关历史报告保留为独立专题证据。但项目 A 必须将这些历史线索作为风险输入，在 B1 隔离所有可能干扰网络验证的组件，并在干净基线通过后逐项受控引入。组件隔离和单变量验证属于项目 A 的实验设计，不等于恢复项目 B。

## 项目 B 历史成果继承

项目 B（此前历史故障排除与技术研究）目前封存，但其全部相关历史报告、源码分析、实验记录和结论均可供项目 A 继承使用。项目 A 必须先查阅相关既有成果；项目 B 已完成且证据充分的实验直接采用，不得重复。引用时保留原结论的证据等级和适用条件。只有旧证据不足、环境实质变化或存在明确缺口时，才提出有针对性的最小补充验证。使用项目 B 成果不代表恢复项目 B。

## 研究与安全原则

- 目标硬件：Panther X2 / RK3566；实机内存 4GB。
- Kernel、DTB、initramfs 和工具版本必须锁定并记录来源与 SHA-256。
- 新系统从头构建，上游优先；6.1.116 只作历史正常行为参照，不复刻其用户空间。
- 不写 eMMC、不修改当前运行系统；未经明确授权不安装软件或修改系统配置。
- 写卡、固件写入和其他破坏性操作前，必须重新确认设备身份、影响范围和授权。
- 所有结论区分已验证、静态审计确认、待验证和推测/候选。

## 其他长期方向

正式用户空间、存储、NPU/RKNN、Immich 与家庭照片中心属于后续独立阶段，不是项目 A 最小验证系统的组成部分。

## 证据与构建

- [阶段性报告索引](docs/reports/index.md)
- [2026-11 报告索引](docs/reports/2026-11/README.md)
- [原始证据归档规范](evidence/README.md)
- `config/versions.env`：版本与构建基线。
- `manifests/build-manifest.template`：构建记录模板。
- 构建和审计 workflow 位于 `.github/workflows/`；按阶段计划决定是否触发，不自动执行。
