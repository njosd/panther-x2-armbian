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

## 2026-11-24 B2-0 GMAC 6.18.63 对照结果与优先级纠偏

新增专项报告：
- `docs/reports/2026-11/PANTHER-X2-PROJECT-A-B2-0-GMAC-6.18-CROSSCHECK-20261124.md`

本轮重要修订：
1. **EEE 降级：** 项目 B 已有 6.1.116 EEE enabled-active 与 6.12.81 EEE disabled 的反向对照。标准 ethtool EEE 状态不能直接等同于 RTL8211F PHYCR2 PHY-mode EEE bit5。不得再把“6.12 没有关闭 EEE”作为故障解释，也不重复 EEE 实机测试。
2. **1500ms delay 降级：** 项目 B 唯一主路线图已收口为 JL2XX1/JL2101 快速启动 workaround；Panther 是 RTL8211F 家族，不能移植该等待作为未经证明的修复。
3. **6.18.63 的正向源码回归：** Rockchip GMAC clock enable 回到 bulk enable + 错误检查 + 5ms settle；并补足 PHY clock enable 失败后的 bulk clock rollback。RK3568 RGMII GRF delay value 先写、再 enable/interface 的顺序与正常 6.1.116 一致。
4. **6.18.63 的新增风险：** STMMAC DMA reset 失败后由 error return 改为 warning-and-continue。此改动来自面向 RK3288/RK3328 的临时 workaround，但没有按 compatible 限定；B2 实机日志必须把 `Failed to reset the dma, device will work with reduced throughput` 作为异常/阻断信号，不得把 open/probe 继续等同于 DMA reset 成功。当前不擅自删除该 workaround。
5. **MAC link-up 复核：** 6.18.63 普通 RGMII 1000Mbps speed select 仍选择正确 1000Mbps 字段；新的 Rockchip TX clock callback 对 Panther RK3568 ops 实际调用 clk_mac_speed=125MHz，目标与旧版一致；未发现可解释现有 TX 故障的新差异。
6. **当前主线：** 不重复 EEE、JL2xx1 1500ms、PHYCR2、CSU、CRU 全树、descriptor 等项目 B 已收口审计。继续核对 6.18.63 GMAC1 probe/setup 与 Panther 精确资源解析和新增通用重构的适用性。B2-0 未完成，B2-1 不放行。


### 2026-11-24 补充：6.18.63 GMAC1 资源映射完成一轮

专项报告第 13 节已按 Panther runtime DTS 核对：
- `rockchip,rk3568-gmac` + MMIO `0xfe010000` 命中 `rk3568_ops` / GMAC id=1；
- RGMII 实际 clock list 为 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed；
- RMII clocks 不命中；XPCS/SGMII/QSGMII/PHP-GRF 路径不命中；
- 外置 RTL8211F 不命中 `phy-is-integrated` / integrated `clk_phy` 路径；
- `clock_in_out=input` 与外置 PHY 的 RGMII 时钟输入是板级接口关系，不应与 integrated PHY 的 `clk_phy` handle 混淆；
- 6.18 的 probe/setup/powerup 控制流与 Panther 的外置 PHY + RGMII runtime DTS 条件匹配，尚未发现新静态错配。

本轮仍没有证明实际硬件 clock/GRF 写入和 RGMII 波形。B2-0 继续；B2-1 不放行。


## 2026-11-24 方法论补充：必须审查 GMAC 组件组合效应，不能只做逐组件孤立比较

用户特别指出：GMAC 数据通路像一条由多个环节共同构成的通道，不同环节/条件的组合可能出现“某些组合可通、另一些组合不通”。B2-0 因此增加组合效应审查要求。

### 1. 研究模型：从组件清单转为端到端状态链

不能只问某个组件单独是否正确，还必须检查组件之间的接口契约、初始化先后、状态传递和错误处理是否兼容。当前 Panther TX 方向至少拆成：

1. DTS/资源描述：compatible、reg、clocks、clock-names、resets、power-domains、pinctrl、phy-supply、phy-mode、phy-handle；
2. Rockchip glue probe/setup：资源解析、clock 获取、regulator、reset、GRF 配置；
3. 时钟/电源/复位时序：bulk clocks、PHY clock、5ms settle、regulator enable、runtime PM；
4. STMMAC platform handoff：DMA mask、bus configuration、MAC address、phylink/MDIO 连接；
5. DMA 初始化：software reset、DMA channel、descriptor ring、tail pointer、DMA start；
6. MAC link-up：speed/duplex、TX clock rate、MAC TE/RE；
7. RGMII 边界：TXC/TXD/TX_CTL、delay value/enable、pinctrl/IOMUX；
8. RTL8211F：PHY reset、strap/延时、RGMII interface、link negotiation、LPI/EEE；
9. MDI/对端：帧是否真正从 PHY 发出并被同网段监听器接收。

每个节点的单项实现可能看起来正确，但跨节点组合仍可能不兼容。例如：clock enable 成功但 TX clock rate 设置失败；DMA reset 失败却被 warning-and-continue 吞掉；MAC TE 已开启但 RGMII delay/pinctrl 与 PHY 输出时序不匹配；PHY link 已建立但 MAC/PHY 对 RGMII 时钟方向或 LPI 行为理解不一致。

### 2. 组合效应审查的四个维度

每个跨版本差异必须额外检查：

- **接口/资源组合：** DTS 属性与驱动分支是否匹配；clock name 与实际 clock list 是否一致；外置 PHY 与 integrated-PHY 路径是否混用；RK3566 芯片是否命中 RK3568 ops 中的预期分支。
- **时序组合：** reset、clock enable、settle delay、PHY power-up、MDIO attach、DMA reset、MAC TE enable 的先后关系是否满足硬件依赖；不能只比较 delay 数值。
- **状态/错误组合：** 某一步失败后是否继续执行；后续步骤是否假定前一步成功；warning-and-continue、ignored return、deferred probe、runtime PM 状态是否可能形成“表面成功、数据不通”。
- **版本/补丁组合：** 组件 A 的新接口是否依赖组件 B 的配套改动；单独 backport/revert 是否会破坏调用约定、结构字段、回调时序或资源释放；不能把不同版本的局部代码随意拼接。

