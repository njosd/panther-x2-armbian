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

## 5. R6-2：RK3568 GRF / CRU clock / reset 静态核验（2026-11-26）

### 5.1 GRF write-mask 语义

两版 glue 都使用 Rockchip GRF high-word write-mask 形式：
- 6.1.65：`GRF_BIT(n) = BIT(n) | BIT(n+16)`；`GRF_CLR_BIT(n) = BIT(n+16)`；delay 使用 `HIWORD_UPDATE(val, 0x7f, shift)`。
- 6.18.63：`GRF_BIT/GRF_CLR_BIT` 语义保持；delay 改用 `GRF_FIELD(hi, lo, val) = FIELD_PREP_WM16(GENMASK_U16(hi,lo),val)`。

两版 GMAC1 delay 寄存器仍是 CON0 0x0388，RX delay bit[14:8]、TX delay bit[6:0]；delay 配置仍是 7-bit 字段，TX/RX enable 仍在 CON1 0x038c bit0/bit1。

### 5.2 GRF CON1 的实质差异：bit7

6.1.65 的 RGMII 写入：
- 设置 PHY interface selection bit4；
- 清 bit5、bit6；
- 设置 delay enable bit0/bit1；
- **没有把 bit7 纳入写 mask**，即保留该位原状态。

6.18.63 的 RGMII 路径：
- generic powerup 先按 `gmac_phy_intf_sel_mask = GENMASK_U16(6,4)` 写 interface selection；
- RK3568 专用 `set_to_rgmii()` 随后明确写 `GRF_CLR_BIT(7)`，并设置 delay enable bit0/bit1。

6.18 将 bit7 定义为 `MODE_RMII_RGMII`（clear）/ `MODE_SGMII_QSGMII`（set），而 6.1.65 在 RK3568 宏中将 bit7 定义为 `GMII_MODE`，但 RGMII 写入并未触碰该位。

这属于真实的初始化语义差异：6.18 明确把 GMAC1 CON1 bit7 设为 0；6.1.65 RGMII 路径只保证 bit4:6、bit0:1，不保证 bit7 初始值。不能将其简单判定为“6.18 回归”或“必然修复”；需用 RK3568 TRM/可信 Rockchip BSP 确认 bit7 复位值及 mode 编码，并在 R7 前纳入寄存器写入核对表。没有 TRM/硬件读值前不推断 bit7 上电状态。

### 5.3 CRU clocks：ID、mux、gate 对照

两版 `include/dt-bindings/clock/rk3568-cru.h` 中相关 clock ID 保持一致：
- `ACLK_GMAC1=195`，`PCLK_GMAC1=196`；
- `CLK_MAC1_REFOUT=199`，`CLK_GMAC1_PTP_REF=200`；
- `SCLK_GMAC1=390`，`SCLK_GMAC1_RGMII_SPEED=391`；
- `SCLK_GMAC1_RMII_SPEED=392`，`SCLK_GMAC1_RX_TX=393`。

两版 `clk-rk3568.c` 中相关定义也一致：
- ACLK_GMAC1：CLKGATE_CON(17) bit3；
- PCLK_GMAC1：CLKGATE_CON(17) bit4；
- CLK_MAC1_2TOP：CLKSEL_CON(33) bits[9:8]，gate bit5；
- CLK_MAC1_OUT：CLKSEL_CON(33) bits[15:14]，gate bit6；
- CLK_MAC1_REFOUT：gate bit10；
- SCLK_GMAC1：CLKSEL_CON(33) bit2，在 `clk_mac1_2top` 与 `gmac1_clkin` 间 mux；
- SCLK_GMAC1_RGMII_SPEED：CLKSEL_CON(33) bits[5:4]；
- SCLK_GMAC1_RX_TX：CLKSEL_CON(33) bits[1:0]。

parent 列表两版一致：`SCLK_GMAC1` 的 parent 为 `clk_mac1_2top` 或 `gmac1_clkin`。Panther board DTS 将 `SCLK_GMAC1` parent 指向 `gmac1_clkin`，并声明 `clock_in_out = "input"`。board DTS 同时将 `gmac1_clkin` 声明为 125 MHz fixed-clock。

因此软件设计意图是从 GMAC1 外部 clock input 路径取 125 MHz 参考时钟；这只是 DT/clock tree 声明，**不证明板上 pin 实际存在 125 MHz 波形，也不证明 RTL8211F 在当前供电状态下输出该时钟**。两版 clock provider 对上述 GMAC1 mux/gate 没有发现影响本路径的 ID 或寄存器位置变化。

