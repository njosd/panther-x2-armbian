# Panther X2 项目 A — 黄金基准 PMIC / Regulator 配置反向追踪计划与证据盘点（2026-11-26）

## 1. 本报告目的

纠正 G0 阶段对 3.3V rail 物理测量的优先级安排。Panther X2 已由两套正常软件基线在同一硬件上证明板载千兆 Ethernet 可工作。当前主要问题是 Linux 6.18 与黄金基准在软件配置、驱动实现、probe/初始化顺序及调用行为上的适配差异。

因此，**不应把重新证明 3.3V rail 存在或先寻找 PCB testpoint 作为网络 bring-up 的前置条件**。板级测量只在黄金基准软件反向追踪后，出现明确、无法用既有软件证据解释的物理异常假设时，才作为针对性补证。

本报告只建立证据盘点和下一步研究顺序，不启动设备、不改变配置、不加载驱动、不访问 PMIC/GRF、不测量电压、不发送网络帧。

## 2. 已确认的黄金基准证据

### 2.1 Linux 6.1.65：第一黄金基线

既有 R3 报告已从 Dropbox 原始 `kernel-config-evidence.zip` 解包并核验 `config-6.1.65-ophub` 与 `modules.builtin`：

| 项目 | 6.1.65 证据 |
|---|---|
| `CONFIG_I2C` | y |
| `CONFIG_I2C_RK3X` | y |
| `CONFIG_REGMAP_I2C` | y |
| `CONFIG_REGULATOR` | y |
| `CONFIG_MFD_RK808` | y |
| `CONFIG_REGULATOR_RK808` | y |
| built-in 对象 | `rk808.ko`、`rk808-regulator.ko`、`i2c-rk3x.ko`、`regmap-i2c.ko` |

这证明 6.1.65 的正常系统构建包含完整 RK809/RK808 MFD 与 regulator 驱动链。结合该版本已在 Panther X2 实机成功完成有线 Ethernet 功能，构成“该软件组合在该硬件上正常运行”的集成正向证据。

边界：目前归档证据明确覆盖最终配置与 built-in 对象；尚不能仅凭配置表推断每个 regulator 的具体运行时写入、实际电压或 probe 顺序。相关细节应从固定源码、DTB、启动日志和已有运行记录中恢复。

### 2.2 Linux 6.1.116：第二黄金行为参照

既有隐私脱敏基准记录 `evidence/network/panther-eth-baseline-redacted.txt` 记录：
- 运行内核为 `6.1.116-ophub`；
- `/boot/config-6.1.116-ophub` 存在；
- `/boot/System.map-6.1.116-ophub` 存在；
- GMAC1 probe 日志显示 clock input、TX delay 0x30、RX delay 0x10、RGMII；
- RTL8211F Gigabit Ethernet 在 PHY 地址 0 识别成功；
- `Link is Up - 1Gbps/Full`。

该证据确认 6.1.116 在 Panther X2 上的网络集成路径正常。下一步需要从已保存的 6.1.116 配置文件/备份资产中提取其 PMIC、regulator、IO-domain 配置和对象，不能将 6.1.65 配置直接假定为 6.1.116 配置。

## 3. 6.18.63 R1 已确认的差异

R1 最终 artifact 的 `.config`、`modules.builtin` 和模块归档已直接核验：
- I2C、I2C_RK3X、REGMAP_I2C、REGULATOR 均为 y；
- 新版 `MFD_RK8XX_I2C` 未启用；
- RK8xx MFD core、I2C transport 和 `REGULATOR_RK808` 均未构建；
- Panther DTB 仍保留 RK809 节点及 SWITCH_REG1 phandle，但 R1 未提供对应 provider；
- 这正是 R1/R3 中 IO-domain supplier deferred-probe 的一个已知原因。

这是一项确定的配置/对象差异，不等于已经证明它是最终 TX 故障的唯一根因；但它比“3.3V rail 可能不稳定”更直接、更值得先核查。

## 4. 必须按顺序完成的黄金反向追踪

### G0-P1：恢复 6.1.65 / 6.1.116 的 PMIC 配置与构建对象