### 3. 建立组合矩阵，而不是无目的穷举

对每个关键阶段建立“版本 × 组件 × 条件 × 结果”矩阵：
- 版本列：正常 6.1.65、正常 6.1.79/6.1.112/6.1.116、已确认异常的 6.1.y 具体版本、6.1.174-rk35xx、6.12.81-rk35xx、目标 6.18.63；
- 组件列：DTS/DTB、Rockchip glue、STMMAC core、DWMAC4、PHY driver、pinctrl/CRU/regulator；
- 条件列：cold boot、PHY reset、link-up、open/reopen、runtime suspend/resume、1000Mbps RGMII、DMA reset error 等，只登记有证据或源码可达的条件；
- 结果列：probe、clock、PHY attach、DMA reset、MAC TE、TX descriptor、MAC counter、外部抓包等边界结果；
- 证据列：精确 source commit、二进制来源、实际命中分支、历史实机结果、置信度。

优先找“单组件没有明显错误，但两个或多个组件组合后出现行为差异”的交互项。先根据调用链、条件分支、时序和错误传播提出少量有因果依据的组合，再评估是否值得进行单变量替换。禁止把所有组件任意排列组合，也禁止仅凭相关性认定根因。

### 4. 故障定位要用边界证据缩小组合范围

已知项目 B 证据显示软件 TX 请求、descriptor 回收和 MAC MMC TX 计数均有活动，但外部监听器未收到对应帧；因此当前最重要的未闭合边界是 MAC 计数之后到外部 RGMII/PHY/MDI 发送之间。

这并不证明故障一定在 PHY：如果 MAC 内部计数点位于真正 TX 输出之前，仍可能是 MAC TE/DMA 状态、时钟、GRF 或 RGMII 输出问题。后续源码研究应逐项确认各计数器的统计位置和代码路径，不能将 MMC TX 计数等同于物理出线。

### 5. 组合候选的入选规则

一个组合候选进入下一轮重点审查，至少满足：
1. 组件间存在明确调用/资源/时序/状态依赖；
2. 正常与异常版本之间至少一个参与组件或接口契约确有差异；
3. 该差异在 Panther RGMII + 外置 RTL8211F + RK3566 条件下实际可达；
4. 能解释现有故障边界，而不与已有实机证据冲突；
5. 有可独立观察或未来可单变量替换的验证方式；
6. 能说明替换时的依赖闭包与回退方案。

### 6. 对当前 B2-0 的直接执行影响

- 先前逐组件源码比较继续保留，但不能把“每项都与 6.1.116 一致”推导成“6.18 整条链必然正常”。
- 下一步优先绘制 6.18.63 Panther GMAC1 从 probe → clock/power/reset → STMMAC handoff → DMA reset → link-up/TX clock → MAC TE 的顺序图，并与 6.1.116 正常路径、首个异常 6.1.y 的精确构建路径逐段比较。
- 特别审查错误返回被忽略/降级后，后续步骤是否仍会运行；以及一个组件的补救提交是否依赖另一个组件或 PHY 生命周期改动。
- 组合审查必须回用项目 B 已有实机结果，不重复设备测试；新证据出现前不做构建、补丁、刷写或网络启动。

**状态不变：B2-0 继续；B2-1 不放行。** 本节更新研究方法与检查表，不代表已证明某个组合就是根因。


## 2026-11-24 组合效应核查：Rockchip pinctrl 错误传播 × GMAC1 RGMII pin groups

本轮不是重做 P4，而是将 P4 已有源码差异放回 GMAC1 的真实 pinctrl 调用链，并新增核对 6.18.63 是否仍携带同一错误条件。

### 1. 精确源码结果

对照版本：
- 正常 6.1.65 候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`
- 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 异常 6.1.174-rk35xx 高置信度候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 异常 6.12.81-rk35xx：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 目标 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`

`drivers/pinctrl/pinctrl-rockchip.c:rockchip_pmx_set()`：
- 6.1.65、6.1.116：`if (ret)`，首 pin 写入失败会返回 errno；
- 6.1.174-rk35xx、6.12.81-rk35xx：`if (ret && cnt)`，当 group 第一个 pin 失败（cnt=0）时，跳过错误返回并最终返回 0；循环已 break，同组后续 pin 不会执行；
- 6.18.63：恢复为 `if (ret)`，首 pin 失败会向 pinctrl core 正常传播错误。

因此，6.18.63 在这项错误传播语义上与两条正常 6.1 通用线一致，而不是继承两个异常 RK35xx BSP 候选的条件。

### 2. 与 Panther GMAC1 pin group 的交互

Panther X2 runtime DTS 中 GMAC1 引用的 M0 pin groups 包含：
- `gmac1m0_tx_bus2`
- `gmac1m0_rgmii_clk`
- `gmac1m0_rgmii_bus`
- MDIO/MDC 相关组

既有 P4 审计已核实 TX 相关组的 pin 顺序：首 pin 写入失败时，异常 `rockchip_pmx_set()` 会跳过同组后续 pin。其潜在影响包括 TXD、TXEN、TXCLK、TXD2/TXD3 等信号未完整切换到 GMAC 功能。

这构成一个明确的跨组件组合：
`GMAC DTS pinctrl state` → `Rockchip pinctrl group iteration` → `rockchip_set_mux()/regmap` → `ret && cnt` 错误传播 → `RGMII TX pin mux 是否完整`。

### 3. 为什么仍不能认定为根因

