# Panther X2 GMAC TX 故障调查路线图（唯一主索引）

- 更新日期：2026-11-20（P1–P4 阶段性报告已归档）
- 当前现场基线：已恢复原版 6.1.116；不在现场运行故障内核。
- 调查方式：优先只读源码、提交历史、仓库报告和公开技术资料。
- 本文件是后续对话的路线锚点；每次继续前先读本文件及其指向的最新报告，不重新规划、不重复已完成工作。

## 固定问题定义

故障定位目前只到达：Linux 网络栈/驱动提交发送后，第三方同二层监听器无法收到故障版本的广播帧。不能声称已定位 MAC、RGMII、PHY 或 MDI 的具体物理故障边界。

版本边界：
- 6.1.116：实机正常。
- 6.1.174-rk35xx：最早明确异常版本。
- 6.12.81-rk35xx：持续异常。

## P1–P4 阶段性报告

- 汇总报告：`PANTHER-X2-GMAC-TX-INVESTIGATION-STAGE-1-4-SUMMARY-20261120.md`。
- P1–P4 限定静态源码审计均已结束；故障物理边界仍未定位。
- P4 首 pin pinctrl 错误处理是未证实候选，无现场 regmap 写入失败证据。
- P5 仅待用户评估与明确授权，不自动进行 Panther 实机操作。

## 当前阶段状态

P1–P4 限定静态源码审计均已结束。尚未定位 TX 故障的 MAC/RGMII/PHY 物理边界。当前不自动进行实机操作；是否进入 P5 需先评估并取得用户明确授权。

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

### P3：实际 RK35xx BSP 与正常 general kernel 的 GMAC 初始化差异（已正式关闭：未找到有效共同 TX 根因差异）

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

**第四个子项已完成，P3 正式关闭：**
- `stmmac_xmit()` / `stmmac_tx_clean()`：普通 TX 提交与回收主逻辑未发现有效新增差异；初步误报的 queue 参数变化已撤销。
- `stmmac_hw_setup()`：函数体一致。
- `stmmac_tso_xmit()`：存在 TSO 专用变化，但当前 DHCP/UDP 普通广播不命中。
- `__stmmac_open()`：SerDes 条件分支差异，Panther RGMII 不命中。
- `stmmac_mac_link_up()`：新增 SerDes powerup 分支不命中 Panther；speed callback 参数变化在 Rockchip RGMII 实现中不改变 speed 配置逻辑。
- `stmmac_dvr_probe()`：发现 c2f148d 中 `LED_FIX` 明确启用，并注册 RTL8211F UID `0x001cc916` fixup；该 fixup 在 PHY init 时写 LED 扩展页 D04 的 Reg 0x10/0x11，代码语义为 LED 配置。未发现其写入 PHYCR、RGMII delay 或 TX/RX 数据通路寄存器；且 6.12.81 候选没有该 stmmac fixup 注册段，因此不是两个异常版本共同具备的有效根因线索。
- 6.1.174 与 6.12.81 共有、6.1.116 不存在、且实际命中 Panther 普通 RGMII TX 的有效 STMMAC core 差异：未发现。
- P3 报告：`PANTHER-X2-P3-STMMAC-LINKUP-PROBE-CLOSEOUT-20261120.md`。
- **P3 正式关闭**。这表示限定源码审计未找到有效共同 TX 路径差异，不表示 GMAC 故障根因已解决。
- 当前源码候选与发布二进制构建 inputs 仍未逐字节闭环；该不确定性保留，不扩大本阶段。



### P4：pinctrl 首 pin 错误处理差异（已正式关闭：潜在错误路径存在，现场触发未证实）

