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

## 8. DWMAC4 descriptor / ring-chain / DMA 一致性对照（R5-3，2026-11-26）

### 8.1 DWMAC4 descriptor 格式与 OWN 交接

两版普通 DWMAC4 TX descriptor 均由四个 32-bit word（des0–des3）构成；TX buffer address 位于 des2，长度及 packet metadata 在 des2/des3，OWN 位于 des3。两版均以 little-endian 读写 descriptor，并在 `dwmac4_rd_prepare_tx_desc()` / TSO 对应函数中保留相同的关键交接顺序：

1. 先填写 buffer address、长度、FS/LS、checksum 等字段；
2. 如需在首 descriptor 同时交 OWN，先执行 `dma_wmb()`；
3. 最后写回包含 OWN 的 des3。

两版均在主 TX 提交路径中先准备整帧 descriptors，再设置首 descriptor OWN；随后执行队列 tail pointer 更新前的 write barrier。6.18 使用 `wmb()` 后调用 queue-aware `stmmac_set_queue_tx_tail_ptr()`；6.1.65 使用 `wmb()` 后按队列计算 tail pointer 并调用旧 helper。此处 barrier/OWN 基本语义保持，暂未发现 6.18 删除 DMA ownership ordering 的证据。

### 8.2 Descriptor ring 内存与 packet buffer DMA 映射

两版都使用 `dma_alloc_coherent()` 分配 TX/RX descriptor ring；descriptor ring 属于 coherent DMA memory，不应再对整个 ring 做 streaming `dma_map_single()` 或手工 cache flush。两版对 skb payload 使用 streaming DMA API：
- linear skb head：`dma_map_single(..., DMA_TO_DEVICE)`；
- skb fragments：`skb_frag_dma_map(..., DMA_TO_DEVICE)`；
- completion/cleanup 时根据记录的 map 类型与长度执行 `dma_unmap_single()` 或 `dma_unmap_page()`。

因此，数据 buffer 的 cache/coherency 维护由 DMA mapping API 和平台 DMA ops 负责；descriptor OWN 的 CPU→DMA 可见性由 coherent allocation + `dma_wmb()` / 提交前 write barrier 配合。不能将两者混为同一个“cache flush”步骤。

### 8.3 32-bit descriptor address 与 host DMA mask

6.18 ring_mode/chain_mode 将 DMA 地址写入 32-bit descriptor word 时显式使用 `lower_32_bits(dma_addr)`；6.1.65 对应位置直接赋值到 32-bit word（隐式截断）。6.18 这项改动使 descriptor 的 32-bit 地址编码意图更清楚，但并不意味着允许任意 64-bit DMA 地址被截断后使用。

两版 STMMAC main 都根据硬件 addr64 与 platform host_dma_width 设置 `dma_set_mask_and_coherent()`，失败后回退 DMA_BIT_MASK(32)，若 32-bit mask 也失败则停止硬件初始化。若 host DMA width 大于 32，还需结合硬件 enhanced addressing mode/EAME 能力与设备寄存器高地址路径。对 Panther X2，必须从 R6 Rockchip glue、GMAC DMA capability 及实际 DMA mask 日志确认设备地址宽度；不能仅凭 RK3566 是 32-bit CPU 就推断 DMA mask。

### 8.4 Ring 与 chain 模式差异

两版都保留 ring_mode_ops 与 chain_mode_ops，模式的选择由 STMMAC descriptor mode/platform configuration 决定，不是由 RTL8211F 或 PHY interface 决定。R1 当前隔离状态没有启用 STMMAC，因此没有 Panther 实际选择值。

发现一项具体的 6.18 修正：`chain_mode.c` 计算首 buffer 长度时：
- 6.1.65 直接将 `bmax` 作为首段映射长度，即使 `skb_headlen(skb) < bmax`；
- 6.18.63 使用 `buf_len = min_t(unsigned int, nopaged_len, bmax)`，然后 `len = nopaged_len - buf_len`。

6.18 避免对短 skb head 以超过实际 headlen 的长度执行 DMA map，是更稳妥的边界处理。其余多段拆分仍按 bmax 分片，首 descriptor 暂不置 OWN，后续 descriptor 填好后再由主路径交接首 descriptor OWN。

