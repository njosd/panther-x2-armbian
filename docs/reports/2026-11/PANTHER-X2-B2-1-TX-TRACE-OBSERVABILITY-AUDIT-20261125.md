# Panther X2 Project A — Linux 6.18.63 TX 追踪观测能力审计

- 日期：2026-11-25
- 阶段：B2-1 / R1 后续可观测性审计
- 源码基线：ophub/linux-6.18.y @ `aee4e352a15d636cbc484f56819c6e59474dfd9f`（Linux 6.18.63）
- R1 构建：Actions Run `45611898629`，Job `139197305317`
- Artifact：`b2-1-r1-network-core`，ID `15023630465`
- Artifact SHA256：`80bd2d33d0e85d8fd4c10fdd33a60c159393db3a45ae5f6e95dd0bf490cc656c`
- R1 Image SHA256：`63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`
- R1 kernel.config SHA256：`480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`
- R1 System.map SHA256：`b5122877c04fcae0172e4938af680ba1e8ec56191bb070024b574b5ce7d494d8`
- 结论性质：源码和实际构建产物只读审计；未访问 Panther、未启用 tracing、未注册 kprobe、未构建诊断补丁、未发包。

## 1. 审计结论

**Linux 6.18.63 的 R1 实际构建已经具备足够的基础追踪设施，可先用静态 tracepoint + 定点 kprobe/kretprobe 追踪 TX 主链；不需要一开始就重编内核。**

最有价值的已确认观测点：

1. 网络核心：`net:net_dev_queue`、`net:net_dev_start_xmit`、`net:net_dev_xmit`，以 skb 指针、设备、长度、协议和驱动返回值串联网络层与驱动入口。
2. DMA API：`dma:dma_map_phys`、`dma:dma_unmap_phys`，可看到设备名、物理地址、DMA 地址、长度和方向。
3. SKB 生命周期：`skb:kfree_skb`、`skb:consume_skb`，可用 skb 指针和调用位置观察丢弃或完成回收。
4. 驱动关键函数：`stmmac_xmit`、`dma_map_page_attrs`、`dwmac4_set_tx_owner`、`dwmac4_wrback_get_tx_status`、`stmmac_tx_clean`、`dwmac4_dma_start_tx`、`dwmac4_set_tx_tail_ptr`，均有源码明确的函数入口/返回观测价值。
5. 描述符辅助快照：STMMAC 自带只读 debugfs `descriptors_status`，可输出 TX/RX ring 的 DMA 地址和 descriptor 四个 word。

**但当前只能确认“追踪能力已编入 R1”，不能确认设备运行时 tracefs 已挂载、具体 kprobe 可成功注册或硬件 TX 已运行。** R1 仍关闭 GMAC/MDIO/PHY；R1 System.map 不会有 STMMAC/DWMAC4 函数符号。

## 2. R1 实际构建配置核验

从真实 artifact 的 `output/kernel.config`、`output/System.map` 直接核验，不以旧版本 config 模板代替。

| 配置/符号 | R1 实际状态 | 意义 |
|---|---|---|
| CONFIG_TRACEPOINTS | y | 内核静态 tracepoint 基础 |
| CONFIG_TRACING | y | trace event/tracing 核心 |
| CONFIG_EVENT_TRACING | y | trace event 接口 |
| CONFIG_FTRACE | y | ftrace 基础框架 |
| CONFIG_FUNCTION_TRACER | 未启用 | 不能依赖 function/function_graph tracer |
| CONFIG_KPROBES | y | 动态函数探针 |
| CONFIG_KRETPROBES | y | 函数返回探针 |
| CONFIG_KPROBE_EVENTS | y | 可通过 tracing 接口创建 kprobe event |
| CONFIG_KALLSYMS | y | 运行时符号查找基础 |
| CONFIG_KALLSYMS_ALL | 未启用 | 不应依赖任意静态数据符号查找；优先探测函数文本符号 |
| CONFIG_DEBUG_FS | y | debugfs 支持 |
| CONFIG_TRACEFS_AUTOMOUNT_DEPRECATED | y | debugfs 挂载后可兼容自动挂载 debugfs/tracing |
| CONFIG_DEBUG_INFO_DWARF5 | y | 构建具备 DWARF5 调试信息配置 |
| CONFIG_DEBUG_INFO_BTF | 未启用 | 不依赖 BTF/CO-RE 参数名 |
| CONFIG_DMA_API_DEBUG | 未启用 | DMA API debug 检查未启用，但不影响下述 DMA tracepoint |
| CONFIG_IKCONFIG_PROC | y | 系统运行时可通过 /proc/config.gz 核对配置 |
| CONFIG_PERF_EVENTS | y | 内核 perf 基础存在；不代表 initramfs 有 perf 工具 |
| CONFIG_BPF_SYSCALL / CONFIG_BPF_EVENTS | y | 内核 BPF 能力存在；不作为本轮首选观测入口 |

