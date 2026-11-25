# Panther X2 B2-0 方向四：Rockchip GMAC glue / CCF / CRU / clock / reset 审计进度（2026-11-25）

## 1. 当前状态与边界

**方向四已完成既定静态审计范围，按证据边界明确的有条件结项归档。** 结项不代表已找到硬件根因或完成实机验证。

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

实际故障源码 c2f148d 与 6.12.81 则采用逐项 `devm_clk_get()` 和逐项 `clk_prepare_enable()` 路径。对 Panther 的 RGMII 路径，相关 clocks 为 `aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`；代码在 handle 非 ERR_PTR 时调用 enable，但没有检查/传播每个 `clk_prepare_enable()` 的返回值；clock handle 获取失败时主要记录错误而不立即终止 probe。其 enable 路径随后执行 CSU disable helper，并等待 `usleep_range(100, 200)`，再将 `clk_enabled` 置 true。

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

四版本中确实存在的 CRU 差异不是 GMAC1 专属 mux/gate 定义，而是其上游公共 USB clock provider flags：
- 6.1.65 / 6.1.116：`HCLK_USB`、`PCLK_USB` 均无 `CLK_IS_CRITICAL`；
- c2f148d / 6.12.81：`HCLK_USB`、`PCLK_USB` 均带 `CLK_IS_CRITICAL`。

这是对既有报告中仅突出 `PCLK_USB` 的补充修正：实际后期源码两个公共 USB clock 都增加了 critical 标记，不能只记录 PCLK。该差异仍属于 provider 注册/unused-clock 管理语义，尚无证据证明它改变 Panther GMAC1 正常运行时 gate 或 TX clock。

两条 critical 分支必须分别解释：HCLK_USB 的 parent list 是 GPLL 派生时钟/XIN24M，与 GMAC1 已确认的 ACLK/PCLK parent chain 无直接关系；PCLK_USB 的 parent 是 aclk_usb，而 ACLK_GMAC1 也以 aclk_usb 为 parent、PCLK_GMAC1 以 pclk_usb 为 parent。因此 PCLK_USB critical 会在 provider 注册阶段保持 PCLK_USB 及其 ACLK_USB parent 的引用/启用状态，属于 GMAC1 共用上游时钟树的真实初始化差异。ACLK_USB 的四个候选 parent 为 GPLL300/GPLL200/GPLL100/XIN24M；Panther DTS 没有为 ACLK_USB 设置 assigned-clock-parent，因此历史实际选择未知。若其选择 GPLL 且 GPLL 当时 enable reference 为 0，则后期 PCLK_USB critical 的注册期 parent recursion 可能触发 GPLL enable callback；后期 GPLL callback 又从黄金版本的“清 PWRDOWN→wait lock→返回”变为“wait lock→切 NORMAL”，disable 前还切 SLOW。此为两项后期源码变化在同一条件下可能联动的路径，不是已证实的历史执行事实。若 ACLK_USB 选择 XIN24M，则该 GPLL callback 联动不成立。GMAC1 probe 正常 enable ACLK_GMAC1/PCLK_GMAC1 时也会递归启用对应父链，故不能仅凭源码推断 MAC active 后的 TX 时钟差异。它可能改变 GMAC probe 前的 early/unused-clock 状态和时钟引用基线，历史 parent/gate readback 缺失，仍需保留为未验证候选。HCLK_USB critical 则不在已确认的 GMAC1 parent chain 内，不应与 PCLK_USB 等同处理。

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
- 本报告已直接读取 c2f148d 的 `clk-rk3568.c`，确认上述 GMAC1 专属定义与公共 HCLK_USB/PCLK_USB flags；
- reset provider、reset ID 已在本报告 §6.1 按实际 c2f148d 完成四版本精确核对；旧报告仅作为历史线索，不再作为该结论的唯一来源。

## 6. 当前覆盖状态与下一步

| 审计领域 | 状态 | 说明 |
|---|---|---|
| 历史报告/禁止重复项清点 | 已完成 | 回读并复用既有专题报告，明确禁止重复范围 |
| 四版本 `dwmac-rk.c` clocks enable / powerup / powerdown | 已完成 | bulk→逐项获取/enable、错误检查、5ms→100–200µs 差异；Panther 实际 RGMII 路径已闭环 |
| 四版本 GMAC1 CRU mux/divider/gate | 已完成 | 专属定义一致；HCLK_USB/PCLK_USB critical flags 为两黄金/两故障分组差异 |
| Panther 四版本 GMAC1 DTS 关键时钟输入 | 已完成 | 形成两组相同 blob，RGMII input 主配置语义一致 |
| 四版本 CRU reset ID / reset controller 精确核对 | 已完成（源码静态范围） | 四版本 ID 236、provider 注册参数与映射一致；STMMAC core 10µs delay 差异见 §6.1 |
| RK3568 CCF/PLL provider 与父链回调 | 已完成 | 四版本 PLL callback、CCF critical 语义及 GPLL 条件链已核对 |
| RGMII GRF callback / link-speed callback | 已完成 | CON0/CON1 写入顺序变化；10/100/1000 rate mapping 一致 |
| regulator / CSU / genpd / runtime-PM handoff | 已完成 | Panther 实际外接 PHY 路径适用性已核对；共同错误传播弱点与 no-op 分支已区分 |
| suspend/resume 与 powerdown | 已完成 | Panther 外接 PHY 主路径一致；integrated-PHY 差异不命中 |
| 四版本总矩阵、证据等级与跨方向一致性 | 已完成 | 见 §6.6–§6.8、§8、§10；方向四有条件结项 |

