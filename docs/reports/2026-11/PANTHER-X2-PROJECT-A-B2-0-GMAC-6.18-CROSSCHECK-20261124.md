# Panther X2 项目 A：B2-0 GMAC 6.18.63 源码交叉核对与 G1 纠偏

- 日期：2026-11-24
- 阶段：B2-0，只读源码/既有报告审计
- 目标：把项目 B 已完成的 GMAC 专项结论准确映射到 B1 的 6.18.63 精确源码；识别 6.18 新增的风险和有利修复。
- 6.1.116 正常源码：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12.81 异常精确源码：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c
- B1 6.18.63 源码：ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9
- 没有构建、补丁、实机操作、MDIO/寄存器访问、接口重启或网络测试。

## 1. 首要纠偏：EEE 不能继续列为当前 TX 根因的高价值候选

回读项目 B 已有原始证据：
- 6.1.116 正常基线：ethtool --show-eee eth0 显示 enabled - active。
- 6.12.81 异常测试：EEE 显示 disabled。
- 项目 B 的 P1 收口报告已经指出：6.1.116 的 PHYCR2 整寄存器写 0x1801 按普通 RTL8211F-CG 数据手册会把 PHYCR2 bit5（PHY-mode EEE enable）写 0，但 6.1.116 的历史 ethtool --show-eee 仍为 enabled-active；没有 PHYCR2 readback，不能推断 MDIO 写成功或最终状态。
- ethtool --show-eee 的标准 EEE advertisement/negotiation 状态，不应未经驱动/PHYLIB 语义核对就等同于 PHYCR2 的 PHY-mode EEE bit。两者不是可直接互换的观测量。
- 6.18.63 Realtek PHY driver 中 rtl8211f_config_phy_eee() 清除 PHYCR2 bit5，注释是“Disable PHY-mode EEE so LPI is passed to the MAC”；这是 PHY 内部工作模式控制，不等于把标准 EEE advertisement 整体禁用。
- 6.18.63 的 RK3568 GMAC ops 没有设置 STMMAC_FLAG_EEE_DISABLE；该通用 flag 是另一层 STMMAC phylink LPI capability 控制，不能与 Realtek PHYCR2 bit5 混为一谈。

**结论：** PHY-mode EEE bit5 仍是 6.1.116 workaround 的一个寄存器副作用，6.18.63 也有显式、窄范围的 PHY driver 设置；但现有运行证据不支持“6.12 因为 EEE 没关闭而故障”。该项降为 PHY 内部 LPI 协同语义的背景差异，不列为当前 TX 主故障候选，不重做 EEE 实机测试。

## 2. 1500ms DMA reset delay：沿用项目 B 已收口结论，不再作为 Panther 主线

6.1.116 的 JL2xx1 workaround commit 49b5f340f346cc9a5b777499fce46150b691b70e 同时加入 DMA reset 前 msleep(1500) 与 MDIO 四次写入，但两者必须分开解释。

项目 B 唯一主路线图已明确：
- 1500ms delay 的原始目的为 JL2XX1/JL2101 快速启动时序；
- 后续实现将该等待限定在匹配的 PHY ID 场景；
- Panther PHY 已确认是 RTL8211F 家族，不是已确认的 JL2xx1；
- 不能因 6.1.116 正常且源码包含 delay，就推断该固定等待是 Panther 正常工作的必要条件。

因此本轮不再把 1500ms 当作高价值 Panther 根因，不建议移植。四次 MDIO 写入仍按 P1 closeout 结论保留：来源及副作用已审计、PHY 实际写入/最终寄存器值未验证，不重开猜测。

## 3. 新发现：6.18.63 已包含 Rockchip DMA reset failure 的 warning-and-continue workaround

6.18.63 精确源码 stmmac_main.c:stmmac_init_dma_engine() 包含：
```c
ret = stmmac_reset(priv);
if (ret) {
        netdev_warn(priv->dev,
                    "Failed to reset the dma, device will work with reduced throughput\\n");
        ret = 0;
}
```

来源 commit：
- ophub/linux-6.18.y@52e66c4a104b254d80e52da91342ea9580dc3bb7
- 日期：2026-09-26
- 标题：workaround for rockchip gigabit ethernet not able to init dma
- 提交说明提到至少 RK3288、RK3328 出现 Failed to reset the dma。

这项改动的性质必须准确描述：
1. 它没有修复 DMA software reset，也没有证明 DMA 已成功 reset；
2. 它把 reset error 从致命返回改成 warning，并继续后续 DMA configuration；
3. 它没有按 compatible 限定 RK3288/RK3328，因而代码效果会作用于使用该 STMMAC core 的其他平台，包括潜在的 RK3566 Panther；
4. 提交说明只报告 RK3288/RK3328，尚无证据说明该 workaround 对 RK3566 必要或安全。

**对 Panther 的意义：** 这不是 6.12.81 故障的解释（6.12.81 当时接口已 UP，且现有证据显示 TX 请求/descriptor/MMC 计数有活动），但它是 B2 恢复 6.18 STMMAC 时必须留意的诊断风险：如果出现 DMA reset failure，6.18 可能只警告并继续，不能把“probe/open 继续”当作 reset 成功。B2 日志审查必须把这条 warning 当成阻断性异常信号记录。

**当前处理：** 不立即删除或修改该 workaround。先确认 Panther 在 6.18 实际是否出现该 warning，以及后续 DMA channel/MAC 初始化和外部发送是否仍有效；这要等受控 B2 网络验证获批后才能验证。

## 4. 6.18.63 的 Rockchip GMAC clock 路径：恢复为接近 6.1.116 的稳健形式

对精确源码函数 gmac_clk_enable() 比较：

| 项目 | 6.1.116 正常 | 6.12.81 异常 | 6.18.63 B1 目标 |
|---|---|---|---|
| clock 获取/使能 | bulk clocks | 独立逐项 | bulk clocks |
| bulk enable 返回值 | 检查并返回 | 不适用 | 检查并返回 |
| PHY clock enable 失败 | 返回错误 | 对各单时钟 enable 未检查 | 返回错误，并回滚已启用 bulk clocks |
| settle delay | 5ms | 100–200µs | 5ms |
| RGMII delay 写入顺序 | delay value → interface/enable | interface/enable → delay value | delay value → interface/enable |

