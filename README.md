# Panther X2 Armbian / 项目 A

本仓库用于 Panther X2（RK3566）的系统构建、启动架构与硬件能力研究。当前统一执行主线为**项目 A：最小系统与基础网络验证**；不自动部署、不操作设备。

## 当前唯一执行基线

- [项目 A 总路线图](docs/reports/2026-11/PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：唯一权威架构、决策原则、U-Boot 论证、组件边界和阶段总览。
- [项目 A 分阶段实施计划](docs/reports/2026-11/PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)：B0—B7 及 B0.1、B1.1 等可执行步骤、验收和停止条件。
- [文档总索引](docs/README.md)：主题文档、证据与历史路线映射。

## 项目 A 当前方向

固定已实机验证的 JP-TvBox U-Boot proper 作为 B1—B3 测试入口，先完成最小 RAM Linux 启动，再验证静态 IP/ARP/ICMP，最后按需做 TCP/UDP。B1—B3 不替换 U-Boot proper，不引入完整发行版服务。eMMC pre-Linux 写入安全门未通过前，不写实验卡、不启动实验固件。

项目 A 不包含网卡故障根因调查、GMAC/MDIO/PHY 专项排障；相关历史报告保留为独立专题证据，不作为项目 A 任务或路线。

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
