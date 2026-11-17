# Panther X2 / Armbian 6.12.81 网络测试记录（脱敏汇总）

- 设备：Panther X2（Rockchip RK3566）
- 测试系统：Armbian 26.11.0，Linux `6.12.81-rk35xx-ophub`
- 主要采集时间：2026-11-16 04:06:04（UTC+08:00）
- 本文范围：用户在对话中分段提交的 6.12.81 网络测试结果，按原测试主题合并为一份连续记录；重点覆盖系统身份、启动介质、运行时 DT、GMAC/PHY、ethtool、统计计数器、IRQ、接口/IP 状态及 DHCPv4 现象。
- 用途：后续与已验证正常的 6.1.116-ophub 网络基线对照，定位 DHCPv4 获取失败。
- 隐私处理：真实 MAC、LAN/WAN 地址、IPv6 地址/前缀、序列号、家庭网络标识及个人路径均不在本文公开；保留芯片/驱动型号、版本、计数器、公开源码标识和文件哈希。
- 证据性质：这是对话中分段终端输出的脱敏整理，不是设备原始日志文件的逐字节副本。数值按已提供的终端结果转录；未提供或未保留的字段明确标为未知，不补造数据。

## 0. 摘要与当前故障表现

6.12.81 系统能识别 Panther X2 的 GMAC1 和 RTL8211F PHY，链路协商为 1000Mb/s Full Duplex，Linux 接口为 UP/LOWER_UP；IPv6 RA/SLAAC 可工作，但没有获得 IPv4 地址，IPv4 路由表为空。

本次核心观察：

1. NetworkManager DHCPv4 多次等待约 45 秒后超时，报告 `no lease` / `ip-config-unavailable`；随后 IPv6 连接仍可激活。
2. 接口有真实的 RX 统计活动，RX MMC 硬件帧计数为 894；并非完全没有收到以太网帧。
3. `ip -s link` 报告 RX dropped=67，但 CRC、alignment、FIFO、DMA fatal bus error、RX buffer unavailable 等多个硬件错误/中断计数为 0。
4. 与 6.1.116 正常基线相比，6.12.81 的 MAC 地址不同；其来源尚不能仅凭地址值判断，需结合 `addr_assign_type`、永久地址和运行时 FDT/NVMEM 继续核实。
5. 6.12.81 的 EEE 为 disabled，而 6.1.116 基线为 enabled-active；目前没有证据证明 EEE 是 DHCP 故障原因。
6. 本报告快照中的 RX dropped=67 是需要解释的差异，但不能将 67/894 当作准确丢包率，也不能未经源码核对就认定是某一种 RX 路径故障。

**当前结论：** 物理链路建立、PHY 识别和 Linux 接口启动均已验证；DHCPv4 未成功。单凭本快照尚不能确定 DHCP Discover 是否由 GMAC 实际发出、是否到达路由器，也不能把 RX dropped 直接等同于 DHCP 故障原因。

## 1. 系统身份与运行版本

采集结果：

| 项目 | 结果 |
|---|---|
| 主机板 | Panther X2 |
| SoC | Rockchip RK3566 |
| Armbian | 26.11.0 |
| 内核 | `6.12.81-rk35xx-ophub` |
| 内核构建时间 | 2026-11-13 11:02:28 UTC |
| 架构 | aarch64 |
| 内核镜像 SHA-256 | `f3164d866f075e01472ed04ba380535a1d5dfcf1b622f10484368a3a5543bb4c` |
| DTB SHA-256 | `00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185` |
| 采集时 uptime | 约 6 分钟 |

`uname -a`、Armbian release 信息、运行文件版本与哈希相互吻合。软件包数据库未列出对应内核包，是当前镜像安装/打包方式的表现，不能据此否定正在运行的内核版本。

## 2. 启动介质与文件系统来源

本次启动系统的只读核对结果：

- 根文件系统位于 TF 卡分区（设备名脱敏）。
- `/boot` 位于同一 TF 卡的 BOOT 分区。
- eMMC 是另一块独立块设备，含独立的 BOOT/ROOTFS、boot0、boot1、RPMB 区域。
- 当前 `/boot/Image` 与运行内核版本吻合；`/boot/Image` / `vmlinuz` 的 SHA-256 与上表一致。
- `armbianEnv.txt` 指向 Panther X2 专用 Linux DTB：`rockchip/rk3566-panther-x2.dtb`。
- `/proc/cmdline` 与 `armbianEnv.txt` 中未见显式 MAC override 参数。
- `boot.scr` 存在；本次 0～18 节采集时没有 extlinux.conf 作为有效启动配置的证据。

