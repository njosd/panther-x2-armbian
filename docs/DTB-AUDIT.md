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

已更新 `.github/workflows/inspect-kernel-package.yml`：下一次手动运行时，会从固定的 `dtb-rockchip-6.18.63-ophub.tar.gz` 中提取 `rk3566-panther-x2.dtb`，记录文件 SHA-256，并使用 `dtc` 反编译为 DTS，将原始 DTB、反编译文本和警告日志一并上传为 artifact。**该新增步骤尚未运行，结果待验证。**

拿到 artifact 后，只对启动关键节点（GMAC/MDIO/PHY、SDHCI/eMMC、SDMMC/TF、USB host）做差异审查。不因这项检查重新编译内核，也不把 NPU/GPU/多媒体节点列为第一版启动阻塞项。检查通过后继续最小 BSP 补丁集和手动 TF 镜像构建。


## 2026-11-14：6.18.63 DTB 实物提取与加速器静态审计（新增）

本节基于 Actions run [43543451274](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274) 的 artifact（artifact id: 14093500129）。本次 artifact 已包含 DTB 二进制、反编译 DTS、DTB SHA-256 和模块归档清单；此前“未取得 DTB 二进制”的状态已更新。

### DTB 实物

- 文件：`rk3566-panther-x2.dtb`
- SHA-256：`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`
- `dtc` 反编译成功；`dtc-warnings.txt` 为空。
- 反编译结果识别为 `model = "Panther X2"`、`compatible = "panther,x2", "rockchip,rk3566"`。

### 与固定 Ophub DTS 源码快照的关系

