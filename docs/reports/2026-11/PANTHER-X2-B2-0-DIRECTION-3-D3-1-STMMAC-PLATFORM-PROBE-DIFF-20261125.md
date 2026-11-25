# Panther X2 B2-0 方向三 D3-1：STMMAC platform probe / resource parsing 四版本差异（2026-11-25）

## 1. 范围

本项只审计 STMMAC common platform 层的设备树参数解析、platform data 填充和 IRQ/resource 解析；不审 Rockchip dwmac-rk.c 内部实现，不审 DWMAC4 DMA 寄存器初始化，不审 TX/RX descriptor 生命周期，不做设备测试。

四个精确比较端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选，非历史 Image 精确 checkout 证明）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（原始 Actions job source_hash 已验证）。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

读取文件均为各端点 raw GitHub 源码；本轮未访问设备、未构建、未修改任何系统或源码。

## 2. stmmac_platform.c 关键函数对照

| 项目 | 6.1.65 | 6.1.116 | 6.1.174-rk35xx | 6.12.81-rk35xx | Panther X2 适用性 |
|---|---|---|---|---|---|
| stmmac_probe_config_dt() | 与 6.1.116 完整函数一致 | 基准 | 增加 bus_id fallback；MDIO 解析拆分；读取 tx-dma-size/rx-dma-size；flow_ctrl 默认处理变化；pclk 名称改为 pclk_mac | 延续 bus_id fallback、MDIO helper、DMA size 解析和 pclk_mac；interface/phylink 节点字段进一步迁移 | alias ethernet0 存在；MDIO 节点/phy-handle 存在；DTS 未见 tx-dma-size/rx-dma-size 或 snps,clk-csr；clock-names 含 pclk_mac |
| stmmac_get_platform_resources() | 与 6.1.116 一致 | 获取 macirq、可选 eth_wake_irq、可选 eth_lpi | 移除 eth_lpi 获取 | 新增可选 sfty IRQ 获取 | Panther DTS 仅列 macirq、eth_wake_irq；上述 lpi/sfty 差异不命中当前节点 |
| pclk 获取名 | pclk | pclk | pclk_mac | pclk_mac | SoC DTSI 实际 clock-names 是 pclk_mac；这是需要保留的真实分歧 |
| bus_id 无 alias fallback | 不适用，缺 alias 时直接回退 0 | 同 6.1.65 | 增加跨设备 static bus_id/highest alias fallback | 延续 6.1.174 | Panther board DTS 明确 ethernet0 = &gmac1，因此 fallback 不触发 |

### 2.1 已直接验证的源码事实

1. 6.1.65 与 6.1.116 的 stmmac_platform.c 中 stmmac_probe_config_dt() 与 stmmac_get_platform_resources() 完整函数内容逐行一致；两份文件长度也一致（25,129 bytes）。
2. 6.1.174 c2f148d 与 6.1.116 相比，probe_config 增加无 alias 时的 bus_id fallback，并把旧 stmmac_dt_phy() 调用改为 stmmac_mdio_setup()；同时增加 platform DMA ring size 属性读取和 pclk_mac 获取。
3. 6.1.174 c2f148d 的 stmmac_get_platform_resources() 移除了 eth_lpi optional IRQ 解析；6.12.81 在此基础上增加 sfty optional IRQ 解析。
4. 6.12.81 的 platform data 由 interface/phylink_node 迁移到 mac_interface/port_node 等较新字段；同时提供 devm_stmmac_probe_config_dt() devres wrapper。

## 3. Panther X2 设备树实际输入核对

### 3.1 GMAC 资源节点

6.1.65/6.1.116 的 rk356x.dtsi 中 gmac1 位于 ethernet@fe010000（约第 698 行），compatible 为 rockchip,rk3568-gmac + snps,dwmac-4.20a；interrupt-names 仅为 macirq、eth_wake_irq（约第 701–703 行）；clock-names 包含 stmmaceth、mac_clk_rx、mac_clk_tx、clk_mac_refout、aclk_mac、pclk_mac、clk_mac_speed、ptp_ref（约第 704–711 行）。6.1.174/6.12.81 的 SoC DTSI 延续该资源名称，并额外描述 XPCS clocks；Panther 的 board-level phy-mode 仍为 rgmii，不因 SoC DTSI 提供 XPCS clocks 就进入 SerDes 路径。

### 3.2 board-level 关键输入