- 精确比较三个源码端点的 `rockchip_pmx_set()`：正常 6.1.116 使用 `if (ret)`；异常 6.1.174-rk35xx 与 6.12.81-rk35xx 使用 `if (ret && cnt)`。
- 若 group 第一个 pin 的 `rockchip_set_mux()` 返回错误，异常版本会跳过错误返回并最终返回 0；循环已 break，group 后续 pin 不会配置。这是真实跨两个异常源码候选共有、正常版本没有的潜在软件错误路径。
- Panther GMAC1 M0 的 `tx_bus2`、`rgmii_clk`、`rgmii_bus` group 首 pin/后续 pin 顺序已核实：首 pin 写入失败可分别跳过 TXD1/TXEN、TXCLK、TXD2/TXD3 等后续 TX pin。
- RK3568 mux=3 是合法 4-bit IOMUX，不命中 RK3506 RMIO 或其他 SoC 特殊分支；正常路径 regmap 写入错误可传回 `rockchip_pmx_set()`。
- **未验证：** Panther 实际启动时 GPIO3 IOMUX regmap 写入是否失败、具体 group、运行时 ownership/硬件 mux 状态。不得将潜在机制认定为根因。
- P4 报告：`PANTHER-X2-P4-PINCTRL-FIRST-PIN-ERROR-CLOSEOUT-20261120.md`。
- **P4 正式关闭**：不再扩大源码搜索、不制作补丁、不操作 Panther。该候选保留为未证实的低至中优先级风险。

### P5：物理边界波形验证（待决策，未授权）
只有在汇总现有证据并说明测试目的、仪器、接线、风险和判定标准后，取得用户明确授权才可讨论/执行。不得自行安排实机操作。

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


## 2026-11-20 P4 触发路径复核更新

在 P4 closeout 后进一步核对 Panther RK3568 正常 pinctrl/regmap 路径：
- Panther GRF syscon 无 clocks/resets/hwlocks，使用普通 MMIO regmap；
- 相关 GPIO3 mux=3 合法；
- RK3568 不命中 RK3506 RMIO 专用分支；
- 未设置 `rockchip,group-info`，不启用 Trust Firmware group-info SMC 校验；
- 普通 MMIO regmap read/write callback 正常路径返回 0。

因此 P4 的通用 `if (ret && cnt)` 缺陷仍然存在，但尚未找到 Panther 正常路径中使首 pin `rockchip_set_mux()` 返回 errno 的现实触发源。优先级从低至中降为极低/理论候选；不再追加 P4 测试，不读危险 MMIO/debugfs，不制作补丁。

下一步若继续，重点不再是扩大相同源码审计，而是先评估 P5 物理边界验证的可行性与成本；P5 未经用户明确授权不得执行。


## 2026-11-20 历史时间基线澄清：boot-before-6.1.116

用户结合此前回退操作的历史语境明确指出：`boot-before-6.1.116.tar.gz` 中的 `before`，很可能是“回退/恢复到 6.1.116 之前”，而不是“从原始 6.1.65 升级到 6.1.116 之前”。该解释与归档内容相符。

已在用户 iMac 上只读检查归档清单，确认其中包含：
- `System.map-6.18.63-ophub`
- `uInitrd-6.18.63-ophub`
- `vmlinuz-6.18.63-ophub`
- `dtb-6.18.63-ophub`
- `initrd.img-6.18.63-ophub`
- `config-6.18.63-ophub`
- `dtb/rockchip/rk3566-panther-x2.dtb`

**当前采用的历史解释：** 该归档是回退到 6.1.116 之前保存的 6.18.63 阶段 `/boot` 快照。6.18.63 很可能是此前升级尝试运行过、后来回退的版本。归档文件名中的 `before-6.1.116` 不代表原始 6.1.65 基线，也不应再被当作识别最初安装版本的证据。

**证据等级与边界：** 归档清单已验证其内容属于 6.18.63 内核文件集合，并含 Panther X2 专用 DTB；“它是在回退到 6.1.116 前备份”的时间语义来自用户对历史操作的明确解释，且与内容一致。6.18.63 的确切升级时间、升级来源、回退原因及完整操作顺序仍未由日志独立验证。不要继续围绕 `before` 命名反复推断，也不必为证明 6.18.63 曾存在而重复检查该归档。

