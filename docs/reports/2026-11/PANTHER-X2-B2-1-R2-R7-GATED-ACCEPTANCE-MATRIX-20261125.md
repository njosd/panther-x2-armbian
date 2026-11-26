# Panther X2 Project A — R2–R7 分段验收矩阵

- 日期：2026-11-25
- 配套计划：PANTHER-X2-B2-1-R2-R7-DETAILED-IMPLEMENTATION-AND-GATED-ACCEPTANCE-PLAN-20261125.md
- 状态：只读研究/计划；未授权设备操作。

## 1. 证据等级

| 等级 | 证据 | 最低解释 |
|---|---|---|
| E0 | 源码/Kconfig/Makefile 依赖审计 | 固定源码中存在预期软件路径 |
| E1 | 构建产物和最终配置 | 预期代码确实被构建 |
| E2 | 运行时注册/绑定 | 框架、设备或驱动已注册/绑定 |
| E3 | probe/资源获取 | 驱动接管目标并取得所需资源 |
| E4 | 功能操作 | 实际操作产生预期结果 |
| E5 | 下游集成成功 | 下游工作，按已知前置条件支持上游 |
| E6 | 对端线侧捕获 | 对端捕获到正确 Ethernet 帧 |

## 2. 验收矩阵

| 阶段 | 对象/交接 | 最早直接验证点 | 观察方法 | 成功证据 | 不能证明 |
|---|---|---|---|---|---|
| R2 | GPIO provider | R2 | `gpio-rockchip` bank bind、gpiochip 注册 | controller bind + gpiochip 证据 | 每个引脚电气质量、GMAC reset consumer（R7-A/C） |
| R2 | Syscon/Regmap | R2 | `rockchip-pinctrl` bind；probe 使用 `syscon_node_to_regmap()` 获取 GRF/PMU regmap | pinctrl probe/bind 成功及无 regmap lookup 错误 | GMAC consumer 的独立 phandle 调用（R7-A）及所有寄存器均正常 |
| R3 | RK3x I2C | R3 | controller 绑定、adapter 注册 | I2C0 adapter | PMIC 事务成功 |
| R3 | RK809 | R3 | 安全 ID/status 只读、重复读取 | 稳定 PMIC 响应 | 全部 PMIC rail |
| R3 | MFD/Regmap | R3 | parent、子设备、regmap 关联 | 子设备和 regmap | 物理电压 |
| R3 | Regulator | R3 | regulator 注册和只读 summary | 预期 regulator 实例 | PHY rail 电压 |
| R3/R7-A | PHY supply consumer | R7-A | GMAC regulator get/enable 返回值 | 实际 consumer 关系 | PHY 引脚电压 |
| R4 | MDIO/PHY 软件框架 | R4 | 框架/driver 注册（若可观测） | 注册证据 | 真实 MDIO 事务 |
| R7-B | MDIO controller/bus | R7-B | bus 注册、PHY 地址访问 | bus/device 证据 | RGMII 数据流 |
| R7-B | PHY identity | R7-B | 地址 0 Clause 22 ID 重复读取 | 稳定 ID | link 或 MAC TX |
| R7-B | RTL8211F bind | R7-B | PHY driver 绑定关系 | 目标 driver 绑定 | DMA |
| R7-B | PHY link | R7-B | PHY state、对端端口状态 | 稳定协商 | 正确帧到达 |
| R5 | STMMAC/DWMAC4 build | R5 | 配置、对象、构建审计 | E0/E1 | 硬件功能 |
| R7-A | STMMAC probe/netdev | R7-A | driver bind、probe、netdev | E2/E3 | interface open |
| R7-C | DMA ring/resources | R7-C | descriptor 分配/ring 初始化 | ring/resource 证据 | DMA 已读取帧 |
| R7-C | DMA engine | R7-C | reset/init、MAC/MTL、队列/IRQ | open 成功和状态 | 物理 TX |
| R7-D | skb/DMA mapping | R7-D | skb bytes/hash、DMA map 返回、地址/长度 | 同一帧与 DMA mapping 关联 | MAC 已发送 |
| R7-D | TX descriptor | R7-D | DMA 地址、长度、FS/LS、OWN 交接 | descriptor 指向目标 buffer | DMA 读取正确 |
| R7-D | TX completion | R7-D | OWN/status、stmmac_tx_clean、错误统计 | 完成且无报告错误 | 对端收到 |
| R7-A | Rockchip probe | R7-A | compatible、rk_gmac_probe、bind | probe 路径完成 | link/data path |
| R7-A | GRF/Syscon | R7-A | provider 获取和相关操作返回 | consumer/operation 证据 | 全部引脚状态 |
| R7-A/C | Clock | R7-A/C | get/enable 返回、clock tree/rate | framework 状态和 enable 成功 | 引脚真实波形 |
| R7-A/C | Reset | R7-A/C | 获取、API 返回和可用状态 | reset 操作成功 | 下游模块全部正常 |
| R7-A | Pinctrl | R7-A | selected state、pinctrl debug | state 已应用 | 板级信号完整性 |
| R7-A/B | PHY regulator | R7-A/B | regulator get/enable、只读状态 | consumer/rail 证据 | 引脚实际电压/噪声 |
| R7-D | 物理 TX | R7-D | 对端逐帧捕获和 payload 核验 | E6 | Panther RX/IP |