已有 P4 复核显示：
- Panther 使用 RK3566/RK3568 对应的普通 GRF syscon/regmap 路径；
- GMAC mux=3 是合法 4-bit IOMUX；
- 未设置会触发 Trust Firmware group-info 校验的 `rockchip,group-info`；
- 未发现 Panther 正常 MMIO regmap 写入路径会自然产生 errno 的具体机制；
- 没有历史故障启动日志证明某个 GMAC pin group 首 pin 的 `rockchip_set_mux()` 曾返回错误。

所以：
- **源码错误条件：已确认。**
- **Panther pin group 的潜在影响：已确认可达。**
- **故障启动时是否触发：未验证，且当前缺少现实触发证据。**
- **是否为 6.1.y 故障族共同根因：不能认定。**

该结果不改变 P4 的“极低/理论候选”评级，不重开 P4 实机调查，也不提出补丁。

### 4. 组合层面的实际意义

该差异说明，单独比较 GMAC driver 可能漏掉真正影响 GMAC 的 pinctrl provider 错误传播。6.1.174/6.12 的 GMAC glue 可以正确请求 pinctrl state，但 provider 在特定首 pin 写入失败条件下可能错误报告成功；上层因此可能继续 probe/link-up，而某些 RGMII TX pins 实际未完成 mux。

反过来，6.18.63 已恢复错误传播语义，未来 B2 即使恢复相同 Panther DTS，也不会继承这一特定“首 pin 失败被吞”组合条件。它仍需要确认 pinctrl state 选择是否成功，但不需要为此重复修改 pinctrl。

### 5. 与其他候选组合的优先级关系

| 组合 | 版本证据 | 触发条件 | 当前评价 |
|---|---|---|---|
| pinctrl 首 pin error × GMAC TX group 顺序 | 正常 6.1 与异常 RK35xx 源码存在差异；6.18 已恢复正常条件 | 首 pin mux/regmap 操作必须真实返回 errno | 有明确跨组件机制，但缺现场触发证据；保留低优先级 |
| GMAC clock enable error × ignored return × 100–200µs settle | 6.12 明确存在，6.18 已恢复 bulk/error-check/5ms 路径 | 必需 clock enable 失败或稳定时间不足 | 源码组合成立；是否实际失败/不足未验证 |
| DMA reset failure × warning-and-continue × MAC TE | 6.18 新增 warning-and-continue | stmmac_reset() 必须实际失败 | 6.18 新风险；未来 B2 必须将该 warning 视为失败，不可继续验收 |
| PHY regulator/reset × RGMII delay × link-up | 跨版本存在顺序/实现差异 | PHY 上电/复位时序与 MAC 配置需发生冲突 | 需进一步按 cold boot 路径核对；不重开已收口的单项 PHY reset/RGMII 数值审计 |

### 6. 下一轮研究

优先对 6.18.63 做完整的“错误状态传播链”审计，而不是只看函数是否返回错误：
1. pinctrl state apply 的错误是否传递至 GMAC probe；6.18 已确认 provider 本身在首 pin error 时返回错误；
2. Rockchip GMAC clock bulk enable / PHY clock enable / rollback 是否正确传播至 probe/open；
3. STMMAC DMA reset 的 warning-and-continue 是否会让后续 DMA/MAC setup 继续；
4. TX clock `clk_set_rate(125MHz)` 失败是否会继续启用 MAC；
5. 对每个“失败后仍继续”的位置，确认后续步骤的前置条件是否被满足，避免形成表面 link-up、实际 TX 不出线。

此处只审计源码控制流和已有日志，不读取 MMIO/MDIO，不重启接口、不发包、不构建、不修改设备。

**B2-0 继续；B2-1 不放行。**


## 2026-11-24 B2-0 组合时序研究增补

专项报告 `PANTHER-X2-PROJECT-A-B2-0-GMAC-6.18-CROSSCHECK-20261124.md` 第 14 节新增 6.1.116、6.12.81、6.18.63 跨组件 power-up 顺序比较。

新增发现与执行要求：
1. 三版 Panther 主调用顺序均为 GMAC clocks → RGMII GRF → external PHY regulator → runtime PM → STMMAC probe；没有发现 6.18 把 PHY 上电与 MAC clock/GRF 的先后颠倒。
2. 6.12.81 的候选风险必须作为组合评估：逐项 clock enable 不检查返回值 + 100–200µs settle + 后续仍继续 GRF/PHY supply/STMMAC probe。不得只把 5ms 与 100µs 的数字孤立比较。
3. 6.18.63 恢复 bulk clock enable 错误传播与 5ms settle；并修复 PHY regulator enable 错误传播，避免 supply enable 失败后仍继续 STMMAC probe。
4. 6.18.63 新增 RK3568 PHY interface select 写入（GMAC1_CON1 bits 6:4），位域不与 RGMII mode bit7、delay enable bits1:0 重叠；但 helper 返回的 RGMII 编码值仍待对照 RK3568 硬件定义，暂不作正确性定论。
5. 三版共同保留 RK3568 RGMII delay/mode regmap_write 返回值不检查的可观察性缺口；没有现场 regmap failure 证据，暂不定为根因。
6. 下一轮先闭合 interface-select enum/寄存器编码与 clock/resource mapping 的组合语义，再核对 STMMAC probe 前后 DMA reset、MAC open/link-up 的依赖状态。所有已审计项目 B 证据继续复用，不重做实机测试。

状态仍为 B2-0；B2-1 不放行。

### 2026-11-24 组合时序与 clock 错误传播补充

专项报告 `PANTHER-X2-PROJECT-A-B2-0-GMAC-6.18-CROSSCHECK-20261124.md` 第 14–16 节进一步闭合了跨组件初始化顺序、RK3568 interface-select 编码及 clock 获取/使能错误传播。

