# Panther X2：JP idbloader（DDR V1.10）实机启动与 DHCP 故障差分（2026-11-19）

- 日期：2026-11-19（以用户上传文件时间为准）
- 设备：Panther X2 / RK3566 / 4 GiB LPDDR4
- 启动介质：eMMC LBA64–667 为 JP-TvBox idbloader；TF 保留原 JP u-boot.itb、Armbian /boot 与 rootfs
- Linux：6.12.81-rk35xx-ophub
- 本报告用途：记录首次实际执行 JP SPL/DDR V1.10 的启动结果，并与 2026-11-16 至 2026-11-18 已归档网络及启动证据差分
- 隐私：公开报告不记录完整运行时 MAC、完整 IPv6 地址或 NetworkManager UUID；原始 UART 启动日志本身未包含运行时 MAC 地址

## 1. 本次实验范围及介质变更

本轮唯一启动链变量变更为：将 JP-TvBox `idbloader.img` 写入 eMMC 用户区 LBA64，覆盖 LBA64–667（604 sectors / 309,248 bytes）。写入前确认目标为 eMMC（DF4032，CID `450100444634303332010f37d8066500`），原 LBA660–667 为全零；写入后从 eMMC 回读 604 sectors，`cmp` 无差异，SHA-256 与源镜像一致：

`e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`

TF 卡未改写；TF 上的 JP `u-boot.itb`（LBA16384）及 Linux 启动文件保持不变。此次不是重复写入或重新校验，而是对已完成写入的首次实机启动进行记录。

## 2. 2026-11-19 启动日志：已验证事实

### 2.1 DDR / SPL

- DDR 输出：`DDR Version V1.10 20210810`。
- LPDDR4，识别容量 4096MB，CS0/CS1 双 rank。
- DDR 训练流程完成，频率依次 324、528、780、1056MHz，最终 1056MHz。
- SPL：`U-Boot SPL 2017.09-armbian (Nov 12 2023 - 15:05:14)`。
- SPL 输出 `Trying to boot from MMC2`。
- ATF、U-Boot proper、FDT 等镜像校验均输出 `+ OK`，随后跳转 ATF。
- 本次已实际验证 JP idbloader 中 DDR V1.10 在 Panther X2 上完成初始化，并继续进入后续启动链。

### 2.2 ATF / U-Boot proper

- BL31：`v2.3-167-g81e0b993a-dirty`，构建日期 2021-09-06。
- U-Boot proper：`U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`。
- U-Boot board model：`Radxa ROCK3 Model C`。
- DRAM：4 GiB。
- U-Boot proper：`Net: eth1: ethernet@fe010000`。
- proper 通过 TF/SD 后续启动链读取 `/boot.scr`、内核、initrd、DTB，执行启动脚本并进入 Linux。

### 2.3 Linux / GMAC

- Linux 启动成功：`6.12.81-rk35xx-ophub`。
- Linux machine model：`Panther X2`。
- Linux 根文件系统及 /boot 仍来自 TF。
- GMAC1：`fe010000.ethernet`，Linux 接口名 `eth0`。
- PHY：RTL8211F，MDIO 地址 0。
- RGMII 模式初始化成功；日志显示 TX delay 0x30、RX delay 0x10。
- Link Up：1000Mbps / Full Duplex，flow control rx/tx。
- 系统启动到 `armbian login: root`，本次完整启动成功。

说明：U-Boot 的 `eth1` 与 Linux 的 `eth0` 是两个阶段各自的接口编号；同一 GMAC1 地址 `fe010000`，不构成接口丢失或枚举失败。

## 3. 本次 DHCP / MAC 结果

依据同一启动周期用户随后提供的只读输出：

| 项目 | 结果 |
|---|---|
| Linux eth0 运行时 MAC | `e6:e0:02:xx:xx:xx`（公开脱敏；完整值仅保留在当前对话证据） |
| IPv4 地址 | 无 |
| IPv4 路由表（`ip route`） | 空 |
| NetworkManager DHCPv4 | 45 秒事务超时，`ip-config-unavailable`，`state changed no lease` |
| IPv6 地址 | 已获得多个 2409: 前缀全球单播地址及 fe80:: 链路本地地址 |
| 物理链路 | 1000Mbps / Full，Link detected yes |

