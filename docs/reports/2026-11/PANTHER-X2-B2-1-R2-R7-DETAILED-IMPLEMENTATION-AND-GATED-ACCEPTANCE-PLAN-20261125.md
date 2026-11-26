# Panther X2 Project A — R2–R7 详细实施计划与分段验收修订

- 日期：2026-11-25
- 状态：研究/计划交付物；不构成构建、启动、写卡或实机操作授权
- 源码基线：ophub/linux-6.18.y @ aee4e352a15d636cbc484f56819c6e59474dfd9f
- 上位计划：PANTHER-X2-B2-1-IMPLEMENTATION-PLAN-20261125.md

## 1. 修订目的

原计划 R2–R6 保持 GMAC/MDIO/PHY 设备树节点关闭，避免过早进入硬件数据面；但因此部分组件只能通过静态配置和构建检查，不能证明其真实功能。此次修订保留 R0→R8 顺序、单变量和 TX-first 原则，为每层增加运行时证据门，并将原 R7 拆成 Probe、MDIO/PHY、MAC/DMA、物理 TX 四段。

**核心原则：组件可能在配置、参数和编译均正确时仍然功能异常。每一层必须有直接验证；无法直接验证时标为 BLOCKED，并明确最早验证点。不得把构建通过写成运行正常。**

## 2. 统一验收状态

| 状态 | 含义 |
|---|---|
| PASS-STATIC | 源码依赖、Kconfig、Makefile、配置差异审计通过 |
| PASS-BUILD | 对象构建成功，产物身份和哈希已记录 |
| PASS-REGISTER | 运行时框架/设备/驱动注册或绑定成功 |
| PASS-PROBE | 目标驱动 probe 完成，必要资源获取成功 |
| PASS-FUNCTIONAL | 通过真实功能操作并取得预期证据 |
| PASS-INTEGRATED | 下游实际成功，且对上游形成边界明确的间接证明 |
| PASS-LINE | 对端真实捕获正确 Ethernet 帧 |
| BLOCKED | 当前硬件/设备树依赖边界不允许直接验证 |
| FAIL | 已执行测试且结果不符合预期 |

每个组件分别标记状态，不允许以一个笼统 PASS 覆盖未验证子项。

### 2.1 全阶段黄金基线与默认配置规则（2026-11-26）

- 每个 R 阶段均须对照第一黄金基线 6.1.65；必要时以 6.1.116 补充正常行为证据。对照范围只覆盖本阶段实际涉及的组件、配置、依赖和实现路径。
- 6.18 默认配置/实现优先。版本升级、配置默认值变化、依赖调整或实现重构均可接受；不要求与 6.1.65 逐项相同。功能验证通过即接受默认实现，不做无证据的旧配置回移。
- 每阶段必须记录 6.1.65 / 6.1.116（适用时）/ 6.18 的差异、证据来源和未知项；缺失原始配置证据不得推断相同或不同。
- 静态、构建、注册、probe、功能和集成证据分级。只有本阶段必需功能已按安全边界实际验证、黄金基线差异已解释且无未解决缺口，才允许整体 PASS 和放行下一阶段。
- 功能失败时，先按黄金基线定位差异，再单变量最小修正；默认功能通过时保留 6.18 默认配置。

## 3. R2–R7 实施卡

### R2 — 共享 SoC Provider

**目标：** 只补入 R0 证明 B1 缺失且 GMAC 路径确实需要的 provider。COMMON_CLK、Rockchip clock/CRU、pinctrl、GPIOLIB、reset controller、ROCKCHIP_GRF 等 B1 已有项不得重复添加。

**验收顺序：**
1. R2.1 静态：核对每个 provider 的精确依赖、对象和真实 consumer。
2. R2.2 构建：确认对象实际 built-in，记录配置 diff 和产物哈希。
3. R2.3 注册：检查 controller/platform device、驱动绑定和可用的 sysfs/debugfs 状态。
4. R2.4 消费者：验证现有且安全的消费者已绑定 provider，检查 deferred probe 和错误日志。
5. R2.5 功能：只采用已知安全的只读操作或现有消费者正常运行证据。不得翻转未知 GPIO，尤其不得操作 reset、电源或存储控制脚。

**通过条件：** 先完成 6.1.65（必要时 6.1.116）对应 provider 配置/实现差异对照，再确认 6.18 默认配置和构建对象；运行时至少达到 PASS-REGISTER，并对安全、现存 consumer 取得功能证据。不得翻转未知 GPIO，尤其不得操作 reset、电源或存储控制脚。GMAC DT 节点仍关闭。

