# Panther X2 最小 RAM 启动系统方案与实机测试关口

> 日期：2026-11-21  
> 状态：方案冻结候选 + 构建流程准备；尚未运行 CI 构建、尚未写 TF、尚未实机启动。  
> 本阶段 eMMC 绝对只读；正式交付版本目标仍是安装在 eMMC 并从 eMMC 启动。

## 1. 本轮目标与边界

本轮不再继续扩展 GMAC TX/RX 故障研究。目标是用最少的可变因素，验证 Panther X2 能否从现有启动链进入一个可交互的 ARM64 Linux 最小系统。

第一阶段采用 RAM initramfs，而不是完整 Ubuntu/Armbian rootfs：
- 验证 SPL/U-Boot 到 Linux 6.18.64 的交接；
- 验证 Panther X2 DTB、串口、CPU、内存、MMC/eMMC 控制器和基础内核初始化；
- 不挂载 eMMC 或 TF 文件系统；
- Linux init 运行后，将所有 MMC block devices（含分区及 eMMC boot partitions）设置为 block-layer read-only；
- 不启动网络配置，不做 GMAC 数据收发测试；
- 不安装服务或应用，不修改 eMMC。

RAM initramfs 是最小启动验收，不是最终服务器系统。通过后再构建无桌面的最小 Debian/Ubuntu rootfs，随后才进入正式 eMMC 安装设计。

## 2. 选定的 Linux 组件

### 2.1 Kernel

选用 Ophub 主线 stable kernel **6.18.64**：
- Release asset：`https://github.com/ophub/kernel/releases/download/kernel_stable/6.18.64.tar.gz`
- SHA-256：`6d7ba9ffee7b84ecb2f9095b3b9441f83bdce8a2e2e7958c18795c8d59eb7812`
- 包大小：124,458,864 bytes
- Release asset 更新时间：2026-11-20 10:32:35 UTC
- Panther X2 设备数据库使用 `stable/6.18.y` 分支路线。
- 主线源码中存在 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`。

注意：release 元数据没有给出该二进制包对应的精确 Linux source commit。2026-11-20 源码树 HEAD `aa69b89ea54f1ec5b9cfc67a0ef429f202d258a1` 是时间上相邻的源码参考，不能在没有构建元数据时声称它就是该包的精确构建 commit。测试使用的是已发布且 SHA-256 固定的二进制包；构建时还要验证包内实际 `Image` 和 Panther X2 DTB 文件。

### 2.2 Kernel config 依据

Ophub stable `config-6.18` 文件 Git blob：
- SHA-1：`192f0098eb527da9a2039c407f07061255092554`
- 文件头标识 Linux/arm64 6.18.63（比 6.18.64 包早一个小版本）。

已核对该稳定配置包含：
- `CONFIG_BLK_DEV_INITRD=y`
- `CONFIG_RD_GZIP=y`
- `CONFIG_MMC=y`
- `CONFIG_MMC_BLOCK=y`
- `CONFIG_MMC_DW_ROCKCHIP=y`
- `CONFIG_MMC_SDHCI_OF_DWCMSHC=y`
- `CONFIG_DEVTMPFS=y`
- `CONFIG_DEVTMPFS_MOUNT=y`

这说明相邻稳定配置具备 initramfs、gzip、Rockchip MMC、SDHCI 和 devtmpfs 支持；仍需从 6.18.64 发布包中提取实际 config（若包内提供）核验，不把 6.18.63 config 当作 6.18.64 的精确证明。

### 2.3 DTB

使用 kernel 发布包内的：
`dtb/rockchip/rk3566-panther-x2.dtb`

构建时必须用 `fdtget` 验证根节点 model 含 Panther，并记录 DTB SHA-256。不得以 E25、E23、ROCK 3C 的 DTB 替代。

### 2.4 Initramfs

使用 BusyBox 1.37.0 作为临时 RAM 救援 shell：
- 源码：`https://busybox.net/downloads/busybox-1.37.0.tar.bz2`
- SHA-256：`3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4`
- ARM64 静态构建。
- 该 BusyBox 只服务于 RAM initramfs 调试环境，不代表正式系统采用 BusyBox 替代完整用户空间。

