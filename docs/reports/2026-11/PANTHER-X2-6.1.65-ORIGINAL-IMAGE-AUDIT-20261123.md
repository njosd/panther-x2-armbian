# Panther X2 原始 6.1.65 镜像静态审计报告

- 审计日期：2026-11-22 至 2026-11-23
- 目标设备：Panther X2 / RK3566
- 原始镜像：\`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz\`
- 审计性质：离线、只读、静态文件审计
- 状态：**Kernel 与 uInitrd 两个核心启动二进制均已完成静态身份、完整性及关键内部结构审计；实机启动仍未验证**
- 项目 A 关系：历史 6.1.65 基线资料；不改变项目 A 当前锁定的 6.18.63 源码自建 B1 路线
- 范围限制：不开展 GMAC/MDIO/PHY 故障根因调查，不制作驱动补丁；Wi-Fi/无线网络与蓝牙永久排除出项目 A

## 1. 结论摘要

本轮已完成原始镜像布局、启动配置、boot script、Panther X2 DTB 文件身份、Kernel 配置与 built-in 驱动清单、模块清单、用户空间/网络工具清单及项目范围排除项的阶段性审计。

关键结论：

1. 原始 gzip 文件的 SHA-256 和 gzip 完整性检查结果已由用户本机提供；gzip 内部原始文件名记录为 \`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img\`。
2. Kernel 配置明确启用 \`CONFIG_STMMAC_ETH=y\`、\`CONFIG_STMMAC_PLATFORM=y\`、\`CONFIG_DWMAC_ROCKCHIP=y\`，相关对象列入 \`modules.builtin\`。此前因模块文件清单未见独立 Rockchip GMAC 模块而产生的“驱动可能缺失”疑点已排除。
3. 原始 boot 配置指向 \`rockchip/rk3566-panther-x2.dtb\`；DTB 文件存在，大小与 SHA-256 已记录。
4. 原始 \`boot.scr\` 的 uImage header/data CRC 检查正确，其 payload 与 \`boot.cmd\` 正文一致。
5. rootfs/initramfs-tools manifest 中的 BusyBox helper、systemd 链接等信息，不等于真实 \`uInitrd\` cpio 内容；实际 uInitrd 尚未解包审计。

**本次并非所有文件均已完整审计。** 仍需从现有 Dropbox 阶段包提取两个关键二进制：\`vmlinuz-6.1.65-ophub\` 和 \`uInitrd-6.1.65-ophub\`。尤其 uInitrd 内部的真实 \`/init\`、早期用户空间及依赖，是完成启动资产闭包判断的必要证据。无需重新运行整个提取脚本，也无需重新上传大阶段包。

## 2. 原始输入身份与镜像布局

### 2.1 原始压缩包

- 压缩大小：892,499,345 bytes（约 851.2 MiB）
- gzip 内部记录的未压缩大小：2,969,567,232 bytes
- gzip 内部原始文件名：\`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img\`
- gzip header 时间：2023-12-07 05:18:54（Unix 时间）
- 用户本机计算的 SHA-256：\`0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea\`
- 用户报告 \`gzip -t\`：通过

gzip header 支持内部镜像文件名及 2023-12-07 构建标识，但不能单独证明上游官方发布身份。当前未取得可独立比对的上游官方 SHA-256。gzip 完整性通过只证明压缩流可完整解压，不证明内容与发布者原件一致。

### 2.2 分区布局

| 项目 | 结果 |
|---|---|
| 展开镜像大小 | 约 2.8 GiB |
| Boot 分区 | ext4，267,386,880 bytes |
| Root 分区 | ext4，2,683,305,984 bytes |
| Boot UUID | \`a5110630-ef2e-4941-9a22-15784ef687a5\` |
| Root UUID | \`ddcbfa1d-95e7-4863-97c8-ec9b7767968b\` |

以上为用户本机只读提取结果；本轮未重新计算原始镜像与展开镜像 SHA-256。

## 3. 启动配置与启动脚本

### 3.1 armbianEnv.txt

已核对的关键字段：

\`\`\`ini
fdtfile=rockchip/rk3566-panther-x2.dtb
rootdev=UUID=ddcbfa1d-95e7-4863-97c8-ec9b7767968b
rootfstype=ext4
rootflags=rw,errors=remount-ro
earlycon=on
console=both
consoleargs=console=ttyS02,1500000 console=tty0
overlay_prefix=rk3566
overlays=
user_overlays=
extraboardargs=net.ifnames=0 max_loop=128
\`\`\`

配置声明使用 Panther X2/RK3566 DTB 路径，并将 rootfs 指向独立 ext4 root 分区；这不证明目标设备实际执行过该镜像中的配置。

### 3.2 boot.cmd / boot.scr

- \`boot.cmd\`：3,310 bytes。
- \`boot.scr\`：3,382 bytes，legacy U-Boot script uImage。
- header CRC：\`0xA2C2FDFA\`，检查正确。
- data CRC：\`0xB7C261DC\`，检查正确。
- 提取 script SHA-256：\`0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a\`。
- script payload 去除 8-byte uImage header 后，与 \`boot.cmd\` 的 3,310-byte 正文一致。

启动脚本读取 \`armbianEnv.txt\`，设置 bootargs，加载 \`uInitrd\`、\`Image\` 和 \`\${prefix}dtb/\${fdtfile}\`，处理可选 overlays/fixups，最后执行 \`booti\`。

\`extlinux/extlinux.conf\` 不存在；只有 \`extlinux.conf.bak\`，不能将备份配置描述为实际生效配置。

### 3.3 符号链接提取缺口

- \`Image\` → \`vmlinuz-6.1.65-ophub\`
- \`uInitrd\` → \`uInitrd-6.1.65-ophub\`
- \`dtb-6.1.65-ophub\` → \`dtb\`

0.3.4 提取报告将上述 3 个符号链接记为 \`symlink path collision\`。这是提取器处理符号链接的缺陷，不是文件系统损坏证据；但必须核验目标文件本身，才能关闭缺口。

## 4. Kernel 配置与 built-in 驱动审计

用户从现有阶段包提取并上传 \`config-6.1.65-ophub\` 与 \`modules.builtin\`，组成 \`kernel-config-evidence.zip\`。已读取两份文件。

关键配置：

| 配置 | 值 | 静态含义 |
|---|---:|---|
| \`CONFIG_STMMAC_ETH\` | \`y\` | STMMAC 主驱动编译进内核 |
| \`CONFIG_STMMAC_PLATFORM\` | \`y\` | STMMAC 平台驱动编译进内核 |
| \`CONFIG_DWMAC_ROCKCHIP\` | \`y\` | Rockchip DWMAC 支持编译进内核 |
| \`CONFIG_DWMAC_GENERIC\` | \`y\` | Generic DWMAC 支持编译进内核 |
| \`CONFIG_PHYLINK\` | \`y\` | PHYLINK 编译进内核 |
| \`CONFIG_PHYLIB\` | \`y\` | PHYLIB 编译进内核 |
| \`CONFIG_ROCKCHIP_PHY\` | \`y\` | Rockchip PHY 驱动编译进内核 |
| \`CONFIG_MDIO_BUS\` | \`y\` | MDIO bus 支持编译进内核 |
| \`CONFIG_OF_MDIO\` | \`y\` | OF/MDIO 支持编译进内核 |
| \`CONFIG_BLK_DEV_INITRD\` | \`y\` | 内核支持 initrd/initramfs |
| \`CONFIG_RD_GZIP\` | \`y\` | 支持 gzip initramfs/initrd 解压 |
| \`CONFIG_DEVTMPFS\` | \`y\` | devtmpfs 支持编译进内核 |
| \`CONFIG_IKCONFIG\` | \`y\` | 内核配置归档支持启用 |
| \`CONFIG_IKCONFIG_PROC\` | \`y\` | 可通过 proc 暴露内核配置 |

\`modules.builtin\` 明确列出：

\`\`\`text
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac.ko
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac-platform.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-generic.ko
kernel/drivers/net/phy/rockchip.ko
kernel/drivers/net/phy/phylink.ko
kernel/drivers/net/phy/libphy.ko
kernel/drivers/net/phy/realtek.ko
kernel/drivers/net/mdio/of_mdio.ko
\`\`\`

这些路径位于 \`modules.builtin\`，表示相应对象编译进内核，不是运行时必须加载的独立模块。

**结论：** 6.1.65 内核配置包含 Rockchip DWMAC/STMMAC 及相关 PHY/MDIO 支持。此前从 06 模块文件清单未发现独立 Rockchip DWMAC/STMMAC \`.ko\` 而产生的驱动缺失疑点，已由 config 与 built-in 清单排除。此结论只描述构建配置，不代表 Panther X2 实机启动、驱动 probe、链路或网络功能通过。

## 5. Panther X2 DTB 文件

- 文件：\`dtb/rockchip/rk3566-panther-x2.dtb\`
- 大小：111,351 bytes
- SHA-256：\`d03ec12df0d69bfa0f0ab5ac462a8fffd8ae5d1c512032ff9468df89248d289f\`
- 本地启动分区 inode：50；regular file，0644
- 文件系统记录时间：2023-12-07 13:18:46

镜像启动配置引用该路径，独立 DTB 阶段包中也存在同尺寸文件。存在性与哈希已记录；这不等于已证明 DTB 与目标设备硬件修订完全匹配，也不等于实机加载成功。

## 6. 真实 uInitrd 二进制与内部结构审计（2026-11-23）

本节依据用户上传到当前对话的真实文件 `uInitrd-6.1.65-ophub` 进行字节级检查；不是依据 05 manifest 推断。原始 Dropbox 文件未被修改。

### 6.1 文件身份与 U-Boot legacy uImage

| 项目 | 实测结果 |
|---|---|
| 文件大小 | 16,865,725 bytes |
| SHA-256 | `b15a440caff522227c1b792271d5bf50508edf1c1bee33396430b8aca18342a0` |
| uImage magic | `0x27051956` |
| Header 长度 | 64 bytes |
| Header CRC（存储/重算） | `0x051694A1` / 一致 |
| Payload 长度 | 16,865,661 bytes |
| Data CRC（存储/重算） | `0x9B275961` / 一致 |
| uImage 时间 | 2023-12-03 10:19:56 UTC |
| Name | `uInitrd` |
| OS / Arch / Type / Compression | Linux / ARM64 / RAMDisk / gzip |
| Load / Entry | 0 / 0 |

uImage header CRC 是将 header CRC 字段清零后重新计算；data CRC 对完整 16,865,661-byte payload 独立计算。两者均与 header 内记录一致。

### 6.2 gzip 与 cpio 完整性

| 项目 | 实测结果 |
|---|---|
| gzip header 文件名 | `mkinitramfs-MAIN_jvPOVk` |
| gzip header 时间 | 2023-12-03 10:19:49 UTC |
| 解压后长度 | 49,225,728 bytes |
| gzip footer CRC32（存储/重算） | `0x8B846DEE` / 一致 |
| gzip ISIZE（存储/实测） | 49,225,728 / 一致 |
| cpio 格式 | `newc`（magic `070701`） |
| 实际条目数（不含 trailer） | 931 |
| 普通文件 / 目录 / 符号链接 | 704 / 166 / 61 |
| 结束标记 | `TRAILER!!!` 存在 |
| 归档尾部填充 | 336 bytes，均为零 |
| 相对符号链接 | 56 条，未发现悬空目标 |

因此，当前上传文件的 uImage、gzip 和 cpio 三层结构均通过静态完整性检查；没有发现截断或 CRC 不匹配。

### 6.3 init 入口与 rootfs 交接逻辑

- cpio 中存在根目录 `/init`，普通文件，mode `0755`，大小 6,556 bytes。
- `/init` 是 shell 脚本，shebang 为 `#!/bin/sh`。
- 启动早期创建/挂载 `/dev`、`/proc`、`/sys`、`/run` 等运行环境。
- 读取内核命令行中的 `root=`、`rootfstype=`、`rootflags=`、`rootdelay=` 等参数。
- 默认 `BOOT=local`，加载 `/scripts/local` 和 `/scripts/nfs`；本镜像启动参数指定本地 ext4 root UUID。
- `scripts/local` 中的 `local_mount_root()` 调用设备解析/等待逻辑、文件系统类型识别与 mount，将真实根分区挂载到 `/root`。
- 随后执行 `run-init`，把控制权交给真实 rootfs 中的 `/sbin/init`；不是在 initramfs 内启动一个长期独立用户空间。

