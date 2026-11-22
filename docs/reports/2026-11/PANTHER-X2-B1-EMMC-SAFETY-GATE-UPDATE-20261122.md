# Panther X2 B1 实机启动前 eMMC 安全门审计更新（2026-11-22）

## 本轮目标

继续收敛 B1 实机启动前的 eMMC 写入风险；不重复已完成的启动链、Vendor Storage、CMD31 最后组查询，不进行 TF 写入或实机启动。

## 1. 当前 eMMC U-Boot 二进制身份

既有实机原始 eMMC user-area 读取证据：

| 区域 | SHA-256 | 大小 |
|---|---|---:|
| LBA 64 idbloader.img | 990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e | 305,152 bytes |
| LBA 16384 u-boot.itb | 3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af | 1,431,552 bytes |

两者均与 Ophub U-Boot 仓库 6e70f41585f15c43f45fcae609adec1865e83eb5 对应 Panther X2 二进制资产的 Git Blob SHA-1 匹配。该提交的 GitHub commit 元数据显示，它是一个新增 z93a 二进制资产的合并提交；提交 diff 仅包含二进制文件，没有 U-Boot 源码、defconfig 或最终 .config。因此该 commit 是二进制资产版本锚点，不是当前 eMMC SPL 的源码构建来源证明。

既有二进制静态指纹：
- eMMC IDB 内含 U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)；
- 内含 DDR loader 字符串 DDR Version V1.13 20220218；
- 内嵌 FDT 报告 Radxa E25 / rockchip,rk3568；
- 上述内容与此前旧 UART 记录有强指纹吻合，但不是本轮新采集，也不等于每次上电执行轨迹。

## 2. 源码候选与风险边界

既有候选研究定位到 Armbian Panther X2 构建路线使用 Radxa stable-4.19-rock3 与 rock-3c-rk3566_defconfig。研究记录的 Radxa 候选源码 commit 为 c55987146f4f9b20f7cb2f917ca88300419afe8d。

该候选源码/defconfig 静态审计发现：
- CONFIG_SPL_MMC_WRITE=y；
- CONFIG_SPL_AB=y；
- CONFIG_FASTBOOT_FLASH=y；
- SPL A/B 失败回退存在对 misc 元数据执行 blk_dwrite() 的路径；
- Vendor Storage 路径存在 blk_dwrite()；
- board_late_init() 的 LAN_MAC fallback 在读取失败或数据无效时可能随机生成 MAC 并尝试写回 Vendor Storage。

**严格结论：** 这些是与当前二进制高度相关的候选源码证据，但尚未证明 eMMC 活动 IDB 二进制精确由该 commit、该 defconfig 和某个已知最终 .config 构建。不得把候选源码配置直接写成当前 SPL 的已确认配置；也不得因此排除当前启动链存在写入风险。

## 3. Vendor Storage 目标位置已明确

既有 Rockchip U-Boot 与 Linux 源码交叉审计确认 Vendor Storage user-area 位置：
- 起始 LBA：7168；
- 4 份副本，每份 128 sectors；
- 结束 exclusive LBA：7680；
- 覆盖 LBA 7168–7679，总计 256 KiB。

既有 eMMC user-area 备份解析确认 vendor0 是唯一有效副本（version=2），含 LAN_MAC ID 3 的 12-byte 双 MAC 条目；其余三个副本为全零。该信息属于既有归档证据，不代表本轮重新读取了 eMMC。

## 4. 本轮新增的 eMMC WP 实测

用户于 2026-11-22 在当前 Armbian root shell 中按 CID 精确识别 /dev/mmcblk0 为 DF4032，然后只读查询：

- CID：450100444634303332010f37d8066500
- EXT_CSD revision：8
- SEC_COUNT：61,071,360 sectors
- WP group：16,384 sectors（8 MiB）
- 可寻址 WP groups：3,728（编号 0–3727）
- USER_WP=0x00
- BOOT_WP=0x00
- BOOT_WP_STATUS=0x00
- mmc-utils 查询 groups 0–3726：No Write Protection
- 仓库只读 helper 通过 CMD31 查询最后 group 3727：status=0，No write protection
- helper 输出确认仅发送 CMD8/CMD31，没有 CMD6/CMD28/CMD29 或数据写入命令。

这补齐了 mmc-utils 向下取整遗漏的最后一个有效 group。当前 user area 全部可寻址组均已获得未保护状态的查询证据。

## 5. 可用的临时芯片级保护路径（尚未执行）

mmc-utils 上游源码定义：
- mmc writeprotect user set pwron <start> <blocks> <device>：通过 EXT_CSD USER_WP 使能和逐组 CMD28 设置 user-area power-on write protection；
- mmc writeprotect boot set <device>：对 boot0/boot1 设置非永久、随 power cycle 解除的写保护；不带 -p；
- perm 与 -p 是永久/一次性保护路径，本项目严格禁止。

