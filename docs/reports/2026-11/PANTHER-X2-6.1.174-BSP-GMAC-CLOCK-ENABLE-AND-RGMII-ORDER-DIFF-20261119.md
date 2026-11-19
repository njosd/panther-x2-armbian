# Panther X2：6.1.174 BSP 候选源码中的 GMAC 时钟使能与 RGMII 初始化差分（2026-11-19）

## 1. 本轮比较对象与证据等级

本轮不再使用 upstream stable tag 代替实际 BSP 构建源码，而是直接比较：

- **6.1.116 正常源码基线：** `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- **6.1.174 BSP 高置信度源码候选：** `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- **6.12.81 BSP 源码：** `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

6.1.174 的 `c2f148...` 是此前仓库通过 Ophub RK35xx 构建工作流和源码树时间点锁定的高置信度候选；由于没有取得该次 Actions job 的完整日志，不能把它说成已由构建日志绝对证明的 binary provenance。

本轮只读取 GitHub 源码与仓库报告，没有连接设备、发帧、抓包、读取寄存器或修改系统配置。

## 2. 关键发现：6.1.174 BSP 已经具有与 6.12.81 相同的 GMAC clock enable 逻辑

文件：`drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`

对三个版本的 `gmac_clk_enable()` 做函数级比较：

- 6.1.174 BSP 候选与 6.12.81 BSP 的函数内容**完全一致**。
- 两者与 6.1.116 正常基线存在明确语义差异。

### 2.1 6.1.116 正常基线

`rk_gmac_clk_init()`：
- 通过 `devm_clk_bulk_get_optional()` 获取 bulk clocks；
- 获取失败会返回错误；
- 单独取得 `stmmaceth` clock，错误会返回；
- 对集成 PHY 的 clock 获取错误会返回。

`gmac_clk_enable()`：
- 使用 `clk_bulk_prepare_enable()`；
- 检查返回值，失败立即返回；
- 对 `clk_phy` 的 `clk_prepare_enable()` 也检查返回值；
- 设置 clock selection 后等待 `mdelay(5)`，即 5 ms；
- 最后才设置 `clk_enabled = true`。

因此，正常的 bulk clock enable 失败不会被静默当作成功继续。

### 2.2 6.1.174 BSP 候选

`rk_gmac_clk_init()` 改为分别调用 `devm_clk_get()`：
- 对多个 clock handle 获取失败只打印错误；
- 除集成 PHY clock 的特殊条件外，不将多数获取失败作为初始化失败返回；
- 外部 PHY 场景下 `clk_phy` 是可选项。

`gmac_clk_enable()`：
- 对每个 clock handle 仅判断是否为 `ERR_PTR`；
- 调用 `clk_prepare_enable()` 时不检查返回值；
- 即使某个 clock 的 prepare/enable 返回错误，仍继续处理其他 clock；
- 最后仍执行 `usleep_range(100, 200)`，并设置 `clk_enabled = true`；
- 整个函数最后返回 0。

因此存在一条确定的条件性静默失败路径：

```
clk handle 有效
  -> clk_prepare_enable(clock) 返回错误
  -> 错误被忽略
  -> 继续初始化
  -> clk_enabled = true
  -> rk_gmac_powerup() 认为时钟启动成功
