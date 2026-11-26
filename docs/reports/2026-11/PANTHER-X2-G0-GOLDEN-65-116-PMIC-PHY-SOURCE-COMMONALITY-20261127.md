# Panther X2 项目 A — 两条黄金基准 RK809/Regulator 软件路径共性核验（2026-11-27）

## 1. 目的与范围

响应“优先从黄金基准反向提取配置和驱动行为”的路线要求，直接比较两个已归档的正常版本源码端点：
- 6.1.65 高置信度候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`
- 6.1.116 正常运行基线：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`

只读读取同一仓库两个固定 commit 的源码文件，按 Git blob SHA 和完整文本相等性比较；不访问设备、不运行网络测试、不修改文件或配置。

## 2. 关键结果：两条黄金源码的 PMIC/PHY 主链高度一致

| 文件 | 6.1.65 blob | 6.1.116 blob | 比较 |
|---|---|---|---|
| `drivers/mfd/rk808.c` | `e00da7c7e3b11c83530c211f62271c4251a8d80b` | 相同 | **逐字节相同** |
| `drivers/regulator/rk808-regulator.c` | `127dc2e2e6903bfc92c2a1abad12a720c7f26626` | 相同 | **逐字节相同** |
| `drivers/soc/rockchip/io-domain.c` | `6619256c2d1180f2a24e5c1a595bafe1d2c65c16` | 相同 | **逐字节相同** |
| `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c` | `514f1ac0dea2d49cd4f581a48db2b02160187d0a` | 相同 | **逐字节相同** |
| `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts` | `1e3153c392d8de617f72b3133eaeddf45569bde8` | 相同 | **逐字节相同** |
| `arch/arm64/boot/dts/rockchip/rk3566.dtsi` | `6c4b17d27bdc526ffacc1d991a09f3982434e9f3` | 相同 | **逐字节相同** |

这意味着，在当前两个已锁定源码端点之间：
- RK809 variant 检测、MFD IRQ、pre-init 和 child-cell 创建代码相同；
- RK809 regulator descriptors、SWITCH_REG1 enable/disable 定义相同；
- Rockchip IO-domain provider/consumer 实现相同；
- GMAC glue 获取 `phy-supply`、enable/disable regulator 的调用路径相同；
- Panther X2 板级 DTS 中 RK809 regulator 子树、GMAC1 PHY supply、reset、clock、RGMII 配置相同。

因此，6.1.65 与 6.1.116 可以共享同一套“黄金 PMIC/PHY 软件行为模型”，不需要把两套黄金系统当成两套不同的 RK809 实现分别重做审计。

**来源身份限制：** 6.1.116 commit 是已锁定正常源码端点；6.1.65 commit 仍是与原始 Image build timestamp/提交线索吻合的高置信度候选源码，尚未建立原始 Image 的二进制级源码绑定。因此 6.1.65 的源码共性结论仍标记 GOLDEN-CANDIDATE SOURCE；两套正常系统的实际网络成功则是独立实机证据。

## 3. Regulator core 的版本差异边界

`drivers/regulator/core.c` 整体 blob 不同：
- 6.1.65：`34d3d82819064551212ba9d612a16d36a0cdedd1`
- 6.1.116：`518b64b2d69bcf6835c3bf8762c9cdbbb9c7df98`

但本次定点比较以下四个直接相关函数，完整函数文本逐字节相同：
- `set_machine_constraints()`
- `regulator_late_cleanup()`
- `regulator_init_complete_work_function()`
- `regulator_init_complete()`

因此，6.1.65→6.1.116 的 regulator core 文件变化没有改变本项目当前已审查的约束应用和 unused-regulator late cleanup 主路径。其他 regulator core 函数仍有差异，但在没有具体调用路径命中前不扩展审计。

## 4. 与既有实机行为的交叉证据

6.1.116 的归档网络基准日志显示：
- RK809/RK817 电源管理 IRQ 记录存在，例如 IRQ 38 对应 `rk817` 的 `rk805_pwrkey_rise`；
- GMAC1 probe 完成，识别 RTL8211F Gigabit Ethernet；
- Link Up 达到 1Gbps/Full。

6.1.116 的真实 `kernel.config` 已从归档提取，7,677 个符号与对应 Ophub `config-6.1` 模板全量零差异。6.1.65 的原始 config 与 `modules.builtin` 也已归档，确认 `MFD_RK808=y`、`REGULATOR_RK808=y`，MFD/regulator built-in 对象存在。

这组证据支持黄金系统确实使用旧 RK808/RK809 MFD 与 regulator 软件链；它不是仅仅依赖 PMIC 上电默认状态的一个“无驱动”系统。

## 5. 对 6.18.63 的当前比较结论

结合既有 R3 §21–§26：
- 6.18 的 RK809 IRQ 24-bit mapping、pre-init table、MFD child cells 与 6.1.65 候选源码一致；
- 6.18 SWITCH_REG1 descriptor 与两套黄金源码一致；
- 6.18 Panther DTS regulator 子树与黄金候选 DTS 一致，唯一节点属性写法差异为 vendor-prefixed `rockchip,system-power-controller` 改为标准 `system-power-controller`；
- 6.18 regulator core 的约 30 秒 unused-regulator cleanup 不是新引入，6.1.65/6.1.116 对应函数一致；
- 6.18 Rockchip glue 的 PHY regulator 错误传播比 6.1.65/6.1.116 更严格，是正向改进，不应回退。

所以目前已知的核心差异仍然是：R1 的 6.18 最终配置没有启用/构建 RK8xx MFD 和 RK809 regulator provider；而两套黄金基准的配置均包含旧版 MFD/regulator。这个配置缺口必须作为后续恢复网络硬件链时的明确变量，不应通过 fixed-regulator 替代来绕过。

## 6. 下一步：不重复 PMIC 源码审计，转向黄金二进制 DTB 核验

现有报告已完成大量源码比较，接下来只补齐一个真实资产证据：
1. 从已归档 6.1.65 原始镜像/DTB 阶段包提取原始 `rk3566-panther-x2.dtb`；已知原始 DTB SHA256 为 `d03ec12df0d69bfa0f0ab5ac462a8fffd8ae5d1c512032ff9468df89248d289f`，不访问 SN64G，不重提 851MB 镜像。
2. 从 6.1.116 已归档 `dtb-rockchip-6.1.116-ophub.tar.gz` 提取对应 DTB（归档 SHA256 `2c60c79d67fee948689fa3ac17cd834e33553f1c65f03bf852529372ae37d5e5`）。
3. 与 6.18.63 R1 实际 DTB 做结构化对照，限定在 RK809 PMIC 节点、IRQ 属性、regulator 子节点 constraints、IO-domain supplies、GMAC1 phy-supply 与相关 phandle。
4. 如果三份 DTB 的这些属性相同，则把 DTS/DTB 作为已解释变量关闭，不做电源测量；若有差异，只针对差异回查对应源码和启动日志。

此后再根据实际差异决定是否进入 MFD/regulator/IO-domain 的受控功能验证。ABCD sender 继续独立准备；在 netdev/open/DMA 条件未出现前记 NOT EXECUTABLE，一旦满足就优先单帧 A→D 与对端 pcap。

**本报告没有访问设备、启动内核、写 PMIC/GRF、测量电压、构建镜像或发送帧。**
