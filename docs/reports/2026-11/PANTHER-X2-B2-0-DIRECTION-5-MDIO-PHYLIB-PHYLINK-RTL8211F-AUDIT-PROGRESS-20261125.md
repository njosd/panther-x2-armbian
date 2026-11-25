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


## 9. 既有专项报告交叉审校与关键边界澄清（2026-11-25）

本节重新读取 15 份既有专题报告，并与方向三 D3-2、方向四结项报告交叉核对。核心目的是区分 Realtek PHY driver 局部 config_init 与完整 MDIO/PHY 初始化序列，避免把两者混为一谈。

### 9.1 Realtek config_init 相近，不代表完整 PHY 初始化序列相同

四版本普通 RTL8211F-CG 的 Realtek driver config_init 主体具有共同点：
- RGMII PHY 内部 TX/RX delay 均关闭；
- PHYCR2 CLKOUT bit 0 由 probe 缓存状态及 DT 属性决定；
- config_init 对 PHYCR2 的软件 mask 仅包含 bit 0；
- 6.1.65、6.1.116、6.1.174、6.12.81 普通 CG 路径均会执行 generic PHY soft reset（6.12 对错误返回显式检查）。

但四版本完整 PHY 初始化序列并不相同。方向三 D3-2 与既有执行顺序报告已确认：
- 6.1.65 / 6.1.116 在 of_mdiobus_register() 返回后执行 JL2xx1 workaround 四次 MDIO 写入，其中 PHY address 0 / page 0xa43 / reg 0x19 写入 0x1801，随后 BMCR 写入 0x8000；
- 该动作发生在 PHY driver probe 之后、后续 stmmac_phy_setup() / phylink attach / config_init() 之前；
- 6.1.174 精确故障源码 c2f148d 与 6.12.81 均没有该四次写入段；
- 后续 Realtek config_init 的 PHYCR2 mask 只包含 bit 0，不会通过软件 RMW 主动恢复 bit 1、bit 5、bit 11 或 bits[13:12]。

正确表述是：四版本 Realtek 普通 CG driver 的局部 config_init 主路径大体相近，但黄金版本与故障版本的完整 PHY 初始化序列确有一个位于 STMMAC MDIO 注册阶段的额外 PHYCR2/BMCR 写入差异。该差异已由方向三结项，方向五只把它作为 PHY 状态与后续 driver 行为之间的关联输入，不重复审计。

### 9.2 0x1801 完整位域影响：以已修正结论为准

按仓库 2026-11-19 PHYCR2 完整位域报告及 RTL8211F-CG datasheet Table 38：
- bit 0：CLKOUT enable；
- bit 1：RXC enable；
- bit 5：PHY-mode EEE enable；
- bit 11：CLKOUT 125/25 MHz frequency select；
- bits[13:12]：CLKOUT SSC capability。

0x1801 不只是设置 CLKOUT 125MHz / enable；按完整 16-bit 写入，它同时清除 bit 1（RXC enable）和 bit 5（PHY-mode EEE enable），并写入 bits[13:12]=01 的非标准/保留编码。该位域解码已在既有报告完成，不重复查表。

必须保留一个尚未闭环的矛盾：6.1.116 曾正常建立 1Gbps link 并有正常网络基线，但源码确实发起 0x1801 写入；若该写入按字面完全生效且 reset 后保持，bit 1 被清零与 Panther 所需 RXC 路径之间存在明显张力。当前缺少 6.1.116 写入后的完整 PHYCR2 回读、BMCR reset 后回读及 RXC/CLKOUT 实际波形，不能任选“写入失败”“reset 恢复”或“RXC pin 不相关”作为事实。

历史报告中任何较早的“0x1801 只配置 125MHz CLKOUT”简化表述，均以 2026-11-18/19 完整位域更正为准；早期记录只保留研究时间线意义。

### 9.3 6.18.63 的 bit 5 清除不能等同于恢复 0x1801

