# Panther X2 B1 实机 U-Boot 启动前检查记录（2026-11-22）

## 目的与执行纪律

记录 B1 首次实机启动前已经完成的只读检查，作为后续工作的唯一现场检查基线。后续继续操作前必须先回读本报告；本报告列出的项目不得无理由重复检查。只有硬件重启、介质/文件/环境发生变化，或后续证据明确指出检查失效时，才重新验证对应项目。

本阶段目标是从现有 eMMC SPL → TF JP-TvBox U-Boot proper 混合启动链，启动 B1 纯 RAM Linux。Linux B1 不启用 MMC/block、USB、网络、Ethernet/GMAC/MDIO/PHY、无线/蓝牙或模块。不得把本阶段扩展成 GMAC 排障或网络测试。

## 1. 串口与 U-Boot 状态（实机已验证）

- Panther X2 UART2 串口：`/dev/cu.usbserial-1460`，1500000 baud。
- 使用现有 Python venv：`$HOME/panther-uart-venv`，pySerial 3.5。
- 仓库脚本 `tools/uart/uart-autoboot-interrupt.py` 已成功自动中断 autoboot，识别到 `=>` 提示符；重新连接 miniterm 后仍停留在 U-Boot。
- U-Boot proper：`U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`。
- 当前交互提示符为 `=>`。截至本记录，没有执行 `source`、`boot` 或 `booti`，B1 Linux 尚未启动。

## 2. DRAM 与 U-Boot 环境（实机已读取）

`bdinfo`：
- DRAM start：`0x00200000`
- DRAM size：`0xEFE00000`
- DRAM end exclusive：`0xF0000000`
- Architecture：AArch64
- Baudrate：1500000

已读取环境：
- `bootcmd=run distro_bootcmd;boot_fit;boot_android ${devtype} ${devnum};`
- `boot_targets=nvme mmc1 mmc0 usb0 pxe dhcp`
- `devtype=mmc`
- `devnum=1`
- `kernel_addr_r=0x00280000`
- `ramdisk_addr_r=0x0a200000`
- `fdt_addr_r=0x0a100000`

本次启动使用的地址应以以上现场值为准，不再要求重复采集同一组环境变量，除非 U-Boot 环境或启动会话发生变化。

## 3. MMC 设备身份（实机已读取）

`mmc list`：
- MMC 1：`dwmmc@fe2b0000`，SD。
- MMC 2：`dwmmc@fe2c0000`。
- MMC 0：`sdhci@fe310000`。

现场识别：
- `mmc dev 1; mmc info`：MMC 1 为 SU08G SD，7.4 GiB，SD 3.0，4-bit，Legacy timing。与已授权写入的 8GB 测试 TF（Armbian 下 `/dev/mmcblk1`，CID `035344535530384780b16ad9b700c15f`）对应。
- `mmc dev 2` 初始化超时：`MMC error: The cmd index is 0, ret is -110` / `mmc_init: -110`。随后显示的旧 MMC1 信息不是 MMC2 成功识别证据。
- `mmc dev 0; mmc info`：MMC 0 为 DF403，29.1 GiB，MMC 5.1，HS200，8-bit，对应 32GB eMMC。

**安全边界：严禁对 MMC 0/eMMC 执行写入。** 本阶段没有任何 eMMC 写入授权；当前仅使用 MMC 1/TF 作为启动文件读取介质。

## 4. TF 分区与文件（实机已读取）

`part list mmc 1`：
- GPT/EFI partition map。
- p1 label：`PANTHER_BOOT`。
- start LBA：32768（`0x8000`）。
- end LBA：4192255（`0x3ff7ff`）。
- type GUID：Linux filesystem `0fc63daf-8483-4772-8e79-3d69d8477de4`。
- partition GUID：`[REDACTED-PARTITION-GUID]`。

`ext4ls mmc 1:1 /` 成功，文件包括：
- `Image`：3,713,032 bytes
- `uInitrd`：484,339 bytes
- `boot.scr`：1,130 bytes
- `boot.cmd`：1,058 bytes
- `dtb/`
- `TEST-INFO.txt`：319 bytes
- `lost+found/`

`ext4ls mmc 1:1 /dtb/rockchip` 确认：
- `rk3566-panther-x2.dtb`：114,549 bytes。

上述介质、分区和文件清单已在当前启动会话核验；除非 TF 被重写、重新插拔或分区/文件改变，不再重复执行同样的目录枚举。

## 5. boot.cmd 内容审查（实机读取并逐字节检查）

