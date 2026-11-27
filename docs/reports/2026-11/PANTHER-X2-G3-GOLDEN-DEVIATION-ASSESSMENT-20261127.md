# Panther X2 Project A — G3 截止点与黄金基线偏离程度评估（2026-11-27）

## 1. 结论

截至 G3-P，Linux 6.18.63 在 RK809 / MFD / regulator provider 软件链上的**实现偏离程度为低到中等**。已完成的黄金源码、配置、DTS 对照没有发现 G3 范围内足以解释 GMAC TX 故障的重大新增回归。

但运行态只验证到 RK809 regulator provider 绑定和 16 个 regulator 对象注册。IO-domain consumer、实际 rail enable/电压、GMAC/PHY、物理 TX 均未验证。因此不能将“G3 PASS”解释为供电链与黄金系统等价或网络链路已恢复。

本报告区分：
- **实现偏离**：源码、Kconfig、DTS、约束处理的版本差异；
- **运行偏离**：目标硬件上是否完成相同 provider/consumer、供电、MAC/PHY 行为。

## 2. 黄金基线证据强度

- 6.1.65：原版 Armbian 实机启动，GMAC 平台驱动绑定、RTL8211F、千兆全双工、DHCP、网关/外网 IPv4 与 DNS 均有实测；最终 config 与 built-in 对象已归档。其源码端点是高置信度 candidate，尚未与原始 Image 二进制绑定。
- 6.1.116：正常实机网络基线，PMIC/IRQ/GMAC/RTL8211F 运行证据已归档；真实最终 config 已恢复；固定源码 commit 已锁定。
- 两条黄金源码端点之间，`rk808.c`、`rk808-regulator.c`、`io-domain.c`、`dwmac-rk.c`、Panther board DTS、RK3566 SoC DTSI 对应文件均逐字节相同。6.1.65 源码身份限制仍然保留。
- 6.1.116 完整 Panther DTB 与 6.18.63 完整 Panther DTB SHA256 相同；6.1.65 原始 DTB 的 GMAC 核心字段已有直接解析，PMIC/IO-domain 子树的原始二进制完整重解析仍有证据限制。

## 3. 截至 G3 的逐层偏离矩阵

| 层 | 黄金基线 | 6.18.63 / G3 证据 | 偏离程度 |
|---|---|---|---|
| I2C / RK809 identity | 6.1.116 正常运行；6.1.65 有配置与实机基线 | G3 中 I2C parent `0-0020` 已绑定；此前只读 ID 为 0xED=0x80、0xEE=0x94 | 低；variant 选择机制不同 |
| MFD / IRQ | 两条黄金基线有 PMIC/IRQ child 运行证据 | 6.18 MFD、RTC、PWRKEY 已运行；24-line IRQ map、三组 status/mask/ACK 布局与 pre-init 表和黄金相同 | 低，存在 API/资源管理差异 |
| Regulator provider | 黄金 config/built-in 证据；两黄金 regulator driver 文件完全相同 | 6.18 RK809 provider platform driver 已绑定，16 个 provider-owned regulator objects 已注册 | 低到中；provider 成功，rail 状态未闭合 |
| Regulator core constraints | 黄金 core 与 DTS 为行为参照 | 6.18 的约束应用顺序/部分电压处理逻辑与 6.1.116 有差异；late unused cleanup 与黄金共有 | 中；需避免把对象注册当作实际 rail 电压 |
| IO-domain | 黄金源码与 DTS 已对照，黄金整机 Ethernet 成功 | G3 故意关闭 IO-domain；未运行 consumer / 未写 GRF | 未验证 |
| GMAC / PHY | 两条黄金基线均有千兆链路；6.1.65 还有 IPv4 端到端结果 | G3 故意关闭 GMAC1/MDIO/PHY | 未验证 |
| 真实 TX | 黄金网络通信成功，但并非本轮 G3 的对照帧 | G3 没有 netdev、PHY 或对端 pcap | 未验证 |

## 4. 已明确的源码/配置差异

### 4.1 MFD

- 6.1.116 通过读取 0xED/0xEE 并按 masked ID 选择 variant；6.18 通过 OF compatible 选择 RK809 variant，不在该 probe 路径重读 ID。此前 Panther 只读记录 0xED=0x80、0xEE=0x94，其中高 nibble 与 RK809 CHIP_NAME code 相符；低 nibble 是 reserved observed value，不称为 silicon revision。
- 6.1.116 使用 `regmap_add_irq_chip()` 并显式释放；6.18 使用 `devm_regmap_add_irq_chip()`。
- 两版 IRQ map、mask/status/ACK 布局和 RK817-family pre-init 表相同；没有发现 6.18 新增 pre-init 写入集合。
- PWRKEY MFD resource 顺序不同；6.18 顺序符合 consumer 的 FALL/RISE index 约定。此项不影响 Ethernet TX 主链。
- poweroff/restart handler 注册 API 不同；本轮未调用这些 handler。
- RK809 Datasheet Rev 2.5 已解释 0xFC RC/W1C 语义。mask registers 中 reserved RW 位由共用 24-line 实现写 mask=1 的规格边界仍保留，但它是黄金与 6.18 共用路径，不是新回归。

### 4.2 Regulator provider / core

