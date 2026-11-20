# Panther X2 GMAC TX 故障调查阶段性报告（P1–P4，2026-11-20）

## 0. 报告用途与结论摘要

本报告汇总 Panther X2（RK3566）GMAC TX 故障调查中 P1–P4 已完成的静态源码审计、历史实机证据和证据边界，供用户决定是否进入下一阶段。它不是根因报告，也不是部署/修复方案。

**核心结论：**
1. 故障边界目前仍停留在：Linux/驱动接受 TX 请求、驱动回收 descriptor、MAC MMC TX 计数增长，但同二层外部接收端没有捕获测试帧。尚未证明帧已从 MAC TX 引脚进入 RGMII，也未证明 RTL8211F 从 MDI 端发射。
2. P1–P3 没有找到能够解释两个异常内核共有回归的、已证实命中 Panther 普通 RGMII TX 路径的软件差异。
3. P4 发现一个真实的 Rockchip pinctrl 首 pin 错误处理缺陷：异常 6.1.174-rk35xx 与 6.12.81-rk35xx 可能吞掉 group 首 pin mux 写入错误，并跳过同组后续 pins。其 pin group 顺序理论上可能影响 Panther TXD/TXCLK；但没有现场证据证明 IOMUX 写入曾失败，故只能列为未证实候选，不能认定根因。
4. P1–P4 已按既定范围全部收口。下一步是否进入 P5 物理边界验证，由用户综合考虑并明确授权；本报告不触发任何设备操作。

## 1. 设备、版本与调查边界

设备：Panther X2 / Rockchip RK3566，GMAC1（fe010000），外接 RTL8211F-CG，RGMII。

版本边界：
- 正常实机基线：Linux 6.1.116-ophub。
- 最早明确异常：Linux 6.1.174-rk35xx。
- 持续异常：Linux 6.12.81-rk35xx-ophub。

源码候选：
- 正常 6.1.116：unifreq/linux-6.1.y @ 5eb841b59d6ead6e264163785a634e78f0253c8e。
- 异常 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip @ c2f148dece4b67ebd30aefad1bdd1990f41e5633（高置信度候选，非逐字节构建证明）。
- 异常 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip @ 661b2d8bf1284556f8876d5ed5fb80c64b22f94c（候选源码，发布二进制精确来源仍未完全闭环）。

调查原则：
- 本轮阶段报告仅整合已有实机证据和已完成静态审计，不在 Panther 上执行任何命令。
- 不安装软件、不修改系统/网络/驱动/内核/DT，不读写 MMIO，不进行 MDIO 操作，不发包、不抓包、不重启接口。
- 不重复已经完成的 descriptor、queue、DMA helper、时钟、RX/NAPI、MAC 地址、DHCP 客户端、EEE/offload/速率等测试。
- 结论严格区分已验证、未验证、推测；源码差异不自动等于故障原因。

## 2. 故障定义与现有外部证据

### 2.1 已验证的 TX 软件路径

历史 6.12.81 测试记录表明：
- Linux outgoing 路径能观察到待发送帧；
- AF_PACKET raw socket 能提交广播帧及发往 iMac 有线 MAC 的单播帧；
- 测试帧进入 `stmmac_xmit()`；
- `stmmac_xmit()` 返回 `NETDEV_TX_OK`；
- TX descriptor 后续进入驱动清理/回收路径；
- 同一启动周期的 Linux TX packets/bytes 与 MAC MMC TX frame/octet 计数随测试帧增加；
- 60-byte 自定义帧后 Linux TX bytes +60，MMC TX octets +64，与 MMC 计入 4-byte FCS 的常见统计口径相符；
- 快照中的 tx_underflow、tx_frame_flushed、tx_payload_error、tx_ip_header_error、mtl_tx_status_fifo_full、mtl_tx_fifo_not_empty 均为 0；TX IRQ 计数有增长。

这些证据说明软件提交、DMA descriptor 完成/回收和 MAC 统计路径在所记录测试中有进展，但不构成 MAC TX pin 或 PHY MDI 端电气出线证明。

### 2.2 已验证的外部接收结果

- iMac en0 在 Panther 发帧期间持续运行 tcpdump，过滤 EtherType 0x88B5。
- 广播帧和发往 iMac 有线 MAC 的单播帧均未捕获。
- 最终统计：0 packets captured、5719 packets received by filter、0 packets dropped by kernel。
- 同期 DHCP Discover 在 hEX 未观察到；其他客户端 DHCP 正常。
- 正常 6.1.116 有线网络作为阳性对照，故障版本外部收不到测试帧的结果不是单纯缺少监听器或接收端未启动。