`ext4load mmc 1:1 0x02000000 boot.cmd` 成功，读取 1058 bytes；随后 `md.b` 检查内存内容。确认脚本：
1. 设置串口 bootargs：`console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init`。
2. 从当前 `${devtype} ${devnum}` 读取 `/Image` 到 `${kernel_addr_r}`。
3. 读取 `/uInitrd` 到 `${ramdisk_addr_r}`。
4. 读取 `/dtb/rockchip/rk3566-panther-x2.dtb` 到 `${fdt_addr_r}`。
5. 执行 `fdt addr ${fdt_addr_r}; fdt resize 65536`。
6. 最后执行 `booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}`。
7. 任一加载失败分支执行 `reset`。

脚本没有写 TF/eMMC 的命令，没有 `saveenv`，没有网络配置。脚本中的 `setenv bootargs` 只修改当前 U-Boot RAM 环境。

## 6. 加载地址与 DRAM 边界（静态核对）

基于本次现场 U-Boot 环境及文件大小：
- Kernel：`0x00280000` 起，3,713,032 bytes。
- DTB：`0x0A100000` 起，114,549 bytes；另请求 FDT resize 65,536 bytes。
- initramfs：`0x0A200000` 起，484,339 bytes。
- 三个 payload 的起始地址互不相同，按文件长度及 FDT resize 预留空间不重叠，均位于 DRAM `0x00200000–0xF0000000` 范围内。

此项仅确认当前已知文件的载入区间与 DRAM 边界关系；不代表已经执行启动，也不替代启动后的内核日志验证。

## 7. boot.scr 检查状态与下一条命令

- `ext4load mmc 1:1 0x02000000 boot.scr` 成功，读取 1130 bytes。
- `iminfo 0x02000000` 返回 `Unknown command 'iminfo'`。当前 U-Boot 不提供 `iminfo` 命令；这是命令缺失，不是 boot.scr 损坏证据。不要再次尝试 `iminfo`。
- 用户执行 `help source`，U-Boot 返回：
  ```
  source - run script from memory
  Usage:
  source [addr]
      - run script starting at addr
      - A valid image header must be present
  For FIT format uImage addr must include subimage
  unit name in the form of addr:<subimg_uname>
  ```
- 因此已确认此 U-Boot 支持 `source`，且要求内存中的脚本带有效镜像头。
- **当前唯一待办检查：** 对已加载在 `0x02000000` 的 `boot.scr` 读取开头 64 bytes，检查传统 U-Boot legacy image magic `27 05 19 56`。命令：
  ```
  md.b 0x02000000 0x40
  ```
- 在核对该输出前，不执行 `source`。不要重新加载或重新检查已确认的 TF 目录、分区、U-Boot 环境和 MMC 设备，除非当前内存内容已被覆盖或 U-Boot 会话重启。

## 8. 启动授权边界与预期行为

在 boot.scr 镜像头确认有效、用户确认开始 B1 启动后，执行 `source 0x02000000` 将：
- 从 MMC 1/TF 读取 Kernel、uInitrd 和 Panther X2 clean-test DTB 到 RAM；
- 设置本次启动的串口参数；
- 调整 FDT 空间；
- 通过 `booti` 将控制权交给 Kernel。

该启动过程不应写入 TF 或 eMMC；Linux B1 不含 MMC/block 驱动，预期以 initramfs 作为 RAM 根文件系统运行。执行后会离开 U-Boot 提示符，进入内核启动日志和 initramfs shell 验证阶段。若出现启动失败，应保留完整 UART 原始日志，不在同一轮同时修改 Kernel、DTB、initramfs 或 U-Boot 环境。

本报告记录的时间点：boot.scr 已加载，`help source` 已确认；boot.scr header 尚未检查；`source` 尚未执行；B1 尚未启动。


## 9. U-Boot 网络基准审计进展（2026-11-22）

用户明确将 U-Boot 网络基准提升至 B1 clean RAM Linux 实机启动之前：历史版本已证明 Linux 可以启动，当前关键未知是网络链路能力。本轮只在当前已运行的 U-Boot proper 提示符下进行，不重启、不切换启动链、不写 TF/eMMC、不保存环境变量。

- 当前 U-Boot proper：U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)。
- help dhcp：命令存在，描述为 DHCP/TFTP boot，语法 dhcp [loadAddress] [[hostIPaddr:]bootfilename]。没有显式 DHCP-only 参数；审计 autoload 前不得执行。
- help mii：只读 device/info/read/dump；write/modify 禁止。
- help mdio：只读 list/read/rx；write/wx 禁止。
- mdio list 实际输出 ethernet@fe010000:。这证明至少一个 MDIO bus 已注册；不证明 PHY 已探测、地址/型号已确认或 Link Up。
- 完整 help 清单含 ping；尚未执行。

用户已授权当前会话的板载有线网口初始化、DHCP 和基本连通性测试。禁止 PHY 寄存器写入、save/saveenv、fatwrite、tftpflash、tftpput、download、fastboot、rockusb、ums、任何 MMC/eMMC 写入，以及 boot/bootd/source/booti/reset。必要 setenv 只可临时存在 RAM，不保存。本轮不重新运行 BootROM/SPL；未来重新启动或写卡仍须遵守 B0.4 安全门。