Ring mode jumbo 路径也在 6.18 显式写入 lower_32_bits DMA 地址，并使用 `STMMAC_NEXT_ENTRY`；6.1.65 使用直接赋值和 `STMMAC_GET_ENTRY`。环形索引 helper 名称变化，需结合宏定义确认 wrap 语义；两版当前均按 TX ring size 回绕，未发现这里改变 descriptor ownership 规则。

### 8.5 本子项结论

**R5-3 DWMAC4 descriptor/ring-chain/DMA coherency 静态对照：PASS（STATIC；差异已标注）。**

确认：
- DWMAC4 descriptor OWN 位和 FS/LS/长度字段的核心语义一致；
- 两版都保留 dma_wmb()，首 descriptor OWN 最后交接；
- coherent descriptor ring 与 streaming skb DMA mapping 分工一致；
- 6.18 明确 lower_32_bits 编码，且继续通过 dma_set_mask_and_coherent() 管理 DMA 地址能力；
- 6.18 chain mode 修正首 buffer 长度不应超过 skb headlen；
- Panther 实际 ring/chain 选择、DMA width、EAME、cache 属性仍未实机确认，留待 R6/R7。

未运行设备测试、未启用驱动、未修改内核配置或源码。

## 9. TX submit 与 completion/reclaim 对照（R5-4 第一轮，2026-11-26）

### 9.1 6.1.65 与 6.18.63 TX submit 顺序

两版 `stmmac_xmit()` 的共同核心顺序：
1. 检查 TX ring 可用 descriptor；
2. 选择 queue / descriptor；
3. 通过 DMA API 映射 skb head 与 fragments；
4. 写入 buffer address、length、FS/LS、checksum 等字段；
5. 把 skb 和 DMA mapping 元数据挂到 TX queue；
6. 设置首 descriptor OWN；
7. `stmmac_enable_dma_transmission()`；
8. flush/tail pointer 更新并启动 TX cleanup timer（6.18 timer/scheduling 细节有调整）。

6.1.65 先处理 skb fragments，再映射/填写 linear head descriptor；6.18.63 先映射并准备 head descriptor（暂不置 OWN），再处理 fragments。两版最终都将首 descriptor OWN 留到所有 frame descriptors 已填写之后，因此核心 ownership handoff 保持一致。

6.18 将 descriptor 访问统一经 `stmmac_get_tx_desc()` / `stmmac_set_desc_addr()` 等 helper，降低对 extended/TBS/basic descriptor 具体布局的直接依赖；6.1.65 在主路径中有更多显式分支访问 `dma_etx`、`dma_entx`、`dma_tx`。

### 9.2 6.18 新增 TX 前置门控

6.18 在常规 TX submit 前增加 EST max-SDU 检查：若 EST 已启用且 queue max_sdu 非零，帧长（若硬件 VLAN insertion 则加 VLAN_HLEN）超过 max_sdu 会 drop。R1/首轮 TX 不应启用 EST；R6 需确认 Panther platform data 不会意外启用 EST/queue gate。

EEE 软件 LPI 退出路径从 6.1.65 的 `stmmac_disable_eee_mode()` 改为 6.18 的 `stmmac_stop_sw_lpi()`；completion 后恢复路径也改为 restart software LPI timer。该差异意味着 TX submit 前还可能涉及 MAC LPI 状态切换，后续实机日志需记录 EEE/LPI 是否 active。

GSO 分支也有变化：6.1.65 仅当 `skb_is_gso(skb) && priv->tso` 时调用 TSO 路径，并检查 TCP/UDP GSO 类型；6.18 对 `skb_is_gso(skb)` 直接调用 `stmmac_tso_xmit()`。首轮 TX 测试应避免 GSO/TSO，先用普通小包隔离基础 descriptor/DMA/doorbell 路径。

### 9.3 Descriptor OWN 与 doorbell 顺序

6.18 普通 TX 路径明确：
- head descriptor 先填充但不置 OWN；
- fragments descriptors 按顺序填写；
- 记录 last segment / skb pointer；
- `stmmac_set_tx_owner(first_desc)`；
- `netdev_tx_sent_queue()`；
- `stmmac_enable_dma_transmission(..., queue)`；
- `stmmac_flush_tx_descriptors()`，其中 `wmb()` 后调用 queue-aware tail pointer helper。

