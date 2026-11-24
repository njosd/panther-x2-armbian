# Panther X2 6.12.81 启动依赖闭包审计

> 状态：A1 第一轮静态审计记录（2026-11-15）
>
> 范围：仅源码、设备树、内核配置、构建脚本与仓库文件树审计；未构建镜像、未写 TF 卡、未操作 Panther X2 实机。

## 1. 固定审计基线

| 项目 | 固定值 |
|---|---|
| 目标板 | Panther X2 / RK3566 |
| Ophub Armbian | `9e71b57f73683f9c4d14a30311e4c2ccbff29566` |
| Linux 6.12.81 源码参考 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` |
| Kernel config 来源 | `ophub/kernel@c23196e10d7702ee2906de4a05421d8971fb2717` |
| Kernel config blob SHA-1 | `dee127c6c644f38426eeb28000d73536084d34a3` |
| U-Boot 文件仓库快照 | `ophub/u-boot@6e70f41585f15c43f45fcae609adec1865e83eb5` |
| Firmware 仓库快照（待核对文件） | `ophub/firmware@a9d0e8337cc8aa2ca4b482acd7b19c74ce05860f` |
| 首轮介质 | 独立 TF 卡；不写 eMMC |

以上源码和配置版本用于审计追溯，不代表完整镜像已经构建或通过实机验证。

## 2. 启动固件与设备数据库

固定 Ophub Armbian 的 `model_database.conf` 中 Panther X2 项为：

- DTB：`rk3566-panther-x2.dtb`
- Mainline U-Boot：`u-boot.itb`
- Bootloader：`idbloader.img`
- 平台/目录：`rockchip/panther-x2`
- 当前上游内核匹配字段：`stable/6.18.y`

### 2.1 文件存在性核对

在固定 U-Boot commit 的文件树中，以下两个文件均存在：

- `u-boot/rockchip/panther-x2/idbloader.img`
  - Git blob SHA-1：`d22b624fc90c46e656baf98894bee182316e692e`
- `u-boot/rockchip/panther-x2/u-boot.itb`
  - Git blob SHA-1：`04cd10bddd4e823d2ea495ee95b264cb2bce1f4c`

两者与本次读取的 U-Boot 默认分支文件 blob SHA-1 相同。注意：这是 Git blob SHA-1，不是文件 SHA-256；仍需在 CI 下载实际文件后计算 SHA-256、记录字节数并保存构建清单。

**已确认：** 固定 commit 的文件树包含 Panther X2 对应的两个启动文件，不能仅因该 commit 的提交说明提及 Z93A 就判定其缺少 Panther X2 文件。

**待验证：** 两个二进制的原始构建来源、DDR 初始化/训练参数、U-Boot 版本及其与 Panther X2 实物内存配置的对应关系。文件路径和 Git blob ID 本身不能证明这些内容。

### 2.2 Ophub rebuild 的写入位置

固定 Ophub Armbian `rebuild` 脚本在生成新镜像时，对 Rockchip 平台使用：

- `idbloader.img`：写入 LBA 64（512-byte sector）
- `u-boot.itb`：写入 LBA 16384

Panther X2 设备数据库的 TRUST_IMG 字段为 NA，因此该分支只写入上述两个文件，不执行 LBA 24576 的 TRUST_IMG 写入。此处的 `dd` 目标是正在生成的镜像 loop device，不是正在运行的 Panther X2 实机。

### 2.3 构建可追溯性阻塞项

固定 Ophub Armbian commit 中的 `git_pull_dir` 使用 `git clone --branch=main --depth=1`；`download_depends` 对 U-Boot 和 firmware 都从 `main` 下载。

因此，仓库 `config/versions.env` 虽然记录了 U-Boot 与 firmware commit，但上游 rebuild 脚本并不会自动使用这些 commit。必须在构建流程中做最小补丁：固定 checkout 到记录的 commit，或按固定 commit 下载所需文件，并在构建日志记录实际 HEAD 和文件 SHA-256。完成前不能称为可追溯的固定构建链。

## 3. Panther X2 启动环境配置

固定板级文件 `build-armbian/armbian-files/different-files/panther-x2/bootfs/armbianEnv.txt` 的关键项：

- `fdtfile=rockchip/rk3566-panther-x2.dtb`
- `rootdev=/dev/mmcblk0p2`
- `rootfstype=ext4`
- `extraargs=rw rootwait`
- `console=both`
- `consoleargs=console=ttyS02,1500000 console=tty0`
- `extraboardargs=net.ifnames=0 max_loop=128`

该配置明确选择 Panther X2 DTB、EXT4 根文件系统及串口控制台。根分区目前使用设备节点 `/dev/mmcblk0p2`，其正确性依赖 Linux MMC 编号符合设备树 alias；需在实机首次启动时核对实际枚举，不应仅凭 DTS 静态映射宣布通过。

## 4. MMC / TF / eMMC 依赖

固定板级 DTS 的 aliases：

- `mmc0 = &sdmmc0`：TF/SD
- `mmc1 = &sdhci`：eMMC
- `mmc2 = &sdmmc1`：SDIO（板载无线模块）

关键节点：

- `&sdmmc0`：4-bit SD，`broken-cd`，状态 okay；使用 Rockchip DesignWare MMC 控制器。
- `&sdhci`：8-bit、non-removable、HS200 1.8V eMMC，状态 okay；使用 Rockchip DWCMSHC SDHCI 控制器。
- `&sdmmc1`：SDIO/Wi-Fi，带 `mmc-pwrseq-simple` 上电时序；不是首版 TF 启动的必要介质。

固定 RK35xx 6.12 config-6.12 中相关选项均为内建（`=y`）：

- `CONFIG_MMC`
- `CONFIG_MMC_BLOCK`
- `CONFIG_MMC_DW`
- `CONFIG_MMC_DW_ROCKCHIP`
- `CONFIG_MMC_SDHCI`
- `CONFIG_MMC_SDHCI_OF_DWCMSHC`
- `CONFIG_PWRSEQ_SIMPLE`

驱动匹配关系也已静态核对：SDMMC0 DTS 的 compatible 列表包含 `rockchip,rk3288-dw-mshc` fallback，固定源码的 `dw_mmc_rockchip_match` 表包含该 fallback；eMMC 的 `rockchip,rk3568-dwcmshc` compatible 由 `sdhci-of-dwcmshc` 驱动匹配。

**阶段结论：** 固定 config-6.12 为 TF、eMMC 控制器提供了内建驱动，不依赖 initramfs 在根文件系统挂载后再加载这些模块。DTS、驱动和配置之间的静态关系目前一致。

**仍未验证：** 实机 TF 启动、eMMC 识别、实际 mmcblk 编号、TF/eMMC 读写和多轮启动稳定性。

## 5. PMIC / regulator / I²C / 时钟依赖

板级 DTS 中：

- I²C0 启用。
- TCS4525 位于 I²C 地址 `0x1c`，compatible 为 `tcs,tcs4525`，为 CPU 提供 `vdd_cpu`。
- RK809 位于 I²C 地址 `0x20`，提供多路 regulator 和时钟输出；DTS 还使用其时钟输出作为 SDIO pwrseq 外部时钟。

固定 config-6.12 中相关驱动均为内建：

- `CONFIG_I2C_RK3X=y`
- `CONFIG_MFD_RK808=y`
- `CONFIG_REGULATOR_RK808=y`
- `CONFIG_REGULATOR_FAN53555=y`
- `CONFIG_REGULATOR_FIXED_VOLTAGE=y`
- `CONFIG_COMMON_CLK_ROCKCHIP=y`
- `CONFIG_CLK_RK3568=y`
- `CONFIG_PINCTRL_ROCKCHIP=y`
- `CONFIG_ROCKCHIP_PM_DOMAINS=y`

注意：TCS4525 并没有单独的 `CONFIG_REGULATOR_TCS4525` 选项；固定源码的 `drivers/regulator/fan53555.c` 明确包含 `tcs,tcs4525` OF 匹配项，对应配置是 `CONFIG_REGULATOR_FAN53555=y`。

**阶段结论：** 在固定 config-6.12 中，DTS 所需的 I²C、RK809、TCS4525/FAN53555、Rockchip 时钟和 pinctrl 驱动均有内建配置证据。

**仍未验证：** 实机 I²C 设备响应、PMIC/regulator probe、CPU 电压调节、启动时序和电源管理稳定性。不能仅凭驱动配置为 y 就认定供电工作正常。

## 6. 已发现的 6.12.81 版本选择冲突

固定 Ophub Armbian 的 Panther X2 设备数据库仍把可选内核范围限制为 `stable/6.18.y`。而本项目选择的 6.12.81 发布资产位于 `kernel_rk35xx`，不是 `kernel_stable`。

rebuild 脚本的 `-u` 参数可以把默认 tag 从 stable 改为 rk35xx，但 `confirm_version` 仍会按设备数据库中的版本范围过滤内核版本。因此只传 `-u rk35xx -k 6.12.81 -a false` 仍会因 Panther X2 行只允许 6.18.y 而被版本过滤拒绝。

构建前必须在项目自己的设备数据库补丁中，把 Panther X2 内核范围调整为支持 6.12.y，并明确使用 `kernel_rk35xx`。建议项目补丁后的行表达为 `rk35xx/6.12.y`，再指定固定版本 6.12.81；最终参数仍需在纯 CI 中验证。

另外，当前项目 `config/versions.env` 的 `TARGET_KERNEL_BRANCH=stable` 与 6.12.81 的 `kernel_rk35xx` 发布渠道不一致，应在构建流程定稿时同步修正，避免变量名误导或实际下载错 release tag。

## 7. 当前判定

| 项目 | 判定 |
|---|---|
| Panther X2 U-Boot 文件路径存在 | 已确认 |
| 固定 U-Boot commit 与当前分支文件 blob 一致 | 已确认（Git blob SHA-1） |
| U-Boot 二进制 SHA-256、大小和来源 | 待验证 |
| Ophub rebuild 写入 LBA 64 / 16384 的逻辑 | 已确认 |
| U-Boot / firmware 下载固定 commit | 未完成，构建阻塞 |
| Panther X2 DTB / 根文件系统启动参数 | 已静态核对 |
| TF / eMMC 控制器和内建驱动匹配 | 已静态核对 |
| RK809 / TCS4525 / I²C / 时钟内建驱动 | 已静态核对 |
| 6.12.81 与设备数据库版本过滤兼容 | 当前不兼容，需项目补丁 |
| 实机启动、存储读写和稳定性 | 未验证 |

## 8. A1 下一步

1. 对两个 Panther X2 U-Boot 二进制下载并计算文件 SHA-256、字节数；核对 FIT 内容、U-Boot 版本、默认环境及启动介质支持。
2. 审查 Ophub rebuild 的最小补丁：U-Boot / firmware 固定 commit，Panther X2 kernel tags 允许 6.12.y，并把 6.12.81 固定到 `kernel_rk35xx`。
3. 检查 6.12.81 发布包内部实际 `.config` 与固定 config-6.12 的差异，确认上述内建驱动配置确实进入最终包。
4. 完成上述静态闭包审计后，再进入镜像构建前检查；仍不刷机、不写卡、不修改 192.168.x.6。

本报告只记录静态证据和构建阻塞，不代表完整系统已在 Panther X2 实机运行。


## 9. U-Boot 历史来源追查补充（2026-11-15）

继续追查 Panther X2 最初适配记录后，发现比“二进制文件在仓库中存在”更关键的历史证据：

- Ophub 原始适配 Issue #1319 的讨论中，适配者明确说明：Panther X2 的 U-Boot 当时“暂时还是借用的 Radxa E23 的”。
- 同一讨论中，适配者表示 Panther X2 的 DTS 是参照 Armbian 主线、参考 Radxa E25 修改，U-Boot 源码当时未公开。
- 这说明当前 Ophub U-Boot 仓库中的 Panther X2 命名文件，不能仅凭路径认定为 Panther X2 专门构建的完整板级固件。至少其早期来源与 Radxa E23 存在继承关系。

来源：
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319#issuecomment-1521843631
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319#issuecomment-1521443259
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319#issuecomment-1521446968

### 风险解释

这不是“必然不能启动”的结论。RK3566/RK3568 同属 Rockchip RK35xx 家族，部分 SPL/U-Boot 代码可能复用；但 IDB/SPL 阶段涉及 DDR 初始化和板级电源/时钟配置，不能仅凭 SoC 家族相同推断适配正确。

因此更新状态：

| 项目 | 新判定 |
|---|---|
| Panther X2 命名的 U-Boot 文件存在 | 已确认 |
| 早期 U-Boot 继承/借用 Radxa E23 | 已确认（历史讨论证据） |
| 当前二进制是否仍为 E23 原始文件或后续修改版本 | 待验证 |
| DDR 初始化参数是否匹配 Panther X2 实际内存 | 待验证，重要风险 |
| U-Boot 是否能从 TF 卡稳定启动并正确加载 Panther X2 DTB | 未实机验证 |

### 必须补齐的证据

1. 找出 Ophub U-Boot 仓库中 Panther X2 两个二进制的首次加入记录、后续替换记录及其对应来源。
2. 找到可公开取得的 Radxa E23 U-Boot 文件/构建配置，比较其二进制哈希和可识别结构；如果没有原始文件，明确标记无法直接比较。
3. 从可识别的 SPL/U-Boot 镜像中提取版本字符串、FIT 配置、设备树、DDR 初始化相关信息；必要时使用专门的 Rockchip 镜像分析工具，在 CI 中只读分析，不对设备执行写入。
4. 确认 Panther X2 的内存颗粒/容量/总线配置与启动固件 DDR 初始化参数相容。

在这些证据补齐前，不把当前 U-Boot 文件标记为“已验证适配 Panther X2”，也不进入实机刷写阶段。

### 历史 USB 风险提示

同一 Issue #1319 还记录了早期 Panther X2 Armbian 镜像 USB 无法工作的报告，后续维护者表示会修复。该历史报告不能直接推断当前 6.12.81 USB 也有故障，但说明 USB 必须作为 A2 的独立验收项目，不能只因 DTS 中 USB2 host 节点为 okay 就判定可用。


## 10. 原始适配分支与 E23 启动链证据补充（2026-11-15）

### 10.1 原始适配分支

通过原始适配者公开的 `tdleiyao/armbian` `panther-x2` 分支读取到分支头提交：

- Commit：`99e8ca02b3472dcc5ad9daa7e7a87cdc22ce9a02`
- 标题：`Panther X2: Modify usb mode and enable GPU`

该提交的可见改动集中于 Panther X2 Linux DTS（包括 USB host 模式、USB2 PHY host 节点、GPU 和 SARADC 状态等），未看到 U-Boot 源码、defconfig 或 U-Boot 构建补丁。该事实与 Issue #1319 中“U-Boot 暂时借用 Radxa E23”的说明相互吻合。

分支文件 `config/sources/families/rockchip.conf` 显示该 Armbian 分支的 Rockchip 家族默认 U-Boot 分支为 `tag:v2022.04`（miqi 除外）。但由于当前可见 Panther X2 分支没有可读取的专用 board config / U-Boot 补丁，尚不能从该文件单独证明 Panther X2 的实际 U-Boot defconfig、编译命令和产物来源。

### 10.2 当前 Ophub U-Boot 仓库的比较限制

在固定 Ophub U-Boot commit `6e70f41585f15c43f45fcae609adec1865e83eb5` 中：

- Panther X2 目录存在 `idbloader.img` 与 `u-boot.itb`。
- 没有找到 `u-boot/rockchip/radxa-e23/` 或 `u-boot/rockchip/e23/` 对应的同名二进制文件。
- Rock 3A 文件存在，但它不是 Radxa E23 文件，不能拿它作为 E23 的二进制对照样本。
- GitHub 二进制 blob 读取接口无法以 UTF-8 返回这些二进制内容；当前 connector 只能确认 blob SHA，不能据此计算文件 SHA-256 或解析 FIT/SPL。

因此，当前没有可直接进行 SHA-256 比较的 E23 原始二进制样本。之前报告中“后续与 E23 原始文件做哈希比较”的工作项需要依赖取得 E23 官方 loader 或构建产物后才能执行，不能用 Rock 3A 文件替代。

### 10.3 当前证据链判定

| 证据项 | 判定 |
|---|---|
| 原始适配者明确说明借用 Radxa E23 U-Boot | 已确认（Issue 评论） |
| 原始 Panther X2 分支头提交主要修改 Linux DTS，未见 U-Boot 补丁 | 已确认（该提交 diff） |
| Armbian Rockchip 家族默认 U-Boot 分支为 v2022.04 | 已确认（家族配置）；非 Panther 专用构建证明 |
| 当前 Ophub U-Boot 仓库包含 Panther X2 命名的启动文件 | 已确认 |
| 当前 Panther X2 二进制是否与 E23 原版完全相同 | 未知 |
| 当前 Panther X2 二进制的实际编译配置、源码 commit、DDR 参数 | 未知 |
| E23 原版 loader 的哈希和可解析内容 | 缺少原始样本，待取得 |

**结论：** “历史上借用 E23”是可靠历史证据，但不能据此断言当前 Ophub Panther X2 二进制仍与 E23 二进制逐字节相同。当前启动固件来源链仍未闭合。

### 10.4 下一步的最短路径

1. 取得 Radxa E23 官方 BSP 对应 U-Boot 源码版本、defconfig、板级 DTS 和 Rockchip DDR loader 文件；重点确认 RK3566 与 E23 板级参数。
2. 取得官方 E23 可下载镜像或 loader 文件，在 CI 中只读提取并记录 SHA-256、大小和版本信息。
3. 对当前 Panther X2 两个 blob 做可复现下载，计算 SHA-256，并使用 `dumpimage` / `mkimage` / Rockchip 专用工具分析容器结构；如果 connector 无法提供二进制下载，则由项目 CI 从公开仓库下载，不触碰实机。
4. 追踪 Ophub U-Boot 仓库 Panther X2 文件的首次加入来源和变更历史。GitHub commit 搜索未返回 Panther/E23 关键词匹配，因此该历史仍需通过仓库 Git 路径历史或 clone 后 `git log --follow` 补齐。

所有这些工作仍属于只读源码与构建产物审计，不涉及写卡或实机修改。

## 11. 以公开实机启动记录和用户旧 6.1.116 系统反向核对（2026-11-15）

本节优先使用实际成功运行记录，不再只从文件名推断 U-Boot。

### 11.1 公开的 Panther X2 实机启动记录

Ophub Issue #1319 的早期适配过程给出了以下直接证据：

- 2023-04-24，适配者 tdleiyao 表示 Panther X2 Armbian 已适配完成，并提供镜像。
- 2023-04-25，适配者明确说明：U-Boot 暂时借用 Radxa E23；其 Linux DTS 是基于 Armbian 主线并参照 Radxa E25 修改，适配者当时主要完成设备树适配，U-Boot 源码未公开。
- Ophub 在同一讨论中说明其按 Panther X2 使用的串口参数配置启动脚本。
- Ophub Contributors #90 记录：2023-04-25 经测试反馈，Panther-X2（RK3566）可安装到 eMMC，使用 rk3566-panther-x2.dtb，千兆有线网络正常。

来源：
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319#issuecomment-1521843631 （U-Boot 借用 Radxa E23）
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319#issuecomment-1521443259 （Armbian 主线、参考 Radxa E25 的 DTS 说明）
- https://github.com/ophub/amlogic-s9xxx-armbian/commit/d6a1a360b66925cf4b73e8727952f7f287144c92 （Panther X2 初始支持）
- https://github.com/ophub/amlogic-s9xxx-armbian/commit/e70c212d62d863f358160a218deee6d0b1ee4ab7 （Panther X2 启动配置文件）
- https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/CONTRIBUTORS.md （第 90 条实机测试记录）

这条证据链将两块板级参考明确区分：
- U-Boot：借用 Radxa E23。
- Panther X2 Linux DTS：参照 Radxa E25 修改。
不能把 E25 DTS 参考误写成 E25 U-Boot 已被实际采用。

### 11.2 当时 Panther X2 的 U-Boot 文件布局

初始支持提交 d6a1a360... 的设备数据库新增 Panther X2 条目，明确配置：

- TRUST_IMG=NA
- MAINLINE_UBOOT=u-boot.itb
- BOOTLOADER_IMG=idbloader.img
- KERNEL_TAGS=6.1.y
- PLATFORM=rockchip
- FAMILY=rk3566
- BOOT_CONF=armbianEnv.txt

因此，2023 年公开成功启动的 Panther X2 路线不是 u-boot.img + trust.bin + idbloader.bin 组合，而是 idbloader.img + u-boot.itb，且设备数据库不要求单独 TRUST_IMG。

这与当前用户旧系统 /etc/ophub-release 中的路径字段完全吻合：

- MAINLINE_UBOOT=/usr/lib/u-boot/u-boot.itb
- BOOTLOADER_IMG=/usr/lib/u-boot/idbloader.img
- BOOT_CONF=armbianEnv.txt
- FDTFILE=rk3566-panther-x2.dtb
- KERNEL_REPO=ophub/kernel
- KERNEL_TAGS=6.1.y
- KERNEL_VERSION=6.1.116

### 11.3 用户旧 6.1.116 系统的交叉核对

用户此前提供的旧系统信息显示：

- 实际运行内核：6.1.116-ophub
- 内核来源：ophub/kernel
- 内核分支：6.1.y
- Panther X2 DTB：rk3566-panther-x2.dtb
- U-Boot 文件路径：/usr/lib/u-boot/u-boot.itb 与 /usr/lib/u-boot/idbloader.img
- /boot 与根文件系统实际位于 eMMC：/dev/mmcblk1p1、/dev/mmcblk1p2
- /etc/ophub-release 同时记录 DISK_TYPE=usb；该字段与实际根/boot 挂载设备不是同一层面的证据，不能据此推断实际启动介质。

另有一份备份系统记录为 KERNEL_VERSION=6.1.192，并有相同的 U-Boot 文件路径及 PACKAGED_DATE=2023-12-07。这份记录应与当前运行的 6.1.116 分开看待，不能把备份版本号混写为 6.1.116。

**当前最强结论：** 用户曾正常运行的 6.1.116 系统采用的 U-Boot 文件布局，与 2023 年公开实机启动成功的 Panther X2 适配方案完全一致；而公开适配者明确说该方案的 U-Boot 借用 Radxa E23。故旧 6.1.116 系统极有可能沿用了这条 E23-derived idbloader.img + u-boot.itb 启动链。

**尚不能声称已证明的部分：**
- 旧系统 /usr/lib/u-boot/ 两个文件的实际 SHA-256、文件大小和内部版本字符串尚未取得。
- 尚未证明旧系统文件与当前 Ophub U-Boot 仓库 Panther X2 blob 是逐字节相同。
- /usr/lib/u-boot/ 中的文件路径是软件包/安装器元数据；仅凭路径不能证明 eMMC raw sectors 中实际写入的 loader 字节与文件完全一致。
- 旧系统根/boot 在 eMMC 是 Linux 运行态证据，不单独证明 BootROM 最初从 eMMC 还是 TF 卡/SPI 读取 ID Block。

### 11.4 对 6.12.81 最小系统的决策建议

目前没有理由先换掉这条经过 Panther X2 实机成功记录的启动方案。优先路线应为：

1. 以旧 6.1.116 环境和 2023 成功适配为参考基线，继续采用 idbloader.img + u-boot.itb 文件组合。
2. 暂时保留当前 Ophub Panther X2 启动文件作为候选，不主动重编 U-Boot。
3. 通过旧系统备份或只读读取旧系统文件，取得两个 U-Boot 文件的 SHA-256、大小和版本字符串。
4. 对比当前 Ophub Panther X2 文件的 SHA-256；相同则建立强关联，不同则继续追踪替换提交和来源。
5. 只有发现旧系统实际文件与当前候选不一致，或有明确硬件/启动问题证据，才评估重建 U-Boot。

以上仍不授权写 TF 卡、eMMC 或修改 192.168.x.6。

## 12. A2 第一轮：GMAC1 网络与 USB 主机依赖（2026-11-15）

本节依据固定 Linux 源码 commit `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`、Panther X2 DTS、其 include 的 `rk3566.dtsi` / `rk356x.dtsi`，以及 Ophub RK35xx `config-6.12` 静态核对。尚未编译合并后的 DTB，也未实机验证。

### 12.1 GMAC1 / RGMII / RTL8211F

Panther X2 DTS 对 `&gmac1` 的显式配置：

- `status = "okay"`，使用 RK3566 的 GMAC1。
- `phy-mode = "rgmii"`。
- 外部固定时钟 `gmac1_clkin` 为 125 MHz，并指定为 GMAC1 时钟父项。
- PHY 供电引用 `vcc_3v3`。
- PHY reset 使用 GPIO3 PA1，低有效，延时参数为 0 / 20,000 / 100,000 微秒。
- RGMII 延时参数：TX `0x30`、RX `0x10`。
- PHY 通过 `phy-handle = <&rgmii_phy1>` 连接 MDIO1，PHY 地址为 0。
- PHY 节点使用通用 Clause 22 compatible：`ethernet-phy-ieee802.3-c22`，而不是在 DTS 中硬编码 RTL8211F 名称；实际芯片型号由 PHY ID 匹配。

固定 Ophub RK35xx `config-6.12` 中相关选项：

- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_PLATFORM=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_PHYLIB=y`
- `CONFIG_REALTEK_PHY=y`
- `CONFIG_MDIO_BUS=y`
- `CONFIG_OF_MDIO=y`

