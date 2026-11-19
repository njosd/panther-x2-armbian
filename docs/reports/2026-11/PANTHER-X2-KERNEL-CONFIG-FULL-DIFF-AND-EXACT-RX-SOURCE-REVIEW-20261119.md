# Panther X2：6.1.116 完整配置核验及精确 STMMAC RX 路径对照（2026-11-19）

## 1. 本轮完成事项

本轮只读分析仓库归档与两个已锁定源码版本；未连接 Panther 设备、未执行网络测试、未修改系统或驱动。

完成：
1. 从 6.1.116 硬件审计 tar.gz 中提取真实 `kernel.config`。
2. 将其全部配置符号与对应 Ophub general `config-6.1` 模板逐项比较。
3. 以已锁定的精确源码 commit，重新核对 6.1.116 与 Ophub 6.12.81 的 STMMAC RX skb 分配和 page-pool refill 路径。

## 2. 6.1.116 完整配置比较：7677 项，零差异

原始归档：
`evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz`

- 归档 Git blob SHA：`56d2c91db73799a4c04764c045f573ab1bc40831`
- 归档大小：161,606 bytes
- 提取文件：`panther-usb-audit-6.1.116-20261116-142425/kernel.config`
- 提取文件大小：238,975 bytes
- 配置行数：9,480
- 有效配置符号数：7,677

对应官方模板：
`ophub/kernel/kernel-config/release/general/config-6.1`
- 模板 commit：`8f6eb6e392d68b89a4708c8c45caf9d3f46eadaa`
- 模板 blob SHA：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`

比较方式：将 `CONFIG_FOO=value` 与 `# CONFIG_FOO is not set` 规范化为符号和值映射，再比较全部符号集合和值。

结果：
- 实际配置符号：7,677
- 模板配置符号：7,677
- 不一致符号：**0**
- 网络、STMMAC/DWMAC、DMA、IOMMU、ARM64 相关差异：**0**

因此，6.1.116 正常运行基线的真实配置与对应 Ophub general 模板完全吻合。配置来源链闭环，不存在“拿错模板”或“现场配置与模板不一致”的证据。

## 3. 两版配置的可确认差异

6.1.116 的完整真实配置已取得；6.12.81 由用户现场输出提供关键符号，且这些关键符号与锁定的 RK35xx config-6.12 模板吻合。注意：本轮并未取得 6.12.81 全部 7,000+ 符号，因此不声称两版完整配置做过全量逐项 diff。

值得保留的跨版本差异：
- ARM64 VA_BITS：6.1 为 39；6.12 为 48。
- `CONFIG_ARM64_SW_TTBR0_PAN`：6.1 未启用；6.12 启用。
- `CONFIG_ARM64_USE_LSE_ATOMICS`：6.1 未启用；6.12 启用。
- `CONFIG_STMMAC_SELFTESTS`：6.1 启用；6.12 未启用。
- 6.12 额外启用 `STMMAC_ETHTOOL`、`STMMAC_FULL`、`DWMAC_ROCKCHIP_TOOL` 等选项；6.1 配置中没有这些符号/选项。
- 两版均启用 STMMAC、Rockchip DWMAC、PHYLINK、PHYLIB、REALTEK_PHY、PAGE_POOL、XDP_SOCKETS、NET_RX_BUSY_POLL、IOMMU DMA、Rockchip IOMMU 和 strict IOMMU default。
- 两版均未启用 DMA API debug。

解释限制：
- 不同内核版本的 Kconfig 符号会增加、删除或改名；某个新版本符号在 6.1 中不存在，不等于 6.1 中存在一个同名但关闭的功能。
- `DMA_NEED_SYNC`、`DMA_OPS_HELPERS` 等应结合 6.1/6.12 DMA API 实现语义审查，不可仅按符号名称做二元推断。
- 39→48 VA_BITS、PAN、LSE 是架构配置变化，但尚无证据表明它们导致 GMAC DMA/cache 故障。
- IOMMU 两版均启用不代表 GMAC1 实际挂接 IOMMU；已核对的 Panther GMAC1 DTS 未见 `iommus` 属性。

## 4. 精确源码版本下的 STMMAC RX 路径复核

### 4.1 源码来源

正常版本：
- 仓库：`unifreq/linux-6.1.y`
- commit：`5eb841b59d6ead6e264163785a634e78f0253c8e`
- 文件 blob SHA：`b42383fbcff86b11dd0b09ea0e1981c714625d80`

故障版本：
- 仓库：`ophub/linux-6.12.y-rockchip`
- commit：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 文件 blob SHA：`bdd0db20864b1aa6b331b3185ae65d87cdd9f3fc`