- 6.1.65 与 6.1.116 的 `drivers/regulator/rk808-regulator.c` blob 完全相同。
- 6.18 RK809 descriptor/provider 路径已通过 G3-P：platform driver 明确绑定，16 个 provider-owned regulator objects 已注册。
- 6.18 regulator core 与 6.1.116 有约束应用顺序和部分电压处理逻辑差异；已审查的约 30 秒 unused-regulator late cleanup 则相同，不是 6.18 新增行为。
- `regulator-init-microvolt` 不由两版 `of_regulator.c` 解析；不能把 DTS 该属性当成已经执行的 PMIC 电压写入。
- DCDC initial-mode、ramp-delay、boot-on/always-on 与 suspend state 约束可能在 provider registration 阶段触发 PMIC 操作；G3-S 已列明相关副作用。
- G3 bootargs 中的 `regulator_ignore_unused` 是本次临时保护，用于跳过 late unused cleanup；它不抑制 provider probe 写入、不强制 enable，也不是黄金配置等价证明，不能未经分析带入最终系统。

### 4.3 DTS / board configuration

- 6.1.116 与 6.18.63 完整 Panther DTB 字节级相同。
- 6.1.65 candidate 与 6.1.116 Panther board DTS 文件 blob 相同；原始 6.1.65 PMIC/IO-domain DTB 子树仍有直接证据缺口。
- 6.18 的 RK809 regulator 子树与黄金候选 DTS 基本一致；已知属性写法差异为 vendor-prefixed `rockchip,system-power-controller` 与标准属性兼容写法。
- G3 DTB 是刻意隔离版：RK809 enabled；IO-domain、GMAC1/MDIO/PHY、eMMC、TF SDMMC0、SDIO、GPU、SARADC disabled。此隔离状态不等于黄金系统最终功能配置。

## 5. G3-P 实机结果及其严格边界

G3-P 运行于 Panther X2 / SU08G / Linux 6.18.63 / RAM-only initramfs：
- RK809 I2C parent `0-0020` 绑定 `rk8xx-i2c`；
- `rk808-regulator.3.auto` 明确出现 `driver -> .../drivers/rk808-regulator`；
- provider 目录下 16 个 regulator class objects 全部链接到该 provider；
- 无 TF/eMMC 持久文件系统挂载；无手工 I2C/PMIC 写入、无 suspend、无 eMMC/SN64G 操作。

**G3-P PASS 的准确含义：provider driver binding + 16 regulator object registration。**

未验证：
- 各 DCDC/LDO/SWITCH 的物理输出电压、电流或 enable state；
- 所有 global regulator IDs 与 RK809 descriptor 的完整 channel mapping；
- IO-domain consumer 获取 supply、实际电压读数和 PMU GRF selector 写入；
- GMAC/MDIO/PHY probe、link、netdev、DMA 或真实 TX。

runtime capture script 的 `[ : not found` 使脚本自动生成的 DTB/controller isolation、deferred list 和部分 debug 信息无效；隔离证据来自 G3-B artifact audit，而不是那些错误的运行时脚本判断。

## 6. 对故障定位的含义

1. G3 之前最明显的配置缺口——6.18 未启用 RK8xx MFD/regulator provider——已在 6.18.63 候选中补齐，并实机证明 provider 注册成功。
2. MFD IRQ/pre-init 核心机制与黄金基线共性很高；没有发现 G3 范围内新的、大规模 PMIC 初始化行为差异。
3. 因此，当前不应继续把“RK809 MFD/provider 根本不能工作”作为首要假设，也不应回头重复 G2/G3。
4. 仍不能排除 regulator constraints、SWITCH_REG1 实际 enable/输出、IO-domain selector、GMAC consumer enable 时序及后续 MAC/PHY/DMA 路径问题。
5. G4 必须先单独评估 IO-domain 的全部 9 个 supplies：按当前 DTS 完整 probe 预期有 14 次 PMU GRF regmap_write 调用，涉及 VSEL0/VSEL1/VSEL2；这不是单 rail/VCCIO5 单独测试。SWITCH_REG1 的 regulator framework 电压读数可能 fallback 到上游固定 3.3V，不能证明 SWITCH_REG1 实际输出。

## 7. 下一步与当前执行状态

- G3：按既定 provider 目标结项，不重复运行。
- G4-S：静态/黄金源码与 DTS 对照 PASS。
- G4-B：独立 build-only candidate 正在 Actions 中；当前 workflow run `45997129528` 的 G3 artifact/source/config 复核、Kconfig merge 均成功，Image 构建仍 in progress；最终 object/symbol/DTB audit 与 artifact upload 尚未完成。
- G4-P：HOLD / NOT AUTHORIZED。不得因为 G3-P PASS 自动启用 IO-domain 或触发 PMU GRF 写入。
- G5 GMAC/PHY 与 ABCD TX：保持后续门，不提前执行。

**最终判断：截至 G3，6.18.63 的 PMIC provider 主链与黄金基线的软件实现高度接近；剩余风险集中在 regulator 约束/实体 rail 状态、IO-domain consumer/GRF selector 与尚未恢复的 GMAC/PHY 运行链，而不是已观察到的 MFD/provider 基础绑定失败。**
