# Panther X2：RTL8211F PHYCR2 probe 时序与上游驱动交叉核对（2026-11-19）

## 1. 本轮目标

承接以下既有报告，不重复已完成工作：
- `116-JL2XX1-WORKAROUND-RUNTIME-PATH-AUDIT-20261118.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`
- `116-RTL8211F-PHYCR2-REFCOUNTED-PHY-LOOKUP-AND-TEARDOWN-AUDIT-20261118.md`

本轮重新读取三个精确源码版本的 `drivers/net/phy/realtek.c`，并核对 STMMAC 的 MDIO 注册与 PHY setup 调用顺序；另对照近期上游 Realtek PHY driver 对 PHYCR2/CLKOUT SSC 的定义。

没有运行设备命令，没有访问 MDIO，没有写 PHY 寄存器，没有改变接口/驱动/内核。

## 2. 三个目标版本的 Realtek PHY driver 行为

源码基线：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.1.174 候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

### 2.1 rtl821x_probe()

三版均：
1. 读取 page 0xa43 / reg 0x18（PHYCR1）；
2. 读取 page 0xa43 / reg 0x19（PHYCR2）；
3. 仅缓存 PHYCR2 的 bit 0：`priv->phycr2 = ret & RTL8211F_CLKOUT_EN`；
4. 若 PHY node 有 `realtek,clkout-disable` 才清除缓存的 bit 0。

6.12 另增加 `devm_clk_get_optional_enabled(dev, NULL)`，但 Panther 归档的 PHY 节点只有 compatible/status/reg，没有 clocks 属性；因此不能据此推断 Panther 6.12 多启用了 PHY 外部 clock。

### 2.2 rtl8211f_config_init()

三版均使用 mask 仅包含 bit 0 的 `phy_modify_paged(0xa43, 0x19, BIT(0), priv->phycr2)`，然后执行 `genphy_soft_reset()`（6.12 对返回值显式检查）。

所以 config_init 不会清除 PHYCR2 的 bit 11 或 bits[13:12]。这与 2026-11-18 已归档结论一致，本轮是精确源码复核，不是新发现。

## 3. 关键时序：116 的 PHY driver probe 先于 STMMAC workaround

6.1.116 的 `stmmac_dvr_probe()` 调用顺序为：

```
stmmac_mdio_register()
  └─ of_mdiobus_register()
      └─ 创建 MDIO PHY device / 绑定 PHY driver
          └─ rtl821x_probe()
              └─ 读取并缓存 PHYCR2 bit 0
  └─ stmmac_mdio_register() 中的 JL2xx1 workaround
      ├─ page 0xa43 / reg 0x19 = 0x1801
      └─ page 0 / reg 0 = 0x8000（BMCR soft reset）
返回 stmmac_dvr_probe()
  └─ stmmac_phy_setup()
      └─ 后续 phylink/PHY 初始化
          └─ rtl8211f_config_init()
              ├─ 使用 probe 时缓存的 bit 0
              ├─ 仅修改 PHYCR2 bit 0
              └─ genphy_soft_reset()
```

源码证据：
- 6.1.116 `stmmac_mdio_register()` 在 `of_mdiobus_register()` 返回后才执行 workaround（行约 485–515）。
- 6.1.116 `stmmac_dvr_probe()` 在 `stmmac_mdio_register()` 返回后才调用 `stmmac_phy_setup()`（行约 7341–7360）。
- 6.12 `stmmac_mdio_register()` 不再含 workaround 四次写入；MDIO 注册返回后同样调用 `stmmac_phy_setup()`。

由此可得：
- 116 的 RTL8211F probe 读取 PHYCR2 时，尚未执行 STMMAC workaround；
- workaround 随后写入 0x1801；
- 后续 config_init 使用 probe 时缓存的 bit 0，并只更新 bit 0；bit 11、bit 12 等不在 mask 中；
- 因此，标准 PHY config_init 不会覆盖 workaround 写入的 bit 11/bit 12；
- 但 PHY 内部 soft reset 对这些 vendor bits 的保持行为，仍需硬件手册或实机读回证明。

这进一步确认了 116 workaround 并非在 RTL8211F probe 之前执行，也不是被 probe 立即覆盖。

