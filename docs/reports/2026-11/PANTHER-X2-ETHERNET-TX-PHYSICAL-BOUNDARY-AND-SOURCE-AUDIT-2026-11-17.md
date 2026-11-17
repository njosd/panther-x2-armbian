# Panther X2 Ethernet TX 物理边界测试与 STMMAC 源码审计（2026-11-17）

- 设备：Panther X2 / Rockchip RK3566
- 当前系统：Armbian，Linux `6.12.81-rk35xx-ophub`
- 对照基线：已验证网络正常的 Linux `6.1.116-ophub`
- 本记录范围：2026-11-17 继续进行的 TX 路径验证、自定义 Ethernet 帧外部接收验证、TX 统计语义审计，以及 Ophub Rockchip 6.1/6.12 STMMAC/DWMAC4 源码对照。
- 记录性质：按用户在本轮对话提供的实机结果和已完成的源码审查整理；不是设备原始日志逐字节副本。没有提供的字段不补造。
- 操作边界：本轮没有安装软件、修改网络配置、修改设备树/内核/驱动或写寄存器。除文中明确记载的一次只读 debugfs 访问导致设备崩溃外，没有进行设备侧改动；该访问已列为禁止重复操作。

## 1. 当前问题定义与关键结论

当前需要解释的现象是：Panther X2 在 Linux 6.12.81 上可以生成并提交 Ethernet TX 帧，Linux 本机 outgoing 抓包可见，但 hEX 没有观察到相应 DHCP Discover；进一步发送的自定义广播帧和发往 iMac 有线 MAC 的单播帧，也没有被 iMac 的持续抓包监听捕获。

现有证据支持：
1. Linux 网络协议栈确实产生了待发送帧。
2. 帧进入 `stmmac_xmit()`，该函数返回 `NETDEV_TX_OK`。
3. TX descriptor 后续被驱动清理路径回收；Linux TX packet/byte 统计和 MAC MMC TX frame/octet 统计在所记录的同一启动周期快照中同步增加。
4. 这些软件与 MAC 统计不能证明帧已通过 RGMII/PHY 电气接口到达网线另一端。
5. iMac 在用户确认持续运行的 tcpdump 监听期间，没有捕获 EtherType `0x88B5` 的测试帧。
6. 目前尚不能把故障精确归因到 GMAC TX、MTL/DMA 队列、RGMII 时序、PHY 发射或更下游链路中的某一个环节。

**当前工作边界：GMAC/MTL/DMA 到 RGMII/PHY 的真实发送边界仍未被证明。** 不将本机 outgoing 抓包、`NETDEV_TX_OK`、descriptor cleanup 或 MMC 计数等同于物理出线成功。

## 2. 测试拓扑与外部接收端

- Panther X2：`eth0`，Linux 接口 MAC 为板载地址（本公开报告不重复暴露完整 MAC）。
- iMac：有线接口 `en0`，MAC 为用户提供的 iMac 有线 MAC；链路协商为 `1000baseT full-duplex`。
- iMac tcpdump：过滤 EtherType `0x88B5`，在 Panther 发帧期间持续运行。
- hEX：此前同步排查 DHCP Discover 时，用户已确认 hEX 没有收到对应 Discover；其他客户端 DHCP 正常。
- 网线：此前千兆链路问题已通过更换网线解决，不把旧网线问题重新作为本轮默认解释。

用户明确确认 iMac tcpdump 在 Panther 发帧时一直保持监听。不得将未捕获结果归咎于监听启动太晚，也不得要求重复执行同一轮监听/发帧测试。

## 3. 自定义 Ethernet 帧外部接收测试

### 3.1 测试方法

Panther 使用 AF_PACKET raw socket 发送自定义 Ethernet 帧，EtherType 为 `0x88B5`。测试覆盖：
- 广播帧；
- 目的 MAC 为 iMac 有线接口 MAC 的单播帧；
- 单帧标记：`PX2-ONE-FRAME-TEST-20261117`。

每轮发送调用均返回成功。iMac 的 `en0` tcpdump 同步过滤 `ether proto 0x88b5`。

### 3.2 结果

- iMac 没有捕获广播测试帧。
- iMac 没有捕获发往其有线 MAC 的单播测试帧。
- iMac 没有捕获单帧标记 `PX2-ONE-FRAME-TEST-20261117`。
- 最终 tcpdump 统计：`0 packets captured`、`5719 packets received by filter`、`0 packets dropped by kernel`。

解释边界：
- `packets received by filter` 是抓包 socket/filter 收到的流量统计，不代表匹配 EtherType 的测试帧存在。
- `0 packets captured` 与用户确认的持续监听共同支持“测试帧未被 iMac 抓到”。
- Panther raw socket 发送成功只代表本机发送调用成功，不等于线上送达。
- 此测试没有证明故障一定在 PHY；仍需区分 MAC/MTL/DMA 的真实输出、RGMII 电气接口、PHY 编码/发射及链路下游。

## 4. Linux TX 路径探针证据

### 4.1 保留的 ftrace/kprobe

以下两个探针已安装并保留，后续分析可引用已有结果，不要求重复执行：

```text
p:stmmac_probe/xmit stmmac_xmit skb=$arg1 dev=$arg2
r10:stmmac_probe/xmit_ret stmmac_xmit ret=$retval
```

已观察到：
- 测试帧进入 `stmmac_xmit()`。
- `stmmac_xmit()` 返回 `NETDEV_TX_OK`。

含义：驱动接受了该 TX 请求。它不是 PHY 发送完成回执，也不是外部接收端确认。

临时 NAPI 探针已删除。不要重复做已经完成的入口/返回测试。

