# Panther X2：6.1.116 JL2xx1 workaround 与 RTL8211F 寄存器语义审计（2026-11-19）

- 日期：2026-11-19
- 范围：静态审计 6.1.116 工作源码中的 STMMAC workaround，结合 RTL8211F 官方数据手册解码其 MDIO 写入
- 未执行设备命令、PHY 写入、接口重启、loopback 或配置修改

## 1. 版本分界（沿用已归档证据）

| 内核 | 已知状态 | JL2xx1 workaround |
|---|---|---|
| 6.1.116 | 已验证正常 | 存在 |
| 6.1.174-rk35xx | 最早明确异常 | 不存在 |
| 6.12.81-rk35xx | 异常 | 不存在 |

6.1.116 的工作源码为 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。workaround 由 commit `49b5f340f346cc9a5b777499fce46150b691b70e` 引入，提交日期 2022-12-24，标题为 `drv: net: ethernet: stmmac fix for jl2xx1 phy`，父提交为 `22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`。

该 commit 改动两个文件：
- `stmmac_main.c`：在 `stmmac_init_dma_engine()` 的 DMA reset 前增加 `msleep(1500)`；
- `stmmac_mdio.c`：在 MDIO bus 注册后增加四次 PHY 地址 0 的 MDIO 写入。

commit API：
https://api.github.com/repos/unifreq/linux-6.1.y/commits/49b5f340f346cc9a5b777499fce46150b691b70e

## 2. 四次 MDIO 写入的准确执行位置

6.1.116 `stmmac_mdio_register()` 在 `of_mdiobus_register(new_bus, mdio_node)` 成功后，先处理 fixed-link 特例；若存在 fixed-link 则跳过后续路径。非 fixed-link 路径随后执行：

```c
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

然后才检查 `priv->plat->phy_node || mdio_node` 并跳转到 bus_register_done。因此对于 Panther 这种通过设备树连接外置 PHY、非 fixed-link 的普通路径，这组写入位于 MDIO bus 注册之后、PHY 扫描/连接后续流程之前。

### 操作含义（协议层）

1. PHY 地址 0、寄存器 31 写入十进制 2627，即十六进制 `0x0a43`：切换到 RTL8211F 扩展页 0xa43。
2. PHY 地址 0、寄存器 25 写入 `0x1801`。
3. PHY 地址 0、寄存器 31 写入 0：切回标准页。
4. PHY 地址 0、寄存器 0 写入 `0x8000)：设置 BMCR bit 15，触发 PHY software reset。

该代码没有先读出 PHYCR2 原值做 read-modify-write；它是整寄存器写入常量 `0x1801`。源码也没有对四次写入的返回值进行检查或打印，因此源码存在该写入路径，不等于已有实机 MDIO 波形/寄存器回读证明每次写入均成功。

## 3. 与 RTL8211F 官方数据手册的对应关系

RTL8211F(I)-CG / RTL8211FD(I)-CG 官方数据手册 Rev. 1.7（2016-12-28）明确：

- PHYCR2 是 Page `0xa43`、Register `0x19`（十进制 25）。
- PHYCR2 bit 11 选择 CLKOUT 频率：0=25MHz，1=125MHz。
- PHYCR2 bit 0 控制 CLKOUT 输出使能。
- PHYCR2 bit 1 控制 RGMII RXC clock output 使能。
- PHYCR2 bit 5 控制 PHY-mode EEE。
- PHYCR2 bits 13:12 是 CLKOUT SSC capability select：00=normal CLKOUT，11=CLKOUT with SSC capability，其他组合标为 Reserved。
- 数据手册 Note 1 明确要求：设置 PHYCR2 这些位后，应执行 PHY reset（Page 0、Reg 0、bit 15=1）。

数据手册对应章节：8.3.17，PDF 第 45 页；PHY address 0 的说明在 7.8，PDF 第 16 页；CLKOUT 与 RGMII RXC 引脚说明在 6.2/6.3，PDF 第 7–8 页。

来源：
https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf

### 3.1 `0x1801` 的位拆解

