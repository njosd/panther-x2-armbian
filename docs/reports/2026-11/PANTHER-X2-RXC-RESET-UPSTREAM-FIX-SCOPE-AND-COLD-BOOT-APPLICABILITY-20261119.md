# Panther X2：RXC/PHY resume 上游修复的适用范围与冷启动 DHCP 故障关联性（2026-11-19）

## 1. 本轮目的

继续审查既有报告发现的上游提交：
`06232cb44bc8e81adc2f1d40a01bed830b607ea2`
标题：`net: stmmac: resume PHY before hardware setup when opening the interface`。

重点确认它是否能解释 Panther 当前 6.12.81 冷启动后 DHCPv4 不成功，而不是仅因平台/PHY 型号相似就将其当作根因。

本轮仅查公开源码、官方 PHY datasheet 与仓库既有测试报告；没有执行设备命令、PHY MDIO 读写、接口重启或配置修改。

## 2. 6.12.81 精确源码不包含该修复

对照：
- Panther 6.12.81 精确源码：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 上游修复提交：`06232cb44bc8e81adc2f1d40a01bed830b607ea2`

在 6.12.81 的 `stmmac_main.c`：
- `__stmmac_open()` 先执行 runtime PM resume；
- 再执行 `stmmac_init_phy()`；
- 接着调用 `stmmac_hw_setup()`；
- 完成后才调用 `phylink_start()`；
- 没有 `phylink_prepare_resume(priv->phylink)`。

上游修复版在 `stmmac_hw_setup()` 前加入 `phylink_prepare_resume()`，并明确注释其原因：接口因 MTU change 等原因 reopen 时，PHY 可能仍处于 phylink_stop 引起的 power-down 状态；PHY power-down 允许停止 RX clock，而 STMMAC DMA software reset 要求 RX clock 正在运行。若先 DMA reset、后 phylink_start 恢复 PHY，就可能 reset 失败。

因此，**6.12.81 确实缺少这项上游修复**。但适用条件必须严格区分。

## 3. 该修复的触发条件不是普通冷启动

上游 commit 描述的故障链：

```
接口已正常运行
  -> MTU change / interface reopen
  -> phylink_stop()
  -> PHY power-down / RX clock may stop
  -> __stmmac_open()
  -> stmmac_hw_setup()
  -> DMA software reset（此时 RX clock 可能尚未恢复）
  -> reset timeout/failure
  -> phylink_start()（原顺序在 DMA reset 后，太晚）
```

修复是在 reopen 的硬件 setup 前先准备恢复 PHY。

Panther 已归档的 6.12.81 DHCP 故障现象则是：
- 启动后接口可以注册；
- PHY 被识别；
- Link Up 1000Mbps Full；
- NetworkManager DHCPv4 Discover 未完成；
- 既有双端抓包将 Discover 的丢失边界定位在 Panther 本机 outgoing 抓包点之后、hEX 收包之前。

现有 6.12.81 测试报告记录 MTU=1500，NetworkManager profile MTU=auto；没有证据表明故障启动前发生 MTU change、PHY suspend/resume 或 netdev reopen。现有日志摘录也没有报告 DMA reset failure，但历史日志筛选并非完整日志的严格排除。

所以：
- 该修复缺失是**已确认源码差异**；
- 它对 RK3566 + RTL8211F-VD 的 reopen 场景是**已确认有效机制**；
- 它解释 Panther 本轮冷启动后 DHCP/raw TX 帧外部不可见，是**当前不成立的推断**，缺少必要触发条件和 DMA reset 错误证据。

不能因为 6.12.81 缺少此修复就直接 cherry-pick 到 Panther，也不能用它解释所有 RX/TX 故障。

## 4. RTL8211F PHYCR2=0x1801 线索重新定级

仓库已有报告 `116-RTL8211F-PHYCR2-RXC-CLEARANCE-CRITICAL-FINDING-20261118.md`、`PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md` 已经确认：
- 6.1.116 的 JL2xx1 workaround 对 MDIO PHY address 0 发起 Page 0xa43 / Reg 0x19 = 0x1801 的整寄存器写入；
- RTL8211F-CG Rev.1.7 定义 bit1 为 RXC clock output enable；
- 因此若写入成功并保持，0x1801 会清除 RXC enable；
- 随后 BMCR software reset；
- 6.1.116 正常双向网络结果与“RXC 确实被关闭且持续关闭”相矛盾。

