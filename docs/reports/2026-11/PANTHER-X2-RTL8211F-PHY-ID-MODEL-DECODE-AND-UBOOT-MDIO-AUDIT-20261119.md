# Panther X2：RTL8211F 原始 PHYID2 型号解码与 U-Boot MDIO 写入审计（2026-11-19）

## 1. 本轮目标与边界

承接 RTL8211F-CG / VD-CG 区分及 PHYCR2=0x1801 线索。本轮只使用仓库已归档的 PHY ID、Linux PHY ID 读取源码、公开 U-Boot 源码候选和现有 U-Boot 二进制仓库目录结构，回答两个问题：

1. Panther 是否已有足够的原始 PHY ID 证据区分普通 RTL8211F-CG 与 RTL8211F-VD-CG？
2. 已知 U-Boot 源码是否会写 PHYCR2 Page 0xa43 / Reg 0x19？

没有连接设备、没有读取 MDIO、没有发帧、没有抓包、没有修改设备。

## 2. 重要发现：已有完整 PHY ID 本身就包含原始 PHYID2

仓库多份 6.1.116 和 6.12.81 实机记录均保存了完整 PHY ID：

0x001cc916

此前型号区分报告曾将“缺少 PHYID2 原始值”列为未确认项。但 Linux PHY ID 的构造方式可以直接从源码确认：

- Linux get_phy_c22_id() 先读取 Clause 22 MII_PHYSID1，放入 32-bit PHY ID 高 16 位；
- 再读取 MII_PHYSID2，直接 OR 到低 16 位；
- PHY sysfs 的 phy_id 属性直接输出 phydev->phy_id，不对其低 16 位做型号掩码。

因此，仓库记录的 0x001cc916 可拆为：

| 字段 | 值 |
|---|---:|
| PHYID1（高 16 位） | 0x001c |
| PHYID2（低 16 位） | 0xc916 |
| PHYID2 OUI_LSB bits 15:10 | 0x32 |
| PHYID2 Model Number bits 9:4 | 0x11 |
| PHYID2 Revision bits 3:0 | 0x6 |

这不是根据 Linux 驱动打印的产品名称猜测，而是由已记录的完整 PHY ID 和 Linux PHY ID 构造源码直接推导。

## 3. 与普通 CG / VD-CG 数据手册型号字段对照

既有型号资料报告记录：

- 普通 RTL8211F(I)-CG / FD(I)-CG：PHYID2 Model Number = 0x11；
- RTL8211F(I)-VD / FD(I)-VD：PHYID2 Model Number = 0x07。

Panther 记录的 PHYID2 为 0xc916，Model Number = 0x11，与普通 CG 系列相符，与 VD-CG 的 0x07 不符。

### 当前型号判断

**高置信度：Panther 实机 PHY 属于普通 RTL8211F-CG / FD-CG 型号编码，不是 RTL8211F-VD-CG 型号编码。**

仍保留一个很窄的限制：该判断依据仓库记录的完整 PHY ID；若历史记录中的 0x001cc916 并非 sysfs 原始 phy_id 值、而是人工改写或经过掩码的值，则需重新评估。但既有报告明确将其记为 PHY sysfs 的 PHY ID，且 Linux sysfs 源码直接输出原值，因此目前没有理由将它视为掩码值。

## 4. 对 VD-CG 专用 RXC / DMA reset 上游案例的影响

2026-08 上游修复案例的具体对象为 RK3566 + RTL8211F-VD + RGMII，涉及 VD-CG 专用 CLKOUT 配置及 PHY power-down 后 RXC 停止，导致接口 reopen 时 DMA reset 失败。

现在 Panther PHYID2 型号字段与 VD-CG 不匹配，因此：

- 不应再把 VD-CG 专用 Page 0xd05 / Reg17 CLKOUT 配置直接套用到 Panther；
- 不应把 VD-CG 特定寄存器布局当作 Panther 的事实；
- VD-CG 上游案例从 Panther 的直接型号匹配候选中降级；
- 一般性“PHY power-down 后 RXC 停止”的 IEEE PHY 行为仍可能适用于其他型号，但 Panther 目前没有接口 reopen、MTU change 或 DMA reset failure 的证据，不能据此恢复为高优先级根因。

普通 CG 的 PHYCR2 Page 0xa43 / Reg19 解释仍是本机更合适的资料分支。

## 5. 已知 Radxa U-Boot 源码中的 Realtek MDIO 行为

项目早期 Panther BSP 来源审计记录了 U-Boot 源码候选：

- Repository：radxa/u-boot
- Branch：stable-4.19-rock3
- Commit：c55987146f4f9b20f7cb2f917ca88300419afe8d
- File：drivers/net/phy/realtek.c

对该精确源码文件逐项检查 phy_write()、0xa43、PHYCR2 相关标识：

### 5.1 普通 RTL8211F 配置路径

该 U-Boot rtl8211f_config() 会：
1. 写 BMCR reset；
2. 切换到 Page 0xd08；
3. 读取 Reg 0x11，按 RGMII interface mode 设置/清除 TX delay 位；
4. 切回 Page 0；
5. 切换到 Page 0xd04，写 Reg 0x10 = 0x617f 设置 LED；
6. 切回 Page 0；
7. 执行通用 autoneg 配置。

