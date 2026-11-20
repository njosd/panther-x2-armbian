# P1 启动链与 initramfs 只读审计进展（2026-11-20）

- 主线：PANTHER-X2-MINIMAL-SYSTEM-MAIN-ROADMAP-P1-P8-20261120.md
- 阶段：P1
- 本报告性质：只读证据归并；P1 尚未验收
- 设备操作：无；未安装、未构建、未写 TF/eMMC、未启动实验系统

## 1. 本轮范围

本轮只核对已有仓库记录、UART 日志、已归档 Actions Artifact 和公开源码配置快照，回答：

1. 6.12.81 是否能接收并解包 gzip initramfs；
2. 当前 U-Boot 到底如何从 TF 卡加载启动文件；
3. 新 8GB TF 卡若沿用当前启动链，需要哪些启动阶段资产；
4. 6.1.116 正常基线与 6.12.81 的启动资产能否在后续形成受控对照。

未触碰 Panther X2 当前系统或任何存储介质。

## 2. 6.12.81 initramfs 支持：运行时证据已成立

### 2.1 实际内核日志（直接实机证据）

仓库原始 UART 记录 evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt 显示：

- U-Boot 将 uInitrd 识别为 AArch64 Linux RAMDisk Image（gzip compressed）；
- initrd payload 大小：19,905,448 bytes；
- U-Boot checksum 验证通过；
- Linux 启动后出现：
  - Trying to unpack rootfs image as initramfs...
  - Freeing initrd memory: 19432K

这两条 Linux 日志是本项最重要的直接证据：实际运行的 6.12.81-rk35xx-ophub 内核成功识别并解包了传入的 initramfs。

因此，使用 gzip 压缩的 cpio initramfs，并通过现有 legacy uInitrd 包装路径交给内核，在技术路径上已有实机先例。后续最小 initramfs 不需要另造一套内核启动机制。

### 2.2 配置快照交叉核对（不是最终二进制 .config）

Ophub 官方 6.12.81 构建 run 对应的 workflow HEAD：
- run：43405957386
- workflow HEAD：f8925391bb2ba2634bb8ca55da39e1a2f4029ffe
- 当时默认配置路径：kernel-config/release/rk35xx/config-6.12

该 HEAD 对应的配置快照 Git blob：
- SHA-1：966f4b6ac7c0ad59179d6ae272423500601fab07

配置中包含：
- CONFIG_BLK_DEV_INITRD=y
- CONFIG_RD_GZIP=y
- CONFIG_RD_BZIP2=y
- CONFIG_RD_LZMA=y
- CONFIG_RD_XZ=y
- CONFIG_RD_LZO=y
- CONFIG_RD_LZ4=y
- CONFIG_RD_ZSTD=y
- CONFIG_DEVTMPFS=y
- CONFIG_DEVTMPFS_MOUNT=y
- CONFIG_PROC_FS=y
- CONFIG_SYSFS=y
- CONFIG_TMPFS=y

后续配置快照 c23196e10d7702ee2906de4a05421d8971fb2717 的 blob SHA-1 为 dee127c6c644f38426eeb28000d73536084d34a3，上述 initramfs / gzip / devtmpfs / proc / sysfs 选项相同。

**证据限制：** 官方 workflow run 的全部 dispatch inputs 未公开，因此无法直接证明最终发布内核 .config 与上述默认配置快照逐字节一致。这里的配置是构建时默认路径的高置信度参考；实际内核已解包 initramfs 的 UART 日志才是运行能力的直接证明。

### 2.3 现有 6.12.81 启动文件身份（实机记录）

依据 GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md 和 UART 原始记录：

| 资产 | 实机记录 | SHA-256 / 说明 |
|---|---:|---|
| U-Boot script boot.scr | 3382 bytes | 0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a |
| boot.cmd | 约 3.3 KiB | 4896dde2b99bebbb34b2ed2f837f30fa1a5b3ad14b80dd2da391effa94d37d0a |
| Kernel Image（文件名 vmlinuz-6.12.81-rk35xx-ophub） | 44,311,040 bytes（UART 实际读取） | f3164d866f075e01472ed04ba380535a1d5dfcf1b622f10484368a3a5543bb4c |
| uInitrd-6.12.81-rk35xx-ophub | legacy image；gzip RAMDisk payload 19,905,448 bytes | a6091faeb544866f4f4af296089fb9106870c5f129ae039c33a5b86f700246c7 |
| rk3566-panther-x2.dtb | 167,306 bytes（UART 实际读取） | 00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185 |