该流程直接证明：此 uInitrd 的设计职责是发现并挂载真实 rootfs，然后切换根目录和 PID 1；它不是 B1 所要求的“脱离持久化存储系统独立运行”的最小 initramfs。

### 6.4 发行版与 initramfs-tools 配置

真实 cpio 内的 `etc/os-release` 声明：

- `PRETTY_NAME="Armbian 23.11.0-trunk bookworm"`
- Debian GNU/Linux 12 / bookworm
- `ID=debian`

`conf/arch.conf`：`DPKG_ARCH=arm64`。

`conf/initramfs.conf` 的关键配置：

| 配置 | 值 |
|---|---|
| `MODULES` | `most` |
| `BUSYBOX` | `auto` |
| `KEYMAP` | `n` |
| `NFSROOT` | `auto` |
| `FSTYPE` | `auto` |
| `RESUME` | `none` |
| `COMPRESS` | `gzip` |

虽然配置写有 `BUSYBOX=auto`，但实际 cpio 中未发现 BusyBox 二进制，也未发现 `dash` 或 `bash`。实际 `/bin/sh`（归档路径 `usr/bin/sh`）是 AArch64 klibc ELF；`run-init` 和 `mount` 也为 klibc 工具。不能把 05 rootfs manifest 中的 BusyBox helper 当成真实 uInitrd 中存在 BusyBox 的证据。