6.18.63 的 gmac_clk_enable()：
- 使用 clk_bulk_prepare_enable()；
- 检查 bulk enable 返回值；
- 单独启用 PHY clock 并检查返回值；
- 若 PHY clock enable 失败，新增 clk_bulk_disable_unprepare() 回滚，修复 bulk clock reference leak；
- 保留 5ms settle delay。

该回滚来自 a93dc81b5ddad2f0f7448f407b662891de0ccf4a（2026-09-28，fix bulk clock leak when the PHY clock fails）。

因此 6.18.63 的 Rockchip clock bring-up 并未继承 6.12.81 的逐项 enable + 忽略返回值 + 100–200µs 组合；它回到了与正常 6.1.116 更接近的 bulk/error-checked/5ms 路径，并进一步补足失败回滚。这是 B2 目标源码中的正向差异，但尚未实机验证。

注意：项目 B 已确认 Panther DTS 不提供 CSU phandle，6.12 的 CSU helper 在本机路径为 NULL/no-op；不要把 CSU disable 当作 Panther 故障机制，也不重复 CSU 调查。

## 5. 6.18.63 的 RK3568 RGMII GRF 写入顺序：与正常 6.1.116 一致

源码函数 rk3568_set_to_rgmii()：
- 6.1.116：先写 GMACx_CON0 的 TX/RX delay value，再写 GMACx_CON1 的 RGMII mode 与 delay enable；
- 6.12.81：先写 CON1 mode/enable，再写 CON0 delay value；
- 6.18.63：恢复为先 CON0 delay value，再 CON1 mode/enable。

Panther 使用 phy-mode="rgmii"，TX delay 0x30、RX delay 0x10，会命中 RK3568 ops 的 RGMII 设置函数。

这说明 6.18.63 在该点与已验证正常的 6.1.116 行为一致，而非继承 6.12.81 顺序。它是有利的源码回归结果，但由于没有 RGMII 物理波形，仍不能证明 delay/电气时序已经正确。

## 6. 6.18.63 的 PHY 生命周期补强

### 6.1 PHY resume 后恢复 RGMII delay

6.18.63 的 rtl821x_resume() 在 genphy_resume() 后等待 20ms，并调用 rtl8211f_config_rgmii_delay()。

来源 commit：
- 2f3e7a2965e851e073e9e6fdee7667f9db726bb8
- 日期：2026-11-04
- 标题：net: phy: realtek: restore RTL8211F RGMII delays on resume

提交说明记录 RTL8211F-VD 在软件 power-down 后可能丢失 RGMII TX/RX delay enable；恢复 carrier/speed 后接收仍异常。修复在 PHY resume 后重新配置 delay。

适用性：
- 这是 close/open、suspend/resume 生命周期的补强；
- Panther 实物完整 PHY 子型号未确认；
- 当前故障证据主要指向初始启动后的 TX 出线缺失，没有证明经历 PHY suspend/resume；
- 因此作为 6.18 正向修复保留，不直接认定为当前根因。

### 6.2 STMMAC PHY resume-before-hardware-setup

6.18.63 包含 phylink_prepare_resume()，在 __stmmac_open() 的 hardware setup/DMA reset 前恢复已 suspend 的 PHY，避免 RXC 尚未恢复就 reset DMA。

但项目 B 已精确核对 6.12.81 的 MTU reopen 路径：release 时会 disconnect PHY，reopen 时重新 attach，与该上游修复所针对的“PHY 仍连接但 suspended”条件不同；当前无 MTU reopen 或 DMA reset timeout 证据。因此这项补强仍是条件性保护，不解释现有 6.12 DHCP 故障。

## 7. 6.18.63 PHY-mode EEE 处理的正确边界

6.18.63 Realtek PHY driver rtl8211f_config_phy_eee() 清除 PHYCR2 bit5，意图是让 LPI 传递到 MAC。该函数属于 Realtek PHY 初始化，不能与：
- 6.1.116 JL2xx1 workaround 对 PHYCR2 的整寄存器写 0x1801；
- ethtool 标准 EEE enabled/active 状态；
- STMMAC STMMAC_FLAG_EEE_DISABLE；
混为一谈。

当前没有足够证据证明 bit5 的变化导致 Panther 普通 TX 帧无法出线。6.1.116 EEE active、6.12.81 EEE disabled 的既有结果反而说明标准 EEE 状态本身不能解释版本故障。此项不重做实机测试。

## 8. 本轮差异总表

| 项目 | 6.18.63 与 6.1.116 的关系 | 对 6.12.81 故障的意义 | 当前等级 |
|---|---|---|---|
| Rockchip clock bulk/error handling/5ms | 基本一致；6.18 另补失败回滚 | 6.18 未继承 6.12 逐项忽略错误/短等待实现 | 已确认正向差异 |
| RK3568 RGMII GRF 写入顺序 | 一致 | 6.18 未继承 6.12 的反向顺序 | 已确认正向差异 |
| STMMAC DMA reset error | 6.18 新增 warning-and-continue | 可能掩盖 reset 失败，必须作为 B2 诊断门槛 | 中高风险集成注意项，非根因 |
| PHY resume RGMII delay restore | 6.18 新增 | 只在 resume 路径相关 | 条件性正向修复 |
| PHY resume before DMA setup | 6.18 有，6.12 精确源码没有 | 当前 6.12 生命周期不满足已知补丁触发条件 | 条件性正向修复 |
| PHY-mode EEE bit5 | 6.18 显式 mask clear | 不能解释 6.12 标准 EEE disabled 的故障现象 | 降级背景差异 |
| 1500ms JL2xx1 delay | 6.18 无 | 项目 B 已判定不应套用于 Panther RTL8211F | 不作为主线 |

