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



## 8. 2026-11-24 补充实机证据：运行环境、实际驱动绑定与设备树

本节补充用户随后提供的完整实机命令输出，用于修正早期记录中驱动名称不够准确的问题，并补充 SoC、内存、存储布局及 GMAC 设备树参数。证据仍仅适用于本次原版 Armbian 6.1.65 混合启动环境。

### 8.1 系统、SoC 与内存

采集时间：2026-11-24 11:10:33 CST。

- `uname -a`：Linux `armbian`，`6.1.65-ophub`，aarch64；构建标识 `#1 SMP Sun Dec 3 05:14:23 EST 2023`。
- Device Tree root model：`Panther X2`。
- Root compatible：`panther,x2`、`rockchip,rk3566`。
- CPU：4 cores，ARMv8，CPU part `0xd05`（Cortex-A55）。
- `MemTotal`：4,024,088 kB；`MemAvailable`：3,732,672 kB。

### 8.2 启动参数与存储布局

`/proc/cmdline`：

```
root=UUID=ddcbfa1d-95e7-4863-97c8-ec9b7767968b rootwait rootfstype=ext4 rootflags=rw,errors=remount-ro bootsplash.bootfile=bootsplash.armbian earlycon console=ttyS02,1500000 console=tty0 consoleblank=0 loglevel=7 ubootpart=1ef0258e-6807-493d-bb0c-a2903d5d5988 usb-storage.quirks=0x2537:0x1066:u,0x2537:0x1068:u net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1
```

设备及挂载关系：

| 设备 | 容量/分区 | 实测用途 |
|---|---|---|
| TF `mmcblk0` | 7.4G | TF 卡 |
| `mmcblk0p1` | 255M ext4 | TF 第一分区 |
| `mmcblk0p2` | 7.1G ext4 | 根文件系统 `/`，同时挂载 `/var/log.hdd` |
| eMMC `mmcblk1` | 29.1G | eMMC |
| `mmcblk1p1` | 255M ext4 | 挂载为 `/boot` |
| `mmcblk1p2` | 28.9G | 未挂载 |
| `mmcblk1boot0/1` | 各 4M | eMMC boot 分区 |
| `zram0` | 1.9G | swap |
| `zram1` | 50M | `/var/log` |

**启动链证据边界：** 当前运行环境明确为 TF 根文件系统 + eMMC `/boot` 的混合布局。上述挂载信息不能单独证明 BootROM、SPL、U-Boot、Kernel 和 DTB 每一个阶段的实际加载来源；尤其不能据此声称本次为 TF 独立启动。后续 B1 必须单独审查启动链及 eMMC 写入风险，不得写入 eMMC。

### 8.3 Ethernet 实际驱动绑定（修正早期记录）

- `eth0`：UP、LOWER_UP；parent device `fe010000.ethernet`；8 TX queues、8 RX queues；altname `end0`。
- 运行时平台驱动 sysfs 路径：`/sys/bus/platform/drivers/rk_gmac-dwmac`。
- PHY 驱动 sysfs 路径：`/sys/bus/mdio_bus/drivers/RTL8211F Gigabit Ethernet`。
- PHY ID：`0x001cc916`；PHY address：0。
- `ethtool eth0`：1000Mb/s、Full Duplex、autoneg on、Link detected yes、external transceiver。
- 本次计数器：RX 484361 bytes / 6797 packets，errors 0、dropped 0；TX 90413 bytes / 1232 packets，errors 0、dropped 0、carrier 0、collisions 0。
- Kernel log：GMAC 节点 `fe010000.ethernet` 初始化；随后识别 RTL8211F（日志设备名 `stmmac-0:00`），配置 `phy/rgmii`，链路升至 1Gbps/Full。