### 6.5 用户空间、udev 与动态链接

真实 initramfs 包含 klibc 启动工具、kmod、udevadm、blkid、btrfs、ntfs-3g、dmsetup、Plymouth、文件系统/设备发现工具和多组共享库。

已抽查 ELF：
- `usr/bin/sh`、`usr/bin/run-init`、`usr/bin/mount` 为 AArch64 klibc 程序；使用归档内的 `klibc-*.so` 解释器，未显示普通 ELF `NEEDED` 共享库项。
- `usr/bin/kmod`、`usr/bin/udevadm`、`usr/sbin/blkid` 为 AArch64 glibc 动态链接程序；其 ELF interpreter 和直接依赖的关键库在归档中可找到。
- 已检查的直接库包括 `libc.so.6`、`libkmod.so.2`、`libacl.so.1`、`libblkid.so.1`、`libcap.so.2`、`libselinux.so.1`、`libzstd.so.1`、`liblzma.so.5`、`libcrypto.so.3`。

udev 相关脚本：
- `scripts/init-top/udev` 启动 `/lib/systemd/systemd-udevd`，执行 udev subsystem/device trigger 和 settle。
- 归档中的 `usr/lib/systemd/systemd-udevd` 是指向 `../../bin/udevadm` 的符号链接；实际使用的是 udevadm 二进制的 udevd 入口。
- `scripts/init-bottom/udev` 停止 udevd，并将 initramfs 的 `/dev` 移交到真实 rootfs。

