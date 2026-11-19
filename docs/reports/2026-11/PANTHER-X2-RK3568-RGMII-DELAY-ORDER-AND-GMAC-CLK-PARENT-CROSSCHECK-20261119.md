# Panther X2：RK3568 RGMII delay 写入顺序与 GMAC1 时钟父链交叉核查（2026-11-19）

## 1. 本轮范围

继续对照 Panther 实际正常/故障源码基线：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

本轮只审计 RK3568 GMAC1 RGMII delay 配置、时钟树父链和 link-up speed callback。没有设备侧命令、MMIO 访问、PHY MDIO 读写、驱动修改或接口操作。

## 2. 新确认的源码差异：RGMII delay 写入顺序发生变化

### 6.1.116

`rk3568_set_to_rgmii()` 顺序：
1. 写 `RK3568_GMAC0/1_CON0`：写入 RX/TX delay 数值；
2. 写 `RK3568_GMAC0/1_CON1`：选择 RGMII，并设置 RXCLK/TXCLK delay enable。

### 6.12.81

同一函数顺序改为：
1. 写 `CON1`：选择 RGMII，并设置 RXCLK/TXCLK delay enable；
2. 写 `CON0`：写入 RX/TX delay 数值。

因此 6.12 将两个寄存器写入顺序反转：**先 enable delay，再写 delay 数值；6.1 则先写数值，再 enable。**

### 2.1 宏语义变化

6.1：
```c
#define DELAY_ENABLE(soc, tx, rx) \
    (((tx) ? soc##_GMAC_TXCLK_DLY_ENABLE : soc##_GMAC_TXCLK_DLY_DISABLE) | \
     ((rx) ? soc##_GMAC_RXCLK_DLY_ENABLE : soc##_GMAC_RXCLK_DLY_DISABLE))
```

6.12：
```c
#define DELAY_ENABLE(soc, tx, rx) \
    ((((tx) >= 0) ? soc##_GMAC_TXCLK_DLY_ENABLE : soc##_GMAC_TXCLK_DLY_DISABLE) | \
     (((rx) >= 0) ? soc##_GMAC_RXCLK_DLY_ENABLE : soc##_GMAC_RXCLK_DLY_DISABLE))
```

6.12 新宏允许用负值表示 disable/不设置 delay，配合 `DELAY_VALUE` 的 `>=0` 检查支持 RGMII-ID/RXID/TXID 模式。6.1 旧宏以 C boolean 判断，无法用负数表达“关闭”。这属于新模式处理能力变化。

### 2.2 Panther 当前配置的实际效果

Panther DT 两个版本一致：
- `phy-mode = "rgmii"`
- `tx_delay = <0x30>`
- `rx_delay = <0x10>`

这两个值均为正数，因此 6.1 与 6.12 的 `DELAY_ENABLE` 对 Panther 都会启用 RX/TX delay；`DELAY_VALUE` 两版都会写入相同的 0x30 / 0x10。

所以：
- **值和最终 enable 状态相同；**
- **仅写入顺序不同；**
- 不能把 6.12 的负值 sentinel 新语义当作 Panther 当前 plain-RGMII 的差异原因。

此外，`rk_gmac_powerup()` 在两个版本中都先执行 GMAC clock enable，再设置 RGMII GRF delay/interface，最后才 enable PHY regulator。PHY 尚未上电时先后写 CON1/CON0，是否会影响后续正常时钟稳定，尚无证据。它是已确认差异，但当前根因优先级低于 clock enable 等待时间变化。

## 3. RK3568 GMAC1 CRU clock parent 定义两版相同

对比两份精确源码的 `drivers/clk/rockchip/clk-rk3568.c`，GMAC1 clock parent mux 和 clock registration 完全一致：

- `mux_gmac1_p = { "clk_mac1_2top", "gmac1_clkin" }`
- `mux_gmac1_rgmii_speed_p = { "clk_gmac1", "clk_gmac1", "clk_gmac1_tx_div50", "clk_gmac1_tx_div5" }`
- `mux_gmac1_rx_tx_p = { "clk_gmac1_rgmii_speed", "clk_gmac1_rmii_speed", "clk_gmac1_xpcs_mii" }`
- `SCLK_GMAC1` 是 `clk_gmac1` mux，parent 包含外部 `gmac1_clkin`；
- `SCLK_GMAC1_RGMII_SPEED` 是 `clk_gmac1_rgmii_speed` mux；
- `SCLK_GMAC1_RX_TX` 是 `clk_gmac1_rx_tx` mux，RGMII parent 为 `clk_gmac1_rgmii_speed`。

两个版本的 mux parent 数组、寄存器偏移和 mux bit 定义相同；未发现 6.1.116→6.12.81 的 CRU GMAC1 clock-tree parent 定义变化。

## 4. Panther DTS 对外部 125MHz clock 的定义两版相同