逐项提取：
- 最终 `.config` 中 MFD、REGMAP、I2C、REGULATOR、IRQ、PINCTRL、IODOMAIN 相关配置；
- `modules.builtin`、`modules.order`、`System.map` 中实际对象/符号；
- 6.1.116 的 `/boot/config-6.1.116-ophub` 与对应模块清单；
- 若存在，6.1.116 原始 DTB/FDT 与运行时设备树；
- 现有启动日志中的 RK809、regulator、IO-domain、GMAC probe/deferred-probe 信息。

不能以 Kconfig default 或 DTS 存在节点代替最终配置/对象证据。若 6.1.116 原始配置无法恢复，标记 UNKNOWN，并说明最小补证，不推测其与 6.1.65 相同。

### G0-P2：黄金驱动源码与设备树反向对照

对 6.1.65、6.1.116 分别锁定实际可证实源码端点；对比：
- RK809 OF compatible 与 variant 匹配；
- I2C transport、regmap 配置、寄存器宽度/stride；
- MFD IRQ chip 的 IRQ 数量、mask/status/ack 映射；
- MFD probe pre-init 表和实际写入寄存器/bit；
- MFD child device 创建顺序；
- RK809 regulator descriptors、selector、电压范围、enable/mode ops；
- DTS 中每路 regulator 的 min/max、boot-on、always-on、初始电压/模式、supply；
- regulator core 注册/约束/late cleanup 对硬件写入的触发条件；
- Rockchip IO-domain consumer 的 supplier 获取、deferred-probe 与 GRF 写入；
- GMAC glue 获取 PHY supply、调用 enable/disable 的具体时机。

先确认 6.1.65 与 6.1.116 哪些行为一致、哪些不同，再判断哪些是正常系统共同依赖。不得把新版 driver 存在写操作直接归类为不可用；要逐寄存器与黄金实现比较其必要性、差异和副作用。

### G0-P3：对照 6.18.63 默认实现

把上述功能链映射到 6.18.63：
- 新旧 Kconfig 符号和对象组织变化；
- RK809 variant 是否仍采用 RK817 family pre-init/IRQ layout；
- pre-init 写入表相对黄金版本新增/删除/改变了什么；
- regulator descriptors/constraints 是否改变；
- IO-domain probe 及电压选择是否改变；
- GMAC PHY supply enable 与 powerup 顺序是否改变。

形成逐项矩阵：`黄金版本实际行为 → 6.18 默认行为 → 差异 → 可能影响 → 现有证据 → 最小验证`。

### G0-P4：决定是否需要任何硬件补证

只有出现以下情况之一，才提出最小硬件只读/功能验证：
- 黄金基准和 6.18 对同一 rail 的控制行为存在明确差异，且源码/日志无法解释；
- 6.18 driver 返回失败或 consumer deferred，且不能从 provider 配置解释；
- PHY/link 行为表明 rail/clock/reset 存在具体异常。

即使需要硬件补证，也优先复用黄金系统已有的启动日志、sysfs、regulator summary、clock summary、pinctrl 状态和可用寄存器只读证据；不预设需要外部测量。电压探测仅在有明确假设、测量点已可靠识别、软件证据不足时作为最后补充，且单独授权。

## 5. G0.2 既有 NO-GO 结论的修订边界

此前 G0.2 对 6.18 stock RK809 MFD/regulator 的写入副作用做了静态识别。这些调用路径真实存在，但“存在写入”并不足以证明其危险，也不足以与两套黄金基线的实际行为进行比较。

因此：
- 暂停把“stock MFD/regulator NO-GO”作为最终架构结论；
- 暂时维持“不未经授权启动/写入”的操作限制；
- 将决策状态改为 **HOLD：等待黄金驱动与配置反向追踪**；
- 不实现 fixed-regulator 替代路径，不以假定的 3.3V 替代真实 PMIC provider；
- 只有完成 G0-P1～P3 后，才根据黄金版本已验证行为决定 6.18 的最小适配方案。

## 6. G0.6 / G0.7 既有报告的处置

- G0.6 fixed-regulator 替代方案保留为历史静态可行性研究，不进入当前主路线，也不实现。
- G0.7 Panther X2 PCB/rail testpoint 公开资料检索保留为背景资料，不作为 G0 放行条件。
- 不要求用户提供原理图或 PCB 照片来继续当前软件差异研究。
- 若未来出现明确硬件假设，再决定是否需要相关板级资料。