这里存在 systemd 项目的 udev 组件，但没有证据表明 initramfs 以 systemd 作为 PID 1；实际 `/init` 是 initramfs-tools shell 脚本，最终交接给真实 rootfs 的 `/sbin/init`。直接依赖已抽查，尚未对所有动态 ELF 做完整递归依赖闭包审计。

### 6.6 内核模块和范围边界

- cpio 中包含 `usr/lib/modules/6.1.65-ophub`，共 386 个 `.ko` 文件，合计 15,764,232 bytes，并包含 modules.dep、modules.alias、modules.builtin 等元数据。
- 未发现 `drivers/net/wireless` 或 `drivers/bluetooth` 模块目录/模块成员。
- 未发现 STMMAC 独立模块文件；第 4 节已确认该驱动族在对应 Kernel 配置中为 built-in。
- udev rules 中存在 `10-wifi-disable-powermanagement.rules` 文件；单个规则文件不等于无线驱动或无线功能已被装入/启用。
- 该 initramfs 还包含大量通用存储、USB、网络和其他模块及用户空间工具，不是 B1 的无模块最小基线。

### 6.7 静态结论与限制

**已证实：** uInitrd 文件身份与三层完整性检查通过；真实 cpio 的 `/init` 会挂载指定 rootfs，并通过 `run-init` 交接到 rootfs 的 `/sbin/init`；其实现属于 Armbian/Debian initramfs-tools 风格；含 klibc、udev、动态用户空间工具和 386 个模块。

**不应据此声称：** Panther X2 实机已经成功执行此 initramfs；所有动态库递归依赖均已闭包；rootfs 或所有模块均与目标硬件实测兼容；该 initramfs 能脱离真实 rootfs 独立运行。

**对 B1 的参考价值：** 可参考早期挂载顺序、root 参数解析、设备等待与 rootfs handoff 的实现；不能把该 uInitrd 直接当作 B1 独立 initramfs，也不应把其发行版用户空间、udev、Plymouth、模块集合或 rootfs 依赖带入 B1。


### 6.8 Kernel 实际二进制身份与内嵌配置（2026-11-23）

本节依据用户上传到当前对话的真实文件 `vmlinuz-6.1.65-ophub` 进行直接字节检查；不是只依据文件名、manifest 或独立 config 文件推断。

| 项目 | 实测结果 |
|---|---|
| 文件大小 | 33,858,048 bytes |
| SHA-256 | `d11b0c781a8ac0ffc153ff60e1b1bd88a926afd8f810dd13896d2f0ea16e8bef` |
| 文件识别 | Linux kernel ARM64 boot executable Image |
| ARM64 Image magic | `ARMd`，偏移 `0x38` |
| ARM64 text_offset | `0x0` |
| ARM64 image_size 字段 | `0x2130000` |
| ARM64 flags 字段 | `0xA` |
| EFI/PE signature | `PE\0\0`，偏移 `0x40` |
| PE Machine | `0xAA64`（AArch64） |
| PE sections | `.text`、`.data` |
| 内核 release | `6.1.65-ophub` |

文件大小与此前用户从 03 阶段包提取并记录的 33,858,048 bytes 完全一致；SHA-256 也与此前本机记录完全一致。文件同时包含 ARM64 Linux Image 头与 AArch64 EFI/PE stub 结构。PE COFF timestamp 字段为 0，不能从该字段推导构建时间。

从内核字符串中读取到的完整版本/构建标识：

```text
Linux version 6.1.65-ophub (root@fv-az841-991)
(aarch64-none-linux-gnu-gcc (Arm GNU Toolchain 13.2.rel1 (Build arm-13.7)) 13.2.1 20231009,
GNU ld (Arm GNU Toolchain 13.2.rel1 (Build arm-13.7)) 2.41.0.20231009)
#1 SMP Sun Dec  3 05:14:23 EST 2023
```

