# 2026-11 报告

本月阶段性测试与调查报告目录。每份报告需链接原始证据和相关 Actions run。

## Panther X2 网络与启动链

- [Ethernet TX 物理边界测试与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)：归档 AF_PACKET 自定义帧与 iMac 持续抓包结果、TX ftrace/kprobe 和 MMC 计数、6.1/6.12 Rockchip STMMAC/DWMAC4 源码对照、危险 debugfs 读取事故及后续只读研究路线。

- [Linux 6.12.81 网络测试结果汇总（脱敏，2026-11-16）](./PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md)：将分段提供的 6.12.81 网络测试结果合并归档，覆盖系统身份、启动介质、运行时 DT、GMAC/PHY、ethtool、MMC/DMA、IRQ、RX dropped、IPv4/IPv6 状态及待验证事项。

- [网络与启动链阶段测试总记录（2026-11-16 至 2026-11-17）](./PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)：按时间汇总 6.1.116 正常网络基线、6.12.81 DHCP/NDP 与 GMAC/DMA 检查、TF/eMMC/U-Boot/DTB 取证、JP-TvBox 启动结果及源码对照；明确区分已验证、未验证和证据缺口。

- [GMAC / DHCP 与 TF U-Boot 启动链调查记录（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)：汇总 Linux 抓包边界、GMAC1/RGMII/RTL8211F、GRF/时钟、TF U-Boot 证据，并追加 6.12.81 GMAC RX/DMA/NAPI 只读复核。
- [TF 前 16 MiB 与 boot.scr 只读证据（2026-11-17）](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)：记录 TF 原始启动区 SHA-256、SPL/U-Boot 字符串偏移、E25/RK3568 内嵌 DTB 标识、boot.scr 镜像头及完整解码脚本行为。
- [eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)：eMMC 历史 U-Boot 文件及 Vendor Storage 只读审计。注意该报告不代表本轮 TF 启动时实际执行的 U-Boot。
- [TF 启动故障调查](./TF-BOOT-FAILURE-INVESTIGATION.md)：此前 TF 启动与系统故障阶段性记录。

- [6.1.116 Ethernet 基线原始采集（脱敏）](../../evidence/network/panther-eth-baseline-redacted.txt)：完整 eth0、GMAC/PHY、ethtool、计数器、路由与网络状态采集。
- [6.1.116 Ethernet 补充采集（脱敏）](../../evidence/network/panther-eth-supplement-redacted.txt)：内核/软件包/启动镜像/DTB 核对及网关、iMac 连通性测试。
