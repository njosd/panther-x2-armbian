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
