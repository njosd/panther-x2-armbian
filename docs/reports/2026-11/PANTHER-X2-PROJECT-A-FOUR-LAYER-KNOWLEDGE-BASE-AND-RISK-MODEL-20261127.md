# Panther X2 项目 A — 四层技术知识库与风险模型（2026-11-27）

## 1. 决策目的

项目 A 将技术知识按可复用范围拆分为四层知识库，避免把 SoC 公共能力、跨产品通用驱动、Rockchip SoC 适配和 Panther X2 板级实现混为一谈。

本模型用于组织证据、确定审计优先级和识别跨层接口风险；不改变既定 G0–G10 门序，不构成任何设备操作、PMIC 写入、GMAC 激活或网络发送授权。

## 2. 四层知识库

| ID | 知识库 | 收录范围 | 典型对象 | 本项目初始风险优先级 |
|---|---|---|---|---|
| K1 | Linux 公共网络栈与内核基础设施 | 跨设备通用的软件接口和机制 | AF_PACKET、网络核心、skb、netdev、DMA API、IRQ/NAPI、PHYLIB/PHYLINK、MDIO framework | 相对低；版本/配置/调用路径变化仍需核验 |
| K2 | 通用 MAC/IP 驱动 | 可被多个 SoC/板卡采用的 MAC IP 与驱动实现 | Synopsys DWMAC4、STMMAC、TX/RX descriptor、DMA channel、MAC/MTL | 低至中；需确认实际 IP revision、capability、配置和驱动版本 |
| K3 | Rockchip SoC 适配 | Rockchip SoC 对通用 IP、时钟/复位/GRF 等资源的适配层 | Rockchip GMAC glue、GRF、CRU、reset、clock、SoC-specific compatible/match data | 中；重点审查 SoC 型号边界、寄存器差异和初始化时序 |
| K4 | Panther X2 板级适配 | 具体 PCB、外围器件、引脚复用和板级设备树连接 | GMAC1、RGMII、RTL8211F、MDIO address 0、M0 pinctrl、PHY reset GPIO、supply、clock source、RGMII delay、board DTS | 高；作为优先审计对象，但不预判硬件损坏 |

风险优先级是当前项目的工程排查顺序，不是来自大样本统计的故障率，也不表示 K1/K2 已经被证明无故障。

## 3. 必须严格区分的概念

1. **RK3566 公共硬件能力 ≠ 每个 RK3566 产品都启用该功能。** 芯片集成 GMAC，不代表每块板都布线、供电、复用引脚或在 DTS 中启用它。
2. **Synopsys DWMAC4/STMMAC ≠ RK3566 独占驱动。** 这是跨产品使用的通用 MAC IP/驱动体系；实际兼容性仍取决于 IP revision、SoC glue、配置和板级资源。
3. **Rockchip GMAC glue ≠ 不加区分的 RK3566 全系实现。** 必须按 compatible、match data、SoC 寄存器布局和驱动分支判断适用范围，不能从 RK3568 名称直接推断 RK3566 所有产品相同。
4. **Panther X2 板级属性不得套用到其他 RK3566 板卡。** PHY 型号、RGMII/MII/SGMII 模式、MDIO 地址、pinctrl、reset、supply、clock 和 delay 均须有该板证据。
5. **设备树静态描述不等于硬件运行事实。** clock fixed-rate 节点不证明物理波形；GPIO 属性不证明实际电气极性/时序；supply phandle 不证明 provider 已绑定或 rail 已达到目标状态。
6. **probe 成功不等于接口 open；接口 open 不等于 DMA 正常；DMA completion 不等于线侧发送成功。** 物理 TX 的最终验收仍以独立 LAN 对端捕获同一测试帧为准。

## 4. 为什么 K4 与跨层边界优先审计

两条黄金基线 6.1.65 与 6.1.116 已在同一 Panther X2 上证明板载千兆网络曾正常工作。这降低了“板卡硬件存在固有、持续性缺陷”的初始怀疑，但不能证明 6.18.63 的驱动、配置和初始化时序必然兼容。

公共组件由于采用范围广，问题通常更容易被发现并反馈；单一板卡的时钟、复位、PHY、引脚复用和供电连接组合使用者较少，特定问题可能长期缺乏触发、复现或上报。因此，本项目优先反向复用黄金系统证据，重点检查 K3/K4 及其与 K1/K2 的交界。

需要重点审查的跨层接口包括：

- K2 MAC ↔ K3 Rockchip glue：interface mode、GRF write-mask、clock/reset 获取与 powerup/down 调用顺序；
- K3 SoC resources ↔ K4 board DTS：clock parent/rate、reset ID、pinctrl group、GPIO 编号/极性；
- K4 PHY supply ↔ K3/K1 regulator/IO-domain provider-consumer：provider 注册、deferred-probe、consumer 获取/enable 及副作用；
- K2 MAC ↔ K4 PHY：RGMII mode、TX/RX delay、PHY reset 时序、PHY clock/RXC/CLKOUT；
- K1 DMA API ↔ K2 STMMAC/DWMAC4：DMA mask、mapping direction、descriptor ownership、completion/reclaim。

上述是风险检查点，不代表已证明其中任一项就是当前故障根因。

