# Panther X2 Ethernet 实际收发、IPv4 DHCP 与 IPv6 NDP 调查记录

- 整理日期：2026-11-17
- 设备：Panther X2（RK3566）/ Armbian；对端为 iMac；网关设备为 hEX
- 调查目标：定位 IPv4 DHCP Discover 未抵达 hEX、IPv6 已获得 RA/SLAAC 但双向通信不完整的共同故障边界
- 操作性质：只读取证与记录整理；未安装软件，未修改系统、网络、内核、驱动、设备树、U-Boot 或路由器配置
- 隐私处理：本文不包含任何实际 IPv6 地址或前缀；MAC 地址、实际 LAN IPv4 地址及设备唯一标识均不公开
- 状态：阶段性调查；实际 Ethernet 发送路径尚未定位到具体硬件/软件环节

> 本文记录 2026-11-17 同一轮 iMac 与 Panther 双端抓包，以及此前 DHCP/IPv6 检查。两台设备系统时钟不同，因此各自 tcpdump 的墙上时间戳不一致；用户确认两端抓包与 ping 测试是同时进行的。不能仅因时间戳不同而把它们视为不同测试轮次。

## 1. 当前总体结论

1. **IPv4 DHCPv4 未成功：** NetworkManager 曾报告 DHCP 配置失败；Panther 本机 tcpdump 能捕获 DHCP Discover（UDP 68 → 67，源/目的 IPv4 为未配置地址/广播地址）。既有 hEX 抓包未观察到 Panther 发出的 DHCP 报文；同一 LAN 其他设备 DHCP 正常。故障边界仍在 Panther 本机抓包点之后、hEX 收包之前，尚未证明具体丢包部件。
2. **IPv6 属于部分可用：** Panther 能收到 hEX 的 Router Advertisement，形成 SLAAC 全局地址和默认路由；但邻居解析与端到端通信不完整，不能判定 IPv6 已打通。
3. **Panther 接收方向有明确成功证据：** Panther 的 eth0 抓包收到 iMac 发来的 Neighbor Solicitation（NS），并观察到 Linux 随即生成 Neighbor Advertisement（NA）。
4. **Panther 发送方向存在关键疑点：** 同一轮双端抓包中，Panther 侧能看到 NA 发出；iMac 侧没有看到来自 Panther 的 NA，也没有看到 Panther 发出的单播 NS。Linux tcpdump 的发送方向抓包只能证明报文经过本机抓包点，不能证明报文已从 GMAC/PHY 物理发出。
5. **目前最值得验证的共同故障边界：** Linux 网络栈抓包点之后、对端实际收到 Ethernet 帧之前。优先验证 GMAC TX、RGMII/PHY 发送和交换链路；目前没有足够证据把故障归结为 TX DMA、PHY、驱动或 U-Boot 中的某一个。
6. **MAC 地址来源不属于本轮主线：** 运行时 MAC 的来源已在此前调查中追溯到 TF 卡；本报告不记录具体 MAC 值，也不将 MAC 差异作为当前 DHCP/NDP 故障的首要解释。可在主故障打通后再单独归档。

## 2. IPv4 DHCPv4 测试与结果

### 已有测试

- 检查 NetworkManager DHCPv4 状态，曾出现 `ip-config-unavailable`，最终网络连接只完成 IPv6 激活。
- 在 Panther 本机抓包，观察到 DHCP Discover：UDP 68 → 67，IPv4 源地址为未配置地址，目的地址为广播地址。
- 在 hEX 侧进行过抓包，既有结果未观察到 Panther 的 DHCP 报文。
- 同一 LAN 的其他设备可以正常自动获取 IPv4 地址。
- 更换网线后，物理链路恢复为 1000Mbps Full Duplex；千兆链路问题已解决，不再作为当前 DHCP 故障的默认解释。
- DHCP 基础检查、hEX 抓包、NetworkManager/Netplan/udev 和接口命名检查此前已完成，不应无理由重复。

### 证据边界