### 2.1 System.map 的实际符号证据

R1 System.map 中已存在：

- `register_kprobe`
- `register_kretprobe`
- `tracepoint_probe_register`
- `trace_event_reg`
- `trace_event_raw_init`

并已存在下列具体静态 tracepoint 对象：

- `__tracepoint_dma_map_phys`
- `__tracepoint_dma_unmap_phys`
- `__tracepoint_net_dev_queue`
- `__tracepoint_net_dev_start_xmit`
- `__tracepoint_net_dev_xmit`
- `__tracepoint_kfree_skb`
- `__tracepoint_consume_skb`
- `__tracepoint_napi_poll`

这比单纯看到 Kconfig=y 更强：这些 tracing/kprobe 核心符号和上述 tracepoint 对象确实进入了 R1 的最终构建产物。

R1 System.map 还包含 local text symbol `packet_sendmsg`（符号类型 `t`），说明当前 KALLSYMS 配置下至少存在局部函数文本符号。后续 R5/R6 必须再核对 STMMAC/DWMAC4 目标函数是否出现在对应构建的 System.map 和运行时 /proc/kallsyms 中，不能拿 R1 符号表代替。

### 2.2 追踪配置的限制

- `CONFIG_FTRACE=y` 不等于函数跟踪已启用；`CONFIG_FUNCTION_TRACER` 未启用，因此不把 function tracer/function_graph 作为方案。
- `CONFIG_KPROBE_EVENTS=y` 与 `CONFIG_KRETPROBES=y` 已启用，kprobe event 不依赖 FUNCTION_TRACER。
- `CONFIG_DEBUG_INFO_DWARF5=y`，但 R1 artifact 没有上传带 DWARF 的 `vmlinux`，只有 Image/System.map/config。因此当前不能从 R1 artifact 得到 `struct sk_buff` 等字段偏移。
- BTF 未启用，不采用依赖 BTF 类型信息的参数名/CO-RE 方案。
- DMA tracepoint 与 `CONFIG_DMA_API_DEBUG` 是两回事。源码中的 `trace_dma_map_phys()` / `trace_dma_unmap_phys()` 调用不以 DMA_API_DEBUG 为前提。

## 3. 静态 tracepoint：可以直接观察什么

### 3.1 网络核心

固定源码：
- `include/trace/events/net.h`
- `net/core/dev.c`

| Trace event | 源码记录字段 | 可证明的边界 | 不提供 |
|---|---|---|---|
| net:net_dev_queue | skbaddr、dev、len、net_cookie | skb 进入设备发送队列路径 | payload 原始字节 |
| net:net_dev_start_xmit | skbaddr、dev、queue_mapping、protocol、len、data_len、VLAN/offload 字段 | 即将调用 netdev ndo_start_xmit | payload 原始字节 |
| net:net_dev_xmit | skbaddr、dev、len、rc | ndo_start_xmit 返回及驱动返回码 | DMA 完成或物理发送 |

`net_dev_start_xmit` 与 `net_dev_xmit` 之间的 skbaddr 可作为网络核心到驱动调用的关联键。对于本项目单帧、单队列、小型线性帧测试，能明确识别同一个 skb 是否进入驱动以及驱动是否返回 NETDEV_TX_OK/BUSY。

注意：STMMAC 的 `stmmac_xmit()` 返回 NETDEV_TX_OK，表示驱动接受并排入发送路径，不等于帧已经从网口发出。

### 3.2 SKB 生命周期

固定源码：`include/trace/events/skb.h`

- `skb:kfree_skb`：记录 skbaddr、location、drop reason 等，可帮助识别映射失败/发送失败后的释放路径。
- `skb:consume_skb`：记录 skbaddr 和 location，可与初始 skbaddr 对照，观察发送完成后的 skb 消耗/回收。

STMMAC `stmmac_tx_clean()` 在处理完成 descriptor 后调用 `dev_consume_skb_any(skb)`。因此在目标版本运行时若观察到相同 skbaddr 的 consume_skb 事件，并与 descriptor completion 事件顺序吻合，可作为完成回收的关联证据；仍不能替代对端抓包。

