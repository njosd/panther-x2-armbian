# Panther X2 B2-0 方向三 D3-6：DMA API / coherency / IOMMU 四版本交叉审计（2026-11-25）

## 1. 范围与复用

本项核对四版本 DMA mapping/sync API、ARM64 cache maintenance、coherent descriptor allocation、DMA mask、DMA_NEED_SYNC/DMA_BOUNCE_UNALIGNED_KMALLOC 配置语义，以及 Panther GMAC1 DTS 的 dma-coherent/iommus 绑定。复用既有 6.1.116 vs 6.12.81 ARM64 DMA coherency 报告和 6.1.116 完整 kernel.config 证据，只补 6.1.65 与实际 6.1.174-rk35xx c2f148d。

固定源码端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

## 2. Panther GMAC1 的 DTS coherency / IOMMU 绑定

四版本 rk356x.dtsi 的 gmac1 节点均没有 dma-coherent 或 iommus 属性。SoC DTSI 其他 VPU/NPU/VOP/视频设备节点存在 iommus 属性，但不能把这些节点的 IOMMU domain 误认为 GMAC1 使用 IOMMU。

因此：
- OF DMA coherency 默认将 GMAC1 作为 non-coherent device；DMA mapping/sync 必须遵守非一致性 DMA API 语义。
- CONFIG_IOMMU_DMA=y、CONFIG_ROCKCHIP_IOMMU=y 仅表示内核包含 IOMMU 框架/驱动，不证明 GMAC1 设备挂入 IOMMU domain。
- GMAC1 未声明 iommus，OF IOMMU configure 对该设备不取得 GMAC1 IOMMU mapping domain；其 DMA API 路径按 direct DMA ops 处理。

该结论在 6.1.65、6.1.116、实际 6.1.174 c2f148d、6.12.81 四版本的 Panther SoC DTSI 上一致；与既有 6.1.116/6.12.81 报告一致。

## 3. ARM64 DMA API 源码差异

### 3.1 普通 streaming DMA cache maintenance

四版本 arch/arm64/mm/dma-mapping.c 的以下函数体逐字一致：

- arch_sync_dma_for_device()：调用 dcache_clean_poc()；
- arch_sync_dma_for_cpu()：DMA_TO_DEVICE 直接返回，其他方向调用 dcache_inval_poc()；
- 6.1.65/6.1.116/实际 6.1.174 c2f148d/6.12.81 均保持相同实现。

因此普通 STMMAC TX DMA_TO_DEVICE payload 的 ARM64 cache clean 没有版本差异；RX DMA_FROM_DEVICE 的 CPU-side invalidate 也没有版本差异。不能把 6.12 CONFIG_DMA_NEED_SYNC=y 单独解释为 TX clean 缺失。

### 3.2 coherent descriptor allocation prep

arch_dma_prep_coherent() 是本方向确认的真实 ARM64 cache maintenance 变化：

| 版本 | arch_dma_prep_coherent() |
|---|---|
| 6.1.65 | dcache_clean_inval_poc() |
| 6.1.116 | dcache_clean_inval_poc() |
| 6.1.174-rk35xx c2f148d | dcache_clean_inval_poc() |
| 6.12.81-rk35xx | dcache_clean_poc() |

因此此前 6.1.116 vs 6.12.81 报告发现的 clean+invalidate → clean 变化，四版本核对后确认是 **6.12.81 单独变化**；实际 6.1.174 故障构建仍与两个黄金版本一样执行 clean+invalidate。它不能解释 6.1.174 与 6.12.81 两个故障版本共同出现的问题。

6.1.116/6.12.81 既有报告已说明该上游变化的 ARM64 DMA API 理由：coherent allocation prep 只需 clean 到 PoC，额外 invalidate 在存在 cacheable linear-map alias 时并不能防止后续 speculative refetch。故此差异是真实实现变化，但目前不构成 descriptor ring stale-cache 根因证据。

### 3.3 DMA_DIRECT_REMAP 与 coherent allocation

四版本 arch/arm64/Kconfig 均 select DMA_DIRECT_REMAP。STMMAC descriptor ring 通过 dma_alloc_coherent() 分配；GMAC1 non-coherent 属性使 ARM64 coherent remap path 相关。6.1.65/116/174 的 coherent prep 仍为 clean+invalidate，6.12 改为 clean；运行时 allocator 分支没有 trace 记录，但 Kconfig、DTS 与驱动调用链足以确认这不是普通 skb payload clean 的差异。

## 4. 6.12 新增 DMA API 条件分支

