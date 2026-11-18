# JL2xx1 workaround 寄存器语义与 RTL8211F 交叉核对（2026-11-18）

## 1. 关键来源链

在 6.1.116 源码仓库中，两个提交紧邻：

- `22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`（2022-12-24 16:07:18 UTC）：`drv: net: phy: Add JLSEMI JL2xx1 driver`
- `49b5f340f346cc9a5b777499fce46150b691b70e`（2022-12-24 16:08:26 UTC）：`drv: net: ethernet: stmmac fix for jl2xx1 phy`

第二个提交只增加：
- stmmac DMA reset 前 1500 ms delay；
- MDIO page 2627 / reg 25 写 0x1801；
- 回 page 0；
- 写 BMCR 0x8000 触发 PHY software reset。

它没有检测 PHY ID。也就是说，提交标题虽明确指向 JL2xx1，代码却放在通用 STMMAC 初始化路径中，对正常注册的任意外接 PHY 都会执行，不只对 JL2xx1 执行。

## 2. JL2xx1 对这组写入的解释

JLSemi 后续公开可检索的 JL2xx1 驱动头文件定义：

- page 2627，reg 25：`PHY CLK Control REG`
- bit 12：`CLK_SRC`
- bit 11：`CLK_125M_OUT`
- bit 3：`CLK_SSC_EN`
- bit 0：`CLK_OUT_PIN`

因此 `0x1801` 设置 bit12、bit11、bit0，随后执行 PHY soft reset。该序列在 JL2xx1 语境下是 PHY 时钟输出相关配置，而非一般的链路协商或 MAC/DMA 设置。

证据来源包括公开 JL2xx1 驱动头文件及其实现；目前没有取得 JLSemi 官方完整 datasheet，因此对 bit12 的电气选择含义不作超出宏定义的推断。

## 3. 与 Panther RTL8211F 的寄存器映射交叉核对

Panther 已知 PHY 为 RTL8211F。Realtek RTL8211F datasheet Rev. 1.4（2014-11-17）明确规定：

- page 0xA43 / reg 0x19（十进制 page 2627 / reg 25）是 PHYCR2；
- bits 13:12 是 CLKOUT SSC Capability Select；
  - 00：Normal CLKOUT；
  - 11：CLKOUT with SSC capability；
  - 其他值：Reserved；
- bit 11 是 CLKOUT Frequency Select，1=125 MHz；
- bit 0 是 CLKOUT Enable；
- datasheet 明确要求设置 PHYCR2 后执行 PHY reset（page 0 / reg 0 bit15）。

`0x1801` 的位分解：

- bit12=1，bit13=0 → bits[13:12]=01；
- bit11=1 → 125 MHz CLKOUT；
- bit0=1 → CLKOUT enable；
- 其余位为 0。

所以同一条硬编码写入若作用于 RTL8211F，按其 datasheet 字段解释，会把 PHYCR2 的 CLKOUT SSC capability 字段设为 `01`，而 datasheet 将该编码列为 Reserved；同时设置 125 MHz CLKOUT 和 CLKOUT enable。随后软件复位符合 datasheet 对 PHYCR2 设置的 reset 要求。

**重要限定：** 这证明该值对 RTL8211F 并非一个可直接解释为“JL2xx1 时钟配置”的等价操作；但 datasheet 把编码标为 Reserved，不足以证明 RTL8211F 一定故障、锁死或时钟输出一定异常。保留编码的实际硅片行为未知，需实测或厂商确认。

## 4. 1500 ms delay 的性质

原始 6.1.116 commit 中的 `msleep(1500)` 是无条件放在 `stmmac_init_dma_engine()` 中的，并没有 PHY ID 判断。

另一个公开 stmmac Kconfig 版本曾提供 `STMMAC_JL2XX1` 选项，其帮助文本明确描述“只在发现 JL2XX1/JL2101 PHY IDs 时延迟 1.5 秒，其他 PHY 不受影响”。这说明“仅对 JL PHY 延时”是后来可见的一种更窄化实现意图；但不能把该 Kconfig 行为倒推成 6.1.116 当前无条件代码已经具有 PHY ID 过滤。

对 Panther RTL8211F 而言，116 的 1.5 秒 delay 确实每次成功 interface open 都执行，但其原始目的指向 JL PHY 的初始化等待。它是否对 RTL8211F 有益，目前没有证据。

## 5. 本轮结论

### 已确认

1. workaround 的提交上下文明确是 JLSEMI JL2xx1 PHY：JL2xx1 驱动提交后约 68 秒，紧接着加入 stmmac workaround。
2. 这组 MDIO 操作在 JL2xx1 驱动资料中对应 page 2627 / reg25 的 PHY 时钟控制。
3. 6.1.116 实际代码没有 PHY ID 条件，因此 Panther RTL8211F 也会进入这条通用写入路径。
4. RTL8211F 的相同 page/reg 是 PHYCR2；写入值 0x1801 会将其 CLKOUT SSC Capability 字段设为 01，而该编码在 Realtek datasheet 中标为 Reserved。
5. 最后的 BMCR soft reset 符合 RTL8211F datasheet 对 PHYCR2 配置后执行 reset 的要求。

### 未确认

1. Panther 116 实机上的 PHYCR2 写入事务是否成功；
2. RTL8211F 实际硅片对 reserved encoding 01 的响应；
3. 该写入是否改变 Panther 实际 CLKOUT / RXC 时钟行为；
4. 该写入是否与 DHCP Discover 不出机或 TX/RX 计数异常存在因果关系；
5. 1500 ms delay 对 RTL8211F 是否有任何积极效果。

### 对回归调查的判断

这条 JL2xx1 workaround 仍然是值得重视的 116 与后续版本差异，但不能再简单称为“116 对 Panther 做了 PHY 优化”。

更准确的表述：

> 116 无条件执行了一段原本紧邻 JL2xx1 驱动提交加入、用于 JL2xx1 PHY 时钟配置/初始化的通用 stmmac workaround。由于 Panther 实际使用 RTL8211F，同一寄存器地址和值在 RTL8211F 上具有不同的寄存器语义，并命中 datasheet 标记为 Reserved 的字段编码。它可能是 116 与后续版本行为差异的重要线索，但当前没有证据证明它是 116 网络正常的原因，或证明该 reserved encoding 对 RTL8211F 有害。

**不建议把四次写入直接移植回 6.12。** 下一步应继续静态核对 RTL8211F PHY driver 的初始化路径：它是否会在 PHY attach/config_init 阶段重写 PHYCR2、是否会读回/修改这些字段，以及 Linux 6.1.116 当时实际绑定的是哪个 PHY driver。若历史 dmesg 能确认 RTL8211F 的 PHY ID/driver bind，则可用现有记录完成，不重复实机测试。