本轮使用的是已锁定的 Ophub 6.12.81 源码 commit，不再把 stable 或 unifreq 的同版本源码候选冒充为实际构建来源。

### 4.2 普通 RX skb 分配失败路径

两版的普通 RX 路径均执行：
`napi_alloc_skb(&ch->rx_napi, buf1_len)`

分配失败时：
- 6.1.116：直接执行 `priv->dev->stats.rx_dropped++`，然后计数并进入 `drain_data`。
- 6.12.81：先执行局部变量 `rx_dropped++`，结束时将累计值加到 `priv->xstats.rx_dropped`。

6.12 的局部累计方式与新版本统计同步结构相配套；目前没有证据显示它改变了普通 skb 分配失败的判定条件或导致额外丢弃。

### 4.3 Page-pool refill

两版的 `stmmac_rx_refill()` 均：
- 使用 `GFP_ATOMIC | __GFP_NOWARN`；
- 对 host DMA width <=32 时附加 `GFP_DMA32`；
- 对空 `buf->page` 调用 `page_pool_alloc_pages()`；
- 分配失败时退出 refill loop；
- 成功后取得 DMA address 并重新填充 RX descriptor。

在本轮检查的主要 refill 逻辑中，没有发现 6.12 新增的、可直接解释“普通 RX skb 分配失败计数增加”的显著行为差异。refill 分配失败本身不是上述 `rx_dropped` 直接增量点，但可能造成 descriptor 补充不足，应由 buffer-unavailable / ring 状态佐证。

## 5. 与既有运行时证据的关系

此前仓库报告已经记录：
- 某次 60 秒相邻采样中，RX dropped 增加 11；同期 RX packets 增加 162。
- 同期 GMAC overflow、missed、buffer unavailable、process stopped、fatal bus error 未增长。
- 当前检查时未发现 eth0 挂载 XDP 程序、TC ingress/egress filter 或 AF_XDP socket。
- 当时系统整体内存指标没有明显压力；这不能排除 NAPI 上下文中的短暂原子分配失败。
- 后续一份 2026-11-17 快照记录 netdev RX dropped=1,694，但该快照没有相邻采样，不能计算其增量。
- 普通 RX 的 `napi_alloc_skb()` 失败仍是现有源码与运行时条件下最直接的候选，但尚未被直接观测或证实。

本轮没有重做上述运行时测试，也没有把 1,694 当作当前值。

## 6. 研究分支结论

### 已关闭
- 6.1.116 实际配置与官方 general 模板是否不一致：**已关闭，完整符号差异为零**。
- 6.12.81 是否遗漏 STMMAC/DWMAC 编译选项：此前用户现场关键配置已核验，与 RK35xx 模板吻合。
- 将 IOMMU 全局启用直接等同于 GMAC DMA 走 IOMMU：不成立。

### 未关闭
- 6.12.81 运行期间 RX dropped 增长的具体触发分支。
- `napi_alloc_skb()` 是否在 NAPI 上下文中发生过失败。
- RX refill 是否出现过短暂 page-pool allocation failure，且未反映为明显硬件 buffer-unavailable 计数。
- 是否有未被现有快照捕获的接收路径异常。

## 7. 下一步建议：只做一个有区分力的被动观测

不再读取两版 kernel config，不再重复一般性内存快照或基础链路测试。

下一步如继续设备侧验证，优先在 6.12.81 上做短时、被动、前后相邻的只读采样：
1. 记录 eth0 的 `ip -s link` 与 `ethtool -S eth0` 中 RX dropped、RX packets、RX buffer unavailable、RX missed、process stopped、DMA error。
2. 同时记录 `/proc/vmstat` 中 allocstall、pgscan、pgsteal、compact_stall、compact_fail，以及 `/proc/meminfo` 的 MemAvailable。
3. 被动监听 DHCP UDP 67/68，不主动续租、不重启接口、不发送测试帧。
4. 在同一时间窗结束后再次采样并比较增量。

该观测只能进一步区分“系统/局部内存分配迹象”“RX ring/refill 迹象”和“报文是否进入本机抓包点”；若没有直接分配失败 tracepoint 或驱动级观测，仍不能仅凭计数确认 `napi_alloc_skb()` 失败。未经用户明确授权，不启用 tracing、不安装工具、不修改内核/驱动/网络配置。

## 8. 关联报告

- `PANTHER-X2-REPOSITORY-RETRACE-NO-REPEAT-AND-NEXT-BOUNDARY-20261119.md`
- `PANTHER-X2-KERNEL-CONFIG-PROVENANCE-AND-READONLY-CAPTURE-20261119.md`
- `PANTHER-X2-KERNEL-CONFIG-RUNTIME-VERIFICATION-20261119.md`
- `PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md`
- `PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`