关键结论：
- 三版主顺序均为 GMAC clocks → RGMII GRF → external PHY supply → runtime PM → STMMAC probe；未发现 6.18 把供电与时钟/接口配置顺序颠倒。
- 6.12.81 的重要组合风险不仅是逐项 clk_prepare_enable() 不检查返回值，还包括逐项 devm_clk_get() 失败仅打印错误、不阻止 rk_gmac_clk_init() 返回成功；后续跳过 ERR_PTR clocks、仍设置 clk_enabled=true 并继续 PHY supply/probe。
- 6.1.116 与 6.18.63 使用 bulk clock 获取并检查获取/使能错误；6.18 另补 PHY clock enable 失败后的 bulk rollback。
- 6.18.63 新增 RK3568 interface-select 的 RGMII 编码链已在 Linux STMMAC enum 与 RK3568 mask 间静态闭合为字段值 001；与 mode/delay bits 不重叠。硬件 TRM/readback 仍未验证。
- 6.18.63 PHY regulator enable 错误会阻止继续 probe；6.1/6.12 旧 helper 曾记录错误但仍返回 0。此项是 6.18 的正向错误传播改进。
- 当前最值得保留的 6.12 候选是 clock 获取/使能失败被吞后继续初始化的跨函数状态组合；仍无证据证明 Panther 实际触发。

下一轮优先查找历史 6.12 启动日志中 clock get/enable 相关错误，核实是否存在对应证据；再继续对照首次异常 6.1.y 构建的实际 source/patch inputs。不得重新跑已经完成的实机测试。

状态仍为 B2-0；B2-1 不放行。
### 2026-11-24 重要修订：DMA reset 前 1500ms wait 必须纳入正常基线差异

专项报告第 17 节纠正了此前对 JL2XX1 1500ms workaround 的过度降级：
- 6.1.65（原版实机网络全通）和 6.1.116（实机网络全通）的 STMMAC `stmmac_init_dma_engine()` 都在 DMA software reset 前无条件执行 `msleep(1500)`。
- 该等待由标题指向 JL2XX1 的 commit 引入，但代码没有 PHY ID 条件，因此 Panther 在两个正常版本上也实际经过这段等待。
- 6.12.81 和 6.18.63 均移除了这段等待；6.12 reset failure 会 abort，6.18 则 warning-and-continue。
- 不重开四次 MDIO 写入的 P1 寄存器猜测；但必须保留 1500ms 等待本身作为正常基线共有的真实时序差异。
- 新候选是“PHY supply/clock 已开启 → STMMAC probe → 1500ms wait 有无 → DMA reset → reset error handling”的组合。当前尚未证明该等待对 Panther 必需，也未证明 6.12 reset 失败。

后续 B2-0 应追踪移除等待的具体提交、DMA reset poll 语义与时序补偿是否被其他改动替代；不能因提交标题指向 JL2XX1 而忽略其无条件通用执行效果，也不能直接移植 1500ms 作为修复。

状态仍为 B2-0；B2-1 不放行。
### 2026-11-24 补充：6.1.65 原版实机黄金线与源码端点映射

