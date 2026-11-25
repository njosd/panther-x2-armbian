# Panther X2 B2-0 方向四：Rockchip GMAC glue / CCF / CRU / clock / reset 审计进度（2026-11-25）

## 1. 当前状态与边界

**方向四进行中。本报告记录历史成果清点及第一轮四版本源码复核，不代表方向四结项。**

严格沿用 B2-0 固定四版本矩阵：
- 6.1.65：黄金基准 A；源码端点 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` 为高置信度候选，不是已闭环的历史构建 source commit。
- 6.1.116：黄金基准 B；`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，历史安装包 source commit 仍有边界。
- 6.1.174-rk35xx：故障基准 A；必须使用实际构建源码 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`。
- 6.12.81-rk35xx：故障基准 B；`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。

本方向只做仓库源码、Kconfig、DTS、已有 config 和历史报告只读审计。没有访问设备、构建、安装软件、修改系统/驱动/DTB/网络配置、读写寄存器或进行网络测试。6.18.63 仅作为后续构建依赖参考，不替代四个历史比较样本。

## 2. 已有报告与禁止重复项

以下历史资产已经回读，后续只引用结论或针对证据缺口补核，不从头重做：

| 既有报告 | 已有覆盖 | 当前处理 |
|---|---|---|
| `PANTHER-X2-B2-0-DIRECTION-2-GMAC-GLUE-CLOCK-POWER-AUDIT-20261124.md` | GMAC glue、CSU、PHY regulator、runtime-PM、powerup 顺序 | 复用；其中原三版本结论不能替代本轮四版本核对 |
| `PANTHER-X2-GMAC-GLUE-CLOCK-POWER-SUPPLEMENTAL-AUDIT-20261124.md` | 6.1.116 / c2f148d / 6.12.81 glue、CRU、CSU、RK809 provider 汇总 | 复用；明确其结论边界 |
| `PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md` | 6.1.116 与 6.1.174 CRU parent/mux/gate/reset 对照 | 复用拓扑，但必须按实际 c2f148d 重新核对故障端点 |
| `PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md` | 三版本 probe/setup/PHY power handoff | 复用，避免重复 integrated PHY、SPH、CSU、regulator 分支 |
| `PANTHER-X2-6.1-TO-6.12-GMAC-CLOCK-ENABLE-SEQUENCE-REGRESSION-20261119.md` | 6.1.116→6.12.81 clocks enable、settle delay、顺序 | 复用已知差异，补足 6.1.65 与精确 c2f148d |
| `PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md` | clock enable 错误处理、5ms→100–200µs | 复用，不将源码差异直接升级为硬件根因 |
| `PANTHER-X2-P3-RK3568-GMAC-BUS-CLOCK-AND-PLL-CCF-DIFF-20261119.md` | RK3568 CRU clock parent 与 PLL CCF callback | 复用，补核 6.1.65，并严格区分初始化时调用与 GMAC probe 时调用 |
| `PANTHER-X2-RK3568-RGMII-DELAY-ORDER-AND-GMAC-CLK-PARENT-CROSSCHECK-20261119.md` | RGMII delay 写入顺序、parent 与 speed callback | 复用；不重做 delay 值比较 |

## 3. 第一轮四版本源码身份与文件指纹

本轮直接从四个锁定源码端点读取目标文件，得到以下 Git blob SHA：

| 文件 | 6.1.65 | 6.1.116 | 6.1.174 c2f148d | 6.12.81 |
|---|---|---|---|---|
| `dwmac-rk.c` | `514f1ac0dea2d49cd4f581a48db2b02160187d0a` | 同左 | `57c352f253fdb358b2118959c6ed2eabe1cdf1e5` | `d760dddfa117e1ca31ed7b42f0e15e676bff5d6d` |
| `clk-rk3568.c` | `006f929e95a4f102fc7192c5a7b9892e0fca3948` | `25cf960793648f5861246a9b2b2613b85fa32c43` | `c1d63c9e6ddd01fcd0eb3008804f0e2c86bf0ba2` | `b02554c4a7434cdd70e278d46f830e723f662752` |
| `rk3566-panther-x2.dts` | `1e3153c392d8de617f72b3133eaeddf45569bde8` | 同左 | `d517c99841cf9d724a61cd31acf9437acbb131e6` | 同左 |
| `rk356x.dtsi` | `d6a5773433837ddcfc277fd66f948754e6100a3b` | `f60f39fbee7d3497fb6ffa1b83487be42b08fc63` | `8cba8158b3875ae63f497787c33c709ca23ab3b7` | `4312a4336f22e28af2e09f9ff4b9dc7e3121c46b` |
| `softrst.c` | `5d07266745b890ec21c32c60ab0526bd393ae8a8` | 同左 | `fd56aaefe6d14b25d0473c68d05ec991298d834d` | 同左 |

