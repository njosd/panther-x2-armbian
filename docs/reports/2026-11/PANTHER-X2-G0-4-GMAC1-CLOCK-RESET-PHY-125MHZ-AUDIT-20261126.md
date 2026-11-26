# Panther X2 项目 A — G0.4 GMAC1 Clock / Reset / PHY 125MHz 来源审计（2026-11-26）

- 状态：**G0.4 静态依赖审计完成；物理 125MHz 来源/波形未验证；条件结项。**
- 范围：复用 R6-1 至 R6-5 已完成源码、DTS、DTB、CRU、TRM 证据；不重复计算已确认的 clock ID/GRF bit/reset ID，不访问硬件。
- 未执行：没有启用 GMAC/MDIO/PHY，没有读取/写入 CRU、GRF、PHY 寄存器，没有驱动 PHY reset，没有外部探测测量，没有发包。

## 1. GMAC1 clock framework 静态链

Panther board DTS 声明：
- `gmac1_clkin` 是独立根节点 `fixed-clock`，频率 125,000,000 Hz；
- clock name 为 `gmac1_clkin`；
- GMAC1 `clock_in_out = "input"`；
- `assigned-clock-parents` 将 `SCLK_GMAC1` 的 parent 指向该 fixed-clock；
- GMAC1 使用 `SCLK_GMAC1_RX_TX`、`SCLK_GMAC1_RGMII_SPEED`、`SCLK_GMAC1` 三个 assigned clocks。

R6 已核实 6.1.65 与 6.18.63 对应 CRU clock IDs、mux/gate 位置与 parent 列表一致：
- ACLK_GMAC1=195，PCLK_GMAC1=196；
- SCLK_GMAC1=390，SCLK_GMAC1_RGMII_SPEED=391，SCLK_GMAC1_RMII_SPEED=392，SCLK_GMAC1_RX_TX=393；
- SCLK_GMAC1 parent 为 `clk_mac1_2top` 或 `gmac1_clkin`，Panther DTS 选择后者；
- 6.18 RK3568 的 `rk_configure_io_clksel()` 对本 SoC ops 为 no-op，不应套用其他 Rockchip SoC 的 IO clock select 行为。

**重要纠正已完成：** RK809 CLKOUT1/CLKOUT2 是独立 provider；Panther DTS 没有把 RK809 CLKOUT phandle 连接到 `gmac1_clkin`。因此不能把“RK809 CLKOUT 输出 125MHz”作为已知时钟链。

fixed-clock provider 只把 DT 的 125MHz 注册到 Linux CCF；它不产生振荡，也不测量输入 pin。故软件 parent/rate 配置静态 PASS，不代表实体 125MHz 存在。

## 2. 物理 125MHz 来源：RTL8211F CLKOUT 仅为候选

既有 R6-5 与 PHY clock handoff 证据支持一个候选链：
`RTL8211F CLKOUT pin35 → PCB trace → RK3566 GMAC1 external clock input → gmac1_clkin CCF parent → SCLK_GMAC1`。

但尚未证实：
- Panther PCB 是否确实把 RTL8211F pin35 连到 RK3566 对应 GMAC1 clock input；
- pin35 是否在当前启动/PHY reset/config_init 后输出 125MHz；
- PHYCR2 相关 CLKOUT enable/频率选择位在 generic PHY soft reset 后是否保持；
- 波形的频率、幅度、占空比、抖动/稳定性是否满足接口要求。

R6 既有对照指出 6.1.116 曾出现 JL2xx1 workaround 写入 PHYCR2=0x1801；6.1.65/6.18 通用 RTL8211F driver 对 PHYCR2 的常规处理不等于已证明会设置 125MHz 选择位。此处不把 workaround 直接复制到 6.18，也不建议先写 PHYCR2。

## 3. GMAC1 reset 与 pin 电平域

