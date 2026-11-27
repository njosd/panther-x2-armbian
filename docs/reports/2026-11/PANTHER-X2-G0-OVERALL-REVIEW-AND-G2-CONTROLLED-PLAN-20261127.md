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
- RK809 0xEE=0x94 的高 nibble 0x9 与 CHIP_NAME code 相符。低 nibble 0x4：Rev 1.01 曾定义为 CHIP_VER code；Rev 1.7 至 Rev 2.5 则改标 RESV、reset default=0x2。不能仅凭 0x94 宣称当前硅片 revision 4；手册定义变更和当前 reserved 非默认值原因仍需 Rockchip 说明。
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


## 9. 2026-11-27 G2-PROBE 追加副作用审计（状态优先级更新）

新增静态报告：`PANTHER-X2-G2-PROBE-SIDE-EFFECT-AND-RTC-CHILD-REVIEW-20261127.md`。

G2-B 最终 config 已从 artifact 实际核验：`RTC_DRV_RK808` 未启用。6.18 RK809 MFD pre-init 却会将 RTC_STOP 置位；只启用 RK809 DT 节点而不启用 RTC child，会使 RTC 不执行恢复启动操作。若启用 RTC child，则增加 RTC_CTRL 0x0D 清 STOP/设置 READSEL、RTC_STATUS 0x0E W1C 清状态，以及 RTC alarm IRQ unmask/ACK 写入。与此同时，RK809 Rev 2.4/2.5 对 0xFA/0xFC reserved W1C/RC 位的定义与 Linux RK817 24-bit mapping 尚未解释；不能通过额外读取 0xFC 代替芯片 errata 证据。pre-init 中途失败也没有 PMIC register rollback；sys-off/shutdown/suspend/resume 存在 0xF4 状态写入。

因此，原第 4 节的 G2 受控计划只能视为历史方案草案，不能直接执行。**当前 G2-PROBE 继续 HOLD / NOT AUTHORIZED**。G2-B build-only 与 G2 runtime PREPARE-ONLY PASS 不构成 probe 授权，也不允许直接把 runtime DTB 中 RK809 改为 enabled。解除 HOLD 前须完成实际芯片版本 register-map/errata 证据、RTC child 取舍与写入审查、失败/退出回退方案，并另行取得明确授权。

## 8. 2026-11-27 G2 静态差异复核修订

G2-S 源码对照已完成，详细记录见 `PANTHER-X2-G2-RK809-MFD-GATE-REASSESSMENT-20261127.md` §8。6.1.116 与 6.18.63 的 RK817 IRQ chip 布局、24-bit mapping、pre-init 表、MFD cell 集合相同；没有发现 6.18 新增 RK809 pre-init 写入。黄金 6.1.116 IRQ 38/39 与 RTC 子 IRQ 的注册记录是正向运行证据，但中断计数为 0，不证明物理按键事件/所有 ACK 位状态。

重要新差异：6.1.116 的 pwrkey resource 数组顺序为 RISE/FALL，6.18 为 FALL/RISE；共同 pwrkey consumer 驱动固定按 index0=FALL、index1=RISE 取 IRQ。6.18 顺序符合 consumer 约定；保留新顺序，不回退。6.18 I2C probe 通过 OF compatible 选择 RK809，不像旧驱动在 probe 中重新读取 0xED/0xEE；但 R1 已有独立只读 ID 实测可补充身份依据。

因此，G2 stock probe 不再因“IRQ mapping 可能是 6.18 regression”而被否决；但 probe 会执行与黄金相同的 pre-init 写入及 regmap IRQ 初始化，仍属 PMIC 写操作，须单独授权。当前下一步先做 G2-B build-only：构建启用 MFD_RK8XX_I2C（可选 INPUT_RK805_PWRKEY）、不启用 REGULATOR_RK808，并保持 RK809 节点 disabled 的隔离 DTB。只验证配置闭包、编译链接和产物；不 probe、不访问硬件。完成后再提交独立 G2-PROBE 授权计划。

## 10. 2026-11-27 G2 准入复核更新：IRQ 手册语义已收敛，转入 stock runtime 候选准备

