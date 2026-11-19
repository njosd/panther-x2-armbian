# Panther X2：RTL8211F-CG / VD 型号区分与 STMMAC RXC/DMA reset 回归线索（2026-11-19）

## 1. 本报告纠正的研究方向

此前 2026-11-19 的 JL2xx1 workaround 报告主要按普通 RTL8211F-CG/FD-CG Rev.1.7 解释 Page 0xa43 Reg19 的 PHYCR2。继续回溯 Panther 既有报告和 Realtek 资料后，发现必须把普通 CG 与 VD-CG 分开：

- 普通 RTL8211F-CG：PHYCR2 位于 Page 0xa43、Reg19。
- RTL8211F-VD-CG：数据手册将 PHYCR2 列为 Page 0xa44、Reg17；CLKOUT 另在 Page 0xd05、Reg17 进行配置。
- Linux 主线 PHY 驱动也明确注释：RTL8211F(D)(I)-VD-CG 的 CLKOUT 配置使用未公开寄存器页，不像其他 RTL8211F 型号通过 PHYCR2。

因此，不能将普通 CG 数据手册的 PHYCR2/CLKOUT 解释直接套用于 VD-CG。

## 2. Panther 实物型号：目前证据不足以定为 VD-CG

回读既有 Panther 报告 `GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md`：

- 实机 Linux 日志及设备树把 PHY 识别为 RTL8211F，PHY 地址 0，RGMII；
- 报告第 15.5 节引用了另一台 RK3566 Home Assistant Green + RTL8211F-VD 的上游故障案例；
- 该报告没有提供 Panther 实物芯片完整顶标照片，也没有记录足以区分普通 CG 与 VD-CG 的 PHYID2 原始数值。

**关键纠正：** 既有报告中出现“RTL8211F-VD”是上游案例的型号，不是 Panther 实物型号已确认的证据。当前不能断言 Panther 使用 VD-CG，也不能断言它一定是普通 CG。

### 2.1 数据手册中的 PHYID2 区别

普通 RTL8211F(I)-CG / FD(I)-CG Rev.1.1 的 PHYID2 定义：
- OUI_LSB bits 15:10 = 110010
- Model Number bits 9:4 = 010001（二进制 0x11）
- Revision Number bits 3:0 = 0110

RTL8211F(I)-VD / FD(I)-VD Rev.1.0 的 PHYID2 定义：
- OUI_LSB bits 15:10 = 110010
- Model Number bits 9:4 = 000111（二进制 0x07）
- Sample classification bit 3 = 1 表示 MP、0 表示 ES
- Revision Number bits 2:0 = 000（数据手册默认/描述值）

因此，**若有实机 PHYID2 原始回读值，可以比“Linux 日志只显示 RTL8211F”更有区分力。** 但需要注意 Linux PHY driver 的 match 表和 PHYID mask 可能把型号名称归并，不能只看驱动打印的产品名。

来源：
- 普通 CG Rev.1.1 数据手册，PHYID2： https://file3.dzsc.com/datasheet/22/04/14/150904366.pdf
- VD-CG Rev.1.0 数据手册，PHYID2： https://atta.szlcsc.com/upload/public/pdf/source/20231027/A9F59B38F0F9CFDEC1A434DCBD1C2D1B.pdf

## 3. 普通 CG 与 VD-CG 的 CLKOUT 配置不可混用

普通 CG Rev.1.7：
- PHYCR2 = Page 0xa43, Reg19
- bit11 选择 CLKOUT 125/25MHz
- bit0 CLKOUT enable
- bit1 RXC enable
- bit5 PHY-mode EEE enable
- bits13:12 CLKOUT SSC capability

VD-CG Rev.1.0：
- CLKOUT 另有独立章节 7.17；
- Page 0xd05, Reg17：
  - 写 0x0e02：关闭 CLKOUT，选择 125MHz；
  - 写 0x0c02：关闭 CLKOUT，选择 25MHz；
  - 写 0x0f02：开启 CLKOUT，选择 125MHz；
  - 写 0x0d02：开启 CLKOUT，选择 25MHz。
- VD 数据手册 PHYCR2 列在 Page 0xa44, Reg17，而非普通 CG 的 Page 0xa43, Reg19。

Linux 主线 `drivers/net/phy/realtek/realtek_main.c` 的明确注释：
`RTL8211F(D)(I)-VD-CG CLKOUT configuration is specified via magic values to undocumented register pages. Unlike other PHY models, CLKOUT configuration does not go through PHYCR2.`

来源：
- VD-CG 数据手册 7.17、PHYCR2 表： https://atta.szlcsc.com/upload/public/pdf/source/20231027/A9F59B38F0F9CFDEC1A434DCBD1C2D1B.pdf
- Linux 主线 Realtek PHY 驱动： https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/077ab8985ee278c3d8618182d335b0f0cd919e16/drivers/net/phy/realtek/realtek_main.c

## 4. 新发现的、与 RK3566 + RTL8211F-VD 高度贴近的 STMMAC 回归

上游 Linux commit：
`06232cb44bc8e81adc2f1d40a01bed830b607ea2`
标题：`net: stmmac: resume PHY before hardware setup when opening the interface`
作者 Stefan Agner，2026-08-03；提交进入上游时间 2026-08-04。

