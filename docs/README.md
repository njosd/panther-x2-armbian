# 文档总索引

本目录保存 Panther X2 项目 A 的架构决策、构建资料、硬件技术参考和历史测试证据。

## 当前唯一执行主线：项目 A

- [项目 A 总路线图](reports/2026-11/PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)：唯一权威路线，涵盖项目边界、JP U-Boot 测试基线论证、最小系统架构、组件选择原则、安全门和 B0—B7。
- [项目 A 分阶段实施计划](reports/2026-11/PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)：B0—B7 细化为可执行子步骤、验收标准和停止条件。
- [B1 最小 RAM 启动与 eMMC 安全关口审计](reports/2026-11/PANTHER-X2-MINIMAL-RAM-BOOT-PLAN-AND-EMMC-SAFETY-GATE-20261121.md)：B1 的专项技术证据与安全审计。
- [项目 A 干净基线与网络组件隔离决策（2026-11-22）](reports/2026-11/PANTHER-X2-PROJECT-A-CLEAN-BASELINE-AND-NETWORK-COMPONENT-ISOLATION-20261122.md)：项目 A 总目标修订、B1 网络变量隔离门和逐项引入规则。
- [B1 纯 RAM 干净基线构建实施记录（2026-11-22）](reports/2026-11/PANTHER-X2-PROJECT-A-B1-CLEAN-RAM-BUILD-IMPLEMENTATION-20261122.md)：B1 构建输入、隔离边界、CI workflow 和当前未验证项。
- [2026-11 报告索引](reports/2026-11/README.md)：项目 A 文件及独立历史专题索引。
- [G4-P-R Provider / Regulator 只读运行时观察（2026-11-27）](reports/2026-11/PANTHER-X2-G4-PR-REGULATOR-READONLY-RUNTIME-OBSERVATION-20261127.md)：RK809 provider 与九路 IO-domain supply 的只读运行时映射及状态记录；不构成 IO-domain consumer 放行。

新对话、新任务和仓库更新必须先回读项目 A 总路线图及实施计划。历史路线文件如与其冲突，以项目 A 文档为准。

## 项目边界

项目 A 只负责最小 RAM Linux 启动、基础硬件枚举、Panther X2 板载有线千兆以太网口的静态连通性及必要 TCP/UDP 验证、可复现构建和长期启动架构评估。Wi-Fi/无线网络、蓝牙及其所有相关控制器、驱动、固件、协议和用户空间组件永久排除在项目 A 的研究、构建、测试、验收和后续引入范围之外；USB/PCIe 外接网卡亦排除。

网卡故障根因调查、GMAC/MDIO/PHY 驱动专项根因排障仍为独立历史专题，项目 A 不恢复其根因调查。但项目 A 必须将相关历史线索作为风险输入，在 B1 干净基线中隔离 GMAC 及所有未经审查、可能影响网络行为的组件；基线通过后再按单变量顺序逐项引入。隔离和受控引入是项目 A 的实验设计与验收条件，不是项目 B 专项排障。

家庭照片中心、Immich、NPU/RKNN、正式存储采购与备份恢复属于后续独立阶段。

## 项目 B 历史成果的复用规则

项目 B 当前封存，不开展新的专项排障；但项目 A 可以并应当使用项目 B 中全部相关历史成果。项目 A 每项相关工作开始前，先检索旧报告、源码分析、实验记录和原始证据。项目 B 已完成且证据充分的实验不得重复，直接引用结果；引用时保留原始证据等级、测试条件和适用边界。仅在旧证据不能回答当前问题、环境实质变化或存在明确证据缺口时，才考虑最小化补充验证，并说明必要性。项目 A 继承成果不等于恢复项目 B。

## 文档分类

| 目录 | 内容 |
|---|---|
| [00-project](00-project/) | 项目目标、阶段规划、决策和状态 |
| [01-hardware](01-hardware/) | 硬件规格、实机识别结果 |
| [02-boot](02-boot/) | U-Boot、启动链、TF/eMMC、UART |
| [03-kernel-bsp](03-kernel-bsp/) | 内核、BSP、DTS、驱动来源 |
| [04-network](04-network/) | 基础网络资料及独立网络专题历史证据 |
| [05-storage](05-storage/) | MMC、EXT4、USB、外置存储 |
| [06-npu-rknn](06-npu-rknn/) | NPU、RKNN、RGA、VDEC |
| [07-immich](07-immich/) | Immich 架构与运行验证 |
| [08-operations](08-operations/) | 部署、维护、备份和恢复 |
| [reports](reports/) | 按日期归档的阶段性报告 |

## 旧路线与技术文档的处理规则

- 旧版最小系统 P1—P8 路线和旧 initramfs 蓝图已由项目 A B0—B7 取代；旧文件保留兼容路径和历史说明，不再作为执行指令。
- [开发阶段与启动介质原则](DEVELOPMENT-STAGES-AND-BOOT-MEDIA-POLICY.md)、[BUILD-PLAN](BUILD-PLAN.md)、[BOOT-DEPENDENCY-AUDIT](BOOT-DEPENDENCY-AUDIT.md) 等技术资料作为历史/专题参考；与项目 A 冲突时不得覆盖项目 A 决策。
- GMAC 专项报告继续保留在独立专题档案，不在项目 A 路线图中引用为待办或执行步骤。

## 维护约定

1. 项目 A 阶段状态只更新在总路线图与实施计划，并由专项报告提供证据。
2. 每次审计/验证结束后记录日期、目标版本/设备、条件、结果、证据路径/Actions、结论等级和未解决问题。
3. 区分已验证、静态审计确认、待验证、推测/候选。
4. 原始证据只追加，不覆盖；分析结论另存报告。
5. 不因目录整理删除旧文件；历史路径保留或提供映射。
6. 大型镜像和构建产物不直接提交 Git；使用 Actions Artifacts/Releases，并记录 Run、Artifact、SHA-256。