DWMAC4 descriptor helper 在首 descriptor OWN 同时置位的路径中仍有 `dma_wmb()`，避免 DMA 在 frame 其余 descriptor 尚未准备完成时观察到首 descriptor OWN。此处两层 barrier 对应不同位置：descriptor helper 的 DMA ownership ordering 与 tail pointer doorbell 前的 write ordering，不能随意删减或合并。

### 9.4 Completion/reclaim 差异

两版 completion 都先读取 descriptor OWN/status；若 DMA 仍持有 descriptor 就停止清理；OWN 已清后执行 `dma_rmb()`，再读取完成状态；按 mapping 类型执行 `dma_unmap_single()` 或 `dma_unmap_page()`；清理 timestamp/descriptor metadata；释放 skb/XDP frame；推进 dirty_tx；最后唤醒已停止的 TX queue。

6.18 主要变化：
- `stmmac_tx_clean()` 增加 `pending_packets` 输出，由外层 NAPI poll 决定是否继续调度，而不是像 6.1.65 在该函数末尾直接 arm TX timer；
- per-queue NAPI TX packet/error/clean 统计改用 `u64_stats_sync`；
- completion 统计先累加局部 `tx_packets/tx_errors`，退出前统一合并；
- XSK TX completion 增加 metadata completion callback，并在完成后将 slot 的 buf_type 复位，避免 teardown 重复计数；
- 6.18 使用统一 descriptor getter/release helper。

这属于 cleanup/scheduling 结构变化；未见普通 skb 路径删除 OWN 检查、DMA read barrier 或 streaming mapping unmap 的证据。

### 9.5 当前可以确定与不能确定的事项

可以确定：
- 两版都采用 coherent descriptor ring + streaming payload mapping；
- 两版均在所有 frame descriptors 准备后才交接首 descriptor OWN；
- 6.18 仍保留 DMA write/read barrier；
- TX doorbell 仍由 queue-specific tail pointer 路径触发；
- completion 仍以 DMA 清除 OWN 作为可 reclaim 的必要条件。

不能据源码单独确定：
- Panther X2 当前 MAC DMA capability、实际 host DMA width / DMA mask；
- 设备树/平台 glue 最终选择 ring 还是 chain、basic 还是 enhanced descriptor；
- GMAC TX channel base/tail pointer 的最终寄存器值；
- DMA 是否真正读取 descriptor、是否将帧送入 MAC/PHY；
- PHY/link、RGMII delay、clock/rail 是否正常。

### 9.6 R5-4 阶段性结论

**TX submit/completion 主路径静态对照：PASS（STATIC / IMPORTANT DIFFERENCES DOCUMENTED）。** 普通 TX 路径的核心 DMA mapping、OWN 交接、barrier、doorbell 和 reclaim 语义两版连续；6.18 在 helper 抽象、EST max-SDU gate、EEE/LPI、GSO 分流、NAPI completion scheduling 与统计方面有结构性变化。

R5-4 仍需完成 TX IRQ/NAPI poll/interrupt mask-unmask/queue wakeup 的完整调用链对照后才能结项。当前未执行硬件 TX/RX、未启用 GMAC/MDIO/PHY、未修改任何配置。

## 10. TX IRQ / NAPI / DMA status decode：6.18 增量复核（R5-4 完成，2026-11-26）

### 10.1 复用既有 D3-7，不重复四版本审计

项目 B2-0 方向三报告 `PANTHER-X2-B2-0-DIRECTION-3-D3-7-IRQ-NAPI-WATCHDOG-RECOVERY-20261125.md` 已完成 6.1.65、6.1.116、实际构建 6.1.174-rk35xx、6.12.81-rk35xx 四版本 IRQ/NAPI/watchdog/recovery 审计。本节不重跑、不复制该四版本矩阵，只针对 R5 新目标 6.18.63 相对 6.1.65 的增量进行核对，并引用 D3-7 的既有结论。

### 10.2 主 IRQ 与 NAPI schedule/complete

6.18.63 的 `stmmac_interrupt()` 仍按 adapter DOWN 检查、common interrupt、DMA interrupt 顺序处理。变化是 safety IRQ 的分流：当独立 `sfty_irq` 不存在时，主 IRQ handler 才执行 safety-feature status check；6.1.65 在主 IRQ handler 中直接检查。Panther DTS 没有 dedicated safety IRQ，因此 6.18 仍会在主 IRQ 检查 safety status。该分支是否实际产生额外阻断，取决于硬件 safety capability/status，当前没有 Panther 运行时 feature dump，不能假设其置位。

