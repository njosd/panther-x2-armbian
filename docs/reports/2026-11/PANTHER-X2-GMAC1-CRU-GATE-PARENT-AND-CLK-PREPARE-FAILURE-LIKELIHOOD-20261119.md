# Panther X2：GMAC1 CRU gate、父时钟链与 clk_prepare_enable 失败可能性核查（2026-11-19）

## 1. 本轮目的

上一轮确认 6.12 dwmac-rk.c 忽略若干 clk_prepare_enable() 返回值。本轮继续检查这些调用在 RK3566/RK3568 CRU provider 上是否容易实际失败，避免把“错误码未检查”误当成已发生的时钟故障。

源码基线：
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12.81：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

## 2. GMAC1 CRU 定义两版相同

对比两版 drivers/clk/rockchip/clk-rk3568.c，GMAC1 相关定义的父级、gate 寄存器和 mux 定义相同：

- ACLK_GMAC1：GATE，parent = aclk_usb，CRU CLKGATE_CON17 bit 3。
- PCLK_GMAC1：GATE，parent = pclk_usb，CRU CLKGATE_CON17 bit 4。
- SCLK_GMAC1：MUX，parents = clk_mac1_2top / gmac1_clkin，CLKSEL_CON33 bit 2。
- SCLK_GMAC1_RGMII_SPEED：MUX，parents = clk_gmac1 / clk_gmac1 / clk_gmac1_tx_div50 / clk_gmac1_tx_div5，CLKSEL_CON33 bit 4。
- SCLK_GMAC1_RX_TX：MUX，parents = clk_gmac1_rgmii_speed / clk_gmac1_rmii_speed / clk_gmac1_xpcs_mii，CLKSEL_CON33 bit 0。

这与上一轮发现的 DTS assigned-clock-parents 相符。两版没有发现这些 GMAC1 clock provider 定义的版本回归。

## 3. ACLK/PCLK 的父级链

RK3568 CRU 定义：
- aclk_gmac1 的 parent 是 aclk_usb；aclk_usb 是 GPLL300/GPLL200/GPLL100/XIN24M 的 composite clock，并带 CRU gate。
- pclk_gmac1 的 parent 是 pclk_usb；pclk_usb 是以 aclk_usb 为 parent 的 composite divider/gate，并标记 CLK_IS_CRITICAL。

因此启用 GMAC1 ACLK/PCLK 会沿父链启用 USB 公共 bus clock 节点；这不是指 GMAC 使用 USB 数据路径，只是 CRU clock tree 的父级命名/共享关系。

## 4. CRU gate enable 本身不会报告硬件写入失败

6.12 的 drivers/clk/clk-gate.c 中，clk_gate_enable() 调用 clk_gate_endisable(hw, 1)，随后无条件 return 0。clk_gate_endisable() 对 HIWORD_MASK gate 写入寄存器，但没有读回确认 gate 状态。

RK3568 ACLK_GMAC1/PCLK_GMAC1 使用标准 GATE 宏，gate ops 因而走上述通用 clk_gate_ops。

含义：
- 如果 MMIO 写入路径正常，标准 gate enable callback 通常返回 0；
- 该 callback 不验证时钟物理波形，也不验证 gate 位写入后是否真的按预期产生时钟；
- 因而 dwmac-rk.c 忽略返回值是代码质量问题，但不能直接推导出 ACLK/PCLK 已发生 enable failure；
- 即使 clk_prepare_enable() 返回 0，也不是物理时钟频率/波形正确的证明。

## 5. clk_prepare_enable() 仍有哪些可能失败条件

Linux common clock framework 的 clk_core_prepare() / clk_core_enable() 会递归处理 parent，并传播 parent prepare/enable callback 错误；还可能因 clock provider runtime-PM 获取失败返回错误。clk_gate_enable() 自身通常返回 0，但父级 provider 或 runtime PM 路径理论上仍可能失败。

