# Panther X2 GMAC TX 故障调查路线图（唯一主索引）

- 更新日期：2026-11-19
- 当前现场基线：已恢复原版 6.1.116；不在现场运行故障内核。
- 调查方式：优先只读源码、提交历史、仓库报告和公开技术资料。
- 本文件是后续对话的路线锚点；每次继续前先读本文件及其指向的最新报告，不重新规划、不重复已完成工作。

## 固定问题定义

故障定位目前只到达：Linux 网络栈/驱动提交发送后，第三方同二层监听器无法收到故障版本的广播帧。不能声称已定位 MAC、RGMII、PHY 或 MDI 的具体物理故障边界。

版本边界：
- 6.1.116：实机正常。
- 6.1.174-rk35xx：最早明确异常版本。
- 6.12.81-rk35xx：持续异常。

## 当前唯一工作项

### P1：JL2xx1 workaround 的 PHY MDIO 写入组（已收口，证据不足）

- 1500ms DMA reset 前延时：已查明原始目的是 JL2XX1/JL2101 快速启动时序；后续代码只对对应 PHY ID 启用；RTL8211F 对照设备不需要。**已降级，不作为 Panther 主线。**
- MDIO addr 0 四次写入：来源追溯到 JLSemi 厂商代码；原 PR 作者后续称 injection 并非必需。
- 已完成：来源追溯、RTL8211F-CG PHYCR2 逐位解码、地址 0 广播语义、BMCR reset 影响边界审查。
- 结论：PHYCR2 Reg25=0x1801 含 Reserved bits 13:12=01，且会清除 RXC/EEE 相关位；地址 0 是广播写入；PHY reset 符合 PHYCR2 配置后的复位要求，但 JLSemi 原始意图与保留位行为无可靠厂商证据。P1 已正式结束，不再猜测。

相关报告：
- `docs/reports/2026-11/PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md`
- `docs/reports/2026-11/PANTHER-X2-JL2XX1-WORKAROUND-ORIGIN-AND-SCOPE-20261119.md`
- `docs/reports/2026-11/PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md`

## 后续顺序（不得跳步）

### P2：RTL8211F PHY 时钟输入链与 U-Boot/Linux 初始化交接（已收口，JP proper 证据不足）
- 已确认 Linux 按 Panther X2 runtime FDT 采用 clock_in_out=input，并重新配置 GMAC clock parent 与 PHY 初始化。
- 已确认 6.1.174 / 6.12 与 6.1.116 的 GMAC1 CRU parent mux / 外部 fixed-clock 描述没有已知差异。
- JP proper 的精确源码、FIT control FDT、实际 clock_in_out 与 PHY 初始化行为无法从现有可审计资产确认；不得用 JP SPL FDT 或较新的 Radxa U-Boot 源码替代。
- P2 未找到已证实可解释最早回归的启动交接根因，正式收口。报告：`PANTHER-X2-P2-UBOOT-LINUX-GMAC-CLOCK-HANDOFF-20261119.md`。

### P3：实际 RK35xx BSP 与正常 general kernel 的 GMAC 初始化差异（当前唯一工作项）

**源码基线与证据等级：**
- 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。
- 最早异常 6.1.174-rk35xx：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，目前为高置信度源码候选。
- 持续异常 6.12.81-rk35xx：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。
- 6.1.174 自动资产 `6.1.174.tar.gz` 与 Ophub Actions run #296（ID `42812333074`）上传 step 时间精确吻合；run head workflow 默认 source 为 `ophub/linux-6.1.y-rockchip`，step 5 会读取 main HEAD；该时刻 main 最新提交为 c2f148d。
- 尚未取得 workflow_dispatch 实际 inputs 和 step 5 的 source_hash 输出，因此 c2f148d 是高置信度候选，不是逐字节构建证明。
- 普通 stable `unifreq/linux-6.1.y@3f06ed3` 只作 upstream 对照，不代表实机 6.1.174-rk35xx 构建。

来源报告：`PANTHER-X2-6.1.174-RK35XX-ACTIONS-RUN-AND-SOURCE-PROVENANCE-CORRELATION-20261119.md`。

