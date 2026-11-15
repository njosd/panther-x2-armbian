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
4. 完成上述静态闭包审计后，再进入镜像构建前检查；仍不刷机、不写卡、不修改 192.168.9.6。

本报告只记录静态证据和构建阻塞，不代表完整系统已在 Panther X2 实机运行。