按实机参数，覆盖全部 3,728 个 user-area 可寻址组的循环次数参数为：
- start = 0；
- WP group size = 16,384 sectors；
- groups = 3,728；
- blocks = 61,079,552 sectors；
- 最后一条 CMD28 的 group 起始地址为 LBA 61,063,168，仍小于 SEC_COUNT 61,071,360。

该 blocks 参数比实际 SEC_COUNT 多 8,192 sectors；上游 mmc-utils 代码将其作为循环上限，并按 WP group 起始地址发 CMD28，而不是对超出容量的扇区写数据。但执行前仍必须核对用户设备上实际安装的 mmc-utils 版本/二进制与所审查实现一致，并确认命令参数解析与构建选项。

**重要：** Power-on WP 设置会修改 eMMC 写保护配置并发送写保护命令；它不是普通只读操作。只有用户明确批准具体操作后才可执行。保护生效期间需避免完整断电；下一次 power cycle 会解除 Power-on 保护。不得使用永久保护选项。

## 6. 对 B1 实机测试的当前判定

- B1 Linux 6.18.63 Image、Panther X2 clean DTB、静态 BusyBox、RAM initramfs、JP proper 组件构建已通过 GitHub Actions run 44976346571（#34）。
- 该 artifact 是组件集合，不是 TF 磁盘镜像；当前 B1 workflow 明确标记 PREPARE-ONLY，不生成 raw/hybrid image。
- 当前 boot.cmd 使用 kernel_addr_r、ramdisk_addr_r、fdt_addr_r，但这些变量在目标 U-Boot 环境中的实际值尚未采集；加载地址重叠/DRAM 边界、fdt resize 65536 余量尚未完成静态/现场核验。
- 尚未写入 8GB SU08G 测试 TF；64GB 6.12 对照 TF 保持冻结。
- 尚未执行 eMMC WP 设置；尚未启动 B1。

## 7. 下一步（严格顺序）

1. 只读核对当前系统安装的 mmc-utils 包版本、mmc 二进制路径及 SHA-256；确认命令语法与实现。
2. 将 B1 组件 artifact 打包为 PREPARE-ONLY TF 镜像：LBA 16384 放置已验证 JP proper FIT；GPT ext4 分区从 LBA 32768 开始，根目录包含 boot.scr、Image、uInitrd、Panther X2 DTB；对 GPT、偏移、文件清单和哈希进行 CI 验证。此步骤只构建 artifact，不写实体 TF。
3. 向用户明确请求对 DF4032 全 user-area Power-on WP（必要时 boot0/boot1 非永久 WP）的单独授权；未获授权不执行。
4. 获得授权后，先设置并逐组读回验证 0–3727 均为 Power-on protected；任一组失败立即停止。
5. 保护验证通过后，才写入唯一指定的 8GB SU08G 测试卡；写卡前重新按 CID/容量确认，64GB 对照卡和 eMMC 不作为写入目标。
6. 写卡后先进入 U-Boot 人工交互窗口，读取 devtype/devnum、kernel_addr_r、ramdisk_addr_r、fdt_addr_r，确认无地址重叠，再执行 B1 boot script。
7. 使用 warm reset 保持 Power-on WP 生效；避免完整断电导致保护提前解除。测试结束后按 eMMC WP 状态和设备启动行为记录收尾。

## 8. 禁止事项

- 不使用 perm、-p、永久 EXT_CSD 锁定。
- 不修改 eMMC 数据区、GPT、IDB、U-Boot、Vendor Storage 或系统分区。
- 不写 64GB 6.12 对照 TF。
- 不在 eMMC Power-on WP 完整读回验证前启动当前混合启动链。
- 不将 #34 组件 artifact 描述为已写卡或已启动。


## 9. B1 TF 镜像打包步骤已加入 CI（2026-11-22）

提交：`3c8bfe97999adbe2ed1d1539384ba9cf8f70db33`

在当前 B1 clean-RAM workflow 的 Kernel/DTB/BusyBox/initramfs 组件构建后，新增 PREPARE-ONLY TF 镜像打包与结构验证步骤：
- 生成 2 GiB 镜像文件；
- GPT 分区 1 从 LBA 32768 开始，类型 EF00，ext4 文件系统；
- 已校验 SHA-256 的 JP-TvBox U-Boot proper FIT 写入 raw LBA 16384；
- 分区根目录放置 Image、uInitrd、boot.scr、boot.cmd 和 Panther X2 专用 DTB；
- 写入 TEST-INFO，明确这是现有 eMMC SPL → TF JP proper 的混合启动，尚未清除 eMMC 安全门；
- 检查 GPT、分区类型、JP proper 写入后哈希、ext4 文件系统和分区内启动文件；
- 生成压缩镜像及 SHA-256 清单，随 B1 artifact 上传。