对于 Panther 当前 RGMII DTS：
- SCLK_GMAC1_RX_TX 与 clk_mac_speed 使用同一 SCLK_GMAC1_RX_TX clock ID；
- 其父链最终由 SCLK_GMAC1 mux 选择；DTS 将 SCLK_GMAC1 指向 gmac1_clkin fixed-clock，标称 125MHz；
- aclk_gmac1 / pclk_gmac1 是标准 gate，父级为 aclk_usb / pclk_usb；
- 当前静态源码没有显示这些 GMAC1 gate 的 enable callback 会因某个可预期的硬件状态而返回错误。

所以从 provider 代码看，clk_prepare_enable() 的实际失败概率不能说为零（parent/runtime-PM error 仍存在），但没有发现一个 Panther 正常启动时必然触发的失败条件。忽略返回值仍应视为缺陷/可维护性退化，但它目前不是强根因证据。

## 6. TRM 对 ACLK/PCLK gate 的说明

RK3568 TRM Part 1 V1.3 的 CRU_GATE_CON17（偏移 0x0344）列出：
- bit 3：aclk_gmac1_en
- bit 4：pclk_gmac1_en
TRM 说明这些 gate 位为 1 时 disable clock；Linux GFLAGS 使用标准 gate 语义并按 enable 清除 disable 位。

本轮没有读取设备 MMIO，也没有使用 devmem/debugfs。TRM 描述仅说明寄存器语义，不代表已经测量 Panther 实机 gate 状态。

## 7. 本轮结论

1. GMAC1 CRU provider 的父链、gate 和 mux 定义在 6.1.116 与 6.12.81 中相同，没有发现版本回归。
2. ACLK_GMAC1/PCLK_GMAC1 是标准 CRU gates；标准 clk_gate_enable() 写 gate 后直接返回 0，不做硬件读回验证。
3. 6.12 dwmac-rk.c 忽略 clk_prepare_enable() 返回值的确是源码缺陷，但 CRU provider 审计没有找到 Panther 当前配置下一个明确、常见、必然失败的时钟 enable 条件。
4. 因而上一轮“静默 enable 失败”候选应从高优先级根因线索降级为中低优先级代码缺陷。不能据此声称 GMAC 时钟启用失败。
5. 5ms → 100–200µs 等待时间变化仍是源码事实，但没有从 CRU gate provider 或 TRM 找到能证明 100–200µs 必然不足的证据。

## 8. 下一步

不再扩大到全 SoC clock tree。下一步应回到与外部帧丢失边界直接相关的证据：
1. 复核现有 6.12.81 完整启动日志中 clock provider、reset、DMA 初始化错误（只读已有记录，不要求重跑）；
2. 核对 stmmac 初始化期间 DMA reset 是否成功、MAC TX/RX enable 顺序是否有版本差异；仅审计尚未闭环部分，排除已完成 TX descriptor/MTL/PHY link/地址来源/环回；
3. 如果已有日志无法证明 100–200µs 等待充分与否，保留未验证，不用猜测替代实测；任何实机验证先向用户申请授权。

未执行设备命令、寄存器读写、驱动修改、接口重启或配置变更。

## 9. 参考来源

- 6.1.116 clk-rk3568.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/clk/rockchip/clk-rk3568.c
- 6.12.81 clk-rk3568.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/clk/rockchip/clk-rk3568.c
- 6.12.81 clk-gate.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/clk/clk-gate.c
- 6.12.81 clk.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/clk/clk.c
- RK3568 TRM Part 1 V1.3：https://opensource.rock-chips.com/images/2/26/Rockchip_RK3568_TRM_Part1_V1.3-20220930P.PDF

## 10. 关联报告

- PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md
- PANTHER-X2-RK3568-RGMII-DELAY-ORDER-AND-GMAC-CLK-PARENT-CROSSCHECK-20261119.md
- PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md