附加 `blockro` 小工具使用 Linux `BLKROSET/BLKROGET` ioctl，在 Linux init 启动后将所有 MMC block devices 设置并验证为只读。任何一个设备无法设置或验证只读，initramfs 就 fail-closed，不进入交互 shell。

重要限制：该只读保护从 Linux init 开始生效，**不能保护此前运行的 SPL、BL31 和 U-Boot proper**。

## 3. 当前已验证的混合启动链

已有 UART 证据证明以下路线可工作：
1. eMMC 中当前活动 SPL；
2. SPL 从 TF 的固定 raw sector 读取 JP-TvBox U-Boot proper；
3. U-Boot proper 识别 TF 的 GPT/EFI 类型分区；
4. 从 TF ext4 分区加载 `/boot.scr`、`/Image`、`/uInitrd`、Panther X2 DTB；
5. 通过 `booti` 启动 ARM64 Linux。

已归档 JP-TvBox proper：
- 路径：`docs/research-assets/bootloader/panther-x2/JP-TvBox-U-Boot/u-boot.itb`
- SHA-256（2026-11-20 用户归档清单）：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`
- 文件大小：1,464,832 bytes
- 计划写入 TF LBA 16384（8 MiB）。
- TF 分区从 LBA 32768（16 MiB）开始，避免 raw FIT 与 GPT/文件系统重叠。
- 本次 TF image 不写 IDB/SPL；它依赖 eMMC SPL，因此明确是 hybrid test，不是 TF 独立启动。

### 为什么暂不更换 U-Boot proper

JP-TvBox proper 是已有实机启动证据的 proper；本轮只更换 Linux Image、DTB 和 RAM initramfs，避免同时变更 bootloader 和 kernel，降低故障定位变量。NixOS/mainline U-Boot 新候选留待下一阶段。

## 4. TF 镜像布局

构建目标：2 GiB raw image，写入现有 8 GB TF 测试卡。

| 位置 | 内容 |
|---|---|
| LBA 0–33 | GPT 主表 |
| LBA 16384（8 MiB） | JP-TvBox `u-boot.itb` raw FIT |
| LBA 32768（16 MiB）起 | GPT 分区 1，EFI 类型 GUID，ext4 文件系统 |
| 分区根目录 `/boot.scr` | 新建最小启动脚本 |
| `/Image` | Linux 6.18.64 ARM64 Image |
| `/uInitrd` | BusyBox RAM initramfs，legacy U-Boot ramdisk image |
| `/dtb/rockchip/rk3566-panther-x2.dtb` | Panther X2 专用 DTB |

Boot script：
- 使用当前已验证的 `devtype/devnum`、`kernel_addr_r`、`ramdisk_addr_r`、`fdt_addr_r`；
- `console=ttyS02,1500000 earlycon`；
- `rdinit=/init`；
- `booti` 启动；
- 不指定 eMMC rootfs，不执行 mount/fsck。

## 5. 最小系统验收标准

只有以下项目全部通过，才判定第一阶段成功：

1. UART 出现 Linux 6.18.64 版本信息，启动进入 `/init`。
2. 能显示 Panther X2 model，CPU 核心和 4 GB DRAM 容量正确。
3. 串口 `ttyS02` 1,500,000 baud 可交互。
4. eMMC 和 TF 控制器被识别；`/proc/partitions` 显示设备。
5. 所有 `/sys/class/block/mmcblk*` 对应设备（包括分区和 boot0/boot1）都显示只读；`blockro` ioctl 验证成功。
6. mount table 仅有 proc、sysfs、devtmpfs、run tmpfs；没有 eMMC/TF 文件系统挂载。
7. 无 kernel panic、initramfs unpack 错误或反复重启。

本轮不以网卡 TX/RX、DHCP、SSH、Immich、NPU 为验收项。

## 6. 关键安全阻断：当前 eMMC SPL 写入风险未排除

### 6.1 新发现的源码证据

JP-TvBox U-Boot proper 日志身份：
- `U-Boot SPL 2017.09-armbian (Nov 12 2023 - 15:05:14)`
- proper 自报 `Model: Radxa ROCK3 Model C`
- 使用 RK3566 ROCK 3C 板级代码路线的证据较强，但二进制到源码 commit 的精确映射尚未证明。

Radxa 源码候选：
- 仓库：`radxa/u-boot`
- 分支 commit：`c55987146f4f9b20f7cb2f917ca88300419afe8d`
- 文件：`configs/rock-3c-rk3566_defconfig`
- 该 defconfig 明确启用 `CONFIG_SPL_MMC_WRITE=y`、`CONFIG_SPL_AB=y`、`CONFIG_FASTBOOT_FLASH=y`。

同一 commit 的源码路径：
- `common/spl/spl_fit.c`：FIT 加载失败时调用 `spl_ab_decrease_tries(info->dev)`；
- `common/spl/spl_ab.c`：A/B metadata 通过 `blk_dwrite()` 写回 `misc` 分区；metadata 校验失败时会初始化并写回 metadata；
- `arch/arm/mach-rockchip/board.c`：`board_late_init()` 调用 `rockchip_set_ethaddr()`；LAN_MAC 无效/读取失败时生成随机 MAC 并调用 `vendor_storage_write()`；
- `arch/arm/mach-rockchip/vendor.c`：Vendor Storage 最终有 `blk_dwrite()` 写路径。

### 6.2 对当前测试的影响

- SPL 先从 TF 加载 proper，若 TF FIT 无效，可能继续尝试其他介质。
- 在该候选源码中，FIT 失败会触发 SPL A/B tries 更新；目标是当前 SPL 设备的 `misc` 分区。
- 如果回退到 eMMC 且 eMMC 存在可写 `misc` 分区，可能发生 eMMC 写入。
- proper 的 Vendor Storage 写入由 `bootdev_type` 选择设备；若启动介质判定落到 eMMC，MAC 无效/读取失败也可能触发写回。
- 目前没有把实际 eMMC 活动 IDB/SPL 二进制与该源码 commit 精确对应，也没有完成 eMMC 分区表与 misc 分区存在性的独立核验。

因此不能把“TF 正常启动时日志没有写入”当作 eMMC 绝对只读证明。

### 6.3 放行条件

在 eMMC 绝对只读阶段，以下条件未满足前，不写 TF、不上电执行这条测试启动链：
1. 从 2026-11-20 eMMC-user-area 镜像提取实际活动 IDB/SPL，计算 SHA-256，与归档 JP `idbloader.img`（归档清单 SHA-256 `e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`）核对。
2. 找到该二进制的精确 U-Boot 源码 commit、defconfig 和最终 `.config`；逐项审计 SPL A/B、Vendor Storage、所有自动写路径。
3. 读取 eMMC 当前 GPT/分区表，确认是否存在 `misc`、Vendor Storage 区域及写路径的实际目标。
4. 若无法证明所有启动路径都不写 eMMC，必须改用经过验证的 eMMC 硬件写保护/隔离，或先研究可真正绕过 eMMC SPL 的 USB RAM boot 路线；不能用 Linux initramfs 的 `blockro` 代替。

## 7. 构建流程已准备，尚未执行

已新增：
- `scripts/panther-x2-minimal-initramfs/init`
- `scripts/panther-x2-minimal-initramfs/blockro.c`
- `scripts/panther-x2-minimal-initramfs/boot.cmd`
- `.github/workflows/build-panther-x2-minimal-ram-boot.yml`

Workflow 使用 `workflow_dispatch`，将：
1. 下载并校验 6.18.64 发布包；
2. 提取 kernel Image 和 Panther X2 DTB；
3. 编译 ARM64 静态 BusyBox 1.37.0；
4. 编译 MMC block-layer read-only helper；
5. 生成 RAM initramfs 和 U-Boot boot.scr；
6. 用已归档 JP proper 构建 2 GiB hybrid TF 镜像；
7. 对镜像、组件和分区表做校验；
8. 上传名为 `panther-x2-minimal-6.18.64-hybrid-PREPARE-ONLY` 的构建产物。

该 workflow 是准备流程，不是写卡或实机启动流程。即使构建成功，产物也不能在 SPL 写入风险未解除前刷入 TF 并启动。

## 8. 下一步执行顺序

1. 先读取 eMMC 镜像中的活动 IDB/SPL，核对归档 JP IDB SHA-256。
2. 完成该 SPL 的精确源码/配置及写路径审计，尤其是 SPL_AB 失败回退。
3. 同时核对 eMMC GPT 是否有 misc 分区、Vendor Storage 实际所在介质和当前内容。
4. 安全关口通过后，触发 GitHub Actions 构建 6.18.64 minimal RAM TF image。
5. 对 8 GB TF 卡写入镜像（明确核对 macOS 设备号，严禁误选 eMMC/其他磁盘）。
6. 再执行 UART 实机启动，收集完整从 SPL 到 initramfs 的串口日志。
7. 通过第一阶段后，再构建最小完整 rootfs，最后进入正式 eMMC 安装/启动设计。

## 9. 状态

- 组件候选：第一阶段已收敛。
- Kernel 版本：选择 6.18.64 stable，精确包 SHA-256 固定。
- DTB：选择 Panther X2 专用 DTB，构建时检查 model 和哈希。
- Bootloader：第一轮暂时沿用已验证 JP proper；不更换 SPL。
- Initramfs：BusyBox 静态 shell + MMC read-only guard。
- TF image：构建流程已准备，尚未运行。
- eMMC 只读：Linux 阶段可设置 block-layer RO；SPL/BL31/U-Boot 阶段仍未证明零写入。
- 实机启动：**未放行**，待活动 eMMC SPL 写入审计。
- 最终产品：eMMC 安装、eMMC 启动、eMMC 运行；正式版本按明确分区/更新/恢复策略允许受控写入。


## 10. 重要补充：确认 eMMC 当前安装的 U-Boot 与 JP-TvBox 不是同一套 IDB/SPL（2026-11-21）

回读 2026-11-20 用户归档清单、eMMC 分区只读 debugfs 提取记录及 2026-11-16 UART/原始 IDB 读取记录后，纠正此前容易混淆的描述：

### 10.1 当前 eMMC 安装的 Panther-X2 U-Boot 资产

用户从当前 eMMC 的 `/usr/lib/u-boot` 只读提取：
- `idbloader.img`：305,152 bytes，SHA-256 `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e`；
- `u-boot.itb`：1,431,552 bytes，SHA-256 `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af`。

这两个 SHA-256 与仓库 `ophub/u-boot` 的 `u-boot/rockchip/panther-x2/` 资产相符：
- IDB blob SHA-1 `d22b624fc90c46e656baf98894bee182316e692e`；
- proper blob SHA-1 `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c`。

2026-11-16 的只读原始设备采集日志还记录从 eMMC 原始区域读取的 IDB 与上述文件 SHA-256 相同。因此这不是仅仅从包管理器推断的候选，而是当前 eMMC 安装资产的强证据。

### 10.2 JP-TvBox 归档资产是另一套不同二进制

JP-TvBox U-Boot 归档：
- `idbloader.img`：归档 SHA-256 `e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`；
- `u-boot.itb`：归档 SHA-256 `a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`。

JP IDB 与当前 eMMC IDB 不同，不能再把 JP-TvBox 的 SPL 直接说成当前 eMMC 正在执行的 SPL。历史 UART 日志中曾出现 SPL 2017.09-armbian（2023-04-23）加载 U-Boot proper（2023-11-12）的组合；它支持“eMMC 前级与 TF proper 分离”的路径，但每次测试实际运行哪一个 IDB，必须由该次串口日志与原始二进制 hash 对应确认。

### 10.3 写入风险的准确表述

Radxa `stable-4.19-rock3` commit `c55987146f4f9b20f7cb2f917ca88300419afe8d` 的 `rock-3c-rk3566_defconfig` 开启 `CONFIG_SPL_AB`、`CONFIG_SPL_MMC_WRITE`、`CONFIG_ROCKCHIP_VENDOR_PARTITION` 和 `CONFIG_FASTBOOT_FLASH`；同一源码树确有 SPL A/B `blk_dwrite()`、Vendor Storage `blk_dwrite()` 和 board_late_init MAC fallback 写入路径。

但尚未证明当前 eMMC IDB（SHA-256 990afd…）就是由该 commit、该 defconfig 和对应最终 .config 构建。因此这些源码只能作为高相关候选证据，不能写成当前二进制已确认包含所有这些代码/配置。

现有日志中的 `No misc partition` 是运行时 U-Boot 输出，但尚未严格定位它对应 eMMC 还是 TF 的设备描述符；必须从原始日志上下文和当前 eMMC GPT 分别核对，不能用该字符串直接证明 eMMC 没有 misc 分区。

### 10.4 对当前构建方案的影响

本方案只把 JP-TvBox `u-boot.itb` proper 放到 TF LBA 16384（8 MiB），不写 JP `idbloader.img`；TF 分区从 LBA 32768（16 MiB）开始。它依赖当前已验证的 eMMC SPL 能从 TF 的对应 raw sector 读取 proper。构建产物仍标记为 PREPARE-ONLY。

在允许实机启动之前，还必须完成：
1. 读取当前 eMMC 原始 IDB 二进制并提取/识别 SPL 版本、DDR blob 标识及可匹配的构建来源；
2. 追溯 `ophub/u-boot` Panther-X2 IDB/proper 二进制的构建 commit、defconfig、最终 .config；
3. 核对当前 eMMC GPT 中 misc 分区是否存在及 Vendor Storage 实际物理目标；
4. 对“TF proper 正常加载”“TF 读取失败”“TF proper FIT 校验失败”“MMC 初始化失败/回退”分别建立实际设备目标和写入调用矩阵；
5. 若任何路径可能写 eMMC，则当前阶段不得执行该启动链，必须改用能隔离 eMMC 写入的启动方法或取得经验证的硬件只读隔离。

这项补充取代本报告第 6 节中任何将 JP-TvBox IDB/SPL 直接等同于当前 eMMC SPL 的表述。


## 11. 优先采用 eMMC 芯片级临时写保护，建立真正的测试保护层（2026-11-21）

在 Linux initramfs 的 block-layer RO 之外，新增一个更早生效的保护评估：如果当前 eMMC 支持 eMMC Power-on Write Protect，可在启动测试前由当前运行中的 Linux 设置 user area 的 power-on write protect，并设置 boot0/boot1 的非永久 write protect。该保护由 eMMC 芯片执行，早于 BootROM/SPL/BL31/U-Boot；用户区 power-on 保护在下一次真正 power-on 后解除，boot partition 保护也不是永久配置。

这项功能已由 mmc-utils 文档/源码确认：
- `mmc writeprotect user get <device>`：只读查询 user-area write-protect groups；
- `mmc writeprotect boot get <device>`：只读查询 boot partition 写保护状态；
- `mmc writeprotect user set pwron <start-block> <blocks> <device>`：设置 user area power-on write protection，范围必须按 WP group 对齐；
- `mmc writeprotect boot set <device>`：保护 boot0/boot1，直到下一次 boot/power-on 周期；
- 严禁使用 `perm`、`-p` 或任何永久写保护操作。

### 11.1 只读预检（可先执行，不改变 eMMC）

先在当前已运行的 Linux 中确认 eMMC 设备名和 CID，不能假定它始终是 `/dev/mmcblk1`：

```sh
lsblk -o NAME,MAJ:MIN,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS

for d in /sys/block/mmcblk[0-9]*; do
    [ -e "$d/device/cid" ] || continue
    echo "===== $d ====="
    cat "$d/device/cid"
    cat "$d/device/name" 2>/dev/null
    cat "$d/size"
done

mmc extcsd read /dev/mmcblkX
mmc writeprotect user get /dev/mmcblkX
mmc writeprotect boot get /dev/mmcblkX
cat /sys/block/mmcblkX/size
cat /sys/block/mmcblkXboot0/force_ro 2>/dev/null
cat /sys/block/mmcblkXboot1/force_ro 2>/dev/null
```

其中 `mmcblkX` 必须替换成通过 CID、型号、容量和当前挂载点确认的 eMMC，而不是 TF。以上均为读取 EXT_CSD、WP 状态和 sysfs 信息，不执行写保护设置。

### 11.2 写保护设置（当前未授权、未执行）

只有在只读预检证明该 eMMC 支持 power-on user-area WP、WP group 大小和容量边界可完整覆盖，并确认 boot0/boot1 状态后，才向用户请求单独授权。授权后计划：

1. 先设置 user area 从 block 0 到容量末尾的 `pwron` WP，确保起止 block 都按 WP group 对齐；
2. 再设置 boot0/boot1 的非永久 write protect；
3. 重新读取 EXT_CSD 和 WP group 状态，逐组确认整个 user area 均为 power-on protected，boot0/boot1 均受保护；
4. 任一组保护失败、容量不对齐、状态查询不完整或设备映射有歧义，立即停止，不进行启动测试；
5. 只有芯片级写保护完整验证后，才允许进行 eMMC SPL → TF proper → RAM initramfs 测试。

设置 WP 本身会写入 eMMC 的保护配置/发送写保护命令，但不会改写用户数据区内容；它不是永久保护。该动作属于硬件存储配置变更，必须取得用户明确授权后执行。

### 11.3 该保护的边界

- eMMC 芯片级 WP 覆盖 user area 和 boot0/boot1 后，能够拒绝测试期间对这些区域的写入，包括 SPL A/B metadata、Vendor Storage、U-Boot 环境或误触发的更新写入。
- RPMB 不作为普通块设备访问；本轮启动链不应启用 RPMB 写服务。若有 secure monitor/TEE 触发 RPMB 写入路径，仍需单独审计。
- 必须确认 WP 状态在所用的复位方式下仍有效。Power-on WP 的解除条件是下一次真正 power-on；如果测试流程会切断 eMMC VCC 或触发会清除该状态的硬复位，则需重新预检，不能假定仍受保护。
- Linux initramfs 的 `blockro` 仍保留，作为第二层软件只读验证；芯片级 WP 和 Linux block-layer RO 是两层不同保护。

### 11.4 当前状态

- 已确认 eMMC 当前安装的 IDB/proper 哈希与 JP-TvBox 不同。
- 现有 Linux 采集记录显示 eMMC user area 只有 BOOT/ROOTFS 两个 GPT 分区，没有 `misc` 分区；仍须用当前原始 eMMC GPT 再次只读确认。
- Vendor Storage 的 LAN_MAC 项在此前 eMMC-user-area 镜像解析中有效；仍须确保芯片级 WP 覆盖其实际物理位置。
- **尚未读取当前 eMMC 的 EXT_CSD/WP group 能力；尚未设置任何 eMMC 写保护；尚未运行 workflow；尚未写 TF；尚未实机启动。**


## 12. 实际 eMMC EXT_CSD / 写保护能力预检结果（用户实机输出，2026-11-21）

用户在当前 SD 启动的 Panther X2 Linux 上执行只读预检，结果已回传并归档。

### 12.1 设备映射（已验证）

- 当前根文件系统：`/dev/mmcblk0p2`，ext4 rw。
- `mmcblk0` CID：`035344534e36344780af5519750159b7`，名称 `SN64G`，容量 124,735,488 sectors（64 GB SD 卡）；对它执行 EXT_CSD 命令返回 timeout，符合 SD 卡不是 eMMC 的情况。
- `mmcblk1` CID：`450100444634303332010f37d8066500`，名称 `DF4032`，容量 61,071,360 sectors（约 29.1 GiB），为板载 eMMC。
- eMMC boot0/boot1 各 4 MiB；lsblk 当前 RO=1 是 Linux boot partition 节点状态，不能等同于 eMMC 芯片 EXT_CSD 硬件写保护。
- 当前 eMMC user area 未挂载；当前系统由 SD 卡启动。

### 12.2 EXT_CSD 能力（已验证）

针对 `/dev/mmcblk1`：
- EXT_CSD revision 1.8，MMC 5.1。
- `SEC_COUNT=0x03a3e000=61,071,360` sectors。
- `HC_ERASE_GRP_SIZE=0x01`，`HC_WP_GRP_SIZE=0x10`，mmc-utils 报告 WP group = 16,384 sectors = 8 MiB。
- `ERASE_GROUP_DEF=1`。
- `USER_WP=0x00`：当前 user-area WP 配置未启用。
- `BOOT_WP=0x00`、`BOOT_WP_STATUS=0x00)：boot0/boot1 当前无芯片级写保护。
- 工具报告 boot power-on RO locking possible，permanent RO locking possible；boot partition 0/1 not locked。
- user WP 查询显示 group 0–3726（blocks 0–61,063,167）均为 No Write Protection。

