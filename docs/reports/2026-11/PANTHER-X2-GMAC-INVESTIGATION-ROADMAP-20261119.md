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

### P3：实际 kernel family 的 GMAC 初始化差异（当前唯一工作项）

**重要基线纠正（2026-11-19）：** 正常 6.1.116 是 Ophub general kernel；异常 6.1.174-rk35xx 是 Ophub RK35xx vendor BSP。不能继续把普通 `unifreq/linux-6.1.y@3f06ed3` 当作实际 6.1.174-rk35xx 镜像源码。

- 6.1.116 正常：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，general config family。
- 6.1.174-rk35xx 异常：高置信度候选 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`；官方 RK35xx workflow 默认 source、kernel suffix 和 release asset 时间吻合，但尚缺该 asset 的 Actions run inputs/source_hash/build log，不能称精确构建 commit 已闭环。
- 6.12.81-rk35xx 异常：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。

**已完成的普通 stable 比较仅作为参考，不代表实际 RK35xx 镜像。** 报告：`PANTHER-X2-P3-INIT-CALLCHAIN-MDIO-PHY-ORDER-20261119.md`。

**新增已验证发现：**
- RK35xx 6.1.174 候选的 `gmac_clk_enable()` 与正常 general 6.1.116 不同：逐项 `clk_prepare_enable()`、未检查返回值、`usleep_range(100, 200)`；general 6.1.116 使用 bulk enable、检查错误并等待 `mdelay(5)`。
- 该 RK35xx 实现自 2025-04 Armbian vendor source 初始导入即存在，并非 6.1.174 version bump 新增。
- RK35xx 6.1.174 与 6.12.81 的关键 `gmac_clk_enable()`、`rk_gmac_clk_init()`、`rk_gmac_powerup()`、`rk_gmac_phy_power_on()` 函数体一致。
- 以上只是 BSP family 差异，尚未证明任何 clock enable 在 Panther 失败，也未证明 100–200µs 导致 TX 不出线；禁止据此制作补丁。

报告：`PANTHER-X2-P3-RK35XX-6.1.174-SOURCE-PROVENANCE-AND-GMAC-CLOCK-DIFF-20261119.md`。

**下一步唯一子项：** 继续只读映射上述时钟 handle 获取与 enable 顺序到 Panther 的实际 DTS clock names、clock_in_out=input 和 parent chain；核实每个差异是否命中 Panther RGMII 路径。已完成的 RGMII delay 数值、CSU NULL/no-op、PHY reset GPIO 不重查。随后再核对 6.12.81 中哪些差异持续存在。不得做实机操作、写 PHY、重启接口或制作补丁。

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