## 9. 下一步研究

1. 继续比较 6.18.63 与 6.1.116/6.12.81 的 GMAC1 MAC link-up / MAC TE enable 路径；只检查普通 RGMII 1000Mbps 分支，SerDes/USXGMII 不适用 Panther。
2. 继续核对 6.18.63 对 Panther 的 RK3568 ops、clock input from PHY、PHY clock handle 与 clk_phy 的实际资源解析；不重复已完成的 CRU parent 全树审计。
3. 对 warning-and-continue DMA reset workaround，追溯 RK3288/RK3328 原始问题背景及 stmmac_reset() 失败后的寄存器/状态假设；不读设备 MMIO，不把它直接改成 fatal。
4. 将所有已确认的 6.18 正向回归与 warning 风险加入 B2 组件账本。
5. EEE、1500ms、CSU、clock 5ms/100–200µs 的既有审计不重做；只有新版本代码或新证据改变前提时才重开。

## 10. 当前状态

B2-0 继续进行；B2-1 不放行。上述均为只读源码结果，未构建、未修改代码、未操作设备。当前没有根因定案，也没有提出补丁。


## 11. 6.18.63 普通 RGMII 1000Mbps MAC link-up / TX clock callback 复核

本轮继续按用户要求把研究范围限定在 Panther 实际命中的普通 RGMII、1000Mbps 分支，不扩展 SerDes/USXGMII。

### 11.1 MAC speed select / TE enable 主体

6.1.116 与 6.12.81 的 `stmmac_mac_link_up()` 对普通接口（包括 RGMII）都支持 SPEED_1000；两者先准备 MAC speed bits，再调用 Rockchip speed callback，配置 duplex/flow control，写 MAC_CTRL，最后调用 `stmmac_mac_set(..., true)`。

6.18.63 将 speed switch 合并为按 speed 选择的统一 switch，SPEED_1000 仍写入 `priv->hw->link.speed1000`；对 Panther RGMII 1000Mbps，选中的 MAC speed 字段没有变化。新加入的 unsupported-speed error 只影响未支持的 speed，不命中 1000Mbps。

因此，已知的 6.18.63 speed switch 重构没有发现能解释 Panther 千兆链路下普通 TX 失败的差异。

### 11.2 TX clock callback 重构及 Panther 实际调用链

6.1.116 / 6.12.81 使用旧的 `fix_mac_speed(bsp_priv, speed)` callback。6.18.63 改为：
- STMMAC `set_clk_tx_rate(bsp_priv, clk_tx_i, interface, speed)`；
- Rockchip glue `rk_set_clk_tx_rate()`；
- RK3568 ops 的 `set_speed = rk_set_clk_mac_speed`；
- `rk_set_clk_mac_speed()` 根据 speed 将 `clk_mac_speed` 设置为 2.5/25/125MHz。

Panther 的 RK3568 ops 没有设置 `clock.gmii_clk_sel_mask`，所以 `rk_set_clk_tx_rate()` 中额外的 RGMII GMII divider GRF 写入分支不命中；实际命中的是 ops->set_speed，最终调用 `clk_set_rate(clk_mac_speed, 125MHz)`。这与 6.1.116/6.12.81 的旧 speed callback 对千兆设置 125MHz 的目标一致。

6.18.63 的调用顺序略有重排：
1. 先写 MAC_CTRL 的 speed/duplex/flow-control 字段；
2. 调用 `set_clk_tx_rate()` 配置 TX clock；
3. 调用 `stmmac_mac_set(..., true)` 设置 MAC TE/RE。

旧版先调用 speed callback，再写 MAC_CTRL，最后启用 MAC。两条路径都在最终 MAC enable 前配置时钟；新路径在时钟设置前先写 MAC speed bits，但此时尚未执行最终 MAC enable。现有源码没有证据表明这会阻止首次发送。

### 11.3 返回值处理的边界

6.18.63 `set_clk_tx_rate()` 若失败会打印错误，但仍继续调用 `stmmac_mac_set(..., true)`。旧版 Rockchip speed callback 是 void，内部 `clk_set_rate()` 失败时打印错误，调用方同样继续启用 MAC。因此“设置 TX clock 失败仍启用 MAC”并不是 6.18 新引入的可确认回归；6.18 只是把错误通过 int 返回到 STMMAC 层记录。

**结论：** 对 Panther RGMII 1000Mbps，6.18.63 MAC speed selection 和 Rockchip TX clock callback 没有发现新的明确功能性回归。保留一个共同风险：若 clk_set_rate(125MHz) 失败，驱动仍会启用 MAC；但旧版也有相同结果，且目前没有任何 Panther 实机错误日志证明该调用失败。

## 12. 当前 G1/G2 研究收敛

- JL2xx1 的 1500ms wait：按项目 B 已收口结论，不再作为 Panther 主线。
- PHYCR2 0x1801：P1 已收口，不重复寄存器猜测；不移植写入。
- PHY-mode EEE bit5：降为背景差异，不能解释 6.1.116 EEE active 与 6.12.81 EEE disabled 的反向对照。
- 6.18.63 Rockchip clock bulk/error handling/5ms：与 6.1.116 正常版本接近，另有失败回滚。
- 6.18.63 RK3568 RGMII GRF delay 写入顺序：与 6.1.116 正常版本一致。
- 6.18.63 普通 RGMII 1000Mbps link-up speed selection/TX clock callback：未发现能解释当前故障的新差异。
- 6.18.63 warning-and-continue DMA reset：当前发现的主要集成风险；必须在 B2 实机日志中作为异常信号处理，不可把 reset failure 当作正常继续。

**B2-0 仍在进行。** 下一轮研究转向 6.18.63 GMAC1 probe/setup 与 Panther 精确 clock/supply/reset 资源解析的差异核验，重点确认哪些 6.18 generic refactor 实际命中 RK3566 GMAC1；不重复 CRU parent 全树、DMA descriptor、EEE、CSU 或 PHYCR2 已收口工作。


