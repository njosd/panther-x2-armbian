# Panther X2 硬件边界与板级设备树基线审计

- 日期：2026-11-22
- 项目：Project A（仅板载有线千兆 Ethernet）
- SoC：Rockchip RK3566
- 状态：源码静态审计完成；目标板内部器件与每个引脚的实物对应关系仍需保留证据等级
- 本报告不授权设备启动、介质写入、U-Boot/FDT 修改或硬件寄存器操作。

## 1. 结论先行

Panther X2 确实是 RK3566 板卡，外部使用接口相对简单。项目 A 应以 **RK3566 SoC 通用 DTSI + Panther X2 专用板级 DTS** 为基础，而不是把 Radxa ROCK3 Model C 的完整 control FDT 当作 Panther X2 板级设备树，也不是从任意 RK3566 通用板 DTB 直接套用。

上游已有 Panther X2 专用板级文件：

- Repository：`unifreq/linux-6.1.y`
- Path：`arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`
- 原始新增 commit：`afaa1a194f812e30a9faedd88d6c09e7a49d909a`
- 原始 commit 对应 Git blob：`306157b84300719895ee025aec4dd0b3efbae7e0`
- 2024-11-17 后续版本 commit：`ffffa29dfec714c7b2682625faff73111174e783`
- 后续版本 Git blob：`5d0ce802558c20ee5d142197a4cb24313bd8277`

专用 DTS 根节点声明：

```dts
model = "Panther X2";
compatible = "panther,x2", "rockchip,rk3566";
```

这正是项目目标硬件身份。Rockchip 的 `rk3566.dtsi` 提供 SoC 公共资源，Panther X2 DTS 提供板级电源、时钟、pinmux、GPIO、外设连接和板级身份。所谓“普通 RK3566 布局”应理解为复用 SoC 通用描述，不应理解为省略板级 DTS。

## 2. 外部接口与整板功能边界

### 2.1 与 Project A/B1 启动直接相关的接口

| 硬件/接口 | 当前证据 | 项目 A 处理 |
|---|---|---|
| RK3566 SoC | Panther X2 专用 DTS compatible；历史 Linux Hardware Name | 目标 SoC |
| RJ45 千兆网口 | 6.1.116 实机 eth0、RTL8211F、1000M Full Duplex；板级 DTS GMAC1/MDIO/PHY 描述 | Project A 唯一网络目标 |
| TF/SD 卡槽 | 历史启动链由 U-Boot 从 TF 读取启动资产；板级 DTS 有 SDMMC 节点 | 仅由 U-Boot 在 Linux 启动前读取；B1 Linux 不启用 MMC |
| UART 调试口 | DTS stdout-path 为 serial2:1500000n8；实机 UART 1500000 bps | B1 必须保留 |
| USB-A 2.0 | 6.1.116 USB 审计记录实际 USB 2.0 High-Speed 设备枚举；公开板卡资料也列 USB 2.0 | Project A 排除 USB；B1 不启用 USB |

### 2.2 板上还有非 Project A 功能

Panther X2 并非只有 SoC、RJ45、USB、TF、UART。公开 Panther X2 硬件资料和现有板级 DTS 还描述了其他板载功能，例如 Wi-Fi/蓝牙模块、LED、按键、PMIC/稳压器；另一份社区板卡资料还列出 SX1302 LoRa、ATECC608A 等器件。不同批次/区域配置是否完全相同，不能只靠产品资料推断当前这台实机的每一颗器件。

本项目的处理原则：
- Wi-Fi/无线网络、蓝牙、USB/PCIe 外接网卡按既定路线图排除。
- LoRa、ATECC608A、LED、按键及其他非目标功能不属于 Project A 验收范围；不得为了项目 A 把它们扩展成新排障任务。
- 不得因它们不属于 Project A，就删除可能承载启动、电源、时钟或 Ethernet 供电的共享基础设施。
- 外观照片可以确认可见接口、器件位置和丝印；不能单独确认 PCB 内层走线、隐藏模块、供电拓扑、PHY reset 极性或时钟来源。此类参数以板级 DTS、原始资料和实测证据交叉确认。

## 3. Panther X2 板级 DTS 中与 Project A 有关的 Ethernet 配置

原始 Panther X2 DTS 的 `&gmac1` / `&mdio1` 给出了板级而非纯 SoC 通用参数：

