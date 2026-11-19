# Panther X2：P1 四次 MDIO 写入语义审计与收口（2026-11-19）

## 范围与约束

仅审查公开源码、历史讨论和 PHY 厂商数据手册。未进行 Panther X2 实机操作、MDIO 读写、PHY reset、接口重启或系统修改。

## 1. JLSemi 原始来源链

已核实以下公开来源：

- 6.1.116 工作树引入提交：`unifreq/linux-6.1.y` commit `49b5f340f346cc9a5b777499fce46150b691b70e`，标题 `drv: net: ethernet: stmmac fix for jl2xx1 phy`，日期 2022-12-24。
- 父提交：`22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`，标题 `drv: net: phy: Add JLSEMI JL2xx1 driver`。
- 该提交对 `stmmac_mdio.c` 增加四次写入；同时在 `stmmac_main.c` 增加 DMA reset 前 1500ms 延时。两项改动应分开判断。
- 更早的公开来源是 Lean OpenWrt commit `coolsnowwolf/lede@b889ab8789155707f5a73f69d87f33d18e33bb78`，补丁 `target/linux/rockchip/patches-5.19/801-fix-stmmac_mdio.patch`。补丁中只有四次写入，没有逐寄存器注释或解释。
- CoreELEC/linux-amlogic PR #13 的 2023-01-03 讨论中，原作者 7Ji 明确表示这些写入来自 Lean OpenWrt 补丁，最初来自其获得的 JLSemi 源代码，但作者当时也不知道具体数值的确切含义。
- 同一讨论中，提问者表示联系到 JLSemi FAE 并收到资料，但 GitHub 页面只呈现为图片附件占位符，没有可检索的文字内容。本次无法从该公开页面核验附件内容，也没有找到可公开验证的 JLSemi 原始驱动文件/寄存器说明来证明四个数值的原始设计意图。

来源：
- https://github.com/unifreq/linux-6.1.y/commit/49b5f340f346cc9a5b777499fce46150b691b70e
- https://github.com/coolsnowwolf/lede/commit/b889ab8789155707f5a73f69d87f33d18e33bb78
- https://github.com/CoreELEC/linux-amlogic/pull/13

## 2. 四次写入与 RTL8211F-CG 数据手册

6.1.116 的执行序列：

