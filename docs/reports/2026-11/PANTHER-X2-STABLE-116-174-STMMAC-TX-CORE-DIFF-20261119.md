# Linux stable 6.1.116 → 6.1.174：STMMAC TX 核心路径定点差分（2026-11-19）

## 1. 本轮范围与边界

本轮按项目当前有效版本边界，直接比较 Greg Kroah-Hartman stable Linux 仓库的 `v6.1.116` 与 `v6.1.174`，聚焦 Panther X2 使用的 Synopsys DWMAC4 / STMMAC 普通 skb TX 路径。

本轮只读取 GitHub 源码；没有连接设备，没有发送测试帧，没有抓包，没有读取寄存器，没有修改任何系统配置。

比较文件：
- `drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
- `drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_core.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4.h`
- `include/linux/stmmac.h`
- `drivers/net/phy/realtek.c`
- `include/linux/dma-mapping.h`
- `kernel/dma/mapping.c`

注意：这只是 stable upstream 两个 tag 的差分，不等于已经证明 6.1.174 Panther BSP 镜像的完整补丁集，也不等于 6.12.81 实际运行二进制的唯一源码映射。

## 2. 普通 TX 提交路径：未发现实质性流程变化

对 `stmmac_xmit()` 逐段对照，以下关键操作顺序在 6.1.116 与 6.1.174 保持一致：

1. 根据 skb queue mapping 选择 TX queue；
2. 检查 ring descriptor 可用量；
3. 处理 VLAN、jumbo、scatter-gather；
4. 对 skb head/fragments 做 DMA mapping；
5. 写入 descriptor buffer address / length / segment flags；
6. 通过 `stmmac_prepare_tx_desc()` 准备描述符；
7. 更新 `cur_tx`；
8. 设置首描述符 OWN；
9. `netdev_tx_sent_queue()`；
10. `stmmac_enable_dma_transmission()`；
11. `stmmac_flush_tx_descriptors()`；
12. 启动 TX clean timer，返回 `NETDEV_TX_OK`。

两版都保留相同的 DMA mapping 方向 `DMA_TO_DEVICE`、相同的描述符准备和 OWN 交接位置，以及相同的 DMA transmission enable / descriptor flush 调用顺序。

可见差异主要是统计数据更新方式：
- 6.1.116 在提交路径直接更新部分 netdev / driver counters；
- 6.1.174 引入每队列 `u64_stats_sync`，把 TX bytes、IC bit 等统计放入同步区间；
- DMA map error 的 dropped counter 从 `dev->stats.tx_dropped` 改为驱动扩展统计字段。

这些变化影响统计记录与并发读取，不改变上述普通 TX descriptor 提交顺序。

## 3. TX completion / descriptor reclaim：核心判断保持一致

对 `stmmac_tx_clean()` 与 `stmmac_tx_err()` 对照：

- 两版均先读取 descriptor status；
- 均以 `tx_dma_own` 判断 DMA 是否仍拥有描述符；
- 均在确认 OWN 已清除后执行 `dma_rmb()`；
- 均根据 `tx_not_ls` / `tx_err` 判断最后分段及发送错误；
- 均执行 DMA unmap、descriptor cleanup/release；
- TX error recovery 均停止 TX DMA、释放/清理描述符、重置 TX queue、重新初始化并启动 TX DMA。

6.1.174 的主要差异仍是把 TX packet/error/clean counters 聚合后放入 per-queue 同步统计区，而不是改变 descriptor ownership 或 DMA reclaim 的判断条件。

因此，当前源码差分不支持“6.1.174 普通 TX 因 clean/reclaim 逻辑改变而被提前释放或错误地停止”的解释。

## 4. DWMAC4 DMA register address abstraction：新变化，但 Panther 走默认偏移回退

这是本轮发现的主要结构性差异：

- 6.1.116 的 DWMAC4 DMA/MTL 代码直接使用固定寄存器偏移宏。
- 6.1.174 引入 `struct dwmac4_addrs` 和可配置寄存器基址/步长，使不同 DWMAC4 集成实现可以覆盖 DMA channel 与 MTL queue register layout。
- 6.1.174 的 `dwmac4_dma_init_tx_chan()`、`dwmac4_dma_init_channel()` 等函数从 `priv->plat->dwmac4_addrs` 取得地址映射指针，再通过宏/inline helper 计算寄存器地址。
- 对 `dwmac4.h` 中可见的 MTL channel、ETS、TX queue weight、send-slope、high/low credit helpers，`addrs == NULL` 时明确回退到原固定地址和原步长。

Panther 适用性核对：
- 6.1.174 `stmmac_of_get_plat_data()` 使用 `devm_kzalloc()` 分配 `plat_stmmacenet_data`，因此未赋值的新增指针初始为 NULL。
- 6.1.174 `dwmac-rk.c` 中没有对 `plat_dat->dwmac4_addrs` 赋值，也没有为 Panther 提供自定义 DWMAC4 register map。
- 因此 Panther 的该指针按当前 Rockchip glue 源码应保持 NULL，使用 helper 的默认寄存器偏移回退，而不是进入其他 SoC 的自定义映射。

**初步结论：** 这项改动对 Panther 是默认地址兼容路径，现有源码证据不支持它改变 Panther 的 TX DMA/MTL 寄存器地址。它仍需与 6.12.81 候选源码中的相同 fallback 逻辑做映射核对，但不能仅凭“引入地址抽象”认定是故障根因。

## 5. 其他观察

- `drivers/net/phy/realtek.c` 在两个 stable tag 的文件内容相同；没有发现 6.1.116→6.1.174 的 RTL8211F 驱动差异。
- `kernel/dma/mapping.c` 在两个 tag 的文件内容相同；`include/linux/dma-mapping.h` 有少量变化，但本轮尚未发现它们改变 STMMAC 普通 TX DMA_TO_DEVICE 映射调用。
- `dwmac-rk.c` 只有极少量文本变化；本轮未发现新增的 Panther TX 专属配置。
- `stmmac_platform.c` 的 MDIO node 解析结构有重构：从单个 `stmmac_dt_phy()` 中查找并配置 MDIO，转为单独的 `stmmac_of_get_mdio()` 辅助函数和更明确的 node 引用管理。它影响 PHY/MDIO discovery 的组织方式，但 6.1.174 Panther 仍可完成 PHY link up；目前没有证据把它与“TX 帧未出网口”建立因果联系。后续若查初始化顺序，将单独审查该路径，不在本轮扩大结论。

## 6. 本轮结论

### 已确认（源码层面）
- 6.1.116 与 6.1.174 的普通 `stmmac_xmit()` 核心提交步骤和调用顺序一致。
- 两版 `stmmac_tx_clean()` 的 OWN 检查、DMA read barrier、descriptor completion/reclaim 主体一致。
- 两版 `stmmac_tx_err()` 的停止、清理、重置、重启流程一致。
- 6.1.174 新增 DWMAC4 register address abstraction；Rockchip Panther glue 没有设置自定义 `dwmac4_addrs`，平台数据经 `devm_kzalloc` 分配，因此使用 NULL 默认地址回退。
- 两版 `drivers/net/phy/realtek.c` 内容相同。

### 尚未证明
- 6.1.174 的实际 Panther BSP 镜像是否只包含上述 upstream stable 变化，还是叠加了其他 ophub/Rockchip 补丁。
- 6.1.174 新增地址抽象在所有 DMA register helpers 中的 Panther 默认回退是否已逐项覆盖；本轮已核对 TX channel init 和 MTL helpers 的关键路径，但不是整份头文件形式化验证。
- 上述源码差分能否解释 6.12.81 的 MAC/RGMII/PHY 之间外部不可见现象；当前没有这样的因果证据。
- 代码执行和 MAC 内部计数仍不能证明帧已越过 RGMII TX 引脚。

### 当前判断
本轮没有发现 6.1.174 对普通 STMMAC TX 提交、DMA descriptor ownership/reclaim 或 RTL8211F 驱动引入直接可疑的行为回归。DWMAC4 地址映射重构是本轮最显著变化，但 Panther 代码走 NULL 默认地址回退，暂不列为根因候选。

## 7. 下一步（仍只做静态研究）

下一项只检查 6.1.116→6.1.174 的 DWMAC4 MAC/MTL TX 启动和队列初始化函数差异，重点是：
- MAC TX enable / disable；
- DMA TX channel start / stop；
- MTL TX queue mode / TXQEN / TQS；
- queue-to-channel mapping；
- link speed change callback 是否会重写上述状态。

不再重复本轮已完成的 `stmmac_xmit()`、`stmmac_tx_clean()`、`stmmac_tx_err()` 或 RTL8211F 文件比较；不做设备测试。