此提交只修改 GitHub Actions workflow；尚无该提交对应的 Actions 运行结果，故不能声称 TF 镜像已构建成功。未写实体 TF、未设置 eMMC WP、未启动设备。

## 10. 当前最短推进路径

1. 等待并核验提交 `3c8bfe9` 对应 B1 Actions 构建结果及新镜像 artifact。
2. 从当前 Armbian root shell 只读采集 mmc-utils 包版本、`mmc` 二进制路径及 SHA-256，核对 Power-on WP 命令实现。
3. 完成 U-Boot 地址变量的安全核验。不得在未知 load address 时执行 boot.cmd。
4. 单独取得用户对 DF4032 全 user-area Power-on WP 的明确授权；未经授权不设置。
5. WP 逐组读回完整通过后，再写唯一 8GB SU08G 测试 TF；64GB 对照卡保持冻结。


## 11. 实机 mmc-utils 旧版源码核对（2026-11-22）

用户实机输出：
- 包：`mmc-utils 0+git20191004.73d6c59-2`
- 二进制：`/usr/bin/mmc`
- SHA-256：`93a71a0c8a05403e205e0b1be3455e8f104f645f5f21e167a488b66fadf654d0`
- `mmc --version` 不支持；程序显示 `0.1`，不是可靠源码版本标识。
- help 列出 `pwron`，未列出 `perm`，但仍需对安装二进制做 dpkg 完整性核对。

对应 Ubuntu 源包版本明确指向上游 Git commit `73d6c59`。该 commit 的 `mmc_cmds.c` 已静态检查：
- `do_writeprotect_user_set()` 参数顺序是独立 argv：type、start block、blocks、device；需要 nargs=5。
- `pwron` 设定 `USER_WP_US_PWR_WP_EN`，不走 `perm` 分支。
- 先通过 CMD6/EXT_CSD 写 USER_WP power-on enable，再循环调用 `set_write_protect()`。
- `set_write_protect()` 使用 CMD28（`MMC_SET_WRITE_PROT`），write_flag=1。
- 完成后再通过 CMD6 恢复原 USER_WP 值。
- 代码未检查 blk_start/blk_cnt 是否超过实际设备容量；blocks 作为循环上限，地址按 blk_start+x 逐组递增。
- 代码中 blk_start/blk_cnt 为 signed int；本设备计划参数均小于 INT_MAX。
- 最后一条 CMD28 地址按实测组大小计算为 LBA 61,063,168，低于 SEC_COUNT 61,071,360；该命令寻址的是最后有效 WP group 的起点。
- 该实现对最后一个 4 MiB 尾段的保护依赖 eMMC 对最后有效 WP group 的定义；CMD31 实测已确认该组可寻址。

**关键风险解释：** 此旧版实现与此前审查的循环控制流一致，但其无容量上限检查意味着命令参数绝不能照抄未经复核。按本设备参数，完整覆盖 3728 组所需 blocks=61,079,552；循环最后一次发 CMD28 的地址仍是 61,063,168，不会向设备发送 61,079,552 作为 CMD28 地址。执行前仍需完成本机 dpkg 文件完整性核验，并再次核对命令的目标设备 CID。

**本轮没有执行任何写保护设置命令。**


## 12. 实机 mmc-utils 包完整性核验通过（2026-11-22）

用户实机执行：
```text
dpkg -V mmc-utils
DPKG_VERIFY_EXIT=0
Package: mmc-utils
Version: 0+git20191004.73d6c59-2
Architecture: arm64
Status: install ok installed
APT Installed: 0+git20191004.73d6c59-2
APT Candidate: 0+git20191004.73d6c59-2
Source: http://ports.ubuntu.com jammy/universe arm64
```

结论：
- `dpkg -V` 无输出且退出码为 0，安装包登记文件通过 dpkg 完整性校验。
- Installed 与 Candidate 版本一致。
- 结合第11节，实机二进制可按 Ubuntu Jammy 的 mmc-utils 源包版本 `0+git20191004.73d6c59-2` / 上游 commit `73d6c59` 审计。
- 这完成了写保护命令实现核验，但不代表用户已授权执行，也不代表已设置任何 WP。
- 当前仍未执行 CMD6/CMD28 写保护设置，未写 TF，未启动设备。


## 13. B1 hybrid TF 镜像 CI #35 失败及修复（2026-11-22）

### #35 实际结果

- Run ID：44978363614
- Commit：`3c8bfe97999adbe2ed1d1539384ba9cf8f70db33`
- Kernel、DTB、BusyBox、initramfs、JP U-Boot proper 等步骤均成功。
- 镜像步骤成功创建 2 GiB GPT 镜像、ext4 文件系统，`e2fsck -fn` 无文件系统问题。
- GPT 检查输出明确显示分区类型为 EFI System Partition；原 workflow 错误地用 `grep EF00` 匹配 `sgdisk -i` 的人类可读输出，导致步骤退出码 1。失败不是内核/DTB/ramdisk 构建问题。