**主线调整：** 原始软件版本研究以用户找到的 6.1.65 原始镜像和已确认正常的 6.1.116 实机/备份基线为主；6.18.63 仅作为中间历史节点参考，不再占用主线排查优先级。后续比较必须区分“原始 6.1.65 → 正常 6.1.116”与“曾尝试升级到 6.18.63 后回退”这两段不同历史。


## 2026-11-20 原始 6.1.65 FIT 默认设备树身份核验

原始镜像报告第 19 节已记录完整证据。当前新增的关键已验证事实：
- 原始 IMG 偏移 `0x800000` 的 FIT control FDT 声明 `/configurations/default = "conf"`；默认配置描述为 `rk3568-radxa-e25`。
- 默认配置引用 `fdt = "fdt"`。该 payload 位于镜像偏移 `0x958800`，长度 20,421 bytes；实测 SHA-256 与 FIT 内声明的 SHA-256 完全匹配。
- payload 根节点明确为 `model = "Radxa E25"`、`compatible = "radxa,e25", "rockchip,rk3568"`；GMAC 节点 compatible 为 `rockchip,rk3568-gmac`。

**阶段判断：** 原始 6.1.65 IMG 自带 U-Boot FIT 的默认配置确实指向 Radxa E25 / RK3568 DTB，不是 Panther X2 / RK3566 专用 DTB。这是高优先级启动链错配疑点。

**不可越界推断：** 尚未证明当年 RKDevTool Boot 栏实际选择了该 FIT、实机 U-Boot 一定采用 default 配置，或 6.1.116 正常运行时仍使用该 DTB。因此目前不能将其定为 GMAC TX 根因，也不能据此直接制作补丁或重刷。

**当前工作项调整：** 先完成原始 IMG 内 FIT/DTB 与 6.1.116 已归档启动文件、运行时 FDT 的来源关系核验；同时区分 RKDevTool 的 Boot 输入与 System IMG 内自带的 FIT。沿用既有报告，不重复扫描已确认的分区表、Loader 字符串和基础 FIT 结构。所有操作继续只读，未经明确授权不写 eMMC/TF。


## 2026-11-20 解释边界修订：E25 FIT FDT 是 U-Boot FDT

原始 6.1.65 FIT 中 `/images/fdt` 的 description 明确为 `U-Boot dtb`；该 FIT 配置组合为 ATF firmware 与 U-Boot loadables。因此此前核验的 Radxa E25 / RK3568 FDT 是 U-Boot proper 所用/随 U-Boot FIT 交付的 FDT，**不能据此声称 Linux 6.1.65 或 6.1.116 使用了 E25 Linux DTB**。

6.1.116 实机归档另有 `fdtfile=rockchip/rk3566-panther-x2.dtb` 和 Panther X2 runtime FDT 证据。这与 U-Boot FIT 内 FDT 属于不同启动阶段，可以同时成立。

同时修正研究方法：不以 `Radxa E25`、`RK3568`、甚至源码路径中的 SoC 名称单独判断兼容性；应追踪实际执行的二进制、U-Boot 实际控制器资源/时钟/复位/pinctrl，以及 Linux 最终加载的 DTB 和驱动路径。已有 RK3566 驱动使用 `rk3568_ops`、RK3566 启动配方复用 `rk3568_bl31` 的仓库证据，进一步说明代码/组件命名不等于板级身份。

**当前工作项：** 只读识别原始 IMG 第一个分区的文件系统与启动目录，核实 Linux Panther X2 DTB、boot script 和环境是否独立存在；再与 6.1.116 已归档 boot.cmd/boot.scr、fdtfile、磁盘 DTB、running FDT 对照。不得重做基础 FIT 扫描，也不得据名称差异直接定根因或制作补丁。


## 2026-11-20 用户提供的 6.1.65 / 6.12.81 镜像对比报告交叉核查

用户提供并归档的报告：`docs/reports/2026-11/网卡DHCP故障分析报告.md`（blob `1fcef7bb72ab71e16fd6e7dea8d42e6b999c19b3`）。该报告比较 6.1.65 正常镜像与 6.12.81 DHCP 异常镜像，补充了 rootfs 网络管理配置差异。

