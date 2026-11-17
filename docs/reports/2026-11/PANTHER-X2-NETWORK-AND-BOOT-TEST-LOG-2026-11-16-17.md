# Panther X2 网络与启动链阶段测试总记录（2026-11-16 至 2026-11-17）

- 设备：Panther X2（RK3566）
- 记录范围：上一次 2026-11-15 网络/SSH 前置审计之后，至 2026-11-17 本轮测试结束
- 核心目的：以已知正常的 Linux 6.1.116-ophub 作为实机对照，梳理 Linux 6.12.81 网络异常；同步记录 GMAC/PHY、DHCP/NDP、启动介质、U-Boot 和源码核查结果
- 记录原则：只记录已有实机输出、仓库证据和已完成源码比较；明确区分实测、静态审计、推断及未验证项目
- 隐私：不记录真实 MAC、设备序列号、实际 LAN 主机地址、IPv6 地址/前缀、分区 UUID 或可反推家庭网络的信息
- 操作说明：本阶段包含只读采集，也包含用户授权的 TF 启动介质测试及 DTB 文件恢复；不能笼统称为全程只读

> 本文是阶段性索引和测试过程汇总，不替代各专项报告和原始证据。已有报告中的原始输出仍以其原文件为准；本记录不覆盖或改写历史证据。

## 1. 测试范围与基线

本轮对照的两套 Linux 系统：

| 项目 | 正常参照 | 异常参照 |
|---|---|---|
| Linux | 6.1.116-ophub | 6.12.81-rk35xx-ophub |
| 启动介质 | eMMC 启动测试 | TF 卡启动测试 |
| SoC / 网卡 | RK3566 / GMAC1 | RK3566 / GMAC1 |
| PHY | RTL8211F，PHY ID 0x001cc916 | RTL8211F，PHY ID 0x001cc916 |
| PHY 地址 / 接口 | 0 / RGMII | 0 / RGMII |
| 目标结果 | IPv4 DHCP 地址与默认路由正常，用户确认网络正常 | DHCP 未完成；IPv6 RA/SLAAC 可形成，但 NDP/端到端通信不完整 |

**重要对照边界：** 两套系统不是同一次启动、同一介质的单变量实验；6.1.116 测试时曾出现 100Mbps downshift，随后通过 EEE 状态变化、延迟复测和更换网线恢复千兆。不能把最初的 100Mbps 状态当成 6.1.116 的最终状态，也不能把它与 6.12.81 的 DHCP 故障直接建立因果关系。

## 2. Linux 6.1.116：正常网络参照测试（2026-11-16）

### 2.1 启动与系统身份

- 用户从 eMMC 启动已安装的 Ophub Armbian。
- 运行内核确认是 `6.1.116-ophub`。
- `/boot/Image` 指向 `vmlinuz-6.1.116-ophub`，`/boot/uInitrd` 指向 `uInitrd-6.1.116-ophub`；实际 DTB 为 `rk3566-panther-x2.dtb`，运行时设备树确认 Panther X2 / RK3566。`6.1.192` 仅出现在已安装软件包记录中，是升级遗留；没有证据表明它参与本次启动。
- 该轮测试的目的，是先确认旧内核在同一 Panther X2 硬件上的网络基线，再与 TF 卡上的 6.12.81 比较。

### 2.2 IPv4 网络状态

实机结果：

- eth0 已通过 DHCP 获得 IPv4 地址（具体地址不在公开仓库记录）。
- 默认网关已安装（具体地址不在公开仓库记录）。
- LAN 网段配置正常。
- 用户明确确认：6.1.116 网络正常；后续项目记忆记录了该轮系统地址及默认网关均存在。

**证据边界（补充后）：** 用户提供的历史对话进一步确认，本轮曾 ping hEX（LAN 网关）与 iMac（LAN 主机），两项均为 0% 丢包；RX/TX errors、dropped、carrier errors 均为 0。具体 LAN 地址不在公开记录中。该补充来自对话文字而非原始终端输出，故标记为“用户确认已验证”，不伪装成原始日志。仍未留存与 6.12 故障轮次相同的 hEX 双端 DHCP 抓包，也没有 DNS、互联网或完整应用层测试的证据。

### 2.3 PHY、链路与 EEE 的实际过程

**首次检查（约 2026-11-16 05:48 UTC）：**

- RTL8211F，PHY ID `0x001cc916`。
- PHY mode：RGMII。
- TX delay：`0x30`；RX delay：`0x10`。
- `clock_in_out=input`。
- `ethtool` 显示 100Mb/s、Full Duplex、Link detected yes。
- 内核日志明确报告：从协商的 1Gbps downshift 到实际 100Mbps，并出现 `Link is Up - 100Mbps/Full`。
- RX/TX errors 与 dropped 当时为 0。
- EEE 显示 `enabled - active`；本机与 link partner 均通告 100/1000 能力。
- 用户实际执行过 `ethtool -d eth0`。该输出是 ST GMAC/DMA 寄存器转储，不是 RTL8211F PHY 寄存器转储。

**EEE 关闭试验（约 05:52 UTC）：**

- 用户同意并实际关闭 EEE。
- 关闭后 EEE 显示 disabled，但链路状态短暂变为 Unknown/Down，日志出现 `Link is Down`。
- 该现象不能解释为关闭 EEE 已修复链路；当时观察到的是链路暂时丢失。

**延迟复测与更换网线（约 05:59–06:01 UTC）：**

- 约 9 分钟后的复测，链路已重新恢复 1000Mb/s Full，Link detected yes；EEE 保持 disabled。
- 随后用户更换网线，再次确认 eth0 为 1000Mb/s Full；对端重新通告 1000baseT，内核日志为 `Link is Up - 1Gbps/Full`。
- 用户明确指出千兆问题已通过更换网线解决。此后本项目不再把网线或旧 100Mbps downshift 当作 6.12 DHCP 故障的默认解释。

### 2.4 6.1.116 这轮测试的证据缺口

历史对话明确确认：本轮没有采集 `ethtool -S`、独立 PHY counters、NetworkManager 状态快照或 DHCP 双端抓包。用户随后补充确认，本轮还完成了到 hEX 与 iMac 的 ping，均为 0% 丢包，且 RX/TX errors、dropped、carrier errors 均为 0。因而：

- 已确认 DHCP 地址、默认路由、到 hEX 和 iMac 的 IPv4 连通性，以及用户确认的正常网络状态。
- 已确认链路最终恢复 1Gbps Full，EEE disabled。
- 已确认错误、丢弃和载波错误计数为 0（依据用户补充的对话记录；原始输出尚未归档）。
- 未留存可与 6.12.81 完全同条件比较的 DHCP Discover/Offer 抓包。
- 未留存 6.1.116 的 GMAC MMC hardware TX/RX counters 与 6.12 的逐项对照。
- 不应为了补齐表格而要求用户重做已经完成的正常网络验证；若将来必须精确比较，应先确认是否仍有原始采集文件。

基线完整归档：

