# Panther X2 B2-0 方向三：STMMAC / DWMAC4 / DMA 静态审计有条件结项（2026-11-25）

## 1. 结项决定与范围

方向三按用户批准的“证据边界明确的有条件结项”归档。

本结项覆盖四版本 STMMAC common/platform、DWMAC4 MAC/DMA、descriptor/ring、DMA API/coherency/IOMMU、IRQ/NAPI/watchdog/recovery 的既定静态审计范围。比较样本固定为 6.1.65、6.1.116、6.1.174-rk35xx、6.12.81-rk35xx。

本结项只表示既定源码、Kconfig、DTS 与已有配置证据的静态审计完成；不表示已找到网卡故障根因，不表示驱动通过实机验证，也不表示 B1、B2.1 或后续网络验收通过。

## 2. 子项完成情况

| 子项 | 状态 | 主要结论 |
|---|---|---|
| D3-1 STMMAC platform probe/resource parsing | 已完成 | 四版本 probe/resource 解析差异已核对；pclk/pclk_mac 与 MDC CSR clock source 变化已记录；运行时频率、寄存器值未知 |
| D3-2 MDIO/PHY attach common 层 | 已完成 | Panther DTS 下四版本 parser 最终 bus/PHY 结果等价；黄金版本有、故障版本缺失的四次 PHYCR2/BMCR 写入保留为候选，不认定根因 |
| D3-3 DWMAC4 DMA 初始化 | 已完成 | 黄金版本 DMA reset 前有 1500ms delay，故障版本缺失；poll interval 10ms→0.5ms；DMA/AXI/channel 软件初始化总体相同 |
| D3-4 TX descriptor 未覆盖分支 | 已完成 | 6.1.65 TSO 多 descriptor mapping 记录位置缺陷及 TX coalescing timer 变化已分类；未发现普通 DHCP 单 skb 的无条件 descriptor 回归 |
| D3-5 RX descriptor/buffer/page-pool | 已完成 | 普通 RX refill/page-pool/DMA sync/OWN/status 主路径未发现能解释普通 DHCP RX 丢失的无条件回归 |
| D3-6 DMA API/coherency/IOMMU | 已完成 | 四版本普通 streaming DMA sync 一致；Panther GMAC1 DTS 无 dma-coherent/iommus；6.12 bounce 条件不命中普通 TX DMA_TO_DEVICE |
| D3-7 IRQ/NAPI/watchdog/recovery | 已完成 | 主 IRQ、NAPI schedule/complete、关键 DMA status decode 与 recovery 顺序未发现故障版本新增的无条件阻断分支 |
| D3-8 四版本总矩阵与一致性审校 | 已完成 | 各子项状态、版本端点、普通 DHCP/UDP 适用性和未验证项已汇总；不存在待执行的方向三静态子项 |

## 3. 关键差异与适用性

1. **MDIO 初始化候选差异：** 6.1.65/6.1.116 存在四次 PHYCR2/BMCR MDIO 写入，实际 6.1.174 c2f148d/6.12.81 缺失。写入值涉及 Reserved bit，缺少现场寄存器回读和时钟波形，不得直接认定为故障根因或制作恢复补丁。
2. **DMA reset 时序差异：** 黄金版本 reset 前有 1500ms delay，故障版本缺失；reset polling interval 从 10ms 缩短到 0.5ms。硬件 reset 完成时间和时钟 ready 状态没有历史运行时证据。
3. **TX 条件分支：** 6.1.65 TSO 多 descriptor mapping 修正及 TX coalescing timer 变化保留；普通 DHCP 单 skb 不因此自动命中 TSO 分支。
4. **RX 条件分支：** NAPI budget、page recycle、VLAN/checksum/XDP 等变化按实际 Panther 配置和 skb 条件分类；没有证据把它们升级为普通 DHCP RX 的无条件回归。
5. **DMA/IRQ/recovery：** 未发现普通 DHCP/UDP 主路径中新增的无条件 DMA cache sync 缺失、错误 GMAC IOMMU 路径、IRQ/NAPI schedule 阻断或 recovery 顺序缺失。

## 4. 四版本来源与证据边界

| 版本 | 角色 | 源码证据等级 |
|---|---|---|
| 6.1.65 | 第一黄金基准 | `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`，高置信度候选；未与原始 Image 精确绑定 |
| 6.1.116 | 后期同机正常基准 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，源码比较端点；历史 Image 精确构建来源仍有限制 |
| 6.1.174-rk35xx | 故障基准 | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，实际构建源码端点 |
| 6.12.81-rk35xx | 故障基准 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，已确认源码端点 |

不得把 6.1.65/6.1.116 的源码比较端点表述为历史 Image 的密码学级构建绑定；不得把 6.1.174 无法恢复的历史最终配置字段补写为 y/n。

## 5. 未验证事项（结项后保留）

- 6.1.65、6.1.116 历史 Image 与精确 source commit 的二进制级绑定。
- 6.1.174 历史最终 kernel.config 中无法恢复的字段。
- DMA reset 的现场完成时间、feature register 实际 addr64 值、DMA mask 运行时结果。
- 故障现场 macirq/RI/TI/FBE/NAPI trace、RX descriptor/page-pool 事件、TX mapping/reclaim 运行时状态。
- PHYCR2/BMCR 实际寄存器状态、CLKOUT/RXC 波形及相关初始化动作在历史故障窗口是否执行。

上述项目属于原始资产不可恢复或历史运行时证据缺失，不构成继续重复静态源码审计的理由。只有出现新的原始构建资产或历史运行时证据时，才允许定点补证。

## 6. 边界与下一方向

- 方向三不包含 Rockchip GMAC glue/CCF/CRU/clock/reset 的完整专题，也不包含 PHYLIB/PHYLINK/RTL8211F PHY driver 专题。
- 按 B2-0 原始顺序，下一方向为**方向四：Rockchip GMAC glue、CCF/CRU、时钟与复位路径（对应原组件方向 B2-3）**；随后才是方向五 MDIO/PHYLIB/PHYLINK/RTL8211F（对应 B2-4），最后进行版本决策与组件恢复顺序整合。
- 已有 GMAC glue/clock/power、CRU parent/gate/reset、6.18.63 Kconfig/Makefile 报告必须先回读并复用。方向四只补原计划范围内尚未闭环的四版本差异与证据矩阵，不重复已经完成的内容。
- 本轮及后续 B2-0 仍只做仓库源码、Kconfig、DTS、既有 config 和历史报告只读审计；不访问设备、不构建、不安装软件、不修改系统/驱动/DTB/网络配置、不启动 B2.1。

## 7. 方向三关联报告

- `PANTHER-X2-B2-0-DIRECTION-3-STMMAC-DWMAC4-DMA-AUDIT-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-1-STMMAC-PLATFORM-PROBE-DIFF-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-2-MDIO-PHY-ATTACH-DIFF-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-3-DWMAC4-DMA-INIT-DIFF-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-4-TX-DESCRIPTOR-REMAINING-BRANCHES-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-5-RX-DESCRIPTOR-PAGEPOOL-DIFF-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-6-DMA-API-COHERENCY-IOMMU-20261125.md`
- `PANTHER-X2-B2-0-DIRECTION-3-D3-7-IRQ-NAPI-WATCHDOG-RECOVERY-20261125.md`

**最终状态：方向三已按“证据边界明确的有条件结项”归档。**
