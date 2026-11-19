# Panther X2：RTL8211F PHYCR2=0x1801 的完整位域影响（2026-11-19）

## 1. 本轮重要更正

此前对 JL2xx1 workaround 写入值 `0x1801` 的解释不完整。重新按 RTL8211F datasheet Table 38 核对完整 PHYCR2 位域后发现：

**0x1801 不只是设置 bit12、bit11、bit0；它还会把 bit1（RXC Enable）清零。**

这是本轮新增的关键事实，必须纳入后续判断。此前报告中只强调 CLKOUT 125MHz 和 CLKOUT enable，未指出 bit1 被清零，属于分析遗漏。

## 2. 0x1801 与 PHYCR2 默认位域对照

RTL8211F(I)-CG / RTL8211FD(I)-CG datasheet：
- Page 0xa43
- Register 0x19
- PHYCR2

`0x1801 = 0001 1000 0000 0001b`，对应：

| 位 | 字段 | 数据手册默认值 | 写入 0x1801 后 | 解释 |
|---|---|---:|---:|---|
| 13:12 | CLKOUT SSC Capability | 00 | 01 | 数据手册规定 00=Normal、11=SSC；01 reserved |
| 11 | CLKOUT Frequency Select | 1 | 1 | 125MHz |
| 7 | CLKOUT SSC Enable | 0 | 0 | 不启用 CLKOUT SSC |
| 5 | PHY-mode EEE Enable | 1 | 0 | **关闭 PHY-mode EEE** |
| 3 | SYSCLK SSC Enable | 0 | 0 | 不启用 SYSCLK SSC |
| 1 | RXC Enable | 1 | 0 | **关闭 RXC clock output** |
| 0 | CLKOUT Enable | 1 | 1 | 使能 CLKOUT |

注意：表中只列出与该写入相关的可定义字段；其他未置位字段按写入值为 0。RO/reserved 位不能据写值推断其硬件状态。

因此 0x1801 在 RTL8211F 上不是“只打开 125MHz CLKOUT”的单一设置，而是同时：
1. 选择 125MHz CLKOUT；
2. 保持 CLKOUT enable；
3. 令 CLKOUT SSC capability 字段为 reserved 编码 01；
4. 清除 RXC Enable；
5. 清除 PHY-mode EEE Enable。

## 3. 这使 workaround 的潜在影响比之前判断更大

Panther 的 PHY ID 为 RTL8211F `0x001cc916`，RGMII，PHY 地址 0。6.1.116 的 STMMAC workaround 对该 PHY 无条件执行：
```c
page 0xa43, reg 0x19 = 0x1801
page 0
BMCR = 0x8000
```

Realtek Linux PHY driver 后续的 `rtl8211f_config_init()` 只以 `BIT(0)` 为 mask 修改 PHYCR2，因此不会主动恢复 bit1、bit5、bit11、bit12。按软件读改写逻辑，bit1 和 bit5 不会被该函数重新置回 1。

**特别是 bit1 RXC Enable：** 数据手册将其定义为 RXC Clock Output Enabled，默认值 1；workaround 写入 0x1801 会清零该位。若该字段控制 Panther RGMII 接收时钟输出，则它理论上可能影响 MAC 接收时钟。但这与 6.1.116 已有成功网络基线形成反向证据，因此在没有明确区分 RXC 输出引脚/功能和 CLKOUT 引脚/功能之前，不能把它直接认定为故障原因。

bit5 PHY-mode EEE Enable 也被清零；但当前没有证据证明 Panther 的 EEE 状态与 RX/DHCP 故障存在因果关系。

## 4. 与 6.1.116 成功运行事实的矛盾必须保留

已知事实：
- 6.1.116 的 workaround 路径会发起 0x1801 写入；
- 6.1.116 的 RTL8211F config_init 不会主动恢复 bit1/bit5；
- 6.1.116 设备曾成功建立 1Gbps/Full link，且有正常网络基线；
- 6.1.174/6.12 没有这组 workaround 写入。

如果 0x1801 清除的 bit1 确实直接关闭 Panther RGMII RXC 时钟，那么它应当使 6.1.116 接收异常，而不是使其正常。因此至少有一个前提尚未闭环：
1. datasheet 的 RXC Enable 字段对应的并非 Panther GMAC 所需 RGMII RXC pin，或它控制的是另一条时钟输出；
2. PHY reset 后该字段被硬件恢复/重新采样；
3. 6.1.116 实机上最终寄存器值与软件写入值不同（例如 MDIO 写入未成功、PHY 型号/修订不同）；
4. 6.1.116 的成功网络基线与该写入之间存在未被当前记录捕获的其他配置因素。

不能选择其中任一项当作事实。

## 5. 对当前故障根因排序的影响

本轮不能据此宣布找到根因，但已把一个重要的测试目标从“只读 CLKOUT bits”扩展为完整 PHYCR2：

- bit12: SSC capability
- bit11: CLKOUT 频率
- bit5: PHY-mode EEE
- bit1: RXC output enable
- bit0: CLKOUT output enable

只读回读时必须保留整个 16-bit 原始值，不能只打印 bit0 或 bit11。

如果后续能安全执行只读 MDIO 读取，应分别记录：
1. PHY 识别 ID；
2. PHYCR2 原始值；
3. PHY BMCR/BMSR 状态；
4. 只读，不写寄存器、不触发 reset、不重新协商链路。

但不能在 6.1.116 与 6.12 之间直接比较一次运行态寄存器值，除非同时记录启动后所处阶段、是否已完成 PHY config_init、是否经历过接口 down/up，以及是否执行过 suspend/resume。

## 6. 当前建议

下一步先不再泛查 STMMAC。重点核对：
1. RTL8211F datasheet 中 RXC、CLKOUT 两种 clock output 的定义、引脚位置及用途；
2. Panther 板级原理图/PHY pin strap/GMAC 引脚连接，确认哪个输出真正连到 RK3566；
3. 6.1.116 实机历史记录是否有 PHYCR2 完整值或 RXC 时钟证据；
4. 若没有历史值，再决定是否需要用户授权的一次只读 PHYCR2 读取。

不建议在当前证据下修改 0x1801、尝试写 bit1 或移除 workaround。任何 PHY 写操作都会改变链路状态，必须先明确授权。

## 7. 来源

- RTL8211F(I)-CG / RTL8211FD(I)-CG datasheet, Table 38, PHYCR2, Page 0xa43 / Register 0x19:
  https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf
- 同版 datasheet 另一来源：
  https://www.ic-golden.com/wp-content/uploads/2024/08/rtl8211fi-cg-datasheet.pdf
- 6.1.116 原始 JL2xx1 workaround commit:
  https://github.com/unifreq/linux-6.1.y/commit/49b5f340f346cc9a5b777499fce46150b691b70e
- 6.1.116 RTL8211F PHY driver:
  https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/phy/realtek.c
- 6.12.81 RTL8211F PHY driver:
  https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/phy/realtek.c

## 8. 关联报告

- `PANTHER-X2-RTL8211F-CLKOUT-WORKAROUND-REGRESSION-20261119.md`
- `PANTHER-X2-RTL8211F-PHYCR2-EXECUTION-ORDER-AND-RESET-BOUNDARY-20261119.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`