6.18.63 目标驱动 realtek_main.c 的 rtl8211f_config_phy_eee() 仅对 PHYCR2 bit 5 做 mask-RMW 清零，源码注释为禁用 PHY-mode EEE，使 LPI 传递给 MAC。

与历史 6.1.65/6.1.116 workaround 整字写 0x1801 相比：
- 6.18.63 只清 bit 5，不清 bit 1 RXC enable；
- 不写 bits[13:12] 的 01 保留编码；
- 不设置/清除 bit 11 或 bit 0 的 CLKOUT 选择/使能；
- 其余 PHYCR2 位由 mask-RMW 保留；
- Panther 默认 DTS 没有 realtek,clkout-disable，因此 rtl8211f_config_clk_out() 不执行该分支中的 PHY soft reset；普通 config_init() 末尾执行 EEE bit 5 清除，不再无条件执行旧版 genphy_soft_reset()。

因此，6.18.63 的 bit 5 清除与 6.1.116 的 0x1801 在单个位层面的结果存在重合，但两者写入范围、RXC 影响、CLKOUT/SSC 影响和 reset 时序均不同。不能把 6.18.63 描述为重新引入 JL2xx1 workaround，也不能用 6.1.116 的 RXC 矛盾直接否定 6.18.63 的单 bit EEE 配置。

6.18.63 的 rtlgen_read_status() 另改为读取 MII_RESV2（源码常量 RTL_PHYSR）解码 speed/duplex；旧四版本读取 Page 0xa43 / Reg 0x12。该变化属于链路状态读取/报告路径，当前没有证据证明它影响普通 TX descriptor 发出。

### 9.4 既有专题报告交叉审校结果

| 专题 | 复核结果 | 当前有效结论/边界 |
|---|---|---|
| PHY ID / CG vs VD | 与既有报告一致 | Panther 完整 ID 0x001cc916 对应普通 RTL8211F-CG 编码；不重复安排 PHYID2 读取 |
| PHYCR2 bitfield / 0x1801 | 与完整位域更正一致 | bit1 RXC、bit5 EEE 均被整字写清零；bits[13:12]=01 不可视为已知有效 SSC 配置 |
| workaround 执行顺序 | 与方向三 D3-2 一致 | probe → 6.1.65/116 workaround → 后续 PHY setup/attach/config_init；6.1.174/6.12 缺失 workaround |
| PHYCR2 paged read API | 与 11/18 API 审计一致 | 内核 helper 的 save/select/read/restore 在 MDIO bus lock 下完成；无已确认的用户态原子 paged-read 接口 |
| 外部模块安全性 | 与 refcount/teardown 审计一致 | PHY refcount 不等于 STMMAC MDIO hardware lifetime；remove/unbind 排他同步仍未证明，不加载模块 |
| MDIO trace | 与 trace 审计一致 | tracepoint 只记录成功的 bus transactions，不记录失败事务；未启用、未执行现场追踪 |
| CLKOUT / RXC / U-Boot handoff | 与既有 P2 报告一致 | DTS/软件时钟声明不能证明物理引脚波形；JP/Ophub U-Boot 对 PHYCR2 的实际写入来源仍有限制 |
| PHY suspend/resume / WOL | 与源码差异一致 | 6.12 及 6.18 的 PM 分支演进不能外推为普通 cold-probe/TX 故障 |
| 6.18.63 EEE / speed status | 与目标源码一致 | bit5 单独清除；speed status 改读 MII_RESV2；均需保持目标内核专项，不混入历史四版本根因矩阵 |

### 9.5 方向五当前差异总矩阵