### 2.3 严格的故障边界

**已证实：** Linux 生成并提交 TX；驱动接受请求；驱动清理 descriptor；MAC MMC 计数增加；外部监听端未捕获对应帧。

**未证实：** MAC 是否在 RGMII TXC/TXD 上输出了正确帧；RTL8211F 是否正确采样/编码并从 MDI 端发射；PHY 线侧到交换机/iMac 的物理路径是否收到帧。

因此故障仍可能位于：
- MAC 内部从 DMA/MTL 到 RGMII pin 的真实发送路径；
- RGMII TX clock/data/控制信号及 pinmux/电气时序；
- RTL8211F 的 RGMII 接收侧/PHY 内部 TX 路径；
- PHY MDI 侧及其后的链路。

当前证据不能在这些层次间做最终归因。

## 3. P1：JL2xx1 workaround 四次 MDIO 写入

### 已确认
- 6.1.116 引入四次写入的代码来源可追溯到 Lean OpenWrt 补丁，讨论作者称其最初来自 JLSemi 提供的代码。
- Page 0xA43 / Reg 25 是 RTL8211F PHYCR2。
- 0x1801 的位字段可按 RTL8211F-CG 数据手册解码：bit11=125MHz CLKOUT 选择，bit0=CLKOUT enable；同时清除 RXC enable、PHY-mode EEE enable 等位；bits13:12=01 属于手册未定义的 Reserved 组合。
- MDIO PHY 地址 0 是 RTL8211F 支持的广播写入地址，不应简单理解为仅对设备树地址 0 的单个 PHY 单播。
- 最后的 BMCR software reset 是 PHYCR2 配置后手册要求的动作；手册没有说 PHYCR2 会被该 reset 清零。

### 证据不足
- 未取得可公开核验的 JLSemi 原始驱动及每个值的厂商解释。
- 未取得厂商对 Reserved bits 13:12=01 的定义。
- 没有证据证明四次写入原本为 RTL8211F-CG 设计，或其在 Panther 实机产生预期效果。
- 没有 Panther 实机 reset 后 PHYCR2 回读或 CLKOUT/RXC 波形证据；本阶段不安排此类操作。

### 决策
P1 正式收口：寄存器语义部分解码，但 JLSemi 原始意图及保留位行为证据不足。停止猜测，不再围绕该写入组扩展。

详细报告：`PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md`。

## 4. P2：U-Boot / Linux GMAC 与 PHY 时钟交接

### 已确认
- Panther Linux runtime FDT 使用 `phy-mode=rgmii`、`clock_in_out=input`；Linux 日志明确显示 `clock input from PHY`。
- Linux 接管时会按自己的 runtime FDT 重新配置 GMAC clock parent/direction，并重新初始化 RTL8211F；不能假定 U-Boot 的硬件状态原样保留。
- 正常与异常 Linux 候选中的 GMAC1 CRU parent mux 和外部 fixed-clock DTS 描述没有已知差异。
- 已知 Radxa U-Boot 参考驱动可说明 clock_in_out 对 GMAC 内部 clock rate 配置路径的含义，但该参考源码不是 JP proper 精确构建源码。

### 未验证
- JP-TvBox 2023 U-Boot proper 的精确源码提交、defconfig、FIT control FDT。
- JP proper 实际使用的 clock_in_out 值、是否真正启动 GMAC DMA/PHY 网络收发，以及退出时物理 CLKOUT/RGMII clock 状态。
- U-Boot 到 Linux 接管时是否出现真实时钟波形中断。

### 决策
P2 正式收口：未找到已证实可解释最早回归的启动交接根因。JP proper 证据不足，不用 SPL FDT 或较新的 Radxa 源码代替。

详细报告：`PANTHER-X2-P2-UBOOT-LINUX-GMAC-CLOCK-HANDOFF-20261119.md`。

## 5. P3：RK35xx BSP / STMMAC 普通 TX 路径

