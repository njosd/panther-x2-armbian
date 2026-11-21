# 旧版最小 initramfs 构建蓝图（已归档，不再作为执行文件）

> **状态：技术原则已整合进「Panther X2 项目 A」；本文件保留原路径仅用于历史链接兼容。**

当前唯一权威文件：
- [项目 A 总路线图](PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)
- [项目 A 分阶段实施计划](PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)

旧蓝图曾将最小用户空间构建与特定网卡故障诊断目标绑定。自 2026-11-21 起，项目 A 与网卡故障根因调查完全分离。项目 A 的网络范围仅限 B2 静态 IP/ARP/ICMP 和 B3 必要 TCP/UDP 基础连通性，不含 GMAC/MDIO/PHY/RGMII/STMMAC 故障排查，也不复测历史专项项目。

原蓝图中有效的 RAM initramfs 分层构建、BusyBox 精简、上游优先、版本/哈希锁定、CI 可复现性、工具按阶段加入、禁止未授权写卡/启动等原则，已经整理进入项目 A。执行时以项目 A 文档为准。
