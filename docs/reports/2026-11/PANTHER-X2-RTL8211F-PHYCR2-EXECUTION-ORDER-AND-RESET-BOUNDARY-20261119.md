# Panther X2：RTL8211F PHYCR2 写入的精确执行顺序与复位边界（2026-11-19）

## 本轮目的

继续核实一个关键问题：6.1.116 的 STMMAC JL2xx1 workaround 是否发生在 RTL8211F PHY driver probe 之前或之后，以及后续 PHY config_init 会不会覆盖它。

本轮只查源码和仓库既有记录；没有运行设备命令，没有读取或写入 PHY 寄存器，没有修改系统或接口。

源码基线：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.1.174 候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

## 1. 精确执行顺序

6.1.116 的正常路径：

```
stmmac_dvr_probe()
  └─ stmmac_mdio_register()
      └─ of_mdiobus_register(new_bus, mdio_node)
          ├─ 注册 MDIO bus
          ├─ 解析 DT 子节点 ethernet-phy@0
          ├─ 创建并注册 phy_device
          │   └─ device_add(&phydev->mdio.dev)
          │       └─ driver core 匹配 RTL8211F
          │           └─ rtl821x_probe()
          │               ├─ 读取 PHYCR1
          │               └─ 读取 PHYCR2，只缓存 bit 0
          └─ 返回 stmmac_mdio_register()
      ├─ fixed-link 检查（Panther 没有 fixed-link）
      ├─ JL2xx1 workaround 四次 MDIO write
      │   ├─ page=0xa43
      │   ├─ reg 0x19 = 0x1801
      │   ├─ page=0
      │   └─ BMCR=0x8000（触发 PHY soft reset）
      └─ phy_node/mdio_node 判断并跳过后续全地址扫描
  └─ stmmac_phy_setup()
      └─ 后续 phylink/PHY attach 与接口启动
          └─ RTL8211F config_init
              ├─ 修改 PHYCR1 中 ALDPS 相关位
              ├─ 配置 RGMII TX/RX delay
              ├─ PHYCR2 仅修改 bit 0（保留其他位）
              └─ genphy_soft_reset()
```

依据：
- `stmmac_main.c`：`stmmac_dvr_probe()` 先调用 `stmmac_mdio_register()`，随后才调用 `stmmac_phy_setup()`。
- `stmmac_mdio.c`：四次 JL2xx1 写入在 `of_mdiobus_register()` 返回后、`phy_node || mdio_node` 检查之前。
- `drivers/net/mdio/of_mdio.c`：`__of_mdiobus_register()` 注册 bus 后同步解析 DT PHY 子节点；`of_mdiobus_register_phy()` 最终调用 `phy_device_register()`。
- `phy_device.c`：`phy_device_register()` 调用 `device_add(&phydev->mdio.dev)`，将 PHY 设备加入 driver core。
- `realtek.c`：RTL8211F 的 `rtl821x_probe()` 读取 PHYCR2 并缓存 bit0。

所以，**在正常 Panther DT 路径中，RTL8211F PHY driver probe 先于 STMMAC workaround；workaround 后续再写 PHYCR2 并触发一次 BMCR reset。**

## 2. 后续 Realtek config_init 对 PHYCR2 的实际影响

三份源码（6.1.116、6.1.174 候选、6.12.81）中的 RTL8211F driver 都执行相同的关键逻辑：

Probe：
```c
priv->phycr2 = ret & RTL8211F_CLKOUT_EN;
if (of_property_read_bool(dev->of_node, "realtek,clkout-disable"))
    priv->phycr2 &= ~RTL8211F_CLKOUT_EN;
```

Config init：
```c
phy_modify_paged(phydev, 0xa43, RTL8211F_PHYCR2,
                 RTL8211F_CLKOUT_EN, priv->phycr2);
```

其中 mask 是 `BIT(0)`，不是整个 PHYCR2 寄存器。因此：
- config_init 会将 bit0 恢复为 probe 时缓存的状态（除非 DT 声明 clkout-disable）；
- 它不会主动清除或重写 bit11；
- 它不会主动清除或重写 bit12；
- 其后调用 `genphy_soft_reset()`。

仓库中 Panther 运行时 PHY 节点没有 `realtek,clkout-disable` 属性，因此驱动会保留 probe 时读到的 bit0 状态。

## 3. 对 6.1.116 与后续版本差异的准确解释

6.1.116：
1. PHY driver probe 先读取原始 PHYCR2，只缓存 bit0。
2. STMMAC workaround 随后将 PHYCR2 写为 0x1801，并执行 BMCR reset。
3. 后续 Realtek config_init 只修改 bit0，保留其余字段，再执行一次 generic PHY soft reset。

6.1.174/6.12.81：
1. PHY driver probe 读取原始 PHYCR2，只缓存 bit0。
2. STMMAC 不再执行 0x1801 workaround。
3. 后续 Realtek config_init 只修改 bit0，再执行 generic PHY soft reset。

因此两条路径的确定差别是：**116 在 config_init 之前额外写入了 PHYCR2 的 0x1801，并触发一次额外的 PHY soft reset；后续版本没有这一步。**

## 4. 仍然不能从源码推出的事实

上述执行顺序已由源码闭环，但仍不能证明：
- 0x1801 的 MDIO 事务均成功。workaround 没有检查四次 write 的返回值。
- PHY 是否接受 bit12 的 reserved 编码。
- BMCR reset 后 bit11/bit12 是否在该具体 RTL8211F silicon revision 上保持。
- 后续 generic soft reset 是否保留 bit11/bit12。
- PHY CLKOUT 的电气波形、频率和幅度是否符合 GMAC 输入要求。
- 缺少这一步是否就是 6.1.174/6.12 RX/DHCP 故障的根因。

尤其需要区分两种概念：
- **源码字段保留：** Realtek config_init 的 MDIO RMW mask 不会改 bit11/bit12。
- **硬件 reset 保留：** PHY 执行 BMCR soft reset 后，芯片内部是否保持这些 vendor bits，需要芯片手册明确说明或只读实机回读；软件 mask 本身不能证明硬件 reset retention。

## 5. 下一步建议

静态代码路径已基本闭环。继续盲目查同一组 C 函数的收益不高。接下来优先做两件事：

1. 对照 RTL8211F 官方资料，查明 PHYCR2 bit11/bit12 在 BMCR soft reset 后的 retention 规则，以及不同 RTL8211F/RTL8211F-VD 型号差异。
2. 检查已有 6.1.116 实机采集是否有 PHY page 0xa43/reg 0x19 的只读回读记录；若没有，再评估一个严格只读的 MDIO 读取方案。读取前必须先解决仓库既有报告指出的 STMMAC remove/unbind 生命周期同步问题，并取得用户明确授权。

不建议直接移植 JL2xx1 workaround，也不建议直接加入 1500ms 延时。当前只能把它们视为版本行为差异，不能作为已证明修复方案。

## 6. 关联报告

- `116-JL2XX1-WORKAROUND-RUNTIME-PATH-AUDIT-20261118.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`
- `116-RTL8211F-PHYCR2-REFCOUNTED-PHY-LOOKUP-AND-TEARDOWN-AUDIT-20261118.md`
- `PANTHER-X2-RTL8211F-CLKOUT-WORKAROUND-REGRESSION-20261119.md`
