# Panther X2 项目 A — R5 STMMAC/DWMAC4 MAC 与 DMA core 审计（2026-11-26）

## 1. 阶段边界

R3、R4 静态审计已条件结项。按实施计划进入 R5。本报告第一轮只比较 STMMAC Kconfig 与 Makefile 的依赖/对象结构，不恢复 GMAC/MDIO/PHY DT 节点，不构建、不加载驱动、不执行 TX/RX，不修改 DMA 算法或源码。

固定源码：
- 6.1.65 黄金候选：`unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`
- 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`

## 2. STMMAC_ETH Kconfig 差异

| 项目 | 6.1.65 | 6.18.63 |
|---|---|---|
| HAS_IOMEM && HAS_DMA | depends | depends |
| PTP_1588_CLOCK_OPTIONAL | depends | depends |
| ETHTOOL_NETLINK | 无 | 新增 depends |
| MII | select | select |
| PCS_XPCS | select | select |
| PAGE_POOL | select | select |
| PHYLINK | select | select |
| CRC32 | select | select |
| RESET_CONTROLLER | select | select |
| NET_DEVLINK | 无 | 新增 select |

结论：
1. 6.18 的 STMMAC_ETH 新增 ETHTOOL_NETLINK 硬依赖。目标配置若缺失此项，STMMAC_ETH 不可能成为 y/m；不能仅检查 HAS_DMA/PTP。
2. 6.18 新增 select NET_DEVLINK，会扩展通用网络管理代码依赖；这是 Kconfig 自动闭包，不代表必须启用 devlink 功能用户态服务。
3. 两版均 select PCS_XPCS、PAGE_POOL、PHYLINK 等，具体最终值仍需从 Kconfig 解析后的 .config 和 built-in 对象验证，不能仅凭 select 文本判定。
4. STMMAC_SELFTESTS 两版都默认 n，并依赖 INET（6.1.65 另显式 depends STMMAC_ETH，位于 if STMMAC_ETH 条件块内）。当前 TX-first 阶段不需要启用 selftests。

## 3. STMMAC Makefile 核心对象变化

两版均将以下对象聚合进 `stmmac.o`：
- `stmmac_main.o`、`stmmac_ethtool.o`、`stmmac_mdio.o`；
- ring/chain descriptor 模式：`ring_mode.o`、`chain_mode.o`；
- 通用 DMA/core：`dwmac_lib.o`、`dwmac1000_core.o`、`dwmac1000_dma.o`、`dwmac100_core.o`、`dwmac100_dma.o`；
- descriptor：`enh_desc.o`、`norm_desc.o`；
- DWMAC4/5：`dwmac4_descs.o`、`dwmac4_dma.o`、`dwmac4_lib.o`、`dwmac4_core.o`、`dwmac5.o`、`hwif.o`；
- MMC/PTP/HWTSTAMP、TC、XGMAC2 core/DMA/descriptors；
- `stmmac_xdp.o`。

6.18 在上述基础上新增：
- `stmmac_est.o`
- `stmmac_fpe.o`
- `stmmac_vlan.o`
- `stmmac_pcs.o)

这些对象被编入 STMMAC 聚合驱动，不代表 Panther X2 首轮 TX 会实际启用 EST/FPE/VLAN/PCS 功能；实际功能路径仍由硬件能力、platform data、DT 与运行时配置决定。首轮 TX 不能把对象存在误认为功能已启用。

## 4. Platform 与 Rockchip glue 边界（登记，不越界）

- STMMAC_PLATFORM 在两版均位于 if STMMAC_ETH 条件块内，select MFD_SYSCON，default y。
- 6.1.65 DWMAC_ROCKCHIP 依赖 OF && (ARCH_ROCKCHIP || COMPILE_TEST)，select MFD_SYSCON。
- 6.18.63 DWMAC_ROCKCHIP 同样依赖 OF 与 ARCH_ROCKCHIP/COMPILE_TEST，并额外 select PCS_XPCS_ROCKCHIP。
- 这部分属于 R6 platform/Rockchip glue，本报告仅记录，不在 R5 提前配置或构建。
- STMMAC_PLATFORM、DWMAC_ROCKCHIP 与 R1 的显式 require_off 一致，当前均关闭。

## 5. R5-1 结论

**R5-1 STMMAC Kconfig/Makefile 初始静态对照：PASS（STATIC）。**

当前最重要的配置门槛是 6.18 新增的 ETHTOOL_NETLINK depends；最重要的对象变化是新增 EST/FPE/VLAN/PCS 对象。DWMAC4 DMA/descriptor 核心对象在两版均已存在，但其真实 Panther 使用路径需要继续审计源码，不能因对象同名就认为行为相同。

尚未完成：
- R5-2 STMMAC main probe/open/stop 生命周期；
- R5-3 DWMAC4 DMA 初始化、descriptor/ring/chain 模式及 cache/coherency；
- R5-4 TX queue、mapping、descriptor ownership、doorbell、IRQ/completion/cleanup 的 6.1.65 与 6.18.63 差异；
- R5 目标配置依赖闭包与最终对象构建验收。

## 6. 下一步

继续 R5-2：逐函数对照两版 `stmmac_main.c` 的 platform probe、net_device 注册、ndo_open、DMA/ring 初始化、ndo_stop 和错误回滚；只建立生命周期调用图，暂不深入 TX descriptor 细节（留 R5-4）。不恢复 DT、不执行硬件 probe。

