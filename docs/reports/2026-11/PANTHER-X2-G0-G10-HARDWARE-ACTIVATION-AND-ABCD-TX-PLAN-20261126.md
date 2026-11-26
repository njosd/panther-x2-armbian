# Panther X2 项目 A — G0–G10 硬件准入与 ABCD-TX 分层验证计划

- 日期：2026-11-26
- 状态：架构计划；不构成设备启动、刷写、PMIC 写入或网络发送授权
- 上位依据：项目 A 总路线图、B2-1 实施计划
- 原则：复用 R1–R6 既有研究；先完成 G0 只读准入，再逐门申请硬件操作；任何失败停在当前门。

## 1. 目标与边界

两条黄金基线 6.1.65（第一功能基准）和 6.1.116（第二正常行为参照）均证明 Panther X2 板载有线千兆网络曾正常工作。当前优先调查 6.18 软件配置、驱动实现、设备树和硬件资源激活适配；不预设硬件损坏，也不把硬件正常当作无需验证供电/时钟/复位的理由。

仅研究板载 GMAC1 千兆 Ethernet。Wi-Fi/蓝牙永久排除；不恢复历史 Project B GMAC 根因调查；不重跑已完成的多版本审计。保持已验证 SPL→JP-TvBox U-Boot proper→TF 加载 Kernel/DTB/uInitrd→RAM initramfs 启动链，不写 eMMC，不触碰 SN64G。SU08G 任何写入/启动仍须逐次授权。

## 2. ABCD 同帧发送验证定义

ABCD 是同一帧在发送路径中的四个连续观察边界，不能以不同帧或单纯计数器拼接结论。

| 标记 | 边界 | 需要关联的证据 |
|---|---|---|
| A | 用户态 AF_PACKET/SOCK_RAW 提交 | interface、EtherType、源/目的 MAC、原始 payload、sequence、length、SHA-256、sendto/sendmsg 返回值/errno |
| B | Linux 网络核心 / skb | 同一 sequence/hash 的 skb、长度、目标 netdev、进入驱动前的证据 |
| C | STMMAC ndo_start_xmit / stmmac_xmit | 同一帧进入驱动、queue、长度、skb/payload 关联及返回状态 |
| D | DMA mapping | DMA API 返回、DMA address、长度、DMA_TO_DEVICE、映射结果；可安全观测时核对 DMA buffer payload |

D 之后继续记录 TX descriptor（buffer DMA address、length、FS/LS、OWN）、DMA completion、driver reclaim/unmap、MAC/PHY/link，最后由独立对端线侧抓包核验。descriptor 不保存 payload；OWN 清除/发送完成/netdev counter 增长均不能替代对端收到。

固定测试帧：实验 EtherType 0x88B5，广播目的 MAC，payload 含 ABCD、递增 sequence、length 和校验/hash；先单帧，之后才按门限增加少量重复帧。无 IPv4/ARP/DHCP/DNS 依赖。发送前固定 LAN 对端与抓包过滤器，确认广播域。每层必须使用同一 sequence/hash；无法直接观察 payload 时写明 NOT OBSERVED，不用计数器冒充。

## 3. G0：硬件前只读准入（当前阶段）

G0 完成前不激活 RK809 MFD/regulator，不恢复 GMAC/MDIO/PHY，不做硬件发送。

