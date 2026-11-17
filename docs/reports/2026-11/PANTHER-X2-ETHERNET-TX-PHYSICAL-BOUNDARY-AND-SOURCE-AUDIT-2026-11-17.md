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