若由于 GMAC/MDIO 节点关闭而不存在安全 consumer，provider consumer 功能项必须标记 BLOCKED，并明确在 R7-A 首次使用时验证；在该必需功能尚未得到验证前，R2 不得整体 PASS 或放行 R3。若仅能证明注册而不能证明 provider 功能，亦不得将注册证据升级为 PASS-FUNCTIONAL。

### R3 — I2C0 / RK809 / MFD / Regulator

Panther DTS 中 RK809 位于 I2C0 地址 0x20。正式实施前须再次核对实际编译 DTB 中 PHY supply phandle 与 regulator 标签，不能凭名称相似推断为同一电源轨。

**验收顺序：**
1. R3.1：I2C0 控制器绑定、adapter 注册。
2. R3.2：使用已确认安全的识别/状态读取验证 RK809 通信和重复读取稳定性；禁止盲目扫描总线。
3. R3.3：确认 RK809 parent driver、MFD 子设备和 regmap 实例。
4. R3.4：确认预期 regulator 实际注册，保存 regulator summary/sysfs/debugfs 可用证据。
5. R3.5：验证现有安全 regulator consumer 的绑定/状态。
6. R3.6：PHY supply consumer 的实际获取/启用只能在 R7-A GMAC probe 时验证；当前标记 BLOCKED。
7. R3.7：仅在寄存器语义确认后允许只读 PMIC 状态观察。寄存器状态不等于电源引脚实际电压，必要时须另行批准外部测量。

**通过条件：** PMIC 稳定通信、MFD/regmap 初始化、regulator 注册及至少一个相关现有 consumer 路径成功。禁止 I2C/PMIC 写入、regulator 开关/电压切换和电源循环。

### R4 — MDIO / PHYLIB / PHYLINK / RTL8211F

1. R4.1 静态/构建：核对 MDIO_BUS、OF_MDIO、PHYLIB、PHYLINK、REALTEK_PHY 的精确依赖和对象。
2. R4.2 软件注册：如运行时可观测，确认框架和 RTL PHY driver 注册；不可观测则保留 PASS-BUILD，不虚构 PASS-REGISTER。
3. R4.3 MDIO bus 实际注册：由于 MDIO 控制器依附 GMAC 硬件，R2–R6 GMAC disabled 时标记 BLOCKED。
4. R4.4 PHY ID：在 R7-B 对地址 0 执行安全、重复的 Clause 22 ID 读取，记录超时/错误并与 RTL8211F 预期 ID 对照。
5. R4.5 PHY 绑定和状态机：确认 PHY 设备绑定目标 Realtek 驱动，观察 phylib/phylink 状态和链路协商。

**通过条件：** R4 软件准备可以通过；真实 MDIO/PHY 功能只能在 R7-B 判定。驱动已注册不等于板载 PHY 已响应。

### R5 — STMMAC / DWMAC4 / DMA Core

1. R5.1 静态/构建：核对精确 Kconfig、Makefile、对象闭包及 Panther 实际 MAC core 类型。
2. R5.2 驱动注册：如有可靠接口则观察 platform driver 注册。
3. R5.3 设备 probe/netdev：最早在 R7-A 验证设备绑定、STMMAC probe 和 net_device 注册。
4. R5.4 接口 open：最早在 R7-C 验证 DMA descriptor 资源分配、ring 初始化、runtime-PM、PHY 初始化、DMA software reset/init、IRQ、队列启动和 DMA start。
5. R5.5 TX 数据路径：R7-D 跟踪唯一测试帧经过 stmmac_xmit、DMA mapping、descriptor 地址/长度/控制位/OWN 交接及 stmmac_tx_clean 完成回收。

**源码核实：** 固定源码中 stmmac_open 分配 DMA descriptor 资源并进入 __stmmac_open；stmmac_hw_setup 初始化 DMA engine 并配置 MAC/MTL；stmmac_xmit 将 skb 数据映射为 DMA 地址并写入 descriptor；DW MAC4 descriptor helper 设置 OWN；stmmac_tx_clean 检查完成状态并回收资源。这些是源码调用路径，不是 Panther 已实测结果。

### R6 — Rockchip GMAC Glue / 资源链

**静态准备：** 核对 compatible、资源/ops 映射、clock/reset/GRF/regulator/pinctrl 依赖、RGMII mode/delay；禁止顺手回移历史 workaround。

**运行时验收最早在 R7-A/R7-C：**
- compatible 匹配和 rk_gmac_probe 执行；
- 平台资源与 DT 解析；
- rk_gmac_setup 中 regulator 获取及 BSP setup；
- clock 初始化、enable callback 返回值；
- GRF 操作和接口模式设置；
- reset 获取、状态和 PHY reset 时序；
- pinctrl state 选择；
- regulator 获取/启用和实际 consumer 关系；
- 到 devm_stmmac_pltfr_probe 的交接。

