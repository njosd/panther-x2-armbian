# Panther X2：Linux 6.1.116 USB + Ethernet 基线归档说明

- 采集日期：2026-11-16
- 参照系统：Armbian 24.8.4 / Ubuntu 22.04.5，Linux 6.1.116-ophub
- 设备：Panther X2（RK3566）
- 用途：作为切换至 TF 卡 Linux 6.12.81-rk35xx-ophub 后的 USB、Ethernet、设备树与启动配置对照基线。
- 原则：本归档为只读采集，不代表对 6.12.81 的问题已有根因结论。

## 归档文件

完整归档已上传至：

[下载归档](../../evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz)

GitHub main 分支路径：

evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz

GitHub Blob SHA：56d2c91db73799a4c04764c045f573ab1bc40831  
GitHub 显示文件大小：161,606 bytes。

此前的两个归档均保留，没有覆盖：

- panther-usb-audit-6.1.116-20261116-142425.tar.gz：早期 USB 原始采集包。
- panther-usb-audit-6.1.116-20261116-142425-complete.tar.gz：USB + Ethernet 基础完整包。

## 归档内容清单

### USB / 网络 / 内核基线

| 文件 | 内容 |
|---|---|
| usb-audit.txt | USB 控制器、Root Hub、设备枚举、USB 拓扑和块设备等采集结果 |
| ethernet-audit.txt | eth0、驱动、链路、PHY、路由、网络服务与配置清单、连通性快照等 |
| kernel.config | 当前运行内核配置 |
| dmesg-full.txt | 完整内核启动及运行日志 |

### 启动与设备树补充证据（boot-config/）

| 文件 | 来源 / 说明 | SHA256 |
|---|---|---|
| running-fdt.dtb | /sys/firmware/fdt，运行时设备树 | f6d95eb21889f57372ace6292bf82b25e1c3fca52da662b60cb1cec832aa9e32 |
| rk3566-panther-x2.dtb | /boot/dtb/rockchip/rk3566-panther-x2.dtb | 5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82 |
| armbianEnv.txt | Armbian 启动环境配置 | 4571b474cc7ee78d6612fa4c364b5d88bf3ec39879a5a512332e2ee1ae940e97 |
| boot.cmd | U-Boot 启动脚本源文件 | 4896dde2b99bebbb34b2ed2f837f30fa1a5b3ad14b80dd2da391effa94d37d0a |
| boot.scr | 编译后的 U-Boot 启动脚本 | 0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a |

以上五个补充文件已在 Panther X2 本机复制，并对每个文件执行 sha256sum。运行时 FDT 与磁盘 DTB 是两个不同对象，哈希不同；不能仅凭哈希差异判断异常。后续应解析两者内容并比较 U-Boot 对设备树所做的修改。

启动配置中已记录的关键参数：

- fdtfile=rockchip/rk3566-panther-x2.dtb
- ROOTFS UUID：ddcbfa1d-95e7-4863-97c8-ec9b7767968b
- 串口：ttyS02,1500000
- USB storage quirks：0x2537:0x1066:u,0x2537:0x1068:u
- net.ifnames=0、max_loop=128
- Docker 优化参数：docker_optimizations=on

本次启动命令行已在采集记录中保留，完整内核配置和 dmesg 也在归档中。

## 已验证的硬件观察

### USB

- 已验证一个实际 USB 物理接口及 USB 2.0 存储设备枚举。
- 设备 VID:PID：1e3d:2093，以 High-Speed 480 Mb/s 连接。
- usb-storage 已绑定，设备识别为 SCSI 磁盘。
- 该次日志未见 USB reset、枚举失败或传输错误。
- xHCI 控制器节点为 fcc00000.usb；日志显示 USB 3 Root Hub 无端口，USB 2 Root Hub 正常。
- 未验证所有物理 USB 口、USB 3 实际数据传输性能及持续负载稳定性。

### Ethernet

- 运行时网卡为 eth0，驱动 rk_gmac-dwmac，GMAC 平台节点 fe010000.ethernet。
- PHY 为 RTL8211F，PHY ID 0x001cc916，接口模式 RGMIi。
- 最近一次已验证链路为 1000 Mb/s Full Duplex；此前曾出现 100 Mb/s，重新接线/更换网线后恢复千兆，不能把早期 downshift 单独归因于内核。
- 已采集 ethtool、sysfs、MDIO/PHY、设备树属性、网络路由/邻居、网络服务与配置文件清单，以及当时的连通性快照。
- 6.1.116 可作为 6.12.81 对照参照；不要把链路速率问题与 DHCP 失败直接等同。

