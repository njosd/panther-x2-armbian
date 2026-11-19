# Panther X2：6.1.116 / 6.12.81 内核配置来源复核与下一步只读取证（2026-11-19）

## 1. 本轮范围

本轮只读回溯仓库和已锁定的 Ophub 构建配置；未访问 Panther 设备、未执行网络测试、未修改系统或仓库中的既有证据文件。

目的：承接 `PANTHER-X2-REPOSITORY-RETRACE-NO-REPEAT-AND-NEXT-BOUNDARY-20261119.md`，核对配置比较的正确基线，并确定取得真实运行 `.config` 的最小步骤。

## 2. 必须采用的正确比较基线

- 正常工作版本：Linux `6.1.116-ophub`，高置信度对应 Ophub **general kernel** 工作流，源码候选 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`，配置族为 `kernel-config/release/general/config-6.1`。
- 故障版本：Linux `6.12.81-rk35xx-ophub`，由 Actions run `43405957386` 高置信度锁定到 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，构建工作流 commit `f8925391bb2ba2634bb8ca55da39e1a2f4029ffe`，配置族为 `kernel-config/release/rk35xx/config-6.12`。
- 因此这不是同一个 RK35xx BSP 的 6.1→6.12 单纯版本升级；是通用 6.1 内核切换到 Rockchip vendor 6.12 BSP。不得用 `unifreq/linux-6.1.y-rockchip` 的配置冒充用户原来正常工作的 6.1.116。

## 3. 配置文件与构建来源证据

### 3.1 6.1.116

仓库完整归档：
`evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz`

- Git blob SHA-1：`56d2c91db73799a4c04764c045f573ab1bc40831`
- 大小：161,606 bytes
- 归档清单明确包含 `kernel.config`，说明中标注为“当前运行内核配置”。

该归档内的真实 `kernel.config` 尚未在本轮完成独立解包与逐项抽取；不可把 Ophub general config 模板直接称为设备最终配置。

### 3.2 6.12.81

构建 Actions 日志已确认使用：
`ophub/kernel@f8925391bb2ba2634bb8ca55da39e1a2f4029ffe:kernel-config/release/rk35xx/config-6.12`

- 配置模板 blob SHA：`966f4b6ac7c0ad59179d6ae272423500601fab07`
- 该模板启用 `CONFIG_IKCONFIG=y` 和 `CONFIG_IKCONFIG_PROC=y`，因此预期可从运行内核的 `/proc/config.gz` 读取其内嵌配置；但仍需实机只读确认文件存在，并且不能在读取前把模板当成最终 `.config`。
- 已锁定的 6.12.81 正式构建配置包含 STMMAC、Rockchip DWMAC、PHYLINK、PHYLIB、Realtek PHY、64-bit DMA address、IOMMU strict default、Rockchip IOMMU；`CONFIG_STMMAC_SELFTESTS` 未启用。

### 3.3 两个配置模板的已知差异

以下均为**配置模板差异**，不是最终运行配置逐项差异：

| 项目 | 6.1 general config-6.1 | 6.12 RK35xx config-6.12 |
|---|---|---|
| STMMAC / Rockchip DWMAC | 启用 | 启用 |
| PHYLINK / PHYLIB / REALTEK_PHY | 启用 | 启用 |
| ARCH_DMA_ADDR_T_64BIT | 启用 | 启用 |
| ROCKCHIP_IOMMU | 启用 | 启用 |
| IOMMU_DEFAULT_DMA_STRICT | 启用 | 启用 |
| STMMAC_SELFTESTS | 启用 | 未启用 |
| DWMAC_ROCKCHIP_TOOL | 未列为启用 | 启用 |
| STMMAC_ETHTOOL | 未列为启用 | 启用 |
| ARM64 VA bits | 39 | 48 |
| ARM64 SW_TTBR0_PAN | 未启用 | 启用 |
| ARM64 LSE atomics | 未启用 | 启用 |
| XDP_SOCKETS / PAGE_POOL / NET_RX_BUSY_POLL | 启用 | 启用 |
| DMA_API_DEBUG | 未启用 | 未启用 |

解释限制：
- `CONFIG_STMMAC_SELFTESTS` 差异影响测试功能，不构成普通 skb/AF_PACKET TX 故障的直接证据。
- `CONFIG_ROCKCHIP_IOMMU=y` 是 SoC 全局驱动选项；Panther GMAC1 DTS 没有 `iommus` 绑定，不能据此推断 GMAC DMA 实际经过 IOMMU。
- ARM64 VA bits、PAN、LSE 等配置差异值得保留在真实 config 对照表中，但目前没有证据将它们直接关联到 GMAC TX 不出线。
- `DMA_OPS`、`DMA_NEED_SYNC`、`DMA_OPS_HELPERS` 等符号随内核版本演进，不能只比较同名/异名配置文本；必须结合各版本 Kconfig 定义和 DMA API 调用语义。

## 4. 关于 `CONFIG_CPU_RK3568=y` 的纠正

此前已核对：`CONFIG_CPU_RK3568=y` 不是把 RK3566 错误编译成 RK3568 的证据。RK35xx 6.1/6.12 配置模板均采用相应选择，且 Panther GMAC compatible 为 `rockchip,rk3568-gmac`。不得把该符号作为本次故障的根因线索。

## 5. 当前真正缺少的证据

1. 6.1.116 归档中的真实 `kernel.config` 需要解包并抽取。
2. 6.12.81 当前运行内核的真实 `.config` 尚未从设备读取；Actions 中的 config 文件是初始模板，不等于已证明的最终配置。
3. 两份真实配置取得后，才可判断模板差异是否保留到最终构建，并关闭或继续配置差异支线。

## 6. 下一步：只读取 6.12.81 运行配置

只需在当前 6.12.81 启动状态下执行一次以下只读命令；不安装软件、不改配置、不重启、不触碰网卡：

```sh
echo "===== KERNEL ====="
uname -a
echo "===== CONFIG SOURCE ====="
if [ -r /proc/config.gz ]; then
    echo "/proc/config.gz"
    zcat /proc/config.gz