`0x1801 = (1 << 12) | (1 << 11) | (1 << 0)`。

按该数据手册定义，写入值涉及：

| 位 | 写入值 | 数据手册定义 | 直接含义 |
|---|---:|---|---|
| 13:12 | 01 | CLKOUT SSC capability select；01 为 Reserved | 写入一个数据手册标为保留的组合 |
| 11 | 1 | CLKOUT frequency select | 选择 125MHz |
| 5 | 0 | PHY-mode EEE enable | 清除该使能位 |
| 1 | 0 | RXC enable | 清除 RXC clock output enable |
| 0 | 1 | CLKOUT enable | 使能 CLKOUT 输出 |

注意：这是按 RTL8211F Rev.1.7 对整寄存器值逐位解码的结果。不能只把 `0x1801` 简化描述为“打开 125MHz CLKOUT”；它同时清除了 bit 1 和 bit 5，并把 bits 13:12 写成数据手册标记为 Reserved 的 `01`。这正是后续需要谨慎验证的关键。

## 4. PHY 地址 0 是否会作用于 Panther 的 RTL8211F

RTL8211F 数据手册 7.8 明确写明：

- PHYAD[2:0] 的常规可配置地址为 0x01–0x07；
- MDIO 命令中的 PHY address=0 是 MAC 发出的 broadcast；
- 默认 PHYCR1 Page 0xa43 Reg24 bit13=1 时，PHY 会响应该 broadcast；该功能可以通过清除该位禁用。

因此，地址 0 不能简单理解成“只针对一个软件编号为 0 的 PHY”。对 RTL8211F 而言，它具有广播语义。若 Panther 的 PHY 保持数据手册默认的 PHYAD_0 Enable，地址 0 写入就可能作用于总线上的 RTL8211F。

本机 Linux PHY 地址 0 的历史识别记录仍然保留，但不能仅凭 Linux 的 `phy addr 0` 字样，推断芯片 strap PHYAD 的全部电气状态；地址 0 broadcast 的数据手册语义是独立证据。

## 5. 与 Panther X2 时钟架构的关联：高价值，但存在待解释矛盾

已归档的 Panther 运行时设备树为：
- GMAC1 `phy-mode = "rgmii"`
- `clock_in_out = "input"`
- RTL8211F PHY，MDIO 地址记录为 0
- GMAC1 使用 PHY 侧提供的 125MHz reference clock 的判断，来自既有时钟树/运行时分析

RTL8211F 数据手册确认其 pin 35 `CLKOUT` 可输出由内部 PLL 生成的 125/25MHz reference clock，供 MAC 使用；如果 MAC 不使用该 clock，该引脚应保持浮空。RGMII 的 RXC 则是另一个独立引脚（pin 27），连续输出 125/25/2.5MHz receive reference clock。

因此，6.1.116 的 `0x1801` 写入与 Panther 的 PHY→MAC 参考时钟架构存在直接的功能关联：它使能 PHY CLKOUT，并选择 125MHz。它不是普通 LED 配置，也不是与数据通道无关的任意 workaround。

但同时，按数据手册 Rev.1.7 解码，`0x1801` 又会清除 PHYCR2 bit1（RXC output enable），并写入保留的 SSC capability 组合。**这与“6.1.116 实际网络收发正常”的已知事实之间存在需要解释的矛盾。** 不能据此断言 0x1801 就是正确配置，也不能假设它对 RTL8211F 完全无害。

可能的解释方向（均未证实）：
- Panther 板级实际使用 PHY CLKOUT pin 35 作为 MAC 参考时钟，而 RXC bit1 的实际作用/复位后状态需要结合芯片版本与板级连接进一步核对；
- RTL8211F 具体料号/硅版本或该数据手册寄存器定义与实物存在差异；
- MDIO broadcast/write 的实际执行或 PHY reset 后寄存器保留行为与静态代码预期不同；
- 6.1.116 还有其他启动/时钟条件使这组写入的副作用不表现为故障。

这些是待证方向，不是结论。

## 6. 1500ms 等待的真实时序位置