说明：
- `dwmac-rk.c` 的 6.1.65 与 6.1.116 Git blob 完全相同；这是文件内容相同的直接证据，不代表 6.1.65 历史 Image 已与该候选源码精确绑定。
- `rk3566-panther-x2.dts` 的四端点形成两组相同内容：6.1.65/6.1.116 一组，c2f148d/6.12.81 一组。板级 GMAC1 关键 RGMII 配置在两组间保持一致。
- `clk-rk3568.c` 和 `rk356x.dtsi` 的整体 blob 不同，不应仅凭文件 hash 差异认定 GMAC1 路径变化；必须对实际命中的 clock/reset 定义逐项比较。

## 4. 已完成的第一轮静态发现

### 4.1 Rockchip GMAC glue 的 clocks enable 主路径

6.1.65 与 6.1.116 的 `dwmac-rk.c` 是同一 Git blob，故以下代码事实对两条黄金源码候选相同：
- `rk_gmac_clk_init()` 使用 `devm_clk_bulk_get_optional()` 获取 `rk_clocks[]`；
- `gmac_clk_enable()` 使用 `clk_bulk_prepare_enable()`，检查并传播错误；
- 对 `clk_phy` 的 `clk_prepare_enable()` 也检查返回值；
- clocks enable 后调用 clock-selection callback（如 ops 提供），随后 `mdelay(5)`；
- `rk_gmac_powerup()` 顺序为 GMAC clocks enable → RGMII interface/delay 配置 → PHY regulator enable → runtime-PM get → STMMAC probe。

实际故障源码 c2f148d 与 6.12.81 则采用逐项 `devm_clk_get()` 和逐项 `clk_prepare_enable()` 路径。对 Panther 的 RGMII 路径，相关 clocks 为 `aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`；代码在 handle 非 ERR_PTR 时调用 enable，但没有检查/传播每个 `clk_prepare_enable()` 的返回值。其 enable 路径随后执行 CSU disable helper，并等待 `usleep_range(100, 200)`，再将 `clk_enabled` 置 true。

因此当前四版本矩阵确认了一个明确分组差异：
- 两个黄金候选（6.1.65、6.1.116）：bulk enable + 返回值检查 + 5ms delay；
- 两个故障构建源码（c2f148d、6.12.81）：逐项 enable + 返回值未检查 + 100–200µs delay。

这是源码层差异，不是已证实的硬件因果关系。没有历史现场 enable return code、实际 clock rate/gate readback 或 PHY/RGMII 波形证据，不能断言时钟 enable 曾失败，也不能断言 100–200µs 对 Panther 必然不足。

### 4.2 GMAC1 专属 CRU mux/divider/gate

四个源码端点的 `clk-rk3568.c` 中，GMAC1 专属以下定义逐项一致：
- `ACLK_GMAC1`：父时钟 `aclk_usb`，gate 为 `RK3568_CLKGATE_CON(17)` bit 3；
- `PCLK_GMAC1`：父时钟 `pclk_usb`，gate 为同一寄存器 bit 4；
- `CLK_MAC1_2TOP`、`SCLK_GMAC1`、RGMII speed mux、RX/TX mux 的寄存器位置和 parent 列表一致；
- RGMII 125MHz 输入 parent chain 对应 Panther DTS 的 `gmac1_clkin → SCLK_GMAC1 → SCLK_GMAC1_RGMII_SPEED → SCLK_GMAC1_RX_TX`。

