# Panther X2：P3 GPLL/ACLK_USB 追踪收口与源码归属纠正（2026-11-19）

## 1. 本轮目的

承接上一轮对 RK3568 GPLL PLL enable/disable callback 的追踪，核实它是否属于实机最早异常版本 6.1.174 的有效故障线索。先回读唯一调查路线图及仓库既有报告，再对照实际 6.1.174 源码端点，不重复任何实机测试。

全程只读 GitHub 源码和项目仓库报告；未访问 Panther 实机，未读写 MMIO/MDIO，未发包/抓包，未重启接口或修改配置。

## 2. 先纠正源码基线：c2f148d 不是 6.1.174 的已证实构建源

项目已有报告 `PANTHER-X2-6.1.174-BSP-GMAC-CLOCK-ENABLE-AND-RGMII-ORDER-DIFF-20261119.md` 已明确更正：

- 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。
- 实机 6.1.174 主要源码候选：`unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7`，2026-05-23。
- `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` 是 2026-11-10 的后期 BSP 快照，不能因为后缀/工作流表面吻合就当成 6.1.174 的源码证明。没有找到它进入实机 6.1.174 构建的 cherry-pick 或构建日志证据。

因此，c2f148d 中的 GMAC 100–200µs settle、逐项 clock enable 及忽略 enable 返回值，以及本报告追踪的 PLL mux enable/disable 改动，都不得归因于实机 6.1.174。

## 3. 本轮对后期 RK35xx BSP PLL 路径的只读核对

在 c2f148d 的 RK3568 CRU/PLL provider 中确认：

- RK3568 GPLL 以 `PLL(pll_rk3328, PLL_GPLL, "gpll", ...)` 注册，使用 RK3036/RK3328 PLL ops；GPLL rate table 非空，因此注册的是包含 `.enable/.disable` 的 `rockchip_rk3036_pll_clk_ops`。
- RK3328 PLL wrapper mux 的 parent 为 `xin24m` 与内部 `pll_gpll`；模式寄存器的 SLOW/NORMAL 切换由 PLL provider callback 执行。
- RK3568 `aclk_usb` 是四选一 composite，parents 为 `gpll_300m`、`gpll_200m`、`gpll_100m`、`xin24m`，mux 位于 `CLKSEL_CON(32)[1:0]`。
- `pclk_usb` 以 `aclk_usb` 为 parent，标记 `CLK_IS_CRITICAL`；GMAC1 的 ACLK/PCLK gate 分别以 `aclk_usb` / `pclk_usb` 为 parent。
- SoC `rk356x.dtsi` 对 CRU 的 assigned-clocks 包含 `PLL_GPLL`，assigned-clock-rates 为 1.188GHz；但没有为 `ACLK_USB` 指定 assigned-clock-parent。Panther 板级 DTS 只为 GMAC MAC/RGMII clock chain 设置 assigned-clock-parents，没有设置 ACLK_USB parent。

这些内容描述后期 BSP 的静态时钟树。它们不能证明实机运行时 ACLK_USB 当前选择的 parent，也不能证明任何 PLL callback 在 Panther 启动时实际执行。

## 4. CCF callback 的调用条件

在 c2f148d 的 common CCF `drivers/clk/clk.c` 中：

- `clk_core_enable()` 只有在某个 clock core 的 `enable_count == 0` 时，才递归 enable parent 并调用该 clock 的 `.enable` callback；成功后才增加 enable_count。
- `clk_core_disable()` 只有在 enable_count 减到 0 时才调用 `.disable` callback，再递归 disable parent。
- 因此，PLL callback 的函数存在/注册不等于每次 GMAC clock prepare 都会执行。是否触发取决于运行时 parent 链以及 PLL core 当时的 CCF enable_count。
- RK3328 PLL wrapper 还有内部 SLOW/NORMAL mux；运行时 parent 状态决定 CCF parent traversal。仅从 DTS 未指定 ACLK_USB parent，无法推断当前模式或 enable callback 的执行历史。

以上调用条件是后期 BSP CCF 源码事实，不构成实机执行证据。

## 5. 与实机最早回归的关联判定

**已验证：**
1. 后期 RK35xx BSP c2f148d 的 PLL provider 确实有 enable 后切 NORMAL、disable 前切 SLOW 的实现。
2. 后期 BSP 的 ACLK_USB 可由 GPLL 派生时钟供给，GMAC1 ACLK/PCLK parent chain 可间接触及该分支。
3. CCF PLL callback 只在 enable_count 0→1 / 1→0 等条件下执行。
4. 项目既有源码逐文件比较已确认：实机 6.1.116 与 6.1.174 源码候选中的 `drivers/clk/rockchip/clk-pll.c`、`clk-rk3568.c`、common mux/gate/composite 等相关文件相同。

