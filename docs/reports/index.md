# 阶段性报告索引

测试/调查报告按 YYYY-MM/ 归档。长期有效的技术结论应回写对应主题文档；报告保留当时的环境、证据和结论。

## 2026-11

- [Panther X2 eMMC U-Boot 与 Vendor Storage 审计](2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)：记录 eMMC BOOT/ROOTFS 只读检查、原始用户区 LBA 64/16384 与 Ophub U-Boot 二进制逐字节匹配、idbloader 内部 E25/RK3568 FDT 与旧 UART 的强指纹吻合、Vendor Storage LAN_MAC 条目结构及待验证的实际启动与 MAC 读取路径；MAC 和 UUID 已脱敏。
- [Panther X2 TF 启动故障调查](2026-11/TF-BOOT-FAILURE-INVESTIGATION.md)：汇总 6.12.81 实机 MMC 枚举后 EXT4/JBD2 I/O 错误的已知证据和未证明问题。