Panther 本机 tcpdump 捕获 Discover，证明报文到达 Linux 本机抓包点；不能证明它已由 MAC DMA 交给 PHY、通过 RGMII/MDI 发出并抵达 hEX。hEX 未观察到 Discover，将当前故障边界限定在本机抓包点之后、hEX 接收之前，但尚不能区分 GMAC、PHY、线缆/交换路径或其他因素。

## 3. IPv6 RA、SLAAC 与邻居状态

### 已验证

- Panther 收到 hEX 发出的 Router Advertisement（RA）。
- RA 包含一个 /64 前缀信息选项，设置 On-link 与 Autonomous 标志；实际前缀已从公开记录中省略。
- Panther 已生成 IPv6 SLAAC 地址并安装默认路由。
- Panther 的 `net.ipv6.conf.all.forwarding` 与 `net.ipv6.conf.eth0.forwarding` 均为 `1`。
- Panther 返回的 NA 带有 `router` 标志；这与 forwarding=1 的配置相符，本身不能据此认定为故障。
- Panther 邻居表中，对 iMac 的链路本地邻居项曾显示 `FAILED`；hEX 路由器邻居项曾显示 `STALE`。

### 尚未验证

- IPv6 地址、默认路由存在，不代表 IPv6 端到端通信已经正常。
- NDP 在 Linux 抓包点出现，不代表帧已成功离开 PHY。
- 当前证据尚不能证明 NA 在物理链路上丢失的确切位置。

## 4. 双端同步 NDP 抓包

### 测试方法

两台设备同时启动抓包，然后由 iMac 对 Panther 的链路本地地址执行 3 次 ping6。为保护隐私，仓库不保存真实地址、MAC 或可反推出地址的报文十六进制内容。

Panther 端执行：

```bash
sudo tcpdump -ni eth0 -e -tttt -vv 'icmp6'
```

iMac 端执行：

```bash
sudo tcpdump -ni en0 -e -tttt -vv 'icmp6'
```

iMac 端测试命令（目标地址以占位符表示，不保存真实 IPv6 地址）：

```bash
ping6 -n -c 3 '<PANTHER_LINK_LOCAL>%en0'
```

两端时钟没有同步，tcpdump 时间戳显示不同日期/时刻；用户明确确认抓包和 ping 是同时进行的。因此以下结果按同一测试轮次关联，不按墙上时间戳直接对齐。

### Panther 侧观察

- 收到 iMac 发出的 3 个 NS，目标为 Panther 的链路本地地址。
- 对每个 NS，Panther 抓包都紧接着观察到一个 NA。
- NA 的 Ethernet 目的端为 iMac；NA 包含 Target Link-Layer Address 选项。
- NA 标志为 `router, solicited, override`。
- 随后 Panther 发出 3 个单播 NS，Ethernet 目的端为 iMac。
- Panther 侧抓包没有观察到对应的 iMac NA 回应。
- 本轮 Panther 抓包统计为 9 packets captured、9 received by filter、0 dropped by kernel。

### iMac 侧观察

- iMac 对 Panther 发出 3 个 NS（目标为 Panther 的链路本地地址）。
- iMac 抓包没有观察到来自 Panther 的 NA。
- iMac 抓包也没有观察到 Panther 发出的单播 NS。
- 同一抓包中，iMac 与其他邻居之间存在成功的 NS/NA 往返。
- 同一抓包中还收到 hEX 发出的 RA。
- iMac 抓包统计为 11 packets captured、670 packets received by filter、0 dropped by kernel。

### 交叉判断

两端对同一测试轮次的观察形成以下对照：

| 方向/环节 | Panther 侧 | iMac 侧 | 当前判断 |
|---|---|---|---|
| iMac → Panther：NS | 收到 3 个 | 发出 3 个 | 已确认到达 Panther Linux 抓包点 |
| Panther → iMac：NA | 看到 3 个 NA 发出 | 未看到对应 NA | 发送经过 Panther 抓包点，但物理发送/对端接收未证实 |
| Panther → iMac：单播 NS | 看到 3 个发出 | 未看到对应 NS | 同样需要确认 Panther 实际 TX 路径 |
| iMac → 其他邻居：NDP | — | 有成功往返 | iMac 的 NDP 功能并非整体失效 |