### 4.2 TX descriptor 清理与统计语义

已结合当前候选 STMMAC 源码核对：
- `stmmac_tx_clean()` 检查 TX descriptor OWN 位；在 DMA 归还 descriptor 后执行相应读屏障/状态处理、解除 DMA mapping 并回收 skb/descriptor。
- 驱动成功完成包计数在清理路径中更新；这说明 DMA descriptor 已进入驱动认定的完成状态。
- descriptor completion 仍不能独立证明 PHY 已将帧从 MDI 端口发出，也不能证明远端收到。

本轮同一启动周期的计数样本：
| 采样阶段 | Linux TX packets / driver completion | MMC TX frame count |
|---|---:|---:|
| 初始记录 | 548（早期接口快照） | 548 |
| 自定义单帧测试前 | 549 | 549 |
| 自定义 60-byte 帧后 | 550 | 550 |

自定义帧后：
- Linux TX packets：+1
- Linux TX bytes：+60
- MMC TX frame count：+1
- MMC TX octets：+64

60 与 64 字节差值符合 MAC MMC octets 统计包含 4 字节 FCS、而 Linux skb/interface bytes 不包含 FCS 的常见统计差异；此处是与观察数据相符的解释，不是线上波形测量。

### 4.3 其他 TX 统计

本轮用户提供的快照中：
- `tx_underflow`：0
- `tx_frame_flushed`：0
- `tx_payload_error`：0
- `tx_ip_header_error`：0
- `mtl_tx_status_fifo_full`：0
- `mtl_tx_fifo_not_empty`：0
- `tx_normal_irq_n`：22
- `q0_tx_irq_n`：22

接口状态：`eth0 UP, LOWER_UP`，接口 MAC 为板载地址。

MMCs category counters（包括 unicast / 64-octet 类计数）为 0，而总 frame/octet 计数增长。该现象值得进一步对照 MMC counter 定义、硬件统计配置和实际帧分类；目前不能解释为“没有发出单播帧”，也不能据此判定 MMC 故障。

`mmc_tx_framecount_gb` 中 `GB` 表示 good + bad frames，不是纯成功帧数；总计数增长只说明 MAC MMC 计数路径记录到帧，不是 PHY 电气出线证明。

### 4.4 旧的跨快照差异结论已撤销

此前曾将不同上下文中的 `tx_pkt_n=392` 与 `mmc_tx_framecount_gb=4` 并列，怀疑 6.12 同一启动周期中软件与 MMC 计数断层。后续启动时间、驱动生命周期和连续采样已核对，当前启动周期内可比的 netdev/driver/MMC TX 计数一致增长。

因此：
- 撤销“当前 6.12.81 启动内软件 TX 完成计数与 MMC TX 计数严重不一致”的结论。
- `392/4` 的来源/生命周期未确认，不作为当前根因证据。
- 不再使用不同启动周期或不同采样上下文的累计值直接相减。

## 5. 6.1 Rockchip 与 6.12 Rockchip 源码对照

源码仓库：
- `unifreq/linux-6.1.y-rockchip`
- `unifreq/linux-6.12.y-rockchip`

当前比较对象是两个 Rockchip 专用源码分支，不等于已经证明设备运行的 6.12.81 二进制完全由其中某一 commit 原样构建。Ophub 构建流程可能应用额外 kernel patches/configuration，实际发布构建与源码候选的精确映射仍待核实。

### 5.1 已比较的文件

- `drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_dma.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4_core.c`
- `drivers/net/ethernet/stmicro/stmmac/dwmac4.h`
- `drivers/net/ethernet/stmicro/stmmac/descs.h`
- 另对照了 `dwmac-rk.c`、Panther X2 DTS 与相关 pinctrl DTS。

### 5.2 `stmmac_xmit()` 的版本变化

目前已看到的差异包括：
- 6.1 调用 `stmmac_enable_dma_transmission(priv, ioaddr)`；6.12 调用增加了 `queue` 参数。
- TX 统计结构由旧同步统计迁移到新版 NAPI statistics。
- 6.12 增加/调整了部分 checksum fallback 和 EST 最大 SDU 检查。
- `stmmac_tx_clean()` 的核心 descriptor completion/cleanup 逻辑没有发现足以解释本故障的根本性变化。

当前 AF_PACKET EtherType `0x88B5`、60-byte 自定义帧不依赖常规 IP checksum offload；EST 检查是否对当前接口/队列启用及实际路径是否生效仍需由完整调用链确认。因此这些差异目前只是审计对象，不是已定位根因。

### 5.3 DMA channel 初始化

两版 `dwmac4_dma_init_tx_chan()` 主体相同：
- 读取 TX channel control；
- 设置 TX PBL；
- 设置 OSP；
- 按配置写入 TX descriptor base address 高/低位。

两版 `dwmac4_dma_init_channel()` 也未见实质差异。

因此现有对照没有显示 6.1→6.12 在 TX descriptor ring base 初始化上发生明显改变。

### 5.4 待继续追踪的 DMA 启动与 MTL 队列映射

尚需完成：
1. `stmmac_enable_dma_transmission()` 的 6.1/6.12 定义与调用链。
2. `stmmac_dma_ops` 的 `.start_tx` callback 绑定到哪个实现。
3. DWMAC4 真正启动 TX channel 的函数及 queue 参数语义。
4. `dwmac4_map_mtl_dma` 的版本差异，及相关 `MTL_RXQ_DMA_MAP*`、`MTL_QX_TXMIIOM` 等寄存器/宏。
5. 默认单队列/queue 0 设备是否在两个版本中都映射到 DMA channel 0；6.12 是否改变映射或默认值。