### 已完成
- 使用高置信度 c2f148d 作为最早异常 6.1.174-rk35xx 源码候选，避免误用普通 stable 6.1.174。
- 已核对 Rockchip GMAC clock/probe/setup/PHY power handoff、SPH、integrated PHY、CSU、RGMII delay、GRF/PHP-GRF 等 Panther 适用性。
- 已比较普通 `stmmac_xmit()`、`stmmac_tx_clean()`、`stmmac_hw_setup()`、`stmmac_mac_link_up()`、`stmmac_dvr_probe()`。
- TX descriptor OWN、barrier、tail pointer、DWMAC4 DMA address、queue0→DMA channel0、TX channel start 等已有专项核对。
- TSO 与 SerDes 差异不命中 Panther 当前普通 RGMII DHCP/UDP 广播路径。

### 特殊发现：RTL8211F LED fixup
- c2f148d 的 `LED_FIX` 明确启用，注册 RTL8211F UID 0x001cc916 fixup。
- PHY 初始化时 fixup 写 LED 扩展页 D04 的 Reg 0x10/0x11。
- 代码语义指向 LED 配置，未发现其写 PHYCR、RGMII delay 或 TX/RX 数据通路寄存器。
- 该注册段在 6.12.81 候选中不存在，故不是两个异常版本共有差异。

### 决策
未发现 6.1.174-rk35xx 与 6.12.81-rk35xx 共有、正常 6.1.116 不存在、且实际命中 Panther 普通 RGMII TX 的有效 STMMAC core 差异。P3 正式关闭。

仍保留一个构建证据缺口：候选源码与发布二进制的 inputs/source_hash 尚未逐字节闭环。

详细报告：
- `PANTHER-X2-P3-RK35XX-STMMAC-CORE-TX-PATH-REVIEW-20261120.md`
- `PANTHER-X2-P3-STMMAC-LINKUP-PROBE-CLOSEOUT-20261120.md`
- `PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md`
- `PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md`

## 6. P4：Rockchip pinctrl 首 pin 错误处理

### 已确认的源码差异
三个源码端点的 `rockchip_pmx_set()`：
- 正常 6.1.116：`if (ret)`，首 pin 失败会返回错误；
- 异常 6.1.174-rk35xx 和 6.12.81-rk35xx：`if (ret && cnt)`。

若 group 第一个 pin 的 `rockchip_set_mux()` 返回错误，异常版本因 cnt==0 跳过错误返回并最终返回 0；循环已 break，同组后续 pin 不会继续配置。

### Panther 适用性
Panther GMAC1 M0 pin group 顺序显示：
- `gmac1m0_tx_bus2` 首 pin TXD0 失败，后续 TXD1/TXEN 不再配置；
- `gmac1m0_rgmii_clk` 首 pin RXCLK 失败，后续 TXCLK 不再配置；
- `gmac1m0_rgmii_bus` 首 pin RXD2 失败，后续 TXD2/TXD3 不再配置。

RK3568 mux=3 是合法 4-bit IOMUX；正常路径通过 GPIO3 对应 regmap 更新 IOMUX，regmap 写入错误可以传播到上述错误处理函数。

### 未验证
- Panther 实际启动时是否有 GPIO3 IOMUX regmap 写入失败；
- 哪个 group 是否发生首 pin 失败；
- runtime pinmux ownership 或硬件 mux 状态；
- TXC/TXD 电气状态。

### 决策
P4 静态审计正式关闭。该缺陷是与 TX pin group 相容的真实潜在软件错误路径，列为未证实候选，不得认定根因。无现场写入失败证据，不制作补丁、不操作设备。

详细报告：`PANTHER-X2-P4-PINCTRL-FIRST-PIN-ERROR-CLOSEOUT-20261120.md`。

## 7. 其他已完成或已降级工作（避免重复）

按主路线图，以下方向已有专项审计/测试记录，不应无新证据重做：
- U-Boot 基础 GMAC 枚举、启动链身份和 MAC 地址来源；
- GMAC clocks、CRU parent、CCF enable、RGMII delay 与 PHY reset GPIO；
- 普通 TX DMA descriptor OWN、barrier、tail pointer、DWMAC4 queue/channel start；
- TX queue0→DMA channel0；
- RX/NAPI、skb 分配器、反向广播与分配探针；
- DHCP 客户端、MAC 更换/克隆、broadcast flag；
- offload、强制 100M、EEE 与电源管理；
- RGMII DTS pin group 定义静态差分；
- 已有 6.1.116 正常基线和 6.12.81 运行时日志。
如要重新触及，必须指出新证据如何改变既有结论。

