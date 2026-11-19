# Panther X2：RGMII TX pinctrl 静态差分与后续验证设计（2026-11-19）

## 1. 目的与边界

基于用户新增的第三方接收测试，当前故障方向已收敛到 Ethernet TX。本轮补查此前尚未完全闭合的一处：6.1.116 与 6.12.81 候选之间的 Rockchip pinctrl 通用实现变化，判断它是否可能使 TX pins 未进入 GMAC 功能态。

只读取公开源码和仓库报告；未连接设备、未发送帧、未抓包、未读取寄存器、未修改设备。

## 2. Panther X2 GMAC1 pinctrl 事实

6.1.116 源码 unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e 与 6.12.81 最可信源码候选 ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c 的 Panther DTS 中，&gmac1 默认 pinctrl state 相同，均选择：
- gmac1m0_miim
- gmac1m0_tx_bus2
- gmac1m0_rx_bus2
- gmac1m0_rgmii_clk
- gmac1m0_clkinout
- gmac1m0_rgmii_bus

两版 rk3568-pinctrl.dtsi 中 GMAC1 M0 pin group 定义相同。主要 TX pins：
- GPIO3_PB5：GMAC1_TXD0，mux 3；
- GPIO3_PB6：GMAC1_TXD1，mux 3；
- GPIO3_PB7：GMAC1_TXEN，mux 3；
- GPIO3_PA2：GMAC1_TXD2，mux 3；
- GPIO3_PA3：GMAC1_TXD3，mux 3；
- GPIO3_PA6：GMAC1_TXCLK，mux 3。

RX 对应：
- GPIO3_PB1/PB2：RXD0/RXD1；
- GPIO3_PB3：RXDV/CRS；
- GPIO3_PA4/PA5：RXD2/RXD3；
- GPIO3_PA7：RXCLK。

这些 TX/RX pins 都属于 GPIO3 bank，使用 RK3568 pinctrl 的 4-bit IOMUX 配置。板级 DTS 没有显示 TX group 被移除或切换到其他 pinmux bank。

## 3. 6.12 Rockchip pinctrl 通用代码的真实变化

### 3.1 rockchip_pmx_set() 的错误处理变化

6.1：
- 遍历 pin group；
- 某个 rockchip_set_mux() 返回错误即停止；
- 只要 ret != 0 就回滚之前已成功设置的 pin，并返回错误。

6.12：
- 遍历逻辑相同；
- 回滚和错误返回条件改为 if (ret && cnt)。

这意味着：若 group 中第一个 pin 的 rockchip_set_mux() 返回错误（此时 cnt == 0），6.12 代码会跳过回滚和错误返回，最终返回 0；pinctrl core 可能把该 state 视为成功，尽管该 group 第一个 pin 未设置成功。

这是一个真实的通用代码差异，理论上可能隐藏某个 pin group 首 pin 的设置失败。但目前没有证据证明 Panther 的 TX pin 写入遇到过 regmap 错误。

### 3.2 该差异对 RK3568 GMAC pin 的适用性

进一步核对 6.12 rockchip_set_mux()：
- rockchip_verify_mux() 与 6.1 完全相同；
- GPIO3 bank 的 RK3568 IOMUX type 为 IOMUX_WIDTH_4BIT；
- GMAC pin mux 值为 3，4-bit mux 最大值为 15；
- rockchip_set_rmio() 仅在 mux 值大于该 IOMUX 可表达的最大值时才执行 RMIO 编码；GMAC mux=3 不满足条件，因此直接返回 0；
- RK3568 不命中 6.12 新增的 RK3506/RK3562/RK3572/RK3576/RK3588 特殊分支；
- RK3568 pin controller 未配置 ie_calc_reg，不会触发新增 input-enable 路径；
- 6.12 最终仍使用与 6.1 相同的 4-bit IOMUX 寄存器布局及 regmap_update_bits() 写入方式。

因此，6.12 新增的 RMIO、其他 SoC 特殊 mux 分支和 writable-32-bit IOMUX 处理不会改变 Panther RK3568 GMAC pin 的正常设置路径。

### 3.3 适用性结论

- **已确认：** 6.1/6.12 Panther GMAC pinctrl DTS group 和 pin definitions 相同。
- **已确认：** RK3568 GMAC pins 的 mux=3 不会进入 6.12 新增 RMIO 特殊编码。
- **已确认：** 正常写入情况下，RK3568 仍走与 6.1 相同的 4-bit IOMUX regmap 写入路径。
- **保留的低优先级风险：** 6.12 rockchip_pmx_set() 在 group 首 pin 写入失败时可能错误地返回成功。若 GPIO3_PB5（TXD0 group 的首 pin）等首 pin 的 regmap 写入发生错误，软件可能隐藏错误；但尚无任何错误日志或运行时证据支持该情况。由于其他 GMAC group 的首 pin也在相同 GPIO3 bank，且 RX 工作正常，这不是强根因候选。

