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


## 17. 实际构建中启用的 Rockchip 专用 loopback 工具及其诊断边界（追加，2026-11-17）

通过已锁定的实际 config：
`CONFIG_DWMAC_ROCKCHIP_TOOL=y`
以及同一 source commit 的 STMMAC Makefile：
`dwmac-rockchip-$(CONFIG_DWMAC_ROCKCHIP_TOOL) += dwmac-rk-tool.o`
确认 Panther 当前 6.12.81 构建包含 Rockchip 专用测试工具 `dwmac-rk-tool.c`。它与 `CONFIG_STMMAC_SELFTESTS` 是不同的机制；实际发布 config 中 `CONFIG_STMMAC_SELFTESTS` 未启用，因此不能期待 `ethtool -t` 暴露 STMMAC self-test。

### 17.1 工具提供的三类 sysfs 功能

源码创建的属性：
- `rgmii_delayline`：读写缓存的 TX/RX delayline 值；
- `mac_lb`：MAC 内部 loopback；
- `phy_lb`：PHY BMCR loopback；
- `phy_lb_scan`：扫描 RGMII delayline 组合。

### 17.2 `rgmii_delayline` 读取不是硬件寄存器回读

`dwmac_rk_get_rgmii_delayline()` 只返回 `bsp_priv->tx_delay` 与 `bsp_priv->rx_delay` 两个软件缓存值；这些值在 probe 时从设备树读取，写入 delayline sysfs 时也同步更新。

所以读取该 sysfs 文件只会显示驱动缓存的值，不能证明 GRF 硬件寄存器实际写入成功，也不能替代 pinctrl/GRF 的独立验证。当前不能把它当作新的现场硬件证据。

### 17.3 MAC loopback 与 PHY loopback 的覆盖范围

- `mac_lb` 设置 GMAC `GMAC_CONTROL_LM`，在 MAC 内部形成回环。它检查专用 DMA descriptor ring、DMA TX/RX、MAC 内部数据路径，但不经过 RGMII 和 RTL8211F 的数据接口。
- `phy_lb` 设置 PHY `MII_BMCR.BMCR_LOOPBACK`，同时强制 MAC/PHY 速率，然后由 MAC TX 发测试帧，经 RGMII TX 到 PHY，再由 PHY 内部回环经 RGMII RX 返回 MAC RX。它能覆盖 MAC↔PHY 的 RGMII 数据路径，但不验证 PHY MDI 线侧发射器、磁性器件、网线和外部 iMac 收包。
- `phy_lb_scan` 会反复调用 `dwmac_rk_set_rgmii_delayline()`，写入 Rockchip GRF 的 RGMII delay 值，属于主动硬件调参，不是只读检查。

### 17.4 loopback 测试本身具有明显影响，未执行

`dwmac_rk_loopback_run()` 会：
1. 获取 RTNL lock；
2. 如果网卡处于 UP 状态，调用 `ndo_stop()` 停止网卡；
3. assert/deassert STMMAC reset，并对 PHY 发起 BMCR reset polling；
4. 设置 PHY/MAC loopback；
5. 重新初始化专用 DMA descriptor ring、DMA channel 0、MAC core、MTL/MAC 队列；
6. 发送测试包并检查 RX；
7. 释放专用 DMA 资源、关闭 loopback，再重新 `ndo_open()`。

因此执行 `mac_lb` 或 `phy_lb` 会短暂中断 eth0 网络并复位 GMAC/PHY；执行 `phy_lb_scan` 还会修改 GRF delay 配置。当前用户未授权任何设备配置/硬件状态修改，本轮只做静态源码审计，没有执行这些操作。

### 17.5 6.1 与实际 6.12 工具代码存在差异，影响测试结果解释

- 6.1 的 `dwmac_rk_xmit()` 调用旧版 `stmmac_enable_dma_transmission(priv, ioaddr)`；6.12 增加 queue 参数并传入 0。
- 6.1 的 loopback 等待逻辑使用 TX/RX interrupt 条件组合，且循环条件存在不合理的 `delay <= 0`；6.12 改为等待 RX interrupt，并以 `delay > 0` 控制超时。
- 6.1 的 `dwmac_rk_rx_validate()` 会检查接收帧并调用 payload 内容校验；6.12 版本主要验证接收长度是否与预期相同，不再逐字节比较 payload。

所以 6.12 工具比旧版修正了等待 RX 完成的逻辑，但其 PASS 结果只证明 RX descriptor 完成且帧长符合预期，不能当作完整 payload 逐字节校验。

### 17.6 后续可用作定点分界测试，但需单独授权

如果后续决定进行一次有控制的主动验证，优先级是：
1. `phy_lb`（1000 Mbps）：验证 MAC↔RGMII↔PHY internal loopback 的完整内部数据路径；
2. 与现有外部 iMac 收包失败证据结合，判断问题更靠近 PHY 线侧发射还是更靠近 MAC/RGMII；
3. 不先运行 `phy_lb_scan`，因为它会批量写入 GRF delayline，且会改变当前配置。

本轮没有运行 loopback、没有写入 delayline，也没有读取任何 dummy-syscon/MMIO debugfs 寄存器。

---

## 18. 6.12 DWMAC4 DMA 初始化函数差异再核对（追加，2026-11-17）

针对精确 6.12.81 source commit `661b2d8` 与 6.1 Rockchip 分支继续比较 `dwmac4_dma.c`：
- `dwmac4_dma_init_channel()` 一致；
- `dwmac4_dma_init_rx_chan()` 一致；
- `dwmac4_dma_init_tx_chan()` 一致；
- `dwmac4_dma_init()` 的函数签名移除了旧的 `atds` 参数，但函数体对 DMA_SYS_BUS_MODE、DMA_BUS_MODE 的配置步骤一致；旧参数在该函数体内没有被使用。

因此目前没有发现 DWMAC4 TX channel PBL、OSP、descriptor base address 初始化行为发生实质变化。此项继续降低了“6.12 初始化 TX DMA channel 时漏设关键寄存器”的可能性。


## 19. 6.1.116 工作内核的真实基线重新锁定：它是 Ophub 通用内核，不是 RK35xx 专用内核（重大纠正，2026-11-17）

此前把 `unifreq/linux-6.1.y-rockchip` 作为 6.1.116 工作系统对照源，是不准确的。结合用户原系统元数据与 2024 年 Ophub 构建工作流，现已找到更匹配的真实基线。

### 19.1 6.1.116 构建类型与源码候选

用户原系统元数据为：
- `KERNEL_SIGNATURE='ophub'`
- `KERNEL_TAGS='stable'`
- `KERNEL_REPO='ophub/kernel'`
- uname build time：`Sun Nov 10 08:21:17 EST 2024`

Ophub 在 2024-11-10 的 workflow 文件：
`.github/workflows/compile-release-general-kernel.yml`
明确设置：
- workflow 时区 `America/New_York`；
- `kernel_source` 默认值 `unifreq`（可选 `codesnas`）；
- `kernel_version` 可选 `6.1.y`；
- `kernel_sign` 默认 `-ophub`；
- `kernel_config` 默认 `kernel-config/release/general`；
- release tag 为 `kernel_stable`。

与此不同，专用 RK35xx workflow 的默认签名是 `-rk35xx-ophub`，release tag 是 `kernel_rk35xx`。

在 `unifreq/linux-6.1.y` 上按 2024-11-10 13:21:17 UTC（即 08:21:17 EST）查找当时 HEAD，得到：
- source commit：`5eb841b59d6ead6e264163785a634e78f0253c8e`
- commit date：2024-11-09 08:06:23 UTC
- commit message：`up to 6.1.116`

同一时点 `codesnas/linux-6.1.y` 也指向相同 SHA。因此即使当时 workflow 输入选择了 codesnas，源码 commit 仍相同。

**判断：** 用户原 6.1.116 系统极高概率来自 Ophub 通用 stable kernel workflow，使用 Linux 6.1.116 通用源码 commit `5eb841b`，而不是后来的 RK35xx 专用 6.1 分支。由于 2024 年对应的旧 Actions run log / 原始安装包哈希尚未取得，仍保留“高置信度重建”而非二进制级确认。

