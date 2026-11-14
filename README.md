# Panther X2 Armbian

用于 Panther X2（RK3566）家庭照片中心项目的系统构建研究。当前阶段只准备可追溯的构建基线，不自动部署、不操作设备。

## 目标

先得到一个从独立 TF 卡启动的最小 Armbian Server 系统，并通过以下验收：

- Panther X2 专用 DTB 与启动固件正确；
- RTL8211F/GMAC 建立稳定链路；
- 从家庭 DHCP 获取 IPv4 地址；
- iMac 与 Panther X2 双向通信；
- SSH 自动启动，冷启动和重启后均可直连；
- 拔掉 UART 后仍可正常管理。

网络验收通过前，不进入 Immich 部署和 NPU 加速测试。

## 当前选型基线

- SoC：RK3566；实机内存 4GB；单有线网口。
- OS：Ubuntu 24.04 LTS（Noble）。
- 内核系列：Ophub stable 6.18.y；候选二进制内核包固定为 6.18.63（SHA-256 已核验）。
- 文件系统：EXT4。
- 镜像类型：Server。
- 设备 DTB：`rk3566-panther-x2.dtb`。
- 启动文件：`idbloader.img`、`u-boot.itb`。
- 首轮介质：独立 TF 卡；不执行 eMMC 安装。

## 仓库状态

- `config/versions.env`：已知源码快照和待锁定项目。
- `docs/BUILD-PLAN.md`：构建链风险与后续步骤。
- `docs/DTB-AUDIT.md`：6.18.63 Panther X2 DTB 与驱动配置审计记录。\n- `docs/RKNPU-BSP-AUDIT.md`：RK3566 RKNPU 独立驱动来源、6.18.63 兼容性和 Panther X2 overlay 风险审计。
- `docs/NETWORK-ACCEPTANCE.md`：首启网络与 SSH 验收标准。
- `manifests/build-manifest.template`：每次构建的记录模板。

当前**没有可直接运行的镜像构建工作流**。内核包 6.18.63 已完成归档校验和内容清单检查；DTB 二进制已提取并反编译，关键节点与固定 Ophub DTS 快照高度吻合，但全量差异及精确构建来源仍未证明。RGA/VDEC 模块已确认存在；RKNPU 驱动和 NPU 设备节点尚未发现，已找到独立 RK3566 驱动候选，需先做离线兼容性验证。U-Boot/firmware 固定下载、Actions 依赖锁定及首启配置审查仍是构建前工作。后续构建只允许手动触发。

## 安全边界

- 不在仓库保存密码、令牌、SSH 私钥或其他凭据。
- 不自动触发构建；后续工作流应仅允许手动触发。
- 不写入 Panther X2 eMMC，不修改当前运行系统。
- 镜像只写入经确认的独立 TF 卡；写卡前必须核对目标设备。
- 不把“网口灯亮”“接口 UP”或一次 DHCP 租约当作网络验收通过。

## 研究状态标记

- **已确认**：有固定源码/配置或用户实机信息支持。
- **待验证**：需要构建或在 Panther X2 实机测试。
- **待锁定**：当前仍依赖动态版本或缺少可确认的版本号。
