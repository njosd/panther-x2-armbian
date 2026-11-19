# Panther X2：P3 三版本 GMAC 初始化调用链与 MDIO/PHY 时序差分（2026-11-19）

## 1. 范围与比较基线

本轮完成 P3 第一步：建立 6.1.116 正常、6.1.174 最早异常、6.12.81 持续异常的 GMAC/MDIO/PHY 初始化调用链。重点先精确比较 6.1.116 与 6.1.174 stable 源码端点，再用已锁定的 6.12.81 vendor 源码作交叉参考。

- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174：unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7
- 6.12.81：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

仅静态读取仓库和精确源码文件；未进行 Panther 实机操作、MDIO 访问、PHY reset、接口重启、抓包、发帧或系统配置修改。

## 2. Rockchip GMAC platform probe 主链

6.1.116 与 6.1.174 的 dwmac-rk.c 下列函数逐函数核对：

- rk_gmac_probe()：完全一致。
- rk_gmac_clk_init()：完全一致。
- rk_gmac_powerup()：完全一致。
- rk_gmac_remove()：完全一致。
- gmac_clk_enable()：enable 分支完全一致；disable 分支仅 callback 与 bulk clock disable 的顺序不同。

Panther 的 compatible 选中 RK3568 ops；RK3568 ops 没有注册 set_clock_selection callback，因此 6.1.174 新的 disable 顺序不会在 Panther 执行。它不影响 cold probe 的 enable path。

两版的主要调用顺序相同：

    rk_gmac_probe
      -> stmmac_get_platform_resources
      -> stmmac_probe_config_dt
      -> rk_gmac_setup
      -> rk_gmac_clk_init
      -> rk_gmac_powerup
           -> rk_gmac_check_ops
           -> gmac_clk_enable(true)
           -> set_to_rgmii(tx_delay, rx_delay)
           -> rk_gmac_phy_power_on(true)
           -> pm_runtime_get_sync
      -> stmmac_dvr_probe

所以，6.1.116→6.1.174 stable 源码中没有发现 Rockchip GMAC cold-probe 调用顺序变化。

## 3. STMMAC probe 与硬件初始化顺序

对 stmmac_main.c 比较以下函数：

- stmmac_dvr_probe()
- stmmac_hw_setup()
- stmmac_init_dma_engine()
- stmmac_init_phy()
- stmmac_phy_setup()
- __stmmac_open()

结果：

1. stmmac_hw_setup() 完全一致。
2. stmmac_init_dma_engine() 完全一致，DMA SW reset、DMA/AXI 配置、RX/TX channel 初始化和 tail pointer 写入顺序没有变化。
3. stmmac_phy_setup() 与 stmmac_init_phy() 完全一致。
4. stmmac_dvr_probe() 的关键初始化顺序一致：硬件能力识别 → NAPI/CSR/PM 初始化 → MDIO bus register → PHYLINK setup → register_netdev。
5. stmmac_dvr_probe() 的非功能性变化包括 per-queue xstats sync 初始化，以及移除已不再使用的 lpi_irq 字段赋值。
6. __stmmac_open() 的变化是将 SerDes powerup 调用条件改为 !serdes_up_after_phy_linkup && serdes_powerup。Panther 使用外接 RTL8211F 的 RGMII，不使用 SerDes callback/flag；该差异不命中 Panther。
7. PHY 实际 attach 发生在 netdev open 路径：__stmmac_open() 调用 stmmac_init_phy()，后者通过 phylink_fwnode_phy_connect() 连接设备树 phy-handle。该时序两版相同。

因此，在已检查的 STMMAC 主初始化链中，没有发现 6.1.174 改变 DMA 初始化与 PHY attach 的先后关系。

## 4. MDIO DT 解析重构：代码变化，但 Panther 的输入使其结果等价

6.1.174 的 stmmac_platform.c 将旧 stmmac_dt_phy() 拆为 stmmac_of_get_mdio() 与 stmmac_mdio_setup()，并在 stmmac_probe_config_dt() 中引入 bus-id fallback。

Panther 两版 DTS 核对结果：

- aliases 均包含 ethernet0 = &gmac1，所以 of_alias_get_id(np, "ethernet") 成功返回 0；新增 fallback 不会运行。
- GMAC1 的 phy-handle = <&rgmii_phy1> 两版一致。
- RK356x SoC DTS 中 GMAC1 子节点 mdio1: mdio 两版均为 compatible = "snps,dwmac-mdio"。
- PHY 子节点两版均为 ethernet-phy@0，reg = <0>。
- GMAC1 的 clock_in_out、phy-mode、reset GPIO、reset delays、TX/RX delay、PHY handle 均相同；6.1.116 中 reset comment 在 6.1.174 被移除，实际属性值没有变化。
- 6.1.116 旧逻辑因非 fixed-link 而分配 mdio_bus_data；6.1.174 新逻辑虽然因存在 phy-handle 不走 legacy scan assumption，但因存在 snps,dwmac-mdio 子节点仍分配 mdio_bus_data。两版 Panther 输入最终都创建 MDIO bus。