## 4. 对 0x1801 解释的上游交叉核对

目标 6.1.116/6.1.174/6.12.81 源码中的旧 Realtek PHY driver 将：
- PHYCR2 定义为 page 0xa43 / reg 0x19；
- CLKOUT_EN 定义为 BIT(0)；
- probe 仅缓存 BIT(0)；
- config_init 仅修改 BIT(0)。

近期上游内核已经出现重构后的 `drivers/net/phy/realtek_main.c`，其中进一步定义：
- `RTL8211F_SYSCLK_SSC_EN = BIT(3)`
- `RTL8211F_CLKOUT_SSC_EN = BIT(7)`
- `RTL8211F_CLKOUT_SSC_CAP = GENMASK(13, 12)`

并在新的配置路径中说明：通过 PHYCR2 bits 7、12、13 配置 CLKOUT SSC capability，参考 EMI improvement parameters application note 1.2 section 2.3 的 reg25 写值 `0x38C3`。

这说明 PHYCR2 的 bits[13:12] 并非在所有资料版本/后续驱动语境下都能笼统视为无意义；它们被后续上游驱动用于 CLKOUT SSC capability。旧 datasheet 中 reserved 的标记不能直接作为最终语义结论。

但 0x1801 的 bits[13:12] = 01，而新上游驱动对 capability 的配置是通过明确 mask 和应用说明值 0x38C3（bits[13:12] = 11）设置；因此仍不能推定 0x1801 是标准 SSC 配置。它更像旧 vendor workaround 中的特定值，其含义需对应芯片版本和应用说明进一步核对。

上游源码参考：
- https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/%2B/0de672c7e1920acc5675d0dd22718c4f6e6b4447/drivers/net/phy/realtek_main.c
- https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/%2B/58c806d867bf265c6fd16fc3bc62e2d3c156b5c9/drivers/net/phy/realtek.c

## 5. 本轮结论分级

### 已确认
1. 三个目标内核版本的 Realtek PHY driver 都在 probe 时读取 PHYCR2，并只缓存 bit 0。
2. 三版 config_init 都只修改 PHYCR2 bit 0，不清除 bit 11 / bits[13:12]。
3. 116 的 STMMAC workaround 在 `of_mdiobus_register()` 返回之后执行，因此晚于 RTL8211F driver probe。
4. 116 的后续 `stmmac_phy_setup()` 在 MDIO 注册及 workaround 返回之后执行。
5. 近期上游驱动已把 PHYCR2 bits 7、12、13 用于 CLKOUT SSC 配置，旧 datasheet reserved 描述需谨慎解读。
6. 目标 6.12 PHY node 没有 clocks 属性，新增 optional PHY clock 获取不能直接解释 Panther 的差异。

### 未确认
1. 0x1801 的 bits[13:12]=01 在 Panther 实际 RTL8211F silicon revision 上的具体含义。
2. BMCR soft reset 是否保留 PHYCR2 bits 11/12。
3. 116 workaround 写入是否改变 PHY 输出波形、RXC/CLKOUT 或 GMAC 的 RX 行为。
4. 6.1.174/6.12 的故障是否由缺失 workaround 导致。

## 6. 下一步建议

静态代码核查在此方向已接近边界。继续翻阅相同的 `realtek.c` 或重复证明 probe/config_init 的 mask 没有价值。

如果要把该线索推进到因果判断，真正缺少的是 PHY 状态证据：
- 116 正常版本在 workaround 后的 PHYCR2 值；
- 故障版本启动后的 PHYCR2 值；
- 如可能，PHYCLKOUT/RXC 的实际频率/波形。

仓库现有归档尚未发现上述 PHYCR2 专项读回值。此前报告已完成只读访问安全性评估，但尚未加载模块、也未读取寄存器。下一步应先检查是否能通过现有内核接口安全只读访问；若必须开发临时模块，则必须先解决 STMMAC parent remove/unbind 与 MDIO 硬件访问的同步问题。未经用户明确授权，不访问设备。

不建议再做更多泛化源码搜索；如果只允许静态分析，下一项有限工作应是对照 6.1.116/6.12 U-Boot 源码是否有对同一 PHY page/register 的写入，随后结束这条静态分支并给出结论。