### 1. RGMII delay 方向：不重新打开

仓库既有 `PANTHER-X2-RGMII-TX-DELAY-THREE-KERNEL-COMPARISON-20261119.md` 已对正常 6.1.116、最早异常 6.1.174、异常 6.12.81 三个精确源码端点完成对比：
- Panther 三版均为 `phy-mode="rgmii"`、TX delay `0x30`、RX delay `0x10`；
- RTL8211F PHY 内部 TX/RX delay 处理相同；
- Rockchip GMAC GRF 的最终 delay 数值及 enable 状态相同；
- 6.1.116 与 6.1.174/6.12 的差异是 CON0/CON1 写入顺序，不能解释稳定运行后持续 TX 丢帧。

用户新报告提及的 2025-03 `DELAY_ENABLE` 上游变更与既有专项报告属于同一项变更，不构成新的未审计方向。该项保持关闭，不重复源码审计或调整 delay。

### 2. NetworkManager / DHCP 方向：报告中的根因推断尚不成立

已核对 NetworkManager 官方配置说明：
- `[ifupdown] managed=false` 只影响 `/etc/network/interfaces` 中列出的接口；
- 如果故障镜像确实删除了该文件，不能仅凭此选项推断 eth0 被 NetworkManager 标记为 unmanaged；
- 移除 `networking.service` 也不等于 NetworkManager 无法独立执行 DHCP。

同时核对项目既有 Armbian build 固定源码快照 `3f3849bf50bfadff94d0d488eb968bdaf970dc72`：
- NetworkManager 扩展安装 `network-manager`、`netplan.io`；
- 默认 Netplan 文件 `00-default-use-network-manager.yaml` 仅设置 `renderer: NetworkManager`，其注释明确设计意图为所有设备交由 NetworkManager 管理，检测到 carrier 后通过 DHCP 自动配置；
- 这条路径不依赖额外独立的 `dhclient` / `dhcpcd` 服务。

**证据边界：** 该 Armbian build 固定源码快照说明预期配置路径，不证明用户所测 6.12.81 镜像 rootfs 一定使用了完全相同文件；Ophub 构建流程曾使用 moving `main`，实际构建 commit 和镜像内文件内容尚未闭环。故仍需实际 rootfs 文件及 NetworkManager 运行状态才能最终排除 DHCP 接管问题。

### 3. 对 GMAC TX 根因定位的影响

NetworkManager 配置只能解释“是否发起 DHCP / 是否取得地址”，不能解释此前已完成的 6.12.81 实机测试中：驱动报告 TX 成功、tcpdump 可见、UDP checksum 正常、tx_errors=0，但第三方同二层监听器收不到广播帧。

因此将 NetworkManager/DHCP 保留为独立的用户态启动配置核查项，不作为 GMAC TX 物理发送故障的根因候选；不因 DHCP 报告而回退到已完成的 delay、普通 TX 或驱动初始化源码审计。

### 4. 后续路线

- 不重复 RGMII delay 三版本审计。
- 不把 `managed=false` 或移除 `networking.service` 单独当成 DHCP 根因。
- 如需单独结清 DHCP 支线，应只核对故障镜像实际 Netplan YAML、NetworkManager 配置/插件、eth0 设备状态与 DHCP 日志；不修改系统配置。
- GMAC TX 的软件静态审计已覆盖 P1–P4；当前仍未定位 MAC/RGMII/PHY/MDI 的实际故障边界。若继续追求物理根因，需要先评估 P5 的最小波形验证方案、仪器/接线、风险与判定标准，再由用户明确授权；未经授权不操作实机。


## 2026-11-20 用户确认：双黄金基准的软件资产逐项替换路线

用户明确确认采用其《网卡 DHCP 故障分析报告》的逐项比较方法：以正常版本为参照，从最可能的差异开始逐项核对、逐项设计软件替换验证；不考虑示波器/逻辑分析仪等硬件波形测试。未经明确授权，不启动故障内核、不刷写或替换设备文件。

