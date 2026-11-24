# Panther X2 GMAC1 RGMII 时钟树、CRU Gate 与 Reset 对比审计

- 日期：2026-11-24
- 范围：只读源码审计；限定 Panther X2 的 GMAC1、RGMII 实际路径。
- 不属于项目 A B1 实机部署或网络验证；本报告不授权任何设备操作。
- 6.1.116 源码基线：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`（与已知构建时间吻合的高置信度候选，非原始 Actions source_hash 闭环）。
- 6.1.174 源码基线：`ophub/linux-6.1.y-rockchip@5483dc4f5384213d1a1cdf90c937db97d58721d8`（对应已核实构建 source_hash）。

## 1. Panther X2 实际 DTS 时钟路径

两版 `rk3566-panther-x2.dts` 的 `&gmac1` 关键时钟配置一致：

```dts
assigned-clocks =
    <&cru SCLK_GMAC1_RX_TX>,
    <&cru SCLK_GMAC1_RGMII_SPEED>,
    <&cru SCLK_GMAC1>;
assigned-clock-parents =
    <&cru SCLK_GMAC1_RGMII_SPEED>,
    <&cru SCLK_GMAC1>,
    <&gmac1_clkin>;
clock_in_out = "input";
phy-mode = "rgmii";
```

板级固定时钟节点 `gmac1_clkin` 为 125MHz fixed-clock。由 assigned-clock-parents 建立的 RGMII 时钟父链为：

`gmac1_clkin (125MHz) → SCLK_GMAC1 → SCLK_GMAC1_RGMII_SPEED → SCLK_GMAC1_RX_TX`

即 MAC1 使用外部 125MHz 输入作为 RGMII 基准时钟源；不是由本审计推断 PHY 实际输出波形正常。

源码依据：
- [6.1.116 Panther X2 DTS](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)
- [6.1.174 Panther X2 DTS](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)

**结论：已验证，两版 Panther 板级 DTS 的 GMAC1 时钟父链、父时钟选择、125MHz 输入定义一致。**

## 2. CRU GMAC1 clock mux、divider 与 gate

两版 `drivers/clk/rockchip/clk-rk3568.c` 中 GMAC1 clock branch 和 mux parent 声明逐段比较，相关定义完全一致：

- `ACLK_GMAC1`：gate 位于 `RK3568_CLKGATE_CON(17)` bit 3，父时钟 `aclk_usb`。
- `PCLK_GMAC1`：gate 位于 `RK3568_CLKGATE_CON(17)` bit 4，父时钟 `pclk_usb`。
- `SCLK_GMAC1`：mux 位于 `RK3568_CLKSEL_CON(33)`，父项为 `clk_mac1_2top` / `gmac1_clkin`。
- `SCLK_GMAC1_RGMII_SPEED`：mux 位于 `RK3568_CLKSEL_CON(33)`，父项包括 125MHz 基准、`clk_gmac1_tx_div50`、`clk_gmac1_tx_div5`。
- `SCLK_GMAC1_RX_TX`：mux 位于同一 CLKSEL_CON(33)，父项包括 RGMII speed、RMII speed、XPCS MII；该 clock 具有 `CLK_SET_RATE_PARENT`。
- `CLK_MAC1_REFOUT`、PTP ref 等分支定义也一致，但 Panther RGMII 输入时钟路径不依赖 MAC REFOUT 输出。

GMAC link speed callback 对应的目标速率在两版均为：
- 1000Mbps → 125MHz
- 100Mbps → 25MHz
- 10Mbps → 2.5MHz

该 callback 对 `clk_mac_speed` 调用 `clk_set_rate()`；Panther DTS 将 `clk_mac_speed` 映射到 `SCLK_GMAC1_RX_TX`。其下游速率选择由既有 CRU mux/divider 树完成。两版 RK3568 CRU 的 mux parent、divider 和寄存器字段没有发现差异。

### 一个真实但有限的 CRU flag 差异

6.1.174 的 CRU 定义将 `PCLK_USB` 标记为 `CLK_IS_CRITICAL`；6.1.116 对应定义的 flags 为 0。`PCLK_GMAC1` 的父时钟正是 `pclk_usb`，所以 6.1.174 会在 CRU critical-clock 保护阶段保持该父时钟开启；6.1.116 则允许其在没有 consumer 引用时按普通 unused-clock 流程处理。

边界：
- `ACLK_USB` 在两版均未标记为 critical；`ACLK_GMAC1` 的 gate 和父链定义没有变化。
- 当 GMAC 驱动启用 `PCLK_GMAC1` 时，CCF 会递归启用父时钟 `PCLK_USB`；所以该 flag 差异主要改变未被 consumer 引用时的空闲/早期 gate 状态。
- 尚无证据证明这一差异会改变 Panther GMAC 已正常启用后的运行状态，亦无证据证明它造成网络故障。

**结论：GMAC1 专属 CRU mux/divider/gate 定义一致；父时钟 PCLK_USB 有一项 critical flag 差异，保留为已知的低优先级启动/空闲状态差异，不认定为故障原因。**

源码：
- [6.1.116 RK3568 CRU](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/clk-rk3568.c)
- [6.1.174 RK3568 CRU](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/drivers/clk/rockchip/clk-rk3568.c)

## 3. 驱动实际获取与启用的时钟集合

### 6.1.116

Rockchip driver 使用 `devm_clk_bulk_get_optional()` 获取 bulk clock 列表。RGMII 路径的关键项包括：
- `aclk_mac`
- `pclk_mac`
- `mac_clk_tx`
- `clk_mac_speed`

随后 `clk_bulk_prepare_enable()` 批量启用，并检查返回值；失败会返回错误。代码注释明确 `stmmaceth` 由 stmmac core 启用。

### 6.1.174

改为逐项 `devm_clk_get()` / `clk_prepare_enable()`。RGMII 实际会启用：
- `aclk_mac`
- `pclk_mac`
- `mac_clk_tx`
- `clk_mac_speed`

`mac_clk_tx` 和 `clk_mac_speed` 在 Panther DTS 中都映射到 `SCLK_GMAC1_RX_TX`，是同一 CCF clock provider 节点的两个 consumer 引用；多次 enable/disable 对应 CCF 引用计数，不是两套独立的硬件 mux。

`mac_clk_rx` 只在 RMII 分支启用；`clk_mac_ref` / `clk_mac_refout` 也属于 RMII 分支。Panther 是 RGMII，故不进入这些 enable 分支。

6.1.174 公共 `rk356x.dtsi` 新增声明 `pclk_xpcs` 和 `clk_xpcs_eee`，但驱动只在 SGMII/QSGMII 条件分支获取这两个时钟。RGMII 下两个结构体指针保持 NULL。后续 enable 代码使用 `!IS_ERR(ptr)` 判断，NULL 会通过该判断，但 Linux CCF 的 `clk_prepare()` / `clk_enable()` 对 NULL 明确返回 0，因此这些调用是无效果的空操作，不会启用 XPCS 硬件时钟。powerdown 对 NULL 的 disable/unprepare 同样无效果。

### 两版驱动处理差异

- 6.1.116：bulk enable 返回值受检查，出错会中止。
- 6.1.174：逐项 enable 的返回值没有被检查，初始化可能在某项时钟启用失败后继续。
- 6.1.174 对 RGMII 还会尝试对 NULL 的 XPCS clock 执行空操作；已由 CCF 源码确认该行为不会解引用 NULL。
- 时钟启用后等待时间 6.1.116 为约 5ms，6.1.174 为 100–200μs；该差异及其历史来源已在此前 clock-enable/settle 子项审计，不在本报告重复推导。

**结论：两版 RGMII 实际需要的核心时钟集合一致，驱动启用顺序和错误处理策略不同；未发现 Panther RGMII 被错误切入 XPCS 或 RMII 时钟分支。时钟错误处理差异保留为驱动层风险，但 CRU provider 对应项没有找到一个必然失败的 Panther 专属条件。**

源码：
- [6.1.116 dwmac-rk.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)
- [6.1.174 dwmac-rk.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)
- [6.1.174 CCF clk.c NULL handling](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/drivers/clk/clk.c)

## 4. GMAC1 reset 映射与执行顺序

Panther DTS 两版均声明：

```dts
resets = <&cru SRST_A_GMAC1>;
reset-names = "stmmaceth";
```

两版 RK3568 clock/reset binding 中 `SRST_A_GMAC1 = 236`。两版 CRU 初始化都以相同参数注册通用 hiword-mask reset controller：
`rockchip_register_softrst(np, 30, reg_base + RK3568_SOFTRST_CON(0), ROCKCHIP_SOFTRST_HIWORD_MASK)`。

寄存器映射可由通用 reset 实现直接推导：
- hiword-mask 模式每个 reset register 管 16 个 reset ID；
- ID 236 → bank 14、bit 12；
- `RK3568_SOFTRST_CON(14) = 0x400 + 14 × 4 = 0x438)；
- assert 写入 `BIT(12) | (BIT(12) << 16)`；
- deassert 写入 `BIT(12) << 16`。

