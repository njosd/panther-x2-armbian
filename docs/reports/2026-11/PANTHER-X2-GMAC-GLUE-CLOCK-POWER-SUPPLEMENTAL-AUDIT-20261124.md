# Panther X2 GMAC glue、时钟与电源路径补充审计归档（2026-11-24）

## 1. 结项状态与范围

**归档性质：历史 GMAC glue/时钟/电源静态审计的补充汇总。它不是 B2-0 方向二结项报告，不改变 B2-0 的原始方向顺序或当前进度。**

本方向只审查 Panther X2 实际命中的 Rockchip GMAC1 RGMII glue 初始化、时钟启用、CRU reset、CSU 接口、电源 regulator 与 runtime-PM 交接。采用已锁定的正常/故障源码端点和仓库既有审计，不重复已完成的 CRU parent/mux/gate/reset、TX core、PHY workaround、RGMII delay 等专题。

本报告仅记录技术结论、公开源码 commit 和公开报告路径；不包含家庭网络地址、设备唯一标识、个人账号或认证材料。

没有访问 Panther X2，没有读取/写入 MMIO、MDIO 或寄存器，没有运行故障内核，没有修改设备树、内核配置、驱动或网络服务，也没有发包、抓包或执行现场测试。

## 2. 固定源码端点

