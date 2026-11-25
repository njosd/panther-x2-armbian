# Panther X2 B2-0 方向三 D3-5：STMMAC RX descriptor / buffer / page-pool 四版本审计（2026-11-25）

## 1. 范围与既有证据复用

本项审计 RX descriptor ownership/status、RX ring refill、page-pool create/alloc/recycle、DMA sync、普通 skb allocation failure、NAPI budget 和 RX error/overflow accounting。已复用 2026-11-19 的 6.1.116 vs 6.12.81 RX 报告，只补 6.1.65 和实际 6.1.174-rk35xx c2f148d；不重复普通 RX 分配失败和 page-pool API 的既有结论。

四版本源码端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

既有报告：PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md，已覆盖 6.1.116/6.12.81 的 RX 主函数、普通 skb allocation failure、page_pool refill fail、XDP/VLAN/checksum/page recycle 条件差异。

## 2. RX page-pool create / refill / DMA buffer 生命周期

四版本 stmmac_main.c 对照结果：

- page_pool_params 初始化代码块（从 struct page_pool_params pp_params 到 page_pool_create）四版本逐字一致。
- page_pool flags 四版本均为 PP_FLAG_DMA_MAP | PP_FLAG_DMA_SYNC_DEV。
- stmmac_rx_refill() 四版本函数体逐字一致；均通过 page_pool_alloc_pages() 分配，失败时退出 refill loop（break），该失败点本身不直接增加 rx_dropped。
- stmmac_rx_buf1_len() 四版本函数体逐字一致。
- RX refill 仍按 page_pool DMA address/buffer 长度填写 RX descriptor，并更新 RX tail pointer；未发现 6.1.65 与实际 c2f148d 的 refill 顺序或分配失败处理变化。
- stmmac_rx() 中 dma_sync_single_for_cpu() 对 buffer/secondary buffer 的调用在四版本均存在；没有发现 6.1.65 或 c2f148d 缺失同步调用的证据。

因此，6.1.65、6.1.116、实际 6.1.174 c2f148d 在 page-pool 创建、refill 及普通 buffer DMA sync 主路径上没有发现新回归；6.12 的 page recycle API 变化另见第 4 节。

## 3. RX descriptor ownership / status / tail pointer

| 项目 | 四版本差异 | 适用性结论 |
|---|---|---|
| dwmac4_set_rx_owner() | 6.1.65/116/174 代码相同；6.12 改为局部 flags 累积后 OR 写回，但设置的 OWN、BUFFER1_VALID_ADDR、可选 INT_ON_COMPLETION_EN 位相同 | 等价的 descriptor ownership handoff，无位定义/顺序变化证据 |
| dwmac4_wrback_get_rx_status() | 6.1.65/116 函数相同；6.1.174/6.12 去掉 net_device_stats 参数并调整统计字段归属；RX descriptor status bit 判断主体相同 | 主要是统计记账，不是 RX descriptor 状态解释回归 |
| dwmac4_dma_init_rx_chan() | 6.1.174 起增加 priv 参数以支持 DWMAC4 register address abstraction；实际寄存器写入序列保持相同 | Panther dwmac4_addrs 为 NULL，使用默认 offsets |
| RX tail pointer | 既有 DWMAC4 RX tail pointer helper 与 common refill 顺序未发现实质差异 | 未发现普通 RX ring kick 新回归 |

## 4. stmmac_rx() 四版本差异

### 4.1 6.1.65 → 6.1.116

stmmac_rx() 函数体逐字一致。唯一相邻 RX helper 差异为 stmmac_rx_vlan() 从直接把 skb->data cast 为 vlan_ethhdr 改为 skb_vlan_eth_hdr(skb) helper；仅 VLAN-tagged frame 解析相关，不命中 Panther 普通未打 VLAN 的 DHCP IPv4 报文。

### 4.2 6.1.116 → 实际 6.1.174 c2f148d