**静态判定：** GMAC1、Rockchip DWMAC、MDIO/PHYLIB 和 Realtek PHY 驱动均有内建配置；DTS 的 RGMII、时钟、供电、reset、MDIO/PHY 连接关系已能对应到源码节点。

**待验证：** 实际 RTL8211F PHY ID 与驱动匹配、PHY reset 波形和时序、RGMII 时序裕量、链路协商、DHCP、持续传输及重启恢复。配置为 `=y` 不等于网口已在 Panther X2 实机工作。

### 12.2 USB 主机路径：发现设备树引用不一致风险

Panther X2 DTS 当前显式启用：

- `&usb_host0_ehci`
- `&usb_host0_ohci`
- `&usb2phy0`
- `&u2phy0_host`

但固定源码的基础 `rk356x.dtsi` 中：

- `usb_host0_ehci` 和 `usb_host0_ohci` 的 `phys` 引用为 `<&u2phy1_otg>`，其 clocks 也引用 `&usb2phy1`。
- `usb2phy1` 与其 `u2phy1_otg` 子节点在基础 DTSI 中默认 disabled。
- Panther X2 DTS 启用的是 `usb2phy0` / `u2phy0_host`，并没有显式启用 `usb2phy1` / `u2phy1_otg`。
- 因此当前板级 DTS 对 EHCI/OHCI host0 的启用，与基础 DTSI 中这两个控制器的 PHY 引用看起来不匹配，可能导致控制器 probe 时无法取得 PHY。