提交说明明确描述：
1. 一个先前提交将 PHY handling 从 `__stmmac_open()/release()` 移出；
2. MTU change 时 `__stmmac_release()` 调用 `phylink_stop()`，在 WoL 未启用时会让 PHY 进入 BMCR power-down；
3. 随后的 `__stmmac_open()` 在 `stmmac_hw_setup()` 内执行 DMA software reset；
4. 但 `phylink_start()` 要等 hardware setup 后才恢复 PHY；
5. IEEE 802.3 允许 power-down PHY 停止 RX clock，而 STMMAC DMA software reset 需要 RX clock 运行（phylink config 设置 `mac_requires_rxc`）；
6. 因此 RK3566 + RTL8211F-VD + RGMII 的案例在 runtime MTU change 时出现 `Failed to reset the dma`，接口重新打开失败；
7. 修复是在 `__stmmac_open()` 的 hardware setup 前调用 PHY resume preparation，使 RX clock 在 DMA reset 前恢复。

来源：
- 上游 commit： https://code.googlesource.com/linux/torvalds/linux/+/06232cb44bc8e81adc2f1d40a01bed830b607ea2
- commit patch： https://code.googlesource.com/linux/torvalds/linux/+/06232cb44bc8e81adc2f1d40a01bed830b607ea2%5E%21/
- 同一 patch 邮件说明： https://lists.openwall.net/netdev/2026/08/03/147

### 4.1 对 Panther 当前故障的适用性判断

这条上游回归与 Panther 的平台（RK3566）、PHY 家族（RTL8211F）、RGMII 接口完全相邻，且机制直接涉及 RXC 时钟与 STMMAC DMA reset，必须列为高优先级候选。

但不能直接认定为 Panther DHCP 故障根因：
- 上游案例触发条件是运行中 MTU change 导致接口关闭/重新打开；
- Panther 既有报告记录 NetworkManager profile MTU=auto、运行时 MTU=1500，但尚无证据表明启动时实际发生了 MTU change 或接口 reopen；
- Panther 既有日志片段未看到 `Failed to reset the dma`，但不是完整启动日志审计；
- 该补丁是 2026-08 上游提交，必须先核实 Panther 正在运行的 6.12.81-rk35xx-ophub 是否包含该修复或其等效 backport；
- 不能仅凭版本号猜测是否包含。

### 4.2 与 JL2xx1 workaround 的关系

两者涉及相邻但不同的时间点：
- JL2xx1 workaround 的 1500ms delay 在 `stmmac_init_dma_engine()` 中，DMA reset 前；
- 其四次 MDIO 写入在 MDIO bus 注册之后、PHY attach/后续扫描之前；
- 2026-08 上游 RXC 修复针对 PHY 已因 `phylink_stop()` power-down 后，接口 reopen 时 DMA reset 前没有及时 resume PHY。

它们不能混为同一个补丁，也不能据此推断 1500ms workaround 等同于 PHY resume。

## 5. 当前结论（更新）

### 已由外部源码/数据手册确认
1. 普通 CG 与 VD-CG 的 CLKOUT 配置路径不同。
2. VD-CG 的 PHYCR2 位于 Page 0xa44 Reg17，CLKOUT 使用 Page 0xd05 Reg17。
3. Linux 主线 PHY 驱动明确区分 VD-CG 的 CLKOUT 配置。
4. 2026-08 上游修复确认 RK3566 + RTL8211F-VD + RGMII 存在 PHY power-down 后 RXC 停止，导致 DMA reset 超时的真实回归场景。
5. 修复要求在 DMA hardware setup 前恢复 PHY。

### Panther 实机仍未确认
1. Panther 的 PHY 是普通 CG 还是 VD-CG；
2. Panther PHYID2 原始值；
3. Panther 是否在启动时触发 MTU change / link down-up / ndo_open reopen；
4. Panther 6.12.81 二进制是否含 commit 06232cb44bc8 或等效修复；
5. Panther 是否实际出现 DMA reset timeout，只是此前日志筛选未覆盖完整日志。

## 6. 下一步最小核查顺序

1. **先做源码/发布包静态核对：** 在实际 6.12.81-rk35xx-ophub 对应源码/补丁集中查找 `phylink_prepare_resume`、`__stmmac_open` 与 commit 06232cb44bc8 的等效改动。必须锁定实际构建来源，不能用当前 Linux 主线替代运行内核。
2. **回读历史只读日志：** 从已上传 UART / dmesg 记录检查启动时是否有接口 reopen、MTU change、DMA reset failure；不要求用户重跑。
3. **确认 PHY 型号：** 优先从历史 PHYID2 原始值、板级 BOM 或芯片顶标照片确认。若缺少，只提出只读 MDIO 读取建议，不主动读写设备。
4. 只有以上证据显示实际存在 suspend/reopen 与 RXC/DMA reset 时序问题，才把该补丁提升为 Panther 主故障候选；否则继续保持为条件性线索。

不进行 PHY 寄存器写入、PHY reset、MTU 修改、接口重启、驱动重载或网络配置更改。

## 7. 相关仓库报告
- [JL2xx1 workaround 与 RTL8211F 寄存器语义审计](./PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md)
- [JL2xx1 workaround 数据手册修订差异与补丁作用范围](./PANTHER-X2-JL2XX1-WORKAROUND-DATASHEET-REVISION-AND-PATCH-SCOPE-20261119.md)
- [GMAC/DHCP 与 TF U-Boot 启动链调查（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)