- GMAC 节点：SoC `gmac1`，运行时平台地址为 `fe010000.ethernet`。
- PHY 模式：`phy-mode = "rgmii"`。
- 时钟方向：`clock_in_out = "input"`。
- 板级外部固定时钟：`gmac1_clkin`，频率声明为 125,000,000 Hz。
- PHY 电源：`phy-supply = <&vcc_3v3>`。
- pinctrl：`gmac1m0_miim`、TX/RX bus、RGMII clock、clkinout 和 RGMII bus 组合。
- PHY reset：`snps,reset-gpio = <&gpio3 RK_PA1 GPIO_ACTIVE_LOW>`，active-low；reset delays 为 `<0 20000 100000>` 微秒。
- RGMII delay：`tx_delay = <0x30>`、`rx_delay = <0x10>`。
- PHY 连接：`phy-handle = <&rgmii_phy1>`；MDIO 节点下 `ethernet-phy@0`，C22 地址 `reg = <0>`。

这些是**已在上游 Panther X2 DTS 中找到的板级配置值**，不是本轮重新实测出的电气事实，也不证明每个属性都适合当前正在运行的启动链/Kernel。Project A 后续应把它们作为有来源的候选基线，结合 6.1.116 已成功运行的设备树与当前目标 DTB 做属性级比较；不得重新猜 delay、时钟、GPIO 或 PHY 地址。

## 4. 不能忽略的共享板级基础设施

同一 Panther X2 DTS 还描述了：
- I2C0 上的 TCS4525 CPU regulator（地址 0x1c）；
- I2C0 上的 RK809 PMIC（地址 0x20）及其多个 regulator/clock 输出；
- SoC IO-domain 电源引用；
- UART2 作为 `serial2` 控制台；
- eMMC、TF 和 SDIO 的不同控制器/总线分配；
- USB2 PHY/控制器；
- LED GPIO/pinctrl；
- SARADC、TSADC 等节点。

Project A B1 需要禁用网络设备和所有非目标驱动，但不能把“功能不在项目范围”错误地等同于“设备树中必须删除”。特别是 regulator、clock、reset、pinctrl、GPIO 和 PMIC 可能是 CPU/DDR/启动控制台或后续 GMAC 的共享依赖。每项是否保留，应依据实际依赖链逐项判断。

## 5. 历史正向基线与现有 DTB 资产

仓库已经保留 6.1.116 Panther X2 的两份关键设备树：

| 文件 | 来源 | SHA-256 |
|---|---|---|
| `running-fdt.dtb` | Linux `/sys/firmware/fdt` 运行时 FDT | `f6d95eb21889f57372ace6292bf82b25e1c3fca52da662b60cb1cec832aa9e32` |
| `rk3566-panther-x2.dtb` | `/boot/dtb/rockchip/rk3566-panther-x2.dtb` | `5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82` |

另有 2026-11-16 6.1.116 USB/Ethernet 实机基线：
- eth0 对应 `fe010000.ethernet`；
- 驱动 `rk_gmac-dwmac`；
- PHY RTL8211F，PHY ID `0x001cc916`；
- RGMII；
- 用户确认 DHCP 获得 LAN IPv4 /24，ping hEX 和 iMac 均 0% 丢包，RX/TX errors/dropped/carrier errors 为 0。

这比当前 U-Boot control FDT 更贴近 Panther X2 实机基线。需要注意：历史运行时 FDT 与磁盘 DTB 是不同对象；二者的差异可能包含 bootloader fixup，不能只用 SHA 不同判断异常。

Ophub 6.18.63 包中也曾确认存在同名 Panther X2 DTB，已记录的 SHA-256 为：
`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`。
当前尚未完成所有版本 DTB 与其源码 commit 的逐属性 provenance 闭环。

## 6. 当前 U-Boot control FDT 的正确解释

2026-11-22 当前 JP-TvBox U-Boot proper 的 control FDT：
- model：`Radxa ROCK3 Model C`
- compatible：`radxa,rock3c`, `rockchip,rk3566`
- address：`0xEB9F63C0`
- total size：35,080 bytes。

该 FDT 与 Panther X2 共用 RK3566 SoC compatible，但其 board-level identity 是 ROCK3C。它可以解释当前 proper 的控制设备树身份，不能替代 Panther X2 的 Linux DTB，也不能作为 Panther X2 的 pinmux、电源、GMAC/PHY 参数来源。

因此，前一轮将其表述为“不是 Panther X2 专用 FDT”是准确的；但不能将它进一步解释为“RK3566 不匹配”或“硬件完全不兼容”。真正的判断必须看板级资源属性。