已有初步比对提示 `dwmac4_map_mtl_dma` 有变化，涉及旧的 Q04MDMACH 特殊处理与较通用 queue mapping 逻辑；尚未完成逐分支条件和寄存器语义核验，不能把该变化直接认定为 Panther X2 故障原因。

如果 queue0 → DMA channel0 映射无实质差异，下一步再比较 descriptor 构造、OWN 位写入顺序、DMA write barrier、ring tail pointer/doorbell 更新，以及 `enh_desc` / `dwmac4_descs.c` 的相关路径。重点只追当前 AF_PACKET 小帧会经过的普通 TX 路径。

## 6. Rockchip GMAC、DTS 与 RGMII 已有对照结论

已完成的静态比较：
- `rk3568_set_to_rgmii()`：6.1/6.12 一致。
- `rk_gmac_powerup()`：一致。
- `rk_gmac_clk_init()`：一致。
- `gmac_clk_enable()`：按最新完整函数对照结果一致。
- `rk_fix_speed()`：函数签名有变化，核心逻辑相同。
- Panther X2 DTS `&gmac1` 配置块在两个分支一致：
  - `clock_in_out = "input"`
  - `phy-mode = "rgmii"`
  - TX delay `0x30`
  - RX delay `0x10`
  - PHY reset GPIO 与延时设置一致。
- `rk3568-pinctrl.dtsi` 中 GMAC1 六组相关 pin 定义在两个分支一致。

运行时 DT 已核实：
- 节点 `/proc/device-tree/ethernet@fe010000` 存在。
- compatible：`rockchip,rk3568-gmac` + `snps,dwmac-4.20a`
- status：`okay`
- phy-mode：`rgmii`
- clock_in_out：`input`
- TX/RX delay：`0x30 / 0x10`
- PHY child：MDIO address 0。

时钟摘要曾读取到 GMAC1 相关时钟 125 MHz。运行时 pinctrl 实际应用状态仍未得到充分验证；源码 pinctrl 定义一致不代表运行时 pinmux 必然正确。

这些结果降低了“板级 DTS 中 RGMII 模式/延迟配置在两个分支被改坏”的可能性，但不能证明 GRF/pinctrl 实际寄存器状态和 RGMII 物理波形正常。

## 7. 公开案例和 patch 线索

- Ophub `kernel_rk35xx` 是面向 RK35xx 系列（包括 RK3566）的专用内核源码/构建项目；其构建体系允许额外 kernel patch/configuration。因此必须继续核对发布 6.12.81 内核与候选源码的确切关系。
- Panther X2 曾有历史 Ethernet 不工作报告（Ophub issue #1960，涉及旧内核环境）。该案例仅证明历史上存在相似现象，不能证明与本轮同根因。
- 2025 年 RK3566/RK3568 dwmac-rk RGMII delay enable patch 调整了 delay enable/disable 配置顺序。当前比较的两个 Rockchip 分支已包含一致实现，运行时 `phy-mode=rgmii`；现有证据不支持将该 patch 当作本轮直接根因。
- 以上均为外部源码/历史 issue 线索，不替代本机实测。

## 8. 一次只读 debugfs 访问导致崩溃：危险操作封存

2026-11-17，读取 debugfs 下 dummy-syscon 的 `registers` 文件时，设备发生同步外部中止并失去响应，断电重启后恢复。崩溃栈包括：
- `regmap_mmio_read32le`
- `_regmap_bus_reg_read`
- `_regmap_read`
- `regmap_read`
- `regmap_read_debugfs`

目标路径属于 `/sys/kernel/debug/regmap/dummy-syscon@0x.../registers`。

当前没有证据证明这次崩溃与 Ethernet TX 故障存在因果关系。它只说明该 dummy-syscon debugfs register read 在当前设备/映射环境中不安全。

**永久排除以下重复操作：**
- 不再读取 `/sys/kernel/debug/regmap/*/registers`，尤其 dummy-syscon。
- 不使用 `devmem` 访问相关 MMIO。
- 不再尝试通过 dummy-syscon 读取 GMAC/GRF 寄存器。
- 不做寄存器写入、驱动重载或内核修改。

后续优先使用静态源码、已取得的运行时设备树、既有日志与安全的只读软件接口；若某项现场寄存器证据无法安全取得，应明确标为未验证，而不是冒险读取。

## 9. 证据状态表

| 项目 | 状态 | 说明 |
|---|---|---|
| Linux 生成 outgoing 帧 | 已验证 | 本机 outgoing 抓包及 AF_PACKET 测试 |
| 进入 `stmmac_xmit()` | 已验证 | 保留的 ftrace/kprobe 入口记录 |
| `stmmac_xmit()` 返回 `NETDEV_TX_OK` | 已验证 | 保留的 return probe |
| TX descriptor 被清理/驱动完成统计增加 | 已验证（软件/驱动层） | `stmmac_tx_clean()` 语义与计数增量 |
| MAC MMC TX frame/octet 计数增长 | 已验证 | 同一轮测试前后计数 |
| iMac 收到自定义帧 | 未发生/未观察到 | 持续监听，0 packets captured |
| hEX 收到对应 DHCP Discover | 未观察到 | 用户已确认 hEX 未收到 |
| MAC/MTL/DMA 实际 TX 输出状态 | 部分验证 | 已有 enable/统计快照，但非测试帧发送瞬间完整状态 |
| queue0 到 DMA channel0 映射 | 待源码核实 | 重点比较 6.1/6.12 |
| DMA 启动函数与 queue 参数语义 | 待源码核实 | 尚未完成完整 callback 链 |
| RGMII TXC/TXD 电气波形 | 未验证 | 未使用示波器/逻辑分析仪 |
| RTL8211F MDI 侧真实发射 | 未验证 | 没有 PHY 线侧测量 |
| 6.12.81 发布二进制的精确源码/patch 映射 | 未验证 | 当前候选源码不能替代发布构建证明 |
| 运行时 pinctrl/GRF 实际状态 | 未完全验证 | 不通过危险 dummy-syscon 读取补证 |