## 13. 6.18.63 RK3568 GMAC setup 与 Panther 资源实际命中关系

对 6.18.63 `dwmac-rk.c` 的 `rk_gmac_setup()`、`rk_gmac_clk_init()`、`rk_gmac_powerup()` 再做一轮按 Panther runtime DTS 条件的静态映射：

### 13.1 实际 compatible / ops

Panther GMAC1 的 compatible 包含 `rockchip,rk3568-gmac`，MMIO resource 为 `0xfe010000`。6.18.63 match table 对应 `rk3568_ops`，其寄存器表将 `0xfe010000` 映射为 GMAC id=1。

RK3568 ops 提供：
- `rk3568_init`
- `rk3568_set_to_rgmii`
- `rk_set_clk_mac_speed`
- GRF interface select mask
- 不要求 PHP-GRF；不要求 SGMII/PCS。

因此不会命中 RK3576/RK3588 PHP-GRF 路径，也不会命中 SGMII/QSGMII/XPCS 路径。

### 13.2 6.18.63 的 RGMII clock list

6.18.63 将公共 Rockchip clocks 列表定义为：
- `aclk_mac`
- `pclk_mac`
- `mac_clk_tx`
- `clk_mac_speed`

RMII 专用 clocks（`mac_clk_rx`、`clk_mac_ref`、`clk_mac_refout`）只在 RMII 时附加。6.18.63 不再把 `pclk_xpcs` 放进所有模式共用的 bulk list；Panther 为外置 RTL8211F + RGMII，且无 PCS-handle/SGMII 证据，因此没有发现缺少 XPCS clock 会影响 Panther 当前 GMAC1 路径的机制。

与 6.1.116 相比，旧版公共 bulk list 包含 `pclk_xpcs`；6.12.81 已经把 XPCS clock 获取/使能限定在 SGMII/QSGMII。6.18 的处理更贴近接口模式。该差异当前评为预期裁剪，不是 TX 故障候选。

### 13.3 外置 PHY 与 clk_phy 的概念边界

6.18.63 只在 PHY node 存在 `phy-is-integrated` 属性时获取 `clk_phy` 并准备 integrated PHY reset control。Panther 的 RTL8211F 是外置 PHY，没有该属性证据，因此不会走 integrated-PHY clock/reset 路径。

这里的 `clk_phy` 不能误解为“PHY 输出给 MAC 的 125MHz RGMII RX clock”。Panther 的 `clock_in_out=input` 是 Rockchip GMAC 时钟方向配置；外置 PHY 的 RGMII 时钟信号通过板级接口进入 MAC，并不意味着驱动必须通过 integrated-PHY 的 `clk_phy` handle 获取或 enable 它。

### 13.4 Setup / power-up 顺序

Panther 当前命中路径仍是：
1. `rk_gmac_setup()` 解析 `phy-interface`、`clock_in_out=input`、TX/RX delay、GRF 和 PHY regulator；
2. `rk_gmac_clk_init()` 获取上述四个 RGMII clocks；
3. `rk_gmac_powerup()` 执行 bulk clock enable；
4. `rk3568_set_to_rgmii()` 写入 GMAC1 GRF delay value 和 RGMII interface/enable；
5. 打开外置 PHY regulator；
6. STMMAC probe/open 后由 MDIO/PHYLIB 连接外置 RTL8211F。

没有发现 6.18.63 将 Panther 外置 PHY 错误识别为 integrated PHY，或把 RGMII 错送入 RMII/SGMII 路径的源码条件。

### 13.5 当前结论

6.18.63 的 RK3568 ops、RGMII clocks 和 external PHY 资源解析与 Panther runtime DTS 条件相符。尚未发现新的静态 setup/probe 错误。但这仍是源码控制流匹配，不是 6.18 网络功能的实机验证；实际 clock rate、GRF 写入是否成功和物理 RGMII 波形仍未验证。


## 14. 跨组件初始化时序：6.1.116、6.12.81 与 6.18.63 的组合核对

本节将 Rockchip glue、CCF clock、GRF、PHY regulator、STMMAC core 的先后关系放在同一条调用链审查，避免把每个函数单独判为“正常”后忽略组合效应。

### 14.1 三版共同的主时序骨架

三版 Panther GMAC1 的主流程均为：

1. rk_gmac_setup() 解析接口模式、clock_in_out、TX/RX delay、GRF、PHY regulator；
2. rk_gmac_clk_init() 获取 Rockchip glue 所需 clocks；
3. rk_gmac_powerup() 开始上电；
4. gmac_clk_enable(true) 使能 GMAC 时钟；
5. 配置 SoC GRF 的接口模式及 RGMII delay；
6. rk_gmac_phy_power_on(true) / rk_phy_powerup() 打开外置 PHY supply；
7. pm_runtime_get_sync()；
8. 调用 STMMAC platform/core probe，注册 MAC、MDIO 并连接 PHY；
9. 接口 open/link-up 时配置 MAC speed、TX clock 和 MAC TE。

因此 6.18.63 没有把 PHY regulator 上电移到 GMAC clock enable 之前，也没有把 RGMII GRF 配置放到 PHY regulator 之后。不能仅凭函数拆分或行号变化判断初始化顺序颠倒。

### 14.2 真正发生变化的是“时钟使能成功”与“后续配置继续”的组合

| 维度 | 6.1.116 | 6.12.81 | 6.18.63 |
|---|---|---|---|
| GMAC clocks | bulk prepare/enable | 逐项 prepare/enable | bulk prepare/enable |
| enable 错误处理 | 检查并返回 | 多项只检查 handle，不检查 enable 返回值 | 检查并返回 |
| 时钟稳定等待 | 5ms | 100–200µs | 5ms |
| clock selection | ops callback（RK3568 未设置） | ops callback（RK3568 未设置） | 新的 SoC GRF IO/CRU selector helper；RK3568 masks 未设置，实际不写此项 |
| RGMII GRF | set_to_rgmii，写入顺序 data→enable | 同左，但历史顺序曾为 enable→data | data→enable |
| PHY regulator enable | 调用后即使失败，helper 最终仍返回 0 | 同样不把 regulator_enable 错误传播给 powerup | 返回真实错误，失败会阻止继续 probe |
| PHY supply 与 MAC clock 的顺序 | clocks→GRF→supply | clocks→GRF→supply | clocks→GRF→supply |

