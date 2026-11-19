# Panther X2：6.1.116 实际配置闭环与 STMMAC RX 路径定点差分（2026-11-19）

## 1. 本轮范围与安全边界

只读读取 GitHub 仓库中的既有归档、官方构建配置和两套候选内核源码；没有连接 Panther 设备，没有运行网络测试，没有修改系统、内核、驱动、设备树或服务。

本轮完成两个目标：
1. 从 6.1.116 硬件审计归档中提取真实 `kernel.config`，与对应构建模板做全量符号比较。
2. 对已锁定的 6.1.116 与 6.12.81 候选 STMMAC `stmmac_rx()` 代码做定点差分，避免重复泛化审计。

## 2. 6.1.116 真实运行配置：与模板完全一致

来源：
- 原始归档：`evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz`
- 归档 blob SHA：`56d2c91db73799a4c04764c045f573ab1bc40831`
- 归档内文件：`panther-usb-audit-6.1.116-20261116-142425/kernel.config`
- 配置长度：238,975 bytes；9,480 行
- 6.1.116 官方模板：`ophub/kernel@8f6eb6e392d68b89a4708c8c45caf9d3f46eadaa:kernel-config/release/general/config-6.1`
- 模板 blob SHA：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`

采用 Kconfig 标准文本解析：`CONFIG_FOO=value` 作为值，`# CONFIG_FOO is not set` 作为 `n`；比较两个文件中所有符号的值，不把注释/格式差异计入符号差异。

结果：
- 归档真实配置：7,677 个符号
- 官方模板：7,677 个符号
- 符号值不一致：**0**
- 网络、STMMAC、DMA、IOMMU、ARM64 相关差异：**0**

因此，6.1.116 原始正常环境的实际配置与对应官方模板完全一致。“6.1.116 设备配置偏离官方模板”这一疑点关闭。

## 3. 两套 STMMAC 源码的准确比较对象

### 6.1.116 候选源码
`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`

文件 blob：
`drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
SHA：`b42383fbcff86b11dd0b09ea0e1981c714625d80`

### 6.12.81 候选源码
`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

