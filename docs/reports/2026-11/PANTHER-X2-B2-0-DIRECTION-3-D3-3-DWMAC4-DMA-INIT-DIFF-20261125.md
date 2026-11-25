# Panther X2 B2-0 方向三 D3-3：DWMAC4 DMA core 初始化四版本差异（2026-11-25）

## 1. 范围与来源校正

本项只审 DWMAC4 DMA core reset、DMA system-bus/AXI 初始化、channel 初始化、TX/RX channel base/PBL 写入，以及普通 DMA address-width enable 条件。已完成的普通 skb TX mapping、descriptor OWN/barrier/tail pointer、MAC TE/DMA ST/MTL TXQEN 结论不重复。

固定端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（原始 Actions source_hash 已验证）。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

**重要来源校正：** 2026-11-19 的部分 6.1.116→6.1.174 报告使用 unifreq/linux-6.1.y@3f06ed3e... 作为 upstream stable 6.1.174 对照；该端点不是 6.1.174-rk35xx 实际构建 source_hash c2f148d。旧报告关于 3f06ed3e 源码的结论仅对该 stable snapshot 成立，不能替代本项对实际故障构建源码 c2f148d 的判断。此前“6.1.174 仍保留 1500ms DMA reset 前延时”的结论不适用于 c2f148d。

## 2. 复用且不重做的既有结果

- PANTHER-X2-STMMAC-TX-DMA-MAPPING-DESCRIPTOR-OWNERSHIP-116-VS-174-20261119.md：普通 TX skb DMA mapping/unmapping、descriptor OWN/barrier、tail pointer 的 116 与 stable 174 对照已完成；本项不重复。
- PANTHER-X2-STABLE-116-174-MAC-DMA-MTL-TX-ENABLE-DIFF-20261119.md：MAC TE、DMA ST、tail pointer、MTL TX queue mode 逻辑已完成 116 与 stable 174 对照；本项不重复这些函数。
- PANTHER-X2-STABLE-116-174-STMMAC-TX-CORE-DIFF-20261119.md：DWMAC4 register address abstraction 在 stable 174 的 NULL fallback 适用性已做初步审计；本项仅补齐实际 c2f148d 与 6.12.81。
- PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md：6.1.116 的 JL2xx1 workaround commit 49b5f340... 同时增加了 stmmac_init_dma_engine() 中 1500ms delay；该 commit 的 diff 仅添加 delay 和 MDIO 四次写入，提交说明为“fix for jl2xx1 phy”，未说明 delay 的具体硬件时序依据。

## 3. DWMAC4 DMA reset：真实的版本差异

### 3.1 reset poll interval

文件：drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c

| 版本 | dwmac4_dma_reset() | 轮询间隔 | 超时上限 |
|---|---|---:|---:|
| 6.1.65 | 读 DMA_BUS_MODE，置 DMA_BUS_MODE_SFT_RESET，再 readl_poll_timeout 等待清零 | 10000 us | 1000000 us |
| 6.1.116 | 同上 | 10000 us | 1000000 us |
| 6.1.174-rk35xx c2f148d | 同样的 SW reset bit 与 polling 条件 | 500 us | 1000000 us |
| 6.12.81-rk35xx | 同 6.1.174 | 500 us | 1000000 us |

6.1.65/6.1.116 对应函数约第 15–25 行；6.1.174/6.12.81 约第 16–26 行。变化是 polling interval 从 10ms 缩短到 0.5ms，timeout 仍为 1s；没有证据表明 reset bit、寄存器或成功条件发生改变。

### 3.2 DMA reset 前 1500ms 延时

文件：drivers/net/ethernet/stmicro/stmmac/stmmac_main.c，stmmac_init_dma_engine()