**关键组合结论：** 6.12 的问题不只是“少等了约 5ms”，而是“逐项 enable 的错误可能被忽略 + 只等待 100–200µs + 后续仍执行 GRF/PHY supply/STMMAC probe”。如果某个时钟 enable 失败，后续阶段仍可能继续，形成表面 probe/link 成功但底层时钟条件不完整的状态。这是比孤立 delay 差异更完整、也更值得保留的组合候选。

但当前没有现场证据证明 6.12 的 Panther GMAC 任一必需 clock 的 enable 曾失败；也没有证据证明 100–200µs 对 RK3566 一定不足。因此它是**高价值机制候选，不是根因定案**。

### 14.3 6.18.63 对这组组合的处理

6.18.63 恢复了 bulk enable 的整体错误检查和 5ms settle；若 clk_phy enable 失败，还会回滚已启用的 bulk clocks。外置 RTL8211F 场景下 integrated-PHY clk_phy 不构成独立时钟依赖，但错误回滚仍是更完整的通用实现。

另一个正向变化是 PHY regulator enable 错误现在会向 rk_gmac_powerup() 传播；旧的 6.1.116/6.12.81 helper 在记录错误日志后仍无条件返回 0。6.18 因而避免在 PHY supply enable 失败时继续进入 STMMAC probe。

### 14.4 6.18 新增的 RK3568 PHY interface select 写入

6.18.63 的 RK3568 ops 新增 gmac_phy_intf_sel_mask = GENMASK_U16(6, 4)；rk_gmac_powerup() 在 set_to_rgmii() 之前通过 rk_get_phy_intf_sel(RGMII) 编码并写入 GMAC1_CON1 的接口选择字段，检查 regmap 写入错误。

旧 6.1.116 / 6.12.81 RK3568 ops 没有这组通用字段写入；其 rk3568_set_to_rgmii() 直接写 GMAC1_CON0 delay values 和 CON1 的 RGMII mode / delay enable。

静态字段位置：
- 新的 PHY interface select：CON1 bits 6:4；
- RGMII/SGMII mode：CON1 bit 7；
- RX/TX delay enable：CON1 bits 1/0；
- delay values：CON0。

这些字段在位域上不重叠，因此按代码写入顺序，6.18 先设置 bits 6:4，再由 set_to_rgmii() 设置 bit7、bit1、bit0，不会从写掩码本身推导出覆盖接口选择字段的冲突。它是 6.18 新增的硬件配置步骤，当前看属于显式补齐接口选择，而非已证实回归。

仍需核实 stmmac_get_phy_intf_sel() 对 RGMII 返回的枚举值与 RK3568 bits 6:4 的硬件编码是否完全一致；本轮尚未完成该 helper/SoC TRM 编码闭环，因此不把“位域不重叠”夸大为“编码必然正确”。

### 14.5 GRF 写入错误传播的组合边界

6.18 新增的通用 PHY interface select GRF 写入会检查返回值并在失败时关闭 clocks、终止 powerup；但 RK3568 set_to_rgmii() 内部两次 regmap_write() 仍为 void 且不检查返回值。该行为在 6.1.116/6.12.81 也存在，不是 6.18 新回归。

因此三版都存在一个共同的可观察性缺口：RGMII delay/mode 写入失败时，glue 层可能继续 PHY supply 上电和 STMMAC probe。当前没有 regmap 错误证据；不得把它单独定为故障原因。

### 14.6 当前组合判断

- **6.12.81 高价值候选：** clock enable error handling 退化 + 100–200µs settle + 无条件继续后续 powerup/probe。
- **6.18.63 正向变化：** bulk enable error propagation + 5ms settle + PHY clock enable 失败回滚 + PHY regulator error propagation。
- **6.18.63 新增项：** RK3568 PHY interface select field write；位域与 RGMII mode/delay enable 不重叠，编码值仍待核对。
- **三版共同缺口：** RK3568 RGMII delay/mode 的两次 regmap_write 返回值未向 powerup 传播。
- **尚未证明：** 6.12 任一必需 clock enable 失败、settle 不足、或 GRF 写入失败在 Panther 实际发生。

这轮没有进行设备操作、构建或补丁修改。

## 15. RK3568 PHY interface-select 编码与实际执行路径闭环

继续追踪 6.18.63 精确源码后，已确认：

- common.h 的 PHY interface select 编码定义为 PHY_INTF_SEL_RGMII = 1；
- stmmac_get_phy_intf_sel(PHY_INTERFACE_MODE_RGMII) 对 RGMII 返回该值 1；
- rk_encode_wm16(1, GENMASK_U16(6, 4)) 将 1 编码到 GMAC1_CON1 bit4，即 bits[6:4] 字段值为 001；
- RK3568 ops 的 gmac_phy_intf_sel_mask 确实为 bits[6:4]；
- 随后的 rk3568_set_to_rgmii() 使用 CON1 bit7 选择 RGMII，并设置 bits1:0 的 RX/TX delay enable；CON0 写入 TX delay 0x30、RX delay 0x10；
- interface select bits[6:4]、mode bit7、delay enable bits[1:0] 不重叠。

因此，6.18 对 Panther RGMII 的新增 interface-select 写入，按 Linux STMMAC interface 编码和 RK3568 ops mask 的组合结果为字段值 001；代码中没有看到与 mode/delay bits 的掩码冲突。当前源码层面可确认编码链条内部一致。仍未以 RK3566/RK3568 TRM 原始字段定义或实机 GRF readback 证明硅片最终解释，硬件寄存器实值仍未验证。