下一步一次一条命令：mii device；确认 PHY 地址/型号和只读 link；审计 autoload 与 DHCP 实现；确认不会触发 TFTP 后再执行 DHCP；随后分别 ping LAN 网关和已知外部 IP。当前 PHY、link、DHCP、ping 均未验证。

详见 PANTHER-X2-UBOOT-NETWORK-BASELINE-20261122.md。

- 追加实测：`mii device` 枚举出 `ethernet@fe010000`，且 Current device 为同一设备。与 `mdio list` 结果相互印证；PHY 地址、型号和 Link 状态仍未验证。
## 10. U0 恢复检查点补充（2026-11-22）

将当前 U-Boot proper 启动完成、停留在 => 提示符且尚未进行 DHCP/连通性测试的状态正式定义为 U0。当前只做过帮助、环境变量和 MII/MDIO 枚举查询；尚未执行 DHCP、下载、存储写入、环境修改或启动新镜像，也没有添加测试组件。当前可确认的快照及网络测试后回归要求，详见 PANTHER-X2-UBOOT-NETWORK-BASELINE-20261122.md 的 U0 节。

后续 U-Boot 网络测试必须先记录将被临时改变的环境变量，再以 RAM 临时状态执行；测试结束恢复原值/未定义状态、清理本轮临时网络参数，并核对启动链、提示符和身份变量未变。无法无重启地恢复的运行时状态必须明确记录，不得声称已回到 U0。当前禁止 reset/reboot 和任何存储写入。


## 11. 2026-11-22 DHCP异常后的现场状态修订

本节覆盖本检查点中“U-Boot网络基准尚未执行DHCP”的旧状态描述；保留此前历史检查记录，不覆盖旧证据。

- 用户已在旧 U-Boot 会话中确认 `autoload=no` 后执行 `dhcp`。
- 实测先出现 `EQOS_DMA_MODE_SWR stuck`，随后 AArch64 Data Abort，U-Boot 停在 `Please RESET the board`，旧会话失效。
- 实体 Reset 短按未恢复；断电重启后通过 UART 自动 Ctrl-C 截停自动启动，重新进入同一 U-Boot proper。
- 重启后 proper 版本、ethaddr、临时环境变量未定义状态及启动环境关键变量已重新核对；bootdelay=0，boot_targets包含 pxe/dhcp，相关自动启动命令含 DHCP、source、TFTP 和潜在 bootefi。
- 重启后尚未重核 mdio list / mii device，因此 U0 仅部分恢复；不得宣布完整 U0 回归。
- 当前 U-Boot DHCP 测试暂停，不再重试；无 DHCP成功、报文往返、TFTP下载或存储写入证据。

6.1.116 正向控制：既有归档确认 Panther X2 Linux 6.1.116 使用 rk_gmac-dwmac、RTL8211F（PHY ID 0x001cc916）、RGMII，千兆全双工；用户确认 DHCP、hEX及iMac ping正常。原版 U-Boot曾输出 `Net: No ethernet found.`，而Linux后续仍能独立初始化并使用网卡。此历史对照支持Linux不依赖U-Boot网络初始化，但不证明当前JP proper DMA异常对同一启动周期交接绝无影响。

后续网络验证以《PANTHER-X2-NETWORK-LAYERED-VALIDATION-PLAN-20261122.md》为方法基线：B1无网络；B2按最小依赖闭包逐层引入；ARP/ICMP/TCP/UDP必须使用两端报文证据。PRE-HANDOFF READY阶段门仍不可跳过。


## 12. 2026-11-22 仓库 boot.cmd 修订与 TF 旧脚本隔离

对照本检查点第 5 节记录的旧 TF 文件内容，发现旧 `boot.cmd` 的三个加载失败分支都会执行 `reset`。仓库版脚本已修订为失败时只输出错误并结束，不调用 reset；修订提交为 `b3e7177d3cafc62c55948d5cbc3fe76b991cea65`。

**该提交不会自动修改 TF。** 本检查点此前记录的 TF 文件仍是旧版本：`boot.scr` 1,130 bytes、`boot.cmd` 1,058 bytes，且旧脚本包含 reset。对应旧文件哈希未归档。不得执行 TF 上旧 `boot.scr`，不得假设仓库脚本已同步到卡上。需等待新的 PREPARE-ONLY artifact，核对 boot.cmd/boot.scr 与哈希，并通过独立安全门和明确授权后才可更新测试 TF。

此前地址快照 `kernel_addr_r=0x00280000`、`fdt_addr_r=0x0a100000`、`ramdisk_addr_r=0x0a200000` 来自旧 U-Boot 会话；DHCP异常后断电重启，当前会话尚未重新核对这三个地址。它们仅作为历史参考，不能直接签署当前 PRE-HANDOFF。