| 版本 | reset 前等待 | reset 后顺序 |
|---|---|---|
| 6.1.65 | msleep(1500) | stmmac_reset → stmmac_dma_init → optional AXI → channel config → RX channel → TX channel |
| 6.1.116 | msleep(1500) | 相同 |
| 6.1.174-rk35xx c2f148d | **无 1500ms delay** | 其余上述调用顺序相同 |
| 6.12.81-rk35xx | **无 1500ms delay** | 其余上述调用顺序相同；atds 参数迁移到 dma_cfg 字段 |

精确位置：6.1.65 约第 2926 行、6.1.116 约第 2930 行；实际 c2f148d 约第 2977 行直接调用 stmmac_reset()，前面没有 msleep；6.12.81 约第 3049 行同样直接 reset。

1500ms delay 来自 unifreq/linux-6.1.y commit 49b5f340f346cc9a5b777499fce46150b691b70e，与四次 MDIO 写入在同一 commit 增加。该提交说明只写“stmmac fix for jl2xx1 phy”，没有说明 delay 对应哪一个具体时钟/复位时序条件。实际 6.1.174-rk35xx c2f148d 和 6.12.81 均不包含该 delay。

这是目前 D3-3 中最重要的真实差异：两条黄金基准在 DMA SW reset 前等待 1.5 秒，两条故障基准不等待。它可能影响 MAC/DMA/平台时钟及外部 PHY 状态稳定后再执行 DMA reset 的时序，但目前没有板级时钟 ready、reset 波形、DMA reset status 或启动日志可证明该 delay 原本解决什么条件。不能直接认定它就是故障根因，也不能将其恢复成补丁建议。

## 4. DWMAC4 DMA init / AXI / channel programming

### 4.1 DMA system bus mode

dwmac4_dma_init() 在四版本中都对 DMA_SYS_BUS_MODE 的既有值做 read-modify-write，并根据 dma_cfg 中 fixed_burst、mixed_burst、aal、eame 条件设置 FB/MB/AAL/EAME；随后对 DMA_BUS_MODE 设置 multi-MSI interrupt mode（若启用）及 DCHE。6.1.65/6.1.116/6.1.174 的函数签名带 atds 参数，但函数体不读取它；6.12 移除未使用的 atds 参数。该签名变化本身没有改变 DWMAC4 DMA_SYS_BUS_MODE 写入逻辑。

### 4.2 AXI bus mode

dwmac4_dma_axi() 四版本函数体逐行一致：根据 axi_lpi_en、axi_xit_frm、axi_wr_osr_lmt、axi_rd_osr_lmt、axi_blen[] 设置 DMA_SYS_BUS_MODE 中 LPI、OSR、BLEN 字段。没有发现 6.1.65→6.1.116→实际 6.1.174 c2f148d→6.12.81 的算法变化。

Panther RK356x SoC DTSI 定义 snps,axi-config，blen=<0 0 0 0 16 8 4>、rd_osr_lmt=8、wr_osr_lmt=4，并设置 snps,mixed-burst。实际 platform data 是否完整按此填充取决于 Rockchip glue 的解析和传递；glue 内部不在本项展开，留给后续原定专题。

### 4.3 channel control / PBL / base address

| 函数 | 6.1.65/6.1.116 | 6.1.174 c2f148d/6.12.81 | 行为判断 |
|---|---|---|---|
| dwmac4_dma_init_channel() | 固定 offset | 增加 priv->plat->dwmac4_addrs 参数 | 仅 register address abstraction；PBLx8 与默认 IRQ mask 算法相同 |
| dwmac4_dma_init_tx_chan() | 固定 offset | 使用 dwmac4_addrs helper | txpbl fallback、OSP、可选 upper address、lower base address 写入顺序相同 |
| dwmac4_dma_init_rx_chan() | 固定 offset | 使用 dwmac4_addrs helper | rxpbl fallback、可选 upper address、lower base address 写入顺序相同 |