新增专项报告第 18 节已将 2026-11-24 原版 Armbian 6.1.65 实机网络全通证据映射至源码候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`。

- 6.1.65 `dwmac-rk.c` 与 6.1.79/112/116 blob 完全相同；Panther DTS blob 完全相同；pinctrl 首 pin 错误处理仍是 `if (ret)`。
- 6.1.65 STMMAC DMA init 在 reset 前无条件等待 1500ms，reset failure 则 error + abort。
- 6.1.65 RTL8211F RGMII delay / PHYCR1 初始化路径与 6.1.116 主体高度一致；LED 扩展不改变普通 RGMII delay 分支。
- 6.1.65 实机网络全通是直接证据；4428... 是高置信度源码候选，不是原始 Image 的逐字节构建来源证明。

版本矩阵必须以 6.1.65 与 6.1.116 双正常实机基线为两端，不得只以 6.1.116 代表正常历史。
## 2026-11-24 B2-0 总账重整：固定研究方向、顺序与结项门

本节为 B2-0 唯一研究总账。此前专项报告新增的时序、DMA reset、pinctrl、非网络组件等发现全部归入下列固定方向；新线索只能登记到所属方向，不得自动切换当前主线或另起并行排查。B2-0 必须按顺序逐项结项。

### 固定的九个研究方向

| 顺序 | 方向 | 范围 | 当前状态 |
|---|---|---|---|
| 1 | 版本基线与回归边界 | 6.1.65/79/112/116 正常线；后续 6.1.y 具体故障版本、6.1.174、6.12.81、6.18.63；镜像/DTB/config/source commit 绑定 | 未结项；当前主线 |
| 2 | Rockchip GMAC glue 与 CCF/CRU/时钟/复位/电源 | probe/setup、clock 获取/使能、settle、GRF、PHY supply、runtime PM、TX clock callback | 已有多轮静态审计，尚未按结项条件封账 |
| 3 | STMMAC core 与初始化交接 | platform handoff、PHY attach、DMA reset、reset error handling、DMA init、open/link-up 生命周期 | 已有多轮静态审计，尚未按结项条件封账 |
| 4 | DWMAC4 DMA 与 TX 数据通路 | DMA mask、descriptor OWN、ring/tail、DMA address/buffer、barrier、AXI、DMA channel、MMC TX 统计位置 | 项目 B 部分审计已完成；需汇总证据并闭合 TX 边界，不重复实机实验 |
| 5 | MDIO、PHYLIB/PHYLINK 与 RTL8211F | MDIO 注册、PHY attach/reset、RGMII delay、PHYCR、EEE/LPI、link 与生命周期 | 项目 B 单项审计大部已完成；只复核 6.18 命中关系 |
| 6 | pinctrl/GPIO/regulator/reset provider | GMAC pin groups、首 pin 错误传播、供电/复位资源、deferred probe | P4 已结项；只做与 6.18 组合关系的收口，不重开实机调查 |
| 7 | 非网络子系统间接影响 TX | DMA/cache coherency、IOMMU、AXI/interconnect/QoS、GIC/IRQ、内存/CMA、runtime PM、firmware/SCMI | 已建立方向和候选矩阵；尚未逐项审计结项 |
| 8 | Linux 网络核心与协议栈 | netdev、TX queue、ARP/IPv4/ICMP、NAPI 和 6.18 API/生命周期变化 | 待审 |
| 9 | 配置、DTS/DTB 与组件组合闭环 | 最终 Kconfig、DTS 资源、模块依赖、built-in/module、组件接口契约和最小依赖闭包 | 待审；只复合查漏，不重做项目 B 配置审计 |

### 每个方向统一结项标准

每个方向必须形成一份可复核的结项记录，至少包含：
1. 正常版本与异常版本的精确源码差异及引入/修改提交；
2. Panther X2 的 compatible、DTS 资源、硬件条件是否实际命中该路径；
3. 与相邻组件的调用顺序、资源契约、时序、状态和错误传播组合；
4. 与项目 B 已有实机证据及 TX 物理边界是否相符；
5. 结论分级：已排除、低优先级保留、高价值候选、需后续实机验证；
6. 组件决策：保留 6.18、使用同分支后续修复、单组件回退/最小修正或暂不改动；
7. 明确列出未闭合事项、证据缺口和结项理由。

“已经读过源码”或“某函数看起来正常”不构成结项。若存在未解释的高价值差异，该方向不得标记完成。

### 研究纪律与顺序

- 当前主线固定为方向 1。方向 1 结项后再依次推进方向 2、3、4……方向 9；此前已经做过的方向 2–6 工作作为已有证据，不丢弃、不重做，届时按结项标准补齐。
- 新发现若属于后续方向，先登记为待办，不中断当前方向；若发现会推翻当前结论的直接证据，可记录为阻断项并说明理由，经用户确认后才调整顺序。
- 一个方向内可以有多个子项，但必须在同一方向账本内逐项勾销；不得把同一问题换名字反复开启。
- 项目 B 的 P1–P4 结论作为已完成输入复用；P5 的物理 TX 边界证据只复用已有材料，不重做硬件实验。
- 不构建、不刷写、不启动网络镜像、不改实机；不读取 MMIO/MDIO，不做寄存器写入。进入后续验证阶段必须另行获得明确授权。

**当前游标：方向 1（版本基线与回归边界）。B2-0 未完成；B2-1 不放行。**
## 2026-11-24 方向 1 进展记录：版本身份与正常/异常边界（未结项）

本节只更新固定总账方向 1，不提前进入方向 2。依据仓库已有证据和用户本轮明确历史信息，当前矩阵修订如下。

### 1.1 已确认的正常基线

| 版本 | 正常性证据 | 源码/资产身份 | 当前判断 |
|---|---|---|---|
| 6.1.65 原版 Armbian | 2026-11-24 Panther X2 实机启动，驱动绑定、RTL8211F、1000Mbps Full Duplex、DHCP、hEX 网关 ICMP、外部 IPv4 ICMP、DNS 均通过 | 原始 IMG SHA256 `0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`；源码候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`，尚非 Image 二进制构建证明 | **实机正常，强黄金基线** |
| 6.1.79 | 用户明确确认：本机 eMMC 备份中存在该版本，意味着实机运行过且没有网络故障 | `unifreq/linux-6.1.y@e77fb4335d38f79b66ab5e1e3c627f54140fcb2a` 是源码版本候选；备份内 Image/DTB/config/modules 哈希及二进制映射待恢复 | **用户确认的正常历史基线；资产闭环未完成** |
| 6.1.112 | 用户明确确认：本机 eMMC 备份中存在该版本，意味着实机运行过且没有网络故障 | `unifreq/linux-6.1.y@a29ec4768872f856a3a17326334d53482d25fcfa` 是源码版本候选；备份内 Image/DTB/config/modules 哈希及二进制映射待恢复 | **用户确认的正常历史基线；资产闭环未完成** |
| 6.1.116 | 已有实机正常运行记录，千兆全双工、DHCP、网关及 iMac 通信正常 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`；boot/DTB/modules 归档 SHA256 已记录 | **实机正常，强黄金基线** |

6.1.79/112 的历史正常性以用户明确说明为依据，不要求重新实机测试；后续只需恢复已有备份资产、核对版本身份和哈希，不重复网络验收。

### 1.2 已确认的异常/待核实版本

| 版本/系列 | 故障证据 | 源码/资产身份 | 当前判断 |
|---|---|---|---|
| 6.1.y（6.1.116 之后的多个升级版本） | 用户明确回忆曾升级多个 6.1.y 版本，网络均出现相同故障；但具体小版本号尚未从历史材料中恢复。用户曾纠正把版本误记为 6.1.119，故不得把 6.1.119 写成确定版本 | 每个实际版本的 Image、release、DTB、源码分支/commit/patchset 均待恢复 | **存在该异常族的用户历史证词；版本清单未闭环** |
| 6.1.174-rk35xx-ophub | 仓库有明确历史实机异常记录，是当前第一个可绑定具体版本与故障源码候选的样本 | 官方 `6.1.174.tar.gz` SHA256 `49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a`；Actions run #296 关联；源码候选 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，高置信度但非逐字节构建证明 | **第一个当前证据绑定较完整的异常样本；不能称为历史上首次故障** |
| 6.12.81-rk35xx-ophub | 实机 TX 发送异常证据完整：本机 TX 可见，第三方同网段监听器未收到帧；已确认 TX 故障边界 | 源码候选 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；官方资产 SHA256 已记录 | **明确异常样本** |
| 历史 Ophub 6.18.63 | 用户历史中存在升级到 6.18.63 后回退的阶段；`boot-before-6.1.116.tar.gz` 内容确认属于 6.18.63 文件集合。具体当时网络故障的实机测试细节与完整安装套件身份仍须与 B1 区分 | 历史 Ophub 6.18.63 套件身份需按旧报告继续核实；项目 A B1 的自建 `aee4e352...` 是另一份独立内核输入，且 B1 的 CONFIG_NET/GMAC 被关闭 | **历史候选异常节点；不可与 B1 的 6.18.63 启动成功/网络隔离镜像混为一谈** |

### 1.3 版本回归窗口的当前结论

1. 目前可确认的正常历史区间至少包括 6.1.65、6.1.79、6.1.112、6.1.116；其中 6.1.65 与 6.1.116 有直接实机网络验收记录，6.1.79/112 的正常性来自用户对实际 eMMC 备份历史的明确确认。
2. 6.1.79、6.1.112、6.1.116 的 `dwmac-rk.c`、`stmmac_mdio.c`、Panther DTS 文件 blob 完全相同；`stmmac_xmit()`、`stmmac_init_dma_engine()`、`stmmac_mac_link_up()`、`stmmac_tx_clean()` 关键函数体相同；Rockchip GMAC `gmac_clk_enable()`、`rk_gmac_powerup()`、`rk_fix_speed()`、`rk_gmac_clk_init()` 相同。正常历史线内部这些 GMAC 主干没有显示回归变化。
3. 6.1.79→6.1.112 的 pinctrl rollback 修正不改变正常 pinmux 配置路径或首 pin 错误返回语义；RTL8211F `config_init` 的 reset 语义变化发生在仍然正常的历史版本之间，不能单独认定为故障原因。
4. 6.1.174-rk35xx 是首个当前有明确历史实机异常证据且可与官方包/Actions run/高置信度源码候选关联的样本；它不等于用户历史上第一次遇到网络故障的版本。
5. 6.1.174 通用 stable 源码 `unifreq/linux-6.1.y@3f06ed3...` 与实际 RK35xx 故障候选 `ophub/linux-6.1.y-rockchip@c2f148d...` 不能互相替代。后续所有回归差异必须基于实际构建分支与补丁集。
6. B1 自建 6.18.63 的网络被有意关闭，B1 启动成功不能作为 6.18 网络正常或异常证据；历史 Ophub 6.18.63 与 B1 6.18.63 必须作为不同软件套件分别记录。

### 1.4 方向 1 尚未结项的必要缺口

- [ ] 从现有 eMMC/Dropbox 备份恢复 6.1.79、6.1.112 的实际 Image、DTB、config、modules 文件身份与 SHA256；不要求重测网络。
- [ ] 从用户历史记录、备份目录或系统包记录恢复 6.1.116 之后出现同一故障的每个 6.1.y 具体小版本号；当前不可猜测或以 6.1.119 代替。
- [ ] 为每个已恢复的异常 6.1.y 版本确定实际 kernel release、发布包/镜像身份、源码仓库、commit、构建 workflow 和额外 patchset；区分通用 stable 与 RK35xx BSP。
- [ ] 对历史 Ophub 6.18.63 版本恢复实际 Image/DTB/config/modules 身份和网络失败记录；与 B1 自建 6.18.63 分离。
- [ ] 明确每个版本的“网络故障”证据级别：仅用户历史回忆、实机日志、链路/DHCP 结果、双端抓包，分别标注，不混为同等证据。

### 1.5 当前方向结项判定

**方向 1：进行中，尚未结项。** 正常线已形成可用源码对照；异常线已建立 6.1.174-rk35xx、6.12.81-rk35xx 两个绑定样本，但 6.1.116 后实际失败的 6.1.y 版本清单及 6.1.79/112 历史二进制资产仍未闭环。不能据现有材料宣称已找到首次回归提交，也不能进入方向 2 作为正式主线。

当前只继续方向 1 的上述缺口。不得为了推进而重复已经完成的 GMAC 源码审计、实机网络测试或 B1 验证。
## 2026-11-24 方向 1 继续核对：历史版本身份、故障证据等级与回归窗口修订

本节进一步回溯 `PANTHER-X2-PROJECT-A-B2-0-EARLY-GOOD-6.1Y-SOURCE-COMPARISON-20261124.md`、四版本资产矩阵、6.1.116→6.1.174 回归筛查、原始 6.1.65 镜像审计、DHCP/TX 故障报告及既有用户历史确认。目的是修正版本身份和证据等级，不开启新的组件研究方向。

### 1.6 方向 1 的版本矩阵修订（以本节为当前汇总口径）

| 版本/版本族 | 当前状态 | 证据级别和限制 |
|---|---|---|
| 6.1.65-ophub | 正常黄金基线 G65 | 用户明确确认 Panther X2 实机测试网络完全正常；项目记录包含 TF rootfs + eMMC `/boot` 混合启动场景及 1000M/Full、DHCP、网关/外部 IPv4、DNS 验收。原始镜像静态审计报告中的“实机启动仍未验证”是该静态审计报告当时的范围状态，不得覆盖后来已完成的独立实机网络验证。原始 IMG SHA256 `0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`。实际构建源码 commit 尚未闭环。 |
| 6.1.79-ophub | 早期正常历史基线 G79 | 用户确认本机 eMMC 备份存在，实际在本机运行过且网络正常；源码候选 `unifreq/linux-6.1.y@e77fb4335d38f79b66ab5e1e3c627f54140fcb2a`。实际 Image/DTB/config/modules 哈希和源码到二进制映射未闭环；不要求重测网络。 |
| 6.1.112-ophub | 早期正常历史基线 G112 | 用户确认本机 eMMC 备份存在，实际在本机运行过且网络正常；源码候选 `unifreq/linux-6.1.y@a29ec4768872f856a3a17326334d53482d25fcfa`。实际 Image/DTB/config/modules 哈希和源码到二进制映射未闭环；不要求重测网络。 |
| 6.1.116-ophub | 正常黄金基线 G116 | 已有实机运行、RTL8211F、1000M Full、DHCP、LAN/网关连通证据；源码 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，内核资产备份 SHA256 已记录。 |
| 6.1.117–6.1.173 之间的其他 6.1.y 版本 | 用户确认后续曾升级多个小版本，出现相同网络故障；具体版本号未恢复 | 不能推测每个版本都失败，也不能把源码提交时间当作实机测试时间。逐个版本的准确 release 字符串和测试证据待恢复。 |
| 6.1.174-rk35xx-ophub | 已确认的异常样本 R174 | 历史记录显示用户测试该版本后回退 6.1.116，6.1.174 网络异常、回退后 IPv4/网关恢复。它是一个已确认失败样本，但**不能称为历史首次故障版本**，因为用户确认在 6.1.y 后续升级族中还有多个小版本，且其准确版本号尚未恢复。 |
| 6.12.81-rk35xx-ophub | 明确异常样本 R612 | 有完整双端测试：板卡侧可见合规 TX 报文，第三方有线同网段监听器收不到，阳性对照有效；RX 方向可收。属于强 TX 单向异常证据。源码端点 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`。 |
| 历史 Ophub 6.18.63-ophub | 历史升级失败/网络未恢复节点 T618-history | 历史对话记录曾运行 `6.18.63-ophub`，eth0 仅 IPv6、无 IPv4/默认路由；此前另有升级写入 `/boot/vmlinuz-6.18.63-ophub` 时空间不足记录。现有证据足以记录为网络未正常工作的历史节点，但未形成与 6.12.81 同等级的第三方 TX 物理边界证据。必须与 Project A 自建 B1 的 6.18.63（`CONFIG_NET=n`、GMAC disabled、已实机启动）严格区分。 |
| 6.1.192-ophub | 不列入实机正常/异常矩阵 | `/etc/ophub-release` 曾记录 `KERNEL_VERSION=6.1.192`，但这只是 rootfs release metadata，不能证明当时运行该版本。不得据此推断 6.1.192 实机启动或网络结果。 |