文件 blob：
`drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
SHA：`bdd0db20864b1aa6b331b3185ae65d87cdd9f3fc`

重要限制：6.12.81 该源码 commit 是此前仓库调查锁定的高度相关候选；目前仍未从 Panther 正在运行的 Image 反推出唯一源码 commit/完整补丁集。因此下列差分是两份明确源码候选的差分，不冒充已证明与运行二进制逐字节对应。

## 4. RX 主函数差分结果

对两个版本完整 `stmmac_rx()` 函数做逐行归一化比较，219 行与 233 行，归纳出 20 组差异。

### 4.1 没有发现普通 skb 分配失败分支的语义变化

两版普通 RX 路径均使用：
`napi_alloc_skb(&ch->rx_napi, buf1_len)`

分配失败时均：
- 增加驱动 `rx_dropped`；
- 增加本轮 NAPI 处理 count；
- 跳转 `drain_data`，随后继续处理/回收流程。

差异仅是计数写法：
- 6.1：在分支中直接 `priv->dev->stats.rx_dropped++`
- 6.12：先累加局部 `rx_dropped++`，在函数末尾统一加到 `priv->xstats.rx_dropped`

这属于统计更新批处理，单凭该差异不能解释分配失败为什么发生。

### 4.2 RX refill 的 page-pool 分配失败处理没有明显变化

两版 `stmmac_rx_refill()` 均调用：
`page_pool_alloc_pages(rx_q->page_pool, gfp)`

失败时均停止 refill loop（`break`），该位置本身不增加 `rx_dropped`。因此不要把 `rx_dropped` 累计值直接解释成 page_pool refill 失败次数。

### 4.3 其余值得记录的差异

| 差异 | 6.1.116 | 6.12.81 候选 | 初步判断 |
|---|---|---|---|
| NAPI budget 边界 | `count >= limit` | `count >= limit - 1 && limit > 1` | 调度/预算处理变化；尚无证据关联当前故障 |
| XDP buffer 准备 | `xdp_prepare_buff(..., false)` | `xdp_prepare_buff(..., true)`，并引入 `stmmac_xdp_buff` 上下文 | 只在 XDP 路径有意义；当前运行快照未发现 XDP 程序 |
| RX page 交给 skb | `page_pool_release_page()` | `skb_mark_for_recycle()` | page-pool 生命周期 API/回收方式变化，需结合内核 page_pool API 理解；不是直接故障证据 |
| VLAN | `stmmac_rx_vlan()` | 根据 `hw_vlan_en` 选择 MAC stripping 或驱动 stripping | 仅在 VLAN stripping 配置/报文相关时可能影响解析 |
| checksum | 仅按 `coe` 判断 | 还检查 IP EtherType 与 `csum_none` | checksum 标记更细化；不直接解释物理收发失败 |
| 统计更新 | 多处直接更新 | 局部累计，函数末尾批量更新 | 统计一致性/并发读取方式变化，不等于收包路径变化 |

### 4.4 纠正一个容易误读的地方

6.12 RX 代码中在 XDP buffer 初始化前出现的 `dma_sync_single_for_cpu()`，在 6.1 对应位置也存在。本轮没有把它误记为 6.12 新增差异。

两版 page-pool 创建均设置：
`PP_FLAG_DMA_MAP | PP_FLAG_DMA_SYNC_DEV`

因此，不能仅凭 6.12 的 `CONFIG_DMA_NEED_SYNC=y` 或看到某个 `dma_sync_single_for_cpu()` 调用，就认定 6.1/6.12 的 RX cache sync 路径存在缺失。需要结合 ARM64 DMA API 实现和实际映射方向再判断。

## 5. 对既有运行时证据的重新定位

既有 6.12.81 测试报告已记录：
- 一次 60 秒相邻采样中 `rx_dropped` 增加 11；
- 同期 RX packet counter 增加 162；
- XDP/TC/AF_XDP 检查未发现附着或 socket；
- MemAvailable 充足，allocstall、pgscan、pgsteal、compact_stall/fail 未见增长；
- 同期 GMAC overflow、missed、buffer unavailable、process stopped、fatal bus error 均未增长。

这些证据意味着：
1. `rx_dropped` 并非仅是启动早期历史累计值。
2. 不能简单归因为系统整体内存不足。
3. 在普通 RX 分支中，`napi_alloc_skb()` 失败仍是候选源码里最直接、且在无 XDP 时仍适用的 `rx_dropped` 来源。
4. 但目前没有直接记录到 `napi_alloc_skb()` 返回 NULL；仍不能把累计 dropped 全部定性为 skb 分配失败。
5. RX refill 缺页与 `rx_dropped` 是不同证据路径，需看 ring/buffer 状态，不应混为一谈。

## 6. 当前结论

### 已验证
- 6.1.116 归档内真实 `kernel.config` 与官方 general config-6.1 全量 7,677 个符号完全一致。
- 6.12.81 现场关键配置与其已锁定的 RK35xx 构建模板一致。
- 两个 STMMAC 源码候选的普通 RX skb 分配失败分支基本相同。
- 两版 page-pool refill 分配失败都不会在该位置直接增加 `rx_dropped`。
- 当前无 XDP/AF_XDP 证据，因此不应优先追查 XDP-only dropped 分支。

### 尚未验证
- 6.12.81 正在运行的 Image 与候选源码 commit 的精确对应关系。
- `napi_alloc_skb()` 是否在故障窗口实际返回 NULL。
- 两版本 DMA API / page_pool API 的底层实现差异是否会影响实际运行。
- DHCP 报文是否到达 Panther RX descriptor，以及丢弃发生在哪个阶段。

### 当前不做
- 不重跑已经完成的常规链路、MAC、PHY、TX descriptor、时钟、DTS 审计。
- 不再重复静态内存快照。
- 不安装工具、不改内核参数、不修改驱动/设备树、不重启网络接口。

## 7. 下一步建议：只推进一个最小证据问题

下一阶段优先解决“6.12.81 的 `napi_alloc_skb()` 失败是否真实发生，以及发生时的分配上下文”，而不是继续扩展普通源码比较。

优先从已有内核日志、可用 tracepoint/现成 debug 接口、已有统计中寻找无需改系统的证据；若必须临时开启 tracing 或增加探针，应先列出具体开关、持续时间、性能影响和恢复方法，得到用户明确授权后再执行。

在该证据闭环前，不建议修改 `DMA_NEED_SYNC`、IOMMU、NAPI budget 或 page-pool 参数进行试错。