### 3.3 DMA API

固定源码：
- `include/trace/events/dma.h`
- `kernel/dma/mapping.c`

| Trace event | 字段 | 用途 |
|---|---|---|
| dma:dma_map_phys | device、phys_addr、dma_addr、size、dir、attrs | 观察 CPU 物理地址到设备 DMA 地址的映射结果 |
| dma:dma_unmap_phys | device、dma_addr、size、dir、attrs | 观察对应 DMA mapping 的解除 |

源码路径确认：STMMAC 普通线性 skb 路径调用 `dma_map_single()`；该接口是头文件 inline wrapper，最终进入 `dma_map_page_attrs()`，再进入 `dma_map_phys()`。`dma_map_phys()` 在底层 map 操作返回后调用 `trace_dma_map_phys()`，因此该事件能记录 DMA 地址和长度；底层 map 返回错误值时也会记录该返回值。

边界限制：`dma_map_phys()` 在少数前置错误分支（例如 device 缺少 dma_mask）会在 tracepoint 前返回；`dma_map_page_attrs()` 对 MMIO/zone-device page 也有早退。因此要完整观察 map 函数返回值，建议同时使用 `dma_map_page_attrs` kretprobe。对于本项目正常 skb 线性 buffer 路径，预期走普通 page mapping，但仍以运行时证据为准。

DMA tracepoint 不携带 skb 指针。关联方式应采用：
1. `net_dev_start_xmit` / `stmmac_xmit` 记录 skbaddr、测试帧 marker 和长度；
2. `dma_map_page_attrs` kretprobe 记录 device/page/offset/size/dir/返回 DMA address；
3. `dma_map_phys` 记录 phys_addr 与 DMA address；
4. descriptor 的 buffer address 与 DMA address 对照。

首轮必须单帧串行发送、禁用不必要 offload/fragment，避免并发 mapping 让关联变得含糊。

### 3.4 NAPI / IRQ

固定源码：
- `include/trace/events/napi.h`
- `include/trace/events/irq.h`

`napi:napi_poll` 可记录 NAPI 指针、设备名、work 和 budget；`irq:irq_handler_entry/exit` 可记录 IRQ 号、handler 名和处理结果。这些事件能说明 TX completion 相关中断/NAPI 是否发生，但本身没有 skb 或 payload 身份，只作为时序背景。

## 4. Kprobe / Kretprobe：补足 tracepoint 看不到的数据

Linux 6.18.63 的 `Documentation/trace/kprobetrace.rst` 明确支持：
- 函数入口参数 `$argN`；
- 返回值 `$retval`；
- 对参数指针的内存解引用 `+/-OFFS(FETCHARG)`；
- 固定长度数组读取，数组长度小于 64；
- kretprobe 中继续访问函数参数。

因此无需一开始改驱动源码，即可尝试在关键函数上读取 skb 内容、descriptor 内容和返回值。所有偏移必须来自**同一次目标构建**的 DWARF/结构布局，禁止猜测偏移。

### 4.1 推荐探针候选

| 函数 | 参数/位置 | 建议记录 | 用途与限制 |
|---|---|---|---|
| stmmac_xmit | 入口 arg1=skb、arg2=netdev | skb 指针、len、data 指针、EtherType 和 payload marker/sequence 字节 | 最关键的驱动入口 payload 直接核验；需 struct sk_buff 字段偏移 |
| dma_map_page_attrs | 入口/返回 | device、page、offset、size、dir、retval DMA address | 记录 DMA mapping 的输入和返回值；普通 dma_map_single 最终会经过此函数 |
| dwmac4_set_tx_owner | 返回时 arg1=descriptor | descriptor 指针、des0..des3 | 观察 OWN 位被驱动置位后的描述符 |
| dwmac4_wrback_get_tx_status | 返回时 arg2=descriptor | descriptor 指针、原始 des3、函数返回 status | 观察 DMA 是否仍拥有 descriptor，以及完成/错误状态 |
| stmmac_tx_clean | 入口/返回 | priv、budget、queue、返回清理数量 | 观察驱动完成清理路径；返回数量是 descriptor/work 数，不直接等于单帧物理发送 |
| dwmac4_dma_start_tx | 入口/返回 | priv、ioaddr、channel | 观察 DMA TX start 回调是否执行 |
| dwmac4_set_tx_tail_ptr | 入口/返回 | priv、ioaddr、tail_ptr、channel | 观察写入 DMA_CHAN_TX_END_ADDR 的目标值 |

