# Panther X2：6.1.174 实际源码基线的 GMAC 时钟路径复核与前报告更正（2026-11-19）

> **更正说明：** 本报告修正同日早前版本的一项关键源码归属错误。此前把 `ophub/linux-6.1.y-rockchip@c2f148d` 的时钟代码误当作 6.1.174 实际构建候选；该提交实际日期为 2026-11-10，远晚于 6.1.174 源码快照 `unifreq/linux-6.1.y@3f06ed3`（2026-05-23）。目前没有证据证明 c2f148d 被 cherry-pick 进 6.1.174 实际镜像。故 100–200µs 等待和忽略 clock-enable 返回值不得归因于 6.1.174。

## 1. 本轮实际比较对象

- 6.1.116 正常源码：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，提交信息 `up to 6.1.116`，2024-11-09。
- 6.1.174 源码：`unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7`，提交信息 `up to 6.1.174`，2026-05-23。
- 另一个较新的 Rockchip BSP 源码快照：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，提交信息 `arm64: dts: rockchip: dshanpi a1 overlay support fspi-nor or amp`，2026-11-10。它仅作为独立分支样本，不作为 6.1.174 构建源。

本轮只读取 GitHub 源码和仓库记录，没有连接设备、发帧、抓包、读取寄存器或修改配置。

## 2. 关键更正：6.1.174 实际源码仍使用 5ms 和错误检查

对 `unifreq/linux-6.1.y@5eb841b` 与 `@3f06ed3` 的 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c:gmac_clk_enable()` 做函数级比较：

两版 enable 路径完全相同：
1. `clk_bulk_prepare_enable(num_clks, clks)`；
2. 检查返回值，失败立即返回；
3. `clk_prepare_enable(clk_phy)`；
4. 检查返回值，失败立即返回；
5. 如有 callback，执行 clock selection；
6. `mdelay(5)`；
7. 设置 `clk_enabled = true`。

6.1.174 相对 6.1.116 只改变了 disable 分支的 clock-selection callback 与 bulk clock disable 的先后顺序；不改变 cold power-up 的 enable 顺序、错误检查或 5ms 等待。

因此：
- **6.1.116→6.1.174：没有 5ms→100–200µs 回归。**
- **6.1.116→6.1.174：没有忽略 bulk clock-enable 返回值的回归。**
- 早前报告把上述两项错误归到 6.1.174，现予撤回。

## 3. c2f148d 中的 100–200µs 代码属于另一份后期 BSP 快照

`ophub/linux-6.1.y-rockchip@c2f148d` 的 `gmac_clk_enable()` 确实：
- 将 bulk clock 获取/使能改成逐项 `devm_clk_get()` / `clk_prepare_enable()`；
- 没有检查这些 `clk_prepare_enable()` 返回值；
- 使用 `usleep_range(100, 200)`；
- 最后仍设置 `clk_enabled = true`。

但 c2f148d 的提交日期是 2026-11-10，且提交主题是 DshanPi overlay 支持；它不是 2026-05-23 的 6.1.174 tag commit。除非未来找到构建日志或明确 cherry-pick 链证明这段代码进入了某个 6.1.174 镜像，否则不能把它当成该镜像的源码证据。

这份代码可以作为后期 Ophub Rockchip BSP 的独立实现风险归档，不能用于解释 6.1.174 最早出现的故障。

## 4. 6.1.116 与 6.1.174 的 RK3568 CRU provider：相关实现文件完全一致

在两个实际源码端点之间，以下文件逐字节相同（GitHub 返回的文件内容完全相等）：

- `drivers/clk/rockchip/clk-rk3568.c`：78,544 bytes；
- `drivers/clk/clk-mux.c`：6,588 bytes；
- `drivers/clk/clk-gate.c`：5,824 bytes；
- `drivers/clk/clk-fixed-rate.c`：5,861 bytes；
- `drivers/clk/clk-composite.c`：13,467 bytes；
- `drivers/clk/rockchip/clk-pll.c`：28,795 bytes。

另外，`drivers/clk/clk.c` 中的 `clk_core_prepare()` 与 `clk_core_enable()` 函数体在两个端点完全相同。没有发现 6.1.174 改变 CCF clock prepare/enable 错误传播语义。

## 5. Panther GMAC1 的 TX/RX clock parent chain 与 provider ops

Panther 两个板级 DTS 端点都定义：
- `gmac1_clkin` 为 125MHz fixed-clock；
- `SCLK_GMAC1` parent 指向 `gmac1_clkin`；
- `SCLK_GMAC1_RGMII_SPEED` parent 指向 `SCLK_GMAC1`；
- `SCLK_GMAC1_RX_TX` parent 指向 `SCLK_GMAC1_RGMII_SPEED`；
- `mac_clk_tx` 与 `clk_mac_speed` 都引用 `SCLK_GMAC1_RX_TX`；
- `stmmaceth` 引用 `SCLK_GMAC1`。

因此 Panther RGMII clock chain 为：
```
gmac1_clkin (125MHz fixed-clock)
  -> SCLK_GMAC1 / clk_gmac1
  -> SCLK_GMAC1_RGMII_SPEED / clk_gmac1_rgmii_speed
  -> SCLK_GMAC1_RX_TX / clk_gmac1_rx_tx
