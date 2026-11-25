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
| D3-8 | 总矩阵与一致性审校 | 已完成（静态范围） | 四版本总矩阵、普通 DHCP 适用性和证据边界一致性审校 |

## 5. 方向三总体结项状态（2026-11-25）

D3-1～D3-8 已全部按原定顺序完成静态源码/Kconfig/DTS 审计。详细四版本矩阵和一致性结论见：
PANTHER-X2-B2-0-DIRECTION-3-D3-8-SYNTHESIS-CLOSEOUT-20261125.md。

| 子项 | 结项要点 | 仍保留的证据限制 |
|---|---|---|
| D3-1 Probe/platform | pclk 与 MDC CSR clock source 的版本差异确认 | pclk_mac 实际频率、CSR divider、clock enable/refcount 未验证 |
| D3-2 MDIO/PHY attach | MDIO parser 在 Panther 上等价；黄金版本有四次 PHYCR2/BMCR 写入，故障版本缺失 | 无 PHYCR2/BMCR readback、MDC/CLKOUT/RXC 波形；0x1801 Reserved bit 不应直接恢复 |
| D3-3 DMA init | 黄金版本 reset 前有 1500ms delay，故障版本缺失；reset poll interval 10ms→0.5ms；DMA/AXI/PBL/channel 算法总体相同 | 无 reset status/完成时间、硬件 addr64 feature dump |
| D3-4 TX descriptor | 6.1.65 TSO mapping first-descriptor 记录风险已在 6.1.116 修复；TX coalescing timer 1000→5000us | 无历史 TSO、NAPI/timer 触发和 ring-full 运行记录 |
| D3-5 RX descriptor/page-pool | page-pool create/refill、DMA sync、RX OWN/status 主路径一致 | 历史 rx_dropped 具体来源和 NAPI budget trace 未知 |
| D3-6 DMA API/coherency/IOMMU | streaming cache sync 四版本一致；GMAC1 无 dma-coherent/iommus；6.12 bounce 条件不命中普通 TX | 6.12 DMA_BOUNCE_UNALIGNED_KMALLOC 运行时值未单独核实；无历史 SWIOTLB counters |
| D3-7 IRQ/NAPI/recovery | IRQ status、NAPI gate、timeout/global reset/per-channel recovery 顺序一致 | 缺 6.1.174 c2f148d 历史 IRQ/FBE/NAPI trace |
| D3-8 总矩阵 | 四版本端点、适用条件、证据等级和方向二结论一致 | 不新增运行时证据 |

### 方向三总体判断

- 最值得后续关联的是黄金版本保留、两个故障版本缺失的 JL2xx1 初始化补丁族：四次 MDIO 写入与 DMA SW reset 前 1500ms delay；另有 MDC CSR clock source 从 stmmac_clk 改为 pclk。
- 这些差异可能影响 PHY 初始化和 DMA 启动时序，但没有现场 PHY register、clock、reset 状态证据，不能认定根因，也不直接提出恢复补丁。
- 普通 DHCP/UDP IPv4 单 skb 的 TX mapping/cache clean、DWMAC4 descriptor、DMA IRQ/NAPI/recovery 主路径没有发现故障版本新增的无条件阻断回归。
- 6.12-only coherent prep、unaligned kmalloc bounce、VLAN/TSO/EST/AF_XDP 等差异有明确触发条件，不可外推到普通 DHCP。
- 6.1.174 所有结论均以实际构建 source_hash c2f148d 为准；旧 upstream stable 3f06ed3e 报告只作历史参考，不替代实际故障源码。

**方向三状态：静态技术审计已完成，具备证据边界明确的结项条件，等待正式归档确认。** 不代表根因已确认，不代表 Panther X2 实机网络驱动通过；不自动启动方向四或 B2.1。

本阶段未访问设备、未构建、未安装软件、未修改系统/驱动/DTB/网络配置，未执行任何网络实测。

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