## 10. 下一步研究顺序

不要求用户重复现有测试，不要求重启、改配置或再发送相同测试帧。继续在源码和仓库证据上推进：

1. 完成 `stmmac_enable_dma_transmission()`、`.start_tx` callback、DWMAC4 TX channel start 的调用链。
2. 逐项核对 `dwmac4_map_mtl_dma` 和 queue0 → DMA channel0 的映射语义。
3. 如映射无异常，再对照普通 TX descriptor 构造、OWN 位、barrier、tail pointer/doorbell 更新。
4. 查明 Ophub 6.12.81 发布包的精确源码 commit、patch list 与 build config；不可将候选分支直接当成实际二进制来源。
5. 只有静态证据仍不足且确实能区分假设时，再提出最小化只读现场核查；先说明命令、目的和风险，绝不读取上述危险 MMIO debugfs 节点。

## 11. 关联记录

- [6.12.81 Ethernet 测试结果汇总](./PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md)
- [网络与启动链阶段测试总记录](./PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)
- [GMAC / DHCP 与 TF U-Boot 启动链调查](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)
- [2026-11 报告索引](./README.md)
- [6.1.116 Ethernet 基线原始采集（脱敏）](../../evidence/network/panther-eth-baseline-redacted.txt)
- [6.1.116 Ethernet 补充采集（脱敏）](../../evidence/network/panther-eth-supplement-redacted.txt)



## 12. TX queue / DMA channel 调用链的进一步核实（追加，2026-11-17）

继续读取两个 Rockchip 分支的 `hwif.h`、`dwmac4_dma.c`、`dwmac4_lib.c` 与 `stmmac_main.c)，得到以下更精确结论。

### 12.1 `stmmac_enable_dma_transmission()` 并不是 DWMAC4 的 TX channel start

- `stmmac_enable_dma_transmission()` 是通过 `stmmac_do_void_callback()` 调用 `dma_ops->enable_dma_transmission` 的通用包装。
- 6.1 和 6.12 的 `stmmac_do_void_callback()` 宏相同：仅当对应 callback 非 NULL 时才调用，否则返回 `-EINVAL`，不执行硬件操作。
- 两个分支的 `dwmac4_dma_ops` / `dwmac410_dma_ops` 初始化表均未设置 `.enable_dma_transmission` 字段。
- 因而 Panther X2 当前使用 DWMAC4 DMA ops 时，普通 `stmmac_xmit()` 中该 callback 调用不会启动 DWMAC4 TX DMA。真正的 descriptor 提交动作由后续 `stmmac_flush_tx_descriptors()` 更新 TX tail pointer 完成。
- 6.12 将通用 callback 参数从 `(ioaddr)` 扩展为 `(ioaddr, queue)`，对当前 DWMAC4 callback=NULL 的路径没有直接作用。不能把这项 API 变化本身当作 Panther TX 故障原因。

### 12.2 DWMAC4 的 channel start 实现两版相同

`dwmac4_dma_start_tx()` 在 6.1 与 6.12 的实现一致：
1. 读取对应 channel 的 `DMA_CHAN_TX_CONTROL`。
2. 设置 `DMA_CONTROL_ST`。
3. 写回 TX channel control。
4. 读取 `GMAC_CONFIG`，设置 `GMAC_CONFIG_TE` 并写回。

`dwmac4_dma_ops` 的 `.start_tx` 在两版均绑定 `dwmac4_dma_start_tx`。未发现此函数在两个候选源码分支间的行为差异。

### 12.3 普通 TX queue 到 DMA channel 的关系

两版 `stmmac_main.c` 的 TX queue 初始化和发送路径均显示：
- TX DMA channel 初始化循环以 `chan` 遍历 `tx_cnt)，使用 `tx_queue[chan]`。
- `stmmac_init_tx_chan(..., tx_q->dma_tx_phy, chan)` 用相同的 `chan` 初始化该 TX queue 的 DMA channel。
- 普通发送从 `skb_get_queue_mapping(skb)` 取得 `queue`，选择 `tx_queue[queue]`。
- `stmmac_flush_tx_descriptors(priv, queue)` 对应的 `stmmac_set_tx_tail_ptr(..., tx_tail_addr, queue)` 把 tail pointer 写入同编号 DMA channel。
- 因此当前 queue 0 发送路径使用 DMA channel 0；这是 TX queue 与 DMA channel 的直接索引关系，不依赖 `dwmac4_map_mtl_dma()`。

用户记录的 TX 统计为 q0 路径，且测试帧进入普通 `stmmac_xmit()`。所以应优先核对 DMA channel 0 的 descriptor ring/tail pointer 提交行为，而不是 RX MTL queue mapping。

### 12.4 TX descriptor flush 与 memory barrier 两版相同

6.1 与 6.12 的 `stmmac_flush_tx_descriptors()` 函数内容一致：
- 根据 enhanced descriptor / TBS 选择 descriptor size；
- 在更新 tail pointer 前执行 `wmb()`；
- 计算 `dma_tx_phy + cur_tx * desc_size`；
- 通过 `stmmac_set_tx_tail_ptr()` 将新 tail address 写到与 queue 同编号的 DMA channel。