```

provider ops 语义：
- `clk_mux_ops` 只有 `get_parent`、`set_parent`、`determine_rate`，没有 prepare/enable callback；
- `clk_fixed_rate_ops` 只有 rate/accuracy 回调，没有 prepare/enable callback；
- `clk_gate_enable()` 写 gate 后固定返回 0；
- 这些 ops 文件在 6.1.116 与 6.1.174 端点完全一致。

所以，Panther TX/RX 使用的外部 fixed-clock → mux 链本身没有一个会返回 enable 错误的 mux/fixed-clock provider callback。它仍受 CCF parent reference-count 和时钟树初始化状态约束，但没有发现 6.1.174 新增的 provider 失败路径。

### ACLK/PCLK branch

RK3568 CRU 对 GMAC1 的定义为：
- `ACLK_GMAC1`：gate，parent `aclk_usb`；
- `PCLK_GMAC1`：gate，parent `pclk_usb`；
- gate provider 使用通用 `clk_gate_enable()`，该函数写入 gate 后返回 0；
- `aclk_usb` / `pclk_usb` 的 composite parent 结构在两个实际端点的 `clk-rk3568.c` 中完全相同。

PLL provider 文件也完全相同；RK3328/RK3036 PLL enable callback 写入 power-up、等待 lock、切换到 normal parent，最后返回 0。没有发现 6.1.174 新增一个会导致 Panther GMAC ACLK/PCLK enable 失败的 provider 实现变化。

这不是对任何一次实机 clock 状态的证明，只是排除了本轮源码端点中可见的 provider 行为回归。

## 6. 本轮结论

### 已确认
1. 6.1.174 的实际源码快照 `3f06ed3` 中，GMAC clock enable 仍为 5ms settle，并检查 bulk enable 返回值。
2. 6.1.116 与 6.1.174 的 RK3568 CRU provider 及通用 mux/gate/fixed-rate/composite/PLL 实现文件完全一致。
3. CCF `clk_core_prepare/enable` 关键函数未改变。
4. Panther TX/RX clock parent chain 以外部 125MHz fixed-clock 为根；mux/fixed-rate ops 没有可返回错误的 enable callback。
5. c2f148d 中的 100–200µs 与忽略错误实现属于另一份 2026-11-10 后期源码快照，目前没有证据能归入 6.1.174 镜像。

### 尚未证明
- 6.1.174 镜像的全部厂商补丁/构建输入是否与 `3f06ed3` 完全一致，仍需原始 Actions 构建日志或 binary provenance 闭环。
- 任何静态 clock provider 比较都不能证明运行时 RGMII TX 波形存在，也不能证明 DHCP Discover 已越过 MAC/RGMII 边界。
- 本轮没有获得帧从 Panther 物理网口输出的证据。

### 阶段判断
本轮没有发现 6.1.116→6.1.174 的 GMAC CRU clock provider 回归。此前以 100–200µs 等待和忽略 clock-enable 返回值解释 6.1.174 故障的说法不成立，除非出现新的构建来源证据。

## 7. 下一步

停止把 clock enable settle/error handling 作为 6.1.174 故障主线。继续从已锁定的 6.1.116→6.1.174 实际源码增量中寻找未审查且直接影响 TX 的差异；优先回到 Rockchip GMAC glue 与 MAC/PHY interface bring-up 的其他变化，而不是重复 CRU provider、clock_summary、parent mux 或任何实机测试。

所有外部发帧、抓包、PHY 计数和物理边界测试继续暂停。只有找到能够证明帧越过 MAC/RGMII 边界的可靠证据后，才讨论是否恢复外部测试。
