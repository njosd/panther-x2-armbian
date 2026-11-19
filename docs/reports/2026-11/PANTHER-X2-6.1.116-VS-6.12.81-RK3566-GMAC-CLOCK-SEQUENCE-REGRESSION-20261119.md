# Panther X2：6.1.116 通用内核与 6.12.81 RK35xx 内核的 RK3566 GMAC 时钟序列差异（2026-11-19）

## 1. 本轮比较基线

这是第一次把 Rockchip GMAC glue 驱动直接按两个实际工作基线对照，而不是沿用此前错误的 6.1 Rockchip 专用分支：

- 正常工作 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`（Ophub 通用内核，构建来源高置信度重建）
- 故障 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`（Actions run 43405957386 / job 131820239401 精确锁定）

重要：2026-11-17 报告第 15 节的 `rk_gmac_powerup()/gmac_clk_enable()` 对照，使用的是 `unifreq/linux-6.1.y-rockchip`，不是 6.1.116 的通用内核。因此此前“Rockchip GMAC powerup/clock init 完全一致”的结论不能用于 6.1.116→6.12.81 的真实回归比较。本报告覆盖并纠正这一点。

## 2. 新发现：GMAC 时钟使能序列有实质变化

### 2.1 6.1.116 的 `gmac_clk_enable()`

源文件 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`，函数约 1714 行：

```c
ret = clk_bulk_prepare_enable(bsp_priv->num_clks, bsp_priv->clks);
if (ret)
    return ret;

ret = clk_prepare_enable(bsp_priv->clk_phy);
if (ret)
    return ret;

if (bsp_priv->ops && bsp_priv->ops->set_clock_selection)
    bsp_priv->ops->set_clock_selection(bsp_priv,
                                       bsp_priv->clock_input, true);