### 1.7 关于 6.1.y 首次故障版本的结论

当前能够确认的是：正常历史线延伸至 6.1.116；用户在后续多个 6.1.y 升级版本中遇到相同故障；6.1.174-rk35xx 是已知的一个异常实机样本。当前资料**不足以把 6.1.174 定为首次故障版本**，也不足以准确列出 6.1.117–6.1.173 中哪些版本被实机运行过。

既有 `PANTHER-X2-KERNEL-6.1.116-TO-6.1.174-REGRESSION-WINDOW-STMMAC-DIFF-20261119.md` 是 6.1.116 stable 源码到 stable 6.1.174 的静态提交筛查，不是逐版本实机测试矩阵。它已指出 6.1.117–6.1.173 无逐版本实机结果，且 6.1.124、6.1.169 等仅为提交筛查线索。不能将提交引入版本当作用户实际测试版本。

另一个必须保持的来源边界：`unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7` 是 stable 6.1.174 源码端点；`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` 是后期 RK35xx BSP 源码候选。后者提交日期晚于 stable 6.1.174 tag，尚无足够 build log/patchset 证明它就是历史现场安装二进制的完整构建输入。两者不可混用，也不可用 stable 端点替代 RK35xx 故障样本的构建来源。

### 1.8 早期正常线的源码对照可结项范围

