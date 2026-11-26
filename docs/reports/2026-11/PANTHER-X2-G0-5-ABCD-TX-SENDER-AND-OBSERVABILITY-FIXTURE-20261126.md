# Panther X2 项目 A — G0.5 ABCD 同帧发送器与追踪夹具审查（2026-11-26）

- 状态：**G0.5 观测设计与夹具规格 COMPLETE；运行时 tracefs/kprobe 可用性和目标网口发送均未验证。**
- 范围：复用 R1 AF_PACKET 最终实机报告、R1 实际构建 tracing 能力审计、R5 TX 静态调用链审计；只读审查仓库代码和报告。
- 未执行：未改 sender 源码、未构建新工具、未挂载 tracefs/debugfs、未注册 kprobe、未恢复 GMAC、未发送目标帧、未操作设备。

## 1. 已完成 R1 AF_PACKET 证据的准确边界

R1 最终 probe 已在 Panther X2/Linux 6.18.63+ 实机通过：
- AF_PACKET SOCK_RAW transmit/receive 与 SOCK_DGRAM socket 创建成功；
- socket 在 `lo` 已 UP 后绑定成功；
- RAW sendto 返回 22 bytes，DGRAM sendto 返回 8 bytes；
- RX poll 收到 22-byte frame，EtherType 0x88B5，payload `PX2R1TX!`，packet type `PACKET_OUTGOING`；
- `lo` 原状态成功恢复。

结论仅为 **AF_PACKET 软件 API + loopback 本地 outgoing packet tap PASS**。R1 没有 GMAC1/MDIO/PHY，`PACKET_OUTGOING` 不是对端/线侧证据。

### 1.1 现有 R1 probe 不可直接充当 ABCD 目标发送器

现有 `scripts/panther-x2-b2-1/af-packet-probe.c` 是 R1 软件 API 诊断工具：
- 默认接口为 `lo`；
- RAW 和 DGRAM 分别发送不同格式/长度；
- 固定 marker 为 `PX2R1TX!`，没有 run ID、sequence、统一 payload hash；
- 为 loopback 诊断临时设置 IFF_UP 并在退出时恢复；
- 它不绑定 GMAC，也没有对端捕获和 DMA 关联。

因此保留它作为 R1 软件 API 回归工具，不把它改造成硬件 TX 工具。G0.5 定义独立的后续 `panther-abcd-tx` sender。

## 2. R1 实际构建已具备的观测设施

复用报告 `PANTHER-X2-B2-1-TX-TRACE-OBSERVABILITY-AUDIT-20261125.md`，其核验对象是 R1 最终 artifact 的真实 `.config`、System.map 和 Linux 6.18.63 固定源码：

| 能力 | R1 实际状态 | 用途/限制 |
|---|---|---|
| TRACEPOINTS / TRACING / EVENT_TRACING | y | 静态 trace event 基础 |
| FTRACE | y | 基础框架；不等于函数 tracer |
| FUNCTION_TRACER | 未启用 | 不依赖 function/function_graph |
| KPROBES / KRETPROBES / KPROBE_EVENTS | y | 定点入口/返回探针候选 |
| KALLSYMS | y；KALLSYMS_ALL 未启用 | static/local 符号不保证可由名字注册探针 |
| DEBUG_FS / TRACEFS_AUTOMOUNT_DEPRECATED | y | 具备支持；运行时是否挂载仍未知 |
| DEBUG_INFO_DWARF5 | y；R1 artifact 未带 DWARF vmlinux | R1 不能直接提供 skb 字段偏移 |
| DEBUG_INFO_BTF | 未启用 | 不依赖 BTF/CO-RE |
| DMA_API_DEBUG | 未启用 | 不影响源码中的 DMA tracepoint |

R1 System.map 已包含：
- `net_dev_queue`、`net_dev_start_xmit`、`net_dev_xmit` tracepoint；
- `dma_map_phys`、`dma_unmap_phys` tracepoint；
- `kfree_skb`、`consume_skb`、`napi_poll` tracepoint；
- `register_kprobe`、`register_kretprobe` 等核心符号。

这证明 R1 构建含有观测基础设施，不证明 tracefs 已挂载、事件已启用、目标 kprobe 可注册或 STMMAC 符号已进入 R1（R1 本来就关闭 STMMAC）。

## 3. ABCD 同帧追踪链与现有观测点

