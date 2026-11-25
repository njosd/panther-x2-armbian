# Panther X2 B2-0 方向三：STMMAC / DWMAC4 / DMA 驱动核心静态审计（2026-11-25）

## 1. 阶段位置与边界

- 上一阶段：方向二 Linux generic network-core 多版本源码/Kconfig/已有配置静态审计，用户已批准按“证据边界明确的有条件结项”正式归档，结项记录见方向二报告 §56。
- 当前阶段：方向三，审计 STMMAC common driver、DWMAC4 MAC/DMA implementation、DMA API usage、ring/descriptor lifecycle、IRQ/NAPI handoff，以及 Panther X2 RK3566 实际使用路径所依赖的通用驱动核心。
- 后续 Rockchip GMAC glue、CCF/CRU、reset、PHY 电源等仍按原计划作为独立后续专题；不在本方向提前展开。
- B2.1/B2.2/B3 实机网络验证不属于本轮。
- 固定比较样本：6.1.65、6.1.116、6.1.174、6.12.81。6.1.65 源码端点仍按方向一/二标注的高置信度候选使用，不得伪称已精确绑定历史 Image。
- 本轮只使用仓库已有源码、提交、Kconfig、DTS、kernel.config、历史报告和公开构建资产做只读审计；不访问 Panther X2、不运行设备命令、不构建、不安装软件、不修改驱动、DTB、内核或网络配置。

## 2. 已完成证据复用与禁止重复项

### 2.1 已完成且不重做

1. 6.1.116 与 6.1.174 stmmac_main.c 普通小帧 TX DMA mapping、unmapping、descriptor address、OWN 发布、barrier、tail-pointer kick 对比：见 PANTHER-X2-STMMAC-TX-DMA-MAPPING-DESCRIPTOR-OWNERSHIP-116-VS-174-20261119.md。
2. 6.1.116 与 6.1.174 STMMAC 版本窗口提交筛查：PCI multi-MSI、LPI IRQ、XGMAC2、chain-mode jumbo TX 等条件适用性已记录；6.1.124 DT/MDIO 解析重构和 6.1.169 chain-mode TX/IRQ 变化已标注：见 PANTHER-X2-KERNEL-6.1.116-TO-6.1.174-REGRESSION-WINDOW-STMMAC-DIFF-20261119.md。
3. 6.1.116 实际 config 闭环及 6.12.81 STMMAC 普通 RX skb allocation/page-pool 分支差异：见 PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md。
4. 6.1.116/6.1.174 Rockchip GMAC glue、clock/reset、PHY supply/runtime-PM 既有专题已归档；本轮只把其结果当作边界，不重复：见 PANTHER-X2-B2-0-DIRECTION-2-GMAC-GLUE-CLOCK-POWER-AUDIT-20261124.md。
5. generic network-core TX queue/qdisc、UDP/IP output、NET_TX_SOFTIRQ 等已在方向二 §3～§24、§26 审计，不在本方向重做。

### 2.2 方向三剩余审计范围

按以下顺序逐项审计，每项结束后形成明确结论，再进入下一项：

1. STMMAC probe / platform resource parsing：platform data、OF match/data、MAC capability selection、DMA capability derivation、IRQ/resource acquisition、clock/reset/PHY handoff 的驱动核心边界。只审 stmmac common/platform driver；Rockchip glue 实际实现留后续。
2. STMMAC DT/MDIO/PHY attach：6.1.124 DT/MDIO 重构在 Panther 节点上的实际适用性；PHY address/IRQ/reset/managed attach 生命周期；只读比较四版本实际 DTS 和源码。
3. DWMAC4 DMA core initialization：DMA channel 数量、地址宽度、AXI/PBL/burst、DMA bus mode、channel start/stop/reset、寄存器编程顺序及错误处理。
4. TX descriptor lifecycle（在既有 116/174 小帧主路径结论基础上，只补四版本差异与未覆盖分支）：ring/chain mode applicability、context descriptor、checksum/TSO、fragment/mapping failure、descriptor availability、IRQ reclaim、timeout/recovery。不得重复已确认相同的普通小帧 mapping/OWN/barrier/tail pointer 路径。
5. RX descriptor/buffer/page-pool lifecycle：ring refill、DMA mapping/sync、OWN handoff、RX interrupt/NAPI poll、normal skb allocation、buffer unavailable/overflow、error/drop accounting；复用已完成的 116/612 RX 对比，仅补四版本和 Panther 适用性差异。
6. DMA API / coherency / IOMMU integration：dma_set_mask/coherent、streaming/coherent mapping、DMA address width、dma-coherent、IOMMU attachment、cache sync API semantics；区分源码、DTS、config 和架构实现证据，不由 CONFIG_DMA_NEED_SYNC 单项推断故障。
7. IRQ / NAPI / watchdog / recovery：STMMAC IRQ registration/affinity、TX/RX IRQ mask/unmask、NAPI schedule/complete、DMA abnormal/fatal bus error、watchdog/reset recovery。generic networking 层已审内容不重做。
8. 最后做四版本矩阵、普通 DHCP 小帧 TX/RX 适用性分类和报告一致性检查；方向三完成后再判断是否进入后续独立专题。

