# Linux stable 6.1.116 → 6.1.174：Rockchip GMAC glue 与队列初始化差分（2026-11-19）

## 1. 本轮范围

本轮从仓库既有报告出发，先排除重复工作，再对照 stable upstream `v6.1.116` 与 `v6.1.174`：

- `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`
- `drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c`
- `drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c`
- `include/linux/stmmac.h`

只读取仓库和源码。没有连接设备、发帧、抓包、读取寄存器或修改配置。

## 2. 先排除已完成工作

仓库既有报告已覆盖以下内容，本轮不重复作为新发现：

- Panther 单 RX / 单 TX queue、普通 queue 0 路径及 MTL 默认配置（主审计报告第 33 节）。
- `stmmac_mtl_configuration()`、`stmmac_rx_queue_dma_chan_map()` 的 queue 初始化逻辑。
- 6.1.116 与 6.12.81 实际构建间 Rockchip 时钟启动等待时间由约 5 ms 缩短为 100–200 µs，以及 RK3568 RGMII GRF 写入顺序变化（主审计报告第 19、20 节）。
- 6.1.116 与 6.12.81 间的 PHY attach、phylink、RGMII speed callback、TX queue / DMA channel 初始化。

特别注意：第 19、20 节中的 5 ms → 100–200 µs 和 GRF 写入顺序变化，比较对象是 **6.1.116 generic source 与 6.12.81 RK35xx BSP source**，不能错误归入本轮 **6.1.116 → 6.1.174 stable upstream** 的差异。

## 3. Rockchip glue 的唯一可见语义变化：GMAC clock disable 顺序

文件：`drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`，函数 `gmac_clk_enable()`。

6.1.116 在 disable 分支的顺序：
1. `clk_bulk_disable_unprepare()`
2. `clk_disable_unprepare(clk_phy)`
3. 如果存在 `set_clock_selection` callback，则调用 callback 关闭 clock selection
4. 清除 `clk_enabled`

6.1.174 改为：
1. 如果存在 `set_clock_selection` callback，先调用 callback 关闭 clock selection
2. `clk_bulk_disable_unprepare()`
3. `clk_disable_unprepare(clk_phy)`
4. 清除 `clk_enabled`

这是一个真实的顺序变化：对于注册了 `set_clock_selection` 的 SoC，6.1.174 在关时钟之前先切换 clock selection，避免时钟已关闭后才访问相关 GRF/clock-selection 控制路径。

### Panther 是否命中

Panther 运行时 FDT 的 MAC compatible 为：
- `rockchip,rk3568-gmac`
- `snps,dwmac-4.20a`

stable 6.1.116 和 6.1.174 的 `rk3568_ops` 均只注册：
- `set_to_rgmii`
- `set_to_rmii`
- `set_rgmii_speed`
- `set_rmii_speed`

两版 `rk3568_ops` 均没有注册 `set_clock_selection`。该 callback 只在其他 SoC ops（例如 RK3588）中注册。

因此 Panther 走 `rk3568_ops` 时，新增的 disable 顺序分支不会执行 callback；其余 clock disable 操作的顺序与 6.1.116 相同。**这项 116→174 stable 改动不适用于 Panther，不能解释 Panther TX 故障。**

## 4. RK3568 RGMII / speed callback：116 与 174 完全一致

逐函数比较结果：

- `rk3568_set_to_rgmii()`：完全一致。仍先按 TX/RX delay 写 GMAC1 CON0，再写 CON1 的 RGMII interface select 和 delay enable。
- `rk3568_set_gmac_speed()`：完全一致。10/100/1000 Mbps 对应 2.5/25/125 MHz。
- `rk_fix_speed()`：完全一致。按 RGMII/RMII interface 选择对应 speed callback。
- `rk_gmac_powerup()`：完全一致。GMAC clock enable、接口模式配置、PHY regulator、runtime PM 和 integrated PHY powerup 的调用顺序没有变化。

因此，6.1.116→6.1.174 stable upstream 没有改变 Panther RK3568 的 RGMII GRF 配置值、写入顺序或 speed-clock rate 选择逻辑。

## 5. MTL queue parsing 与 DMA channel 初始化：关键函数未变化

