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


## 13. 纠正“最后 4 MiB 无法保护”的判断：SanDisk DF4032 最后一个部分 WP group 可寻址（2026-11-21）

本节修正第 12.3、12.4、12.6 节中“尾部半组无法保护/尚无法确认是否存在”的过度保守结论。新证据来自与实机 CID 精确匹配的 SanDisk iNAND 7232 数据手册，以及 JEDEC JESD84-B51 对 CMD28/CMD31 的定义。

### 13.1 实机 eMMC 型号得到确认（高度匹配，型号已识别）

实机 CID：

```
450100444634303332010f37d8066500
```

CID 字段解码：
- MID `0x45`：SanDisk；
- CBX `0x01`：BGA embedded device；
- OID `0x00`；
- PNM ASCII `DF4032`；
- PRV `0x01`。

SanDisk iNAND 7232 eMMC 5.1 数据手册明确列出 CID MID=45h、OID=00h、PNM 的 32GB 型号为 DF4032、PRV=01h；并列出 32GB 用户容量 `0x3A3E000` LBA、`HC_ERASE_GROUP_SIZE=1`、`HC_WP_GRP_SIZE=0x10`，写保护组大小 8 MiB。这与实机 EXT_CSD/CID/SEC_COUNT 完全吻合。因此可把实机识别为 SanDisk iNAND 7232 DF4032 32GB 型号，而非仅凭通用 CID MID 推测品牌。

### 13.2 尾部不是“半个不存在的组”，而是最后一个有效组的可用容量只有半组

实机 user area：
- 总容量：`SEC_COUNT = 0x03A3E000 = 61,071,360` sectors；
- WP group：`0x4000 = 16,384` sectors = 8 MiB；
- `floor(SEC_COUNT / WP_GROUP)=3727` 个完整组；
- `ceil(SEC_COUNT / WP_GROUP)=3728` 个可寻址组；
- 最后一个组 index 3727 的起始 LBA：`3727 × 16384 = 61,063,168 = 0x03A3C000`；
- 最后一个组在 user area 中实际存在的可用部分：LBA 61,063,168–61,071,359，共 8,192 sectors = 4 MiB；组的名义边界会延伸到设备容量之外，但组起始地址仍在有效 user-area 地址范围内。

SanDisk 数据手册同时将 32GB user density 定义为 `0x3A3E000` LBA，并定义其 WP group 为 8 MiB；这与上述 3728 个可寻址组（最后一组容量被设备末端截断）的解释一致。

### 13.3 JEDEC 命令语义支持对最后一个有效组起始地址操作

JEDEC JESD84-B51 §6.6.15 规定 CMD28 SET_WRITE_PROT 对“addressed write-protect group”设置保护；地址单位对大于 2GB 的设备是 sector。该节还规定，只有提供给 CMD28/CMD29/CMD30 的地址参数越出有效范围，设备才以 ADDRESS_OUT_OF_RANGE 拒绝命令。

最后组起始地址 LBA 61,063,168 小于 SEC_COUNT 61,071,360，因此 CMD28 的地址参数本身位于有效 user-area 地址范围内。CMD31 §6.10.4 的说明规定一次返回 32 个 WP groups 的保护类型；超出有效范围的尾部组位返回 0。因此可以从最后组起始地址直接发起 CMD31 查询该组；同一次 32-group payload 中超出容量的组位应为 0。

**据标准命令模型和 SanDisk 容量/组大小定义，最后 4 MiB 是最后一个有效 WP group 的实际容量尾段，应由对该组起始 LBA 的 CMD28 保护覆盖；不是一个需要独立 CMD28 地址的半组。** 这解决了“是否存在可寻址最后组”的规范层问题。

### 13.4 mmc-utils 的真实缺陷与正确覆盖参数

mmc-utils 当前上游实现：
- `do_writeprotect_user_get()` 使用向下取整 `dev_sizeblks / wp_sizeblks`，只查询 3727 个完整组，漏掉最后一个可寻址组；
- `do_writeprotect_user_set()` 要求 start 和 count 均为 WP group 的整数倍，之后按 group 起始地址逐个发送 CMD28；但它没有用 `blk_cnt <= dev_sizeblks` 限制 count，也不会对 count 范围逐扇区写数据。

因此覆盖 3728 个可寻址组的参数计算为：
- start = 0；
- group_count = 3728；
- blocks = `3728 × 16384 = 61,079,552` sectors；
- mmc-utils 循环发送的最后一条 CMD28 地址为 `61,063,168`，即有效最后组的起始 LBA，未向设备发送越界的 CMD28 地址。

这说明标准 mmc-utils 的 user-set 参数可以用“向上取整后的 group 数 × group size”迭代所有可寻址组。blocks 参数会比 BLKGETSIZE 返回的容量多 8,192 sectors，但它只用于循环次数；真正发给 eMMC 的 CMD28 参数是每组起始 LBA。**这是源码控制流推导，不是已经在本机实测的行为；执行前必须先确认设备上 mmc-utils 二进制与所审查源码一致，或自行构建/审查固定版本。**

### 13.5 仍须补做的只读验证，不再把它当作容量未知问题

下一步只读验证方案：
1. 获取本机 mmc-utils 版本/构建来源，固定上游源码 commit。
2. 对 `do_writeprotect_user_get()` 做仅查询范围的临时补丁：把组数从 floor 改为 ceil，即 `(dev_sizeblks + wp_sizeblks - 1) / wp_sizeblks`；不改变任何写保护设置函数。
3. 使用修改版 `mmc writeprotect user get`，确认它对最后查询批次仍以 group 3712 起始地址发 CMD31，并解析 group 3727 的两位状态；这只是 CMD31 查询，不发送 CMD28。
4. 若现状仍为 No WP，则确认最后组确实可读回且状态为 No WP；这将完成最后组可寻址性实机验证。
5. 只有用户另行明确授权后，才执行 3728 组的 Power-on WP 设置；随后再次运行 ceil 版只读查询，确认 group 0–3727 全部为 Power-on protection。