```

注意：`!IS_ERR(clock)` 只证明 handle 不是错误指针，并不证明 `clk_prepare_enable()` 成功。

### 2.3 6.12.81 BSP

`gmac_clk_enable()` 与 6.1.174 BSP 候选逐字一致：
- 同样逐个 `devm_clk_get`；
- 同样忽略 `clk_prepare_enable` 返回值；
- 同样等待 100–200 µs；
- 同样无条件设置 `clk_enabled = true`。

这意味着该行为不是 6.12 才出现的新变化，而是 **6.1.174 BSP 候选中已经存在、并延续到 6.12.81 的共同代码路径**。

## 3. Panther 的 RGMII 路径确实使用这些时钟

Panther 的运行时 FDT / 已归档 DTS 基线：
- compatible：`rockchip,rk3568-gmac`；
- MAC：GMAC1；
- `phy-mode = "rgmii"`；
- `clock_in_out = "input"`；
- 外接 RTL8211F，不是 integrated PHY。

在 6.1.174 BSP 候选 `rk_gmac_clk_init()` 中：
- RGMII 取得的关键 clocks 包括 `aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`；
- `mac_clk_rx`、`clk_mac_ref`、`clk_mac_refout` 仅 RMII 分支取得/启用；
- `pclk_xpcs`、`clk_xpcs_eee` 仅 SGMII/QSGMII 分支取得/启用；
- `clk_phy` 对外接 PHY 为可选，不应将它与上述 GMAC 必需时钟混为一谈；
- `stmmaceth` 由 STMMAC core 自身管理，Rockchip glue 中对应 enable 调用仍是注释状态。

因此当前最值得关注的是 ACLK、PCLK、MAC TX 和 GMAC speed clock 的实际 prepare/enable 结果，而不是 RMII/XPCS 专用时钟。

## 4. 同一 BSP 变化还改变了 RK3568 RGMII delay 写入顺序

文件：`dwmac-rk.c`，函数 `rk3568_set_to_rgmii()`。

6.1.116：
1. 先向 GMAC1 CON0 写入 TX/RX delay 数值；
2. 再向 GMAC1 CON1 写入 RGMII interface select 与 TX/RX delay enable。

6.1.174 BSP 候选：
1. 先向 GMAC1 CON1 写入 RGMII interface select 与 delay enable；
2. 再向 GMAC1 CON0 写入 TX/RX delay 数值。

6.1.174 的宏还允许以负值表示某一方向 delay 不由 SoC 配置；但 Panther 的 `phy-mode=rgmii` 会传入实际 TX/RX delay 数值，因此两个方向都会进入 enable/value 配置。

6.12.81 的该函数与 6.1.174 BSP 候选保持同一顺序。这是已有报告曾在 6.1.116→6.12 比较中发现的变化；本轮新确认的是它同样存在于 6.1.174 BSP 候选源码。

两版最终写入的 delay 数值与 enable 状态可以相同，但写入顺序不同。当前没有证据证明这段初始化顺序本身导致运行时 TX 不输出，因此保留为次级候选，不把它定为根因。

## 5. 与已有实机证据的交叉约束

### 已有 6.12.81 运行时证据

仓库既有 clock_summary 采集显示：
- `clk_gmac1` / GMAC 主时钟：125 MHz，enable/prepare 计数非零；
- `mac_clk_rx`、`mac_clk_tx` 对应 GMAC RX/TX clock：125 MHz，计数非零；
- `clk_mac_speed`：125 MHz，计数非零；
- `aclk_mac`：297 MHz，计数非零；
- `pclk_mac`：99 MHz，计数非零；
- `ptp_ref`：62.5 MHz。

这降低了“6.12.81 当前采样时刻关键 clocks 完全没有开启”的可能性。

但 clock_summary 是后续运行时快照：
- 不能还原 probe 时每一次 `clk_prepare_enable()` 的返回值；
- 不能证明启动时序的 100–200 µs 一定足够；
- 不能证明 clock 在 MAC/DMA 第一次初始化前已经稳定；
- 也不能证明 6.1.174 历史异常启动时的 clock enable 结果。

### 已有 link-up 证据

6.1.174 与 6.12.81 均有 RTL8211F PHY ID、1000 Mbps Full Link 相关证据。Link Up 表明 PHY/链路协商路径工作，但不能证明 MAC TX 所需的每个内部时钟均按要求成功 enable、稳定并持续工作。

## 6. 当前判断

### 已确认（源码层面）
1. 6.1.116 与 6.1.174 BSP 候选的 GMAC clock init / enable 逻辑有实质变化。
2. 6.1.174 BSP 候选忽略多个 `clk_prepare_enable()` 的返回值，仍可能继续初始化并设置 `clk_enabled = true`。
3. 6.1.174 BSP 候选将时钟稳定等待从 5 ms 缩短到 100–200 µs。
4. 6.1.174 BSP 候选和 6.12.81 BSP 的 `gmac_clk_enable()` 完全一致。
5. Panther 当前 RGMII 路径使用 ACLK、PCLK、MAC TX 和 GMAC speed clock；该代码不是不适用的 SGMII/RMII 分支。
6. RK3568 RGMII delay 写入顺序在 6.1.174 BSP 候选中也已改变，并延续到 6.12.81。

### 尚未证明
1. 6.1.174 或 6.12.81 实机启动时是否有任一关键 `clk_prepare_enable()` 实际返回错误。
2. 是否有 clock provider 的 prepare/enable callback 在 Panther 的特定启动时序下失败。
3. 100–200 µs 是否不足以满足 Panther RK3566 GMAC / PHY clock 稳定要求。
4. RGMII delay enable-before-value 顺序是否会导致本机故障。
5. 该候选是否足以解释 DHCP Discover 未从 Panther 物理网口输出。

### 当前优先级
这是目前最值得保留的 **6.1.116 正常 → 6.1.174 首个明确异常 → 6.12.81 持续异常** 的共同 BSP 候选之一。

其中：
- “忽略 clock enable 错误”是明确的代码缺陷风险，但尚无实机失败记录；
- “5 ms 缩短至 100–200 µs”是明确的时序变化，但尚无资料证明该等待时间不足；
- 两者同时存在于 6.1.174 与 6.12.81，使它们比仅出现在 6.12 的变化更值得优先研究。

本报告不建议直接修改驱动或移植 5 ms，也不建议通过现场试错验证。

## 7. 下一步（继续静态研究）

下一步只做一项：追踪 RK3566 GMAC1 的四个关键 clock provider 和对应 `clk_ops`：
1. `aclk_gmac1`
2. `pclk_gmac1`
3. `clk_gmac1_rx_tx` / `mac_clk_tx`
4. `clk_gmac1_rgmii_speed` / `clk_mac_speed`

检查：
- 6.1.116 与 6.1.174 BSP 对应 CRU clock provider 是否有变化；
- prepare/enable callback 是否有可返回错误的条件；
- rate / parent / gate 选择是否发生改变；
- 已有日志或 clock_summary 是否能排除其中某些失败路径。

不重复已完成的 clock_summary、CRU mux、clock tree 实机采集；不读取寄存器、不运行 devmem、不发帧、不抓包、不改设备配置。若纯静态资料无法证明某次 enable 成败，就明确保留为未验证，不要求用户重复测试。
