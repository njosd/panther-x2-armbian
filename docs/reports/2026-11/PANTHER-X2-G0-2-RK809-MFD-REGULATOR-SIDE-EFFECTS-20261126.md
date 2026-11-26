# Panther X2 项目 A — G0.2 RK809 MFD / Regulator 副作用与准入决策（2026-11-26）

- 状态：**G0.2 静态审计完成；stock RK8xx MFD + RK809 regulator 路径 NO-GO（当前安全边界下不放行）**。
- 性质：冻结源码与已归档证据的只读复核；没有访问设备、执行 I2C/PMIC 事务、启用驱动、写寄存器或修改配置。
- 固定目标源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。
- 黄金对照：6.1.65 高置信度候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`；源码来源仍未与原始 Image 二进制绑定，按候选证据标注。
- 复用报告：R3 §7、§11、§18–§26；G0.1 provider/consumer 矩阵；R2–R7 gated acceptance matrix。没有重跑已完成的寄存器只读测试或四版本审计。

## 1. 现有只读证据（不重复测试）

- I2C0 controller 已绑定 rk3x-i2c，i2c-dev adapter 89:0 已注册。
- RK809 地址 0x20 指定 ID 寄存器读取结果为 0xED=0x80、0xEE=0x94，Linux masked identity 判定为 RK809 ID 0x8094。
- 全位 RO 状态寄存器 0xF0=0xC2、0xF6=0x00 已各完成一次 I2C_RDWR 只读事务。
- 这些读数不提供 SWITCH_REG1 输出电压遥测，不证明 rail 电压、纹波、负载能力或 PHY 供电。
- 现有安全读取白名单仅确认上述 0xED、0xEE、0xF0、0xF6；本轮没有扩大硬件访问范围。

## 2. MFD probe 的确定执行链与写入集合

冻结 6.18.63 源码的 `rk8xx_i2c_probe()` 通过 OF compatible 选择 RK809 variant，建立 I2C regmap 后调用 `rk8xx_probe()`。该 I2C OF 路径不是先读芯片 ID 再确认 variant；6.1.65 候选源码则有 0xED/0xEE ID 读取与 mask 判定。当前实测 ID 与 RK809 compatible 相符，但这不消除 OF match 的信任边界。

RK809 在 6.18 复用 RK817 IRQ、pre-init 与 MFD cell 集合。probe 顺序为：

1. 选择 `rk817_irq_chip` 与完整 `rk817_pre_init_reg[]`；
2. 要求存在 IRQ；
3. `devm_regmap_add_irq_chip()` 初始化中断控制器；
4. 遍历 pre-init 表并执行 `regmap_update_bits()`；
5. 创建整组 MFD 子设备；
6. 若 DT 有 system-power-controller 属性，注册 poweroff/restart handler。

### 2.1 IRQ mask / ACK 写入

- IRQ chip：24 IRQ、3 组寄存器、stride 2；status/ack base 0xF8，mask base 0xF9，`init_ack_masked=true`。
- Linux 初始化构造的默认 mask 为每组 0xFF，预期更新 mask registers 0xF9、0xFB、0xFD。
- 初始化读取 status 0xF8、0xFA、0xFC；若状态非零，对相应 ACK/status register 写回 `status & mask`。不是无条件写 0xFF，但可能清除已锁存事件。
- RK809 Datasheet Rev 2.4 对 0xFA bit2–7、0xFC bit0–1 标为 W1C reserved，0xFC bit6–7 标为 RC reserved；Linux 24-bit RK817 mapping 却为这些位定义 IRQ。
- 6.1.65 候选源码已使用相同 24-bit mapping、默认 mask 和 ACK 策略。因此这是跨版本历史兼容疑点，不是已证实的 6.18 regression；仍未证明当前 0x8094 芯片版本对这些保留位的真实语义。

**判定：** 0xF8–0xFD 不能列入当前允许访问或允许自动写入白名单。没有额外官方 silicon/register-map 证据前，MFD IRQ 初始化不可放行。

### 2.2 RK817-family pre-init

6.1.65 候选与 6.18.63 的 `rk817_pre_init_reg[]` 完整数组逐字节一致。关键范围：

| 地址/范围 | 用途 | 初始化行为 | 当前审查 |
|---|---|---|---|
| 0x0D | RTC_CTRL | RTC_STOP 位设置 | 需按 RK809 RTC 语义审查；属于非网络功能 |
| 0x12–0x4F 中表列 codec registers | DTOP、AREF、ADC/DAC、AMIC/DMIC、耳机、Class-D、APLL、DI2S | 多数使用 MASK_ALL 整字节写入固定值 | 与本项目网络目标无关；0x16 bitfield 未文档化，0x19/0x2E 在公开 Rev 1.8/2.4 register summary 未列出 |
| 0xFE | GPIO_INT_CFG | INT polarity bit1 写低有效 | 需确认板级 PMIC IRQ 极性及连接；不可只凭驱动默认值推断 |
| 0xF2（RK817_SYS_CFG(1)） | 热告警/关断阈值 | 设置 HOTDIE=105°C、TSD=140°C 对应字段 | 可能影响 PMIC 热保护策略，需与当前芯片/板级要求核对 |

pre-init 不包含直接切换 SWITCH_REG1 enable/selector 的表项；但不能据此称整个 MFD probe 无副作用。codec 表写入仍会发生，即使 codec 子驱动不加载。

### 2.3 MFD 子设备及生命周期动作

RK809/RK817 cell 列表会同时创建 clkout、regulator、pwrkey、RTC、codec、charger 子设备。关闭 codec 子驱动并不能跳过 MFD core 中已先执行的 codec pre-init。

system-power-controller handler 注册本身不会立即关机/重启；但调用 poweroff/restart 会更新 SYS_CFG(3)=0xF4 的 DEV_OFF/DEV_RST 位。shutdown、suspend、resume 路径也会更新 SYS_CFG(3) 的 SLPPIN 功能字段。首次硬件实验若未来获准，必须禁止 suspend/resume、poweroff/restart，并单独审查安全退出方式；不能把普通退出、关机或重启视为无副作用。

## 3. Regulator provider 注册范围与自动副作用

`rk808_regulator_probe()` 对 RK809 选择完整 `rk809_reg[]` 并循环注册全部 descriptor，不是只注册 SWITCH_REG1。

- 全部 DCDC、LDO、SWITCH regulator 都会进入 regulator core。
- regulator core 的 `set_machine_constraints()` 可按 DTS 约束调用 set_voltage、set_current_limit、set_mode、设置 suspend state、ramp delay、pull-down、soft-start 等 ops；因此“注册 descriptor”并不保证只读。
- Panther DTS 对多路 rail 设置 always-on/boot-on、initial mode、suspend state 等约束。其注册动作必须逐 rail 与具体 ops/寄存器位对应，不能笼统假定不会写入。
- SWITCH_REG1 descriptor 对应 supply_name vcc9，使用 RK817_POWER_EN_REG(3) 的 bit2 enable；没有 voltage selector/set_voltage 操作。Panther GMAC1 phy-supply 指向它，但 R1 的 GMAC1 节点 disabled。
- SWITCH_REG1 本身没有 regulator-always-on、regulator-boot-on 或初始电压约束。provider 注册不等于 enable，也不等于实际 3.3V 存在。
- DT populated 系统默认 full constraints。约 30 秒后 regulator core 先 resolve pending supplies，再对无 always_on、无 use_count、硬件状态读为 enabled 且可控状态的 regulator 执行 late cleanup disable。此行为在 6.1.65 候选与 6.18.63 都存在，不是 6.18 新增。若 GMAC consumer 未及时取得并 enable SWITCH_REG1，它可能被清理关闭；这属于潜在风险，不是已观察事实。
- 不允许为了避免 cleanup 而擅自添加 always-on 或使用 regulator_ignore_unused 作为正式修复；这会改变原板约束并掩盖 consumer 绑定问题。

## 4. 6.1.65 黄金基线对照

| 项目 | 6.1.65 高置信度候选 | 6.18.63 固定源码 | 结论 |
|---|---|---|---|
| RK809 variant 识别 | 读取 0xED/0xEE 并 mask | OF match data 选择 variant，不在该 probe 路径重读 ID | 有实现差异；实测 ID 与 RK809 compatible 相符 |
| IRQ mapping | 复用 RK817 24-bit IRQ table | 相同 | 非 6.18 新回归；datasheet 保留位问题仍存在 |
| pre-init 数组 | RK817-family 完整表 | 逐字节相同 | 历史共同写入，不代表当前 silicon 适用性已证明 |
| SWITCH_REG1 descriptor | enable register/mask/value 相同 | 相同 | 未发现该 rail 控制位的版本差异 |
| regulator late cleanup | full constraints、约 30 秒 delayed cleanup | 相同 | 非 6.18 regression |
| PHY supply consumer | Rockchip glue 获取 phy regulator 并 enable；旧 helper 对 enable 错误处理可能吞错 | 6.18 返回并传播 regulator_enable 错误 | 6.18 错误传播更严格，不回退 |

6.1.65 源码仍为候选端点而非 Image 二进制绑定。原版 6.1.65 Panther X2 实机网络成功是整机正向行为证据，不等于上述 PMIC 每个寄存器写入都独立验证安全。

## 5. G0.2 准入决策

### 5.1 当前明确禁止

在当前项目授权和证据条件下，不放行 stock RK809 MFD probe，也不放行 stock RK809 regulator provider probe。原因：

1. MFD 无现成“只注册网络所需 rail”的隔离阶段；IRQ mask/ACK 与整组 pre-init 写入发生在创建 regulator 子设备之前。
2. IRQ mapping 与公开 RK809 Rev 2.4 对若干 reserved bits 的定义存在未解决差异。
3. pre-init 包含大量与网络无关的 codec 写入，其中部分寄存器没有公开完整 bitfield 语义。
4. regulator probe 注册全部 rail，可能根据 DTS constraints 自动写入多类 PMIC 配置；SWITCH_REG1 还存在 delayed cleanup 风险。
5. 尚无安全的电源/PMIC 回退方案，也没有完成原始 6.1.65 DTB 的 PMIC 子树二进制对照。

### 5.2 当前只读白名单

仅引用已完成的读取，不新增事务：

- 0xED、0xEE：RK809 identity；已实测 0x8094。
- 0xF0：全位 RO PMIC_SYS_STS；已实测 0xC2。
- 0xF6：全位 RO PMIC_OFF_SOURCE；已实测 0x00。

明确不扩展到 0xF5、0xF8–0xFD、0xFE 或其他配置寄存器。此前对 0xED/0xEE/0xF0/0xF6 的授权不延伸到其他寄存器，也不授权驱动 probe。

### 5.3 后续可研究的替代路径（仅设计，不实现）

若项目后续确实必须验证 SWITCH_REG1，可先静态设计一个最小化、专用测试 provider/临时驱动方案，评估能否避开 RK809 stock MFD 的 codec pre-init 与不确定 IRQ ACK，同时仅观察既有 rail 状态。任何主动 enable/disable 仍须单独评估当前 enable bit、上电状态、外部实测电压、消费者关系、失败回滚及电源影响，并取得单独授权。不得直接编写/加载该驱动作为本轮后续动作。

## 6. 结论与下一步

**G0.2 结论：stock MFD/regulator 在当前安全边界下 NO-GO；不是硬件 FAIL，也不是 6.18 网络功能 FAIL。** G0.2 已完成风险识别和当前不放行决策；“允许写入白名单”为空，只有已完成的四个只读寄存器可引用。

下一项进入 **G0.3：只读归并 IO-domain supplier/deferred-probe 证据**，确认 R1 各 consumer 的 defer 日志、provider 缺失关系、重试/最终绑定状态证据缺口及 bank/rail 映射。不得为了消除 defer 启用 RK809 MFD/regulator 或写 GRF。

本报告没有启动 Panther X2、没有访问 PMIC、没有读取 IRQ registers、没有写入 PMIC/GRF、没有启用任何驱动、没有改动设备配置或存储介质。