| 标记 | 观测点 | 首选证据 | 可证明范围 | 缺口/限制 |
|---|---|---|---|---|
| A | sender `sendto()` | sender 记录完整 frame hex、sequence、length、payload hash、返回字节数/errno | 用户态提交了确定的原始 Ethernet frame | sendto 成功不代表网络核心/驱动/硬件成功 |
| B | 网络核心 | `net:net_dev_queue`、`net:net_dev_start_xmit`、`net:net_dev_xmit` | 用 skbaddr、dev、len、queue、protocol、rc 关联同一 skb 到驱动调用边界 | tracepoint 不包含 payload 字节；以 skbaddr 与 C 关联 |
| C | STMMAC 驱动入口 | `stmmac_xmit` 入口 kprobe，读取 skb 指针、len、data 和固定 payload 字节 | 同一 skb 进入 STMMAC；payload marker/sequence 与 A 一致 | `stmmac_xmit` 为 static/local 候选；KALLSYMS_ALL=n，必须先检查目标 build 的符号可见性和实际 kprobe 注册 |
| D | DMA mapping | `dma:dma_map_phys` + `dma_map_page_attrs` kretprobe | device、phys/DMA address、size、direction、mapping 返回值 | DMA tracepoint 没有 skbaddr；必须单帧串行、单线性 buffer，并将 DMA address 与 descriptor 对照 |
| D+ | descriptor / doorbell | `dwmac4_set_tx_owner`、`dwmac4_set_tx_tail_ptr`、`dwmac4_dma_start_tx` kprobe；必要时最小驱动 tracepoint | DMA buffer 地址进入 descriptor、OWN handoff、软件执行 doorbell/start 路径 | static 函数可能不可探测；kprobe 命中不等于硬件已取走 descriptor |
| completion | completion / reclaim | `dwmac4_wrback_get_tx_status`、`stmmac_tx_clean`、DMA unmap、`skb:consume_skb` | OWN 归还、状态判断、mapping 解除和 skb 回收 | OWN 清除/completion 不等于对端收到 |
| E6 | 对端线侧捕获 | 外部主机 pcap，逐帧解析 EtherType/MAC/sequence/payload hash | 对端实际收到正确 Ethernet frame | 必须确认抓包点在目标链路另一端，不能使用 Panther loopback 代替 |

### 3.1 重要关联规则

1. A/B/C/D 必须是同一帧、同一 sequence；禁止用多帧不同阶段结果拼接成 PASS。
2. 首轮只发一帧、单队列、单 descriptor、线性 skb；禁用 GSO/TSO、VLAN insertion、fragment、多队列并发和不必要 offload。
3. B/C 通过 skbaddr 关联；C/D 通过单帧期间唯一的 DMA mapping、device、长度和 DMA address 关联；D/descriptor 通过 descriptor buffer address 与 DMA address 一致性关联。
4. DMA tracepoint 不带 skbaddr；不能单靠 `dma_map_phys` 证明映射属于某个 skb。若单帧仍无法唯一关联，需在驱动增加最小 tracepoint，或用同构建可用 kprobe 记录映射调用上下文。
5. 不能把 descriptor 当成 payload 副本：descriptor 保存 buffer DMA address、长度、控制/OWN；ABCD payload 在 DMA buffer 中。
6. 不高频轮询 STMMAC `descriptors_status`。其 ring snapshot 无活动 DMA 一致性锁；只作为发送前后辅助快照或 DMA quiescent 后静态检查。
7. 所有 kprobe 的结构偏移必须来自同一 kernel build 的 DWARF/偏移清单，禁止猜测或套用其他版本。
8. 若 kprobe/tracefs 不可用，结论是 OBSERVABILITY BLOCKED，不是网络 FAIL；先补足观测，不增加发送量。

## 4. 独立 ABCD sender 规格（只定义，不实现）

新工具：`panther-abcd-tx`，静态 AArch64 ELF，源码和二进制独立归档。现有 R1 probe 保持不变。

### 4.1 固定帧格式

- Socket：`AF_PACKET / SOCK_RAW`，只发送完整 Ethernet II frame；不使用 SOCK_DGRAM。
- EtherType：实验专用 `0x88B5`，不进入 IPv4/ARP/DHCP/DNS。
- Destination MAC：广播 `ff:ff:ff:ff:ff:ff`；source MAC 从目标 netdev 实际地址读取，不伪造。
- Payload 固定 50 bytes，便于同构建 kprobe 一次读取（小于 64-byte trace array 上限）：

| 字段 | 长度 | 内容 |
|---|---:|---|
| magic | 4 | ASCII `ABCD` |
| run_id | 4 | 本轮唯一标识 |
| sequence | 8 | 单帧序号；首轮固定一个值 |
| payload_len | 2 | 后续校验字段长度 |
| digest | 32 | SHA-256(`magic || run_id || sequence || payload_len`) |

总帧长为 Ethernet header 14 + payload 50 = 64 bytes（不含 PHY/MAC 添加的 FCS）。sender 必须打印完整 frame hex、run_id、sequence、length、digest 和 sendto 返回值。对端从 pcap 解码相同字段并独立计算 hash。

### 4.2 Sender 必须遵守

- 必须显式指定 interface；不存在/不是预期目标时拒绝发送。
- 只读读取 ifindex、MAC、flags；接口 UP 由单独阶段控制，sender 不自动 up/down，不改地址/路由。
- 发送前输出完整测试向量；默认只允许 count=1；若要重复帧，必须在单帧 PASS 后另行确定低速 count/间隔。
- 不使用 raw socket loopback 测试结果作为物理网卡证据。
- 只发送 EtherType 0x88B5；不配置 IP，不启动监听服务，不改变持久状态。
- sender 返回值只用于 A；不得将退出码定义成全链路 PASS。