方向四原定静态审计子项现已完成；总矩阵、证据等级及跨方向一致性审校见 §6.6–§6.8、§8，正式有条件结项决定见 §10。


## 6.1 四版本 CRU reset ID / provider 闭环（2026-11-25）

### 6.1.1 DTS consumer 与 reset binding

四版本 `rk356x.dtsi` 的 GMAC1 节点均声明 `resets = <&cru SRST_A_GMAC1>`、`reset-names = "stmmaceth"`。四版本 binding 的 `SRST_A_GMAC1` 均为 ID 236；相邻 `SRST_GMAC1_TIMESTAMP` 为 237。binding 文件整体 blob 虽然不同，GMAC1 reset ID 数值一致。Panther board DTS 没有覆盖该 reset specifier，因此继承 SoC DTS 的 ID 236。

### 6.1.2 CRU reset controller 注册与寄存器映射

四版本 `clk-rk3568.c` 均调用 `rockchip_register_softrst(np, 30, reg_base + RK3568_SOFTRST_CON(0), ROCKCHIP_SOFTRST_HIWORD_MASK)`。四版本均为 30 registers、HIWORD_MASK；常规映射每寄存器 16 个 reset IDs。ID 236 对应 bank 14、bit offset 12、register `RK3568_SOFTRST_CON(0) + 14 * 4`。映射和 hiword-mask assert/deassert 写入规则一致。此处是源码映射推导，不是实际 MMIO readback。

### 6.1.3 softrst.c 文件变化的实际影响边界

6.1.65 / 6.1.116 的 `softrst.c` blob 相同；c2f148d / 6.12.81 blob 相同。后期版本增加 lookup-table reset provider API，并在 assert/deassert 中支持 `softrst->lut`。但 RK3568 CRU 初始化在四版本仍调用普通 `rockchip_register_softrst()`，不是 `rockchip_register_softrst_lut()`；该 LUT 能力没有用于 Panther RK3568 GMAC1 reset 路径，不能据此推断 ID 236 映射发生变化。

### 6.1.4 STMMAC core reset sequence 的时间差异

四版本 `stmmac_main.c` 在 GMAC reset assert/deassert、optional AHB reset deassert 的主要顺序一致；但进入 `stmmac_hw_init()` 前的显式等待不同：
- 6.1.65：没有该处显式 `udelay(10)`；
- 6.1.116：存在 `udelay(10)`；
- c2f148d：存在 `udelay(10)`；
- 6.12.81：存在 `udelay(10)`。

因此该 10µs delay 是 6.1.65 与后续三个源码端点的差异，不是 6.1.174 首次故障版本相对 6.1.116 的新增差异，不能解释 6.1.116 正常→6.1.174 故障的首发回归。不得笼统写成四版本 reset 流程逐字节一致。

### 6.1.5 reset 子项结论

- **已验证：** 四版本 GMAC1 reset consumer、ID 236、CRU provider 注册参数、HIWORD_MASK 规则和寄存器 bank/bit 映射一致。
- **已验证：** 后期 `softrst.c` LUT API 没有被 RK3568 CRU 初始化调用，不改变本路径映射。
- **已验证：** STMMAC reset 到 MAC hardware init 的显式 10µs 等待仅在 6.1.65 缺失，6.1.116/6.1.174/6.12.81 均存在。
- **未验证：** reset 寄存器运行时值、assert/deassert 实际总线完成时间、硬件复位脉冲宽度及 PHY/MAC 电气状态。
- **定级：** 没有发现 6.1.174 相对 6.1.116 的 GMAC1 reset ID/provider regression；10µs delay 差异属于 6.1.65→6.1.116 已出现的变化。

## 6.2 CCF / PLL provider 四版本补核（2026-11-25）

### 6.2.1 文件指纹与 callback

`clk-pll.c` blob：
- 6.1.65 / 6.1.116：`6e5e502be44a63afdcf1044766a1f75d6ab953b3`（相同）
- c2f148d：`f6d9d199acd81860fbf25b3b330ca33da1705af0`
- 6.12.81：`a6b1d8a1ce459369d4c9eeca3349a3b01212e86b`

四版本 `clk-rk3568.c` 均将 RK3568 GPLL 注册为 `PLL(pll_rk3328, PLL_GPLL, "gpll", ...)`，使用 RK3328/RK3036 PLL ops family。
- 6.1.65 / 6.1.116：enable 清除 PWRDOWN → wait lock → 返回；disable 直接设置 PWRDOWN。
- c2f148d / 6.12.81：enable 在 wait lock 后调用 mux `set_parent(PLL_MODE_NORM)`；disable 前调用 `set_parent(PLL_MODE_SLOW)`。
- 四版本 `clk-mux.c` blob 完全相同；common CCF 的 0→1/1→0 enable 引用计数及 parent recursion 语义相同。

### 6.2.2 Panther GMAC1 关系与证据边界