## 3. 版本端点与证据分级

| 样本 | 角色 | 当前可用源码/构建证据 | 限制 |
|---|---|---|---|
| 6.1.65 | 黄金 A | 方向一/二已记录的高置信度候选源码端点及历史实机正常基线 | 未绑定历史 Image 的精确 checkout SHA |
| 6.1.116 | 黄金 B | 已归档源码端点、实际 kernel.config、历史正常实机基线 | 历史 Image 精确 source commit 绑定限制 |
| 6.1.174 | 故障 A | 已确认源码 commit 与原始 Actions job 来源；故障实机样本 | 历史最终 config 部分字段不可恢复 |
| 6.12.81 | 故障 B | 已确认源码 commit、原始构建来源、最终 kernel.config；故障实机样本 | 特定运行时 DMA/descriptor 状态未归档 |

## 4. 本轮执行顺序与状态

| 顺序 | 子项 | 状态 | 交付 |
|---|---|---|---|
| D3-1 | STMMAC probe/platform resource parsing | 已完成（静态源码范围） | 四版本函数/结构/配置差异；pclk/MDC CSR clock source 变化已归档 |
| D3-2 | DT/MDIO/PHY attach 生命周期 | 已完成（静态源码范围） | 四版本 MDIO parser、PHY attach、四次 MDIO 写入差异及 Panther 适用性 |
| D3-3 | DWMAC4 DMA 初始化/寄存器编程 | 已完成（静态源码范围） | 四版本 reset timing、DMA/AXI/PBL/channel/address-width 对照 |
| D3-4 | TX descriptor 其余分支 | 已完成（静态源码范围） | 四版本 TSO mapping lifecycle、mapping error/ring shortage、completion/reclaim、TX timer/recovery 条件差异 |
| D3-5 | RX descriptor/buffer/page-pool | 已完成（静态源码范围） | 四版本 RX refill/page-pool/DMA sync/OWN/status/NAPI 对照 |
| D3-6 | DMA API/coherency/IOMMU | 已完成（静态源码/Kconfig/DTS 范围） | 四版本 DMA map/sync、ARM64 cache maintenance、DMA_NEED_SYNC/bounce、coherency/IOMMU 交叉矩阵 |
| D3-7 | IRQ/NAPI/watchdog/recovery | 已完成（静态源码范围） | 四版本 IRQ status/NAPI schedule/timeout/recovery 对照 |
| D3-8 | 总矩阵与一致性审校 | 进行中 | 汇总 D3-1～D3-7、核对范围/来源/结论一致性 |

## 5. 当前唯一工作项：D3-8

D3-1 至 D3-6 已在配套报告中按静态源码范围结项。本轮当前只做 D3-7：核对 STMMAC IRQ registration/mask/unmask、NAPI schedule/complete、DMA abnormal/fatal bus error、watchdog 与 recovery；generic network-core 层的 NET_TX_SOFTIRQ 已在方向二完成，不重做。
- 回读 D3-1～D3-7 报告与方向三总计划；
- 建立四版本差异总矩阵，区分无条件差异、条件性差异、仅统计/API 变化与未验证运行时事项；
- 逐项检查 6.1.174 使用实际构建 source_hash c2f148d，不混用 upstream stable 3f06ed3e；
- 检查普通 DHCP/UDP 单 skb 的适用性结论与方向二结论是否一致；
- 形成方向三结项评估，不自动启动方向四或 B2.1。