6.18 新增的 `rk_configure_io_clksel()` 对 RK3568 ops 是 no-op：RK3568 ops 没有设置 `io_clksel_io_mask/io_clksel_cru_mask`。因此不能把 6.18 其他 Rockchip SoC 的 IO clock select 变化套用到 RK3566/Panther。

### 5.4 CRU reset：SRST_A_GMAC1

两版 clock binding 都定义 `SRST_A_GMAC1=236`；两版 RK3568 CRU 都注册 30 个 reset registers，并使用 `ROCKCHIP_SOFTRST_HIWORD_MASK`。reset 控制器两版的 hiword assert/deassert 写法相同。

按 16 resets/register 计算，ID 236 对应：
- bank = 14；
- bit offset = 12；
- `RK3568_SOFTRST_CON(0)=0x400`，寄存器偏移为 `0x400 + 14*4 = 0x438`；
- assert 写 bit12 与 bit28 mask；deassert 写 bit28 mask。

SoC DTS 的 GMAC1 节点使用 `resets = <&cru SRST_A_GMAC1>`，name `stmmaceth`。两版 DTS reset ID 和 reset provider 处理逻辑一致。此处是静态映射计算；未访问 CRU 寄存器，也未执行 assert/deassert。

### 5.5 R6-2 阶段结论

**R6-2 GRF/CRU clock/reset 静态核验：PASS（STATIC；一个需 TRM 复核的 GRF bit7 差异已明确）。**

目前可确认：
- delay 字段位置/宽度、enable 位位置一致；
- clock IDs、主要 mux/gate 位置与 parent 列表一致；
- 外部输入时钟路径在 DTS 中被声明为 125 MHz fixed-clock，并被选为 SCLK_GMAC1 parent；
- GMAC1 reset ID/provider 逻辑一致。

仍不能确认：
- CON1 bit7 的硬件实际语义及上电值；
- 外部 125 MHz 时钟实际波形/质量；
- 该时钟是否确由 PHY 输出，以及 PHY 供电/复位是否满足；
- 真实硬件 CRU/GRF 当前寄存器状态。

R6-3 转向原始 DTB 二进制属性对照。需要取得并校验原始 6.1.65 黄金 DTB、R1 6.18.63 隔离 DTB 和目标 6.18.63 完整 Panther DTB 的确切文件及 SHA256。若原始黄金 DTB 不在仓库可访问文件中，先定位既有审计附件/归档，不重新构建、不触碰 SN64G/eMMC，也不让用户重复已完成的导出工作。


## 6. R6-3：DTB 实物提取、属性对照与证据边界（2026-11-26）

### 6.1 已取得 6.18.63 DTB 实物并独立复核

从既有 GitHub Actions run `43543451274` 下载原始 artifact `ophub-kernel-6.18.63-driver-inspection`（artifact ID `14093500129`，ZIP SHA-256 `69028bca5e9193e9610e768b5fcbc836d48a2ce592784c855c73be171bb306ee`），从中直接提取：
- `extracted/rk3566-panther-x2.dtb`，117,859 bytes；
- `extracted/rk3566-panther-x2.from-dtb.dts`，137,260 bytes；
- dtc warning 文件为空。

本轮重新计算 DTB SHA-256，结果为 `5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`，与既有 6.18.63 DTB 审计记录以及 6.1.116 Panther X2 磁盘 DTB 的 SHA-256 完全相同。这证明两个已归档文件是字节级完全相同的 DTB，不只是属性语义相似。注意这不等于它与 6.1.65 原始 DTB 相同。

### 6.2 6.18.63 实际 DTB 中 GMAC1 属性（非 DTS 推测）

反编译的 DTB 实际节点 `/ethernet@fe010000`：
- compatible：`rockchip,rk3568-gmac`、`snps,dwmac-4.20a`；
- reg：`0xfe010000 / 0x10000`；
- IRQ：SPI 32 macirq、SPI 29 eth_wake_irq；
- reset：`SRST_A_GMAC1`（clock binding ID 236）；
- clocks：8 项，与 SoC DTS 定义顺序一致；
- assigned clocks：ID 393、391、390，即 SCLK_GMAC1_RX_TX、SCLK_GMAC1_RGMII_SPEED、SCLK_GMAC1；
- assigned parents：391、390、fixed-clock phandle；
- `clock_in_out = "input"`；
- `phy-supply` 指向 vcc_3v3 phandle；
- `phy-mode = "rgmii"`；
- pinctrl：6 组 gmac1m0；
- reset GPIO：GPIO3 line 1，active-low；
- reset delays：`<0 20000 100000>`；
- TX/RX delay：`0x30 / 0x10`；
- PHY handle 指向 MDIO1 地址 0；
- GMAC1 status = okay，MDIO 子节点在完整 DTB 中存在。