**名称纠正：** 早期本报告引用 `ethtool -i` 的 `st_gmac` 字符串。后续实机 sysfs 绑定证据明确显示平台驱动为 `rk_gmac-dwmac`。因此本项目比较驱动绑定时应以平台驱动 sysfs 路径 `rk_gmac-dwmac` 为准；`stmmac-0:00` 是日志中的 MAC/MDIO 设备命名，不应误认为平台驱动名。此前 `st_gmac` 记录保留为原始工具输出，不再作为最终平台驱动识别结论。

### 8.4 GMAC Device Tree 实测参数

运行设备树路径：`/sys/firmware/devicetree/base`。

GMAC 节点：`/ethernet@fe010000`。

| 属性 | 实测值 |
|---|---|
| GMAC compatible | `rockchip,rk3568-gmac`、`snps,dwmac-4.20a` |
| reg | base `0xfe010000`，size `0x10000` |
| status | `okay` |
| phy-mode | `rgmii` |
| phy-handle | phandle `0x4f` |
| clock_in_out | `input` |
| tx_delay | `0x30` |
| rx_delay | `0x10` |
| phy-supply | phandle `0x18` |
| rockchip,grf | phandle `0x1d` |
| snps,axi-config | phandle `0x44` |
| snps,reset-gpio | 原始 cell：`00 00 00 4e 00 00 00 01 00 00 00 01` |
| snps,reset-delays-us | `0`、`20000`、`100000` |
| interrupt-names | `macirq`、`eth_wake_irq` |

其他已观察内容：
- GMAC 节点 pinctrl-0 引用 phandle `0x48` 至 `0x4d`。
- 时钟、assigned-clocks、clock parents 的原始 big-endian cells 已采集，但本次没有完成符号解码；不对具体时钟频率或父时钟关系作推断。
- MDIO 子节点为 `ethernet-phy@0`；运行时 PHY 地址及 ID 已由 sysfs/ethtool 证实。
- Root compatible 中的 `rockchip,rk3566` 标识 SoC/板级兼容信息；GMAC 子节点的 `rockchip,rk3568-gmac` 是该 MAC 节点的 compatible 字符串，不能据此把整板误判为 RK3568。

### 8.5 相关内核日志与无关告警的边界

- GMAC 节点 `fe010000.ethernet` 初始化约在启动 2.394s。
- 日志显示 TX delay `0x30`、RX delay `0x10`，RGMII，clock input from PHY。
- RTL8211F PHY 约在 16.607s 被识别。
- 1Gbps/Full 链路约在 21.255s 建立。
- 日志出现 `IRQ eth_lpi not found` 警告，但随后 GMAC 初始化成功并建立千兆全双工链路；不能仅凭该警告判定网口失败。
- brcmfmac firmware failure 属于无线部分；项目 A 已排除无线/蓝牙，不纳入本次有线网口判断。
- rockchip-drm 的 VOP 提示与本次 Ethernet 验证无关。

### 8.6 当前最终基准结论

在原版 Armbian 6.1.65 的本次混合启动环境中，已验证以下完整有线 IPv4 路径：

`Panther X2 / RK3566 → fe010000 GMAC → rk_gmac-dwmac → RTL8211F (0x001cc916) → RGMII → 1000Mb/s Full Duplex → DHCP IPv4 → 192.168.9.1 网关 → 外部 IPv4 → DNS 查询成功`

其中：
- **已验证：** 原版系统启动、运行时 GMAC 平台驱动绑定、RTL8211F PHY 识别、RGMII、千兆全双工、DHCP、网关 IPv4、外部 IPv4、DNS 查询。
- **已验证但需限定：** TF 根文件系统与 eMMC `/boot` 的混合挂载布局。
- **未验证：** BootROM/SPL/U-Boot/Kernel/DTB 各阶段完整加载来源；TF 独立启动；IPv6 端到端；吞吐与长期稳定性。
- **未外推：** 本记录不代表 B1/B2 或 6.18.y 已经通过任何实机启动或网络测试。

本节作为 2026-11-24 补充证据，优先用于后续驱动绑定和设备树对照；早期记录中的 `st_gmac` 字符串保留作原始输出历史，但平台驱动最终识别以本节运行时 sysfs 证据为准。