另外两条 DWC3 路径：

- `usbdrd30`（USB3 OTG/DRD）基础节点默认 disabled。Panther X2 / RK3566 DTSI 虽然给内部 `usbdrd_dwc3` 设置了 `u2phy0_otg`、`maximum-speed = "high-speed"`，但没有将 `usbdrd30` 父节点置为 okay；板级 DTS 也没有启用该父节点。
- `usbhost30`（USB3 Host）基础节点默认 disabled，板级 DTS 没有启用它。
- 所以不能把 RK3566 芯片具有 USB3 能力，或 config 中存在 DWC3 驱动，等同于当前 Panther X2 DTB 已启用 USB3 主机。

固定 `config-6.12` 中 EHCI/OHCI platform、DWC3、Rockchip USB2/USB3 PHY 驱动均有内建配置，例如：

- `CONFIG_USB_EHCI_HCD=y`
- `CONFIG_USB_EHCI_HCD_PLATFORM=y`
- `CONFIG_USB_OHCI_HCD=y`
- `CONFIG_USB_OHCI_HCD_PLATFORM=y`
- `CONFIG_USB_DWC3=y`
- `CONFIG_USB_PHY=y`
- `CONFIG_PHY_ROCKCHIP_INNO_USB2=y`
- `CONFIG_PHY_ROCKCHIP_INNO_USB3=y`

**当前判定：存在风险，需在构建前解决或明确解释。** 这不是单纯缺少内核驱动的问题，而是 DTS 节点状态与 PHY phandle 引用之间的潜在不一致。下一步必须对固定源码实际编译合并 DTB，并用 `dtc` / `fdtdump` 检查最终的 `status`、`phys`、`clocks` 和 PHY provider；同时对照 Panther X2 原始适配历史和实际板上 USB 端口布线。未经该步骤，不把 USB2 host 标记为已确认可用，也不把 USB3 标记为已启用。

### 12.3 串口与基础网络启动线索

- Panther X2 DTS 的 `chosen.stdout-path` 指向 `serial2:1500000n8`。
- 固定 config 中 `CONFIG_SERIAL_8250=y`、`CONFIG_SERIAL_8250_CONSOLE=y`、`CONFIG_SERIAL_OF_PLATFORM=y`、`CONFIG_SERIAL_8250_DW=y`，有串口控制台内建配置证据。
- `CONFIG_IP_PNP=y` 与 `CONFIG_IP_PNP_DHCP=y` 已启用，但这只表示内核 IP autoconfiguration 能力；不等于用户态 DHCP 客户端或 SSH 服务已安装、启用。

### 12.4 A2 下一步

1. 在 CI 对固定 6.12.81 源码实际编译 `rk3566-panther-x2.dtb`，保存 DTB 并审查合并后的 USB 控制器/PHY 关系。
2. 对照原始 Panther X2 USB 修复历史，追踪 `usb_host0`、`usb2phy0/1` 的节点选择是否有后续修订；不要凭 SoC 芯片框图猜端口映射。
3. 检查 6.12.81 发布包中的最终 `.config`、模块清单和 firmware 依赖，而不是只依赖配置仓库模板。
4. 审计最小 rootfs 是否具备 DHCP 客户端、SSH server、systemd/udev、网络命名与网卡初始化；此项目前未完成。