注意：
- uInitrd 是 legacy U-Boot RAMDisk image 外壳，内部 payload 为 gzip 压缩 initramfs。
- 当前脚本从启动设备读取 armbianEnv.txt，再加载 uInitrd、Image、dtb/<prefix>/<fdtfile>，最后执行 booti。
- armbianEnv.txt 中的 Linux DTB 选择为 rockchip/rk3566-panther-x2.dtb。
- 以上哈希来自既有实机采集记录；本轮未重新读取设备。

## 3. 当前混合启动链与 8GB TF 卡的关键约束

依据 PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md：

### 3.1 已闭环的阶段

- U-Boot proper 将 SD/TF 枚举为 mmc 1，eMMC 枚举为 mmc 0。
- SPL 输出 Trying to boot from MMC2；Rockchip SPL ATAGS 映射显示 MMC2/SD 对应 proper 的 mmc 1。
- U-Boot proper 从 mmc 1:1 找到 /boot.scr。
- 随后从 TF 读取 Kernel、initrd 和 Panther X2 Linux DTB。

因此，SPL → U-Boot proper → Linux boot files 的 TF 路径已有实机日志证据。

### 3.2 当前混合链的资产位置

| 启动阶段 | 介质 / 位置 | 身份 |
|---|---|---|
| BootROM → SPL | eMMC LBA 64 | 旧 Panther X2/E25 SPL，U-Boot SPL 2017.09-armbian（2023-04-23），DDR V1.13 |
| SPL → U-Boot proper | TF LBA 16384 | JP-TvBox U-Boot proper，U-Boot 2017.09-armbian（2023-11-12） |
| U-Boot proper → Linux | TF 第 1 分区 | /boot.scr、Kernel、uInitrd、Panther X2 DTB |

TF LBA 16384 的 JP-TvBox u-boot.itb：
- 大小：1,464,832 bytes
- SHA-256：a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce

eMMC LBA 64 原版 SPL 的 SHA-256：
- 990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e

**对新 8GB TF 卡的直接影响：** 如果继续沿用当前混合启动链，不能只在卡上创建普通分区并复制 /boot 文件；还必须在 TF LBA 16384 放置与当前链匹配的 U-Boot proper。eMMC SPL 是现有链的前置依赖，本项目不会修改它。

### 3.3 BootROM 来源证据边界

当前最符合证据的路径是 BootROM 从 eMMC 启动旧 SPL，再由 SPL 从 TF 加载 JP U-Boot proper。eMMC LBA64 指纹、SPL banner、DDR V1.13、SPL MMC2 日志和 RK3566 BootROM 公开启动优先级相互吻合。

但报告明确保留：BootROM 本次读取 eMMC 的硬件级来源寄存器/轨迹尚未直接取得。因此不把第一段升级为直接实测事实。对于本轮 TF 卡规划，采用“保留现有 eMMC SPL、不修改 eMMC”的保守策略。

### 3.4 文件系统类型尚未确认

已有 UART 日志显示：
- U-Boot proper 输出 PartType: EFI；
- 扫描 mmc 1:1 后成功找到 /boot.scr 并读取后续文件。

PartType: EFI 是分区类型信息，不是文件系统类型。现有仓库资料没有直接记录当前 TF BOOT 分区的 FSTYPE，因此不能据此断言它是 FAT 或 ext4。

**待补证：** 当前 TF /boot 所在分区的实际文件系统类型，以及 U-Boot 对该类型的支持。写入 8GB 卡前必须闭环此项；目前不指定新卡的分区格式。

## 4. 6.1.116 正常基线对照边界

6.1.116 归档已保存：
- vmlinuz-6.1.116-ophub 对应的 Kernel Image；
- uInitrd-6.1.116-ophub；
- rk3566-panther-x2.dtb；
- armbianEnv.txt、boot.cmd、boot.scr；
- 完整 kernel.config、dmesg、磁盘 DTB 和运行时 FDT。