这说明该二进制记录的编译用户/主机字符串为 `root@fv-az841-991`，编译器为 Arm GNU Toolchain 13.2.1，链接器为 GNU ld 2.41.0.20231009，内核编译时间字符串为 2023-12-03 05:14:23 EST（10:14:23 UTC）。主机名形态与云端 runner 环境相符，但单凭字符串不能证明具体 GitHub Actions run、runner 身份或构建来源。

#### 内嵌 IKCONFIG

内核中存在 `IKCFG_ST` / `IKCFG_ED` 标记。提取其间 gzip 数据并解压成功，得到 235,886 bytes 的完整文本 Kernel config。关键字段如下：

| 配置 | 内嵌值 |
|---|---|
| `CONFIG_IKCONFIG` | `y` |
| `CONFIG_IKCONFIG_PROC` | `y` |
| `CONFIG_STMMAC_ETH` | `y` |
| `CONFIG_STMMAC_PLATFORM` | `y` |
| `CONFIG_DWMAC_ROCKCHIP` | `y` |
| `CONFIG_DWMAC_GENERIC` | `y` |
| `CONFIG_PHYLINK` | `y` |
| `CONFIG_PHYLIB` | `y` |
| `CONFIG_ROCKCHIP_PHY` | `y` |
| `CONFIG_MDIO_BUS` | `y` |
| `CONFIG_OF_MDIO` | `y` |
| `CONFIG_BLK_DEV_INITRD` | `y` |
| `CONFIG_INITRAMFS_SOURCE` | 空字符串 |
| `CONFIG_RD_GZIP` / `CONFIG_RD_XZ` / `CONFIG_RD_ZSTD` | 均为 `y` |
| `CONFIG_DEVTMPFS` | `y` |
| `CONFIG_NET` | `y` |
| `CONFIG_PACKET` / `CONFIG_UNIX` / `CONFIG_INET` | 均为 `y` |
| `CONFIG_MODULES` | `y` |

内嵌配置确认此前从 `config-6.1.65-ophub` 和 `modules.builtin` 得出的关键构建配置：STMMAC/Rockchip DWMAC、PHYLINK、PHYLIB、Rockchip PHY 与 OF/MDIO 支持均编译进内核。该结果是实际 Kernel 二进制自身携带的配置证据，强于仅凭独立配置文件推断。它仍然只证明编译配置，不证明驱动在 Panther X2 实机 probe 或工作成功。

#### 与 uInitrd 的构建时间关系

Kernel banner 记录的编译时间为 2023-12-03 10:14:23 UTC；uInitrd uImage header 时间为 2023-12-03 10:19:56 UTC，gzip header 时间为 10:19:49 UTC。时间顺序相隔约 5 分钟，与先生成 Kernel、随后生成 initramfs 的构建顺序相容。时间相近不能单独证明两者由同一个 workflow run 生成。

#### 静态结论与限制

**已证实：** Kernel 文件身份、大小和 SHA-256 与本机提取记录一致；ARM64 Image 与 AArch64 PE/EFI 头可识别；内核版本、编译器/链接器标识和编译时间可从二进制读取；内嵌 IKCONFIG 成功解压，并确认关键配置。

**不应据此声称：** Kernel 已在 Panther X2 实机成功启动；EFI stub 或 U-Boot 启动路径已实测；设备树匹配、驱动 probe、PHY 链路或网络功能通过；构建主机字符串足以确定某个 GitHub Actions run。


## 7. Kernel 与模块清单