**关键结论：** Panther 的 Linux 网络栈能处理收到的 NS 并生成 NA；但同一轮 iMac 抓包未见 Panther 发出的 NA，也未见 Panther 发出的单播 NS。该结果使 Panther 本机抓包点之后的发送路径成为当前优先调查对象。它还不是 GMAC/PHY 故障的最终证明，因为 tcpdump 的发送抓包点早于物理链路完成发送。

## 5. 相关 GMAC/PHY 既有审计结果

以下项目此前已做过只读审计，本轮不重复执行，也不将其视为已证明物理链路完全正常：

- 有线链路在更换网线后达到 1000Mbps Full Duplex。
- PHY 识别为 RTL8211F。
- Linux 运行时设备树配置为 RGMII。
- Linux 驱动日志和 GRF 读回曾确认 MAC 侧 TX/RX delay 配置。
- Linux GMAC1 软件时钟树曾显示相关时钟已使能，软件读回为预期频率。
- 既有 DMA 统计曾显示有 TX 帧回收和完成中断；这不等于 PHY 引脚上的物理发送成功。
- 尚无 PHY 引脚 TXC/TXD/RXC/RXD 的波形、setup/hold、skew、占空比或 jitter 实测证据。

详细背景见：[GMAC / DHCP 与 TF U-Boot 启动链调查记录](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)。

## 6. 当前故障模型与证据等级

### 已验证

- IPv4 DHCPv4 没有成功完成。
- DHCP Discover 到达 Panther Linux 本机抓包点。
- 既有 hEX 抓包未观察到 Panther DHCP 报文。
- Panther 收到 hEX RA，并形成 IPv6 SLAAC 地址和默认路由。
- Panther 收到 iMac 的 NS，并在本机抓包点生成 NA。
- 同一轮 iMac 抓包未看到 Panther 的 NA 或 Panther 发出的单播 NS。
- iMac 与其他邻居的 NDP 往返正常。

### 高优先级假设，尚未证实

Panther Ethernet 发送路径在 Linux 本机抓包点之后存在异常。候选范围包括 GMAC TX 提交/队列、DMA 到 MAC 的交接、RGMII 时序/电气条件、PHY 发送及交换链路。

### 目前不能下的结论

- 不能说 TX DMA 已经故障。
- 不能说 RTL8211F 已经故障。
- 不能说 U-Boot 一定是根因。
- 不能说 RGMII delay 一定配置错误。
- 不能仅凭 Link Up 或 Linux tcpdump 的 outgoing packet 认定实际物理发送成功。
- 不能将 iMac 的整体 NDP 功能判为故障。

## 7. 下一步最有区分力的验证

1. **先在 hEX 侧确认 Panther 发出的报文是否实际抵达。** 优先观察 DHCP Discover；必要时再观察 Panther 发出的 IPv6 NA/NS。使用只读抓包，不修改 hEX 配置。
2. 若 hEX 收不到 DHCP Discover，继续定位 Panther Linux 抓包点之后的发送链路；对照 eth0 TX 统计、驱动队列/描述符状态、PHY 统计与可获得的硬件诊断。
3. 若 hEX 收到报文，再沿 hEX 桥接/交换路径与 iMac 接收侧定位，不再把全部故障归因于 Panther。
4. 将 DHCPv4 与 IPv6 NDP 放在同一 Ethernet 收发模型下比较，避免分别进行无目标的协议配置调整。
5. 继续保留只读取证原则：未经明确授权，不安装软件、不修改系统/网络/驱动/内核/设备树/U-Boot，不影响现有服务。

## 8. 维护与隐私约定

- 本报告是分析记录，不是原始抓包文件；原始包中可能包含地址、MAC 和其他家庭网络信息，不直接上传公开仓库。
- 所有实际 IPv6 地址、前缀、链路本地地址、临时地址、网关地址均不写入本文。
- 不公开真实 MAC、实际 LAN IPv4 地址、设备序列号、CID、UUID 或其他可识别标识。
- 新证据应注明采集命令、设备、是否同步及是否只读；原始证据与分析报告分开保存。
- 新发现与旧结论冲突时，保留旧证据并追加纠错，不静默覆盖历史记录。
- 不重复已完成测试；优先选择能够区分故障边界的最小只读验证。
