# Panther X2 项目 A — G0.6 非写入型 Fixed-Regulator Provider 替代路径可行性（2026-11-26）

- 状态：**静态可行性成立（CONDITIONAL）；未批准实现或启动。**
- 目的：在 stock RK809 MFD/regulator 当前 NO-GO 的前提下，评估能否仅把“已由硬件上电并经外部测量确认的 rail”映射成 Linux fixed-regulator provider，从而隔离 PMIC MFD 写入副作用，继续验证 IO-domain/MAC/PHY 软件路径。
- 范围：固定 6.18.63 源码、R1 实际构建 artifact、Panther DTS 与 RK3568 官方 Hardware Design Guide；只读分析。
- 未执行：没有修改 DTS/config、没有构建新 DTB/kernel、没有测量电压、没有启动设备、没有写 PMIC/GRF、没有恢复 GMAC、没有发包。

## 1. 关键前提：固定 regulator 驱动已在 R1 实际构建中

从已下载并核验的 R1 artifact `b2-1-r1-network-core`（ID 15023630465）直接检查：
- `CONFIG_REGULATOR=y`
- `CONFIG_REGULATOR_FIXED_VOLTAGE=y`
- `System.map` 存在 built-in `reg_fixed_voltage_probe` 与 `fixed_voltage_ops`。

这说明 R1 的 6.18.63 构建已包含 fixed-voltage provider，不需要为该驱动新增内核配置。未来 R7 最终配置仍须重新核验，不以 R1 artifact 代替目标 build。

## 2. Fixed-regulator 无 GPIO、无控制 ops 时的实际行为

固定源码 `drivers/regulator/fixed.c`：
- 普通 fixed-voltage provider 使用空的 `fixed_voltage_ops`（无 enable、disable、is_enabled、set_voltage ops）；
- `of_get_fixed_voltage_config()` 从 DT 读取固定 min/max 电压，设置 `fixed_uV`，并令 `apply_uV=0`；
- 没有 enable GPIO 时，不存在 PMIC/I2C/GRF 写操作。

固定源码 `drivers/regulator/core.c`：
- 若 regulator 没有 enable GPIO、没有 `ops->enable` 且没有上游 supply，`set_machine_constraints()` 会把该 regulator 标记为 `always_on`；
- 没有 `ops->is_enabled` 时，core 的 `_regulator_is_enabled()` 返回 1；
- consumer 调用 `regulator_enable()` 时，core 认为 rail 已经 enabled，不会进入需要硬件 enable op 的路径；`regulator_disable()` 也不会关闭 always-on rail；
- `regulator_get_voltage()` 从 fixed_uV 返回固定值。

因此它可以作为**已经由硬件供电的 rail 的软件描述符**，不会主动打开/关闭 PMIC rail，也不会写 PMIC 寄存器。

重要限制：这不是电源开关，也不会产生 3.3V。若 rail 实际关闭、欠压或不稳定，fixed provider 仍会向 consumer 报告 3.3V；这种情况会造成软件描述与物理硬件不一致，必须禁止使用。只有外部测量先证明 rail 实际稳定，才可考虑该路径。

## 3. 最小测试依赖映射

Panther DTS 当前拓扑：
- `pmuio1-supply`、`pmuio2-supply` → `vcc3v3_pmu`（RK809 LDO_REG6，DTS 3.3V、always-on、boot-on）；
- `vccio5-supply` → `vcc_3v3`（RK809 SWITCH_REG1，DTS 未设置 always-on/boot-on）；
- GMAC1 `phy-supply` → 同一个 `vcc_3v3`；
- GMAC1 M0 pins 使用 VCCIO5；PMUIO2 包含 UART2 M0 与 I2C0 pins。Rockchip RK3568 Hardware Design Guide Rev V1.2 分别明确 GMAC1 M0 属 VCCIO5、UART2 M0/I2C0 属 PMUIO2。

建议的测试-only provider 设计（尚未实施）：

| 测试 provider | 固定电压 | 仅替代的供电属性 | 用途 |
|---|---:|---|---|
| `vcc3v3_pmu_observed` | 3.3V | `pmuio1-supply`、`pmuio2-supply` | PMUIO1/PMUIO2 软件电压描述；PMUIO2 会按 3.3V 写 PMU GRF VSEL2，保持 UART2 M0/I2C0 IO domain 与已测 rail 一致 |
| `vcc_3v3_observed` | 3.3V | `vccio5-supply`、GMAC1 `phy-supply` | VCCIO5 selector 与 PHY supply 共用同一已测 3.3V rail |