**介质边界：** 用户已明确本轮 U-Boot 从 TF 卡读取启动数据，而不是读取 eMMC Vendor Storage。板载 MAC 信息存储位置与本轮实际 U-Boot 启动介质是两个不同问题，不能混为一谈；也不能因 Linux 当前 MAC 与旧基线不同就称其为软件随机生成。

## 3. 内核启动日志：GMAC 与 PHY 初始化

关键启动信息（保留技术字段，省略设备唯一标识）：

- GMAC 平台设备：`fe010000.ethernet`
- 驱动日志前缀：`rk_gmac-dwmac`
- 时钟方向：`clock input`
- TX delay：`0x30`
- RX delay：`0x10`
- PHY mode：RGMII
- integrated PHY：no
- Synopsys User ID：`0x30`
- Synopsys ID：`0x51`
- DMA host/device width：32/32 bit
- DMA capability register：支持日志所列能力，包括 RX/TX checksum、TSO
- RX buffer 管理：`Register MEM_TYPE_PAGE_POOL RxQ-0`
- PHY：RTL8211F Gigabit Ethernet
- PHY 地址：0
- PHY 状态通知：`irq=POLL`
- 链路：1000Mb/s Full Duplex，RX/TX flow control
- 驱动报告：`configuring for phy/rgmii link mode`

`irq=POLL` 是 PHY 状态轮询模式，不代表 GMAC MAC 中断未工作；后续 MAC IRQ 统计显示 IRQ 有活动。

启动日志还出现：

- `IRQ sfty not found`
- `No Safety Features support found`

当前只将其记录为 Safety IRQ/feature 不可用提示；没有证据将它与 DHCP 故障建立因果关系。

## 4. 运行时设备树（Live Device Tree）

运行时 FDT 中 GMAC1 节点的关键属性：

| 属性 | 运行时值 |
|---|---|
| 节点 | `ethernet@fe010000` |
| compatible | `rockchip,rk3568-gmac`, `snps,dwmac-4.20a` |
| status | `okay` |
| phy-mode | `rgmii` |
| clock_in_out | `input` |
| tx_delay | `0x30` |
| rx_delay | `0x10` |
| PHY child reg | 0 |
| PHY child status | `okay` |

clock-names 包含：

- `stmmaceth`
- `mac_clk_rx`
- `mac_clk_tx`
- `clk_mac_refout`
- `aclk_mac`
- `pclk_mac`
- `clk_mac_speed`
- `ptp_ref`
- `pclk_xpcs`
- `clk_xpcs_eee`

设备路径与驱动绑定：

- platform device：`/sys/devices/platform/fe010000.ethernet`
- platform driver：`/sys/bus/platform/drivers/rk_gmac-dwmac`
- PHY 路径位于该设备的 MDIO bus `stmmac-1`，PHY 地址 0。

注意：DTB 中 `clocks` / `assigned-clocks` 的原始十六进制值是 phandle 引用。不能仅比较 phandle 数值就认定实际时钟不同；必须解析目标时钟节点和运行时 clock tree。

## 5. 与 6.1.116 正常基线的静态配置对照

| 项目 | 6.1.116 正常基线 | 6.12.81 本次测试 |
|---|---|---|
| GMAC 节点 | `fe010000.ethernet` | `fe010000.ethernet` |
| compatible | `rockchip,rk3568-gmac` / `snps,dwmac-4.20a` | 相同 |
| phy-mode | RGMII | RGMII |
| clock_in_out | input | input |
| TX delay | `0x30` | `0x30` |
| RX delay | `0x10` | `0x10` |
| PHY | RTL8211F | RTL8211F |
| PHY 地址 | 0 | 0 |
| DMA width | 32/32 | 32/32 |
| PHY MDIO bus 名称 | `stmmac-0` | `stmmac-1` |
| EEE | enabled-active | disabled |

已知的节点、PHY、RGMII 模式、时钟方向、delay 和 DMA width 在两套系统间一致。MDIO bus 名称变化可能只是设备注册顺序差异，不能直接判定为故障。

EEE 状态确实不同，但仅凭状态差异不足以证明 EEE 导致 DHCP 失败。6.1.116 的链路最终正常运行且 EEE 曾处于 enabled-active，因此 EEE 不能被先验认定为根因。