external-gmac1-clock 节点在实际 DTB 中为 fixed-clock，频率 cell `0x07735940`，即 125,000,000 Hz，clock-output-name `gmac1_clkin`。

### 6.3 与 6.1.65 原始黄金 DTB 的可证实比较

6.1.65 原始 IMG DTB 身份已在原始镜像审计中直接记录：
- 文件 `dtb/rockchip/rk3566-panther-x2.dtb`；
- 111,351 bytes；
- SHA-256 `d03ec12df0d69bfa0f0ab5ac462a8fffd8ae5d1c512032ff9468df89248d289f`。

已归档的 2026-11-20 原始 DTB 解析结果明确确认 6.1.65：
- GMAC 节点 ethernet@fe010000；
- compatible 为 rockchip,rk3568-gmac + snps,dwmac-4.20a；
- status okay；
- reg 0xfe010000 / 0x10000；
- phy-mode rgmii；
- clock_in_out input；
- TX/RX delay 0x30 / 0x10；
- MDIO PHY address 0；
- 六组 GMAC1 M0 pinctrl 及其引脚/mux/pull/drive 解析；
- assigned clocks IDs 0x189、0x187、0x186；parent IDs 0x187、0x186 和 fixed-clock phandle；
- fixed-clock 为 125MHz gmac1_clkin；
- reset GPIO 指向 GPIO3 line 1、原始 flags cell=1；
- phy-supply 指向 vcc_3v3。

因此现有原始 DTB 解析证据支持：**6.1.65 黄金 DTB 与 6.18.63 实际 DTB 的 GMAC1 主要硬件连接、RGMII、clock parent、delay、PHY address、pinmux 设计高度一致。** 这与此前 6.1.65/6.1.116 黄金交叉报告相互印证。

6.1.65 旧解析记录没有保留 reset-delays-us 的实际原始 cell，故不能把 6.18 DTB 的 `<0 20000 100000>` 声称为已完成两份原始二进制的逐项确认。6.1.65 DTB 原始文件大小/hash 与 6.18 DTB 不同是全 DTB 层面的事实，不可仅凭 hash 不同推断 GMAC 配置不同。

### 6.4 仍缺失的原始文件字节

6.1.65 的 `04-device-tree.tar.gz` 仍在 Dropbox 原始证据库，file ID `id:9qHOnx-HLYoAAAAAAAAADA`，大小 2,256,475 bytes；原始镜像和阶段包按既定约束继续保留，不移动、不覆盖。

当前可通过既有报告和哈希确认原始 DTB 身份，并复用已保存的完整 GMAC 解析结果；但本轮工具只能从 Dropbox 阶段包读取文本提取结果，未能把压缩包中的二进制成员直接放入本次本地分析环境。因此本节**不声称已对 6.1.65 与 6.18 DTB 执行本轮重新反编译或全属性自动 diff**。如后续必须补齐 reset delay、完整 phandle/clock cells 或全 DTB diff，只需取得现有 2.2 MiB 阶段包/DTB 文件，不需要重新从 851 MiB 原始镜像提取，也不需要重新运行历史提取流程。

### 6.5 DTB 相关结论

- 6.18.63 包内 DTB 的原始二进制已提取并重新核验 hash。
- 该 DTB 与 6.1.116 磁盘 Panther X2 DTB 完全相同（SHA-256 相同）。
- 6.1.65 原始 DTB 与 6.18/6.1.116 DTB 文件不同，但已有原始解析证据显示 GMAC1 的核心硬件属性一致。
- 尚缺 6.1.65 原始 DTB 二进制在本轮的重新反编译与自动全属性 diff；既有报告中 reset delay cell 也未留存。
- 不把非 GMAC 节点差异或 MMC aliases 变化混入当前 TX 根因推断；存储别名属于独立板级属性，若后续涉及启动介质映射，再回到存储专题核验。

**R6-3 GMAC1 DTB 核心属性语义对照：PASS（基于 6.1.65 已归档原始 DTB 解析 + 6.18 DTB 实物复核）；全 DTB 二进制自动 diff：BLOCKED（缺 6.1.65 DTB 原始字节在本轮环境）。**

### 6.6 R6 当前状态与下一步

R6-1 Rockchip glue/board+SoC DTS 源码对照：PASS（STATIC）。  
R6-2 GRF/CRU clock/reset 静态核验：PASS（STATIC；bit7 硬件语义仍待 TRM/可信 BSP 证据）。  
R6-3 GMAC1 DTB 核心属性语义对照：PASS（已有黄金原始解析证据 + 6.18 DTB 实物）；完整二进制 diff BLOCKED。

