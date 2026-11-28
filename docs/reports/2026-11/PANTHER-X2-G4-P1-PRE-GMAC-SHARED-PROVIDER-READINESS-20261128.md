# Panther X2 Project A — G4-P1 Pre-GMAC 共享基础组件就绪证据复核（2026-11-28）

- 状态：**EVIDENCE RECONCILIATION COMPLETE / CONDITIONAL PASS；未执行新硬件操作**
- 范围：只复用 R2、R3、R6、G4-P0 已有报告和一次已授权 G4-P0 RAM-only runtime 证据
- 目的：GMAC1/MDIO/PHY 保持 disabled 时，确认其共享基础 provider 已有何种证据，明确真正缺口；不通过重复启动或主动切换资源来制造证据

## 1. 结论

当前大部分非 GMAC 共享基础组件已经在既有 6.18.63 系统启动或 G4-P0 RAM-only 会话中建立了证据。尤其是 pinctrl/GPIO、main-GRF syscon、PMUGRF syscon regmap 获取、I2C0/RK809 只读通信、RK809 regulator provider binding、IO-domain driver binding 均有可复用的既有记录。

但这些证据不能被扩大解释为“所有 GMAC 前置资源均已功能验证”：
- clock/CRU 的 GMAC consumer enable、rate/parent 及物理时钟波形尚未验证；
- reset controller 的 GMAC reset consumer assert/deassert 尚未验证；
- GMAC pinmux 尚未应用；
- RK809 regulator provider 已绑定，但具体 rail 当前状态/use_count、SWITCH_REG1 PHY consumer enable 尚未验证；
- IO-domain child 已绑定，但九路 supply/selector 功能未验证，完整 mapping 仍 NO-GO。

因此 G4-P1 作为“共享基础组件注册/绑定证据复核”可记 **CONDITIONAL PASS**；不得将其记为全部 GMAC consumer resource PASS。无需重复 G4-P0 实机启动。剩余 clock/reset consumer 动作应留在后续有明确副作用边界的准入阶段，不应为满足形式而提前触发。

## 2. 逐组件证据矩阵

| 组件 | 已有证据 | 当前状态 | 尚未证明 / 不可外推 |
|---|---|---|---|
| RK3566 clock/CRU provider | R2/B1 最终配置已包含 COMMON_CLK、COMMON_CLK_ROCKCHIP、CLK_RK3568；R6 对照 clock IDs 195/196/390–393、mux/gate/parent 与 6.1.65 | PASS-STATIC / PASS-BUILD | GMAC consumer enable、实际 rate/parent、引脚波形未验证 |
| Rockchip pinctrl | R2 在既有 R1 镜像中观察到 rockchip-pinctrl driver bind；main-GRF 必需 syscon lookup 成功 | PASS-REGISTER / PASS-INTEGRATED | GMAC1 M0 pin group 未由 GMAC consumer 选择 |
| Rockchip GPIO | R1 runtime 中 gpio0–gpio4 五个 bank 均绑定 rockchip-gpio，五个 32-line gpiochip 注册 | PASS-REGISTER | PHY reset GPIO3_PA1 未操作；不做手动 GPIO 翻转 |
| Main-GRF syscon/regmap | R2 pinctrl probe 对必需 rockchip,grf lookup 成功 | PASS-INTEGRATED | 不代表 GMAC 的 RGMII mode/delay 写入已执行 |
| PMUGRF syscon/regmap | G4-P0 rockchip-iodomain probe 成功绑定；源码顺序表明在处理 supplies 前取得 parent PMUGRF regmap | PASS-PROBE（限 regmap acquisition） | 未读写 VSEL0/1/2；无 selector transaction runtime trace |
| Reset controller | B1/R1 最终配置含 RESET_CONTROLLER；R6 核实 SRST_A_GMAC1 ID236、bank14/bit12 和 offset 0x438，黄金逻辑对照完成 | PASS-STATIC / PASS-BUILD | GMAC reset consumer 获取及 assert/deassert 未验证；不提前主动 reset |
| I2C0 / RK3x | R3.1 adapter/controller runtime bind 和 i2c-dev adapter 注册证据 | PASS-RUNTIME | 不代表 RK809 MFD 子设备初始化 |
| RK809 I2C identity/status | R3.2/R3.7：ID 0x8094；PMIC_SYS_STS 0xF0=0xC2；PMIC_OFF_SOURCE 0xF6=0x00；只读事务成功 | PASS-RUNTIME（只限这些寄存器） | 不提供 rail 电压/负载能力证据 |
| RK809 MFD/regmap | G4-P0 已观察 rk808-regulator platform device 绑定；provider 初始化的 PMIC pre-init/IRQ 行为属于该启动会话的预期副作用 | PASS-REGISTER / PASS-PROBE（本次运行） | 不等于完整 MFD 所有 child 均正常；不得把本次绑定证据解释为无副作用 |
| RK809 regulator provider | G4-P0 rk808-regulator driver bind；21 个 regulator class objects 注册，其中 RK809 provider 对象及四个相关 supply 名称已识别 | PASS-REGISTER | rail 当前 enable/state/use_count 未在本次人工只读检查中复核；SWITCH_REG1 consumer 未启用 |
| Rockchip IO-domain | G4-P0 IO-domain child/platform device 创建并绑定 rockchip-iodomain | PASS-REGISTER / PASS-PROBE（binding-only） | 九路 supply 属性全部缺失；无 voltage read/notifier/selector 功能证据；完整映射 NO-GO |

