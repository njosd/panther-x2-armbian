# Panther X2 B2-0 方向五：MDIO / PHYLIB / PHYLINK / RTL8211F 静态审计进度（2026-11-25）

## 1. 审计边界与版本固定

本报告对应 B2-0 原组件方向 B2-4：MDIO、PHYLIB、PHYLINK 与 Panther 外接 RTL8211F PHY 驱动。

四版本源码端点固定如下：

| 版本 | 角色 | 仓库与 commit | 证据边界 |
|---|---|---|---|
| 6.1.65 | 第一黄金基准 | unifreq/linux-6.1.y @ 4428b96f34a16e9a0beeed1dcb0ae3d4326145fc | 高置信度源码候选，未与原始 Image 完成密码学级绑定 |
| 6.1.116 | 后期正常基准 | unifreq/linux-6.1.y @ 5eb841b59d6ead6e264163785a634e78f0253c8e | 源码比较端点，历史 Image 精确 source commit 绑定仍有限制 |
| 6.1.174-rk35xx | 故障基准 | ophub/linux-6.1.y-rockchip @ c2f148dece4b67ebd30aefad1bdd1990f41e5633 | 实际构建源码端点 |
| 6.12.81-rk35xx | 故障基准 | ophub/linux-6.12.y-rockchip @ 661b2d8bf1284556f8876d5ed5fb80c64b22f94c | 已确认源码端点 |

6.18.63（ophub/linux-6.18.y @ aee4e352a15d636cbc484f56819c6e59474dfd9f）仅作为项目目标内核的补充兼容性核对，不纳入上述四版本历史故障分组。

本轮只读 Git 源码、DTS、Kconfig 与既有报告。没有访问 Panther X2，没有读取/写入 MDIO 或 PHY 寄存器，没有构建、安装软件、修改驱动或系统配置，也没有启动 B2.1。

## 2. 已有成果复用与禁止重复范围

本方向先回读并复用以下既有报告：