其中 `dwmac4_set_tx_owner`、`dwmac4_wrback_get_tx_status` 是静态函数，但作为 DWMAC4 descriptor ops 的函数指针实现被调用；后续仍须确认它们在目标构建符号表中存在且不在 kprobe blacklist 中。

### 4.2 ABCD 字节读取

AF_PACKET 测试程序发送不带 VLAN 的小型线性 Ethernet 帧，首轮不使用 fragments/GSO。驱动入口 `stmmac_xmit(skb, dev)` 的第一个参数就是 skb。

Kprobe event 可通过同构建的 `struct sk_buff` 偏移读取：
- skb->len；
- skb->data 指针；
- skb->data 开始处的 Ethernet header；
- Ethernet header 后固定位置的项目 magic、run ID、sequence 和部分 payload。

例如概念上读取 `skb->data + 14` 后的固定字节数组。这里的 14 仅对应无 VLAN Ethernet II header；最终测试帧格式必须固定并核验。**不能把下面的结构偏移写成猜测常数**：实际 event 定义须在 R5/R6 构建后从同构建 DWARF 计算并生成。

示意（非可直接执行命令）：

```text
p:panther/stmmac_xmit stmmac_xmit skb=$arg1:x64
  len=+SKB_LEN_OFFSET($arg1):u32
  data=+SKB_DATA_OFFSET($arg1):x64
  marker=+14(+SKB_DATA_OFFSET($arg1)):x8[16]
```

Kprobe 读取到的 marker/sequence/hash 是驱动入口处 buffer 的直接内容证据。它不能单独证明 DMA 已读取该 buffer。

### 4.3 descriptor 内容与 OWN

固定源码：
- `dwmac4_descs.c:dwmac4_set_addr()` 将 DMA address 低 32 位写入 des0，高 32 位写入 des1。
- `dwmac4_rd_prepare_tx_desc()` 写入 des2 buffer length、des3 packet length、FS/LS/checksum 等字段。
- `dwmac4_set_tx_owner()` 设置 TDES3_OWN。
- `dwmac4_wrback_get_tx_status()` 先检查 OWN；若仍为 OWN 则返回 tx_dma_own；OWN 清除后再检查 LAST 和错误位。

因此在 `dwmac4_set_tx_owner` 返回时记录 descriptor 四个 word，可将 DMA map 返回的 DMA address 与 des0/des1 对照；在 `dwmac4_wrback_get_tx_status` 返回时再记录 des3 和 status，可观察设备是否归还 descriptor 以及是否报告错误。

descriptor 不保存 ABCD 副本。它保存的是 DMA buffer address、长度和控制/所有权信息；ABCD 本体仍在 DMA mapping 所指向的 packet buffer 中。

### 4.4 DMA doorbell 与真实交接顺序

固定源码 `stmmac_main.c` 的普通 skb TX 顺序：

1. `stmmac_xmit()` 将 skb->data 做 DMA_TO_DEVICE mapping；
2. `stmmac_set_desc_addr()` 把 DMA address 写入 descriptor；
3. `stmmac_prepare_tx_desc()` 写入长度和 descriptor 控制字段；首 descriptor 初始不置 OWN；
4. 保存 skb 与 TX buffer 元数据；
5. `stmmac_set_tx_owner()` 调用 DWMAC4 callback 设置 OWN；
6. `stmmac_enable_dma_transmission()` 调用 DWMAC4 start callback；
7. `stmmac_flush_tx_descriptors()` 执行 `wmb()`；
8. `stmmac_set_queue_tx_tail_ptr()` 计算 ring tail DMA address；
9. `dwmac4_set_tx_tail_ptr()` 将 tail pointer 写入 `DMA_CHAN_TX_END_ADDR`；
10. `stmmac_xmit()` 返回 NETDEV_TX_OK。

DWMAC4 `dwmac4_dma_start_tx()` 会设置 DMA channel 的 ST 位，并设置 GMAC_CONFIG_TE；`dwmac4_set_tx_tail_ptr()` 执行 tail-pointer MMIO 写入。

**这两个事件必须分开记录：**
- OWN 置位：descriptor 所有权交给 DMA；
- wmb + tail-pointer write：驱动按源码顺序发布 ring 更新并通知 DMA。

