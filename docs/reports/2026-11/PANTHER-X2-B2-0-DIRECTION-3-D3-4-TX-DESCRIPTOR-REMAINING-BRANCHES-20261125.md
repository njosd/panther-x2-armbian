# Panther X2 B2-0 方向三 D3-4：STMMAC TX descriptor 未覆盖分支四版本审计（2026-11-25）

## 1. 范围与复用

本项只补充 TX descriptor 既有报告未覆盖的条件路径：TSO 多 descriptor 映射记录、mapping failure/descriptor shortage、TX completion/reclaim、timer、recovery，以及 6.12 新增的条件性 TX 分支。普通单 skb mapping/OWN/barrier/tail pointer 与普通小帧 checksum 已在既有报告闭环，不重做。

四版本端点：6.1.65 候选 unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc；6.1.116 unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e；实际 6.1.174-rk35xx ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633；6.12.81-rk35xx ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

复用既有报告：
- PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md §14：DWMAC4 descriptor format、OWN、DMA address low/high word、普通 mapping、IOMMU DTS、PHY fixup。
- 同一报告 §40：6.12 checksum fallback、queue0 coe_unsupported、EST max-SDU、普通 DHCP/0x88B5 短帧适用性。
- PANTHER-X2-STMMAC-TX-DMA-MAPPING-DESCRIPTOR-OWNERSHIP-116-VS-174-20261119.md：普通 skb mapping/OWN/barrier/tail-pointer 主路径。
- PANTHER-X2-STABLE-116-174-STMMAC-TX-CORE-DIFF-20261119.md：TX core 稳定分支差异。该旧报告的 6.1.174 upstream stable endpoint 不是实际 c2f148d；本项以 c2f148d 对真实故障构建补齐。

## 2. DWMAC4 descriptor helper：四版本一致

直接对四个精确端点的 dwmac4_descs.c 函数体比较：

| 函数 | 6.1.65 | 6.1.116 | 6.1.174 c2f148d | 6.12.81 |
|---|---|---|---|---|
| dwmac4_rd_prepare_tx_desc() | 同一函数体 | 同一 | 同一 | 同一 |
| dwmac4_rd_prepare_tso_tx_desc() | 同一函数体 | 同一 | 同一 | 同一 |
| dwmac4_set_tx_owner() | 同一函数体 | 同一 | 同一 | 同一 |
| dwmac4_set_addr() | 同一函数体 | 同一 | 同一 | 同一 |
| dwmac4_set_sec_addr() | 同一函数体 | 同一 | 同一 | 同一 |

因此没有发现四版本改变普通 DWMAC4 descriptor 的 des0/des1 DMA address 低高位写入、des2 buffer length、des3 FD/LD/checksum/OWN 编码的差异。TSO descriptor helper 同样未变。

## 3. TSO 多 descriptor DMA mapping 生命周期：6.1.65 与后续版本存在真实差异

对 stmmac_tso_xmit() 逐函数比较发现：

- 6.1.65：在 map 整个 skb linear head 后，把 DMA mapping address/length/map_as_page/buf_type 记录在 first_entry 对应的 tx_skbuff_dma[]。
- 6.1.116：改为把同一 DMA mapping 记录在 tx_q->cur_tx（TSO payload 最后一个 descriptor）对应的 tx_skbuff_dma[]；源码新增注释明确说明，多个 descriptor 共享同一线性 DMA buffer 时，应由最后 descriptor 完成后再 unmap，避免 DMA engine 仍可能读取后续尾部区域时过早解除映射。
- 6.1.174 c2f148d：采用 6.1.116 的 last-descriptor mapping bookkeeping；tso_des 局部变量只是把 des + proto_hdr_len 明确传给 tso allocator，地址语义相同。
- 6.12.81：保留 last-descriptor mapping bookkeeping；另对带硬件 VLAN tag 的 TSO skb 先执行 __vlan_hwaccel_push_inside()，避免 TSO 分段后 VLAN tag 丢失。

适用性：Panther DTS 声明 snps,tso，硬件 TSO capability 可用时该分支可被使用；但普通 DHCP Discover、小于 MTU 的单 skb 不属于 GSO/TSO，不命中此差异。6.1.65 的早期 unmap 风险仅限 TSO 多 descriptor 路径，不能外推为普通 DHCP TX 根因。

## 4. stmmac_xmit() 普通 TX 与 mapping failure / descriptor shortage

四版本 stmmac_xmit() 精确函数差异归纳：

1. 6.1.65 与 6.1.116 函数体完全一致。
2. 6.1.116→实际 6.1.174 c2f148d 的差异仅为 per-queue stats 更新方式和 drop/error 计数位置；没有改变普通 skb 的 DMA mapping、mapping_error 分支、descriptor availability 检查、OWN 发布或 tail pointer 触发顺序。
3. 6.1.174→6.12.81 新增 EST max-SDU 条件 drop、非 IP/不支持 COE queue 的 CHECKSUM_PARTIAL software checksum fallback，以及 per-queue stats API；普通 DHCP IPv4 queue0 无 EST 配置、无 coe_unsupported、EtherType 为 IPv4，因此两个新增条件均不命中。该结论与 §40 已有审计一致。
4. 6.12 的 stmmac_enable_dma_transmission() 调用增加 queue 参数，但 DWMAC4 的 dwmac4_dma_ops 未注册 enable_dma_transmission callback；DWMAC4 使用独立 start_tx/stop_tx callback 和 set_tx_tail_ptr。故该通用 callback 签名变化对 Panther DWMAC4 不产生直接行为变化。