## 7. Project A 推荐资产与裁剪原则

1. SoC 基础：采用与锁定 Kernel 同一源码树的 `rk3566.dtsi`。
2. 板级基线：采用 Panther X2 专用 `rk3566-panther-x2.dts`，不要从 ROCK3C DTS 反向改名，也不要用通用 RK3566 DTB 替代。
3. B1 clean-test DTB：保持 Panther X2 的根节点身份、UART2 console、内存/保留区、启动所需 clocks/resets/pinctrl/regulator/PMIC 基础；Ethernet、MDIO/PHY、MMC/SDIO、USB、无线/蓝牙等设备按 B1 规则隔离，且不得破坏共享依赖。
4. B2 Ethernet DTB：从同一板级 DTS 派生独立测试变体，只启用板载 GMAC1/MDIO/PHY 与经依赖审计确认必要的资源；不同时加入 USB、Wi-Fi、蓝牙、LoRa 或其他设备。
5. B2 的每项配置必须来自锁定源码、历史 6.1.116 正向 DTB、原始 Panther X2 DTS 或可复现实机证据；不凭经验更改 RGMII delay、时钟频率、reset GPIO、PHY 地址。
6. B1/B2/B3 尽量固定 Kernel/DTB/initramfs/BusyBox/启动链；每轮仅改变被批准的单一组件或最小依赖闭包。

## 8. 仍需完成的审计

- 解包并独立读取历史 6.1.116 `running-fdt.dtb` 和磁盘 Panther X2 DTB，生成结构化属性清单及差异报告。
- 固定与项目 A Kernel commit 匹配的 Panther X2 DTS 源码版本；不得混用不同 Kernel 分支的 SoC DTSI。
- 对 B1 最终 DTB 做 `model/compatible/chosen/memory/reserved-memory/aliases/PSCI` 核对。
- 对 B2 Ethernet DTB 做 GMAC/MDIO/PHY/pinctrl/clock/reset/regulator/interrupt/DMA 属性核对。
- 将 U-Boot final FDT fixup 的输出副本和 SHA-256 纳入 PRE-HANDOFF 阶段门。
- 目标板实机最终验证仍需等待 PRE-HANDOFF READY；本报告不授权启动。

## 9. 证据来源

1. Panther X2 board DTS：`unifreq/linux-6.1.y` commit `afaa1a194f812e30a9faedd88d6c09e7a49d909a`，及后续 commit `ffffa29dfec714c7b2682625faff73111174e783`。
2. 本仓库 `docs/BSP-SOURCE-AUDIT.md`：Panther X2 DTS lineage 与 Vendor DTS 说明。
3. 本仓库 `docs/DTB-AUDIT.md`、`docs/DTB-INSPECTION-2026-11-14.md`：6.18.63 DTB 包及源码核验状态。
4. 本仓库 `docs/01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md`：6.1.116 实机网络/USB 与设备树归档。
5. 公开 Panther X2 硬件/软件交叉参考：`https://github.com/yjdwbj/panther-x2`。其硬件配置表和状态表属于社区维护者资料，不替代用户当前实机测量。
6. Rockchip RK3566 Brief Datasheet：`https://www.rock-chips.com/uploads/pdf/2022.8.26/192/RK3566%20Brief%20Datasheet.pdf`，用于 SoC 能力背景，不用于推断 Panther X2 板级走线。

## 10. 阶段结论

- **已确认：** Panther X2 目标 SoC 为 RK3566；上游存在专用 `rk3566-panther-x2.dts`；历史 6.1.116 有 Panther X2 运行时 FDT 和磁盘 DTB；历史 Linux 实测 Ethernet 曾正常工作。
- **静态源码确认：** Panther X2 GMAC1 使用 RGMII、MDIO PHY 地址 0、外部 125 MHz clock、专用 pinctrl、reset GPIO 和供电引用。
- **未验证：** 历史运行时 FDT 与磁盘 DTB 的完整属性差异；目标 Kernel commit 对应 DTB 的确切构建来源；当前 U-Boot proper 的 ROCK3C control FDT 对 Panther X2 的板级资源适配程度；最终交给 Linux 的 FDT。
- **结论：** Project A 不需要“寻找一块看起来最普通的 RK3566 板子”。我们已经有 Panther X2 专用板级 DTS 和正常运行过的 DTB，应以它们为中心建立最小系统。B1 先隔离非目标设备但保留启动/电源基础设施，B2 再只放行板载 Ethernet 所需资源。