两个精确 DTS 均包含：
```dts
gmac1_clkin: external-gmac1-clock {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <125000000>;
    clock-output-names = "gmac1_clkin";
};

&gmac1 {
    assigned-clocks = <&cru SCLK_GMAC1_RX_TX>,
                      <&cru SCLK_GMAC1_RGMII_SPEED>,
                      <&cru SCLK_GMAC1>;
    assigned-clock-parents = <&cru SCLK_GMAC1_RGMII_SPEED>,
                             <&cru SCLK_GMAC1>,
                             <&gmac1_clkin>;
    clock_in_out = "input";
    ...
};
```

这表示设备树把外部 PHY clock 输入抽象成 125MHz fixed-clock，并将 CRU 父链配置为：
```
external gmac1_clkin (125 MHz, PHY clock input representation)
  -> SCLK_GMAC1 / clk_gmac1
     -> SCLK_GMAC1_RGMII_SPEED / clk_gmac1_rgmii_speed
        -> SCLK_GMAC1_RX_TX / clk_gmac1_rx_tx
```

这份 fixed-clock 节点是设备树中的时钟描述/父节点，不是对实物引脚波形的测量，也不能单凭它证明板上确有稳定 125MHz 输入。两个版本 DTS 与 CRU 定义一致，因此它本身不是版本差异。

## 5. 1Gbps link-up speed callback 两版行为相同

6.1.116：
- `stmmac_mac_link_up()` 调用 `fix_mac_speed(bsp_priv, speed)`；
- RK3568 callback 对 10/100/1000 分别设置 2.5/25/125MHz。

6.12.81：
- 调用签名扩展为 `fix_mac_speed(bsp_priv, speed, mode)`；
- Rockchip `rk_fix_speed()` 接收新增 mode 参数，但函数体未使用；
- RK3568 callback 对 10/100/1000 仍分别设置 2.5/25/125MHz；
- `clk_mac_speed` 由 bulk array 索引改为独立 clock handle，但最终指向 DTS 的 `SCLK_GMAC1_RGMII_SPEED`。

因此 1Gbps 时设定 125MHz 的目标值和实际 clock ID 相同。尚未证明实机 `clk_set_rate()` 成功，但既有运行记录显示 1Gbps Full Link Up，降低了“link-up speed callback 完全未执行”的可能性。

## 6. 本轮结论与候选优先级

| 项目 | 结果 | 当前解释力 |
|---|---|---|
| RGMII delay 最终数值 | 两版均 0x30/0x10 | 低 |
| RGMII delay enable 状态 | 两版 Panther plain-RGMII 均 enable | 低 |
| delay 寄存器写入顺序 | 6.1 先值后 enable；6.12 先 enable 后值 | 低到中，尚无时序证据 |
| RGMII-ID sentinel 宏语义 | 6.12 新增负值支持 | Panther 当前不适用 |
| GMAC1 CRU clock parent tree | 两版一致 | 排除源码 parent-tree 变化 |
| DTS 外部 125MHz clock 描述 | 两版一致 | 不能证明物理波形 |
| 1Gbps speed callback 目标 rate | 两版均 125MHz | 低 |
| GMAC clock enable 等待时间 | 6.1 5ms；6.12 100–200µs | 仍是更高优先级的源码差异 |
| 6.12 clock enable 错误处理 | 多个 clk_prepare_enable 返回值未检查 | 已确认代码质量退化；尚无实际失败证据 |

### 结论

本轮没有发现 GMAC1 CRU clock parent 或 1Gbps speed callback 的版本回归。RGMII delay 寄存器写入顺序确有变化，但 Panther 当前数值和最终使能状态一致，而且两个寄存器都在 PHY regulator 上电前写入；暂时不能解释接口已 Link Up 但帧没有被外部接收的现象。

当前仍应优先追查：
1. 6.12 的 100–200µs GMAC clock stabilization delay 是否足够（6.1 为 5ms）；
2. 6.12 的 clk_prepare_enable 错误是否曾发生但被静默忽略；
3. 若这两项没有证据，再回到 MAC TX enable 与实际 RGMII/PHY 发射边界。

不读取危险 dummy-syscon debugfs registers，不使用 devmem，不做 PHY 寄存器写入，不修改任何配置。

## 7. 源码链接

- 6.1.116 dwmac-rk.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.12.81 dwmac-rk.c: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 clk-rk3568.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/clk-rk3568.c
- 6.12.81 clk-rk3568.c: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/clk/rockchip/clk-rk3568.c
- 6.1.116 Panther DTS: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.12.81 Panther DTS: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts

## 8. 关联报告

- `PANTHER-X2-6.1.116-VS-6.12.81-RK3566-GMAC-CLOCK-SEQUENCE-REGRESSION-20261119.md`
- `PANTHER-X2-6.12.81-STMMAC-PHY-RESUME-PATCH-APPLICABILITY-20261119.md`
- `PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`