## 5. 知识条目统一证据标签

每条知识条目、差异和结论使用以下标签，可组合使用：

| 标签 | 含义 |
|---|---|
| `COMMON-VERIFIED` | 公共软件机制已有直接验证证据，注明版本和验证范围 |
| `VERSION-DIFF` | 版本间存在源码、配置或对象差异；差异本身不等于故障 |
| `SOC-ADAPTATION` | 涉及 Rockchip SoC 适配，必须注明 compatible/SoC 范围 |
| `BOARD-VERIFIED` | Panther X2 板级配置/行为有直接证据，注明启动版本和条件 |
| `BOARD-UNVERIFIED` | Panther X2 板级配置或运行行为尚无直接验证 |
| `CROSS-LAYER-RISK` | 两层之间存在未闭合的 provider/consumer、时序、资源或数据接口 |
| `STATIC-ONLY` | 仅源码、Kconfig、DTS 或二进制静态分析 |
| `BUILD-ONLY` | 仅证明配置解析、编译/链接和产物结构 |
| `RUNTIME-OBSERVED` | 实机观察到指定运行行为，但不自动推及更高层功能 |
| `E2E-VERIFIED` | 独立端到端证据通过；TX 必须有对端 pcap 捕获同一帧 |

不得把静态审计、CI 构建、driver bind、netdev 注册、carrier、计数器变化或 DMA completion 升级为 E2E-VERIFIED。

## 6. 黄金基线与 6.18 的使用规则

- 6.1.65 是第一功能黄金基线；6.1.116 是第二正常行为参照。两者已有证据优先复用，不重复测试。
- 对每个涉及硬件的子项，优先从黄金基线恢复实际 config、built-in 对象、源码、DTB、启动日志和运行结果，再与锁定的 6.18.63 对照。
- 6.1.65/6.1.116 的成功降低同一硬件固有缺陷的怀疑，但不自动证明 6.18 新驱动实现正确。
- 公共层若已完成既定多版本审计，不重复开题；仅在当前阶段存在具体证据缺口或版本/配置发生实质变化时补证。
- K3/K4 优先级较高，但仍严格遵守现有阶段顺序：当前先完成 G2-B build-only；G2-PROBE、G3/G4、G5/G6/G7 各自保留准入门。
- GMAC 高风险审计清单、G5-A1/A2、G6-A/B、G7-E6 顺序和 ABCD 单帧规则不因本知识库调整而改变。

## 7. 当前证据映射（2026-11-27）

| 层 | 已有证据 | 尚未证明的关键事项 |
|---|---|---|
| K1 公共网络栈 | R1 AF_PACKET 软件 API 实机验证；B2-0 方向二 generic network-core 多版本静态审计；R1 trace/观测配置审计 | 目标 GMAC 的真实 skb→driver→DMA→线侧 TX |
| K2 通用 MAC/IP 驱动 | B2-0 方向三及 B2-1 R5 STMMAC/DWMAC4 静态审计 | Panther 实机 MAC capability/register map、DMA reset 结果、descriptor 生命周期和真实 TX |
| K3 Rockchip SoC 适配 | B2-0 方向四、B2-1 R6 glue/GRF/CRU/clock/reset 静态审计 | 6.18 实机 probe/powerup 资源状态与时序；provider-ready 后的运行状态 |
| K4 Panther X2 板级 | 两条黄金基线正常运行；6.1.116 与 6.18.63 完整 Panther DTB 字节相同；6.1.65 GMAC 核心属性已有原始解析 | 6.18 provider/consumer 最终状态、PHY reset/clock 实际运行条件、RGMII 线侧行为和 TX E6 |

## 8. 本模型对当前路线的约束

- 不新增或提前执行一个“板级硬件排障”阶段；本模型只是现有审计的知识分类与风险排序。
- 不因 K4 优先级高就要求盲测电压、寻找 PCB testpoint 或重复已完成黄金基线测试。只有软件对照出现具体、无法解释的物理异常假设时，才提出针对性最小补证。
- 不绕过 PMIC/regulator/IO-domain provider，不手写寄存器，不强制时钟，不伪造 PHY link，不修改 DMA 算法。
- 不恢复已封存 Project B 的 GMAC 根因调查。
- 不影响 SN64G 黄金对照卡和 eMMC；不进行未授权写入、安装或系统配置修改。

## 9. 当前结论与下一步

**知识库分类与风险模型：已建立（架构决策）。** 它提供后续审计统一标签和优先级，不代表 K1–K4 全部通过。

当前执行下一项仍为 **G2-B build-only**：启用 `MFD_RK8XX_I2C=y`，不启用 `INPUT_RK805_PWRKEY` 与 `REGULATOR_RK808`；RK809 节点保持 disabled，GMAC/MDIO/PHY 继续 disabled。只审查最终配置、依赖闭包、built-in 对象、编译/链接和产物。通用 QEMU virt 不模拟 RK3566/Panther X2，不安排无代表性的 kernel system boot；如后续执行 QEMU user-mode 工具自检，单独标记为用户态测试。G2-B 不访问 PMIC、不触发 probe、不构成 PMIC runtime PASS。G2-PROBE 仍须独立副作用审查和明确授权。

---
