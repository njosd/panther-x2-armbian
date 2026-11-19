# Panther X2：STMMAC 6.1.124 MDIO 重构与 Panther DTS 行为等价性核查（2026-11-19）

## 1. 核查对象

同一 unifreq/linux-6.1.y 仓库两个精确提交：
- 6.1.116：5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174：3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7

重点审查 6.1.124 上游 STMMAC 变更：`stmmac_dt_phy()` 重构为 `stmmac_of_get_mdio()` + `stmmac_mdio_setup()`，以及新旧代码对 Panther GMAC1 的 MDIO bus、phy_node、needs_reset 的实际处理结果。

## 2. Panther DTS 证据

两个端点的 `rk3566-panther-x2.dts` 中 GMAC1 配置相同：
- `phy-mode = "rgmii"`
- `phy-handle = <&rgmii_phy1>`
- `&mdio1` 下定义 `ethernet-phy@0`，`reg = <0>`，compatible 为 `ethernet-phy-ieee802.3-c22`
- SoC `rk356x.dtsi` 中 GMAC1 子节点 `mdio1: mdio` 明确带 `compatible = "snps,dwmac-mdio"`
- GMAC1 alias 为 `ethernet0 = &gmac1`

因此这不是“没有 phy-handle、依赖 legacy 扫描”的设备树；也不是 fixed-link。

## 3. 6.1.116 旧逻辑

`stmmac_dt_phy()`：
1. `mdio = !of_phy_is_fixed_link(np)`。Panther 不是 fixed-link，所以 mdio=true。
2. 扫描 GMAC1 子节点，找到 compatible 为 `snps,dwmac-mdio` 的 `mdio1`，赋给 `plat->mdio_node`。
3. 因 `plat->mdio_node` 存在，仍保持 mdio=true。
4. 分配 `plat->mdio_bus_data`，并设置 `needs_reset = true`。

同一配置解析流程通过 `of_parse_phandle(np, "phy-handle", 0)` 取得 `rgmii_phy1`，并将 `phylink_node=np`。

## 4. 6.1.174 新逻辑

新代码先通过 `of_parse_phandle()` 取得 `plat->phy_node`，再由 `stmmac_mdio_setup()`：
1. `stmmac_of_get_mdio()` 扫描 GMAC1 子节点，找到同一个 `snps,dwmac-mdio` 的 `mdio1`。
2. `plat->mdio_node` 非 NULL。
3. 即使 `legacy_mdio = !of_phy_is_fixed_link(np) && !plat->phy_node` 对 Panther 求值为 false，`plat->mdio_node` 仍使分配 `plat->mdio_bus_data` 的条件成立。
4. 同样设置 `needs_reset = true`。

新旧代码都通过相同 `phy-handle` 指向 `rgmii_phy1`，MDIO bus 节点都指向 `mdio1`，并且都创建 bus data、启用 reset 需求。

## 5. 结论：该重构对 Panther 的关键行为等价

| 关键行为 | 6.1.116 | 6.1.174 | 是否变化 |
|---|---|---|---|
| phy-handle 目标 | rgmii_phy1 / addr 0 | 相同 | 否 |
| MDIO 子节点 | mdio1 | mdio1 | 否 |
| MDIO bus data 分配 | 是 | 是 | 否 |
| needs_reset | true | true | 否 |
| ethernet bus_id | alias ethernet0 -> 0 | 相同 | 否 |
| phy-mode | rgmii | rgmii | 否 |

因此，6.1.124 的 MDIO 解析重构虽然是结构性代码变化，但在 Panther 当前 DTS 上，MDIO bus 创建条件、PHY 节点、bus id 和 reset 需求均等价。它不能解释 6.1.174 的 TX 外发异常；不再将该重构列为故障候选。

## 6. 限定说明

这是两个源码提交和 DTS 的静态行为比较，不是对运行时设备树 blob、实际 MDIO 总线注册日志或硬件 reset 波形的重新实测。已知异常版本能读取 RTL8211F PHY ID 并建立 1Gbps Full Link，与本次静态等价结论一致，但不能用 Link Up 代替对所有数据通路的验证。

## 7. 后续研究方向调整

6.1.117–6.1.173 已筛出的 STMMAC/PHY 改动中，当前没有剩余的高解释力初始化差异。下一步不再追 MDIO/PHY 节点解析，改为对比 6.1.116 与 6.1.174 的 DMA mapping/cache coherency、descriptor ownership/barrier 和 DMA address path，限定 Panther 当前 RK3566 DWMAC4/5 ring-mode TX 小帧路径；同时排除已经完成的 descriptor 计数、MTL queue、TX physical boundary 和 MAC 地址来源检查。

不要求用户重复设备测试；不访问设备，不改驱动、不改 DTS、不读写寄存器。

## 8. 源码链接

- 6.1.116 STMMAC platform：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c
- 6.1.174 STMMAC platform：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c
- 6.1.116 Panther DTS：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.1.174 Panther DTS：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.1.116 RK356x SoC DTS：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- 6.1.174 RK356x SoC DTS：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- Upstream MDIO bus refactor rationale：https://lkml.iu.edu/2312.0/07396.html

## 9. 关联报告

- PANTHER-X2-KERNEL-6.1.116-TO-6.1.174-REGRESSION-WINDOW-STMMAC-DIFF-20261119.md
- PANTHER-X2-GMAC-CLOCK-ENABLE-ERROR-HANDLING-AND-SETTLE-DELAY-REGRESSION-20261119.md