GMAC1 ACLK/PCLK 的 parent 分别为 `aclk_usb` / `pclk_usb`；后者以 `aclk_usb` 为 parent。ACLK_USB 可从 GPLL 派生时钟中选 parent，但 Panther DTS 没有为 ACLK_USB 静态指定 parent。既有 GPLL/ACLK_USB closeout 已核实 PCLK_USB critical parent-chain 初始化发生在 CRU clock registration 阶段；若该 parent chain 选中 GPLL，callback 属于 CRU 初始化阶段，而不是 GMAC probe 首次启用时。没有 Panther 6.1.174 启动周期的 ACLK_USB parent / PLL mode readback。

c2f148d / 6.12.81 还将 NPLL 标记为 `CLK_IS_CRITICAL`，而 6.1.65 / 6.1.116 未标记；NPLL 不在 GMAC1 已知 ACLK_USB parent 备选列表内，不应关联到 GMAC1。

### 6.2.3 CCF 子项结论

- **已验证：** 6.1.65 与 6.1.116 PLL provider 实现相同；后期两个故障源码采用 enable 后切 NORMAL、disable 前切 SLOW。
- **已验证：** CCF mux/common 引用计数机制没有与上述差异同源的新增回归。
- **未验证：** 故障启动时 ACLK_USB 实际 parent、PLL wrapper mode、PLL callback 实际调用次数与时间。
- **定级：** PLL provider 差异是后期 BSP 分组变化，不能单凭静态代码证明影响 Panther GMAC TX；不安排设备读取或实机验证。


## 6.3 Rockchip glue probe / setup / power handoff 四版本实际路径复核（2026-11-25）

### 6.3.1 Panther 实际命中的设备与 PHY 条件

四版本 Panther DTS 的 GMAC1 节点内容一致（SoC DTS blob 分组已见 §3）：
- compatible = "rockchip,rk3568-gmac"，命中驱动 rk3568_ops；
- phy-mode = "rgmii"，命中 plain RGMII case；
- clock_in_out = "input"；
- tx_delay = <0x30>、rx_delay = <0x10> 均显式提供，setup 中的缺省 delay 值不命中；
- phy-supply = <&vcc_3v3>；
- phy-handle = <&rgmii_phy1>，PHY 节点为标准外接 Clause 22 PHY，未声明 phy-is-integrated；
- rockchip,grf 与 reset GPIO 等板级资源在 DTS 中提供。

因此下文只把 plain-RGMII、外部 PHY、clock-input 分支作为实际路径。Integrated PHY、RMII、SGMII/QSGMII 和缺省 delay 分支均不作为 Panther 当前路径结论。

### 6.3.2 probe 与 setup 的分组差异及适用性

- 6.1.65 / 6.1.116：dwmac-rk.c blob 完全相同，probe 顺序为 match → resources → stmmac_probe_config_dt() → rk_gmac_setup() → clock init → powerup → stmmac_dvr_probe()。
- c2f148d：probe 增加 sph_disable、get_eth_addr、integrated_phy_power 等 platform-data 设置，调用 rk_gmac_csu_init()，并创建 loopback sysfs；这些是后期 glue 功能变化。对 Panther 当前外接 PHY/plain-RGMII 路径，integrated-PHY 专属处理不命中；SPH 和 MAC address source 不等同于 RGMII TX clock/data path；CSU 处理已由既有 CSU 报告覆盖，不重复扩展。
- 6.12.81：延续上述后期 probe 结构，使用 devm_stmmac_probe_config_dt() 与 STMMAC_FLAG_SPH_DISABLE；这些差异不改变 Panther DTS 的 RGMII 选择条件。
- c2f148d 与 6.12.81 的 setup 增加/扩展了对 GRF handle 的处理；6.12.81 对 rockchip,grf lookup 失败会直接返回错误，c2f148d 的对应路径仍以旧式 handle 检查/回调处理。Panther 四版 DTS 均提供 GRF phandle，静态 DTS 不显示缺失，因此不能把该错误路径作为当前已发生故障的解释。

### 6.3.3 regulator 与 runtime-PM handoff

四版本 rk_gmac_phy_power_on() 的错误处理语义相同：
- 调用 regulator_enable() / regulator_disable()；
- 失败时只输出错误日志；
- 函数最终仍返回 0。

因此 regulator enable/disable 失败会被 glue helper 屏蔽，rk_gmac_powerup() 不会因 regulator helper 返回值获知该失败。这是四版本共同存在的错误传播弱点，不是 6.1.116→6.1.174 新增差异。四版本 rk_gmac_powerup() 也均调用 pm_runtime_get_sync() 而不检查其返回值；该点同样是共同风险，不可归为后期单独回归。

四版本外部 PHY 路径的主 handoff 顺序均为：
1. rk_gmac_check_ops()；
2. GMAC clocks enable；
3. plain-RGMII callback 写入 GRF interface/delay；
4. rk_gmac_phy_power_on(..., true)；
5. pm_runtime_get_sync()；
6. stmmac_dvr_probe()。

当 regulator helper 返回失败时，当前代码仍会继续 runtime-PM get 与 STMMAC probe。现有历史记录没有 regulator return code 或电源轨测量，不能推断历史启动时确实发生过失败。

### 6.3.4 probe 错误回滚边界