- `PANTHER-X2-B2-0-DIRECTION-3-D3-2-MDIO-PHY-ATTACH-DIFF-20261125.md`：四版本 STMMAC MDIO bus 注册、PHY node 解析、PHY attach 与 JL2xx1 四次写入时序。
- `PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md`：JL2xx1 四次写入的来源、地址 0 广播语义与证据限制。
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`：6.1.116 实机绑定、PHYCR1/PHYCR2 掩码与配置行为。
- `116-RTL8211F-MDIO-TRACE-AND-PAGED-READ-SAFETY-20261118.md`、`116-RTL8211F-PHYCR2-MODULE-POLICY-AND-API-SAFETY-AUDIT-20261118.md`：MDIO trace、分页寄存器访问与 API 安全性。
- `116-RTL8211F-PHYCR2-REFCOUNTED-PHY-LOOKUP-AND-TEARDOWN-AUDIT-20261118.md`：PHY 设备引用计数与 teardown 生命周期。
- `PANTHER-X2-RTL8211F-PHY-ID-MODEL-DECODE-AND-UBOOT-MDIO-AUDIT-20261119.md`：完整 PHY ID 0x001cc916 的字段解码，普通 CG 型号编码判断。
- `PANTHER-X2-RTL8211F-PHYCR2-PROBE-ORDER-AND-CURRENT-UPSTREAM-CROSSCHECK-20261119.md`：PHY driver probe、STMMAC workaround 与 config_init 的时序。
- `PANTHER-X2-RTL8211F-CLKOUT-WORKAROUND-REGRESSION-20261119.md`、`PANTHER-X2-JL2XX1-WORKAROUND-REGISTER-SEMANTICS-20261119.md`：历史 workaround 与寄存器语义。
- `PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md`：目标内核的 PHYLIB、PHYLINK、MDIO、REALTEK_PHY 编译依赖及 6.18 Realtek 对象布局。

不重复审计方向三已经完成的 STMMAC MDIO parser/attach 主链，不重做方向四的 Rockchip glue、CRU、时钟和 reset 专题，也不恢复已封存的 Project B 实机根因调查。

## 3. Panther 实际 PHY 分支与设备树输入

四版本 DTS 对照：
- 6.1.65 与 6.1.116 的 Panther board DTS blob 相同：`1e3153c392d8de617f72b3133eaeddf45569bde8`。
- 6.1.174-rk35xx 与 6.12.81-rk35xx 的 Panther board DTS blob 相同：`d517c99841cf9d724a61cd31acf9437acbb131e6`。

四版本 Panther 节点均命中：
- GMAC1 外接真实 Clause 22 MDIO PHY，`phy-handle` 指向 `ethernet-phy@0`，MDIO 地址 0；
- `phy-mode = "rgmii"`；
- PHY 节点只声明 compatible、reg、status，没有 `realtek,aldps-enable`、`realtek,clkout-disable`、`realtek,led-data`、LED 子节点或 PHY 专属 `clocks` 属性；
- 历史 6.1.116 dmesg 记录 IRQ=POLL，PHY 节点没有专属中断描述。

既有实机完整 PHY ID 为 `0x001cc916`，高 16 位 PHYID1=0x001c，低 16 位 PHYID2=0xc916，Model Number=0x11。该字段与普通 RTL8211F-CG 编码相符，不是 RTL8211F-VD-CG 的 Model Number=0x07。故本方向的 Panther 实际分支按普通 RTL8211F-CG（精确 PHY ID 0x001cc916）审计；VD-CG 专属寄存器路径不得混入。

## 4. 四版本 Realtek PHY driver 对照

审计文件均为各固定源码端点的 `drivers/net/phy/realtek.c`。

### 4.1 PHY ID match 与分页访问

四版本均有独立精确匹配项：
- `PHY_ID_MATCH_EXACT(0x001cc916)` → RTL8211F Gigabit Ethernet；
- `PHY_ID_MATCH_EXACT(RTL_8211FVD_PHYID)` → RTL8211F-VD Gigabit Ethernet。

普通 CG 与 VD 使用不同的 `phy_id` 分支。普通 CG 的 `rtl821x_probe()` 读取 Page 0xa43 / Reg 0x18（PHYCR1）和 Reg 0x19（PHYCR2）；对 PHYCR2 仅缓存 bit 0。若 DT 声明 `realtek,clkout-disable` 才清除缓存 bit 0。Panther 没有该属性，因此驱动不主动要求关闭 CLKOUT。

### 4.2 Panther RGMII config_init 的有效行为

四版本对普通 RTL8211F-CG 的 RGMII 分支一致：
- PHYCR1 的 ALDPS 位使用 mask 做 read-modify-write；无 `realtek,aldps-enable` 时保存并恢复 probe 读到的原位值，不是强制开启 ALDPS。
- `PHY_INTERFACE_MODE_RGMII` 对应 TX delay=0、RX delay=0；PHY driver 通过 Page 0xd08 的 Reg 0x11/0x15 清除 PHY 内部 2ns TX/RX delay。
- PHYCR2 操作只 mask bit 0，写回 probe 时缓存的 CLKOUT_EN 状态；不覆盖 bit 5、bit 11 或 bits[13:12]。
- 对 Panther 的普通 CG 分支，四版本均会执行 `genphy_soft_reset()`。6.12.81 对返回值显式分支处理，但仍传播 reset 错误。

这与 Panther DTS 的 SoC 侧 RGMII delay 配置相互对应：PHY 侧内部 delay 关闭，SoC 侧使用 board DTS 的 `tx_delay` / `rx_delay` 和 Rockchip GRF 配置。此处只确认软件配置意图，不等于实测延迟或波形。

### 4.3 6.1.65 → 6.1.116 → 6.1.174 → 6.12.81 的差异适用性

| 差异 | 源码观察 | Panther 当前 DTS 适用性 |
|---|---|---|
| 可选 LED 配置 | 6.1.65 无 `realtek,led-data` 支持；6.1.116 加入；6.1.174 调整 LED 写入位置；6.12 改为 LED framework/DT trigger 解析与恢复 | Panther 没有 LED 配置属性或 LED 子节点，不命中 |
| PHY 可选时钟 | 6.12 `rtl821x_probe()` 新增 `devm_clk_get_optional_enabled()`，suspend/resume 增加 clock disable/enable | Panther PHY 节点没有 `clocks`，可选 PHY clock 不构成已声明输入；且仅涉及 PM 路径 |
| suspend/resume | 6.1 三版本使用 `genphy_suspend`，resume 调用 `genphy_resume` 后等待 20ms；6.12 使用 `rtl821x_suspend/resume` 并设置 `PHY_ALWAYS_CALL_SUSPEND` | 只在 PHY suspend/resume / WOL 条件下适用；不是普通冷启动 TX 路径 |
| speed status 代码组织 | 6.1 三版本由 `rtlgen_read_status()` 调用 `genphy_read_status()` 后再调用 `rtlgen_get_speed()`；6.12 拆分为 decode helper，但仍读取 Page 0xa43 / Reg 0x12 | 对普通 CG 的速率读取语义未发现改变 |
| PHY interrupt | 四版本 `rtl8211f_config_intr()` 与 handler 的核心实现一致 | Panther 历史记录为 IRQ=POLL；中断处理分支不作为当前普通链路差异候选 |

6.1.116 的 `realtek,led-data` 写入位于普通 CG 的 PHYCR2 配置之前；6.1.174 的代码将该 LED 写入移到 `has_phycr2` 分支之后，普通 CG 命中 PHYCR2 分支并先返回 soft reset。该源码结构差异对 Panther 不产生实际 LED 写入差异，因为 Panther 没有 LED 属性。6.12 的 LED framework 同样没有 Panther DT 输入。

## 5. MDIO paged API、锁与错误恢复：四版本一致

对四版本 `drivers/net/phy/phy-core.c` 逐项核对：
- `phy_save_page()`：先 `phy_lock_mdio_bus()`，再读取当前 page；
- `phy_select_page()`：在持有 MDIO bus lock 时保存旧 page，并在必要时切换目标 page；
- `phy_read_paged()` / `phy_write_paged()` / `phy_modify_paged_changed()`：在同一锁保护区间内执行 page select、寄存器访问与 page restore；
- `phy_restore_page()`：尝试恢复旧 page，并释放 MDIO bus lock；若原操作成功而恢复失败，返回恢复错误；若原操作已失败，保留更早的操作错误。

以上函数四版本实现保持一致，没有发现 page select、读写、恢复之间锁保护被拆开或 page restore 语义变化。

`drivers/net/phy/mdio_bus.c` 的 `__mdiobus_read/write()`：
- 6.1.65 / 6.1.116 在 lockdep assertion 后直接调用 bus read/write；
- 6.1.174 / 6.12.81 新增 PHY 地址上界检查，以及 bus read/write callback NULL 检查并返回 `-ENXIO` / `-EOPNOTSUPP`。

Panther 地址 0 在合法范围内，STMMAC MDIO bus 提供 read/write callbacks；上述后期防御性检查在正常 Panther 路径不会改变行为。该项不构成 TX 候选。

## 6. PHYLIB 与 PHYLINK：普通 polling/RGMII 路径

### 6.1 PHYLIB generic status

四版本 `genphy_read_status()` 的普通 Clause 22 autoneg 主路径一致：
- 更新 link 状态；
- link 保持 up 且 autoneg enabled 时可跳过重复协商状态读取；
- 读取 master/slave、LPA；
- 在 autoneg complete 后解析 linkmode。

四版本 Realtek `rtlgen_get_speed()` 都在 link up 后读取 Page 0xa43 / Reg 0x12，并按相同掩码解码 10/100/1000 等速率。6.12 只是把 switch 提取为 `rtlgen_decode_speed()`，读取寄存器和速率映射不变。

### 6.2 PHY state machine

6.1.65、6.1.116、6.1.174 的 `drivers/net/phy/phy.c` blob 相同（SHA `d1aea767ed09f188351eed12e4ccc4d6101e1766`）。6.12.81 将 state machine 拆为锁内 `_phy_state_machine()` 与锁外 `_phy_state_machine_post_work()`，并引入明确的 `PHY_ERROR` 状态和精确错误函数 `phy_error_precise()`。

6.1 三版本在 link check/MDIO 错误时调用 `phy_error()` 并进入 `PHY_HALTED`；6.12 在锁内记录出错函数与 errno，进入 `PHY_ERROR`，并将 suspend 操作移至 post-work。6.12 还在 HALTED/ERROR 路径清理更多 link negotiation 状态字段。

**适用性：** 这是 MDIO/PHY 状态读取发生错误时的错误状态与恢复处理差异；普通 link polling 成功时不会进入该分支。没有历史日志证明 Panther 故障窗口出现 PHY MDIO status read error，故不升级为普通启动 TX 根因候选。若后续取得对应错误日志，需单独按该条件解释。

### 6.3 PHYLINK RGMII PHY mode

方向三已确认 Panther 通过 `phy-handle` 连接外接 PHY，不是 fixed-link 或 in-band PCS。6.1 三版本 `phylink_resolve()` 的 `MLO_AN_PHY` 分支直接取 `pl->phy_state`，再应用手动 flow-control 设置；6.12 将该 switch 改为按 `act_link_an_mode` 分支判断，但 PHY mode 仍直接使用 `pl->phy_state`。

对 Panther 的 PHY mode 路径，未发现 6.12 将 link/speed/duplex 改为 PCS in-band 状态来源，也未发现与 RGMII 外接 PHY 相适用的新的 link-state 阻断条件。PHYLINK attach 的调用顺序不在本节重复，引用方向三 D3-2。

## 7. 6.18.63 目标内核补充核对（不混入四版本历史矩阵）

6.18.63 精确源码为 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。Realtek PHY 驱动拆分到 `drivers/net/phy/realtek/realtek_main.c`，`CONFIG_REALTEK_PHY` 仍控制该驱动；这与 Kconfig/Makefile 报告的对象布局一致。

对普通 RTL8211F 分支发现以下目标内核差异：

1. `rtl821x_probe()` 不再读取并缓存 PHYCR1/PHYCR2 当前值；改为读取 DT 的 `realtek,aldps-enable`、`realtek,clkout-disable` 布尔属性，并获取可选 PHY clock。
2. Panther 未声明上述两个属性，因此 `rtl8211f_config_aldps()` 与 `rtl8211f_config_clk_out()` 均按源码注释保持 PHY 当前值，不主动改写 ALDPS 或 CLKOUT。与早期“读取并回写相同掩码位”的方法相比，目标驱动减少了 MDIO 读写。
3. `rtl8211f_config_init()` 额外调用 `rtl8211f_config_phy_eee()`，对普通 CG 的 Page 0xa43 / Reg 0x19 清除 `RTL8211F_PHYCR2_PHY_EEE_ENABLE = BIT(5)`。源码注释为禁用 PHY-mode EEE，使 LPI 传递给 MAC。这是 6.18.63 相对四个历史端点的新 PHY 配置动作；旧版 JL2xx1 写入值 0x1801 的 bit 5 同样为 0，但这不等于认可恢复整个 0x1801 workaround。该 bit 的实际 PHY 状态及对 MAC EEE/LPI 的影响尚无现场回读/波形证据。
4. 6.18.63 的 `rtl8211f_config_init()` 不再在普通默认配置下无条件调用 `genphy_soft_reset()`；只有当 DT 设置 `realtek,clkout-disable` 时，`rtl8211f_config_clk_out()` 才执行该 soft reset。Panther 没有该属性，因此目标驱动普通 config_init 路径不触发此处的 PHY soft reset。这是相对 6.1.65/6.1.116/6.1.174/6.12.81 的实际初始化序列差异，必须在后续目标配置评估中单独保留，不能未经验证就判定优劣。
5. 6.18.63 `rtlgen_read_status()` 改为读取 `MII_RESV2`（源码常量 `RTL_PHYSR`）并解码 speed 与 duplex；四个历史版本读取 Page 0xa43 / Reg 0x12 解码 speed。新旧寄存器来源并非同一地址；源码注释说明新路径用于覆盖 downshift 情况，但本项目没有硬件寄存器回读证明两种状态来源对 Panther 的等价性。
6. 6.18.63 `rtl8211f_probe()` 新增清除 PME event registers 的写入，并增加 wakeup-source/WOL 支持；Panther DTS 未声明 wakeup-source，也没有 PHY IRQ 配置，因此相关唤醒中断路径不命中当前板级描述。
7. 6.18.63 `rtl8211f_resume()` 在 genphy resume 与 20ms 等待后重新执行 RGMII delay 配置；这是 suspend/resume 恢复路径，不影响普通 cold probe 的结论。

同时检查 6.18.63 `stmmac_mdio.c`，未检出 6.1.65/6.1.116 中 JL2xx1 workaround 的四次 MDIO magic writes。6.18.63 通过 PHY driver 对 bit 5 的显式清除与旧 workaround 的一个位值存在表面重合，但二者执行位置、写入范围、reset 行为均不同，不能等同。

**目标内核结论：** 6.18.63 的 Realtek PHY driver 不是简单照搬 6.12.81；它在 EEE、soft reset、speed status register 和 suspend/resume 上有新的实现。尤其 bit 5 清除、默认 config_init 不再 soft reset、speed status register 改变，应进入未来 6.18 目标配置的风险与验证清单，但不能倒推为 6.1.174/6.12.81 历史故障的原因。

## 8. 本轮阶段性结论

已完成：
- 四版本普通 RTL8211F-CG 精确驱动分支与 Panther DTS 适用性核对；
- PHYCR1、RGMII delay、PHYCR2 bit 0、soft reset 的四版本行为对照；
- 四版本 MDIO paged API 锁保护和 page restore 错误语义对照；
- MDIO bus callback/地址防御性检查的适用性分类；
- PHYLIB genphy status、PHY polling state machine 的四版本比较；
- PHYLINK RGMII PHY mode resolver 的四版本比较；
- 6.18.63 目标内核 Realtek PHY driver 的补充差异核对。

仍需在方向五最终结项前完成：
- 对方向五全部既有专项报告逐项建立“已复用/不重复/尚缺证据”索引，确保 PHYCR2、EEE、CLKOUT、WOL、MDIO trace 与 API 安全结论无遗漏或冲突；
- 汇总四版本差异的首次出现版本、Panther 适用分支、优先级与证据等级；
- 对 6.18.63 目标内核新增 PHY 配置动作单独列出风险，不混入四版本历史故障矩阵；
- 完成最终方向五覆盖矩阵与有条件结项评估。

**当前状态：方向五进行中，尚未结项。** 本报告只记录静态审计进度，不表示已找到 TX 根因，也不授权任何设备操作或 B2.1。

## 9. 主要源码索引

- [6.1.65 Realtek PHY driver](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/phy/realtek.c)
- [6.1.116 Realtek PHY driver](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/phy/realtek.c)
- [6.1.174-rk35xx Realtek PHY driver](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/phy/realtek.c)
- [6.12.81-rk35xx Realtek PHY driver](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/phy/realtek.c)
- [6.18.63 target Realtek PHY driver](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/phy/realtek/realtek_main.c)
- [6.18.63 target STMMAC MDIO](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9f/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c)