kprobe 观察到 `dwmac4_set_tx_tail_ptr` 被调用及其参数，只能证明软件执行到该 MMIO 写入函数；不等于已读回寄存器或证明 DMA 硬件确实取走 descriptor。若需验证寄存器实际状态，必须先核对芯片/寄存器语义，再决定是否增加安全 readback；不得随意 devmem 读取。

### 4.5 completion 与 skb 回收

固定源码 `stmmac_tx_clean()`：
- 读取 descriptor status；
- OWN 仍置位则停止清理；
- OWN 清除后执行 `dma_rmb()`，再读取后续 descriptor 状态；
- 对最后一个 descriptor 检查错误，成功时增加 tx_packets/tx_pkt_n；
- 解除 DMA mapping；
- 调用 `dev_consume_skb_any(skb)`；
- 增加 tx_clean 并累计 tx_errors。

可将以下事件按 descriptor 指针、DMA address、skbaddr、queue 和时间顺序关联：
- `dwmac4_wrback_get_tx_status` 返回；
- `dma:dma_unmap_phys`；
- `skb:consume_skb`；
- `stmmac_tx_clean` 与统计变化。

对单 descriptor 的首轮小帧，关联关系最简单。后续多 descriptor/fragments 测试必须扩展为每个 segment 独立记录，不能把一个 descriptor 当成完整帧。

## 5. STMMAC 自带 debugfs 与统计接口

### 5.1 debugfs

固定源码在 `CONFIG_DEBUG_FS` 下创建：
- `/sys/kernel/debug/stmmaceth/<ifname>/descriptors_status`
- `/sys/kernel/debug/stmmaceth/<ifname>/dma_cap`

文件以 0444 创建。前者输出 TX/RX descriptor ring 的 DMA address 及 des0..des3；后者报告 DMA hardware capabilities。

限制：
- `descriptors_status` 在接口未 IFF_UP 时不输出 ring；
- 它遍历 descriptor ring 时没有为 DMA 并发更新提供快照锁，正在发送时读取可能看到前后不一致的瞬时状态；
- 只作为辅助快照，不能替代 OWN handoff/completion 点的定点观测；
- debugfs 未挂载时不能假设文件可用。

### 5.2 STMMAC ethtool / netdev statistics

源码提供的统计包括：
- 软件 TX queue：`tx_pkt_n`、`tx_irq_n`、`tx_threshold`；
- NAPI/清理：`tx_normal_irq_n`、`tx_clean`、`tx_set_ic_bit`；
- 错误：`tx_underflow`、`tx_carrier`、`tx_losscarrier`、`tx_deferred`、`tx_jabber`、`tx_frame_flushed`、`tx_payload_error`、`tx_ip_header_error`、`tx_collision`；
- 标准统计：`tx_packets`、`tx_bytes`、`tx_errors`、`tx_dropped`；
- 若实际硬件 capability 报告支持 RMON/MMC，才有对应硬件 MMC TX frame/octet counters。

**特别注意计数时点：**
- `tx_bytes` 在 stmmac_xmit 提交路径中累计，早于 descriptor completion；
- `tx_packets` / `tx_pkt_n` 在 stmmac_tx_clean 观察到 descriptor 完成且无错误后累计；
- `tx_clean` 是清理调用计数，不是发送帧数；
- 所有统计均为累计值，不能单独识别某个 ABCD sequence；
- MMC counters 是否存在取决于运行时读取到的 DMA capability。

R1/B1 的最小 BusyBox 环境没有 ethtool/ip/tcpdump 等完整网络工具，R1 artifact 本身也不含 initramfs。后续应在 CI 侧构建一个小型静态诊断 helper，使用 `SIOCETHTOOL` 读取驱动统计、`RTM_GETLINK` 读取 netdev 统计；无需在 Panther 安装软件。AF_PACKET sender 也以独立静态程序提供。

## 6. tracefs / debugfs 运行时可用性检查边界

当前仅能从构建配置证明 tracing facility 已编入，未证明设备运行时挂载状态。

未来获准进行只读取证时，先检查：
- `/proc/config.gz`；
- `/proc/kallsyms`；
- `/proc/mounts`；
- `/sys/kernel/tracing/available_events`；
- `/sys/kernel/debug/tracing/available_events`；
- `/sys/kernel/tracing/kprobe_events`；
- `/sys/kernel/debug/stmmaceth/<ifname>/`。