### 13.6 状态修正

- 已验证：SanDisk DF4032/iNAND 7232 型号与实机 CID 匹配；32GB 容量和 8 MiB WP group 与数据手册吻合。
- 规范支持：最后一组起始 LBA 在设备容量内，CMD28 对该组起始地址有效；CMD31 可查询该组，超出设备范围的后续位应为 0。
- 源码已确认：标准 mmc-utils 的 `get` 向下取整而漏查最后一组；`set` 按 group 起始地址循环且未对总 blocks 做设备容量上限检查。
- 尚未实机验证：该 DF4032 对最后组 CMD31 的实际返回；mmc-utils 当前安装二进制与审查源码是否一致。
- 未执行：任何 CMD28、任何 user-area Power-on WP 设置、boot WP 设置、TF 写入或实机启动。

参考：SanDisk iNAND 7232 eMMC 5.1 datasheet DOC-06397/DOC-04417，CID、User Density、Table 18 WP group size；JEDEC JESD84-B51 §6.6.15、§6.10.4；mmc-utils `mmc_cmds.c` `do_writeprotect_user_get/set`。


## 14. 测试介质冻结：8GB TF 专用测试，64GB TF 保留 6.12 对照系统（用户明确要求，2026-11-21）

用户明确指定后续所有最小系统构建验证、镜像写入和实机启动测试均使用另一张 **8GB TF 卡**。现有 **64GB TF 卡是 6.12 对照系统，必须保持原状**，不得格式化、重新分区、写入镜像、修复文件系统、升级或作为临时测试盘。

### 14.1 三类介质的职责

| 介质 | 身份 | 用途 | 操作策略 |
|---|---|---|---|
| 8GB TF | 专用测试卡（具体 CID/型号待采集） | 后续唯一测试卡：写入最小系统镜像、启动及调试 | 允许在用户明确安排的测试步骤中写入；每次操作前核对 CID、型号、容量及目标路径 |
| 64GB TF | 现有 6.12 对照系统（CID/型号需与此前记录对应） | 保留作对照、必要时恢复对照启动 | 冻结为只读基准；不写入、不格式化、不改分区、不做文件系统修复，不作为临时存储 |
| Panther X2 eMMC | SanDisk iNAND 7232 DF4032，CID `450100444634303332010f37d8066500` | 测试保护对象；正式交付阶段则是目标安装介质 | 当前测试阶段先完成临时写保护验证；正式版本最终刷写到 eMMC 是另一阶段的明确目标 |

### 14.2 防止设备编号混淆

Linux 的 `/dev/mmcblkN` 编号会随启动介质、内核枚举顺序和插卡情况改变。不得把 mmcblk0/mmcblk1 固定等同于某张卡或 eMMC。任何读取、写入、挂载、保护操作前，均须结合 CID、型号、容量、分区表和当前挂载点识别目标。写入 8GB 测试卡前，必须同时确认目标不是 64GB 对照卡，也不是 eMMC。

### 14.3 当前约束和状态

- 64GB 6.12 对照卡：冻结，不动。
- 8GB 测试卡：作为后续唯一写入及启动测试介质；其 CID、精确容量和设备节点尚待只读识别。
- eMMC：在芯片级 Power-on WP 覆盖完整性完成验证并经用户明确授权前，不允许进入可能触发写入的启动测试。
- 任何测试镜像写入只允许针对经 CID 再次确认的 8GB 测试卡；不能用设备节点编号或容量近似值单独作为识别依据。
- 正式交付架构最终以 eMMC 为系统安装/启动介质；当前 TF 启动仅为研究与验证阶段的临时测试方法，不改变最终部署目标。


## 15. 单 TF 卡槽下的测试介质切换顺序（用户明确补充，2026-11-21）

Panther X2 只有一个 TF 卡槽。当前 64GB TF 卡是 6.12 对照系统；8GB TF 测试卡不能与它同时插入，也不能在当前 64GB TF 启动环境中直接读取。

读取/识别 8GB 卡必须先切换到板载 eMMC 启动的原版 6.1.116 系统，具体顺序：
1. 在当前系统正常关机；
2. 取出 64GB 6.12 对照卡并单独保存，冻结不动；
3. TF 卡槽保持空置，从板载 eMMC 启动原版 6.1.116；
4. 从启动日志、根文件系统来源及块设备 CID 确认系统确实从 eMMC 启动；
5. 系统稳定后，将 8GB 测试卡插入唯一 TF 卡槽；
6. 只读采集 8GB 卡 CID、型号、容量、分区表及设备节点；同时可在该 eMMC 启动环境中读取 eMMC EXT_CSD、WP group 和 mmc-utils 版本，并进行只读 CMD31 查询准备。

不得在 64GB 卡仍插入时要求用户读取 8GB 卡；不得假设支持热插拔，插卡前先确认板级/内核对 SD 热插拔支持。如不能确认热插拔安全，则应在 eMMC 系统关机状态下插入 8GB 卡，再从 eMMC 启动。

### 15.1 设备职责不变

- 64GB TF：6.12 对照系统，取出后保存，不写入、不格式化、不修复。
- eMMC：运行原版 6.1.116 的临时管理/采集环境，同时仍是当前测试阶段的保护对象；读取 eMMC 不等于允许写 eMMC。
- 8GB TF：唯一测试介质；在确认 CID/容量前不写入任何镜像。
- 最小系统镜像最终只写入 8GB TF；正式交付系统最终仍刷写到 eMMC。

### 15.2 当前阶段状态

尚未执行介质切换；尚未从 eMMC 6.1.116 启动；尚未插入/识别 8GB TF；64GB 对照卡未修改。执行切换前须先确认当前服务可安全关机，并保留现有 6.12 对照卡原状。


## 16. 最小 RAM 启动构建流程复核与只读 CMD31 工具准备（2026-11-21）