## 6. ethtool：驱动、链路与 EEE

`ethtool -i eth0`：

| 项目 | 结果 |
|---|---|
| driver | `st_gmac` |
| version | `6.12.81-rk35xx-ophub` |
| bus-info | `fe010000.ethernet` |

`ethtool eth0`：

- Supported link modes：10/100/1000baseT，含 Half/Full 支持项。
- Advertised link modes：包含 10/100/1000。
- Link partner advertised：包含 10/100/1000。
- Speed：1000Mb/s。
- Duplex：Full。
- Auto-negotiation：on。
- Link detected：yes。

EEE：

- 本次 EEE disabled。
- Tx LPI disabled。
- Link partner 仍通告 100/1000 EEE 能力。
- LPI / EEE wakeup error 计数没有显示明显错误。

## 7. ethtool -S：MAC/MMC 与 DMA 统计快照

采集时只执行了一次 `ethtool -S eth0`。重要计数如下：

### 7.1 MMC 硬件收发计数

| 计数器 | 值 |
|---|---:|
| MMC TX frame count | 23 |
| MMC TX octets | 4,912 |
| MMC RX frame count | 894 |
| MMC RX octets | 67,402 |
| MMC RX CRC error | 0 |
| MMC RX alignment error | 0 |
| MMC RX run error | 0 |
| MMC RX jabber error | 0 |
| MMC RX length error | 0 |
| MMC RX FIFO overflow | 0 |
| MMC RX watchdog error | 0 |
| MMC RX total error | 0 |

### 7.2 RX/TX DMA、IRQ 与 NAPI 计数

| 计数器 | 值 |
|---|---:|
| `rx_desc` | 0 |
| `rx_gmac_overflow` | 0 |
| `rx_missed_cntr` | 0 |
| `rx_overflow_cntr` | 0 |
| `rx_buf_unav_irq` | 0 |
| `rx_process_stopped_irq` | 0 |
| `rx_overflow_irq` | 0 |
| `fatal_bus_error_irq` | 0 |
| `rx_pkt_n` | 894 |
| `rx_normal_irq_n` | 893 |
| `normal_irq_n` | 893 |
| `napi_poll` | 1,825 |
| `q0_rx_pkt_n` | 894 |
| `q0_rx_irq_n` | 893 |
| `tx_pkt_n` | 23 |
| `tx_normal_irq_n` | 0 |
| `tx_clean` | 932 |
| `tx_set_ic_bit` | 0 |
| `q0_tx_pkt_n` | 23 |
| `q0_tx_irq_n` | 0 |

### 7.3 其他校验和与 EEE 计数

| 计数器 | 值 |
|---|---:|
| `ip_hdr_err` | 0 |
| `ip_payload_err` | 0 |
| `ip_csum_bypassed` | 838 |
| `ipv4_pkt_rcvd` | 53 |
| `ipv6_pkt_rcvd` | 3 |
| `irq_tx_path_in_lpi_mode_n` | 9 |
| `irq_tx_path_exit_lpi_mode_n` | 8 |
| RX LPI counters | 0 |
| `phy_eee_wakeup_error_n` | 0 |

说明：

- RX hardware counters 说明 MAC 统计层观察到接收帧活动；这并不证明 DHCP Offer 曾到达设备。
- `rx_pkt_n`、MMC frame counters、netdev `rx_packets` 是不同层级/定义的计数，不能未经驱动源码确认就推导其包含关系。
- `tx_pkt_n` 与 MMC TX frame count 在这次快照中同为 23，但这也不能单独证明 DHCP Discover 已经成功从 PHY 引脚发出。
- `tx_normal_irq_n=0`、`q0_tx_irq_n=0` 与 TX packet/clean 计数的关系需要结合驱动实现解释，不能直接判为 TX 中断失效。

## 8. /proc/interrupts 与软中断

MAC IRQ：

| 项目 | CPU0 | CPU1 | CPU2 | CPU3 | 合计 |
|---|---:|---:|---:|---:|---:|
| eth0 IRQ 67 | 7 | 0 | 0 | 903 | 910 |
| eth0 IRQ 68 | 0 | 0 | 0 | 0 | 0 |

- `/proc/interrupts` 的 `Err` 为 0。
- eth0 IRQ 67 合计 910，与 `rx_normal_irq_n=893` 同一数量级。
- IRQ 68 为 0 不代表网卡没有中断；当前活动的 eth0 IRQ 是 IRQ 67。