## 3. 必须保留的历史状态纠正

早期 G0.1 矩阵将 RK809 MFD/regulator 和 IO-domain 标为 BLOCKED/DEFERRED，是当时 R1/G3 的状态。G4-P0 后续在单独审查并取得授权的 RAM-only 会话中，已证明 RK809 regulator provider 与 IO-domain binding。应以 G4-P0 最新运行证据更新“是否绑定”状态，但不删除早期风险判断：

- R3 对 stock MFD/regulator probe 的副作用审计仍然有效；
- G4-P0 确实运行了 RK809 provider probe，且出现预期 PMIC 初始化动作；这不是只读操作；
- G4-P0 通过删除全部九个 IO-domain supply 属性，刻意绕开 voltage-read/notifier/selector 写入路径；
- 因此 provider binding PASS 与 supply/selector safety PASS 是两个不同问题。

## 4. G4-P1 验收结论

| 子项 | 判定 |
|---|---|
| clock/CRU 配置与静态依赖 | PASS-STATIC / PASS-BUILD |
| pinctrl / GPIO provider runtime registration | PASS-REGISTER |
| main-GRF syscon lookup | PASS-INTEGRATED |
| PMUGRF syscon regmap acquisition | PASS-PROBE（由 G4-P0 IO-domain probe 支持） |
| reset controller 配置/实现 | PASS-STATIC / PASS-BUILD |
| I2C0 与 RK809 安全只读事务 | PASS-RUNTIME |
| RK809 regulator provider binding/class registration | PASS-REGISTER |
| IO-domain binding-only | PASS-REGISTER / PASS-PROBE |
| GMAC clock/reset/pinmux consumer 功能 | NOT VERIFIED（有意留待 GMAC 最后启用） |
| SWITCH_REG1 PHY consumer enable | NOT VERIFIED（G4-P2） |
| IO-domain nine-supply/selector function | NO-GO / NOT VERIFIED（G4-P2） |

**G4-P1 = CONDITIONAL PASS（共享基础 provider 注册/绑定证据已充分复用；GMAC 专属 clock/reset/pinmux 消费动作仍未执行）。**

这不是要求先单独打开 GMAC clocks 或手动操作 reset。那些动作属于 GMAC consumer 路径，若提前执行会破坏“GMAC 最后启用”的隔离原则。只有 G4-P2 解决供电/IO-domain 风险后，才在 R7-A 的独立授权范围内由正式驱动调用这些 consumer API，并逐项观测。

## 5. 下一门 G4-P2 的问题清单

G4-P2 不应立即进行硬件操作，先做只读源码/DTB/黄金证据审计：
1. 复核 Panther X2 九个 IO-domain supply 的 index、provider、voltage getter 能力、selector write handler 和 probe 顺序；
2. 明确 vccio1 / SWITCH_REG1 regulator_get_voltage() 失败导致的 partial-write 路径是否仍存在于固定源码；
3. 核对 G4-P0 真实运行时 provider 状态能否提供任何安全的既有状态证据；不通过 raw PMIC/GRF/MMIO 读取补证；
4. 对照 6.1.65/6.1.116 黄金 DTS、MFD/regulator 与 IO-domain 调用路径，保留 6.1.65 原始 DTB binary 限制；
5. 评估是否存在不修改上游驱动、不伪造 regulator 电压、不引入不真实 fixed-regulator 的安全方案；
6. 若无安全方案，保持 G4-P2 HOLD，停止在 GMAC 前，不得为了继续推进而强行恢复九路 supply。

## 6. 安全边界

本报告只回读仓库文件和既有运行证据；没有访问 Panther X2，没有重复启动 G4-P0，没有切换 regulator/GPIO/reset，没有读写 PMIC/GRF/MDIO，没有发送网络帧，没有写入 SU08G/SN64G/eMMC。

G4-P1 复核通过不自动授权 G4-P2 实机操作或 R7-A GMAC probe。GMAC 继续 disabled。