## 5. 目标内核构建与探针准入要求

R1 的 tracing 能力可作为候选配置模板，但目标 R7 Kernel 构建仍需重新验证最终配置、对象和符号。至少归档：

- 同一 build 的 `.config`、Image、DTB、`System.map`、`vmlinux`（带 DWARF5）或经验证的结构偏移表；
- `stmmac_xmit`、`stmmac_tx_clean`、`dwmac4_set_tx_owner`、`dwmac4_wrback_get_tx_status`、`dwmac4_set_tx_tail_ptr` 等目标符号的实际存在、绑定/内联情况；
- `dma_map_page_attrs` 的实际符号与 kretprobe 可用性；
- 最终 tracepoint event 列表；
- 所有 kprobe event 定义、参数偏移和来源；
- sender 源码/二进制 SHA256；
- 对端抓包脚本/过滤器和 pcap 校验方法。

**不能只因为 R1 的 CONFIG_KPROBE_EVENTS=y，就假设后续 STMMAC static 函数可探测。** R1 的 KALLSYMS_ALL 未启用；若目标函数不可见，优先对 STMMAC 公共发送路径添加最小 tracepoint，不开启全局 function tracer。

## 6. 对端抓包夹具

- 由 iMac 或另一台局域网主机承担，不能使用 Panther 自身 loopback。
- 在目标网口所在同一二层网络、目标链路另一端抓包；记录抓包主机接口/MAC、交换机端口、时间戳和过滤条件。
- 过滤 EtherType `0x88B5`；保存原始 pcap，而不只保存终端摘要。
- 每帧核验 source/destination MAC、EtherType、run_id、sequence、payload_len、digest，并对完整 payload 重新计算 SHA-256。
- 对端必须看到唯一的预期 sequence；缺帧、重复帧、序列错乱或 hash 不一致均不算 TX PASS。
- 先用另一台已知正常设备验证抓包过滤器和 pcap 解析流程；这只是夹具校验，不替代 Panther 测试。
- 对端抓包成功才是 E6 物理 TX 证据；驱动统计、DMA completion、switch port counters 仅作辅助。

## 7. 当前可执行性与 ABCD 节奏

| 当前/未来阶段 | 真实 ABCD 可执行性 | 必须做的检查 |
|---|---|---|
| G0.5（当前） | 不可执行；目标 GMAC disabled | 固定 sender 帧格式、探针字段和对端 pcap 规范 |
| G1–G4 | 不可执行；没有目标 netdev/open/DMA | 每隔一至两门检查一次目标 netdev/open/DMA 条件；不造假帧 |
| G5-A | netdev 注册但未 open 时不可执行 | 只检查 netdev、目标函数符号和 tracepoint/kprobe 可用性 |
| G5-B | 若 interface open 和 DMA 前置条件已满足，才可能单帧执行 | 若未满足，继续 BLOCKED；不为了测试越级 open |
| G6 | 预期首次完整 A→B→C→D | 单帧、单队列、同一 sequence/hash，观察 descriptor/OWN/completion/reclaim |
| G7 | 对端捕获 E6 | 同一测试格式，正确 sequence/hash 到达对端才 TX PASS |
| G8+ | TX 回归帧 | 每个新增 RX/协议层后复测单帧 ABCD，防止回归 |

任何阶段连续两门不能执行真实 ABCD，下一门必须重新评估是否已经出现 netdev/open/DMA 条件；一旦出现，优先做一帧，不等待 IP/ARP/TCP/UDP。

## 8. G0.5 结论与下一步

- R1 AF_PACKET 软件 API 与 loopback outgoing tap 已有实机 PASS，但不能证明 Ethernet。
- R1 最终内核已有 tracepoints、kprobe/kretprobe、DMA/SKB/NAPI 事件基础；目标运行时 tracefs/kprobe 状态未验证。
- 既有 TX trace observability audit 已覆盖大部分 B/C/D 观测设计；本报告将其转为固定 ABCD sender 与单帧对端验证规格，不重复做 R5 源码审计。
- 现有 R1 probe 不适合目标网口：无 run_id/sequence/hash，且发送对象是 lo。应新建独立 sender，不修改 R1 工具。
- 首轮必须单帧、小包、单队列、无 GSO/VLAN/fragments；B/C 用 skbaddr 关联，D 用单帧 DMA map + descriptor address 关联。
- static/local STMMAC/DWMAC4 函数是否能 kprobe 必须由目标 build 证实；必要时采用最小静态 tracepoint，不启用全局 function tracer。
- 物理 TX 最终必须由对端 pcap E6 确认。

**G0.5 设计结论：COMPLETE（STATIC DESIGN）；没有硬件发送授权。** G0.5 后 G0 总审仍需把 G0.1–G0.5 条件和风险统一复核；G0 总审通过前不进入任何硬件激活门。
