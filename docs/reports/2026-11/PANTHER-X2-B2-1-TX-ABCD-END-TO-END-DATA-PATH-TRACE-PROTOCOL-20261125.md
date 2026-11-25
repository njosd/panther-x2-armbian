# Panther X2 Project A — TX “ABCD” 端到端数据流追踪协议

- 日期：2026-11-25
- 源码基线：Linux 6.18.63，ophub/linux-6.18.y @ aee4e352a15d636cbc484f56819c6e59474dfd9f
- 状态：设计/研究规范；不授权构建、启动、trace 或发包。

## 1. 核心思想

使用唯一 payload marker（例如 ASCII “ABCD”）作为数据身份，沿发送路径追踪它的内容、地址引用和所有权交接。不能要求每一层都把字面上的 ABCD 存在寄存器中：不同层对同一帧的表示不同。

- 软件 packet buffer：真实 payload bytes。
- DMA mapping：指向 packet buffer 的 DMA address、length、DMA direction。
- TX descriptor：DMA address、buffer length、packet length、first/last segment 和 OWN/control bits。
- DMA engine：按 descriptor 从映射的内存读取数据。
- MAC：序列化 Ethernet frame，并按硬件配置处理帧格式/FCS。
- PHY：将 MAC 侧数据流编码为物理信号，不保存可由软件普通读取的 ASCII payload 副本。
- 对端抓包：重新解码 Ethernet frame，恢复 payload bytes。

因此验收目标是：**内存边界核对内容身份，DMA/descriptor 边界核对地址、长度和所有权，最后由对端核对完整帧内容。**

## 2. 测试帧身份

首轮专用 Ethernet 帧：
- 目标 MAC：广播地址；
- 源 MAC：Panther 接口 MAC；
- EtherType：0x88B5；
- payload header：固定项目 magic、run ID、递增 sequence、payload length、pattern ID、checksum/hash；
- body：ABCD 重复或确定性字节模式；
- 不包含 IP/ARP/ICMP/DHCP/DNS。

单独的四字节 ABCD 不足以唯一识别一帧。每帧必须有 run ID、sequence 和确定性 payload，防止旧帧、重复帧误判。

首轮选择小型、线性、无 fragment 的帧，避免 scatter-gather/jumbo/VLAN insertion/checksum offload/TSO 造成额外变量。记录并控制 offload；不能假设默认值。之后再增加不同长度。

## 3. 数据交接链

AF_PACKET send()
  -> packet socket / skb
     A: skb bytes + marker/sequence/hash
  -> dev_queue_xmit / qdisc
     B: 同一 skb 或可追溯 clone 到目标 net_device
  -> ndo_start_xmit -> stmmac_xmit()
     C: marker、length、queue、cur_tx index
  -> dma_map_single(skb->data, len, DMA_TO_DEVICE)
     D: map success、DMA address、length、direction
  -> TX descriptor preparation
     E: DMA address、buffer length、packet length、FS/LS、OWN handoff
  -> DMA reads mapped buffer
     F: descriptor ownership/status transition、IRQ/NAPI
  -> stmmac_tx_clean()
     G: completion status、error status、bytes/packets reclaim
  -> MAC -> RGMII -> RTL8211F PHY -> MDI/link -> switch
     H: 对端抓到对应帧
  -> peer capture
     I: sequence、length、payload bytes/hash、frame count

## 4. 各边界如何追踪

### A. AF_PACKET / skb
发送程序在 send 前记录完整帧、长度、sequence 和 hash。内核入口处的诊断观察应确认对应 skb 和 payload。send 系统调用返回只说明 socket 接受/处理了请求，不代表驱动或硬件已发送。

### B. qdisc / net_device
追踪 skb 身份进入目标 net_device。若中间发生 clone/替换，记录 clone/转换关系；不能假设 skb pointer 必须全程不变。可用 pointer/correlation ID 辅助关联，并用 marker/hash 做内容身份核对。

### C. STMMAC TX 入口
在 stmmac_xmit 观察 skb pointer/correlation ID、frame length、marker、queue、当前 descriptor index、fragment 数和 descriptor mode。

固定源码的普通非 jumbo 路径使用 dma_map_single(priv->device, skb->data, nopaged_len, DMA_TO_DEVICE)，检查映射错误，保存 DMA 元数据并将 DMA 地址写入 descriptor。fragment/jumbo 路径不同，所以首轮使用线性小帧。

### D. DMA mapping
记录映射返回成功、DMA address、mapped length、DMA_TO_DEVICE。DMA address 是 I/O DMA 地址，不保证等于 CPU physical address，不能直接当作物理地址解引用。Streaming DMA 有 CPU/device ownership 和同步规则。先核对原 skb bytes，再依 DMA API 语义及 descriptor 证据验证；需要额外证据时添加窄范围诊断 instrumentation，不得随意读取内存。

### E. TX descriptor
记录 descriptor ring index、descriptor DMA address、buffer DMA address、buffer length、packet length、first/last flags、OWN 交接前后状态和完成错误位。

固定源码 DW MAC4 descriptor helper 将 buffer 地址/长度和控制位写入 descriptor，并设置 OWN；descriptor 本身不是 ABCD payload 的副本，而是 DMA 的数据引用和执行说明。