回读 D3-1～D3-7 七份子项报告和方向二 §53/§55，建立总矩阵并做最终一致性审校。

### D3-1 结项结果（2026-11-25）
- 四版本 stmmac_platform.c 与相关 stmmac_main.c、rk356x.dtsi 已完成静态对照。
- 6.1.65/6.1.116 的关键 probe/resource 函数逐行一致；6.1.174-rk35xx 与 6.12.81 的变化及 Panther 分支适用性已记录。
- pclk/pclk_mac 名称与 MDC CSR clock source 变化已确认；运行时频率、寄存器值和 enable/refcount 未验证，明确保留为运行时证据限制。
- D3-1 已按静态源码范围结项，详见 PANTHER-X2-B2-0-DIRECTION-3-D3-1-STMMAC-PLATFORM-PROBE-DIFF-20261125.md。

### D3-2 结项结果（2026-11-25）
- 四版本 MDIO parser 在 Panther DTS 输入下得到相同的 MDIO bus、PHY node、bus_data 和 bus_id 结果。
- 黄金版本 6.1.65/6.1.116 存在四次 PHYCR2/BMCR MDIO 写入，实际故障源码 6.1.174 c2f148d/6.12.81 缺失；P1 已有寄存器语义报告，本阶段只补齐精确四版本端点。
- 6.1.174/6.12 的 mac_requires_rxc 及 PHY resume/attach 语义变化已记录；没有运行时 RXC/PHY 状态证据，不认定根因。
- D3-2 已按静态源码范围结项，详见 PANTHER-X2-B2-0-DIRECTION-3-D3-2-MDIO-PHY-ATTACH-DIFF-20261125.md。

### D3-3 当前结果（2026-11-25）
- 6.1.65/6.1.116 在 stmmac_init_dma_engine() 的 DMA SW reset 前有 1500ms delay；实际 6.1.174 c2f148d/6.12.81 缺失。
- dwmac4_dma_reset() 的 polling interval 从黄金版本 10ms 变为故障版本 0.5ms，timeout 均为 1s。
- DWMAC4 DMA/AXI/channel init 算法总体相同；address map abstraction 对 Panther 使用 NULL default offsets。
- DMA feature/address-width 软件逻辑已对照；硬件 feature register 实际值、DMA mask 成功状态及 platform PBL/AXI/queue 最终值未闭环。
- D3-3 继续进行中；详细结果见 PANTHER-X2-B2-0-DIRECTION-3-D3-3-DWMAC4-DMA-INIT-DIFF-20261125.md。
- 本轮没有设备访问、构建、安装、驱动/DTB/系统配置修改。

## 6. 记录格式

每个差异至少记录：
1. 版本与精确源码 commit；
2. 文件、函数、结构字段及必要行号；
3. 四版本具体行为差异；
4. Panther X2 RK3566 / DWMAC4 / RGMII / 外置 RTL8211F 的实际适用条件；
5. 是否影响普通 DHCP 小帧 TX/RX，或只影响 jumbo/GSO/XGMAC/特殊 PHY/多队列等条件路径；
6. 对应 Kconfig、kernel.config、DTS 证据；
7. 已验证、未验证、推测三类结论；
8. 与既有报告的关系，明确是新发现、补齐或重复项（重复项不重做）。

## 7. 停止条件

- 若某一差异只在 Panther 未启用的 XGMAC、PCI、multi-MSI、chain mode、TSO/jumbo 或额外 DMA channel 条件下触发，明确降级，不沿该分支扩展。
- 若证据已在既有报告完整闭环，引用并跳过，不重复。
- 若精确来源或配置无法恢复，保留未知，不用模板、相邻版本或推测补值。
- 本方向不得访问设备、构建、安装软件、修改内核/驱动/DTB/系统/网络配置。
- 本方向完成前不得进入 B2.1/B2.2/B3 或后续独立专题。

## 8. 安全声明

本文件仅建立方向三静态审计工作边界和执行清单，不代表任何源码差异已验证，也不代表设备已通过网络测试。后续每次推进只完成一个子项并归档，不跳项、不扩大范围。