下一步不重复导出已知证据。先补齐 RK3568 GRF CON1 bit7 的可信寄存器定义来源（TRM/官方 BSP）；同时审查 6.1.65 原始解析中已保存的完整 M0 pinctrl 和 clock cells 是否足够覆盖 R7-A。只有存在具体未决字段时才请求现有 04-device-tree 阶段包或单个 DTB，不要求重做原始镜像提取。


## 7. R6-2 补充：RK3568 TRM 对 GRF CON1 bit7 的确认（2026-11-26）

已取得 Rockchip 官方公开 RK3568 TRM Part1 Rev 1.3（2022-09-30）对应的 GRF 寄存器字段说明。GMAC1 CON1 bit7 定义为 `gmac1_qsgmii_mode`：
- 属性：RW；
- reset value：0；
- 0：RMII/RGMII mode；
- 1：SGMII/QSGMII mode。

同一字段表给出 bits[6:4] 为 `gmac1_phy_intf_sel`，RGMII 编码为 `3'b001`，RMII 编码为 `3'b100`。这与 6.1.65 的 `RK3568_GMAC_PHY_INTF_SEL_RGMII`（bit4 set、bit5/6 clear）一致，也与 6.18 的通用 `GENMASK(6,4)` 编码路径一致。

因此，之前标记的 bit7 差异现已可准确解释：
- 6.1.65 RGMII 路径不显式写 bit7，依赖 TRM 定义的硬件 reset default=0；
- 6.18 RGMII 路径显式写 bit7=0，保证进入 RMII/RGMII mode，而不依赖该位此前仍保留 reset default；
- 对 Panther 的 RGMII 模式，两版最终目标值一致；6.18 的显式 clear 是更确定的初始化，不构成配置回归。

仍不能仅凭 TRM reset value 证明当前运行时寄存器值；bootloader 或此前软件可能在 Linux probe 前修改 GRF。首次授权硬件 probe 时，应记录 Linux 接管前后/初始化后的寄存器值（如采用安全的只读观测点），但不得为了确认而先启用驱动或写寄存器。

**bit7 语义与 reset default：PASS（官方 TRM 静态证据）。** R6-2 的 bit7 未决项关闭。

## 8. R6-4：R7-A 首次硬件准入清单与解除边界规则（2026-11-26）

### 8.1 R7-A 不是单纯把 status 改为 okay

恢复 Panther GMAC1/MDIO/PHY DTB 节点并让 platform driver probe，会触发实际硬件动作。依据 6.18.63 Rockchip glue：
1. rk_gmac_probe() 读取资源、解析 DT、创建 regulator/clock/reset 资源句柄并配置 STMMAC platform callbacks；
2. rk_gmac_clk_init() 获取 bulk clocks；Panther clock_in_out=input，不走 RMII 50MHz clock rate 分支；
3. STMMAC platform init 进入 rk_gmac_powerup()；
4. gmac_clk_enable(true) 使能 bulk clocks、PHY clock handle（如适用），配置 clock selection 并等待 5ms；
5. generic interface-selection 路径写 GRF；
6. RK3568 RGMII 路径写 CON0 delay、CON1 mode/delay-enable；
7. rk_phy_powerup() 对 phy-supply 调用 regulator enable；
8. runtime PM get；随后 STMMAC core 继续 MAC/DMA 初始化。

这会启用时钟、写 GRF、使能 regulator，并可能触发后续 PHY reset/MDIO 活动。它不是“只观察 probe 是否成功”的无副作用操作。

### 8.2 依赖闭包与当前状态

