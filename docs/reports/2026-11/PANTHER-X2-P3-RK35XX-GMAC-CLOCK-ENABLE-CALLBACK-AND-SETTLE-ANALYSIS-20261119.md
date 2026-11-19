# Panther X2：RK35xx BSP GMAC 时钟调用条件与 100–200µs settle 窗口审计（2026-11-19）

## 1. 范围和源码基线

承接 Actions run #296 / 6.1.174 自动资产来源核验。本轮以高置信度候选源码审查 Panther 的实际 RGMII clock enable 路径，并确认 PLL provider callback 的真实调用条件。

- 正常 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 最早异常 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（高置信度候选；run #296 的实际 workflow_dispatch inputs/source_hash 尚未直接取得）
- 持续异常 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

只读公开源码与项目既有证据。未访问 Panther 实机、未读写 MMIO/MDIO、未发包/抓包、未重启接口、未修改配置或制作补丁。

## 2. Panther RGMII 路径实际获取/使能哪些 clocks

c2f148d 的 Panther DTS 明确：
- GMAC1 compatible：rockchip,rk3568-gmac
- phy-mode = rgmii
- clock_in_out = input
- assigned-clocks 只设置 SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED、SCLK_GMAC1 的 parent
- SCLK_GMAC1 parent 指向外部 gmac1_clkin fixed-clock
- PHY 节点没有 clocks 属性。

SoC DTS 的 clock-names：
- stmmaceth → SCLK_GMAC1
- mac_clk_rx → SCLK_GMAC1_RX_TX
- mac_clk_tx → SCLK_GMAC1_RX_TX
- clk_mac_refout → CLK_MAC1_REFOUT
- aclk_mac → ACLK_GMAC1
- pclk_mac → PCLK_GMAC1
- clk_mac_speed → SCLK_GMAC1_RX_TX
- ptp_ref → CLK_GMAC1_PTP_REF
- pclk_xpcs / clk_xpcs_eee → XPCS 专用时钟。

c2f148d 的 rk_gmac_clk_init() 对 RGMII 实际获取：
- mac_clk_rx（只获取；RGMII 分支不 enable）
- mac_clk_tx
- aclk_mac
- pclk_mac
- stmmaceth
- clk_mac_speed
- clk_phy 从 PHY node 取值，但 Panther PHY node 没有 clocks，属于 optional 外接 PHY clock，取得错误指针后不会 enable。

pclk_xpcs / clk_xpcs_eee 只在 SGMII/QSGMII 分支获取；Panther RGMII 不获取。即使基础 SoC DTS 有这两个 clock-names，也不代表 RGMII path 使用 XPCS。

gmac_clk_enable(true) 的 Panther RGMII 实际调用：
1. aclk_mac：clk_prepare_enable()
2. pclk_mac：clk_prepare_enable()
3. mac_clk_tx：clk_prepare_enable()
4. clk_mac_speed：clk_prepare_enable()
5. pclk_xpcs / clk_xpcs_eee 在 RGMII 下保持零初始化 NULL；IS_ERR(NULL) 为 false，clk_prepare_enable(NULL) 按 CCF API 返回 0/no-op。
6. clk_phy 为 ERR_PTR 时被跳过。
7. mac_clk_rx / clk_mac_ref / clk_mac_refout 的 enable 只在 RMII 分支，不命中 Panther。

特别注意：mac_clk_tx 与 clk_mac_speed 在 Panther DTS 都引用 SCLK_GMAC1_RX_TX，是同一个 CCF clock core 的两个 consumer handle。两次 prepare/enable 会增加同一 core 的引用计数两次；对应 disable 也各调用一次，引用计数配平。这不是对同一硬件 mux 重复执行两次独立 mux 切换，也不是天然错误。

stmmaceth / SCLK_GMAC1 由 STMMAC core 负责 enable，不在 Rockchip glue 这组 enable 中主动打开。

## 3. c2f148d 的 clock get / enable 错误处理风险，映射到 Panther 后重新定级

RK35xx BSP：
- devm_clk_get() 失败时多数只打印错误，不立即返回 probe failure；
- gmac_clk_enable() 对 ERR_PTR handle 跳过；
- 对 clk_prepare_enable() 的返回值不检查；
- 最终仍设置 clk_enabled = true。

这是实际代码质量退化，且与正常 6.1.116 的 bulk get/enable 错误检查不同。

但检查 Panther 当前 RGMII clock provider 后，不能把它直接等同于“Panther 很可能发生 clock enable failure”：
- ACLK_GMAC1 / PCLK_GMAC1 使用标准 Rockchip CRU gate provider；底层 clk_gate_enable() 写 gate 后直接返回 0。
- SCLK_GMAC1_RX_TX 是 mux clock，mux ops 没有独立 enable callback。
- Panther TX/RX MAC clock root 是 gmac1_clkin fixed-clock；fixed-rate provider 没有 prepare/enable callback。
- ACLK/PCLK 上游是 aclk_usb / pclk_usb composite clock；composite 的 mux/divider/gate ops 本身没有一个 Panther RGMII 路径下已知会返回错误的 prepare callback。
- 如果 ACLK_USB 当前父链使用 GPLL，PLL provider enable callback 会执行，但其函数最终也返回 0；内部 wait_lock() 的错误返回值被忽略，仅打印 timeout 日志。该行为在 6.1.116 和 RK35xx BSP 两边都存在，不是 c2f 新增的错误传播差异。
- CCF runtime-PM 等一般失败理论上仍存在，但当前静态 provider/consumer 结构没有发现 Panther 正常 probe 时一个可预期、必然失败的条件。