本节优先级高于本报告第 3、4、7、8、9 节中关于“必须等待 Rockchip 解释 0xFC RC/W1C 才能准备 G2”的旧表述。详细源码与寄存器访问证据见 `PANTHER-X2-G2-PROBE-SIDE-EFFECT-AND-RTC-CHILD-REVIEW-20261127.md` §10。

### 10.1 已收敛的结论
- RK809 Rev 2.5 明确将 0xFC bit[7:6] 定义为 RC、bit[5:2] 与 bit[1:0] 定义为 W1C；Linux regmap-irq 初始化读取 0xFC 后的 RC 清除行为是手册已定义语义，不再作为未知副作用或 G2 build 准入阻塞。
- Linux 6.18.63 的 RK809/RK817 共用 24-line IRQ map、mask/status/ACK 初始化顺序与两条黄金版本相同。mask registers 的 reserved RW 位被整字节 mask=1 的共享实现规格边界继续记录，不修改 stock IRQ map，也不将其定性为已证实硬件故障。
- 0xEE=0x94 解释为 CHIP_NAME 高 nibble=9、低 nibble reserved observed value=4；低 nibble 不是 silicon revision 4。该值不阻塞候选构建。
- RTC child 必须纳入候选配置，以避免 MFD pre-init 设置 RTC_STOP 后没有标准 RTC child 清除；PWRKEY child 同样按黄金运行路径纳入。regulator provider 仍留给 G3。

### 10.2 新的 G2 顺序
1. 保留已通过的 G2-B build-only artifact，不重做、不覆盖。
2. 以同一 Linux 6.18.63 commit 和 R1 frozen config 为基线，另建 G2 stock-runtime candidate build：启用 RK8xx MFD/I2C、RTC、PWRKEY；不启用 regulator provider；DTB 中启用 RK809，但 GMAC1/MDIO/RTL8211F 继续 disabled。
3. 仅在 GitHub Actions runner 编译、链接、封装候选 Image/DTB/initramfs，核对最终 config、built-in 对象、DTB 状态和所有 SHA256。此举不接触 Panther X2。
4. 生成独立 G2-PROBE 操作清单：列明 MFD pre-init、IRQ mask/status/ACK、RTC 0x0D/0x0E 与 alarm IRQ unmask、PWRKEY IRQ 请求、system-off handler 注册；明确失败退出与避免 shutdown/reboot/suspend 的约束。
5. 候选资产冻结后，再单独申请实机 probe 授权。未授权前不得写 SU08G、启动候选镜像或访问 PMIC。

### 10.3 不变的阶段边界
- G2 只验证 RK809 MFD/regmap/IRQ/RTC/PWRKEY；不启用 regulator provider、不恢复 IO-domain consumer 链以外的 GMAC/MDIO/PHY，不执行 TX。
- G3 才引入 RK809 regulator provider；G4 核对 IO-domain；G5 恢复 GMAC/PHY；G6/G7 完成 descriptor/DMA 与真实对端 pcap 验收。
- 当前 ABCD = NOT EXECUTABLE；不因本次文档修订声称硬件通过。
- 本轮只更新源码证据与准入文件，没有启动设备、没有访问 PMIC、没有写 TF/eMMC。

状态更新：G2-S PASS；G2-B BUILD PASS（历史 artifact 保留）；G2 stock-runtime candidate = PREPARATION AUTHORIZED（build-only only）；G2-PROBE = HOLD / NOT AUTHORIZED。
## 11. G2 stock-runtime candidate 构建工作流已准备（尚未执行）

本轮在仓库新增：
- `scripts/panther-x2-g2/g2-stock-runtime.fragment`：在冻结 R1 config 上启用 `CONFIG_I2C=y`、`CONFIG_MFD_RK8XX_I2C=y`、`CONFIG_RTC_DRV_RK808=y`、`CONFIG_INPUT_RK805_PWRKEY=y`；明确不启用 `CONFIG_REGULATOR_RK808`。
- `.github/workflows/build-panther-x2-g2-stock-runtime.yml`：独立 build-only workflow，复用 R1 成功 artifact 和固定 6.18.63 source/compat patch；仅在 Actions runner 编译 Image，输出 PMIC node `okay`、GMAC1/MDIO/PHY `disabled` 的候选 DTB；增加 MFD core/I2C、RTC、PWRKEY object 与 vmlinux symbol 检查，并保留对象哈希和配置/DTB 清单。