本节仅为源码/config 静态审计。没有构建镜像、写卡、安装软件或修改 Panther X2 实机。

## 13. 脱敏归档：用户历史 Panther X2 6.1.116 备份基线（2026-11-15）

本节记录从用户保留的历史备份中读取到、可供后续内核和启动链审计复用的信息。只记录与系统/内核相关的非敏感元数据及归档校验值；不上传原始归档、应用数据、Docker 配置、数据库、账号凭据、家庭网络地址、设备序列号或个人目录信息。

### 13.1 历史系统基线

| 项目 | 已知记录 |
|---|---|
| 设备 | Panther X2 / RK3566 |
| 发行版 | Armbian 24.8.4 |
| 用户空间基线 | Ubuntu 22.04.5 LTS |
| 架构 | aarch64 |
| 实际运行内核 | 6.1.116-ophub |
| 内核仓库 | ophub/kernel |
| 内核源码分支记录 | 6.1.y |
| DTB | rk3566-panther-x2.dtb |
| U-Boot 主镜像路径 | /usr/lib/u-boot/u-boot.itb |
| Bootloader 路径 | /usr/lib/u-boot/idbloader.img |
| 启动环境文件 | armbianEnv.txt |
| 旧系统记录的下载/介质元数据 | DOWNLOAD_TYPE=tar、DISK_TYPE=usb |

注意：旧版 /etc/ophub-release 中的 KERNEL_TAGS 曾记录为 stable，而实际内核来源分支记录为 6.1.y；两者属于不同层级的元数据，不应混为一个字段。旧记录中的 PACKAGED_DATE=2023-12-07 也不等于本次备份文件的创建日期。

该旧系统曾正常运行，是 Panther X2 + Ophub 6.1 系列的历史实机基线。它不是 6.12.81 的实机验证，也不能证明当前候选二进制与旧系统完全相同。

### 13.2 备份归档清单与 SHA-256

备份目录中与内核相关的归档及其随附 sha256sums 记录如下。用户在 iMac 上执行 shasum -a 256 -c sha256sums，三项均返回 OK。

| 归档 | SHA-256 | 校验 |
|---|---|---|
| boot-6.1.116-ophub.tar.gz | 68e991e78c19ecaf96d766a058b9b1149a57efcef5a729fd971edf47808ed6d2 | OK |
| dtb-rockchip-6.1.116-ophub.tar.gz | 2c60c79d67fee948689fa3ac17cd834e33553f1c65f03bf852529372ae37d5e5 | OK |
| modules-6.1.116-ophub.tar.gz | d8056b6abe03cdee392e56e4d5cf20ccfd5d1f577d579fbf29923cfba6a1b529 | OK |

另有 boot-before-6.1.116.tar.gz，其中目录清单搜索仅发现 armbianEnv.txt 与本次相关；该归档没有出现在上述三项 SHA256 清单中，因此本节不为它声明已校验。

备份目录记录日期为 2025-06-27。此日期是备份文件记录的时间，不应与旧系统软件包元数据中的 PACKAGED_DATE 混淆。

### 13.3 归档内容检查结果

只读取归档目录，没有解压或修改原始备份：

- boot-6.1.116-ophub.tar.gz：未发现 idbloader.img、u-boot.itb、trust.bin 或包含 U-Boot 的目录路径。
- boot-before-6.1.116.tar.gz：未发现上述 U-Boot 文件；仅发现 armbianEnv.txt。
- dtb-rockchip-6.1.116-ophub.tar.gz：作为 DTB 归档保留，后续可用于与 6.12.81 Panther X2 DTB 做静态差异比较。
- modules-6.1.116-ophub.tar.gz：作为旧内核模块基线保留，可用于驱动模块清单比较。
- 其他系统配置/应用归档中也未找到 idbloader.img、u-boot.itb 或 trust.bin。

因此，本次备份可供后续使用的内容是旧内核、DTB、模块及启动环境参考；没有收录旧系统实际使用的 U-Boot 二进制。不能从上述归档 SHA256 推导 U-Boot 文件的哈希。

### 13.4 对后续 6.12.81 审计的用途

1. 将 rk3566-panther-x2.dtb 作为旧版成功运行系统的设备树参考，比较 6.12.81 DTS 的节点状态、GPIO、时钟、PHY、USB、存储和 regulator 差异。
2. 从 DTB 归档提取旧版 DTB，在 CI 中用 dtc 反编译后做结构化比较；比较前记录原始归档 SHA256 和提取文件 SHA256。
3. 从 modules 归档生成模块清单，与 6.12.81 最终内核包比较驱动覆盖范围；注意旧版模块清单不能替代新版本 .config。
4. 从 boot 归档提取 armbianEnv.txt，作为旧版启动参数参考；任何设备节点编号仍需按新系统实际 MMC 枚举重新验证。
5. 继续沿用 Panther X2 历史成功方案的 idbloader.img + u-boot.itb 文件布局作为 6.12.81 候选启动链；不因本次备份未收录二进制就推断旧系统使用了不同方案。

### 13.5 证据边界

| 结论 | 证据级别 |
|---|---|
| 用户历史系统实际运行 6.1.116-ophub | 用户提供的旧系统记录 |
| 历史系统配置了 idbloader.img + u-boot.itb 路径 | 用户提供的 /etc/ophub-release |
| 三个内核相关归档的 SHA256 校验通过 | 用户在 iMac 上执行校验并提供结果 |
| boot 归档未包含两个 U-Boot 文件 | 对归档目录的只读列表检查 |
| 旧系统实际使用的 U-Boot 二进制内容/哈希 | 未取得，未知 |
| 旧版 DTB、模块与 6.12.81 的差异 | 待提取并比较 |
| 6.12.81 能否在 Panther X2 实机启动 | 未验证 |

本节只保存审计所需的非敏感索引和校验值。原始备份继续由用户本地保存，不进入 Git 仓库。
## 14. USB 实物接口约束与原始适配 DTS 交叉线索（2026-11-15）

### 14.1 实物接口信息（用户确认）

- Panther X2 机身外部可供使用的 USB 接口只有一个。
- 该外露接口目前尚未确认是 USB 2.0 还是 USB 3.x。
- 其他 USB 控制器/PHY 即使存在于 SoC 或 DTS 中，也不能默认属于外部可用接口；它们可能用于板载内部设备、其他板级连接，也可能在当前产品设计中未接线。
- 在确认原理图、板级布线或取得实机枚举证据之前，不推断具体控制器与该外露接口的对应关系。

### 14.2 原始 Panther X2 适配分支的 USB 配置变化

检查原始适配分支提交 `tdleiyao/armbian@99e8ca02b3472dcc5ad9daa7e7a87cdc22ce9a02`（标题：Panther X2: Modify usb mode and enable GPU）的 DTS diff，发现该提交相对其父提交对 USB 节点做过明确调整：

- 启用 `usb_host0_xhci`，并设置 `dr_mode = "host"`。
- 启用 `usb_host0_ohci`。
- 启用 `usb_host1_ehci`。
- 启用 `usb2phy0`、`usb2phy0_host` 和 `usb2phy0_otg`。

这比单纯看当前 6.12.81 DTS 更有价值：原始适配者曾针对 Panther X2 调整过 USB host/PHY 节点组合，说明 USB 节点状态和 PHY 选择需要结合该历史变更理解，不能把某个基础 DTSI 默认 phandle 不匹配直接视为板级设计错误。

但该提交 diff 只能证明原始适配分支曾采用上述 DTS 配置，不能证明单一外露 USB 口的物理布线、接口速率，也不能证明所有启用节点都对应外部端口。提交链接：https://github.com/tdleiyao/armbian/commit/99e8ca02b3472dcc5ad9daa7e7a87cdc22ce9a02

### 14.3 当前 USB 审计策略调整

后续按“最小必要硬件路径”审计，而不是追求所有 USB 节点都启用：

1. 以原始适配分支及其父提交为历史基线，逐项比较当前 6.12.81 DTS 的 `usb_host0_xhci`、`usb_host0_ehci`、`usb_host0_ohci`、`usb_host1_ehci`、`usbhost30`、`usbdrd30` 和 `usb2phy0/1` 节点状态及 phandle。
2. 通过编译合并 DTB 检查最终生效的节点状态、PHY、clock、reset 和 regulator 引用；不要仅看单个 DTS 文件中的局部片段。
3. 追踪每个候选控制器与 PHY 在 RK3566 SoC DTSI 中的连接关系，并结合原始适配变更确认其设计意图。
4. 对未连接外部接口、且无证据表明承担板载内部通信功能的控制器，不主动启用；但也不在缺乏板级证据时擅自禁用可能服务于内部设备的节点。
5. 外露 USB 接口的 USB 2.0/3.x 速率最终以板级原理图/PCB 走线或实机 USB 设备枚举协商结果确认。控制器名称、DTS 节点名称和 SoC 规格都不是单独的充分证据。

### 14.4 当前结论

| 项目 | 状态 |
|---|---|
| Panther X2 外露 USB 接口数量 | 用户确认：1 个 |
| 外露接口速率 | 未知，USB 2.0/3.x 待确认 |
| 原始适配 DTS 曾启用的 USB host/PHY 组合 | 已从指定提交 diff 确认 |
| 原始 DTS 节点与实际 PCB 端口的一一对应 | 未知 |
| 6.12.81 合并 DTB 的最终 USB 拓扑 | 待编译核验 |
| 其他 USB 控制器是否承担内部设备通信 | 待查板级资料/设备树消费者关系 |

当前不修改 DTS，不操作实机。USB 仍是最小系统构建前必须完成的静态依赖核查项，但审计目标限定为确认唯一外露接口所需的最小路径，并避免误关内部设备依赖。
## 15. 6.12.81 USB host0 PHY 引用复核（2026-11-15）

固定源码 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的板级 DTS 与 SoC 基础 DTSI 交叉检查，发现一项明确的静态引用不一致：