以下子项可标记为“源码静态对照已完成”，不再重复：
- 6.1.79/112/116 三个正常源码端点的 `dwmac-rk.c`、`stmmac_mdio.c`、Panther X2 DTS 文件完全相同；
- 三版本 `stmmac_xmit()`、`stmmac_init_dma_engine()`、`stmmac_mac_link_up()`、`stmmac_tx_clean()` 函数体完全相同；
- 三版本 Rockchip GMAC `gmac_clk_enable()`、`rk_gmac_powerup()`、`rk_fix_speed()`、`rk_gmac_clk_init()` 完全相同；
- 6.1.79→6.1.112 pinctrl 变化仅涉及跨 bank rollback 时重新计算 bank，正常 mux 配置路径及首 pin 错误返回语义不变；
- RTL8211F `config_init` reset 语义在 6.1.79 与 6.1.112/116 之间变化，但两侧都是用户确认的正常历史版本，不能单独解释后续故障；6.1.116 与 stable 6.1.174 的 `realtek.c` blob 相同。

这些结果只对照了正常历史线内部，不代表已完成正常线到真实异常 BSP 二进制的全量源码差分。

### 1.9 当前只剩的方向 1 工作项

- [ ] 继续从已有本机备份清单/历史记录恢复 6.1.116 之后用户实际运行过、且网络故障的每个 6.1.y 小版本号。不要猜测，不以 6.1.119 代替；若原始记录确实没有具体版本，明确标为“历史版本号不可恢复”，不要求用户重复测试。
- [ ] 对每个能恢复的异常版本绑定其真实 release 字符串、发行包名、Image/DTB/config/modules 指纹、实际源码仓库/commit/patchset 和构建来源；优先查 6.1.174-rk35xx 的 build workflow inputs/patchset，解决 stable `3f06ed3` 与 BSP `c2f148d` 的来源差异。
- [ ] 对 G79/G112 仅补齐已有 eMMC 备份资产的身份/哈希映射；不重做网络验收，也不因本轮没有可访问原始二进制而反复要求用户采集。
- [ ] 确认历史 T618 `6.18.63-ophub` 的确切包/构建来源与网络现象证据；不能引用 B1 自建 6.18.63 的启动结果替代。
- [ ] 形成最终版本关系图：G65/G79/G112/G116 正常历史 → 后续 6.1.y 多版本异常族（具体成员能恢复多少列多少）→ 6.12.81 异常 → 历史 Ophub 6.18.63 网络未恢复；将每条连线标注为实际测试、用户历史确认或源码候选。

