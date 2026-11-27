# Panther X2 项目 A — G0 总体复核与 G2 受控激活预案（2026-11-27）

## 1. 结论摘要

**G0：CONDITIONAL PASS（仅允许形成下一门实施/授权计划，不构成硬件操作授权）。**

依据：
- 6.1.65 与 6.1.116 两条黄金基线已证明同一 Panther X2 板载千兆 Ethernet 能工作。
- 6.1.65 与 6.1.116 的 RK809 MFD、regulator、IO-domain、Rockchip GMAC glue 源码关键文件完全相同（6.1.65 源码端点仍保留 candidate 身份限制）。
- 6.1.65 最终配置包含旧 RK808/RK809 MFD 与 regulator built-in；6.1.116 的真实最终配置已恢复；6.18.63 R1 的主要缺口是未构建新版 RK8xx MFD/regulator provider。
- 6.1.116 与 6.18.63 完整 Panther DTB 字节级相同；6.1.65 原始 DTB 的 GMAC1 核心解析已归档，PMIC/IO-domain 子树仍缺原始二进制重新解析。
- 现有 R1 的 I2C/RK809 只读身份与状态证据、R2 的 pinctrl/GPIO/Syscon provider 运行证据已完成；不重复测试。
- ABCD sender/trace/对端 pcap 规格已完成；真实目标网卡尚不可发送。

G0 的 CONDITIONAL PASS 仅表示已有静态和运行证据足以编制下一门 G2 的最小受控计划。G0 不放开 MFD probe、不启用 regulator、不恢复 GMAC、不执行发送。

## 2. G0 子项最终状态

| 子项 | 状态 | 当前处理 |
|---|---|---|
| G0.1 provider/consumer 依赖矩阵 | PASS-STATIC / CONDITIONAL | R2–R6 证据已映射；R1 I2C/RK809运行证据复用 |
| G0.2 RK809 MFD/regulator 行为对照 | PASS-COMPARISON / HOLD-ACTION | 黄金与 6.18 的主要初始化行为已对照；6.18 MFD probe 有写入是继承路径，不单独作为 NO-GO；实际 probe 仍需单独授权 |
| G0.3 IO-domain | PASS-STATIC / RUNTIME UNKNOWN | 缺 provider 时 R1 的 deferred-probe 早于 GRF write；后续重试最终状态未知；provider 出现后再验证 |
| G0.4 clock/reset/PHY | PASS-STATIC / PHYSICAL UNKNOWN | clock ID/mux/reset/GRF mode 已核对；125MHz 物理来源与波形未知，不作为 G2 前置 |
| G0.5 ABCD 夹具 | PASS-DESIGN | 同帧 payload/run_id/sequence/hash、trace 和对端 pcap 设计已固定 |
| G0-P1 配置/对象 | PASS | 6.1.65/6.1.116/6.18.63 配置证据已恢复 |
| G0-P2 黄金驱动行为 | PASS-COMPARISON | 关键源码逐文件比较已归档 |
| G0-P3 黄金与 6.18 差异 | PASS-COMPARISON | IRQ/pre-init/SWITCH_REG1/late cleanup/PHY supply 路径已对照 |
| G0-P4 黄金 DTB | CONDITIONAL PASS | 6.1.116=6.18完整DTB字节级相同；6.1.65原始DTB GMAC核心属性已解析，PMIC/IO-domain原始二进制子树未重新解析 |

## 3. 已解释与未解释事项

### 已解释，不再重复

1. 两条黄金系统都包含 RK809 MFD/regulator 软件链；6.1.65 config/built-in 明确启用，6.1.116 实际 config 已归档。
2. 黄金版本的 RK809 pre-init 表与 6.18 对应表逐字节相同；SWITCH_REG1 的 enable descriptor 一致。
3. regulator late cleanup 的关键函数在 6.1.65、6.1.116 与 6.18 的相关实现中不是新引入行为。
4. 6.1.116 和 6.18 完整 DTB 完全相同；GMAC1 RGMII、clock、reset、PHY address 和 vcc_3v3 关键连接与 6.1.65 已有原始解析一致。
5. 不需要重新测量板上 3.3V rail，也不需要先找到 PCB testpoint；不实现 fixed-regulator 替代路径。

### 仍需保留，但不阻塞 G2 计划编制

- 6.1.65 原始 DTB 的 RK809/IO-domain 子树尚未从二进制重新解析；候选 DTS 对照为高置信度但非 binary PASS。
- R1 中 IO-domain deferred-probe 的最终重试/绑定状态未留存；这是 provider 恢复后的运行时验证项。
- RK809 0xEE=0x94 的低 nibble 手册含义仍 UNKNOWN；但当前身份高 nibble 与 RK809 相符，黄金整机成功是同板集成正向证据。
- 125MHz fixed-clock 是 CCF 模型；实体来源/波形未知。此项属于 G4/R7-A 前置，不阻塞只验证 PMIC MFD。
- 6.18 Rockchip glue 的 powerup 生命周期与 6.1.65 不同；这是 G5-A probe 前必须审查的真实版本差异，不应在 G2/G3 提前处理。

