# 第一版构建计划

## 1. 当前目标

构建一份最小可运行系统，先验证 Panther X2 的启动、以太网 DHCP、SSH 和重启稳定性。暂不安装 Immich，不进行 NPU/RKNN 配置。

目标配置：

| 项目 | 目标 |
|---|---|
| 设备 | Panther X2 / RK3566 |
| 系统 | Ubuntu 24.04 LTS Noble |
| 内核系列 | Ophub stable 6.18.y |
| 已选二进制包 | 6.18.63（固定资产及 SHA-256 已记录） |
| 根文件系统 | EXT4 |
| 镜像类型 | Server |
| DTB | rk3566-panther-x2.dtb |
| 启动固件 | Panther X2 专用 idbloader.img + u-boot.itb |
| 首轮介质 | 独立 TF 卡 |

## 2. 已确认的源码与内核包

具体 commit、资产 URL、大小及 SHA-256 见 `config/versions.env`。

已确认：
- Ophub 设备数据库包含 Panther-X2 项目条目，指向 stable 6.18.y 和 Panther X2 DTB。
- 固定的 U-Boot 源码快照包含 Panther X2 的 `idbloader.img` 和 `u-boot.itb`。
- 固定的 Linux DTS 源码包含 GMAC1、RGMII PHY 模式、时钟、供电及复位相关节点。
- Ophub kernel 的 `kernel_stable` Release 已发布 `6.18.63.tar.gz`，GitHub Release API 提供了资产 SHA-256：`47e3f46636594cbf212474a13bac97e1310c3ee51007dee3fa20f93d8659f1ca`，资产大小 124,360,986 bytes。
- Ophub rebuild 的参数解析支持关闭自动查询，并通过 `-k` 指定精确版本；Action 将 `armbian_kernel` 映射为 `-k`，`auto_kernel` 映射为 `-a`。因此预期可用 `armbian_kernel: 6.18.63` 与 `auto_kernel: false` 固定下载版本。

重要区别：
- `9bbed252...` 是 Linux 源码参考 commit；其提交时间晚于 6.18.63 Release 资产的更新时间。当前没有证据证明该二进制包就是由这个源码 commit 构建。
- 因此本项目分别记录源码参考快照与二进制发布资产，不声称两者存在已验证的一一对应关系。
- Release API 的 digest 是远端资产元数据；构建下载后仍必须自行计算 SHA-256 并比对。

这些源码事实和发布资产存在性不能证明内核包在 Panther X2 实机上启动成功，也不能证明网络正常。

## 3. 当前构建阻塞项（未解决前不启动构建）

### 3.1 上游工作流会追踪动态代码

已审查的 Ophub 工作流包含：
- Armbian Build 从 `main` 克隆；
- Ophub Action 使用 `@main`；
- Release 上传 Action 使用 `@main`；
- 默认配置 `auto_kernel: true` 自动查询内核版本。

因此不能直接复制并运行原工作流，否则无法保证本项目构建链固定。

### 3.2 rebuild 脚本会动态下载 U-Boot 和 firmware

当前 rebuild 脚本的 `git_pull_dir` 使用分支名克隆，下载依赖时默认拉取 U-Boot 和 firmware 的 `main`。虽然本仓库记录了已核实的 commit，但仅记录 commit 并不会让原脚本自动使用它们。

下一步必须对 rebuild 逻辑做最小补丁：将 U-Boot、firmware 的下载改为固定 commit checkout，或直接从固定 commit 下载所需目录；构建日志中记录实际 HEAD。补丁应尽量小并单独保存、审查。

### 3.3 Kernel package、DTB 与驱动状态

6.18.63 发布资产已通过深度检查工作流：
- 外层归档 SHA-256 与仓库记录一致；
- 6 个内部包 SHA-256 全部匹配发布包内的校验清单；
- ARM64 Image 和完整配置文件存在；
- Panther X2 DTB 已提取并反编译，SHA-256 已记录，dtc 无警告；
- DTB 的板型标识、GMAC1/PHY、eMMC、TF/SD、USB 等关键节点已做静态抽查，与固定 Ophub DTS 高度吻合；完整结构化等价及二进制构建来源仍未证实；
- RGA、VDEC 模块已从 modules 包及配置头确认存在；尚未实机 probe 或应用验证；
- 未发现明确 RKNPU 模块或 NPU 设备节点。DTB 中虽有 vdd_npu、qos_npu 等资源描述，但不代表驱动可用；
- MPP/VENC 内核支持仍待确认。

检查运行：[43543451274](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274)，Job [132289067398](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274/job/132289067398)。artifact ID：14093500129。完整记录见 `docs/DTB-AUDIT.md`。

当前判断是“内核包与 DTB 静态审计已完成一轮，启动关键节点初步吻合”，不是“已证明镜像可在实机启动”。NPU/RKNN 不作为第一版 TF 启动、DHCP、SSH 验收的前置条件，但应在后续 BSP 来源审计中单独评估。

### 3.4 BSP/NPU 路线与独立模块候选

已确认 Panther X2 专用 Vendor 6.1 路线在板级 DTS 中启用 `rknpu`、`rknpu_mmu`、`bus_npu`，对应 Rockchip Vendor 内核树包含 `drivers/rknpu`、Kconfig/Makefile 接入和 RK356x 驱动配置。

