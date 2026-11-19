# Panther X2：STMMAC TX DMA mapping、descriptor ownership 与 barrier 对比（6.1.116 vs 6.1.174）

## 1. 比较基线

- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e（已知 Panther 正常基线）
- 6.1.174：unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7（历史最早明确异常版本）
- 比较对象限定为 STMMAC 通用 TX 主路径、DWMAC4 descriptor helper 和 DMA init 等关键位置。

## 2. 典型 skb 小帧 TX 主路径：未发现功能性差异

两版 `stmmac_xmit()` 的普通非 jumbo skb 路径都执行：
1. `dma_map_single(priv->device, skb->data, nopaged_len, DMA_TO_DEVICE)`；
2. 检查 `dma_mapping_error()`；
3. 保存 DMA 地址到 `tx_skbuff_dma[]`；
4. `stmmac_set_desc_addr()` 写入 descriptor buffer 地址；
5. `stmmac_prepare_tx_desc()` 设置长度、FIRST/LAST 和 OWN；
6. 更新 `cur_tx`；
7. `stmmac_flush_tx_descriptors()` 执行 `wmb()`，更新 TX tail address 并写 tail pointer。

两版在上述普通小帧数据流的关键操作、顺序和错误处理上一致。6.1.174 中出现的主要差异是统计结构改造（例如 txq_stats、u64_stats_update），没有改变 DMA_TO_DEVICE mapping 或 descriptor 地址交付顺序。

## 3. DMA mapping / unmapping

普通 skb 数据仍由 DMA API `dma_map_single(..., DMA_TO_DEVICE)` 映射，TX completion 路径按保存的 DMA 地址执行 unmap。两版没有发现普通 skb TX 路径改成直接使用 CPU physical address、改变 DMA direction、改变 mapping size 或跳过 mapping error 检查。

XDP/page_pool 分支也都保留 `dma_sync_single_for_device(..., DMA_BIDIRECTIONAL)`；但 Panther DHCP/普通网络 skb 不应与 XDP TX 分支混为一谈。

## 4. descriptor ownership 和内存屏障

在 `dwmac4_descs.c`：
- `dwmac4_set_tx_owner()` 两版都通过 `p->des3 |= cpu_to_le32(TDES3_OWN)` 设置 OWN。
- `dwmac4_rd_prepare_tx_desc()` 两版都在首 descriptor OWN 发布前使用 `dma_wmb()`，然后写 DES3。
- `stmmac_flush_tx_descriptors()` 两版都在写 tail pointer 前使用 `wmb()`。
- descriptor ring 的 OWN 发布和 tail pointer kick 顺序没有发现回归。

注意：`dma_wmb()` 与 `wmb()` 的语义并不完全相同；本轮结论是两版相应位置的屏障调用保持一致，而不是说两种屏障可以互换。

## 5. DMA reset / init 等待

两版 `stmmac_init_dma_engine()` 都保留 `msleep(1500)`，随后执行 `stmmac_reset()` 并检查 reset 返回值。该位置不存在 116→174 的等待缩短或 reset 调用顺序变化。

## 6. 当前结论

1. 在已核对的 STMMAC 通用 TX 小帧路径中，6.1.116 与 6.1.174 的 DMA mapping、descriptor 地址写入、OWN 发布、barrier 和 tail-pointer kick 顺序一致。
2. 没有发现 6.1.174 把普通 skb TX 改成错误 DMA direction、漏做 DMA map/unmap、提前发布 OWN 或移除 barrier 的证据。
3. 本轮未发现可解释“软件 TX 计数增加但外部没有收到帧”的 STMMAC 通用 TX 回归点。
4. 因此不再把通用 stmmac_main.c 的普通 skb TX mapping/ownership 作为高优先级候选。

## 7. 重要限制与下一步

本轮还不能据此排除 Rockchip glue 层、DWMAC4 DMA register programming、SoC DMA coherency/IOMMU/内存属性或 boot-time firmware 配置差异。下一步应限定比较：
- `dwmac-rk.c` 中 RK3566 power/clock/reset、DMA interface 与 AXI bus 配置；
- `dwmac4_dma.c` 中 DMA channel TX/RX start、PBL、地址宽度及 descriptor base/tail register programming；
- 6.1.116 与 6.1.174 对应 RK3566 DTS 的 `dma-coherent`、IOMMU、memory-region 和 AXI 属性；
- 若以上 Linux 源码/DTS 也等价，再回到 6.12 与 6.1 的差异，而不是继续重复普通 skb mapping 检查。

未进行实机测试、寄存器读取、设备配置更改或驱动修改。

## 8. 源码链接

- 6.1.116 stmmac_main.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.1.174 stmmac_main.c：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.1.116 dwmac4_descs.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c
- 6.1.174 dwmac4_descs.c：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c