### 16.1 复用既有 eMMC boot.cmd 启动语义已核对

回读 `docs/reports/2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md` 的 eMMC 原始 `boot.cmd` 审计，确认 Panther X2 现有启动脚本使用：

```sh
load ${devtype} ${devnum} ${ramdisk_addr_r} ${prefix}uInitrd
load ${devtype} ${devnum} ${kernel_addr_r} ${prefix}Image
load ${devtype} ${devnum} ${fdt_addr_r} ${prefix}dtb/${fdtfile}
booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}
```

因此，本项目继续使用 U-Boot legacy uInitrd 包装 + `booti` 的路径与当前 Panther X2 原版 6.1.116 启动配置一致，不另换启动机制。新构建的 legacy ramdisk image architecture 字段必须标为 AArch64；此前工作流写成 `-A arm` 不够准确，现已改为 `-A arm64` 并增加 `mkimage -l` 输出检查。

U-Boot v2026.10 `booti` 源码的 `bootm_find_images()` 调用 `boot_get_ramdisk()` 解析传入的 ramdisk 地址，legacy image 格式可按其 image header 识别；当前原版脚本和既有 U-Boot 运行记录也提供了相同用法的本机先例。

### 16.2 已修正测试镜像布局及构建检查

GitHub Actions workflow 已修正：
- GPT 分区类型恢复为已验证的 `EF00`（EFI System 类型），不再使用此前临时改成的 `8300`；文件系统仍为 ext4，与当前 U-Boot 从 SD/TF ext4 分区加载 `boot.scr` 的既有实机证据一致。
- JP proper 在镜像 LBA 16384 的写后哈希由“只打印”改为严格比较，任何不匹配均使 workflow 失败。
- 记录 GPT 分区信息并检查类型代码；输出 boot.scr/uInitrd header、Image、DTB、脚本哈希。
- uInitrd legacy header 明确标记 AArch64，并检查 `mkimage -l` 的架构字段。
- workflow 仍只生成 PREPARE-ONLY artifact，不触碰任何物理 TF/eMMC。

### 16.3 新增最后一个 WP group 的只读查询程序

新增源文件：
- `scripts/panther-x2-minimal-initramfs/mmc-wp-read-last.c`

该程序只允许目标设备同时满足：
- Linux MMC type 为 `MMC`；
- eMMC name 为 `DF4032`；
- CID 与命令行提供的预期 CID 完全相同。

程序读取 EXT_CSD（CMD8），从 SEC_COUNT、HC_ERASE_GRP_SIZE 和 HC_WP_GRP_SIZE 计算容量与 WP group；核对 BLKGETSIZE64 与 SEC_COUNT 一致后，计算最后一个可寻址 WP group，并以 CMD31 查询包含该组的最后一批 32 组状态。它会输出最后一组索引、起始 LBA、CMD31 payload 和保护状态。

源码只发出：
- CMD8 SEND_EXT_CSD（读 512 bytes）；
- CMD31 SEND_WRITE_PROT_TYPE（读 8 bytes）。

源码没有 CMD6、CMD28、CMD29 或数据写入调用；没有实现任何写保护设置功能。该工具必须在 root 权限下运行，且内核允许 MMC_IOC_CMD；若返回权限错误，不要改用任何写命令或尝试规避限制。

GitHub Actions workflow 已加入该程序的静态 ARM64 编译，并将二进制作为 PREPARE-ONLY artifact 附件输出。该工具尚未在目标设备编译或运行，CMD31 对 DF4032 最后组的实际返回仍未验证。

### 16.4 关于 2 GiB 镜像写入 8GB 卡后的 GPT 备份表位置

当前 workflow 产物为 2 GiB image，之后会写入容量更大的 8GB TF。GPT backup header 在 image 内位于 2 GiB 边界，不会自动移动到 8GB 卡物理末尾。写卡后需要对 8GB 卡执行一次只针对 GPT 元数据的 `sgdisk -e`（或等效 GPT relocate 操作），并用 `sgdisk -v` 验证；该步骤必须在用户确认 8GB 测试卡 CID/容量和写入目标后才进行。它不会扩展 ext4 分区，测试分区仍保留 2 GiB 上限。64GB 6.12 对照卡不参与此操作。

### 16.5 当前构建和实机状态

- 已复核：现有 eMMC 6.1.116 `boot.cmd` 使用 legacy uInitrd + booti；现有 U-Boot proper 已从 TF ext4 分区加载文件。
- 已修正：GPT 类型恢复 EF00；uInitrd 标记 AArch64；JP proper 镜像写入哈希改为强制校验。
- 已新增：DF4032 最后 WP group 的只读 CMD8/CMD31 查询程序；已加入 ARM64 静态构建 artifact。
- 尚未执行：GitHub Actions workflow；8GB TF 识别或写入；eMMC CMD31 查询；任何 CMD28/boot WP 设置；最小 Linux 实机启动。
- 64GB TF 6.12 对照卡保持冻结。
- 用户已明确：读取 8GB TF 必须先取出 64GB 卡、从板载 eMMC 启动原版 6.1.116，再在唯一 TF 卡槽插入 8GB 测试卡。该顺序为实机采集前提。

### 16.6 下一步顺序

1. 用户按单卡槽顺序切换至 eMMC 原版 6.1.116；确认 root 和 /boot 确实位于 eMMC。
2. 插入 8GB 测试卡（如热插拔安全未确认，则关机插卡后从 eMMC 启动），只读采集其 CID、容量、分区与设备节点；64GB 卡保持取出。
3. 运行 artifact 中的 `mmc-wp-read-last`，参数使用重新确认的 eMMC CID；只读查询最后 WP group。
4. 在独立授权后，才考虑 eMMC user-area 和 boot0/boot1 Power-on WP 设置；不得把查询工具误作设置工具。
5. 可并行在 GitHub Actions 手动触发 PREPARE-ONLY 构建；成功后审查 artifact 的文件清单、hash、GPT 和启动脚本，不写任何实体存储。
6. 完成 eMMC 芯片级保护全覆盖验证后，才授权将镜像写入经 CID 识别的 8GB 测试卡并进行 UART 实机启动。

