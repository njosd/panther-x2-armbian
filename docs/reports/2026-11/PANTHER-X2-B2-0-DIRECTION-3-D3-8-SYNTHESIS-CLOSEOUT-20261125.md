# Panther X2 B2-0 方向三 D3-8：STMMAC/DWMAC4 四版本总矩阵与一致性审校（2026-11-25）

## 1. 审计范围与来源基线

本报告汇总方向三 D3-1～D3-7。只采用以下四个固定源码端点：

| 版本 | 角色 | 源码端点 | 证据等级 |
|---|---|---|---|
| 6.1.65 | 黄金基准 A | unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc | 高置信度候选；尚无原始 build run 与 Image checkout SHA 绑定 |
| 6.1.116 | 黄金基准 B | unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e | 固定源码端点；原始构建二进制 commit 绑定仍有限 |
| 6.1.174-rk35xx | 故障基准 A | ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633 | 原始 Actions job source_hash 已验证 |
| 6.12.81-rk35xx | 故障基准 B | ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c | 原始构建来源已锁定 |

**关键来源校正：** 6.1.174-rk35xx 的实际构建源码是 c2f148d，不是 2026-11-19 部分 stable 对照报告使用的 upstream stable 3f06ed3e...。尤其 `stmmac_init_dma_engine()` 的 1500ms pre-reset delay：stable 3f06ed3e 有该 delay，但实际故障源码 c2f148d 没有。本轮以 c2f148d 作为故障基准，旧 stable 报告不覆盖该结论。

## 2. D3-1～D3-7 完成矩阵

| 子项 | 主要完成内容 | 最重要的版本差异 | Panther / 普通 DHCP 适用性 | 状态 |
|---|---|---|---|---|
| D3-1 Probe/platform resource | probe、clock、IRQ、资源解析及 Panther DTS 分支 | 黄金版本 MDC CSR 动态选择使用 stmmac_clk；故障版本使用 pclk。Panther DTS 的 pclk_mac 可供后两者获取 | 影响 MDIO MDC divider 时钟源；运行时频率/CSR 值未验证，不是普通 TX descriptor 直接差异 | 已完成 |
| D3-2 MDIO/PHY attach | MDIO bus、PHY node、bus_data、needs_reset、phylink attach | 黄金版本含 JL2xx1 workaround 的四次 MDIO 广播写入；实际 6.1.174 c2f/6.12 缺失。故障版本新增 mac_requires_rxc 管理语义 | 可能影响 RTL8211F 初始化/PHY RXC 管理；没有 PHYCR2/BMCR readback、RXC 波形或 suspend/resume 记录，不能认定根因 | 已完成 |
| D3-3 DWMAC4 DMA init | reset、DMA bus mode、AXI、PBL、channel、address width | 黄金版本 DMA reset 前 msleep(1500)，故障版本缺失；reset polling 从 10ms 缩至 0.5ms。DMA/AXI/channel init 算法总体一致 | 发生在接口 DMA 初始化阶段，可能影响启动时序；无 reset status/时钟 ready 运行时证据 | 已完成 |
| D3-4 TX descriptor | TSO multi-descriptor、mapping failure、ring shortage、completion/reclaim、TX timer/recovery | 6.1.65 TSO mapping 记在 first descriptor，6.1.116 起移到 last descriptor；TX coalescing timer 1000us→5000us | TSO mapping 差异不触发普通 DHCP 单 skb；timer 影响 completion/reclaim 延迟，不改变首个 skb 发射 | 已完成 |
| D3-5 RX descriptor/page-pool | page-pool create/refill、DMA sync、RX OWN/status、allocation failure、NAPI budget | refill 与 page-pool flags 四版本一致；故障分支有 NAPI budget 边界和 6.12 recycle/VLAN/checksum 演进 | 未发现普通 DHCP RX 的无条件 drop 回归；历史 rx_dropped 具体来源未知 | 已完成 |
| D3-6 DMA API/coherency/IOMMU | ARM64 cache maintenance、DMA direct map/sync、DMA mask、DTS IOMMU/coherency | coherent prep clean+invalidate→clean 仅 6.12；6.1.174 c2f 仍与黄金版本相同。6.12 新增 unaligned kmalloc bounce 条件 | 普通 DMA_TO_DEVICE cache clean 四版本一致；GMAC1 无 dma-coherent/iommus；bounce 条件不命中普通 TX | 已完成 |
| D3-7 IRQ/NAPI/watchdog/recovery | 主 IRQ、DMA status、NAPI schedule、timeout、per-channel/global recovery | 6.1.174/6.12 主要为寄存器地址抽象及统计字段变化；RI/TI/TBU/FBE/TPS handling、NAPI gate、reset worker 顺序一致 | 未发现普通 DHCP 的无条件 IRQ/NAPI/recovery 阻断分支；历史 c2f IRQ trace 缺失 | 已完成 |