## 8. 重要安全边界：禁止重复的危险 MMIO 读取

2026-11-17 曾在读取 debugfs dummy-syscon registers 时发生同步外部中止并导致设备失去响应。当前没有证据证明该崩溃与 TX 故障有关，但该访问路径在此设备/映射环境中不安全。

永久禁止重复：
- `/sys/kernel/debug/regmap/*/registers`，尤其 dummy-syscon；
- 相关 MMIO 的 `devmem` 读取；
- 通过 dummy-syscon 读取 GMAC/GRF；
- 未授权的寄存器写入、PHY MDIO、驱动重载、接口重启、内核修改。

无法安全取得的现场寄存器状态应继续标为未验证，不能为补齐证据冒险。

## 9. 目前最值得保留的假设与证据强度

| 假设/方向 | 现有证据 | 当前评价 |
|---|---|---|
| P4 pinctrl 首 pin 错误吞噬 | 两异常源码共有、正常版没有；GMAC TX pin group 顺序有理论影响；无现场失败证据 | 最具体的未证实软件候选；不能认定根因 |
| GMAC/MAC 到 RGMII 的 TX 输出异常 | 外部接收端收不到；软件/MAC 统计增长；没有 TXC/TXD 波形 | 物理边界未定位，不能排除 |
| RTL8211F PHY TX / MDI 发射异常 | 外部接收端收不到；没有 PHY 线侧观测；P1/P3 无共同已证实配置回归 | 未验证 |
| U-Boot→Linux clock handoff | JP proper control FDT 缺失；Linux 会重新配置自身 clock tree | 证据不足，P2 已收口 |
| STMMAC 普通 TX descriptor/queue 核心回归 | 多个关键函数和 DWMAC4 descriptor/start 路径未发现有效共同差异 | 当前源码候选中优先级降低；发布二进制 provenance 仍有缺口 |
| JL2xx1 PHYCR2 写入语义 | JLSemi 来源链存在，RTL8211F Reserved bits 行为缺乏厂商定义 | 证据不足，P1 已停止 |

## 10. 若用户考虑进入 P5：需要回答的问题（仅供决策，不代表已授权）

P5 的目的不是“再跑一遍网络测试”，而是把发送链物理边界切开。理想证据应区分：
1. MAC 侧 RGMII TXC/TXD/TX_CTL 是否出现正确时钟、控制和测试帧数据；
2. 若 RGMII 侧存在正确帧，RTL8211F 是否在 MDI 侧产生相应差分信号；
3. 若 RGMII 侧不存在正确帧，则 PHY 线侧测量无需先做，优先回到 MAC/pinctrl/clock 的边界。

潜在手段（须另行评估设备可达性、仪器和风险）：
- 高带宽示波器或具备足够采样率/带宽的逻辑分析设备，观测 RGMII TXC、TXD[3:0]、TX_CTL；
- 千兆 Ethernet PHY MDI 侧需要适当差分/高速测量方案，普通逻辑分析仪不适用；
- 低风险只读软件证据（如可用时 pinctrl debugfs ownership）只能说明 Linux framework 的 owner/function，不能替代硬件 mux 寄存器和波形；
- 不使用危险 dummy-syscon debugfs/devmem。

进入 P5 前需先明确：可用测试点/夹具、示波器探头与带宽、是否有安全的高阻探测方式、是否可能影响 125MHz RGMII 时钟/高速信号完整性、设备停机窗口，以及每个结果对应的判定分支。没有合适仪器或测试点时，不应为“完成流程”而做低质量测试。

## 11. 当前决策状态

- P1：已结束，证据不足，不再猜测。
- P2：已结束，JP proper 证据不足。
- P3：已结束，未发现有效共同 STMMAC TX 根因差异。
- P4：已结束，发现未证实的 pinctrl 首 pin 错误候选。
- P5：待用户综合考虑，尚未授权；本报告不安排实机操作。

**阶段性结论：** 现有软件证据已把 Linux TX 请求、descriptor 回收和 MAC MMC 统计路径推进到可观察状态，但未证明 MAC→RGMII→PHY→MDI 的物理发送成功。当前最具体的软件候选是 P4 pinctrl 首 pin 错误处理，但其触发条件尚未在 Panther 现场证实。下一步应由用户基于仪器/测试点/风险/成本决定是否进入物理边界验证，而不是继续无边界地搜索源码或盲目打补丁。