函数注释明确要求 OWN bit 是 descriptor 准备阶段最后设置的状态，再以 barrier 确保 descriptor 内容在交给 DMA 前可见。当前两分支该 flush/barrier 顺序没有差异。

### 12.5 方向修正后的源码审计重点

目前：
- RX MTL queue→DMA mapping 的版本差异已确认，但与当前 TX 故障不是同一条路径，暂降为低优先级。
- DWMAC4 TX start 函数一致。
- queue 0→DMA channel 0 的 TX 索引关系一致。
- TX flush、`wmb()` 和 tail pointer 更新函数一致。
- `stmmac_xmit()` 的 6.1/6.12 普通发送路径仍有少量顺序变化（6.12 新增 `skb_tx_timestamp()` 的位置等），但 descriptor OWN 与 flush 的核心次序尚未发现被反转或移除。

下一步重点应收敛到：
1. 6.12 与 6.1 的 descriptor prepare / set owner 实际实现及 DWMAC4 descriptor format；
2. DMA address mapping、IOMMU/coherent DMA 属性和 TX ring memory；
3. Ophub 6.12.81 发布二进制对应的确切源码 commit 与 patch/config 集合；
4. 对现有安全证据重新判断是否能定位到 DMA descriptor 已完成之后、RGMII/PHY 之前的边界。

以上为候选源码对照结果，不代表实际运行二进制已被证明与候选源码逐字节对应。


## 13. Ophub 发布构建流程与实际二进制来源核验（追加，2026-11-17）

已读取 Ophub 仓库当前 `.github/workflows/compile-rockchip-rk35xx-kernel.yml`（workflow blob SHA `ea1e0c531b1b10c2ce67e3ab08ed46f8d6541f66`）和 `README.md`。

该 workflow 明确显示：
- `kernel_source` 是可选输入，允许选择 `unifreq/linux-6.12.y-rockchip` 或 `ophub/linux-6.12.y-rockchip` 等来源。
- `kernel_version` 可选择 `6.12.y`。
- `kernel_auto` 默认 true。
- workflow 在构建前通过 GitHub API 读取所选源码仓库 `main` 分支的当前 HEAD SHA，并写入环境变量 `source_hash`。
- `kernel_config` 默认指向 `kernel-config/release/rk35xx`，也允许关闭该配置覆盖。
- kernel 构建通过 `ophub/amlogic-s9xxx-armbian@main` 执行。
- 构建产物上传到可更新的 `kernel_rk35xx` release tag。

因此，仅凭运行内核字符串 `6.12.81-rk35xx-ophub` 和构建日期，无法唯一反推出：
1. 选择的是 unifreq 还是 ophub 的 6.12 Rockchip 源码仓库；
2. 构建时对应 `main` 分支的确切 commit；
3. `kernel_auto` 实际解析到的源码版本；
4. 当次构建实际应用的 config 与 patch 集；
5. 当前设备的 Image 是否就是该 workflow 某次发布的原始资产，或经过二次打包/替换。

Ophub README 也明确区分 RK35xx 专用 BSP 内核，并说明可通过 `kernel-config` 与 `kernel-patch` 自定义构建。由此，当前对 `unifreq/linux-6.12.y-rockchip` 的源码审计只能作为有针对性的候选对照，不能声称已审计了 Panther 当前运行的精确构建源代码。

**后续最小化证据目标：** 从设备现有 Image 的 build metadata、安装/下载记录、kernel package 文件名与哈希，或当次 GitHub Actions workflow run/构建日志中，寻找 source repository、source SHA、kernel config 与 patch 应用记录。若设备侧现存文件没有这些元数据，则需要用户提供当时下载的原始 kernel package 或其文件名/哈希；不要求重启或修改设备。