四版本在 rk_gmac_powerup() 失败时均通过 probe 错误路径移除 DT config；若 stmmac_dvr_probe() 失败，则调用 rk_gmac_powerdown()。后期版本增加 loopback sysfs 创建/清理步骤；这不是正常网络收发路径。早期与后期 devm_stmmac_probe_config_dt() 资源管理差异需结合 STMMAC core 生命周期看待，不应简单视为 GMAC TX 差异。

### 6.3.5 本子项结论

- **已验证：** 四版本 Panther 都命中 rk3568_ops 的 plain-RGMII、外部 PHY、clock-input 路径；显式 delay 值使 setup 缺省值分支不适用。
- **已验证：** 6.1.65 与 6.1.116 的 glue 文件完全相同；c2f148d/6.12.81 有后期 probe 功能扩展。
- **已验证：** regulator helper 屏蔽 regulator enable/disable 错误、runtime-PM get 返回值未检查，是四版本共有弱点，不是故障版本新增差异。
- **未验证：** 历史 regulator 操作返回值、PM runtime 实际状态、GRF 写入返回值与运行时寄存器状态。
- **定级：** 未发现 probe/handoff 顺序在 6.1.116→c2f148d 之间整体重排；共同错误传播弱点不能解释版本分组回归，保留为代码风险背景。

## 6.4 RK3568 RGMII callback 写寄存器顺序：四版本补齐

既有 2026-11-19 报告已比较 6.1.116 与 6.12.81。本轮补齐 6.1.65 与实际故障源码 c2f148d：
- 6.1.65 / 6.1.116：rk3568_set_to_rgmii() 先写 GMAC1_CON0 的 delay 数值，再写 GMAC1_CON1 的 RGMII interface 与 RX/TX delay enable。
- c2f148d / 6.12.81：先写 GMAC1_CON1 的 interface 与 delay enable，再写 GMAC1_CON0 的 delay 数值；后期实现通过 DELAY_ENABLE() / DELAY_VALUE() 宏支持负值 sentinel。

Panther 的 tx_delay=0x30、rx_delay=0x10 均为正值，四版本最终选择的 RGMII interface、delay 数值及 RX/TX delay enable 语义相同；差异在寄存器写入顺序。该顺序变化首次出现在本矩阵的故障源码 c2f148d 相对黄金基准 6.1.116，因此是一个真实的版本回归候选，不能因最终值相同而删除。

但四版本 rk_gmac_powerup() 都先完成 clocks enable，再执行 RGMII callback，之后才打开 PHY regulator。没有 GRF 总线事务时间、PHY 上电瞬间波形或 RGMII 信号测量，故尚不能判断“先 enable、后写 delay”是否导致外部 PHY 可见异常。沿用既有报告的低至中优先级，不升级为根因结论。

## 6.5 本轮总判断与后续审校任务

本轮补核没有发现四版本 probe/powerup 主流程整体重排，也没有发现 regulator helper 的错误传播语义在故障版本发生变化。实际版本差异仍集中于：
1. clocks enable API、错误检查与稳定等待（§4.1）；
2. RGMII GRF 两寄存器写入顺序（§6.4）；
3. 相关 CRU/CCF provider 变化及其尚未证实的调用条件（§6.2）。

当时尚待完成总矩阵一致性审校；后续完成情况见 §6.6、§6.7、§6.8 和 §8，本报告最终结项决定见 §10。


## 6.6 方向四四版本总矩阵（第一轮审校版）

| 审计点 | 6.1.65 黄金 A | 6.1.116 黄金 B | 6.1.174 故障 A（c2f148d） | 6.12.81 故障 B | 首次分组差异与解释 |
|---|---|---|---|---|---|
| Rockchip glue 文件 | blob 与 6.1.116 相同 | blob 与 6.1.65 相同 | 后期重构 | 后期重构 | 黄金与故障源码形成两组 |
| GMAC clocks 获取/enable | bulk 获取、bulk enable | 同 6.1.65 | 逐项获取、逐项 enable | 同后期路径 | 本矩阵最早观察到于 c2f148d；逐项 enable 返回值未检查，clock 获取失败主要只记录错误 |
| clock settle | 5ms | 5ms | 100–200µs | 100–200µs | 本矩阵最早观察到于 c2f148d；静态证据不能证明等待时间不足 |
| RGMII callback 写序 | CON0 delay value → CON1 interface/enable | 同 6.1.65 | CON1 interface/enable → CON0 delay value | 同 c2f148d | 本矩阵最早观察到于 c2f148d；最终数值/enable 语义相同，只有写入顺序不同 |
| PHY regulator helper | 失败只日志、返回 0 | 同左 | 同左 | 同左 | 四版本共同弱点，不是版本回归 |
| runtime-PM get | pm_runtime_get_sync 返回值未检查 | 同左 | 同左 | 同左 | 四版本共同弱点，不是版本回归 |
| GMAC1 CRU mux/divider/gate | 与其他三版相同 | 相同 | 相同 | 相同 | 未发现 GMAC1 专属定义回归 |
| HCLK_USB critical | 无 | 无 | 有 | 有 | 后期 provider 标记；HCLK_USB 不在 GMAC1 已确认 parent chain |
| PCLK_USB critical | 无 | 无 | 有 | 有 | 后期 provider 标记；PCLK_USB→ACLK_USB 与 GMAC1 共用上游，可能改变 CRU 初始化时引用/启用基线；active TX 影响未验证 |
| GMAC1 reset ID/provider | ID 236；30 regs；HIWORD | 相同 | 相同 | 相同 | 未发现 reset ID/provider 回归 |
| STMMAC reset 后 10µs delay | 无 | 有 | 有 | 有 | 6.1.116 已存在，不能解释 6.1.116→6.1.174 首发故障 |
| GPLL provider callback | wait lock 后返回；disable PWRDOWN | 同左 | wait lock 后切 NORMAL；disable 前切 SLOW | 后期实现 | 本矩阵最早观察到于 c2f148d；是否命中 GMAC1 实际 parent chain 未验证 |
| RGMII speed callback | 10/100/1000→2.5/25/125MHz | 同左 | 同左 | 同左；回调签名增加未使用 mode 参数 | rate mapping 不变；handle 获取/存储方式随 glue 重构变化；运行时 clk_set_rate 未验证 |
| powerdown/suspend/resume | 外接 PHY 顺序 runtime-PM put→regulator off→clock off | 同左 | 同左；移除仅供 integrated-PHY 的 powerdown 调用 | 同 c2f148d | Panther 未声明 integrated PHY，变化不命中当前路径；外接 PHY 顺序相同 |
| Panther GMAC1 DTS | RGMII/input/125MHz/0x30/0x10 | 同 6.1.65 | 同关键语义 | 同 c2f148d | DTS 关键配置保持一致 |