stmmac core 两版 reset 流程相同：对 `stmmaceth` reset 执行 assert、deassert，然后对可选 AHB reset 做 deassert，等待 10μs，再进行 MAC hardware init。Panther DTS 未提供名为 `ahb` 的第二项 reset，因此该 optional AHB reset 不构成额外的 Panther reset 线。

**结论：已验证，两版 GMAC1 reset ID、CRU reset register 映射、hiword-mask 写法和 stmmac core assert/deassert 顺序一致；没有发现 6.1.174 新增或遗漏 Panther GMAC1 reset 的证据。**

源码：
- [6.1.116 RK3568 binding](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/include/dt-bindings/clock/rk3568-cru.h)
- [6.1.174 RK3568 binding](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/include/dt-bindings/clock/rk3568-cru.h)
- [6.1.116 reset controller](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/softrst.c)
- [6.1.174 reset controller](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/drivers/clk/rockchip/softrst.c)
- [6.1.116 stmmac core reset sequence](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174 stmmac core reset sequence](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)

## 5. 本项结论与证据等级

### 已验证
1. 两版 Panther DTS 的 RGMII clock parent assignments 与 125MHz external fixed-clock 定义一致。
2. 两版 RK3568 CRU 中 GMAC1 专属 mux、divider、gate 的定义一致。
3. 两版 GMAC1 reset ID、reset register mapping、hiword-mask 语义和 stmmac reset 执行顺序一致。
4. 两版 RGMII 的核心 clock enable 集合一致；XPCS clocks 不会在 Panther RGMII 路径产生有效 enable 操作。
5. 6.1.174 的 PCLK_USB critical flag 是真实差异，但主要影响无 consumer 时的空闲/早期 gate 状态。

### 未验证
- Panther 实机当时 CRU 寄存器中的 mux/gate/reset 实际值。
- PHY 输出的 125MHz 时钟波形、占空比、抖动及板级时钟质量。
- 两版源码候选与历史现场运行二进制的逐字节构建闭环（尤其 6.1.116 原始 source_hash 缺失）。

### 本项判断
**CRU parent/mux/gate/reset 的 Panther GMAC1 主路径没有发现足以解释 6.1.174 网络回归的确定性变化。** PCLK_USB critical flag 与驱动时钟错误处理策略属于真实差异，但目前没有证据证明其导致运行期 GMAC TX 故障。不得据此制作补丁或操作实机。

本项结项：**源码依赖关系已查清；没有发现已证实的 CRU parent/gate/reset 根因。** 后续继续沿既定审计路线，不重复本项。