## 3. 方向三最重要的差异集合

### 3.1 黄金版本有、两个故障版本缺失：初始化时序 bundle

目前方向三最值得后续关联的不是普通 descriptor 或 IRQ，而是同一 JL2xx1 相关初始化补丁族在黄金与故障源码之间的差异：

1. `stmmac_mdio_register()` 中四次 MDIO 写入：切换 page、写 PHYCR2、恢复 page、触发 BMCR software reset。黄金版本有，实际 6.1.174 c2f/6.12 缺失。
2. `stmmac_init_dma_engine()` 在 DMA SW reset 前 `msleep(1500)`：黄金版本有，实际 6.1.174 c2f/6.12 缺失。
3. 这两项均随 unifreq commit 49b5f340... 出现，commit message 为 JL2xx1 PHY fix；提交没有进一步说明 1500ms delay 的具体硬件时序依据。
4. 6.1.65/6.1.116 的 MDC CSR 动态选择以 stmmac_clk 为输入，6.1.174/6.12 改为 pclk；这可能改变 MDIO MDC divider 的选择。

这组差异可能影响外接 RTL8211F 的初始化和 DMA 启动相对时序，但 0x1801 包含 Reserved bit 组合，且缺少现场 PHYCR2/BMCR readback、MDC/CLKOUT/RXC 波形、DMA reset status。因此只列为高优先级待关联候选，不建议直接恢复写入或制作补丁。

### 3.2 其他真实但有条件的差异

- `dwmac4_dma_reset()` polling interval 从 10ms 缩短到 0.5ms，timeout 仍为 1s；没有证据证明 reset success condition 改变。
- 6.1.65 的 TSO mapping bookkeeping 有早期 unmap 风险，6.1.116 已修复；普通 DHCP 不走 TSO。
- TX coalescing timer 默认值从 1000us 改为 5000us，且后续版本避免在 NAPI 已 scheduled 时重复 arm；影响 completion/reclaim 时间，不是首个 skb 发送决策。
- 6.12 的 VLAN TSO、CHECKSUM_PARTIAL fallback、EST max-SDU、AF_XDP metadata、page recycle API、DMA unaligned kmalloc bounce 均有明确条件；Panther 普通未打 VLAN 的 DHCP 单 skb 不命中。
- 6.12 ARM64 coherent allocation prep 从 clean+invalidate 改为 clean，但实际 6.1.174 c2f 仍使用 clean+invalidate；不是两个故障版本共同差异。
- 6.1.174/6.12 DWMAC4 register address abstraction 对 Panther 使用 NULL default offsets；未发现寄存器地址目标改变。

## 4. 普通 DHCP/UDP 单 skb 的跨层适用性

以普通 IPv4 DHCP、单 skb、未分片、无 GSO/TSO、无 VLAN、常规 queue0 Ethernet netdevice 为边界：

1. 普通 TX skb mapping、DMA_TO_DEVICE cache clean、DWMAC4 descriptor OWN/地址写入、tail pointer、DMA interrupt RI/TI、NAPI schedule 和 recovery 主路径没有发现故障版本新增的无条件 drop/阻断分支。
2. 6.12 `dma_kmalloc_needs_bounce` 对 DMA_TO_DEVICE 属于 safe direction，不触发新增 bounce；`DMA_NEED_SYNC=y` 不等于 GMAC1 skip sync。
3. GMAC1 DTS 没有 dma-coherent/iommus，按 non-coherent direct DMA 设备分析；显式 DMA sync 代码四版本一致。
4. 普通 DHCP 不触发 TSO mapping、VLAN TSO、EST max-SDU、AF_XDP、XDP、jumbo 或多队列 MSI 条件分支。
5. 因此方向三没有发现一个可直接解释普通 DHCP TX 无帧输出的、已证实无条件触发的 STMMAC/DWMAC4 通用回归。

这不代表所有差异都与故障无关；MDIO/PHY 与 DMA reset 初始化时序 bundle 仍是高优先级候选，必须等待相应运行时证据才能判断。

## 5. 未决证据与边界