### 6.6.1 本轮审校后的优先级与边界

- **已确认且与故障版本分组一致的 glue 差异：** bulk→逐项 clock enable、错误检查减弱、5ms→100–200µs settle、RGMII CON0/CON1 写入顺序反转。它们是静态源码回归候选，不等于已经证明硬件因果。
- **已确认但影响边界不同：** HCLK_USB critical 与 GMAC1 parent chain 无直接关系；PCLK_USB critical 保持与 GMAC1 共用的 ACLK_USB 父链；若 ACLK_USB 选择 GPLL，可能与后期 GPLL callback 变化形成注册期时序联动，但实际 parent/callback 未知；active TX 影响未验证。
- **已确认但不是 6.1.116→6.1.174 新增：** regulator helper 错误吞并、runtime-PM get 返回值未检查；STMMAC 10µs reset delay 在 6.1.116 已存在。
- **已排除为当前源码差异解释：** GMAC1 专属 CRU mux/divider/gate、reset ID/provider 映射、Panther DTS RGMII 输入配置。
- **保留未验证：** 历史实际 clock enable 返回值、clock rate/gate readback、GRF 写事务与寄存器值、PHY 电源轨、runtime-PM 状态、PLL parent/mode、RGMII 波形。

**注意样本身份：** 6.1.65 的源码端点仍是高置信度候选，不是历史 Image source commit 的闭环证明；6.1.116 也保留其历史安装包 source binding 边界。故本矩阵中 6.1.65/6.1.116 的源码对照事实与历史二进制来源证明必须分开表述。


## 6.7 CCF 对 CLK_IS_CRITICAL 的实际语义四版本复核

本轮继续直接检查四版本 drivers/clk/clk.c，而不是只从 Rockchip provider flag 推断效果：

- 四版本均在 clock core 注册阶段识别 CLK_IS_CRITICAL，对 critical clock 执行 prepare + enable；
- 四版本 clk_core_disable() 均阻止将 critical clock 的最后一个 enable reference 降至 0；
- 四版本 clk_core_unprepare() 均阻止将 critical clock 的最后一个 prepare reference 降至 0；
- 6.12.81 的 trace helper 名称有调整，但上述 critical reference 保护语义保持一致。

因此这不是一个“仅影响日志/unused 标记”的装饰性 flag，而是实际保持 clock prepare/enable reference 的机制。结合 §4.2 的 parent topology：
- HCLK_USB critical 会保持 HCLK_USB 及其所选 parent 链；它不属于已确认的 GMAC1 ACLK/PCLK 依赖链。
- PCLK_USB critical 会保持 PCLK_USB，并通过 parent recursion 保持 ACLK_USB parent；该 ACLK_USB 同时是 ACLK_GMAC1 的 parent。因此 PCLK_USB critical 确实可能改变 GMAC1 共用上游 ACLK_USB 在 CRU 初始化阶段的引用计数/启用状态。
- GMAC1 probe 启用 ACLK_GMAC1/PCLK_GMAC1 时也会按 CCF parent recursion 启用对应 parent；所以在 MAC 正常 active 后，critical 与 consumer enable 是否导致额外硬件状态差异，不能从源码 flag 单独推出。

**结论等级：**
- **已验证：** 四版本 CCF critical flag 的 prepare/enable 与最后引用保护语义相同；后期 RK3568 provider 新增的 HCLK_USB/PCLK_USB flags 会触发这套既有机制。
- **已验证：** HCLK_USB 不在 GMAC1 已确认 parent chain；PCLK_USB → ACLK_USB 与 ACLK_GMAC1 共用上游 parent；ACLK_USB 的四个候选 parent 在四版本一致。
- **条件性关联：** 若历史 ACLK_USB parent 为 GPLL，后期 PCLK_USB critical 的注册期 enable 可能使后期 GPLL callback 提前执行；实际 parent、callback 调用时序均未知。
- **未验证：** 历史启动时 ACLK_USB 的实际 parent、PCLK_USB/ACLK_USB 的 enable_count 与 gate readback、CRU provider 注册和 GMAC probe 的先后时序、GPLL callback 实际调用次数/时刻，以及该初始化差异是否影响故障发生窗口。
- **不得推断：** 不把 PCLK_USB critical 标记直接认定为 TX 故障根因；不把 HCLK_USB critical 与 GMAC1 时钟链建立因果联系。


