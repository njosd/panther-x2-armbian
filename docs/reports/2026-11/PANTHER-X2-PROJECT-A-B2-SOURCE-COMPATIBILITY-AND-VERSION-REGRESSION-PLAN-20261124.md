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
| G116 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，Linux 6.1.116 | 正常网络黄金基线及源码对照 | 已验证驱动/PHY、千兆链路、DHCP、LAN 连通；保留历史采集证据边界 |
| R61Y | Linux 6.1.y 系列（用户确认曾连续升级多个小版本，网络故障始终相同；各次实测的精确版本号待从仓库报告/镜像记录恢复） | **跨小版本持续异常的版本族** | 故障持续性来自用户回忆；逐个版本的实机记录、Image/DTB/config/source commit 尚需绑定。不能把整个 6.1.y 系列简化为单一 6.1.174。 |
| R174 | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`，Linux 6.1.174 | 6.1.y 异常版本族中的一个已被项目 B 重点审计的源码候选 | 构建源码映射为高置信度候选，不代表它是用户记忆中的第一个故障版本，也不是所有历史报告中的绝对二进制证明 |
| R612 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，6.12.81 | 项目 B 已有实机异常与精确源码审查对象 | PHY/千兆 link 正常、DHCPv4 未成功；TX 外部物理边界未闭环 |
| T618 | `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`，6.18.63 | 当前 B1 构建和后续 B2 的精确目标源码 | B1 已实机启动；网络被隔离，尚无 6.18 Ethernet 运行证据 |

**比较规则：** 6.1.65/6.1.116 是正常实机行为参照；6.1.y 是用户确认曾跨多个升级版本持续出现相同网络故障的异常版本族，6.1.174 是其中一个精确源码审计样本，不能代表全部测试版本；6.12.81 是另一异常样本；6.18.x 历史完整系统需按具体构建绑定，6.18.63 B1 是网络隔离目标源码基线。不能把 6.12.81 的源码差异直接推定为 6.18.63 仍存在，也不能把 6.1.116 的私有修改无条件移植到 6.18。

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
- [ ] 恢复 6.1.y 系列曾经升级测试的具体小版本清单、每个版本的镜像/DTB/config/source commit 和实机故障记录；在清单恢复前，将 6.1.174 仅作为一个代表性源码样本，不称为 6.1.y 的最早故障版本；
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

