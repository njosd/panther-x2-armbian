# Panther X2：ARM64 DMA cache/coherency 6.1.116 vs 6.12.81 源码核查（2026-11-19）

## 1. 比较基线与既有证据

- 6.1.116 源码：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.12 源码：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。
- 已有 TX 物理边界报告确认：GMAC1 DTS 未声明 `iommus`；`CONFIG_ROCKCHIP_IOMMU=y` 只是全局驱动启用，不代表 GMAC1 绑定 IOMMU。6.12 构建配置记录 `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y`，但不改变上述 GMAC1 DT 绑定事实。
- STMMAC TX descriptor ring 由 `dma_alloc_coherent()` 分配；普通 skb payload 由 `dma_map_single(..., DMA_TO_DEVICE)` 映射。

## 2. 普通 skb payload 的 DMA cache sync：关键操作一致

两版 `arch/arm64/mm/dma-mapping.c` 中：
- `arch_sync_dma_for_device()` 都执行 `dcache_clean_poc(start, start + size)`。
- `arch_sync_dma_for_cpu()` 都对 `DMA_TO_DEVICE` 直接 return；其他方向执行 `dcache_inval_poc()`。

因此，普通 skb 的 `DMA_TO_DEVICE` map/sync 路径所依赖的 ARM64 cache clean，在 6.1.116 和 6.12.81 之间没有变化。当前不能将普通 TX payload 未被 clean 到 PoC 归因于这处架构源码变化。

## 3. 找到一处真实变化：coherent allocation 的预处理

`arch_dma_prep_coherent()` 在两版不同：
- 6.1.116：`dcache_clean_inval_poc(start, start + size)`，并保留一段说明，解释 clean+invalidate 是为了减少某些 vendor 对 DMA API 的特殊滥用场景风险；
- 6.12.81：改为 `dcache_clean_poc(start, start + size)`。

该函数被 `kernel/dma/direct.c` 的 coherent allocation 路径调用。STMMAC TX/RX descriptor ring 使用 `dma_alloc_coherent()`，所以这处变化的作用对象与 descriptor ring 内存分配有关，而不是普通 skb payload 的 `dma_map_single(DMA_TO_DEVICE)` 同步。

## 4. 这处变化是否能解释故障？目前只能列为条件性候选

不能直接断言它是根因，原因如下：
1. `dma_alloc_coherent()` 的具体实现可能经过 direct remap、atomic/global pool、架构专用 allocator 或其他分支；`arch_dma_prep_coherent()` 是否实际命中，取决于该构建的 DMA 相关 Kconfig 与运行时分配路径。
2. 当前已归档的 6.12.81 配置片段没有记录 `CONFIG_DMA_DIRECT_REMAP`、`CONFIG_DMA_GLOBAL_POOL`、`CONFIG_ARCH_HAS_DMA_ALLOC` 等足以确定具体 coherent allocation 分支的配置。
3. clean+invalidate 改为 clean 是 coherent allocation 初始化阶段的 cache 维护差异；它本身不证明 DMA descriptor ring 在运行时出现 stale cache line，也不证明 descriptor 内容错误。
4. 两版 `arch_sync_dma_for_device()` 的普通 TX payload clean 保持一致；不能把 coherent allocation 预处理变化扩大解释为所有 TX 数据都没有 cache clean。

所以：这是真实且值得保留的 6.1→6.12 ARM64 DMA 差异，优先级高于已排除的 MDIO/普通 skb mapping 差异；但目前证据不足以定根因。

## 5. IOMMU 方向的结论

6.1.116 的 ARM64 `arch_setup_dma_ops()` 接收 `iommu` 参数，并在非空时调用 `iommu_setup_dma_ops()`；6.12.81 的接口改为 `arch_setup_dma_ops(dev, coherent)`，IOMMU 配置流程在 `of_dma_configure_id()` 中仍执行 `of_iommu_configure()`。

但 Panther GMAC1 的设备树没有 `iommus` 属性，因此本次 API 签名变化不能单凭源码差异解释 GMAC1 DMA mapping 回归。不要把 SoC 其他单元（例如 VPU）的 IOMMU domain 日志误认为 GMAC1 使用 IOMMU。

## 6. 当前结论矩阵

| 项目 | 116 vs 6.12 | 判断 |
|---|---|---|
| 普通 skb `DMA_TO_DEVICE` cache clean | 相同 | 已排除该函数变化导致的回归 |
| `DMA_TO_DEVICE` sync-for-CPU | 两版均直接 return | 已排除 |
| coherent allocation prep | clean+invalidate → clean | 真实差异，条件性候选 |
| GMAC1 IOMMU attachment | 两版 DTS 均无 `iommus` | 低优先级，不应误判为 IOMMU 故障 |
| descriptor ring coherent allocation 实际分支 | 尚无对应构建 Kconfig/运行时 allocator 证据 | 未验证 |

## 7. 下一步（限定范围，不重跑设备测试）

