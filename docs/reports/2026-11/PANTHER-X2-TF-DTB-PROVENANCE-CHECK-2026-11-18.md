# Panther X2 TF 卡 DTB 来源核查（2026-11-18）

## 结论摘要

- **已验证：** TF 卡启动脚本实际选择 `rockchip/rk3566-panther-x2.dtb`；U-Boot 从 TF 卡加载该文件，加载大小为 167,306 bytes。证据见本仓库报告 `GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md` 第 14.3 节及 2026-11-18 U-Boot 现场记录。
- **已验证：** TF 卡正式 DTB 与同目录 `rk3566-panther-x2.candidate.dtb` 均为 167,306 bytes，但 U-Boot CRC32 分别为 `6330e83a` 与 `ab4ef404`，因此二者不是相同二进制。
- **已验证：** 官方 `ophub/kernel` 的 `kernel_rk35xx` Release 在 2026-11-13 发布了 `6.12.81.tar.gz`，大小 141,437,450 bytes，GitHub 资产 SHA256 为 `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`。另有独立的 `deb-6.12.81.tar.gz`，不可与主包混淆。
- **已验证：** 官方 RK35xx 构建工作流支持 `kernel_package=all`（包含 Image、modules、dtbs）以及 `dtbs`（只生成 DTB 文件）；工作流把构建输出目录中的产物上传到 Release。
- **已验证：** `ophub/linux-6.12.y-rockchip` 提交 `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 中存在 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`。该文件 Git blob SHA 为 `d517c99841cf9d724a61cd31acf9437acbb131e6`。其板级定义包含 Panther X2 compatible、GMAC1 RGMII、RTL8211F 所用 MDIO PHY 节点、复位 GPIO/时序、TX/RX delay，以及 NPU 电源调节器定义。
- **尚未验证：** TF 卡上的正式 DTB 是否与官方 6.12.81 发布包内的 DTB 完全相同。当前研究环境可读取 GitHub 元数据及源码，但 GitHub connector 不支持二进制 Release 资产下载；因此未能从发布包提取 DTB 并计算 SHA256/CRC32。
- **尚未验证：** 上述源码提交哈希是否就是这次 6.12.81 资产构建时实际 checkout 的提交。提交时间（2026-11-13 08:01:39 UTC）早于主包上传时间（11:14:36 UTC），与构建时间线相符，但尚无对应 workflow run/job 日志或构建元数据作直接证明。
- **不能据此推断：** `rk3566-panther-x2.candidate.dtb` 的来源。用户明确说明自己只按既定步骤更换过 U-Boot，没有自行替换其他文件；因此不能把 candidate 文件归因于用户操作，也不能在没有镜像/文件历史证据时认定它是官方包原件或后续生成物。

## 官方 Release 资产身份

仓库：`ophub/kernel`  
Release：`kernel_rk35xx`  
官方主资产：
- 文件：`6.12.81.tar.gz`
- 资产 ID：`743358387`
- 大小：141,437,450 bytes
- SHA256：`72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`
- 上传时间：2026-11-13 11:14:36 UTC

同一 Release 的其他相近资产：
- `6.12.81-rk35xx-flippy-2611b.tar.gz`，资产 ID `743329557`，SHA256 `a5b0bc5d3c8311cee472c105e5ee2d1c9e6395a94efb4488253a0faae132d064`。这是不同的手动上传资产，不是上面的官方自动构建主包。
- `deb-6.12.81.tar.gz`，资产 ID `743358636`，SHA256 `e07d967c2a4d54aee3e910db414c100e01843db2a5b5e49e44d13942aec5e6bc`。

Release 页面：
https://github.com/ophub/kernel/releases/tag/kernel_rk35xx

## 构建流程核查

官方工作流：
https://github.com/ophub/kernel/blob/main/.github/workflows/compile-rockchip-rk35xx-kernel.yml

该工作流的手动输入包括：
- `kernel_source` 可选择 `ophub/linux-6.12.y-rockchip`；
- `kernel_version` 可选择 `6.12.y`；
- `kernel_package` 可选择 `all` 或 `dtbs`；
- 编译动作完成后，将 `PACKAGED_OUTPUTPATH` 下文件上传到 `kernel_rk35xx` Release。

上游构建动作文档说明：`all` 生成 Image、modules、dtbs；`dtbs` 仅生成 DTB 文件。由此可知 DTB 是独立的构建输出类别，但不能仅凭工作流定义还原本次运行时实际选择的输入参数或产物清单。

源码：
https://github.com/ophub/linux-6.12.y-rockchip/tree/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip

Panther X2 DTS：
https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts

## TF 卡现场证据

- U-Boot 设备映射：`mmc 1` 是 TF 卡；Linux 下 TF 卡为 `/dev/mmcblk0`。eMMC 为另一设备，未读取或修改其内容。
- TF 卡 `armbianEnv.txt` 设置 `fdtfile=rockchip/rk3566-panther-x2.dtb`。
- 实际 `boot.scr` 从当前 TF 卡分区读取 `dtb/${fdtfile}`，并把该 DTB 传给内核。
- UART 启动记录显示 DTB 读取大小 167,306 bytes。
- 正式 DTB CRC32：`6330e83a`。
- candidate DTB CRC32：`ab4ef404`。
- 两者长度相同、CRC 不同；不能互相视为相同文件。

## 下一步（不修改设备）

要完成真正的二进制同一性判定，需要取得官方 `6.12.81.tar.gz` 或同构建生成的 DTB 包，提取 `rk3566-panther-x2.dtb`，计算 SHA256/CRC32，并与 TF 卡正式 DTB 比较。若主包没有直接包含 DTB，则检查同一构建产生的 `deb-6.12.81.tar.gz` 或 `linux-dtb-rockchip64-ophub` 包，并先确认其版本/构建身份。

在完成上述比较前，正式 DTB 的状态应记录为“与启动配置一致、来源高度可能为原始系统文件，但尚未完成官方发布包二进制核验”；candidate DTB 的来源保持未知。

## 操作边界

本次只读取公开 GitHub 元数据、构建脚本、源码及已有 TF 卡现场记录。没有对 Panther X2、TF 卡或 eMMC 执行写入、安装或配置修改。