`CONFIG_TRACEFS_AUTOMOUNT_DEPRECATED=y` 只是允许在 debugfs 挂载后兼容自动挂载 `debugfs/tracing`；不能据此假定 `/sys/kernel/tracing` 已挂载。若 tracefs/debugfs 不存在，本轮只记录缺失，不自行 mount、不创建 kprobe、不写 tracing 控制文件。挂载和启用 event/kprobe 会改变运行时状态，必须另行授权。

## 7. 最终观测分层与推荐顺序

| 层 | 首选观测 | 需要的补充 | 成功边界 |
|---|---|---|---|
| 测试程序 | 发送前帧 bytes、sequence、length、hash | 无 | 测试输入正确 |
| 网络核心 | net_dev_queue/start_xmit/xmit | skbaddr 对照 | 同一 skb 到达驱动并被接受 |
| STMMAC 入口 | stmmac_xmit kprobe 读取 skb data | 同构建结构偏移 | 驱动入口 payload 与测试帧一致 |
| DMA mapping | dma_map_phys/unmap_phys + dma_map_page_attrs kretprobe | 单帧串行关联 | 映射地址、长度、方向正确 |
| DWMAC4 descriptor | dwmac4_set_tx_owner kretprobe | descriptor 字段偏移/原始 word | descriptor 指向同一 DMA buffer 且 OWN 已置位 |
| DMA doorbell | dwmac4_dma_start_tx、dwmac4_set_tx_tail_ptr | 可选、经确认安全的寄存器 readback | 软件已执行启动与 tail-pointer 写入 |
| DMA completion | dwmac4_wrback_get_tx_status、stmmac_tx_clean | dma_unmap_phys、consume_skb | 驱动观察到 OWN 归还、无 descriptor 错误并回收 |
| MAC/PHY/线缆 | link、MAC/MMC counters、交换机端口计数 | 必要时外部 RGMII/线侧仪器 | 只能作为线侧结果的辅助定位 |
| 对端 | 逐帧抓包并核对 payload | run ID、sequence、hash | 对端收到完全匹配的 ABCD 测试帧（PASS-LINE） |

推荐优先级：
1. 静态 tracepoint；
2. 只针对缺失字段的 kprobe/kretprobe；
3. STMMAC debugfs/ethtool/netdev counters；
4. 只有前三者不能完成可靠关联时，才考虑最小诊断 tracepoint 补丁；
5. 若软件显示 DMA completion 但对端无帧，先用 MAC/PHY/交换机状态缩小范围；是否需要外部 RGMII/线侧仪器另行评估，不预先采购。

## 8. 需要单独准备的构建交付物

R1 artifact 没有 DWARF-bearing `vmlinux`，因此未来 R5/R6 构建必须额外满足以下之一：
- 上传与 Image 同一 build 的 `vmlinux`（含 DWARF5），或
- 在 CI 中生成并归档结构偏移清单，至少覆盖 `struct sk_buff` 的 len/data、`struct dma_desc` 的 des0..des3，以及必要的 TX queue/ring 关联字段。

同时归档：
- 目标函数符号清单和 System.map；
- 最终 .config、源码 commit、补丁、Image hash；
- kprobe event 定义及其对应的结构偏移来源；
- 诊断 helper 源码和二进制 hash。

禁止用另一内核版本的结构偏移套用 6.18.63；禁止只保存 event 命令而不保存 offset 来源。

## 9. 故障定位与证据边界

| 最后通过点 | 下一处缺失 | 优先排查范围 |
|---|---|---|
| 测试程序帧/hash 正确 | net_dev_queue/start_xmit 无事件 | AF_PACKET、netdev 选择、trace event 状态 |
| start_xmit 有 skbaddr | stmmac_xmit 无命中 | ndo_start_xmit 绑定、目标符号/kprobe 注册 |
| stmmac_xmit marker 正确 | DMA map 返回错误/无事件 | DMA mask、page/offset、DMA ops |
| DMA map 成功 | descriptor DMA address 不匹配 | stmmac_set_desc_addr、descriptor 格式/写入 |
| OWN handoff 已发生 | 无 completion/OWN 不归还 | DMA engine、doorbell、bus/clock/reset、descriptor |
| completion 已发生 | 对端无帧 | MAC TX、RGMII、PHY、线缆、交换机端口/抓包点 |
| 对端收到正确帧 | 后续 RX/IP 失败 | 转入 R8，不无故重开 TX 根因调查 |

若 trace event 丢失、kprobe 无法注册或 tracefs 不可用，结论应为“观测能力 BLOCKED”，不能直接判定硬件功能 FAIL。若 probe 本身改变时序或出现 buffer overrun，必须记录并评估观测扰动。