**重新定级：** “忽略 clk_prepare_enable() 返回值”仍是确定的错误处理缺陷，但在 Panther 已知 RGMII clock provider 组合下，缺乏具体会返回错误的 provider 路径；不能把它保留为强根因候选。应从高优先级降为低/中优先级风险，除非既有日志或实际构建中的 clock get error 提供新证据。

## 4. 100–200µs settle 的准确位置和含义边界

c2f148d 的 gmac_clk_enable(true) 顺序：
1. 对上述 RGMII clocks 调用 clk_prepare_enable（错误返回未检查）；
2. 若平台有 set_clock_selection callback 才调用；RK3568 Panther ops 没有该 callback；
3. 调用 rockchip_csu_disable(aclk/pclk)；Panther 没有 CSU phandle，已审计为 NULL/no-op；
4. usleep_range(100, 200)；
5. clk_enabled = true；
6. 返回 rk_gmac_powerup()；
7. 设置 RGMII GRF interface/delay；
8. 打开 phy-supply regulator；
9. pm_runtime_get_sync()；
10. 进入 STMMAC probe。

所以 100–200µs 是 MAC/bus/TX clock gates enable 后、RGMII GRF 配置和 PHY regulator enable 前的固定 settle 窗口。它不是 RTL8211F 上电后的 PHY PLL lock delay，因为 PHY regulator 在该 delay 之后才打开；也不是 GPLL lock time 本身，GPLL provider 的 lock polling 属于另一个 CCF callback。

6.1.116 的对应顺序为 bulk clock prepare/enable（检查错误）→ 可选 PHY clock prepare/enable（检查错误）→ clock selection callback（Panther RK3568 ops 无此 callback）→ mdelay(5) → clk_enabled=true → RGMII GRF → PHY regulator。

因此对 Panther 实际有效的比较是：
- 6.1.116：关键 GMAC clocks enable 后固定等待 5ms；
- RK35xx BSP 6.1.174/6.12.81：对应 clocks enable 后固定等待 100–200µs；
- 两者在 delay 后均才进行 RGMII GRF 配置和 PHY regulator enable；
- 5ms / 100–200µs 均不是 PHY regulator 稳定后的等待。

源码没有为 vendor 的 100–200µs 说明明确板级依据；Armbian/Rockchip vendor 初始导入已有该值，但没有找到证明该窗口足以覆盖 Panther PHY/GMAC 上电/时钟稳定条件的厂商文档。不能凭经验断言 100–200µs 必然不足，也不能把 5ms 自动视为硬件必需。

## 5. PLL callback：不会在 GMAC probe 时首次启用 ACLK_USB 父链

本节纠正前一轮对“PLL callback 可能由 GMAC probe 触发”的表述。

RK3568 CRU 定义：
- ACLK_USB：四选一 composite，parent list = gpll_300m / gpll_200m / gpll_100m / xin24m，mux 为 CLKSEL_CON(32)[1:0]。
- PCLK_USB：parent = aclk_usb，标记 CLK_IS_CRITICAL。
- ACLK_GMAC1：gate，parent = aclk_usb。
- PCLK_GMAC1：gate，parent = pclk_usb。

c2f148d common CCF 的 clk_core_init() 对 CLK_IS_CRITICAL clock 在该 clock 注册时立即调用 clk_core_prepare() 与 clk_core_enable_lock()，并记录失败日志。因此 PCLK_USB 的 parent chain 在 CRU branch registration 阶段就会被准备/使能；若 ACLK_USB 当时选中 GPLL 派生 parent，GPLL parent chain 的 0→1 enable callback 会在 CRU provider 初始化阶段触发，而不是等 GMAC platform probe。

随后 GMAC probe 启用 ACLK_GMAC1/PCLK_GMAC1 时：
- PCLK_USB 已是 critical 且其 parent chain 已持有引用；
- ACLK_USB 也已因 PCLK_USB 的 parent chain 被准备/使能；
- GMAC gate 的 prepare/enable 只增加 consumer/gate 引用，不会再次从 0→1 启用 ACLK_USB/GPLL parent chain；
- GMAC glue 没有对 ACLK_USB 调用 clk_set_parent() 或 clk_set_rate()。

因此 **PLL callback 不是 GMAC probe 时新发生的时钟启动事件**。若 callback 执行，它属于更早的 CRU provider/critical clock 初始化阶段；若 parent chain 选择 XIN24M，则不会经过 GPLL core。