## 4. 下一门：G2 RK809 MFD/regmap 受控计划（不执行）

### G2 目标

只验证 6.18.63 stock RK8xx I2C transport + RK8xx core 对 Panther X2 RK809 的识别、regmap 初始化、MFD child creation 和 IRQ domain 建立；不启用 regulator consumer、不恢复 GMAC/MDIO/PHY、不做 TX。

### 4.1 进入 G2 前的静态条件

- 固定源码：ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f。
- 最终配置必须审查 MFD_RK8XX_I2C、MFD_RK8XX、MFD_CORE、REGMAP_I2C、REGMAP_IRQ 的依赖闭包。
- 仅加入本门必需对象；不加入 REGULATOR_RK808，除非 G3 单独计划。
- 固定并保存新 build 的 .config、Image、DTB、System.map、vmlinux/DWARF（为后续 trace 观测使用）及哈希。
- 先确认 R1 当前 DTB 中 RK809 节点 status、compatible、interrupt parent/flags 与 I2C 地址；不得将完整 DTB 和 R1 隔离 DTB 混淆。
- 复用 R1 已完成的 RK809 ID 0x8094、0xF0=0xC2、0xF6=0x00 只读证据，不重复事务。

### 4.2 G2 启动后观察

只观察：
- I2C client 与 rk8xx-i2c driver bind；
- RK8xx core probe 返回状态；
- PMIC variant（按 DT compatible）；
- regmap 创建；
- MFD child devices 是否按预期注册；
- IRQ domain/资源注册结果；
- probe 错误、deferred-probe、重复 probe；
- 与黄金 6.1.65/6.1.116 启动日志的对应关系。

不读取 IRQ status/ACK 寄存器，不主动发起 PMIC I2C 事务，不操作 regulator，不调用 enable/disable，不写 GRF/CRU/GPIO，不触碰 PHY/MAC。

### 4.3 G2 预期副作用和停止条件

必须承认 stock MFD probe 会执行黄金版本同样存在的 rk817_pre_init_reg[] 初始化写入，并建立 regmap IRQ；不能称为只读操作。该行为与两条黄金系统使用的驱动链相符，但仍须由用户对这一次 6.18 probe 单独授权。

停止条件：
- I2C bind/probe 失败；
- PMIC compatible/variant 不匹配；
- regmap 或 MFD child 创建不完整；
- IRQ domain 注册失败或产生未解释错误；
- 发生与预期不同的电源/系统状态变化；
- 出现无法观测/无法安全回退的副作用。

G2 PASS 只代表 MFD/regmap/child/IRQ framework 已成功建立，不代表 regulator rails、IO-domain、PHY、GMAC 或网络已通过。

### 4.4 ABCD 检查

G2 没有目标 netdev/open/DMA，因此 ABCD = NOT EXECUTABLE。记录该阶段缺失条件；不为测试而恢复 GMAC。

## 5. G3/G4/G5/G6 的后续顺序（仅计划）

- G3：单独引入 RK809 regulator provider；比较黄金 descriptors/constraints；核对注册实例和 provider/consumer 绑定，不手动切换 rail。
- G4：检查 IO-domain deferred-probe 是否因 provider 可用而重试；核对最终 bind 与软件 selector 行为；clock/reset/pinctrl 的运行时条件按最小范围验证。125MHz 物理来源仍是 G5/R7-A 前的明确阻塞。
- G5-A：单独恢复 GMAC1 platform 节点，观察 Rockchip glue/STMMAC probe、netdev 注册；注意 6.18 probe 可能通过 platform init 触发 powerup。
- G5-B：单独恢复 MDIO/PHY，读取 PHY ID 并确认 RTL8211F bind/link；不把 link up 当作 TX PASS。
- G6：首次 interface open/DMA ring/IRQ/NAPI 功能验证；满足条件后优先一帧完整 A→B→C→D。
- G7：独立对端 pcap 收到同一帧，核验 EtherType、MAC、run_id、sequence、length、digest，才是物理 TX PASS。

## 6. ABCD 检查频率（强制）

每个 G 阶段结束都记录一次 ABCD 可执行性；G1–G4 至少每隔一门复核一次，任何连续两门不可执行后下一门必须重新检查。目标 netdev 注册后检查 open/DMA 前置条件；interface open 与 DMA ring 准备完成时立即进行单帧测试，不等 IP/ARP/TCP/UDP。每新增 RX 或协议层后都发送同一格式回归帧。

ABCD 各边界必须关联同一 run_id/sequence/payload hash：
- A：AF_PACKET 原始帧提交；
- B：网络核心 skb / netdev queue；
- C：STMMAC stmmac_xmit()；
- D：DMA mapping（地址、长度、方向），随后关联 descriptor/OWN/completion/reclaim；
- E6：对端 pcap 重新计算 payload hash，物理 TX 最终验收。

## 7. 当前结论

G0 只允许进入 G2 实施计划评审，不允许自动启用驱动。G2 需要用户对 stock RK809 MFD probe 及其已知初始化写入单独授权后才可实施。本报告不构成授权，不修改任何设备或构建产物。