`/proc/softirqs`：

| 类型 | CPU0 | CPU1 | CPU2 | CPU3 | 合计 |
|---|---:|---:|---:|---:|---:|
| NET_RX | 983 | 115 | 127 | 987 | 2,212 |
| TASKLET | 120 | 14 | 11 | 19,294 | 19,439 |

CPU3 的 TASKLET 计数明显偏高，但现有证据没有证明这些 tasklet 属于网络路径，也没有证据支持将其直接归因于 IRQ affinity 或 DHCP 故障。

## 9. ip -details -s link：接口层统计

接口 `eth0`：

- Flags：UP、LOWER_UP。
- MTU：1500。
- Link：1000Mb/s Full Duplex。
- TX/RX queues：各 8。
- Carrier：1。
- Operstate：up。

接口统计：

| 方向 | 项目 | 值 |
|---|---|---:|
| RX | bytes | 63,826 |
| RX | packets | 894 |
| RX | errors | 0 |
| RX | dropped | **67** |
| RX | missed | 0 |
| RX | multicast | 0 |
| TX | bytes | 4,820 |
| TX | packets | 23 |
| TX | errors | 0 |
| TX | dropped | 0 |
| TX | carrier | 0 |
| TX | collisions | 0 |

qdisc：

| 项目 | 值 |
|---|---:|
| sent bytes | 4,820 |
| sent packets | 23 |
| dropped | 0 |
| overlimits | 0 |
| requeues | 0 |

关键解释：

- RX dropped=67 是当前快照的重要异常线索。
- Linux stmmac 的 `stmmac_get_stats64()` 将 netdev `stats->rx_dropped` 取自驱动扩展统计 `priv->xstats.rx_dropped`，因此不能简单说它只是上层协议栈丢弃。
- 可能增加该计数的 RX 路径包括 skb 分配失败、FCS trim 失败、VLAN 处理失败、XDP drop/consume 或不支持的 XDP multi-buffer 路径等；本次尚未确定是哪一种。
- `67 / 894` 不能当作精确丢包率，因为两个计数器的统计定义、时间窗口和包含关系尚未核实。
- qdisc dropped=0 与 RX dropped=67 属于不同方向/层次，二者不矛盾。

## 10. IP、路由与邻居状态

本次采集时：

- `ip -br address show dev eth0`：只有 IPv6 global 地址和 link-local 地址；没有 IPv4 地址。
- `ip route show`：IPv4 路由表为空。
- `ip -6 route show`：存在 IPv6 前缀路由、link-local 路由及通过路由器 RA 学到的默认路由。
- `ip neigh`：可见 IPv6 路由器邻居项。
- 接口 carrier=1、operstate=up、MTU=1500、Speed=1000、Duplex=full。

这证明 IPv6 RA 路径至少部分工作，但不证明 IPv4 DHCP 广播帧能够双向通过，也不证明 IPv6 单播邻居解析和端到端通信完全正常。

## 11. DHCPv4 现象与证据边界

本轮已知现象：

- NetworkManager DHCPv4 多次等待约 45 秒后超时。
- 日志出现 `no lease`、`ip-config-unavailable`。
- 随后 IPv6 使连接状态转为 activated。
- 本次 0～18 节快照没有 IPv4 地址与 IPv4 路由。

应区分以下层次：

1. DHCP 客户端是否生成 Discover。
2. Discover 是否进入 Linux netdev / 驱动 TX 路径。
3. DMA 是否完成 TX descriptor。
4. GMAC 是否从 MAC TX 引脚发出帧。
5. PHY 是否正确编码并从 MDI 发送。
6. 交换网络是否转发到 DHCP 服务器/路由器。
7. Offer 是否沿反向路径到达 PHY、GMAC、DMA 和 Linux。
8. DHCP 客户端是否接受 Offer 并配置地址。

当前快照只能证明 DHCP 未完成，不能单独定位失败发生在哪一层。特别是 Linux 本机抓包若显示 outgoing，只能证明帧经过相应 Linux 抓包点，不等于已经从物理网口成功发出。

## 12. MAC 地址来源：本报告保留的事实与未决项

本轮 Linux 当前 MAC 与 6.1.116 正常基线 MAC 不同。为避免公开板卡标识，具体值已从本文移除。

已知事实：

