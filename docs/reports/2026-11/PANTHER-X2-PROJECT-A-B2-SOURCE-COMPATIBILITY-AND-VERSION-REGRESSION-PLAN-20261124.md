# Panther X2 项目 A：B2 源码适配、版本回归与组件恢复审查计划

- 日期：2026-11-24
- 阶段：B2-0 策略修订
- 目标内核：Ophub Linux 6.18.y；当前 B1 精确源码基线为 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`（6.18.63）
- 研究对象：Panther X2 / RK3566 板载 GMAC1、DWMAC4、MDIO、RTL8211F 及其必要的 Linux 网络核心和 SoC 资源。
- 本文不执行构建、设备测试、补丁应用或版本回退；只定义源码审查和决策流程。

## 1. B2 目标重新定义

B2 不是把 B1 关闭的 Kconfig 选项按顺序重新打开。B2 的首要任务是确认 Linux 6.18.y 中每个关键组件的源码实现是否正确、是否适配 Panther X2/RK3566、是否引入版本回归，以及是否需要选择其他已验证版本的组件实现、回退单个组件或进行最小修正。

组件配置审查是第二层工作：在源码版本和实现适配性判断之后，复核配置依赖、DTS、时钟、复位、电源、DMA、中断和用户空间闭包，完成组件组合与查漏补缺。

### 1.1 双层审查原则

**第一层：源码/版本/硬件适配（主线）**
- 比较组件在 6.1.65、6.1.116、项目 B 已审查的 6.1.174/6.12.81，以及目标 6.18.63 精确源码中的实现变化。
- 判断变化是上游正常演进、Rockchip BSP 特定实现、硬件适配差异、代码质量退化、已知修复缺失，还是与 Panther 当前故障路径无关。
- 检查返回值处理、资源获取失败路径、初始化/复位/电源/时钟顺序、并发/生命周期、DMA/cache/IOMMU 语义、寄存器编程和设备树接口。
- 对每项差异判定 Panther X2 是否实际命中该代码路径，以及是否有运行时证据支持。
- 形成保留 6.18 原实现、选择上游修复、回退单个组件、移植最小补丁或暂不改动的决策。所有改动必须有源码依据和可验证假设。

**第二层：配置复合/查漏补缺（辅助线）**
- 继承项目 B 已完成的 Kconfig、DTS、时钟树、reset、pinctrl、regulator、DMA、IRQ、PHY 和运行时证据。
- 仅检查 6.18.63 的最终配置和 Panther X2 DTB 是否正确连接所选组件；补齐遗漏依赖、错误的 compatible/属性/资源引用。
- 不把配置值相同等同于驱动实现相同，也不把配置/DTB 编译通过等同于硬件适配完成。

## 2. 版本和证据基线

| 标识 | 精确版本/来源 | 角色 | 证据边界 |
|---|---|---|---|
| G65 | Armbian Linux 6.1.65，Panther X2 本机实测 | 正常网络黄金基线 | 已验证 RTL8211F、RGMII、千兆全双工、DHCP、网关/外部 IPv4、DNS；启动介质为 TF rootfs + eMMC /boot 混合 |
| G79/G112 | Linux 6.1.79、6.1.112；对应系统备份存在于本机 eMMC 历史备份 | **早期正常运行版本候选/正向历史基线** | 用户明确说明：这两版若在本机 eMMC 备份中，必定曾在本机实机运行；用户不记得 6.1.116 之前发生过网络不通，且网络中断会使机器应用功能不可用。因此按“实机运行且用户回忆网络正常”纳入正向证据。专项网络验收日志/精确 Image、DTB、config、源码 commit 仍待恢复；不得标成有抓包专项验收。 |
| G116 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，Linux 6.1.116 | 正常网络黄金基线及源码对照 | 已验证驱动/PHY、千兆链路、DHCP、LAN 连通；保留历史采集证据边界 |
| R61Y | Linux 6.1.y 后期升级版本族（用户确认曾升级多个小版本，网络故障始终相同；各次具体小版本待恢复） | **跨小版本持续异常的版本族** | 与 6.1.79/6.1.112 早期正常版本区分；用户确认网络故障是在后续升级阶段出现并持续。逐个异常版本的实机记录、Image/DTB/config/source commit 尚需绑定。不能把整个 6.1.y 系列简化为单一 6.1.174。 |
| R174 | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，Linux 6.1.174 | 6.1.y 异常版本族中的一个已被项目 B 重点审计的源码候选 | 构建源码映射为高置信度候选，不代表它是用户记忆中的第一个故障版本，也不是所有历史报告中的绝对二进制证明 |
| R612 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，6.12.81 | 项目 B 已有实机异常与精确源码审查对象 | PHY/千兆 link 正常、DHCPv4 未成功；TX 外部物理边界未闭环 |
| T618 | `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`，6.18.63 | 当前 B1 构建和后续 B2 的精确目标源码 | B1 已实机启动；网络被隔离，尚无 6.18 Ethernet 运行证据 |

**比较规则：** 正常/正向历史线包括 6.1.65、6.1.79、6.1.112、6.1.116；其中 6.1.79/6.1.112 的实机运行与网络正常来自用户对本机 eMMC 备份和使用历史的明确确认，专项验收证据完整度低于 6.1.65/6.1.116。异常线是后续 6.1.y 多个升级版本（具体小版本待恢复），6.1.174 是其中一个精确源码审计样本，不能代表全部测试版本；6.12.81 是另一异常样本；6.18.x 历史完整系统需按具体构建绑定，6.18.63 B1 是网络隔离目标源码基线。不能把 6.12.81 的源码差异直接推定为 6.18.63 仍存在，也不能把 6.1.116 的私有修改无条件移植到 6.18。

## 3. 项目 B 已有源码审计成果：复用，不重做

以下历史工作是 B2 的输入。进入对应组件前先回读原报告和源码 commit，不重新执行已经完成的设备测试。

### 3.1 STMMAC / PHY 初始化路径

- 6.1.116 的 `stmmac_init_dma_engine()` 在 DMA reset 前存在 `msleep(1500)`；同一 JL2xx1 workaround 还在 MDIO 注册后对 PHY 地址 0 执行 page 2627 / reg 25 = `0x1801`、回 page 0、BMCR soft reset 四次写入。
- 该 workaround 在已审计的 6.1.174 RK35xx 与 6.12.81 RK35xx 源码中均不存在。
- 该修改标题指向 JL2xx1，而 Panther 实机 PHY 是 RTL8211F。虽然 6.1.116 正常环境确实包含它，且 RTL8211F 驱动后续只 mask PHYCR2 bit 0，不清除其他位，但这不能证明 JL2xx1 专用写入对 RTL8211F 必要或安全。
- 当前等级：**高价值版本差异候选，非根因；禁止直接移植 PHY 寄存器写入。**
- 原报告：`6.1.116-174-6.12-SHARED-GMAC-REGRESSION-AUDIT-20261118.md`、`116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`。

### 3.2 Rockchip GMAC clock enable / settle / error handling

- 6.1.116 使用 bulk clock prepare-enable 并检查错误，clock selection 后等待 5ms。
- 6.12.81 RK35xx 改为逐项 clock enable，存在忽略 `clk_prepare_enable()` 返回值后仍设置 `clk_enabled=true` 的条件性静默失败路径；等待缩短为 100–200µs，并新增 CSU disable 行为。
- Panther RGMII 实际命中的 clocks、共享 CCF handle、CSU provider 条件及调用顺序已做过专项分析；不能把所有时钟差异都泛化为实际故障。
- 当前等级：**明确源码质量/时序差异；6.18 是否继承、是否实际命中以及对 RK3566 的影响均待精确核查。**
- 原报告：`PANTHER-X2-6.1.116-VS-6.12.81-RK3566-GMAC-CLOCK-SEQUENCE-REGRESSION-20261119.md`、`PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md`、`PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md`。

### 3.3 RGMII delay 写入顺序

- 6.1.116 的 RK3568 GMAC 路径先写 delay value，再写 RGMII mode/delay enable。
- 6.1.174/6.12 路径顺序相反；相关上游改动目标涉及 RK3566/RK3568 的 RGMII_ID/RXID/TXID delay enable/disable。
- Panther 当前为 `phy-mode="rgmii"`，TX/RX delay `0x30/0x10`。不得只因顺序变化就认定是故障根因。
- 当前等级：**已确认源码差异，Panther 实际影响待核查。**
- 原报告：`6.1.116-174-6.12-SHARED-GMAC-REGRESSION-AUDIT-20261118.md`、`PANTHER-X2-6.1.116-VS-6.12.81-RK3566-GMAC-CLOCK-SEQUENCE-REGRESSION-20261119.md`。

### 3.4 STMMAC PHY resume 上游修复适用性

- 6.12.81 精确源码不包含 `phylink_prepare_resume()`。
- 但其 MTU reopen 路径会 disconnect PHY，reopen 时重新连接；与该上游修复针对的“PHY 保持连接但 suspended”生命周期不同。
- 当前没有 MTU reopen / DMA reset timeout 证据，已从当前 DHCP 主故障候选中降级。
- 当前等级：**精确源码差异已确认，但现有证据不支持直接移植该补丁。**
- 原报告：`PANTHER-X2-6.12.81-STMMAC-PHY-RESUME-PATCH-APPLICABILITY-20261119.md`。

### 3.5 DWMAC4 DMA 与 TX 物理边界

- 已检查 6.1/6.12 的 DWMAC4 DMA channel 初始化和寄存器地址抽象；Panther 未配置可选 `dwmac4_addrs`，因此新 helper 回退到标准寄存器布局。
- 已有 TX 证据：`stmmac_xmit()` 返回 `NETDEV_TX_OK`、descriptor 被清理、同一启动周期 Linux TX 与 MMC TX 计数同步增长；外部 iMac 未捕获自定义广播/单播测试帧。该证据不能证明帧已通过 RGMII/PHY 电气出线。
- 已有审计明确撤销跨启动周期的 TX 计数断层结论；不能复用已撤销的旧推断。
- 当前等级：**部分源码路径已比对，物理出线边界未闭环；B2 只继承结论，不重新开启项目 B 的专项根因实验。**
- 原报告：`PANTHER-X2-RK3566-GMAC-ROCKCHIP-GLUE-AND-DWMAC4-DMA-REGISTERS-116-VS-174-20261119.md`、`PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`。

### 3.6 PHY driver

- 6.1.116 实机已确认绑定 Linux RTL8211F PHY driver，PHY ID `0x001cc916`，MDIO 地址 0。
- 6.1.116/6.1.174/6.12.81 的 RTL8211F config_init 对 PHYCR2 只 mask bit 0，不清除 bits[13:12]/bit11。
- PHYCR2 reserved 位的硅片语义、reset 后持久性和 JL2xx1 workaround 对 RTL8211F 的实际影响尚未证实。
- 当前等级：**驱动行为静态审计已完成；寄存器语义和因果关系未验证，不做寄存器写入。**

## 4. B2 源码审查矩阵：每个组件都要先判断“代码是否适合”，再判断“配置是否正确”

| 组件层 | 必须检查的源码问题 | Panther X2 硬件适配重点 | 配置复核（辅助） |
|---|---|---|---|
| Linux 网络核心 | 6.18 网络栈 API/生命周期、netdev/packet/ARP/IPv4 路径的版本变化及已知修复 | ARM64/RK3566 通用路径；只覆盖本阶段实际需要的协议 | NET/INET/PACKET、loopback、IPv4/ARP/ICMP |
| STMMAC core | open/close、DMA reset、PHY/phylink 生命周期、TX/RX/NAPI、错误处理和资源回滚 | Synopsys DWMAC 4.20a、Panther DMA 宽度/队列/AXI 能力 | STMMAC_ETH、平台框架、built-in/module |
| DWMAC4 | DMA channel/MTL mapping、descriptor/OWN/barrier、ring/tail、IRQ、DMA address/coherency | RK3566 32-bit DMA host/device width、无 GMAC IOMMU/memory-region 声明的当前 DTS | DWMAC4 相关选项、DMA API 依赖 |
| Rockchip GMAC glue | clock get/enable 返回值、clock/reset/power 顺序、speed callback、RGMII GRF 配置、CSU 条件 | RK3566 GMAC1、clock input、125MHz、RGMII、TX/RX delay、共享 CCF clock | DWMAC_ROCKCHIP、clock/reset/pinctrl/regulator providers |
| CCF/CRU | provider API 变化、parent/rate/gating、enable count/error propagation | SCLK_GMAC1、SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED、ACLK/PCLK_GMAC1 | clock phandle、assigned-clocks/parents/rates |
| MDIO/PHYLIB/PHYLINK | bus registration、scan、attach、link state、suspend/resume、错误/超时传播 | MDIO1、PHY addr 0、RGMII 连接与 reset 时序 | MDIO_BUS、OF_MDIO、PHYLIB、PHYLINK |
| Realtek PHY | RTL8211F probe/config_init、RGMII delay、soft reset、EEE/clock/LED 修改、寄存器 mask | PHY ID 0x001cc916、RTL8211F 实际芯片语义；不套用 JL2xx1 专用 workaround | REALTEK_PHY、PHY firmware（如实际需要） |
| pinctrl/reset/regulator/GPIO | provider 初始化顺序、defer probe、错误处理、资源共享和 suspend 状态 | GMAC1 M0、GPIO3_PA1 active-low reset、vcc_3v3；不误关共享 PMIC/CRU | 节点 status、pinctrl groups、reset delays、supply |
| ARM64 DMA/cache/IOMMU | DMA ops 选择、coherency、mapping/unmapping、barrier、地址宽度和 IOMMU attach | RK3566 DMA mask、32-bit DMA、当前 GMAC 无 iommus/dma-coherent 声明 | DMA/IOMMU 配置和设备树引用 |
| IRQ/NAPI | IRQ mapping、request/free、NAPI schedule/complete、poll/queue 关联 | GMAC IRQ 与 DMA channel/MTL queue 对应 | interrupts/interrupt-names、GIC/IRQ provider |
| Panther X2 DTS | binding 变化、compatible match、资源名变化、默认值和新增必需属性 | fe010000 GMAC1、MDIO1、RTL8211F、M0 pinctrl、clock/reset/supply | B1 clean DTB 与原始板级 DTS 的差异 |

## 5. B2 阶段顺序（源码审查先于配置恢复）

| 阶段 | 主任务 | 组件配置工作 | 阶段放行条件 |
|---|---|---|---|
| B2-0 | 汇总黄金基线、项目 B 既有审计与差异清单；锁定 6.18.63 精确源码 | 只做最终 config/DTB 的待核对项登记，不重复项目 B 已完成配置审计 | 建立组件审计账本、证据等级、待验证差异与审查顺序 |
| B2-1 | 网络核心源码/API/版本审查 | 最小 NET/INET/PACKET/loopback 配置闭包 | 6.18 核心源码审查通过，依赖配置闭包有依据 |
| B2-2 | STMMAC core + DWMAC4 源码版本审查 | STMMAC/DWMAC4 依赖配置；GMAC DT 仍 disabled | reset、DMA、TX/RX、IRQ/NAPI 关键路径无未解释高风险差异，或已有受控修复方案 |
| B2-3 | Rockchip GMAC glue + CCF/CRU 源码审查 | GMAC1 时钟、reset、pinctrl、regulator、GRF 配置复核 | Panther 实际命中路径已追踪，错误处理/时序/clock parent 差异有结论 |
| B2-4 | MDIO/PHYLIB/PHYLINK/RTL8211F 源码审查 | MDIO1/PHY addr 0/compatible/reset/supply 配置复核 | PHY 生命周期和寄存器初始化路径已审查；无未经证实的 PHY 写入 |
| B2-5 | 全组件版本/配置复合、差异收敛与最小运行验证方案 | 生成最终 config、DTB、模块/内建清单和工具闭包 | 每个组件有保留/修复/回退/待验证结论；完成集成试验卡后才进入构建与实机验证 |

B2 每个阶段均执行：**先源码对照 → 确认 Panther 路径是否命中 → 评估版本/补丁选项 → 再核对配置/DTB → 写试验卡**。静态审查可并行阅读不同组件，但实机变量仍必须一次只改变一个。

## 6. 组件版本选择与修改纪律

每个候选差异必须填写：

1. 组件名、文件路径、函数/调用链；
2. 6.1.65/6.1.116/6.1.y 各次实测版本（逐个记录）/6.12.81/历史完整 6.18.x/6.18.63 对应源码仓库、精确 commit；
3. 原始差异（不只贴配置）及引入/回退 commit；
4. 该差异修复了什么问题，是否有 upstream commit、commit message、review 或 datasheet 依据；
5. Panther X2 的 compatible、SoC revision、PHY ID、DTS 属性和运行条件是否命中；
6. 现有实机证据与该差异的因果关系强弱；
7. 方案：保留 6.18、采用 6.18.y 后续修复、单组件回退、最小 cherry-pick/revert、暂缓或排除；
8. 预期副作用、API 兼容、依赖闭包和回退路径；
9. 验证方式与停止条件。

**版本回退不是默认策略。** 优先考虑同一 6.18.y 分支中有明确修复依据的后续提交；只有证明该提交引入了 Panther 可命中的回归，且上游修复/局部修正不可用时，才考虑单组件 revert/backport。不得为了“像 6.1.116”而整包降回 6.1/6.12，也不得无依据把 JL2xx1 PHY 写入复制到 RTL8211F。

## 7. B2 当前明确不做的事

- 不重复项目 B 已经完成的 U-Boot 启动链、Vendor Storage、基础 DTS/PHY 识别、descriptor/queue 基础检查和已有抓包测试。
- 不恢复 U-Boot DHCP 或 GMAC 根因专项；此前 U-Boot `EQOS_DMA_MODE_SWR stuck` + Data Abort 只限定为 U-Boot 路径异常，不能推导 Linux 6.18 GMAC 根因。
- 不重复运行 6.1.65/6.1.116 已通过的 DHCP/网关测试。
- 不读取 dummy-syscon debugfs registers，不使用 devmem，不做 MMIO/MDIO/PHY 寄存器写入，不做硬件波形实验，除非未来形成单独的安全方案并获明确授权。
- 不引入 Wi-Fi/无线、蓝牙、USB/PCIe 外接网卡；这些不属于项目 A。
- 不在源码差异和适用性尚未解释前制作补丁或切换组件版本。

## 8. B2-0 当前状态与放行门

已完成：
- [x] 6.1.65 正常网络实机黄金基线纳入；
- [x] 6.1.116 正常网络实机黄金基线纳入；
- [x] 6.18.63 B1 自动启动基线及网络隔离边界纳入；
- [x] 项目 B 关键 STMMAC、DWMAC4、Rockchip GMAC clock、RGMII、PHY 源码审计报告定位并纳入 B2 输入；
- [x] 明确源码/版本/硬件适配为主线，配置复合为辅助线。

待完成：
- [ ] 回读并建立所有项目 B 相关报告的组件审计账本，避免漏项/重复；
- [ ] 恢复 6.1.y 后续升级阶段出现相同网络故障的具体小版本清单、每个版本的镜像/DTB/config/source commit 和实机故障记录；6.1.174 仅作为一个代表性源码样本，不称为整个异常族的最早故障版本；
- [ ] 恢复本机 eMMC 备份中的 6.1.79、6.1.112 对应资产身份；按用户确认将其作为实机运行且网络正常的早期正向历史基线，继续补齐专项日志/哈希/源码映射，不再列为“是否实机运行未知”或异常样本；
- [ ] 对 T618 精确 commit 逐项验证上述已知差异是否存在、是否改变、是否命中 Panther 路径；
- [ ] 补齐 T618 组件自身新增/删除/重构/修复的版本差异；
- [ ] 形成组件级保留/修复/回退/待验证决策；
- [ ] 之后才完成最终 config/DTB 复合查漏和 B2-1 构建/验证试验卡。

**当前判定：B2-0 策略已修订，B2-0 尚未完成；B2-1 不放行。** 本文不授权构建、写卡、启动网络镜像或修改设备。

## 9. 关键历史报告

- `6.1.116-174-6.12-SHARED-GMAC-REGRESSION-AUDIT-20261118.md`
- `PANTHER-X2-6.1.116-VS-6.12.81-RK3566-GMAC-CLOCK-SEQUENCE-REGRESSION-20261119.md`
- `PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md`
- `PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md`
- `PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md`
- `PANTHER-X2-6.12.81-STMMAC-PHY-RESUME-PATCH-APPLICABILITY-20261119.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`
- `PANTHER-X2-RK3566-GMAC-ROCKCHIP-GLUE-AND-DWMAC4-DMA-REGISTERS-116-VS-174-20261119.md`
- `PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`
- `PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md`



## 2026-11-24 B2-0 新增源码对照结果：早期正常 6.1.y

新增只读审计报告：
`PANTHER-X2-PROJECT-A-B2-0-EARLY-GOOD-6.1Y-SOURCE-COMPARISON-20261124.md`

本轮确认：
- 找到 `unifreq/linux-6.1.y` 中 6.1.79 commit `e77fb4335d38f79b66ab5e1e3c627f54140fcb2a`、6.1.112 commit `a29ec4768872f856a3a17326334d53482d25fcfa`；6.1.116 使用既有精确 commit `5eb841b59d6ead6e264163785a634e78f0253c8e`。
- 6.1.79/112/116 三个正常历史端点的 `dwmac-rk.c`、`stmmac_mdio.c`、Panther X2 DTS 文件 blob 完全相同。
- `stmmac_xmit()`、`stmmac_init_dma_engine()`、`stmmac_mac_link_up()`、`stmmac_tx_clean()` 三个正常端点函数体完全相同。
- Rockchip GMAC 的 `gmac_clk_enable()`、`rk_gmac_powerup()`、`rk_fix_speed()`、`rk_gmac_clk_init()` 在 6.1.79/112/116 完全相同；stable 6.1.174 端点冷启动 enable 路径也未见功能性变化。
- pinctrl 在 6.1.79→6.1.112 的变化是 rollback 阶段重新计算 bank；错误条件仍为 `if (ret)`。首 pin 错误不会被吞掉。
- RTL8211F `config_init` 在 6.1.79 与 6.1.112/116 之间存在 reset 语义变化，但两个阶段均为用户确认的正常运行历史；6.1.116 与 stable 6.1.174 的 `realtek.c` 文件完全相同。
- 因此，早期正常版本间已有的上述变化，不能单独解释后续网络故障。重点应转向实际首次异常版本的源码来源/patchset，而非把 stable 6.1.174 和 RK35xx BSP 候选混为一谈。

下一步优先：
1. 恢复 eMMC 备份中的 6.1.79/112 Image、DTB、config、modules 身份与哈希；
2. 找出 6.1.116 之后首次出现网络故障的实际小版本和实际源码分支；
3. 对该异常版本绑定精确 source commit、build inputs、patchset；
4. 再映射至 6.12.81 与 6.18.63 的源码继承/重构差异。

阶段仍为 B2-0；不放行 B2-1，不构建、不刷写、不改设备。


## 2026-11-24 研究重点修订：B2-0 以 GMAC1/RGMII 数据通路回归为主线

用户明确要求：结合项目 B 的分段排查结果，B2-0 应重点研究 GMAC 相关源码和硬件适配。项目 B 已经完成的配置审计在 B2 中主要用于复合、查漏补缺；不能把 B2 简化为逐项恢复配置，也不能重复项目 B 已收口的测试。

### A. 先固定故障边界，防止错误归因

项目 B 既有实机证据表明：
- Linux outgoing / AF_PACKET 能提交测试帧；
- 普通 STMMAC TX 路径接受请求，stmmac_xmit() 返回 NETDEV_TX_OK；
- TX descriptor 后续被驱动清理/回收；
- Linux TX 统计与 MAC MMC TX frame/octet 计数增长；
- 同期 iMac 有线接口对测试 EtherType 的持续抓包为 0 个对应帧；
- 没有 TXC/TXD/TX_CTL 波形或 PHY MDI 侧观测。

因此目前只证明 TX 软件提交、descriptor 回收及 MAC 统计有进展；没有证明 MAC 已从 RGMII TX 引脚输出正确帧，也没有证明 RTL8211F 已从 MDI 侧发射。B2 源码研究必须优先审查从 GMAC probe/setup、clock/power/reset、RGMII GRF/pinctrl 到 STMMAC/DWMAC4 DMA/MAC 的完整路径，不能把 Link Up、MMC TX 增长或 NETDEV_TX_OK 等同于物理发送成功。

### B. 项目 B 已有结果的使用规则

以下项目 B 结果视为已有输入，不要求重做设备测试：
1. U-Boot 启动链、MAC 地址来源及 Linux 重新初始化 GMAC 的事实；
2. Panther DTS 的 GMAC1/MDIO1/RGMII/RTL8211F 配置核对；
3. GMAC CRU parent、clock topology、clock_summary 相关审计；
4. RGMII delay 数值、GRF 配置和写入顺序审计；
5. STMMAC 普通 TX、DWMAC4 descriptor OWN/barrier/tail pointer/channel0、DMA reset、TX queue 等专项审计；
6. RX/NAPI、DHCP 客户端、MAC 克隆、offload、EEE、速率等已有排查；
7. pinctrl 首 pin 错误处理静态审计及其 Panther 正常 regmap 路径触发条件复核。

任何重开项必须指出新版本源码或新证据如何改变旧结论。不得重复设备操作，不访问 dummy-syscon debugfs/devmem，不做 MMIO/MDIO 写入、驱动重载、接口重启或物理波形实验。

### C. GMAC 版本回归的优先级

| 优先级 | 研究项 | 已有项目 B 线索 | B2-0 需要完成的工作 |
|---|---|---|---|
| G1 | 6.1.116 正常源码中 STMMAC DMA reset 前 msleep(1500) 与 MDIO 注册后的 JL2xx1 四次 PHY 写入，在 6.1.174-rk35xx / 6.12.81-rk35xx 缺失 | 49b5f340f346cc9a5b777499fce46150b691b70e 引入；异常候选中未见等价实现。workaround 名称指向 JL2xx1，而 Panther 实物仅确认 RTL8211F 家族，不能直接套用 | 分离审查 1500ms DMA reset 前等待与四次 MDIO 写入；核对是否存在 RTL8211F 适用性、PHY 型号/修订差异、等价 backport，以及 6.18.63 是否存在相同/替代机制。禁止直接复制写入 |
| G2 | Rockchip GMAC clock enable 语义变化 | 6.1.116 bulk enable 并检查错误、另启 PHY clock、固定等待 5ms；6.12.81 改逐项 enable、若干返回值未检查、等待约 100–200µs | 精确追踪 6.18.63 对应实现、错误传播和 Panther 实际命中 clock list；与首个异常 RK35xx 构建比较 |
| G3 | RGMII GRF 写入顺序 | 6.1.116 先写 delay value 再 enable/interface；6.1.174-rk35xx 与 6.12.81 候选先 enable/interface 再写 delay value | 追踪进入 6.18.63 的具体提交及 plain RGMII（非 ID 模式）语义；区分确有源码差异和能解释当前板级失败 |
| G4 | GMAC probe/setup/power handoff | rk_gmac_probe()/rk_gmac_setup()/rk_gmac_powerup() 的条件分支和资源处理存在跨分支变化；部分 clock helper 相同不能代表整个 probe path 相同 | 逐函数审查 clock/reset/regulator、runtime PM、PHY supply、STMMAC handoff、错误清理与 defer probe |
| G5 | PHY/RXC 与 DMA reset 时序 | 上游存在 RK3566 + RTL8211F-VD + RGMII 在 PHY power-down 后 RXC 停止、导致 reopen 时 DMA reset 失败的真实案例；修复为硬件 setup 前恢复 PHY | 先核实 Panther 实际 PHY 型号/修订和是否存在 reopen/MTU change 触发；核对 6.18.63 是否包含等效修复。该场景是条件性候选，不得将其误判为已发生 |
| G6 | STMMAC/DWMAC4 TX descriptor/DMA | 项目 B 已核对 OWN/barrier/tail pointer、channel0、DWMAC4 start；当前未发现能解释现象的共同差异 | 不重复基础路径；仅当 6.18.63 与已知正常源码出现具体新差异时，才重开 descriptor/cache/DMA mapping |
| G7 | pinctrl/IOMUX 首 pin错误 | 两异常 BSP 候选出现 if (ret && cnt)，正常 6.1.116 为 if (ret)；后续已发现 Panther 正常 syscon/regmap 路径缺少明显 errno 来源 | 保留为低优先级理论候选；除非新证据证明 mux 写入失败，不得继续占用主线或制作补丁 |

### D. 必须修正的版本/源码来源边界

1. 6.1.79、6.1.112、6.1.116 是用户确认的早期正常实机历史线；其通用 unifreq/linux-6.1.y 源码端点可用于早期正常行为比较，但 6.1.79/112 的 eMMC 二进制与源码 commit 映射仍待补齐。
2. 6.1.174-rk35xx 是首个明确异常样本，其高置信度源码候选为 ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633；不能用通用 stable unifreq/linux-6.1.y 的 6.1.174 端点替代它。
3. 6.12.81-rk35xx 候选为 ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。
4. 6.18.63 B1 的网络栈/GMAC 被有意隔离，B1 启动成功不构成 6.18 GMAC 网络功能成功或失败证据。必须把 B1 实际 source commit 与未来 B2 网络恢复后的源码输入分开登记。
5. 上一份 6.1.79/112/116 对照报告中关于 stable 6.1.174 GMAC cold power-up 路径相同的结论，仅适用于通用 stable 端点；不能用来降低 6.1.174-rk35xx BSP GMAC probe/setup 路径的审查优先级。

### E. B2-0 接下来的实际研究顺序

1. 先建立 GMAC1 的版本—源码—硬件路径账本：正常 6.1.65/79/112/116，异常 6.1.y 实测版本（逐个恢复）、6.1.174-rk35xx、6.12.81-rk35xx、6.18.63。
2. 优先完成 G1：拆解 1500ms DMA reset 等待和 JL2xx1 MDIO workaround，确认它们是否分别影响 GMAC reset/RXC 时序，严禁假设 RTL8211F 必须采用 JL2xx1 写入。
3. 随后完成 G2/G3/G4：逐函数审计 Rockchip GMAC 时钟使能、RGMII GRF 顺序、probe/setup/power handoff，重点绑定 Panther 的 RGMII + clock input 路径。
4. 完成 G5：只做 PHY 型号/生命周期条件的源码和历史日志核对，不对设备做 MDIO 读取或写入。
5. 最后将以上差异映射到 6.18.63；配置复合与查漏补缺作为后续工作，不得抢在源码适用性审查之前。
6. 输出每个差异的已确认存在/未确认构建来源/是否命中 Panther/证据强度/可能修复方式/回退风险，再决定 B2-1。

### F. 当前状态

B2-0 仍在进行，B2-1 不放行。当前主线是 GMAC1/RGMII 从 Linux probe 到 MAC→RGMII TX 的源码与硬件适配审查。以上只调整研究优先级，不授权构建、补丁、刷写、启动网络镜像或任何设备操作。