### 已完成子项

1. **6.1.65 与 6.1.116 GMAC Linux DTB 语义交叉核对：** 已归档 `PANTHER-X2-GOLDEN-DTB-CROSSCHECK-6.1.65-6.1.116-20261120.md`。两条黄金线的 GMAC 主节点、RGMII、delay、PHY 地址、M0 pin groups、clock parent 设计高度一致；未发现值得优先替换的 GMAC DTB 差异。该结果不是完整 DTB 逐字节比较。
2. **四版本资产来源矩阵：** 已归档 `PANTHER-X2-FOUR-VERSION-KERNEL-ASSET-MATRIX-20261120.md`。确认 6.1.65 原始 IMG 含 Image、uInitrd、Panther DTB；6.1.116 的 boot/DTB/modules 归档已校验；6.1.174 与 6.12.81 官方 RK35xx 发布资产身份及摘要已记录；6.12.81 的 GMAC 主链为 built-in。

### 当前唯一工作项：补齐 6.1.65 与 6.1.174 内核套件闭包

按最小范围推进，不重复已完成的 DTB、RGMII delay、STMMAC 普通 TX、PHY workaround、pinctrl 等源码审计：

A. 6.1.65 原始 IMG rootfs：只读确认 `/lib/modules/6.1.65-ophub`、`modules.dep`、`modules.builtin`、`modules.order`，以及 `config-6.1.65-ophub` 或 Image 内嵌 IKCONFIG 是否存在；建立 Image 与 modules 的版本匹配关系。

B. 6.1.174 官方自动包：对资产 `6.1.174.tar.gz`（SHA256 `49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a`）只读索引内部 boot/modules/DTB/config 子包与校验清单；不与 `deb-6.1.174.tar.gz` 或 Flippy 手动资产混淆。

C. 6.12.81：已有完整 config/modules 审计，不重复；仅在四版本套件闭包需要时引用既有报告。

D. 对照两条黄金线与两条故障线的 built-in / module 分布、kernel release、config、initramfs 依赖及打包布局。只有找到一个满足“两个正常版本共同具备、两个故障版本共同缺失或行为不同、且能独立替换并保持 ABI/依赖闭包”的变量，才把它列为首个实机软件替换候选。

### 替换实验门槛

- 不把跨版本 `.ko` 当作可互换文件；必须核对 vermagic、modversions、符号依赖及 kernel release。
- 若 GMAC 主链 built-in，替换单个模块无效；需要按依赖闭包定义内核套件或寻找可独立替换的上游组件。
- 每轮只改变一个可定义的软件变量，保持其他启动组件/测试环境不变；预先准备回退到 6.1.116 的方案与校验值。
- 源码差异只能提出候选，最终是否有效必须由用户授权后的实机 A/B 结果决定。

**路线说明：** 本项目当前不安排 P5 波形/硬件测量。旧阶段报告中的 P5 仅作为历史方案记录，不再作为当前执行路线。当前以软件资产闭包、版本差异和受控替换为唯一推进方向。


## 2026-11-20：6.1.174 官方包只读审计工作流已建立

用户同意：只要对四版本差异比较有意义即可，要求不得偏离 GMAC TX 根因调查路线。

已新增 `.github/workflows/audit-rk35xx-6.1.174-kernel.yml`，commit `48256669797c4be88d9cf1390fb8165e4980a49a`。

工作流约束与范围：
- 仅 `workflow_dispatch` 手动触发；`permissions: contents: read`；Ubuntu GitHub runner；不访问 Panther X2、不读取用户本地数据。
- 固定下载 Ophub `kernel_rk35xx` Release 的 `6.1.174.tar.gz`，asset size 135,267,299 bytes，SHA256 `49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a`；下载后重新校验 size/hash 和 gzip 完整性。
- 读取外层发布包清单和 `sha256sums`，枚举全部内层 tar.gz/tgz，逐一核验发布清单中的 SHA256，生成完整成员索引。
- 从内层包提取/读取内核配置关键项、modules.builtin 中 GMAC/PHY 内建路径、GMAC/PHY 相关模块路径，以及 Image、DTB、modules.dep/modules.order 等关键文件的存在性和摘要。
- 不安装、不执行、不刷写内核/模块/DTB/initramfs；产物作为 Actions artifact 保存 30 天。
- 报告必须区分官方发布包内容与历史实机安装来源；本工作流不能证明历史现场确实安装了该包，也不能单独证明源码 commit 到二进制的构建关系。