### #36 修复提交

- Commit：`078a33eec2da56300356e1e87634cef8b4e82542`
- 将 GPT 分区类型改为 Linux filesystem（8300），与 ext4 实际用途一致。
- 将分区结束 LBA 显式对齐到 2048-sector 边界（4192255）。
- 验证条件改为匹配 `sgdisk -i` 输出中的 `Linux filesystem` 类型描述。
- 修复提交触发 Actions run #36，Run ID：44978969701；记录时状态为 in_progress，结果待定。
- 尚未声称新镜像已通过 CI；等待 #36 完成后检查 job logs 与 artifact。

## 14. 写保护操作授权状态

截至本报告更新时，用户仅授权持续推进项目，没有明确批准向 eMMC 发送 CMD6/CMD28 设置 Power-on write protection。故：
- 未执行 `mmc writeprotect user set`；
- 未执行 boot-area WP 设置；
- 未设置临时或永久写保护；
- 未写 TF、未启动实机。


## 15. 当前运行系统位于目标 eMMC：禁止在线设置整盘 WP（2026-11-22）

用户在当前 Armbian root shell 只读采集：

```text
ROOT:
 /dev/mmcblk0p2 ext4 rw
MMC0 mounts:
 /dev/mmcblk0p2 -> /
 /dev/mmcblk0p1 -> /boot
 /dev/mmcblk0p2[/var/log] -> /var/log.hdd
lsblk:
 mmcblk0 29.1G RO=0
 ├─mmcblk0p1 255M ext4 /boot RO=0
 └─mmcblk0p2 28.9G ext4 / and /var/log.hdd RO=0
```

结论：
- 当前运行系统根分区和 /boot 均位于目标 eMMC user area，且为读写挂载。
- 禁止在当前系统中对完整 user area 设置 Power-on WP；否则会阻断当前根文件系统、/boot、日志等后续写入，可能导致运行异常或文件系统损坏。
- 不得尝试通过简单 remount-ro / umount 规避：根文件系统仍被内核、服务、日志和其他进程使用，且全盘 WP 会影响 eMMC 上其他运行时写入。
- 下一阶段必须先建立独立于 eMMC 的临时运行环境（优先评估可从 TF 启动、完全驻留 RAM 的 rescue Linux；或经验证的 initramfs rescue 路径），确认根文件系统、日志、swap、服务状态均不依赖 mmcblk0 后，才考虑设置 WP。
- 需特别区分：从 TF 加载 kernel/initramfs 不等于 Linux 根文件系统已脱离 eMMC；必须由独立 initramfs 接管 PID 1，且不 pivot 到 eMMC。
- 在独立 rescue 环境中设置 WP 前，仍须先核对当前启动链写入风险与 WP 保护覆盖；任何设置都需用户单独明确授权。
- 当前没有设置 WP，没有写 TF，没有启动 B1。

## 16. Actions #36 状态（2026-11-22）

查询 GitHub Actions API 时，run 44978969701（commit 078a33eec2da56300356e1e87634cef8b4e82542）仍为 `in_progress`，尚无最终结论。不得把镜像打包修复标记为通过。


## 17. B1 镜像 CI #36 失败原因及 #37 修复