DHCP 日志明确显示第一次 DHCPv4 transaction 超时，NetworkManager 随后再次发起事务并记录 no lease；随后连接状态进入 IPv6 激活成功。因此本次的 `CONNECTED_GLOBAL` 不能解释为 IPv4 DHCP 成功。

本次被上传的 DHCP 状态采集没有运行 tcpdump，也没有记录本次 Discover/Offer 的逐包情况。因此：
- 已验证：本次 IPv4 DHCP 未取得租约。
- 未验证：本次 DHCP Discover 是否到达 Panther 的 outgoing packet capture、是否真正从 PHY 线上发出、是否到达 hEX。
- 不把 2026-11-16 的 Discover 抓包结果移植成 2026-11-19 本轮的逐包证据。

## 4. 与既往启动日志差分

### 4.1 2026-11-18 暂停现场（旧 eMMC SPL）

既往 2026-11-18 UART 日志显示：
- DDR：`DDR Version V1.13 20220218`，LPDDR4 4GiB，最终 1560MHz。
- SPL：`U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`。
- U-Boot proper：Nov 12 2023 build，`Model: Radxa ROCK3 Model C`。
- proper 输出 `Net: eth1: ethernet@fe010000`。
- 当时日志在 U-Boot autoboot 被 Ctrl+C 中断，没有进入 Linux；因此那份日志不能作为当时 Linux DHCP 结果的证据。
- 随后的启动链分析和 eMMC LBA64 替换实测，确认此前实际执行的是旧 SPL/DDR V1.13；本轮则已执行 JP SPL/DDR V1.10。

### 4.2 2026-11-19 本轮

- DDR 从 V1.13 / 1560MHz 变为 V1.10 / 1056MHz。
- SPL build 从 Apr 23 2023 变为 Nov 12 2023。
- BL31 版本/构建日期保持相同。
- U-Boot proper 版本、构建时间、板型字符串保持相同。
- U-Boot proper 仍枚举同一个 GMAC1：`Net: eth1: ethernet@fe010000`。
- 本轮新增完整 Linux 启动及 GMAC/PHY/link 证据。
- 需要补充区分：11 月 18 日报告已记载过一次 JP U-Boot proper 启动 Linux 后 PHY/千兆链路正常、DHCP/IP 未恢复的实机结果；11 月 18 日那份单独的暂停现场 UART 日志本身则停在 U-Boot prompt，没有 Linux/DHCP 记录。本轮是首次确认 JP idbloader / DDR V1.10 也实际执行后，DHCP 仍未恢复。

这次差分证明：更换 eMMC idbloader 后，JP SPL/DDR V1.10 被实机执行并成功进入原有后续链；但 DHCP 故障并未随 SPL/DDR 替换消失。

## 5. 与既往 DHCP / MAC 测试差分

### 5.1 2026-11-16 至 2026-11-17 已有证据

既有 `GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md` 记录：
- Linux 6.12.81 本机曾捕获 DHCP Discover：0.0.0.0:68 → 255.255.255.255:67。
- 同期 hEX 未观察到 Panther DHCP Discover；其他 LAN 设备 DHCP 正常。
- 当时已确认链路为 1000Mbps Full，RTL8211F、RGMII、TX/RX delay、GRF 和主要 GMAC 时钟均已完成检查。
- TX 软件完成计数、netdev TX 与 MMC TX 在同一启动生命周期的后续快照中一致；已撤销先前因跨生命周期计数造成的“TX 计数严重不一致”结论。
- 6.12.69 是源码比较基线，不是 Panther 实机运行内核；不能把它描述为本轮切换过的内核。
- 运行时 MAC 以 E6 前缀开头，而 eMMC Vendor Storage 记录的板载 GMAC 地址以 86 前缀开头；报告明确指出 MAC 来源链仍未闭合，不能单凭地址不一致认定 DHCP 根因。
- 已知此前 U-Boot 读取的是 TF 卡 Vendor 数据，而不是 eMMC Vendor 数据。

### 5.2 本轮新增对照