- `arch/arm64/boot/dts/rockchip/rk356x.dtsi` 中 `usb_host0_ehci`（`fd800000`）引用 clock `<&usb2phy1>`，PHY `<&u2phy1_otg>`。
- 同一文件中 `usb_host0_ohci`（`fd840000`）也引用 clock `<&usb2phy1>`，PHY `<&u2phy1_otg>`。
- Panther X2 板级 DTS 将 `usb_host0_ehci`、`usb_host0_ohci` 设为 `status = "okay"`。
- Panther X2 板级 DTS 启用的是 `usb2phy0` 和 `u2phy0_host`，未见启用 `usb2phy1` / `u2phy1_otg`。

这不是仅凭节点命名作出的推断，而是当前固定源码中控制器节点的 phandle 引用与板级启用节点直接对照所得。它构成潜在的 probe/PHY 依赖风险；尚不能仅据此断言实际启动一定失败，因为最终结果还取决于合并 DTB、PHY provider 节点状态、驱动对缺失/未启用 provider 的处理，以及板级 DTS 其他覆盖。

### 15.1 对照原始适配历史

原始 Panther X2 适配提交 `tdleiyao/armbian@99e8ca02b3472dcc5ad9daa7e7a87cdc22ce9a02` 曾启用 `usb_host0_xhci`、`usb_host0_ohci`、`usb_host1_ehci`，并启用 `usb2phy0`、`usb2phy0_host`、`usb2phy0_otg`。这说明早期板级适配有针对 USB PHY/host 拓扑作过调整；但不能证明该历史配置与当前 Ophub 6.12.81 的基础 DTSI 节点组合天然兼容。

### 15.2 当前风险判断与处理原则

- `usb_host0_ehci` / `usb_host0_ohci` 的 inherited PHY reference 与板级启用的 PHY0 host port 不一致：**静态证据已确认，实际影响待验证**。
- 不应因为外露 USB 只有一个，就把 EHCI、OHCI、XHCI 简单视为三个独立外部接口；EHCI/OHCI 通常是同一 USB2 host 控制器的高速/全速低速 companion 控制器，可能共同服务一个物理 root hub/端口拓扑。
- 不应在没有合并 DTB 证据前修改板级 DTS，也不应直接禁用 EHCI/OHCI 中任一个。
- 下一步必须编译固定 commit 的 `rk3566-panther-x2.dtb`，反编译并核对最终节点状态与 phandle；同时查看 `usb2phy0/1` provider 及其 host/otg 子节点状态。
- 随后将 6.1.116 备份中的旧 DTB 与新 DTB 作结构化比较。旧 DTB 当前仅保存在用户本地备份中，尚未进入仓库或 CI 工作区；旧 DTB 的内容比较不能用旧系统元数据代替。
- 最终确认外露接口速率仍需板级原理图/PCB 信息或实机 USB 设备协商结果。DTS 中 USB3 节点未启用只能说明当前设备树没有明确启用对应 USB3 host/OTG 控制器，不能单独证明 PCB 没有 USB3 走线。

### 15.3 证据状态

| 项目 | 状态 |
|---|---|
| 当前 6.12.81 host0 EHCI/OHCI PHY phandle | 源码已确认：usb2phy1 / u2phy1_otg |
| 当前 Panther X2 板级启用的 USB2 PHY host 端 | 源码已确认：usb2phy0 / u2phy0_host |
| 两组引用是否导致 probe 失败 | 未验证 |
| 编译后最终 DTB 中的 phandle/status | 待编译核验 |
| 6.1.116 旧 DTB 对应关系 | 待从本地备份归档提取后比较 |
| 唯一外露 USB 口实际速率 | 未知 |
### 15.4 合并 DTB 构建审计工作流

已新增 GitHub Actions 工作流 `.github/workflows/audit-panther-usb-dtb.yml`，固定检出 Ophub 6.12.81 源码 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，执行内核标准 `dtbs` 构建目标，提取 `rk3566-panther-x2.dtb`，计算 SHA-256，并用 `dtc` 反编译保存合并后的 DTS 与 USB 节点摘录。

工作流仅在 GitHub Actions runner 上构建和检查，不接触 Panther X2 实机，也不修改源码或设备配置。运行成功后应重点审阅 artifact 中的 `usb-topology-excerpts.txt`、`rk3566-panther-x2.merged.dts` 和 `dtc-warnings.txt`。工作流文件提交后仍需由 Actions 实际运行，当前不能将构建成功标记为已验证。
## 16. 首版最小系统网络与 SSH 远程维护验收门槛（2026-11-15）

用户明确要求：初始版本必须先保证 Panther X2 有线网口正常工作、DHCP 可获得地址、SSH 可从局域网连接；不能完全依赖 UART 进行后续故障排查和修补。该要求成为首版系统的 P0 验收门槛，优先级高于 USB、NPU、Immich 和其他外设功能。

### 16.1 P0 启动与远程维护链

首版必须具备完整链路：

1. U-Boot 正确加载 Panther X2 DTB 和 Linux 内核。
2. GMAC1 驱动成功 probe。
3. MDIO 总线发现外部 PHY，PHY reset/时钟/RGMII 时序正常。
4. 网线连接后建立 Ethernet carrier，至少支持 1000BASE-T 全双工协商（若实物 PHY/磁性器件/网口规格确认支持千兆）。
5. 用户态网络管理组件启动，DHCP 客户端获取 IPv4 地址、默认路由和 DNS（具体网络管理方案以 rootfs 实际构建配置确定，不预先假定 NetworkManager 或 systemd-networkd）。
6. SSH server 随系统启动并监听 LAN 接口。
7. 从同一局域网另一台设备建立 SSH 会话，能够执行基础诊断命令。
8. 冷启动、软重启和网线断开/重接后，网络与 SSH 自动恢复。

UART 仍需保留为启动早期日志和救援接口，但不能作为唯一管理通道。

### 16.2 首版最低诊断能力

SSH 登录后至少应具备以下诊断工具/接口：

- ip：检查接口、carrier、地址、路由和邻居表。
- ethtool：检查 PHY 协商速率、双工和链路状态（若工具未安装，需明确替代方案）。
- dmesg / journalctl：检查内核驱动 probe、PHY、DHCP 和 SSH 启动日志。
- systemctl：检查网络管理器和 SSH 服务状态（前提是最终 rootfs 使用 systemd）。
- ping / getent 或等效工具：验证局域网网关、DNS 和基础连通性。
- lspci 不属于 RK3566 网络排查必需项；不为此额外引入依赖。

SSH 认证方式、初始用户创建、密钥注入和密码策略必须在镜像构建方案中明确；禁止使用无密码 root SSH 或默认公开凭据。

### 16.3 当前证据与待核查项

| 层级 | 当前证据 | 状态 |
|---|---|---|
| 板级 GMAC1 DTS | RGMII、125 MHz 外部时钟、reset GPIO、PHY handle、供电引用 | 源码已核查 |
| 内核 GMAC 驱动 | STMMAC、Rockchip DWMAC 配置模板为内建 | config 模板已核查；最终包待核 |
| PHY 驱动 | PHYLIB、Realtek PHY 配置模板为内建 | config 模板已核查；实际 PHY ID/最终包待核 |
| 最终内核配置 | 尚未从固定 6.12.81 发布包完整提取并核对 | 待核 |
| 内核模块/firmware | 尚未确认最终包中驱动是否内建或作为模块提供、firmware 是否缺失 | 待核 |
| rootfs 网络管理组件 | 尚未从实际 rootfs 构建定义确认 | 待核 |
| DHCP 客户端 | 用户态 DHCP 能力尚未确认 | 待核 |
| SSH server | 安装、启用、启动顺序和认证配置尚未确认 | 待核 |
| 实机链路/DHCP/SSH | 未执行 | 未验证 |

### 16.4 后续工作顺序（P0）

A. 固定 6.12.81 发布包核验
- 下载并校验 config/versions.env 固定的 Ophub RK35xx 6.12.81 发布包。
- 提取最终 boot/config、modules、firmware 归档清单。
- 核实 CONFIG_STMMAC_ETH、CONFIG_DWMAC_ROCKCHIP、CONFIG_PHYLIB、CONFIG_REALTEK_PHY、MDIO、网络核心、PHY 相关配置的最终值。
- 对驱动为模块的情况，确认对应 .ko 存在、依赖可解析、模块随 rootfs 安装；对内建驱动则记录 =y。
- 核实 Panther X2 实际 PHY ID 能否由最终 Realtek PHY 驱动匹配；当前 DTS 是通用 Clause 22 compatible，不能仅凭“可能是 RTL8211F”提前下结论。
- 检查所需 firmware 是否存在；没有 firmware 依赖时也明确记录。

B. rootfs 用户态网络与 SSH 核验
- 从固定 Armbian build commit 和 Panther X2 board config 追踪 rootfs 包选择、网络管理方案、DHCP 客户端、SSH server、默认服务启用方式。
- 明确实际使用 NetworkManager、systemd-networkd、ifupdown 或其他方案，不能同时假定多个组件负责同一接口。
- 核实服务 enable/start 顺序、DHCP 超时行为、网卡命名规则（当前历史配置包含 net.ifnames=0，需确认实际效果）、SSH host key 生成和用户认证策略。
- 检查最小系统是否包含 iproute2、日志工具及必要诊断命令。

C. 构建产物静态验收
- 形成一份明确的最小网络/SSH 软件包清单与配置，不把完整桌面/容器/Immich 带入首版。
- 构建首版 TF 测试镜像前，静态检查镜像内 rootfs 的网络配置、SSH 服务 enable 状态、用户和 host key 生成机制。
- 仅在 A/B 静态审计通过后，才计划 TF 卡实机测试。

D. 实机验收（未来阶段，当前未授权执行）
- 串口只用于记录 boot log；主要验收通过 LAN SSH 完成。
- 冷启动后 DHCP 获取地址并从另一台 LAN 主机 SSH 登录。
- 多次重启、链路重协商、拔插网线后重复验证。
- 从 SSH 检查 dmesg、ethtool、ip addr/route、网络服务日志。
- 验收失败时保留 UART 救援路径，但修复目标是恢复网络远程管理，不把“UART 可登录”当成首版通过。

