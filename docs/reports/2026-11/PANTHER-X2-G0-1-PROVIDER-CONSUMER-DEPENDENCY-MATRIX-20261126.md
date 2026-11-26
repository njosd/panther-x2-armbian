# Panther X2 项目 A — G0.1 Provider/Consumer 依赖矩阵（2026-11-26）

- 状态：**G0.1 第一轮矩阵已整理；尚需与 R7-A 准入清单逐项交叉复核。**
- 范围：只读归并已归档 R2–R6，不访问设备、不重跑测试、不更改配置。
- 依据：R2 Shared SoC Provider Audit；R3 RK809/I2C/Regulator Preflight；R4 MDIO/PHY Audit；R5 STMMAC/DWMAC4 Core Audit；R6 Rockchip Glue Audit；R2–R7 Gated Acceptance Matrix。

## 1. Provider → Consumer 总矩阵

| Provider / 资源 | Consumer / 下游 | 6.18.63 已有证据 | 黄金基线对照 | 当前结论 / 后续门 |
|---|---|---|---|---|
| RK3566 CRU/CCF clock provider | GMAC1 ACLK/PCLK/SCLK、STMMAC MAC clock | R6 静态核对 clock IDs 195/196/390–393、mux/gate/parent；GMAC 目标 parent 指向 DTS fixed-clock gmac1_clkin | R6 对照 6.1.65 clock binding/CRU 定义；核心 IDs/位置一致 | STATIC PASS；实际 enable/rate/波形 G4/R7-A |
| RK3566 pinctrl + GRF/PMU Syscon/Regmap | GMAC1 M0 pin groups、IO-domain GRF 写入、Rockchip glue GRF | R2 实机 pinctrl bind；syscon GRF/PMU regmap 获取成功；R6 TRM 核验 GMAC1 CON0/CON1 与 bit7 语义 | 6.1.65 配置值与 6.18 对照一致；黄金 DTB 已有核心属性解析 | provider runtime PASS；GMAC pinmux 尚未应用，R6/R7-A |
| Rockchip GPIO provider | GMAC1 PHY reset GPIO3 line1 active-low；其他 GPIO consumers | R1 实机 GPIO0–GPIO4 全部 bind，五个 32-line gpiochip 注册 | 6.1.65 与 6.18 GPIO/pinctrl 相关 config 均 y；实现来源仍保留精确构建 commit 限制 | provider runtime PASS；PHY reset consumer 尚未执行，G4/R7-A |
| Rockchip reset controller | GMAC1 SRST_A_GMAC1 ID236 | R6 静态计算 bank14/bit12、寄存器 offset 0x438；provider API 代码对照 | 6.1.65/6.18 reset ID/provider 逻辑一致 | STATIC PASS；实际 assert/deassert 未验证，G4/R7-A |
| RK3x I2C controller + i2c-dev | RK809@0x20、FAN53555@0x1c 等 I2C clients | I2C0 driver bind；i2c-dev adapter 89:0 注册；FAN53555 识别；RK809 ID 0x8094 与 0xF0=0xC2、0xF6=0x00 两组只读事务通过 | R3 6.1.65 final config 有 I2C_RK3X/REGMAP_I2C；6.18 相同基础能力 | RUNTIME PASS（限已读寄存器）；不代表 MFD/regulator |
| RK809 I2C MFD parent / regmap IRQ | RK809 MFD children、regulator provider | R1 未构建；6.18 probe 根据 OF match variant，随后执行 RK817-family pre-init regmap_update_bits；IRQ layout/生命周期也需审查 | 6.1.65 Golden 有旧 rk808/rk808-regulator built-in；新旧实现不等价，需继续比对 | BLOCKED：probe 含 PMIC 写入；G0.2 决策后才可考虑 G2 |
| RK809 regulator provider (SWITCH_REG1 / vcc_3v3 等) | GMAC1 phy-supply；PMU IO-domain supplies；其他 DTS consumers | R1 未构建 REGULATOR_RK808；regulator registration/constraints 可能自动写 voltage/mode/enable | 6.1.65 具备旧 regulator built-in；6.18 配置缺失，不能假设相同注册副作用 | BLOCKED：G0.2 后另行 G3；provider注册≠rail物理电压 |
| RK3568 PMU IO-domain consumer | PMU bank voltage select、GRF/PMU GRF | R1 ROCKCHIP_IODOMAIN=y；因缺 regulator provider，devm_regulator_get_optional() 返回 defer 后退出，尚无最终重新 probe/bind证据；成功路径会 regulator_get_voltage 后写 GRF | 6.1.65 整机网络正常，但尚无对应 provider/IO-domain 独立运行时记录 | BLOCKED/DEFERRED：G0.3；不可将 defer 记 PASS |
| RK809 SWITCH_REG1 实际 rail | GMAC1 PHY vcc_3v3 | DTS phandle 正确；无 regulator consumer 成功、无 rail voltage/纹波/负载测量 | 黄金系统整体正常不能证明本 rail 单项测量 | NOT VERIFIED：G3/G4/R7-A；需要安全测量方案 |
| External gmac1_clkin 125MHz | RK3568 SCLK_GMAC1 input、RGMII/PHY reference | DTS fixed-clock 125MHz、clock_in_out=input；CCF逻辑路径静态核验 | 6.1.65/6.18 DTB核心clock parent定义一致 | STATIC ONLY；物理来源与波形未验证，G0.4 |
| Rockchip DWMAC glue | GRF/clock/reset/regulator/pinctrl consumers；STMMAC platform core | R6 6.1.65/6.18源码生命周期对照；6.18 probe/init 会 enable clocks、写GRF、enable phy-supply、runtime PM | 已核对两版 glue 调用路径和关键差异 | STATIC CONDITIONAL；未 probe；必须通过G0后单独授权 G5-A |
| STMMAC/DWMAC4 core | net_device、DMA engine、TX/RX queues、IRQ/NAPI | R5-1..R5-4静态对照完成；R1未构建/启用目标MAC | 6.1.65/6.18 descriptor OWN、DMA mapping、barrier、completion核心语义连续；6.18 reset failure变warning-and-continue | STATIC CONDITIONAL；真实 DMA capability/reset/ring 未验证，G6 |
| PHYLIB/MDIO_BUS/OF_MDIO/PHYLINK | MDIO bus、PHY attach/state machine | R4 Kconfig/Makefile/RTL8211F驱动静态审计；R1关闭相关对象 | 6.1.65/6.18依赖组织不同；REALTEK_PHY必须显式启用 | STATIC CONDITIONAL；无6.18 MDIO事务/PHY bind/link，G5-B |
| RTL8211F PHY driver | PHY ID match/config_init/autoneg/link、RGMII delay interaction | R4静态对照已识别probe/config_init差异；无6.18实机执行 | 6.1.65黄金整机网络正常；旧/新实现不应假定相同 | STATIC ONLY；PHY ID/link待G5-B |
| AF_PACKET / Linux packet injection | 用户态原始帧→skb→netdev TX | R1 软件 API 在 loopback 路径已实机验证；目标 GMAC disabled | R1不是目标网卡数据路径；不能外推为物理TX | 软件 API 有限范围 PASS；目标网卡 A/B/C/D 未执行，G6 |
| STMMAC TX DMA path | skb→DMA mapping→descriptor OWN→doorbell→completion/reclaim | R5静态源码路径已审计；R1未启用驱动；无目标运行时trace | 两版核心语义连续，6.18存在若干生命周期/错误处理差异 | STATIC ONLY；A/B/C/D C/D待G6 |
| Physical Ethernet TX | GMAC→RGMII→RTL8211F→MDI/变压器/网线→交换机→对端抓包 | 无6.18线侧证据；两条黄金基线整机正常 | 6.1.65/6.1.116有实际正常网络正向行为，但不代替6.18 | NOT VERIFIED；G7决定性验收 |