**方向 1 状态：未结项。** 正常历史线的角色及内部源码稳定性已基本查清；6.1.174 只能定为已知异常样本，不能定为首次回归点。当前不进入方向 2，不重复项目 B 已完成的 GMAC/PHY 子项，不构建、不刷写、不启动网络镜像、不修改设备。
## 2026-11-24 方向 1 补充核查：早期备份时间、误导性版本元数据与源码筛查边界

### 1.10 6.1.79 / 6.1.112 历史备份的新增可核实信息

回查 `PANTHER-X2-ORIGINAL-SOFTWARE-IMAGE-PROVENANCE-20261120.md` 后，找回旧对话记录的目录时间：

| 版本 | 历史备份目录日期 | 解释 |
|---|---|---|
| 6.1.65 | 2024-02-27 | 原始系统版本备份节点 |
| 6.1.79 | 2024-10-18 | 用户确认曾在本机实际运行且网络正常的历史节点 |
| 6.1.112 | 2024-11-11 | 用户确认曾在本机实际运行且网络正常的历史节点 |

这进一步支持 6.1.79/112 属于真实设备历史，不是从源码版本列表推测出来的版本。但仓库当前只有目录时间与用户确认记录，没有恢复到 6.1.79/112 的 Image、DTB、config、modules 原始文件及各自哈希；因此版本身份的实机历史可信度高，二进制构建来源仍未闭环。Dropbox 按版本号和 Panther X2 关键词的检索本轮未返回对应文件，不能把“搜索无结果”解释为文件不存在，也不能宣称已经恢复备份资产。

### 1.11 6.1.192 元数据陷阱已进一步排除

仓库实机证据 `evidence/boot/2026-11-16-panther-x2-emmc-boot-files-audit.txt` 和 `evidence/network/panther-eth-baseline-redacted.txt` 显示：
- 当时运行内核为 `6.1.116-ophub`；
- `/boot/Image` 和 `/boot/uInitrd` 均指向 `6.1.116-ophub` 文件；
- `6.1.192-1-ophub` 出现在已安装软件包数据库和 DTB 目录名中，属于升级遗留/版本不一致；
- 没有证据表明 6.1.192 曾作为本机运行内核启动。

因此，6.1.192 不得作为 6.1.116 之后的实机测试节点，也不得列入网络正常或异常矩阵。版本身份必须以 `uname`/`/proc/version`、实际启动的 Image 与运行时 DTB 交叉确定，不能仅凭 package metadata 或文件目录名。

### 1.12 6.1.117–6.1.173 源码筛查结果与实机版本必须分层

既有 6.1.116→6.1.174 stable 源码筛查报告已识别 6.1.117、6.1.124、6.1.142、6.1.158、6.1.164、6.1.167、6.1.169 等提交簇。这些是源码变更的版本标签，不代表用户逐个安装或实机运行过这些版本。

目前可保留的源码筛查结论：
- 6.1.174 最终版本提交自身修改 GRO/SKB shared-frag 元数据传播及 Makefile，不直接修改 STMMAC、Rockchip GMAC 或 PHY；因此不能把最后一个 6.1.174 版本 bump 提交当作已知 TX 根因。
- 6.1.117 的 WoL IRQ 状态初始化与 Panther 当前未使用 WoL 的证据不匹配。
- 6.1.124 是 STMMAC DT/MDIO 解析结构性重构；既有专项报告已逐项核对 Panther 的 mdio node/phy attach 行为，现有异常版本仍能识别 RTL8211F 并建立 1Gbps link，尚无证据把该重构与物理 TX 不出线建立因果关系。
- 6.1.142 的 alias fallback 对 Panther 已定义 `ethernet0 = &gmac1` 的情形通常命中显式 alias；没有发现能解释 TX 物理边界的证据。
- 6.1.158 powerdown 时 clock selection 顺序变化不等于当前 powerup 路径变化。
- 6.1.164/167 的 MSI、LPI IRQ 等分支与 Panther RK3566 平台 GMAC 普通中断路径不匹配。
- 6.1.169 的 chain-mode jumbo-frame DMA mapping 修复不命中 Panther 已知 `chain_mode=0` ring-mode 普通 DHCP 小帧路径。

以上结论只说明已筛到的这些上游 stable 变更对当前 Panther 路径解释力低；不能覆盖 RK35xx vendor BSP 的差异，也不能据此排除 6.1.117–6.1.173 之间其他非 STMMAC/网络代码提交。

### 1.13 方向 1 当前阶段性结论

1. 早期正常版本历史已形成时间序列：6.1.65（2024-02-27 备份）→ 6.1.79（2024-10-18）→ 6.1.112（2024-11-11）→ 6.1.116（2024-11-10 构建、后续实机运行验证）。6.1.79/112 的日期顺序与 6.1.116 的 build timestamp 不应被混写成严格升级顺序；它们是历史归档节点。
2. 6.1.116 之后用户确认存在多个出现相同故障的 6.1.y 版本，但当前仓库没有逐个版本的准确实机清单；6.1.174-rk35xx 是第一个已归档且可绑定明确故障证据的样本，不等于用户历史首次遇到故障。
3. 6.1.192 是软件包元数据，不是已证明的运行内核；从版本矩阵中排除。
4. 6.1.117–6.1.173 的源码提交筛查不能代替实际运行版本清单；已筛查的若干 STMMAC 变更多数不命中 Panther 已知路径，但这并不构成对整个内核的回归排除。
5. 6.1.174-rk35xx 自动资产与 Actions run #296 的上传时间吻合，c2f148d 为高置信度源码候选；由于 workflow_dispatch 实际 inputs/source_hash 输出未取得，仍非二进制级确证。

**方向 1 仍未结项。** 现阶段不能从现有资料精确定位 6.1.y 首次故障小版本，也没有必要重复网络测试。后续唯一有效增量是恢复用户已有的逐版本历史记录/备份资产，或取得 6.1.174 Actions 实际 source_hash/build provenance；若原始材料无法提供，最终报告必须把缺口标记为不可恢复，而不能猜测。方向 2 继续保持冻结。