**当前仍未获准实机启动。** 本报告不把“构建流程已准备”写成“已构建”，也不把历史 6.12.81 启动成功写成新 6.18.64 最小 initramfs 已实机验证。


## 17. 8GB TF 测试卡数据处置授权及当前 eMMC 实机基线（2026-11-21）

用户明确授权：后续使用的 8GB TF 卡现有内容不需要保留，可以全部删除、重新分区和格式化，用作本项目专用测试介质。此授权仅针对那张经 CID/容量/型号确认的 8GB TF，不适用于 64GB 对照卡或 eMMC。

介质约束更新：
- 8GB TF：允许破坏性重分区、格式化和写入测试镜像；必须先读取 CID、型号、精确容量、设备节点、分区及挂载状态，并在执行前再次核对目标身份。
- 64GB TF：6.12.81 对照系统，完全冻结，不插入、不写入、不格式化、不修复。
- eMMC：当前临时采集环境及测试阶段保护对象；不得因 8GB TF 数据可删除而扩大对 eMMC 的写入授权。
- 单卡槽切换规则不变：取出 64GB 卡 → 从 eMMC 启动 6.1.116 → 再插入 8GB 卡；除非已确认板级热插拔安全，否则关机插卡。

### 17.1 已取得的 eMMC 实机身份与挂载基线

用户在 root shell 提供的 2026-11-21 实机输出确认：
- 系统：Armbian unofficial，Linux 6.1.116-ophub，BOARD_NAME=RK-Panther-X2。
- 根文件系统：/dev/mmcblk0p2，ext4；/boot：/dev/mmcblk0p1，ext4。
- 当前唯一识别到的主 MMC 设备：/dev/mmcblk0，type=MMC，name=DF4032。
- CID：450100444634303332010f37d8066500。
- 容量：61071360 个 512-byte sectors（约 29.1 GiB）。
- boot0/boot1 各约 4 MiB，Linux 当前显示 RO=1；该值只是块层状态，不能当作 eMMC 芯片级 WP 已生效的证据。
- 当前 lsblk 未显示任何 SD 卡设备；8GB TF 尚未插入/识别。
- 本机 /usr/bin/mmc 为 mmc-utils 0.1 风格命令集；mmc version 不受支持，准确包版本/构建来源尚待查证。

### 17.2 下一步只读查询

先在当前 eMMC 6.1.116 环境对 /dev/mmcblk0 执行以下只读查询：

```sh
mmc extcsd read /dev/mmcblk0
mmc writeprotect user get /dev/mmcblk0
mmc writeprotect boot get /dev/mmcblk0
```

以上子命令用于读取 EXT_CSD 和现有 WP 状态，不是设置命令。严禁误用 user set 或 boot set。取得输出后再核对 user area 全部 WP group、boot0/boot1 状态及 CMD31 工具适配情况。

随后再按单卡槽顺序插入 8GB 卡，先只读识别其 CID/容量/分区/挂载状态。用户已授权该 8GB 卡可格式化，但在身份确认前不运行任何擦除/分区/格式化/镜像写入命令。

当前仍未执行：EXT_CSD/WP 查询、8GB 卡插入识别、eMMC WP 设置、TF 写入和最小系统实机启动。



## 18. EXT_CSD 读取结果及 mmcblk 编号变化纠正（2026-11-21）

用户上传两份实机记录，必须按各次启动的 CID 区分设备，不能跨启动沿用 mmcblk 编号。

### 18.1 第一份记录：64GB SD 与 eMMC 同时枚举

- /dev/mmcblk0：CID `035344534e36344780af5519750159b7`，name `SD64G`，容量 124,735,488 sectors（约 59.5 GiB），这是 64GB 6.12 对照 TF 卡。
- /dev/mmcblk1：CID `450100444634303332010f37d8066500`，name `DF4032`，容量 61,071,360 sectors，这是 eMMC。
- 当时 / 与 /boot 挂载于 /dev/mmcblk0p2、/dev/mmcblk0p1，说明该次运行根系统实际来自 64GB TF，而不是 eMMC。
- 对 /dev/mmcblk0 执行 mmc extcsd read 及 WP get 均 Connection timed out；该目标是 SD64G，不是 eMMC。不能将这些超时归因于 DF4032。
- 对 /dev/mmcblk1 的 EXT_CSD 读取开始成功，但上传记录中该段输出不完整。

### 18.2 第二份记录：DF4032 eMMC EXT_CSD 完整读取

第二份记录对当时的 /dev/mmcblk0 成功读取 EXT_CSD；型号、SEC_COUNT 与既有 DF4032 CID/容量相符。读取值：
- EXT_CSD rev 1.8 / MMC 5.1。
- SEC_COUNT=0x03a3e000=61,071,360 sectors，与 eMMC sysfs 容量吻合。
- HC_ERASE_GRP_SIZE=1，即 512 KiB。
- HC_WP_GRP_SIZE=0x10=16；结合 HC_ERASE_GRP_SIZE，WP group 大小为 8 MiB。
- ERASE_GROUP_DEF=1。
- BOOT_WP_STATUS=0x00，BOOT_WP=0x00，USER_WP=0x00。
- BOOT_CONFIG_PROT=0x00；RO locking 支持，但 ro lock status 为 not locked。

这些寄存器值表明当前未配置 EXT_CSD 所报告的 User Area / Boot Area 写保护，也未锁定 RO locking。它们不能替代 user area 逐组 CMD31/WP 状态查询。boot0/boot1 的 Linux RO=1 仍仅是块设备层只读标志。

### 18.3 重要纠正与下一步

