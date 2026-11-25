# Panther X2 B2-0 方向三 D3-7：STMMAC IRQ / NAPI / watchdog / recovery 四版本审计（2026-11-25）

## 1. 范围与复用

本项仅审 STMMAC/DWMAC4 驱动层 IRQ request/handler、DMA interrupt status decode、NAPI schedule/complete、TX timeout、per-channel TX recovery 与 global reset worker。方向二已完成的 NET_TX_SOFTIRQ、generic queue watchdog 与 qdisc 不重复；D3-4 已审 TX coalescing timer，D3-5 已审 RX NAPI budget 和 descriptor lifecycle，本项只引用这些结果。

四版本端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（实际构建源码）。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

既有运行时/源码证据：
- PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md 已有 macirq、NAPI、DMA status 与物理 TX 边界记录。
- 6.1.116 正常启动与 6.12.81 故障启动日志已有 IRQ/queue counters；本项不重跑设备测试。
- 方向二 §23/§24 已完成 generic TX queue/watchdog 与 NET_TX_SOFTIRQ 层审计。

## 2. Panther IRQ 资源适用性

Panther gmac1 DTS 提供主 macirq 与 eth_wake_irq（WoL/wake）；没有 LPI IRQ、dedicated safety IRQ、RX/TX per-queue MSI 资源，也没有 multi-MSI 配置。因此四版本实际常规数据路径为共享的 MAC 主 IRQ + queue0 RX/TX NAPI；可选 LPI/safety/multi-MSI 分支不命中。

版本变化：
- 6.1.65/6.1.116 有可选 LPI IRQ request；6.1.174-rk35xx c2f148d 不再走该 LPI IRQ request 路径；6.12 使用 safety IRQ 合并接口。
- 6.1.116 起初始化 wol_irq_disabled=true；6.1.65 该赋值缺失。该状态只影响独立 wake IRQ 的 enable/disable 管理，不改变主 macirq 的 DMA status/NAPI 处理。
- 6.12 将 safety CE/UE IRQ 资源整合为 sfty_irq；Panther 没有该资源，故不会改变普通数据 IRQ 路径。

## 3. 主 IRQ handler 与 NAPI schedule

### 3.1 stmmac_interrupt()

6.1.65/6.1.116/实际 6.1.174 c2f148d 的 stmmac_interrupt() 函数体一致：adapter down 时返回 IRQ_HANDLED；处理 common interrupt；随后处理 DMA interrupt；最后返回 IRQ_HANDLED。

6.12 增加 safety-feature 判断：仅当没有独立 sfty_irq 时，在主 IRQ handler 中检查 safety status。Panther 没有 sfty_irq，因此该检查会在主 IRQ 路径执行；但 Panther GMAC4.20a 的 safety capability 是否置位由硬件 feature register 决定，现无运行时 feature dump。未发现该分支改变 RI/TI/FBE 的普通 DMA IRQ decode。

### 3.2 stmmac_napi_check()

四版本 stmmac_napi_check() 函数体逐字一致。它根据 DMA interrupt handler 返回的 handle_rx/handle_tx 标志，对对应 RX/TX queue 执行 napi_schedule_prep()/__napi_schedule_irqoff() 并屏蔽相应 DMA channel IRQ；NAPI poll 完成后再按原路径重新启用 IRQ。

因此没有发现 6.1.65→6.1.116→实际 6.1.174 c2f148d→6.12.81 的 NAPI schedule gate 或 IRQ mask/unmask 顺序变化。

## 4. DWMAC4 DMA interrupt status decode

文件：drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c，dwmac4_dma_interrupt()。

| 状态位 | 四版本处理 |
|---|---|
| RBU | 增加 rx_buf_unav_irq 统计 |
| RPS | 增加 rx_process_stopped_irq 统计 |
| RWT | 增加 rx_watchdog_irq 统计 |
| ETI | 增加 tx_early_irq 统计 |
| TPS | 增加 tx_process_stopped_irq，返回 tx_hard_error |
| FBE | 增加 fatal_bus_error_irq，返回 tx_hard_error |
| RI | 返回 handle_rx，触发 RX NAPI |
| TI | 返回 handle_tx，触发 TX NAPI |
| TBU | 返回 handle_tx，触发 TX NAPI |
| ERI | 增加 rx_early_irq 统计 |

6.1.65/6.1.116 通过固定寄存器 offset 访问 DMA channel status/interrupt enable；实际 6.1.174 c2f148d/6.12 使用 dwmac4_addrs register map helper。Panther dwmac4_addrs 未赋值，NULL fallback 使用标准 DWMAC4 offsets，寄存器目标不变。

6.1.174 起移除 NIS summary counter 的 normal_irq_n++ 统计；6.1.174/6.12 将 RX/TX per-queue IRQ stats 改为 u64_stats sync/per-CPU stats。上述均为统计记账变化。RI/TI/TBU/FBE/TPS 的返回标志和中断 ack（intr_status & intr_en）保持相同。

