# Panther X2 B2-1 R6 Rockchip DWMAC glue 与硬件参数审计

日期：2026-11-26  
状态：进行中；本文件首轮仅记录 R6-1 源码增量与 DTS 源码核对。  
黄金基线：6.1.65 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`  
目标版本：6.18.63 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`

## 1. 范围与约束

本轮只读审计 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`、Panther X2 board DTS 及 RK356x SoC DTS。未访问设备、未读取/写入寄存器、未加载驱动、未修改 Kconfig/DTB/网络配置。R1 的 GMAC/MDIO/PHY disabled 边界继续有效。

## 2. R6-1：RK3568 glue 与 Panther X2 适配

### 2.1 SoC match 与 MAC 实例识别

两版均将 `rockchip,rk3568-gmac` 绑定到 `rk3568_ops`，并以 GMAC MMIO resource base 区分实例：
- GMAC0：`0xfe2a0000`
- GMAC1：`0xfe010000`

Panther X2 的 GMAC1 SoC DTS 节点地址为 `0xfe010000`，因此匹配实例 ID=1。该判断来自源码/DTS 静态证据，不是设备 probe 结果。

### 2.2 RK3568 GRF mode 与 delay 编程差异

6.1.65：
- `rk3568_set_to_rgmii()` 对 GMAC1 CON0 写入 RX/TX delay 字段；
- CON1 写入 `RK3568_GMAC_PHY_INTF_SEL_RGMII`（bit4=1、bit5=0、bit6=0）以及 RX/TX clock delay enable（bit1/bit0）；
- 代码中 RGMII/RMII 的 interface selection 使用旧的显式宏；`rk3568_ops` 未设置通用 `init` 和 `gmac_phy_intf_sel_mask`。

6.18.63：
- 新增 `rk3568_init()`，按 MMIO resource 设置 `gmac_grf_reg` 为 GMAC1_CON1；
- `rk3568_ops` 提供 `gmac_phy_intf_sel_mask = GENMASK_U16(6,4)`；
- 通用 `rk_gmac_powerup()` 通过 `rk_get_phy_intf_sel(PHY_INTERFACE_MODE_RGMII)` 与 `rk_encode_wm16()` 先写 interface selection；
- `rk3568_set_to_rgmii()` 随后写 CON0 delay，CON1 写入 `RK3568_GMAC_MODE_RMII_RGMII`（bit7 clear）及 RX/TX delay enable。

**含义：** 6.18 将 PHY interface selection 从 RK3568 专属 set_to_rgmii 函数迁入通用 ops/mask 路径，并将 bit7 的 RMII/RGMII mode 明确纳入 RGMII 初始化。它与 6.1.65 不是逐条寄存器写入相同的实现。不能只看 delay 值相同就认为 GRF 初始化等价；R7 前必须以 RK3568 TRM/可信 BSP 与原始 DTB 对照确认 bit4:6、bit7 语义及写入时序。

### 2.3 Probe / powerup 生命周期变化（重要副作用）

6.1.65 的 `rk_gmac_probe()` 顺序：
1. `stmmac_get_platform_resources()`；
2. `stmmac_probe_config_dt()`；
3. `rk_gmac_setup()`；
4. `rk_gmac_clk_init()`；
5. **在调用 `stmmac_dvr_probe()` 之前直接调用 `rk_gmac_powerup()`**；
6. 再进入 STMMAC core probe。

6.18.63 的 `rk_gmac_probe()`：
1. 使用 `devm_stmmac_probe_config_dt()`；
2. 设置 `plat_dat->init/exit/suspend/resume` 回调；
3. 完成 `rk_gmac_setup()` 与 `rk_gmac_clk_init()`；
4. 交由 `devm_stmmac_pltfr_probe()` 统一执行 platform/core probe；Rockchip powerup 由注册的 `plat_dat->init` 生命周期回调触发，而不是在 rk_gmac_probe 中直接提前调用。

因此两版的硬件初始化相对 STMMAC core probe 的先后关系不同。6.18 的 probe 函数仍非“纯读取”：`rk_gmac_setup()` 会取得 regulator/syscon/clock 资源，clock init 对 RMII/PHY clock 可能设置 rate；真正 powerup 会 enable clocks、写 GRF mode/delay、enable phy-supply regulator，并涉及 runtime PM。**仅将驱动绑定或恢复 DT status 就可能触发硬件副作用，绝不能作为无害探测。**

### 2.4 Clock 管理变化

两版都取得 Rockchip bulk clocks、`stmmaceth` MAC clock，并在 powerup 时 bulk prepare/enable；也都支持 PHY clock 和 clock input/output 配置。

6.1.65 的 `rk_gmac_clk_init()` 将 `stmmaceth` 单独保存为 `clk_mac`，RMII clock rate 通过该 clock 设置；6.18.63 改为使用 `plat->stmmac_clk` 设置 RMII 50MHz，并移除独立 `clk_mac` 获取路径。两版 PHY clock rate 均可能设为 50MHz（仅 integrated PHY 分支）。

Panther DTS 设置 `clock_in_out = "input"`，故 Rockchip glue 将 PHY 侧视为提供参考时钟；GMAC1 的 assigned clock parent 将 `SCLK_GMAC1` 指向 `gmac1_clkin`。这意味着外部时钟源、RK809 clock output 和 clock parent 必须作为一条链审计，不能仅验证 Linux clock framework 返回成功。

### 2.5 PHY regulator 与 reset 侧效应

两版 `rk_gmac_setup()` 都执行 `devm_regulator_get(dev, "phy")`，对应 Panther DTS 的 `phy-supply = <&vcc_3v3>`。取得 regulator handle 不等于已 enable；powerup 路径会调用 regulator enable，powerdown 会 disable。R3 已证明 RK809 I2C 节点可做受限只读身份/状态读取，但尚未验证 MFD/regulator provider 和 vcc_3v3 实际输出能力，因此此项仍是 R7 放行前置条件。

Panther board DTS 的 `snps,reset-gpio`、active-low 和 reset delays 是 STMMAC PHY reset 路径配置；不要与 Rockchip glue 的 integrated PHY reset control 混淆。当前 RTL8211F 是外置 PHY，`phy-is-integrated` 未设置，不应触发 integrated PHY 专用 powerup 分支。

## 3. Panther X2 DTS 源码属性对照（非原始 DTB 结论）

### 3.1 Board DTS：6.1.65 与 6.18.63

两版 `rk3566-panther-x2.dts` 的 GMAC1 override 保留相同的关键配置：
- `assigned-clocks`：SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED、SCLK_GMAC1；
- `assigned-clock-parents`：RGMII_SPEED、SCLK_GMAC1、外部 `gmac1_clkin`；
- `clock_in_out = "input"`；
- `phy-supply = <&vcc_3v3>`；
- `phy-mode = "rgmii"`；
- GMAC1 M0 pinctrl 组合；
- `snps,reset-gpio = <&gpio3 RK_PA1 GPIO_ACTIVE_LOW>`；
- `snps,reset-active-low`；
- `snps,reset-delays-us = <0 20000 100000>`；
- `tx_delay = <0x30>`、`rx_delay = <0x10>`；
- PHY handle 指向 MDIO1 address 0。

board DTS 中 GMAC1 和 MDIO1 在两版源码均写为 `status = "okay"`。R1 实验 DTB 是经过独立隔离构建的产物，不能把 board DTS 的默认状态误认为 R1 实际 DTB 已启用。

### 3.2 SoC DTS：继承属性

6.1.65 `rk356x.dtsi` 与 6.18.63 `rk356x-base.dtsi` 的 GMAC1 节点保留相同关键结构：
- compatible：`rockchip,rk3568-gmac` + `snps,dwmac-4.20a`；
- reg：`0xfe010000 / 0x10000`；
- IRQ：SPI 32 `macirq`、SPI 29 `eth_wake_irq`；
- clocks/clock-names 八项顺序相同；
- reset：`SRST_A_GMAC1`，name `stmmaceth`；
- `rockchip,grf = <&grf>`；
- `snps,axi-config`、mixed-burst、MTL RX/TX config、TSO；
- AXI burst length `<0 0 0 0 16 8 4>`，read OSR 8，write OSR 4；
- RX/TX queues-to-use 均为 1，queue0。

该 SoC 公共节点默认 `status = "disabled"`；board DTS override 后为 okay。R1 专用隔离构建另行关闭相关节点。上述为源码 DTS 对照，不代替原始 6.1.65 黄金 DTB 与 R1/6.18 DTB 的二进制属性提取。

## 4. R6-1 阶段性结论

**R6-1 Rockchip RK3568 glue 与 Panther board/SoC DTS 源码对照：PASS（STATIC；关键初始化差异和副作用已识别）。**

当前必须保留的未决点：
1. 6.18 RK3568 GRF bit4:6 与 bit7 的完整语义/写入时序需用 TRM 或可信 BSP 核验；
2. 6.1.65 原始黄金 DTB 与 6.18.63/R1 DTB 的实际属性、phandle、clock/reset 资源二进制核验尚未完成；
3. RK809 vcc_3v3 rail 仍未验证可供 PHY 使用；
4. 外部 125MHz clock 的真实来源、幅度/稳定性及 clock framework 运行态尚未验证；
5. GMAC1 DMA width、寄存器 capability 与实际 reset 结果仍待后续 R6/R7 阶段。

不因此放开任何硬件边界。下一步 R6-2：对 RK3568 GRF/CRU clock/reset 定义、寄存器位含义及 6.1.65/6.18.63 clock provider 实现做专项静态核验；再进入原始 DTB 二进制属性对照。