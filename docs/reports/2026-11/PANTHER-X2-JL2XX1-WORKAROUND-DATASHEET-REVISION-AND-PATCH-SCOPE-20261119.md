# Panther X2：JL2xx1 STMMAC workaround 的 PHY 数据手册修订差异与补丁作用范围（2026-11-19）

本报告补充并修正同日的：
`PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md`

## 1. 本轮最重要的修正：PHYCR2 bit 1 不能跨数据手册修订版一概而论

前一份报告依据 RTL8211F(I)/RTL8211FD(I)-CG Rev.1.4/Rev.1.7 的表格，将 PHYCR2 bit 1 描述为 RW、默认 1。进一步查到的早期 Rev.1.1 资料却将 bit 1 描述为 RO、默认 0；Rev.1.2 资料又明确列为 RW、默认 1。

| 数据手册版本/型号 | PHYCR2 bit 1 | 默认值 |
|---|---|---:|
| RTL8211F(I)/FD(I)-CG Rev.1.1 | RO，RXC Enable | 0 |
| RTL8211F(D)(I)-CG Rev.1.2 | RW，RXC Enable | 1 |
| RTL8211F(I)/FD(I)-CG Rev.1.4 | RW，RXC Enable | 1 |
| RTL8211F(I)/FD(I)-CG Rev.1.7 | RW，RXC Enable | 1 |
| RTL8211F(D)(I)-CG Rev.1.9 | RW，RXC Enable | 1 |

Sources:
- Rev.1.1: https://www.alldatasheet.com/html-pdf/1131976/REALTEK/RTL8211F-CG/16937/48/RTL8211F-CG.html
- Rev.1.2: https://dl.xkwy2018.com/downloads/RK3588/01_Official%20Release/04_Product%20Line%20Branch_NVR/02_Key%20Device%20Specifications/RTL8211F%28D%29%28I%29-CG_DataSheet_1.2.pdf
- Rev.1.4: https://atta.szlcsc.com/upload/public/pdf/source/20190902/C187932_1913F3711F05FE1324DF2946D70D648D.pdf
- Rev.1.7: https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf
- Rev.1.9: https://www.scribd.com/document/766949405/RTL8211F-D-I-CG-DataSheet-1-9

因此，前一份报告中“写入 0x1801 会清除 RXC enable，可能解释 RX 异常”的说法必须降级为**依具体芯片修订版而定**：
- 对 Rev.1.2 及后续所列版本，bit1 是 RW，整寄存器写 0x1801 会把 bit1 写 0；
- 对 Rev.1.1，bit1 是 RO，写入 0x1801 不会按普通 RW 语义改变它，表中默认值为 0。
- 不能仅凭封装标识 RTL8211F-CG 或 Linux PHY ID 推断实物对应哪一版数据手册/硅修订版。

这说明在没有读取实物 PHYCR2、确认完整料号/版本之前，不应把 RXC 被关闭当作既定事实。

## 2. 0x1801 的其他位也存在修订版差异

在 Rev.1.1 中 bits 15:12 被列为 Reserved；Rev.1.2 中 bits 15:12 仍是 Reserved；Rev.1.4/1.7 中 bits 13:12 被重新定义为 CLKOUT SSC Capability Select：
- 00：Normal CLKOUT
- 11：CLKOUT with SSC capability
- 其他组合：Reserved

因此写入 0x1801（bits13:12=01）：
- 对 Rev.1.1/1.2：写入保留位；
- 对 Rev.1.4/1.7：写入该字段的 Reserved 组合。

这组写入仍不是保留其他位的 read-modify-write，而是对 PHYCR2 写入整个常量。对于 bit5（PHY-mode EEE Enable），Rev.1.2/1.4/1.7 表格默认 1，0x1801 会将其清零；bit0 CLKOUT Enable 则置 1；bit11 维持 1（125MHz）。bit1 的结果按上节所列版本分别判断。

## 3. 补丁作用范围的精确控制流

上游补丁：
`unifreq/linux-6.1.y@49b5f340f346cc9a5b777499fce46150b691b70e`
parent:
`22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`
date: 2022-12-24
subject: `drv: net: ethernet: stmmac fix for jl2xx1 phy`

补丁 API：
https://api.github.com/repos/unifreq/linux-6.1.y/commits/49b5f340f346cc9a5b777499fce46150b691b70e

