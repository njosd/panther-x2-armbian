# Panther X2 B2-0 方向2：Rockchip GMAC glue、时钟与电源路径审计结项（2026-11-24）

## 1. 结项状态与审计边界

**B2-0 方向2：GMAC glue、时钟与电源路径的既定静态审计子项已结项。**

本报告承接方向1结项后的工作，只归纳 Panther X2 / RK3566 的 GMAC1 RGMII 实际路径。所有结论均来自既有归档及固定源码/DTS 静态核对；没有执行设备命令、安装软件、修改配置、构建内核、读取/写入 MMIO 或重启网络服务。

本报告不将“源码存在差异”自动解释为“故障根因”，也不把未测量的电压、时钟波形或现场寄存器状态写成已验证事实。

## 2. 已继承并关闭：GMAC1 CRU clock tree、gate 与 reset

既有报告：
`PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md`

核对的源码端点：
- 正常基线 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 故障样本 6.1.174：Ophub RK35xx 源码审计端点；构建来源另见方向1报告。
- 故障样本 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

已确认：
1. Panther RGMII 的 125MHz external fixed-clock、assigned-clock-parents 与 GMAC1 clock parent chain 在正常/故障端点保持一致。
2. GMAC1 专属 CRU mux、divider、gate 定义及 gate 寄存器位置没有发现可解释故障的回归。
3. GMAC1 reset ID、hiword-mask register mapping、STMMAC assert/deassert 顺序一致。
4. 6.1.174 的 PCLK_USB `CLK_IS_CRITICAL` flag 是真实差异，但目前只能确认其影响未被 consumer 引用时的早期/空闲 gate 状态；没有证据证明它改变 GMAC 正常运行。
5. 6.1.116 bulk clock enable 会检查错误；6.1.174/6.12.81 的逐项 enable 路径存在忽略返回值的差异，但没有发现 Panther 当前 clock provider 组合下必然失败的条件。

**判断：** CRU parent/mux/gate/reset 依赖关系已查清，没有发现已证实根因。实机 gate/mux/reset 寄存器值和 125MHz 波形未测量，保持未验证。

## 3. CSU：6.12 新增调用在 Panther 上是 no-op

### 3.1 Panther DTS 不提供 CSU 引用

对照正常 6.1.116、故障 6.1.174 和故障 6.12.81 的 RK356x 公共 GMAC1 节点及 Panther 板级 GMAC1 节点：
- GMAC1 节点均没有 `rockchip,csu` 属性；
- GMAC1 节点均没有 `rockchip,csu-names` 属性；
- GMAC1 节点没有声明 `power-domains` 属性。

因此，不能把 6.12 glue 中的 CSU 操作解释为 Panther GMAC1 的实际电源域切换或普通 CRU gate 操作。

### 3.2 6.12 glue 对缺失 handle 的处理