本轮重新核对官方 datasheet：
- PHY pin 27 是 RGMII RXC，连续接收参考时钟，千兆时为 125MHz；
- PHYCR2 bit1 明确是 RXC output enable；
- PHYCR2 表要求设置后执行 software reset；
- BMCR software reset 的表格仅明确说明 BMCR/BMSR 返回默认值；datasheet 并未明确说明 PHYCR2 所有 vendor bits 的 software-reset retention 规则。
- hardware reset（PHYRSTB）则明确使所有寄存器返回默认值。两种 reset 不可混为一谈。

因此目前能说的是：源码发起了整寄存器写入，后续驱动不主动恢复 bit1；但没有 MDIO 波形/返回值检查、实机 PHYCR2 回读、software-reset retention 证明，不能说 PHY 实际最终关闭 RXC。116 正常网络是必须解释的反证。

另外，Panther 的 Linux PHY ID 记录为 `0x001cc916`，此前仓库报告已指出驱动打印的 RTL8211F 名称不足以区分普通 CG 与 VD-CG；应使用原始 PHYID2 或芯片顶标进一步确认。当前报告不重复型号推断，也不把另一平台 RTL8211F-VD 案例当成 Panther 型号证据。

## 5. 对当前主故障的优先级调整

| 线索 | 状态 | 对本轮冷启动 DHCP 故障的优先级 |
|---|---|---|
| 6.12 缺少 phylink_prepare_resume | 源码已确认 | 低；仅在 PHY 已 suspend 后 reopen 时触发 |
| 116 的 JL2xx1 0x1801 写入 | 源码已确认，实机最终寄存器状态未知 | 中低；存在 RXC 关闭矛盾，不能直接解释 6.12 TX 外部不可见 |
| PHY 普通 CG / VD-CG 实物型号 | 未确认 | 需要历史 PHYID2 或顶标证据 |
| DHCP Discover 本机 outgoing 后未到 hEX | 已由历史双端抓包限定边界 | 仍是当前主线 |
| 6.12 RX DMA/descriptor 收包路径及其与外部报文边界 | 仓库有多个已完成静态审计，尚无根因 | 继续以既有结果为基础，不重复测试 |

## 6. 下一步有限工作

不再重复阅读 PHYCR2 probe/config_init 或重复反汇编已审计的 STMMAC 调用链。

下一步只做以下静态核查：
1. 从 6.1.116、6.1.174、6.12.81 已归档启动日志中确认是否有 netdev reopen、MTU change、PHY suspend 或 DMA reset 错误；若记录不包含这些事件，明确标为“历史日志无证据”，不要求用户重跑。
2. 继续回到当前已确认的网络边界：本机 outgoing 抓包可见，但 hEX 看不到对应帧。只审计尚未闭环的 6.12 RX/TX 时钟/中断/descriptor 路径，排除已完成的 TX descriptor、MTL、PCS、phylink link-up、MAC 地址来源、loopback 测试。
3. PHY 型号区分只使用已有 PHYID2 原始值或现有照片；没有则不要求重复采集，保留未验证状态。

本轮不建议做设备侧 MDIO 读取或任何写入；如果后续确有必要读取，先单独提出具体只读命令、影响范围与安全条件，等待用户授权。

## 7. 参考来源

- Upstream fix commit： https://code.googlesource.com/linux/torvalds/linux/+/06232cb44bc8e81adc2f1d40a01bed830b607ea2
- Exact Panther 6.12.81 source： https://github.com/ophub/linux-6.12.y-rockchip/tree/661b2d8bf1284556f8876d5ed5fb80c64b22f94c
- RTL8211F-CG/FD-CG Rev.1.7 datasheet： https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf
- PHYCR2 and RXC definition, datasheet Table 38：PDF page 45
- RGMII RXC pin 27 definition：PDF page 8
- Software reset BMCR behavior：PDF page 34
- PHY address 0 broadcast semantics：PDF page 19

## 8. 关联仓库报告

- `PANTHER-X2-RTL8211F-CG-VS-VD-AND-STMMAC-RXC-RESET-REGRESSION-20261119.md`
- `PANTHER-X2-RTL8211F-PHYCR2-PROBE-ORDER-AND-CURRENT-UPSTREAM-CROSSCHECK-20261119.md`
- `PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md`
- `PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md`
- `PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`
