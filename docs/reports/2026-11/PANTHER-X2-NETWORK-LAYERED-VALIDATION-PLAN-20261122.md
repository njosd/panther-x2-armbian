# Panther X2 项目 A：板载有线网络分层验证与归因方案

- 日期：2026-11-22
- 范围：仅 Panther X2 板载有线千兆 Ethernet；Wi-Fi/无线、蓝牙、USB/PCIe 外接网卡全部排除。
- 目标：从可重复的 clean RAM Linux 基线出发，以实际双向报文证据逐层打通网络；不以源码推测、驱动 probe、carrier 或单向计数器代替连通性证明。
- 原则：继承项目 B 历史成果，不重做已完成实验；单变量/最小依赖闭包；失败即停；保留最近通过检查点。

## 1. 历史正向对照：Linux 6.1.116

仓库既有 6.1.116 基线归档记录：
- 运行内核为 6.1.116-ophub，Panther X2 运行时 FDT/磁盘 DTB身份已核对。
- eth0 由 rk_gmac-dwmac 驱动，平台节点 fe010000.ethernet。
- PHY 为 RTL8211F，PHY ID 0x001cc916，RGMII；最近一次验证为 1000Mbps Full Duplex。
- 用户确认 DHCP 获得 LAN IPv4 /24，ping hEX 网关及 iMac 均为 0% 丢包；RX/TX errors、dropped、carrier errors 为 0。
- 归档同时包含脱敏后的原始网络采集文本、运行时 FDT、磁盘 DTB、内核配置和 dmesg。

证据边界：
- 上述 6.1.116 Linux 正常网络是项目 A 的正向控制（positive control），可用于核对目标板真实有效的 DTB、驱动、PHY 和网络行为。
- 旧归档并未完整证明当时实际执行的所有前级 SPL/proper 二进制身份；不得把 6.1.116 Linux 正常结果包装成与当前 eMMC SPL + JP proper 完全同链的同条件试验。
- 原版 U-Boot 日志曾显示 `Net: No ethernet found.`，而其后 Linux 6.1.116 能独立初始化网卡并正常通信。这支持“U-Boot 未枚举/未初始化 Ethernet 不必然阻止 Linux 重新初始化”的架构结论。
- 这不能单独证明当前 JP proper 在 DHCP 时发生 Data Abort 后，硬件状态必然不影响紧接着启动的 Linux。当前实测在异常后通过断电重启恢复；冷启动会重新经历启动链，不能冒充同一启动周期内的交接连续性证明。
- 既有混合链记录另载：JP proper 枚举 GMAC 后，Linux PHY/千兆链路曾正常，但 DHCP/IP 未恢复。该历史结果必须与 6.1.116 正向基线分开记录，不能混成一次测试。

## 2. 当前 U-Boot 网络基准结论

2026-11-22 当前 eMMC 前级 SPL + TF JP-TvBox U-Boot proper：
- proper 版本：U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)。
- `mdio list`、`mii device` 曾枚举 `ethernet@fe010000`；MII/MDIO 只读查询地址 0–4未取得有效 PHY 标准寄存器响应（多项返回 0xffff）。
- proper 内置 FIT FDT 静态审计身份为 Radxa ROCK3 Model C，不是 Panther X2 专用 FDT。
- 在临时设置 `autoload=no` 并读回确认后执行 `dhcp`，UART 先出现 `EQOS_DMA_MODE_SWR stuck`，随后出现 AArch64 Synchronous Abort / Data Abort，最后停在 `Please RESET the board`。没有 DHCP 成功、DHCP 报文往返、TFTP 下载或网络连通结果证据。
- 实体 Reset 短按未恢复；断电重启后重新进入同一 proper。重启后 `ethaddr` 保持 `16:70:f6:c8:b2:95`；`ethact`、`ethprime`、`autoload`、`ipaddr`、`serverip`、`gatewayip`、`netmask`、`bootfile` 均未定义。
- 当前会话已读取 `bootcmd`、`bootdelay=0`、`distro_bootcmd`、`boot_targets=nvme mmc1 mmc0 usb0 pxe dhcp`、`bootcmd_nvme/mmc1/mmc0/usb0/pxe/dhcp`。PXE/DHCP 自动启动路径包含网络初始化、脚本获取/执行、TFTP 和潜在 bootefi；不得让设备无人值守自动运行这些路径。
- 当前 DHCP 测试已挂起；禁止重复执行 `dhcp` 或以此开展 U-Boot GMAC 根因专项。U-Boot 网络连通性标记为“未完成/因 DMA 初始化异常暂停”，不是“硬件损坏”或“项目失败”。

## 3. 对照实验逻辑

必须把三种问题分开：
1. U-Boot 自己是否能使用 Ethernet；
2. U-Boot 对硬件的初始化/异常是否影响 Linux 后续重新初始化；
3. Linux 自己的 Ethernet 组件链是否能建立双向通信。

6.1.116 正向控制用于回答“板级硬件和已验证 Linux 路径曾经可用”；当前固定启动链 + 6.1.116 匹配 Kernel/DTB/initramfs 的受控启动，可用于检验“当前启动固件组合下 Linux 是否仍能独立初始化”。它是冷启动对照，不是同一次 U-Boot DMA 崩溃后无复位接管的证明。若要证明同一启动周期的遗留状态影响，必须另有可安全复现且不崩溃的控制实验；当前不为此重试 DHCP，也不修复 U-Boot 网络路径。

