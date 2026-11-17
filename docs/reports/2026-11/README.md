# 2026-11 报告

本月阶段性测试与调查报告目录。每份报告需链接原始证据和相关 Actions run。

## Panther X2 网络与启动链

- [GMAC / DHCP 与 TF U-Boot 启动链调查记录（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)：汇总 Linux 抓包边界、GMAC1/RGMII/RTL8211F、GRF 与时钟读回、PHY reset GPIO、TF/eMMC 身份及当前 TF 启动链证据；已追加 TF 前 16 MiB 与 boot.scr 新证据。
- [TF 前 16 MiB 与 boot.scr 只读证据（2026-11-17）](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)：记录 TF 原始启动区 SHA-256、SPL/U-Boot 字符串偏移、E25/RK3568 内嵌 DTB 标识、boot.scr 镜像头及完整解码脚本行为。
- [eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)：eMMC 历史 U-Boot 文件及 Vendor Storage 只读审计。注意该报告不代表本轮 TF 启动时实际执行的 U-Boot。
- [TF 启动故障调查](./TF-BOOT-FAILURE-INVESTIGATION.md)：此前 TF 启动与系统故障阶段性记录。