当前阶段边界：本节只定义验收标准和审计工作；未安装软件、未修改 rootfs/内核配置、未构建或写入实机镜像，也未操作 Panther X2。

## 17. 首版网络与 SSH 用户态构建路径：第一轮源码审计（2026-11-15）

本节将网络/SSH 作为首版 P0，检查固定 Ophub Armbian 工作流与项目记录的 Armbian build 源码快照。证据分为“构建脚本明确传参”“固定源码默认行为”“最终 rootfs 尚待检查”，不可混为一谈。

### 17.1 Ophub Server 构建工作流选择

固定 Ophub Armbian commit `9e71b57f73683f9c4d14a30311e4c2ccbff29566` 的 `.github/workflows/build-armbian-arm64-server-image.yml` 中，Armbian 编译命令明确传入：

- `BUILD_MINIMAL=no`
- `BUILD_DESKTOP=no`
- `RELEASE` 由构建矩阵选择，项目目标基线为 Noble。
- Server workflow 在后续步骤再运行 Ophub 的 rootfs 整理脚本。

固定 Armbian build commit `3f3849bf50bfadff94d0d488eb968bdaf970dc72` 的 `lib/functions/configuration/main-config.sh` 规定：未显式设置 `NETWORKING_STACK` 时，`BUILD_MINIMAL=yes` 选择 `systemd-networkd`；否则选择 `network-manager`。该构建命令未传入 `NETWORKING_STACK`，所以按此源码快照的默认逻辑应选择 NetworkManager。

### 17.2 NetworkManager + Netplan DHCP 路径

固定 Armbian build 源码中：

- `extensions/network/net-network-manager.sh` 为 NetworkManager 扩展添加 `network-manager`、`network-manager-openvpn`、`netplan.io` 软件包。
- 扩展启用 `systemd-resolved.service`，部署 Netplan 配置，并禁用 `NetworkManager-wait-online.service`。
- `extensions/network/config-nm/netplan/00-default-use-network-manager.yaml` 设置 `renderer: NetworkManager`，其注释说明所有设备交给 NetworkManager 管理，检测到 carrier 后通过 DHCP 自动配置。

这条路径不要求额外假定一个独立的 isc-dhcp-client；DHCP 由 NetworkManager 管理。Panther X2 当前 boot 环境参数包含 `net.ifnames=0`，因此传统接口名通常为 `eth0`；Netplan 配置的通配匹配为 `e*`，静态上能够覆盖该命名。最终仍需在 rootfs 和实机验证接口名及 DHCP 行为。

### 17.3 Noble CLI 基础软件包证据

固定 Armbian build commit 的 `config/cli/noble/main/packages` 明确列出：

- `openssh-server`
- `iproute2`
- `iputils-ping`
- `rsyslog`
- `systemd-resolved`

因此在该 CLI rootfs 配置路径中，SSH server 和基本网络诊断工具有软件包清单证据。NetworkManager 及 Netplan 则由前述网络扩展额外加入。

**重要边界：** 软件包在配置清单中，不等于最终镜像已安装、服务已 enable、SSH 已监听或用户认证已配置。最终 rootfs 的 `ssh.service` enable 状态、host key 生成、首启用户创建、密码/公钥认证策略仍需从实际镜像检查。

### 17.4 构建来源可追溯性发现

虽然项目 `config/versions.env` 固定记录了 Armbian build commit `3f3849bf50bfadff94d0d488eb968bdaf970dc72`，但固定 Ophub Server workflow 的实际源码下载步骤使用 `git clone --single-branch --depth=1 --branch=main https://github.com/armbian/build.git`，没有 checkout 到上述固定 commit。

因此：
- 本节关于 NetworkManager 默认选择、Netplan DHCP 和 Noble CLI 包清单的结论，是对项目固定 Armbian 源码快照的静态审计结果。
- Ophub workflow 在实际运行时使用的 Armbian build 源码版本可能随 main 分支变化。
- 不能声称历史 workflow 运行时必然使用了 `3f3849bf...` 的实现。
- 后续自建/修订的可追溯构建流程必须显式 checkout `ARMBIAN_BUILD_COMMIT`，并在构建日志记录实际 HEAD；不能只在 versions.env 记录一个未被 workflow 消费的 commit。

### 17.5 当前阶段判定

| 项目 | 当前结论 |
|---|---|
| Ophub Server workflow 的 BUILD_MINIMAL | 已从固定 workflow 源码确认：no |
| 固定 Armbian build 源码默认网络栈 | 已确认：非 minimal 时为 NetworkManager |
| NetworkManager + Netplan DHCP 配置 | 已确认：carrier 后 DHCP |
| Noble CLI 软件包清单包含 openssh-server | 已确认 |
| Noble CLI 软件包清单包含 iproute2 / iputils-ping / rsyslog | 已确认 |
| 固定 Ophub workflow 实际使用的 Armbian build commit | 未固定，workflow clone main |
| 6.12.81 最终内核包的 GMAC/PHY 配置与模块 | 待专用 CI 提取 |
| 最终 rootfs 中 NetworkManager、Netplan、openssh-server 是否存在 | 待镜像构建产物核查 |
| ssh.service 是否 enabled、host keys 和首启账户策略 | 待最终 rootfs 核查 |
| DHCP、链路、SSH 实机验收 | 未验证 |

### 17.6 下一步

1. 运行 `.github/workflows/audit-panther-network-ssh.yml`，核对 Ophub 6.12.81 发布包最终内核 config 和 modules，而不是仅看 config 模板。
2. 在构建器中固定 Armbian build commit；明确首版采用 NetworkManager + Netplan，避免构建来源变化造成网络栈漂移。
3. 对首版候选 rootfs 做只读静态检查：NetworkManager/Netplan 配置、ssh.service enable 状态、SSH host key 生成、初始用户和认证策略。
4. 只有静态检查通过后才进入 TF 卡实机启动；以局域网 SSH 作为主要验收通道，UART 作为辅助救援。

当前没有构建或写入实机镜像，没有安装软件，也没有修改 Panther X2 实机。

### 15.5 合并 DTB 实际结果（GitHub Actions run 43668003702，2026-11-15）

本次工作流已在固定 Ophub commit 上成功编译 `rk3566-panther-x2.dtb`，并成功上传 artifact。构建成功只证明 DTB 编译通过，不代表 USB 控制器在实机可用。

- DTB SHA-256：`00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185`
- Artifact：`panther-x2-6.12.81-merged-usb-dtb-audit`
- Artifact SHA-256：`e4e0b42d90ae99f5f4be197f9b7cedc099d0b3c84a12db11be8ac5636c6d2921`

对反编译后的最终合并 DTS 进行 phandle 反查，确认：

1. `/usb@fd800000`（EHCI）与 `/usb@fd840000`（OHCI）均为 `status = "okay"`。
2. 两个控制器的 `phys = <0x2d>`，反查为 `/usb2-phy@fe8b0000/otg-port`（即 PHY1 OTG 子节点）。
3. 对应 PHY1 provider `/usb2-phy@fe8b0000` 为 `status = "disabled"`，其 `otg-port` 也为 `status = "disabled"`。
4. 板级启用的 `/usb2-phy@fe8a0000`（PHY0）及其 `host-port` 均为 `status = "okay"`，但当前已启用的 EHCI/OHCI 并未引用这个 PHY0 host 子节点。
5. `/usbdrd`（USB DRD/DWC3）父节点为 disabled；`/usbhost`（USB3 host/DWC3）父节点也为 disabled。不能据此声称当前 DTS 已启用 USB3 host/OTG。

因此，先前提出的“host0 EHCI/OHCI 引用了未启用 PHY1 OTG，而板级启用 PHY0 host”的风险，已由最终合并 DTB **确认存在**，不再只是源码片段推测。该关系可能导致 PHY 获取失败、控制器 probe 失败或 USB host 无法正常工作；具体内核驱动行为和实机影响仍未验证。

### 15.6 USB 结论与后续动作

- **已验证（构建产物）：** 固定 commit 的 Panther X2 DTB 可编译；最终 phandle 关系如上。
- **已确认（静态配置问题）：** 已启用的 EHCI/OHCI 引用 disabled 的 PHY1 OTG；enabled 的 PHY0 host 没有被这两个 enabled 控制器引用。
- **未验证：** EHCI/OHCI 在该状态下实际 probe 结果；唯一外露 USB 插口的实际 PHY/控制器走线及 USB2/USB3 速率。
- **不做的事：** 不因外露接口只有一个就直接改写 phandle；不猜测应把控制器改指向 PHY0 host；不禁用 EHCI/OHCI 中任意一个；不在此阶段改 DTS 或刷机。
- **下一步：** 先追踪 Panther X2 原始板级 DTS 的 USB 节点变更历史，核实 PHY0/PHY1、EHCI/OHCI 与 DWC3 的设计意图；随后对照本地 6.1.116 旧系统 DTB。确定板级拓扑后再提出最小 DTS 修补候选，并通过 CI 重新编译和静态审查。实机 USB 测试留到网络/SSH P0 首版通过之后。

本次 dtc 反编译还报告若干既有结构类 warning（例如 duplicate unit-address、unnecessary address/size cells、graph child address）；这些 warning 不影响本次 DTB 编译成功，但应保留完整 warning 清单，后续按涉及节点逐项判断，不应一概视为 USB 故障。

### 16.5 合并 DTB 对 GMAC1 的补充核验（run 43668003702）

同一份成功编译的最终合并 DTB 也可用于核对 GMAC1 节点，得到以下构建产物证据：

- `/ethernet@fe010000` compatible 为 `rockchip,rk3568-gmac` / `snps,dwmac-4.20a`，`status = "okay"`。
- `phy-mode = "rgmii"`，`clock_in_out = "input"`，PHY 电源引用有效的 regulator phandle。
- reset GPIO 为 GPIO3 PA1，低有效，延时数组为 0 / 20,000 / 100,000 微秒。
- TX/RX delay 属性分别为 `0x30` / `0x10`。
- `phy-handle` 指向本节点 MDIO 子节点 `ethernet-phy@0`，地址为 0，状态为 okay。
- 外部固定时钟节点 `gmac1_clkin` 为 125 MHz，assigned-clock-parents 中可见该时钟引用。

