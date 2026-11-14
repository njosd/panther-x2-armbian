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

### 3.3 Kernel package 与 DTB 状态

6.18.63 发布资产已通过检查工作流下载并核验：
- 外层归档 SHA-256 与 `config/versions.env` 记录一致；
- 6 个内部归档校验值全部 MATCH；
- ARM64 Image 存在；
- Rockchip DTB 包清单包含 `rk3566-panther-x2.dtb`；
- 内核配置包含 Rockchip GMAC、Realtek PHY、Rockchip MMC 等基础驱动选项。

DTB 仍有一项未完成：本次 artifact 只上传清单与配置摘要，没有包含 DTB 二进制，因此尚不能反编译并与 DTS 逐项比对。固定 DTS 参考源为 `Lyric-c/panther-x2` 的 `userpatches/kernel/rockchip64-6.18/dt/rk3566-panther-x2.dts`，blob SHA `52cbb88552dcae7d15a18682c7a77ec0888dbdc3`。GMAC/PHY 地址、时序、复位，eMMC/TF 与 USB host 的节点摘要见 `docs/DTB-AUDIT.md`。

因此，当前结论是“内核包中存在目标 DTB 文件且驱动配置具备”，不是“DTB 二进制已证明与参考 DTS 一致”。后续检查只需补取 DTB 二进制并核对启动关键节点，不需要重新审计整个内核包。

### 3.4 GitHub Actions 依赖

Action 必须固定到完整 commit SHA，而不是 `@main` 或可移动标签。当前记录了 checkout、upload-artifact 和 Ophub upload Action 的候选 commit；正式 workflow 仍需逐一核实所用 Action 的接口、权限及兼容性。Armbian Build 也必须 checkout 到记录的 commit，而非克隆 main。

### 3.5 Ubuntu 构建依赖并非完全可复现

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

运行记录：`43526258367`。检查通过，artifact 已下载并审阅。注意该 artifact 不含原始 DTB 字节，DTB 二进制比对仍列为待办。

## 6. 构建前检查清单

- [x] Ophub stable kernel Release 中存在 6.18.63 资产，远端 SHA-256 已记录。
- [x] 手动运行 `.github/workflows/inspect-kernel-package.yml`，下载归档并核对 SHA-256（run 43526258367）。
- [x] 检查归档结构：6 个内部包校验值匹配；确认 ARM64 Image、Panther X2 DTB 文件名及相关驱动配置存在。
- [ ] 提取 DTB 二进制并反编译，与固定 DTS 参考源核对启动关键节点；当前 artifact 仅含清单，不含 DTB 字节。详见 `docs/DTB-AUDIT.md`。
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