### 4.1 CONFIG_DMA_NEED_SYNC

- 6.1.65/6.1.116/6.1.174 所用 6.1 Kconfig 中没有 CONFIG_DMA_NEED_SYNC 符号；不能把“无该符号”写成同名功能关闭。
- 6.12.81 RK35xx 构建模板包含 CONFIG_DMA_NEED_SYNC=y；用户 2026-11-19 提供的 6.12.81 运行配置也确认该符号为 y。
- 6.12 引入 dma_skip_sync / dma_need_sync 相关优化接口；但 Panther GMAC1 没有 dma-coherent 属性，dev_is_dma_coherent(dev) 为 false。普通 direct DMA path 仍执行 arch_sync_dma_for_device()/arch_sync_dma_for_cpu()，没有证据表明 GMAC1 被设置为 skip-sync。

结论：DMA_NEED_SYNC=y 不等于“跳过 GMAC1 cache sync”；必须结合设备 coherent 属性和具体 DMA API 分支判断。

### 4.2 CONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC

6.12.81 RK35xx config-6.12 构建模板启用 CONFIG_DMA_BOUNCE_UNALIGNED_KMALLOC=y；当前归档的 6.12.81 现场关键 config 输出没有单独记录该符号，故最终运行值按“模板 y、运行时未单独核实”标注。6.1 Kconfig 不包含该选项。

6.12 include/linux/dma-map-ops.h 的 dma_kmalloc_needs_bounce() 条件为：设备/方向不属于 dma_kmalloc_safe，且 size 未按 dma_get_cache_alignment() 对齐。

具体适用性：
- DMA_TO_DEVICE 被 dma_kmalloc_safe() 明确视为 safe；因此 STMMAC 普通 TX skb payload 不命中新增 kmalloc bounce 条件。
- RX DMA_FROM_DEVICE 对 non-coherent device 可能进入对齐检查；但 Panther STMMAC RX 使用 page_pool pages，普通 MTU 默认 buffer size 为 DEFAULT_BUFSIZE=1536 bytes（或更大的 2/4/8/16KiB buffer size），均为常见 cache-line alignment 的整数倍。page_pool create flags 为 PP_FLAG_DMA_MAP | PP_FLAG_DMA_SYNC_DEV，四版本相同。
- 目前没有证据显示 Panther RX page_pool buffer size 未对齐或触发 SWIOTLB bounce；不能把该新条件直接认定为 RX drop 根因。

### 4.3 direct DMA map/unmap helper 差异

kernel/dma/direct.h 四版本对照：

- 6.1.65/6.1.116/实际 6.1.174 c2f148d 的 dma_direct_map_page() 主体一致：DMA capability 检查、必要时 SWIOTLB map、non-coherent 且未 SKIP_CPU_SYNC 时执行 arch_sync_dma_for_device()。
- 6.12 在 dma_capable() 检查之外新增 dma_kmalloc_needs_bounce(dev,size,dir) 条件；其适用性按 §4.2 限定。
- 6.1 三版本 dma_direct_sync_single_for_device()/cpu() 与 6.12 的 arch_sync 调用条件一致；6.12 调整为直接调用 SWIOTLB sync helper，helper 内部处理是否为 bounce buffer。
- 6.1 三版本 dma_direct_unmap_page() 在 is_swiotlb_buffer() 时才调用 swiotlb_tbl_unmap_single()；6.12 改为无条件调用该 helper。当前没有证据表明 Panther GMAC1 普通 DMA mapping 使用 SWIOTLB bounce；此变化不能外推为普通 DMA unmap 错误。

## 5. DMA mask / address width 与运行时证据

四版本 STMMAC 的 DMA mask 软件逻辑已在 D3-3 对照：优先使用 plat->host_dma_width，否则采用硬件 feature register 解码的 dma_cap.addr64，再调用 dma_set_mask_and_coherent()；失败回退 32-bit mask。EAME 根据硬件 capability 和架构 DMA address type 条件设置。

已存在的运行时证据：
- 6.1.116 正常启动日志报告 Using 32/32 bits DMA host/device width。
- 6.12.81 故障启动日志也报告 32/32 bits。
- 当前没有 6.1.65、实际 6.1.174 c2f148d 的同类历史日志，不将 32/32 外推到这两个版本。

因此 6.1.116 与 6.12.81 的运行时 DMA width 相同，降低了 6.12 单纯因切换 64-bit descriptor address mode 而故障的可能性；但不证明所有运行时 DMA mask、物理地址或缓存一致性状态完全相同。

## 6. Kconfig / 配置证据分级

