# Panther X2 项目 A：B2-0 / G1 DMA reset、JL2xx1 workaround 与 PHY EEE/RXC 源码复核

- 日期：2026-11-24
- 阶段：B2-0，只读源码审计
- 目标硬件：Panther X2 / RK3566 / GMAC1 fe010000 / RGMII / RTL8211F（实物完整子型号未确认）
- 源码端点：
  - 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
  - 异常 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
  - B1 6.18.63 源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`
- 本轮没有构建、补丁、设备操作、MDIO 读写或寄存器访问。

## 1. 本轮最重要的新发现：6.1.116 的 workaround 同时清除了 RTL8211F PHY-mode EEE

先前已确认，commit `49b5f340f346cc9a5b777499fce46150b691b70e`（2022-12-24，标题 `drv: net: ethernet: stmmac fix for jl2xx1 phy`）同时引入：
1. `stmmac_init_dma_engine()` 中 DMA software reset 前的 `msleep(1500)`；
2. `stmmac_mdio_register()` 中四次对 PHY address 0 的 MDIO 写入。

本轮把写入值与 6.1.116、6.12.81、6.18.63 的 Realtek PHY driver 逐层关联后，发现一个此前没有被提升为主线的交叉差异：

四次写入中的第二条：
```c
stmmac_mdio_write(new_bus, 0, 31, 2627); /* page 0x0a43 */
stmmac_mdio_write(new_bus, 0, 25, 0x1801); /* PHYCR2 */
```

按 RTL8211F-CG PHYCR2 定义，`0x1801` 的 bit 5 为 0，即清除 PHY-mode EEE enable。它还会改变 CLKOUT、RXC 及保留位字段，不能把整个写入简单描述成“只开 125MHz CLKOUT”。

更关键的是：
- 6.1.116 的 Realtek `rtl8211f_config_init()` 最后对 PHYCR2 只按 `RTL8211F_CLKOUT_EN` mask 恢复/设置 CLKOUT bit0；它不会把 bit5 恢复为 1。因此 workaround 清除的 bit5 会保留下来。
- 6.12.81 的 `rtl8211f_config_init()` 仍只管理 ALDPS、RGMII delay、CLKOUT 和 soft reset；没有找到等价的 PHY-mode EEE bit5 清除。
- 6.18.63 的 Realtek PHY driver 已有明确的 `rtl8211f_config_phy_eee()`：
  ```c
  /* Disable PHY-mode EEE so LPI is passed to the MAC */
  return phy_modify_paged(phydev, RTL8211F_PHYCR_PAGE, RTL8211F_PHYCR2,
                          RTL8211F_PHYCR2_PHY_EEE_ENABLE, 0);
  ```
  并在 `rtl8211f_config_init()` 中调用。

这构成一条值得高度重视的跨版本语义链：

| 版本 | PHY-mode EEE bit5 行为 |
|---|---|
| 6.1.116 正常 | JL2xx1 workaround 的 `0x1801` 清除 bit5，后续 config_init 不恢复 |
| 6.12.81 异常 | 不再执行四次 MDIO 写入，Realtek PHY config_init 也未找到等价清除 |
| 6.18.63 B1 源码 | 不再使用 JL2xx1 通用 MDIO 写入；Realtek PHY driver 改为显式清除 PHY-mode EEE bit5 |

**当前判断：** 这是目前 G1 下最具体的跨版本候选之一。6.1.116 与 6.12.81 之间的差异不只是“旧 workaround 有/无”，还可能是 PHY-mode EEE 的最终状态发生变化；6.18.63 又出现了更明确、更窄范围的 PHY driver 实现。它可能与 PHY RXC/LPI 行为有关，但尚不能认定为 TX 故障根因。

## 2. 6.1.116 四次写入的真实作用范围和执行顺序

6.1.116 `stmmac_mdio_register()` 的顺序：
1. `of_mdiobus_register(new_bus, mdio_node)` 成功；
2. fixed-link 检查；fixed-link 会跳过这组写入；
3. 非 fixed-link 执行四次 PHY address 0 写入；
4. 随后才进入设备树 PHY node / MDIO node 后续路径。

Panther 是外置 PHY、非 fixed-link，源码控制流上属于会执行写入的路径。

`of_mdiobus_register()` 内部会注册设备树 PHY child；`phy_device_register()` 最终执行 `device_add()`。因此 Realtek PHY probe 会在该注册阶段被触发。6.1.116 `rtl821x_probe()` 会先缓存 PHYCR2 的 CLKOUT bit0；随后 STMMAC 的四次写入修改 PHYCR2；再到 PHY attach/config_init 阶段，Realtek config_init 仅对 bit0 做 masked update，保留 workaround 写入的 bit5=0。此控制流解释了为何 EEE bit5 清除可以在后续 PHY config_init 中继续保留。

边界：
- PHY address 0 对 RTL8211F 的广播语义已由数据手册确认，默认可响应 broadcast；实物是否关闭广播响应未知。
- 驱动没有检查这四次 `stmmac_mdio_write()` 的返回值，源码存在写入不等于每次实机都成功。
- PHY 实物完整型号/硅修订未确认；普通 CG 与 VD-CG 对 PHYCR2 的寄存器布局不同。
- 因此“可能影响 Panther PHY”有较强的源码和数据手册依据，但“实机确实写入成功”仍未验证。

## 3. 1500ms delay：与 MDIO 写入同一提交，但作用不能混为一谈

`msleep(1500)` 位于 `stmmac_init_dma_engine()`：
```
检查 DMA 参数
设置 enhanced descriptor 标志
msleep(1500)
stmmac_reset()          // DMA software reset
stmmac_dma_init()
初始化 DMA channels / RX / TX
```

它发生在每次相关 DMA hardware setup 的 reset 之前，不是 TX packet fast path 的延时。

版本对照：
- 6.1.116：存在 `msleep(1500)`；
- 6.12.81：不存在；
- 6.18.63：不存在，改为 `stmmac_prereset_configure()` 后直接 `stmmac_reset()`。

commit `49b5f340` 的提交说明只有 JL2xx1 workaround 标题，没有解释为什么要等待 1500ms，也没有说明延时与四次 MDIO 写入各自的必要性。没有证据能证明 1500ms 是为 Panther 的 RTL8211F 专门设计，也不能证明它就是 6.1.116 正常的原因。

**特别注意：** 单纯等待不能恢复一个已经处于 BMCR power-down、停止 RXC 的 PHY。若根因是 PHY 已 suspend，正确的处理是先恢复 PHY/RXC，而不是无限延长等待。故 1500ms 与 RXC resume 必须分开分析。

## 4. 6.18.63 对 RXC/DMA reset 的新处理

6.18.63 STMMAC 主线代码出现几项 6.12.81 尚未具备的处理：

### 4.1 明确声明 STMMAC 需要 RXC
`stmmac_phylink_setup()`：
```c
/* Stmmac always requires an RX clock for hardware initialization */
config->mac_requires_rxc = true;
```
6.12.81 已有 `mac_requires_rxc = true`，所以该要求本身不是 6.18 才出现的差异。

### 4.2 PHY suspend 后 reopen 前恢复
6.18.63 的 `__stmmac_open()` 在 `stmmac_hw_setup()` 前调用 `phylink_prepare_resume()`。该函数只有在 `mac_requires_rxc`、PHY 存在且 `phydev->suspended` 时才执行 `phy_resume()`。

上游提交 `11ab26d2abdef3e038736624e7b98bfb2cf772eb`（2026-08-11，标题 `net: stmmac: resume PHY before hardware setup when opening the interface`）明确记录：
- MTU change 后 PHY 可能保持连接但被 `phylink_stop()` suspend；
- PHY power-down 时可以停止 RXC；
- DMA software reset 需要 RXC；
- 若等到 `phylink_start()` 才恢复 PHY，恢复发生得太晚；
- 该问题在 RK3566 + RTL8211F-VD + RGMII 设备上有实际案例。

**适用性限制：** 6.12.81 的 `stmmac_change_mtu()` 使用旧路径 `stmmac_release()`，其中会 `phylink_disconnect_phy()`，再由 reopen 重新 attach PHY；它与上游提交描述的“MTU change 只 stop phylink、保留已连接但 suspended PHY”路径并不完全相同。因此不能直接把该 2026 上游 reopen bug 归因于 6.12.81 Panther 故障。它对后续 6.18 版本和其他 reopen/suspend 场景仍是重要参考。

### 4.3 DMA setup 时阻止 EEE LPI 停止 RXC
6.18.63 `stmmac_hw_setup()` 在 DMA reset 前后使用：
```c
phylink_rx_clk_stop_block(priv->phylink);
ret = stmmac_init_dma_engine(priv);
...
phylink_rx_clk_stop_unblock(priv->phylink);
```
phylink 实现说明：当该 PHY 支持相应 EEE 操作且配置允许时，block 会暂时禁止 PHY 在 EEE LPI 状态停止 RXC，unblock 后恢复原能力。

6.12.81 尚未找到上述调用。是否在 Panther 的具体平台能力/feature 组合下实际启用此 block，仍需按 phylink 配置条件核对，不能只凭函数存在认定已命中。

### 4.4 1500ms 不是简单被 6.18 的某个等待替代
6.18 的 `phylink_prepare_resume()` 注释明确提到 IEEE 802.3 允许 PHY 恢复 RXC 最长 500ms，但当前实现没有额外等待。它的目标是先恢复 suspended PHY，而不是复制旧版 1500ms 固定延时。

因此 6.18 是通过更精确的 PHY 生命周期/RXC 控制改善 reset 前提，不是简单把 1500ms 改成另一个等待值。

## 5. 6.18 Realtek PHY driver 与 6.1 workaround 的关系

6.18.63 的 Realtek PHY driver 将相关配置拆成窄范围函数：
- `rtl8211f_config_aldps()`
- `rtl8211f_config_rgmii_delay()`
- `rtl8211f_config_clk_out()`
- `rtl8211f_config_phy_eee()`

其中 PHY-mode EEE 由独立 masked update 清除 bit5；CLKOUT 由单独 helper 按 DT property 控制；不再使用整寄存器常量 `0x1801`。

相较 6.1.116 的全局 STMMAC MDIO workaround，这种方式更明确地限定到 Realtek PHY driver，避免对所有非 fixed-link STMMAC 总线都发出 address 0 广播写入，也避免把 CLKOUT、RXC、EEE 和保留位混在一个整寄存器常量中。

6.18 PHY driver 的具体型号差异仍需检查：普通 RTL8211F-CG 与 RTL8211F-VD-CG 的 CLKOUT 寄存器页不同，驱动已对 VD 单独处理 CLKOUT；不能仅凭打印名称 RTL8211F 判断具体 PHY 型号。

## 6. 当前证据评级

| 线索 | 已确认 | 未确认 | 当前评级 |
|---|---|---|---|
| 6.1.116 workaround 清除 PHY EEE bit5；6.12.81 没有等价清除；6.18.63 显式清除 | 三个源码端点的代码语义 | Panther PHY 是否启用/协商 EEE、bit5 实机状态、该状态是否造成 TX 故障 | **高价值候选，优先继续** |
| 1500ms DMA reset 前等待 | 6.1.116 有，6.12/6.18 无；与 MDIO 写入同一 commit | 延时原始设计意图、Panther 必要性、去掉后是否会导致启动时序问题 | 中等候选，暂不直接恢复 |
| 四次 MDIO broadcast 写入 | 6.1.116 非 fixed-link 全局执行；6.12/6.18 无 | 实际写入成功、PHY 型号/修订、保留位行为、实物广播状态 | 高风险历史 workaround，不应原样移植 |
| 6.18 PHY resume before DMA reset | 上游明确修复特定 PHY suspend/RXC 场景 | Panther 是否触发相同 reopen 场景；6.12 旧 MTU path 与该场景不同 | 条件性候选，不直接解释 6.12 故障 |
| 6.18 EEE RXC stop block | 6.18 存在，6.12 未发现；代码有明确条件 | Panther phylink config 是否使该功能实际生效 | 中高价值候选 |

## 7. 下一步研究顺序

1. **优先查 PHY EEE 状态链：** 对照 RTL8211F 数据手册和 PHY driver，确认 bit5 的语义及不同 CG/VD 修订；继续查 6.18 显式清除 PHY-mode EEE 的历史来源与原因。
2. **核对历史证据：** 只回读已有 6.1.116/6.12.81 日志和项目 B 的 EEE 测试记录，查是否有 EEE advertisement、LPI、RXC 或 link transition 线索；不要求重测。
3. **核对 6.12.81 的 PHY config 结果：** 现有源代码显示它没有清除 bit5；需要确认运行时 PHY 是否真的启用/协商 EEE，避免从源码直接跳到根因。
4. **单独评估 1500ms：** 查找是否有其他平台或 JL2xx1 issue 说明该等待的作用；没有厂商/硬件依据前不恢复。
5. **继续 G2/G3/G4：** GMAC clock enable、CSU 和 RGMII GRF 顺序仍按 B2-0 计划继续；本轮发现不替代这些研究。

## 8. 禁止事项与阶段状态

- 不把 JL2xx1 四次 MDIO 写入直接复制到 RTL8211F。
- 不因 1500ms 被删除就直接加回延时。
- 不执行 MDIO 读写、PHY reset、寄存器访问、MMIO/devmem、接口重启或驱动重载。
- 不构建、不刷写、不改变设备。
- B2-0 继续进行，B2-1 不放行。

**阶段结论：** G1 已出现一个更有解释力的方向：正常 6.1.116 workaround 的一个副作用（清除 PHY-mode EEE）与 6.18.63 后来明确加入的 Realtek PHY EEE 配置语义一致，而 6.12.81 正好缺少两者之间的显式处理。它可能最终只需要一个针对 PHY EEE 状态的窄范围修正，但是否能解释 Panther 的实际 TX 物理故障，仍需先核对 PHY 型号、EEE 协商和既有运行日志。不能提前定案。
