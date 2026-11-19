# Panther X2：6.1.116 RTL8211F PHY CLKOUT workaround 与 6.1.174/6.12 回归核查（2026-11-19）

## 1. 本轮目标与更正

沿用 2026-11-18 报告确定的最高优先级差异：6.1.116 中存在、6.1.174-rk35xx 与 6.12.81 中缺失的 JL2xx1 STMMAC workaround。本轮核对原始补丁、Panther PHY ID、RTL8211F datasheet 的 PHYCR2 定义及代码执行条件。

同时更正 2026-11-19 前一份报告对 GMAC clock delay 的优先级判断：仓库 2026-11-17 Ethernet source audit 第 37 节已追踪 upstream generic gmac_clk_enable() 历史，确认 5ms 在 upstream 重构前就存在，重构提交保留了该 5ms；6.12 vendor 分支的 100–200µs 是后续 vendor 分支差异。同一报告也已确认 Panther GMAC DT 没有 rockchip,csu / rockchip,csu-names，CSU handle 取值失败后置 NULL，helper 对 NULL no-op。因此 CSU disable 和等待时间差异不能作为已证实硬件时序回归。本报告将这条方向降级。

## 2. 原始 workaround commit

源 commit：unifreq/linux-6.1.y@49b5f340f346cc9a5b777499fce46150b691b70e，标题为 drv: net: ethernet: stmmac fix for jl2xx1 phy，日期 2022-12-24。

该补丁增加两项行为：

1. 在 stmmac_init_dma_engine() 执行 stmmac_reset() 前插入 msleep(1500)。
2. 在 stmmac_mdio_register() 中，MDIO bus 注册成功、fixed-link 检查之后，PHY node/mdio node early-exit 之前，插入以下写入：