- 当前 MAC 在运行时网络接口上可见。
- `/proc/cmdline` 未见显式 MAC override。
- `armbianEnv.txt` 未见显式 MAC 参数。
- 运行时 FDT GMAC 节点及 PHY 配置已核对；本次报告所记录的 0～18 节输出没有完整给出 `mac-address`、`local-mac-address`、`nvmem-cells` 等属性的原始值。
- 用户明确说明板载 MAC 数据存储于 eMMC 板载存储区域；同时本轮实际 U-Boot 启动数据来自 TF 卡，不能把“MAC 储存位置”与“本次 U-Boot 从哪个介质启动”混为一谈。

尚未验证：

- `/sys/class/net/eth0/addr_assign_type`。
- `ethtool -P eth0` 返回的 permanent address。
- 运行时 DT 是否含 `mac-address` / `local-mac-address`。
- 设备是否通过 NVMEM provider 读取板载 MAC。
- U-Boot 是否将板载 MAC 正确写入最终传给 Linux 的 FDT。
- 当前 MAC 是否为 permanent、由 bootloader 设置、由内核/驱动设置，或被其他启动流程覆盖。

因此不能把当前 MAC 简单称为“随机 MAC”，也不能仅凭两次启动 MAC 不同就断言 DHCP 故障由 MAC 引起。

## 13. 6.1.116 正常基线：用于对照的关键数据

6.1.116 基线来自单独的已归档报告 `panther-eth-baseline.txt` 与 `panther-eth-supplement.txt`。以下只列对本报告有用的比较项：

| 项目 | 6.1.116 正常基线 | 6.12.81 本次快照 |
|---|---:|---:|
| 内核 | 6.1.116-ophub | 6.12.81-rk35xx-ophub |
| PHY | RTL8211F | RTL8211F |
| Link | 1Gbps Full | 1Gbps Full |
| RGMII | 是 | 是 |
| clock_in_out | input | input |
| TX/RX delay | 0x30 / 0x10 | 0x30 / 0x10 |
| DMA width | 32/32 | 32/32 |
| EEE | enabled-active | disabled |
| RX MMC frames | 3,069 | 894 |
| RX MMC octets | 3,757,762 | 67,402 |
| RX errors | 0 | 0 |
| RX dropped（netdev） | 0 | 67 |
| RX buffer unavailable IRQ | 0 | 0 |
| RX process stopped IRQ | 0 | 0 |
| fatal bus error IRQ | 0 | 0 |
| IPv4 DHCP | 成功 | 未成功 |
| IPv4 address/route | 已配置 | 无 |

采集时长和网络活动量不同，因此帧数/字节数不可直接作为性能对比。最有意义的差异是 6.12.81 netdev RX dropped=67，而 6.1.116 为 0；同时 6.12.81 EEE 状态不同。两者目前都只是待解释差异，不是已证明根因。

## 14. 公开源码问题线索（非本机实测结论）

后续源码研究发现，上游 STMMAC RX 路径在 2026 年存在与 `napi_build_skb()` 失败处理有关的修复：

- 2026-09-21：`napi_build_skb()` 失败后回收 page，但旧代码可能未清除 `buf->page`，导致 refill 路径误用已回收 page；修复提交为 `0a7822e34a0bfde31b194ac3da3253e5032b44cc`。
- 2026-11-13：修复 multi-descriptor frame 中首个 `napi_build_skb()` 失败后未正确丢弃该帧剩余 descriptor 的问题。

这些上游修复提示 6.12 STMMAC RX 路径值得做精确源码对照，但当前尚未证明 Panther 所运行的 Ophub 6.12.81 是否包含或缺少这些补丁，也未证明本次 67 个 dropped 来自 `napi_build_skb()` 失败。DHCP 小帧通常不需要跨多个 RX descriptor，因此 11 月 13 日 multi-descriptor 修复不是 DHCP 小包故障的直接解释；9 月 page recycle 问题是否相关也需先核对版本源码和运行时计数。

## 15. 已确认、未确认与推测

### 已确认（实机输出或用户明确确认）

- 运行内核为 6.12.81-rk35xx-ophub。
- Panther X2 / RK3566 平台。
- Linux 从 TF 卡系统启动，`/boot` 与 rootfs 均在 TF 卡。
- GMAC1 为 `fe010000.ethernet`，驱动为 `rk_gmac-dwmac` / `st_gmac`。
- RTL8211F PHY，地址 0，RGMII。
- Linux 运行时 DT 显示 GMAC 节点 okay，clock input，TX/RX delay 为 0x30/0x10。
- 链路 1000Mb/s Full，carrier=1，operstate=up。
- RX 统计有活动；本次 netdev RX dropped=67。
- 本次没有 IPv4 地址，IPv4 路由表为空。
- IPv6 地址/RA 路由存在。
- 本次快照中 CRC、alignment、FIFO、fatal bus error、RX buffer unavailable 等列出的错误计数为 0。
- 6.1.116 基线网络正常，最终千兆链路已通过更换网线恢复；不得把旧网线问题重新作为本次 DHCP 故障默认解释。