另外纠正一个路径边界：6.18 stmmac_prereset_configure() 只有在 plat_dat->set_phy_intf_sel 非 NULL 时才执行；Rockchip RK3568 glue 本身没有赋值该 callback。因此 Panther 这次 interface-select 写入并不是 stmmac_prereset_configure() 调用，而是在 rk_gmac_powerup() 中直接调用 rk_get_phy_intf_sel()、rk_encode_wm16() 和 rk_write_gmac_grf_reg() 完成。两条路径不可混淆。

**本项状态：** 源码编码链内部一致；硬件最终状态未验证；暂不列为故障候选。
## 16. 必需 clock 获取失败与 enable 失败的组合传播

继续把 rk_gmac_clk_init() 与 gmac_clk_enable() 合并审查后，发现 6.12 的风险比单纯“逐项 enable 忽略返回值”更完整：

- 6.1.116：使用 devm_clk_bulk_get_optional() 获取 bulk clocks；获取错误会由 rk_gmac_clk_init() 返回并阻止 probe 继续。stmmaceth 单独获取，失败同样返回错误。bulk enable 失败会阻止 powerup。
- 6.12.81：逐个 devm_clk_get() 获取 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed 等；获取失败只打印错误，不从 rk_gmac_clk_init() 返回。后续 gmac_clk_enable() 对 ERR_PTR handle 跳过 enable；对有效 handle 调用 clk_prepare_enable() 却不检查返回值，最后仍将 clk_enabled 设为 true。
- 6.18.63：恢复 devm_clk_bulk_get_optional() 获取 bulk clocks，并检查获取错误；gmac_clk_enable() 检查 bulk enable 返回值，失败即停止；PHY clock enable 失败时回滚 bulk clocks。stmmaceth 仍单独获取并检查。

这形成一个明确的跨函数状态差异：6.12 可能在某个 Rockchip glue clock handle 获取失败或 enable 失败后，仍将 clk_enabled 标记为 true，并继续 RGMII GRF、PHY supply、runtime PM 和 STMMAC probe；6.1/6.18 对 bulk 获取/使能失败会更早终止。

**候选强度：高价值组合机制。** 它比单独的 100–200µs settle 更有直接的错误传播因果链；但必须区分“代码允许此故障模式”与“Panther 实际发生此故障模式”。目前尚无历史日志证明 6.12 的具体某个 clock 获取/enable 失败。后续如发现 6.12 启动日志中 cannot get clock / Failed to get clocks / clock provider defer 等记录，才可把候选进一步提升；没有这些证据前不下根因结论。

此外，6.12 逐项获取的 RGMII 相关时钟句柄名称与 Panther DTS 中的 clock-names 应逐项核对，不能只看 RK3568 ops。现有 DTS 包含 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed 和 stmmaceth；在外置 PHY + RGMII 条件下，mac_clk_rx / clk_mac_ref / clk_mac_refout 属 RMII 专用，pclk_xpcs / clk_xpcs_eee 属 SGMII/QSGMII 专用。该名字映射目前没有发现 Panther 的明显缺项。

**本项状态：** 6.12 的错误传播退化已由精确源码确认；Panther 现场是否触发仍未知。
## 17. 重要纠偏：1500ms DMA reset 前等待是正常 6.1.65/6.1.116 的实际通用执行差异

本轮重新把用户 2026-11-24 实机通过的原版 6.1.65 纳入精确源码对照，发现此前将 1500ms delay 仅作为 JL2XX1 专用背景而降级，结论不够准确，现予纠正。

### 17.1 代码事实
- 正常 6.1.65 源码端点 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` 的 `stmmac_init_dma_engine()` 在 `stmmac_reset()` 前无条件执行 `msleep(1500)`。
- 正常 6.1.116 源码端点 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` 同样无条件执行该 1500ms wait。
- 引入该代码的 commit `49b5f340f346cc9a5b777499fce46150b691b70e` 标题为 `drv: net: ethernet: stmmac fix for jl2xx1 phy`；该提交同时在 stmmac_main.c 增加 1500ms wait，并在 stmmac_mdio.c 增加四次 MDIO 写入。
- 但 1500ms wait 写在通用 `stmmac_init_dma_engine()` 中，没有 PHY ID / compatible / SoC 条件判断。因此它不只是 JL2XX1 的条件性执行：Panther X2 在 6.1.65 和 6.1.116 上也会实际经过这段等待。
- 6.12.81 精确源码 `661b2d8` 的同一函数没有 1500ms wait；DMA reset 失败会记录 error 并返回，终止该次初始化。
- 6.18.63 精确源码 `aee4e35` 同样没有 1500ms wait；但 reset 失败改为 warning-and-continue，随后继续 DMA channel 初始化。

### 17.2 必须按组合解释，而不是孤立看 delay

这形成一条新的高价值跨组件时间/错误传播候选：

`RK GMAC powerup（clock/GRF/PHY supply） → STMMAC probe → 1500ms 等待（6.1.65/6.1.116 有，6.12/6.18 无） → DMA software reset → DMA channel/descriptor 初始化`

对比：

| 版本 | 1500ms DMA reset 前等待 | DMA reset 失败处理 | 已知网络结果 |
|---|---|---|---|
| 6.1.65 | 有，无条件 | error + abort | 用户 2026-11-24 实机网络全通 |
| 6.1.116 | 有，无条件 | error + abort | 已有实机网络全通 |
| 6.12.81 | 无 | error + abort | 已实机建立 1Gbps link，但 TX 外部接收故障 |
| 6.18.63 | 无 | warning + continue | B1 网络关闭，网络行为未验证 |

注意：6.1.65/6.1.116 的等待并非 PHY regulator enable 后的固定“PHY 上电等待”API，而是 STMMAC DMA engine 初始化中的通用等待；但从调用顺序看，它确实发生在 Rockchip glue 已开启 PHY supply、STMMAC 准备 DMA reset 之后。其实际硬件作用可能是让 PHY/相关时钟/GMAC 状态有额外稳定时间，也可能仅为 JL2XX1 特定问题的副作用。源码只能证明等待存在及执行位置，不能证明它对 Panther 必需。