| 子项 | 6.1.65 | 6.1.116 | 6.1.174-rk35xx | 6.12.81-rk35xx | Panther 适用性 |
|---|---|---|---|---|---|
| 普通 RTL8211F-CG 精确 PHY ID | 0x001cc916 match | 同 | 同 | 同 | Panther 实际命中 |
| PHY driver RGMII 内部 delay | TX/RX=0 | 同 | 同 | 同 | 四版本一致；SoC GRF delay 属方向四 |
| PHYCR2 driver mask | 仅 bit0 | 仅 bit0 | 仅 bit0 | 仅 bit0 | 不覆盖 bit1/bit5/bits[13:12] |
| 普通 CG driver soft reset | config_init 执行 | 执行 | 执行 | 执行（显式检查错误） | 与 STMMAC 前置 workaround 是不同 reset |
| STMMAC JL2xx1 PHYCR2/BMCR workaround | 有 | 有 | 无 | 无 | 黄金/故障版本分组差异；效果未知 |
| paged PHY helper 锁保护 | save/select/read/restore 在锁内 | 同语义 | 同语义 | 同语义 | 未发现锁保护回归 |
| MDIO bus callback/地址检查 | 基础检查 | 基础检查 | 增加 addr/callback 防御检查 | 同后期方向 | Panther 地址 0/callback 正常，不命中异常路径 |
| PHYLIB polling state machine | 旧 state machine | 6.1 共同实现 | 6.1 共同实现 | 拆分锁内/锁外 post-work，引入 PHY_ERROR | 仅 MDIO/PHY 操作错误路径；无历史错误证据 |
| PHYLINK MLO_AN_PHY resolve | 使用 phy_state | PHY mode 语义相同 | PHY mode 语义相同 | 按 act_link_an_mode 重构，PHY mode 仍用 phy_state | 未发现 Panther 被改走 PCS in-band |
| PHY interrupt | driver 支持配置/handler | 同 | 同 | 同 | Panther IRQ=POLL，非当前主路径 |
| suspend/resume | genphy suspend/resume | 同 | 同 | RTL821x 专用 suspend/resume、PHY_ERROR 相关清理 | PM 条件路径，不等同普通 cold boot |
| LED framework | 无后续 DT LED 支持 | 增加 realtek,led-data | 调整 LED 写入位置 | LED framework / DT trigger | Panther 无 LED 属性/子节点，不命中 |

固定四版本源码 blob SHA：
- drivers/net/phy/realtek.c：6.1.65 cd4e6e4919539f69b515c70974f3f71a7de38c5f；6.1.116 3d29f78108e746b7a2f99772dabb8374fd78f278；6.1.174 9221cae79ea0f538d1a0cd5150052ee1fca4b605；6.12.81 ff15239ee63d137be5b4c9ba8538c3b02e414aa5。
- drivers/net/phy/phy-core.c：6.1.65 2c8bf438ea617aeae2e0d247a3d84ab29dd897df；6.1.116/6.1.174 相同 7e5dd14ec6994e76e85609f6412d717505e56a93；6.12.81 1f98b6a96c15355e5c318de0f161e426639c483c。
- phy_device.c、mdio_bus.c、phylink.c 四版本 blob 均不同；文件 SHA 本身不能证明 Panther 路径行为变化，结论必须以已核对的具体函数和条件分支为准。

### 9.6 方向五阶段判断

已完成：
- 首轮 Realtek 普通 CG driver 四版本差异；
- MDIO paged API 锁保护和错误恢复；
- PHYLIB state machine 与 PHYLINK MLO_AN_PHY resolver；
- 6.18.63 目标驱动 EEE、soft reset、speed status 补充差异；
- 15 份既有专题报告复核及与方向三/方向四的层级一致性审校；
- 方向五当前差异矩阵和适用性边界。

仍未完成：
- 对四版本 PHYLIB/PHYLINK 其他与 Panther 外接 PHY 路径直接相关的状态/协商回调，完成最后一次“是否有遗漏函数/分支”的覆盖确认；
- 汇总方向五证据等级、首次观察到的版本边界、普通 TX 相关性和不可验证事项；
- 更新方向五正式结项评估，明确哪些未决项属于静态范围内可完成、哪些必须保留为运行时/硬件证据限制。

**当前状态仍为方向五进行中，尚未结项。** 本轮只读仓库源码与报告；未访问 Panther X2、未读取或写入 PHY/MDIO 寄存器、未构建/安装/修改任何系统内容，未启动 B2.1。


### 9.7 PHYLIB / PHYLINK 剩余 Panther 相关回调覆盖（补充完成）