**证据不足：**
- Panther 在 c2f148d 后期 BSP 下的 ACLK_USB parent 与 PLL mux runtime state。
- 任意一轮启动时 GPLL callback 的实际调用次数和时间点。

**已排除为 6.1.174 首次回归解释：**
- 后期 BSP PLL enable/disable mux 改动不能解释 6.1.174 首次异常，因为该改动不在当前可审计的 6.1.174 源码端点差异中。
- 即使 6.12.81 延续后期 BSP 行为，它也只能是持续异常版本的背景差异，不能解释最早从 6.1.174 开始的回归。

## 6. 本支线结论

**停止继续追踪 c2f148d 的 GPLL/ACLK_USB runtime parent。** 其余未知状态需要实机 clock summary/MMIO 才能回答，但即使查明，也不能解释 6.1.174 最早回归；目前没有理由为了一个不属于最早故障源码差异的分支安排实机取证。

不执行 clock-summary 读取，不安排任何设备操作，不制作补丁。

P3 回到唯一有效比较对象：6.1.116 正常源码候选 `5eb841b` 与 6.1.174 实际源码候选 `3f06ed3`，继续只读审查尚未完成、且能直接影响 GMAC TX bring-up 的差异。优先从已存在的 GMAC 初始化/PHY interface call-chain 报告的未闭环部分继续；不得重复 CRU provider、PLL、RGMII delay、PHY reset GPIO、CSU、DMA descriptor/OWN/tail pointer 等已完成审计。

## 7. 参考报告与源码

- 实际 6.1.174 GMAC 时钟基线纠正：`PANTHER-X2-6.1.174-BSP-GMAC-CLOCK-ENABLE-AND-RGMII-ORDER-DIFF-20261119.md`
- 后期 RK35xx BSP 源码来源审计：`PANTHER-X2-P3-RK35XX-6.1.174-SOURCE-PROVENANCE-AND-GMAC-CLOCK-DIFF-20261119.md`（其关于 c2f148d 为 6.1.174 候选的推断已被后续报告撤回）
- RK3568 CRU/PLL 后期 BSP 比较：`PANTHER-X2-P3-RK3568-GMAC-BUS-CLOCK-AND-PLL-CCF-DIFF-20261119.md`（仅作为后期 BSP 技术记录，不作为 6.1.174 故障证据）
- 6.1.116：https://github.com/unifreq/linux-6.1.y/tree/5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174 源码候选：https://github.com/unifreq/linux-6.1.y/tree/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7
- 后期 BSP 对照：https://github.com/ophub/linux-6.1.y-rockchip/tree/c2f148dece4b67ebd30aefad1bdd1990f41e5633


## 8. 后续证据更新：本报告的源码排除结论已被取代（2026-11-19）

本报告第 2、5、6 节曾因未找到 6.1.174 对应 Actions run，而将 c2f148d 视为不属于实机 6.1.174 的后期快照，并据此排除它解释最早回归。该判断已被新的构建来源证据更新：

- Ophub 自动资产 6.1.174.tar.gz 创建于 2026-11-10 13:09:30Z；
- Actions run #296（ID 42812333074）在 13:09:27–13:09:40Z 执行上传 step，编译 step 明确为 6.1.y；
- run head SHA 对应 workflow 默认 kernel_source 为 ophub/linux-6.1.y-rockchip；
- run 的 source-hash step 在 12:04:15Z 执行；该时间点源仓库 main 的最新提交是 c2f148dece4b67ebd30aefad1bdd1990f41e5633。

由于 REST API 未公开该次 workflow_dispatch 的实际 inputs，且 step 5 输出日志不可取得，c2f148d 仍为高置信度候选而非逐字节证明。但它应恢复为 P3 实际 6.1.174 的主要源码候选；本报告关于“c2f148d 不属于 6.1.174、不能解释最早回归”的判断不再适用。

后续 PLL callback 进一步审计也已确认：PCLK_USB critical clock 在 CRU provider 注册阶段建立 parent chain，GPLL callback 若执行，发生在 GMAC probe 之前；PLL 分支退出当前 P3 工作项。100–200µs settle 仍作为待解释时间差异保留，但无充分厂商依据或因果证明。

请以以下两份新报告和唯一路线图为准：
- PANTHER-X2-6.1.174-RK35XX-ACTIONS-RUN-AND-SOURCE-PROVENANCE-CORRELATION-20261119.md
- PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md
- PANTHER-X2-GMAC-INVESTIGATION-ROADMAP-20261119.md

本报告保留历史审计轨迹，不删除。
