# Panther X2 U-Boot 板载有线网络基准实测记录（2026-11-22）

## 1. 目的与顺序

用户明确调整项目 A 优先级：历史版本已经证明 Linux 可以启动；当前先确认 U-Boot 能否独立初始化板载有线网口、建立链路并完成基本 IP 连通。顺序调整为：U-Boot 网络基准 → B1 无网络 RAM Linux → B2 网络组件逐项引入 → B3 TCP/UDP 双向验证。B1 仍是隔离基线，但不再阻挡本轮 U-Boot 实测。

仅测试 Panther X2 板载有线千兆 Ethernet；Wi-Fi/无线、蓝牙、USB/PCIe 外接网卡永久排除。不恢复历史 GMAC 根因排查。

## 2. 固定现场基线

- 当前 U-Boot 提示符：=>，Linux 尚未启动。
- U-Boot proper：U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)。
- 当前启动链：eMMC 前级 SPL → TF 上 JP-TvBox U-Boot proper 混合链；不是完整 JP SPL+proper 链。
- 不改变启动链、不重启、不启动其他镜像。

## 3. 用户授权及安全边界

用户已明确授权当前已运行 U-Boot 会话中的板载有线网口初始化、DHCP 和基本连通性实测。

授权不包括写入 eMMC/TF、save/saveenv、MII/MDIO PHY 寄存器写入/修改、fatwrite、tftpflash、tftpput、download、fastboot、rockusb、ums、boot/bootd/bootcmd/source/booti/reset、替换 SPL/U-Boot 或改变启动介质。必要 setenv 仅允许当前 RAM 临时变量，不保存。

本轮不重新运行 BootROM/SPL，不访问块设备；这不构成未来重新启动、写卡或修改 eMMC 的 B0.4 安全门豁免。

## 4. 已完成的命令能力审计

### DHCP
help dhcp 返回：
    dhcp - boot image via network using DHCP/TFTP protocol
    Usage:
    dhcp [loadAddress] [[hostIPaddr:]bootfilename]

命令入口存在，但帮助语义是 DHCP/TFTP 组合命令，没有显式 DHCP-only 参数。必须先审计该版本 autoload 机制，确认 autoload=no 可阻止 TFTP 下载后才运行 DHCP。确认前不执行，不猜测 bootfile。

### MII
help mii 显示只读 device/info/read/dump；同时有 write/modify。项目只允许只读命令。

### MDIO
help mdio 显示只读 list/read/rx；同时有 write/wx。项目只允许只读命令。

### MDIO bus 枚举
现场执行 mdio list，实际输出：
    ethernet@fe010000:

结论：实机已验证至少一个名为 ethernet@fe010000 的 MDIO bus 已注册。它对应目标以太网控制器地址；但不证明 PHY 已探测、PHY 地址/型号正确、物理链路 Link Up、MAC 收发正常或 DHCP 成功。

### ping
ping 出现在此前提供的完整 U-Boot help 清单中，只确认命令入口存在，尚未执行。

## 5. 当前验证状态

| 层次 | 状态 | 证据/缺口 |
|---|---|---|
| DHCP/ping 命令入口 | 部分确认 | 命令存在，未实测 |
| Ethernet/MDIO 注册 | 已确认一项 | mdio list 列出 ethernet@fe010000 |
| PHY 枚举 | 未验证 | 待 mii device、PHY info |
| 物理链路 | 未验证 | 待只读 link 状态 |
| DHCP | 未验证 | 待审计 autoload 并安全实测 |
| LAN 网关 ICMP | 未验证 | 待 ping |
| 外部 IP ICMP | 未验证 | 待 ping |
| TCP/UDP | 本轮不测 | 后续 B3 分别验证 |

## 6. 下一步

严格一次一条命令：
1. mii device，列出实际 MII 设备。
2. 确认 PHY 地址/型号；只读检查，不猜地址、不写寄存器。
3. 只读确认 PHY link。
4. 检查 printenv autoload，并从当前 U-Boot 对应源码核实 DHCP 实现；只有确认 autoload=no 不会触发 TFTP 下载，才运行 DHCP。
5. DHCP 成功后分别 ping LAN 网关和已知外部 IP；DNS 不作为前置条件。
6. 任一层失败即停，不同时更换网线、端口、U-Boot 或网络参数。

## 7. 结果解释边界

U-Boot DHCP、网关和外部 IP ping 均成功，表示当前启动链在本次条件下完成 Ethernet 初始化、PHY/link、MAC 收发、DHCP 和 IP 基本连通，可作为 Linux B2 的强对照；但不能证明 Linux 唯一故障点。PHY/link 成功但 DHCP 失败，只证明已通过层级。U-Boot 无法识别 PHY 或建立 link，也不能直接判定硬件损坏。U-Boot 与 Linux 的 control FDT、pinctrl、reset、delay 和初始化路径可能不同。

## 8. 当前结论

目前只能确认当前 U-Boot 有 DHCP/MII/MDIO/ping 命令入口，且实机注册了 ethernet@fe010000 MDIO bus。PHY、link、DHCP、ICMP 均未验证。下一条待执行命令：mii device。本报告不代表网络已经打通。

关联文档：项目 A 总路线图、分阶段实施计划、B1 U-Boot 启动前检查记录及 U-Boot 候选研究报告。