在固定 6.12.81 源码 `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 中：
- `rk_gmac_csu_init()` 分别调用 `rockchip_csu_get(dev, "aclk")` 与 `rockchip_csu_get(dev, "pclk")`；
- 获取结果为 ERR_PTR 时，驱动将对应 handle 设为 `NULL`；
- 后续 `rockchip_csu_disable(NULL)` / `rockchip_csu_enable(NULL)` 进入 `csu_disable()`，因 `IS_ERR_OR_NULL(clk)` 条件直接返回 0。

CSU provider 的 OF match table 仅列出 `rockchip,rk3562-csu` 与 `rockchip,rk3572-csu`，没有 RK3566/RK3568 CSU compatible。provider 的实际配置路径通过 `sip_smc_bus_config()` 发起 SMC；但 Panther 没有 GMAC CSU phandle，故不会进入该路径。

**结论：** 6.12 GMAC glue 中的 CSU disable/enable 对 Panther GMAC1 是空操作。该调用不是 Panther 当前网络故障的有效硬件操作路径，不再围绕 CSU 扩展审计。

## 4. PHY supply 与 regulator 电源路径

### 4.1 三个源码端点的 Panther DTS 一致

正常 6.1.116、故障 6.1.174、故障 6.12.81 的 Panther 板级 DTS 均保持：
- `&gmac1` 的 `phy-supply = <&vcc_3v3>`；
- `vcc_3v3` 对应 RK809 PMIC 的 `SWITCH_REG1`；
- PHY reset GPIO 与 active-low 语义一致；
- reset delay 为 <0, 20000, 100000> 微秒；
- RGMII、TX/RX delay 和 PHY 绑定保持既有基线配置。

此处验证的是 DTS 供电引用及控制配置相同，不代表已经测量到 PMIC 输出电压、PHY 电源轨纹波或实际电流。

### 4.2 驱动供电控制逻辑

三版 Rockchip GMAC glue 均通过：
`devm_regulator_get(dev, "phy")`
取得 PHY regulator。获取失败会使 setup/probe 返回错误。

`rk_gmac_phy_power_on()` 的三版逻辑一致：
- powerup 时调用 `regulator_enable()`；
- powerdown 时调用 `regulator_disable()`；
- 失败时打印错误；
- 函数最终仍返回 0，不把 regulator 错误向上层传播。

因此，调用者后续对该函数返回值的检查无法发现实际 regulator enable/disable 失败。这是已确认的共同错误处理弱点，不是 6.1.174 或 6.12.81 新引入的版本差异。

### 4.3 runtime PM

三版普通外接 PHY 路径均在 PHY regulator enable 后调用 `pm_runtime_get_sync()`，但不检查返回值；powerdown 时调用 `pm_runtime_put_sync()`。这是既有共同实现，不构成已确认的版本回归。现有资料没有证明 Panther 的 runtime-PM 操作在故障启动中失败。

## 5. GMAC powerup 顺序与剩余差异

Panther 外接 RTL8211F、RGMII 路径的既有静态审计顺序为：

1. enable GMAC clocks；
2. 配置 RGMII interface / delay；
3. enable 外接 PHY regulator；
4. 调用 runtime PM get；
5. 进入 STMMAC probe。

已确认的版本差异：
- 6.1.116 clock enable 采用 bulk enable 并检查返回值；
- 6.1.174/6.12.81 采用逐项 enable，部分 `clk_prepare_enable()` 返回值未检查；
- 已审计的正常 6.1.116 与故障 6.12.81 clock settle delay 为约 5ms 与 100–200µs；
- 6.1.174 的 PCLK_USB critical flag 是已记录的 CRU 差异。

证据边界：
- 不能由等待时间差异直接推出 100–200µs 不足；
- 不能由忽略返回值直接推出实机发生 clock enable failure；
- 不能由 regulator 错误处理缺陷推出实际 PHY 供电失败；
- 已有 Link Up 证据说明 PHY 至少完成基本链路协商，但不等同于供电电压质量或 TX 物理输出已验证。

## 6. 方向2结项清单

- [x] 继承 GMAC1 RGMII clock parent / mux / divider / gate 审计。
- [x] 继承 GMAC1 reset ID、CRU mapping 与 STMMAC reset 顺序审计。
- [x] 核对 6.12 CSU get/disable/enable 在 Panther DTS 上的实际调用条件，确认 handle 为 NULL、helper no-op。
- [x] 核对 Panther GMAC1 DTS 未声明独立 power-domain phandle。
- [x] 对照三版 Panther DTS 的 PHY supply、RK809 SWITCH_REG1、PHY reset 配置。
- [x] 对照三版 `rk_gmac_phy_power_on()` 与 runtime-PM 调用，区分共同弱点和版本差异。
- [x] 明确 clock settle、clock enable error handling 和 PCLK_USB flag 是已确认源码差异，但尚无实机因果证据。
- [x] 保留实际电压、波形、现场时钟状态为未验证；不安排未授权设备操作。

**最终判定：方向2既定 GMAC glue、时钟与电源静态审计子项结项。** 当前未发现已证实的 CSU、PHY regulator、runtime-PM 或 genpd 版本回归根因。后续如出现新的启动日志、源码端点或明确证据，再按证据增补，不重复本报告已关闭项目。

## 7. 主要源码与关联归档

- [6.1.116 Panther X2 DTS](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)
- [6.1.116 RK356x SoC DTSI](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.1.174 Panther X2 DTS](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)
- [6.1.174 RK356x SoC DTSI](https://github.com/ophub/linux-6.1.y-rockchip/blob/5483dc4f5384213d1a1cdf90c937db97d58721d8/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.12.81 Panther X2 DTS](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts)
- [6.12.81 RK356x SoC DTSI](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.12.81 Rockchip GMAC glue](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)
- [6.12.81 CSU provider](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/soc/rockchip/rockchip_csu.c)
- [GMAC1 CRU parent/gate/reset 依赖审计](./PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md)
- [GMAC probe/setup/PHY 电源交接差异审计](./PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md)
- [GMAC clock enable 与 settle delay 回归审计](./PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md)
- [仓库历史证据重溯与禁止重复边界](./PANTHER-X2-REPOSITORY-RETRACE-NO-REPEAT-AND-NEXT-BOUNDARY-20261119.md)