### 12.3 重要边界：user area 尾部存在半个 WP group 的容量余数

计算：
- 完整 WP groups：`61,071,360 / 16,384 = 3,727 remainder 8,192` sectors。
- mmc-utils `writeprotect user get` 的源码按整数除法计算 group 数（`dev_sizeblks / wp_sizeblks`），所以只查询并报告 0–3726；最后 8,192 sectors（4 MiB）没有出现在输出中。
- mmc-utils `writeprotect user set` 要求 start 和 blocks 都是 16,384 sectors 的倍数，并对每个 group start 发 CMD28；其参数校验不允许用 8,192-sector 半组长度。

因此，当前输出只能证明完整的 3,727 个组没有保护；不能据此声称 eMMC user area 全容量已可由 mmc-utils 一条命令完整覆盖。最后 4 MiB 是否能通过对尾部地址发 CMD28 而保护、芯片如何处理最后一个不完整组、以及如何可靠读回验证，必须进一步依据该 eMMC 型号/控制器行为和 MMC 规范确认。**在这个尾部问题解决前，不设置 user WP，也不允许把芯片级 WP 当作全 user-area 的完整保护。**

### 12.4 下一步只读研究与安全决策

1. 识别 DF4032 的完整厂商/型号/容量规格（结合 CID 字段、EXT_CSD 厂商字段及板级资料），查明最后不完整 WP group 的标准行为。
2. 审查 mmc-utils 的 WP group 查询源码与 CMD28/CMD31 读回机制；明确是否可以单独查询最后一个 group，且不触发写入。
3. 计算覆盖范围并设计验证方案；若末尾 4 MiB 不能可靠保护，则不能宣称完整芯片级只读，改用硬件断开 eMMC VCC/总线隔离或其他经验证方案。
4. boot0/boot1 的 Power-on WP 与 user area 分开处理；只有确认 eMMC 当前启动流程无需写 boot partitions，且保护可在当前启动周期维持，才考虑设置。
5. 所有设置命令仍需用户单独明确授权；严禁 `perm`、`-p`、EXT_CSD 永久锁定或分区配置类命令。