## 2. 关键依赖链

```text
RK3566 CRU / CCF ───────────────┐
Pinctrl / GRF / PMU Syscon ─────┤
GPIO / Reset controller ────────┤
                                ├─> Rockchip DWMAC glue
I2C0 / i2c-dev -> RK809         │       ├─> STMMAC/DWMAC4 core
                   └─> MFD/regmap (blocked)    ├─> net_device
                        └─> regulator (blocked)│    └─> AF_PACKET A
                             ├─> IO-domain (deferred)   -> skb B
                             └─> GMAC phy-supply        -> stmmac_xmit C
                                                      -> DMA mapping D
                                                      -> descriptor/OWN
                                                      -> completion/reclaim
                                                      -> MAC/RGMII/PHY
                                                      -> peer packet capture
```

注意：该图是功能依赖关系，不是 Linux driver core 的确定 probe 时间顺序。实际顺序以 supplier/consumer、deferred-probe、probe log、sysfs bind 和资源 API 返回为准。

## 3. 本轮结论

1. R2 是当前已通过的共享 SoC provider 基础：pinctrl/Syscon consumer、GPIO bank/gpiochip 均有实机只读证据。
2. R3 的 I2C0/RK809身份/只读状态路径有实机证据；MFD/regmap/regulator 尚未启用且 probe/registration 有写寄存器副作用。不得将 PMIC 状态字节解释为 rail 电压。
3. IO-domain 在 R1 中因 regulator provider 缺失而 deferred；成功路径会写 GRF，故既不是已通过，也不是纯只读 consumer。
4. R4/R5/R6 目前主要是源码/Kconfig/DTB静态证据。R5静态TX链审计完成，不代表硬件DMA已工作；R6的125MHz fixed-clock不代表板上实际波形。
5. R1 AF_PACKET loopback 只证明 Linux packet socket API 在该软件环境可用，不证明目标 GMAC、STMMAC、DMA、PHY 或线侧发送。
6. 当前真实目标 TX 最早只能在目标 netdev、interface open、DMA ring 等前置条件通过后执行；G6执行ABCD同帧链，G7由对端捕获确认物理TX。

## 4. 尚待 G0 处理的缺口

- RK809 MFD probe pre-init/IRQ/生命周期及 regulator 自动约束写入白名单。
- IO-domain deferred-probe 的完整最终状态/重试记录及 regulator supplier 映射。
- 6.1.65原始DTB完整自动diff仍缺原始二进制本轮提取；已有GMAC核心解析可复用，不重提851MiB镜像。
- 外部125MHz时钟的实际物理来源和波形测量方案。
- ABCD A/B/C/D 同帧 trace可关联能力与对端抓包夹具审查。

## 5. 下一步

G0.1第一轮矩阵完成。G0.2 stock RK809 MFD/regulator 静态审计结论 NO-GO；允许写入白名单为空。G0.3 已完成静态拓扑/写入路径归并：GMAC1 M0→GPIO3→VCCIO5，vccio5 与 phy-supply 共用 vcc_3v3/SWITCH_REG1；VCCIO5 selector 写 PMU GRF 0x140/0x144。R1 deferred-probe 后续最终 bind 状态 UNKNOWN。下一项 G0.4 clock/reset/PHY 物理时钟来源审计；不启动硬件、不启用 MFD/regulator、不写 GRF。