clock framework 显示 enabled 不等于引脚上有正确波形；reset API 成功不等于下游硬件全部正常；regulator 注册不等于 PHY 引脚电压正确。

### R7 — 恢复硬件路径，拆成四道独立验收门

R7 唯一变量是目标 Panther X2 DTB 中 GMAC1、MDIO bus、PHY address 0 及必要引用/状态。不得同时改内核源码、Kconfig、bootargs、initramfs 或测试程序。

**R7-A：Platform Probe**
- 启动前审查 DTB 反编译差异、所有 phandle 和资源。
- 观察 compatible、rk_gmac_probe、资源获取、clock/reset/pinctrl/regulator、STMMAC handoff、netdev 注册及 deferred probe。
- 不发送测试帧。
- PASS 仅证明 probe/resource path，不证明 MDIO、DMA 或 TX。

**R7-B：MDIO / PHY**
- 确认 MDIO bus 注册。
- 对地址 0 重复读取 PHY ID，核实 RTL8211F 绑定、PHY 状态机和链路协商。
- 同步记录对端交换机端口状态。
- PASS 证明控制总线/PHY 响应和链路协商，不证明 MAC 数据面。

**R7-C：MAC / DMA open**
- 接口 UP 属于主动操作，须单独授权。
- 检查 TX/RX ring 资源、descriptor 初始化、DMA mapping/resource、runtime PM、PHY 初始化、DMA reset/init、MAC/MTL、IRQ、队列及 DMA start。
- 保存前后 netdev/driver counters。
- 不宣称物理 TX 成功。标准 open 可能同时初始化 RX/TX 结构。

**R7-D：物理 TX**
- 用专用 AF_PACKET 原始帧程序发送 EtherType 0x88B5 广播帧。
- payload 带固定项目标识、run ID、递增序列、长度、确定性数据和校验。
- 不配置 IPv4，不依赖 ARP、ICMP、DHCP、DNS。
- 追踪同一帧在 skb、DMA mapping、descriptor、completion 和对端抓包中的身份。
- 对端真实捕获是最终 PASS-LINE 证据。发送系统调用返回、TX counter 增长、descriptor completion 或 PHY link 均不能替代。
- 多轮、多长度重复；TX-PASS 前不进入 R8。

## 4. 统一故障隔离

每次失败冻结源码/config/DTB/bootargs/initramfs 哈希、完整 UART 日志、设备绑定/deferred probe、相关 provider 状态、最后成功边界、首个失败边界、测试序列和两端证据。

先区分功能失败与观测能力不足。找不到 trace facility 不等于硬件故障。每轮只修正一个组件或已证明不可拆分的最小闭包；失败证据不得覆盖。

## 5. 下游成功可提供的间接证据

| 成功事件 | 支持的上游路径 | 不能证明 |
|---|---|---|
| RK809 ID 稳定读取 | I2C 控制器和该事务通信 | 所有 PMIC 轨正常 |
| MFD/regulator consumer 成功 | I2C、PMIC、regmap、regulator 对应路径 | PHY 引脚实际电压 |
| PHY ID 稳定 | MAC 侧 MDIO、总线事务、PHY 响应 | RGMII 数据通路和 TX DMA |
| PHY link up | PHY 与链路协商、相关供电/时钟前提 | MAC DMA 或帧到达 |
| netdev 注册 | MAC platform probe 和 net_device 建立 | interface open/DMA |
| descriptor completion | 对应 DMA/驱动完成路径 | 物理线侧收到正确帧 |
| 对端捕获正确 payload | 到达该对端捕获点的整条 TX 路径 | Panther RX 或 IP 协议 |

间接证据必须绑定具体事件及其前置条件，不可泛化为上游所有功能都正常。

## 6. 放行约束

- R2–R6 的 GMAC/MDIO/PHY disabled 边界不变。
- R7-A、R7-B、R7-C、R7-D 各自独立记录、独立判定。
- 任一门 FAIL/BLOCKED，不进入下一门。
- R7-D 未 PASS-LINE，不得引入 RX、ARP、IPv4、ICMP、路由、TCP/UDP、DHCP/DNS。
- 上位计划 G1/R1 状态以总路线图和 B2-1 主计划最新执行记录为准；本文件不自动授权任何构建、刷写或实机操作。
- R2 必须先完成黄金基线对照和现有 R1 镜像的只读运行时验证；R2 未整体 PASS，不放行 R3。

## 7. 源码依据

固定 commit：aee4e352a15d636cbc484f56819c6e59474dfd9f。
- arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c
- drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c
- drivers/net/mdio/mdio_bus.c
- drivers/net/phy/phy_device.c
- drivers/regulator/rk808-regulator.c
