# 2026-11 报告

本月阶段性测试与调查报告目录。每份报告需链接原始证据和相关 Actions run。

## Panther X2 网络与启动链

- [TRACE 缓冲区空状态确认（2026-11-19）](./PANTHER-X2-TRACE-BUFFER-EMPTY-BASELINE-20261119.md)：确认 tracer=nop、entries-in-buffer/entries-written=0/0；当前 trace buffer 无需保留的历史记录，尚未创建探针。
- [TRACEFS 双路径实例与缓冲区核验（2026-11-19）](./PANTHER-X2-TRACEFS-MOUNT-IDENTITY-AND-BUFFER-20261119.md)：确认两个路径为同一 tracefs 实例；trace 文件为 515 bytes，内容尚未读取，保留现有 tracing 状态。
- [TRACEFS 当前状态核验（2026-11-19）](./PANTHER-X2-TRACEFS-CURRENT-STATE-20261119.md)：记录 tracing_on=1、current_tracer=nop、无已注册 kprobe/启用事件；保留 tracing 状态与缓冲区，下一步只读确认双挂载实例关系。
- [napi_alloc_skb() 返回值短时探针结果（2026-11-19）](./PANTHER-X2-NAPI-ALLOCATOR-RETURN-PROBE-RESULT-20261119.md)：30 秒探针命中 62 次、missed 0、NULL 返回事件 0；临时探针已删除且原 tracing 状态保持不变。该结果只降低分配失败嫌疑，不证明整个 RX 路径正常。
- [6.12.81 实机 KPROBE / TRACEFS 只读能力检查（2026-11-19）](./PANTHER-X2-6.12-KPROBE-TRACEFS-READONLY-CAPABILITY-20261119.md)：确认实机 tracefs、KPROBES/KPROBE_EVENTS、目标函数 kallsyms 符号及现有 kmem/page_pool/NAPI/SKB tracepoint；下一步先只读检查 tracing 现状，尚未创建探针。
- [6.1.116 实际内核配置闭环与 STMMAC RX 差分（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md)：从原始硬件审计归档提取真实 kernel.config，与官方模板 7,677 个符号全量比较（差异 0）；对 6.1.116/6.12.81 候选 STMMAC RX 主函数进行定点差分。
- [NAPI skb 分配器差分与只读取证方案（2026-11-19）](./PANTHER-X2-NAPI-SKB-ALLOCATOR-DIFF-AND-READONLY-TRACE-CHECK-20261119.md)：比较两版 napi_alloc_skb 实现，记录 6.12 tracing/kprobe 构建能力及不改变运行状态的只读检查方案。
- [6.12.81 实际运行内核配置核验（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-RUNTIME-VERIFICATION-20261119.md)：记录 Panther 实机 6.12.81 运行配置与已锁定构建模板的关键符号核验结果。
- [内核配置来源与只读取证计划（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-PROVENANCE-AND-READONLY-CAPTURE-20261119.md)：记录两版内核正确构建来源、模板差异和配置提取边界。

- [Ethernet TX 物理边界测试与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)：归档 AF_PACKET 自定义帧与 iMac 持续抓包结果、TX ftrace/kprobe 和 MMC 计数、6.1.116/6.12.81 精确源码对照、TX descriptor/DMA/MTL/FIFO/时钟审计、危险 debugfs 读取事故及后续 MAC TXC/TXD 物理边界研究路线。

- [Linux 6.12.81 网络测试结果汇总（脱敏，2026-11-16）](./PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md)：将分段提供的 6.12.81 网络测试结果合并归档，覆盖系统身份、启动介质、运行时 DT、GMAC/PHY、ethtool、MMC/DMA、IRQ、RX dropped、IPv4/IPv6 状态及待验证事项。

- [网络与启动链阶段测试总记录（2026-11-16 至 2026-11-17）](./PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)：按时间汇总 6.1.116 正常网络基线、6.12.81 DHCP/NDP 与 GMAC/DMA 检查、TF/eMMC/U-Boot/DTB 取证、JP-TvBox 启动结果及源码对照；新增独立的 6.12.69 RX/IRQ/NAPI 只读快照与 DHCP 证据边界判读，明确区分不同内核启动周期、已验证、未验证和证据缺口。

- [GMAC / DHCP 与 TF U-Boot 启动链调查记录（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)：汇总 Linux 抓包边界、GMAC1/RGMII/RTL8211F、GRF/时钟、TF U-Boot 证据，并追加 6.12.81 GMAC RX/DMA/NAPI 只读复核。
- [TF 前 16 MiB 与 boot.scr 只读证据（2026-11-17）](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)：记录 TF 原始启动区 SHA-256、SPL/U-Boot 字符串偏移、E25/RK3568 内嵌 DTB 标识、boot.scr 镜像头及完整解码脚本行为。
- [eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)：eMMC 历史 U-Boot 文件及 Vendor Storage 只读审计。注意该报告不代表本轮 TF 启动时实际执行的 U-Boot。
- [TF 启动故障调查](./TF-BOOT-FAILURE-INVESTIGATION.md)：此前 TF 启动与系统故障阶段性记录。

- [6.1.116 Ethernet 基线原始采集（脱敏）](../../evidence/network/panther-eth-baseline-redacted.txt)：完整 eth0、GMAC/PHY、ethtool、计数器、路由与网络状态采集。
- [6.1.116 Ethernet 补充采集（脱敏）](../../evidence/network/panther-eth-supplement-redacted.txt)：内核/软件包/启动镜像/DTB 核对及网关、iMac 连通性测试。