### 17.3 对之前结论的修订

- 保留 P1 已收口决定：不重开 JL2XX1 四次 MDIO 写入的寄存器猜测，不把它们移植到 RTL8211F。
- **撤销“1500ms delay 不属于 Panther 主线”的绝对表述。** 更准确结论是：该等待的提交意图来自 JL2XX1 workaround，但实现是 STMMAC 通用、无条件执行；因此它是 Panther 两个已验证正常版本共有的实际时序条件，必须纳入版本组合差异。
- 6.12.81 的“无等待 + reset failure abort”与 6.18.63 的“无等待 + reset failure warning-and-continue”必须分开看。后者比前者多一层可能掩盖 reset 失败的风险。
- 不能直接推断 1500ms 是 Panther 正常工作的必要条件；也不能因为其提交说明写 JL2XX1 就把它排除。需要结合 6.1.65、6.1.116 两条实机成功基线和后续异常版本继续追踪。

### 17.4 下一步静态核查

1. 追踪 6.12/6.18 移除 1500ms 的具体提交及其理由，确定是上游重构、特定硬件 workaround 清理，还是 Ophub/Rockchip patchset 差异。
2. 比较 6.1.65/6.1.116 的 `stmmac_reset()` 与 6.12/6.18 实现、reset poll 条件、DMA reset bit 清除判定及调用上下文；只读源码，不读设备 MMIO。
3. 检查等待被删除后，是否同时有其他 PHY power-up、clock stabilization 或 DMA reset 时序补偿改动；以调用顺序和真实条件为依据，不猜测。
4. 与 6.12.81 既有“接口 UP、TX descriptor 回收、MMC TX 计数增长、外部 0 收包”证据交叉解释：该结果不排除 reset/初始化边界的部分异常，但也不支持直接断言 DMA reset 失败。
5. 6.18.63 若未来进入获批实机阶段，DMA reset warning 必须单独作为异常门槛；在此之前不启动、不构建、不打补丁。

**当前评价：** 1500ms wait 的存在/删除与 DMA reset 错误处理形成版本间真实差异，列为 B2-0 高价值时序组合候选；是否为 Panther 必需仍未验证。
## 18. 原版 6.1.65 实机黄金线的精确源码映射补充

将 2026-11-24 原版 Armbian 6.1.65 TF 启动网络全通记录与其最可能源码端点结合后，新增以下对照：

- 原版 6.1.65 精确版本提交候选：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（提交说明 up to 6.1.65；构建时间与 2023-12-07 镜像时间相邻，仍非 Image 二进制的逐字节来源证明）。
- 该版本的 dwmac-rk.c blob 为 514f1ac0dea2d49cd4f581a48db2b02160187d0a，与 6.1.79/6.1.112/6.1.116 的既有 blob 完全相同。
- 该版本 Panther DTS blob 为 1e3153c392d8de617f72b3133eaeddf45569bde8，与 6.1.79/6.1.112/6.1.116 的既有 DTS blob 完全相同。
- 该版本 pinctrl-rockchip.c blob 为 0276b52f37168423346316089a39417082e6f1f6；首 pin 失败仍执行 if (ret) 返回错误，不存在 if (ret && cnt) 的吞错行为。
- 该版本 stmmac_init_dma_engine() 有无条件 msleep(1500)，之后 stmmac_reset() 失败则 error + abort。
- 该版本 rtl8211f_config_init() 按 RGMII interface 清除 PHY 内 TX/RX delay，更新 ALDPS/PHYCR1；对 has_phycr2 条件执行 PHYCR2 配置，最后 genphy_soft_reset()。这与 6.1.116 的主体初始化流程高度一致；6.1.116 后续增加的 LED 配置不改变这里的 RGMII delay 分支。

因此 6.1.65 不仅是“系统网络功能通过”的实机基准，也为 6.1.116 的 GMAC glue、Panther DTS、DMA reset 前等待和 pinctrl 错误传播提供了更早的源码正向对照。下一轮版本回归表必须同时以 6.1.65 与 6.1.116 为正常端点，不得只用 6.1.116 代表所有正常版本。

**来源边界：** 6.1.65 实机网络全通是用户提供的直接测试证据；4428... 是时间和源码版本匹配的高置信度源码候选。尚未把原始 Image 的 build-id、完整 .config、modules 与该 commit 做到逐字节构建来源闭环。
## 19. 新增研究主线：非网络子系统可能间接阻断 TX

根据用户提出的关键假设，B2-0 不再把故障搜索边界限定为网络相关目录。需要正式纳入“非网络组件/通用内核机制改变了 GMAC TX 所依赖的系统条件”的研究主线。即使 GMAC、STMMAC、PHY、RGMII 和协议栈配置各自正确，内存/DMA/cache、IOMMU、总线/QoS、IRQ、时钟/电源管理、固件或全局设备树也可能通过跨子系统依赖影响 TX。

### 19.1 目前已核对的 DTS 事实

对照源码端点：
- 正常 6.1.65 候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`；Panther DTS blob `1e3153c392d8de617f72b3133eaeddf45569bde8`。
- 异常 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；Panther DTS blob `d517c99841cf9d724a61cd31acf9437acbb131e6`。
- 目标 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`；Panther DTS blob `a0a08476f45fb2d602fd7312def6f587f33fb91e`。

Panther GMAC1 子节点在三个版本中均保留核心配置：`phy-mode=rgmii`、`clock_in_out=input`、`phy-supply=vcc_3v3`、同一组 GMAC1 M0 pinctrl、同一 reset GPIO/延迟、同一 TX/RX delay 值、同一 AXI 配置 `blen=<0 0 0 0 16 8 4>`、`rd_osr_lmt=8`、`wr_osr_lmt=4`，以及单 TX/RX queue 的 MTL 配置。6.12 的 SoC GMAC node 增加了 XPCS clocks，但 Panther 使用 RGMII，当前驱动条件路径不获取 RMII/XPCS 专用资源；这不是已证实故障。

