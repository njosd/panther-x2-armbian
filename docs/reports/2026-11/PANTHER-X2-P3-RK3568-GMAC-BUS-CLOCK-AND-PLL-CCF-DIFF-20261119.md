# Panther X2：P3 GMAC 时钟树深层映射——RK3568 CRU 与 PLL enable/disable 语义（2026-11-19）

## 1. 范围

承接 P3 RK35xx BSP 来源审计，本轮只读比较：
- 正常 general：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 故障 RK35xx BSP 6.1.174 候选：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633
- 持续异常 RK35xx BSP 6.12.81：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

没有访问 Panther 实机，没有读取 clock summary/MMIO，没有发包、抓包、MDIO/PHY 操作、接口重启或配置修改。

## 2. 已确认的 Panther GMAC1 时钟拓扑

Panther X2 DTS 与 RK356x SoC DTS 对照确认：

- GMAC1 MAC 主时钟：`stmmaceth = SCLK_GMAC1`。
- GMAC1 TX/RX 数据时钟：`mac_clk_tx` 与 `mac_clk_rx` 均对应 `SCLK_GMAC1_RX_TX`。
- GMAC1 bus clocks：`aclk_mac = ACLK_GMAC1`，`pclk_mac = PCLK_GMAC1`。
- GMAC speed clock：`clk_mac_speed = SCLK_GMAC1_RX_TX`。
- Panther DTS 设置 `clock_in_out = "input"`，并将 `SCLK_GMAC1` 的 parent 指向外部 fixed-clock `gmac1_clkin`。
- PHY 子节点 `rgmii_phy1` 没有 `clocks` 属性；RK35xx BSP 对该外接 PHY 调用 `of_clk_get(phy_node, 0)` 会得到错误指针，但仅 integrated PHY 才把该获取失败作为致命错误。随后 `gmac_clk_enable()` 用 `IS_ERR()` 跳过该不存在的可选 PHY clock。

### 2.1 general 6.1.116 与 RK35xx BSP 的 handle 获取

General 6.1.116：
- bulk optional clock 名称：`aclk_mac`、`pclk_mac`、`pclk_xpcs`、`mac_clk_tx`、`clk_mac_speed`；
- 通过 `devm_clk_bulk_get_optional()` 获取并检查错误；
- 单独获取 `stmmaceth`，检查错误；
- 仅 integrated PHY 获取并启用 PHY clock。

RK35xx BSP 6.1.174 候选：
- 逐项 `devm_clk_get()`：`mac_clk_rx`、`mac_clk_tx`、`aclk_mac`、`pclk_mac`、`stmmaceth`、`clk_mac_speed`；
- 对 handle 获取失败只记录日志，不统一将错误返回 probe；
- `pclk_xpcs` / `clk_xpcs_eee` 仅在 SGMII/QSGMII 获取；
- 外接 PHY clock 是 optional，获取失败后不会启用。

Panther SoC DTS 中上述 RGMII 必需 clock-names 均有定义；当前没有证据证明某个名称缺失或 provider lookup 必然失败。**但 BSP 不传播 clk_get / clk_prepare_enable 错误，意味着运行时若某个必需 clock provider 返回错误，驱动仍可能继续并把 clk_enabled 置 true；是否发生过尚无证据。**

## 3. GMAC1 CRU 的具体父子关系

6.1.116 general 与 RK35xx BSP 6.1.174 候选中的 `drivers/clk/rockchip/clk-rk3568.c`，GMAC1 相关 PNAME / clock registration 行逐项一致：

- `SCLK_GMAC1` parent list：`clk_mac1_2top`、`gmac1_clkin`。
- `SCLK_GMAC1` 为 mux，带 `CLK_SET_RATE_PARENT | CLK_SET_RATE_NO_REPARENT`。
- `SCLK_GMAC1_RX_TX` parent list：`clk_gmac1_rgmii_speed`、`clk_gmac1_rmii_speed`、`clk_gmac1_xpcs_mii`。
- `ACLK_GMAC1` 是 gate，parent 为 `aclk_usb`。
- `PCLK_GMAC1` 是 gate，parent 为 `pclk_usb`。
- `pclk_usb` 是无 mux composite，parent 为 `aclk_usb`。
- `aclk_usb` parent list：`gpll300`、`gpll200`、`gpll100`、`xin24m`。

Panther DTS 把 GMAC1 的 MAC 主时钟切到外部 `gmac1_clkin`，但 GMAC ACLK/PCLK 仍沿 SoC CRU 的 USB-domain parent chain。它们不是外部 125MHz RGMII clock 的同一条路径。

这一区分很重要：即使 MAC TX/RX 时钟来源已由外部 PHY 输入固定，GMAC bus/interface clock 的父时钟仍可能依赖 GPLL 分支。

## 4. 新发现：Rockchip PLL CCF enable/disable 实现不同

文件：`drivers/clk/rockchip/clk-pll.c`

General 6.1.116 的 `rockchip_rk3036_pll_enable()`：
1. 清除 PLL PWRDOWN；
2. 等待 PLL lock；
3. 返回；没有切换 PLL mux parent。

General 6.1.116 的 `rockchip_rk3036_pll_disable()`：
1. 直接设置 PLL PWRDOWN；
2. 没有先把 mux 切到 slow parent。