## 7. ABCD 发送测试的阶段要求

ABCD 设计继续保留，不因 PMIC 研究而延迟其准备：
- G0-P1～P3：不具备目标 netdev，ABCD 记 NOT EXECUTABLE；可准备 sender、trace 配置和对端 pcap 夹具。
- 每完成一至两层软件/硬件激活审查，就重新检查目标 netdev/open/DMA 条件。
- 一旦目标网卡注册、open 与 DMA 前置条件满足，优先做一帧 A→B→C→D；不得等到 ARP/IP/TCP/UDP 完成。
- 若条件尚未满足，明确缺少哪个前置，不伪造 PASS，也不越级 open。
- 对端 pcap 是物理 TX 最终证据。

## 8. 本轮结论

当前优先级已修正为 **Golden-first software reverse audit**：
1. 恢复 6.1.65 与 6.1.116 的最终配置/对象；
2. 复原两套黄金基准 RK809/MFD/regulator/IO-domain 的实际软件行为；
3. 与 6.18.63 默认实现逐项对照；
4. 依据真实差异决定最小验证与适配；
5. 在具备 netdev/open/DMA 条件的最早阶段做 ABCD 单帧物理发送验证。

本报告没有执行设备操作、PMIC/GRF 访问、电压测量、镜像构建或网络发送。


## 9. 已有证据复用与当前精确进度（2026-11-27）

本节以已归档报告为准，不重新执行已经完成的审计：

| 子项 | 现有证据 | 当前状态/动作 |
|---|---|---|
| 6.1.65 最终 config / built-in | `PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md`、`PANTHER-X2-B2-1-R3-RK809-I2C-REGULATOR-PREFLIGHT-20261126.md` | 已确认 MFD_RK808=y、REGULATOR_RK808=y，rk808/rk808-regulator built-in；不重复提取 |
| 6.1.116 最终 config | `PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md` | 真实 7,677 符号配置已从归档提取，和官方 config-6.1 模板零差异；不重复提取 |
| 6.1.116 PMIC 运行证据 | `evidence/network/panther-eth-baseline-redacted.txt`、`PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md` | 正常启动 IRQ 记录含 rk817 / rk805_pwrkey；GMAC/RTL8211F 1Gbps Full 已有运行证据 |
| 6.1.65 ↔ 6.1.116 MFD/regulator/IO-domain/glue 源码 | `PANTHER-X2-G0-GOLDEN-65-116-PMIC-PHY-SOURCE-COMMONALITY-20261127.md` | rk808.c、rk808-regulator.c、io-domain.c、dwmac-rk.c 与 Panther board DTS 完全相同；regulator core 四个关键函数相同 |
| 黄金版本 ↔ 6.18 RK809 pre-init / IRQ / SWITCH_REG1 | R3 报告 §21–§26 | 已完成静态对照；pre-init 表相同，IRQ mapping 相同，SWITCH_REG1 descriptor 相同；保留源码身份和 datasheet 边界 |
| regulator late cleanup / PHY supply consumer | R3 报告 §25–§26 | 已完成对照；约 30 秒 cleanup 是黄金与 6.18 共有行为；6.18 glue 错误传播更严格 |
| 黄金 DTB binary | 6.1.65 原始 DTB hash 已归档；6.1.116 DTB 归档 SHA 已归档 | **尚未完成原始二进制提取和 PMIC/IO-domain 子树三版本结构化 diff；这是当前唯一软件资料补齐项** |

### 当前下一步（唯一）

提取并解析已归档 6.1.65 与 6.1.116 原始 Panther DTB，与 6.18.63 R1 实际 DTB 比较以下范围：RK809 IRQ/system-power-controller 属性、完整 regulator 子树约束、IO-domain supplies、GMAC1 phy-supply 和相关 phandle。无需重新提取完整镜像，不访问 SN64G，不写 eMMC/TF，不启动设备。三份 DTB 关键属性一致则关闭 DTS 变量；有差异则只追踪具体差异。

G0-P1 配置恢复、G0-P2 黄金 PMIC 驱动行为、G0-P3 6.18 对照均已完成或已有报告覆盖；不得重复这些审计。G0-P4 最终准入决策待 DTB binary diff 后再做。