**已完成的时钟子项：**
- c2f148d 的 Panther RGMII 实际启用集合已映射：`aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`；RMII、XPCS、PHY external clock 分支不命中。
- `mac_clk_tx` 与 `clk_mac_speed` 指向同一 CCF core，双 enable/disable 是平衡引用计数，不是两次独立 mux 操作。
- BSP 的单项 `clk_prepare_enable()` 返回值确实被忽略，但 Panther 当前 gate/mux/fixed-clock provider 组合没有发现一个可预期的必然失败 callback；该错误处理退化降为低/中优先级风险。
- 100–200µs settle 位于 MAC/bus clocks enable 后、RGMII GRF 配置与 PHY regulator enable 前；它不是 PHY 上电后的 PLL lock delay。其硬件充分性没有厂商证据，暂留为待解释差异，不做补丁。
- `PCLK_USB` 标记为 `CLK_IS_CRITICAL`，在 CRU clock registration 阶段即准备/使能 parent chain。GPLL callback 若执行，发生在 CRU 初始化阶段，不是 GMAC probe 首次启用；PLL callback 差异降级，不再追运行时 parent、不安排 clock-summary 读取。
- 报告：`PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md`。

**第三个子项已完成：** 比较 c2f148d / 6.12.81 / 6.1.116 的 RK35xx GMAC probe、setup、powerup、powerdown、suspend/resume。
- SPH disable 只影响 RX split-header/GRO，不进入普通 TX 提交路径。
- Vendor MAC callback 已有专项测试/审计；integrated PHY/BGS OTP 不命中外接 RTL8211F；Panther DTS 显式提供 TX/RX delay；PHP-GRF 差异不命中 RK3568 ops。
- PHY regulator 错误不传播、pm_runtime_get_sync 返回值不检查是三个版本共有弱点，不是本次回归新引入。
- 其余 probe flags、CSU no-op、loopback sysfs 未发现可解释普通 TX 故障的机制。
- 报告：`PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md`。

**下一步唯一子项：** 由于此前 TX core 审计有部分使用普通 stable 6.1.174，而不是当前高置信度的 c2f148d，针对源码归属纠正，定点复核 c2f148d 的 STMMAC core（stmmac_xmit/TSO、TX reclaim、DMA engine init/channel start、open/hw_setup/link-up handoff）。只比较正常 6.1.116 与 c2f148d，并用已有 6.12.81 结果做第三端交叉核对；只寻找 6.1.174-rk35xx 与 6.12.81-rk35xx 共有、但正常 6.1.116 不存在的有效 TX 路径变化。不要重做普通 descriptor OWN/tail pointer/barrier、DMA register helper、queue parser 和物理 TX 边界审计；若无差异则明确关闭。全程只读，不操作 Panther、不写寄存器、不发包、不抓包、不制作补丁。


### P4：pinctrl 首 pin 错误处理差异
只读低优先级；必须出现新证据才继续。不得为此重启故障内核。

### P5：物理边界波形验证
最后讨论；需用户明确授权。不得自行安排实机操作。

## 已完成/已降级项目（禁止无新证据重复）

- U-Boot 是否识别 GMAC 的基础支线。
- MAC 地址来源闭环。
- DDR 频率差异的独立记录。
- BL31 早期初始化反汇编扩展（已停止）。
- IOMMU 绑定路径（无绑定证据）。
- 普通 TX DMA descriptor、OWN/barrier/tail pointer/回收、MAC TE、DMA ST、MTL 基础对比。
- RGMII delay 数值一致性审计。
- PHY reset GPIO 执行路径审计（无失败证据）。
- RX/NAPI 反向广播与分配探针支线。
- DHCP 客户端/MAC/offload 对照。
- EEE、100M、电源管理已有测试。
- CSU disable 对应 NULL/no-op。
- GMAC 时钟等待 5ms 与 100–200µs 差异：不解释最早 6.1.174 回归，已从主线移除。
- DMA coherency、PHY resume patch、内核配置来源与运行时核验。
- pinctrl 通用错误处理差异：低优先级，尚无现场写入失败证据。

## 每轮工作纪律

1. 先读本索引和相关报告，再动手。
2. 一次只推进当前工作项。
3. 对每个结论标注：已验证 / 未验证 / 推测 / 降级。
4. 新发现先对照既有报告，确认不是重复工作。
5. 完成一个子项后再切换；同步更新本索引和报告。
6. 不得把代码差异直接写成根因。
7. 不得在未经授权时启动故障内核、发包、抓包、写 PHY、重启接口或修改设备配置。