| 配置/能力 | 6.1.65 | 6.1.116 | 6.1.174 | 6.12.81 |
|---|---|---|---|---|
| DMA_DIRECT_REMAP | ARM64 Kconfig select | select；真实 kernel.config 与模板 7677 项零差异 | ARM64 Kconfig select；历史最终 config 部分字段未知 | ARM64 Kconfig select；RK35xx 模板 y |
| DMA_NEED_SYNC | 该 6.1 Kconfig 不存在 | 不存在 | 不存在 | 模板 y；现场运行配置已确认 y |
| DMA_BOUNCE_UNALIGNED_KMALLOC | 该 6.1 Kconfig 不存在 | 不存在 | 不存在 | 模板 y；现场运行配置未单独核实 |
| DMA_OPS_HELPERS | 该 6.1 Kconfig 不存在 | 不存在 | 不存在 | 模板 y |
| IOMMU_DMA / ROCKCHIP_IOMMU | 模板启用 | 真实配置与 general 模板一致 | 历史最终配置未完整恢复 | 模板与现场关键配置启用 |
| GMAC1 dma-coherent / iommus | DTS 均未声明 | 未声明 | 未声明 | 未声明 |

配置模板不能冒充所有历史最终 config；6.1.174 部分最终 config 仍按方向二报告保留未知。

## 7. D3-6 结论

### 已验证
- 四版本 ARM64 普通 streaming DMA_TO_DEVICE clean 和 DMA_FROM_DEVICE invalidate 实现相同。
- 6.1.65/6.1.116/实际 6.1.174 c2f148d 的 coherent allocation prep 都是 clean+invalidate；只有 6.12 改为 clean。该差异不是两个故障版本共同点。
- 四版本 ARM64 均 select DMA_DIRECT_REMAP；GMAC1 DTS 没有 dma-coherent/iommus，按 non-coherent direct DMA path 分析。
- 6.12 新增 unaligned kmalloc bounce 条件，但 DMA_TO_DEVICE 明确 safe；普通 TX 不命中。RX page_pool buffer 常规大小对齐，暂无命中证据。
- CONFIG_DMA_NEED_SYNC=y 不表示 GMAC1 自动跳过 cache sync；当前 source path 仍有显式 arch sync。
- 全局 IOMMU 配置启用不能证明 GMAC1 经过 IOMMU。

### 未验证
- 6.12.81 运行配置中的 DMA_BOUNCE_UNALIGNED_KMALLOC 最终值未从现场输出单独核实（构建模板 y）。
- 没有历史 dma_map/unmap trace、DMA API debug、SWIOTLB bounce 计数或设备 coherency runtime state。
- 6.1.65 源码端点仍是高置信度候选；6.1.174 历史最终 config 有既有缺口。

**D3-6 状态：已完成（静态源码/Kconfig/DTS 范围）。** 未发现普通 DHCP IPv4 DMA_TO_DEVICE 路径缺少 cache clean 或错误走 GMAC IOMMU 的证据。6.12 的 unaligned kmalloc bounce 和 coherent prep 变化均有明确条件/设计理由，不构成当前普通 TX 根因结论。按顺序进入 D3-7 IRQ/NAPI/watchdog/recovery。

## 8. 精确源码链接与既有报告

- [6.1.65 ARM64 DMA mapping](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/arch/arm64/mm/dma-mapping.c)
- [6.1.116 ARM64 DMA mapping](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/mm/dma-mapping.c)
- [6.1.174-rk35xx ARM64 DMA mapping](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/arch/arm64/mm/dma-mapping.c)
- [6.12.81-rk35xx ARM64 DMA mapping](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/mm/dma-mapping.c)
- [6.1.65 kernel/dma/direct.h](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/kernel/dma/direct.h)
- [6.12.81 kernel/dma/direct.h](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/kernel/dma/direct.h)
- [6.12.81 DMA API config template](https://github.com/ophub/kernel/blob/f8925391bb2ba2634bb8ca55da39e1a2f4029ffe/kernel-config/release/rk35xx/config-6.12)
- 复用：PANTHER-X2-ARM64-DMA-COHERENCY-116-VS-61281-20261119.md
- 复用：PANTHER-X2-KERNEL-CONFIG-RUNTIME-VERIFICATION-20261119.md
- 复用：PANTHER-X2-KERNEL-CONFIG-PROVENANCE-AND-READONLY-CAPTURE-20261119.md
- 复用：PANTHER-X2-KERNEL-CONFIG-FULL-DIFF-AND-EXACT-RX-SOURCE-REVIEW-20261119.md