为关闭“是否遗漏普通 PHY polling / autoneg / link callback”的缺口，本轮补读四版本：
- drivers/net/phy/phy.c
- drivers/net/phy/phy_device.c
- drivers/net/phy/phylink.c
并沿 Panther 实际 MLO_AN_PHY + 外接 Clause 22 PHY 路径检查关键函数。

#### PHYLIB 函数级对照

| 函数/范围 | 四版本结果 | 差异意义 |
|---|---|---|
| phy_config_aneg() | 四版本函数体一致 | driver config_aneg / genphy_config_aneg 分派无变化 |
| genphy_config_aneg() | 四版本函数体一致 | 通用 Clause 22 autoneg 配置主路径无变化 |
| genphy_read_status() | 四版本函数体一致 | 通用链路状态、autoneg、LPA 读取主路径无变化 |
| genphy_update_link() | 四版本函数体一致 | link status 更新 helper 无变化 |
| phy_start_aneg() | 四版本函数体一致 | mutex 保护与 _phy_start_aneg() 调用顺序无变化 |
| phy_check_link_status() | 6.1 三版本相同；6.12 增加 link-up 后 EEE active 检查及 enable_tx_lpi 状态更新 | 仅 EEE/LPI 管理状态；不改变 link read 或普通 TX 发帧函数 |
| _phy_start_aneg() | 6.1 三版本内部 helper；6.12 改为可导出函数，核心 sanitize→config_aneg→check_link_status 顺序一致 | 符号可见性/API 变化，不构成 Panther 正常 autoneg 功能回归 |
| phy_start()/phy_stop() | phy_start 四版本一致；phy_stop 在 6.12 配合 PHY_ERROR 与锁外 post-work 调整 | 与 state-machine 错误处理变化同属错误/停止路径 |
| phy_state_machine() | 6.1.65/116/174 的 phy.c 文件 blob 完全相同；6.12 拆分锁内 _phy_state_machine 与锁外 post-work | 6.12 对 MDIO/PHY 错误记录、PHY_ERROR、suspend 执行位置有变化；成功 polling 主路径仍执行 phy_check_link_status |

6.12 phy_check_link_status() 在 PHY 从非 RUNNING 变为 RUNNING 时额外调用 genphy_c45_eee_is_active()，并更新 enable_tx_lpi；link down 时清除该状态。这是 EEE/LPI 功能路径，不改变 phy_read_status() 的调用顺序，也不构成普通 IPv4 UDP/DHCP TX 必然阻断条件。结合 6.18.63 对 PHY-mode EEE bit 5 的单 bit 配置，应把它们作为 EEE/LPI 专项，而不是与 PHYCR2 整字 0x1801 或 TX descriptor 路径混为一谈。

#### PHYLINK 函数级对照

| 函数/范围 | 四版本结果 | 差异意义 |
|---|---|---|
| phylink_connect_phy() | 四版本函数体一致 | 外接 PHY attach 接口主体无变化 |
| phylink_disconnect_phy() | 四版本函数体一致 | disconnect 主体无变化 |
| phylink_stop() | 四版本函数体一致 | stop 主体无变化 |
| phylink_start() | 6.1 三版本相同；6.12 主要使用 req_link_an_mode 输出当前配置日志，PHY start / resolve / polling 的主体顺序相同 | 未发现 Panther PHY start 被跳过或延迟的分支变化 |
| phylink_phy_change() | 6.1 三版本相同；6.12 在 PHY link down 时记录 link_failed | 与 resolver 的 link-down/retrigger 状态管理配套 |
| phylink_resolve() | 6.1 三版本的 MLO_AN_PHY 分支相同；6.12 重构为 act_link_an_mode 分支，PHY mode 仍直接使用 pl->phy_state | Panther 外接 PHY 状态来源未切换到 PCS/in-band |
| manual flow control | 6.1 在 MLO_AN_PHY 分支内调用；6.12 移至非-fixed mode 的共同分支 | PHY mode 仍会应用 manual flow control；不是 Panther 的分支丢失 |