- mmcblk 编号会随启动介质和枚举顺序变化。每次操作前必须按 CID + name + capacity 确认设备，禁止只凭 /dev/mmcblk0。
- 第一份记录显示 64GB 对照卡当时被插入且承载了根文件系统。该记录未显示对其执行任何写入命令，但后续仍按冻结原则不再操作这张卡。
- 第二份记录是目前 DF4032 EXT_CSD 的有效读取证据；但尚缺完整的 `mmc writeprotect user get` 和 `mmc writeprotect boot get` 输出。
- 下一步先通过 sysfs CID 精确查找 DF4032 的当前设备节点，再对该节点执行只读 `mmc writeprotect user get` 与 `mmc writeprotect boot get`。不要沿用历史 mmcblk0/1 编号。
- WP group 理论大小为 8 MiB。SEC_COUNT 对应容量不是 8 MiB 的整数倍，需以 mmc-utils 的实际逐组查询及 CMD31 返回进一步确认末尾部分组的边界/处理；不可自行把不完整尾组忽略。
- 尚未执行任何 WP 设置命令，尚未插入/识别 8GB 测试卡，尚未写入 TF 或启动最小系统。


### 18.4 对第二份 EXT_CSD 输出的证据强度补充

第二份上传记录只显示执行了 `mmc extcsd read /dev/mmcblk0` 及 EXT_CSD 内容，没有在同一份记录中附带该时刻 `/sys/class/block/mmcblk0/device/cid`、name 和容量。因此：
- SEC_COUNT=61,071,360 与已知 DF4032 容量完全一致，强烈符合 DF4032 的身份；
- 但仅凭该输出不能严格证明该次命令目标的 CID 就是 DF4032；
- 在执行任何后续 WP 查询前，必须在同一次终端会话中先打印 CID/name/sectors，并按 DF4032 的已知 CID 精确匹配，再使用动态确定的设备节点。


## 19. GitHub Actions run 44871804530 失败根因与工作流修正（2026-11-21）

Run: https://github.com/njosd/panther-x2-armbian/actions/runs/44871804530

### 19.1 已由日志确认的事实

- 外层 kernel package 下载成功，SHA-256 校验通过。
- 外层包实际包含：
  - `6.18.64/dtb-allwinner-6.18.64-ophub.tar.gz`
  - `6.18.64/dtb-amlogic-6.18.64-ophub.tar.gz`
  - `6.18.64/dtb-rockchip-6.18.64-ophub.tar.gz`
  - `6.18.64/boot-6.18.64-ophub.tar.gz`
  - `modules`、`header` 与 `sha256sums`
- 上一轮宽泛 `dtb*-${KERNEL_VERSION}-ophub.tar.gz` 查找按文件系统枚举顺序错误选中了 Allwinner DTB 包。这是工作流逻辑缺陷，不是上游包缺少 Rockchip DTB。
- boot archive 实际列出 `vmlinuz-6.18.64-ophub`、`uInitrd-6.18.64-ophub`、`initrd.img-6.18.64-ophub` 等；没有名为 `Image` 的文件。
- 失败日志显示原步骤在查找 `Image` 时退出。因此本次尚未真正检查 Rockchip DTB 包内容，也未构建 BusyBox/initramfs/TF image；无 artifact。
- 日志列出 vmlinuz 文件大小 43,878,912 bytes，但日志未运行 `file` 或检查 ARM64 Image magic，故其实际格式仍未验证。

### 19.2 工作流修正

- DTB archive 查找改为精确选择 `dtb-rockchip-6.18.64-ophub.tar.gz`，不再使用无区分的 dtb* 通配符。
- kernel payload 先找 `Image`，否则找版本化 `vmlinuz-6.18.64-ophub`。
- 不盲目把 vmlinuz 改名为 Image：工作流检查 ARM64 Image magic（文件偏移 0x38 的字节 `41 52 4d 64`）；若为 raw Image 则复制；若为 gzip 则解压后再次检查 magic；其他格式明确失败。
- 经审查修正该分支，确保 raw 分支和 gzip 解压分支都实际生成 `work/boot/Image`，并移除后续会覆盖解压结果的无条件复制。
- 相关提交：`d0292c3a860b559cc9d646b74a042311b04bc49e`。此前精确 DTB 归档与 vmlinuz 选择修正提交：`388266afac791e2b6af6353bf16dc2535ad9bc58`。

### 19.3 下一轮验证目标与当前状态

下一次 Actions 应依次验证：
1. 选择到 Rockchip DTB archive，并打印 Panther X2/RK3566 候选。
2. `vmlinuz` 是否为 raw ARM64 Image 或 gzip 压缩的 ARM64 Image；不符合则停下，不生成假 Image。
3. 找到确切的 `rk3566-panther-x2.dtb` 并通过 model 检查。
4. 之后才进入 BusyBox、initramfs、uInitrd、GPT、JP proper 哈希和 artifact 生成。

截至本记录，工作流修正已提交，但尚未由新的 Actions run 验证。无 TF/eMMC 设备写入或实机启动。


## 20. DF4032 eMMC WP 查询实测结果（2026-11-21）

用户在 eMMC 启动的 Armbian 6.1.116 环境中，先通过 sysfs 同时核对 CID、型号、容量，再动态确定设备节点。输出：
- `mmcblk0 name=DF4032`
- CID=`450100444634303332010f37d8066500`
- sectors=`61071360`
- Root source=`/dev/mmcblk0p2`，确认本次根文件系统位于 DF4032 eMMC。

只读查询结果：
- User Area WP Group size：16384 blocks / 8,388,608 bytes（8 MiB）。
- 工具报告 Groups 0–3726，覆盖 blocks 0–61,063,167，状态 `No Write Protection`。
- eMMC user area 总计 61,071,360 sectors；上述报告范围之外尚余 8,192 sectors（4 MiB）。当前 mmc-utils 输出没有为该尾部范围列出独立 group，不能据此声称尾部已逐组验证；需确认芯片/工具对末尾不完整 WP group 的定义。
- Boot Area：`BOOT_WP_STATUS=0x00`、`BOOT_WP=0x00`，Power-on RO locking possible，Permanent RO locking possible，ro lock status `not locked`。