逐函数比较：

- `stmmac_mtl_setup()`：完全一致。未提供 MTL phandle 时，RX/TX queue 数量均默认 1；queue 0 默认 DCB。TX queue 的数量、scheduler、priority 和 mode 解析逻辑没有变化。
- `stmmac_mtl_configuration()`：完全一致。
- `stmmac_rx_queue_dma_chan_map()`：完全一致；该函数配置 RX MTL queue 到 DMA channel 的映射，不是 TX queue 到 TX DMA channel 的映射。
- `stmmac_init_dma_engine()`：完全一致。DMA reset、DMA CSR channel init、RX channel init、TX channel init、TX tail pointer 初始化的循环范围和顺序相同。
- `stmmac_start_all_dma()`：完全一致。先启动 RX channel，再启动 TX channel。
- `stmmac_set_tx_queue_weight()`：完全一致。

这与仓库此前确认的 Panther 单队列 queue 0 / DMA channel 0 基线一致。本轮没有发现 6.1.174 把 Panther TX 从 channel 0 映射到其他 channel，或改变 TX channel 初始化/启动顺序。

## 6. stmmac_platform.c 的重构：MDIO 管理变化，不是 TX queue 变化

6.1.174 将旧的 `stmmac_dt_phy()` 解析结构拆分为：
- `stmmac_of_get_mdio()`
- `stmmac_mdio_setup()`

同时增加 bus-id fallback 管理和错误路径上的 OF node 引用释放。

本轮核对到的 MTL queue parser `stmmac_mtl_setup()` 在两版完全一致。平台数据仍通过 `devm_kzalloc()` 初始化，MTL queue 的默认值和 Panther 的单队列路径没有因这次 MDIO 重构而改变。

该变化可能影响 MDIO node discovery / lifecycle，属于 PHY 管理路径；但 Panther 有 firmware `phy-handle`、MDIO 子节点和已验证的 RTL8211F link-up。现有源码证据没有把这次重构与普通 TX 帧无法外部接收建立因果关系，因此不列为 TX 根因候选。

## 7. 本轮结论

### 已确认
- 6.1.116→6.1.174 的 Rockchip GMAC glue 可见语义变化，是 clock disable 时 callback 与 clock disable 的先后顺序调整。
- Panther 的 RK3568 ops 没有注册该 callback，因此该变化对 Panther 不生效。
- RK3568 RGMII delay GRF 写入、speed clock 速率映射、power-up 顺序均完全一致。
- MTL queue parser、MTL configuration、RX queue-to-DMA mapping、DMA engine init、TX channel init/start 的关键函数完全一致。
- stmmac_platform 的主要结构性重构集中在 MDIO node 管理，不改变 MTL queue parser。

### 尚未证明
- upstream stable tag 差异不等同于 6.1.174 Panther 实机镜像的全部 BSP/ophub 补丁差异。
- 上述源码一致性不能证明寄存器写入在实机成功，也不能证明帧已越过 MAC/RGMII 边界。
- 本轮没有获得 DHCP Discover 从 Panther 物理网口输出的证据。

### 阶段判断
在 6.1.116→6.1.174 stable upstream 范围内，已经检查的：
1. skb → descriptor TX 提交与回收；
2. MAC TE、DMA ST、TX tail pointer、MTL TXQEN；
3. Rockchip RK3568 GMAC glue；
4. 单队列 / DMA channel 初始化与启动；

均未发现能解释 Panther TX 外发失败的直接回归。

这只是对已检查代码范围的排除结论，不等于整个内核没有回归，也不等于证明帧已经出网口。

## 8. 下一项静态研究

不再重复 stable upstream 的上述 STMMAC / RK3568 函数。下一项应转向 **6.1.116 与 6.1.174 实际 Panther BSP 构建来源之间的额外补丁差异**，优先核对：
- 6.1.174 实际构建所用的 kernel source commit；
- ophub/Rockchip 相对于 stable upstream 的补丁或 cherry-pick；
- Panther GMAC 节点及其 include/fixup 产物是否在两个构建中存在未归档的变化。

继续只做仓库和静态源码研究，不执行任何实机测试。
