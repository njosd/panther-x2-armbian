# JP-TvBox U-Boot 实机启动记录

- 日期：2026-11-17
- 设备：Panther X2（RK3566）
- 测试介质：TF 卡
- U-Boot 候选：Ophub u-boot 仓库 jp-tvbox，commit 8bb67df906cdc8c4e33a30e5e4d562c5cb0e32a6
- 本次写入文件：idbloader.img、u-boot.itb；写入后均已从 TF 卡回读，SHA-256 与候选文件一致。
- 原始 UART 日志：evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt
- 原始日志 SHA-256：9d5eaeade7b15b443acbde6fcb363eac9c0c77f119c459e27ba1ddeece07fa08

## 实机观察

1. 主 U-Boot 成功运行：日志为 `U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`，与 JP-TvBox 候选 `u-boot.itb` 的构建标识一致。
2. U-Boot 从 MMC1/TF 卡读取 `/boot.scr`、内核、initrd 和设备树；脚本启动后，Linux 报告 `Machine model: Panther X2`。
3. Linux 成功启动到 systemd 启动流程，并出现 `Armbian login:` 提示符。日志中的内核版本为 `6.12.81-rk35xx-ophub`，不是 6.1.116。
4. 网卡驱动识别 RTL8211F PHY，随后报告 `Link is Up - 1Gbps/Full`。这证明 PHY/物理链路已建立；本日志没有 DHCP 成功或获得可用 IP 的证据，因此网络层仍未恢复/未验证。
5. 其他功能尚未完成系统性测试。日志中可见 GPU panfrost 驱动初始化、Wi-Fi/蓝牙驱动启动；同时有显示 VOP 未找到、cpufreq 初始化失败等信息，均不能据此判定相关功能已完整可用。

## 重要证据差异：SPL 来源待确认

本次 UART 日志开头显示 `DDR Version V1.13 20220218`，以及 `U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`。此前对 JP-TvBox 候选 `idbloader.img` 的静态字符串核验结果为 DDR V1.10、SPL 构建日期 Nov 12 2023。两者不一致。

因此，当前可以确认 JP-TvBox 主 U-Boot 阶段已在 Panther X2 上运行并启动 Linux；但仅凭这份日志，尚不能确认实际执行的 SPL/DDR 初始化代码就是刚写入 TF 卡的 JP-TvBox `idbloader.img`。需要后续单独追查 SPL 启动来源。

## 当前结论

- 已验证：JP-TvBox 主 U-Boot 在 Panther X2 上运行；从 TF 卡加载 Panther X2 Linux 设备树及启动文件；Linux 6.12.81 启动到登录提示符。
- 已验证：RTL8211F PHY 被识别，千兆全双工物理链路建立。
- 未验证/仍异常：DHCP、IP 地址获取及端到端网络通信。
- 待测：其他外设与系统功能。
- 待确认：本次实际运行的 SPL 是否来自 JP-TvBox idbloader。