### 20.1 结论边界

- 已验证：DF4032 身份、容量、当前 root 来源；mmc-utils 报告的 3727 个 User Area WP groups 均为 No Write Protection；Boot Area WP 寄存器为 0，RO lock 未锁定。
- 未验证：最后 4 MiB 不完整尾部 WP group 的精确保护状态；硬件实际拒绝写入的行为；本阶段是否需要设置临时 WP。
- 该结果是只读查询，没有执行任何 WP set/clear、分区或写入操作。
- 不应把“未启用 eMMC WP”解释为 eMMC 有故障；它只表示当前没有启用这些保护配置。

### 20.2 8GB 测试卡后续步骤

- 用户已明确授权：后续测试专用 8GB TF 卡现有内容可以清空并格式化。
- 64GB TF 卡是 6.12 对照系统，必须保持原样，不得格式化、分区、写入或用于实验。
- 机器只有一个 TF 卡槽。8GB 卡检查时，需先让设备从 DF4032 eMMC 的 6.1.116 系统启动，再插入/更换为 8GB TF 卡；不能依赖另一张 TF 卡同时存在。
- 插入 8GB 卡后，先只读列出所有 MMC 设备的 CID、name、容量、分区、RO 和 mount 状态，精确识别 8GB 卡；再次核对 DF4032 eMMC CID。严禁仅凭 mmcblk 编号选目标。
- 只有在 8GB 卡身份唯一确认、确认不是 DF4032、不是 64GB 对照卡，且其所有分区未挂载后，才可按用户授权执行格式化/写入。
- 本次尚未插入或格式化 8GB 卡，尚未写入 TF 镜像或启动最小系统。


## 21. 8GB TF 卡热插拔识别实测（2026-11-21）

用户在 DF4032 eMMC 启动的 Armbian 6.1.116 系统运行期间插入 8GB TF 卡，无需关机，内核成功识别新卡并自动挂载其两个分区。

### 21.1 同次输出中的设备身份

- eMMC：`/dev/mmcblk0`，TYPE=MMC，NAME=DF4032，CID=`450100444634303332010f37d8066500`，sectors=61,071,360（29.1 GiB）。
- 新插入 TF：`/dev/mmcblk1`，TYPE=SD，NAME=SU08G，CID=`035344535530384780b16ad9b700c15f`，sectors=15,523,840（约 7.4 GiB）。
- TF 分区：`/dev/mmcblk1p1` 511M ext4，自动挂载到 `/media/devmon/BOOT`；`/dev/mmcblk1p2` 6.9G btrfs，自动挂载到 `/media/devmon/ROOTFS`。
- eMMC 根系统仍位于 `/dev/mmcblk0p2`；TF 卡不是当前根文件系统。

### 21.2 已验证结论

- 已验证：当前运行的 6.1.116 Linux 能在不关机情况下检测该 8GB TF 卡，识别其 SD 类型、型号、CID、容量及分区。
- 已验证：插卡后 eMMC 仍保持原设备身份和设备节点；本次枚举为 eMMC mmcblk0、TF mmcblk1。
- 已验证：系统 automount 服务自动挂载了 TF 卡两个分区。
- 未验证：拔卡热移除行为、连续插拔稳定性、8GB 卡写入性能及新最小系统的启动能力。
- 本次仅有识别和自动挂载输出；没有执行格式化、分区、镜像写入或 eMMC 写入。

### 21.3 下一步安全步骤

- 8GB 卡现有内容已由用户明确授权可以清空，但在正式写入镜像前仍需卸载其两个自动挂载分区。
- 卸载目标必须明确限定为 `/dev/mmcblk1p1` 与 `/dev/mmcblk1p2`，且执行前重新核对 CID/name/sectors，不能只凭历史 mmcblk1 编号。
- 64GB 对照 TF 与 DF4032 eMMC 继续保持不写入。
- 只有最小系统镜像构建成功、artifact 可下载并完成内容/哈希检查后，才进入 8GB 卡写入和实机启动测试。



## 22. GitHub Actions run 44872611656：6.18.64 包缺少 Panther X2 DTB，构建输入回退至已验证 6.18.63（2026-11-21）

Run: https://github.com/njosd/panther-x2-armbian/actions/runs/44872611656

### 22.1 本次失败的准确位置

- 外层 Ophub 6.18.64 kernel package 下载成功，SHA-256 与锁定值匹配。
- 工作流正确选中了 `dtb-rockchip-6.18.64-ophub.tar.gz`，并成功解出 boot 与 Rockchip DTB 归档。
- boot archive 中找到 `vmlinuz-6.18.64-ophub`；日志的 `file` 输出确认它是原生 ARM64 Linux Image（little-endian，4K pages）。本轮不再是 Image 文件名/格式问题。
- 随后精确查找 `*/rockchip/rk3566-panther-x2.dtb` 失败，日志明确报 `rk3566-panther-x2.dtb not found in DTB archive`。
- BusyBox、initramfs、U-Boot script、hybrid TF image 均未执行；run 无 artifact。

### 22.2 与历史 6.18.63 证据交叉核对

仓库已有 6.18.63 检查 run `43543451274` 的 artifact 证据：
- 6.18.63 外层包 SHA-256：`47e3f46636594cbf212474a13bac97e1310c3ee51007dee3fa20f93d8659f1ca`。
- Rockchip DTB 包曾成功提取 Panther X2 专用 `rk3566-panther-x2.dtb`。
- 该 DTB SHA-256：`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`。
- 该二进制曾成功由 dtc 反编译，识别为 Panther X2（model/compatible）；其启动关键节点审查见本仓库 DTB 核验报告。