- 03 Kernel manifest：21 条数据项；\`vmlinuz-6.1.65-ophub\` 大小 33,858,048 bytes；\`Image\` 是指向它的符号链接。
- 06 modules manifest：4,560 条数据项，其中 4,547 个普通文件、13 个符号链接。
- 存在 \`/lib/modules\` 与 \`/usr/lib/modules\` 两套重复目录布局及 modules.dep、modules.alias、modules.builtin 等元数据。
- 可见 Realtek \`r8125.ko\`、\`r8168.ko\`。
- 未发现独立 Rockchip DWMAC/STMMAC 模块文件，但第 4 节已确认其为 built-in。

对于 B1，当前路线明确不启用 Kernel modules、不打包 \`/lib/modules\`，因此无需把 202 MiB 模块包整体复制进新系统。模块包作为原始镜像证据保留。

## 8. 网络工具与项目范围隔离

07 network-userspace 包清单包含 \`ip\`、\`bridge\`、\`tc\`、\`ethtool\`、\`dhclient\`、\`ping\`、\`ss\`、\`curl\`、\`wget\`。这只确认文件存在，不代表其动态库依赖、静态属性或独立 initramfs 可运行性已验证。项目 A B1 不预置网络工具；后续阶段达到验收门槛后再逐项引入。

08 project-scope-exclusions 索引共 1,865 项，但自动分类存在误判（例如 \`logrotate.d/btmp\` 被宽泛规则纳入），不能视为精确无线/蓝牙组件清单。项目 A 已将 Wi-Fi/无线网络与蓝牙永久排除，不继续审计或测试其功能。

## 9. 提取器失败项与可信度限制

用户本机运行 \`panther_x2_audit_pack.py 0.3.4\` 的报告：

- Source entries：22,548
- Failed files：16
- Special objects not materialized：0
- Wireless/BT inventory entries：1,865

16 条失败包括：3 条启动分区符号链接（\`Image\`、\`uInitrd\`、\`dtb-6.1.65-ophub\`）；5 条 module 提取失败记录（\`xt_dscp.ko\` 因重复路径出现两条）；8 个 Linux netfilter 头文件。

汇总中的 “special objects not materialized: 0” 与 symlink 失败记录不一致，不能据此声称提取无损。symlink collision 不等于源镜像损坏；模块和头文件失败项是否重要，应按实际依赖判断。当前 B1 启动资产的两个目标二进制仍需单独提取和校验。

## 10. Dropbox 证据保留清单

用户明确要求：**本项目结束前，现有 6.1.65 原始镜像与阶段审计文件继续保留在 Dropbox，不删除、不移动、不覆盖。** Git 只保存报告和必要的小型文本证据，不将 851 MiB 原始镜像或 202 MiB 模块包复制进仓库。

### 10.1 原始镜像

| 文件 | Dropbox file ID | 大小 |
|---|---|---:|
| \`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz\` | \`id:9qHOnx-HLYoAAAAAAAAABw\` | 892,499,345 bytes |

### 10.2 八个阶段包

| 阶段包 | Dropbox file ID | 体积 | 用户提取报告 SHA-256 |
|---|---|---:|---|
| \`01-image-layout.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAACw\` | 1.0 MiB | \`5f7962adff81f3b2b129dafc5ae270f58dfa946588c88d836232f6a06f1129e0\` |
| \`02-boot-chain.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAACg\` | 11.6 KiB | \`6de2ed2c8d72ab51258aae900b972a3cea454f254fba62144271f75d219175c3\` |
| \`03-kernel.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADQ\` | 13.3 MiB | \`02320ca87cf9f87a296d6de7c703672b9c0e81d02f208a8b7a621bc0db8c86b7\` |
| \`04-device-tree.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADA\` | 2.2 MiB | \`b09451c53393353de55cbd4d7074eca593fd64a21ff9bc88cab223a9cdd6f3af\` |
| \`05-initramfs-userspace.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADg\` | 35.1 MiB | \`9dd82ac5d97e97c4fc7a1746423412b5e627343f6854c071092174fcdb1c6a08\` |
| \`06-modules-dependencies.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADw\` | 202.1 MiB | \`a65fe3442741970f2a094c5853ef05e1a16db30ebd3fd77953e07621d24eab86\` |
| \`07-network-userspace.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAAEA\` | 3.7 MiB | \`66d300a64b4987220709833b174190d8f508dc2d4d1bf1c20d0bbea9ea43877\` |
| \`08-project-scope-exclusions.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAAEQ\` | 18.8 KiB | \`b9d0093273fec3a6124811652fb4d34025718a5a450f4967e8d6d6076352d77\` |

上述 SHA-256 来自 0.3.4 用户本机提取报告，本轮未重新逐包复算。

### 10.3 附加证据

- \`FINAL-REPORT.txt\`：\`id:9qHOnx-HLYoAAAAAAAAACA\`
- \`UPLOAD-SHA256SUMS.txt\`：\`id:9qHOnx-HLYoAAAAAAAAACQ\`
- \`kernel-config-evidence.zip\`：\`id:9qHOnx-HLYoAAAAAAAAAFQ\`，包含 \`config-6.1.65-ophub\` 与 \`modules.builtin\`
- 单独上传的 manifest：\`03-kernel-MANIFEST.tsv\`、\`05-initramfs-userspace-MANIFEST.tsv\`、\`06-modules-dependencies-MANIFEST.tsv\`

## 11. 尚需补齐的审计项与完成条件

### 11.1 已完成：真实 uInitrd

已从现有 `05-initramfs-userspace.tar.gz` 的精确成员提取并上传真实 `uInitrd-6.1.65-ophub`。文件大小和 SHA-256 与 manifest 一致；uImage header/data CRC、gzip CRC/ISIZE、cpio newc 结构均已独立验证。详细结果见第 6 节。

Dropbox 中的原始 uInitrd 与 05 阶段包保持不动。

### 11.2 已完成：Kernel 实际二进制

用户已将 `vmlinuz-6.1.65-ophub` 作为当前对话附件提供。已直接复算文件大小和 SHA-256，结果与此前本机提取记录完全一致；已解析 ARM64 Image/EFI PE 头、内核 release、编译器/链接器标识、编译时间，并从内嵌 `IKCONFIG` 区段提取完整 235,886-byte 配置。关键配置与此前独立 config 证据相符，详见第 6.8 节。

无需重新提取或上传 03 阶段包。Dropbox 原始 Kernel 与 03 阶段包保持不动。

### 11.3 暂不扩大范围

- 不重新解压完整 202 MiB `06-modules-dependencies.tar.gz`。
- 07 网络工具的完整依赖审计不属于当前 uInitrd 闭包任务，也不进入 B1。
- 不追查无线/蓝牙功能；项目 A 永久排除。
- 不因本报告内容转入 GMAC/MDIO/PHY 故障排查或制作补丁。

### 11.4 完成定义

本轮已完成 6.1.65 真实 uInitrd 与 Kernel 两个核心启动二进制的静态身份及关键内部结构审计：uInitrd 的 uImage/gzip/cpio、`/init` 与 rootfs handoff 已检查；Kernel 的 ARM64 Image/PE 头、版本/build 字符串与内嵌 IKCONFIG 已检查。两项核心启动资产的静态审计闭合。

即使两项静态检查全部完成，也不等于 Panther X2 实机启动成功、驱动 probe 成功或网络功能通过。实机行为必须单独标注为未验证，除非有实际启动日志/测试证据。

## 12. 对项目 A B1 的结论

- 6.1.65 是历史原始镜像审计对象，不是项目 A 当前 B1 Kernel 构建目标。
- B1 仍按仓库既定方案，从锁定的 Linux 6.18.63 源码 commit 自建 Kernel、clean-test DTB、gzip initramfs 和静态 BusyBox。
- 不直接复用 6.1.65 发行版 Kernel、uInitrd、rootfs、模块或网络用户空间作为 B1 组件。
- 6.1.65 的网络/STMMAC/DWMAC 配置不符合 B1 的 \`CONFIG_NET=n\`、无 Ethernet driver、无 modules 的干净基线要求。
- 不因 6.1.65 启用了相关驱动而开展 GMAC 根因调查或制作补丁。
- Wi-Fi/无线网络、蓝牙及其控制器/驱动/固件/协议/用户空间继续永久排除。

## 13. 归档纪律

- 原始镜像、8 个阶段包和附加证据文件继续保留在 Dropbox，直至用户明确宣布项目结束或另行要求。
- 不删除、不移动、不覆盖 Dropbox 原始包和阶段包。
- Git 仓库只保存本报告及必要的小型文本证据，不加入大型原始镜像或 modules 压缩包。
- 后续提取只针对第 11 节明确列出的文件，不重复已完成的镜像布局、boot script CRC、DTB 文件存在性和 Kernel 配置核验。
- 结论必须区分用户本机报告、已读取文件静态证据、待验证事项和实机运行证据。

## 14. 镜像构建来源、上游工作流与自定义代码审计（2026-11-23 修订）

本节修正前一版的来源推断：不能把 `lintao1890/panther-x2-armbian` 当成 2023-12-07 镜像的构建仓库。GitHub 仓库元数据显示，该仓库是 `ophub/amlogic-s9xxx-armbian` 的 fork，创建于 2024-01-21，晚于原始镜像时间。因此它只能作为后续 fork 快照/交叉比较样本，不能是 2023-12-07 构建当时的在线仓库身份。

### 14.1 镜像自身保留的构建元数据

设备遗留的 `/etc/ophub-release` 字段记录：

- `BUILD_REPOSITORY=github.com/armbian/build`
- `REBUILD_REPOSITORY=github.com/ophub/amlogic-s9xxx-armbian`
- `KERNEL_REPO=ophub/kernel`
- `KERNEL_TAGS=stable`
- `CONTRIBUTORS=tdleiyao`
- `BUILDER_NAME=ophub`
- `PACKAGED_DATE=2023-12-07`
- `MODEL_NAME=Panther-X2`、`SOC=rk3566`

这些元数据指向 Armbian 基础构建、Ophub Rebuild 项目和 Ophub kernel 发布资产。特别是 `REBUILD_REPOSITORY` 明确指向 Ophub 官方仓库，而不是 lintao1890 的 fork。

`BUILDER_NAME=ophub` 是镜像签名/标识字段，本身不能证明每个二进制均由 Ophub 作者亲自编写，也不能证明镜像由某台个人机器本地打包。

### 14.2 构建时间点的 Ophub 上游提交

镜像 gzip header 时间为 2023-12-07 05:18:54 UTC。与该时点相邻的 `ophub/amlogic-s9xxx-armbian` 提交：

- `c2fdbfa0be9d8e4ab3704c33525adae53bca681e`
- 提交时间：2023-12-07 03:28:08 UTC
- 提交说明：`Adding kernel directory check`

同一提交也出现在后来 fork 的历史中。时间关系与镜像的 `PACKAGED_DATE` 相符，但仍缺原始 GitHub Actions run ID、workflow dispatch inputs、实际 checkout SHA 和产物记录，故它是强时间点源码候选，不是单独的构建证明。

### 14.3 当时工作流呈现的构建方式

该时间点的 `.github/workflows/build-armbian.yml` 工作流内容显示：

1. 在 GitHub Actions runner 上 checkout `ophub/amlogic-s9xxx-armbian`；
2. clone Armbian 官方 `armbian/build` 的 `main` 分支；
3. 使用 `RELEASE=jammy BOARD=odroidn2 BRANCH=current` 等参数先生成通用 Jammy 基础镜像；
4. 调用 `ophub/amlogic-s9xxx-armbian@main` 的 Rebuild Armbian action；
5. 通过 GitHub Release action 上传重构后的镜像。

这说明公开构建流程设计为 **GitHub Actions 自动构建**，不是要求维护者在个人电脑上手工编译、打包。由于 `armbian/build@main` 与 Ophub action 都使用浮动分支引用，精确依赖提交仍需历史 run/日志才能锁定。

### 14.4 Panther X2 专用配置与贡献者代码

构建时点的 Ophub `model_database.conf` 已有 Panther X2 记录，字段包括 model ID `r301`、SoC `rk3566`、DTB `rk3566-panther-x2.dtb`、kernel tag family `6.1.y`、board `panther-x2`、contributor `tdleiyao`、boot config `armbianEnv.txt`。

这说明 Panther X2 支持并非由基础 Armbian Odroid N2 配置自动产生，而是通过 Ophub 项目中的板级记录和 Panther X2 专用文件集成。贡献者字段表明存在板级支持贡献，但不能仅凭该字段认定贡献者自行编写了全部相关代码，必须看具体提交和文件 diff。

### 14.5 后续 fork 与上游的文件级比较

对 `lintao1890/panther-x2-armbian@31b1b96f258a6d66ecaf8a719145860b533100f6` 与 `ophub/amlogic-s9xxx-armbian@c2fdbfa0be9d8e4ab3704c33525adae53bca681e` 的 Git tree 做了逐项比较：

- fork 的仓库创建时间为 2024-01-21，晚于镜像时间；
- 两边共有的 tracked blob 文件中，没有发现内容不同的文件；
- fork 比对应上游快照多 6 个文件：4 个 kernel config、1 个 OpenWrt build dependency 脚本、1 个 x86_64 loader symlink/文件；
- `.github/workflows/build-armbian.yml`、`rebuild`、Panther X2 `model_database.conf`、Panther X2 `armbianEnv.txt`、`armbian_rootfs.sh`、`armbian_compile_kernel_script.sh` 均与对应上游快照逐字节相同。

因此目前没有证据表明这个后续 fork 在上述构建关键文件中加入了个人改写。反而，已检查的内容与 Ophub 上游快照一致。额外 6 个文件的存在本身不证明它们参与了这次镜像构建；还需按 workflow 调用关系确认是否会被执行。

### 14.6 是否存在个人编写代码、是否本地打包：当前判断

- **个人电脑本地打包：没有证据支持。** 公开 workflow 是 GitHub Actions 自动化流程，镜像元数据也指向 Ophub Rebuild 仓库。
- **个人 fork 是 2023-12-07 构建源：排除。** 当前可核验的 lintao1890 fork 创建于 2024-01-21，晚于镜像。
- **个人贡献者代码：可能存在板级贡献，但不能泛化。** Panther X2 的 model database、专用 boot environment、DTB 等需追踪引入提交；当前尚无证据显示它们包含私下未公开的构建后补丁。
- **构建是否完全可复现：尚不能确认。** Armbian build、Ophub Rebuild action、kernel release、U-Boot 和 firmware 部分依赖浮动 `main` 或发布标签；缺原始 Actions run 与具体 inputs。

### 14.7 下一轮必须审计的代码范围

1. 取得 2023-12-07 附近 Ophub Actions workflow run 及其 inputs、checkout SHA、日志和上传产物记录；
2. 追踪 Panther X2 的 model database 行、Panther 专用 boot files、DTS/DTB 及相关文件最初由哪个提交引入、作者是谁、修改内容是什么；
3. 锁定当时 `ophub/amlogic-s9xxx-armbian@main`、`armbian/build@main`、`ophub/kernel`、`ophub/u-boot@main`、`ophub/firmware@main` 的实际 commit/tag；
4. 对实际生成的 Kernel、DTB、uInitrd 与阶段包中的二进制做哈希/构建指纹比对。

审计原则：不把贡献者身份等同于私人定制，也不把上游仓库归属等同于所有组件均为上游原生。只有定位到具体提交、代码差异和实际构建调用关系后，才判断自定义代码是否影响 Kernel、DTB、initramfs、rootfs、bootloader 或网络行为。