逐行复核补丁后的 `stmmac_mdio_register()`，执行顺序是：

1. `of_mdiobus_register(new_bus, mdio_node)` 成功；
2. XGMAC 情况下执行一个 dummy read；
3. 检查 fixed-link；如果发现 fixed-link，直接跳转 `bus_register_done`，不执行这四次写入；
4. 非 fixed-link 路径执行四次地址 0 写入；
5. 若设备树有 `phy_node` 或 `mdio_node`，跳转 `bus_register_done`；
6. 否则才扫描 PHY 地址并处理 PHY IRQ。

这意味着 workaround 并不是“只在发现 JL2xx1 后执行”。它在一般非 fixed-link 的 STMMAC MDIO bus 路径中执行，甚至早于后续 PHY 地址扫描/连接；只要设备走到这段代码就会发出写入。

### 对 Panther 的适用性

既有 Panther 设备树/日志显示使用外置 RTL8211F、非 fixed-link、由 PHY 节点连接。因此，按该控制流，Panther 属于会执行四次写入的路径。由于 PHY address=0 在 RTL8211F 数据手册中定义为 MDIO broadcast，默认支持 broadcast response，这组写入可能命中该 PHY。

但这里仍有边界：
- 这是源码控制流与数据手册语义的组合推断；
- 还没有实机 MDIO 波形证明每次写操作都成功；
- 驱动没有检查/记录这四次 `stmmac_mdio_write()` 的返回值；
- 地址 0 broadcast 功能可被 PHY 配置关闭，实物状态尚未读取。

## 4. 1500ms delay 的补丁原文与边界

同一 commit 对 `stmmac_main.c` 的改动仅是在 `stmmac_init_dma_engine()` 中，DMA reset 前插入：

```c
msleep(1500);
ret = stmmac_reset(priv, priv->ioaddr);
```

commit message 只有 `drv: net: ethernet: stmmac fix for jl2xx1 phy`，没有说明 JL2xx1 具体硬件故障、时钟关系或为什么需要 1500ms。

所以：
- 可以确认这是作者为 JL2xx1 PHY 问题加入的 workaround；
- 不能从 commit message 推导其具体物理机制；
- 1500ms delay 与四次 MDIO 写入是同一提交里针对同一标题问题的两个改动，但源码并没有证明两者各自必要性，也没有证明其中任何一项对 RTL8211F 是必需的。

## 5. 目前最强的推论与不能越过的边界

**强推论：** 6.1.116 的通用 STMMAC MDIO 初始化流程会在 Panther 非 fixed-link 路径上，尝试向 PHY 地址 0 广播写入 RTL8211F PHYCR2 和 BMCR reset；较新版本缺少这段 JL2xx1 workaround。这是一个具体、可比较、可能影响 PHY 初始化状态的版本差异。

**尚不能推论：**
- 不能说 6.1.116 一定把 RXC 关闭了；
- 不能说 RTL8211F 的 RXC/CLKOUT 状态就是当前 DHCP 故障根因；
- 不能说 1500ms 等待本身是故障修复关键；
- 不能把 JL2xx1 标题直接等同于 RTL8211F 适用性。

## 6. 下一步最小工作

1. 继续静态查明 RTL8211F Rev.1.1 与 Rev.1.2 对 PHYCR2 bit1/bit13:12 的修订变化是否来自芯片型号/硅修订差异，还是文档更正。
2. 查 Panther 已有 BOM、原理图、板级资料或 PHY ID/扩展寄存器历史输出中是否有可区分的芯片信息；没有则不猜。
3. 对照 6.1.116 正常启动日志与 6.1.174/6.12 的 PHY 初始化时序，确认是否有已记录证据能验证 MDIO reset 之前/之后的状态差异。
4. 若仍缺实物寄存器状态，先向用户提出只读 MDIO 读取方案；不做写入、不做 PHY reset、不重启网卡，除非另行明确授权。

## 7. 相关报告

- [JL2xx1 workaround 与 RTL8211F 寄存器语义审计（2026-11-19）](./PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md)
- [6.1.116 → 6.1.174 → 6.12 共享 GMAC 回归线索审计（2026-11-18）](./6.1.116-174-6.12-SHARED-GMAC-REGRESSION-AUDIT-20261118.md)