同时发现第三方项目 [w568w/rknpu-module](https://github.com/w568w/rknpu-module)，将 Vendor RKNPU 驱动移植为 mainline 外置模块，并提供 RK3566 NPU overlay。其 README 报告 OrangePi 3B（RK3566）在 Armbian mainline 6.19.3 和 7.0.0 上运行，使用 librknnrt 2.3.2；**没有证据证明可直接用于当前 Ophub 6.18.63**。

该项目还记录 RK3566 IOMMU v2 页表地址可能超过 4GB 并造成总线错误，当前以禁用 NPU IOMMU 的 non-IOMMU 模式规避。不能未经验证照搬到 Panther X2，但首轮移植评估不应默认启用 NPU IOMMU。

Linux 6.18 的 Rocket 驱动支持范围与 RK3566 Vendor RKNPU/RKNN ABI 不同；不能把 Rocket 模块存在等同于 Immich RKNN 后端可用。Immich RKNN 后端依赖 Vendor `rknpu` ABI 的公开讨论也已记录在 `docs/DTB-AUDIT.md`。

**路线决定：** 暂时保持 Ophub 6.18.y 主线候选不变；优先审计 `w568w/rknpu-module` 的源码、许可证、API 依赖、overlay 和 RKNN Runtime 配套，随后在 GitHub Actions 中固定其源码 commit，使用 Ophub 6.18.63 headers 做纯编译验证。编译验证通过仍不代表实机 probe 或 RKNN 推理成功。若 6.18 API 差异过大，再比较升至该模块已验证的 6.19.y 与保留 Vendor 6.1 备选路线。


### 3.5 GitHub Actions 依赖

Action 必须固定到完整 commit SHA，而不是 `@main` 或可移动标签。当前记录了 checkout、upload-artifact 和 Ophub upload Action 的候选 commit；正式 workflow 仍需逐一核实所用 Action 的接口、权限及兼容性。Armbian Build 也必须 checkout 到记录的 commit，而非克隆 main。

### 3.6 Ubuntu 构建依赖并非完全可复现

Armbian 构建会使用动态 APT 软件源。固定 Git commit 不能保证未来 bit-for-bit 可复现。第一阶段的目标应定义为“可追溯、可重复重建”，保存：
- 所有源码 commit；
- Actions commit；
- 构建器镜像/运行环境；
- APT 包清单和构建日志；
- 实际 kernel package 版本及校验值；
- 最终镜像 SHA-256。

## 4. 首启网络设计

Server 镜像预期使用 NetworkManager。首启配置应确保有线接口建立自动连接的 DHCP profile，SSH 服务启用。不要在 NetworkManager 管理接口的同时盲目叠加 ifupdown 配置。

必须检查最终镜像实际使用的网络管理器和接口名；不要假定设备一定叫 eth0。网络配置不应写死 Panther X2 的 IP，先由 hEX DHCP 分配地址。密码、Token、私钥不得提交到公开仓库。

## 5. 内核包检查工作流

已新增并手动运行 `.github/workflows/inspect-kernel-package.yml`：
- 仅 `workflow_dispatch` 手动触发；
- checkout 与 artifact upload Action 固定到完整 commit SHA；
- 下载 `6.18.63.tar.gz` 并与仓库记录的 SHA-256 比对；
- 执行 gzip 完整性检查，生成归档文件清单、内核配置摘要和相关模块路径清单；
- 不运行 rebuild、不写入镜像、不操作任何设备。

最近运行记录：`43543451274`，检查通过，artifact 已下载并审阅；包含原始 DTB、反编译 DTS、完整模块路径清单及配置摘要。

## 6. 构建前检查清单

- [x] Ophub stable kernel Release 中存在 6.18.63 资产，远端 SHA-256 已记录。
- [x] 手动运行 `.github/workflows/inspect-kernel-package.yml`，下载归档并核对 SHA-256（run 43526258367）。
- [x] 检查归档结构：6 个内部包校验值匹配；确认 ARM64 Image、Panther X2 DTB 文件名及相关驱动配置存在。
- [x] 提取 DTB 二进制并反编译；启动关键节点已与固定 Ophub DTS 静态抽查，完整等价与 provenance 仍待验证。详见 `docs/DTB-AUDIT.md`。
- [x] 已找到 Vendor 6.1 RKNPU 驱动源码及 Panther X2 DTS 启用证据。
- [x] 已找到 RK3566 mainline 外置 RKNPU 模块候选及其 6.19.3 实测声明。
- [ ] 审计外置模块的固定 commit、许可证、内核 API 依赖、overlay 与 RKNN Runtime 配套。
- [ ] 在 GitHub Actions 中以 Ophub 6.18.63 headers 进行纯编译验证。
- [ ] TF/SD 控制器与 USB host 节点按 Panther X2 实际板级映射进一步核对。
- [ ] U-Boot 与 firmware 下载已改为固定 commit。
- [ ] Armbian Build、Ophub Action、上传 Action 均固定 commit。
- [ ] 构建 workflow 仅手动触发，不配置 push 自动构建。
- [ ] workflow 不包含 eMMC 安装或设备远程操作。
- [ ] DHCP 与 SSH 首启配置已经静态审查。
- [ ] 构建输出包含 manifest、日志和 SHA-256。
- [ ] 目标 TF 卡容量与写入设备已由用户确认。

## 7. 明确不做

- 不在首版镜像中部署 Immich。
- 不启用 RKNN/NPU/VPU 加速。
- 不改 Panther X2 当前系统、内核、驱动或网络服务。
- 不执行 eMMC 安装。
- 不因首次网络失败就反复刷写；先保留日志并定位 U-Boot、DTB、GMAC/PHY、NetworkManager 各层。