**状态：工作流文件已提交，尚未运行。** 当前连接的 GitHub 工具没有 workflow_dispatch 写入/触发动作，因此不能声称已经开始或完成审计。需要在 GitHub 仓库 Actions 页面手动运行 `Audit Ophub RK35xx 6.1.174 kernel package`，随后读取 run/artifact 结果继续分析。不得为了触发而把 workflow 改成 push 自动运行。

后续只围绕本轮产物补齐 6.1.174 内核套件闭包，再补齐 6.1.65 原始 IMG rootfs 的 modules/config 索引；不重复 6.12.81 已完成的 built-in 驱动配置审计，不返回已关闭 P1–P4 源码支线。


## 2026-11-20：6.1.174 官方内核包审计已成功完成

用户提供 Actions Job URL 后，已读取 run、job steps、完整 job logs 和 artifact，并下载 artifact 在分析环境中展开核对。

- Run `44728503121` / Job `136261930960`：success，5/5 steps 成功。
- Artifact ID `14625845189`，SHA256 `4d0da74e574037eeea37bbd2a5cd868b02bf7ea1c48532b08f9ede97e3f8fce2`。
- 官方 6.1.174 外层资产 size/SHA256 匹配；boot、dtb-rockchip、modules、header 四个内层包 SHA256 全部匹配发布清单。
- 6.1.174 config：`CONFIG_STMMAC_ETH=y`、`CONFIG_STMMAC_PLATFORM=y`、`CONFIG_DWMAC_ROCKCHIP=y`、`CONFIG_PHYLIB=y`、`CONFIG_REALTEK_PHY=y`、`CONFIG_MDIO_BUS=y`、`CONFIG_OF_MDIO=y`；`CONFIG_MODVERSIONS` 未启用。
- `modules.builtin` 明确列出 stmmac、stmmac-platform、dwmac-rockchip、libphy、realtek PHY、of_mdio 等 built-in 路径；modules 文件索引中没有 Panther GMAC 主链独立 `.ko`。这与既有 6.12.81 built-in 结果一致，也符合 6.1.116 已知正常主链为 built-in 的情况。故“替换单个 GMAC .ko”不构成有效实验，跨版本混用模块更不应尝试。
- 官方 DTB 套件含 `rk3566-panther-x2.dtb`，SHA256 `871bad4ded75e9da3aea61e26a9a26516c9f39968c49d5f32de2124420185e75`。目前仅确认文件存在，尚未与两条黄金线做 6.1.174 GMAC 节点字段差异；不能仅凭 hash 判断好坏。
- boot 套件有 vmlinuz、initrd.img、uInitrd、System.map、config 五项。当前工作流未生成 vmlinuz 本体 hash，后续如需精确资产比对应补上。

详细报告：`docs/reports/2026-11/PANTHER-X2-6.1.174-OFFICIAL-KERNEL-ASSET-AUDIT-20261120.md`。

### 路线收敛

当前不做模块替换；不立即替换 DTB。下一个最有价值的比较项是：对 6.1.174 官方 Panther DTB 做 GMAC 节点定向解码，与 6.1.65/6.1.116 黄金 DTB 已有字段逐项对照，同时补记 6.1.174 vmlinuz hash。若无差异，再收口 DTB 候选。随后补齐 6.1.65 原始镜像 rootfs 中 modules/config 闭包，才能形成真正四版本统一矩阵。任何候选仍需有明确可控的单变量软件替换方案才进入实机验证。