- 本轮 eth0 运行时 MAC 与此前实机记录的 E6 前缀运行时地址相同（本报告脱敏）。
- 新 SPL/DDR V1.10 并未让运行时 MAC 回到 eMMC Vendor Storage 中的板载 86 前缀地址。
- 既往 11 月 17 日记录和本轮都观察到 E6 前缀运行时 MAC；但因旧报告只保留前缀，不能断言完整 MAC 相同。
- DHCP 仍无 IPv4 lease。
- 本轮没有新的 Panther/hEX 同步抓包，也没有本轮 DHCP Discover 的线上帧源 MAC 证据。

因此，当前可确认的是：**更换 eMMC SPL/DDR 后，Linux 运行时 MAC 身份线索和 DHCP 失败现象均未发生可见改变。** 这说明故障不因 SPL/DDR V1.10 替换而自动消失；但还不能据此排除 SPL/U-Boot 对 MAC 来源、GMAC 状态或报文路径的其他影响。

## 6. 结论更新

### 已验证

1. eMMC JP idbloader 写入 LBA64–667，写后回读与源文件逐字节一致。
2. Panther X2 实机执行 DDR V1.10 / SPL，识别 4GiB LPDDR4 并完成训练，进入 ATF/U-Boot。
3. JP SPL 成功从 MMC2/TF 路径加载后续 U-Boot proper。
4. U-Boot proper 成功执行 TF 上启动脚本，Linux 6.12.81 成功启动。
5. U-Boot proper 仍枚举 GMAC1；Linux RTL8211F PHY 初始化和 1Gbps Full 链路正常。
6. 本轮 IPv4 DHCP 仍无租约；IPv6 已获得全球单播地址。
7. 本轮运行时 MAC 为 E6 前缀；既往报告也记录 E6 前缀，但历史完整地址未保留，不能确认完整 MAC 一致。

### 未验证 / 不能推出

1. 本轮 DHCP Discover 是否真正从 PHY 线侧发出。
2. 本轮 DHCP Discover 的 Ethernet source MAC 及是否到达 hEX。
3. 运行时 MAC 从 TF Vendor、FDT、NVMEM、efuse 或其他路径最终取得的完整因果链。
4. DHCP 故障是否由 MAC 源地址不匹配、GMAC TX/RGMII/PHY 物理路径、交换网络过滤或其他原因造成。
5. DDR V1.10 与 V1.13 的性能/稳定性优劣；本轮只证明 V1.10 能启动，未进行内存压力或长期稳定性测试。

## 7. 后续研究边界（避免重复）

既往已经完成且不应无理由重复的项目：
- 更换网线后的 1Gbps 链路确认；
- RTL8211F PHY ID / MDIO 基本识别；
- Linux RGMII mode、TX/RX delay、GRF、pinctrl 和主要时钟只读核对；
- 同一生命周期 TX 软件/netdev/MMC 计数一致性核对；
- RX DMA / IRQ / NAPI 基本活动检查；
- 6.12.81 与 6.12.69 候选源码函数级对照；
- 旧 SPL 与 JP proper 的启动链身份确认；
- 本次 eMMC idbloader 写入与回读校验。

下一步若继续 DHCP 定位，应针对“同一个 DHCP Discover”建立 Panther outgoing / hEX ingress 同步证据，并记录二层源 MAC；不重复基础 DHCP、PHY、时钟或 DMA 测试，不先改 MAC 或网络配置。

## 8. 时间戳注意事项

本轮上传文件名日期为 2026-11-19，但用户提供的 `journalctl -b` 记录时间为 `Nov 16 13:13`。在确认系统时钟/NTP 前，不能把该 journal 时间当作真实的 11 月 19 日墙钟时间，也不能据此与外部抓包时间直接对齐。

## 9. 证据文件

- UART 原始启动日志：`evidence/boot/2026-11-19-panther-x2-jp-idbloader-uart.log`
- DHCP / 接口状态输出（公开版本已脱敏）：`evidence/network/2026-11-19-panther-x2-dhcp-ipv4-status.txt`
- 历史基线：`docs/reports/2026-11/GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md`
- 历史启动链差分：`docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