## 4. 后续可考虑的只读验证及其证据能力

### A. pinctrl debugfs 软件归属检查

若用户日后授权，可只读查看 pinctrl debugfs 的 pinmux-pins / pinmux-functions，重点核对 GPIO3_PB5/PB6/PB7、PA2/PA3/PA6 与 RX 对应 pins 是否由 GMAC1 group 声明占用，是否存在 GPIO 或其他设备的冲突。

- 风险：低，仅读取 pinctrl debugfs 状态，不写寄存器、不改变配置。
- 能证明：Linux pinctrl framework 当前记录的 mux owner / function 归属，以及是否存在软件层 pin ownership 冲突。
- 不能证明：IOMUX 硬件寄存器的实际值，也不能证明 TXC/TXD 电气波形。
- 判定：这是唯一值得保留的低风险、只读现场核查；不是物理 TX 输出认证。

### B. 直接读取 GRF/IOMUX 寄存器

不列入验证方案。此前已发生 dummy-syscon debugfs register read 导致设备崩溃的事故；用户已禁止 devmem 和危险寄存器访问。本项目不通过 devmem、regmap debugfs 或未知 MMIO 路径读取这些寄存器。

### C. RGMII TXC/TXD 电气观测

示波器/逻辑分析仪观察 TXC、TXD[3:0]、TXEN，才可直接判断 MAC 到 PHY 的 RGMII 发送侧是否出现时钟与数据活动。它需要物理接触测试点，并通常需要触发发送活动。

- 这属于物理边界测试，不是只读软件核查。
- 用户此前明确暂停所有发帧及 RGMII/MDI 物理测试；本报告不授权、不安排、不执行。
- 只有用户未来主动重新授权后，才讨论探测点、仪器、风险与最小步骤。

## 5. 更新后的候选与验证优先级

| 候选 | 当前证据 | 是否需要实验 | 优先级 |
|---|---|---|---|
| 6.12 gmac_clk_enable() 忽略 clock enable 错误 | 源码差异真实；已有稳态 clock_summary 显示相关时钟 enabled；无启动时失败记录 | 若要证实，需在 cold probe 时捕获各 clk_prepare_enable() 返回值；现有稳态快照无法回溯历史返回值 | 中 |
| RK3568 GMAC TX pinmux 未生效 | DTS/pin definitions 相同；正常路径源码写入逻辑基本相同；6.12 有首 pin 错误被吞的通用差异 | 可先做 A 项只读 pinctrl ownership 检查；真正硬件 mux 状态需更直接证据 | 低至中 |
| MAC 已完成计数但未越过 RGMII | 已有 MMC good-only 累计值，但未逐帧关联；MMC 不是 PHY/MDI 证明 | 需要物理 RGMII TXC/TXD 观测；当前暂停 | 高价值边界认证，但暂不授权 |
| RTL8211F PHY 未将 RGMII 输入转成线侧发送 | PHY 驱动差异已大幅审查；无可用指定帧 TX counter | 需 PHY 线侧仪器或外部接收证据；不能靠 RTL8211F 普通状态寄存器完成 | 当前不安排 |

## 6. 当前结论与建议

1. 当前无需再扩大 Linux 网络栈、STMMAC 普通 TX、DMA/MTL、MAC TE、phylink、EEE、checksum/offload、DHCP 客户端等排查范围。
2. 静态软件研究剩余的最有价值方向是：把 6.12 GMAC clock enable 错误处理与 pinctrl 首 pin 错误处理这两个“可能静默失败”的路径进一步做源码条件审查；但目前都没有现场失败证据。
3. 若希望在不发帧、不读危险寄存器的前提下再获得一条实机证据，唯一建议保留的是 A 项 pinctrl debugfs 软件归属只读检查。它只检查软件 pin ownership，不宣称证明硬件 mux 或物理 TX。
4. 若 A 项无冲突，且后续 clock enable 返回值也无失败证据，那么继续纯软件源码搜索的边际收益将很低；真正区分 MAC/RGMII 与 PHY/线侧，需要未来另行授权的物理边界观测。
5. 所有此前暂停的外部发帧、抓包、PHY counter/register、RGMII/MDI 测试继续暂停。本报告仅提出验证能力和边界，不代表用户授权实施。