RK35xx BSP 6.1.174 候选：
1. enable：清除 PWRDOWN → 等待 lock → `pll_mux_ops->set_parent(..., PLL_MODE_NORM)`；
2. disable：先 `set_parent(..., PLL_MODE_SLOW)` → 再设置 PWRDOWN。

RK35xx BSP 6.1.174 与 6.12.81 的这两个函数体相同。该行为在 RK35xx 源码初始导入 commit `e1ae5c80f59ecd3f7cdd285c35110d21d42923d8`（2025-04-11）就已存在，不是 6.1.174 version bump 新增。

### 4.1 该 PLL callback 确实用于 RK3568 PLL

RK3568 的 `rk3568_pll_clks[]` 将 APLL/DPLL/CPLL/GPLL/NPLL/VPLL 定义为 `pll_rk3328` 类型。Rockchip `rockchip_clk_register_pll()` 对 `pll_rk3328` 和 `pll_rk3036` 选择 `rockchip_rk3036_pll_clk_ops`，因此上面的 enable/disable callback 是 RK3568 GPLL 等 PLL clock provider 实际注册的操作，不是无关 SoC 的 dead code。

GMAC1 的 ACLK parent `aclk_usb` 可选择 `gpll300/gpll200/gpll100`。因此若运行时 ACLK_USB parent 选择 GPLL 派生时钟，GMAC ACLK 的 CCF parent prepare/enable 链会涉及该 PLL provider。

### 4.2 已排除的通用 clock framework 差异

在 general 6.1.116 与 RK35xx BSP 6.1.174 候选中：
- `drivers/clk/clk-gate.c` 的 `clk_gate_enable()`、`clk_gate_disable()`、`clk_gate_is_enabled()` 函数体相同；
- `drivers/clk/clk.c` 的 `clk_core_prepare()`、`clk_core_enable()`、`clk_core_disable()` 函数体相同；
- `drivers/clk/clk-mux.c` 文件完全相同；
- `drivers/clk/rockchip/clk-rk3568.c` 的 GMAC1 clock parent / mux / gate 定义相同。

因此，当前发现不是 CCF 通用 prepare/enable 算法或 GMAC1 mux/gate 注册变化，而是 Rockchip PLL provider 的 enable/disable 顺序实现差异。

## 5. 因果边界

### 已验证

1. GMAC1 MAC 时钟的外部输入路径与 ACLK/PCLK bus clock path 是两条不同的 clock chain。
2. GMAC1 ACLK/PCLK 分别依赖 `aclk_usb` / `pclk_usb`；`aclk_usb` 可由 GPLL 派生时钟供给。
3. RK3568 PLL 使用 `pll_rk3328` 类型，并注册到包含上述 RK3036 PLL enable/disable callbacks 的 ops。
4. BSP 相对 general 6.1.116 增加 PLL enable 后切换 normal、disable 前切换 slow 的动作；6.12.81 延续该实现。
5. 通用 CCF enable/disable、clk-gate、clk-mux 实现以及 RK3568 GMAC1 parent definitions 未发现相应差异。

### 未验证 / 不得推断

1. Panther 运行时 `aclk_usb` 实际选择 GPLL300、GPLL200、GPLL100 还是 XIN24M。
2. 故障内核启动时，GPLL 是否发生过从 slow 到 normal 的切换、是否等待 lock 成功。
3. 该 PLL mux 切换是否与 GMAC probe、MAC enable 或 TX 发送时序发生竞争。
4. 当前证据不能说明该差异导致 TX 不出线；它只是一个有明确调用链依据、且 6.1.174-rk35xx/6.12.81-rk35xx 共有的候选机制。

## 6. P3 下一步

继续只读，不操作 Panther：

1. 追踪 RK3568 PLL 的 `gpll300/gpll200/gpll100` 注册、parent index 与模式寄存器语义，确认 GPLL parent mux 在 CCF 中如何报告当前父时钟。
2. 检查 U-Boot / Linux clock init 是否可能设置或保留 `aclk_usb` parent；区分 DTS 指定值、驱动默认值与 bootloader 遗留硬件状态。
3. 检查 BSP clock provider 是否在 probe/init 时调用 PLL ops，还是仅在 clock refcount 从 0→1 / 1→0 时调用；不要把函数存在等同于函数已执行。
4. 只有静态证据仍不能确认运行时 parent 时，再提出最小只读 clock summary 取证方案；未经用户授权不执行。

不重复已完成的 RGMII delay、PHY reset GPIO、CSU NULL/no-op、TX DMA descriptor、普通 CCF enable 流程审计。

## 7. 参考链接

- General 6.1.116 RK3568 CRU: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/clk-rk3568.c
- RK35xx 6.1.174 candidate RK3568 CRU: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/clk/rockchip/clk-rk3568.c
- General 6.1.116 PLL provider: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/clk-pll.c
- RK35xx 6.1.174 candidate PLL provider: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/clk/rockchip/clk-pll.c
- RK35xx 6.12.81 PLL provider: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/clk/rockchip/clk-pll.c
- RK35xx initial vendor import: https://github.com/unifreq/linux-6.1.y-rockchip/commit/e1ae5c80f59ecd3f7cdd285c35110d21d42923d8