## 完整性状态与限制

已确认：

1. 原始 USB + Ethernet 归档在本机执行 tar -tzf 成功，目录中有四个核心文件。
2. 补充的五个启动/设备树文件已在本机复制，且逐个计算 SHA256。
3. GitHub main 分支已存在新的 complete-with-boot-config.tar.gz 文件，文件大小和 Blob SHA 已记录。

尚未完成的独立核验：

- 尚未在本次会话中解开 GitHub 上的新归档，逐项确认其内部确实包含四个核心文件和 boot-config/ 下五个补充文件。
- 尚未取得新归档在 Panther 本机的整体 SHA256，因此不能声称 GitHub 下载副本与本机新归档已做端到端哈希比对。
- GitHub Blob SHA 是 Git 对象标识，不等同于归档文件的 SHA256。

建议在切换前做一次极简只读检查：对新归档执行 tar -tzf，确认 boot-config/running-fdt.dtb、boot-config/armbianEnv.txt、boot-config/rk3566-panther-x2.dtb、boot-config/boot.cmd、boot-config/boot.scr 均在包内，并记录新归档整体 sha256sum。无需重新采集 USB 或 Ethernet。

## 6.12.81 对照时的约束

- 由操作者关机并切换 TF 卡；本说明不授权自动修改设备。
- 尽量保持同一网线、交换机端口、USB 物理接口和同一 U 盘。
- 启动后采集对应的运行时 FDT、磁盘 DTB、启动环境、内核配置、dmesg、USB 与 Ethernet 状态。
- 先核对链路和设备树，再围绕 DHCP Discover/Offer 路径做针对性分析；不重复此前已完成的整套 hEX 抓包。
- 不预设根因，不把 100 Mb/s 链路、PHY flags 或设备树单一差异直接认定为 DHCP 故障原因。
- 在用户明确授权前，不安装软件、不改内核/驱动/网络配置，不影响已有服务与存储测试。

## 阶段结论

6.1.116 的 USB + Ethernet 运行基线、内核配置、完整 dmesg、磁盘 DTB、运行时 FDT 和主要启动配置均已采集。本阶段不再需要重复 USB 插拔、测速或通用网络测试。完成新归档内部清单及整体 SHA256 的最后核验后，即可切换到 6.12.81 进行针对性实机对照。


## 补充：6.1.116 启动身份与端到端连通性确认

> 来源：用户于 2026-11-17 提供的历史对话补充记录。此处是对话中已确认结果的归档，不是原始终端日志；原始命令输出未随本段提供。

### 启动身份

- 实际运行内核：`6.1.116-ophub`。
- `/boot/Image` 指向 `vmlinuz-6.1.116-ophub`。
- `/boot/uInitrd` 指向 `uInitrd-6.1.116-ophub`。
- 实际 DTB：`rk3566-panther-x2.dtb`；运行时设备树确认设备为 Panther X2 / RK3566。
- `6.1.192` 仅出现在已安装软件包记录中，属于升级遗留；没有证据表明它参与本次启动。实际运行内核、启动镜像和 DTB 均指向 6.1.116。

### IPv4 连通性

本轮 6.1.116 实机验证结果：

| 检查项 | 结果 |
|---|---|
| eth0 状态 | `UP, LOWER_UP` |
| 链路 | 1000 Mbps Full Duplex |
| DHCP | 已获得 LAN IPv4 地址 /24 |
| ping hEX（LAN 网关） | 0% 丢包 |
| ping iMac（LAN 主机） | 0% 丢包 |
| RX/TX errors、dropped、carrier errors | 均为 0 |

具体 LAN 地址不在公开记录中。上述结果补充确认：6.1.116 不仅获得 DHCP 地址和默认路由，而且到 hEX 与另一台 LAN 主机的 IPv4 通信正常。

**证据边界：** 本补充来自用户提供的历史对话文字；尚未取得对应原始终端输出或抓包文件。因此可将测试结果标记为“用户确认已验证”，但不能把本段当作逐条原始命令输出，也不能据此声称已完成 DNS、互联网或完整应用层测试。