## 5. NAPI poll 与 TX/RX 处理

- RX NAPI poll：6.1.65/6.1.116 主体一致；实际 6.1.174 c2f148d 与 6.12 的差异主要为 per-queue stats/XDP context/NAPI budget 边界，见 D3-5。没有发现新的 IRQ schedule/complete 顺序回归。
- TX NAPI poll：6.1.65→6.1.116 的 pending_packets/timer 协作和默认 TX coalescing timer 变化已在 D3-4 结项；6.1.174/6.12 延续后续实现。
- combined RX/TX NAPI 分支保留同样的 queue schedule/complete 语义；Panther 运行时队列配置为单 RX + 单 TX，实际使用 channel0。
- 6.12 safety/PCS/EST 等额外 common interrupt 处理分支与 Panther 无 dedicated safety IRQ、无 integrated PCS、无 EST 配置的实际条件不匹配。

## 6. TX timeout 与 recovery

四版本 stmmac_tx_timeout() 函数体完全一致：只调用 stmmac_global_err(priv)。

以下 worker/recovery 函数四版本逐字一致：

- stmmac_global_err()：carrier off、设置 STMMAC_RESET_REQUESTED、调度 service event。
- stmmac_service_event_schedule()：仅在设备未 DOWN 且尚未排队时 queue_work(service_task)。
- stmmac_reset_subtask()：清除 reset request；检查 DOWN；获取 rtnl_lock；设置 RESETING/DOWN；执行 dev_close() + dev_open()；清理状态并释放锁。

stmmac_tx_err() 四版本的恢复动作顺序也一致：stop TX queue → stop TX DMA → free TX skb buffers → clear TX descriptors → reset TX queue → init TX channel → start TX DMA → wake TX queue。6.1.174/6.12 仅将 tx_errors 统计字段从 net_device_stats 移到 xstats/per-queue stats，不改变恢复步骤。

因此 watchdog timeout 或 DMA TPS/FBE 导致的驱动恢复动作，没有发现故障版本新增无条件跳过 reset、遗漏 channel re-init 或不唤醒 queue 的代码差异。

## 7. 对 Panther 普通 DHCP/UDP 的判断

1. Panther 使用主 macirq，queue0 RX/TX；没有多队列 MSI、LPI 或 dedicated safety IRQ。可选 IRQ 分支变化不命中。
2. 四版本 DMA interrupt status 对 RI/TI/TBU/FBE/TPS 的行为一致；故障版本没有改变普通 RX/TX NAPI schedule 的核心判定。
3. 6.1.174/6.12 的 NIS/per-queue stats 变化不改变中断 ack 或 handle_rx/handle_tx 返回值。
4. TX timeout、global error worker、full adapter reset 和 per-channel TX recovery 函数动作顺序一致。
5. 6.1.65/6.1.116 的 TX timer差异见 D3-4；RX NAPI budget差异见 D3-5；不在此重复。

## 8. D3-7 结论

### 已验证
- 四版本主 IRQ→common interrupt→DMA interrupt 结构一致；6.12 新增 safety check 对 Panther 无 dedicated safety IRQ 的路径不改变 RI/TI decode。
- stmmac_napi_check() 四版本逐字一致；DMA IRQ mask/unmask 与 NAPI schedule gate 未发现回归。
- DWMAC4 RI/TI/TBU/FBE/TPS status handling 四版本相同；变化集中于 register address abstraction 与统计字段。
- TX timeout、global error、service event、reset_subtask 四版本一致；per-channel TX recovery 动作顺序一致。
- LPI/safety/multi-MSI 可选分支差异已按 Panther DTS 资源过滤，不外推到实际 macirq path。

### 未验证
- 缺少 6.1.174 c2f148d 的历史 macirq/RI/TI/FBE/NAPI trace；无法确认历史故障窗口是否出现 DMA fatal bus error、RBU 或 NAPI budget starvation。
- 6.12 safety capability 是否由硬件 feature register 置位没有运行时 dump；不影响已核对的普通 DMA status bits。
- 没有历史 TX timeout/reset worker 执行日志；静态恢复流程一致不等于历史运行时没有触发。

**D3-7 状态：已完成（静态源码范围）。** 未发现能够解释普通 DHCP/UDP 无帧输出的、故障版本新增的无条件 IRQ/NAPI/recovery 阻断分支。运行时中断计数和 fatal bus error 证据缺口保留，不重跑设备测试。按原顺序进入 D3-8 四版本总矩阵与一致性审校。

## 9. 精确源码链接

- [6.1.65 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.65 dwmac4_lib.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [6.1.174-rk35xx dwmac4_lib.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)
- [6.12.81-rk35xx dwmac4_lib.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c)