只做两件事：
1. 从 6.12.81 标准版和 Flippy 版的真实 `.config`/headers 包中确认 DMA allocation 相关 Kconfig（特别是 `CONFIG_DMA_DIRECT_REMAP`、`CONFIG_DMA_GLOBAL_POOL`、`CONFIG_ARCH_HAS_DMA_ALLOC`、`CONFIG_DMA_API_DEBUG`）；不能用同一仓库其他版本 config 代替。
2. 根据实际配置，静态追踪 `dma_alloc_coherent()` 对 Panther GMAC descriptor ring 最终命中的 allocator，确认 `arch_dma_prep_coherent()` 是否执行、descriptor CPU mapping 是 noncached 还是其他属性。

若 coherent allocation 预处理实际不命中，或该内存最终属性与预期一致，则关闭此候选；不要为了验证而修改驱动或做未经授权的现场寄存器读取。之后将焦点回到实际 6.12.81 发布二进制与源码/build provenance，以及现有报告尚未确认的 descriptor/payload 实际内容边界。

本轮未进行实机测试、未访问设备、未读取或写入 MMIO、未修改驱动/DTS/系统配置。

## 8. 源码与关联报告

- 6.1.116 ARM64 DMA mapping：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/mm/dma-mapping.c
- 6.12.81 ARM64 DMA mapping：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/mm/dma-mapping.c
- 6.1.116 direct DMA allocator：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/kernel/dma/direct.c
- 6.12.81 direct DMA allocator：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/kernel/dma/direct.c
- 既有 TX physical boundary / DMA report：`PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`

## 9. 后续补充：DMA_DIRECT_REMAP 路径已由架构 Kconfig 确认

继续检查两个源码端点的 `arch/arm64/Kconfig`：两版均由 ARM64 架构 `select DMA_DIRECT_REMAP`。Panther GMAC1 的 SoC DTS 节点没有 `dma-coherent`，故按 OF DMA coherency 规则作为 non-coherent device 配置；GMAC1 也没有 `iommus`，所以不走 Rockchip IOMMU DMA mapping。

结合 `kernel/dma/direct.c`：
1. STMMAC 通过 `dma_alloc_coherent()` 分配 TX/RX descriptor ring；
2. 对 non-coherent device，ARM64 的 `DMA_DIRECT_REMAP=y` 使 direct allocator 选择 remap coherent allocation 路径（普通 GFP_KERNEL 分配不属于 atomic pool 分支）；
3. 该 remap 路径明确调用 `arch_dma_prep_coherent(page, size)`，随后建立 coherent/non-cacheable remap。

因此，前文所列 `arch_dma_prep_coherent()` clean+invalidate → clean 的差异，不再只是一个“可能执行”的函数差异：按两版架构 Kconfig、GMAC1 DTS 和 STMMAC descriptor allocation 调用链，它确实位于该 descriptor ring 分配路径上。此处是源码/Kconfig 推导，尚未取得运行中函数调用 trace。

## 10. 对该差异的技术定性：真实变化，但不是当前优先根因

ARM64 上游补丁说明（Will Deacon，2022-08-23）指出，`arch_dma_prep_coherent()` 的目的，是把此前通过 cacheable mapping 产生的 dirty cache lines clean 到 PoC，使 non-coherent device 能看到内存内容。补丁解释认为 clean 已满足 DMA API；额外 invalidate 在仍存在 cacheable linear-map alias 的情况下作用有限，因为 CPU 可能在 invalidate 后再次 speculative fetch 该 cache line。

因此：
- `dcache_clean_inval_poc()` 和 `dcache_clean_poc()` 确实不同：前者 clean+invalidate，后者只 clean；
- ARM64 上游设计明确认为 coherent allocation preparation 只需 clean 到 PoC，invalidate 并非必要条件；
- 该差异本身不构成 6.12 DMA descriptor 数据不可见的证据；不能仅凭“6.1 正常、6.12 异常”就把它判为回归根因。

结论：将此项从“待验证的较高优先级候选”下调为“已确认调用路径上的实现差异，但按 ARM64 DMA 设计理由不太可能单独导致故障”。不建议为此单独修改内核或恢复 invalidate。只有后续获得 descriptor stale/alias 访问的直接证据，才重新打开。

## 11. 本项结案与下一步

ARM64 DMA coherency 源码路径本身暂时结案：普通 skb payload DMA_TO_DEVICE clean 相同；coherent descriptor ring prep 的差异真实但有上游明确理由，暂不足以解释 TX 失败。下一步应回到已有报告中尚未闭环的证据边界：6.12.81 当前启动周期的 MMC good/bad TX 计数与实际 MAC 发送结果、以及实际发布二进制与公开候选源码/补丁的精确对应。不要再重复 DMA mapping、descriptor OWN、tail pointer、MDIO、clock 或 PHY reset 检查。

### 参考资料

- ARM64 DMA patch：Drop cache invalidation from arch_dma_prep_coherent()（2022-08-23）：https://lists.infradead.org/pipermail/linux-arm-kernel/2022-August/768719.html
- ARM64 patch review discussion（2022-08-24）：https://lists.infradead.org/pipermail/linux-arm-kernel/2022-August/768952.html
- 当前 Linux ARM64 cache operation 定义：https://github.com/torvalds/linux/blob/master/arch/arm64/mm/cache.S