### 12.5 状态修正

- 已验证：eMMC 为 `/dev/mmcblk1`，CID/容量匹配；MMC 5.1；WP group 8 MiB；user area 完整组 0–3726 未保护；boot0/boot1 未芯片级保护；支持 power-on locking。
- 未验证：尾部 4 MiB 部分组保护方式；设置后 CMD31 读回策略；实际启动过程中 WP 状态是否持续到目标复位/启动序列。
- 未执行：任何写保护设置、任何 EXT_CSD 写操作、TF 镜像写入或实机启动测试。


### 12.6 mmc-utils 源码交叉核对（补充）

对 mmc-utils `mmc_cmds.c` 的 `do_writeprotect_user_get()` 与 `do_writeprotect_user_set()` 做了源码检查（交叉参考源码镜像：`Asuswrt-Merlin/asuswrt-merlin.ng`，commit `5f55bac2886f205d11bd44761bd3be4c02c58e79`，文件 `release/src-rt-5.04axhnd.675x/router-sysdep.xt12/mmc-utils/mmc_cmds.c`）：

- `user get` 使用 `cnt = dev_sizeblks / wp_sizeblks`，整数除法会舍弃最后不足一个 WP group 的余数；它只对完整组发起 CMD31 查询。
- `user set` 明确检查 `blk_start % wp_blks == 0` 和 `blk_cnt % wp_blks == 0`，否则拒绝；随后按 `wp_blks` 步长对每个 group 起始地址发 CMD28。它不能通过该命令保护 8,192-sector 的半组长度。
- 该实现对 `USER_WP` 先设置相应 enable 位，再逐组发 CMD28，最后恢复原 `USER_WP` 值；真正逐组锁定由 CMD28 完成。
- `user get` 通过 CMD31 查询 group 的 write-protect type。其输出未覆盖的最后半组，不能被误读成“末尾未保护”或“末尾已保护”；只说明工具没有查询该区域。
- 此处源码是可审计的 mmc-utils 实现参考，不代表用户设备上的 `/usr/bin/mmc` 已证明与该 commit 完全一致；后续应读取本机 mmc-utils 版本/源码包或二进制构建信息核对。

因此目前的严格结论是：**mmc-utils 的标准 user-set/get 接口无法按其边界参数直接表达最后 4 MiB；最后半组的芯片级实际保护行为仍未验证。不得自行把 blocks 向上取整后执行，也不得猜测 CMD28 会自动覆盖或拒绝。**