## 3. 停止条件

- 配置或构建与批准差异不一致：不启动。
- provider/PMIC/MDIO/probe 任一失败：停在当前门。
- 缺少观测手段：标记 BLOCKED，研究观测方法，不伪造 PASS。
- DMA mapping、descriptor ownership/completion 异常：停止发送，保留 ring/driver 证据。
- 对端缺帧、序列号缺失或 payload 不符：TX FAIL，不引入 R8。
- R7-D 未通过，不引入 RX/ARP/IPv4。

## 4. 每次测试记录字段

阶段/门、授权范围、时间戳、源码/config/DTB 哈希、启动日志区间、测试 marker/sequence、测试前后计数器、观测方法、原始输出位置、解释和限制、最后通过边界、是否放行。

## 5. 非破坏性观测优先级

1. 已有 sysfs/procfs/debugfs 只读状态；
2. 已有 netdev/driver statistics；
3. 内核中已经存在且启用的 tracepoint/function tracing；
4. 单独受控构建中的最小诊断 instrumentation；
5. 仅在寄存器语义和读取安全性已确认后进行寄存器只读；
6. 只有软件证据不足且另行批准时才做外部电气测量。

禁止随意读取 MMIO、dump 未文档化寄存器，或为获取观测而改变 reset/clock/power/GPIO 状态。


## 6. 全阶段黄金基线与 6.18 默认配置放行门（2026-11-26）

以下为 R2–R7 每一阶段的必填交叉验收项；R0/R1/R8 亦遵循 B2-1 主计划中的同一规则。

| 通用验收项 | 必须记录的内容 | 未满足时的处理 |
|---|---|---|
| 第一黄金基线 | 6.1.65 对应功能、最终配置/内嵌 IKCONFIG、built-in/module 对象、相关 DTS/源码证据 | 缺少证据的字段标未知，不得推断 |
| 第二黄金参照 | 6.1.116 相关正常行为/配置证据（适用时） | 说明是否适用及原因 |
| 6.18 默认实现 | 最终 `.config`、依赖闭包、对象、源码实现与版本差异 | 不以 fragment/Kconfig default 替代最终结果 |
| 实际功能 | 本阶段安全可执行的注册、probe、只读操作或功能测试，记录输入与输出 | 仅有静态/构建证据时不得整体 PASS |
| 最小改动决策 | 默认功能通过则保留；失败才依据差异提出单变量修正 | 禁止为了配置一致机械回移 |
| 阶段放行 | 差异已解释、必需功能有直接或边界明确的集成证据、限制已归档 | FAIL/BLOCKED 或必需功能未验证时不放行 |

**黄金基线证据边界：** 6.1.65 已有原版系统在 Panther X2 上完成 Ethernet/RTL8211F、千兆链路、DHCP、网关/外网 IPv4 和 DNS 的正向实机验证；其内嵌 IKCONFIG 与 `modules.builtin` 是构建配置证据，不代表其中每个 provider 的独立功能都已单独测试。不能把整机网络成功无条件泛化为所有 provider 的独立 PASS。

**默认配置接受原则：** 6.18 的组件版本、配置值、依赖结构和实现方式可以不同于 6.1.65。只要当前阶段功能通过且差异有解释，就接受 6.18 默认实现；不要求配置逐项相同。

R2 运行时 consumer 说明：6.18.63 Panther X2 pinctrl 节点带有 GRF/PMU syscon phandle；pinctrl probe 实际调用 syscon API 并通过 of_platform_populate 创建 GPIO bank 子设备。故 R2 可以在不启用 GMAC/MDIO/PHY 的前提下，使用 pinctrl bind 与 gpio-rockchip/gpiochip 作为共享 provider 的安全运行时验证路径。