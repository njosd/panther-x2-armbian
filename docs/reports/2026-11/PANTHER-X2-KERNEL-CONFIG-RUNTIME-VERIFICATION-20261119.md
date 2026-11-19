# Panther X2：6.12.81 实际运行内核配置核验结果（2026-11-19）

## 1. 现场输出

用户在 Panther X2 当前启动的系统执行只读配置提取，内核身份：

```
Linux armbian 6.12.81-rk35xx-ophub #1 SMP Fri Nov 13 11:02:28 UTC 2026 aarch64 GNU/Linux
```

用户提供的配置输出确认：
- `CONFIG_ARM64_VA_BITS=48`
- `CONFIG_ARM64_SW_TTBR0_PAN=y`
- `CONFIG_ARM64_USE_LSE_ATOMICS=y`
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_SELFTESTS` 未启用
- `CONFIG_STMMAC_ETHTOOL=y`
- `CONFIG_STMMAC_FULL=y`
- `CONFIG_STMMAC_PLATFORM=y`
- `CONFIG_DWMAC_GENERIC=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_DWMAC_ROCKCHIP_TOOL=y`
- `CONFIG_PAGE_POOL=y`
- `CONFIG_NET_RX_BUSY_POLL=y`
- `CONFIG_XDP_SOCKETS=y`
- `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y`
- `CONFIG_IOMMU_DMA=y`
- `CONFIG_ROCKCHIP_IOMMU=y`
- `CONFIG_DMA_NEED_SYNC=y`
- `CONFIG_DMA_API_DEBUG` 未启用
- `CONFIG_CPU_RK3568=y`

用户粘贴时终端输出中的下划线被 Markdown 加粗/断行格式打散；以上按符号原名和显示值规范化记录。

## 2. 与 6.12.81 正式构建模板比对

以上关键符号和值与已锁定的 Ophub RK35xx `config-6.12` 模板一致。模板 blob SHA：
`966f4b6ac7c0ad59179d6ae272423500601fab07`

因此本次可以确认：
- 6.12.81 实际运行内核的关键网络、STMMAC、Rockchip DWMAC、IOMMU、DMA、ARM64 配置与已锁定的正式构建模板吻合；
- 不是由于运行时内核意外采用另一套明显不同的 STMMAC/DWMAC 或 DMA 配置导致此前的模板比较失效；
- `CONFIG_CPU_RK3568=y` 与已核对的 RK35xx 构建配置一致，不构成将 RK3566 硬件识别/编译成 RK3568 的证据；
- `CONFIG_ROCKCHIP_IOMMU=y` 仅证明内核包含 Rockchip IOMMU 支持；Panther GMAC1 当前设备树没有 `iommus` 属性，不能据此推断 GMAC DMA 经过 IOMMU。

## 3. 配置支线结论

**6.12.81 运行配置与正式模板不一致**这一疑点关闭。

本次只核对了用户提供的关键符号，不声称对运行配置与模板做过逐字节完整 diff。尚未关闭的唯一配置证据缺口是：从 6.1.116 完整归档中抽取真实 `kernel.config`，与其 general config 模板及 6.12.81 实际配置做严格差分。

## 4. 下一步

不再重复读取 6.12.81 配置，不再围绕 `CONFIG_CPU_RK3568`、`STMMAC_SELFTESTS` 或 IOMMU 选项泛化排查。

下一步应完成 6.1.116 归档中真实 `kernel.config` 的抽取。随后：
1. 若 6.1.116 真实配置与 general config 模板一致，则配置比较支线正式结项；
2. 只保留有 DMA/缓存一致性语义影响的实际差异，不把普通调试/测试选项当作 TX 故障根因；
3. 转回既有报告中尚未闭环的 RX dropped / skb allocation 证据路径，避免重跑已完成的 TX descriptor、MTL/FIFO、时钟、DTS、PHY 与 MAC 来源审计。

## 5. 安全与影响

本轮只读读取运行内核配置；没有安装软件、修改配置、重启服务/接口、写寄存器或改变启动介质。