### #36 日志结论
- Run ID：44978969701，commit `078a33eec2da56300356e1e87634cef8b4e82542`。
- GPT 分区类型正确显示为 Linux filesystem，分区 LBA 32768–4192255。
- ext4 创建、卸载及 `e2fsck -fn` 均通过。
- JP proper raw LBA 16384 写入后 SHA-256 与预期完全一致：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`。
- 最后生成 ext4 文件清单时，runner 用户对 `lost+found` 目录没有读取权限，`find` 返回 Permission denied；在 `set -euo pipefail` 下导致 job 失败。
- 因此 #36 失败点是清单扫描误将 ext4 自动目录纳入普通文件清单，不是镜像、GPT、文件系统或 JP proper 内容错误。

### #37 修复
- Commit：`3d9abd4d1c1bdb44a2153fe0bd4225403bad4a45`
- 文件：`.github/workflows/build-panther-x2-b1-clean-ram.yml`
- 将清单命令改为对 `./lost+found` 使用 prune，只哈希实际部署文件。
- 记录时 Actions run #37（ID `44979808662`）为 in_progress；结果待核验。
- 该修复没有放宽文件权限、没有更改分区布局、没有修改内核/DTB/initramfs，也没有触碰实体 TF/eMMC。

## 18. B1 clean kernel 与 eMMC rescue 的功能边界

本轮重新核对仓库实际配置和 init：

### B1 clean kernel（保持原样）
- `kernel.config.fragment` 明确关闭 `CONFIG_BLOCK`、`CONFIG_MMC`、SCSI/ATA/NVMe/MTD。
- Panther X2 B1 clean DTB 禁用 MMC/eMMC/TF 节点。
- BusyBox applet 白名单不包含 `mmc` 或其他存储管理工具。
- `/init` 由 initramfs 作为根运行，挂载 proc/sysfs，输出内核/DTB/内存/挂载信息，然后进入交互 shell；不 pivot 到 eMMC，不挂载持久化分区。
- 该配置适合验证最小 RAM Linux 是否独立启动，但**不能枚举 eMMC，也不能在 Linux 内设置/读取 eMMC WP**。

### Rescue kernel（必须独立设计，不修改 B1）
- 若要从 Linux 读取/设置 eMMC WP，必须另建独立 rescue kernel 配置，启用最小必要的 BLOCK/MMC host/controller/SDHCI 或 DW-MMC Rockchip/EXT_CSD ioctl 支持，并在对应 DTB 中启用 eMMC 控制器。
- Rescue initramfs 必须自己作为 PID 1 根文件系统，禁止挂载、fsck、swap、pivot_root 到 eMMC；日志仅输出串口或 RAM。
- rescue 还需要经过审查的静态 mmc-utils/只读查询 helper；在实际操作前应证明没有自动 mount/udisks/systemd 存储服务。
- Rescue 内核支持 MMC 会增加驱动和初始化范围，不能与 B1 最小基线混为一个产物；必须独立配置、独立 artifact、独立验证。

### 启动链前置风险尚未解决
- 当前 eMMC SPL / U-Boot proper 在 Linux 启动前执行。即使 rescue Linux 后续将 user area 设为 Power-on WP，也不能保护同一次启动中已经发生的 SPL/U-Boot 写操作。
- 当前活动 SPL 的精确源码/最终配置仍未证明；候选源码存在 SPL A/B metadata 与 Vendor Storage 写入路径。
- 因此，单纯“先从 TF 启动 rescue，再由 Linux 设置 WP”并不能自动满足“保护启动链本身”的安全目标。必须先研究 Boot ROM 启动介质选择、TF 启动时是否仍执行 eMMC SPL、当前 SPL 的写入触发条件，以及是否存在可在 SPL 执行前建立硬件/芯片级保护的可行路径。
- 在该前置问题解决前，不安排 rescue 启动、WP 设置或 B1 实机启动。

## 19. 当前状态

- B1 clean-RAM 组件构建：#34 已通过。
- B1 hybrid TF image：#35/#36 因 CI 清单/验证脚本问题失败；#37 正在验证修复。
- eMMC user WP 全部 3728 组均通过只读查询确认当前未保护。
- 当前 Armbian 根分区和 /boot 均读写挂载于目标 eMMC；禁止当前系统在线设置整片 user-area WP。
- Rescue kernel/initramfs 尚未创建；没有写 TF，没有设置 WP，没有启动 B1。


## 20. Rescue 启动路径与既有 BootROM 结论对照（2026-11-22）

重新回溯 P2-BOOT 架构报告后，确认 BootROM 介质选择问题已经有专项审计，不应重复做一般性 BootROM 优先级搜索：

- RK3566 Hardware Design Guide 的自动启动顺序把 eMMC 排在 SDMMC 之前；
- Panther X2 2026-11-18 现场 source tag 为 eMMC source ID 2；
- eMMC user-area LBA64 有有效 IDB；
- 2026-11-19 已实测混合启动：BootROM/eMMC IDB → eMMC SPL → TF U-Boot proper；
- SDMMC0_DET 不是 eMMC/SD 启动优先级选择脚；
- RK3566 SD Boot Card/BCB 升级标记不能作为普通冷启动跳过 eMMC SPL 的方法；
- 既有报告认为在 eMMC 有效 IDB 保持可被 BootROM 读取时，仅向 TF 写入完整 idbloader + proper 不能让 BootROM 直接执行 TF SPL。

因此，TF 上的 RAM Rescue Linux 仍会先经过当前 eMMC SPL。它可以让 Linux 用户空间不依赖 eMMC，但**不能保护同一次启动中更早执行的 eMMC SPL/BL31/U-Boot 阶段写入**。本项目不能把“RAM rootfs”误写成“整个启动链已隔离 eMMC”。

当前真正未闭环的不是 BootROM 一般优先级，而是：
1. Panther X2 板级是否存在原厂 eMMC 上电隔离/复位/供电控制机制；
2. 当前活动 eMMC SPL/proper 二进制与可审计源码、最终配置的精确对应关系；
3. 是否能通过不改写 eMMC IDB 的可恢复方式，在启动前阻断其写路径。

此前专项报告明确禁止清除 eMMC IDB、改写 boot area/EXT_CSD、短接信号或改变板级硬件。没有新的原理图/PCB证据或用户授权前，不实施任何此类尝试。

## 21. B1 #37 当前运行状态

- Run ID：44979808662
- Commit：`3d9abd4d1c1bdb44a2153fe0bd4225403bad4a45`
- 截至本次查询，#37 正在执行 kernel build；此前 source fetch/checkout 成功。
- 镜像打包步骤尚未运行，因此尚无 #37 最终结果或镜像 artifact。


## 22. 用户明确收敛 eMMC 风险研究范围，优先实机 B1（2026-11-22）

用户明确指出 eMMC 已有备份，必要时可以恢复；不接受无限扩大 eMMC 保护研究导致 B1 长期无法推进。自本节起调整项目执行边界：

- B1 唯一核心目标：使用 TF 启动 Panther X2 最小 RAM Linux，验证 Kernel、目标 DTB、initramfs、静态 BusyBox 的实机启动链。
- 停止扩展“证明 eMMC 所有 SPL/BL31/U-Boot 写路径绝对安全”的研究。
- eMMC 全盘 WP、Power-on WP、永久 WP、专用 Rescue kernel、板级硬件隔离不再是 B1 启动前置条件；不再主动展开这些专题。
- 保留现有 eMMC 备份和已知启动链证据；不主动改写 eMMC IDB、SPL、U-Boot proper、GPT 或 Vendor Storage。
- 测试优先写入专用 8GB TF，不触碰 64GB 对照卡。
- 对 TF 写入仍严格识别目标盘、核对容量/型号、写前确认和写后哈希验证，防止误写 eMMC。
- 若测试确实需要修改 eMMC，先说明对象、原因、恢复方式和风险，再由用户明确批准。
- 允许按已验证混合启动链（eMMC SPL → TF JP proper → TF B1 Kernel/initramfs）进行可恢复测试，不因未证明所有早期 bootloader 写路径绝对无写而无限期阻塞。
- B1 clean kernel/DTB/initramfs 保持原样，不把 MMC/网络/无线功能混入 B1。

本决策替代此前“必须先完成全面 eMMC 写保护或 Rescue 隔离才能推进 B1”的门槛。历史分析保留作背景，不再作为当前 B1 阻塞项。

## 23. #37 CI 当前状态

Run ID `44979808662`，commit `3d9abd4d1c1bdb44a2153fe0bd4225403bad4a45`：
- Kernel、DTB、BusyBox、initramfs、JP proper 等步骤全部成功。
- 正在执行 `Package PREPARE-ONLY hybrid TF image and verify layout`。
- 镜像打包步骤尚未结束，artifact 上传待执行；暂不标记通过。


## 24. B1 hybrid TF image CI #37 成功（2026-11-22）

- Run ID：`44979808662`
- Commit：`3d9abd4d1c1bdb44a2153fe0bd4225403bad4a45`
- 结论：success；全部 12 个步骤成功。
- artifact ID：`14737222318`
- 名称：`panther-x2-b1-clean-ram-prepare-only`
- 大小：5,916,095 bytes；expires 2026-12-06T03:19:38Z。
- artifact ZIP SHA-256：`888bd4b5030b03d85693815b815b38e38d4d522b7ef70be2891ab8d5442896fc`（已下载并核验与 GitHub artifact digest 一致）。
- 压缩 TF image：`panther-x2-b1-hybrid-PREPARE-ONLY.img.zst`。
- 压缩 image SHA-256：`856fce763baea0e38a49ff38a519cb3373f5ae37f4a18eb32b763f8effcec92d`。
- 未压缩 2 GiB image SHA-256：`d4a40621a6e144735f6b3cbd564cf567552c89ff5878890a8a164f3239084a11`。
- GPT partition 1：Linux filesystem，first sector 32768，last sector 4192255，ext4，label PANTHER_BOOT。
- JP proper FIT 位于 raw LBA 16384，构建步骤内回读 SHA-256 与已知值一致。
- 分区内六个文件均生成 SHA-256 清单：Image、uInitrd、boot.scr、boot.cmd、DTB、TEST-INFO。
- ZIP 内 `SHA256SUMS` 全部通过校验。
- 此为 PREPARE-ONLY 镜像 artifact；没有写入实体 TF/eMMC，没有执行实机启动。

### Manifest 文案更正

下载检查发现 `BUILD-MANIFEST.txt` 的旧文案仍写着“no disk image”，与新 workflow 已生成 PREPARE-ONLY hybrid image 的事实不一致。已提交更正：
- Commit：`793d26b5e955eb53fddb418015dccb68827950b7`
- manifest 现说明：只生成 PREPARE-ONLY hybrid TF image artifact，不写实体 TF/eMMC。
- 该提交触发后续 Actions 构建；本节所列 #37 artifact 本身功能验证成功，manifest 文案更正的后续 artifact 仍待构建验证。

## 25. 用户决策后的当前执行计划

1. eMMC 全面写保护/Rescue/早期 bootloader 写路径研究停止作为 B1 阻塞项。
2. 先确认专用 8GB TF 的准确设备身份和容量；不触碰 64GB 对照卡。
3. 下载并核验 #37 或更新的 CI artifact；将压缩镜像解压到本地临时文件，核对 SHA-256。
4. 写入前必须以设备型号/容量/设备节点三项交叉确认 8GB TF，确认目标设备不是 eMMC 或 64GB 对照卡。
5. 写入后回读 raw LBA 16384 的 JP proper 区域及 GPT/分区文件，核对哈希。
6. 插卡后先停在 U-Boot 交互提示符，只读获取 devtype/devnum、kernel_addr_r、ramdisk_addr_r、fdt_addr_r 和 DRAM bank 信息；确认无地址重叠后再运行 B1 boot script。
7. 实机串口验证目标是确认 Kernel、DTB、initramfs、BusyBox shell；Linux 网络/存储设备保持刻意关闭。

当前唯一实机阻塞转为：8GB TF 的目标设备确认、实体卡写入、U-Boot 地址现场核对。eMMC WP 不再是前置条件。


## 26. #38 最终 artifact 验证、8GB TF 识别及写卡授权（2026-11-22）

### #38 CI
- Run #38，ID：`44980223119`
- Commit：`793d26b5e955eb53fddb418015dccb68827950b7`
- 状态：completed / success。
- Artifact ID：`14737920711`
- Artifact ZIP：`panther-x2-b1-clean-ram-prepare-only.zip`
- ZIP 大小：5,916,079 bytes
- ZIP SHA-256：`e00439d7dcab26a041bb93f389bd292fca7feeccc19d0ad5bfd5c6697030ffc6`
- ZIP integrity test：PASS。
- Artifact `output/SHA256SUMS` 全部 16 项 PASS。
- Manifest 已更正：`purpose=PREPARE-ONLY; hybrid TF image artifact only; no physical TF/eMMC writes`。

### #38 最终 TF image
- 文件：`panther-x2-b1-hybrid-PREPARE-ONLY.img.zst`
- 压缩文件大小：2,465,875 bytes
- 压缩文件 SHA-256：`b1fb1168a40cec3d4afa19a3431239a20a83ee154ebb40097a48643da193bf62`
- `zstd -t`：PASS，解压长度 2,147,483,648 bytes（2 GiB）。
- 未压缩镜像 SHA-256：`8bbb57ecb169bd9da28f16ee9f5995e5c3a569252f4f09e732f5384f74d993df`
- GPT：单一 Linux filesystem 分区，起始 LBA 32768，结束 LBA 4192255，ext4，label `PANTHER_BOOT`。
- JP proper FIT 位于 raw LBA 16384；构建阶段回读 SHA-256：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`。
- 该镜像仍为 PREPARE-ONLY artifact；尚未写入实体卡。