stmmac_tx_avail() 四版本函数体完全一致；普通 ring-full 判断与 NETDEV_TX_BUSY/queue stop 逻辑未发现版本差异。普通 mapping failure 分支也没有发现除前述 6.12 checksum fallback 入口之外的条件变化。

## 5. TX completion/reclaim 与 recovery

### 5.1 descriptor reclaim

stmmac_tx_clean() 四版本的 OWN 检查、dma_rmb()、descriptor status 判断、DMA unmap_single/unmap_page 和 skb/XDP frame 释放主路径一致。差异主要为：
- 6.1.65→6.1.116：TX clean 与 NAPI coalescing timer 的协作改为 pending_packets 返回/后续 NAPI 处理；不是 DMA unmap 或 descriptor ownership 变化。
- 6.1.116→6.1.174：per-queue stats 从循环内逐项更新改为累计后统一更新；descriptor reclaim/unmap 顺序未改变。
- 6.1.174→6.12：增加 AF_XDP TX metadata completion；仅 tx_q->xsk_pool 存在且 metadata enabled 时触发，Panther 当前家庭照片服务目标不使用 AF_XDP，不命中。

### 5.2 TX coalescing timer

- STMMAC_COAL_TX_TIMER：6.1.65 = 1000us；6.1.116、6.1.174 c2f148d、6.12.81 = 5000us。
- stmmac_init_coalesce() 对每个实际 TX channel 设置 tx_coal_frames 和 tx_coal_timer，因此默认 timer 非零。
- 6.1.65 stmmac_tx_timer_arm() 在 timer 非零时直接 arm；6.1.116 及后续版本先检查对应 NAPI 是否 scheduled，已 scheduled 时取消 timer，避免重复 arm。

这是 TX completion/reclaim 调度延迟的真实差异，影响的是 TX completion polling/cleaning 的时间行为，不是首个 skb 的 DMA map 或 MAC 发射指令。对普通低速 DHCP 帧是否实际延迟、是否造成队列耗尽，需要历史 NAPI/queue 状态证据；当前无该证据。

### 5.3 TX error recovery

stmmac_tx_err() 四版本均执行：stop netdev TX queue → stop TX DMA → free TX skb buffers → clear descriptors → reset TX queue → re-init TX channel → start TX DMA → wake queue。6.1.174/6.12 的差异仅是统计字段归属；未发现 recovery 动作顺序改变。

## 6. 对 Panther 普通 DHCP TX 的适用性

| 差异 | 触发条件 | Panther 普通 DHCP IPv4 单 skb | 判断 |
|---|---|---|---|
| 6.1.65 TSO mapping 记录在 first descriptor | GSO/TSO，线性 buffer 被拆成多个 DMA descriptor | 不触发 | 特殊 TSO 路径，非 DHCP 根因 |
| 6.12 TSO VLAN software insertion | VLAN-tagged TSO skb | 不触发 | 不适用 |
| 6.12 checksum fallback | CHECKSUM_PARTIAL 且 COE unsupported 或非 IP EtherType | queue0 支持 COE，IPv4 EtherType；或 DHCP 为 CHECKSUM_NONE | 已有 §40 结论：不触发 |
| 6.12 EST max-SDU drop | EST enabled 且 queue max_sdu 非零且 skb 超限 | Panther 未见 EST/TAPRIO 配置 | 不适用 |
| 6.1.65→后续 TX timer 1000→5000us、NAPI scheduled 检查 | TX completion timer / NAPI 状态 | 可能影响完成回收延迟；不改变初次 TX descriptor | 保留为 completion timing 差异 |
| 6.12 enable_dma_transmission queue 参数 | generic callback 注册且调用 | DWMAC4 dma_ops 未注册该 callback | 不适用 |

## 7. D3-4 结论

### 已验证
- DWMAC4 descriptor prepare/OWN/address helper 五个关键函数四版本完全一致。
- 普通 stmmac_xmit mapping、mapping_error、descriptor availability 主体未见故障版本无条件回归；6.1.174 c2f148d 相对 6.1.116 主要是 stats 变更。
- 6.1.65 TSO 多 descriptor mapping bookkeeping 存在早期 unmap 风险，6.1.116 已修复，实际 6.1.174/6.12 保持修复后行为。
- 6.12 的 VLAN TSO、checksum fallback、EST max-SDU 和 AF_XDP metadata 均有明确条件；普通 DHCP IPv4 单 skb 不命中。
- TX completion timer 默认值从 1000us 改为 5000us，arm 条件也变化；TX recovery 动作顺序一致。

### 未验证
- 没有历史证据证明 Panther 运行时启用过 TSO、TX coalescing 参数是否被用户空间/ethtool 改写，或 NAPI scheduled 状态。
- 没有历史 ring-full、DMA mapping error、TX completion timer 触发频率和 descriptor reclaim 延迟日志。
- 6.1.65 源码仍为高置信度候选端点，不是历史 Image 二进制级绑定。

**D3-4 状态：已完成（静态源码范围）。** 本项未发现可解释普通 DHCP 单 skb 无帧输出的无条件 descriptor 编码或 mapping 回归。保留 6.1.65 TSO last-descriptor mapping bugfix、TX coalescing timer 变化为条件性差异。按原顺序进入 D3-5 RX descriptor/buffer/page-pool lifecycle。

## 8. 精确源码链接

- [6.1.65 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.65 dwmac4_descs.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)
- [6.1.116 dwmac4_descs.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)
- [6.1.174-rk35xx dwmac4_descs.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)
- [6.12.81-rk35xx dwmac4_descs.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)