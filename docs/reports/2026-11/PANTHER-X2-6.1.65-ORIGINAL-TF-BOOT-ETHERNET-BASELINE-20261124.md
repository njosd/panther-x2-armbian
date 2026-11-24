# Panther X2 原版 Armbian 6.1.65 TF 启动与有线 IPv4 实测记录

- 测试日期：2026-11-24
- 目标设备：Panther X2 / RK3566
- 测试对象：用户明确确认的原版 Armbian 6.1.65 系统
- 启动介质：TF 卡启动（不是本项目 B1 最小系统）
- 系统标识：Armbian-unofficial 24.2.0-trunk Jammy
- 内核：Linux 6.1.65-ophub
- 测试范围：原版系统启动后，板载有线 Ethernet 的链路、DHCP、IPv4 网关、外部 IPv4 与 DNS
- 本记录性质：用户提供的 Panther X2 串口实机输出；只记录观察事实，不外推至 B1

## 1. 启动与系统身份

串口登录信息及系统 banner 显示：
- Armbian-unofficial 24.2.0-trunk Jammy
- Linux 6.1.65-ophub
- uptime 约 6 分钟
- 内存总量约 3.84 GiB
- 系统 banner 显示 IPv4 地址 192.168.9.187

用户明确指出：这是原版 6.1.65 在 TF 卡实际启动的效果，不是正在打包构建的 B1 最小系统。B1 workflow 当时仍处于打包/构建过程中。

本次启动日志另显示：
- 根文件系统来自 TF 的 `mmcblk0p2`，ext4 挂载成功；
- `/boot` 来自 eMMC 的 `mmcblk1p1`；
- 因此本次是 TF rootfs 与 eMMC /boot 组合的实际运行状态。此处仅按日志记录，不推断更早期 BootROM/SPL 的完整来源链。

## 2. Ethernet 接口与地址

`ip -br link`：
- `eth0` 为 `UP`，标志包含 `LOWER_UP`；
- MAC 显示为 `be:5b:25:b3:b3:77`。该值仅为本次现场输出，不作为公开仓库中的长期设备身份数据；
- `wlan0` 为 DOWN，本项目 A 排除无线部分，不分析。

`ip -br addr`：
- `eth0` IPv4：`192.168.9.187/24`
- 同时存在两个全局 IPv6 地址和一个 link-local IPv6 地址；本次没有进行 IPv6 通信验收。

`ip route`：
- 默认路由：`default via 192.168.9.1 dev eth0 proto dhcp metric 100`
- 直连网段：`192.168.9.0/24 dev eth0`
- 存在 `169.254.0.0/16` link-scope 路由。

据 DHCP 来源标记及地址/默认路由结果，可确认原版系统的 eth0 已取得 DHCP IPv4 配置。

## 3. 驱动与物理链路

`ethtool -i eth0`：
- driver：`st_gmac`
- version：`6.1.65-ophub`
- supports-statistics：yes
- supports-test：yes
- supports-register-dump：yes

`ethtool eth0`：
- Supported / Advertised link modes 包含 10/100/1000BASE-T；
- Link partner advertised link modes 包含 10/100/1000BASE-T；
- Speed：`1000Mb/s`
- Duplex：`Full`
- Auto-negotiation：`on`
- Link detected：`yes`
- PHYAD：0
- Port：Twisted Pair
- Transceiver：external

此前同一次启动内核日志已显示 RTL8211F Gigabit Ethernet PHY 绑定及链路升至 1Gbps/Full。结合本次 ethtool 输出，原版 6.1.65 当前实机链路状态确认正常。

## 4. IPv4 通信实测

### 4.1 hEX 网关

命令：
```sh
ping -c 4 -W 2 192.168.9.1
```

结果：
- 4 packets transmitted
- 4 packets received
- 0% packet loss
- RTT min/avg/max/stddev：0.600 / 0.668 / 0.766 / 0.065 ms

结论：Panther X2 eth0 到局域网 hEX 网关的 IPv4 ICMP 通信成功。

### 4.2 外部 IPv4

命令：
```sh
ping -c 4 -W 2 223.5.5.5
```

结果：
- 4 packets transmitted
- 4 packets received
- 0% packet loss
- RTT min/avg/max/stddev：15.274 / 15.541 / 15.792 / 0.187 ms

结论：原版系统通过默认 IPv4 路由访问外部 IPv4 地址成功。

### 4.3 DNS

命令：
```sh
getent ahostsv4 www.baidu.com
```

返回 IPv4 地址：
- 36.152.44.93
- 180.101.49.44
- 180.101.51.73
- 36.152.44.132

结论：系统 NSS/getent 查询链路成功解析 `www.baidu.com` 的 IPv4 地址。该结果证明本次 DNS 查询成功，不单独证明所用 DNS 服务器身份、查询协议或完整 DNS 故障转移行为。

## 5. 终端回显现象

串口回显中出现可见的 ANSI 控制序列文本，例如：
- `ESC[...` 颜色与光标控制序列；
- `ESC[?2004h` / `ESC[?2004l` bracketed-paste 模式切换；
- `ESC[K`、`ESC[J` 等行/屏幕清理控制序列。

这些内容出现在终端回显/粘贴记录中，但命令本身均实际执行，输出结果完整可辨。当前判断是终端客户端未正确解释部分 ANSI/VT 控制序列，或终端类型/串口终端模式不匹配；这属于终端显示/交互问题，不是 Ethernet 故障证据。尚未确定具体终端应用及其版本，因此不在本记录中预设修复方法。

## 6. 结论与证据边界

### 已实机验证（仅限原版 Armbian 6.1.65 TF 启动环境）
- 原版 6.1.65 系统成功进入用户空间并可登录；
- `st_gmac` 驱动已加载；
- eth0 为 UP/LOWER_UP；
- 千兆全双工链路已建立；
- DHCP 获取 IPv4 地址 192.168.9.187/24 及默认网关 192.168.9.1；
- 网关 ICMP、外部 IPv4 ICMP、域名 IPv4 解析均成功。

### 尚未验证
- IPv6 端到端通信；
- Ethernet 吞吐、双向性能、长时间稳定性、压力及错误计数；
- 终端应用/版本与其正确 ANSI、VT100/VT220、bracketed-paste 设置；
- 其他内核版本或其他系统组合的行为。

### 明确禁止的推论
本记录**不构成 B1 通过证据**。它不证明 B1 的 Kernel、Panther X2 DTB、独立 RAM initramfs、静态 BusyBox 或最小网络组件已经构建、启动或连通。B1 当时仍在打包构建，必须等待其自身 artifact 审计与目标硬件验证。

## 7. 对项目 A 的参考价值

本记录作为原版 6.1.65 的实机正向网络行为基准，供后续比较：
- 同一 Panther X2 硬件在原版 6.1.65 完整系统环境下，板载有线 Ethernet 可以达到 DHCP、网关、外部 IPv4 和 DNS 全通；
- 后续最小系统实验必须独立证明每一层能力，不得把本记录的结果转记为 B1/B2/B3 通过；
- 若后续候选系统表现不同，应比较各自 Kernel/DTB/启动链/用户空间与网络管理配置，按项目路线逐层定位，不预先归因或直接制作补丁。

