# 文档总索引

本目录保存 Panther X2 家庭照片中心项目的技术参考、设计决策和测试分析报告。

## 当前主线

先让 Panther X2（RK3566）的最小系统稳定启动。当前优先排查 Ophub Linux 6.12.81 从独立 TF 卡启动时，MMC 已枚举后出现的 EXT4/JBD2 写入 I/O 错误。暂不部署 Immich、不启用 NPU、不写入 eMMC。

## 文档分类

| 目录 | 内容 |
|---|---|
| [00-project](00-project/) | 项目目标、阶段规划、决策和状态 |
| [01-hardware](01-hardware/) | 硬件规格、实机识别结果 |
| [02-boot](02-boot/) | U-Boot、启动链、TF/eMMC、UART |
| [03-kernel-bsp](03-kernel-bsp/) | 内核、BSP、DTS、驱动来源 |
| [04-network](04-network/) | 网卡、PHY、DHCP、SSH |
| [05-storage](05-storage/) | MMC、EXT4、USB、外置存储 |
| [06-npu-rknn](06-npu-rknn/) | NPU、RKNN、RGA、VDEC |
| [07-immich](07-immich/) | Immich 架构与运行验证 |
| [08-operations](08-operations/) | 部署、维护、备份和恢复 |
| [reports](reports/) | 按日期归档的阶段性测试与调查报告 |

## 现有文档位置（整理过渡期）

为避免一次性搬迁造成旧链接失效，现有文档暂时保留在 docs 根目录。后续按主题逐份迁移，并在本索引中更新路径。

| 当前文件 | 主题归属 | 整理状态 |
|---|---|---|
| [BUILD-PLAN.md](BUILD-PLAN.md) | 00-project / 02-boot | 待整理 |
| [BUILD-QUICKSTART.md](BUILD-QUICKSTART.md) | 08-operations | 待整理 |
| [BOOT-DEPENDENCY-AUDIT.md](BOOT-DEPENDENCY-AUDIT.md) | 02-boot | 待整理 |
| [BSP-SOURCE-AUDIT.md](BSP-SOURCE-AUDIT.md) | 03-kernel-bsp | 待整理 |
| [DTB-AUDIT.md](DTB-AUDIT.md) | 03-kernel-bsp | 待整理 |
| [DTB-INSPECTION-2026-11-14.md](DTB-INSPECTION-2026-11-14.md) | 03-kernel-bsp / reports | 待整理 |
| [RKNPU-BSP-AUDIT.md](RKNPU-BSP-AUDIT.md) | 06-npu-rknn / 03-kernel-bsp | 待整理 |
| [NETWORK-ACCEPTANCE.md](NETWORK-ACCEPTANCE.md) | 04-network | 待整理 |
| [FIRST-BOOT-AND-ROADMAP-2026-11-15.md](FIRST-BOOT-AND-ROADMAP-2026-11-15.md) | 00-project / 02-boot | 当前阶段基线，暂保留原路径 |

## 当前状态与下一步

- 首版镜像构建及静态验收：见 [首启与路线基线](FIRST-BOOT-AND-ROADMAP-2026-11-15.md)。
- 新增 TF 启动故障调查：见 [2026-11-15 TF 启动故障调查](reports/2026-11/TF-BOOT-FAILURE-INVESTIGATION.md)。
- 新增 eMMC 启动链与 Vendor Storage 调查：见 [2026-11-16 eMMC U-Boot 与 Vendor Storage 审计](reports/2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)。
- 对应脱敏证据摘录：见 [eMMC BOOT 文件审计证据](../evidence/boot/2026-11-16-panther-x2-emmc-boot-files-audit.txt)。
- 新上传的 UART 原始日志放入 evidence/uart/，保持原样并附校验值。
- 先补齐索引和目录规范，再渐进迁移旧文档；不重跑已完成的测试。

## 维护约定

1. 每次有意义的审计/验证结束后，更新对应主题文档或新增报告，并更新本索引。
2. 报告记录日期、目标版本/设备、测试条件、结果、证据路径/Actions 链接、结论等级和未解决问题。
3. 明确区分：已验证、静态审计确认、待验证、推测/候选。
4. 原始证据只追加，不覆盖；分析结论另存报告，不修改原始日志。
5. 不因目录整理而删除旧文件；迁移时保留历史链接映射或兼容说明。
6. 大型镜像和构建产物不直接提交 Git；使用 Actions Artifacts/Releases，并记录 Run、Artifact、SHA-256。