6.12 phylink_resolve() 还把旧 mac_link_dropped 状态调整为 link_failed，并将 MLO_AN_PHY、MLO_AN_FIXED 与 PCS 状态解析改为按 act_link_an_mode 分支。PHY mode 仍然直接使用 PHY state，PHY link down 会触发 link-down/retrigger 处理。该变化属于状态机组织和链路失败重试管理。

另核对 STMMAC 的 stmmac_mac_config()：6.1.116、6.1.174、6.12.81 均为空实现（注释为 Nothing to do, xpcs_config() handles everything）。因此 phylink resolver 中旧版本在某些 legacy 条件下对同接口 speed/duplex/pause 变化调用 mac_config()，对 Panther 当前 STMMAC callback 不会产生额外寄存器写入；不能把该通用 phylink API 变化直接推定为 Panther GMAC 配置回归。

**覆盖结论：** Panther 外接 PHY 的 autoneg 配置、genphy status 读取、PHY start、phylink connect/disconnect、PHY mode link-state source 与 link-up/down callback 已完成最后一轮函数覆盖。没有发现 6.1.174 相对两个黄金版本新增的、在普通 PHY polling/autoneg 成功路径无条件阻断 link 或普通 TX 的 PHYLIB/PHYLINK 回归。6.12 的差异主要集中于 PHY error state/post-work、EEE/LPI bookkeeping、link_failed/retrigger 与 API 结构重构；均需相应错误、EEE 或 link-failure 条件，不应外推为已证实 TX 根因。

本轮未把 generic PHYLIB/PHYLINK 的其他 Clause 45、SFP、fixed-link、PCS in-band、cable-test、loopback、WOL 等非 Panther 路径扩展成新专题。


### 9.8 与方向三 D3-2 关联的 mac_requires_rxc / PHY_F_RXC_ALWAYS_ON 核对

方向三 D3-2 已发现故障源码起始版本新增 mac_requires_rxc；本轮沿 PHYLINK/PHYLIB 路径补齐其实际调用范围，避免遗漏 RXC 相关通用 PHY 管理行为。

- 6.1.65 / 6.1.116：STMMAC phylink_config 未设置 mac_requires_rxc；PHYLINK 没有 Panther 会命中的 phylink_prepare_resume 调用。
- 6.1.174（精确源码 c2f148d）：STMMAC 设置 mac_requires_rxc=true；在 system/runtime resume 路径调用 phylink_prepare_resume()。该 helper 只在 PHY 已 suspended 时调用 phy_resume()，源码注释解释其目的是某些 MAC resume 需要 RXC 先恢复。它不是普通 cold-probe / netdev open / 常规 TX 路径。
- 6.12.81：继续设置 mac_requires_rxc=true；phylink 在 PHY attach 时将 PHY_F_RXC_ALWAYS_ON 传给 phy_attach_direct()，并在 PCS pre-init 传递 rxc_always_on。phy_attach_direct() 将 flags OR 入 phydev->dev_flags。
- 6.12.81 实际 RTL8211F driver realtek.c 不引用 PHY_F_RXC_ALWAYS_ON，也不读取 phydev->dev_flags；Panther 是外接 RTL8211F-CG，不是需要 PCS pre-init 的 SFP/SerDes 路径。因此当前没有证据表明这个 flag 会改变 Panther RTL8211F 的普通 RGMII config_init 或普通发送行为。

**适用性判断：** 6.1.174 新增 mac_requires_rxc / resume 前恢复 PHY，与 RXC 时钟恢复语义有关，必须作为版本差异保留；但该 helper 的调用仅位于 resume 流程，不能解释首次冷启动阶段的 DHCP Discover 无法发出。6.12 将该能力扩展为 attach flag / PCS pre-init 传递，当前 Panther RTL8211F driver 不消费该 flag。该项与 6.1.116 workaround 清除 PHYCR2 bit1 RXC 的历史矛盾存在概念关联，但二者不是同一操作，也不能用一个源码 flag 推断历史 PHYCR2 实际值或 RXC 引脚波形。