## 4. B1/B2/B3 网络验证阶段

### B1：纯 RAM、无网络基线
- Kernel 网络栈与所有 Ethernet/GMAC/MDIO/PHY 驱动关闭；不包含网络用户空间工具、固件、服务或模块。
- MMC/block、USB、无线/蓝牙等非必要设备栈排除；Linux 以 RAM initramfs 运行。
- 验证仅限启动、UART console、CPU/内存、initramfs/BusyBox 基本用户空间。
- B1 不验证网络，也不预置网络参数。B1 的意义是建立可重复、可回退的无网络参照。

### B2：最小网络路径，逐个最小依赖闭包
每个构建必须冻结 Kernel config、Kernel/DTB/initramfs 哈希、启动参数和唯一变化项。每个阶段先静态审计 Kconfig/Makefile/驱动依赖，再构建，不猜参数、不同时改多个子系统。

建议的验证顺序（依赖关系须以目标源码树和最终 .config 实际解析结果确认，不将此表当作未经审计的硬编码配置）：
1. 网络核心/协议栈最小闭包（仅为后续测试所必需；无物理网卡驱动时不宣称可通信）。
2. Ethernet netdev + stmmac/DWMAC Rockchip MAC 驱动最小闭包。
3. MDIO/PHYLIB/目标 PHY 驱动最小闭包；PHY 型号及地址依据 6.1.116 正向基线、Panther X2 DTB 与实机 Linux 证据核对。
4. 目标板最终 DTB 中 MAC/clock/reset/pinctrl/PHY 连接描述；以 Panther X2 运行时 DTB/已验证磁盘 DTB 为证据源，逐项核对后再采用，不复制 ROCK3C FDT 参数。
5. 接口初始化与 Link/速率/双工确认。
6. 静态 IPv4（先不启用 DHCP/DNS/路由服务），ARP 双向。
7. 同网段 ICMP 双向，再测试网关 ICMP；随后才考虑 DHCP。
8. TCP、UDP 独立测试双向收发。

若某个驱动的 Kconfig 依赖必须同时开启多个符号，则将其视为一个有依据的“最小依赖闭包”实验变量，记录全部符号及来源；不得假称只改变一个 Kconfig bit。

### B3：传输层验收
- TCP：至少一个已知 LAN 对端监听端口；分别验证连接建立、双向 payload、关闭和重复连接。
- UDP：分别验证单向、反向和双向 payload；记录序号/长度/丢包情况。
- 不以 ping 成功代替 TCP/UDP 验收。

## 5. 每层证据要求：两端抓包与接收确认

每个数据路径测试至少保留：
- Panther X2 发送端：命令、返回值、接口/路由/邻居状态、内核日志、驱动计数器前后差值。
- 对端（优先 LAN iMac 或 hEX 可观测点）：抓包确认报文真实到达、源/目的 MAC/IP、协议字段及响应。
- Panther X2 接收端：抓包或协议栈/套接字证据确认返回包真正进入本机并被处理。
- 时间戳必须对齐。计数器增加只作辅助，不作为线上报文已成功的单独证据。

故障边界解释：
- TX 计数增加但对端无报文：不能认定已上网线；停在本机发送/MAC/DMA/PHY路径边界。
- 对端收到请求但未响应：检查对端配置和响应条件，不先改 Panther 驱动。
- 对端已发响应而 Panther 未收到：停在回程链路/MAC/DMA/中断/接收路径边界。
- Panther 已收到帧但协议/应用未处理：再检查本机协议栈、地址、路由或套接字。
- 每次失败只提出一个最有区分力的下一项验证；不叠加配置。

## 6. 参数来源与变更纪律

- MAC：使用已完成的 MAC 来源调查结论；只核对最终 FDT/接口映射，不重开来源调查。
- MAC 寄存器/资源地址：Panther X2 SoC/板级资源、目标驱动匹配和目标 DTB；不从 ROCK3C 猜。
- 时钟、reset、pinctrl、电源：Panther X2 运行时 DTB/磁盘 DTB、驱动资源获取路径和实际 probe 日志；DTS 属性不等于寄存器动作已发生。
- PHY 型号/ID/连接模式：6.1.116 已验证的 RTL8211F/PHY ID/RGMII 作为强参照，仍需确认目标内核驱动 attach 到同一板级 PHY。
- PHY 地址：依据有效 MDIO 读数或 Linux PHY attach 日志，不从 `phy@0` 节点名猜。
- IP/掩码：使用已知 LAN 规划和未占用测试地址；先静态配置，不引入 DHCP/DNS。
- MTU/速率/延迟/时钟等特殊参数：先使用已验证板级默认值；没有报文/日志证据不调参。

每次改动必须记录唯一目的、基线、唯一变化或最小依赖闭包、预期、停止条件、完整日志、镜像哈希、双端报文。失败立即停止并回到最近通过的检查点。

## 7. 进入条件与当前下一步

- B1 实机启动前仍必须通过独立的 PRE-HANDOFF READY 清单；本方案不绕过 U-Boot 发送端核查阶段门。
- 当前 U-Boot DHCP 已挂起，不再尝试；U0 在断电重启后只完成部分快照恢复，需补核对必要设备枚举并归档异常。
- 下一步不是修改 GMAC 参数，也不是直接启动 Linux；先把本轮 U-Boot 异常、重启后环境快照、6.1.116 正向对照和分层方法归档，再继续 PRE-HANDOFF 静态审计。