因此 MDIO parser 代码重构在 Panther 当前 DT 输入下没有改变 bus-id、MDIO bus 创建与 PHY node 选择结果。

## 5. MDIO 注册、四次广播写入与 PHY attach 的真实顺序

精确比较：

- 6.1.116 drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c blob：c60ad9357f1a845b9c58b25b09adc50793805f92
- 6.1.174 同文件 blob：完全相同。
- 6.1.116 与 6.1.174 drivers/net/phy/realtek.c blob：完全相同。

两版 stmmac_mdio_register() 中均包含 P1 审查的四次地址 0 写入：

    stmmac_mdio_write(new_bus, 0, 31, 2627);
    stmmac_mdio_write(new_bus, 0, 25, 0x1801);
    stmmac_mdio_write(new_bus, 0, 31, 0);
    stmmac_mdio_write(new_bus, 0, 0, 0x8000);

调用顺序（两版一致）：

    stmmac_dvr_probe
      -> stmmac_mdio_register
           -> mdiobus_alloc
           -> 设置 read/write/parent/phy_mask
           -> of_mdiobus_register(new_bus, mdio_node)
           -> 检查 fixed-link
           -> 四次 MDIO 地址 0 写入
           -> 因 phy_node 或 mdio_node 存在，跳过 fallback PHY 扫描
           -> priv->mii = new_bus
      -> stmmac_phy_setup / phylink_create
      -> register_netdev

    用户打开 netdev 后：
      -> __stmmac_open
      -> stmmac_init_phy
      -> phylink_fwnode_phy_connect
      -> PHY attach / PHY driver config_init 路径

这说明：
- 四次写入不是 6.1.116 独有、也不是 6.1.174 新增；它们在两个 stable 端点都存在，且调用位置相同。
- MDIO bus 注册与 PHY attach 不是同一动作：MDIO bus 在 platform probe 阶段注册，phy-handle attach 在 netdev open 阶段完成。
- 两版 stmmac_mdio.c 与 Realtek PHY driver 完全相同，因此没有发现 MDIO controller 回调或 RTL8211F driver config_init 在 6.1.174 的变化。
- 6.12.81 vendor 源码的 stmmac_mdio.c 中不再包含这四次写入；这是 6.12 与 6.1 源码的差异，但不是 6.1.174 首次回归的差异，不能用于解释 6.1.174 的最早故障。

## 6. 本轮结论

### 已确认

1. 6.1.116→6.1.174 stable 源码中，Rockchip GMAC probe / power-up 顺序未改变。
2. STMMAC 的 DMA hardware setup、MDIO registration、phylink setup、PHY attach 时序未发现会命中 Panther 的变化。
3. MDIO DT parser 有重构，但 Panther 的 ethernet0 alias、phy-handle、snps,dwmac-mdio 子节点使新旧逻辑最终等价。
4. 四次 MDIO 写入在 6.1.116 和 6.1.174 均存在，且顺序/调用位置一致；它们不能解释两者之间的版本回归。
5. Realtek PHY driver 与 STMMAC MDIO controller driver 在两个 stable 端点逐字节相同。
6. 已检查的 6.1.174 STMMAC __stmmac_open() SerDes 差异不适用于 Panther 外接 RGMII PHY。

### 证据不足

1. stable tag 源码比较不能证明某个 Panther 镜像是否叠加了额外 BSP patch；仍需镜像构建输入/patch 集合与最终源码闭环。
2. 静态调用顺序一致不能证明运行时寄存器写入成功，也不能证明帧已越过 MAC/RGMII 边界。
3. 6.12.81 的四次写入缺失是跨分支差异，但不能回溯解释 6.1.174 的最早故障。

### 决策

**P3 第一步（初始化调用链）完成：在 6.1.116→6.1.174 已锁定 stable 源码范围内，没有发现可解释 TX 故障的初始化顺序或 MDIO/PHY attach 时序回归。**

下一步不再重复这些函数。转向核实 6.1.174 实际镜像相对于 stable 源码是否有额外构建补丁、cherry-pick、vendor overlay 或 DTS fixup；只有先闭环实际构建输入，才能继续追查“stable 源码未显示、但实机版本确实回归”的差异。

## 7. 源码链接

- 6.1.116 dwmac-rk.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 dwmac-rk.c: https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 stmmac_platform.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c
- 6.1.174 stmmac_platform.c: https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c
- 6.1.116 / 6.1.174 stmmac_mdio.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c
- 6.1.116 / 6.1.174 realtek.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/phy/realtek.c
- 6.1.116 Panther DTS: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.1.174 Panther DTS: https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- 6.12.81 stmmac_mdio.c: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c