### 现场识别的专用 8GB TF
用户在 Armbian root shell 现场输出：
```text
mmcblk0: type=MMC name=DF4032 CID=450100444634303332010f37d8066500
mmcblk1: type=SD name=SU08G CID=035344535530384780b16ad9b700c15f
/dev/mmcblk1 size=7.4G
  mmcblk1p1 511M ext4 (not mounted)
  mmcblk1p2 6.9G btrfs (not mounted)
```
- 目标卡唯一识别为 `/dev/mmcblk1`，型号 `SU08G`，CID 如上。
- eMMC `/dev/mmcblk0` 为当前运行系统根设备，明确禁止作为写入目标。
- 64GB 对照卡不在本次目标内。
- 8GB TF 原有分区 p1/p2 及数据将在整卡写入后被覆盖。

### 用户授权
用户明确回复“相关内容和进展同步仓库，确认”，确认允许将已识别的 SU08G 8GB TF（`/dev/mmcblk1`，CID `035344535530384780b16ad9b700c15f`）整卡覆盖为 B1 测试镜像。
- 授权仅针对该 SD 卡，不包含 eMMC、boot0/boot1 或 64GB 对照卡。
- 下一步执行前仍须在写卡现场再次自动核对 SD 类型、型号、CID、容量、挂载状态和目标设备节点。
- 写入后对整张 2 GiB 镜像区域回读 SHA-256，与 `8bbb57ecb169bd9da28f16ee9f5995e5c3a569252f4f09e732f5384f74d993df` 比较；再核对 GPT 与分区文件。
- 写卡和回读尚未发生；不得记录为已完成。