## 10. 当前状态

- [x] 下载并核验 R1 实际 artifact。
- [x] 核对 R1 最终 tracing/kprobe/tracefs/DWARF 配置。
- [x] 从 R1 System.map 核验 tracing 核心符号和网络/DMA/SKB/NAPI tracepoint 对象。
- [x] 固定 Linux 6.18.63 源码核对网络、DMA、STMMAC、DWMAC4 的观测点。
- [x] 核对 STMMAC debugfs ring snapshot 与 ethtool/netdev 统计语义。
- [ ] tracefs/debugfs 运行时挂载与事件列表：未验证。
- [ ] STMMAC/DWMAC4 目标 kprobe 注册：未验证，须等 R5/R6 构建和获准运行时测试。
- [ ] skb/descriptor 偏移表：未生成，须从同构建 DWARF 获取。
- [ ] 任何 Panther 实机 tracing、接口 UP、发包或对端捕获：均未执行。

本报告只完成观测能力研究，不改变 B1/R0 前置门，不放行 R2，也不授权 Panther 实机操作。


## 11. 补充审计：descriptor 交接与 completion 的低扰动观测（2026-11-25）

### 11.1 不把 ring 连续轮询作为主证据

再次核对 `stmmac_main.c` 与 `dwmac4_descs.c` 后，明确以下边界：

- STMMAC `descriptors_status` 通过 `stmmac_rings_status_show()` 遍历 TX ring，并直接读取每个 descriptor 的 des0..des3；没有对整个 ring 加锁，也没有建立与 DMA 更新之间的一致性快照协议。
- 该文件在接口未 IFF_UP 时直接返回，不输出 ring；接口 UP 后读取也可能与 DMA 对 descriptor 的写回并发。
- 因此不允许用高频读取 `descriptors_status` 的方式追踪 OWN 翻转；不把某次快照中的瞬时混合值判为硬件故障。
- 该文件保留为发送前/发送后辅助快照，或在停止队列并确认 DMA quiescent 后的静态检查；不作为活动 TX 的主要验收依据。

### 11.2 交接点：利用驱动真实顺序做事件式记录

固定源码 `stmmac_main.c`：

- `stmmac_flush_tx_descriptors(priv, queue)` 的注释明确要求 OWN bit 是 descriptor 最后设置的字段；
- 随后执行 `wmb()`；
- 再调用 `stmmac_set_queue_tx_tail_ptr()`；
- 后者计算 `tx_q->dma_tx_phy + index * desc_size`，再调用硬件回调 `stmmac_set_tx_tail_ptr()`。

普通 skb TX 路径在调用 flush 前已完成 DMA mapping、descriptor address/length/control 写入和 OWN 设置。因此首选诊断补丁不是轮询 ring，而是在如下精确位置发出 trace event：

1. descriptor 内容已填好、OWN 已设置之后，记录 queue、ring index、descriptor CPU pointer、descriptor DMA address、des0..des3、关联 skb pointer、skb len、DMA buffer address/len；
2. 在 `stmmac_flush_tx_descriptors()` 的 `wmb()` 之后、tail-pointer callback 之前记录发布事件；
3. 在 `stmmac_set_queue_tx_tail_ptr()` / DWMAC4 callback 记录 tail pointer 目标地址与 channel。

交接记录应以单帧、单队列、单 descriptor 的第一轮测试为基准。记录 descriptor 指针和 DMA address 的关系，不把 descriptor 当成 ABCD payload 的副本。

注意：tracepoint 在 OWN 设置后增加少量执行时间，仍然会改变时序；它比连续轮询更可控，但不是零扰动。若现有静态 tracepoint + 可用 kprobe 已能可靠捕获同一数据，则优先不加补丁；只有目标函数不可探测或关联字段不足时才引入该补丁。

### 11.3 Completion 点：跟随驱动自己的 OWN 判断和 DMA barrier

固定源码 `dwmac4_descs.c`：

- `dwmac4_wrback_get_tx_status(x, p, ioaddr)` 首先读取 `p->des3`；
- 若 OWN 仍置位，返回 `tx_dma_own`；
- OWN 清除且不是 last descriptor 时返回 `tx_not_ls`；
- last descriptor 根据 ERROR_SUMMARY 及具体错误位生成完成/错误状态。

固定源码 `stmmac_main.c` 的 `stmmac_tx_clean()`：

