# Panther X2 项目 A — G0.7 板级电源资料与安全测量点可获得性（2026-11-26）

- 状态：**公开资料检索完成；Panther X2 专用原理图/netlist/testpoint 未找到；硬件测量准备 BLOCKED。**
- 范围：只读检查项目仓库、公开 Panther X2 软件/产品资料及 Rockchip RK3568 Hardware Design Guide；没有拆机、测量或访问设备。
- 本报告不把 RK3568 参考设计等同于 Panther X2 实际 PCB。

## 1. Panther X2 专用公开资料

检查结果：
- 项目使用的公开 Panther X2 软件仓库 `yjdwbj/panther-x2` 包含 README、dmesg、RKNN benchmark、升级工具和产品/启动照片；未发现原理图、PCB layout、netlist、BOM 或测试点图。
- Dewi Alliance 的 Panther X2 产品资料列出 RK3566、4GB、eMMC/TF、RTL8211F 千兆 Ethernet、RK809 等硬件规格，但没有电源网表或板级原理图。
- Panther X2 用户手册提供产品外观、接口和系统架构，没有内部电源原理图。
- Rockchip RK3568 Hardware Design Guide Rev V1.2 可确认 SoC 层 IO domain 和 pin multiplexing，但不能说明 Panther X2 PCB 上 RK809 SWITCH_REG1、LDO_REG6、VCCIO5 的实际走线、元件位号或探测点。

因此，目前不能安全指定某个电容、焊盘、测试点或芯片引脚作为 Panther X2 的 VCC3V3_PMU / VCC_3V3 测量位置。不能套用 Firefly、Radxa、Neardi 或其他 RK3566 开发板的测试点。

## 2. SoC 官方设计资料可确认的域映射

Rockchip RK3568 Hardware Design Guide Rev V1.2：
- GMAC1 M0 对应 VCCIO5；GMAC1 M1 对应 VCCIO6。Panther DTS 使用 `gmac1m0_*` pin groups，因此当前目标是 VCCIO5。
- UART2 M0 与 I2C0 属 PMUIO2；PMUIO2 支持 1.8V/3.3V。
- PMUIO1 只支持 3.3V。
- 官方指南明确要求 IO domain 的软件选择电压必须与实际外部供电一致，否则可能造成接口异常甚至损坏 IO。

网络检索中存在第三方板卡资料把 GMAC 与 VCCIO6 关联的不同描述；该描述不能覆盖 SoC 官方 M0/M1 pin map。对 Panther X2，必须以实际 DTS 的 M0 pin group 与 Rockchip 官方 pin map 组合判断为 VCCIO5。

## 3. G0.6 fixed-regulator 路径所需实测项

| rail | DTS / regulator 来源 | SoC 域 | 用途 | 当前状态 |
|---|---|---|---|---|
| VCC3V3_PMU | RK809 LDO_REG6 / `vcc3v3_pmu` | PMUIO1、PMUIO2 | UART2 M0、I2C0 等 PMU IO | DTS 标称 3.3V、always-on/boot-on；实际电压/纹波未测 |
| VCC_3V3 | RK809 SWITCH_REG1 / `vcc_3v3` | VCCIO5 | GMAC1 M0 IO 与 RTL8211F `phy-supply` | DTS 未标 always-on/boot-on；实际电压/启动状态未测 |

必须分别确认：
1. 两条 rail 在当前真实板卡上是否存在、由哪个器件/输出供电；
2. 可用测量点的实际元件位号和 net 名；
3. 对地参考点；
4. 3.3V 实际值、空载/当前负载变化与稳定性；
5. VCC_3V3 是否在 PMIC regulator driver 未加载时仍保持供电；
6. 在整个单次测试窗口中是否会因 suspend、PMIC_SLEEP_H、关机或其他电源状态改变而掉电。

只有测量点经板级资料确认后，才可另行安排低风险电压测量；不允许根据 DTS 网名猜测附近电容就是该 rail。

## 4. 当前结论

- SoC 层电压域归属可确认：GMAC1 M0=VCCIO5；UART2 M0/I2C0=PMUIO2。
- Panther DTS 的电源拓扑可确认：VCC3V3_PMU 与 VCC_3V3 是两条不同 rail；VCC_3V3 同时供给 VCCIO5 和 PHY。
- Panther X2 板级真实连接与可安全测量位置无法由公开资料确认。
- G0.6 fixed-regulator 路径因此保持 CONDITIONAL BLOCKED；不能创建 fixed regulator 假报 3.3V，也不能进入 IO-domain GRF 写入或 GMAC probe。

## 5. 需要的最小补充资料

要继续而不猜测测点，优先需要以下任意一种：
1. Panther X2 原始原理图 PDF / KiCad / Altium 导出 PDF，至少包含 RK809、电源输出、RK3566 VCCIO5/PMUIO1/PMUIO2 和 RTL8211F 页面；
2. 若无原理图，提供 PCB 正反面高清照片，能看清 RK809、RTL8211F、周围电感/电容/电阻位号和丝印；照片只用于进一步识别候选位置，不能单独证明电气连通；
3. 厂商确认的 VCC3V3_PMU、VCC_3V3 测试点位号或 netlist。

收到资料后先做静态 net tracing，标出测量点与不应触碰的相邻引脚，再单独提交测量方案。未经确认不要求用户先上表笔测量。

## 6. 下一步

G0.7 资料检索阶段结束，但 rail 测量准备未放行。下一步是补齐 Panther X2 专用板级资料；资料到位后静态确认测点。没有资料时，保持 fixed-regulator 路径 BLOCKED，不能为了赶进度退回 stock RK809 MFD 的未审查写入路径。