PLL provider 的模式 mux：
- 当前硬件模式为 NORMAL 时，wrapper gpll 的当前 parent 是内部 pll_gpll；CCF parent traversal 才会经过 PLL core。
- 当前硬件模式为 SLOW 时，wrapper 当前 parent 是 xin24m；enable parent chain 不会因为 aclk_usb 选择 gpll_300m 就自动触发内部 pll_gpll enable callback。
- RK35xx callback 的“power up → wait lock → set NORMAL”只能在 PLL core 已经作为当前 parent 被 enable 时执行；它不是一个无条件把 SLOW mux 切到 NORMAL 的独立启动钩子。

此外，RK3568 SoC DTS 对 GPLL 有 assigned-clock-rate，但没有为 ACLK_USB 指定 assigned-clock-parent；Panther 板级 DTS 也没有 ACLK_USB parent assignment。故 Linux 静态 DTS 不能决定 ACLK_USB 四选一的实际父项，父项由 Linux 接管时的硬件 mux 状态决定。当前没有可审计的 6.1.174 启动周期 ACLK_USB runtime parent 证据。

**本节结论：** PLL callback 的 NORMAL/SLOW 代码差异是确实存在的 BSP provider 差异，但它不在 GMAC probe 的即时 clock-enable 路径中；没有证据把它与当前 TX 丢帧直接关联。停止把它作为 P3 当前工作项，不安排 clock-summary 现场读取。

## 6. 已有证据的限制

项目仓库存在 6.1.116 和 6.12.81 的 clock-summary / 时钟树证据；其稳态值不能证明启动瞬态。已有日志检索没有找到“timeout waiting for pll to lock”或“cannot get clock”的命中，但当前可检索归档并非 6.1.174 完整启动日志，故只能说“已检索资料未见”，不能声称 6.1.174 从未发生。

U-Boot proper 日志中 GPLL 1188MHz 是 6.12.81 启动链的既有记录；它不提供 ACLK_USB 的 parent index，也不是 6.1.174 故障启动周期的记录，不能用来填补 ACLK_USB 状态缺口。

## 7. 本轮结论与 P3 下一步

### 已验证
1. c2f148d 的 Panther RGMII 实际 enable clocks 集合已明确；RMII/XPCS/PHY clock 分支不命中。
2. mac_clk_tx 与 clk_mac_speed 是同一 SCLK_GMAC1_RX_TX CCF core 的两个 consumer handles，双 enable/双 disable 引用计数平衡。
3. 6.1.174 BSP 的单项 clock-enable 返回值被忽略；但 Panther active provider chain 没有发现明确会失败的 callback，故错误处理差异不能直接解释故障。
4. 100–200µs 位于 MAC/bus clocks enable 后、RGMII GRF 设置与 PHY regulator enable 之前；其硬件充分性没有厂商证据。
5. PCLK_USB critical clock 在 CRU clock registration 阶段已准备/使能其 parent chain；PLL callback 若执行，属于 CRU init 阶段，不是 GMAC probe 首次启用。
6. ACLK_USB parent 未由 Panther DTS/SoC DTS 静态指定；现有 6.12 U-Boot log 不能提供该 parent index。

### 未验证
- 6.1.174 故障启动时 ACLK_USB 的 parent index 和 PLL wrapper mode；
- 100–200µs 是否足以覆盖 Panther GMAC bus/interface clock gate 和 GRF 稳定；
- 故障启动时是否出现过 PLL wait-lock timeout 或实际 clock get/enable error。

### 当前定级
- PLL mode callback 差异：降级，退出 P3 当前工作项。
- ignored clk_prepare_enable return：低/中优先级代码风险，无当前具体失败路径。
- 100–200µs settle：保留为待解释的时间差异，但无因果证据；不做补丁。
- 不安排实机 clock-summary 或寄存器读取。

### 下一步唯一工作项
在 c2f148d 与 6.12.81 RK35xx 源码中继续审查 rk_gmac_probe() / rk_gmac_setup() / rk_gmac_powerup() 以外尚未覆盖、且能命中 Panther 外接 RGMII 的差异；特别检查 PHY supply / runtime-PM / probe flags 与 STMMAC core handoff 的条件分支。对照 6.1.116，只保留 6.1.174 和 6.12.81 都存在、且在最早异常 6.1.174 上已生效的差异。已经完成的 DMA descriptor、MDIO/PHY attach 顺序、RGMII delay、CSU、CRU provider、PLL callback 不重做。

不操作 Panther，不写寄存器，不制作补丁。

## 8. 参考源码

- 6.1.116 dwmac-rk.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 RK35xx candidate dwmac-rk.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 RK35xx candidate clk-rk3568.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/clk/rockchip/clk-rk3568.c
- 6.1.174 RK35xx candidate clk-pll.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/clk/rockchip/clk-pll.c
- 6.1.174 RK35xx candidate common CCF clk.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/clk/clk.c
- 6.12.81 RK35xx dwmac-rk.c: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- RK35xx Actions run #296: https://github.com/ophub/kernel/actions/runs/42812333074