- **G0.1 依赖矩阵**：将 R2–R6 证据映射为 provider→consumer→实际动作→证据等级→阻塞项；分别记录 6.1.65、6.1.116、6.18.63 默认配置/对象和已知实机行为。
- **G0.2 PMIC 副作用：已完成静态审计，stock MFD/regulator NO-GO。** MFD probe 会执行 IRQ mask/条件 ACK、整组 RK817 pre-init 并创建全部子设备；regulator probe 注册全部 rail，约束处理及约 30 秒 late cleanup 可能写 PMIC/关闭未使用 rail。当前允许写入白名单为空；不得启用 stock driver。详见 G0.2 报告。
- **G0.3 IO-domain：静态拓扑/写入路径已完成，运行时最终 bind 状态 UNKNOWN。** 已确认 GMAC1 M0→GPIO3→VCCIO5；vccio5-supply 与 GMAC1 phy-supply 均指向 vcc_3v3/SWITCH_REG1；VCCIO5 selector 会写 PMU GRF 0x140/0x144。实际 rail 电压/selector readback 未验证，不放行 consumer probe。
- **G0.4 clock/reset/PHY：静态审计完成，物理来源/波形 UNKNOWN。** CRU clock IDs/mux/gate、SRST_A_GMAC1 ID236、GPIO3_PA1 active-low、RGMII delay/mode 已复用 R6 证据确认；RTL8211F CLKOUT pin35 仅为 125MHz 候选，DTS fixed-clock 不证明实际波形。
- **G0.5 ABCD 夹具：静态设计完成。** R1 loopback probe 仅作为软件 API 回归，不可充当目标 TX sender；新建独立 sender 规格，固定 0x88B5/ABCD/run_id/sequence/digest 帧格式，复用 R1 tracepoint/kprobe/DMA trace 能力和外部 pcap。运行时 tracefs/kprobe 可用性仍待后续授权阶段验证。
- **G0.6 Fixed-regulator 替代路径：静态可行性成立、硬件条件 BLOCKED。** R1 已内建 fixed-voltage regulator；可将经外部确认已供电的 PMUIO1/2 与 VCCIO5 rail 映射为无控制 ops 的 always-on provider，避免 stock RK809 MFD 写入；IO-domain 仍会写 PMU GRF，必须单独授权。VCC3V3_PMU/VCC_3V3 实测和板级 testpoint 未确认前不得实现。
- **G0.7 板级资料：公开检索未找到 Panther X2 专用原理图/netlist/testpoint。** 需补充至少 RK809、电源 rails、RK3566 IO domains、RTL8211F 周边的板级原理图或高清 PCB 正反面照片；未确认测点前不得要求用户探测电压。

G0 放行条件：依赖矩阵和关键副作用已说明；必需 provider 缺口及 deferred-probe 原因可追溯；未解决项明确列 BLOCKED；ABCD 发送器/观测点/对端抓包方案可执行；无未审查的自动硬件副作用。G0 通过仅允许提交 G1 单独操作计划，不自动授权设备操作。

## 4. G1–G10 分阶段放行

| 阶段 | 唯一目标与激活边界 | ABCD 检查点 |
|---|---|---|
| G1 I2C/RK809 只读边界 | 复用已完成 I2C0 bind、RK809 ID 0x8094、0xF0/0xF6 只读证据；除非出现明确缺口，不重复读取；不启用 MFD | 不具备 MAC/netdev，记 NOT EXECUTABLE |
| G2 RK809 MFD/regmap | stock MFD 当前 NO-GO；只有替代最小 provider 方案完成静态设计、回退审查并另行授权后才可评估 | 不发帧；目标 MAC 未激活 |
| G3 regulator provider | stock 全量 regulator provider 暂不放行；必须先解决 G2 provider 安全路径，逐 rail 约束/自动写入与物理测量条件另审 | NOT EXECUTABLE；检查目标网口仍隔离 |
| G4 IO-domain 与共享硬件资源 | 在 provider 安全放行后，核验 IO-domain supplier/deferred-probe/GRF 写入；再逐项确认 GMAC 所需 clock/reset/pinctrl/GPIO/PHY supply，物理电压/波形另证 | 复核一次 netdev/open/DMA 的前置条件 |
| G5-A Rockchip glue/STMMAC probe | 单独恢复目标 MAC 节点和最小依赖；核验资源、probe、bind、netdev 注册；不把 probe 当作 open/link | netdev 未 open 时不执行真实 A–D |
| G5-B MDIO/RTL8211F | 单独核验 MDIO bus、地址0 PHY ID、driver bind、link；不写 PHY 寄存器 | 若接口与 DMA 前置条件确已满足，另行批准后单帧 A→D；否则 BLOCKED |
| G6 interface open/DMA | 单独 open；记录 DMA reset outcome、ring、queue、IRQ/NAPI、MAC/MTL 初始化。6.18 reset failure warning-and-continue 必须独立检查 | 低速单帧完整 A→B→C→D + descriptor/OWN/completion/reclaim |
| G7 物理 TX | 保持同一软件/线缆/对端条件，对端逐帧捕获 EtherType、MAC、sequence、length、hash | 完整 ABCD + E6；对端收到正确帧才 TX PASS |
| G8 RX | 独立验证对端→Panther 的 PHY/MAC RX、DMA RX、NAPI、skb、AF_PACKET；首轮不混入 ARP | TX 回归帧复测，确认新增 RX 未破坏 TX |
| G9 ARP/IPv4/ICMP | 逐项加入 ARP、静态 IPv4、ICMP；地址从实际 LAN 读取；不依赖 DHCP/DNS | 每一子项完成后复测 ABCD TX |
| G10 TCP/UDP 与按需服务 | TCP、UDP 分开；DHCP/DNS/SSH 仅在基础功能通过后按需引入 | 每个新增协议阶段后复测 ABCD TX |