| 未决项 | 证据上限 | 后续需要的证据类型 |
|---|---|---|
| 6.1.65 精确 build source commit | 高置信度候选源码端点 | 原始 Actions checkout SHA 与 Image/artifact 绑定 |
| 6.1.116 精确 build commit | 源码端点固定、实际配置可核对 | 原始构建记录与 Image SHA 绑定 |
| 6.1.174 PHYCR2/BMCR 实际状态 | 源码缺少 workaround 已验证 | 历史 MDIO readback 或可控启动时序对照 |
| 1500ms delay 是否必要 | 源码差异已验证，硬件时序依据未证实 | reset/clock ready 时间、PHY reset 与 DMA SWR 状态记录 |
| MDC CSR divider / pclk_mac 运行时状态 | DTS/parser 输入已验证 | 实际 clock rate、CSR divider、MDC 波形 |
| DMA address width / EAME | 软件逻辑已验证；6.1.116/6.12 有 32/32 历史日志 | 6.1.65/174 的 feature register 与 DMA mask 记录 |
| TX/RX ring 与 NAPI 运行时状态 | 静态函数路径已验证 | 历史 descriptor OWN、IRQ status、NAPI poll、queue stop/wake trace |
| 6.1.174 历史最终 config 部分字段 | 原资产不可恢复，见方向二 | 仅当找到原始 artifact/config 才能补证 |

这些是运行时/历史资产限制，不是尚未执行的静态专题；方向三不重复设备测试、不构建、不修改系统配置。

## 6. 一致性审校

- D3-1～D3-7 均使用相同四版本端点；6.1.174 始终使用实际 build source_hash c2f148d。
- D3-3 已明确修正 2026-11-19 stable 3f06ed3e 对照的适用边界；旧 stable snapshot 的 1500ms delay 结论不再用于描述实际 c2f148d。
- D3-2 的四次 MDIO 写入与 D3-3 的 1500ms delay 均追溯到同一 49b5f340... 补丁族，未把它们误计为两个独立来源事件。
- D3-4/5/6/7 的条件分支与 D2 方向二 §53 普通 DHCP/UDP 适用性边界一致；没有把 TSO、VLAN、EST、AF_XDP、XDP 或 unaligned bounce 条件外推到普通 DHCP。
- D3-6 的 clean-only coherent prep 变化只属于 6.12；未错误标注为 6.1.174/6.12 两个故障版本共同差异。
- 方向三所有子项均按静态源码/Kconfig/DTS 范围结项；未把静态审计结论外推为 Panther 实机驱动通过或故障根因确认。

## 7. 方向三结项评估

**评估结论：方向三原定静态审计范围已完成，具备证据边界明确的结项条件。**

理由：
1. D3-1～D3-7 全部按原定顺序完成，D3-8 总矩阵与一致性审校通过。
2. 四版本源码差异、Panther DTS 实际命中分支、配置证据等级和条件适用性均已记录。
3. 方向三最重要的候选差异与普通 DHCP 单 skb 的适用性已区分；没有把源码差异直接等同根因。
4. 剩余事项均为历史运行时证据、构建来源绑定或不可恢复配置资产，不是当前仍可通过重复 STMMAC/DWMAC4 静态审计解决的明确子项。
5. 继续重复相同源码/Kconfig 检索不会提高证据等级；若后续取得新的历史日志/原始 artifact，应按本报告未决表定点补证。

**状态：方向三静态技术审计已完成，等待正式归档确认。** 本报告不宣布 B2-0 全部完成，不启动方向四或 B2.1，不进行设备访问、构建、安装或系统配置修改。

## 8. 子项报告索引

- D3-1：PANTHER-X2-B2-0-DIRECTION-3-D3-1-STMMAC-PLATFORM-PROBE-DIFF-20261125.md
- D3-2：PANTHER-X2-B2-0-DIRECTION-3-D3-2-MDIO-PHY-ATTACH-DIFF-20261125.md
- D3-3：PANTHER-X2-B2-0-DIRECTION-3-D3-3-DWMAC4-DMA-INIT-DIFF-20261125.md
- D3-4：PANTHER-X2-B2-0-DIRECTION-3-D3-4-TX-DESCRIPTOR-REMAINING-BRANCHES-20261125.md
- D3-5：PANTHER-X2-B2-0-DIRECTION-3-D3-5-RX-DESCRIPTOR-PAGEPOOL-DIFF-20261125.md
- D3-6：PANTHER-X2-B2-0-DIRECTION-3-D3-6-DMA-API-COHERENCY-IOMMU-20261125.md
- D3-7：PANTHER-X2-B2-0-DIRECTION-3-D3-7-IRQ-NAPI-WATCHDOG-RECOVERY-20261125.md