- [6.1.116 USB + Ethernet + boot-config 归档说明](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [完整归档文件](../../../evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz)
- Git Blob SHA-1：`56d2c91db73799a4c04764c045f573ab1bc40831`；文件大小 161,606 bytes。
- 归档包含 `ethernet-audit.txt`、`usb-audit.txt`、`kernel.config`、`dmesg-full.txt`，以及运行时 FDT、磁盘 DTB、`armbianEnv.txt`、`boot.cmd`、`boot.scr`。
- 两个较早归档仍保留，没有覆盖。

## 3. Linux 6.12.81：DHCP 与链路复测

### 3.1 基本网络现象

- eth0 已识别 RTL8211F，PHY 地址 0。
- 更换网线后物理链路达到 1000Mbps Full Duplex。
- NetworkManager 曾报告 DHCPv4 `ip-config-unavailable`，最终只完成 IPv6 激活。
- Panther 本机 tcpdump 能捕获 DHCP Discover：UDP 68 → 67，源地址为未配置地址，目的地址为 IPv4 广播地址。
- 既有 hEX 抓包未观察到 Panther 发出的 DHCP 报文；同一 LAN 其他设备 DHCP 正常。
- 本机 tcpdump 的 outgoing hook 只能证明报文经过 Linux 本机抓包点，不能证明帧已由 GMAC/DMA 送到 PHY、从网口物理发出或抵达 hEX。

### 3.2 同步 IPv6 NDP 双端抓包（2026-11-17）

测试方法：Panther 与 iMac 同时启动 ICMPv6 抓包，由 iMac 对 Panther 链路本地地址执行 3 次 ping6。两台设备系统时钟不同，墙上时间戳不一致；用户确认抓包与 ping 是同时进行的，因此按同一轮测试关联。

Panther 端：
- 收到 iMac 发出的 3 个 NS。
- 对每个 NS 都观察到 Linux 随即生成一个 NA。
- NA 的 Ethernet 目的端为 iMac，并含 Target Link-Layer Address 选项。
- 随后 Panther 发出 3 个单播 NS。
- Panther 本机抓包未观察到 iMac 对这些单播 NS 的 NA 回应。
- 统计：9 packets captured、9 received by filter、0 dropped by kernel。

iMac 端：
- 发出 3 个面向 Panther 的 NS。
- 未观察到来自 Panther 的 NA。
- 也未观察到 Panther 发出的单播 NS。
- 同一抓包中，iMac 与其他邻居存在成功的 NS/NA 往返，并收到 hEX 的 RA。
- 统计：11 packets captured、670 packets received by filter、0 dropped by kernel。

结论：iMac → Panther 的 NS 已到达 Panther Linux 抓包点；Panther → iMac 的 NA/NS 只在 Panther 本机 outgoing 抓包点可见，iMac 端未见。它支持“故障边界在 Panther 本机抓包点之后”的判断，但没有证明具体是 TX DMA、GMAC、RGMII、PHY 或交换链路。

专项报告：[Panther Ethernet DHCP / IPv6 NDP 调查](./PANTHER-ETHERNET-DHCP-IPV6-NDP-INVESTIGATION-2026-11-17.md)。

## 4. Linux 6.12.81：GMAC / PHY / DMA 只读取证

### 4.1 设备树、RGMII、GRF 与时钟

已完成的只读检查：

- GMAC1 MMIO：`0xfe010000`。
- 运行时 FDT 的 GMAC1 节点为 M0 RGMII；PHY RTL8211F 地址 0。
- `clock_in_out=input`；TX delay `0x30`、RX delay `0x10`。
- 驱动日志识别 RTL8211F，Link Up 为 1Gbps/Full。
- GRF_MAC1_CON0 读回 `0x00001030`，CON1 读回 `0x00000013`，与 Linux 写入的 delay/interface/enable 配置吻合。
- clk_summary 中 GMAC1 相关时钟显示已使能；关键 125MHz 时钟读回正常。
- PHY reset GPIO 的 phandle、GPIO line、pinmux/pinconf 与 stmmac reset 时序已对照；没有证据证明 PHY reset 失败。
- 这些都是 Linux 接管后的软件配置/寄存器读回，不是 TXC/TXD/RXC/RXD 的物理波形测量，不能证明 RGMII setup/hold、skew、占空比或 jitter 合格。

### 4.2 GMAC / DMA 统计

此前新内核采集的计数器快照：

| 计数器 | 值 |
|---|---:|
| mmc_tx_octetcount_gb | 1050 |
| mmc_tx_framecount_gb | 4 |
| mmc_rx_framecount_gb | 238 |
| mmc_rx_octetcount_gb | 16817 |
| RX CRC / alignment / FIFO / total errors | 0 |
| fatal_bus_error_irq | 0 |
| rx_buf_unav_irq | 0 |
| rx_overflow_irq | 0 |
| rx_process_stopped_irq | 0 |
| rx_pkt_n | 15604 |
| rx_normal_irq_n | 15571 |
| tx_pkt_n | 392 |
| tx_normal_irq_n | 15 |
| tx_clean | 16345 |
| q0_tx_pkt_n | 392 |
| q0_rx_pkt_n | 15604 |
| q0_rx_irq_n | 15571 |
| napi_poll | 31916 |
| IRQ 67 / IRQ 68 | 15808 / 0 |

解释边界：
- `tx_pkt_n`、`tx_clean`、MMC hardware TX frame counters 与物理线上实际成功发出的帧不是同一统计口径。
- `tx_pkt_n=392` 与 `mmc_tx_framecount_gb=4` 的差距是值得继续追踪的线索，但不能据此断言 388 帧未发出；必须先确认各计数器的具体定义、清零时机和统计范围。
- 没有 fatal bus error 或 RX CRC 错误，不代表 TX 物理发送一定正常。

### 4.3 Loopback 与 delayline scan

已执行的新内核驱动诊断：

- 1000Mbps 下 `mac_lb`：FAIL。
- 1000Mbps 下 `phy_lb`：FAIL。
- `phy_lb_scan` 的 RX delayline 0x00–0x7f 扫描没有找到可用窗口，报告 `Can't find suitable delayline`。
- 此前临时调整 runtime delayline 到 TX/RX 0x7f/0x7f，用户随后恢复为 TX 0x30/RX 0x10。

解释边界：
- `mac_lb` 与 `phy_lb` 使用驱动专用 loopback descriptor/buffer 路径，不等同于普通 netdev TX/RX 的完整链路测试。
- PHY loopback 虽设置 PHY BMCR loopback，仍共享 GMAC/DMA RX completion 路径，不是独立 PHY-only 测试。
- 两项 FAIL 不能单独证明 RTL8211F 损坏或 PCB RGMII 时序错误；失败也可能与 DMA RX completion、descriptor ownership/status、buffer、帧长或超时有关。
- delayline scan 无窗口是当前重要现象，但不能仅凭扫描结果决定永久改变 delay 参数。

专项报告：[GMAC / DHCP 与 TF U-Boot 启动链调查](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)。

## 5. 启动介质、U-Boot 与 DTB 证据

### 5.1 eMMC 与 TF 身份核对（2026-11-16）

已完成只读审计：

- 当时运行系统与 /boot 来自 TF：Linux 设备 `/dev/mmcblk0`；eMMC 为 `/dev/mmcblk1`。
- eMMC BOOT/ROOTFS 未挂载，使用 debugfs 只读检查。
- eMMC 用户区 LBA 64 的 idbloader 数据与 Ophub Panther X2 对应文件逐字节一致；LBA 16384 的 u-boot.itb 亦一致。
- eMMC Vendor Storage 中存在 LAN_MAC（ID 3）条目，包含两个 GMAC 地址；地址字节未公开。
- 以上 eMMC 镜像身份不能证明设备当前实际从 eMMC 启动或执行这些镜像。后续用户明确指出当前启动 U-Boot 读取的是 TF 卡上的数据，而不是 eMMC vendor 数据；后续调查按此事实处理，不再混淆 eMMC 历史镜像与 TF 实际启动链。

报告：[eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)。

### 5.2 TF 前 16 MiB 与实际 boot.scr（2026-11-17）

只读读取 TF 卡前 16 MiB：
- 读取 16,777,216 bytes。
- SHA-256：`75c7e878c4ea78aea76fb9ecb3b037becfe413ba467603df34a4258d9688a70f`。
- 可读字符串包含 SPL `U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`、DDR V1.13、Radxa E25 / RK3568、FIT/U-Boot proper 等标识。
- 字符串只能证明内容存在，不能证明其中每个 driver 本次启动都已 probe。

实际 `boot.scr`：
- `dumpimage -l` 报告数据大小 3318 bytes，脚本正文 3310 bytes。
- 已取得完整解码内容：从 U-Boot 当前启动设备加载 `armbianEnv.txt`、uInitrd、Image 和指定 DTB；随后执行 overlay/fixup 处理并 `booti`。
- 当时的 boot.scr 会从当前 `devtype/devnum` 读取文件，不应只凭文件系统挂载位置推断实际启动介质。
- 之后又对 eMMC 与 TF 上 boot.scr、启动链和文件哈希进行区分核对。

报告：[TF 前 16 MiB 与 boot.scr 只读证据](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)。

### 5.3 FIT control FDT 提取与校验

从 TF 的 `u-boot.itb` 中检查 FIT 元数据：
- FIT SHA-256：`3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af`。
- FIT 默认 configuration 描述为 `rk3568-radxa-e25`，引用 FDT image。
- FIT 声明 FDT data-size 20,421 bytes，内部 SHA-256 为 `e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228`。
- 首次 dumpimage 提取结果带 12-byte 零前缀、hash 不匹配，不能作为有效 DTB。
- 后续从正确偏移 1,411,072（0x158800）提取 20,421 bytes，SHA-256 与 FIT 内部声明完全一致，且 dtc 解析成功。
- 该控制 FDT 中 GMAC1 节点为 `status="disabled"`，`phy-mode="rgmii"`，`clock_in_out="output"`，并包含对应的 M1 pinctrl、delay 和 reset GPIO 描述。
- 该 FDT 证明镜像内封装了什么，不等于证明 U-Boot 本次实际 probe GMAC1，也不能仅凭节点状态判断 U-Boot 网络驱动是否工作。

专项报告：[U-Boot FIT FDT 提取调查](./PANTHER-X2-UBOOT-FIT-FDT-EXTRACTION-ISSUE-20261117.md)。

### 5.4 JP-TvBox U-Boot 候选实机启动（2026-11-17）

用户授权后，在 TF 测试介质写入 Ophub JP-TvBox 候选 `idbloader.img` 与 `u-boot.itb`；写入后从 TF 回读，SHA-256 与候选文件一致。原始 UART 日志已归档。

实机结果：
- JP-TvBox 主 U-Boot 成功运行，banner：`U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`。
- U-Boot 从 MMC1/TF 读取 boot.scr、内核、initrd 和设备树。
- Linux 6.12.81 成功启动到 systemd 流程并出现登录提示符，Machine model 为 Panther X2。
- RTL8211F 被识别，Link Up 为 1Gbps/Full。
- 没有 DHCP 成功或获得可用 IPv4 地址的证据；网络层仍未恢复/未验证。
- UART 中 SPL banner/DDR V1.13 与 JP 候选 idbloader 静态字符串中的 SPL/DDR V1.10 不一致；因此不能确认本次实际执行的 SPL/DDR 初始化代码就是写入的 JP-TvBox idbloader。
- 显示 VOP、cpufreq 等日志异常和 GPU/Wi-Fi/蓝牙初始化信息仅作记录；本轮没有完成这些功能的系统性验收。

证据：
- [JP-TvBox 实机启动 UART 原始日志](../../../evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt)
- [JP-TvBox 启动测试清单](../../../evidence/manifests/panther-jp-tvbox-u-boot-boot-20261117.md)

## 6. 运行时 DTB 文件恢复事件（2026-11-16）

在前序软件包核对过程中，误执行的 purge 操作删除了 `/boot/dtb` 目录中的文件。随后用户明确授权，从此前只读采集的 6.1.116 硬件审计归档恢复 Panther X2 DTB：

- 来源：`panther-usb-audit-6.1.116-20261116-142425/boot-config/rk3566-panther-x2.dtb`
- 目标：`/boot/dtb/rockchip/rk3566-panther-x2.dtb`
- 两者 SHA-256 一致：`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`
- 文件大小 117,859 bytes；cmp 成功。
- `/boot/armbianEnv.txt` 指向 `rockchip/rk3566-panther-x2.dtb`。
- 此次只恢复了 Panther X2 运行所需的该 DTB；没有证据表明整个原 `/boot/dtb` 目录已完整恢复。
- 未重启；没有授权重启。

这是一次经用户授权的文件恢复，不是网络故障修复，也不能作为 DHCP 问题已解决的证据。

## 7. 源码对照：已完成与未完成

### 7.1 Linux 6.12.69 与 Ophub 6.12.81

已核对的公开源码基线：
- Rockchip Linux `develop-6.12` 分支 Makefile 标识 `SUBLEVEL=69`。
- Ophub Linux 6.12 源码固定提交：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。

按函数边界逐项比较，以下函数在这两个源码版本中完全一致：
- `stmmac_xmit()`
- `stmmac_tx_clean()`
- `stmmac_tx_err()`
- `stmmac_tx_timer_arm()`
- `rk_gmac_powerup()`
- `rk3568_set_to_rgmii()`
- `rk3568_set_gmac_speed()`
- `rk_gmac_probe()`

结论仅限上述函数：这些函数不是 6.12.69 与 Ophub 6.12.81 之间的差异来源。其他文件、函数、配置、补丁和构建选项仍未完成全量比较。

### 7.2 6.1.116 与 6.12 的源码比较状态

已完成针对 RGMII / Realtek PHY 的定向核查，既有调查报告记录：
- `phy-mode="rgmii"` 下，Rockchip MAC 侧 delay 由 `rk3568_set_to_rgmii()` 配置。
- RTL8211F 对 `rgmii` 的 PHY 内部 TX/RX delay 处理在所查代码中没有发现可解释本故障的明显差异。
- 尚未完成完整 STMMAC TX descriptor、DMA channel、IRQ、NAPI、RX refill、DMA mapping/barrier、IOMMU 和 kernel config 的全路径差异审计。

注意：`ethtool -i` 的 driver 字符串 `st_gmac` 是 STMMAC ethtool 通用标识，不应仅凭该字符串认定 6.1.116 与 6.12 使用了不同网卡驱动实现。

## 8. 关键结论矩阵

| 项目 | 状态 | 证据/边界 |
|---|---|---|
| 6.1.116 获得 DHCP IPv4 与默认路由 | 已验证 | 用户实机确认；详细逐包抓包未留存 |
| 6.1.116 最终 1Gbps Full | 已验证 | 延迟复测、换线后 ethtool/内核日志 |
| 6.1.116 EEE disabled 时最终恢复链路 | 已验证 | 用户实机复测；EEE 关闭瞬间曾短暂 Link Down |
| 6.12.81 Link Up 1Gbps Full | 已验证 | ethtool / 驱动日志 |
| 6.12.81 DHCP Discover 到达 Linux 抓包点 | 已验证 | Panther 本机 tcpdump |
| 6.12.81 DHCP Discover 抵达 hEX | 未观察到 | 既有 hEX 抓包未见；不是同一时刻同步双端捕获 |
| 6.12.81 IPv6 RA/SLAAC | 已验证 | Panther 收到 RA、生成地址和默认路由 |
| 6.12.81 NA/NS 物理发送成功 | 未验证 | Panther outgoing tcpdump 可见，但 iMac 未见对应帧 |
| 6.12.81 GMAC/PHY 物理层波形合格 | 未验证 | 没有示波器/逻辑分析仪波形 |
| loopback / delayline scan | 已执行，结果失败 | 驱动诊断路径不等同于普通物理链路完整验收 |
| JP-TvBox 主 U-Boot 启动 Linux 6.12.81 | 已验证 | UART banner 与登录提示符 |
| JP-TvBox 方案恢复 DHCP | 未验证/未恢复 | 本轮没有 DHCP 成功证据 |
| JP-TvBox idbloader 是实际执行 SPL | 未验证 | UART SPL/DDR 字符串与候选文件静态字符串不一致 |
| 6.12.69 与 Ophub 6.12.81 所列函数相同 | 已验证 | 固定源码函数级比较 |
| 6.1.116 与 6.12 全部网络路径无差异 | 未验证 | 尚未完成全量源码/配置对比 |

## 9. 后续工作基线（避免重复测试）

1. **以 6.1.116 作为已知正常的网络参照，不再重新做基础 DHCP/网关验证。** 需要引用时使用本报告和原始完整归档。
2. **当前主故障仍是 6.12.81 本机 outgoing 抓包点之后的 Ethernet 发送路径。** 不把问题简单归因于 DHCP 客户端、hEX、PHY 或 U-Boot。
3. 继续源码审计时，优先比较 TX descriptor ownership、DMA address mapping、memory barrier、DMA doorbell/channel start、TX IRQ/NAPI completion，以及 RX refill/descriptor completion；同时核对构建配置与 IOMMU/DMA coherent 属性。
4. 结合现有 MMC hardware counters 与驱动 counters 继续分析统计定义，不能直接用 `tx_pkt_n` 对比 `mmc_tx_framecount_gb` 后宣称丢包数量。
5. U-Boot 候选研究继续以静态审计为主；当前 JP-TvBox 主 U-Boot 已能启动，但 DHCP 未恢复，SPL 来源仍未厘清。
6. 不重复 DHCP 基础抓包、已完成的 hEX 检查、PHY ID、RGMII delay、GRF、clock_summary、pinmux、PHY reset GPIO 和 TF 前 16 MiB 提取。
7. 未经明确授权，不安装软件、不修改内核/驱动/DTB/网络服务、不写 eMMC、不刷写启动区、不重启。后续任何写入测试必须先明确目标介质、写入范围和恢复路径。

## 10. 关联仓库记录

- [6.1.116 USB/Ethernet 基线归档说明](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [GMAC / DHCP 与 TF U-Boot 调查](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)
- [Ethernet DHCP / IPv6 NDP 双端调查](./PANTHER-ETHERNET-DHCP-IPV6-NDP-INVESTIGATION-2026-11-17.md)
- [eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)
- [TF 前 16 MiB 与 boot.scr 只读证据](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)
- [U-Boot FIT FDT 提取调查](./PANTHER-X2-UBOOT-FIT-FDT-EXTRACTION-ISSUE-20261117.md)
- [U-Boot 候选研究](./PANTHER-X2-UBOOT-CANDIDATE-RESEARCH-20261117.md)
- [JP-TvBox UART 原始日志](../../../evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt)
- [JP-TvBox 启动测试清单](../../../evidence/manifests/panther-jp-tvbox-u-boot-boot-20261117.md)



## 补充记录：6.1.116 启动身份与 LAN 连通性（用户提供历史对话）

本节补入此前未纳入阶段总记录的对话结论：

- 实际运行内核为 `6.1.116-ophub`。
- `/boot/Image` → `vmlinuz-6.1.116-ophub`；`/boot/uInitrd` → `uInitrd-6.1.116-ophub`。
- 实际 DTB 为 `rk3566-panther-x2.dtb`，运行时设备树确认 Panther X2 / RK3566。
- `6.1.192` 仅见于已安装软件包记录，是升级遗留；无证据表明其参与本次启动。
- eth0 为 `UP, LOWER_UP`，1000 Mbps Full Duplex；DHCP 获得 IPv4 /24 地址。
- ping hEX（LAN 网关）与 iMac（LAN 主机）均为 0% 丢包。
- RX/TX errors、dropped、carrier errors 均为 0。

**证据性质：** 上述细节来自用户在 2026-11-17 提供的历史对话文本，不是原始终端日志。具体 LAN 地址不公开；该段只补充“用户确认已完成”的测试结果，不声称仓库已包含原始命令输出。它修正了此前“没有证据显示逐项完成网关和 LAN 主机 ping”的记录。DNS、互联网和 DHCP 双端抓包仍不在这段证据范围内。


## 6.1.116 原始网络采集文件补充归档

此前用户上传的 `panther-eth-baseline.txt` 与 `panther-eth-supplement.txt` 已确认是本阶段 6.1.116 网络基线的直接采集材料。现已将两份文件制作脱敏副本并归档：

- [完整基线采集输出（脱敏）](../../evidence/network/panther-eth-baseline-redacted.txt)
- [补充采集输出（脱敏）](../../evidence/network/panther-eth-supplement-redacted.txt)

这两份采集文件提供了此前摘要未完整呈现的驱动统计、PHY/EEE、接口计数器、中断、路由和 NetworkManager 等信息。脱敏仅处理家庭 IP、MAC、UUID 和构建主机标识；原始上传附件未修改。脱敏副本保留原始诊断输出结构，但不等同于字节级原件。


## 8. TX 软件完成计数与 MAC MMC 发送帧计数的语义核对（2026-11-17）

### 8.1 源码定义

对照源码：
- Ophub Linux 6.12 candidate：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- Linux 6.1 BSP 参考：`unifreq/linux-6.1.y` 当前分支快照（不是已证明的 6.1.116 精确构建 commit）

已核实：

1. `tx_pkt_n` 在 `stmmac_tx_clean()` 中累计。驱动轮询 TX descriptor，确认 DMA OWN 位已清除后读取 descriptor status；当该 descriptor 是一个 packet 的最后 segment，且未报告 `tx_err`，才增加 `tx_packets`，最终写入 `tx_pkt_n`。
2. `tx_clean` 仅表示执行 TX cleanup 的次数，不是发送包数；`tx_normal_irq_n` 是 TX normal IRQ 统计，也不是发送包数。
3. `mmc_tx_framecount_gb` 对应 DWMAC MMC 的 `MMC_TX_FRAMECOUNT_GB` 硬件计数器。源码注释明确：`_GB` 表示 good and bad frames，`_G` 表示 good only。
4. `stmmac_mmc_setup()` 设置 `MMC_CNTRL_RESET_ON_READ | MMC_CNTRL_COUNTER_RESET | MMC_CNTRL_PRESET | MMC_CNTRL_FULL_HALF_PRESET`。
5. `dwmac_mmc_read()` 将硬件寄存器读数累加到 `priv->mmc` 软件累计字段（`+= readl(...)`）。因此正常驱动路径下，reset-on-read 是硬件读取机制，不意味着 ethtool 展示值只代表最后一次读取窗口。

源码参考：
- [Ophub 6.12 stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [Ophub 6.12 mmc_core.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/mmc_core.c)
- [Linux MMC counter register definitions and GB/G semantics](https://code.googlesource.com/linux/torvalds/linux/+/b8910630c967ffee582289451ddb5f9f19c26872/drivers/net/ethernet/stmicro/stmmac/mmc_core.c)

### 8.2 6.1.116 与 6.12.81 已有计数对照

| 统计来源 | 6.1.116 正常基线 | 6.12.81 异常快照 |
|---|---:|---:|
| 软件 TX completed packets（`tx_pkt_n`） | 1,550 | 392 |
| MAC MMC TX frame count GB | 1,557 | 4 |
| 差值（仅作观察） | 7 | 388 |

6.1.116 基线原始脱敏文件还记录 `q0_tx_pkt_n=1550`、`tx_normal_irq_n=68`、`tx_clean=4365`。6.12.81 网络测试阶段记录 `q0_tx_pkt_n=392`、`tx_normal_irq_n=15`、`tx_clean=16345`。

### 8.3 解释与限制

- 这组跨版本差异比单独比较 `tx_pkt_n` 或 `mmc_tx_framecount_gb` 更有诊断价值：6.1.116 两种统计大致吻合，6.12.81 则严重偏离。
- `tx_pkt_n` 表示驱动基于 DMA descriptor status 认定的成功完成包数；MMC 是 MAC 硬件帧计数。它们不是同一层计数，但在同一驱动生命周期内通常应有合理关联。
- 不能将 392−4 直接认定为恰好 388 个线上丢包。尚需排除两次采样时刻/驱动生命周期不同、计数器是否发生过重置、ethtool 统计读数完整性及硬件 MMC 功能状态等因素。
- MMC 的 `mmc_tx_octetcount_gb=1050` 与 `mmc_tx_framecount_gb=4` 同时偏低，提示不能仅将帧计数差异视为某个单一统计字段显示错误。
- 6.12.81 与 6.1 参考源码中的 `stmmac_tx_clean()` 主体相同；6.12 增加的 XSK TX metadata completion 路径与当前未发现 AF_XDP socket 的状态不匹配，暂不作为本机解释。
- 普通 `stmmac_xmit()` 路径有 queue-aware DMA enable 和 checksum queue capability 等版本变化，但当前证据不足以把其中任一改动认定为故障原因。6.12.81 发布 Image 的精确源码 commit/补丁集仍未被证明等于当前源码候选。

### 8.4 当前优先级调整

DHCP Discover 已被 Panther 本机 outgoing 抓包捕获，而 hEX 未收到。结合 TX 软件完成计数与 MMC 硬件计数严重偏离，当前首要调查方向应为：

1. TX descriptor status / DMA completion 与 MAC MMC 统计之间的断层；
2. GMAC MAC TX enable、MTL TX queue/FIFO、DMA TX channel 状态及错误状态；
3. MAC 到 PHY 的 RGMII TXC/TXD 物理发送路径。

RX dropped 是持续存在的独立接收侧异常，不应直接拿来解释 DHCP Discover 的发送失败。

**状态：** 计数定义与跨版本异常已得到源码及归档数据支持；TX 根因仍未确认。未执行设备配置修改或驱动/内核操作。


## 9. GMAC/DMA 寄存器现场解码（2026-11-17）

用户提供 `ethtool -d eth0`、TX 相关 `ethtool -S` 与 `ip -s link` 快照。

### 9.1 MAC 与 DMA enable 状态

按 DWMAC4 寄存器定义解码：

| dump 项 | 值 | 寄存器含义 | 观察 |
|---|---:|---|---|
| GMAC Reg0 | `0x08072203` | MAC_CONFIG | bit0 RE=1，bit1 TE=1；MAC RX/TX enable 均置位 |
| DMA Reg1 | `0x00081011` | DMA channel TX control（base + 0x04） | bit0 ST=1；TX DMA channel start 置位 |
| DMA Reg2 | `0x00080C01` | DMA channel RX control（base + 0x08） | bit0 SR=1；RX DMA channel start 置位 |
| DMA Reg5 | `0xE0198000` | TX descriptor list base low（base + 0x14） | TX descriptor ring 基地址 |
| DMA Reg8 | `0xE0198740` | TX descriptor tail pointer（base + 0x20） | 当前尾指针 |
| DMA Reg17 | `0xE0198740` | current TX descriptor（base + 0x44） | 与尾指针相等 |
| DMA Reg21 | `0xDF3A8000` | current TX buffer address（base + 0x54） | 当前/最近 DMA buffer 地址 |

DWMAC4 channel register offsets 与位定义参考：
- `dwmac4.h`：MAC_CONFIG、GMAC_CONFIG_RE、GMAC_CONFIG_TE。
- `dwmac4_dma.h`：DMA_CHAN_TX_CONTROL、DMA_CHAN_RX_CONTROL、DMA_CONTROL_ST、DMA_CONTROL_SR、TX/RX descriptor pointers。
- `stmmac_ethtool.c`：GMAC4 dump 将 DMA channel registers 从 base 0x1100 位置复制到 ethtool 输出区。

### 9.2 本次发送统计

| 指标 | 本次结果 |
|---|---:|
| ip link TX packets | 116 |
| q0_tx_pkt_n | 116 |
| mmc_tx_framecount_gb | 116 |
| mmc_tx_octetcount_gb | 29,977 |
| tx_underflow | 0 |
| mmc_tx_underflow_error | 0 |
| mmc_tx_carrier_error | 0 |
| tx_loss_carrier | 0 |
| fatal_bus_error_irq | 0 |
| mtl_tx_status_fifo_full | 0 |
| mtl_tx_fifo_not_empty | 0 |
| mtl_tx_fifo read-control write/wait/read/idle | 均为 0 |
| ip link TX errors/dropped/carrier | 均为 0 |

本次 ip link TX packets、驱动 q0_tx_pkt_n 与 MAC MMC framecount_gb 均为 116，软件完成计数和 MAC 计数在本快照中完全一致。

### 9.3 当前判断

- 当前 MAC TE/RE 使能，DMA TX/RX start 置位；本快照没有显示 TX 通道停止。
- TX tail pointer 与 current TX descriptor pointer 相同，瞬时状态看不出待处理 TX descriptor backlog；这不代表此前 DHCP Discover 发送时也如此。
- 当前无 TX underflow、carrier error、fatal bus error 或 MTL TX FIFO 堵塞计数证据。
- 这份快照不支持“TX DMA 当前持续停摆”或“MAC TX 被关闭”的判断。
- 先前 6.12.81 快照的 `tx_pkt_n=392` 与 `mmc_tx_framecount_gb=4`，而本次两者为 116。由于这些软件累计统计在同一驱动实例中不应自然倒退，跨快照比较前必须确认中间是否发生过重启、驱动 unbind/rebind、接口重初始化或计数器复位；不能把两个不同生命周期的累计值直接相减或比较。

### 9.4 下一步验证

先只读确认当前启动/驱动生命周期，再取得同一时间点的完整 TX 计数：

- `uptime -s`、`cat /proc/uptime`
- `dmesg -T | grep -Ei 'fe010000|eth0|stmmac|reset|unregister|register|link is'`
- 同一轮采集 `ip -s link show dev eth0` 与 `ethtool -S eth0` 中 tx_pkt_n、tx_normal_irq_n、tx_clean、tx_undeflow_irq、tx_process_stopped_irq、tx_early_irq、fatal_bus_error_irq、tx_underflow、tx_carrier、tx_loss_carrier、mmc_tx_framecount_gb、mmc_tx_octetcount_gb。

不执行任何寄存器写入、驱动重载或网络配置修改。


## 10. TX 计数跨采样生命周期复核与更正（2026-11-17）

用户补充了启动时间、完整 eth0 生命周期日志及同一轮 TX 计数。

### 10.1 启动/驱动生命周期

- `uptime -s`: `2026-11-16 03:59:45`
- `/proc/uptime`: `4044.25` 秒（采样时约 67 分钟 uptime）
- dmesg: GMAC probe/init 在 04:00:01；eth0 注册在 04:00:15；链路 Up 在 04:00:19。
- 用户提供的 eth0/stmmac 生命周期日志中未见之后的 eth0 unregister/register 或 GMAC reset。

### 10.2 当前启动周期内的 TX 计数

| 采样 | netdev TX packets | tx_pkt_n | MMC TX framecount_gb |
|---|---:|---:|---:|
| 初始测试快照 | 23 | 23 | 23 |
| 04:49:08 | 91 | 未单独提供 | 未单独提供 |
| 04:50:08 | 92 | 未单独提供 | 未单独提供 |
| 前一轮寄存器采样 | 116 | 116 | 116 |
| 本次计数采样 | 118 | 118 | 118 |

本次 MMC TX octetcount_gb=30639；前一轮为29977，增加662 bytes；TX packet/frame 增加2。TX underflow、carrier error、TX process stopped、TX early IRQ、fatal bus error 均为0。

### 10.3 对此前“392 对 4”结论的更正

此前分析将 `tx_pkt_n=392` 与 `mmc_tx_framecount_gb=4` 作为 6.12.81 同一生命周期中的异常差异，这是证据不足的跨上下文比较。当前已确认的本次启动周期数据从 23、91/92、116 到118持续增长，且有完整生命周期日志，没有显示驱动重注册；软件 TX 完成包数与 MMC TX frame count 在可对照快照中一致。

因此：
- 撤销“本次 6.12.81 启动内 TX 软件完成计数与 MAC MMC 计数严重不一致”的结论。
- `392/4` 数据应标记为来源/生命周期未确认，不可用于当前根因判断。
- 当前快照不支持 TX DMA 长期停摆、MAC TX disabled、TX FIFO underflow 或总线错误。
- DHCP Discover 在本机 outgoing packet capture 可见、但 hEX 未观察到的现象仍待解释；packet socket outgoing capture 发生在真正线上发送确认之前，不能单凭它证明帧已经到达 PHY 线侧。

### 10.4 下一步

应将单个 DHCP Discover 与同一时间窗口的 TX software/MMC 计数增量关联起来，并结合 hEX 端同步抓包判断帧是否离开 Panther 的 PHY。不得再用不同启动或采样上下文的累计计数作直接比较。


## 11. TX 计数连续性确认及 ethtool DMA dump 字段边界（2026-11-17）

进一步核对上一轮 ethtool DMA dump 映射及当前启动周期计数。

### 11.1 当前启动周期计数时间线

本次启动时间 2026-11-16 03:59:45，GMAC 初始化/eth0 注册/Link Up 分别在 04:00:01、04:00:15、04:00:19。用户提供的当前启动期采样：
- 初始：TX packets=23、tx_pkt_n=23、MMC framecount=23。
- 04:49:08：TX packets=91。
- 04:50:08：TX packets=92。
- 随后寄存器采样：TX packets=116、tx_pkt_n=116、MMC framecount=116。
- 最新：TX packets=118、tx_pkt_n=118、MMC framecount=118；MMC TX octets=30639；前一采样为29977，增量662 bytes。
未见当前启动期间 eth0 unregister/register 或 GMAC reset 证据。

因此当前启动期软件、netdev、MMC TX packet/frame 计数一致。此前 392/4 的来源生命周期未确认，不得用于当前启动的同生命周期差异结论。

### 11.2 修正并明确 ethtool DMA dump 的映射边界

按候选源码 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`：
- `stmmac_ethtool_gregs()` 将 DWMAC4 channel base address 起始的一段寄存器复制到 ethtool DMA dump 区。
- channel base = 0x1100，channel register stride = 0x80。
- 该 dump 的 DMA Reg0..Reg22 对应偏移 0x00..0x58（每项 4 bytes）。

已确认相关字段：
- Reg0 = channel control（0x1100）
- Reg1 = TX control（0x1104），ST bit0=1 表示 TX DMA start 置位
- Reg2 = RX control（0x1108），SR bit0=1 表示 RX DMA start 置位
- Reg5 = TX descriptor base low（0x1114）
- Reg7 = RX descriptor base low（0x111c）
- Reg8 = TX tail/end address（0x1120）
- Reg10 = RX tail/end address（0x1128）
- Reg11/12 = TX/RX ring length（0x112c/0x1130）
- Reg13 = channel interrupt enable（0x1134），不是 DMA channel interrupt status
- Reg14 = RX watchdog（0x1138）
- Reg15 = slot control/status（0x113c）
- Reg17 = current TX descriptor（0x1144）
- Reg19 = current RX descriptor（0x114c）
- Reg21 = current TX buffer address low（0x1154）

重要限制：DMA channel interrupt status 位于 channel base + 0x60（索引 Reg24），不在当前 Reg0..Reg22 这段 ethtool dump 中。因此不能从这份 dump 的 Reg13 或其他字段直接宣称读到了 DMA channel 当前 status/error 位。TX tail pointer 与 current TX descriptor 相等只是一帧采样时的指针关系，不能单独证明 DHCP Discover 的线上发送成功。

### 11.3 当前结论

- 当前 MAC TE/RE 与 DMA TX/RX start 均置位。
- 当前启动期 TX 计数连续且软件/netdev/MMC 相互吻合。
- 未见 TX underflow、carrier error、fatal bus error 或 TX process stopped 统计。
- 当前证据不支持持续 TX DMA 停摆；尚未证明单个 DHCP Discover 到达 MAC/PHY 线侧。
- 下一步应对同一个 DHCP Discover 做 Panther eth0 outgoing 与 hEX 物理入口的同步抓包；不再用累计计数差异推断线上发送故障。

## 12. 2026-11-17 晚间补充：GMAC RX / DMA / NAPI 现场快照

用户提供当前 eth0 与 GMAC 只读统计：
- eth0 为 UP / LOWER_UP，Carrier on，运行时 MTU=1500；NetworkManager profile Wired connection 1 的 MTU 设置为 auto。
- ip -s link：RX packets=25,539、bytes=2,244,918、errors=0、dropped=1,694、missed=0；TX packets=283，TX errors/dropped=0。
- ethtool -S：mmc_rx_framecount_gb=25,663、rx_pkt_n=25,663、q0_rx_pkt_n=25,663；rx_normal_irq_n=25,649、q0_rx_irq_n=25,649、normal_irq_n=25,660、napi_poll=51,984。
- CRC、alignment、FIFO overflow、RX missed、RX buffer unavailable、RX process stopped、fatal bus error 等相关计数均为 0。
- /proc/interrupts：eth0 IRQ 67 的 CPU 计数为 154/0/0/25875；IRQ 68 为 0/0/0/0。
- dmesg 片段显示 RTL8211F、RGMII、PTP clock、PAGE_POOL RxQ-0 初始化及 1Gbps Full Link Up。

**判断：** GMAC RX、驱动 RX 统计、接收 IRQ 与 NAPI 均有活动；本次证据不支持 GMAC RX 完全未启动。但 netdev RX dropped 累计 1,694 尚未归因；netdev RX packets 与驱动/MMC 计数差 124，不能直接解释为线上丢包。当前快照没有相邻采样，不能计算 dropped 增量。

**操作记录限制：** 用户终端粘贴过程中多条命令错位；日志筛选输出只明确显示 Link Up 行。因此本次未见 DMA reset 错误，但不视为完整日志审计。没有执行 DHCP renew、接口重启、驱动重载或配置修改。

**下一步：** 从泛化的 GMAC 接收时钟怀疑转向 DHCP Discover/Offer 的实际报文路径，优先被动监听 eth0 UDP 67/68，并在需要时与 hEX 入口同步抓包；不重复已完成的时钟、PHY、RGMII、GRF 和基础 DHCP 检查。


## 13. 2026-11-17 后续实机复核：同一 Linux 6.12.81 环境的 RX 计数与 DHCP 定位边界

本节记录同一 **Armbian / Linux 6.12.81-rk35xx-ophub** 环境下随后提供的另一轮只读统计快照。用户确认测试期间只更换过 U-Boot，没有更换 Linux 内核包。因此第 12、13 节不是两个不同 6.12 内核版本的对照；两节仅按采样时点/记录批次分开保存，累计计数仍须考虑是否跨越重启或驱动生命周期。

### 13.1 接口、MTU 与内核日志

- NetworkManager 活动 profile：`Wired connection 1`。
- profile MTU 设置：`auto`；eth0 运行时 MTU：1500。
- eth0 状态：`UP, LOWER_UP`；当前链路为 1Gbps / Full，flow control rx/tx。
- 本次日志筛选只得到一条明确匹配记录：`Link is Up - 1Gbps/Full - flow control rx/tx`。
- 筛选结果没有显示 `Failed to reset the dma`、`DMA engine initialization failed`、`Hw setup failed` 或 `Link is Down`。但这是 grep 筛选片段，不是完整启动日志审计；只能记为“本次提供的筛选输出未见”，不能据此证明整个启动期间从未发生。

### 13.2 Linux netdev 与 GMAC RX 计数

`ip -s link show dev eth0`：

| 指标 | 读数 |
|---|---:|
| RX bytes | 2,244,918 |
| RX packets | 25,539 |
| RX errors | 0 |
| RX dropped | 1,694 |
| RX missed | 0 |
| TX packets | 283 |
| TX errors / dropped | 0 |

`ethtool -S eth0` 关键计数：

| 指标 | 读数 |
|---|---:|
| `mmc_rx_framecount_gb` | 25,663 |
| `mmc_rx_octetcount_gb` | 2,358,886 |
| `rx_pkt_n` / `q0_rx_pkt_n` | 25,663 / 25,663 |
| `rx_normal_irq_n` / `q0_rx_irq_n` | 25,649 / 25,649 |
| `normal_irq_n` | 25,660 |
| `napi_poll` | 51,984 |
| `ipv4_pkt_rcvd` / `ipv6_pkt_rcvd` | 3,536 / 182 |
| `ip_csum_bypassed` | 21,939 |
| `no_ptp_rx_msg_type_ext` | 25,663 |
| `mmc_rx_multicastframe_g` | 2,168 |
| `mmc_rx_broadcastframe_g` / `mmc_rx_unicast_g` | 0 / 0 |
| `tx_pkt_n` / `q0_tx_pkt_n` | 283 / 283 |
| `tx_normal_irq_n` / `q0_tx_irq_n` | 11 / 11 |
| `tx_clean` | 26,335 |
| `tx_set_ic_bit` | 11 |

以下相关硬件/驱动错误计数均为 0：MMC CRC、alignment、run、jabber、FIFO overflow、watchdog、discard；RX descriptor、overflow、checksum error、CRC、length、MII、GMAC overflow、watchdog、missed、buffer unavailable、process stopped、watchdog IRQ、fatal bus error 等。

`/proc/interrupts`：

- IRQ 67：四 CPU 计数为 154 / 0 / 0 / 25,875。
- IRQ 68：四 CPU 计数为 0 / 0 / 0 / 0。

### 13.3 证据判读

1. **已验证：** GMAC MAC RX 统计、驱动 RX 统计、RX IRQ 与 NAPI 均有大量活动；本轮数据不支持“GMAC RX 完全没有启动”或“RX DMA 整体完全停摆”。
2. **已验证：** 本次快照中上述硬件/驱动 RX 错误计数为 0。
3. **已验证但原因未知：** Linux netdev 累计 RX dropped 为 1,694。没有相邻时间点采样，无法计算本次窗口的 dropped 增量；没有证据将其归因于 DMA descriptor、驱动、协议栈或 DHCP。
4. **待解释：** netdev RX packets=25,539，与 GMAC/MMC/驱动 RX frame=25,663 相差 124。统计层次和采样时刻不同；没有逐包关联前，不把 124 解释为线上丢包。
5. **待解释：** `mmc_rx_unicast_g=0`、`mmc_rx_broadcastframe_g=0` 与总 RX frame、驱动及 NAPI 活动并存。需按该硬件 counter 定义、统计使能和驱动读取方式核对，不能仅据此断言没有单播或广播流量。
6. **未验证：** IRQ 68 为 0 是否异常；需结合驱动申请/使用中断向量的实现，不能单凭计数判断。
7. **未验证：** DHCP Discover 是否到达 PHY 线侧、hEX 是否收到，以及 DHCP Offer 是否返回 Panther。RX 活动不能证明特定 DHCP TX/RX 帧成功通过物理链路。
8. **当前不支持的解释：** 现有快照不支持把问题简单归因于 GMAC 全局时钟未使能或 RX DMA 完全失效；但也不能排除特定报文、特定描述符或 TX 物理边界问题。

### 13.4 下一步最小只读验证

- 先检查现有系统是否已有 `tcpdump`（仅查询命令是否存在，不安装软件）。
- 若工具已存在，再被动监听 eth0 的 UDP 67/68，观察自然发生的 DHCP Discover/Offer；不主动执行 DHCP renew，不重启 eth0、NetworkManager 或驱动。
- 若需要判定报文是否离开 Panther，应将同一时间窗口的 Panther outgoing 观察与 hEX 入口抓包对应；本机 outgoing 抓包和累计 TX 计数都不能替代线侧/对端证据。
- 继续把 RX dropped 的归因与 DHCP TX 边界分开处理，避免把两个尚未建立因果关系的现象混为一谈。

**操作记录：** 本轮仅整理用户提供的既有只读输出；没有安装软件、修改配置、执行 DHCP renew、重启接口/服务、重载驱动或重启系统。真实 MAC、家庭地址及其他可识别信息不写入公开报告。

详细计数器与 MAC 来源线索另见：[GMAC / DHCP 与 TF U-Boot 启动链调查记录](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md) 的第 13、16 节。

## 14. 版本标签纠错：实机没有第二套 6.12.69 内核

原第 13 节标题及正文中的“Linux 6.12.69”属于错误标注，现已更正。**6.12.69 仅是源码比较时 Rockchip `develop-6.12` 分支 Makefile 的 SUBLEVEL 值，不是 Panther X2 实机运行版本。**

实机运行版本以 UART 原始启动日志 `Linux version 6.12.81-rk35xx-ophub` 为准。相关测试期间用户确认只更换 U-Boot，没有更换内核包。第 12、13 节记录的是同一 Linux 6.12.81 环境下不同时间/批次的统计，不构成 6.12.69 与 6.12.81 的实机对照。

内核包基线为 Ophub `kernel_rk35xx` 标准资产 `6.12.81.tar.gz`（141,437,450 bytes；SHA-256 `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`）。Flippy 变体虽曾被离线审计，但没有证据表明它用于本次实机启动。
## 15. 排查方向澄清：TX 未结案，RX 计数不是主线切换（2026-11-17）

新增的 RX/IRQ/NAPI 快照仅用于判断 GMAC 接收侧是否整体失效，并记录 RX dropped=1,694 这一独立待解释现象；它不构成将 DHCP 故障排查从 TX 转向 RX 的依据。

**主故障仍是 TX：** DHCP Discover 已在 Panther 本机 outgoing 抓包点可见，但既有 hEX 抓包未观察到 Panther 报文。MAC TE、DMA TX ST 置位、TX 软件完成计数与 MMC TX frame 计数在同一可比启动周期内吻合，且未见 TX underflow/carrier/fatal bus/FIFO 堵塞计数异常。这些只能排除部分“TX 整体停摆”假设，不能证明特定 DHCP 帧已从 PHY 发出。

TX 尚未完成的工作包括：单个 DHCP Discover 与 descriptor 提交/completion/MMC 增量的逐包关联；Panther 与 hEX 同时间窗口的逐包同步捕获；RGMII TXC/TXD 到 PHY MDI 的实际物理发送确认；以及 6.12.81 实际发布构建对应源码的完整 TX DMA 路径审计。

下一步仍应优先完成 TX 路径静态审计和同一 DHCP Discover 的双端关联。RX dropped 作为独立支线保留，不得替代 TX 主线或被直接认定为 DHCP 故障原因。未经授权不主动 renew DHCP、不重启接口、不修改系统。

## 16. TX 静态审计进度补充（2026-11-17）

TX 专项报告第 20 节已完成本轮 MTL/FIFO 队列配置比较及 GMAC 时钟启动顺序复核。当前没有发现 TX MTL queue mode、scheduler、FIFO partition 或 queue0→DMA0 映射的直接版本回归。6.1 的 5 ms 与 6.12 的 100–200 μs clock-enable wait 是真实差异，但 Panther 的运行时时钟父项指向 PHY 提供的 125 MHz 外部时钟，clk_summary 也显示软件时钟树频率/使能符合 DT；该差异保留为待解释项，不认定为根因。

下一步 TX 主线集中到 MAC TXC/TXD 物理输出边界。不得重复已完成 descriptor/MTL 静态审计；不得擅自执行 loopback、phy_lb、phy_lb_scan、接口重启或寄存器写入。详见：[TX 物理边界与源码审计](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md) 第 20 节。


## 17. RGMII TX 物理测量准备（2026-11-18）

已根据 Realtek RTL8211F datasheet 与 Rockchip RK3566 Hardware Design Guide 整理 PHY 输入侧测点：RTL8211F pin 20 TXC、pin 19 TXCTL、pin 18–15 TXD0–3。1000BASE-T 下 TXC 为 125 MHz，数据在时钟双边沿传输。Panther X2 使用 BROWAN H1GW V04，但本轮未找到可核验的该板 Ethernet 原理图/PCB netlist，因此其 RGMII IO 电压、串联电阻编号和测试点位置仍未知，不得套用其他 RK3566 板卡的编号或电压。

下一步先确认板级近照/原理图能否定位 TX 测点和实际 IO 电压；未确认前不做电气探测。详见 TX 专项报告第 21 节。


## 18. 调查优先级调整（2026-11-18）

用户明确要求：所有板级硬件审计放最后。由于同一 Panther X2 硬件在 Linux 6.1.116 环境下 Ethernet 正常，当前优先比较 6.1.116 与 6.12.81 软件路径差异，重点核对 GMAC probe/open/link-up 中的时钟、GRF、pinctrl、RGMII delay、PHY reset/MDIO/phylink 初始化及 MAC address 传递。软件可调整的硬件控制项排第二；板级照片、RGMII 波形、MDI 侧物理审计排最后，仅在软件路径无法解释后再考虑。

这不绝对排除 6.12 软件对硬件控制方式的回归，但不应把板级测量作为当前前置条件。详见 TX 专项报告第 22 节。


## 19. 软件优先审计：GMAC clock enable 与 MAC fallback（2026-11-18）

6.1.116/6.12.81 Rockchip glue 源码对照发现：
- Panther 的 `phy-mode=rgmii`、`tx_delay=0x30`、`rx_delay=0x10` 下，两版 RGMII delay 最终 GRF 值等价；写入顺序不同。
- 6.12 将 clock enable 从 bulk enable + 检查返回值改为逐项 enable 但不检查返回值，并将等待由约 5 ms 缩短为 100–200 μs。实机 clk_summary 显示相关时钟当前 125 MHz 且 enable，尚不能归因。
- 6.12 新增 `get_eth_addr=rk_get_eth_addr`。若 UMAC address 无效，回调会读 Rockchip Vendor Storage；失败则生成随机 MAC 并尝试写回。当前尚未证明回调实际执行，也未确认运行内核 Vendor provider 和底层介质。
- MAC 不一致本身不能解释 hEX 未见广播 Discover。

下一项仅需从本次 boot kernel log 确认 `rk_get_eth_addr`、Vendor read failure、random MAC fallback 是否出现；该检查只读，不涉及任何 Vendor Storage 写操作。详见 TX 专项报告第 23 节。