### 5.2 Page 0xa43 的访问

该文件中的 rtl8211f_parse_status() 会：
- 向 Page Select Reg31 写入 0xa43；
- 读取 PHY status register（Reg17）；
- 轮询 link / speed / duplex；
- 读取路径没有写 PHYCR2 Reg19。

该文件没有出现 Page 0xa43 / Reg 0x19 写入，也没有出现 0x1801 或 PHYCR2 标识。

因此，**在这份已知 Radxa U-Boot 源码候选中，没有发现 U-Boot 写入普通 RTL8211F PHYCR2 的行为。** 但 U-Boot 会配置 RGMII TX delay 和 LED，并会执行 BMCR reset；这些属于其他 PHY 寄存器操作。

## 6. 当前 6.12.81 / JP U-Boot 源码映射限制

不能把第 5 节的 Radxa 源码结论直接套到当前 6.12.81 测试启动所用的 JP-TvBox / Ophub U-Boot：

- 项目配置记录的 ophub/u-boot@6e70f41585f15c43f45fcae609adec1865e83eb5 是 U-Boot 二进制资产仓库提交；
- 该提交的 Panther 目录只包含 idbloader.img 和 u-boot.itb 二进制；
- 该仓库 README 也说明它用于存放并分发 U-Boot binaries；
- 该提交没有提供可与 Panther 二进制直接对应的 U-Boot 源码树、defconfig、编译器参数或完整 source commit。

所以目前只能得出：
1. 已知 Radxa stable-4.19-rock3 源码没有写 PHYCR2 Reg19；
2. 当前 Ophub/JP U-Boot 二进制的确切源码行为仍未验证；
3. 不能用 Radxa 源码替代 JP U-Boot 的源码证明，也不能因为 binary repo 中找不到源码就断言 U-Boot 没有改写 PHYCR2。

## 7. 对当前故障研究优先级的修正

| 方向 | 更新后的判断 |
|---|---|
| Panther PHY 是否为 VD-CG | **高置信度排除 VD-CG 型号编码**；已有 PHY ID 足以解码 |
| 普通 CG PHYCR2 / JL2xx1 workaround 差异 | 仍是 116 与后续版本间真实的源码行为差异，但实际写入成功与 reset 后最终值未知 |
| VD-CG 专用 CLKOUT / RXC 配置路径 | 不适用于 Panther 的已记录 PHYID2 型号 |
| Radxa U-Boot 是否写 PHYCR2 | 已知源码候选中没有 |
| 当前 JP/Ophub U-Boot 是否写 PHYCR2 | 源码 provenance 不足，未验证 |
| GMAC TX / RGMII / PHY 发送边界 | 仍未定位；不得把 PHY 型号识别当成物理 TX 输出证明 |

## 8. 后续验证价值与安全边界

当前已有完整 PHY ID，因此**不需要为了区分 CG / VD 再安排一次 PHYID2 读取**。这关闭了一个原本可能要求额外现场读取的型号确认项目。

若将来用户另行授权 PHY 状态读取，真正有价值的是在不写寄存器、不 reset、不重启链路的前提下读取完整 PHYCR2 原始值；但此前的报告已指出外部临时模块访问 MDIO 的对象生命周期与 STMMAC parent remove/unbind 同步尚未完全证明安全，因此不能直接执行。没有解决这一生命周期问题前，不加载临时模块、不访问 MDIO。

当前继续只做静态源码/仓库研究。所有外部发帧、抓包、PHY 写入、PHY reset、RGMII/MDI 物理测试仍暂停。

## 9. 直接源码与数据依据

- Linux 6.1.116 get_phy_c22_id()：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/phy/phy_device.c
- Linux 6.1.116 PHY sysfs phy_id_show()：同上文件
- Panther 已记录完整 PHY ID：0x001cc916，见 116-RTL8211F-MDIO-TRACE-AND-PAGED-READ-SAFETY-20261118.md 与 panther-x2-6.1.116-usb-ethernet-baseline-20261116.md
- 普通 CG / VD-CG PHYID2 字段定义：PANTHER-X2-RTL8211F-CG-VS-VD-AND-STMMAC-RXC-RESET-REGRESSION-20261119.md 所列两份数据手册
- Radxa U-Boot realtek.c：https://github.com/radxa/u-boot/blob/c55987146f4f9b20f7cb2f917ca88300419afe8d/drivers/net/phy/realtek.c
- Ophub U-Boot binary repository commit：https://github.com/ophub/u-boot/tree/6e70f41585f15c43f45fcae609adec1865e83eb5

**结论：** Panther 已记录的原始 PHY ID 足以把型号归入普通 RTL8211F-CG 编码，VD-CG 专用回归候选应降级。已知 Radxa U-Boot 源码未写 PHYCR2 Reg19；当前 JP/Ophub U-Boot 源码无法从二进制资产仓库锁定。PHYCR2 实际运行态仍未验证，不能把源码差异当作根因。