参考：
- [Ophub RK35xx compile workflow](https://github.com/ophub/kernel/blob/main/.github/workflows/compile-rockchip-rk35xx-kernel.yml)
- [Ophub kernel README](https://github.com/ophub/kernel/blob/main/README.md)


## 14. DWMAC4 descriptor、DMA mapping 与 PHY fixup 的进一步对照（追加，2026-11-17）

### 14.1 DWMAC4 TX descriptor 格式和 OWN 位设置

对照两个 Rockchip 分支 `drivers/net/ethernet/stmicro/stmmac/dwmac4_descs.c`：
- `dwmac4_rd_prepare_tx_desc()` 函数体逐字一致。
- `dwmac4_set_tx_owner()` 函数体逐字一致。
- `dwmac4_set_addr()` 函数体逐字一致：分别把 DMA address 的低 32 位写入 `des0`、高 32 位写入 `des1`。
- `dwmac4_set_sec_addr()` 函数体也一致。

普通 DWMAC4 descriptor 中：
- payload buffer length 写入 `des2)；
- packet length、FIRST/LAST、checksum insertion 和 OWN 标志写入 `des3)；
- 首 descriptor 的 OWN 提交前，`dwmac4_rd_prepare_tx_desc()` 使用 `dma_wmb()`；
- TX 发送结束后 `stmmac_flush_tx_descriptors()` 再用 `wmb()` 后更新 tail pointer。

上述关键函数 6.1/6.12 未发现差异。当前没有源码证据支持“6.12 把 DWMAC4 TX OWN 位放错 descriptor word”或“DMA 地址高低位写反”。

### 14.2 普通 AF_PACKET 小帧所经过的 DMA mapping

两个分支的普通 `stmmac_xmit()` 都使用：
- `dma_map_single(priv->device, skb->data, nopaged_len, DMA_TO_DEVICE)`
- 检查 `dma_mapping_error()`
- 保存返回的 DMA address；
- 通过 DWMAC4 `set_addr` callback 写入 descriptor。

两版 `dwmac4_set_addr()` 相同。两版设置 DMA host/device width 的代码也相同：先按硬件/平台 host DMA width 调用 `dma_set_mask_and_coherent()`，失败时回退 32-bit mask。

实机日志证据：
- 6.1.116 基线日志：GMAC 报告 `Using 32/32 bits DMA host/device width`。
- 6.12.81 补充日志：同样报告 `Using 32/32 bits DMA host/device width`。

这说明两套实机启动时驱动最终采用的 host/device DMA width 均为 32/32；降低了“6.12 改成 64-bit DMA 地址模式导致 descriptor 地址解释不同”的可能性。

但仍需区分：
- 32/32 width 是驱动设置的 DMA mask/硬件地址宽度摘要；
- 它不能单独证明每一次 `dma_map_single()` 返回的 IOVA/物理 DMA address、cache maintenance 和 descriptor payload 内容正确；
- 现有 kprobe 没有直接读取 descriptor DMA address 或 payload 内存内容，不能补造这类证据。

### 14.3 GMAC 是否挂接 Rockchip IOMMU

两个候选分支的 `rk356x.dtsi` 中 `gmac1: ethernet@fe010000` 节点均未声明 `iommus` 属性。Panther X2 板级 `&gmac1` 配置块也未额外声明 `iommus`。

日志中的 IOMMU 默认 domain 为 Translated，不能因此推断 GMAC 自身使用 IOMMU。采集日志里出现的 `fdea0800.iommu` 属于 `vdpu_mmu`（视频解码单元），不是 GMAC1 的 IOMMU；不要将它与当前 TX 故障混为一谈。

据当前 DTS 静态证据，GMAC1 没有通过设备树绑定到该 Rockchip IOMMU。DMA API 仍然必须正确工作，但“GMAC IOMMU page-table 映射错误”暂时缺少设备树基础，应降为低优先级。

### 14.4 6.1 分支存在、6.12 分支缺失的 RTL8211F LED PHY fixup

另发现一个与 PHY 有关、但目前不支持作为 TX 根因的分支差异：
- 6.1 Rockchip 分支的 `stmmac_main.c` 存在 `#define LED_FIX 1` 代码块，并注册 RTL8211F PHY UID fixup。
- RTL8211F fixup 切换 PHY 扩展页 `0xd04`，写寄存器 `0x10=0xc160`、`0x11=0x0008)，随后切回 page 0；源码注释将其标为 LED 配置。
- 6.12 Rockchip 分支没有这组 `LED_FIX` 代码和 RTL8211F LED fixup 注册。

当前判断：
- 这是候选源码中真实存在的 PHY 初始化差异，值得保留在版本差异清单中。
- 从函数内容和注释看，它调整的是 RTL8211F LED 配置，不是 RGMII delay、TX/RX 时钟、MAC interface mode 或 PHY advertisement。
- 因而目前不把它当作 TX 无帧输出的根因。
- 6.1.116 运行日志是否实际执行过该 fixup 尚无明确日志证据；不能把“源码存在 fixup”写成“6.1.116 实机已执行 fixup”。
- 该 fixup 的寄存器读写返回值处理也不严谨，但不建议在未取得 PHY 数据手册/可靠驱动资料前推断其会破坏 PHY 正常收发。

### 14.5 当前 DMA / descriptor 方向结论

已确认相同的部分：
- 32/32 DMA host/device width；
- GMAC1 DTS 未挂接 IOMMU；
- 普通 `dma_map_single(DMA_TO_DEVICE)` 调用模式；
- DWMAC4 DMA address low/high word 写入；
- DWMAC4 TX descriptor 格式；
- OWN 位设置与 `dma_wmb()`；
- tail pointer flush 的 `wmb()` 顺序。

尚未确认的部分：
- 6.12.81 实际发布二进制是否来自当前候选源码；
- 实机每个测试帧对应的 DMA address 与 descriptor 内容；
- DMA 读取的 payload 字节是否与 AF_PACKET 提交内容一致；
- MAC TX 输出引脚上的 RGMII TXC/TXD 波形；
- RTL8211F 线侧 MDI 发射是否正常。

下一步应将重点从“源码里是否明显改坏 descriptor 格式”转向“实际 6.12.81 构建来源和 PHY/MAC 初始化路径差异”，同时继续审查 Rockchip GMAC 的 TX/RGMII 时钟及 PHY 状态配置；不得通过读取 dummy-syscon debugfs 寄存器或 devmem 获取现场寄存器值。


## 15. Rockchip glue、phylink 与 RTL8211F 初始化路径继续对照（追加，2026-11-17）

### 15.1 RK3568/RK3566 专用 RGMII 配置函数保持一致

再次逐函数核对两个 Rockchip 分支的 `dwmac-rk.c`：
- `rk_gmac_powerup()` 一致；
- `rk_gmac_clk_init()` 一致；
- `rk3568_set_to_rgmii()` 一致；
- `rk3568_set_gmac_speed()` 一致；
- `rk3568_ops` 中 GMAC1 的资源地址、RGMII speed callback 绑定一致；
- `rk_fix_speed()` 的函数签名从 `(priv, speed)` 改为 `(priv, speed, mode)`，但函数体仍按相同的 PHY interface mode 调用 `set_rgmii_speed()`，新增的 `mode` 参数未参与配置。

对当前运行时 DT 的 `phy-mode = "rgmii"`、`clock_in_out = "input"`、TX/RX delay 0x30/0x10 而言，候选源码两版的 Rockchip RGMII 选择、delay 写入和按链路速率设置 `clk_mac_speed` 逻辑没有发现差异。

### 15.2 Rockchip glue 初始化有结构性变化，但当前未构成故障证据

`rk_gmac_setup()` 在 6.12 做了更严格的 GRF 获取检查：
- 6.1 对 `rockchip,grf` lookup 结果保存后继续初始化，后续 RGMII 函数遇到错误会打印并跳过 GRF 写入；
- 6.12 对 `rockchip,grf` lookup 失败直接 probe 失败；
- 6.12 还按 SoC ops 的 `php_grf_required` 条件获取 PHP GRF，并在要求但缺失时 probe 失败。

当前 6.12 实机 GMAC 驱动已成功 probe，运行时设备树的 `rockchip,grf` 属性存在，故“GRF phandle 缺失导致未配置 RGMII”不符合当前证据。不能为验证这一点读取任何 dummy-syscon MMIO/debugfs registers。

### 15.3 phylink / PHY fwnode 解析接口有变化

`stmmac_init_phy()` 在 6.1 从 `plat->phylink_node` 取得 firmware node；6.12 改用 `plat->port_node`，并在手动 PHY 连接分支新增 `phy_support_eee()`（仅当 DMA capability 支持 EEE）。

`stmmac_mdio_register()` 同样从旧的 `phylink_node` 改为 `port_node`，并调整 MDIO C22/C45 callback 和 PHY mask 处理。

当前设备树 PHY 节点仍为 `mdio/ethernet-phy@0`，PHY addr 0 已由 MDIO/PHY ID 证据确认。尚未找到证据显示 6.12 把 Panther 的 PHY 连接到了错误节点；但 port-node 迁移是值得与实际 DT parse/运行时 phylink attachment 日志交叉核验的版本变化，暂列“结构性变化、影响未证实”。

### 15.4 RTL8211F config_init 细节变化

两个候选分支的 `rtl8211f_config_init()` 对当前 RGMII 模式的核心动作一致：
- 配置 ALDPS；
- 对 `PHY_INTERFACE_MODE_RGMII` 将 PHY 内部 TX delay 和 RX delay 都设置为 0；
- 写入扩展页 `0xd08` 的 delay 控制位。

这与当前设备树 `phy-mode = "rgmii"` 及 Rockchip GMAC 内部 `tx_delay=0x30/rx_delay=0x10` 的设计相匹配：延迟由 MAC/SoC 侧配置，PHY 侧关闭内部 RGMII delay。没有看到 6.12 在这两项 delay 选择上与 6.1 不同。

差异主要是 LED 恢复流程：
- 6.1 的部分路径读取 DT `realtek,led-data` 并直接写 LED 页；
- 6.12 改为调用 `rtl8211f_restore_leds()`，并在部分提前返回路径也恢复 LED；
- `has_phycr2` 路径的软复位与 LED restore 顺序也有调整。

这些变化看起来集中在 LED 配置恢复，而不是 MAC/PHY 数据通道配置。除非后续找到 LED fixup 对 PHY page selector/复位状态造成副作用的证据，否则优先级低。

### 15.5 本轮收敛结论

当前候选源码对照没有发现 RK3568 RGMII delay、MAC speed clock rate、RTL8211F 内部 TX/RX delay 选择存在 6.1→6.12 的直接变化。

新增需要保留的两个版本变化：
1. `stmmac_init_phy()` / MDIO 注册改用 `port_node`，其影响需结合实际运行时 phylink attachment 确认；
2. Realtek RTL8211F LED restore/config 逻辑改变，但暂未显示与数据帧 TX 有直接关系。

因此，当前更重要的未知量仍是：
- 实际 6.12.81 构建是否应用了候选源码之外的补丁；
- 6.12.81 实际 phylink/PHY attachment 和 link-up 回调链；
- TX DMA completion 之后 GMAC MAC TX/RGMII 输出是否有有效波形。

下一轮应检查实际源码构建身份与 phylink link-up 回调参数/调用时序，并继续从已有启动日志找 PHY attach、link-up、clock rate 记录。无需新增设备侧测试；禁止读取 dummy-syscon 寄存器。


## 16. 6.12.81 实际构建来源已由 GitHub Actions 日志锁定（重大进展，2026-11-17）

此前第 13 节将实际构建来源列为未知。现在已找到与实机内核 build timestamp 完全吻合的 Ophub GitHub Actions run，并从该 run 的 job log 取得 source hash、编译参数和 config 来源。该部分结论应覆盖第 13 节原先的“尚无法确定”状态。

### 16.1 对应的构建任务

- Workflow run：[`43405957386`](https://github.com/ophub/kernel/actions/runs/43405957386)
- Workflow：`Compile rockchip rk35xx kernel`
- 开始时间：2026-11-13 10:01:57 UTC
- Job：`build`，成功完成
- Job ID：`131820239401`
- 运行时读取的 kernel source：`ophub/linux-6.12.y-rockchip`
- Branch：`main`
- 精确 source commit：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 自动查询并构建的 kernel：`6.12.81`
- 输出 LOCALVERSION：`-rk35xx-ophub`
- 编译日志明确输出 kernel output name：`6.12.81-rk35xx-ophub`

用户提供的运行内核标识：
`6.12.81-rk35xx-ophub #1 SMP Fri Nov 13 11:02:28 UTC 2026`

Actions 日志在 2026-11-13 11:02:28.858 UTC 记录：
`UPD include/generated/utsversion.h`
随后在 11:03:00.573 UTC 记录：
`OBJCOPY arch/arm64/boot/Image`

因此，实机 `uname -v` 的秒级 build timestamp 与这次构建中更新 UTS version header 的时刻完全一致；版本字符串和 LOCALVERSION 也一致。这构成非常强的构建来源指纹。**当前可以高置信度将实机 6.12.81 对应到该次 Actions 构建任务**，但在没有设备上已安装 Image 的 SHA256 或原始安装包文件名时，仍不声称已经对设备当前 Image 做了二进制哈希验证。

### 16.2 构建参数和补丁状态

该次 Actions log 明确记录：
- `kernel_source = ophub/linux-6.12.y-rockchip`
- `kernel_version = 6.12.y`
- `kernel_auto = true`
- `kernel_package = all`
- `kernel_toolchain = gcc`
- `kernel_sign = -rk35xx-ophub`
- `kernel_config = kernel-config/release/rk35xx`
- `kernel_patch = false`
- `auto_patch = false`
- `No custom kernel patches provided.`
- 构建时从 `ophub/linux-6.12.y-rockchip/main` clone 源码；
- 日志确认解析出的版本为 `6.12.81`；
- 使用 `config-6.12` 作为初始 `.config`。

source commit SHA 是 `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，而 workflow 自身 commit 为 `f8925391bb2ba2634bb8ca55da39e1a2f4029ffe`。两者不能混为一谈：前者是 Linux kernel source commit，后者用于确定 Ophub 构建仓库中的 workflow/config 文件版本。

### 16.3 6.12 实际构建源码与此前候选源码逐文件核对

从 `ophub/linux-6.12.y-rockchip@661b2d8` 读取源文件，并与此前用来对照的 `unifreq/linux-6.12.y-rockchip` 默认分支比较，以下文件内容和 Git blob SHA 完全一致：
- `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`
- `stmmac_main.c`
- `stmmac_platform.c`
- `stmmac_mdio.c`
- `dwmac4_dma.c`
- `dwmac4_core.c`
- `dwmac4_descs.c`
- `dwmac4.h`
- `descs.h`
- `hwif.h`
- `drivers/net/phy/realtek.c`
- `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`
- `arch/arm64/boot/dts/rockchip/rk356x.dtsi`

这意味着此前关于 6.12 TX DMA、descriptor、Rockchip GMAC glue、phylink、RTL8211F、Panther X2 DTS 的代码对照，虽然当时拿的是 unifreq 6.12 候选分支，但现在已经由文件 blob SHA 证明：**这些被审计文件与实机高置信度构建源 commit 完全一致。** 之前的代码分析可升级为针对实际 6.12.81 源码的有效审计结论，而不再只是近似候选。

### 16.4 该次构建使用的正式配置

从 workflow commit `f8925391bb2ba2634bb8ca55da39e1a2f4029ffe` 读取：
`kernel-config/release/rk35xx/config-6.12`
Blob SHA：`966f4b6ac7c0ad59179d6ae272423500601fab07`

与当前排查相关的配置：
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_PLATFORM=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_DWMAC_ROCKCHIP_TOOL=y`
- `CONFIG_PHYLINK=y`
- `CONFIG_PHYLIB=y`
- `CONFIG_REALTEK_PHY=y`
- `CONFIG_ARCH_DMA_ADDR_T_64BIT=y`
- `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y`
- `CONFIG_ROCKCHIP_IOMMU=y`
- `# CONFIG_STMMAC_SELFTESTS is not set`
- `# CONFIG_DMA_API_DEBUG is not set`

注意：`CONFIG_ROCKCHIP_IOMMU=y` 是全局 SoC 驱动配置，不代表 GMAC1 绑定到 IOMMU；GMAC1 DTS 仍未声明 `iommus`。此外，正式构建配置中 `CONFIG_STMMAC_SELFTESTS` 明确未启用。若设备侧曾观察到相反的 running config 值，则需要区分该值来自哪一版内核/哪份 config，不能把不同版本混为一谈。

### 16.5 发布资产与精确安装包的边界

同一 workflow run 在 11:14:34 UTC 成功打包：
- `6.12.81.tar.gz`
- `deb-6.12.81.tar.gz`

对应 release asset `6.12.81.tar.gz` 于 11:14:36 UTC 创建，SHA256：
`72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`

同一 release 另有 `6.12.81-rk35xx-flippy-2611b.tar.gz`，于 11:04:04 UTC 创建，SHA256：
`a5b0bc5d3c8311cee472c105e5ee2d1c9e6395a94efb4488253a0faae132d064`
Release 描述明确说明文件名带 `flippy` 的包由 Flippy 手动上传，而无该后缀的包是在线自动编译。不能把两种资产误认成同一个构建产物。实机的 build timestamp 强烈指向上述 11 月 13 日构建，但尚未从设备现有安装记录确认实际使用了哪个 archive。

### 16.6 对研究路线的影响

1. 6.12.81 的源码来源已锁定为 Ophub repo commit `661b2d8`，配置来源也已锁定。
2. 前面审计过的 6.12 STMMAC / DWMAC4 / Rockchip glue / Realtek PHY / Panther DTS 文件均与该 commit 完全一致。
3. 当前应把研究重心转向：该精确 6.12 源 commit 相对实际 6.1.116 工作版本的变更，以及两者正式配置差异。
4. 6.1.116 的精确源码 commit/config/package 来源仍未锁定；不能默认它就是当前 unifreq 6.1 分支的任意 HEAD。
5. 不需要在 Panther 上重复发送帧或抓包，也不需要修改设备。任何后续现场取证应先从只读文件/日志着手。