因此，当前能作出的结论是：6.18.64 的本次发布包未提供工作流要求的 Panther X2 DTB 路径；不能把它当作 DTB 已验证的构建输入。回退到已有包内 DTB 实物、哈希和反编译证据的 6.18.63，是为了先完成最小 RAM 启动链验证，不代表 6.18.63 是最终内核版本决定。

### 22.3 已提交的工作流调整

提交：`be4b4748182a9857e8b98d2f40bea7949d7d512f`

工作流 `.github/workflows/build-panther-x2-minimal-ram-boot.yml` 已调整：
- Kernel version 从 6.18.64 改为 6.18.63；
- 外层包 SHA-256 固定为上述已验证值；
- 新增 Panther X2 DTB SHA-256 固定值，提取后先做 SHA-256 校验，再检查 model；
- 修正候选打印的 grep 表达式，便于日志列出 Panther/RK3566 DTB。

本次只修改 GitHub Actions 工作流文件；没有对 Panther X2、eMMC、8GB TF 或 64GB 对照卡执行任何操作。

### 22.4 当前状态与下一步

- 已验证：6.18.64 kernel Image 格式正确，但本次包内目标 DTB 缺失。
- 已有历史证据：6.18.63 包含 Panther X2 DTB，且其 DTB SHA-256 已知。
- 已提交：工作流改用 6.18.63 并强制校验 DTB 二进制哈希。
- 待验证：新工作流是否通过 DTB 提取/校验，并继续完成 BusyBox、initramfs、镜像及 artifact 构建。
- 未执行：任何 TF 写入、eMMC 写保护设置、实机启动。

下一步手动运行更新后的 workflow。只有新 run 的日志和 artifact 证实构建完整，才继续检查镜像内容；仍不因构建成功自动放行 TF 写入或实机启动。



## 23. SU08G 8GB TF 卸载确认（2026-11-21）

用户执行针对两个已识别分区的普通卸载：
```sh
umount /media/devmon/BOOT
umount /media/devmon/ROOTFS
```

随后输出确认：
- `findmnt /dev/mmcblk1p1` 与 `findmnt /dev/mmcblk1p2` 均无输出，两个分区已不再挂载。
- 同一会话再次读取 `/sys/class/block/mmcblk1/device/cid`、name、size：CID=`035344535530384780b16ad9b700c15f`，name=`SU08G`，sectors=`15523840`。
- `lsblk` 显示 `/dev/mmcblk1p1`（511M ext4）和 `/dev/mmcblk1p2`（6.9G btrfs）均无挂载点，RO=0。
- `/dev/mmcblk0` 仍为约 29.1G DF4032 eMMC；`/boot` 与 `/` 分别位于 mmcblk0p1/p2。boot0/boot1 显示 RO=1。
- 当前设备列表未出现 64GB SD64G 对照卡。

结论：已再次确认 SU08G 身份及其分区卸载状态，达到后续镜像写入前置条件之一。该操作仅卸载文件系统，没有执行擦除、分区表修改、格式化或写入。用户虽已授权清空 SU08G，但仍须先取得成功构建的最小系统 artifact，并完成镜像文件、分区布局、启动文件和哈希审查；在此之前不向 TF 卡发出任何破坏性命令。eMMC 与 64GB 对照卡继续保持不写入。


## 24. 2026-11-21 最小启动系统范围与工作流修订基线

本节优先于本报告前文旧版构建描述。历史失败记录继续保留，但不能据此声称新工作流已通过。

### 24.1 阶段目标

当前首要目标是 B1：最小 RAM Linux 启动认证，不是网络测试，也不是完整系统构建。B1 只包含 Kernel、Panther X2 DTB、静态 BusyBox、最小 `/init`、MMC block-layer 只读保护及必要目录。不加入 iproute2、ethtool、DHCP、DNS、SSH、NetworkManager、systemd、udev、Docker、NPU/RKNN、Immich。B1 通过后才建立 B2/B3 网络验证层。

### 24.2 BusyBox

CI 使用一个静态 BusyBox 单体二进制，只创建 `/init` 和交互 shell 实际使用的命令链接，不安装完整 applet 链接树。当前仍以 BusyBox defconfig 编译，二进制内部可能含未暴露的 applet；CI 上传编译 applet 清单，不能将它描述为逐项裁剪后的最小 BusyBox 二进制。若后续需要进一步缩小二进制，应单独制作精简配置并验证，不得阻碍首轮启动认证。

### 24.3 工作流修订

- 将 `/init` 与 `boot.cmd` 中残留的 6.18.64 标识更正为当前固定候选 6.18.63。
- 从 initramfs 构建中移除 `mmc-wp-read-last`；它不再作为启动镜像组件或 artifact 交付。
- BusyBox 运行时只建立实际需要的命令链接，并输出编译 applet 清单。
- 启动脚本分别检查 Kernel、uInitrd、DTB 加载结果，避免把某一阶段失败误报为下一阶段成功。

### 24.4 安全门

本次修订没有解决 SPL/U-Boot 阶段可能写入 eMMC 的风险。Linux `/init` 设置 block-layer RO 发生得太晚，不能保护 pre-Linux。未取得用户对具体 eMMC Power-on WP 操作及范围的明确授权前，不得向 SU08G 写入测试镜像或启动该混合链。64GB 对照卡保持不动。

### 24.5 状态

本节记录工作流/文档修订；必须等新的 GitHub Actions run 通过、artifact 检查通过后，才能把 CI 构建标记为已验证。写卡和实机启动仍为未执行。


## 25. PREPARE-ONLY 工作流结构损坏修复（2026-11-21）

用户反馈 GitHub Actions 页面没有出现预期的 Run workflow 入口。复核仓库默认分支当前文件后，确认：

- `workflow_dispatch:` 原本存在；触发器声明不是缺失原因。
- 但 BusyBox 构建步骤在静态配置检查处被截断，导致后续编译命令漂移到文件末尾、位于 artifact 上传步骤之后；read-only initramfs 与镜像准备步骤还出现重复段落。该文件不能运行，之前关于“工作流已修订完成”的判断不成立。

