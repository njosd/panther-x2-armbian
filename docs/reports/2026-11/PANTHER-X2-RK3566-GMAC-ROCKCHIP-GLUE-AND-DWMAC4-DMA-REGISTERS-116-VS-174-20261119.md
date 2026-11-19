# Panther X2：RK3566 GMAC glue 与 DWMAC4 DMA 寄存器路径（6.1.116 vs 6.1.174）

## 1. 范围

本轮承接 TX DMA mapping/descriptor ownership 对比，继续核对 Rockchip glue `dwmac-rk.c`、DWMAC4 DMA register programming 和 Panther 所用 RK356x DTS。源码端点仍为：
- 6.1.116：5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174：3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7

## 2. Rockchip glue 差异

两个端点 `dwmac-rk.c` 中 RK3568 GMAC ops / RGMII 初始化函数主体相同。可见的相关行为差异是 `rk_gmac_power()` 的 power-down 顺序：6.1.174 将 `set_clock_selection(..., false)` 移到 `clk_bulk_disable_unprepare()` 之前，6.1.116 则在 clocks disable 后调用。

该变化只发生在 `enable=false` 的 power-down 分支；power-up 分支的 bulk clock enable、PHY clock enable、clock selection enable 和 5ms delay 顺序没有变化。因此它不解释冷启动时的 TX DMA 小帧失败，除非另有证据证明运行中曾发生 power-down/reopen 循环。

## 3. DWMAC4 DMA register address abstraction

6.1.160 上游同步引入 `struct dwmac4_addrs`，把 DMA channel / MTL channel 寄存器地址计算改为可由平台覆盖；`dwmac4_dma.c` 中相关函数因此增加 `struct stmmac_priv *priv` 参数，并从 `priv->plat->dwmac4_addrs` 读取可选地址描述。

关键判断：
- 当 `priv->plat->dwmac4_addrs == NULL` 时，`dwmac4_dma.h` / `dwmac4.h` helper 回退到原来的标准寄存器基址和 stride；
- RK3566 Panther 使用 `rockchip,rk3568-gmac`，本轮检查 `dwmac-rk.c` 未发现为 RK3568 GMAC 设置 `plat->dwmac4_addrs`；
- 因而 Panther 走默认寄存器地址布局，新旧代码的 DMA channel base、TX/RX control、descriptor base address 等寄存器偏移保持原值。

这次改造是平台可覆盖能力扩展，不等于 Panther 实际 DMA 寄存器地址发生变化。

## 4. DMA channel 初始化字段

6.1.174 的 `dwmac4_dma_init_tx_chan()` 仍然：
1. 读取 DMA channel TX control；
2. 设置 PBL 字段；
3. 设置 OSP；
4. 写回 TX control；
5. 在 `CONFIG_ARCH_DMA_ADDR_T_64BIT && dma_cfg->eame` 时写高 32 位 descriptor base；
6. 写低 32 位 descriptor base。

RX channel 对应写 RPBL 和 RX descriptor base。由于 Panther `dwmac4_addrs` 未配置，以上寄存器地址计算回退到旧默认布局。当前未发现该寄存器初始化抽象对 Panther 造成地址偏移回归的证据。

## 5. Panther DTS：DMA 属性

6.1.116 与 6.1.174 的 `rk356x.dtsi` GMAC1 节点完全相同：
- GMAC base：`0xfe010000`
- compatible：`rockchip,rk3568-gmac`, `snps,dwmac-4.20a`
- `snps,axi-config = <&gmac1_stmmac_axi_setup>`
- AXI burst lengths：`<0 0 0 0 16 8 4>`
- read outstanding：8；write outstanding：4
- mixed-burst enabled
- RX/TX each one queue
- 本节点未声明 `dma-coherent`、`iommus` 或 `memory-region`。

因此这两个源码端点之间没有发现 GMAC DTS 的 DMA coherency / IOMMU / AXI 参数变化。

## 6. 当前结论

1. 6.1.116→6.1.174 的 RK3568 GMAC glue 差异主要是 power-down clock-selection 顺序；power-up 路径不变。
2. DWMAC4 DMA register addressing 在 6.1.160 增加可选平台地址表，但 Panther RK3568 没有配置该表，helper 回退到旧默认偏移；不能把这次抽象扩展当成寄存器地址回归。
3. GMAC1 DTS 的 AXI burst、outstanding、queue、coherency/IOMMU 声明在两端点相同。
4. 到目前为止，6.1.116→6.1.174 这条路径没有找到能解释 Panther TX 小帧不出线的明确 Linux 源码/DTS 差异。

## 7. 研究下一步

下一步转向更有解释力的层次：
1. 核对 6.1.116 与 6.12.81 在 ARM64 DMA API / Rockchip IOMMU / cache maintenance / DMA ops 默认选择上的变化，尤其是未声明 `dma-coherent` 的 GMAC 在 RK3566 上是否获得相同 DMA ops；
2. 对照 6.12.81 `dwmac4_dma.c` 的 TX channel start / tail pointer register path，检查是否出现实质寄存器编程变化；
3. 如果 Linux DMA API 与 DWMAC4 寄存器路径也没有变化，就停止在 6.1.116→174 通用 STMMAC 层扩展搜索，把注意力集中到 6.12 与 boot firmware/DDR memory attribute 的交互，并把它标为待验证而非既定根因。

未执行设备命令、未读取/写入 MMIO、未修改设备树/驱动、未重跑实机测试。

## 8. 源码链接

- 6.1.116 dwmac-rk.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 dwmac-rk.c：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 dwmac4_dma.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c
- 6.1.174 dwmac4_dma.c：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c
- 6.1.116 rk356x.dtsi：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- 6.1.174 rk356x.dtsi：https://github.com/unifreq/linux-6.1.y/blob/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7/arch/arm64/boot/dts/rockchip/rk356x.dtsi
- 6.1.160 upstream sync commit：https://github.com/unifreq/linux-6.1.y/commit/e329a16684894999cd305f06a7154b0a81f01a5d