- GMAC1 SoC reset：`SRST_A_GMAC1` ID 236；R6 已静态映射到 CRU reset bank14/bit12、寄存器偏移 0x438；6.1.65/6.18 reset provider hiword assert/deassert 逻辑一致。
- PHY reset：`GPIO3_PA1`，active-low；DTS 声明 reset delays `<0 20000 100000>`，即 assert 前等待 0、assert 20ms、deassert 后等待 100ms 的驱动时序语义（具体调用顺序仍以 R6 glue 代码为准）。
- GMAC1 M0 所有 pinctrl signals 位于 GPIO3 bank；Rockchip RK3568 Hardware Design Guide Rev V1.2 将 GMAC1 M0 归属 VCCIO5。因此 GPIO3_PA1 PHY reset pin 也属于 GPIO3/VCCIO5 bank 的电平域。
- VCCIO5 DTS supply 与 GMAC1 phy-supply 都指向 `vcc_3v3` / RK809 SWITCH_REG1；实际 rail 电压、板上连接和 reset 波形尚未测量。

不得仅凭 GPIO provider/gpiochip 已注册就认为 GPIO3_PA1 的电气输出、复位极性和外部 PHY pin 电平已通过。也不得在未授权情况下主动切换 GPIO/reset。

## 4. RGMII delay 与 GRF 状态

R6 已核实：
- CON0 offset 0x0388，RX delay bits[14:8]、TX delay bits[6:0]；
- CON1 offset 0x038c，delay enable bits0/1；
- DTS TX delay=0x30、RX delay=0x10；
- CON1 bit7 经 RK3568 TRM 确认为 gmac1_qsgmii_mode，RW，reset=0；0=RMII/RGMII，1=SGMII/QSGMII。6.18 显式清零，6.1.65 RGMII 路径依赖 reset default；两版最终目标模式一致。

这些是静态寄存器定义/软件写入证据，不证明当前寄存器值、板级 RGMII 波形、TX/RX 时序 margin 或 PCB signal integrity。

## 5. 黄金基线对照与当前结论

| 项目 | 6.1.65 / 6.1.116 | 6.18.63 | 状态 |
|---|---|---|---|
| CRU clock IDs/mux/gate/parent | 既有静态对照一致 | 固定源码/DTB确认 | STATIC PASS |
| DTS fixed-clock | 125MHz input model | 同一设计意图 | STATIC PASS |
| RK809 CLKOUT→GMAC | 无 DTS phandle 连接 | 无 DTS phandle 连接 | 已排除该声明链 |
| RTL8211F CLKOUT pin35 实际输出 | 黄金整机工作，但无对应波形记录 | 无波形记录 | UNKNOWN |
| GMAC1 CRU reset | ID/provider 语义一致 | 同 | STATIC PASS |
| PHY reset GPIO3_PA1 | active-low DTS 属性 | 同 | STATIC PASS；电气行为未验证 |
| RGMII delay/mode | DTS delay一致；bit7依赖reset default | 显式清bit7 | 最终目标一致；运行时值未验证 |

## 6. 首次外部测量方案（未来单独授权，不是本轮操作）

进入 R7-A 前先寻找 Panther X2 原理图、PCB netlist 或厂商资料，确认 RTL8211F CLKOUT pin35 与 RK3566 GMAC1 input 的真实连线和可接触测试点。若无法取得，需单独授权高阻探测：

1. 先在不改变 PHY/MAC 配置的前提下确认探头接地点、测点负载和探测带宽；
2. 对照 6.1.65 黄金系统与 6.18 候选系统，在 PHY reset 前后记录 pin35 频率、幅度、占空比和稳定性；
3. 如能安全接触 SoC clock input 端，测量两端波形是否一致；
4. PHYCR2 仅在寄存器语义/读副作用明确并另行授权后只读；本阶段不写 PHYCR2；
5. 任何需要 reset、驱动 probe、寄存器写或改变时钟路径的动作均独立授权；
6. 125MHz 不存在或波形不合格时停止，不进入 DMA/TX。

## 7. G0.4 结论与下一步

**G0.4 STATIC COMPLETE / HARDWARE UNKNOWN。** 软件时钟、reset ID、GRF delay/mode 与 DTS 关系已清楚；实体 125MHz 来源/波形、PHY reset 电气行为与实际 rail 未验证。当前不放行 R7-A。

下一项唯一任务为 **G0.5：ABCD 发送夹具与同帧观测能力审查**。复用 R1 AF_PACKET 实机 API 证据与 R5 TX traceability 源码审计，确认 A/B/C/D 同一帧的 sequence/hash 关联方式、现有 tracepoint/ftrace 可观测范围、最小诊断 instrumentation 缺口和外部对端抓包配置。此项仍只读研究/工具准备，不恢复 GMAC、不发送目标帧。