本轮修复已提交：

- Workflow 修复提交：`a7064af364f9d6ce2426d1cda2b64221d695671b`
- BusyBox oldconfig 管道退出码修正：`19e91f4ccb2c6b168ab11f9e3b9352582bdc96b6`
- Initramfs devtmpfs 挂载失败改为 fail-closed：`eaa01cad7db5706eacf7ed15a737a8622d8df0bd`

修复后的静态复核：
- 保留 `workflow_dispatch`。
- 构建步骤顺序为 Checkout、Install tools、Kernel/DTB、BusyBox、initramfs、hybrid image、Artifact upload。
- BusyBox 静态配置检查、编译、静态 ELF 检查和必需 applet 检查均回到 BusyBox 步骤内。
- initramfs、镜像准备和 artifact 上传步骤各出现一次，不再有截断的静态配置命令。
- Kernel 固定为 6.18.63；未重新引入 6.18.64 或 `mmc-wp-read-last`。
- `/init` 的 devtmpfs 挂载失败现在停止启动，不再忽略错误。

**验证边界：**以上是仓库文件回读与结构检查，不等于 GitHub Actions YAML/runner 构建已通过。尚未运行 workflow、尚未写入 SU08G、尚未启动设备。即使 CI 成功，eMMC pre-Linux 写入安全门仍未解除；本 artifact 继续仅供 PREPARE-ONLY 检查。


## 26. Ophub 6.18.63 发布资产摘要核验（2026-11-21）

通过 GitHub Release API 直接读取 `ophub/kernel` 的 `kernel_stable` 发布资产元数据，找到唯一匹配资产：

- 文件：`6.18.63.tar.gz`
- 大小：124,405,384 bytes
- Release API digest：`sha256:67d2d78a570cb6128ec2c9546bd11f1ca2f32305325c146cd724d856654e51e9`
- 资产更新时间：2026-11-16T02:42:31Z

已将 Workflow 的 `KERNEL_PACKAGE_SHA256` 从错误的历史值 `47e3...` 改为发布端公布的 `67d2...`，提交 `9121c06d62bb8c197f8777bba7e0685c69fdf75a`，并回读确认。

**尚未验证：**
- 尚未成功下载该 124 MB 资产，因此未独立计算本地 SHA256。
- 尚未检查归档内部成员、boot/dtb/config 文件的实际名称与路径。
- 因此 Workflow 对内部归档文件名的假设仍需在允许执行的构建验证中确认。
- Kernel config 选项检查已写入 Workflow，但尚未对真实 config 执行。

本次只读取 Release API 元数据并修改仓库文本；未触发 Actions、未写 TF、未启动设备。


## 27. Workflow 尾部重复片段清理与回读（2026-11-21）

继续检查发现：虽然 Workflow 主体已恢复，但文件在 Artifact upload step 之后仍残留 34 行非空重复 shell 片段（从 `work/kernel-config.txt | sort ...` 开始，包含重复的 Kernel/DTB 查找与处理代码）。该尾部不属于任何合法 step，存在 YAML 结构风险。

已删除 Artifact upload 结束后的全部重复尾部，提交：
- `eec31af55ef78adb0e2806858069d8fbf79f7932`

随后重新 fetch 默认分支回读，确认：
- 文件 262 行；
- `workflow_dispatch` 存在；
- 七个步骤按预期顺序各出现一次；
- BusyBox、initramfs、image、artifact 关键步骤均没有重复；
- Kernel SHA256 为 Release API digest `67d2d78a...`；
- Kernel 配置 grep 命令完整；
- 文件在 `retention-days: 30` 后正常结束，没有多余命令。

**验证限制：**这仍然是内容回读和结构静态检查，不是 YAML parser/actionlint 通过，也不是 GitHub Actions runner 构建成功。Release tarball 仍未下载，内部成员和配置文件位置未得到实物验证。

本轮没有触发 Actions、没有写 TF、没有启动设备。


## 28. Workflow 依赖与 Artifact 完整性修正（2026-11-21）

再次回读 Workflow、`init`、`blockro.c`、`boot.cmd` 后发现两个确定的构建缺陷：

1. Artifact upload 列表包含 `work/kernel-boot-files.txt`，但 Kernel 解包步骤没有生成该文件。
2. 镜像构建调用 `partprobe`，但 apt 安装列表没有安装提供该命令的 `parted` 包。

已修复：
- 增加 Kernel boot archive 文件清单生成命令。
- 安装 `parted`，补齐 `partprobe`。
- 显式安装 `file`，避免后续 `file` 检查依赖 runner 镜像预装状态。

提交：
- 缺少 inventory / parted：`d291234f77069b556b06e959237478bb7805cc38`
- 显式 file 依赖：`a6151510fe1e568464b9e54452f4881e2592d9d3`

修复后回读确认：
- 七个 Workflow steps 顺序正确；
- kernel boot inventory 的生成与 artifact 引用都存在；
- `partprobe` 与 apt 的 `parted` 依赖匹配；
- `file` 已显式安装；
- BusyBox/initramfs/image/artifact 四个关键 step 各出现一次；
- init 的 devtmpfs fail-closed、MMC 节点遍历和 blockro 的 BLKROSET/BLKROGET 逻辑与前述设计一致；
- boot.cmd 加载 `/Image`、`/uInitrd` 和 Panther X2 DTB。

**未完成验证：**
- 仍未对 YAML 执行独立 parser/actionlint；
- 未执行 ShellCheck 或实际 runner 构建；
- 未下载并检查 6.18.63 发布 tarball 内部成员；
- 未证明 Kernel config 文件名和路径；
- 未实际验证 Kernel 所需配置；
- 未执行设备启动认证。

本轮未触发 Actions、未写 TF、未启动设备。