## 27. B1 专用 8GB TF 实际写入、回读与 GPT 修复完成（2026-11-22）

### 写入目标与源镜像

现场再次核对目标设备：
- 设备：`/dev/mmcblk1`
- 类型：SD
- 型号：`SU08G`
- CID：`035344535530384780b16ad9b700c15f`
- 容量：7,948,206,080 bytes（约 7.4 GiB）
- eMMC `/dev/mmcblk0` 未作为写入目标；64GB 对照卡未触碰。
- 写入前 TF 分区已卸载，自动挂载服务 `devmon@devmon.service` 已临时停止。

本次实际使用的是 #37 镜像，不是 #38：
- 文件：`/tmp/panther-x2-b1-hybrid-PREPARE-ONLY.img.zst`
- 压缩文件 SHA-256：`856fce763baea0e38a49ff38a519cb3373f5ae37f4a18eb32b763f8effcec92d`
- zstd 完整性检查：PASS
- 解压长度：2,147,483,648 bytes
- 解压后镜像 SHA-256：`d4a40621a6e144735f6b3cbd564cf567552c89ff5878890a8a164f3239084a11`

### 首次写入后的自动挂载干扰及纠正

首次写入后，Armbian 的 devmon/udevil 自动挂载了新镜像的 ext4 分区；内核日志出现 `EXT4-fs (mmcblk1p1): recovery complete`。随后回读 SHA-256 不匹配。对比源镜像与 TF 首批差异，首个差异位于字节偏移 16,778,285，处于 GPT 分区起点之后的 ext4 超级块区域。该证据与自动挂载时发生 ext4 journal recovery 相符。