## 7. STMMAC open/stop 与 DMA 初始化生命周期对照（R5-2，2026-11-26）

### 7.1 ndo_open 路径差异

6.1.65 `stmmac_open()` 主要执行 `stmmac_setup_dma_desc()`，随后调用 `__stmmac_open()`；失败时释放 descriptor resources。PHY/phylink 的连接、运行时 PM 和平台资源的先后关系由此前 probe/platform 生命周期建立。

6.18.63 `stmmac_open()` 新增明确的顺序：
1. 初始化 TX LPI timer；
2. `stmmac_setup_dma_desc()` 分配 TX/RX descriptor resources；
3. `pm_runtime_resume_and_get()`；
4. `stmmac_init_phy()`；
5. 按 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` 决定是否先启动 legacy SerDes；
6. `__stmmac_open()`；
7. `phylink_speed_up()`。

失败路径分别执行 SerDes powerdown、PHY disconnect、runtime PM put、descriptor resources free。此处 6.18 将 PHY 初始化与 runtime PM/SerDes 资源生命周期更明确地纳入 open 路径。它与 R3/R4 的 PHY probe 副作用直接相连，进一步证明恢复 DT 后 `ip link set up` 不是纯软件动作，而会触发 PHY/时钟/供电相关硬件操作。

### 7.2 ndo_stop 路径差异

6.1.65 `stmmac_release()` 内联执行 phylink stop/disconnect、disable queues、取消 TX timer、停止 netif TX、释放 IRQ、停止 TX/RX DMA、释放 descriptor resources、关闭 MAC、SerDes powerdown、carrier off、PTP release、runtime PM put，并处理 FPE workqueue。

6.18.63 将主体收敛到 `__stmmac_release()`：停止 phylink、queues、timer、TX、IRQ、DMA、descriptor resources、PTP/FPE；外层再做 legacy SerDes powerdown、PHY disconnect、runtime PM put。功能边界大体相同，但资源收尾函数被拆分，open/stop 的 PHY/PM 配对更清晰。

### 7.3 DMA engine reset 行为：需要特别注意的版本差异

6.1.65 `stmmac_init_dma_engine()`：
- 要求 `plat->dma_cfg` 与 `pbl` 有效，否则返回 `-EINVAL`；
- ring + extended descriptor 时设置 ATDS；
- 固定 `msleep(1500)`；
- 执行 `stmmac_reset()`；reset 失败直接返回错误，阻止后续 DMA 初始化；
- 初始化 DMA、AXI、channel、RX/TX channel base 与 tail pointer。

6.18.63 `stmmac_init_dma_engine()`：
- 先执行 `stmmac_prereset_configure()`，失败立即返回；
- 再执行 `stmmac_reset()`；
- reset 失败仅输出 warning，将错误清零并继续初始化，日志称设备可能以 reduced throughput 工作；
- 不再在该函数内固定 sleep 1500ms；
- 通过 `stmmac_set_queue_rx_tail_ptr()` / `stmmac_set_queue_tx_tail_ptr()` 更新 queue tail pointer。

这是对 TX bring-up 有实质影响的差异。6.18 可能在 reset 未成功的情况下继续执行后续 DMA 初始化；因此不能仅凭 `ndo_open` 成功就认定 DMA reset 成功。R7 TX-first 观察必须单独保留 DMA reset 日志/状态作为前置证据。也不能为模仿 6.1.65 而直接把 6.18 reset warning 改成 fatal；应先通过受控实机证据判断。

### 7.4 hw_setup 顺序差异

6.1.65 `stmmac_hw_setup()` 先初始化 DMA engine，随后写 MAC 地址、MAC core、MTL、安全特性、RX checksum、启用 MAC RX/TX、DMA operation mode、MMC/PTP、RIWT、ring length 与 TSO 等。

6.18.63 在 DMA reset 前增加 phylink PCS pre-init，并调用 `phylink_rx_clk_stop_block()`，保证 reset/写 MAC address 时 RX clock 不因 EEE LPI 停止；DMA 初始化失败时解除 block 并返回，成功后写 MAC address 再解除 block。随后初始化 MAC/MTL，并新增可选 RX packet parser table 配置；TSO 启用检查改为同时检查硬件 `tsoen` 能力和 platform flag。

这表明 6.18 将 RX clock/EEE/PCS 时序纳入 MAC setup。对 Panther 不能直接假定该路径会生效：需要结合 R6 platform glue 的 phylink PCS 指针、clock 属性和实际硬件能力核实。

### 7.5 R5-2 阶段性结论

**R5-2 open/stop 与 DMA 初始化静态对照：PASS（DIFFERENCES IDENTIFIED；STATIC ONLY）。** 重点差异：6.18 open 增加 PM/PHY/SerDes 生命周期；DMA reset 失败从 6.1.65 的 fatal 改为 6.18 warning-and-continue；DMA pre-reset 配置及 queue tail pointer API 改变；hw_setup 增加 PCS/RX-clock LPI 保护。

尚未审计 TX descriptor 提交、DMA ownership、doorbell、IRQ/NAPI completion 与 reclaim；这些仍留在 R5-3/R5-4。未运行硬件 probe、未执行 TX/RX、未更改源码或配置。
