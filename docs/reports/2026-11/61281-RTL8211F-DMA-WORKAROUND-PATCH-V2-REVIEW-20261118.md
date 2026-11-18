# Panther X2：6.12.81 STMMAC 实验补丁 v2 静态审计记录

日期：2026-11-18  
目标源码：`ophub/linux-6.12.y-rockchip`  
固定源码提交：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`  
补丁：`patches/6.12.81/0001-stmmac-rtl8211f-dma-experiment-v2.patch`  
状态：**源码定位与接口核对已完成；补丁语法/应用检查、编译和实机验证仍未完成。不得用于生产启动项。**

## 1. 本轮确认的源码事实

1. Panther X2 DTS 根节点 compatible 为 `panther,x2`、`rockchip,rk3566`；aliases 中 `ethernet0` 指向 `gmac1`。因此 v2 补丁同时检查根节点 compatible 和设备的 `ethernet` alias ID=0，将实验限制在 Panther X2 的 ethernet0/GMAC1。
2. `arch/arm64/configs/rockchip_linux_defconfig` 中 `CONFIG_STMMAC_ETH=y`。STMMAC 为 built-in 时，内核命令行参数采用 `stmmac.<参数名>=<值>` 的形式；实际目标镜像使用的 .config 仍需核对。
3. 目标版本 `stmmac_mdio.c` 中，`of_mdiobus_register()` 成功返回后，代码先进行 XGMAC dummy read，再继续后续 MDIO/PHY 处理，最终保存 `priv->mii`。v2 将 PHY 实验插入注册成功后、XGMAC dummy read 前，并排除 XGMAC。
4. `phy_read_paged()`、`phy_write_paged()` 和 `phy_read_poll_timeout()` 在该源码版本的 PHY API 中有声明；轮询宏会把负的 MDIO 读取错误作为失败返回，而不是误判为 reset bit 已清除。
5. `stmmac_init_dma_engine()` 的目标源码在 `stmmac_reset()` 前没有 1500ms 延时。v2 在此处增加可选延时，不改变默认路径。

## 2. v2 补丁设计

- `stmmac.phycr2_test=0`：关闭，默认值。
- `stmmac.phycr2_test=1`：只对 Panther X2 ethernet0 的 MDIO 地址 0 执行 RTL8211F PHY ID 检查；匹配 `0x001cc916` 后，将 PHYCR2 page `0x0a43` / register `0x19` 写为 `0x1801` 并立即读回。
- `stmmac.phycr2_test=2`：在模式 1 后写 BMCR_RESET，轮询 reset bit 清除，随后再读回 PHYCR2。
- `stmmac.dma_delay_ms=0`：关闭，默认值。
- `stmmac.dma_delay_ms=1500`：仅 Panther X2 ethernet0 在 `stmmac_init_dma_engine()` 的 `stmmac_reset()` 前等待 1500ms；其他值忽略并记录警告。

两个参数独立，可先分别实验，不需要组合。

## 3. 必须保留的解释边界

- PHYCR2 的 `0x1801` 不是无副作用的读写测试值，会改变 PHY 的多项功能设置。
- RTL8211F 驱动后续的 `config_init()` 仍可能依据 PHY probe 阶段缓存的 PHYCR2 状态再次修改 bit 0 并执行 soft reset。因此“注入后立即读回”不代表后续 PHY 初始化完成后的最终寄存器值；测试必须同时采集后续 PHY 初始化日志和最终寄存器值。
- DMA 延时放在 `stmmac_init_dma_engine()` 内；若恢复或重初始化路径再次调用该函数，1500ms 延时也可能再次发生。
- `ethernet0` alias 限定依赖目标 DTB 保留该 alias。目标 Panther X2 DTS 已静态确认有该 alias，但实机启动时加载的 DTB 是否与该源码一致，仍需通过启动证据确认。

## 4. 当前验证状态

| 项目 | 状态 |
|---|---|
| 6.12.81 候选源码提交定位 | 已确认候选提交；尚不能证明预编译 release 与该提交逐字节完全一致 |
| Panther X2 DTS 根 compatible / ethernet0 alias | 静态审计确认 |
| STMMAC built-in defconfig 项 | 静态审计确认 |
| PHY paged access / reset poll API | 静态审计确认 |
| PHY 注入位置 | 静态审计确认 |
| DMA reset 前插入位置 | 静态审计确认 |
| v2 补丁 unified-diff 结构 | 已整理 hunk 和上下文；尚未在完整源码树运行 `git apply --check` |
| 编译 | 未执行 |
| TF 卡镜像制作 / 写卡 | 未执行 |
| Panther X2 实机启动与网络验证 | 未执行 |

## 5. 后续步骤

1. 在独立工作目录取得固定提交的完整源码树，运行 `git apply --check`、`git diff --check`，必要时修正上下文。
2. 核对真实 6.12.81 release 的源码/配置对应关系和完整构建工具链，再进行独立构建。
3. 先做无注入对照，再分别做 PHY 模式 1、PHY 模式 2、DMA 延时实验；每轮保持单变量。
4. 只有完成补丁应用检查、构建及 TF 卡回滚准备，并经用户确认后，才进行写卡和实机启动。

**结论：v2 已比初稿增加了 Panther X2 + ethernet0 双重限定，避免参数意外影响其他平台或网卡；但它仍是实验补丁草案，不是修复结论。当前没有对 eMMC、现有系统或设备配置执行任何操作。**