固定源码：`ophub/linux-6.18.y` commit `9bbed25243be8b43df410ebb9a8bbb1992234114`，文件 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`，blob SHA `a0a08476f45fb2d602fd7312def6f587f33fb91e`。

静态抽查显示，包内 DTB 与该源码在 Panther X2 板型识别、GMAC1/RGMII/PHY reset/延时、SDHCI eMMC、SDMMC TF/SDIO、USB 控制器等关键硬件描述上高度吻合。DTB 的 alias 展开结果也显示 `mmc0` 指向 `/mmc@fe310000`（SDHCI/eMMC），与 Ophub 源码的 `mmc0 = &sdhci` 一致。

但这仍是关键节点的静态抽查，不是对 DTS 全部属性、所有 include 展开结果的逐字节/逐属性完整 diff；也不能单凭相似性证明二进制一定由上述 commit 构建。二进制与源码的构建来源关系继续标记为“高度吻合、精确 provenance 未证实”。

### 多媒体与 NPU 证据（重要更正）

此前检查脚本使用了不准确的配置符号名称（例如 `CONFIG_ROCKCHIP_RGA`），导致结果显示 `NOT_RECORDED`。从实际 modules 归档中的生成配置头和模块文件可进一步确认：

- `include/config/VIDEO_ROCKCHIP_RGA` 存在，且 `drivers/media/platform/rockchip/rga/rockchip-rga.ko` 存在：RGA 驱动已编译为模块并打包。
- `include/config/VIDEO_ROCKCHIP_VDEC` 存在，且 `drivers/media/platform/rockchip/rkvdec/rockchip-vdec.ko` 存在：Rockchip VDEC 驱动已编译为模块并打包。
- `drivers/media/platform/verisilicon/hantro-vpu.ko` 也存在，但它不能直接等同于 RK3566 的 RKNPU。
- 在本次 modules 归档完整文件清单及相关模块路径筛选中，未发现 RKNPU 驱动模块或明确的 Rockchip MPP/VENC 模块。
- DTB 反编译文本包含 `vdd_npu` 电源轨、`qos_npu` 节点及 NPU pin group 相关信息，但未发现可识别的 NPU 设备节点（例如 `npu@...`）。这说明板级 DTS/BSP 留有 NPU 相关资源描述，**不等于 Linux NPU 驱动已启用**。

因此当前结论：
- RGA：软件包中存在驱动模块，静态证据已确认；尚未在 Panther X2 实机验证驱动成功 probe 或用户态调用。
- VDEC：软件包中存在驱动模块，静态证据已确认；尚未验证硬件解码路径和应用兼容性。
- VENC：当前归档未找到对应 Rockchip 编码驱动模块，待确认是否以其他驱动形式提供。
- RKNPU/RKNN：当前没有可用驱动证据；不能把 NPU 电源/QoS 描述当成驱动支持。
- MPP：当前未找到明确的 MPP 服务/驱动证据；用户态 MPP 库与内核驱动还需分开审计。

### 检查脚本修正

在 commit `1ce47d772e26becadab4b773e32150d8a054a52c` 中修正配置符号审计：
- 使用实际的 `CONFIG_STMMAC_ETH`、`CONFIG_VIDEO_ROCKCHIP_RGA`、`CONFIG_VIDEO_ROCKCHIP_VDEC` 等符号；
- 将完整内核 `.config` 纳入 artifact，避免以后只凭 `NOT_RECORDED` 摘要判断。
- 该修正提交尚未由新的 Actions run 验证；下一次手动运行后再将完整配置结果标为已验证。

### 更新后的状态

| 项目 | 状态 |
|---|---|
| DTB 原始二进制与 SHA-256 | 已取得并验证文件存在 |
| DTB 反编译 | 已完成，无 dtc 警告 |
| 板型/GMAC/PHY/eMMC/TF/USB 关键节点 | 已静态抽查，与固定 Ophub DTS 高度吻合 |
| DTB 与 DTS 精确构建来源 | 未证实 |
| RGA 模块及配置头 | 已确认存在，实机未验证 |
| VDEC 模块及配置头 | 已确认存在，实机未验证 |
| VENC / MPP 内核支持 | 未发现明确模块，继续审计 |
| RKNPU/RKNN 驱动 | 未发现，未验证 |
| 实机启动及 Immich 硬件加速 | 未验证 |

本阶段仍不安装、不修改 Panther X2，不制作或写入镜像。下一步优先审计 RKNPU 驱动来源和可移植补丁边界；首版启动验收不等待 NPU。


## 2026-11-14：RKNPU BSP 来源与 Mainline 可移植路线（新增）

### 1. Panther X2 Vendor 6.1 路线的直接证据

参考仓库：[`Lyric-c/panther-x2`](https://github.com/Lyric-c/panther-x2)，固定参考 commit `2ceb614fc294b4832268ec3e50716e7e9d3f1e8b`。

- 分支说明将 `vendor` 定义为 Rockchip BSP 6.1.y，内核源为 `armbian/linux-rockchip` 的 `rk-6.1-rkr5.1`；`current` 则为 mainline 6.18.y。
- Vendor 设备树 `userpatches/kernel/rk35xx-vendor-6.1/dt/rk3566-panther-x2.dts` 明确启用 `&rknpu`、`&rknpu_mmu`、`&bus_npu`，并设置 `rknpu-supply = <&vdd_npu>`；同时启用 `&mpp_srv`、`&rkvdec`、`&rkvenc` 等多媒体节点。
- 对应 Vendor SoC DTSI `arch/arm64/boot/dts/rockchip/rk356x.dtsi` 定义 `npu@fde40000`，compatible 为 `rockchip,rk3568-rknpu`、`rockchip,rknpu`，并定义 NPU 时钟、复位、电源域、OPP 和 IOMMU。
- 同一 Vendor 内核树包含 `drivers/rknpu/`，其 `Kconfig` 定义 `CONFIG_ROCKCHIP_RKNPU`，`drivers/Kconfig` 和 `drivers/Makefile` 分别接入该驱动目录。
- `rknpu_drv.c` 中的 `rk356x_rknpu_config` 被 `compatible = "rockchip,rknpu"` 使用；这为 RK3566/RK3568 共用的 RKNPU 驱动路径提供了源码证据。

以上证明 Vendor 6.1 方案不只是给设备树加一个节点，而是由 SoC DTSI、板级 DTS、RKNPU 驱动源码、Kconfig/Makefile 和 Rockchip IOMMU/电源/时钟等内核子系统共同组成。

### 2. 已发现的 Mainline 外置驱动路线

参考项目：[`w568w/rknpu-module`](https://github.com/w568w/rknpu-module)。该项目将 Rockchip Vendor RKNPU 驱动移植为 mainline Linux 的 out-of-tree 模块，并提供 RK3566 设备树 overlay。

其 README 声明的实测环境为 OrangePi 3B v1.1（RK3566）、Armbian mainline `6.19.3-edge-rockchip64` / `7.0.0-rc7-edge-rockchip64`，配套 `librknnrt v2.3.2`。这比直接移植整套 Vendor 内核更接近本项目所需的独立驱动包路线，但当前没有证据证明它可直接编译运行于 Ophub 6.18.63。

该项目 overlay `dts/rk3566-rknpu-overlay.dts` 的设计特点：
- 以 overlay 添加 `npu@fde40000`、NPU power domain 和 OPP 表，不必替换整份 Panther X2 DTB；
- NPU 使用 `rockchip,rk3568-rknpu` / `rockchip,rknpu` compatible；
- overlay 将 NPU IOMMU 节点保持 disabled，先以 non-IOMMU 模式运行；
- 项目明确记录 RK3566 IOMMU v2 页表可能被分配到 4GB 以上物理地址、导致总线错误的问题；其临时规避方式是禁用 NPU IOMMU，而不是直接启用 Panther X2 Vendor DTS 中的 `&rknpu_mmu`。

**特别注意：** Panther X2 实机内存为 4GB，不能把该项目针对 OrangePi 3B 的 IOMMU 结论未经验证地直接套用；但它足以说明第一轮移植/编译验证不应默认启用 NPU IOMMU。应先核对 Panther X2 的 RAM 地址布局、NPU DMA mask、CMA 和驱动实际模式。

### 3. Rocket 与 RKNN Runtime 不是同一套接口

Linux 6.18 官方 Rocket 文档列出的硬件支持对象为 RK3588；Rocket 使用 Mesa/Teflon 用户态栈，不是 Vendor RKNPU 驱动 ABI。Immich 的 RKNN 后端讨论也记录了 `librknnrt` 需要 Vendor `rknpu` 模块，不能仅因系统存在 Rocket 设备节点就认为 RKNN Runtime 可用。

因此本项目需要区分：
- Mainline Rocket：不能作为 RK3566 的 RKNN 路线依据；
- Vendor `rknpu`：RK3566 BSP 路线，具备官方 RKNN Runtime 生态；
- `w568w/rknpu-module`：将 Vendor ABI 驱动移植到 mainline 的外置模块，已报告在 RK3566 + 6.19.3 实测，但对本项目 6.18.63 尚未验证。

### 4. 当前技术判断

优先级调整如下：
1. **保留 Ophub 6.18.y 主线作为基础系统候选。**
2. 将 `w568w/rknpu-module` 作为优先审计的独立 RKNPU 模块候选，而不是立即移植完整 Vendor 6.1 内核。
3. 单独审计其代码、许可证、内核 API 依赖、DKMS/Kbuild、设备树 overlay、IOMMU 规避方式及 RKNN Runtime 版本要求。
4. 先在 GitHub Actions 中使用固定模块源码 commit 和 Ophub 6.18.63 header 包做纯编译验证；只有编译通过后，才考虑制作独立补丁/模块包。编译通过仍不等于实机 probe 或 RKNN 推理成功。
5. 如果 6.18.63 API 差异导致移植成本过高，再评估升至已被该模块验证的 6.19.y Ophub 内核，或保留 Vendor 6.1 作为 NPU 专用备选；暂不改变已选主线。

### 5. 证据与限制

- Vendor 6.1 驱动源与 Panther X2 DTS：静态源码已读取；未在本项目重新构建或实机验证。
- `w568w/rknpu-module`：上游 README 报告 RK3566 + 6.19.3 实测；这是第三方项目声明，不是 Panther X2 实测。
- 6.18.63：当前包未发现 RKNPU 模块或 NPU 节点；尚未尝试移植外置模块。
- RKNN Runtime：官方 `rknn-toolkit2` 文档列出 RK3566 支持平台；具体运行库版本与外置驱动 ABI 仍需配套验证。
- Immich：RKNN 后端与 Vendor `rknpu` ABI 的关系有公开项目讨论记录；尚未在本项目 Immich 部署环境验证。

参考链接：
- [Panther X2 Vendor/Mainline 分支与构建说明](https://github.com/Lyric-c/panther-x2/blob/2ceb614fc294b4832268ec3e50716e7e9d3f1e8b/README.md)
- [Panther X2 Vendor 6.1 DTS](https://github.com/Lyric-c/panther-x2/blob/2ceb614fc294b4832268ec3e50716e7e9d3f1e8b/userpatches/kernel/rk35xx-vendor-6.1/dt/rk3566-panther-x2.dts)
- [w568w RKNPU mainline module](https://github.com/w568w/rknpu-module)
- [Linux 6.18 Rocket documentation](https://docs.kernel.org/6.18/accel/rocket/index.html)
- [RKNN Toolkit2](https://github.com/rockchip-linux/rknn-toolkit2)
- [Immich RKNN backend discussion](https://github.com/immich-app/immich/discussions/30970)


### 6. 外置模块源码快照锁定（补充）

为避免后续审计跟随可变 `main`，已读取 `w568w/rknpu-module` 当前 main 分支并锁定本轮审计快照：

- Repository: `w568w/rknpu-module`
- Branch: `main`
- Commit: `a8792fe6b633f90cf2c6808267cac327537ab4cf`
- Commit message: `ci: switch to DietPi apt repo to match device kernel (7.0.0-rc7)`
- DKMS package version: `rknpu/0.9.8`
- License: GPL-2.0（上游 README 声明）

静态检查到的构建组成：
- `Kbuild` 以 out-of-tree 模块方式构建 `rknpu.o`，核心对象包括 driver、GEM、fence、job、reset、IOMMU、debugger、devfreq；
- 编译定义选择 DRM GEM、debugfs、fence 路径；没有选择 Vendor DMA Heap 路径，因此该快照不依赖 `rknpu_mem.o` / `linux/rk-dma-heap.h`；
- `src/include/compat/rockchip/` 提供若干 Rockchip 私有头文件兼容层，至少包含 `rockchip_iommu.h`、`rockchip_ipa.h`、`rockchip_opp_select.h`、`rockchip_system_monitor.h`；
- DKMS 配置包名/版本为 `rknpu/0.9.8`，并设置 `AUTOINSTALL=yes`；
- overlay 是单独的 `dts/rk3566-rknpu-overlay.dts`，与模块可分开编译/审计。

这说明它不是简单复制 Vendor 6.1 的整个驱动目录，而是已做过一轮 out-of-tree 拆分和兼容封装，符合“独立 BSP 功能包”的方向。仍需重点核对兼容层是否足以覆盖 Ophub 6.18.63、devfreq 相关 API、模块符号依赖、overlay 的 Panther X2 regulator/clock/power-domain 映射及实际 4GB RAM/IOMMU 风险。

**本 commit 仅作为审计输入锁定，不代表推荐直接安装或自动更新。** 下一轮 CI 必须使用该固定 SHA，而不是 `main`。