### 尚未验证

- 当前 MAC 的赋值类型和永久地址。
- U-Boot 是否从板载 MAC 存储读取并写入最终 FDT。
- DHCP Discover 是否成功离开 Panther PHY 并到达路由器。
- DHCP Offer 是否从路由器发出并到达 Panther PHY。
- RX dropped=67 的精确触发路径。
- 6.12.81 实际构建中是否包含上述 STMMAC RX 上游修复。
- Linux 接管前 U-Boot 遗留的 GMAC 时钟、GRF、pinctrl 状态是否存在异常。
- RGMII TX/RX 物理波形与时序裕量。

### 推测/候选，不作为结论

- STMMAC RX page-pool / skb 分配失败路径可能与 RX dropped 有关。
- U-Boot 与 Linux 的 GMAC 状态交接可能存在差异。
- MAC 来源/传递链可能存在问题。
- EEE 状态差异可能值得审查。

以上候选都必须由针对性证据支持，不能用来替代实测。

## 16. 后续最小化核查清单（只读）

本报告整理后，下一轮只推进尚未完成、能区分假设的证据，不重做已完成的常规链路测试：

1. MAC 来源：读取 `addr_assign_type`、`ethtool -P`、运行时 FDT 的 MAC/NVMEM 属性及 NVMEM provider 列表。
2. 精确源码：定位 Ophub 6.12.81 对应的实际源码提交/补丁集，核对 STMMAC `stmmac_rx()`、page-pool refill、`napi_build_skb()` 错误路径及 `rx_dropped` 增量点。
3. DHCP 物理边界：如需再抓包，应设计同步的 Panther 与路由器端采集，区分本机 outgoing、路由器收到和路由器回应；执行前先说明范围并取得用户授权。
4. 若源码/计数器不能解释 TX/RX 差异，再检查 U-Boot 实际使用的控制 DT、GMAC probe 与 CRU/GRF/pinctrl 交接；不因猜测直接刷写 U-Boot 或改动 delay。
5. 不修改内核、驱动、设备树、网络服务或路由器配置；不安装工具。

## 17. 相关归档与交叉引用

- 6.1.116 正常基线：仓库中 `panther-eth-baseline-redacted.txt`、`panther-eth-supplement-redacted.txt` 及对应归档说明。
- 6.1.116 与 6.12.81 的阶段性网络/启动总记录：`PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md`。
- GMAC / DHCP / U-Boot 后续专项调查：`GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md`。
- IPv6 NDP 与 DHCP 双端抓包专项调查：`PANTHER-ETHERNET-DHCP-IPV6-NDP-INVESTIGATION-2026-11-17.md`。
- U-Boot FIT/FDT、TF 启动区及 boot.scr 证据：同月相关专项报告。

## 18. 归档说明

本文把原先分段提交的 6.12.81 网络测试信息集中为单一可检索文档。对话中没有提供完整原始终端输出的项目，仅记录可确认的关键值与证据边界；不将总结性描述伪装成原始日志。若后续找到原始采集文件，应另行作为脱敏证据附件保存，并在本文追加 SHA-256 和来源说明，不覆盖本报告。



## 19. MAC 状态补充核查（后续只读输出）

本节记录后续补充的只读检查。为避免泄露设备标识，具体 MAC 字节值不在此重复。

| 检查项 | 结果 | 解释 |
|---|---|---|
| `/sys/class/net/eth0/addr_assign_type` | `0` | Linux 将接口地址标记为 permanent 类型 |
| `ethtool -P eth0` | 与当前地址一致 | 驱动报告的 permanent address 与运行地址相同 |
| `/sys/class/net/eth0/address` | 与 permanent address 一致 | 当前接口地址一致 |
| Live DT `mac-address` | 与当前地址一致 | 运行时 FDT 中存在该属性 |
| Live DT `local-mac-address` | 与当前地址一致 | 运行时 FDT 中存在该属性 |
| Live DT `nvmem-cells` | absent | GMAC 节点未声明该属性 |
| Live DT `nvmem-cell-names` | absent | GMAC 节点未声明该属性 |
| `/sys/bus/nvmem/devices` | 存在 `rockchip-otp0` | 仅证明系统注册了 OTP NVMEM provider，不证明 GMAC MAC 从该 provider 读取 |
| MAC 相关 FDT 节点 | 包含 GMAC1、pinctrl、clock 等节点 | 与本节 MAC 地址来源判断无直接新增证据 |