## 6.8 RGMII speed callback 与 suspend/resume 四版本补充闭环

本轮补齐此前历史专题只做两版本比较、方向四矩阵未单列的 glue speed callback 与 powerdown/resume 分支。

### 6.8.1 RGMII link-speed callback

四版本实际 Panther 条件均为 RK3568 ops + plain RGMII：
- `rk_fix_speed()` 对 RGMII/RGMII_ID/RGMII_RXID/RGMII_TXID 调用 `ops->set_rgmii_speed`；6.1.65、6.1.116、c2f148d 的函数签名相同，6.12.81 增加 `mode` 参数但函数体不使用该参数。
- 四版本 `rk3568_ops.set_rgmii_speed` 均绑定 `rk3568_set_gmac_speed`。
- 四版本 speed→rate 映射相同：10Mbps→2.5MHz、100Mbps→25MHz、1000Mbps→125MHz；未知 speed 记录错误并返回。
- 四版本均调用 `clk_set_rate()`，失败时记录错误，不向调用者传播返回值。
- 黄金版本通过 `bsp_priv->clks[RK_CLK_MAC_SPEED].clk` 取得 clock handle；后期源码改为独立的 `bsp_priv->clk_mac_speed` 字段。后期 clk init 对该 handle 获取失败只记录错误，speed callback 本身仍直接调用 `clk_set_rate`。这与 §4.1 的逐项 clock 获取/错误传播弱化属于同一后期 glue 重构背景；本轮未发现 speed→rate 数值映射变化。
- Panther DTS 的 `clock_in_out = "input"` 与外部 125MHz fixed-clock 配置保持一致；该配置不能被解释为 speed callback 不执行，也不能据静态源码推断历史 `clk_set_rate` 实际返回值或最终 mux/rate readback。

**结论等级：**
- **已验证：** 四版本 RGMII speed callback 绑定关系与 10/100/1000Mbps rate mapping 一致；6.12 仅增加未使用的 mode 参数。
- **已验证：** `clk_set_rate` 错误均只记录、不向上返回，是四版本共有行为。
- **已验证：** clock handle 的存储/获取方式随后期 glue 重构改变，属于既有 clock acquisition/error-handling 差异的延伸，不构成独立的 rate mapping 回归。
- **未验证：** 历史 link speed callback 是否执行、`clk_set_rate` 返回值、CCF 实际 rate/mux 与硬件输出频率。
- **适用性：** 只讨论 Panther RGMII 分支；RMII/S/ QSGMII 其他 interface 分支不据此外推。

### 6.8.2 powerdown / suspend / resume

四版本 `rk_gmac_suspend()` 的主顺序一致：先调用 `stmmac_suspend()`；若设备不允许 wakeup，则执行 `rk_gmac_powerdown()` 并设置 `suspended=true`。四版本 `rk_gmac_resume()` 均在 `suspended` 为 true 时执行 `rk_gmac_powerup()`、清除标记，最后调用 `stmmac_resume()`。

6.1.65/6.1.116 的 `rk_gmac_powerdown()` 在 runtime-PM put 前有 integrated-PHY 专属 powerdown 条件；c2f148d/6.12.81 的该 helper 不再保留该调用。Panther DTS 未声明 integrated PHY，故该差异不命中 Panther 外接 PHY 路径。四版本对 Panther 外接 PHY 的 powerdown 顺序均为 runtime-PM put → regulator disable helper → GMAC clock disable。

**结论等级：**
- **已验证：** Panther 外接 PHY 的 suspend/resume 与 powerdown 主路径没有发现 6.1.116→c2f148d 新增的调用顺序回归。
- **已验证：** integrated-PHY 专属 powerdown 调用变化不适用于 Panther 当前外接 PHY。
- **未验证：** 历史是否进入 suspend/resume、wakeup policy、runtime-PM 实际状态及 suspend/resume 期间的 clock/regulator 返回值。
- **定级：** 不作为当前普通启动 TX 回归候选；保留为非命中 Panther 当前配置的差异说明。


## 8. 与方向二、方向三的交叉一致性审校（2026-11-25）

本节只核对边界、术语、版本端点和跨层结论是否冲突；不重做方向二 generic network-core 或方向三 STMMAC/DWMAC4/DMA 已结项的函数审计。

### 8.1 三方向职责边界

| 方向 | 已批准审计层 | 本方向可引用内容 | 不在本方向重复的内容 |
|---|---|---|---|
| 方向二 | Linux generic network-core | 普通 DHCP/UDP TX 的 generic queue/qdisc/validate/ndo 之前适用性、generic TX queue/watchdog 证据限制 | Rockchip glue、STMMAC 私有 descriptor/DMA、CRU/CCF |
| 方向三 | STMMAC / DWMAC4 / DMA | platform probe/resource parsing、MAC/DMA reset、descriptor/DMA/IRQ/NAPI 证据 | Rockchip glue 的完整 clocks/power/CRU/PLL provider 专题、PHYLIB/PHYLINK/RTL8211F |
| 方向四 | Rockchip GMAC glue / CCF / CRU / clock / reset | glue clocks enable、RGMII GRF callback、公共/专属 clock parent/gate、PLL callback、reset provider | generic network-core TX、STMMAC descriptor/DMA lifecycle、MDIO/PHY driver 专题 |