该 workflow 尚未 dispatch、尚未产生新的 build artifact；当前只完成仓库文件准备与静态核对。它不会写实体 TF/eMMC，也不会连接 Panther X2。其候选 DTB 启用 RK809，只有在后续明确授权后才可用于实机启动；目前绝不能刷写或启动。

最新仓库提交：fragment `4d76f055fb3b9b5829d293d0bdb5f9fb86459889`；workflow 初建 `fbc778be75b0848590768845cb8813e89b82e4dd`，后续对象检查与 shell continuation 修订提交 `8c57039a1703a414e6bdd06511aa332549b64451`、`51d15c4f7d469b90eb44c35b740a01c740a3fbda`、`40f460b510876314e6e39589e9f3724e1d5d8f56`。
## 12. G2 stock-runtime workflow 二次审计与修正（2026-11-27）

复核上一版新 workflow 后，发现它存在确定的配置依赖缺失，不能直接 dispatch：

1. `RTC_DRV_RK808` 位于 `if RTC_CLASS` Kconfig 条件块中；只设置 `RTC_DRV_RK808=y` 而未显式设置 `RTC_CLASS=y`，不能保证 RTC driver 被纳入最终配置/编译。
2. `INPUT_RK805_PWRKEY` 位于 `if INPUT` 与 `if INPUT_MISC` 层级下；仅设置 PWRKEY 子项不保证 `INPUT`、`INPUT_MISC` 已启用。
3. 即使 MFD/RTC/PWRKEY 对象编译成功，也不足以证明 PMIC 可被 I2C 和 IRQ 路径实际发现。G2 必须同时核验 RK3x I2C controller、Rockchip GPIO、pinctrl、IRQ domain，以及 RTC class interface 的 built-in 依赖闭包。
4. `RTC_CLASS=y` 会使 `RTC_HCTOSYS` 和 `RTC_SYSTOHC` 默认开启；前者可能在启动时用 PMIC RTC 改写系统时钟，后者在时间同步条件满足时可能写回 PMIC RTC。为隔离 G2 probe 行为，候选明确关闭二者，并在 build/package 两侧都做否定断言。
5. 原工作流失败时仍可能上传不完整的正式候选 artifact，且 cache save 的条件早于对象/产物完整性审查。现改为只有完整 build 与依赖审计通过才上传正式候选；失败时仅上传诊断日志；cache 仅在 Image build 成功后保存。
6. 原始候选打包工作流不能直接复用：它固定指向旧 G2-B artifact（RK809 DT node disabled），并有跨 step shell 变量作用域问题。新建独立 `package-panther-x2-g2-stock-runtime.yml`，输入新的 G2 build run ID，重新验证 artifact 内部 SHA256、最终 Kconfig、PMIC 节点状态和依赖对象，并通过 `$GITHUB_ENV` 将动态 Image/config/DTB hash 传递到后续 step。

修正后的 G2 fragment 明确包含 `I2C=y`、`MFD_RK8XX_I2C=y`、`RTC_CLASS=y`、`RTC_DRV_RK808=y`、`INPUT=y`、`INPUT_MISC=y`、`INPUT_EVDEV=y`、`INPUT_RK805_PWRKEY=y`；`RTC_HCTOSYS`、`RTC_SYSTOHC`、`REGULATOR_RK808` 保持关闭。

新增对象检查覆盖 `i2c-rk3x.o`、`gpio-rockchip.o`、`pinctrl-rockchip.o`、RK8xx MFD core/I2C、RTC 和 PWRKEY，并要求关键 probe 符号出现在对象及最终 vmlinux 中。对象哈希清单命名为 `G2-PMIC-DEPENDENCY-OBJECTS-SHA256.txt`。运行时 init 脚本增加 `/sys/class/rtc`、`/sys/class/input`、I2C devices 的只读观察。

当前状态：workflow 与 package workflow 已修订并完成静态复核；**尚未 dispatch、尚无新构建 artifact、尚未写 TF/eMMC、尚未启动 Panther X2、尚未执行 PMIC probe**。G2-PROBE 仍 HOLD / NOT AUTHORIZED。