elif [ -r "/boot/config-$(uname -r)" ]; then
    echo "/boot/config-$(uname -r)"
    cat "/boot/config-$(uname -r)"
else
    echo "NO_READABLE_KERNEL_CONFIG"
fi | grep -E '^(CONFIG_(IKCONFIG|IKCONFIG_PROC|CPU_RK3568|STMMAC|DWMAC|PHYLINK|PHYLIB|REALTEK_PHY|ARCH_DMA_ADDR_T_64BIT|IOMMU|ROCKCHIP_IOMMU|DMA|ARM64_VA_BITS|ARM64_SW_TTBR0_PAN|ARM64_USE_LSE_ATOMICS|ARM64_WORKAROUND_CLEAN_CACHE|XDP_SOCKETS|PAGE_POOL|NET_RX_BUSY_POLL)|# CONFIG_(STMMAC|DWMAC|IOMMU|DMA|ARM64_VA_BITS|ARM64_SW_TTBR0_PAN|ARM64_USE_LSE_ATOMICS|XDP_SOCKETS|PAGE_POOL|NET_RX_BUSY_POLL).+ is not set)|^(\/proc\/config.gz|\/boot\/config-.+|NO_READABLE_KERNEL_CONFIG)$'
```

注意：若输出为 `NO_READABLE_KERNEL_CONFIG`，只记录结果，不尝试安装工具或修改内核。届时再从已存在的启动/包文件中寻找配置。

## 7. 下一阶段判定

- 若真实 6.12 配置与正式模板一致，且 6.1 真实配置与其 general 模板吻合：关闭“构建配置误配”支线；配置差异只作为背景，不继续泛化挖掘。
- 若出现差异：只对 STMMAC/DWMAC、DMA API、IOMMU、ARM64 cache coherency、NAPI/XDP 相关项逐个回溯 Kconfig 依赖及源码语义，不因单个符号不同直接判定根因。
- 随后回到已归档的 RX dropped / skb allocation 证据，但不重复网络基础测试。此前已完成的 TX descriptor、MTL/FIFO、DMA channel、DTS、时钟树、PHY reset 和 MAC 来源审计不重做。

## 8. 关联资料

- [6.1.116 完整硬件/内核配置归档](../../../evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz)
- [6.1.116 基线说明](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [TX 与 STMMAC 源码审计](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- [仓库回溯与下一步边界](./PANTHER-X2-REPOSITORY-RETRACE-NO-REPEAT-AND-NEXT-BOUNDARY-20261119.md)