6.1.174/6.12 的 Rockchip dwmac-rk.c 未给 plat->dwmac4_addrs 赋值；平台数据使用 devm_kzalloc 初始化，新增 pointer 未赋值时为 NULL。既有 dwmac4.h 地址 helper 对 NULL 使用默认 DWMAC4 register offsets。因此 Panther 不会因为新增 register map abstraction 自动切换到自定义寄存器布局。此项与 2026-11-19 stable 报告的结论一致，但本轮将实际 c2f148d 与 6.12.81 端点纳入核对。

## 5. DMA address width / EAME 条件

四版本 stmmac_main.c 的 DMA mask/address-width 主体逻辑一致：

1. 先从硬件 feature/capability 取得 DMA address width 信息；
2. 若报告可寻址宽度大于 32 bit，则尝试按硬件报告宽度设置 DMA mask/coherent mask；
3. 若 CONFIG_ARCH_DMA_ADDR_T_64BIT 启用，则设置 dma_cfg->eame=true；
4. DWMAC4 DMA init 根据 eame 设置 DMA_SYS_BUS_MODE_EAME；TX/RX channel init 仅在 CONFIG_ARCH_DMA_ADDR_T_64BIT 且 eame 为真时写入 descriptor base address high 32 bits。

四版本该逻辑未见功能差异。ARM64 架构满足 64-bit DMA address type 的编译条件，但硬件 feature register 实际报告的 addr64/host_dma_width 及运行时 dma_set_mask_and_coherent 成功结果，不能仅由 SoC 型号或 CONFIG_ARCH_DMA_ADDR_T_64BIT 推定；当前没有历史硬件 feature dump 或运行时 DMA mask 记录。因此 EAME 是否实际置位、是否写 high address registers 保持未验证。

## 6. 当前 D3-3 初步结论

### 已验证
- 6.1.65/6.1.116 的 DMA reset poll interval 为 10ms，实际 6.1.174 c2f148d/6.12.81 为 0.5ms；reset bit、poll condition、1s timeout 不变。
- 6.1.65/6.1.116 在 stmmac_init_dma_engine() reset 前有 1500ms sleep；实际 6.1.174 c2f148d/6.12.81 没有。
- 1500ms delay 与四次 MDIO writes 同属 49b5f340... 提交；commit message 指向 JL2xx1 PHY fix，但没有公开说明 delay 的具体时序原因。
- DWMAC4 DMA system bus mode、AXI、channel control/PBL、TX/RX channel base programming 算法四版本保持一致；6.1.174/6.12 register address abstraction 对 Panther 走 NULL default offsets。
- DMA address width/EAME 的软件判断逻辑四版本一致；实际硬件能力位与运行时 DMA mask 状态未知。

### 未验证 / 继续工作
- 尚未完成 Panther platform data 的 DMA config/PBL/AXI/queue-count 运行时值证据；不能把 DTS 声明直接当作最终寄存器值。
- 尚未取得 DMA reset 的历史状态寄存器值、reset 完成时间或平台时钟 ready 证据。
- 尚未核对 DMA init 1500ms delay 与 Rockchip glue clock/reset/power 顺序的跨层关系；该项留在后续既定平台专题，不在此扩展。
- 尚未完成 DWMAC4 DMA feature register addr64/host_dma_width 与 dma_set_mask 的运行时闭环。

**D3-3 状态：进行中。** 已完成 DWMAC4 DMA core 主要初始化函数四版本初审，并发现两个黄金/故障版本分界明显的时序差异（reset 前 1500ms delay 缺失、reset polling interval 缩短）。当前先保留为高优先级候选，不宣布根因；下一步只补齐 DMA feature/address-width 与 PBL/AXI/queue platform data 的静态来源证据。D3-4/D3-5 descriptor 生命周期尚未开始。

## 7. 精确源码链接

- [6.1.65 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.65 dwmac4_lib.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [6.1.116 dwmac4_lib.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [6.1.174-rk35xx dwmac4_lib.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [6.12.81-rk35xx dwmac4_lib.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [JL2xx1 delay + MDIO workaround commit 49b5f340](https://github.com/unifreq/linux-6.1.y/commit/49b5f340f346cc9a5b777499fce46150b691b70e)