在 6.1.116 `stmmac_init_dma_engine()` 中，执行顺序为：

```
检查 DMA 参数
设置 enhanced descriptor 标志
msleep(1500)
stmmac_reset()                 // DMA software reset
stmmac_dma_init()
初始化 DMA channel
初始化 RX/TX channel
```

在 `__stmmac_open()` 中，调用顺序为：

```
pm_runtime_resume_and_get()
stmmac_init_phy()              // attach/connect PHY
...
stmmac_hw_setup()
  └─ stmmac_init_dma_engine()
       └─ msleep(1500)
       └─ stmmac_reset()
...
phylink_start()
申请 IRQ
启动 queues / DMA IRQ
```

所以 1500ms 不是每个 TX 包的延时，也不是 DMA descriptor 完成后的等待。它是在网卡 open 流程中，PHY attach 之后、DMA engine reset 和硬件 setup 之前执行的一次固定等待。它可能为前面的 PHY/时钟/复位状态留出稳定时间，但仅凭源码无法证明这就是该延时的设计目的。

## 7. 当前证据结论

### 已验证（源码/数据手册）

1. JL2xx1 workaround 由 2022-12-24 commit 引入，确切修改为 DMA reset 前 1500ms 等待，以及 MDIO 注册后的四次写入。
2. 6.1.116 工作源码包含这两项；6.1.174 与实际 6.12.81 源码均缺少它们（沿用 2026-11-18 报告的逐版本审计）。
3. 四次写入中的 `0x0a43:0x19=0x1801` 在 RTL8211F 上对应 PHYCR2，而非泛化的未知寄存器。
4. RTL8211F 官方数据手册明确规定 PHYCR2 的 CLKOUT、RXC、EEE 位及 PHY reset 要求。
5. RTL8211F 对 MDIO PHY address 0 有 broadcast 响应语义（默认使能）。
6. 1500ms 等待位于 PHY attach 后、DMA reset 前，不在 packet TX 快路径。

### 尚未验证

1. Panther 实物 RTL8211F 的完整料号/硅版本及 PHYCR2 复位后实际回读值。
2. Panther PCB 上 pin35 CLKOUT、pin27 RXC 的实际连接对象与是否被使用。
3. 6.1.116 运行时该四次 MDIO 写入是否全部成功、PHY reset 后寄存器最终值。
4. 6.1.174 与 6.12 缺少该 workaround 是否足以导致 MAC/PHY 时钟或 TX/RX 异常。
5. JL2xx1 原作者的硬件平台、PHY 型号与该 workaround 的最初故障背景。

### 当前判断

这是目前最有价值的共享回归候选，但还不能作为根因定案。尤其是 `0x1801` 与 RTL8211F PHYCR2 位定义之间的关联非常具体，值得优先继续；同时，RXC enable 被清零这一点必须解释，不能跳过。

## 8. 后续最小研究步骤（不做设备改动）

1. 追查 JL2xx1 workaround 的原始提交背景/后续修正，确认作者为何在全局 STMMAC MDIO 注册路径写入这四个值。
2. 对照 RTL8211F 数据手册各修订版及公开驱动，确认 PHYCR2 复位后的保留/锁存行为和 bit1 的实际控制范围。
3. 通过仓库现有 Panther X2 原理图/PCB 资料（若存在）确认 pin35 CLKOUT 与 pin27 RXC 的走线目的端；没有资料则标记为未验证，不做硬件审计。
4. 只有静态语义明确后，才提出一个最小只读验证方案；任何 PHY MDIO 写入、接口重启、loopback 或 PHY reset 都需要用户另行明确授权。

## 9. 相关报告

- [6.1.116 → 6.1.174 → 6.12 共享 GMAC 回归线索审计（2026-11-18）](./6.1.116-174-6.12-SHARED-GMAC-REGRESSION-AUDIT-20261118.md)
- [TX 物理边界与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- [BL31 早期初始化反汇编审计与测试收口（2026-11-19）](./PANTHER-X2-BL31-EARLY-INIT-DISASSEMBLY-AND-TEST-STOP-20261119.md)