6.18 的 `stmmac_napi_check()` 与 6.1.65 的核心流程一致：读取 DMA status，区分 RI/TI/TBU，分别 schedule RX/TX NAPI，并在 NAPI schedule 成功时持锁屏蔽相应 channel IRQ。NAPI poll 在 work_done 小于 budget 且 `napi_complete_done()` 成功后，持锁重新启用对应 IRQ。未发现 6.18 改变普通 TX IRQ mask→NAPI schedule→complete→unmask 的核心顺序。

### 10.3 DWMAC4 status decode 的增量差异

两版 `dwmac4_dma_interrupt()` 均：
- 读取 channel status 与 interrupt enable；
- 根据 RX/TX 方向 mask status；
- RI 返回 `handle_rx`；
- TI 返回 `handle_tx`；
- TBU 也触发 `handle_tx`；
- TPS/FBE 产生 TX hard error；
- 最后以 `intr_status & intr_en` 写回 status，执行 W1C ack。

6.18 相对 6.1.65 的差异：
1. NIS summary 的 `normal_irq_n` 统计不再递增；
2. RX/TX per-queue IRQ 统计改为 per-CPU `u64_stats`；
3. RWT 计数从 AIS 条件块中移出，单独判断；因此 RWT 统计不再依赖 AIS 同时置位；
4. status/enable 寄存器地址统一使用 `dwmac4_addrs` register-map helper，函数签名新增 `priv` 参数；Panther 若 `dwmac4_addrs == NULL`，需依赖默认标准 DWMAC4 offset fallback。该 fallback 已在 D3-7 对 6.1.174/6.12 路径核实，但 6.18 Panther glue 最终是否保持 NULL 仍由 R6 确认。

普通 RI/TI/TBU/TPS/FBE 的判定与返回语义保持一致；W1C ack 仍写 `intr_status & intr_en`。未发现 6.18 在普通 TX completion 中断上增加新的屏蔽条件或丢弃 TI/TBU 的变化。

### 10.4 TX NAPI pending 与 timer

6.1.65 的 TX NAPI poll 调用 `stmmac_tx_clean()`，在 work_done 小于 budget 时完成 NAPI 并重新启用 TX IRQ。6.18 新增 `pending_packets` 输出参数：clean 阶段若仍有待处理 TX packet，NAPI poll 在 IRQ re-enable 后调用 `stmmac_tx_timer_arm()`。Combined RX/TX NAPI 也使用相同 pending 标志。这与 D3-4 已记录的 timer/coalescing 演进相呼应；不重复 D3-4 结论。其意义是 6.18 对“仍有 pending TX 但本轮 NAPI 可以结束”的情形增加显式 timer 衔接，实机必须同时观察 TX IRQ 与 timer 触发，不能只检查 IRQ counter。

### 10.5 R5-4 完成结论

**R5-4 IRQ/NAPI/TX completion 增量审计：PASS（STATIC；结合既有 D3-7）。** 6.18 保留普通 RI/TI/TBU decode、TPS/FBE hard-error、W1C ack、NAPI schedule/mask 与 complete/unmask 核心路径。新增/变化主要是 safety IRQ 分流、RWT 统计条件、per-CPU IRQ stats、register-map helper 和 TX pending timer 协作。

### 10.6 R5 总结与边界

**R5 STATIC AUDIT COMPLETE（CONDITIONAL）。** R5-1 Kconfig/Makefile、R5-2 open/stop 与 DMA reset/init 生命周期、R5-3 descriptor/ring-chain/DMA coherency、R5-4 TX submit/completion/IRQ/NAPI 均已完成源码增量对照。

结论不是“6.18 已经可用”或“TX 已打通”。R1 仍按隔离设计关闭 STMMAC/DWMAC。R5 只确认未来启用驱动时的源码调用链与版本差异，未验证 Panther 实际 MAC/DMA capability、register map、DMA mask、reset outcome、queue/channel 配置和 PHY link。

下一阶段按既定顺序进入 R6：Rockchip DWMAC glue、Panther DTS/clock/reset/GRF/PHY interface 参数对照。R6 必须将原始 6.1.65 黄金 DTB 与 6.18.63 DTB 二进制属性逐项比对；在完成 R6 和安全边界审查前，不启用 GMAC/MDIO/PHY、不执行硬件 TX。
