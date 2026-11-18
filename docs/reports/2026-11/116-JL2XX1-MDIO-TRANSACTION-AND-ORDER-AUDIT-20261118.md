# Panther X2 6.1.116 JL2xx1 MDIO workaround：事务返回值与执行时序审计（2026-11-18）

## 1. 本轮范围

承接 `116-JL2XX1-WORKAROUND-RUNTIME-PATH-AUDIT-20261118.md`，只核查：

- 四次 MDIO write 的调用结果是否被检查；
- write 回调实际能报告什么；
- MDIO bus reset、PHY 扫描与四次 workaround 写入的先后关系；
- 6.1.174 / 6.12 是否存在等价底层写入实现。

没有重复实机测试，没有修改设备。

源码基线：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.1.174 候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 6.12：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

## 2. 四次写入的返回值完全被忽略

6.1.116 `stmmac_mdio_register()` 中：

```c
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

四个调用均没有赋值给 `err/ret`，也没有检查返回值。因此即使某次写操作返回负数，代码仍会继续执行后续写入，最终仍可能走到 `bus_register_done` 并将 `new_bus` 保存到 `priv->mii`。

这是明确的源码事实，不是推测。

## 3. write 回调可以检测什么，不能检测什么

6.1.116 / 6.1.174 的 `stmmac_mdio_write()` 做以下操作：

1. `pm_runtime_resume_and_get()`，失败时返回负值；
2. 轮询 GMAC MII address 的 `MII_BUSY` 位，最多等待 10 ms；超时返回 `-EBUSY`；
3. 向 MII data 寄存器写数据；
4. 向 MII address 寄存器写入 PHY 地址、寄存器地址和 WRITE/BUSY 控制位；
5. 再次轮询 `MII_BUSY`，最多等待 10 ms；
6. 返回轮询结果。

6.1.12 的 `stmmac_mdio_write_c22()` 虽然拆分为通用底层写函数和 Clause 22 wrapper，但行为相同：runtime PM、busy 检查、写 data/address、等待 busy 清除、返回状态。

因此该返回值主要表示：

> **GMAC MDIO 控制器是否完成了这次管理总线事务，或在控制器忙状态/运行时电源恢复时遇到错误。**

它不能证明 PHY 对寄存器写入作出了有效应答，更不能证明目标寄存器内容已经变成指定值。Clause 22 MDIO write 的这条控制器路径没有读回寄存器，也没有通过 PHY ACK 机制核验目标寄存器状态。

即使返回 0，也只能说明控制器事务完成，不能作为 PHY 寄存器生效的充分证据。

## 4. MDIO reset / PHY 扫描 / workaround 写入的真实顺序

6.1.116 中 `stmmac_mdio_register()` 调用 `of_mdiobus_register(new_bus, mdio_node)`。

该调用进入 `__mdiobus_register()`，其顺序是：

1. 注册 MDIO bus device；
2. 初始化 bus 锁；
3. 处理 bus-level reset GPIO（若有）；
4. 调用 `bus->reset(bus)`（若已设置）；
5. 扫描 PHY 地址并注册发现的 PHY；
6. 返回 `of_mdiobus_register()`；
7. 回到 `stmmac_mdio_register()`；
8. 执行四次 JL2xx1 workaround write；
9. 检查 fixed-link / phy_node 等后续分支并保存 bus。

Panther DTS 使 `mdio_bus_data->needs_reset = true`，因此 bus reset callback 被设置为 `stmmac_mdio_reset()`。这条 reset callback 与四次 JL2xx1 写入不是同一回事；前者在 PHY 扫描前执行，后者在 MDIO 注册及 PHY 扫描成功返回后执行。

`stmmac_mdio_reset()` 还可能处理 GMAC 节点的 `snps,reset` GPIO 和 delay 属性；在非 GMAC4 时会执行一次 dummy MII address 写入。它不等同于四次 JL2xx1 PHY 寄存器写入。

因此，四次特殊写入并非让 PHY 首次可被扫描/发现的前置条件；在正常 Panther DTS 路径中，PHY 已经通过 MDIO bus 注册扫描后，驱动才发起这四次写入。

## 5. 与 6.1.174 / 6.12 的对照

- 6.1.174 的 `stmmac_mdio_register()` 已没有四次 workaround write；
- 6.12 的 `stmmac_mdio_register()` 也没有；
- 6.1.174 的底层 `stmmac_mdio_write()` 与 6.1.116 同属相同的 busy-poll + data/address register transaction 逻辑；
- 6.12 拆分为 `stmmac_mdio_write()` 和 `stmmac_mdio_write_c22()`，Clause 22 wrapper 仍执行 runtime PM、MII_BUSY 等待、写寄存器、等待完成并返回状态。

目前没有发现 6.1.174 或 6.12 通过另一处代码自动补做这四次 JL2xx1 特殊寄存器写入的证据。

## 6. 本轮结论

### 已确认

1. 116 正常 Panther 路径会发起四次 PHY 地址 0 的 MDIO write。
2. 四次调用的返回值均被丢弃；一次或多次控制器事务失败不会因此阻止后续代码继续。
3. MDIO bus reset 和 PHY 扫描发生在这四次写入之前。
4. write callback 返回成功不等于 PHY 已确认目标寄存器内容。
5. 174 / 612 没有这四次特殊写入，但底层普通 Clause 22 MDIO 写机制仍然存在。

### 尚未确认

1. 116 实机上四次 MDIO 控制器事务是否全部成功；
2. RTL8211F 是否接受并保留 page 2627 / reg25=0x1801 的写入；
3. 最后的 BMCR=0x8000 是否触发了 PHY reset，以及 reset 后寄存器状态；
4. 该 JL2xx1 workaround 对 RTL8211F 是否有正面作用、无影响或副作用。

### 对根因判断的修正

不能把 116 的四次 workaround 描述为“已成功配置 RTL8211F”。准确表述应为：

> **116 正常路径确实在 PHY 已扫描后，向地址 0 发起四次特殊 Clause 22 MDIO 写操作；驱动忽略了所有返回值，也不做寄存器读回，因此目前只证明调用发起，不证明事务全部成功或 PHY 配置生效。**

下一步最有价值的是追查 patch 原始提交和 RTL8211F / JL2xx1 的寄存器定义、page 2627 的来源，确认这组操作究竟会对 RTL8211F 做什么。不要据此直接修改设备或重跑测试。