四版本中确实存在的 CRU 差异不是 GMAC1 专属 mux/gate 定义，而是其上游公共 `PCLK_USB` provider flag：
- 6.1.65 / 6.1.116：`PCLK_USB` 无 `CLK_IS_CRITICAL`；
- c2f148d / 6.12.81：`PCLK_USB` 增加 `CLK_IS_CRITICAL`。

该 flag 的作用边界仍按既有报告限定：它影响 clock provider 注册阶段的 critical/unused clock 管理语义；不能据此声称 GMAC1 正常运行时 gate 或 TX clock 被改变。GMAC1 是 PCLK_USB 的 consumer 时，是否发生实际运行时差异仍不能仅凭该 flag 推断。

### 4.3 Panther DTS 的 GMAC1 关键输入

四端点 Panther DTS 均配置：
- `phy-mode = "rgmii"`；
- `clock_in_out = "input"`；
- `gmac1_clkin` 为 125MHz fixed-clock；
- `assigned-clocks` 与 `assigned-clock-parents` 建立同一 RGMII 输入时钟父链；
- `phy-supply = <&vcc_3v3>`；
- PHY reset GPIO、active-low 与 reset delay、GMAC1 M0 pinctrl 和 TX/RX delay 的关键语义一致。

因此本方向只讨论 Panther 实际命中的外接 PHY、RGMII、clock-input 路径。RMII、SGMII/QSGMII、XPCS、integrated PHY 以及 RMII-only clock 分支不作为当前主路径结论。

## 5. 必须修正的历史证据边界

既有 `PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md` 的 6.1.174 CRU 源码链接使用 `5483dc4f...`，并非已由原始 Actions run #296 直接确认的实际构建源码 `c2f148de...`。因此：
- 该旧报告的 6.1.116 侧证据和拓扑梳理可复用；
- 其 6.1.174 CRU provider 结论不能不加说明地视为对实际故障构建源码的精确审计；
- 本报告已直接读取 c2f148d 的 `clk-rk3568.c`，确认上述 GMAC1 专属定义与公共 PCLK_USB flag；
- reset provider、reset ID 与实际 c2f148d 的精确核对仍列为方向四待完成项，未将旧报告的结论直接平移。

## 6. 当前覆盖状态与下一步

| 审计领域 | 状态 | 说明 |
|---|---|---|
| 历史报告/禁止重复项清点 | 已完成第一轮 | 已回读八份相关报告；仍需与 B2-0 原始任务顺序核对 |
| 四版本 `dwmac-rk.c` clocks enable / powerup 主路径 | 已完成第一轮 | 6.1.65 与 6.1.116 文件 blob 相同；两故障源码分组差异已确认 |
| 四版本 GMAC1 CRU mux/divider/gate | 已完成第一轮 | 专属定义一致；PCLK_USB critical flag 为两黄金/两故障分组差异 |
| Panther 四版本 GMAC1 DTS 关键时钟输入 | 已完成第一轮 | 形成两组相同 blob，RGMII input 主配置语义一致 |
| 四版本 CRU reset ID / reset controller 精确核对 | 待完成 | 旧报告仅有 6.1.116 与非精确 c2f148d 之前端点；需按实际 c2f148d 补核 |
| RK3568 CCF/PLL provider 与父链回调 | 待完成 | 继承既有三端点报告，补 6.1.65 并核实 c2f148d 精确调用链 |
| 最终四版本差异矩阵与一致性审校 | 待完成 | 以上完成后再汇总，不提前结项 |

下一步只推进表中第一项未闭环的 reset ID / reset controller 精确核对；随后按原有报告顺序补齐 CCF/PLL 的 6.1.65 对照。若某项既有证据已足够，则只做来源和端点确认，不重复源码专题。

## 7. 安全与范围声明

- 不访问 Panther X2，不执行设备命令，不读写寄存器，不进行网络测试。
- 不修改任何系统、内核、驱动、DTS、Kconfig 或网络服务。
- 不构建、不安装、不触发 Actions。
- 不启动 B2.1，不进入方向五 MDIO/PHYLIB/PHYLINK/RTL8211F 专题。
- 不把静态源码差异等同于故障根因；所有历史源码身份、最终配置和运行时证据边界继续保留。