1. 调用 descriptor status callback；
2. 若返回 `tx_dma_own`，停止清理；
3. OWN 清除后执行 `dma_rmb()`；
4. 检查最后 segment 的错误状态；
5. 对成功帧增加 packet 统计；
6. DMA unmap；
7. `dev_consume_skb_any(skb)`；
8. 释放 descriptor 并推进 dirty_tx。

推荐 completion trace event 在驱动得到 status 后记录：
- queue / ring index / descriptor pointer / descriptor DMA address；
- status enum；
- OWN、LAST、ERROR_SUMMARY 及原始 descriptor word；
- skb pointer、sequence marker、DMA mapping address/length；
- 随后是否成功 unmap、consume skb、计入 tx_packets。

最小补丁可放在 `stmmac_tx_clean()` 中，紧跟 `stmmac_tx_status()` 返回之后记录 status；如果要记录 dma_rmb 后的 descriptor word，则在 OWN 清除分支、`dma_rmb()` 之后记录。这样不会额外抢先读取尚未归还的 descriptor。错误和 OWN 仍置位的分支必须分别记录，不能只记录成功完成。

### 11.4 关于 static 函数与 kprobe 可解析性：新增限制

R1 实际配置中 `CONFIG_KALLSYMS_ALL` 未启用。Linux kprobe event 按符号名解析时，不能假定所有 static/local 函数都能从运行时 kallsyms 找到。

以下目标均为 static 函数或可能被编译器内联/优化，必须在目标 R5/R6 构建中检查：
- `stmmac_xmit`
- `stmmac_tx_clean`
- `dwmac4_set_tx_owner`
- `dwmac4_wrback_get_tx_status`

因此：
- 不能仅因函数在源码中存在，就宣称 kprobe 一定能注册；
- 同构建 DWARF 用于结构字段偏移和源码行/局部变量分析，不会自动让 static 函数成为运行时 kprobe 可解析符号；
- 每个候选必须经过同构建 System.map、`/proc/kallsyms`、`available_filter_functions`（若可用）及实际 kprobe 注册结果核验；
- 如果 static 函数不可探测，首选在 STMMAC 公共驱动路径加入最小静态 tracepoint，而不是为了观测而开启全局 function tracer；
- 可将 `CONFIG_KALLSYMS_ALL=y` 作为备选构建配置评估，但不能保证所有优化/内联后的函数都能被探测，也不能替代实际验证。

### 11.5 更新后的最小诊断补丁建议

如需补丁，优先仅新增三个 trace event，不改原有逻辑、寄存器值、descriptor 顺序、DMA barrier、queue flow 或错误处理：

| Event | 插入时点 | 必需字段 |
|---|---|---|
| panther_tx_submit | skb 与 descriptor 已关联、OWN 设置后 | skb、marker/sequence、skb len、queue/index、desc ptr、desc DMA addr、DMA buf addr/len、des0..3 |
| panther_tx_doorbell | `wmb()` 后、tail pointer callback 前 | queue/channel、ring index、tail DMA address |
| panther_tx_complete | status 已读取；OWN 清除分支在 `dma_rmb()` 后 | queue/index、desc ptr/DMA addr、status、des0..3、skb、DMA mapping、completion/error |

实际补丁应避免在 tracepoint 内做动态内存分配、复制整帧、打印大量日志或执行寄存器读写。payload ABCD 仍由发送程序和 `stmmac_xmit` 入口的少量 marker 字节核对；descriptor event 负责把同一 skb 与 DMA buffer/descriptor 对上。若 kprobe 已能安全读取 marker，则先采用 kprobe；否则只在 skb 入口补一个固定长度 marker event。

### 11.6 结论更新

- [x] 确认 STMMAC ring snapshot 不具备活动 DMA 场景下的全 ring 一致性保证。
- [x] 确认 OWN → `wmb()` → tail pointer 的源码顺序。
- [x] 确认 completion 路径的 OWN 检查 → `dma_rmb()` → 状态判断 → DMA unmap → skb consume 顺序。
- [x] 明确 static/local 函数的 kprobe 符号可见性风险（R1 未启用 KALLSYMS_ALL）。
- [x] 将事件式、驱动内精确时点记录作为必要时的最小补丁方案。
- [ ] 实际运行时探针注册与 trace event：未验证。
- [ ] 诊断补丁构建与时序扰动评估：未执行。
- [ ] Panther 实机 DMA descriptor 状态和线侧 TX：未执行。

本补充不改变 B1 前置门，不授权或执行实机 TX。