`pmu_io_domains` 的其他 supply properties（vccio1、vccio2、vccio3、vccio4、vccio6、vccio7）若仍指向未注册的 RK809 regulators，会在 probe 中返回 `-EPROBE_DEFER` 并阻止整个 IO-domain probe。测试 DTB 必须对这些非目标域做明确处理：要么移除属性让 `devm_regulator_get_optional()` 返回 `-ENODEV` 并跳过，要么在确认实际电压后提供对应 provider。项目 A 首轮优先只管理 PMUIO1/2 与 VCCIO5；其他 domain 必须保持隔离，且先确认没有任何允许运行的设备依赖它们。

该映射的目标不是模拟完整 RK809，而是仅为当前启动控制台/I2C0 和 GMAC1 M0 提供准确的软件电压描述。

## 4. IO-domain 写入仍然存在，不能称为全只读

即使使用 fixed-regulator，不加载 RK809 MFD/regulator：
- PMUIO1 index0：读取固定 3.3V，但 RK3568 driver 对该 index 不写 selector；
- PMUIO2 index1：对 PMU GRF `VSEL2=0x0148` 写 high-word mask/value；3.3V 时分别写 `0x00020000` 与 `0x00200020`；
- VCCIO5 index6：对 PMU GRF `VSEL0=0x0140` 写 `0x00200000`，对 `VSEL1=0x0144` 写 `0x00200020`。

这仍是硬件状态写入。fixed-regulator 只避免 PMIC 写入；它不避免 IO-domain driver 写 GRF。未来必须先测量并确认 rail，再单独授权 IO-domain consumer probe；不能在当前 G0 研究阶段执行。

## 5. 物理前置条件与 NO-GO 情况

需要通过 Panther X2 板级原理图/PCB netlist 或已确认 testpoint，分别找到并测量：
1. `VCC3V3_PMU`：确认 3.3V 稳定，供 PMUIO1/PMUIO2；
2. `VCC_3V3` / RK809 SWITCH_REG1 输出：确认 3.3V 稳定，供 VCCIO5 与 RTL8211F PHY。

测量必须记录空载/当前运行负载、稳定性、测试点和地参考。当前尚未取得 Panther X2 专用的、可核验的这两个 rail 测试点位置；不得把其他 RK3566 开发板的原理图、电容位置或测试点套用到 Panther X2。

以下任一情况即 NO-GO：
- 无法确认板上 rail/testpoint；
- rail 实测不是 3.3V、未上电、波动或负载下不稳定；
- vcc_3v3 实际由 PMIC 动态控制且无法保证测试期间常开；
- 无法保证 suspend/resume/poweroff/restart 不会改变 rail；
- 测试 DTB 仍让非目标 IO-domain/设备 consumer 意外 probe；
- VCCIO5/PHY supply 电压或接线无法确认。

如 NO-GO，不得通过 stock MFD 写寄存器、强制 regulator enable 或手动 devmem 写 GRF 绕过；回到 PMIC 安全方案重新评审。

## 6. 与 stock PMIC 路径的比较

| 方案 | PMIC MFD pre-init/IRQ 写入 | PMIC regulator 自动约束/cleanup | IO-domain GRF 写入 | 当前结论 |
|---|---|---|---|---|
| stock RK809 MFD + regulator | 有 | 有可能 | 有 | G0.2 NO-GO |
| fixed-regulator 代表已测 rail | 无 | 无 PMIC rail 控制 | 仍有，且可限定到 PMUIO2/VCCIO5 | 有条件可行，需物理测量和单独授权 |
| 自定义最小 PMIC provider | 需自定义、仍可能写 enable bit | 可限定 rail，但必须完整设计 | 有 | 后续备选，不实现 |

fixed-regulator 路径仅适用于临时隔离 MAC/PHY/IO-domain 软件适配问题；它不验证 RK809 PMIC driver，不构成最终生产配置。最终系统仍需单独决定如何正确管理 SWITCH_REG1 以及其他 PMIC rails。

## 7. G0.6 结论与下一步

**G0.6 STATIC FEASIBILITY PASS / HARDWARE CONDITION BLOCKED。** 已证明 R1 kernel 有 fixed-regulator provider；Linux regulator core 可将无控制 ops 的 fixed rail 作为 always-on 逻辑 provider；IO-domain 对未声明的 optional supply 会跳过。理论上可以避开 stock RK809 MFD 的 pre-init/IRQ 写入，并仅让 PMUIO1/2 与 VCCIO5 进入目标依赖链。

但在确认 Panther X2 专用测试点、测量 VCC3V3_PMU 与 VCC_3V3、审核测试 DTB 所有 active consumers 之前，不得实现或启动该方案。

下一项唯一任务为 G0.7：只读查找 Panther X2 专用原理图/PCB/netlist/官方文档，确认两条 rail 的真实来源和可安全测量位置；如果找不到，形成需要用户提供的最小资料清单。不得用其他 RK3566 开发板的电路图替代 Panther X2。