### 8.2 方向二交叉核对

方向二 §53～§56 已正式有条件结项。其“未发现已证实且无条件命中普通 DHCP/UDP TX 的 generic network-core 回归”只覆盖 Linux generic network-core 层，不是对 Rockchip glue 或 STMMAC 私有路径的排除。

方向四发现的 bulk→逐项 clock enable、错误检查变化、5ms→100–200µs settle 和 RGMII GRF 写入顺序变化均发生在 Rockchip glue/平台初始化层，不与方向二结论冲突，也不能被方向二的普通 DHCP/UDP 适用性结论排除。

方向二记录的 generic TX queue stop/watchdog、可选 packet-mangle hook 和 6.12 unreadable-fragment 条件门，继续保持方向二原有证据等级；本方向不把它们移入 CRU/clock 根因链。

### 8.3 方向三交叉核对

方向三 D3-1～D3-8 已按证据边界明确的有条件结项归档。方向四只复用其 platform resource 与 reset 相关事实，不重做 STMMAC/DWMAC4/DMA 函数审计。

特别区分以下两组时间差异：

- **方向三 DMA reset 时序：** 黄金版本在 DWMAC4 DMA reset 前有 1500ms delay，故障源码缺失；reset poll interval 从 10ms 缩短至 0.5ms。它属于 MAC/DMA core reset sequence。
- **方向四 GMAC glue clocks settle：** 黄金版本 bulk clock enable 后等待 5ms；故障源码逐项 enable 后等待 100–200µs。它属于 Rockchip glue clock initialization。

二者的调用层、等待对象和执行位置不同。现有静态证据不允许把两者合并成一个“总初始化延时不足”结论，也没有证据证明任一等待时间单独导致历史 TX 故障。

方向三报告中关于 pclk / pclk_mac 资源名称及 MDC CSR clock source 的差异，属于 STMMAC platform resource / MDC 配置证据；方向四的 ACLK_GMAC1/PCLK_GMAC1 与 ACLK_USB/PCLK_USB 是 RK3568 CRU 总线 clock provider 层。命名相似不代表同一 clock handle 或同一硬件时钟，禁止将二者直接等同。

方向三的四次 PHYCR2/BMCR MDIO workaround 写入差异继续作为方向三保留的 PHY 初始化候选；方向四不据此推断 regulator、PLL 或 RGMII GRF 写入的因果关系。

### 8.4 版本端点和证据等级一致性

方向二、方向三、方向四继续使用同一四版本比较矩阵：
- 6.1.65：高置信度源码候选，未与历史 Image 精确绑定；
- 6.1.116：源码比较端点，历史 Image source commit 绑定仍有限制；
- 6.1.174-rk35xx：实际构建源码 c2f148dece4b67ebd30aefad1bdd1990f41e5633；
- 6.12.81-rk35xx：已确认源码端点 661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

本轮未发现三个方向对上述样本身份的表述冲突。方向四的“本矩阵最早观察到于 c2f148d”仅表示四个锁定源码端点中的分组首次差异，不宣称上游真实引入版本或最早故障小版本。

### 8.4.1 GPLL 是否自身 critical：条件链的进一步排除

再次核对四版本 RK3568 CRU PLL descriptor：
- GPLL descriptor 四版本的 flags 均为 0，GPLL 自身没有 CLK_IS_CRITICAL；
- NPLL 在 6.1.65/6.1.116 flags 为 0，在 c2f148d/6.12.81 增加 CLK_IS_CRITICAL；NPLL 不属于 ACLK_USB 已确认的 parent candidates；
- 因而不能以“GPLL 自身已被 critical 保持”为理由排除 PCLK_USB parent recursion；但也不能据此断言 PCLK_USB 注册必然触发 GPLL callback。

更精确的条件是：若 PCLK_USB 注册时实际 parent chain 选中 GPLL，且当时 GPLL 的 CCF enable reference 尚为 0，则 parent recursion 的 0→1 transition 会触发对应 GPLL enable callback；若 GPLL 已由其他 consumer 持有 enable reference，则不会因 PCLK_USB 注册再次执行 0→1 callback。历史 enable_count、ACLK_USB mux readback 与 provider 注册时序均缺失，因此该路径仍为条件性推论。

### 8.5 交叉审校结论

- **未发现方向二与方向四的层级结论冲突。**
- **未发现方向三与方向四的 reset / clock 概念可直接合并的依据；两组 delay 必须分别记录。**
- **未发现四版本源码端点和来源证据等级冲突。**
- **跨方向未决事项继续按原报告归属，不因引用而转移结项状态。**
- 本节完成跨方向一致性检查；其后补充的 speed callback 与 suspend/resume 核对见 §6.8。


## 9. 安全与范围声明

