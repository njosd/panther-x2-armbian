# 6.1.116 Panther X2：JL2xx1 workaround 两项代码的实际执行路径审计（2026-11-18）

## 审计问题

不能把“源码中存在”直接当作“Panther X2 实机确实执行”。本报告沿 6.1.116 的 stmmac 调用链、Panther X2 DTS 和条件分支核实：

1. DMA 初始化前的 `msleep(1500)` 是否在正常网卡启动时执行；
2. MDIO 注册后的四次 PHY 地址 0 写入是否会被 Panther X2 的设备树条件跳过。

源码基线：
`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`

Panther X2 DTS：
`arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`

## 1. 1500 ms 延时：不是 probe 阶段，而是在网卡 open 阶段

调用链已确认：

```
net_device ndo_open
  stmmac_open()
    __stmmac_open()
      stmmac_hw_setup()
        stmmac_init_dma_engine()
          msleep(1500)
          stmmac_reset()
```

关键源码事实：

- `stmmac_open()` 调用 `__stmmac_open()`；
- `__stmmac_open()` 在 PHY attach 成功后调用 `stmmac_hw_setup()`；
- `stmmac_hw_setup()` 调用 `stmmac_init_dma_engine()`；
- `stmmac_init_dma_engine()` 在 DMA reset 前无条件执行 `msleep(1500)`；
- 该函数中 1500 ms 前没有 PHY 型号、DTS 属性或其他条件判断。前面的 DMA 配置合法性检查失败则会提前返回，但那种情况下网卡 open 本身也不会成功。

因此：

> **只要 6.1.116 Panther 网卡成功执行了一次正常的接口 open/up，1500 ms 延时就必然执行一次。**

如果接口经历 down/up，每次重新 open 都会再次执行。它不是单纯“系统启动/probe 时延时一次”。

实机执行的边界：目前没有 6.1.116 当时的函数级时间戳或 trace 记录。因此可确认的是：成功 open 的代码路径必经该延时；若历史记录确认 116 的 eth0 成功 up，则可据此判定当次执行。不能声称已从历史日志直接测得 1500 ms 的实际睡眠时长。

## 2. 四次 MDIO 写入：Panther DTS 不满足跳过条件，正常 MDIO 注册后必定发起

四次写入位于 `stmmac_mdio_register()`，顺序如下：

```
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

执行前的条件分支：

1. `mdio_bus_data` 必须存在，否则函数直接返回 0；
2. `of_mdiobus_register(new_bus, mdio_node)` 必须成功，否则走错误分支；
3. 检查 `phylink_node` 下是否存在名为 `fixed-link` 的子节点；若存在，跳到 `bus_register_done`，跳过四次写入；
4. 若没有 `fixed-link`，立即执行四次写入；
5. 写入之后才检查 `priv->plat->phy_node || mdio_node` 并跳过后续 PHY 扫描。

Panther X2 116 DTS 的实际相关内容：

```
&gmac1 {
    phy-mode = "rgmii";
    phy-handle = <&rgmii_phy1>;
    ...
};

&mdio1 {
    rgmii_phy1: ethernet-phy@0 {
        compatible = "ethernet-phy-ieee802.3-c22";
        reg = <0>;
        status = "okay";
    };
};
```

DTS 中没有 `fixed-link`。同时 `phy-handle` 指向 `ethernet-phy@0`，即 PHY 地址 0。

`stmmac_probe_config_dt()` 的条件也已核实：

- Panther 不是 fixed-link，因此 `stmmac_dt_phy()` 中 `mdio = !of_phy_is_fixed_link(np)` 为 true；
- 因此分配 `plat->mdio_bus_data`，并设置 `needs_reset = true`；
- `phy-handle` 被解析为非空 `plat->phy_node`；
- `plat->phylink_node` 指向 GMAC 节点本身。

`rk_gmac_probe()` 调用 `stmmac_dvr_probe()`。后者在非 TBI/RTBI PCS 条件下调用 `stmmac_mdio_register()`。Panther 的接口模式是 RGMII，不属于被跳过的 TBI/RTBI 分支。

所以在以下正常成功条件下：

- Panther GMAC probe 成功；
- MDIO bus 注册成功；
- 没有 fixed-link（DTS 已确认）；

四次写入就会执行到。它们位于 `phy_node` 判断之前；`phy-handle` 非空并不会跳过写入，反而只会在写入之后跳过额外的全地址扫描。

### 重要限定：执行 write 调用 ≠ PHY 肯定接受并生效

四次 `stmmac_mdio_write()` 的返回值没有被检查。因此源码可以证明驱动会向 MDIO bus 发起这四次写操作，但不能单凭源码证明：

- MDIO 总线上每次事务都成功；
- PHY 地址 0 当时确实响应；
- PHY 接受 page 2627 / reg25 的写入；
- PHY soft reset 已完成；
- 写入对 RTL8211F 产生了预期效果。

这些属于寄存器事务/实机 PHY 状态层面的证据，不能由调用路径代替。

## 3. 本轮结论分级

| 项目 | 源码路径判断 | 实机层面的判断 |
|---|---|---|
| DMA reset 前 1500 ms | 正常接口 open 成功时必经；每次 open 执行 | 需结合历史 eth0 up 记录；没有函数级时间戳证明实际时长 |
| MDIO 四次写入 | Panther 无 fixed-link；成功 MDIO 注册后必定发起四次 write 调用 | 事务成功及 PHY 寄存器实际生效尚未证明 |

## 4. 对 6.1.116 → 6.1.174 → 6.12 回归分析的影响

目前可以把“116 只是包含代码但运行时因 Panther DTS 条件而完全跳过四次 MDIO 写入”这一解释排除。

更准确的说法是：

- 1500 ms：成功 open 路径必执行；
- 四次 MDIO write：成功 MDIO 注册路径必发起；
- 两项均不能仅凭源码推断 PHY 寄存器最终状态或 workaround 是否为 RTL8211F 故障的因果因素。

因此它们仍是 116 与后续异常版本之间真实存在的源码行为差异候选，但不能将“调用已发起”夸大为“PHY 已按预期完成配置”。

## 5. 下一项最小审计

不重复任何实机测试。下一步应核查 6.1.116 的 `stmmac_mdio_write()` 具体实现和 `stmmac_mdio_reset()` / MDIO bus 注册顺序，并进一步确认四次写入的 MDIO 事务错误是否会被静默忽略。然后比较 6.1.174 与 6.12 是否存在等价替代逻辑。
