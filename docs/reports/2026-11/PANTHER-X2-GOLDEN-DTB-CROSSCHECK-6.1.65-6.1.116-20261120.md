# Panther X2：两条黄金基准的 Linux GMAC DTB 交叉核对（2026-11-20）

## 1. 本轮目标与范围

按用户要求，以 6.1.65 原始镜像和 6.1.116 正常实机为两条黄金基准，逐项比较 Linux GMAC1 设备树配置，判断 DTB 是否是优先替换候选。

只读使用：
- 原始 6.1.65 IMG 中 BOOT 分区提取的 `rk3566-panther-x2.dtb` 及此前已归档解析结果；
- 6.1.116 已归档磁盘 DTB、runtime FDT、启动日志；
- 6.1.116 精确源码端点 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` 的 Panther DTS、RK356x SoC DTSI、pinctrl DTSI 和 clock binding。

没有读取或写入 Panther 实机，没有启动故障内核，没有修改 DTB/驱动/配置。

## 2. GMAC 主节点语义对照

| 项目 | 6.1.65 原始 IMG DTB | 6.1.116 正常基线 | 判断 |
|---|---|---|---|
| GMAC 节点 | `ethernet@fe010000` | runtime FDT 同路径 | 一致 |
| compatible | `rockchip,rk3568-gmac`, `snps,dwmac-4.20a` | runtime FDT 相同 | 一致 |
| status | okay | runtime FDT 为 okay | 一致 |
| reg | `0xfe010000 / 0x10000` | runtime FDT 相同 | 一致 |
| phy-mode | rgmii | runtime FDT 为 rgmii | 一致 |
| clock_in_out | input | runtime FDT 为 input；启动日志打印 clock input from PHY | 一致 |
| TX/RX delay | `0x30 / 0x10` | runtime FDT 与启动日志均为 `0x30 / 0x10` | 一致 |
| PHY | MDIO `ethernet-phy@0`，reg=0 | runtime FDT reg=0；实机 PHY 为 RTL8211F、地址0 | 一致 |
| pinctrl 方案 | 六组 gmac1m0 | 6.1.116 runtime FDT 引用六组 pinctrl；已有实机记录确认使用 M0 | 一致 |

上述 6.1.65 字段来自原始 IMG 内 DTB 的直接解析；6.1.116 的 runtime 字段来自已归档 FDT/启动日志。它们不是对两个 DTB 文件做逐字节比较。

## 3. Pinctrl 引脚与电气配置

6.1.65 原始 DTB 已解析出的六组 bank/pin/mux：

| pin group | bank/pin/mux |
|---|---|
| gmac1m0-miim | (3,20,3), (3,21,3) |
| gmac1m0-tx-bus2 | (3,13,3), (3,14,3), (3,15,3) |
| gmac1m0-rx-bus2 | (3,9,3), (3,10,3), (3,11,3) |
| gmac1m0-rgmii-clk | (3,7,3), (3,6,3) |
| gmac1m0-clkinout | (3,16,3) |
| gmac1m0-rgmii-bus | (3,4,3), (3,5,3), (3,2,3), (3,3,3) |

6.1.65 DTB 的 pin config 已展开：
- TXD0/TXD1：drive level 2；TXEN：pull-none；
- TXD2/TXD3：drive level 2；
- TXCLK：drive level 1；
- 其余列出的 GMAC 引脚为 pull-none。

6.1.116 精确源码端点的 `rk3568-pinctrl.dtsi` 对应定义逐项相同：
- miim：GPIO3_C4/C5；
- TX bus2：GPIO3_B5/B6/B7；
- RX bus2：GPIO3_B1/B2/B3；
- RGMII clock：GPIO3_A7/A6；
- clkinout：GPIO3_C0；
- RGMII bus：GPIO3_A4/A5/A2/A3；
- mux 均为 3，pull/drive-strength 设置与 6.1.65 已提取值一致。

因此两条正常线的 GMAC pinmux 不是两套不同方案，而是同一组 M0 引脚和相同的配置值。该结论是 DTB 数据与 6.1.116 源码的语义交叉核对；6.1.116 runtime FDT 的完整 pinconf 原始 cell 未在既有采集文本中保存，不能声称已完成两份二进制 DTB 的全属性逐字节比较。

## 4. GMAC clock parent 语义

6.1.65 原始 DTB 中：
- `assigned-clocks` 为 CRU clock IDs `0x189`、`0x187`、`0x186`；
- `assigned-clock-parents` 对应 `0x187`、`0x186`，第三个 parent 为 fixed-clock phandle；
- fixed-clock 节点为 125MHz 的外部 `gmac1_clkin`。

通过 6.1.116 精确源码端点的 `rk3568-cru.h` 交叉解码：
- `0x186 = 390 = SCLK_GMAC1`
- `0x187 = 391 = SCLK_GMAC1_RGMII_SPEED`
- `0x189 = 393 = SCLK_GMAC1_RX_TX`

6.1.116 Panther DTS 对应的赋值与父链源码定义相同：
`SCLK_GMAC1_RX_TX -> SCLK_GMAC1_RGMII_SPEED -> SCLK_GMAC1 -> gmac1_clkin(125MHz)`。

6.1.116 既有运行时 clock 记录还确认 GMAC1 相关时钟为预期 125MHz。该频率记录来自 Linux 接管后的软件时钟树，不是对物理引脚波形的测量。

## 5. Reset / PHY supply 交叉核对边界

6.1.65 原始 DTB 已确认：
- `snps,reset-gpio` 指向 GPIO3 bank 的 line 1，原始 flags cell 为 1；
- `phy-supply` 指向名为 `vcc_3v3` 的 PMIC regulator。

6.1.116 精确 Panther DTS 采用 GPIO3_PA1、active-low reset，reset delays 为 `<0 20000 100000>`，PHY supply 同样指向 `vcc_3v3`。这支持板级意图相同；但原始 6.1.65 DTB 既有解析记录尚未保存 reset-delays-us 的实际 cell，因此该项暂列为源码/配置意图相符，不列为原始 DTB 字节级已证实。

## 6. 阶段结论

**已验证 / 高置信度：**
1. 两条黄金基准的 GMAC 主节点均指向 fe010000、RK3568 DWMAC4.20a IP、plain RGMII、clock input、TX/RX delay 0x30/0x10、PHY address 0。
2. 两条黄金基准采用相同的 GMAC1 M0 pin groups；6.1.65 原始 DTB 的引脚和 drive/pull 值与 6.1.116 精确源码定义一致。
3. 两条黄金基准的 GMAC1 clock parent 设计均使用 SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED、SCLK_GMAC1，并以外部 125MHz gmac1_clkin 为 parent。
4. 6.1.116 正常实机 runtime FDT、启动日志和链路结果确认该配置确实进入正常运行路径。

**尚未验证：**
- 两份 DTB 的完整二进制逐字节差异；
- 6.1.65 原始 DTB reset delay cell 与 6.1.116 完整 runtime pinconf cell 的逐项对照；
- 两条黄金基准完整 DTB 中所有非 GMAC 节点的差异。

**判断：** 当前没有发现能解释 TX 回归的、只存在于故障版本而两条黄金基准共同不存在的 GMAC Linux DT 配置差异。故不把“替换 6.1.65 DTB”列为第一轮实验；目前证据反而显示两条正常线的 GMAC 配置设计高度一致。该项作为“未发现有效差异”收口，不等于整个 DTB 或启动链已证明没有问题。

## 7. 下一项

转向四版本资产矩阵中的下一项：确认 6.1.65 原始镜像内的 kernel Image、modules、initramfs 与 6.1.116 正常基线的对应关系和可替换边界；随后再与 6.1.174、6.12.81 的发布资产对照。仍然先静态盘点，不制作补丁、不启动故障内核、不刷写或修改设备。