```c
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

其操作为：PHY 地址 0；Page Select reg31=2627（0x0a43）；Page 0xa43 reg25 写 0x1801；切回 page 0；BMCR reg0 写 0x8000 触发 software reset。补丁没有按 PHY ID 或 compatible 判断 JL2xx1，而是通用 STMMAC MDIO 注册路径中的无条件写入（fixed-link 提前跳过除外）。

## 3. Panther 确实命中该写入

已有实机基线确认 Panther 使用 RTL8211F，PHY ID 0x001cc916，MDIO 地址 0，RGMII，clock_in_out=input，驱动日志为 clock input from PHY。

在 6.1.116 精确源码 unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e 的 stmmac_mdio_register() 中，四次写入位于 fixed-link 检查之后、phy_node/mdio_node early-exit 之前。因此 Panther 有 PHY node 不会跳过写入，6.1.116 正常启动时确实会对真实 RTL8211F 地址 0 执行这组操作。

6.1.174 高置信度源码候选 ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633，以及 6.12.81 精确构建源码 ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c，均没有这四次写入；两者的 stmmac_init_dma_engine() 也没有 1500ms 延时。6.1.174 的源码映射仍是高置信度候选，非已取得 Actions job 完整日志的绝对证明；6.12.81 构建来源已由仓库既有报告锁定。

## 4. RTL8211F datasheet 对 PHYCR2 的定义

Realtek RTL8211F(I)-CG / RTL8211FD(I)-CG datasheet 将 Page 0xa43、Register 0x19（十进制 25）定义为 PHYCR2。

相关字段：
- bit 11：CLKOUT Frequency Select，0=25MHz，1=125MHz。
- bit 0：CLKOUT Enable，1=使能 CLKOUT pin 输出。
- bit 13:12：CLKOUT SSC Capability Select，00=Normal CLKOUT，11=CLKOUT with SSC capability，其他值保留。
- datasheet 明确注明：设置 PHYCR2 后应执行 PHY reset（Page 0 / Reg 0 / bit 15）。

所以 0x1801 中可识别的有效位至少包括 bit11=1（选择 125MHz CLKOUT）和 bit0=1（使能 CLKOUT）。但 bit12=1 使 SSC capability 字段成为 01，而 datasheet 将其标记为 reserved。不能把整个 0x1801 简化解释成单纯的 CLKOUT=125MHz enable；bit12 的含义尚未证实，可能与特定芯片修订或旧版 vendor 设置有关。

## 5. 为什么这条线索与 Panther 高度相关，但仍未定案

Panther 的配置明确为 clock input from PHY。PHYCR2 中 bit11/bit0 控制 PHY CLKOUT 的 125MHz 选择与输出使能。因此 6.1.116 workaround 至少有一个与 Panther PHY 时钟输入拓扑直接相关的潜在作用：在 PHY reset 后明确配置 RTL8211F 的 125MHz CLKOUT。

但 RTL8211F datasheet 对 bit11 和 bit0 的默认值也都列为 1，即默认已选择 125MHz 并使能 CLKOUT。因此删除这次写入并不自动等于 CLKOUT 被关闭。可能影响仍需核实的因素包括 bit12 reserved 设置、不同 silicon revision 的默认行为、bootloader 是否先写过 PHYCR2，以及 PHY reset 前后的寄存器状态。

当前最稳妥判断：这组写入与 Panther 的 PHY 时钟输入拓扑直接相关，值得优先核实其真实效果；但尚不能认定缺失写入必然关闭 CLKOUT。

## 6. 1500ms 延时应单独看待

同一 commit 还在 DMA reset 前加入 1500ms 等待，但补丁没有注释说明原因，也没有轮询 PHY status 或 clock-ready。PHYCR2 写入 + BMCR reset 是直接改变 PHY 配置；DMA reset 前等待只是延后 MAC DMA reset。两者是同一 commit 的两项改动，不能先验地当作同一机制。应先解析 PHYCR2 写入的影响，再单独研究 1500ms 是否只是 JL2xx1 特定 workaround 的额外等待；目前不建议直接移植 1500ms 到 Panther。

## 7. 当前结论

已确认：
1. 6.1.116 正常版本在 Panther MDIO 地址 0 上执行 Page 0xa43 / Reg 0x19 = 0x1801，随后触发 PHY soft reset。
2. 写入位于 MDIO 注册后、phy_node/mdio_node early-exit 之前，Panther 有 PHY node 不会跳过。
3. 6.1.174 与 6.12.81 当前源码候选均没有这段写入。
4. Panther PHY ID 为 RTL8211F 0x001cc916，地址 0；PHY 模式 RGMII，clock input from PHY。
5. RTL8211F datasheet 将 Page 0xa43 / Reg 0x19 定义为 PHYCR2，bit11/bit0 控制 125MHz CLKOUT 选择和输出使能。
6. 0x1801 还设置 datasheet 标记 reserved 的 bit12；其语义未知。
7. datasheet 对 bit11 与 bit0 的默认值均列为 1，因此缺少写入不等于已证明 CLKOUT 被关闭。

最高价值待验证问题：6.1.116 的 PHYCR2=0x1801 写入是否改变 Panther RTL8211F 的 CLKOUT/PHY 状态，以及 6.1.174/6.12 启动时实际 PHYCR2 值是什么？

## 8. 下一步（先只读静态，不改设备）

1. 检查 6.1.116 与 6.12.81 的 Realtek PHY driver / generic PHY probe 是否在 MDIO 注册后又改写 PHYCR2 或 EEE/CLKOUT。
2. 核对 RTL8211F-CG 与 Panther 当前实物型号/修订对应的数据手册，尤其 bit12 的定义。
3. 从已有 U-Boot 源码和启动日志中查找是否也有 Page 0xa43 / Reg 0x19 写入。
4. 结合 clock_in_out=input 与外部固定 125MHz clock 节点，核实 PHY CLKOUT 是否确为 GMAC clock input 的物理来源。
5. 若静态链路无法闭环，再提出一次只读 PHYCR2 MDIO 回读。只有用户明确同意后才操作设备；不写 PHY、不重启链路、不改变接口配置。

## 9. 参考链接

- 原始 JL2xx1 workaround commit：https://github.com/unifreq/linux-6.1.y/commit/49b5f340f346cc9a5b777499fce46150b691b70e
- 6.1.116 exact source：https://github.com/unifreq/linux-6.1.y/tree/5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174 source candidate：https://github.com/ophub/linux-6.1.y-rockchip/tree/c2f148dece4b67ebd30aefad1bdd1990f41e5633
- 6.12.81 exact source：https://github.com/ophub/linux-6.12.y-rockchip/tree/661b2d8bf1284556f8876d5ed5fb80c64b22f94c
- RTL8211F datasheet, PHYCR2：https://www.ic-golden.com/wp-content/uploads/2024/08/rtl8211fi-cg-datasheet.pdf
- RTL8211F PHYCR2 另一份资料：https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf

## 10. 关联报告

- 6.1.116 → 6.1.174 → 6.12 共享 GMAC 回归线索审计（2026-11-18）。
- Panther 6.1.116 完整软件基线采集（Ethernet TX source audit 第 48 节）。
- Panther GMAC clock delay / CSU 方向审计（Ethernet TX source audit 第 37 节）。
- RTL8211F-CG 与 VD-CG 寄存器定义差异及 STMMAC RXC/DMA reset 线索（2026-11-19）。