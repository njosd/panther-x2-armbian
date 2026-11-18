# 重要补充：116 的 0x1801 整寄存器写入会清除 RTL8211F RXC Enable（2026-11-18）

## 1. 为什么新增本报告

前一份 `JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261118.md` 主要解释了 `0x1801` 置位的 bits[13:12]、bit11、bit0，但遗漏了对其余可写位的影响。

原始代码不是按 mask 修改寄存器，而是直接向 RTL8211F PHYCR2（page 0xa43 / reg 0x19）写入完整 16-bit 值 `0x1801`。因此所有未置位的 RW 位也会被写为 0。这个差异非常重要。

数据手册依据：Realtek RTL8211F(I)-CG / RTL8211FD(I)-CG Datasheet Rev. 1.4，2014-11-17，Table 38，PHYCR2，page 0xa43 / address 0x19。

## 2. 0x1801 的完整位解码

`0x1801 = 0001 1000 0000 0001b`

| 位 | RTL8211F PHYCR2 定义 | 默认值 | 写入 0x1801 后 | 含义 |
|---:|---|---:|---:|---|
| 13:12 | CLKOUT SSC Capability | 00 | 01 | Reserved 编码 |
| 11 | CLKOUT Frequency Select | 1 | 1 | 125 MHz |
| 7 | CLKOUT SSC Enable | 0 | 0 | 不启用 CLKOUT SSC |
| 5 | PHY-mode EEE Enable | 1 | 0 | 关闭 PHY-mode EEE |
| 3 | SYSCLK SSC Enable | 0 | 0 | 不启用 SYSCLK SSC |
| 1 | RXC Enable | 1 | 0 | **关闭 RXC clock output** |
| 0 | CLKOUT Enable | 1 | 1 | 开启 CLKOUT |

其他 RO/Reserved 位按 datasheet 定义处理；不能把对 RO 位的写入解释为可配置效果。

最重要的两个额外影响：

1. bit 1 从默认 1 被清为 0。Datasheet 明确写明 bit 1 是 `RXC Enable`，1 表示 RXC Clock Output Enabled。
2. bit 5 从默认 1 被清为 0。Datasheet 明确写明 bit 5 是 `PHY-mode EEE Enable`。

## 3. RXC 与 Panther RGMII 接收链的直接关系

同一份 Realtek datasheet 第 7.11.1 节明确说明：

- RTL8211F 的 RGMII 接口中，TXC 由 MAC 产生；
- RXC 始终由 PHY 产生；
- 1000Base-T 下 RXC 来源频率为 125 MHz；
- RTL8211F 的 RGMII MAC interface 包含 TXC/RXC；
- PHY block diagram 中 PCS RX 输出包括 RXCTL、RXD[3:0] 和 RXC。

因此，如果 PHYCR2 bit 1 的清零实际生效并持续，PHY 将关闭它向 MAC 提供的 RGMII RXC 输出。按标准 RGMII 连接，这会直接影响 MAC 接收数据采样，而不只是一个与数据面无关的辅助时钟。

## 4. 这与 6.1.116 已知正常现象存在明显矛盾，不能跳过

现有项目基线记录 6.1.116 Panther Ethernet 正常工作；同时仓库 dmesg 证实该次运行绑定 RTL8211F 驱动。

若以下条件全部成立：
- 四次 workaround 写入中的第二次 MDIO transaction 确实到达 PHY；
- PHYCR2 对该写入按 datasheet 接受；
- bit 1 清零在 BMCR software reset 后保持；
- RTL8211F 的 RGMII RXC pin 确实直接连接 RK3566 GMAC RXC；
那么应预期 RGMII 接收时钟停止，与 116 正常收包的已知现象不相容。

因此当前必须保留这个矛盾，不能直接推断 workaround 导致 116 正常，也不能仅凭源码发起 write 就断言 RXC 在 116 实机被关闭。

可能解释（均未证实）：
1. MDIO write callback 被调用，但控制器事务未成功完成；源码忽略返回值。
2. PHY 对该值的实际处理与 datasheet 表格描述不同，或芯片版本/具体变体行为有差异。
3. 后续有其他固件、PHY 状态机或未纳入当前静态审计的写入重新使能 RXC。
4. 设备实际 RGMII 时钟连接/PHY 型号细节与当前假设不同。
5. PHY soft reset 对 PHYCR2 的保持行为与对 CLKOUT 设置的说明不能简单外推到所有位。

这些只是待核验解释，不是结论。

## 5. 对回归调查的影响

此发现将 JL2xx1 workaround 从“可能改变 CLKOUT/保留 Reserved 编码”的一般性线索，提升为一个更具体的候选：

> 116 的通用 workaround 对 RTL8211F PHYCR2 做整寄存器写入，按 RTL8211F datasheet 字段解释会清除 RXC Enable 和 PHY-mode EEE Enable，同时设置 CLKOUT 字段。若 RXC disable 实际生效，理论上会影响 RGMII RX 数据通道。

但是，这仍然无法解释“116 网络正常”，所以**不能将它直接认定为根因，也不能据此把 0x1801 移植到 6.12**。相反，这个矛盾提示我们此前“源码调用必然发生”与“PHY 实际寄存器状态”之间仍有证据缺口。

## 6. 最小下一步

在不修改任何配置的前提下，优先核对 6.1.116 已有归档是否包含：
- PHYCR2 page 0xa43/reg 0x19 的读回值；
- MDIO bus/PHY 地址的原始信息；
- 是否有 PHY register dump 或 ethtool private register snapshot。

如果历史归档没有该寄存器值，下一步实机验证应仅做只读读取：
- 先读并保存当前 page selector；
- 读取 page 0xa43 / reg 0x19；
- 恢复原 page selector；
- 不执行任何 MDIO write、不触发 PHY reset、不重启接口。

由于这是对正在运行设备进行读取，正式执行前仍需单独确认用户授权。此报告不要求当前执行实机读取。