四版本 Panther board DTS 均有 ethernet0 = &gmac1 alias，并启用 &gmac1；GMAC 使用 RGMII、外接 PHY address 0。当前节点没有 eth_lpi 或 sfty 命名 IRQ，也没有 tx-dma-size/rx-dma-size 或 snps,clk-csr 属性。

因此：
- 6.1.174 新增的 bus_id fallback 对 Panther 不触发；bus_id 仍由 ethernet0 alias 得到 0。
- 6.1.174 移除 eth_lpi、6.12 新增 sfty IRQ 的变化均不改变 Panther 当前已声明的 IRQ 资源集合。
- 新增 tx-dma-size/rx-dma-size 属性读取在 Panther 当前 DTS 输入上读取不到值；ring size 后续默认值/平台覆盖行为属于 D3-4/D3-5，留到原顺序再审，不在 D3-1 提前展开。

## 4. 需要保留的跨层差异：pclk clock 名与 MDC clock source

这是本项最值得继续追踪的实际差异：

- 6.1.65/6.1.116 的 stmmac_probe_config_dt() 在 stmmac_platform.c 约第 589 行调用 devm_clk_get_optional(..., "pclk")；但 Panther RK356x DTSI 的 clock-names 是 "pclk_mac"，并没有名为 "pclk" 的条目。
- 6.1.174 c2f148d 在约第 622 行改为获取 "pclk_mac"；6.12.81 在约第 626 行也获取 "pclk_mac"，与 Panther DTSI 名称匹配。
- 6.1.116 stmmac_main.c 的 stmmac_clk_csr_set() 约第 304 行按 priv->plat->stmmac_clk 的频率计算 MDC CSR divider；6.1.174 c2f148d 约第 321 行改为按 priv->plat->pclk；6.12.81 约第 306 行同样按 priv->plat->pclk。
- 因此 6.1.174/6.12.81 的 MDC divider 输入时钟来源与 6.1.65/6.1.116 不同，而且新的 pclk_mac 名称与 Panther SoC DTSI 匹配。该变化直接涉及 MDIO MDC 时钟配置，不是 Ethernet 数据帧 TX descriptor 路径。

边界：本项只确认 DTS clock-name、platform parser 的获取名称、stmmac_clk_csr_set() 选择的 clock handle 来源。尚未确认各版本运行时 pclk_mac 的实际频率、clock enable/refcount 交接及最终 CSR divider 寄存器值；这些需要既有 Rockchip glue 证据和后续对应阶段交叉核对。不得仅凭静态代码认定它造成 DHCP/TX 故障。已知 6.1.174/6.12.81 曾能识别 RTL8211F 并建立 1Gbps link，这说明 MDIO 初始化并非完全失效，但不能证明 MDC divider/时序在所有场景等价。

## 5. 本项结论与状态

### 已验证
- 6.1.65 与 6.1.116 的 platform probe/resource parser 关键函数完全一致。
- 6.1.174-rk35xx 与 6.12.81-rk35xx 的 common platform parsing 演进包括 alias fallback、MDIO helper、DMA ring size 属性、pclk_mac 名称和 platform data 字段迁移。
- Panther ethernet0 alias、单一 macirq + eth_wake_irq 资源和 pclk_mac clock-name 使多个新旧分支的实际适用性可以明确判定。
- 当前未发现由 bus_id fallback、lpi/sfty optional IRQ 差异直接造成 Panther 普通数据 TX 失败的证据。

### 未决
- pclk_mac 实际频率、运行时 enable/refcount 与 MDC CSR divider 最终值尚未形成完整四版本证据闭环。
- 6.1.65 的源码端点仍是高置信度候选，不能提升为历史 Image 精确构建源码。
- 本项没有审查 DWMAC4 DMA channel、AXI/PBL、DMA address width、descriptor ring 等内容。

**D3-1 状态：部分完成，继续进行中。** 已完成 platform probe/resource parser 四版本源码差异初审；唯一保留的 Panther 相关跨层点是 pclk 名称/CSR clock source。下一步只补齐这一点的静态交叉证据，或明确证据上限后关闭 D3-1；之后再进入 D3-2。不得提前进入 D3-3 及之后子项。

## 6. 精确源码链接

- [6.1.65 stmmac_platform.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)
- [6.1.116 stmmac_platform.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)
- [6.1.174-rk35xx stmmac_platform.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)
- [6.12.81-rk35xx stmmac_platform.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c)
- [6.1.65/6.1.116 rk356x.dtsi](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.1.174-rk35xx rk356x.dtsi](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.12.81-rk35xx rk356x.dtsi](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk356x.dtsi)
- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)