- 不访问 Panther X2，不执行设备命令，不读写寄存器，不进行网络测试。
- 不修改任何系统、内核、驱动、DTS、Kconfig 或网络服务。
- 不构建、不安装、不触发 Actions。
- 不启动 B2.1，不进入方向五 MDIO/PHYLIB/PHYLINK/RTL8211F 专题。
- 不把静态源码差异等同于故障根因；所有历史源码身份、最终配置和运行时证据边界继续保留。


## 10. 方向四结项评估与决定（2026-11-25）

### 10.1 原定静态审计范围完成情况

| 原定审计子项 | 结果 | 证据边界 |
|---|---|---|
| 历史报告回读、重复项排除、四版本源码身份固定 | 完成 | §2、§3；保留 6.1.65/6.1.116 历史构建绑定限制 |
| Rockchip GMAC glue clocks 获取、enable/disable、错误传播与 settle | 完成 | §4.1、§6.6；实际返回值/时钟 readback 未知 |
| Panther 实际 DTS 与 RGMII/plain external PHY/input 分支确认 | 完成 | §4.3、§6.3 |
| RK3568 GMAC1 CRU parent/mux/divider/gate | 完成 | §4.2；静态定义一致，不代表运行时 readback |
| CRU reset consumer、ID、provider、寄存器映射 | 完成 | §6.1；ID 236 与 provider 映射一致 |
| CCF critical reference 与 PLL provider/callback | 完成 | §6.2、§6.7、§8.4.1；实际 parent/reference/callback 时序未知 |
| probe/setup、regulator、CSU/genpd、runtime-PM handoff | 完成 | §6.3 与既有方向 glue/power 归档；硬件电源状态未测量 |
| RGMII GRF interface/delay callback 写入顺序 | 完成 | §6.4；寄存器事务/波形未知 |
| RGMII link-speed callback | 完成 | §6.8.1；历史 clk_set_rate 结果未知 |
| powerdown/suspend/resume | 完成 | §6.8.2；历史是否进入相关路径未知 |
| 与方向二、方向三跨层一致性核对 | 完成 | §8；未发现结论冲突，边界已明确 |
| 四版本总矩阵、优先级与证据等级 | 完成 | §6.6、§6.6.1 |

### 10.2 结项结论

**方向四按“证据边界明确的有条件结项”归档。**

本轮四版本静态源码比较确认，黄金组（6.1.65/6.1.116）与故障组（c2f148d/6.12.81）之间存在以下真实分组差异：
1. GMAC clock 获取/enable 从 bulk 路径变为逐项获取/enable，错误检查与传播减弱；
2. clocks enable 后 settle 从 5ms 缩短为 100–200µs；
3. RGMII GRF CON0/CON1 写入顺序反转；
4. HCLK_USB 与 PCLK_USB 新增 CLK_IS_CRITICAL；其中 HCLK_USB 不在已确认 GMAC1 parent chain，PCLK_USB 与 GMAC1 共用 ACLK_USB 上游；
5. GPLL enable/disable callback 改为 wait-lock 后切 NORMAL、disable 前切 SLOW；只有在 ACLK_USB 实际选择 GPLL 且 GPLL enable reference 当时为 0 等条件满足时，才可能与 PCLK_USB critical 注册期 parent recursion 联动。

同时确认：
- GMAC1 专属 CRU mux/divider/gate、reset ID 236/provider mapping 与 Panther DTS RGMII 关键输入配置没有发现可解释版本故障的确定性回归；
- RGMII 10/100/1000 speed-rate mapping 四版本一致；
- regulator helper 与 runtime-PM 错误传播弱点是四版本共同项；
- Panther 外接 PHY 的 powerdown/suspend/resume 路径没有发现故障组新增的适用性回归；
- CSU 对 Panther 当前 DTS 无 phandle、调用为 no-op；无独立 GMAC power-domain 绑定。

这些结论均为源码/DTS/既有配置的静态结论。没有证据证明 clock enable 实际失败、100–200µs 必然不足、GRF 写入顺序造成电气异常、PCLK_USB/GPLL 条件链在历史故障启动中实际命中，或任一差异已经构成 TX 根因。

### 10.3 结项后保留的未验证事项

- 6.1.65 与 6.1.116 历史 Image 的精确 source commit 绑定限制；
- 历史 clock enable / clk_set_rate 返回值、实际 clock rate、mux/gate readback；
- ACLK_USB 实际 parent、GPLL mode/reference count 与 callback 时序；
- GRF 写入事务顺序在硬件总线上的实际完成情况、RGMII/PHY 波形；
- PHY regulator 实际输出、电源质量、runtime-PM 状态；
- reset 硬件脉冲宽度及历史运行时 reset 状态。

这些缺口来自历史现场运行时证据缺失或源码 provenance 限制；不要求为完成静态审计而重复既有工作，也不构成访问设备或开展 B2.1 的授权。

### 10.4 范围与后续阶段门

方向四结项仅关闭 B2-0 原组件方向 B2-3 的静态源码审计。方向五（MDIO/PHYLIB/PHYLINK/RTL8211F PHY driver，对应原组件方向 B2-4）仍未开始；版本决策与组件恢复顺序整合也未开始。

本结项不启动 B2.1，不访问 Panther X2，不构建、不安装软件、不修改系统/驱动/DTB/网络配置，不读写设备寄存器。进入方向五须遵循 B2-0 原始顺序，等待用户明确指示。