任何连续两个阶段不能执行真实 ABCD 后，下一阶段必须重新评估 netdev/open/DMA 条件；一旦具备条件，优先单帧验证，不等全部协议栈完成。若不具备，记录缺失条件，不绕过前置门。

## 5. 实际启动/激活顺序

预期依赖顺序为：既有 BootROM/eMMC SPL→JP proper→RAM Linux；SoC clock/CRU、pinctrl、GPIO、GRF/Syscon、reset、I2C 基础设施；经安全审查后 RK809 MFD/regmap；再 regulator provider；IO-domain consumer；GMAC PHY supply、clock/reset/pinctrl/GPIO 等资源；Rockchip DWMAC glue/STMMAC；MDIO/RTL8211F；interface open、DMA ring/IRQ/NAPI；ABCD TX；对端捕获；RX 与协议栈。

这不是 DTS 节点顺序，也不保证 Linux driver core 严格线性 probe。真实顺序以 supplier/consumer、deferred-probe、probe 日志、sysfs bind 和资源 API 返回为准。

## 6. 每门统一记录与停止条件

记录阶段/子门、授权范围、源码 commit、最终 config、Image/DTB/initramfs/tool hashes、6.1.65/6.1.116 对照、唯一变量、启动日志、probe/deferred-probe、provider/consumer、资源返回值、ABCD 同帧序列与 hash、DMA mapping/descriptor/completion/reclaim、对端抓包、最后通过边界和回退点。

配置/构建差异未解释不启动；PMIC副作用不清不启用；supplier defer 不绕过；PHY supply/clock/reset 未确认不 open；DMA mapping/descriptor/OWN/completion 异常立即停止发送；对端无帧或内容不符判 TX FAIL，不进入 ARP/IPv4。写介质、重启、PMIC/PHY寄存器写、供电/复位动作、实机发送均须单独授权。

## 7. 当前进度

- [x] G0–G10 总体门序、启动依赖和 ABCD-TX 同帧定义已建立。
- [x] G0.1 provider/consumer 依赖矩阵第一轮归档；交叉复核仍待 G0 总审。
- [x] G0.2 stock RK809 MFD/regulator 副作用审计；当前决策为 NO-GO，允许写入白名单为空。
- [x] G0.3 IO-domain 静态 supplier/deferred-probe 路径、GMAC1 VCCIO5 mapping 与 GRF 写入行为已归档；运行时最终 bind 状态仍 UNKNOWN。
- [x] G0.4 clock/reset/PHY 静态依赖及 125MHz 候选来源审计完成；物理连线/波形和 reset 电气行为未验证。
- [x] G0.5 ABCD sender 规格、tracepoint/kprobe/DMA mapping 观测链和对端 pcap 夹具审查完成（静态设计）。
- [x] G0.6 fixed-regulator 替代路径静态可行性审查；等待 Panther 专用 rail 测量点和实际电压证据。
- [x] G0.7 Panther X2 公开板级资料检索完成；专用原理图/netlist/testpoint 未找到，安全测量仍 BLOCKED。
- [ ] 补充 Panther X2 板级资料并完成静态 net tracing；资料到位前不做电压测量。
- [ ] G0 总体准入复核（须先解决板级测点资料缺口）。
- [ ] G0.4 PHY 125MHz 物理时钟与硬件资源测量方案。
- [ ] G0.5 ABCD 发送器与观测夹具审查。
- [ ] G0 总体准入评审。
- G0 未完成前不启动下一硬件门。