| 依赖 | R7-A 必须满足的条件 | 当前状态 |
|---|---|---|
| Kernel/STMMAC/DWMAC4/Rockchip glue | R1–R6 对应对象、Kconfig、源码闭包固定 | R5 static PASS；R6 static PASS/CONDITIONAL |
| GMAC1/MDIO/PHY DTB | compatible/reg/IRQ/clock/reset/GRF/phandle 正确；GMAC1、MDIO、PHY 节点状态按单一变量恢复 | 当前 R1 仍 disabled；6.18 DTB 属性已核验 |
| GRF | CON0/CON1 offset、write-mask、RGMII bit4:6、bit7、delay field 确认 | TRM 静态 PASS；运行时值未知 |
| CRU clock | IDs、mux parents、gate、rate path 正确；外部 input clock 真实存在 | DTS/CRU 静态 PASS；真实波形未测 |
| CRU reset | SRST_A_GMAC1 ID 236 映射正确 | 静态 PASS；实际 reset 未执行 |
| Pinctrl/GPIO | GMAC1 M0 pin groups 与 GPIO3_PA1 reset line 的 pinmux/方向/极性正确 | Golden/DTB 静态 PASS；R2 GPIO/pinctrl provider runtime PASS；GMAC pinmux 尚未应用 |
| RK809 I2C/MFD/regulator | provider 可注册，vcc_3v3 consumer mapping/constraints 正确，probe 写入副作用已审查 | I2C0 与 RK809 ID/RO status 已验证；MFD/regulator provider runtime 未启用 |
| PHY supply | vcc_3v3 实际 enable 成功，输出满足 RTL8211F 供电要求 | 未验证；0xF0/0xF6 不是电压遥测 |
| PHY reset | GPIO3_PA1 active-low 与 reset timing 可靠 | DTB 静态 PASS；实机时序未验证 |
| External 125MHz clock | gmac1_clkin 物理来源与频率确认，且 PHY 与 SoC 输入方向一致 | DTS 声明 125MHz input；物理波形/来源未测 |
| PHY/MDIO | RTL8211F address 0、MDIO transaction、ID/attach、link negotiation | 6.1.65/6.1.116 golden runtime PASS；6.18 当前未启用 |
| TX witness | 独立对端抓包、测试帧夹具、MAC 对端链路固定 | 既有计划已定义；本轮未执行 |

### 8.3 解除边界的分层规则

**Gate 0 — 当前隔离（现状）**
- GMAC1、MDIO1、PHY 仍 disabled；
- 不加载 DWMAC/Rockchip glue；
- 不启用 RK809 MFD/regulator provider；
- 不读写 GRF/CRU/GMAC/PHY 寄存器；
- 不发出测试帧。

**Gate 1 — 静态放行准备（R6 收尾）**
- R5、R6 源码/Kconfig/DTB 依赖闭包归档；
- RK3568 TRM 字段、clock/reset 映射、黄金基线参数明确；
- R3 provider probe 的每项写入/约束副作用已有可审计清单；
- 6.1.65 黄金 DTB 核心 GMAC 属性解析与 6.18 DTB 对照闭合；如要完整全 DTB diff，只使用现存 04-device-tree 阶段包，不重提取原始镜像；
- 构建产物、DTB、bootargs、initramfs、SU08G 介质哈希冻结。

Gate 1 完成仅允许准备一次独立的实机授权申请，不自动允许驱动 probe。

**Gate 2 — PMIC/provider 单独验证（独立授权）**
- 先在 GMAC/MDIO/PHY 仍 disabled 的 DTB 下，单独考虑启用 RK809 MFD/regulator 最小闭包；
- 执行前必须完成 MFD pre-init、IRQ、regulator constraints、unused-regulator cleanup、poweroff/restart/suspend/resume 的完整写入副作用审计；
- 需要验证 vcc_3v3 时，应有独立电气测量/安全测量方案；I2C RO 状态寄存器不能代替电压测量；
- 此阶段不绑定 GMAC、不扫描 MDIO、不执行 PHY reset。

**Gate 3 — 首次 GMAC platform probe（独立授权）**
- 只有 Gate 2 provider/rail 与外部 clock 条件已验证，才恢复最小 GMAC1/MDIO/PHY 节点闭包；
- 首次启动只观察 probe、clock/reset、PHY attach/link；不配置 IP，不运行 DHCP/ARP/ICMP；
- 任何 regulator/clock/reset 失败立即停止，不通过忽略错误、强制寄存器写或回移旧版代码绕过。

**Gate 4 — TX-first 真实帧（独立授权）**
- 固定 Kernel/config/initramfs/DTB/bootargs，只使用专用 SU08G；
- 对端抓包夹具先用已知正常设备验证；
- Panther 不配置 IPv4，使用固定 EtherType 0x88B5 广播帧；
- 对端逐帧确认所有序列号与 payload；counter、completion 和抓包交叉核验；
- 只有真实对端捕获通过才判 TX-PASS，之后才允许进入 RX 与上层协议。

### 8.4 当前 R7-A 结论

**当前不具备 Gate 2/3/4 的自动放行条件。** 缺少的关键不是 STMMAC 源码，而是 RK809 MFD/regulator 的受控运行时验证、vcc_3v3 电气验证、外部 125MHz clock 实际波形验证，以及首次硬件操作的单独授权。

R6 当前可以形成的结论是：驱动/DTS/GRF/CRU 的静态设计参数已基本明确；解除边界必须从 provider/供电/时钟开始分层，而不是直接把 GMAC1 status 改为 okay。
