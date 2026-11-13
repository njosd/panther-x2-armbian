# 第一版构建计划

## 1. 当前目标

构建一份最小可运行系统，先验证 Panther X2 的启动、以太网 DHCP、SSH 和重启稳定性。暂不安装 Immich，不进行 NPU/RKNN 配置。

目标配置：

| 项目 | 目标 |
|---|---|
| 设备 | Panther X2 / RK3566 |
| 系统 | Ubuntu 24.04 LTS Noble |
| 内核系列 | Ophub stable 6.18.y |
| 根文件系统 | EXT4 |
| 镜像类型 | Server |
| DTB | rk3566-panther-x2.dtb |
| 启动固件 | Panther X2 专用 idbloader.img + u-boot.itb |
| 首轮介质 | 独立 TF 卡 |

## 2. 已确认的源码基线

具体 commit 见 `config/versions.env`。这些是源码快照，不是已经构建或实机验证的镜像。

源码核查已确认：
- Ophub 设备数据库包含 Panther-X2 项目条目，指向 stable 6.18.y 和 Panther X2 DTB。
- 固定的 U-Boot 源码快照包含 Panther X2 的 `idbloader.img` 和 `u-boot.itb`。
- 固定的 Linux DTS 源码包含 GMAC1、RGMII PHY 模式、时钟、供电及复位相关节点。
- 这些源码事实不能证明实际 PHY 协商、DHCP、ARP、SSH 或长期网络稳定性。

## 3. 当前构建阻塞项（未解决前不启动构建）

### 3.1 上游工作流会追踪动态代码

已审查的 Ophub 工作流包含：
- Armbian Build 从 `main` 克隆；
- Ophub Action 使用 `@main`；
- Release 上传 Action 使用 `@main`；
- `auto_kernel: true` 自动查询内核版本。

因此不能直接复制并运行原工作流，否则无法保证本项目构建链固定。

### 3.2 rebuild 脚本会动态下载 U-Boot 和 firmware

当前 rebuild 脚本的 `git_pull_dir` 使用分支名克隆，下载依赖时默认拉取 U-Boot 和 firmware 的 `main`。虽然本仓库记录了已核实的 commit，但仅记录 commit 并不会让原脚本自动使用它们。

下一步必须对 rebuild 逻辑做最小补丁：将 U-Boot、firmware 的分支克隆改为固定 commit checkout，或直接从固定 commit 下载所需目录；构建日志中记录实际 HEAD。补丁应尽量小并单独保存、审查。

### 3.3 内核二进制包版本尚未锁定

Linux 源码 commit 与 Ophub 发布的 kernel package 版本不是同一标识。固定源码 commit 不等于固定 `linux-image` 二进制包。

必须先确认 Ophub kernel 仓库中真实存在、适用于 RK3566/目标架构的 6.18 stable 发布包，并确认 rebuild 脚本如何选择该包。随后：
1. 在 `config/versions.env` 填入实际版本和发布资产信息；
2. 将自动查询关闭；
3. 将精确版本传入 rebuild；
4. 构建时校验下载包版本/校验值。

在此之前 `KERNEL_PACKAGE_VERSION=UNLOCKED`，工作流不得执行打包步骤。

### 3.4 GitHub Actions 依赖

Action 必须固定到完整 commit SHA，而不是 `@main` 或可移动标签。当前记录了 checkout 与 upload-artifact 的候选 commit；正式 workflow 仍需逐一核实所用 Action 的接口、权限及兼容性。

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

## 5. 构建前检查清单

- [ ] 内核二进制包精确版本已确认且可下载。
- [ ] U-Boot 与 firmware 下载已改为固定 commit。
- [ ] Armbian Build、Ophub Action、上传 Action 均固定 commit。
- [ ] 构建 workflow 仅手动触发，不配置 push 自动构建。
- [ ] workflow 不包含 eMMC 安装或设备远程操作。
- [ ] DHCP 与 SSH 首启配置已经静态审查。
- [ ] 构建输出包含 manifest、日志和 SHA-256。
- [ ] 目标 TF 卡容量与写入设备已由用户确认。

## 6. 明确不做

- 不在首版镜像中部署 Immich。
- 不启用 RKNN/NPU/VPU 加速。
- 不改 Panther X2 当前系统、内核、驱动或网络服务。
- 不执行 eMMC 安装。
- 不因首次网络失败就反复刷写；先保留日志并定位 U-Boot、DTB、GMAC/PHY、NetworkManager 各层。