这确认了最终 DTB 中 GMAC1 及其 MDIO PHY 节点均处于启用状态，DTS 的关键时钟、供电、reset、RGMII 和 PHY handle 引用已进入编译产物。它仍不证明 PHY 实际型号、PHY ID 驱动匹配、reset 电气波形、RGMII 时序裕量、网线 carrier、千兆协商或数据传输成功；这些必须继续通过最终内核配置/驱动包审计及未来实机测试验证。

特别注意：PHY 节点只声明通用 Clause 22 compatible，最终 DTB 没有硬编码 RTL8211F 等具体型号。后续不能在未读取 PHY ID 或板级 BOM 前把具体 Realtek 型号当成已确认事实。

### 17.7 网络/SSH 专项审计首次运行结果与脚本修正（run 43668579977）

首次运行在下载和完整性校验阶段成功：
- Ophub 6.12.81 RK35xx 发布包实际大小为 141,437,450 字节，与固定记录一致。
- 实际 SHA-256 为 `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`，与固定记录一致。
- 外层 gzip/tar 结构可正常读取，内层归档目录清单成功生成。

失败原因是审计脚本错误假定内层归档名称为 `boot-6.12.81-ophub.tar.gz` 和 `modules-6.12.81-ophub.tar.gz`；实际包内名称包含 RK35xx 标识：
- `boot-6.12.81-rk35xx-ophub.tar.gz`
- `modules-6.12.81-rk35xx-ophub.tar.gz`

这是审计脚本路径匹配错误，不是发布包损坏，也不是内核配置或驱动失败。由于脚本在定位 boot/modules 归档时退出，最终内核配置提取、模块清单分析、Armbian 网络/SSH 源码审计及 Ophub 构建来源核查均未执行。

已在 commit `853bf96841e7a53e5372c85eb305378e6e16538b` 修正归档文件名匹配，并收紧 config 文件名匹配规则。需要重新运行工作流；修复提交本身不代表审计已成功。下一次运行还应检查归档内是否存在 SHA256SUMS 并校验内层文件，避免仅依赖外层发布包摘要。

### 17.8 第二次网络/SSH 专项审计运行结果（run 43668971426）

第二次运行已成功完成：
- Ophub 6.12.81 外层包下载，大小与固定值一致（141,437,450 bytes）。
- 外层 SHA-256 与固定值一致（`72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`）。
- 外层 gzip/tar 完整性检查。
- 五个归档成员的索引生成。

失败发生在 boot 归档配置文件定位命令：`tar -tzf "$boot" | awk '... { print; exit }'`。由于工作流启用 `pipefail`，awk 找到目标后提前退出，tar 写入已关闭管道触发 SIGPIPE，导致步骤退出码 2。artifact 中的 boot 归档目录索引已证明配置文件确实存在：`config-6.12.81-rk35xx-ophub`。因此这仍是审计脚本管道处理错误，不是发布包或内核配置错误。

已在 commit `80522f8296e243fb3b77107127a3ac79664182da` 修正：先把完整 tar 成员清单写入文件，再从文件中筛选 config 路径，避免提前关闭 tar 输出管道。该提交尚未运行验证，下一步需重新触发工作流。

### 17.9 网络/SSH 专项审计成功结果（run 43669171821，2026-11-15）

第三次运行（workflow run #3）所有步骤成功，成功下载并校验固定 Ophub 6.12.81 RK35xx 内核包、提取最终 config、索引 modules 包，并审计固定 Armbian build 源码快照及固定 Ophub Server workflow。Artifact ID：`14143082992`，artifact ZIP SHA-256：`b2fc272881bef576b0e6961bfb2cea5a0cbb13f9c4eb9e614cb41a4c1f0ba3d0`。

#### 17.9.1 最终内核包网络配置

最终 `config-6.12.81-rk35xx-ophub` 确认：
- `CONFIG_NET=y`、`CONFIG_PACKET=y`、`CONFIG_UNIX=y`、`CONFIG_INET=y`
- `CONFIG_NETDEVICES=y`、`CONFIG_ETHERNET=y`
- `CONFIG_STMMAC_ETH=y`、`CONFIG_STMMAC_PLATFORM=y`、`CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_PHYLINK=y`、`CONFIG_PHYLIB=y`、`CONFIG_REALTEK_PHY=y`
- `CONFIG_MDIO_BUS=y`、`CONFIG_OF_MDIO=y`
- `CONFIG_MODULES=y`、`CONFIG_IPV6=m`

结论：GMAC1 依赖的 STMMAC、Rockchip DWMAC、PHYLIB、Realtek PHY、MDIO 和 PHYLINK 主链均为内建（`=y`），不依赖启动后加载对应 .ko。最终 modules 包中未发现 stmmac/dwmac/Realtek PHY 主链模块，与内建配置吻合。modules 包中的其他平台网卡和无线模块不应误认为 Panther X2 GMAC1 的依赖。

IPv6 为模块（`=m`），但首版远程维护 P0 以 IPv4 DHCP + SSH 为验收目标，IPv6 不是此目标的前置依赖。

#### 17.9.2 Armbian rootfs 网络与 SSH 软件包路径

固定 Armbian build commit `3f3849bf50bfadff94d0d488eb968bdaf970dc72` 的源码核查确认：
- Noble CLI 基础软件包清单列出 `openssh-server`、`iproute2`、`iputils-ping`、`rsyslog`、`systemd-resolved`。
- Ophub Server workflow 传入 `BUILD_MINIMAL=no`、`BUILD_DESKTOP=no`。
- 该 Armbian commit 在未设置 `NETWORKING_STACK` 时，非 minimal 默认选择 `network-manager`。
- NetworkManager 扩展加入 `network-manager`、`network-manager-openvpn`、`netplan.io`，启用 `systemd-resolved.service`，部署 Netplan 和 NetworkManager 配置。
- Netplan 默认 renderer 为 NetworkManager，配置注释说明所有设备由 NetworkManager 管理，检测到 carrier 后通过 DHCP 自动配置。

这证明固定 Armbian 源码快照具备合理的有线 DHCP 和 SSH 软件包构建路径，但不证明实际 rootfs 已包含并启用这些组件。

#### 17.9.3 构建来源偏差

固定 Ophub workflow 实际执行 `git clone -q --single-branch --depth=1 --branch=main https://github.com/armbian/build.git build`，没有 checkout 项目 `config/versions.env` 中记录的 `ARMBIAN_BUILD_COMMIT=3f3849bf50bfadff94d0d488eb968bdaf970dc72`。因此本次 Armbian 源码审计是固定 commit 的可重复静态分析，但不能证明 Ophub workflow 当时实际构建 rootfs 使用了该 commit。后续构建流程必须消除此偏差。

#### 17.9.4 SSH 尚未完成静态验收

本次只证明 Noble CLI 软件包清单包含 `openssh-server`，尚未检查最终 rootfs 是否实际安装该包、`ssh.service/sshd.service` 是否 enabled、host keys 是否生成、首启用户是否创建及其密码/公钥策略、PermitRootLogin/PasswordAuthentication、防火墙 TCP/22 规则，以及首启流程是否会阻塞网络管理。不能把软件包清单当作“SSH 已可登录”。

#### 17.9.5 当前阶段结论

| 检查项 | 状态 |
|---|---|
| Ophub 6.12.81 最终内核包完整性 | 已验证（大小、SHA-256、gzip/tar） |
| 最终内核 GMAC / DWMAC / PHY / MDIO 配置 | 已验证，关键项均为内建 |
| 最终 modules 包 | 已索引；未见 GMAC 主链模块，与内建配置吻合 |
| 固定 Armbian 源码的 NetworkManager + Netplan DHCP 路径 | 已验证（源码级） |
| 固定 Armbian Noble CLI SSH 软件包清单 | 已验证（源码级） |
| Ophub workflow 实际 Armbian build commit | 未固定 main 分支，存在来源偏差 |
| 最终 rootfs 中网络包和配置 | 未验证 |
| SSH enable、host key、初始用户与认证 | 未验证 |
| LAN IPv4 DHCP、TCP/22 SSH 登录 | 未验证，需未来实机验收 |

下一步不应重复内核 config 检查，而应审计 Ophub rootfs 生成流程：实际 Armbian checkout 版本、CLI 包安装、首启用户创建、SSH enable/host key 和防火墙配置。只有拿到最终 rootfs 后，才能做文件级静态检查。未经授权，不在 Panther X2 实机安装或修改任何内容。


## 17.10 SSH 首次登录与 Host Key 生命周期审计（run 43670178481，2026-11-15）

第四次网络/SSH 专项审计成功完成。Run：`43670178481`；Job：`132678274475`；审计代码 commit：`67da4fb164f335275c421c3052f61bc77b6dd5d1`。Artifact ID：`14143727667`；ZIP SHA-256：`248b493f0446ed8e987e23188ec6e179a1d8e1c84e1da28266d2d6f9a24880df`。

本次下载并逐项检查了 artifact 中的固定源码文件，不只依赖 Actions 日志。

### 17.10.1 Ophub SSH 配置

固定 Ophub commit `9e71b57f73683f9c4d14a30311e4c2ccbff29566` 的 Server workflow：
- Armbian 编译参数为 `BUILD_MINIMAL=no`、`BUILD_DESKTOP=no`。
- 清理/打包阶段调用 `build_armbian_rootfs_file.sh -v <release> -s true -c true -k true -p arm64`。
- 固定脚本 `compile-kernel/tools/script/docker/build_armbian_rootfs_file.sh` 在 `-s true` 时，将 sshd 配置设为 Port 22、`PermitRootLogin yes`、`PasswordAuthentication yes`。
- 同一脚本将 root 密码写为 `1234`（SHA-512 crypt）。

这确认 Ophub 构建意图允许首次 root 密码 SSH 登录。它不等于已验证最终镜像的 sshd 服务启用状态或实机可连接性。

### 17.10.2 Armbian 首次登录可通过交互式 SSH 承载

