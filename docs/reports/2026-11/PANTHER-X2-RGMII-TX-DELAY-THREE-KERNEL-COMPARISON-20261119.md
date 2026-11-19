# Panther X2：RGMII TX delay 三版本源码对照（6.1.116 / 6.1.174 / 6.12.81）

## 1. 本轮目标与边界

只核对与当前 TX 故障直接相关的一项：PHY 的 RGMII TX delay 与 RK3568 GMAC TX clock delay 配置，在已知正常 6.1.116、最早明确异常 6.1.174、故障 6.12.81 三版之间是否发生有效变化。

本轮只读精确版本源码及设备树，不访问设备、不发帧、不抓包、不读写寄存器、不改配置。

源码版本：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.1.174：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

## 2. Panther 三版 GMAC 设备树配置相同

三版 `rk3566-panther-x2.dts` 的 `&gmac1` 关键字段一致：

- `clock_in_out = "input"`
- `phy-mode = "rgmii"`
- `tx_delay = <0x30>`
- `rx_delay = <0x10>`
- 使用同一组 `gmac1m0_* ` pinctrl groups
- 同一 PHY reset GPIO 与 reset delays
- PHY 节点均为 MDIO address 0

即：三版设备树没有把 RGMII TX delay 从 PHY 内部延时切换到另一个模式，也没有改变 TX delay 数值。

## 3. RTL8211F PHY driver 的 TX delay 配置相同

三版 `drivers/net/phy/realtek.c` 的 `rtl8211f_config_init()` 对 `PHY_INTERFACE_MODE_RGMII` 均执行：

- `val_txdly = 0`
- `val_rxdly = 0`
- 对 Page `0xd08` / Reg `0x11` 的 TX delay bit 执行 mask 修改，清除 PHY 内部 2ns TX delay
- 对 Page `0xd08` / Reg `0x15` 的 RX delay bit 执行 mask 修改，清除 PHY 内部 2ns RX delay

因此 Panther 的设计组合是：
- PHY driver 按 RGMII 模式关闭 PHY 内部 TX/RX delay；
- TX/RX delay 数值由 Rockchip GMAC GRF delayline 提供；
- 这套策略在 6.1.116、6.1.174、6.12.81 源码中没有实质变化。

6.12.81 的 Realtek driver 在 LED 恢复、optional clock 获取及 soft-reset 返回值检查方面有额外代码，但没有改变上述 RGMII TX delay mask/value。

## 4. RK3568 GMAC glue 的 delayline 差异

三版均由 `rk3568_set_to_rgmii()` 配置：
- GMAC1 CON0：TX/RX delay 数值字段；
- GMAC1 CON1：RGMII interface select 与 TX/RX delay enable 位。

6.1.116 的实现顺序：
1. 先写 CON0 delay 数值；
2. 再写 CON1，选择 RGMII 并使能 TX/RX delay。

6.1.174 / 6.12.81 的实现顺序：
1. 先写 CON1，选择 RGMII 并设置 TX/RX delay enable；
2. 再写 CON0 delay 数值。

这是一项源码执行顺序变化，但最终写入的两个寄存器及字段相同。由于 Panther DTS 中 TX/RX delay 都是非零值（0x30 / 0x10），6.1.174/6.12 的 `DELAY_ENABLE(tx_delay, rx_delay)` 会同时使能 TX/RX delay；6.1.116 的旧式逻辑也会同时使能两者。

因此当前没有证据表明该顺序变化会造成持续的 TX delay 配置差异。它最多意味着配置瞬间先后顺序不同，不能据此解释链路稳定后 TX 持续不出网口。

## 5. 该分支结论

**已排除为持续性版本回归候选：**
- Panther DTS 的 RGMII 模式与 TX delay 值；
- RTL8211F 内部 TX delay enable/disable 配置；
- RK3568 GMAC GRF TX delay 数值与最终 enable 状态。

**仅记录、不升级为故障候选：**
- 6.1.116 与 6.1.174/6.12 的 CON0/CON1 写入先后顺序变化。最终寄存器值相同，尚无证据将瞬态次序与持续 TX 故障建立因果关系。

**未因此证明：**
- GMAC TXC/TXD/TX_CTL 电气信号正常；
- RGMII 信号已经到达 RTL8211F；
- PHY 已从 MDI 端发出任何指定帧。

本轮只关闭“TX delay 配置是否在三个内核间发生持续变化”这一项，不是 TX 物理边界验证。

## 6. 后续唯一合理方向

既然 PHY 内部 RGMII TX delay 与 RK3568 GRF TX delay 的最终配置在三个版本间一致，下一项应继续追踪 RK3568 的 GMAC TX 时钟路径本身：`clock_in_out=input` 下 GMAC TXC 输出/输入时钟选择、`mac_clk_tx` / `clk_mac_speed` 的时钟父子关系，以及 6.1.116 到 6.1.174 首次异常之间相关 clock enable/parent/rate 调用路径是否改变。

不重复读取已经完成的 clock_summary、CRU mux、pinctrl 或 GRF 运行时状态；只从精确版本源码和既有报告中定位尚未审计的差异。任何新的设备读取均先提出方案并等待授权。

## 7. 依据

- 6.1.116 DTS: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.1.174 DTS: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.12.81 DTS: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 对应版本 `drivers/net/phy/realtek.c` 与 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`，见上述精确源码提交。

**结论：** 在 Panther 已知 RGMII 配置下，6.1.116、6.1.174、6.12.81 的 PHY TX delay 与 RK3568 GMAC TX delay 最终设置相同。该分支不解释当前持续 TX 故障，应关闭，继续研究 GMAC TX clock source/enable 路径。