### 本节结论

1. 当前接口 MAC、驱动报告的 permanent MAC，以及运行时 FDT 的 `mac-address` / `local-mac-address` 三者一致。
2. `addr_assign_type=0` 表示 Linux 当前将其标记为永久地址类型；不应称为 Linux 临时随机生成地址。
3. GMAC 节点没有显式 NVMEM cell 引用；系统存在 `rockchip-otp0` 并不能据此推断该 MAC 来自 OTP。
4. 用户此前已通过启动链调查确认本轮 MAC 来源与 TF 卡数据有关。该来源结论作为既有调查结论保留，不在当前 DHCP 主线重复追查。
5. MAC 来源/传递链降为最低优先级；除非后续出现直接证据表明它影响 DHCP 报文收发，否则不继续投入排查资源。



## 20. STMMAC 6.12.81 源码审计：`rx_dropped` 的实际增加路径

### 20.1 源码样本与版本边界

本轮对照了以下可访问源码快照：

- Linux stable：[`gregkh/linux` 的 `v6.12.81` STMMAC 源码](https://github.com/gregkh/linux/blob/v6.12.81/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)，文件内容 SHA-1（Git blob）：`5016b8c39b6847fbeced096842daac1412fb221e`。
- Rockchip BSP 候选：[ `unifreq/linux-6.12.y-rockchip` 的 `v6.12.81` STMMAC 源码](https://github.com/unifreq/linux-6.12.y-rockchip/blob/v6.12.81/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)，文件内容 SHA-1（Git blob）：`495e98f7b71654393d357de2c348f75b9d8b686b`。
- Ophub Rockchip kernel 当前分支的同路径文件与 unifreq 当前分支文件内容相同（Git blob：`bdd0db20864b1aa6b331b3185ae65d87cdd9f3fc`）；但它不是设备镜像的构建提交证明。

Ophub 项目公开的构建来源同时列有 `unifreq/linux-6.12.y-rockchip` 与 `ophub/linux-6.12.y-rockchip` 等选项。因此，当前 `6.12.81-rk35xx-ophub` 内核版本字符串和构建日期，尚不足以唯一确定设备镜像采用的具体源码仓库、commit 和补丁集合。上述两个 v6.12.81 文件是高度相关的审计候选，不冒充已从本机 Image 反推出的精确构建源码。

### 20.2 在 v6.12.81 候选源码中，直接增加 `rx_dropped` 的位置

逐项检索 `stmmac_main.c` 后，归纳出四类实际增加路径：

| 路径 | 代码位置（unifreq v6.12.81） | 触发条件 | 对普通以太网 RX 是否默认发生 |
|---|---|---|---|
| ZC skb 构造失败 | `stmmac_dispatch_skb_zc()`，约 5115–5118 行 | `napi_alloc_skb()` 返回 NULL | 否；属于 AF_XDP zero-copy 分支 |
| XSK/XDP 消费丢弃 | `stmmac_rx_zc()`，约 5352–5362 行 | XDP verdict 为 CONSUMED，或 XSK_CONSUMED | 否；属于 AF_XDP zero-copy 分支 |
| 普通 RX 的 XDP_CONSUMED | `stmmac_rx()`，约 5561–5580 行 | 已附加的 XDP 程序返回 CONSUMED | 只有挂载并执行 XDP 程序时才可能 |
| 普通 RX skb 分配失败 | `stmmac_rx()`，约 5592–5601 行 | `napi_alloc_skb(&ch->rx_napi, buf1_len)` 返回 NULL | 是；这是无 XDP 程序时普通 RX 路径仍可能触发的分支 |

另有 `stmmac_get_stats64()` 将 `priv->xstats.rx_dropped` 赋给 netdev 的 `stats->rx_dropped`（约 7101 行）。因此，`ip -s link` 的 RX dropped 在该驱动实现中确实反映上述驱动路径汇总，而非简单的 CRC/FIFO 错误计数。

### 20.3 哪些常见怀疑在这份源码中不是直接的 `rx_dropped` 来源

- `stmmac_rx_status()` 返回 `discard_frame` 时，普通 RX 路径回收 page、标记 frame error，并在未启用 RX timestamp 时增加 `rx_errors`；该分支不是这里的 `rx_dropped++` 路径。
- 普通 RX 代码对 FCS 做长度扣除；VLAN tag 处理调用 VLAN helper。该 v6.12.81 代码路径没有在这些操作失败时增加本处的 `rx_dropped`。
- `stmmac_rx_refill()` 中 `page_pool_alloc_pages()` 失败会停止 refill loop，但本身不增加 `rx_dropped`。它可能造成 RX descriptor 补充不足，是另一条应结合 buffer-unavailable / ring 状态检查的路径。
- 当前设备快照的 `rx_buf_unav_irq=0`、`rx_process_stopped_irq=0`、`fatal_bus_error_irq=0`，暂不支持已经发生明显 DMA buffer-unavailable 或 process-stopped 故障；但单次计数快照不能完全排除短暂 refill 问题。

### 20.4 对此前两个上游补丁线索的修正

此前查到的 2026-11-13 `napi_build_skb()` multi-descriptor 修复，针对的是包含 `napi_build_skb()` 的较新 STMMAC RX 代码路径。上面核对的 Linux stable v6.12.81 和 unifreq Rockchip v6.12.81 两份文件中均没有 `napi_build_skb()` 调用，而使用 `napi_alloc_skb()`。因此，**不能把该 11 月 13 日补丁当作当前 6.12.81 故障的直接解释**。补丁原文：[2026-11-13 stmmac patch](https://lore-kernel.gnuweeb.org/b4-sent/20261113-stmmac-rx-skb-fail-v1-1-fcaae89f2d2c%40gmail.com/T/)。

同理，先前提到的 `napi_build_skb()` 失败后 page 回收指针未清理问题，不能直接套用到上述 v6.12.81 代码。该版本中已检查到的普通 page recycle 分支会将 `buf->page` 置为 NULL；而 skb 分配失败分支并没有先 recycle 当前 page。必须以实际构建源码为准，不能把其他较新代码的缺陷移植成当前故障结论。

### 20.5 当前最值得验证的两个候选

在暂不考虑 XDP/AF_XDP 的前提下，普通 RX 路径中最直接的 `rx_dropped` 来源是 `napi_alloc_skb()` 分配失败。若设备确实挂载了 XDP 程序，XDP_CONSUMED 也会增加该计数。AF_XDP zero-copy 分支另有两种计数来源，但需要相应 XSK socket/pool 活动。

所以，现阶段不能直接宣布“67 次 skb 分配失败”；必须先确认：

1. eth0 是否挂载 XDP 程序。
2. 是否存在 AF_XDP socket / XSK pool。
3. 采集时是否有内存分配失败或 memory pressure 证据。
4. 设备实际运行的 Ophub 内核构建究竟来自哪个源码仓库、commit 和补丁集合。

### 20.6 计数器语义补充

在上述 v6.12.81 源码中：

- `rxq_stats->napi.rx_packets`：普通 RX 成功交给 GRO 的 packet 数。
- `rxq_stats->napi.rx_pkt_n`：NAPI 处理计数 `count`，其统计口径不是成功交付协议栈的 packet 数；多 descriptor frame、错误/丢弃分支会影响 count 的含义。
- `priv->xstats.rx_dropped`：独立的驱动丢弃累计值。
- `stmmac_get_stats64()` 分别读取/赋值上述统计。

因此，不能用 `rx_pkt_n`、netdev `rx_packets`、MMC RX framecount 三个数相等或不等，直接推断 67 次丢弃发生在哪个分支。当前快照中它们恰好接近/相等，仍需结合采集时间和分支状态解释。

### 20.7 本轮结论

- 已从 v6.12.81 候选源码列出全部直接增加 `rx_dropped` 的主要分支。
- 目前最优先排查的是普通 RX 的 `napi_alloc_skb()` 分配失败路径，以及是否存在 XDP/AF_XDP 相关分支。
- CRC、FIFO、VLAN、FCS、DMA fatal error 不是这份 v6.12.81 源码中普通 `rx_dropped` 计数的直接增加位置。
- 尚未取得设备 Image 对应的精确源码 commit；源码候选与实际运行二进制的逐字节对应关系仍未验证。
- 未执行设备配置修改、驱动修改或软件安装。

