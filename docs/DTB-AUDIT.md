# Panther X2 DTB 核验记录

更新日期：2026-11-14

## 结论摘要

- Ophub 6.18.63 内核包的 DTB 归档清单中，**确实存在** `rk3566-panther-x2.dtb`。
- 6.18.63 检查报告同时确认 ARM64 内核映像存在；相关内核配置记录了 Rockchip GMAC、Realtek PHY、Rockchip MMC 控制器支持。
- 已重新读取 Panther X2 6.18 DTS 源文件，Git blob SHA 为 `52cbb88552dcae7d15a18682c7a77ec0888dbdc3`。
- **尚未完成 DTB 二进制内容与 DTS 源码的逐项比对**：本次 Actions artifact 上传的是归档清单、校验结果和配置摘要，并未包含可供本地反编译的 DTB 二进制。因此目前只能确认目标 DTB 文件名在内核包中，不可声称其内容与指定 DTS 完全一致。

## 固定输入

### Ophub 内核包

- 版本：`6.18.63`
- 资产：`https://github.com/ophub/kernel/releases/download/kernel_stable/6.18.63.tar.gz`
- 外层 SHA-256：`47e3f46636594cbf212474a13bac97e1310c3ee51007dee3fa20f93d8659f1ca`
- 检查工作流：`.github/workflows/inspect-kernel-package.yml`
- 检查运行：`43526258367`
- artifact：`ophub-kernel-6.18.63-driver-inspection`

检查 artifact 中的 `checksum-verification.txt` 显示 6 个内部归档均 MATCH；外层归档 SHA-256 也与仓库记录一致。内层 Rockchip DTB 包清单列出 `rk3566-panther-x2.dtb`。

### DTS 参考源

- 仓库：[`Lyric-c/panther-x2`](https://github.com/Lyric-c/panther-x2)
- 路径：`userpatches/kernel/rockchip64-6.18/dt/rk3566-panther-x2.dts`
- Git blob SHA：`52cbb88552dcae7d15a18682c7a77ec0888dbdc3`
- 文件链接：[DTS source](https://github.com/Lyric-c/panther-x2/blob/2ceb614fc294b4832268ec3e50716e7e9d3f1e8b/userpatches/kernel/rockchip64-6.18/dt/rk3566-panther-x2.dts)

注意：该 DTS 是独立的 Panther X2 6.18 参考快照。当前没有证据证明 Ophub 6.18.63 包内 DTB 正是由该 blob 编译生成；两者应分别记录，不建立未经验证的源码—二进制对应关系。

## DTS 中与第一版启动有关的节点

以下内容来自上述固定 DTS 源文件：

| 功能 | DTS 配置摘要 | 对第一版的意义 |
|---|---|---|
| 板型识别 | model = Panther X2；compatible = panther,x2 / rockchip,rk3566 | 板型匹配 |
| 有线网卡 | `ethernet0 = &gmac1` | 使用 GMAC1 |
| GMAC PHY | `phy-mode = "rgmii"`；`phy-handle = &rgmii_phy1` | RGMII PHY 链路配置 |
| PHY 地址 | `ethernet-phy@0`，`reg = <0>` | 当前参考 DTS 使用 PHY 地址 0 |
| PHY 时序 | `tx_delay = <0x30>`；`rx_delay = <0x10>` | 需要实机链路验证 |
| PHY 复位 | GPIO3 PA1，低有效；复位延时 0/20/100 ms | 需要实机链路验证 |
| eMMC | `&sdhci`，8-bit、HS200 1.8V、non-removable | 系统存储控制器配置 |
| TF 卡 | `&sdmmc0`，4-bit、broken-cd | 独立 TF 卡启动目标 |
| USB | XHCI/USB2 host 节点启用 | 基础 USB host 支持 |

## 6.18.63 内核配置摘要

来自 Actions artifact 的 `relevant-kernel-config.txt`：

- `CONFIG_ARM64=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_REALTEK_PHY=y`
- `CONFIG_MMC=y`
- `CONFIG_MMC_SDHCI_OF_DWCMSHC=y`
- `CONFIG_MMC_DW_ROCKCHIP=y`
- `CONFIG_USB_DWC3=y`

这些配置表明内核具备相关驱动支持，但不能单独证明目标设备树、时钟、复位、供电和 PCB 接线完全匹配。

## 状态判定

| 项目 | 状态 |
|---|---|
| 6.18.63 外层归档 SHA-256 | 已验证 |
| 6 个内部归档 SHA-256 | 已验证 |
| Panther X2 DTB 文件名存在于 Rockchip DTB 包清单 | 已确认 |
| 6.18.63 内核映像为 ARM64 Image | 已确认 |
| GMAC / Realtek PHY / Rockchip MMC 配置项 | 已确认 |
| DTS 参考源及 blob SHA | 已确认 |
| 包内 DTB 二进制 SHA-256 | 未取得 |
| 包内 DTB 反编译内容与指定 DTS 比对 | 未完成 |
| Panther X2 实机启动、DHCP、SSH | 未验证 |

## 下一步（保持最小范围）

在后续构建工作流中增加一个轻量检查步骤：从固定的 `dtb-rockchip-6.18.63-ophub.tar.gz` 中实际提取 `rk3566-panther-x2.dtb`，记录文件 SHA-256，并使用 `dtc` 反编译为 DTS，保存反编译结果作为 artifact。随后只对启动关键节点（GMAC/MDIO/PHY、SDHCI/eMMC、SDMMC/TF、USB host）做差异审查。

不因这项检查重新编译内核，也不把 NPU/GPU/多媒体节点列为第一版启动阻塞项。检查通过后继续最小 BSP 补丁集和手动 TF 镜像构建。