参考：
- [Ophub 2024 general kernel workflow](https://github.com/ophub/kernel/blob/8f6eb6e392d68b89a4708c8c45caf9d3f46eadaa/.github/workflows/compile-release-general-kernel.yml)
- [6.1.116 source commit](https://github.com/unifreq/linux-6.1.y/commit/5eb841b59d6ead6e264163785a634e78f0253c8e)
- [Ophub workflow/config update commit, 2024-11-10](https://github.com/ophub/kernel/commit/8f6eb6e392d68b89a4708c8c45caf9d3f46eadaa)

### 19.2 两次内核构建实际上来自不同内核系列/构建配置

| 项目 | 工作正常的 6.1.116 | 故障的 6.12.81 |
|---|---|---|
| Ophub workflow | general kernel | RK35xx kernel |
| kernel source | `unifreq/linux-6.1.y`（高置信度） | `ophub/linux-6.12.y-rockchip` |
| source SHA | `5eb841b...`（高置信度） | `661b2d8...`（Actions log 确认） |
| signature | `-ophub` | `-rk35xx-ophub` |
| config family | `kernel-config/release/general/config-6.1` | `kernel-config/release/rk35xx/config-6.12` |
| source basis | 通用 Linux 6.1.y | Rockchip vendor 6.12 BSP |

这说明不能把问题简单归类为“同一 RK35xx BSP 从 6.1 升级到 6.12”。实际是从通用 6.1 kernel 切换到 Rockchip vendor 6.12 BSP。此前使用 `unifreq/linux-6.1.y-rockchip` 对照得到的 6.1 侧结论，不再代表用户原来正常工作的 6.1.116 系统；后续以本节的 `unifreq/linux-6.1.y@5eb841b` 为工作基线。

### 19.3 设备树：板级 GMAC 与 pinctrl 实际保持一致

对比两个准确候选 source commit：
- 6.1：`unifreq/linux-6.1.y@5eb841b`
- 6.12：`ophub/linux-6.12.y-rockchip@661b2d8`

结果：
- Panther X2 DTS 的完整 `&gmac1` 板级配置块规范化空白后完全一致；
- 六个 GMAC1 pinctrl group 内容逐字一致：
  - `gmac1m0_miim`
  - `gmac1m0_clkinout`
  - `gmac1m0_rx_bus2`
  - `gmac1m0_tx_bus2`
  - `gmac1m0_rgmii_clk`
  - `gmac1m0_rgmii_bus`
- TX/RX 引脚及 drive-level 配置没有变化；
- 两版 Panther DTS 都使用 `phy-mode="rgmii"`、`clock_in_out="input"`、`tx_delay=0x30`、`rx_delay=0x10`、PHY addr 0、相同 reset GPIO 与 reset delays。

SoC `rk356x.dtsi` 的 GMAC1 clock-names 在 6.12 增加了 `pclk_xpcs` 和 `clk_xpcs_eee`，与 SGMII/QSGMII XPCS 支持有关；对 Panther 当前 RGMII 模式，新驱动仅在 SGMII/QSGMII 分支获取这两项。

### 19.4 Rockchip GMAC glue 的真实差异：时钟管理和 GRF 写入顺序

这次从真正的 6.1.116 generic source 比较后，发现此前未覆盖的实际差异：

**A. GMAC clock enable 稳定等待时间变化**
- 6.1.116 generic `gmac_clk_enable()`：bulk enable clocks、执行可选 clock selection 后，`mdelay(5)`，即等待约 5 ms。
- 6.12.81 RK35xx `gmac_clk_enable()`：逐项 enable clock、执行 clock selection 与 CSU disable 后，`usleep_range(100, 200)`，等待约 100–200 µs。

这是实际存在的约 25–50 倍等待时间缩短。两版对 Panther RGMII 实际需要的核心时钟（`aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`）均有 enable 路径；旧版额外 bulk 获取的 `pclk_xpcs` 对 RGMII 不应是必要时钟。

当前判断：这是值得重点审查的启动时序差异，但 PHY 后续有 GPIO reset delays（20 ms + 100 ms）且系统最终能够 link-up，因此还不能仅凭等待时间缩短就认定根因。

**B. RK3568 RGMII GRF 写入顺序变化**
- 6.1.116：先向 GMAC1 CON0 写 TX/RX delay value，再向 CON1 写 RGMII interface select 与 RX/TX delay enable bits。
- 6.12.81：先向 CON1 写 RGMII interface select 与 `DELAY_ENABLE()`，再向 CON0 写 `DELAY_VALUE()`。

在当前 `phy-mode=rgmii` 且 TX/RX delay 都非零（0x30/0x10）时，两版预期最终 enable/value 状态相同；但硬件寄存器写入顺序确实相反。需要保留为候选时序差异，不将其夸大为已证实故障。

**C. 6.12 新增 CSU 支持对 Panther GMAC 节点应无作用**
6.12 的 `rk_gmac_csu_init()` 查找 `rockchip,csu`，而当前 Panther GMAC1 节点没有该属性；`rockchip_csu_get()` 因缺少 phandle 返回错误，驱动将句柄置 NULL，后续 CSU helper 对 NULL 返回 0。因此不能把 CSU disable 当作当前 Panther 实际执行的配置步骤。

### 19.5 配置差异与 DMA 路径

Ophub 2024 general config：
- file blob：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_SELFTESTS=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_REALTEK_PHY=y`
- `CONFIG_PHYLINK=y`
- `CONFIG_ARCH_DMA_ADDR_T_64BIT=y`
- `CONFIG_ROCKCHIP_IOMMU=y`
- `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y`
- `CONFIG_DMA_API_DEBUG` 未启用

Ophub 2026 RK35xx config：
- file blob：`966f4b6ac7c0ad59179d6ae272423500601fab07`
- 上述主要驱动/架构配置相同；
- `CONFIG_STMMAC_SELFTESTS` 未启用；
- 新增 `CONFIG_DWMAC_ROCKCHIP_TOOL=y`；
- 新增 `CONFIG_STMMAC_ETHTOOL=y`。

所以用户此前记录的 `CONFIG_STMMAC_SELFTESTS=y` 对应旧 6.1.116 general config；6.12.81 正式 config 中该项未启用。这解释了两版测试能力不同，但不是普通 TX 数据路径故障证据。

在实际 6.1.116 generic source 与实际 6.12.81 BSP source 间再次核对：
- DWMAC4 descriptor `dwmac4_rd_prepare_tx_desc()`、`dwmac4_set_tx_owner()`、`dwmac4_set_addr()` 仍一致；
- `stmmac_flush_tx_descriptors()` 仍一致，OWN barrier 和 TX tail pointer 顺序未变；
- `dwmac4_dma_ops` 两版均无 `.enable_dma_transmission` callback，均绑定 `.start_tx = dwmac4_dma_start_tx`；
- `stmmac_xmit()` 6.12 新增 EST max-SDU 检查及非 IP/不支持 COE 情况的 checksum software fallback；Panther DTS 未配置 EST，用户 AF_PACKET EtherType 0x88B5 raw frame 正常情况下不会进入 checksum fallback。其 descriptor/DMA mapping/flush 主体仍一致。

### 19.6 运行时 clock-names 核对（已完成）

此前建议只读核对的 `/proc/device-tree/ethernet@fe010000/clock-names` 已有实测结果，不再列为待办。运行时 FDT 共 10 项：
`stmmaceth`、`mac_clk_rx`、`mac_clk_tx`、`clk_mac_refout`、`aclk_mac`、`pclk_mac`、`clk_mac_speed`、`ptp_ref`、`pclk_xpcs`、`clk_xpcs_eee`。
因此当前运行时 DT 确实提供 6.12 Rockchip glue 对 RGMII 所需的 `mac_clk_tx`、`aclk_mac`、`pclk_mac`、`clk_mac_speed` 名称。该项已关闭，不重复要求用户读取。

本节的源代码/配置比较均为静态分析；没有对 Panther 执行 loopback、写入 GRF、修改系统配置或读取 dummy-syscon。


## 20. TX MTL/FIFO 配置路径与时钟启动差异复核（追加，2026-11-17）

本轮继续只审计 TX，不执行设备侧测试。比较基线为实际 6.12.81 source commit `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 与 6.1.116 高置信度工作基线 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。

### 20.1 DWMAC4 TX MTL queue operation mode

- `dwmac4_dma_tx_chan_op_mode()` 的 6.1/6.12 主要配置逻辑相同：store-and-forward/threshold、TXQEN、TQS 的处理没有实质变化；变化主要是 DWMAC4 register address helper 的调用接口。
- `dwmac4_prog_mtl_tx_algorithms()` 两版函数体逐字一致。
- `stmmac_dma_operation_mode()` 存在变化：6.1 总是按 RX/TX queue 数量拆分 FIFO；6.12 仅对 `has_gmac4` 或 `has_xgmac` 拆分。Panther 运行时 compatible 为 `snps,dwmac-4.20a`，被识别为 GMAC4；运行时 DT 的 TX queue 配置为 1，因此两版对当前 Panther 的 FIFO 分配结果相同。
- `dwmac4_map_mtl_dma()` 的版本差异涉及 `MTL_RXQ_DMA_MAP0/1`，实现的是 RX queue 到 DMA channel 的映射，不是 TX queue 的数据发送映射。TX queue 0 仍由普通发送路径直接索引 TX DMA channel 0。

**结论：** 当前没有发现 6.1→6.12 的 TX MTL queue mode、TX scheduling algorithm、TX FIFO partition 或 queue0→DMA0 路径变化足以解释普通 DHCP/raw frame 无法到达外部接收端。

### 20.2 6.12 时钟启用等待时间缩短：真实差异，但尚非根因

逐函数核对实际 6.12.81 的 `dwmac-rk.c` 与 6.1.116 工作基线：

- 6.1.116：通过 `clk_bulk_prepare_enable()` 启用核心时钟，检查返回值；随后调用 clock-selection callback，并等待 `mdelay(5)`（约 5 ms）。
- 6.12.81：逐个调用 `clk_prepare_enable()`；这些调用的返回值没有被检查；随后等待 `usleep_range(100, 200)`（约 100–200 μs），再将 `clk_enabled` 设为 true。
- 等待时间缩短约 25–50 倍，是明确的源码差异。6.12 的个别 clock lookup 错误只打印日志而不直接终止 probe；但本机运行时 clock-names 已核实存在，且 clk_summary 显示核心 GMAC 时钟链已启用，故当前没有证据证明某个 clock lookup/enable 实际失败。

历史依据：2014 年 Rockchip GMAC 驱动提交讨论中，维护者被问及 `mdelay(5)` 是否用于 PLL source stabilization，作者答复“yes”。这说明旧等待时间原本有稳定时钟源的设计意图；但该历史讨论不能单独证明当前 RK3566 RGMII 输入时钟配置也必须等待 5 ms。参考：[Linux Rockchip GMAC driver discussion](https://lists.infradead.org/pipermail/linux-rockchip/2014-November/001611.html)。

### 20.3 Panther 当前时钟父项使该差异暂时降级

现有实机证据：

- 运行时 FDT：`clock_in_out = "input"`。
- `assigned-clock-parents` 的末级 parent 指向外部固定时钟节点 `gmac1_clkin`。
- 运行时 clk_summary：`gmac1_clkin`、`clk_gmac1`、`clk_gmac1_rgmii_speed`、`clk_gmac1_rx_tx` 均显示 125 MHz 且处于 enable 状态。
- `mac_clk_tx`、`clk_mac_speed` 的 consumer 均落在 `clk_gmac1_rx_tx` 这条 125 MHz 时钟链上。

因此，当前 Panther 使用 PHY 输入的 125 MHz reference clock，而不是简单依赖内部 PLL 产生 GMAC1 参考时钟。软件时钟树的 parent/rate/enable 状态符合运行时 DT 设计；这降低了“当前时钟父项选错/频率错误/时钟未使能”的可能性。

仍然不能据 clk_summary 证明 GMAC TXC/TXD 引脚上实际有正确的 125 MHz RGMII 波形，也不能证明启动时钟稳定瞬态完全没有问题。故将 5 ms→100–200 μs 保留为**待解释的时序差异**，但优先级低于直接检查 MAC TX/RGMII 物理输出；不把它写成根因。

### 20.4 本轮 TX 审计状态更新

已完成：
- 普通 SKB/AF_PACKET TX descriptor 构造、DMA mapping、OWN、barrier、tail pointer；
- DWMAC4 TX channel start 与 queue0→DMA0；
- TX MTL queue mode、scheduler、FIFO partition；
- 6.1.116 与 6.12.81 的 32/32 DMA width、无 GMAC IOMMU 绑定；
- 当前运行时 GMAC 时钟名称、父项及软件频率状态。

仍未完成/未验证：
- 单个 DHCP Discover 对应的 TX descriptor DMA address、descriptor 内容和 payload 内容；
- 同一个 Discover 是否从 GMAC TXC/TXD 引脚实际发出；
- RTL8211F MDI 侧实际发射与外部接收端的逐帧边界；
- 6.12 运行时 MAC TX output waveform 与 PHY 输入采样时序。

**下一步继续围绕“MAC TX/RGMII TXC/TXD 是否真实输出”推进，不转向 RX dropped。** 不重复已完成的 TX descriptor/MTL 静态比较，不执行 loopback、phy_lb、phy_lb_scan、接口重启或任何寄存器写入；若需要示波器/逻辑分析仪测量，应先说明测点和所需设备，再由用户决定。


## 21. RGMII TX 物理测量点与判读方法（追加，2026-11-18）

本轮只进行公开硬件资料研究和既有证据边界整理；未要求用户拆机、探测引脚或执行设备侧操作。

### 21.1 Panther X2 板级资料可获得性

公开资料可以确认 Panther X2 使用 RK3566、千兆 Ethernet，第三方实机拆机资料识别其 PCB 为 BROWAN H1GW V04；但本轮没有找到可核验的 H1GW V04 Ethernet 原理图、PCB netlist 或 RGMII 测试点编号。故不能把其他 RK3566 板卡的电阻编号、走线位置或电压配置直接套用到 Panther X2。

参考：
- [Panther X2 hardware identification (BROWAN H1GW V04)](https://lorenzogangemi.com/blog/repurposing-panther-x2/)
- [Panther X2 product manual / FCC filing](https://fccid.io/)

### 21.2 可直接定位的 RTL8211F RGMII TX 测点

当前运行日志识别 PHY 为 RTL8211F Gigabit Ethernet。RTL8211F 40-pin QFN datasheet 给出 MAC→PHY 输入脚：

| RTL8211F pin | 信号 | 用途 |
|---:|---|---|
| 20 | TXC | MAC 提供给 PHY 的发送参考时钟 |
| 19 | TXCTL | 发送控制 |
| 18 | TXD0 | 发送数据 bit 0 |
| 17 | TXD1 | 发送数据 bit 1 |
| 16 | TXD2 | 发送数据 bit 2 |
| 15 | TXD3 | 发送数据 bit 3 |

在 1000BASE-T 模式，TXC 为 125 MHz；TXD[3:0] 与 TXCTL 按时钟上升沿和下降沿传输。PHY datasheet 的 RGMII timing table 给出 8 ns 标称时钟周期，并列出 sub-ns 级边沿/时序参数。

**物理边界判定：** 若能在 PHY 输入侧的 TXC/TXCTL/TXD[3:0] 观察到与测试发送同步的活动，说明信号至少到达 RTL8211F 的 RGMII 输入端；若 MAC 发送计数增长、但 PHY 输入侧没有相应 TXC/TXCTL/TXD 活动，则故障边界仍在 GMAC/RGMII pinmux/GRF/板级走线到 PHY 输入之间。仅有 TXC 时钟而没有 TXCTL/data 不能算作帧已传输。

参考：[Realtek RTL8211F datasheet, sections 6.3, 7.11.1 and RGMII timing](https://file3.dzsc.com/datasheet/22/04/14/150904366.pdf)。

### 21.3 电压与测量安全约束

- RK3566 RGMII IO domain 可为 1.8 V 或 3.3 V，必须与 PHY RGMII IO 电平一致；公开的 RK3566 设计指南没有给出 Panther H1GW V04 的具体选择。因此在取得 Panther 原理图或确认 PHY VDDIO 实际电压之前，不应按 3.3 V 或 1.8 V 预设探头逻辑阈值。
- Rockchip 参考设计要求 TXD/TXEN/TXCLK 串联电阻靠近 RK3566，TXCLK 与 TXD/TXEN 走线时延匹配；指南列出 50 Ω ±10% 单端阻抗及 TX/RX 相关布线约束。这些是通用设计要求，不代表已证明 Panther PCB 不符合。
- 不能用普通逻辑探头直接接触 0.4 mm pitch QFN 邻脚进行试探；应优先寻找 TX 信号串联电阻的可接触焊盘或专用测试点，并使用高阻、低电容探头和可靠接地。探测 PHY 芯片脚存在短路风险。
- 若要只判断“有没有发送活动”，可先以 TXCTL 触发观察 TXC/TXD；若要逐位解码并核验整个帧，需要同时采集 TXC、TXCTL、TXD0–3 六路信号。RGMII 为 DDR，采样/带宽必须足以分辨 125 MHz 时钟两边沿的数据；低速、低采样率逻辑分析仪不能用于时序合规判断。
- 任何探测都应先确认探测点、电压、地参考和仪器输入规格。不得为找测点而使用 devmem、dummy-syscon debugfs、写寄存器或改 delayline。

### 21.4 当前可以下的结论与不能下的结论

**已知：**
- Linux outgoing、驱动接受、descriptor 清理和 MAC MMC TX 计数有正向证据；
- iMac 持续抓包未收到自定义广播/单播测试帧；
- 当前软件时钟树显示外部 125 MHz reference clock 与 GMAC 时钟链已启用；
- PHY 型号和其 RGMII TX 输入引脚定义可以由公开资料确定。

**未知：**
- Panther H1GW V04 的 RGMII 实际 IO 电压；
- PHY 输入脚/串联电阻在 PCB 上的准确可接触位置；
- 发送测试帧期间 TXC/TXCTL/TXD[3:0] 是否出现符合时序的电气波形；
- PHY MDI 四对差分线是否真正发出对应编码信号。

### 21.5 下一项行动顺序

1. 先确认是否能取得 Panther X2 PCB 清晰近照（能看到 RTL8211F 芯片标记、周边电阻/丝印）或 H1GW V04 原理图；仅用于识别测点，不要求拆焊或改动。
2. 由板级资料确定 RGMII IO 电压与 TX 串联电阻/测试点。
3. 若有合适示波器及探头，再决定是否做一次只读波形观察；先看 TXC 与 TXCTL 活动，再视仪器通道数决定是否同时采集四条 TXD。
4. 只有在 RGMII 输入波形正常后，才继续把物理边界向 RTL8211F MDI 侧推进。

本阶段没有执行任何 Panther 设备命令、loopback、PHY reset、接口重启或硬件探测。下一轮仍聚焦 TX，不转向 RX dropped。


## 22. 调整调查优先级：先软件回归，硬件审计最后（2026-11-18）

用户明确调整调查顺序：所有板级硬件审计（拆机、找测点、示波器观察 RGMII/MDI、检查电阻/走线）放到最后。理由是同一 Panther X2 硬件在 Linux 6.1.116 环境下 Ethernet 工作正常，说明现有板卡、GMAC、PHY 与连接链路至少存在一套可工作的软硬件组合；当前应优先查找升级至 Linux 6.12.81 后的软件路径回归，以及是否能通过软件配置/驱动调整恢复工作。

此证据显著降低“板级硬件本身不可用”的优先级，但逻辑上不能绝对排除 6.12 对时钟、pinmux、delayline、PHY 初始化时序等控制方式的变化，使原有硬件在新软件下失配。因此应区分：
- **板级硬件损坏/固有不兼容：** 低优先级，暂不拆机或测波形；
- **软件控制硬件的配置/时序回归：** 高优先级，属于软件审计主线；
- **真正的物理波形/走线/器件故障：** 仅在软件对照与可逆软件验证无法解释时再查。

### 22.1 新调查顺序

1. **优先：6.1.116 与 6.12.81 软件路径对照。** 从实际运行版本、实际启动 DTB/U-Boot 传递环境出发，核对 GMAC probe、clock enable/parent/rate、GRF/pinctrl、RGMII delay、PHY reset/MDIO/phylink 初始化、MAC address 传递及 TX/DHCP 路径。已有证据不重复采集。
2. **其次：软件可调整的硬件控制项。** 只有找到明确版本差异和运行时证据后，才设计单变量、可回滚的软件验证；未获明确授权不修改系统。
3. **最后：板级硬件审计。** 仅当前两阶段不能解释故障时，再考虑板级照片/原理图、示波器/逻辑分析仪和 MDI 侧测量。

### 22.2 对原第 21 节的优先级修正

第 21 节的 RGMII TXC/TXD 测点与测量方法保留为未来备用资料，不再作为当前下一步，也不要求用户现在提供 PCB 近照或准备测量仪器。第 21.5 节行动顺序被本节的新顺序覆盖。

### 22.3 下一项具体工作

回到纯软件审计：以已确认的 6.1.116 正常环境和 6.12.81 异常环境为对照，先审计 Rockchip GMAC glue driver 在 probe/open/link-up 中对时钟、GRF、pinctrl、RGMII delay 与 PHY/phylink 的配置调用链；对照仓库已有运行时 DT、boot log、clk_summary、PHY 信息，列出确实发生变化且当前运行时证据尚未排除的项目。

不重复 TX descriptor/MTL/FIFO 已完成的比较；不转向 RX dropped；不做板级物理测量，不运行 phy_lb，不写寄存器，不重启接口。


## 23. Software-first audit: Rockchip GMAC glue / MAC identity differences (2026-11-18)

本轮按第 22 节新优先级，只比较 6.1.116 与 6.12.81 软件源码；没有设备操作、配置修改或板级测量。

### 23.1 RGMII delay 配置：Panther 当前参数下最终值等价

实际运行时 Panther DT 已核实：
- `phy-mode = "rgmii"`（不是 `rgmii-id`）；
- `tx_delay=0x30`、`rx_delay=0x10`；
- GMAC1 M0 pinctrl；
- GRF_MAC1_CON0/CON1 实测最终值 `0x00001030 / 0x00000013`。

6.1.116 的 `rk3568_set_to_rgmii()` 将 delay 值写入 CON0，再将 RGMII interface 与 TX/RX delay enable 写入 CON1。6.12.81 改为：
- 使用 `DELAY_VALUE(RK3568, tx_delay, rx_delay)` 写 CON0；
- 使用 `DELAY_ENABLE(RK3568, tx_delay, rx_delay)` 与 RGMII mode 写 CON1；
- 写入顺序变为 CON1 后 CON0。

6.12 新宏以 delay 是否 `>= 0` 决定 enable/disable；Panther 当前两个 delay 均为正值，因此两版最终 CON0/CON1 值一致。该差异不足以解释当前故障；写入顺序差异仅为初始化瞬态候选，暂不升级为根因。

### 23.2 GMAC clock enable 错误处理：存在真实回归候选，但当前运行时状态不支持直接归因

6.1.116：
- 使用 `clk_bulk_prepare_enable()` 启用核心 clocks；
- 检查返回值，失败则返回错误；
- 对 `clk_phy` 也检查返回值；
- 时钟选择后等待约 5 ms。

6.12.81：
- 分别调用多个 `clk_prepare_enable()`；
- 没有检查这些调用的返回值；
- `clk_phy` 也仅在非 ERR_PTR 时调用，未检查 enable 返回值；
- 新增 CSU clock control；
- 等待改为约 100–200 μs。

这属于明确的软件控制流程变化。它意味着某个 clock enable 失败时，6.12 可能仍将 `clk_enabled` 置 true 并继续 probe/powerup，而旧版会在失败时中止。**但** Panther 运行时 `clk_summary` 已确认 GMAC1 相关 clocks 为 125 MHz 且 enable，运行时 clock-names 也齐全；因此不能仅凭源码差异断言本次发生了 enable failure。仍需日志/启动时序证据。

### 23.3 新增 `rk_get_eth_addr()`：必须核实是否实际执行

6.12.81 的 `rk_gmac_probe()` 新增：
`plat_dat->get_eth_addr = rk_get_eth_addr`
6.1.116 没有该回调赋值。

6.12 stmmac core 的 `stmmac_check_ether_addr()` 只有在当前 netdev MAC 无效时，先尝试读取 MAC UMAC register；若仍无效，才调用平台 `get_eth_addr`。Rockchip 回调的逻辑：
1. 若传入地址有效，直接返回；
2. 否则调用 `rk_vendor_read(LAN_MAC_ID, ...)`；
3. Vendor read 失败或地址无效时，调用 `eth_random_addr()`；
4. 随后尝试 `rk_vendor_write(LAN_MAC_ID, ...)`。

`rk_vendor_read()` 的公共封装在没有 provider 注册时返回 `-1`。6.12 的 `flash_vendor_storage.c` 通过异步 init thread 完成 vendor storage 初始化及 `rk_vendor_register()`；若此路径确实是当前内核配置所用 provider，理论上存在 GMAC probe 先于 provider 注册完成的竞态窗口。**目前尚未确认 Panther 运行内核启用了该 provider、实际 provider 是哪一个，也没有证据证明竞态在本次启动发生。**

与实机线索的关系：
- eMMC Vendor Storage 已有审计确认包含 LAN_MAC（ID 3）条目及板载 GMAC 地址；
- 当前运行 eth0 曾显示 E6 前缀地址，板载记录为 86 前缀；
- 当前 U-Boot 读取 TF Vendor 数据而不是 eMMC Vendor 数据，是已确认事实；
- 不能据此直接断言 Linux 6.12 的 `rk_vendor_read()` 读的是 eMMC 或 TF，必须先确认 provider/底层读设备。
- MAC 地址不一致本身不能解释 hEX 看不到 DHCP Discover；有效的本地单播 MAC 仍应能发送广播 DHCP 帧。

**本项当前状态：** 源码路径已确认；回调是否执行、Vendor provider 类型及读取设备、是否生成随机地址，均待实机日志/配置证据。

### 23.4 其他已对照项

- 6.12 `rk_gmac_probe()` 还新增 `STMMAC_FLAG_SPH_DISABLE`、integrated PHY power callback、CSU 初始化和 loopback sysfs；Panther 使用外置 RTL8211F，integrated PHY callback 不应直接影响该 PHY。
- `rk_fix_speed()` 新增 mode 参数，但实际 speed clock 设置逻辑与 6.1 相同；Panther 已经协商到 1000Mbps Full Duplex，不能据此解释当前 Discover 丢失。
- 6.12 `stmmac_phy_setup()` 调整 phylink config / fwnode 选择并新增 `mac_requires_rxc`；当前 1Gbps Link Up 已证明 PHY/phylink 至少完成基本协商，尚无证据把这些差异与 TX 丢帧关联。

### 23.5 下一项最小只读验证

先只确认新回调是否执行，以及是否发生 Vendor read fallback。读取本次启动内核日志中是否存在：
- `rk_get_eth_addr: mac address`
- `rk_vendor_read eth mac address failed`
- `generate random eth mac address`
- `device MAC address`

该结果只用于关闭/确认 MAC identity 支线，不会改变 DHCP TX 主线边界。不要调用 vendor read/write 接口，不做任何 MAC 写入或配置修改。

**当前软件审计结论：** 已发现 clock enable 错误处理和 MAC address fallback 两个真实版本差异；尚未找到能直接解释 TX Discover 在本机 outgoing 之后消失的已证实根因。下一步先确认 MAC callback 是否执行，再继续审计尚未完成的 GMAC open/link-up/PHY path。硬件物理审计仍排最后。


## 24. Software-first audit: phylink link-up and netdev open sequence (2026-11-18)

本节是对第 23 节“继续审计 GMAC open/link-up/PHY path”的静态源码补充。仅读取并比较以下候选源码，不执行 Panther 设备命令，不重跑 loopback，不修改设备或系统：

- 6.1 候选：`unifreq/linux-6.1.y`，commit `5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.12 候选：`ophub/linux-6.12.y-rockchip`，commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 对照文件：`stmmac_main.c`、`stmmac_platform.c`、`dwmac-rk.c`

注意：这些是源码候选分支的对照；6.12.81 发布二进制与候选 commit 的精确构建映射仍未完成，不能将源码差异直接等同于实机已加载行为。

### 24.1 phylink link-up 到 Rockchip speed callback

两版的 `stmmac_phylink_mac_ops` 均将 `.mac_link_up` 绑定到 `stmmac_mac_link_up()`。对 Panther 的 RGMII/1000Mbps 路径，两版函数均按以下顺序执行：

1. 读取 MAC control；
2. 根据协商速率设置 MAC speed 字段；
3. 更新 `priv->speed`；
4. 调用平台 `fix_mac_speed`；
5. 更新 duplex 与 flow control；
6. 写回 MAC control（如有变化）；
7. 调用 `stmmac_mac_set(..., true)`。

6.12 在该函数前部新增了条件式 `serdes_powerup`（仅 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` 标志和回调均存在时执行），并在末尾增加 HWTSTAMP latency correction。6.12 的 `fix_mac_speed` 回调新增 `mode` 参数；Rockchip `rk_fix_speed()` 对 Panther RGMII 分支仍只调用 `set_rgmii_speed(bsp_priv, speed)`，没有使用新参数。6.1/6.12 的 RGMII speed 配置核心逻辑相同。

当前未发现上述 link-up 顺序差异能解释普通 RGMII TX 帧不出线。Panther 的 Rockchip glue 是否注册 SerDes powerup callback/相关 flag 尚未在本节逐一追完；但当前平台配置是外置 RTL8211F 的 RGMII，不应把新增的 XPCS/SerDes 分支当作已命中路径。

### 24.2 `phylink_node` → `port_node` 是同一设备树节点的表示迁移

6.1 的 `stmmac_probe_config_dt()` 将 `plat->phylink_node = np`；6.12 改为 `plat->port_node = of_fwnode_handle(np)`。6.1 的 `stmmac_init_phy()` 通过 `of_fwnode_handle(plat->phylink_node)` 取得 fwnode；6.12 直接使用 `plat->port_node`。两版最终均以 GMAC 节点作为 phylink/fwnode 起点，再由 `phy-handle` 解析 PHY 节点。

因此这不是把 PHY 从一个节点改接到另一个节点的证据。现有运行时 DT 已确认 GMAC 节点的 PHY child 为 MDIO address 0；当前没有证据显示此迁移造成错误 PHY attach。

### 24.3 `__stmmac_open()` 的关键顺序对照

两版均在 netdev open 时先恢复 runtime PM，再执行 PHY attach/init，随后配置 DMA queue 参数、执行硬件初始化、启动 phylink、申请 IRQ、启用队列并启动 TX queue。

可见差异：
- 6.1 对 TBI/RTBI PCS 有额外的 PHY init 跳过条件；6.12 改为按 XPCS C73 模式判断。Panther 当前为 RGMII 外置 PHY，不属于 TBI/RTBI，也没有证据表明使用 XPCS C73，因此两版都会进入 `stmmac_init_phy()`。
- 6.1 若平台提供 `serdes_powerup`，在硬件初始化前调用；6.12 仅在未设置 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` 时提前调用，否则延迟到 link-up。该分支是否注册对 Panther 生效的 callback 尚未确认；当前 RGMII 外置 PHY 配置没有命中证据。
- 6.12 在复制 DMA config 前增加对 TBS 状态的保留处理；未发现这改变普通 AF_PACKET 小帧的队列选择或 TX descriptor 路径。
- 6.12 移除了旧版 open 阶段对整个 `xstats` 的 memset；这是统计生命周期差异，不是硬件 TX 启动差异。

目前未发现 `__stmmac_open()` 的通用顺序变化可以解释 Panther 的普通 queue 0 TX 故障。

### 24.4 `stmmac_hw_setup()` 的初始化顺序

两版共有的核心顺序为：

1. `stmmac_init_dma_engine()`（含 DMA 初始化/SW reset）；
2. 写入 MAC address；
3. `stmmac_core_init()`；
4. MTL 配置与 RX checksum 配置；
5. 使能 MAC RX/TX；
6. 设置 DMA operation mode；
7. MMC/PTP 等初始化；
8. 配置 ring length、TSO/SPH/VLAN/TBS；
9. `stmmac_start_all_dma()` 启动 RX/TX DMA channel。

6.12 在 DMA 初始化之前增加：
`if (priv->hw->phylink_pcs) phylink_pcs_pre_init(...)`
注释说明用于确保 RX clock 已启用。此分支只有在运行时确实存在 `hw->phylink_pcs` 时才执行。Panther 当前是 RK3566 + RGMII + 外置 RTL8211F；现有资料没有显示其使用 XPCS/外部 phylink PCS，因此该新增分支目前不应被认定为 Panther 已命中。具体运行时指针值未直接读取，标为未验证。

6.1 在 `stmmac_start_all_dma()` 后还有 FPE workqueue/handshake 初始化；6.12 将相关 FPE 状态管理改为新机制。这与当前普通 RGMII TX 路径没有直接关联证据。

### 24.5 phylink 配置变化及其边界

6.12 的 `stmmac_phy_setup()` 新增 `phylink_config.mac_requires_rxc = true`，并调整 MAC capabilities 获取方式；6.1 使用静态 `mac_capabilities` 字段。该配置可能影响 phylink 等待 RX clock 的链路状态处理，但 Panther 在 6.12 已报告 1Gbps Full Link Up，说明链路协商路径至少达到 link-up。当前没有证据表明此属性会阻止 TX descriptor 提交或造成已 link-up 后的普通帧不出线。

### 24.6 本轮结论

- **已确认：** phylink link-up 的主要 MAC 配置顺序在两个候选版本中一致；Rockchip RGMII speed callback 的实质行为一致。
- **已确认：** `phylink_node` → `port_node` 是节点表示方式迁移，最终解析起点仍是同一个 GMAC DT 节点。
- **已确认：** `__stmmac_open()` 和 `stmmac_hw_setup()` 的普通 RGMII 核心启动顺序没有发现能直接解释 TX 故障的差异。
- **新增但尚未证明命中 Panther：** 6.12 的 `mac_requires_rxc` 与 `phylink_pcs_pre_init()`；后者取决于 `hw->phylink_pcs` 是否非空。
- **尚未完成：** Panther 实际 6.12.81 构建的源码/patch/config 精确映射；Rockchip glue 的 SerDes callback/flag 是否在 Panther 实际初始化时注册；`hw->phylink_pcs` 的实机指针/路径。
- **根因状态：** 本节未定位根因。现有证据仍只把故障边界限定在本机 outgoing 软件抓包之后、外部接收端观察之前；不能据此把故障精确归因于 MAC、RGMII 或 PHY。

### 24.7 下一步

继续静态核对 Rockchip glue 对 `serdes_powerup`、`integrated_phy_power`、`fix_mac_speed` 的 callback 注册条件，以及 6.12.81 实际构建补丁/配置映射。若这些分支均未命中，再集中审计 6.12 新增/改写的 RX-clock/phylink PCS 逻辑是否影响 Panther RGMII 初始化。不得重跑 `mac_lb`、`phy_lb`、`phy_lb_scan`，不得重复 TX descriptor/MTL 审计，不进行设备侧改动。


## 25. Software-first audit: Rockchip glue callback registration and applicability (2026-11-18)

本轮继续第 24.7 节的静态源码审计，只核对 Rockchip dwmac-rk.c 对平台回调的注册、RK3568 ops 内容及其是否适用于 Panther X2 的 RK3566 + 外置 RTL8211F RGMII 组合。没有执行设备命令、环回测试、配置修改或硬件操作。

源码候选：
- 6.1：unifreq/linux-6.1.y，commit 5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12：ophub/linux-6.12.y-rockchip，commit 661b2d8bf1284556f8876d5ed5fb80c64b22f94c

### 25.1 RK3566 实际匹配的 Rockchip ops

两版 dwmac-rk.c 均将 rockchip,rk3568-gmac 映射到 rk3568_ops。RK3566 设备树使用该 compatible，因此这部分是 Panther 应走的 Rockchip glue 实现，而不是其他 SoC 的 ops。

两版 rk3568_ops 的关键回调一致：set_to_rgmii = rk3568_set_to_rgmii、set_rgmii_speed = rk3568_set_gmac_speed；set_to_rmii / set_to_sgmii / set_to_qsgmii 也均对应 RK3568 实现；GMAC1 resource 地址仍为 0xfe010000。因此，RK3568 ops 表本身没有发现与本次 TX 故障直接相关的回调替换。

### 25.2 6.12 的 SerDes 延迟上电路径没有被 Rockchip glue 注册

6.12 通用 stmmac 使用 plat->serdes_powerup 与 STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP。但在本次对照的 Rockchip dwmac-rk.c 中，rk_gmac_probe() 没有给 plat_dat->serdes_powerup 赋值，没有设置 STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP，RK3568 ops 也没有 SerDes powerup 回调成员。

故 Panther 使用此 Rockchip glue 时，通用 stmmac 中新增的“PHY link-up 后才执行 SerDes powerup”条件分支没有已知回调可调用。6.1 在 open 阶段无条件检查 serdes_powerup 与 6.12 的条件式处理，对 Panther 都是空操作。本分支可从当前优先嫌疑中排除。

### 25.3 6.12 新增 integrated PHY power callback 对 Panther 外置 PHY 不适用

6.12 的 rk_gmac_probe() 新增 plat_dat->integrated_phy_power = rk_integrated_phy_power。stmmac_init_phy() 在 attach PHY 前调用该回调；关闭接口、suspend/resume 等路径也会调用它。Rockchip 回调首先检查 bsp_priv->integrated_phy、ops 与 ops->integrated_phy_power，条件不满足就直接返回 0，不执行 PHY 电源操作。

RK3568 ops 未提供 integrated PHY power 实现；Panther 使用外置 RTL8211F，而不是 RK3568 SoC 内置 PHY。因此该新增回调在 Panther 上应为 no-op，不会改变外置 RTL8211F 的电源/复位时序。

6.1 则在 Rockchip glue 的 rk_gmac_powerup()/powerdown() 中直接处理 integrated PHY。该差异只对 phy-is-integrated 的平台配置有意义，不适用于当前外置 RTL8211F 组合。

### 25.4 6.12 新增 SPH_DISABLE 标志

6.12 的 rk_gmac_probe() 新增 plat_dat->flags |= STMMAC_FLAG_SPH_DISABLE。这是针对 Split Header 模式的配置，不等于关闭普通 TX，也不改变 RGMII speed callback。现有 TX descriptor 审计及运行时普通 AF_PACKET 小帧路径没有证据表明 Panther 使用 SPH。该标志暂不构成普通 DHCP Discover 无法到达外部接收端的解释。

### 25.5 本轮结论

- 已确认：RK3566 使用 rk3568_ops；两版 RK3568 RGMII 设置和速率回调相同。
- 已确认：Rockchip glue 没有注册 serdes_powerup，也没有设置 SerDes link-up 延迟标志；通用 stmmac SerDes 延迟路径不适用于 Panther 当前驱动组合。
- 已确认：新增 integrated_phy_power 在外置 RTL8211F 配置下为 no-op，不会控制该外置 PHY。
- 已确认：SPH_DISABLE 是 Split Header 相关标志，当前没有证据将它与普通小帧 TX 故障关联。
- 根因状态：本轮排除了几个容易误判的新增回调分支，仍未发现直接根因。

### 25.6 下一步

继续追踪 6.12 stmmac_hw_setup() 中新增的 hw->phylink_pcs / phylink_pcs_pre_init() 路径：先静态确定 RK3568 + RGMII + 外置 RTL8211F 是否可能建立该 PCS 指针，以及它是否会改变 GMAC RX clock / DMA 初始化时序。若该指针在此组合中必为空，则可直接排除此支线，不需要 Panther 实机重复采集。随后再审计 6.12 新增的 MAC capability / mac_requires_rxc 逻辑。


## 26. Software-first audit: PCS selection, pre-init and mac_requires_rxc (2026-11-18)

本轮继续第 25.6 节，只做源码静态追踪，不执行 Panther 设备命令、不重跑测试、不修改设备。

源码候选：
- 6.1：unifreq/linux-6.1.y，commit 5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12：ophub/linux-6.12.y-rockchip，commit 661b2d8bf1284556f8876d5ed5fb80c64b22f94c

### 26.1 RK3568 glue 不提供 select_pcs

在 6.12 Rockchip dwmac-rk.c 中，rk_gmac_probe() 设置 fix_mac_speed、integrated_phy_power 等平台回调，但没有设置 plat_dat->select_pcs；rk3568_ops 也没有 PCS 选择回调。6.1 对照版本同样没有该回调。

6.12 stmmac_main.c 的 stmmac_mac_select_pcs() 逻辑为：只有 priv->plat->select_pcs 非空时才调用平台选择；否则返回 NULL。phylink 的 mac_select_pcs API 文档明确规定 NULL 表示该接口不需要 PCS。因此，对 Panther 当前 RK3566 compatible rockchip,rk3568-gmac + phy-mode=rgmii + 外置 RTL8211F 组合，phylink 不会选中 XPCS/PCS。

### 26.2 phylink_pcs_pre_init() 分支的适用性

6.12 stmmac_hw_setup() 新增：只有 priv->hw->phylink_pcs 非空时才调用 phylink_pcs_pre_init()。该调用不是所有 RGMII 设备都会执行的无条件步骤，而是针对有 PCS 实例的路径。

在本次检查的 stmmac_main.c、stmmac_platform.c 和 Rockchip dwmac-rk.c 中，没有发现 Panther 平台为 hw->phylink_pcs 提供赋值/选择的路径；Rockchip glue 也没有 select_pcs。故现有静态证据强烈支持 Panther 的该指针为空，新增 PCS pre-init 对当前 RGMII 外置 PHY 路径不生效。严格说明：本轮没有逐一审计整个内核树所有可能写入 mac_device_info.phylink_pcs 的第三方平台文件，也没有读取实机指针值；因此把“本平台路径未提供 PCS”列为已确认，把“运行时指针绝对为 NULL”列为源码推断而非实机验证。

### 26.3 mac_requires_rxc 的真实作用

6.12 stmmac_phy_setup() 设置 phylink_config.mac_requires_rxc = true。phylink 在连接 PHY 时将 PHY_F_RXC_ALWAYS_ON 作为 attach flags 传入 phy_attach_direct()，phy_attach_direct() 将 flags 合并到 phydev->dev_flags。

这项变化与 PCS pre-init 是两条不同路径：即使没有 PCS，mac_requires_rxc 仍会在 PHY attach 时设置该 PHY 标志。但标志是否影响具体 PHY，取决于 PHY 驱动是否读取它。

### 26.4 RTL8211F 驱动是否消费该标志

在 6.12 drivers/net/phy/realtek.c 中，RTL8211F config_init、suspend/resume 及驱动定义没有读取 dev_flags 或 PHY_F_RXC_ALWAYS_ON 的代码；对该文件检索 dev_flags 与 PHY_F_RXC_ALWAYS_ON 均为 0 处命中。因此在当前使用的上游 Realtek RTL8211F 驱动实现中，phylink 设置该标志不会改变 RTL8211F 的配置、电源管理或时钟行为。

注意：这只证明当前候选 realtek.c 中没有消费该标志；6.12.81 实际构建是否对 Realtek 驱动打过额外补丁仍受构建映射未完成这一限制。

### 26.5 本轮结论

- **已确认：** RK3568 Rockchip glue 未设置 plat_dat->select_pcs；stmmac_mac_select_pcs() 在该配置下返回 NULL；phylink 的 NULL 语义为不需要 PCS。
- **源码推断：** Panther 当前 RGMII 外置 RTL8211F 路径不会选择 PCS，因而 6.12 stmmac_hw_setup() 新增的 phylink_pcs_pre_init() 分支应被跳过。尚未以实机指针值直接验证。
- **已确认（候选源码）：** mac_requires_rxc 设置 PHY_F_RXC_ALWAYS_ON attach flag；候选 RTL8211F 驱动不读取该标志，因此没有发现它改变 RTL8211F 行为的路径。
- **结论：** 6.12 新增 PCS pre-init 与 mac_requires_rxc 目前均不构成解释 Panther 普通 TX 失败的有效嫌疑。RX clock / PCS 这条支线可以从当前优先级中关闭，但保留实际 6.12.81 构建补丁映射未完成的限制。
- **根因状态：** 仍未定位 TX 故障根因。

### 26.6 下一步

继续检查 6.12.81 实际构建与候选源码的映射，以及 6.1→6.12 中与 RTL8211F 外置 PHY 配置相关的真实驱动差异，尤其 PHY 初始化时序、ALDPS/EEE 配置及 RGMII interface handling。此前已经完成的 PHY ID、PHY reset、EEE 运行时状态、RGMII delay 和 GMAC 时钟实机检查不得重复；本阶段只做源码差异审计，先确定存在有意义的差异再决定是否需要新的验证。


## 27. RTL8211F PHY driver 6.1.116 vs 6.12.81 comparison (2026-11-18)

本轮按第 19 节已锁定的真实工作基线比较，而非比较两个 RK35xx 专用分支：
- 正常 6.1.116：unifreq/linux-6.1.y @ 5eb841b59d6ead6e264163785a634e78f0253c8e；realtek.c blob `3d29f78108e746b7a2f99772dabb8374fd78f278`。
- 故障 6.12.81：ophub/linux-6.12.y-rockchip @ 661b2d8bf1284556f8876d5ed5fb80c64b22f94c；realtek.c blob `ff15239ee63d137be5b4c9ba8538c3b02e414aa5`。

6.12.81 source commit 与构建任务的对应关系已在第 16 节锁定；6.1.116 source commit 是基于 2024-11-10 workflow 时间戳和版本元数据重建的高置信度基线，尚缺原始 Actions run / 安装包 SHA256，故仍非二进制级确认。

### 27.1 RGMII 内部 TX/RX delay 设置没有版本回归

两版 `rtl8211f_config_init()` 对 `phydev->interface == PHY_INTERFACE_MODE_RGMII` 均设置：
- `val_txdly = 0`
- `val_rxdly = 0`

随后均通过 page `0xd08` 的寄存器 `0x11` / `0x15` 对应位清除 PHY 内部 TX/RX delay。对于 Panther 运行时 DT 的 `phy-mode = "rgmii"`，两版都要求 PHY 侧不插入内部 RGMII delay；TX/RX delay 由 RK3566 GMAC 侧配置（当前运行时 DT 缓存值 0x30/0x10）。

两版都使用 `phy_modify_paged_changed()` 修改相同 page/register/mask，并对错误返回进行检查。未发现 6.12 改变 RGMII mode 分支、delay 位选择或写入目标。

### 27.2 ALDPS 配置逻辑保持一致

两版 `rtl821x_probe()` 都读取 page `0xa43` 的 `RTL8211F_PHYCR1`，缓存现有 `ALDPS_PLL_OFF | ALDPS_ENABLE | ALDPS_XTAL_OFF` 位；只有设备树存在 `realtek,aldps-enable` 时才强制置位。两版 `rtl8211f_config_init()` 都将缓存值写回相同寄存器位。

仓库保存的 Panther 运行时 PHY 节点 `/ethernet@fe010000/mdio/ethernet-phy@0` 只有 `compatible`、`status`、`reg`，没有 `realtek,aldps-enable`。因此当前 DT 没有要求驱动强制开启 ALDPS；两版均保留 PHY 原有 ALDPS 位状态。未发现 ALDPS 配置策略的 6.1→6.12 变化。

### 27.3 PHYCR2 / CLKOUT 配置与 soft reset 的核心行为一致

两版均在 `rtl821x_probe()` 中读取 PHYCR2 的 `RTL8211F_CLKOUT_EN` 位，并缓存其原状态；只有存在 `realtek,clkout-disable` 属性时才清除该位。两版 `rtl8211f_config_init()` 在 `has_phycr2` 条件下都修改相同 PHYCR2 位并执行 `genphy_soft_reset()`。

6.12 将 LED restore 放到 soft reset 之后；6.1 的 `realtek,led-data` 写入则发生在 PHYCR2 soft reset 之前。这个顺序差异影响 LED 配置在复位后的恢复，不改变 PHYCR2 CLKOUT 位的目标值，也没有证据表明它改变 RGMII TX/RX 数据通道。

Panther 运行时 PHY 节点没有 `realtek,clkout-disable` 属性，两版都保留 probe 时读取到的 CLKOUT_EN 状态。

### 27.4 6.12 新增可选 PHY clock 管理，但 Panther DT 未提供 PHY clock

6.12 的 `rtl821x_probe()` 新增 `devm_clk_get_optional_enabled(dev, NULL)`；6.12 的 `rtl821x_suspend()` 在 PHY suspend 后关闭该可选 clock，`rtl821x_resume()` 在恢复前重新开启。6.1 的 suspend callback 直接使用 `genphy_suspend()`，resume callback 执行 `genphy_resume()` 后等待 20 ms。

对照仓库中保存的 Panther 运行时 PHY 节点：
- 节点为 `/ethernet@fe010000/mdio/ethernet-phy@0`；
- 节点属性仅记录 `compatible = ethernet-phy-ieee802.3-c22`、`status = okay`、`reg = 0`；
- 没有 `clocks` 或 `clock-names` 属性。

因此 `devm_clk_get_optional_enabled()` 在 Panther 当前 PHY 节点下应得到 NULL，不会管理额外 PHY clock；`clk_disable_unprepare(NULL)` / `clk_prepare_enable(NULL)` 对该 optional clock 不形成实际时钟切换。两版在普通 PHY suspend/resume 的核心动作仍是 BMCR power-down / clear power-down，并保留约 20 ms resume 等待。该新增 clock 管理对当前 Panther 组合不构成可见的活动路径。

### 27.5 PHY_ALWAYS_CALL_SUSPEND 是条件式 suspend/WOL 变化，不是在线 TX 路径变化

6.12 的 RTL8211F driver table 将 `.suspend` 从 `genphy_suspend` 改为 `rtl821x_suspend`，并新增 `PHY_ALWAYS_CALL_SUSPEND`；6.1 没有该 flag。

6.12 PHY core 的 `phy_suspend()` 逻辑显示，该 flag 主要改变 WOL 已启用时是否允许继续调用 PHY suspend callback。普通无 WOL 情况下，两版都会执行 PHY suspend；有 WOL 时，6.12 允许执行 suspend，而 6.1 返回 `-EBUSY`。这是设备关闭/电源管理语义，不是网卡处于 UP、PHY link-up 时的普通 TX descriptor/发送路径。

当前资料没有证明 Panther 在故障测试时启用了 WOL。即使启用，该差异也只会在 PHY suspend 生命周期发生时相关；不能据此解释接口正常 UP 且 link-up 后普通 DHCP/raw frame 不到达外部接收端。

### 27.6 RTL8211F LED 配置是主要剩余代码差异

6.1 的 `rtl8211f_config_init()` 在检测到 `realtek,led-data` 时，直接写 page `0xd04` 的 LED control register 和 EEE LED control register；之后恢复 page 0。6.12 改用 LED framework：probe 时解析 LED 子节点，config_init 时调用 `rtl8211f_restore_leds()`，并在部分 early-return / PHYCR2 soft-reset 路径后恢复 LED 配置。

这是 LED 指示配置/复位后恢复机制的变化。没有证据显示它修改 GMAC、RGMII TXC/TXD、PHY TX analog 或普通帧发送控制寄存器。它目前不构成有力的 TX 故障解释。

### 27.7 本轮结论

- **已确认（候选源码）：** 两版 RTL8211F 对 RGMII mode 的内部 TX/RX delay 都设置为 0；ALDPS 和 PHYCR2 CLKOUT 位的读取、缓存及回写策略一致。
- **已确认（运行时 DT 记录）：** Panther PHY 节点没有 `realtek,aldps-enable`、`realtek,clkout-disable`、`clocks` 或 `clock-names` 属性；6.12 的可选 PHY clock 管理在当前 DT 下应为空操作。
- **已确认（源码）：** 6.12 新增的 `PHY_ALWAYS_CALL_SUSPEND` 影响 WOL 与 suspend 行为，不在普通 UP/link-up TX 数据路径中。
- **已确认（源码）：** 6.1→6.12 的 RTL8211F 主要差异集中在 LED 配置恢复和可选 clock / suspend 管理；未发现可解释当前普通 TX 故障的 RGMII 数据通道改动。
- **根因状态：** 本轮未定位根因；RTL8211F driver 这条支线的优先级可降低。

### 27.8 下一步

不再泛查 Realtek PHY 的 LED/电源管理代码。转向审计 6.1.116 generic 与 6.12.81 RK35xx 的 PHY attach / phylink connection 和 EEE capability 初始化差异，但先判断 Panther 的 `phy-handle` 实际连接分支是否经过相关代码。重点关注 6.12 `stmmac_init_phy()` 新增 `phy_support_eee()` 的调用条件、phylink attach flags、PHY `config_init` 的触发时机及 soft reset 前后次序。已完成的 PHY ID、reset GPIO、EEE 运行时状态、RGMII delay 实机检查不再重复；只做源码与已归档日志分析。


## 28. PHY attach, EEE initialization and phylink link-up comparison (2026-11-18)

本轮按第 27.8 节继续源码审计。没有执行 Panther 实机测试、没有更改设备配置，也没有重复旧的 PHY/EEE 运行时检查。

### 28.1 Panther 使用 firmware phy-handle 路径，不会命中 6.12 新增的 phy_support_eee() fallback

6.12 `stmmac_init_phy()` 的连接流程：
- 从 `priv->plat->port_node`（不存在时回退 `dev_fwnode()`）取得 MAC port firmware node；
- `fwnode_get_phy_node()` 查找关联 PHY；
- 若找不到 PHY node，才使用 `priv->plat->phy_addr` 手工从 MDIO bus 取 PHY；
- 只有这个手工 fallback 分支且 `priv->dma_cap.eee` 为真时，才调用 `phy_support_eee(phydev)`；
- 若找到 PHY node，则调用 `phylink_fwnode_phy_connect()`，不调用 `phy_support_eee()`。

6.1 `stmmac_init_phy()` 也有相同的 firmware PHY node / 手工 fallback 两条连接路径，但没有 `phy_support_eee()` 调用。

仓库保存的 Panther 运行时设备树记录明确包含 `/ethernet@fe010000/mdio/ethernet-phy@0`，`reg = 0`，MAC 的 PHY 连接通过 firmware `phy-handle` 指向该节点。因此 Panther 应走 `phylink_fwnode_phy_connect()` 分支，而不是 6.12 新增 `phy_support_eee()` 的手工地址 fallback。

**结论：** 6.12 新增的 `phy_support_eee()` 对 Panther 当前设备树连接路径不执行，不能解释当前 TX 故障。该结论以归档运行时 DT 的 phy-handle 关系为依据；不是仅凭 PHY 节点存在就推断。

### 28.2 PHY attach 的其他差异

6.12 在 `stmmac_init_phy()` 中加入 `integrated_phy_power(true)`，但第 25.3 节已确认 RK3568 ops 对外置 RTL8211F 返回 no-op。PHY node 查找从旧版 `plat->phylink_node` 转为新版 `plat->port_node`，最终仍通过 firmware node 连接同一个外置 PHY。

6.12 的 `stmmac_phy_setup()` 新增 `mac_requires_rxc = true`，其 attach flag 影响已在第 26 节分析；候选 RTL8211F 驱动不消费 `PHY_F_RXC_ALWAYS_ON`。

### 28.3 phylink MAC capability 初始化确有架构变化，但不符合当前故障表象

6.1 `stmmac_phy_setup()` 在创建 phylink 前，按 `max_speed`、GMAC/XGMAC 类型和 TX queue 数量直接构造 `phylink_config.mac_capabilities`，包括 10/100/1000 及 pause/duplex 能力。

6.12 改为 `mac_get_caps()`：调用 MAC core 的 `update_caps` 回调刷新 `priv->hw->link.caps`，再把它作为 phylink MAC capabilities，并按 `plat->max_speed` 限速。DWMAC4 的 `dwmac4_update_caps()` 主要按 TX queue 数量调整 half-duplex capability 位。

这是 phylink capability 的初始化架构变化，但不是 TX descriptor 或 MAC TX enable 路径。现有故障系统有 1000Mbps Full link-up 的运行记录，说明至少千兆全双工能力协商成功；因此它不能解释“PHY link 已建立但普通 TX 帧无法到达外部”的现象。保留一点：尚未对 6.12.81 构建实际 MAC capability 位做二进制级核实，但当前不值得安排实机重复采集。

### 28.4 mac_link_up / EEE 初始化路径对照

两版 `stmmac_mac_link_up()` 在普通 RGMII speed selection、MAC speed/duplex 位更新、flow-control 设置、`stmmac_mac_set(..., true)` 及 EEE 初始化主流程上相同。

6.12 增加的 SerDes 延迟 powerup 条件已在第 25.2 节证明 Panther Rockchip glue 未注册该回调，因此是空操作。

6.1 调用 `fix_mac_speed(bsp_priv, speed)`；6.12 新接口调用 `fix_mac_speed(bsp_priv, speed, mode)`。Rockchip `rk_fix_speed()` 在 6.12 增加 `mode` 形参，但函数体仍按 `bsp_priv->phy_iface` 分支，并未读取新增 `mode` 参数；RGMII 分支仍调用相同 `set_rgmii_speed(bsp_priv, speed)`。故接口签名变化对 Panther RGMII 的实际速率回调没有改变。

两版 EEE link-up 主流程均在 `phy && priv->dma_cap.eee` 条件下调用 `phy_init_eee()`，然后执行 `stmmac_eee_init()`、设置 TX LPI enable 并调用 `stmmac_set_eee_pls()`。参数字段从旧版 `plat->rx_clk_runs_in_lpi` 转为新版 `STMMAC_FLAG_RX_CLK_RUNS_IN_LPI`，需要确认 Panther 的 platform flag 映射，但此前运行时 EEE 状态已检查，不重复设备测试。该参数影响 `phy_init_eee()` 对 RX clock in LPI 的要求，不改变普通帧 TX 的 DMA 描述符提交逻辑；当前没有证据显示它造成持续普通帧发送失败。

### 28.5 本轮结论

- **已确认：** Panther 有有效 firmware PHY node / phy-handle，6.12 新增 `phy_support_eee()` 只在没有 PHY node 的手工 MDIO fallback 分支执行，因此 Panther 不会命中。
- **已确认：** 两版 `stmmac_mac_link_up()` 的普通 RGMII speed/duplex/MAC enable/EEE 主流程相同；6.12 新增 `mode` 形参在 Rockchip `rk_fix_speed()` 中未被读取。
- **已确认：** 6.1 的静态 phylink capabilities 改为 6.12 MAC core 动态 capabilities，但已有 1000Mbps Full link-up 事实不支持把它作为当前 TX 故障解释。
- **未关闭但低优先级：** `rx_clk_runs_in_lpi` 到 `STMMAC_FLAG_RX_CLK_RUNS_IN_LPI` 的平台标志映射，及 6.12.81 构建中的实际 EEE flag 值；不安排重复 EEE 实机测试，只有源码映射发现不同才继续。
- **根因状态：** PHY attach / EEE / phylink link-up 这一组新增逻辑目前没有发现能解释 Panther 普通 TX 失败的活动差异。

### 28.6 下一步

回到更接近故障边界的 MAC 初始化和 TX/RX DMA bring-up：审计 6.1.116 与 6.12.81 在 `stmmac_hw_setup()` 中 MAC reset、DMA reset、DMA channel init、RX ring refill/start 与 MAC RX/TX enable 的严格调用顺序和失败返回处理。优先静态比较函数调用图与 RK3568 实际 ops；已有 TX descriptor、DMA channel state、ST/Tail pointer、IRQ/NAPI、TX cleanup 及统计核对不重跑。若找到实际顺序差异，再决定是否需要一项新的、能区分 RX/TX 边界的定向验证。


## 29. Newly found 6.1.116-only stmmac vendor patch: 1.5 s delay + unconditional MDIO writes (2026-11-18)

本轮在审计 `stmmac_init_dma_engine()` 时，沿 Git 历史追查到一个此前未识别的关键版本差异。没有执行 Panther 实机命令或修改设备。

### 29.1 差异来源已追到具体历史提交

6.1.116 对照源码 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` 包含提交：
- commit `49b5f340f346cc9a5b777499fce46150b691b70e`
- message：`drv: net: ethernet: stmmac fix for jl2xx1 phy`

该提交同时向两个函数加入代码：
1. `stmmac_init_dma_engine()` 在 DMA SW reset 前新增 `msleep(1500)`；
2. `stmmac_mdio_register()` 在 MDIO bus 注册后新增四条写操作：
   - `stmmac_mdio_write(new_bus, 0, 31, 2627)`（page select = 0x0a43）
   - `stmmac_mdio_write(new_bus, 0, 25, 0x1801)`
   - `stmmac_mdio_write(new_bus, 0, 31, 0)`
   - `stmmac_mdio_write(new_bus, 0, 0, 0x8000)`（BMCR software reset）

这不是 6.1 主线 stmmac 通用初始化行为，而是一个提交标题明确指向 JL2xx1 PHY 的厂商/平台补丁。该提交没有按 PHY compatible/PHY ID 做条件判断。

### 29.2 对 Panther 当前配置，这四条写操作会命中地址 0 的 RTL8211F

已归档 Panther 运行时信息：PHY 地址 0、型号 RTL8211F、PHY ID `0x001cc916`，不是 fixed-link。6.1 `stmmac_mdio_register()` 的代码顺序是：
- `of_mdiobus_register()` 成功后；
- fixed-link 检查通过（Panther 没有 fixed-link）；
- 执行上述四条写操作；
- 之后才检查 `priv->plat->phy_node || mdio_node` 并跳过自动 PHY 扫描。

因此，只要 Panther 使用该 6.1.116 源码路径且 `mdio_bus_data` 非空（已有 `stmmac-0:00` PHY 注册记录支持 MDIO bus 存在），这组硬编码 MDIO 写就会在 PHY address 0 执行。它不是只对没有 DT phy-handle 的自动扫描路径执行。

6.12.81 候选源码 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 `stmmac_mdio_register()` 不含这四条写操作；`stmmac_init_dma_engine()` 也没有 1.5 s 延时。

### 29.3 写入目标确实是 RTL8211F PHYCR2，但存在必须解释的矛盾

RTL8211F datasheet 将 page `0x0a43`、register `0x19`（十进制 25）定义为 PHYCR2。Rev 1.7 描述其中：
- bit 0：CLKOUT enable；
- bit 1：RXC clock output enable；
- bit 5：PHY-mode EEE enable；
- bit 11：CLKOUT 25/125 MHz 频率选择；
- bit 13:12：CLKOUT SSC capability select。

整字写入 `0x1801` 会设置 bit 12、bit 11、bit 0，同时把 bit 1、bit 5 等未置位位清零。之后执行 BMCR software reset。

6.1 候选 Realtek 驱动的 `rtl821x_probe()` 会读取并缓存 PHYCR2 的 CLKOUT bit 0；随后 attach 时 `rtl8211f_config_init()` 只用 `phy_modify_paged(..., RTL8211F_CLKOUT_EN, priv->phycr2)` 恢复 bit 0，并不会恢复 bit 1 或 bit 5。因此，如果该序列确实在 RTL8211F 上成功执行，按源码字面推导，RXC enable / PHY-mode EEE enable 可能被清除。

**但这与已验证的 6.1.116 正常双向网络通信事实形成矛盾。** 不能忽略这个反证，也不能直接宣称此序列导致 6.12 TX 故障。尚待查明的可能性包括：实际 6.1.116 二进制未包含该提交/该函数路径、MDIO 写操作未成功作用于该 PHY、具体芯片/寄存器语义与候选 datasheet 修订不一致，或 PHY 驱动/后续流程还有其他恢复机制。当前尚无运行时 MDIO trace 或 PHYCR2 前后值可确认写入结果。

### 29.4 1.5 s delay 与四条 MDIO 写必须视为同一历史补丁组合，但分开评估

`msleep(1500)` 与上述 MDIO 写在同一个 `49b5f340` 历史提交中加入。该等待发生在 `__stmmac_open()` 已完成 `pm_runtime_resume_and_get()`、`stmmac_init_phy()` / PHY attach 与 `phy_init_hw()` 后，随后才进入 DMA SW reset、DMA channel 初始化。phylink_start 则在 `stmmac_hw_setup()` 完成之后执行。

因此它不是系统启动时的通用 1.5 秒等待，而是每次网卡 open/reopen 时，在 PHY 初始化后、DMA reset 前增加 1.5 秒等待。它可能是该旧平台补丁针对 PHY/时钟稳定性所需的时序 workaround，但 commit message 指向 JL2xx1，不能未经验证外推到 RTL8211F。

### 29.5 本轮结论与证据等级

- **已确认（源码）：** 6.1.116 候选源码含 `49b5f340` 补丁；6.12.81 候选源码没有 1.5 s delay 和四条硬编码 MDIO 写。
- **已确认（代码路径）：** Panther 的地址 0、非 fixed-link MDIO 配置满足该 6.1 代码块的执行条件；该块位于 `phy_node/mdio_node` early-exit 判断之前。
- **已确认（datasheet）：** 地址 0、page 0x0a43、reg 0x19 对 RTL8211F 是 PHYCR2；0x1801 整字写会清除 bit1 与 bit5。
- **源码推断：** 后续 Realtek config_init 只恢复 CLKOUT bit0，不恢复 RXC/EEE bit，因此若写成功，寄存器位状态可能改变。
- **未验证且存在反证：** 这组写操作是否真的作用于当前 PHY，以及 6.1.116 的实际二进制是否包含该补丁。正常双向网络结果不支持简单地认定 RXC 被禁用。
- **根因状态：** 这是目前发现的最具体、最接近 PHY/RGMII 时钟边界的 6.1→6.12 代码差异之一，但尚不能定为根因。

### 29.6 下一步（仍先静态查证，不要求用户重复实机测试）

1. 继续查 `49b5f340` 补丁的来源/目标平台，确认 JL2xx1 PHY 的准确型号及寄存器意义，判断为什么补丁被无条件放入通用 stmmac 路径。
2. 核对 6.1.116 的实际构建产物/构建工作流能否证明该补丁确实进入运行内核；若无法证明，降低该分支的权重。
3. 对照 Panther 的 GMAC `clock_in_out = "input"`、pinctrl `clkinout` 和时钟树记录，判断 PHY CLKOUT 是否连接到 RK3566 的 GMAC clock input。不得重复读取已完成的 clock_summary / GRF / pinctrl 实机项目；使用已归档数据。
4. 在没有解决“旧内核正常通信”这一反证前，不建议在 6.12 上直接补回这四条 MDIO 写，也不建议修改 PHYCR2。任何实机 MDIO 写操作都必须另行获得用户明确授权。


## 30. JL2xx1 workaround provenance and RTL8211F broadcast-address caveat (2026-11-18)

本轮继续第 29 节的历史来源核查；只读取 Git 历史、驱动源码、既有运行时 DT 记录和公开 RTL8211F datasheet，没有对设备执行 MDIO 操作。

### 30.1 补丁来源已经明确：它紧跟 JLSEMI JL2xx1 驱动加入

在 `unifreq/linux-6.1.y` 的 Git 历史中，三个提交构成连续演变：

1. `22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`，2022-12-24 16:07:18 UTC：`drv: net: phy: Add JLSEMI JL2xx1 driver`。加入 JLSemi JL2xx1 PHY driver，驱动 ID 定义为 `0x937c4030`（mask `0xfffffff0`），并声明适配 JL2xx1/JL2101。
2. `49b5f340f346cc9a5b777499fce46150b691b70e`，2022-12-24 16:08:26 UTC：`drv: net: ethernet: stmmac fix for jl2xx1 phy`。在刚加入 JL2xx1 driver 的下一分钟，向通用 STMMAC MDIO 注册和 DMA 初始化加入第 29 节所述四次 MDIO 写与 1.5 s delay。
3. `79065ed12cb4e253b532028a551fdba2963d2d65`，2023-07-25 03:22:23 UTC：`drv: net: phy: remove jl2xx1`。删除 JLSEMI PHY driver 的 Kconfig、Makefile 和三个源文件，但**没有删除或回滚** `stmmac_main.c` 的 1.5 s delay，也没有删除 `stmmac_mdio.c` 的四条硬编码写。

因此在 6.1.116 对照 commit `5eb841b...` 中，这段 STMMAC workaround 已成为一个失去原 PHY driver 配套的遗留补丁。其原始目标可高置信度认定为 JLSEMI JL2xx1/JL2101 系列，而不是 Realtek RTL8211F。

参考：
- [JLSEMI driver added](https://github.com/unifreq/linux-6.1.y/commit/22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36)
- [STMMAC JL2xx1 workaround added](https://github.com/unifreq/linux-6.1.y/commit/49b5f340f346cc9a5b777499fce46150b691b70e)
- [JL2xx1 driver removed, STMMAC workaround retained](https://github.com/unifreq/linux-6.1.y/commit/79065ed12cb4e253b532028a551fdba2963d2d65)

### 30.2 修正第 29 节关于 PHY address 0 的描述：这是 MDIO broadcast address

此前第 29.2 节写成“这组写会命中 address 0 的 RTL8211F”，需要更精确地表述：RTL8211F datasheet 说明 PHYAD 物理地址范围为 1–7；MDIO address 0 是 broadcast command，所有允许响应 broadcast 的 PHY 都会响应。datasheet 同时说明 RTL8211F 可通过 page 0xa43、reg 0x18（十进制 24）bit 13 控制是否禁用 address-0 broadcast 响应，并可在 PHYAD=000 时记住第一个非零地址。

因此，`stmmac_mdio_write(new_bus, 0, ...)` 不是针对某颗 PHY 的唯一寻址，而是发往 MDIO broadcast address。Panther 目前只有一颗已识别 PHY 的运行时记录（RTL8211F，ID `0x001cc916`，DT `reg=0`），所以它可能作用于该 PHY，但是否响应取决于该芯片当前 broadcast-enable/PHYAD 状态。没有历史 MDIO trace 或寄存器读回，不能写成“已证明成功写入 RTL8211F”。

RTL8211F datasheet Rev 1.7 对 PHYCR2（page 0xa43, reg 0x19）定义：bit 0 CLKOUT enable、bit 1 RXC enable、bit 5 PHY-mode EEE enable、bit 11 CLKOUT 125/25 MHz 选择、bit 13:12 CLKOUT SSC capability。整字写 `0x1801` 会置 bit 12、11、0，并清 bit 1、5、7、3 等可写位；但 bit 13:12 的 `01` 组合在 datasheet 中标为保留/非标准配置，不能把它描述成一个有明确预期功能的 SSC 选择。

资料：
- [RTL8211F(D)(I)-CG Datasheet Rev 1.7](https://static.chipdip.ru/lib/595/DOC042595102.pdf)
- [RTL8211F PHYCR2 register summary](https://xonstorage.z8.web.core.windows.net/pdf/realtek_rtl8211ficg_apr22_xonlink.pdf)
- [RTL8211F PHY address / broadcast behavior](https://datasheet.lcsc.com/datasheet/pdf/7023c5bb6713a670a415e3c449e0d974.pdf?productCode=C187932)

### 30.3 这使它成为“旧内核遗留的错误通用化 workaround”，但仍不是当前 TX 根因

源码证据现在支持：
- workaround 的提交目标是 JLSEMI JL2xx1，而 Panther PHY ID 是 Realtek `0x001cc916`，型号不同；
- 它没有任何 PHY ID / compatible 检查，却被放进通用 STMMAC MDIO 注册路径；
- JL2xx1 driver 后来被移除，STMMAC workaround 却残留；
- Panther 的 `clock_in_out="input"`、RGMII、PHY address 0 等运行时记录与旧 workaround 并非同一目标硬件组合。

但仍有两个重要限制：
1. 6.1.116 对照源码 SHA `5eb841b...` 是基于版本与 workflow 线索重建的高置信度来源，不是当前已取得的设备上运行 Image 二进制哈希；
2. 6.1.116 实机确实正常双向通信，与“这组写入成功清除了 RXC enable”推断冲突。broadcast address 0 的响应条件、PHY strap / broadcast-enable 状态、旧内核真实二进制是否含该块，均未实证。

因此，**不能把这段 workaround 当成 6.1.116 正常的原因，也不能简单说 6.12 删除它导致 TX 故障**。它更像一项应该从通用 STMMAC 路径移除的历史遗留风险；而且其关键寄存器改动更直接涉及 RXC/PHY EEE，不足以解释目前已定位在 TX 外部不可见的现象。

### 30.4 当前对 1.5 s delay 的独立判断

1.5 s delay 与 PHY 专用 MDIO 写来自同一 `49b5f340` 提交，故其来源同样是 JL2xx1 workaround。它位于每次 netdev open 的 DMA reset 前，不是 SoC probe 上电后的一次性全局延时。6.12 没有该等待，但 Panther 在 6.12 可以完成 PHY link-up，且该等待并未被证明是 RK3566 GMAC 必需的稳定时间。现阶段它是历史补丁差异，不是强根因候选。

### 30.5 本轮结论及后续

- **已确认：** 这段 patch 原始目标为 JLSEMI JL2xx1/JL2101；后来 PHY driver 被移除，STMMAC 两处遗留代码仍留在 6.1 分支。
- **已确认：** RTL8211F 的 MDIO address 0 是 broadcast 地址语义，旧代码并非对 RTL8211F 的唯一寻址；是否响应需看 PHY broadcast 状态。
- **已确认：** `0x1801` 会清除 PHYCR2 RXC enable 与 PHY-mode EEE enable 位，并写入保留的 CLKOUT SSC capability 编码；若有效作用于 RTL8211F，属于不应随意施加的 PHY 配置。
- **未验证：** 6.1.116 安装的实际 Image 是否包含这段旧 patch，以及 Panther PHY 当时是否响应 MDIO broadcast 写入。
- **结论：** 旧 workaround 与 Panther 型号不匹配，不可移植；但它并不能解释 6.12 的 TX 故障，尤其不能忽略 6.1 正常通信这一反证。

下一步继续审计 6.1.116 的构建身份与运行时日志证据，优先寻找可确认实际内核源码/二进制的历史 build metadata；不要求用户重跑 PHY 检查，也不执行 MDIO 写入。若仍无法获得 6.1 二进制来源，应该把这段遗留 patch 从“6.1.116 实际执行”降级为“高置信度候选源码包含”，避免把推断写成事实。


## 31. 6.1.116 source identity strengthened by exact upstream release commit and boot-image hash (2026-11-18)

本轮继续核对 6.1.116 的实际构建身份与 Actions 记录。只读取 GitHub 历史、仓库现有归档；没有设备操作。

### 31.1 6.1.116 对照源码 commit 不再只是按日期猜测

通过 GitHub REST 对 `unifreq/linux-6.1.y` 的 `drivers/net/ethernet/stmicro/stmmac/stmmac_main.c` 历史按 `until=2024-11-10T14:00:00Z` 查询，确认：
- commit `5eb841b59d6ead6e264163785a634e78f0253c8e`
- commit message 明确为 `up to 6.1.116`
- author/committer 时间：2024-11-09 08:06:23 UTC
- `Makefile` 将 `SUBLEVEL` 从 115 更新为 116
- Panther 归档中的运行内核 `uname -a` / `proc/version` 为 `6.1.116-ophub #1 SMP Sun Nov 10 08:21:17 EST 2024`，即 2024-11-10 13:21:17 UTC。

该源码 commit 是 6.1.116 版本更新提交，时间比运行内核编译时间早约 29 小时；并且正好是本轮所用 `stmmac_main.c` 版本。故 6.1.116 源码对照 commit 从“按版本与日期重建的高置信度候选”升级为“与运行版本号、源码 SUBLEVEL 和编译时间高度吻合的精确 release commit 候选”。

### 31.2 现有 Image 文件身份已保存 SHA256，但还没有可对照的构建产物

`panther-eth-supplement-redacted.txt` 已保存：
- `/boot/Image` 与 `/boot/vmlinuz-6.1.116-ophub` 是同一文件，SHA256：`bbc2ffc6e728f3a793151c225efef0ccac6b9ebb0cfed6907cd93062fd3a31d6`；
- `/boot/Image` symlink 指向 `vmlinuz-6.1.116-ophub`；
- `/boot/uInitrd` 指向 `uInitrd-6.1.116-ophub`；
- `uname` 与 `/proc/version` 报告运行 `6.1.116-ophub`，编译时间为 2024-11-10 08:21:17 EST；
- `/boot/config-6.1.116-ophub` 和 `/boot/System.map-6.1.116-ophub` 存在；另有独立的 6.1.192 文件。

### 31.3 6.1.192 包版本是环境元数据不一致，不代表运行的是 6.1.192

同一归档的 `dpkg-query` 显示 `linux-image-ophub` 与 `linux-dtb-rockchip64-ophub` 安装包版本为 `6.1.192-1-ophub`；但实际运行内核、`/boot/Image`、`/boot/uInitrd` 均明确指向 6.1.116。`/boot` 同时存在 6.1.116 与 6.1.192 的 kernel/initrd/System.map/config 文件。

因此本轮只确认“包管理器安装版本字段与正在运行/默认启动的 kernel 文件版本不一致”；不能把包版本 6.1.192 当成当前运行内核，也不能用它否定 `6.1.116` 的 uname 与 Image 证据。形成这一状态的升级/回滚过程在现有材料中没有完整记录。

### 31.4 Actions run 核对：之前引用的 43543451274 与 6.1.116 无关

GitHub Actions API 返回：
- run `43543451274` 的名称是 `Inspect Ophub 6.18.63 kernel package`，不是 6.1.116 构建；此前仅凭用户提供的链接不能将其当成 6.1.116 build evidence。
- 本仓库与 6.1.116 相关的 run `43722925635` 名为 `Audit Panther X2 6.1.116 reference DTB`，工作流 `.github/workflows/audit-reference-dtb.yml` 只从 `audit/6.1.116-reference-dtb` 分支读取已上传 DTB ZIP，验证 DTB SHA256 与结构；不构建 Linux kernel Image。
- 当前可见的本仓库 Actions runs 列表没有 6.1.116 kernel Image build run。

所以，Actions 层面尚未找到 6.1.116 Image 的 build log / artifact / artifact SHA256 关联。不能把 DTB audit run 当成 kernel build。

### 31.5 对 JL2xx1 workaround 的证据等级更新

由于 `5eb841b...` 是明确的 `up to 6.1.116` release commit，且构建时间与源码 release 时间吻合，6.1.116 候选源码确实包含 `49b5f340` JL2xx1 workaround 的判断进一步增强。

但当前仍缺 `/boot/vmlinuz-6.1.116-ophub` 对应的原始 build artifact 或可复现的二进制构建链；因此严格表述仍是：
- **高度吻合：** 6.1.116 实际运行 Image 很可能由 `unifreq/linux-6.1.y@5eb841b...` 构建；
- **未做到二进制证明：** 没有 upstream build artifact hash / build log 将 `bbc2ffc6...` 与该 commit 绑定；
- **代码存在性已确认：** 该 commit 的 `stmmac_mdio.c` 包含 2022 年 JL2xx1 专用遗留 workaround；
- **实际执行结果未确认：** Panther 的 RTL8211F 是否响应地址 0 的 MDIO broadcast 写仍无历史 trace/寄存器前后值。

### 31.6 本轮结论与下一步

6.1.116 源码身份已经从“日期推测”提升到“release commit 与构建版本/时间吻合”；但当前 repo Actions 没有对应 Image 构建，不能把它提升为二进制级证明。包版本 6.1.192 是已安装包元数据，不是实际运行版本。

下一步不再重复查同一 Actions 列表。继续做纯静态的 binary/source provenance：查找 `bbc2ffc6...` Image hash、构建时间 `2024-11-10 08:21:17 EST`、`root@<REDACTED_BUILD_HOST>` 对应的公开 Ophub release/build records；如果无公开可验证 artifact，明确记录 provenance 的证据上限，并把 JL2xx1 workaround 保留为“release 源码中存在、实机是否执行未知”的历史差异，不把它当 TX 根因。


## 32. MAC/DMA bring-up call order and RX ring preparation comparison (2026-11-18)

本轮完成 `stmmac_open → __stmmac_open → stmmac_hw_setup → stmmac_init_dma_engine → stmmac_start_all_dma` 的静态调用顺序对照，并下钻至 DWMAC4 DMA reset/start ops。未执行实机测试或寄存器访问。

### 32.1 主初始化顺序：6.1 与 6.12 基本一致

两版共同顺序：
1. `stmmac_open()` 先调用 `stmmac_setup_dma_desc()`，分配 DMA descriptor rings 并初始化 TX/RX ring；
2. `__stmmac_open()` 调用 `pm_runtime_resume_and_get()`；
3. `stmmac_init_phy()` attach PHY；
4. 执行平台 SerDes powerup（6.12 增加 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` 条件，但 Panther RK3568 glue 未注册 SerDes powerup callback）；
5. `stmmac_hw_setup()`；
6. `stmmac_init_dma_engine()` 做 DMA SW reset、DMA config、channel config、RX/TX base/tail pointer；
7. `stmmac_core_init()`、MTL 配置、`stmmac_mac_set(..., true)`；
8. 配置 DMA operation mode、ring length 等；
9. `stmmac_start_all_dma()` 先启动所有 RX channel，再启动所有 TX channel；
10. 返回 `__stmmac_open()` 后才 `phylink_start()`、request IRQ、enable queues、enable DMA IRQ、start netdev TX queues。

对 Panther RGMII，6.12 在 `stmmac_hw_setup()` 最前增加的 `phylink_pcs_pre_init()` 只有 `priv->hw->phylink_pcs` 非空才执行；RK3566 Panther RGMII 路径没有 PCS，因此该新增步骤不命中。

### 32.2 RX buffer/ring 初始化函数相同

两版 `stmmac_init_rx_buffers()` 函数逐字相同：从 page_pool 分配 RX page，设置 DMA address，配置 secondary buffer（若启用 SPH），并写 descriptor buffer address。Panther glue 在 6.12 设置 `STMMAC_FLAG_SPH_DISABLE`，因此 SPH 不应启用；这与已有代码基线一致。

两版 `stmmac_start_all_dma()`、`stmmac_start_rx_dma()`、`stmmac_start_tx_dma()` 逐字相同：RX channel 先于 TX channel启动。

### 32.3 `stmmac_setup_dma_desc()` 的差异被 Panther DT 排除

6.12 在 ring size 选择上增加 `plat->dma_tx_size` / `plat->dma_rx_size` 覆盖：若设备树设置 `tx-dma-size` / `rx-dma-size`，优先使用 DT 指定值；否则仍使用 `DMA_DEFAULT_TX_SIZE` / `DMA_DEFAULT_RX_SIZE`。

6.1 版本直接使用默认 ring size（或已有 `priv->dma_conf` size）。本轮读取 6.12 候选 Panther DTS `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`，`&gmac1` 节点没有 `tx-dma-size` 或 `rx-dma-size` 属性，因此新增 DT override 对 Panther 不生效，默认 ring size 路径相同。此项不是当前故障差异。

### 32.4 DMA SW reset polling cadence 有变化，但总超时相同

RK3566 使用 DWMAC4 DMA ops。对照 `dwmac4_dma_reset()`：
- 6.1：`readl_poll_timeout(..., 10000, 1000000)`，每 10,000 µs 轮询，最大 1,000,000 µs；
- 6.12：`readl_poll_timeout(..., 500, 1000000)`，每 500 µs 轮询，最大同样 1,000,000 µs。

因此 6.12 改为更频繁地检查 SW reset bit，但没有缩短最大等待上限；不是 reset timeout 被缩短。结合已有 6.12 DMA channel 已运行、ST/Tail pointer推进、无 fatal DMA error 的实机记录，当前没有证据指向 reset polling cadence 是 TX 外发失败原因。

### 32.5 DWMAC4 RX/TX start 的寄存器动作相同

两版 DWMAC4 `start_rx` / `start_tx` 的操作语义相同：
- RX：read channel RX_CONTROL → set `DMA_CONTROL_SR` → write back；再 read `GMAC_CONFIG` → set `GMAC_CONFIG_RE` → write back。
- TX：read channel TX_CONTROL → set `DMA_CONTROL_ST` → write back；再 read `GMAC_CONFIG` → set `GMAC_CONFIG_TE` → write back。

6.12 为适配 `dwmac4_addrs` 增加寄存器地址偏移结构参数，但没有改变 SR/ST/RE/TE 位的设置顺序和动作。此前运行时 TX ST=1、tail pointer推进、TX cleanup/MMC计数等记录也与软件已发起 DMA 相吻合。

### 32.6 本轮确认与剩余差异

- **已确认：** 初始化调用顺序、RX-before-TX 启动顺序、RX buffer init、RX/TX start helpers 在两版相同。
- **已确认：** 新增 DT ring-size override 不会命中 Panther 当前 DTS（无 `tx-dma-size` / `rx-dma-size`）。
- **已确认：** DWMAC4 reset polling cadence 从 10ms 改为 0.5ms，但最大 1s timeout 相同。
- **已确认：** 6.12 `phylink_pcs_pre_init()` 不命中 Panther RGMII；SerDes powerup conditional 对 Panther无实际作用。
- **仍存在的主差异：** 6.1 的 `stmmac_init_dma_engine()` 在 DMA reset 前等待 1500ms；6.12 没有。第 30 节已追到该等待与 JL2xx1 专用 workaround 同一提交，目标不是 Panther RTL8211F，因此不能直接移植/认定根因。
- **另一个差异：** 6.1 `stmmac_hw_setup()` 在 `stmmac_start_all_dma()` 后可启动 FPE workqueue/handshake（当 `dma_cap.fpesel`）；6.12 对照代码不再有该段。当前 Panther FPE 是否实际报告可用、DT 是否启用 FPE、FPE 是否可能改变 TX path 尚未证明；若无 FPE 配置，该差异不参与普通 TX。需静态确认 RK3568 feature register/capability与 Panther platform configuration 后再决定是否追踪，不做实机测试。

### 32.7 下一步

主流程没有发现可解释“6.12 DMA 正常运行但外部收不到帧”的顺序变化。下一轮先静态核对 Panther DWMAC4 实际选择的 DMA ops、硬件 feature capability、FPE enable 条件，以及 6.1/6.12 `stmmac_core_init()` 与 `stmmac_dma_operation_mode()` 对 GMAC TE/RE、MTL TX queue enable/priority/flow-control 的最终写入差异。优先排除“DMA TX 已运行，但 MAC/MTL TX queue 被配置成不发包”的软件路径；不重复实机 DMA/descriptor/counter 测试。


## 33. MTL TX queue / FIFO / FPE static comparison (2026-11-18)

本轮继续第 32 节预定的 MAC/MTL 配置审计。对照 `unifreq/linux-6.1.y@5eb841b...` 与 `ophub/linux-6.12.y-rockchip@661b2d8...` 的 `stmmac_mtl_configuration()`、`stmmac_dma_operation_mode()`、`dwmac4_core_init()`、RK3568 glue 与平台 DT parser。纯源码审计，无设备操作。

### 33.1 Panther 的 MTL queue 数量按当前 DT/驱动解析规则为 1 RX + 1 TX

两版 `stmmac_parse_hw_config()` / `stmmac_mtl_configuration()` 都在未提供 `snps,mtl-rx-config` / `snps,mtl-tx-config` 时回退到 `rx_queues_to_use=1`、`tx_queues_to_use=1`，queue 0 默认设为 `MTL_QUEUE_DCB`。Panther 现有 DTS 记录未见 MTL 多队列 phandle 配置，且归档 TX path 已确认普通 queue 0。因此以下多队列算法、权重、CBS、队列优先级和 RSS 路径都不会因 Panther 单队列配置执行。

### 33.2 MTL 初始化函数两版逐字相同

`stmmac_mtl_configuration()` 两版完全相同：
- 只有 TX queue 数量 >1 才设置 TX queue weight、TX scheduling algorithm、CBS、TX priority；
- 总是执行 RX queue-to-DMA mapping 和 MAC RX queue enable；
- RX/TX queue 数量 >1 才执行相应优先级/路由/RSS配置。

在单队列 Panther 配置下，唯一无条件执行的 RX MTL 操作相同。没有发现 6.12 把 TX queue 0 禁用或改变 TX scheduling 的差异。

### 33.3 DMA FIFO sizing 的源码变化不会改变 Panther 结果

6.1 无条件将 FIFO size 除以 RX/TX queue 数量；6.12 仅在 `has_gmac4 || has_xgmac` 时做该除法，注释说明是 DW QoS Eth / DW XGMAC 的共享 Tx/Rx FIFO memory split。RK3568 Panther 的 DWMAC4 兼容配置使 `has_gmac4` 为真；队列数量又是 1，所以两版最终 FIFO size 相同，不会造成 queue0 FIFO 变小或变成 0。

### 33.4 `dwmac4_core_init()` 唯一显著差异是 FPE interrupt enable

两版共同设置 `GMAC_CONFIG_TE`（当 `hw->ps` 有效）和 speed bits、写 MAC_CONFIG、配置 one-us counter、启用默认 MAC interrupts。6.1 还读取 `GMAC_HW_FEATURE3.FPESEL`，若硬件报告 FPE capability 则额外设置 `GMAC_INT_FPE_EN`；6.12 删除了这一段显式 FPE interrupt enable。

但 FPE 是 IEEE 802.1Qbu/802.3br Frame Preemption，不是普通以太网帧 TX 的必要条件。两版普通 `stmmac_xmit()`、TX descriptor 提交与 DMA start 不以 FPE 为前提；6.12 仍保留 `dma_cap.fpesel` 检查和 phylink link-up/down FPE state handler，只是 FPE 初始化/中断管理实现演变。当前没有 Panther 启用 FPE 的 DT/config 证据，也没有 FPE handshake failure 记录。故该差异目前不解释普通 DHCP Discover 无法外发，列为低优先级非根因。

### 33.5 当前 MTL 方向结论

- **已确认：** Panther 为 queue 0 单 RX/单 TX；两版 MTL 配置函数完全相同。
- **已确认：** FIFO sizing 改动在 RK3568 GMAC4 + 单队列条件下数值不变。
- **已确认：** 未发现 6.12 新增或遗漏了普通 TX queue 0 的启用、映射、权重或 scheduler 操作。
- **低优先级差异：** FPE interrupt enable 的删除；没有启用 FPE 的证据，不能视作普通 TX 根因。
- **重要边界：** `stmmac_mtl_configuration()` 主要配置 RX queue 与多队列特性；TX queue0 正常工作仍依赖 MAC link-up callback 设置 speed/duplex/TE、Rockchip `fix_mac_speed()` 更新 MAC speed clock，以及 MAC/PHY RGMII时序。

### 33.6 下一步：转入 link-up 回调的实际执行顺序与状态写入

下一轮静态追踪 `stmmac_mac_config()`、`stmmac_mac_link_up()`、`rk_fix_speed()` 和 phylink 的调用时序，重点确认：
1. `hw->ps` 在 `stmmac_core_init()` 时是否有效；若当时为 0，MAC TE 何时被打开；
2. `stmmac_mac_link_up()` 是否在 6.1/6.12 都设置 GMAC_CONFIG_TE、speed、duplex、port select 与 flow control；
3. RK `fix_mac_speed()` 是否在相同 link-up 阶段设置 `clk_mac_speed`，以及 6.12 新接口/调用时机是否改变；
4. 是否存在“DMA ST=1、descriptor 已清理，但 MAC TE 或 speed clock 未处于正确状态”的代码路径。

这比继续重复 MTL/DMA ring 检查更接近当前证据边界。仍只读源码和已有日志，不要求重跑设备测试。


## 34. phylink core resolve/link-up sequencing cross-check (2026-11-18)

本轮按第 33.6 节继续检查 phylink core 的 `phylink_resolve()` / `phylink_link_up()`，并回查第 28 节既有 stmmac callback 结论，避免重复做设备测试。仅静态比较 6.1.116 与 6.12.81 候选源码。

### 34.1 PHY 自协商路径的 resolve 行为保持等价

6.1 `phylink_resolve()` 使用 `cur_link_an_mode` switch；6.12 改用 `act_link_an_mode` if/else，并将 `link_failed` 状态管理与原 `mac_link_dropped` 重构。对于 Panther 的 `MLO_AN_PHY`：
- 两版都从 `pl->phy_state` 取得 link state；
- 两版都在 PHY link up 时设置 `mac_config=true`；
- 两版都应用 manual flow-control policy；
- 两版都在 interface 变化时先执行 link-down，再 `phylink_major_config()`；
- 两版都在 link state 从 down→up 时调用 `phylink_link_up()`。

6.12 将 `phylink_apply_manual_flow()` 从所有模式统一调用改为仅非 `MLO_AN_FIXED` 调用。Panther 是 `MLO_AN_PHY`，仍然执行，因此行为没有变化。

### 34.2 6.1 的 legacy mac_config 重调在 Panther 上是空操作

6.1 在 interface 未变化、没有 PCS 且 `legacy_pre_march2020` 条件满足时，会再次调用 `phylink_mac_config()`；6.12 删除了这个 legacy 分支。

但 STMMAC 注册的 `stmmac_mac_config()` 函数本身仅有注释 `Nothing to do, xpcs_config() handles everything`，函数体为空。Panther 是 RGMII 且没有 PCS；因此即便 6.1 满足 legacy 条件，这次额外调用也不写 MAC/MTL/时钟寄存器。删除该调用不能解释 TX 差异。

### 34.3 Link-up callback 的先后次序未变

两版 `phylink_link_up()` 都执行：
1. 从 PHY/link state 取得 speed、duplex、pause；
2. 更新 `cur_interface`；
3. 确定 negotiation mode；
4. `phylink_pcs_link_up()`（Panther 无 PCS，为空操作）；
5. 调用 `mac_ops->mac_link_up()`；
6. 最后才 `netif_carrier_on()`。

6.12 的 `cur_link_an_mode` 改为 `act_link_an_mode`，属于当前生效模式字段重命名/状态模型整理；在 Panther PHY 自协商模式下没有发现调用顺序变化。

`stmmac_mac_link_up()` 两版均在 `mac_link_up` callback 中：
- 先调用 Rockchip `fix_mac_speed()`，按已协商的 1000Mbps 将 `clk_mac_speed` 设为 125MHz；
- 再更新 MAC speed/duplex 字段；
- 调用 flow-control 配置；
- 写 MAC control register（若值变化）；
- 调用 `stmmac_mac_set(..., true)` 开启 MAC。

6.12 新增的 SerDes powerup 在 link-up callback 开头执行，但 Panther 的 Rockchip glue 未注册该回调，且当前是 RGMII，不会产生动作。6.12 新增的 hwtstamp latency correction 在普通 MAC enable 后执行，不改变普通帧发送开关。

### 34.4 Rockchip speed-clock callback 的变化是参数/对象管理，不是速率逻辑改变

两版 `rk_fix_speed()` 都按 `bsp_priv->phy_iface` 选择 RGMII 分支，并调用 `set_rgmii_speed(bsp_priv, speed)`；6.12 增加的 `mode` 参数没有被使用。

`rk3568_set_gmac_speed()` 两版都按 10/100/1000 Mbps 设置 2.5/25/125 MHz。6.1 从 bulk clock 数组索引取得 `clk_mac_speed`，6.12 从 `bsp_priv->clk_mac_speed` 直接取得；当前 Panther runtime clock_summary 已记录 125MHz 且 enabled，因此代码对象重构没有证据指向速率时钟缺失。

### 34.5 本轮结论

- **已确认：** Panther `MLO_AN_PHY` 下，6.1 与 6.12 phylink resolve/link-up 主调用顺序等价。
- **已确认：** 6.12 删除的 legacy `mac_config` 重调对 STMMAC 是空函数调用，不改变寄存器。
- **已确认：** `mac_link_up()` 中 fix speed → MAC speed/duplex → flow control → MAC enable 的顺序没有改变；PHY 自协商成功后才将 carrier 置为 on。
- **已确认：** RK3568 speed callback 的速率表和 125MHz 目标值相同，6.12 仅新增未使用的 `mode` 参数并改变 clock 指针保存方式。
- **结论：** phylink resolve / link-up 回调顺序目前可以从普通 TX 故障候选中降级；没有发现 6.12 在 PHY link-up 后遗漏 MAC TE enable 的代码路径。

### 34.6 下一步

避免再对第 28 节已完成的 `mac_link_up()` 做重复逐函数比较。下一轮回到仍未完全闭合的 software boundary：检查 `stmmac_mac_set()` 的具体 TE/RE 位操作与 MAC core init/reset 后的寄存器写入覆盖关系，以及 DWMAC4 `core_init` 中 MAC_CONFIG 的默认值/PS 位处理是否可能在 link-up 之前或之后覆盖 TE。若源码两版同样，则当前静态代码审计可给出更明确的边界结论：TX descriptor/DMA/MTL/phylink/MAC enable 均未发现足以解释外部 TX 消失的 6.1→6.12 软件差异，下一步必须依靠已归档的运行时证据或未来经授权的引脚级 TXC/TXD 观测来区分 MAC output 与 PHY line-side；不重复既有 loopback、tcpdump、DMA 计数和时钟测试。


## 35. DWMAC4 MAC enable callback and GMAC_CONFIG overwrite audit (2026-11-18)

本轮闭合第 34.6 节：比较 `stmmac_mac_set()` 实际落到的 DWMAC4 callback、`dwmac4_core_init()`、MAC_CONFIG 的 TE/RE 写入覆盖关系，以及硬件接口选择。仅静态源码与已有运行时 DT 证据；未访问设备寄存器、未运行实机测试。

### 35.1 Panther 选择 DWMAC4.10+ MAC ops，而不是 legacy MAC_CTRL callback

现有运行时 DT 已确认 GMAC compatible 包含 `snps,dwmac-4.20a`。在 6.1.116 和 6.12.81 候选源码的 `hwif.c` 中，DWMAC4 core ID >= `DWMAC_CORE_4_10` 的 hwif entry 均选择 `dwmac410_ops`；其 `.set_mac = stmmac_dwmac4_set_mac`。4.20a 高于 4.10 门槛，因此 Panther 走该项（以实际 Synopsys core version 4.20a 记录为前提）。

这点很重要：不能误用表中仅供更早 DWMAC4 entry 的 `dwmac4_ops`（其 `.set_mac = stmmac_set_mac`，操作旧 MAC_CTRL_REG）。Panther 的正确路径是 `stmmac_dwmac4_set_mac()`，直接读写 GMAC_CONFIG。

### 35.2 `stmmac_dwmac4_set_mac()` 两版逐字相同

6.1 与 6.12 的 `dwmac4_lib.c` 函数均为：
- enable=true：`value |= GMAC_CONFIG_RE | GMAC_CONFIG_TE`；
- enable=false：`value &= ~(GMAC_CONFIG_TE | GMAC_CONFIG_RE)`；
- 仅在值变化时写回 GMAC_CONFIG。

因此 link-up callback 与 `stmmac_hw_setup()` 调用 `stmmac_mac_set(..., true)` 时，都会明确置位 MAC RX/TX enable。两版没有 callback 映射差异，也没有 TE/RE 位掩码差异。

### 35.3 `dwmac4_core_init()` 的 MAC_CONFIG 处理相同

两版 `dwmac4_core_init()` 都先读 GMAC_CONFIG，再 OR `GMAC_CORE_INIT`；仅当 `hw->ps` 非零时才设置 TE 和 port-speed bits；随后写回 GMAC_CONFIG。

Panther 是外接 PHY + RGMII，未配置内部 PCS，因此 `hw->ps` 通常保持 0；core_init 这一步本身不会置 TE。但这不构成问题：紧接着 `stmmac_hw_setup()` 无条件调用 `stmmac_mac_set(..., true)`，通过上述 DWMAC4 callback 同时置位 RE 和 TE。随后 DMA start helper 也会设置对应 RE/TE。故不能只看 core_init 的 `hw->ps==0` 就推断 MAC TX 未启用。

两版 `dwmac4_core_init()` 对 MAC_CONFIG 的读-改-写逻辑逐字相同。其唯一相关函数体差异是 6.1 按 `FPESEL` 额外打开 FPE interrupt，6.12 删除该中断使能；不改 MAC_CONFIG 的 TE/RE。

### 35.4 MAC link-up 对 MAC_CONFIG 的覆盖关系

两版 `stmmac_mac_link_up()` 均先读取 MAC_CTRL_REG（对 DWMAC4，此宏对应 GMAC_CONFIG），保留原值并清除 speed mask，按协商速率写 speed bits；随后设置 duplex、flow-control，若值变化写回；最后调用 `stmmac_mac_set(..., true)` 再次强制置位 TE/RE。

6.12 变化：
- `fix_mac_speed` callback 新增 `mode` 参数（RK callback 当前不使用）；
- 新增可选 SerDes powerup（Panther RGMII 不命中）；
- 新增可选 timestamp latency correction（在 MAC enable 之后，且需平台 flag）。
这些都没有清除或覆盖 TE。

### 35.5 本轮结论：MAC enable/TE 覆盖路径已闭合

- **已确认：** Panther DWMAC4.20a 使用 `dwmac410_ops`，`set_mac` callback 为 `stmmac_dwmac4_set_mac`。
- **已确认：** 两版 `stmmac_dwmac4_set_mac()` 逐字相同，enable 时设置 GMAC_CONFIG.RE + TE。
- **已确认：** 即使 `dwmac4_core_init()` 因无 PCS、`hw->ps=0` 而不置 TE，`stmmac_hw_setup()` 随后仍无条件开启 RE/TE；link-up 时又再次开启。
- **已确认：** 两版 `dwmac4_core_init()` 的 MAC_CONFIG 写入逻辑一致，未发现后续软件路径把 TE 清零。
- **结论：** 6.1→6.12 的普通 MAC enable/TE 控制流程没有找到可解释 TX 外部不可见的差异。当前不能再把“6.12 漏开 MAC TE”作为合理根因假设。

### 35.6 重要补充：6.12 新增 unicast filter capability 修正只影响 RX

6.12 `stmmac_hw_init()` 新增对 GMAC4 `dma_cap.multi_addr` 的检查：若硬件没有额外 unicast address registers，就清除 `IFF_UNICAST_FLT` 并令 `unicast_filter_entries=0`，避免 secondary unicast filter 被错误承诺。此变化针对 MAC 接收过滤；不会影响本机发出的 DHCP Discover，也不改变 TX queue/TE/descriptor。不得将它误判为 TX 故障根因。

### 35.7 软件审计边界与下一步

到此，普通 TX 路径已依次闭合：skb/descriptor → DMA channel0 → DMA start → MTL queue0/FIFO → phylink PHY link-up → MAC speed/duplex → GMAC_CONFIG.TE。以上候选 6.1.116 与 6.12.81 源码对照中，尚未发现一处足以解释“TX DMA 有完成计数，但 hEX/iMac 外部均收不到帧”的确定性软件差异。

尚未完全覆盖的是：
1. 6.12.81 实际发布二进制与公开 `ophub/linux-6.12.y-rockchip@661b2d8...` 候选源码是否逐文件一致（构建补丁/配置仍可能有差异）；
2. MAC 到 RGMII TXD/TXC 引脚的最终硬件输出，以及 PHY line-side 发出状态。既有 loopback/scan 结果不能单独定位到 MAC output 或 PHY line-side；不得重复运行这些测试。

**当前证据支持的最窄结论：** TX 帧已进入驱动/DMA处理并由 MAC/DMA 统计回收，但尚未证明它到达 GMAC RGMII TX 引脚或 PHY 介质侧。当前故障边界在“GMAC内部 TX 统计/descriptor completion”与“外部接收端未见帧”之间；现有静态代码证据不足以断言是 MAC core、RGMII pinmux/波形、PHY 或板级信号完整性中的哪一层。

下一步不再重复常规 stmmac 主路径。应先继续静态核对 6.12.81 发布构建的补丁/配置来源，以及 `dwmac-rk.c` 中平台 reset/clock/pinctrl 的完整 probe→runtime PM→open 时序是否存在与已测正常 6.1.116 不同的、且当前实机记录尚未排除的状态切换。只有当静态证据无法再缩小范围时，才提出一个最小、非破坏性的新增验证，并先征求用户授权。


## 36. Rockchip GMAC probe / runtime-PM / open lifecycle audit (2026-11-18)

本轮按第 35.7 节检查 Rockchip GMAC 从 probe 到 netdev open 的时钟、电源、reset 和 runtime-PM 生命周期。只读比较 6.1.116 与 6.12.81 候选源码并检索已归档日志；未执行设备命令、未重跑环回/抓包、未改配置。

### 36.1 STMMAC runtime-PM 时钟回调两版完全相同

`stmmac_runtime_suspend()` / `stmmac_runtime_resume()` 两版函数体一致，均分别调用 `stmmac_bus_clks_config(priv, false/true)`。`stmmac_bus_clks_config()` 两版也逐字相同：runtime resume 依次 enable `stmmac_clk`、`pclk` 和可选 `plat->clks_config`，逐项检查返回值并在失败时回滚；runtime suspend 则 disable 两个 core clocks，再调用可选平台 callback。

Rockchip `rk_gmac_pm_ops` 的 suspend/resume 仍走 `stmmac_suspend()` / `stmmac_resume()`；6.12 的 platform wrapper 改为 `stmmac_pltfr_exit()` / `stmmac_pltfr_init()` helper，并增加 init 错误传播，但实际回调仍调用同一个 `plat->exit/init`。该差异属于 system sleep resume 错误处理，不是普通 netdev UP 期间的 TX 路径。

### 36.2 probe 与 open 的 runtime-PM 引用顺序没有变化

两版 `rk_gmac_powerup()` 都先启用 Rockchip glue clocks、配置 RGMII、启用 PHY regulator，再执行 `pm_runtime_get_sync(dev)`；`rk_gmac_powerdown()` 都先 `pm_runtime_put_sync()`，再关闭 PHY regulator 和 glue clocks。

两版 `stmmac_dvr_probe()` 都执行 `pm_runtime_get_noresume()` → `pm_runtime_set_active()` → `pm_runtime_enable()`；netdev 注册后都 `pm_runtime_put()`，允许 core clocks runtime suspend。两版 `__stmmac_open()` 都先 `pm_runtime_resume_and_get()`，再连接 PHY、执行 `stmmac_hw_setup()`、启动 phylink、申请 IRQ、启动队列；失败路径均 `pm_runtime_put()`。没有发现 6.12 把普通 open 的 PM resume 放到硬件初始化之后，或提前关闭 core clocks 的调用顺序变化。

### 36.3 MAC/AHB reset 与硬件初始化入口相同

两版 `stmmac_dvr_probe()` 的 reset 顺序一致：
1. 对可选 `stmmac_rst` assert/deassert；
2. deassert `stmmac_ahb_rst`；
3. `udelay(10)`；
4. `stmmac_hw_init()`。

两版 `stmmac_hw_init()` 均先 `stmmac_hwif_init()`，再读取 DMA hardware feature register。6.12 新增 unicast-filter capability correction、按 DMA capability 限制队列数/FIFO size 等，但 Panther 单 TX/RX queue 的普通发送不受这些新分支影响；unicast-filter correction 只涉及接收过滤。6.12 `stmmac_hw_setup()` 新增 PCS pre-init 已在第 26 节确认 Panther RGMII 无 PCS，不会命中。

### 36.4 6.12 的 integrated-PHY power callback 不会作用于外置 RTL8211F

6.12 `stmmac_release()` / PHY attach 生命周期增加 `integrated_phy_power()` callback；Rockchip callback 检查 `bsp_priv->integrated_phy` 和 RK3568 ops 对应成员。Panther 的 `integrated_phy? (no)` 已有启动日志，RK3568 ops 也没有 integrated PHY power callback，因此此项是 no-op。不会在普通 open 或 close 时切断 RTL8211F 电源。

### 36.5 仍然存在的真正差异：6.1 使用 upstream clock rework，6.12 RK35xx BSP 保留旧式逐项 enable

本轮追溯了这项差异的来源，而不是只重复记录 5ms 与 100–200µs：

- 6.1.116 工作基线使用 `devm_clk_bulk_get_optional()` + `clk_bulk_prepare_enable()`；bulk enable 返回值和 `clk_phy` enable 返回值均检查，失败会返回错误，不会把 `clk_enabled` 置 true。该实现来自 Linux upstream commit [`ea449f7fa0bf`](https://github.com/torvalds/linux/commit/ea449f7fa0bf3fcd02e04a770b9ff707bf5e8f96)（2023-04-07，`dwmac-rk: rework optional clock handling`），commit message 明确目标是可选时钟管理及正确处理 `-EPROBE_DEFER`。
- 6.12.81 RK35xx 候选来自 Rockchip vendor tree `rockchip-linux/kernel@f34ce119daa3`（2026-04-27 导入快照），`gmac_clk_enable()` 仍逐项调用 `clk_prepare_enable()`，不检查各项返回值，随后无条件将 `clk_enabled=true`；并使用 `usleep_range(100, 200)`，而 6.1 路径为 `mdelay(5)`。
- 因此这是 Rockchip 6.12 vendor BSP 与 6.1 upstream-reworked glue 的实际实现差异，不应简单表述为“Linux 6.12 通用内核改变了等待时间”。

**对 Panther 的适用性评估：**
- 已有运行时 clock-names 记录包含 `mac_clk_tx`、`aclk_mac`、`pclk_mac`、`clk_mac_speed`；已归档 clk_summary 显示 GMAC1 相关 125MHz clock tree 最终处于 enabled 状态。这降低了“某个必需 clock 一直未启用”的可能性。
- 但 clk_summary 是运行后的稳态快照，不等同于 `clk_prepare_enable()` 当时每个调用均成功，也不能还原启动瞬态。6.12 的忽略返回值确实使单项 enable 失败可能被静默吞掉；这是一项真实错误处理弱化。
- 5ms→100–200µs 是真实等待差异，但 upstream commit 的说明重点是 clock acquisition/error handling，并没有证明 5ms 是针对 Panther RGMII 必需的 PHY 稳定时间。当前 `clock_in_out=input` 且最终 link 1Gbps Full，不能仅凭等待时间认定根因。
- 已有归档的 6.1.116 启动日志有 `clock input from PHY`、`init for RGMII`，但当前仓库尚未找到一份足以逐项核对 6.12.81 probe 时所有 `cannot get clock` / enable failure 的完整原始日志。此点标记为“未验证”，不要求用户重复读取 clock_summary。

### 36.6 本轮结论与优先级更新

- **已关闭：** STMMAC runtime-PM callback、PM 引用顺序、probe/open PM 次序、MAC/AHB reset 顺序没有发现 6.1→6.12 的有效差异。
- **已关闭：** 新增 integrated-PHY callback 对 Panther 外置 RTL8211F 不生效。
- **保留为当前最高优先级软件候选：** 6.12 Rockchip vendor `gmac_clk_enable()` 对逐项 clock enable 返回值不检查，且只等待 100–200µs；6.1 upstream rework 检查错误并等待 5ms。该差异能解释“若某项启动时钟 enable 失败或时钟源尚未稳定，后续流程仍继续”的代码风险，但目前没有实证证明 Panther 本次启动发生了该故障。
- **没有发现：** probe/open/runtime-PM 中发生了错误的时钟关闭、PHY 电源切断或 reset 次序倒置。

### 36.7 下一步（只读，不重复测试）

下一轮不再检查 runtime PM、clock_summary、PHY reset 或 pinctrl 的已完成项目。优先做两件静态工作：
1. 追踪 `ea449f7` 之前 Rockchip driver 旧实现及 5ms 等待的历史意图，厘清 100–200µs 与 5ms 是否针对同一 clock-stabilization requirement；
2. 继续核对 6.12.81 发布包的 Rockchip glue 实际源码是否与 `rockchip-linux/kernel@f34ce119` / Ophub 候选一致，特别是编译时是否存在额外补丁改变 clock lookup、clock enable 或 regulator/reset 顺序。

只有找到能将差异与当前 Panther 运行时事实直接关联的证据后，才提出新的最小只读验证；未经明确授权不修改设备、不重启、不写寄存器。


## 37. Clock-delay history, CSU applicability, and 6.12.81 release-source provenance (2026-11-18)

本轮继续第 36.7 节，只读追踪上游提交历史、官方 6.12.81 发布构建记录和 Panther DTB 对 Rockchip CSU 的适用性；没有运行 Panther 命令、没有重跑任何环回/抓包测试、没有修改设备。

### 37.1 5ms 不是 2023 upstream 重构新增的稳定等待

检查 upstream `dwmac-rk: rework optional clock handling`（`rockchip-linux/kernel@c649bf43a28ee085b105c5f1f726398cc70d5ae6`，对应 upstream `ea449f7fa0bf3fcd02e04a770b9ff707bf5e8f96`）的完整 diff：
- 原先逐个 `devm_clk_get()` 改成 `devm_clk_bulk_get_optional()`；
- `gmac_clk_enable()` 改用 `clk_bulk_prepare_enable()`，并检查 bulk 和 `clk_phy` enable 返回值；
- `mdelay(5)` 在 diff 中原样保留，没有新增、缩短或改变位置；
- commit message 明确说明动机是减少重复 clock request 代码、正确处理 optional clocks 和 `-EPROBE_DEFER`。

因此：5ms 在这次 upstream 重构前就已存在。该提交没有说明 5ms 是 RK3566/RGMII 的硬件稳定时间。6.12 vendor 源码的 `usleep_range(100, 200)` 与 6.1 的 `mdelay(5)` 是 vendor 分支之间的行为差异，但现阶段没有可靠资料证明这两个等待值对应同一个明确的硬件时序要求。**等待时间差异本身不作为根因结论。**

### 37.2 CSU 是 6.12 新增代码，但 Panther 的设备树不会启用它

6.12 `dwmac-rk.c` 新增 `rk_gmac_csu_init()`，尝试取得名为 `aclk` / `pclk` 的 CSU handle；`gmac_clk_enable()` 随后调用 `rockchip_csu_disable()`，关机时调用 `rockchip_csu_enable()`。

核对 6.12 Panther X2 DTS 与 RK356x 公共 DTS：
- `gmac1` 节点没有 `rockchip,csu` 或 `rockchip,csu-names` 属性；
- `rk_gmac_csu_init()` 对获取失败的 handle 赋 NULL；
- `rockchip_csu` helper 对 NULL handle 直接返回 0。

所以虽然这段代码存在于 6.12 BSP，**在 Panther X2 当前 DTS 下 CSU 操作是 no-op**，不能解释当前 TX 故障。此项关闭。

### 37.3 Panther 的 RK3568 ops 没有 set_clock_selection callback

对照两版 `rk3568_ops`：都没有注册 `.set_clock_selection`。因此 Panther DTS 的 `clock_in_out = "input"` 不会通过该 callback 在 `gmac_clk_enable()` 中触发 GRF clock-selection 写入。两版在这一点相同，不构成 6.1→6.12 差异。

### 37.4 XPCS clocks 是 6.12 额外启用项，但当前不构成优先根因

6.12 RK356x DTSI 为 GMAC1 提供 `pclk_xpcs` 和 `clk_xpcs_eee`；vendor `gmac_clk_enable()` 在 clock handle 有效时会启用它们，即使 Panther 使用 RGMII。它们属于 XPCS/SGMII 相关时钟，不是 RGMII TXC 的直接输出时钟。该差异值得保留记录，但当前没有证据表明它们会阻断 GMAC1 RGMII TX；不提升为根因。

### 37.5 6.12.81 官方包与源码候选的关联度已提高

核对 `ophub/kernel` 官方 `kernel_rk35xx` release、workflow 和源码仓库：
- 官方 `6.12.81.tar.gz` asset SHA256 为 `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`，与本项目 `config/versions.env` 记录一致；asset 创建时间为 2026-11-13 11:14:36Z。
- `ophub/kernel` workflow run `43405957386` 在 2026-11-13 10:01:57Z 启动，任务为 `Compile rockchip rk35xx kernel`，编译输入显示 `6.12.y`，在 11:15:04Z 成功结束；与 `6.12.81.tar.gz` asset 上传时间吻合。
- 该 workflow 的 `Get kernel source commit hash` 步骤会读取所选 kernel source 仓库 `main` 分支 HEAD；workflow 允许选择 `ophub/linux-6.12.y-rockchip` 或 `unifreq/linux-6.12.y-rockchip`。
- 两个仓库的 `main` 在当前均指向同一 SHA：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；该 commit 是 2026-11-01 导入/维护的 6.12 BSP 源快照。该快照中 `dwmac-rk.c` 的代码与本轮分析的 6.12 候选一致。

**证据等级：强关联、非完整直接证明。** GitHub 公共 workflow-run API 没有暴露当次 `workflow_dispatch` 的全部 inputs 和 source-hash step 输出，因此尚不能把该 run 的源仓库选择和 source SHA 标为直接验证。但由于该 run 编译 6.12.y、asset 同时段发布，且两种 6.12 source 选择当时指向相同候选 SHA，`661b2d8...` 是当前最可信的 6.12.81 源码对照基线。实际运行内核 `6.12.81-rk35xx-ophub` 的后缀也与非 Flippy 官方 asset 对应；不能拿 `6.12.81-rk35xx-flippy-2611b` 的配置误当成当前内核配置。

### 37.6 当前剩余候选与结论

经过本轮，以下差异降级/关闭：
- 5ms 等待的“已知硬件稳定要求”解释：没有上游证据；
- CSU disable/enable：Panther DTS 无 CSU phandle，运行时 no-op；
- `set_clock_selection`：RK3568 ops 两版均未注册；
- XPCS clocks：新增但非 RGMII TXC 直接时钟，缺少故障关联证据。

**仍保留的最高优先级代码风险：** 6.12 `gmac_clk_enable()` 对 `clk_prepare_enable()` 的各项返回值全部忽略，随后无条件设置 `clk_enabled=true`；6.1 upstream-reworked 实现使用 bulk enable 并检查返回值。若 6.12 启动时 `mac_clk_tx` 或其他必需 clock enable 失败，后续 PHY link 和 MAC/DMA 内部计数仍可能正常，但 RGMII TX 侧时钟/信号可能不完整。该因果链与“内部 TX 完成计数增加、外部抓包收不到”相容，但**尚无本次启动发生 clock enable failure 的直接证据**，仍是可证伪候选而非根因定论。

### 37.7 下一步

不再重复审计 delay、CSU、runtime PM 或 clock_summary。下一步从代码层面精确区分：
1. 6.12 里 `mac_clk_tx` 与 `clk_mac_speed` 分别对应的 RK3566 CRU 输出/门控路径；
2. clock provider 的 `clk_prepare_enable()` 对这些时钟可能返回的错误条件，以及其父时钟/assigned-clock 配置是否会导致“稳态显示 enabled，但本次 enable 调用失败或 TX 输出时钟未建立”。

优先用 RK3566 CRU 源码、DTS 和已有 clock tree 记录完成静态推演。若仍需要设备证据，只提出一个只读、低风险、无需寄存器直读/重启的定向验证，并先征求授权。