固定 Armbian commit `3f3849bf50bfadff94d0d488eb968bdaf970dc72`：
- rootfs 构建逻辑创建 `/root/.not_logged_in_yet` 标记。
- `/etc/profile.d/armbian-check-first-login.sh` 在 root 登录 shell 检测该标记并调用 `/usr/lib/armbian/armbian-firstlogin`。
- 首次登录脚本入口要求 `tty -s`，因此必须是分配 PTY 的交互式 SSH；无 PTY 的 `ssh host command` 不会运行该交互流程。
- 脚本明确把非空 `SSH_CONNECTION` 视为已经有用户接入，不会等待本地控制台按 Enter。
- Ophub 的 rootfs 修改没有设置 Armbian 的 `PRESET_ROOT_PASSWORD` 或 `PRESET_USER_NAME` 标记。因此首次交互式 SSH 登录会要求重新设置 root 密码（输入两次），随后创建普通用户，并继续 shell、时区和 locale 等首次初始化。
- 首次初始化成功后才删除 `.not_logged_in_yet` 标记；中途失败会保留标记，以便下次登录重试。

**结论（源码级）：** 首次登录流程具备通过 iMac 交互式 SSH + PTY 完成的代码路径，不要求 UART/显示器。Ophub 的 `1234` 是初始登录凭据，初始化流程仍会要求设置 root 最终密码。用户创建是首次初始化流程的一部分。

### 17.10.3 Host Key 首启流程与时序

固定 Armbian rootfs 构建逻辑会在 `armbian-firstrun.service` 存在时 enable 该服务。该 unit：
- `After=ssh.service`
- `Before=getty.target`
- `WantedBy=multi-user.target`
- `Type=simple`、`RemainAfterExit=yes`
- 执行 `/usr/lib/armbian/armbian-firstrun start`

默认配置 `OPENSSHD_REGENERATE_HOST_KEYS=true`。firstrun 脚本会删除旧的 `/etc/ssh/ssh_host_*`，调用 `dpkg-reconfigure openssh-server` 生成新 Host Keys，再执行 `service ssh restart`。

**时序注意：** 该服务明确排在 `ssh.service` 之后，且会重新启动 SSH。故不能假定第一次开机时 SSH daemon 从启动到完成 Host Key 重建期间完全没有变化。未来实机验收需观察首次连接是否遇到服务重启，以及 Host Key 稳定后第二次连接是否正常。当前未证明该时序必然导致连接失败。

### 17.10.4 网络与 SSH 的剩余验证边界

本次源码审计支持以下结论：
- 固定 Armbian Noble CLI 软件包列表包含 `openssh-server`、`iproute2`、`iputils-ping`。
- 固定源码默认 NetworkManager + Netplan 路径适用于 `BUILD_MINIMAL=no`，Netplan 配置声明检测到 carrier 后由 NetworkManager 使用 DHCP。
- Ophub `-s true` 配置 SSH root/password 登录。
- Armbian 首次初始化能通过交互式 SSH PTY 运行。

仍未验证：
- Ophub 那次实际构建使用的 Armbian commit；workflow clone `main`，并未固定到本项目审计的 `3f3849b...`。
- 最终 rootfs 是否实际安装 `openssh-server`、`network-manager`、`netplan.io`。
- 最终 rootfs 中 `ssh.service` 是否 enabled、sshd_config 最终生效内容、Host Keys 的实际生成状态。
- 最终镜像是否存在影响 TCP/22 的防火墙规则。
- 实机 DHCP 地址获取、SSH 首次登录、初始化完整完成、SSH 重连和重启后持久性。

| 检查项 | 当前判定 |
|---|---|
| Ophub SSH 配置意图及初始 root 密码 | 已确认（固定脚本源码） |
| Armbian first-login 交互式 SSH/PTY 路径 | 已确认（固定源码） |
| 首次初始化包含 root 密码重设和普通用户创建 | 已确认（固定源码） |
| Host Key 首启生成及 SSH restart 逻辑 | 已确认（固定源码） |
| 最终 rootfs 中 sshd/networking 包与服务状态 | 未验证 |
| DHCP + TCP/22 实机可达及完整首次初始化 | 未验证 |

### 17.10.5 审计脚本的小问题

本次 run 的首次登录报告生成步骤早于下载 Ophub Server workflow，因此报告中的 workflow grep 当时没有输入文件；命令使用 `|| true`，没有使工作流失败。后续 provenance 步骤成功下载了 workflow，且从该文件确认了 `-s true` 调用。结论已由 artifact 内的实际 workflow 文件复核，但报告编排应修正：先下载 Ophub workflow，再生成 first-login lifecycle 报告，避免报告缺少调用上下文。

下一步应继续审计最终 rootfs 构建/打包流程，特别是 Armbian checkout 固定、包实际安装、`ssh.service` enable、Host Key 与防火墙文件状态；不重复本次已完成的源码检查，不操作 192.168.x.6 实机。


## 17.11 第一版最小启动镜像构建工作流（2026-11-15）

已新增专用 GitHub Actions 工作流：

- 文件：`.github/workflows/build-panther-x2-minimal.yml`
- 工作流名称：Build Panther X2 minimal bootable image
- 当前构建目标：Armbian Noble CLI + Ophub RK35xx 6.12.81 + Panther X2 原始 DTS + 历史 Rockchip loader 组合。
- 运行方式：GitHub Actions → Build Panther X2 minimal bootable image → Run workflow。
- 输出 Artifact：`panther-x2-minimal-6.12.81-noble`（成功完成后才会生成）。

### 固定输入

| 组件 | 固定选择 |
|---|---|
| Ophub rebuild 脚本 | `9e71b57f73683f9c4d14a30311e4c2ccbff29566` |
| Armbian build 源码 | `3f3849bf50bfadff94d0d488eb968bdaf970dc72` |
| 基础板型 | Odroid N2（仅借用 Armbian 通用 ARM64 rootfs/构建路径，最终重建为 Panther X2） |
| 发行版 | Ubuntu Noble |
| Panther X2 内核标签 | `rk35xx/6.12.y`（在 CI 临时修改该设备数据库行，不改上游仓库文件） |
| 内核包 | Ophub RK35xx 6.12.81，外层 SHA-256 使用 config/versions.env 固定值 |
| U-Boot | Ophub/u-boot commit `6e70f41585f15c43f45fcae609adec1865e83eb5` |
| Firmware | Ophub/firmware commit `a9d0e8337cc8aa2ca4b482acd7b19c74ce05860f` |
| 根文件系统 | ext4，目标 root 分区 6144 MiB |
| 初始 SSH | TCP/22、root/password，Ophub 脚本初始密码 `1234` |
| 安装目标 | 独立 TF 卡；不安装到 eMMC |

### 构建方法

1. 固定 commit 下载 Ophub rebuild 工具、Armbian build 源码、U-Boot 和 firmware。
2. 从固定 Ophub RK35xx 6.12.81 release 下载内核包，核对外层 SHA-256、内部 `sha256sums`，并确认 boot、dtb-rockchip、modules、header 四类归档存在。
3. 将 Panther X2 设备数据库的 kernel selector 从默认 `stable/6.18.y` 临时切换到 `rk35xx/6.12.y`。
4. 使用 Armbian Noble + Odroid N2 构建通用基础 rootfs，再由固定 Ophub 工具重建为 Panther X2 镜像。
5. 关闭 Ophub rebuild 对 U-Boot/firmware moving branch 的自动下载，改用已预置的固定 commit；rootfs EDID 文件也从同一固定 firmware checkout 复制。
6. 禁用自动查询最新内核，指定具体版本 `6.12.81`，并使用已预置的该版本包（设备数据库仍以 `rk35xx/6.12.y` 表示系列）。
7. 最终镜像挂载检查：内核、initrd、Panther X2 DTB、rootfs modules、SSH 配置、NetworkManager、Netplan、first-login、firstrun、U-Boot 文件和分区内容。
8. 额外从镜像原始扇区读取数据，与固定 U-Boot checkout 的 `idbloader.img`（sector 64）和 `u-boot.itb`（sector 16384）逐字节比较，避免只验证文件名而未验证镜像实际写入内容。

### 重要边界

- 这是首版构建工作流，尚未运行成功；只有 Actions 成功、Artifact 生成并通过镜像内容检查后，才能称为“已生成可用镜像”。
- 最终静态镜像检查不能替代 Panther X2 实机启动、DHCP、SSH 首次登录和重启恢复验证。
- 基础 rootfs 使用 Armbian Odroid N2 构建目标，是沿用 Ophub 官方 Server workflow 的构建模式；最终镜像由 Ophub rebuild 脚本替换成 Panther X2 DTB、6.12.81 内核和 Rockchip loader。仍需在实机确认没有残留板型特定服务影响启动。
- Ophub 原始重建脚本有少量 CI 临时补丁，目的是阻止 U-Boot/firmware 从 moving branch 下载；不改动用户设备，也不修改仓库中的上游源码。
- 没有构建或写入 eMMC；没有操作 192.168.x.6 实机。


### 17.11.1 构建工作流收敛补充

后续对构建工作流增加了以下保护：
- 通过 `systemctl --root=<target-rootfs> enable` 显式启用 `ssh.service`、`NetworkManager.service` 和 `armbian-firstrun.service`，不只依赖基础镜像包的默认 enable 状态。
- 最终镜像检查要求 openssh-server、network-manager、netplan.io 均为 dpkg 已安装状态。
- 最终镜像检查要求 Netplan 配置明确使用 NetworkManager renderer，并包含 `dhcp4: true`。
- U-Boot 镜像写入后，从最终镜像 sector 64 / 16384 读取 loader 字节并与固定 U-Boot 源文件逐字节比较。
- 内核选择使用具体版本参数 `6.12.81`，而非系列字符串 `6.12.y`；设备数据库 selector 仍是 `rk35xx/6.12.y`。
- Ophub rebuild 和 rootfs helper 中会访问 moving branch 的 U-Boot/firmware 下载被本地 CI 补丁关闭，改用预置的固定 U-Boot/firmware commit；EDID 文件也从固定 firmware checkout 复制。
- 构建参数集中记录在 `config/versions.env`：基础板型 odroidn2、内核标签 rk35xx、root 分区 6144 MiB。

工作流当前仍未运行；Artifact 和实机状态均未产生新的验证结论。
