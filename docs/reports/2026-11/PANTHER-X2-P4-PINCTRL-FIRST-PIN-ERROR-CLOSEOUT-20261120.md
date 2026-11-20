# Panther X2：P4 Rockchip pinctrl 首 pin 错误处理静态审计收尾（2026-11-20）

## 1. 目的、边界与源码端点

本报告完成 GMAC1 RGMII pinctrl 首 pin 错误处理的限定静态审计。目标是确认：
- 6.12 Rockchip pinctrl 是否可能吞掉 pin group 第一个 pin 的 mux 写入错误；
- 该行为是否也存在于最早异常 6.1.174-rk35xx；
- Panther GMAC1 M0 pin group 的首 pin 顺序是否使该问题理论上影响 TX pins；
- 现有证据能否证明 Panther 发生过该错误。

全程只读公开源码及仓库已有资料。未操作 Panther、未读取/写入 MMIO、未查看危险 dummy-syscon debugfs、未发送帧、未抓包、未修改设备或制作补丁。

源码端点：
- 正常 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 最早异常 6.1.174-rk35xx 高置信度候选：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633
- 持续异常 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

## 2. 首 pin 错误吞噬：源码事实

三个端点的 drivers/pinctrl/pinctrl-rockchip.c 均包含 rockchip_pmx_set()，其循环逻辑相同：
1. 从 group 的第 0 个 pin 开始调用 rockchip_set_mux()；
2. 遇到非零返回值立即 break；
3. 根据 ret 和 cnt 决定是否回滚并向 pinctrl core 返回错误。

区别在错误处理条件：
- 6.1.116：if (ret)。即使第一个 pin（cnt == 0）失败，也会跳过空回滚循环并返回原始错误。
- 6.1.174-rk35xx：if (ret && cnt)。
- 6.12.81-rk35xx：if (ret && cnt)。

因此，6.1.174 和 6.12.81 中若第一个 pin 的 rockchip_set_mux() 返回错误，cnt == 0，代码会跳过错误返回，最终返回 0。pinctrl core 因而可能把该 mux group 视为成功。循环已经 break，group 中后续 pin 不会被尝试设置。

这是一个真实、可复核、跨两个异常源码候选共有而正常 6.1.116 不存在的错误处理差异。它不只是 6.12 的新增问题。

## 3. rockchip_set_mux() 中首 pin 错误可能来自哪里

对 RK3568 路径核对：
- rockchip_verify_mux() 会检查 iomux index、unrouted 和 GPIO-only 限制；
- Panther GMAC1 M0 引脚均为 GPIO3 bank 的合法 4-bit IOMUX，mux 值为 3；
- mux=3 可由 4-bit IOMUX 直接表达，不进入 RK3506 RMIO 特殊处理；
- RK3568 不进入 RK3562/RK3572/RK3576/RK3588 等其他 SoC 专用分支；
- 正常路径最终使用 GPIO3 对应 regmap 的 regmap_update_bits()，其错误返回会沿 rockchip_set_mux() 传给 rockchip_pmx_set()。

因此，理论触发条件不是 GMAC pin mux 值非法或 Panther 误入其他 SoC 分支，而是某次针对对应 IOMUX 寄存器的 regmap 写入操作返回错误（或其他前置校验在未来源码/配置变化下返回错误）。本轮没有发现 Panther 的正常静态 DTS 配置本身会触发校验失败。

## 4. Panther GMAC1 M0 group 顺序与 TX 影响

6.1.116、6.1.174-rk35xx、6.12.81-rk35xx 的 RK3568 pinctrl DTS 中，相关 group 定义及顺序一致。关键 group 的 pin 顺序如下：

| Group | 首 pin | 后续 pin | 若首 pin 失败且错误被吞，未执行部分 |
|---|---|---|---|
| gmac1m0_miim | GPIO3_PC4 / MDC | GPIO3_PC5 / MDIO | MDIO 不会继续设置 |
| gmac1m0_clkinout | GPIO3_PC0 | 无 | 无后续 pin |
| gmac1m0_rx_bus2 | GPIO3_PB1 / RXD0 | PB2 / RXD1、PB3 / RXDV | 两个后续 RX pin 不会继续设置 |
| gmac1m0_tx_bus2 | GPIO3_PB5 / TXD0 | PB6 / TXD1、PB7 / TXEN | TXD1、TXEN 不会继续设置 |
| gmac1m0_rgmii_clk | GPIO3_PA7 / RXCLK | PA6 / TXCLK | TXCLK 不会继续设置 |
| gmac1m0_rgmii_bus | GPIO3_PA4 / RXD2 | PA5 / RXD3、PA2 / TXD2、PA3 / TXD3 | 包括 TXD2/TXD3 在内的后续 pin 不会继续设置 |