mdelay(5);
bsp_priv->clk_enabled = true;
```

对 RGMII，`rk_gmac_clk_init()` 的 bulk clock list 来自：
`aclk_mac`, `pclk_mac`, `pclk_xpcs`, `mac_clk_tx`, `clk_mac_speed`。
随后在适用时使能 `clk_phy`，调用 clock selection callback（若 SoC ops 提供），等待固定 5ms，才标记 clocks enabled。

### 2.2 6.12.81 的 `gmac_clk_enable()`

同一文件函数约 3251 行。驱动改为逐项获取/使能 clock：
- RGMII 路径逐项 enable `clk_phy`（若有效）、`aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`；
- `pclk_xpcs` / `clk_xpcs_eee` 仅在 SGMII/QSGMII 取用；
- 执行 `set_clock_selection()`（若 ops 提供）；
- 新增 `rockchip_csu_disable(csu_aclk)` 和 `rockchip_csu_disable(csu_pclk)`；
- 最后只等待 `usleep_range(100, 200)`，即约 0.1–0.2ms，而非 5ms。

因此等待时间缩短约 25–50 倍。更重要的是这不是单纯改 delay：clock handling 从 bulk prepare-enable 改成多个独立 `clk_prepare_enable()` 调用，并新增 CSU disable 动作。

### 2.3 错误处理也发生变化

6.1：
- `clk_bulk_prepare_enable()` 返回错误时立即退出；
- `clk_prepare_enable(clk_phy)` 返回错误时退出。

6.12：
- 多个 `clk_prepare_enable()` 的返回值没有检查；
- 仅检查 clock handle 是否为 ERR_PTR；
- 即使某个 clock 的 prepare/enable 操作失败，函数仍可能继续执行并将 `clk_enabled=true`。

这意味着 6.12 的 clock enable 失败有可能不再像旧 bulk path 一样直接阻止后续初始化，也可能没有清晰的失败日志。当前没有实机日志证明某个 GMAC clock enable 实际失败，但这是一个明确的错误处理退化点。

## 3. 对 Panther 当前 DTS 的映射

已归档的 Panther X2 最终合并 DTB / DTS：
- GMAC1 `phy-mode="rgmii"`
- `clock_in_out="input"`
- TX/RX delay `0x30/0x10`
- PHY addr 0
- clock-names 含 `stmmaceth`, `mac_clk_rx`, `mac_clk_tx`, `clk_mac_refout`, `aclk_mac`, `pclk_mac`, `clk_mac_speed`, `ptp_ref`（6.12 SoC DTS 另增加 XPCS clocks）

对当前 RGMII 路径：
- 6.1 的 bulk list 会获取/使能 `aclk_mac`, `pclk_mac`, `pclk_xpcs`, `mac_clk_tx`, `clk_mac_speed`；其中 `pclk_xpcs` 在 RGMII 并非功能必需，但旧驱动 bulk list 无条件包含。
- 6.12 明确只在 SGMII/QSGMII 取得/使能 XPCS clocks；RGMII 不走 XPCS。
- 两版都会处理 `mac_clk_tx` 与 `clk_mac_speed`，Panther DTS 中这两个名字映射到同一 `SCLK_GMAC1_RX_TX` 时钟源。
- 两版都把 `clock_in_out=input` 解析为 `clock_input=true`。
- RK3568 ops 未绑定 `set_clock_selection` callback；所以当前 RK3566/RK3568 GMAC1 路径中该 callback 条件不成立，不能把它当成两版间的有效配置差异。

## 4. 时钟使能与 PHY 上电的调用顺序

两版 `rk_gmac_powerup()` 都是先调用 `gmac_clk_enable(true)`，随后按 RGMII 写入 SoC GRF interface/delay 配置，之后才调用 `rk_gmac_phy_power_on(true)` 打开 PHY regulator，再进行 runtime PM 操作。

区别在于：
- 6.1：clock enable + clock selection 后等待 5ms，然后 RGMII GRF 设置、PHY regulator 上电；
- 6.12：逐项 clock enable + CSU disable 后等待 100–200µs，然后 RGMII GRF 设置、PHY regulator 上电。

因此缩短的等待发生在 PHY regulator 上电之前。不能直接把它解释为“给 RTL8211F 上电后少等了 5ms”；更准确的描述是：**SoC GMAC 时钟使能/CSU 操作之后、RGMII GRF 配置和 PHY regulator 上电之前的稳定等待缩短了约 25–50 倍。**

目前未从 commit history 确认这项改动的原始设计理由，也没有硬件时钟波形证据证明 100–200µs 对 Panther 一定不足。

## 5. 当前结论与优先级

### 已验证源码事实

1. 6.1.116 与 6.12.81 的 Rockchip GMAC glue 时钟使能路径并不相同。
2. 6.1.116 使用 bulk clock enable，并在 clock selection 后固定等待 5ms。
3. 6.12.81 改为逐项 enable 多个 clocks，增加 CSU aclk/pclk disable，并将等待缩短为 100–200µs。
4. 6.12 的逐项 `clk_prepare_enable()` 返回值没有被检查；6.1 bulk enable 路径检查返回值。
5. Panther 当前 RGMII/input 配置会走到该时钟使能路径；PHY regulator 上电发生在该等待之后。
6. 两版 RK3568 GMAC speed callback 对 10/100/1000 Mbps 设置的速率映射一致：2.5/25/125MHz。
7. `rk_fix_speed()` 新增的 mode 参数在 Rockchip callback 函数体中未被使用；不构成 Panther RGMII speed 配置差异。

### 当前判断

**这是目前最值得优先追查的 6.1.116→6.12.81 共享回归候选之一。**

原因：
- 它来自真实的 6.1.116 通用内核与精确 6.12.81 构建源比较；
- 修改发生在 GMAC bring-up 的电源/时钟初始化阶段，早于 PHY 上电和接口收发；
- 旧版 5ms 与新版 100–200µs 的差异显著；
- 新版同时改变了 clock enable error handling。

但不能仅凭代码就宣布它是根因。还需要确定 CSU helper 对 RK3566 的实际行为，以及时钟树/父时钟对该时序的约束。

## 6. 下一步限定核查（继续静态，不动设备）

1. 追查 6.12 中引入逐项 clock enable、CSU disable、100–200µs 等改动的提交历史和作者说明。
2. 检查 Rockchip CSU API 在 RK3566 上是否有 provider；如果没有，确认 `rockchip_csu_get()` 返回错误后转 NULL，`rockchip_csu_disable(NULL)` 是否为空操作。
3. 结合 RK3566 CRU clock tree，确认 GMAC1 `aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed` 的父子关系和 125MHz 输出条件。
4. 查 6.1.116 与 6.12.81 对应的 GMAC 时钟 enable 日志、clock summary（若既有记录中存在），不要求重跑。
5. 如果静态证据仍无法区分，再提出只读 clock summary / driver log 方案；不执行 MMIO、devmem、dummy-syscon debugfs，不改 clock rate、不改设备树、不运行 loopback。

## 7. 相关报告

- [6.12.81 精确构建源码中的 STMMAC PHY resume 修复适用性核查](./PANTHER-X2-6.12.81-STMMAC-PHY-RESUME-PATCH-APPLICABILITY-20261119.md)
- [Ethernet TX 物理边界与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- [GMAC/DHCP 与 U-Boot 启动链调查（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)