注意：三个版本的 Panther DTS 文件整体 blob 不同，不能由“GMAC 子节点核心字段相同”推断整个设备树相同。必须继续比较根节点、memory/reserved-memory、全局 DMA coherency、CPU/cache、GIC/IRQ、CRU/PMU、IOMMU、QoS 和其他新增节点。

### 19.2 当前可排除或降级的一个常见误区：Rockchip IOMMU

在目前读取的三个 Panther GMAC 节点中，均未见 `iommus` 属性；GMAC1 没有直接绑定 Rockchip IOMMU 的设备树关系。RK356x SoC DTS 中 VPU/RGA/VOP 等多媒体设备有各自 IOMMU 节点，但不能仅因 IOMMU 驱动或多媒体组件存在，就认定它会重映射 GMAC DMA。当前没有证据支持“GMAC TX 被 Rockchip IOMMU 直接拦截”。

不过，DMA API、cache coherency、DMA mask、物理地址可达性仍是独立问题；无 `iommus` 不等于 DMA/cache 一定正确。需要追踪 STMMAC 设备 DMA mask、descriptor/buffer 分配与 map/unmap/sync 路径，并核对 ARM64 平台 coherent/non-coherent 属性及相关内核配置。

### 19.3 非网络影响 TX 的优先研究矩阵

| 方向 | 可能的跨组件影响路径 | 当前状态/下一步证据 |
|---|---|---|
| DMA API / cache coherency / memory attributes | TX descriptor 或 packet buffer 对 DMA 不可见、地址/同步错误 | 高优先级静态审计；核对 DMA mask、dma_map/unmap/sync、arm64 DMA ops、DTS coherency 属性及 CONFIG_DMA_* 差异 |
| AXI/interconnect/QoS / bus arbitration | GMAC 发起 DMA 读请求后被总线仲裁、QoS 或时钟条件限制 | 高优先级；比较 GMAC AXI 参数、QoS 节点/驱动、CRU ACLK_GMAC1 及系统 interconnect 变更；寻找超时/总线错误证据 |
| GIC / IRQ / NAPI / softirq | TX completion IRQ 未送达或延迟，队列停止/descriptor 回收异常 | 高优先级；将既有 descriptor 回收证据与 IRQ handler/NAPI 路径对照，确认计数点与中断处理关系 |
| 内存布局 / CMA / reserved-memory / SWIOTLB | DMA buffer 地址超出控制器能力或映射失败 | 中高优先级；比较启动参数、memblock、reserved-memory、DMA zone 与 mask |
| CPU cache / coherency / architecture config | 新配置或补丁改变 DMA 一致性维护语义 | 高优先级；比较实际 `.config` 和 arm64 DMA 相关源码/补丁，避免只看 GMAC Kconfig |
| runtime PM / genpd / CRU / reset | GMAC/AXI 时钟、总线域或相关供电被其他 PM 操作关闭/降频 | 中高优先级；核对 GMAC 所属 power-domain（若有）、runtime PM 引用计数与 suspend/resume 路径 |
| firmware / SCMI / secure-world / boot handoff | 固件设置的时钟、复位、QoS 或安全访问策略发生变化 | 中优先级；先找 Panther 相关日志/设备树依赖，不假设所有 SCMI warning 与 GMAC 有关 |
| 网络之外的内核新增功能 | 通用 DMA、netdev、workqueue、RCU、lockdep、security 或 vendor patch 改变执行时序/内存状态 | 作为差分搜索面；必须找到具体依赖链，不做全仓库无目标猜测 |

### 19.4 重要证据边界

项目 B 已有现象：软件 TX 请求、TX descriptor 回收和 MAC MMC TX 计数有活动，但外部监听器未收到帧。它把问题定位到“软件提交之后、外部线缆接收之前”，但不能证明 DMA 真的把正确字节送入 MAC，也不能证明 MAC MMC 计数位于 RGMII 物理发送之后。下一步必须精确定位：
1. TX descriptor OWN/complete 状态由谁更新，CPU 是否在正确 cache/DMA 同步后观察到；
2. TX packet buffer 的 DMA address 是否处于硬件可访问范围，DMA mapping 是否成功；
3. MMC TX counter 在 MAC 数据路径的具体统计位置，是否可能在实际 RGMII 发射前递增；
4. TX completion IRQ、NAPI/cleanup 与 MAC 发射之间的先后关系；
5. AXI DMA 读请求是否可能被总线错误/时钟/QoS 条件阻断。

因此，descriptor 回收 + MMC TX 计数增长不能直接等同于“DMA 已成功把帧送到 PHY”。也不能据此直接把问题归咎于 PHY。

### 19.5 对 B2 干净系统策略的正式调整

干净系统不应简单等于“只启用网络驱动”。它应成为可审计的最小依赖闭包：
- 必须保留：CPU/内存管理、DMA API 与 arm64 cache maintenance、必要的 CRU/GRF/GPIO/regulator、pinctrl、GIC/IRQ、必要的时钟/复位框架、基础网络栈、STMMAC/DWMAC、RTL8211F PHYLIB、静态 IP/ARP/ICMP 测试工具。
- 初期不主动启用：Wi-Fi/蓝牙、GPU/VPU/RGA/NPU、多媒体、显示、音频、摄像头、USB 网络、VPN/防火墙复杂规则、容器和非必要后台服务。
- 但“初期不启用”不等于随意裁掉通用内核子系统；尤其不能删除 DMA/cache、IOMMU 核心依赖、IRQ、时钟/电源框架等基础设施。IOMMU 若与 GMAC 无绑定，可先不加载具体多媒体 IOMMU master，但必须以依赖关系证明。
- 先以 6.1.65/6.1.116 的正常行为作为参考，构建依赖闭包和差异表；之后逐类恢复非必要组件，若恢复某类后故障出现，再通过最小差异确定触发组件或组合。

本节新增的是研究范围和验证策略，不代表已经找到非网络根因。无设备操作、无构建、无补丁。B2-0 继续，B2-1 不放行。