```c
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

Realtek RTL8211F(I)-CG / RTL8211FD(I)-CG Datasheet Rev.1.4（2014-11-17）可确认：

- Page 0xA43 / Reg 0x19（十进制 25）是 PHYCR2。
- PHYCR2 Bit 13:12：CLKOUT SSC Capability Select；00=Normal CLKOUT，11=CLKOUT with SSC capability，其他值 Reserved。
- Bit 11：CLKOUT 频率，0=25MHz，1=125MHz。
- Bit 7：CLKOUT SSC Enable。
- Bit 5：PHY-mode EEE Enable。
- Bit 3：SYSCLK SSC Enable。
- Bit 1：RXC clock output enable。
- Bit 0：CLKOUT output enable。
- 手册明确要求设置 PHYCR2 后执行 PHY reset。

`0x1801 = (1<<12) | (1<<11) | (1<<0)`。按手册逐位解释：

| 位 | 值 | 解释 |
|---|---:|---|
| 13:12 | 01 | Reserved 组合；厂商手册未定义其行为 |
| 11 | 1 | 选择 CLKOUT 125MHz |
| 7 | 0 | 不使能 CLKOUT SSC |
| 5 | 0 | 清除 PHY-mode EEE enable |
| 3 | 0 | 不使能 SYSCLK SSC |
| 1 | 0 | 清除 RXC clock output enable |
| 0 | 1 | 使能 CLKOUT |

所以该写入不是单纯“打开 125MHz CLKOUT”：它还清除了 RXC enable、PHY-mode EEE enable，并写入了手册标记为 Reserved 的 bits 13:12=01。不能把该值视为有完整厂商保证的 RTL8211F 标准配置。

数据手册：
https://atta.szlcsc.com/upload/public/pdf/source/20190902/C187932_1913F3711F05FE1324DF2946D70D648D.pdf

## 3. PHY 地址 0 的广播语义

RTL8211F 数据手册第 7.8 节说明：

- 常规 PHYAD strap 地址范围为 0x01–0x07。
- MAC 以 PHY address=0 发出的 MDIO 命令属于 broadcast。
- RTL8211F 默认允许响应该广播；可通过 Page 0xA43 / Reg 24 / Bit 13 禁止。
- Page 0xA43 / Reg 24 / Bit 6 另有 PHYAD=000 时记住首个非零 PHY 地址的功能。

因此，这四次 addr=0 写入不能简单视为对“Linux 设备树 reg=0 的一个 PHY”的单播操作。凡是总线上实际存在且接受地址 0 广播的 PHY，都可能受到相应写入影响；最后的 BMCR reset 也可能触发多个响应 PHY 的复位。具体受影响设备集合取决于总线拓扑和各 PHY 的广播响应状态，当前无硬件拓扑证据，不作扩大推断。

## 4. 最后一次 BMCR software reset

`Reg 0 = 0x8000` 设置 BMCR Bit 15，触发 PHY software reset。

Realtek 数据手册明确写明：
- 软件复位后 BMCR、BMSR 返回默认值；
- 操作可能改变 PHY 内部状态和物理链路状态；
- PHYCR2 配置后应执行 PHY reset。

手册没有在该处声明 PHYCR2 会被软件 reset 清零。因此：
- 不能说最后一次 reset 必然抹掉前面的 PHYCR2 写入；
- 更符合手册文字的解释是该 reset 用于使 PHYCR2 设置生效；
- 但不能仅凭数据手册推断本次特殊值（尤其 Reserved bits=01）复位后的实际硅片行为和最终回读值。

## 5. RTL8211F 与 JLSemi 的兼容性边界

2026 年公开 Linux netdev 补丁讨论提供了新的旁证：JLSemi JL2101/JL2121 与 RTL8211F 在多个 paged register、RGMII delay、状态和 LED 寄存器方面存在兼容/共用关系。但这些资料讨论的是 JL21xx 对 RTL8211F 驱动寄存器模型的兼容性，并没有证明本次旧 workaround 的 `0xA43:0x19=0x1801` 对 JL2XX1 的特定目的，更不能证明该保留位组合在 RTL8211F-CG 上有定义。

参考：
- https://lists.openwall.net/netdev/2026/10/21/159
- https://lists.openwall.net/netdev/2026/11/05/576

## 6. P1 结论与收口

### 已确认
1. 四次写入在 6.1.116 的 `stmmac_mdio_register()` 中，MDIO bus 注册后、后续 PHY node early-exit 路径之前执行。
2. 代码源流可追溯到 Lean OpenWrt 补丁，讨论作者称其最初来自 JLSemi 提供的代码。
3. RTL8211F-CG 的对应寄存器是 PHYCR2，`0x1801` 的位含义可按 Realtek 数据手册解码。
4. RTL8211F 的 PHY 地址 0 具有广播语义。
5. BMCR reset 是 PHYCR2 设置后手册要求的步骤；手册只明确 BMCR/BMSR 返回默认值，没有说明 PHYCR2 被清零。

### 证据不足
1. JLSemi 原始驱动/原始寄存器初始化代码及每个值的厂商解释未能取得可公开核验的文本证据；FAE 附件仅在 PR 页面显示图片占位符。
2. 没有厂商资料定义 RTL8211F PHYCR2 bits 13:12 的 Reserved 值 01 的行为。
3. 没有资料证明该四次写入原本就是为 RTL8211F-CG 设计，或证明其在 Panther 的实物 PHY 上产生预期效果。
4. 没有 Panther 实机写入成功、reset 后 PHYCR2 回读、CLKOUT/RXC 实际状态证据；本轮按用户要求不进行实机操作。

### 决策
**P1 到此收口，结论为“寄存器语义部分已解码，但 JLSemi 原始意图及 RTL8211F 对保留值的行为证据不足”，不再沿这四次写入继续猜测。**

按既定路线转入 P2：RTL8211F PHY 时钟输入链及 U-Boot/Linux 初始化交接。保留本报告作为后续排查基线，不重复本支线的源码与手册解码工作。
