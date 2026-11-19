# Linux stable 6.1.116 → 6.1.174：MAC / DMA / MTL TX 使能路径差分（2026-11-19）

## 1. 范围与操作边界

本轮只对照 Greg Kroah-Hartman stable Linux `v6.1.116` 与 `v6.1.174` 的 STMMAC / DWMAC4 源码，沿 TX 提交之后的硬件启动路径检查：

- MAC TX enable（GMAC_CONFIG.TE）
- DMA TX channel start/stop（DMA_CONTROL_ST）
- TX descriptor tail pointer
- MTL TX queue operation mode（TSF / TTC / TXQEN / TQS）
- phylink link-up 中新增的 SerDes 回调

只读取 GitHub 源码。没有连接 Panther 设备，没有发帧，没有抓包，没有读取任何实机寄存器，没有修改配置。

## 2. MAC TE：使能/清除逻辑完全相同

文件：`drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c`

两版 `stmmac_dwmac4_set_mac()` 完全一致：

- enable=true：设置 `GMAC_CONFIG_RE | GMAC_CONFIG_TE`
- enable=false：清除 `GMAC_CONFIG_TE | GMAC_CONFIG_RE`
- 仅当新旧值不同时才写寄存器

因此，stable 116→174 没有改变 MAC TX enable 的位操作语义。

## 3. DMA TX channel start/stop：操作相同，寄存器地址经新抽象层

文件：`drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c`

两版 `dwmac4_dma_start_tx()` 的硬件操作顺序相同：

1. 读取 DMA TX Control；
2. 设置 `DMA_CONTROL_ST`；
3. 写回 DMA TX Control；
4. 读取 GMAC_CONFIG；
5. 设置 `GMAC_CONFIG_TE`；
6. 写回 GMAC_CONFIG。

`dwmac4_dma_stop_tx()` 两版均只清除 `DMA_CONTROL_ST` 并写回。

差异是 6.1.174 为函数增加 `struct stmmac_priv *priv` 参数，通过 `priv->plat->dwmac4_addrs` 计算 DMA channel register offset。Panther 的 Rockchip glue 未设置该字段，平台数据由 `devm_kzalloc()` 零初始化，故使用 NULL/default register layout。对 Panther 而言，这应落回原来的 DMA channel 偏移。

## 4. TX tail pointer：写入目标相同，地址抽象改变

两版 `dwmac4_set_tx_tail_ptr()` 都把 tail pointer 写入 DMA channel TX End Address 寄存器。6.1.174 仅增加 `priv` 参数并经 `dwmac4_addrs` 计算地址；Panther 仍走默认偏移。

这与此前已经审查的 `stmmac_xmit()` 描述符刷新路径一致：当前未发现 116→174 对 Panther tail pointer 的目标寄存器或写入语义发生变化。

## 5. MTL TX queue operation mode：算法相同

文件：`drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c`

两版 `dwmac4_dma_tx_chan_op_mode()` 的配置算法相同：

- Store-and-Forward 模式设置 `MTL_OP_MODE_TSF`；否则按阈值配置 TTC；
- 清除 `MTL_OP_MODE_TXQEN_MASK`；
- 非 AVB queue 设置 `MTL_OP_MODE_TXQEN`，AVB queue 设置 `MTL_OP_MODE_TXQEN_AV`；
- 清除 TQS 字段并按 `fifosz / 256 - 1` 写入每队列 FIFO 大小；
- 最后写回 MTL TX Queue Operation Mode。

6.1.174 仅在函数中引入 `priv->plat->dwmac4_addrs` 并通过地址 helper 访问寄存器。算法、字段和值的计算没有变化。

## 6. phylink link-up 新增 SerDes power-up 回调：Panther 不适用

文件：`drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`

6.1.174 在 `stmmac_mac_link_up()` 的开头新增：

- 只有 `priv->plat->serdes_up_after_phy_linkup` 为 true；
- 且 `priv->plat->serdes_powerup` 回调非 NULL；
- 才调用 SerDes power-up。

该功能面向需要在 PHY link-up 后再启动 SerDes 的平台。

Panther 适用性核对：
- 6.1.174 `include/linux/stmmac.h` 将 `serdes_powerup` 和 `serdes_up_after_phy_linkup` 放在平台数据结构中；
- `dwmac-rk.c` 没有为 Rockchip Panther 设置该回调或标志；
- `stmmac_of_get_plat_data()` 分配平台数据时使用 `devm_kzalloc()`，未赋值字段为零/NULL；
- Panther 使用 RGMII + 外接 RTL8211F，而非需要该回调的 SerDes 平台。

因此该新增条件对 Panther 应为 false，不能解释当前 TX 故障。这里的结论是基于 stable 6.1.174 Rockchip glue 与平台数据初始化的源码判断，不是实机运行时字段读数。

## 7. 本轮结论

### 已确认（源码差分）
- MAC TE enable/disable 操作相同。
- DMA TX channel ST start/stop 操作相同。
- TX tail pointer 写入相同类型的 DMA channel TX End Address 寄存器。
- MTL TX queue mode 的 TSF/TTC/TXQEN/TQS 配置算法相同。
- 上述 DWMAC4 DMA/MTL 访问在 6.1.174 经新增可配置地址抽象，但 Panther 没有自定义映射，按源码应走默认寄存器布局。
- 6.1.174 新增 SerDes link-up power-up 条件回调；Panther Rockchip glue 未配置它，按平台数据零初始化应不触发。

### 尚未证明
- 尚未对 6.1.174 实际 Panther BSP 完整补丁集逐文件复核，不能把 upstream tag 差分等同于当时实机镜像的全部差异。
- 源码路径相同不能证明实机寄存器写入成功，也不能证明 MAC 输出引脚出现了 RGMII TX 信号。
- 本轮没有获得帧越过 MAC/RGMII 边界的证据。

### 对故障定位的意义
当前已连续检查两层：
1. Linux skb → DMA descriptor 提交及 reclaim；
2. MAC TE、DMA ST、tail pointer、MTL TX queue operation mode。

在 stable 116→174 upstream 代码中，这两层均未发现针对 Panther 的明显发送行为回归。当前不应把问题归因于 `stmmac_xmit()` 或上述硬件启动函数的 upstream stable 改动。

这并不证明代码完全无误，也不证明帧已出网口；它只排除了本轮覆盖范围内可见的主要逻辑差异。

## 8. 下一项静态研究

下一步不再重复上述函数。优先审查 6.1.116→6.1.174 的：
- TX queue / DMA channel 数量及映射初始化；
- platform data 的默认值与 DT 解析；
- Rockchip glue 在 probe、power-up、fix_mac_speed 中对 GRF、时钟、RGMII mode 的写入差异。

目标是确认是否存在“TX 被分配到错误 DMA channel / MTL queue”或“link-up 时平台时钟/接口配置被改变”的软件因果链。继续只做源码和仓库证据审查，不做实机测试。