6.1.116 与 6.12.81 的 boot.cmd、boot.scr 记录 SHA-256 相同：
- boot.cmd：4896dde2b99bebbb34b2ed2f837f30fa1a5b3ad14b80dd2da391effa94d37d0a
- boot.scr：0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a

这说明两条基线使用的启动脚本逻辑相同，有利于后续固定启动脚本做 Kernel/DTB/initramfs 对照。

但 6.1.116 归档没有包含当年实际使用的 idbloader.img / u-boot.itb 二进制；不能声称已证明 6.1.116 历史启动时使用的 U-Boot proper 与当前 JP-TvBox U-Boot 完全相同。后续若用当前 U-Boot proper 启动 6.1.116 配套 Kernel/DTB，应标记为“共用当前启动固件的受控对照”，而不是“完全复刻历史 6.1.116 启动链”。

6.1.65 原始镜像 BOOT 分区中存在 uInitrd、Image 和 Panther X2 DTB，但本轮不提前加入测试矩阵；按 P5 规则，只有 6.1.116 对照出现无法解释的结果时再考虑 6.1.65。

## 5. 本轮取得的额外审计材料

为复核此前 6.12.81 双资产审计结果，本轮从 GitHub Actions 下载既有 artifact：
- Run：43597391230
- Artifact ID：14114622745
- 文件：ophub-rk35xx-6.12.81-audit.zip
- 大小：2,882,954 bytes
- 本地复核 SHA-256：7c80df5faf4646309b44da64b0995abd63dff2c3412156aada3167538df6a2c5

该 artifact 只包含先前 workflow 生成的报告、DTB 反编译文本和配置快照，不包含原始 141MB kernel 发布包。没有重新下载原始大包，没有触发新的 workflow。

## 6. 当前结论矩阵

| P1 问题 | 结论 | 证据等级 |
|---|---|---|
| 6.12.81 是否支持外部 initramfs | 是，实际日志证明成功解包 | 已验证（实机日志） |
| gzip 是否可用 | 是，现有 uInitrd 为 gzip，内核成功解包 | 已验证（实机日志） |
| CONFIG_BLK_DEV_INITRD / CONFIG_RD_GZIP | 构建默认配置快照均为 y | 静态配置确认；不是最终二进制 .config 直接导出 |
| 现有 U-Boot 是否从 TF 读取启动文件 | 是，读取 mmc1:1 的 boot.scr、Kernel、initrd、DTB | 已验证（实机 UART） |
| 现有 U-Boot 是否接受 legacy gzip uInitrd | 是，识别 AArch64 Linux RAMDisk、校验并传递给内核 | 已验证（实机 UART） |
| 当前 TF 的 U-Boot proper 所在位置 | LBA 16384 | 已验证（历史写入回读记录与启动链报告） |
| 当前 TF BOOT 分区文件系统类型 | 未知 | 待补证 |
| 新 8GB 卡能否只靠普通分区文件启动 | 不能按现有混合链直接假设；需要 raw LBA 16384 U-Boot proper | 已验证启动链约束 |
| 6.1.116 能否作为后续最小环境对照 | Kernel/DTB/uInitrd/boot script 资产已归档；启动脚本一致 | 可行性高；历史 U-Boot 二进制未闭环 |

## 7. 下一项唯一工作

继续 P1，不进入 P2：

**只补齐当前 TF BOOT 分区的文件系统类型和当前 U-Boot 文件系统读取能力证据。**

优先从已有资料继续查找；如果仓库仍无直接证据，再向用户索取一条只读的当前系统挂载/文件系统信息。确认前不为 8GB 卡指定 FAT/ext4，不写卡。

## 8. 操作记录

- 本轮只读回读仓库文档、已有 UART 日志、配置快照和历史 Actions artifact。
- 没有对 Panther X2 发出命令。
- 没有格式化、分区、写入或读取 8GB TF 卡。
- 没有触碰 eMMC。
- 没有重复任何 GMAC TX/RX、PHY、RGMII、DMA 或环回测试。