差异主要为 per-queue RX stats 累积、XDP context 结构包装、RX status API 参数变化，以及 NAPI budget 判断从 count >= limit 改为 count >= limit - 1 && limit > 1。普通 RX skb allocation failure 分支仍保持同样语义：napi_alloc_skb() 返回 NULL 时计入 rx_dropped 并进入 drain/recycle 路径；没有发现 c2f148d 新增无条件 drop。

预算边界变化可能让 poll 在 budget 大于 1 时少处理一个 descriptor 后返回，属于 NAPI 调度/公平性变化，不等于丢弃当前 descriptor；当前没有历史 NAPI budget/poll trace 证明其造成故障。

### 4.3 实际 6.1.174 c2f148d → 6.12.81

复用既有 RX 报告确认的差异：
- page_pool_release_page() 改为 skb_mark_for_recycle()，适配新 page_pool recycle API；
- VLAN stripping 根据 hw_vlan_en 选择 MAC-level stripping 或 driver-level stripping；
- checksum valid 标记新增 IP EtherType 与 csum_none 条件；
- XDP context、统计累积及 AF_XDP 相关支持演进。

这些差异均有明确条件。Panther 当前未见 XDP/AF_XDP 附着、VLAN-tagged DHCP 或 RX checksum error 的历史证据；不能将其直接认定为普通 DHCP RX drop 原因。

## 5. 普通 RX allocation / refill failure 的证据边界

1. 普通 skb allocation 失败点是 napi_alloc_skb()；四版本都存在，失败时计入 rx_dropped 并走 drain/recycle。
2. page_pool_alloc_pages() refill 失败时退出 refill loop，但该点本身不直接增加 rx_dropped。因此不能把 rx_dropped 总数等同于 page_pool refill failure 次数。
3. page_pool create flags、refill 函数和 DMA sync 调用四版本一致，未发现 6.1.65/6.1.174 c2f148d 与 6.1.116 的普通 RX cache sync 缺失。
4. 6.12 的 skb_mark_for_recycle() 是生命周期 API 迁移，不等于新增 DMA mapping；不能仅凭 CONFIG_DMA_NEED_SYNC=y 推断 page_pool cache sync 错误。
5. 现有 6.12.81 历史统计曾见 rx_dropped 增长，但没有直接证据证明 napi_alloc_skb() 在当时返回 NULL；该运行时归因仍未闭环。

## 6. D3-5 结论

### 已验证
- 6.1.65 与 6.1.116 的 stmmac_rx() 主函数逐字一致；普通 RX page-pool create/refill/buffer length 也一致。
- 实际 6.1.174 c2f148d 的 page-pool create/refill 与 6.1.116 相同；其 RX 主函数变化集中于 NAPI budget、XDP context 和统计记账，没有发现普通 skb allocation failure 分支新增无条件 drop。
- 6.12 page recycle、VLAN/checksum/XDP 变化与既有 116/612 报告一致，均有条件触发边界。
- DWMAC4 RX OWN handoff 和 status decode 的关键 descriptor 位语义没有发现故障版本回归。

### 未验证
- 没有历史 RX descriptor dump、DMA buffer address、page_pool allocation failure 事件或 NAPI poll trace。
- 无法证明历史 rx_dropped 增长具体来自 napi_alloc_skb()、XDP、checksum、VLAN 或其他错误分支。
- 6.1.65 源码端点仍为高置信度候选。

**D3-5 状态：已完成（静态源码范围）。** 未发现能解释普通 DHCP RX 丢失的、已证实无条件触发的 STMMAC RX descriptor/page-pool 回归。NAPI budget 变化和 6.12 recycle/VLAN/checksum 变化保留为条件性差异；历史 RX drop 具体来源仍需运行时证据，不能用静态代码推断。按顺序进入 D3-6 DMA API / coherency / IOMMU integration。

## 7. 精确源码链接

- [6.1.65 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.65 dwmac4_descs.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)
- [6.1.174-rk35xx dwmac4_descs.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c)