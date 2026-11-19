# Panther X2：GMAC clock enable 错误处理与稳定等待时间版本回归（2026-11-19）

## 1. 本轮核心结论

精确对照源码：
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12.81 候选：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

此前只强调 5ms 与 100–200µs 的差异不够完整。真正重要的是两项同时变化：
1. 时钟 enable 错误处理从检查并向上返回错误，变为逐个调用但忽略返回值。
2. 时钟 enable 后等待从 5ms 缩短到 100–200µs。

这两项是已确认源码差异，但尚无实机证据证明 Panther 的关键时钟实际 enable 失败或 100–200µs 不足；它们是高优先级候选，不是根因定案。

## 2. 6.1.116 行为

RGMII 路径通过 devm_clk_bulk_get_optional 获取四个时钟：aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed。获取失败会返回错误。

gmac_clk_enable() 使用 clk_bulk_prepare_enable()，检查返回值并在失败时退出；随后单独 enable clk_phy，也检查返回值。rk_gmac_powerup() 检查 gmac_clk_enable() 返回值，因此 bulk clock enable 失败不会被静默当作成功继续。

完成 clock selection 后执行 mdelay(5)，即等待 5ms，然后才设置 clk_enabled=true。

## 3. 6.12.81 候选源码行为

6.12 将 bulk 获取改成多个 devm_clk_get()。获取失败多数只打印错误，不立即返回。对 Panther 的 RGMII 路径，mac_clk_rx 只在 RMII 分支 enable；XPCS clocks 只用于 SGMII/QSGMII，不是当前 RGMII enable 路径。

RGMII 实际 enable 的主要时钟为 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed；如果存在有效 PHY clock handle，还会尝试 enable clk_phy。

关键代码逻辑是：先用 IS_ERR() 检查 clock handle，再调用 clk_prepare_enable()，但不检查该函数的返回值。随后继续处理其他时钟，最终执行 usleep_range(100, 200)，并设置 clk_enabled=true。

因此，IS_ERR() 只能说明 handle 是否为错误指针，不能证明 prepare/enable 成功。若某个已取得 handle 的 clock 在 clk_prepare_enable() 阶段返回错误，6.12 仍可能继续初始化并把自身状态标记为 clock enabled。这是已确认的条件性静默失败路径。

## 4. Panther DTS 对照

两版 rk356x.dtsi 的 GMAC1 均声明 stmmaceth、mac_clk_rx、mac_clk_tx、clk_mac_refout、aclk_mac、pclk_mac、clk_mac_speed、ptp_ref。6.12 另增加 pclk_xpcs 和 clk_xpcs_eee，但 Panther 运行配置为 phy-mode=rgmii，XPCS clocks 不应进入当前路径。

当前 RGMII 路径重点是 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed。mac_clk_rx 仅在 RMII 分支 enable；clk_mac_refout 不是当前 RGMII input-clock enable 路径。

## 5. 与故障现象的关联

已知 Panther 在 6.12.81 能识别 PHY、Link Up 1000Mbps Full，TX descriptor/驱动完成计数增长，MMC TX frame/octet 计数增长，但外部 hEX/iMac 未观察到测试帧。

这些事实降低了“关键时钟完全没有开启”的可能性，但不能证明所有 GMAC internal/bus/TX clocks 的频率、门控和稳定时序都正确。

- 静默 enable 失败：如果失败的是 ACLK/PCLK/TX/MAC speed clock，理论上可能影响初始化/传输；但目前没有实际失败证据。
- 等待缩短：可能影响初始化时序，但没有证据证明 RK3566 上 100–200µs 必然不足。
- 两项组合是值得继续验证的候选，不足以支持直接修改驱动或恢复 5ms。

## 6. 状态表

| 项目 | 6.1.116 | 6.12.81 候选 | 结论 |
|---|---|---|---|
| RGMII clocks 获取 | bulk optional | 独立 devm_clk_get | 已确认差异 |
| bulk enable 错误处理 | 检查并返回 | 不再使用 bulk | 已确认差异 |
| 单时钟 enable 返回值 | 检查/传播 | 忽略 | 已确认差异 |
| enable 失败能否静默继续 | bulk 路径不会 | 可以 | 已确认代码路径 |
| settle delay | 5ms | 100–200µs | 已确认差异 |
| 实机是否发生 enable 失败 | 未知 | 未知 | 未验证 |
| 100–200µs 是否不足 | 未知 | 未知 | 未验证 |
| 是否为 DHCP/TX 故障根因 | 未知 | 未知 | 未定因 |

## 7. 下一步限定范围

1. 仅核对 Panther 最终运行 DT 中四个关键 RGMII clock 的 provider/name 对应关系，不重复已完成的基本 DTS 比对。
2. 仅追踪 RK3568 的 ACLK_GMAC1、PCLK_GMAC1、SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED enable callback 及其可能返回错误的条件。
3. 查找已有完整启动日志中的 clock provider/prepare/enable 错误；若没有记录，标记未验证，不要求用户重跑网络测试。
4. 若静态资料无法判断 100–200µs 是否足够，就保留为单一假设，不凭空下结论；任何现场验证须先提出最小风险方案并等待授权。

不重复 MAC 地址来源、TX descriptor、MTL TX queue、RGMII DTS 值、PHYCR2 probe/config_init、已完成环回测试。禁止读取 dummy-syscon debugfs registers 和使用 devmem。

## 8. 参考源码

- 6.1.116 dwmac-rk.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.12.81 dwmac-rk.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 rk356x.dtsi：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- 6.12.81 rk356x.dtsi：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- 2026 RK3568 SGMII series（6.12 驱动重构背景）：https://lkml.iu.edu/2609.0/01713.html
- 2025 RGMII delay ordering patch：https://lists.openwall.net/linux-kernel/2025/03/06/1811

## 9. 关联报告

- PANTHER-X2-RK3568-RGMII-DELAY-ORDER-AND-GMAC-CLK-PARENT-CROSSCHECK-20261119.md
- PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md
- PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md