因此，若相应 group 首 pin 的 mux 写入确实失败：
- gmac1m0_tx_bus2 首 pin 失败会影响整个 TXD0/TXD1/TXEN group；
- gmac1m0_rgmii_clk 首 pin RXCLK 失败会跳过后续 TXCLK；
- gmac1m0_rgmii_bus 首 pin RXD2 失败会跳过后续 TXD2/TXD3。

这提供了一个理论上能影响 MAC→PHY RGMII TX 输出的机制。不能因为 group 名称含 RX 就忽略其后续 TX pin。

## 5. 与故障现象的匹配程度

### 已验证
- 首 pin 错误被吞的实现差异存在于 6.1.174-rk35xx 和 6.12.81-rk35xx，正常 6.1.116 没有。
- Panther GMAC1 M0 group 的 DTS pin 顺序包含 TXD0/TXCLK/TXD2/TXD3 等上述关联。
- rockchip_set_mux() 的 regmap 错误可传播到 rockchip_pmx_set()；当错误发生在 group 首 pin 时，异常版本会错误返回 0 并跳过该 group 余下 pin。
- 该机制与两个异常版本共有、正常版本没有的时间边界相符；并且有可能造成 pin group 部分配置失败。

### 未验证
- Panther 实际运行的 6.1.174/6.12.81 启动时，GPIO3 IOMUX 对应 regmap 写入是否曾返回错误。
- 具体哪个 pin group 首 pin 发生错误。
- 运行时 pinmux owner/state 是否存在异常。
- 硬件 IOMUX 寄存器最终值及 TXC/TXD 电气状态。

### 不能推断
- 不能仅凭源码条件分支认定 regmap 写入发生过错误。
- 不能把当前故障直接归因于 pinctrl。
- 不能用正常 6.1.116 的 DTS group 定义相同，证明异常内核的实际 pinmux 寄存器状态也相同。
- 不得通过 devmem、regmap debugfs 或 dummy-syscon debugfs 读取 IOMUX/GRF；既有报告已记录危险 dummy-syscon 读取事故。

## 6. P4 结论与关闭条件

**P4 静态源码审计完成，结论为：存在真实且与 TX 引脚组相容的潜在软件错误路径，但缺少现场失败证据，根因未证实。**

P4 按限定目标正式关闭，不继续扩大源码搜索，不制作补丁，也不安排 Panther 实机操作。该项保留为未证实的低至中优先级候选，而不是“已排除”。

若未来重新决定补充证据，既有报告提出的唯一低风险软件核查是只读 pinctrl debugfs 的 pinmux ownership（前提是用户明确授权且目标内核/接口可用）。它只能说明 Linux framework 记录的 owner/function，不能证明硬件寄存器或 RGMII 波形。任何寄存器读取、发帧、抓包或示波器测试均不在本次授权范围内。

## 7. 下一步路线建议

P1–P4 的限定静态源码审计现已结束。纯源码继续搜索的边际收益较低。下一阶段不自动执行任何实机测试；应先汇总全部证据并评估是否值得进入 P5 物理边界验证。若不授权 P5，则当前调查以“TX 故障的 MAC/RGMII/PHY 物理边界尚未定位；P4 潜在 pinctrl 错误路径未获现场证实”作为阶段性结论。

## 8. 源码参考

- [6.1.116 pinctrl-rockchip.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/pinctrl/pinctrl-rockchip.c)
- [6.1.174-rk35xx pinctrl-rockchip.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/pinctrl/pinctrl-rockchip.c)
- [6.12.81-rk35xx pinctrl-rockchip.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/pinctrl/pinctrl-rockchip.c)
- [6.12.81-rk3568-pinctrl.dtsi](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3568-pinctrl.dtsi)
- [6.1.174-rk35xx rk3568-pinctrl.dtsi](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/arch/arm64/boot/dts/rockchip/rk3568-pinctrl.dtsi)
