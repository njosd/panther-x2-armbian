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