处理过程：
1. 临时停止 `devmon@devmon.service`。
2. 卸载 `/dev/mmcblk1p1`（p2 不存在/未挂载）。
3. 确认 devmon 为 inactive，p1/p2 均无挂载记录。
4. 在自动挂载保持停止的情况下重新写入完整 2 GiB 镜像。
5. 写入后立即回读前 512 个 4 MiB block（共 2,147,483,648 bytes）并计算 SHA-256。

第二次写入后回读 SHA-256：
`d4a40621a6e144735f6b3cbd564cf567552c89ff5878890a8a164f3239084a11`

与源镜像解压 SHA-256 完全一致，证明 TF 上完整 2 GiB 镜像区域与 #37 源镜像逐字节一致。自动挂载服务保持临时停止，避免再次改写 ext4 元数据。

### GPT 备份表位置修复

2 GiB 镜像写入 7.4 GiB TF 后，内核提示备份 GPT header 仍位于镜像末尾 LBA 4194303，而非实体卡末尾 LBA 15523839。这是镜像容量小于 TF 卡容量导致的预期 GPT 位置不匹配。

现场使用系统已有 GNU Parted：
- 执行 `parted /dev/mmcblk1 unit s print`；
- 在明确显示可将 GPT 扩展使用剩余磁盘空间的提示下选择 `Fix`；
- Parted 将备份 GPT 结构修复到实体卡末尾；没有扩展 p1，也没有扩展 ext4 文件系统。

修复后只读复核：
- `parted -s /dev/mmcblk1 unit s print`：正常，无 GPT 修复警告；
- `fdisk -l /dev/mmcblk1`：Disklabel type=gpt，单一 Linux filesystem 分区；
- 实体卡容量：15,523,840 sectors；
- p1 起始 LBA：32768；
- p1 结束 LBA：4192255；
- p1 大小：4,159,488 sectors（2 GiB）；
- 文件系统：ext4，label `PANTHER_BOOT`。
- `sgdisk` 未安装；未安装软件，改用系统已有 Parted 完成修复。

### 当前状态与边界

- #37 PREPARE-ONLY 镜像已实际写入唯一获授权的 SU08G 8GB TF。
- 2 GiB 写入区域回读 SHA-256 完全一致。
- GPT 备份表位置已修复并通过 Parted/fdisk 只读复核。
- p1 保持原始镜像定义的 LBA 范围；没有扩容。
- devmon 自动挂载服务目前为临时停止状态；TF 分区未挂载。
- 未写入 eMMC；未修改 eMMC GPT、IDB、SPL、U-Boot proper、Vendor Storage 或 boot area。
- 未写入 64GB 对照卡。
- 尚未启动 B1；尚未执行任何 U-Boot boot 命令。

### 下一步：U-Boot 只读启动前检查

设备仍运行当前 Armbian（根文件系统位于 eMMC）。准备阶段完成后，下一步为正常关机并进入 JP U-Boot proper 的交互提示符，先只读采集：

```text
printenv devtype devnum kernel_addr_r ramdisk_addr_r fdt_addr_r
bdinfo
mmc list
```

根据现场输出核对：
- TF 的 U-Boot 设备类型与设备编号；
- `kernel_addr_r`、`ramdisk_addr_r`、`fdt_addr_r` 是否有效且互不重叠；
- DRAM bank 范围与各加载地址/镜像大小是否兼容。

地址核验通过前，不执行 `booti`，不运行 boot script。该阶段仍只验证 B1 Kernel、Panther X2 DTB、RAM initramfs 与静态 BusyBox；B1 内核中刻意关闭的网络、存储、无线等功能不纳入本轮测试。