禁止由无关进程持续 dump 正在被 DMA 使用的 ring：CPU 与 DMA 并发更新会造成竞态或误读。优先在精确 handoff/completion 点使用受控诊断 hook，且必须单独构建、单独审计。

### F. DMA 执行
DMA 根据 descriptor 读取映射的 packet buffer。可观察 OWN 被设备清除/归还、descriptor completion status、DMA interrupt/NAPI completion、错误位和 ring index 进展。descriptor 完成是驱动解释的 DMA completion 证据，不独立证明 PHY 发出了正确信号或交换机收到帧。

### G. 驱动完成回收
固定源码 stmmac_tx_clean 检查 descriptor ownership/status，统计完成包和字节，处理错误，解除 DMA mapping 并回收 descriptor。必须将完成事件关联到同一 descriptor index、skb metadata 和 sequence。未做 correlation 的总计数器不能单独识别某个 payload。

### H. MAC / RGMII / PHY
这一层不应期待寄存器中出现 ASCII ABCD。MAC counters/status、link state 是间接证据。RGMII 是并行数字数据/时钟接口；PHY 将数据流编码成物理线侧信号。PHY 管理寄存器通常报告控制/状态，不提供 payload 副本。

只读取源码和芯片文档明确支持的安全状态/计数器；不得猜寄存器地址或读取未文档化 MMIO。MAC/PHY loopback 是额外主动测试，不能替代外部线侧验证。

### I. 对端抓包
这是最终决定性证据。核对源 MAC、广播目标 MAC、EtherType 0x88B5、项目 marker、run ID、sequence、长度、payload bytes/hash、帧数；确认无重复/过期 sequence 和缺失 sequence。

对端抓到正确帧证明帧到达该抓包点，不证明 Panther RX 或更高层协议。

## 5. 观测手段分级

**Tier 1：现有计数器和对端证据**
- 发送程序 expected-frame log；
- 对端逐帧抓包；
- netdev 前后统计；
- 本内核实际可用的 STMMAC ethtool/private stats；
- PHY link 和交换机端口状态。

**Tier 2：内核已有 trace**
先审计最终内核的 tracepoint、function tracing、kprobe/ftrace 配置和实际可用性；不能假定 BPF、ftrace、kprobes、debugfs、ethtool 或 tcpdump 已经包含在 B1。记录 trace buffer、丢事件数、时钟源和 skb correlation。对端抓包工具可以运行在局域网另一台机器，不需要装到 Panther。

**Tier 3：独立诊断构建**
如果现有观测不足，才考虑临时、窄范围 trace instrumentation，分别放在网络层 handoff、STMMAC DMA mapping/descriptor handoff 和 TX completion。只记录 marker/sequence、skb correlation、queue/index、DMA address/length 和 descriptor status；不得改变发送算法、descriptor 内容、时序策略或寄存器值。诊断补丁与功能修复分离，并比较有无 instrumentation 的结果，防止 trace 改变时序。

## 6. 故障定位表

| 最后已确认 | 首个缺失/失败 | 优先调查边界（不是预设根因） |
|---|---|---|
| 发送程序拥有正确帧 | 没有对应 skb/packet path 事件 | 测试程序、packet socket、网络核心 |
| skb 到达 netdev | 没有进入 STMMAC TX | qdisc/netdev queue/driver ops |
| 进入 stmmac_xmit | DMA map 失败 | DMA API/device mapping |
| DMA map 成功 | descriptor 无效或 OWN 未交接 | descriptor preparation/order/ring |
| OWN 已交给 DMA | 无 completion 或 DMA error | DMA engine、bus access、clock/reset、descriptor format |
| descriptor completion | 对端无帧 | MAC TX、RGMII timing、PHY、线缆/交换机/抓包点 |
| 对端有帧但 payload 不符 | 长度/内容/hash 不匹配 | buffer 生命周期、mapping、descriptor segmentation、MAC/offload |
| 对端收到正确帧 | 后续 RX/IP 测试失败 | 不重开 TX 调查，除非 TX 回归也失败 |

这张表用于找到第一条尚未证明的交接边界，不直接宣告根因。

## 7. 重要限制

1. 数据不需要在每层复制；descriptor 可以通过 DMA address 引用同一缓冲区。
2. DMA address 不自动等于 CPU physical address。
3. DMA completion/驱动统计不等于线侧交付。
4. PHY 管理寄存器不提供 payload bytes。
5. PASS-LINE 必须有对端捕获。
6. 诊断 hook 必须最小化并单独审计。
7. interface UP、descriptor dump、寄存器访问、loopback、发包或实机测试均须另行授权。

## 8. 固定源码锚点

commit aee4e352a15d636cbc484f56819c6e59474dfd9f：
- drivers/net/ethernet/stmicro/stmmac/stmmac_main.c：stmmac_open、__stmmac_open、stmmac_hw_setup、stmmac_xmit、stmmac_tx_clean。
- drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c：DW MAC4 descriptor address/length/control/OWN。
- drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c：Rockchip GMAC platform glue。
- drivers/net/ethernet/stmicro/stmmac/stmmac_platform.c：STMMAC platform handoff。