- 正常基线 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.1.174-rk35xx 故障构建：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`；其原始 Actions run #296 job log 已直接确认 source_hash。
- 6.12.81-rk35xx 故障构建：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

以上源码端点用于本方向静态比较；它们不替代历史安装文件逐字节 hash，也不将源码差异直接等同于实机根因。

## 3. GMAC glue probe / setup / power handoff

复用三版本 `dwmac-rk.c` 的既有逐项比较：

- Panther 使用外置 RTL8211F，DTS 未声明 `phy-is-integrated`；integrated-PHY power/reset/BGS OTP 分支不命中。
- Panther DTS 显式提供 RGMII TX/RX delay；6.1.116 的缺省值与后续版本缺省值差异不命中当前设备树。
- PHP-GRF 属性命名差异不命中 RK3568 Panther 所用 ops；有效 `rockchip,grf` 资源已有证据。
- SPH disable 影响 RX split-header/GRO，不进入普通 TX 提交路径。
- MAC address callback、loopback sysfs 等新增功能没有证据影响普通 TX 自动路径。
- 三版本 `rk_gmac_phy_power_on()` 都调用 regulator enable/disable，失败时记录日志但最终仍返回 0；这是共有错误处理弱点，不是已发现的版本回归。
- 三版本 `pm_runtime_get_sync()` 返回值均未检查；同样是共有弱点。
- 外接 PHY 的普通 powerup 顺序均为：启用 GMAC clocks → 设置 RGMII interface/delay → 启用 PHY supply → runtime-PM get → STMMAC probe。
- suspend/resume 的外接 PHY 普通路径未发现能解释已知回归的有效新增差异。

**结论：** 已审查的 GMAC glue probe/setup/power handoff 差异中，未发现一个已证实且同时命中 Panther 外接 RGMII 普通 TX 路径的回归根因。

## 4. CRU clocks 与 reset

复用已完成的 GMAC1 CRU parent/gate/reset 审计：

- Panther GMAC1 RGMII 实际启用集合已映射为 `aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`。
- `mac_clk_tx` 与 `clk_mac_speed` 在相关 provider 中指向同一 CCF core；双 enable/disable 属于平衡引用计数，不是两次独立 mux 操作。
- 正常与故障源码端点的 Panther GMAC1 parent/mux/gate/reset 主路径没有发现足以解释故障的确定性差异。
- GMAC1 reset ID、CRU reset register 映射、hiword-mask 写法和 STMMAC assert/deassert 顺序一致。
- 6.1.174 的 `PCLK_USB` critical 标记是实际源码差异，但其作用发生在 CRU clock registration/早期 parent chain 阶段；没有证据证明它导致运行期 GMAC TX 故障。
- 单项 clock enable 返回值处理在版本间存在差异；故障版本逐项 enable 时忽略部分返回值。当前没有实机证据证明 Panther 的关键 clock enable 实际失败。
- GMAC bring-up settle delay 从 6.1.116 的 5ms 缩短为 6.12.81 的 100–200µs，是已确认源码时序差异；尚无 RK3566/Panther 厂商时序证据证明 100–200µs 不足，故保留为未验证时序候选，不制作补丁、不直接恢复 5ms。

## 5. CSU 与 power-domain 核查

针对 6.12.81 新增的 `rockchip_csu_disable()`：

- Panther GMAC1 DTS 节点及对应 SoC 节点未声明 `rockchip,csu` / CSU phandle 与名称映射。
- `rk_gmac_csu_init()` 获取 aclk/pclk CSU handle 后，对错误 handle 置为 NULL。
- CSU provider 的公共入口对 NULL handle 直接返回 0；不会继续调用 SoC 专用 CSU callback。
- 因此 Panther GMAC1 当前设备树配置下，CSU disable 路径为 no-op；没有证据表明它关闭 GMAC ACLK/PCLK 或触发安全监控调用。
- Panther GMAC1 节点未声明独立 `power-domains` 绑定；本方向没有发现可归因于该属性的 GMAC power-domain 差异。

**证据边界：** 这是源码与 DTS 静态结论，不是实机 CSU 寄存器状态或电源域状态的现场读回。

## 6. PHY supply provider

- Panther DTS 的 GMAC1 `phy-supply` 指向 RK809 的 `vcc_3v3` / SWITCH_REG1 regulator。
- 这不是 `regulator-fixed`；它依赖 RK809 PMIC、I2C、MFD 与 regulator provider 链。
- 6.1.116、6.1.174、6.12.81 的 Panther DTS 供电引用一致；三版本 glue 的 regulator enable/disable 错误处理也一致。
- 6.18.63 Kconfig/Makefile 依赖审计已另行闭合 RK809 provider 的构建依赖链；该报告只用于依赖关系核验，不证明 provider 在实机 probe/供电成功。
- 当前没有证据证明历史故障由 RK809 regulator enable 失败引起。

## 7. 方向二结论矩阵

| 子项 | 结论 | 状态 |
|---|---|---|
| GMAC glue probe/setup/powerup/powerdown | 已完成三版本比较；未发现已证实的 Panther 普通 RGMII TX 回归根因 | 已结项 |
| RGMII clock parent/mux/gate | Panther 实际命中路径已映射；无确定性根因差异 | 已结项 |
| GMAC1 CRU reset | ID、寄存器映射及 assert/deassert 顺序一致 | 已结项 |
| clock enable 错误处理 | 存在版本差异；无现场 enable failure 证据 | 已审计，风险保留 |
| clock settle delay | 5ms 与 100–200µs 差异已确认；硬件充分性未验证 | 已审计，假设保留 |
| CSU disable | Panther 无 CSU phandle，NULL/no-op | 已结项 |
| GMAC power-domain | DTS 未声明独立 power-domain | 已结项 |
| RK809 PHY supply | provider 链已识别；无 regulator failure 现场证据 | 已结项 |

### 7.1 最终判断

**本补充审计范围内，未找到已证实的 GMAC glue、CRU、CSU 或 PHY supply 回归根因。此结论仅适用于本文件列出的静态审计范围，不代表 B2-0 对应方向已结项。**

仍保留两项证据限制：
1. 故障现场没有关键 clock enable 的返回值或实际频率/门控读回，无法证明故障版本的时钟启用全部成功。
2. 100–200µs settle delay 是否满足 Panther 板级时钟/PHY 稳定要求，缺少厂商时序依据或现场波形证据。

这两项作为“未验证风险/假设”留档，不阻碍本方向静态审计结项；不以此授权任何现场操作、补丁或配置修改。

## 8. 相关既有证据

- `PANTHER-X2-GMAC-RGMII-CLOCK-CRU-PARENT-GATE-RESET-AUDIT-20261124.md`
- `PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md`
- `PANTHER-X2-6.1-TO-6.12-GMAC-CLOCK-ENABLE-SEQUENCE-REGRESSION-20261119.md`
- `PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md`
- `PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md`

**归档边界：本文件仅作为既有 GMAC glue/时钟/电源证据的补充索引。按 B2-0 原始计划，该内容属于后续 Rockchip GMAC glue / CCF / CRU / 时钟复位专题范围；不得据此跳过 Linux 网络核心和 STMMAC/DWMAC4/DMA 两个先行方向。**
