# Panther X2 项目 A：B1 完整基础配置与网络隔离基线纠偏

- 日期：2026-11-23
- 适用阶段：B1；为 B2-1 至 B2-5 提供统一起点
- 基准提交：`212f222d23833da1911085b794c9876322a973c4`
- 状态：仓库变更已提交至独立分支；未运行 CI、未生成新 artifact、未进行实机测试

## 1. 纠偏原因

旧 B1 从 `allnoconfig` 起步，除网络外还裁掉 MMC/block、USB、文件系统、模块和大量正常 SoC/外设基础能力。DTB 脚本还禁用了 eMMC、TF/SD、USB host/PHY 和通用 UART1，替换完整 aliases，并删除 Ethernet LED 与 GMAC 外部时钟节点。这扩大了变量范围，使启动失败更难归因。

用户决定恢复正常基础配置，只裁剪网络相关功能。本报告覆盖此前 B1 与该决定冲突的规则。

## 2. 新 B1 原则

**保留正常 RK35xx 非网络基础配置，只隔离网络相关功能。**

保留 ARM64 4KB 页、VA48、PA48、LPA2 off、RK3566 erratum、BLOCK/MMC/eMMC/TF/SD、USB host/PHY、常规文件系统、MODULES、UART1/2、时钟/复位/pinctrl/regulator/PMIC/DMA/中断等正常基础能力。

只隔离网络协议栈、网络设备、Ethernet/GMAC/STMMAC/DWMAC、MDIO、PHY/PCS、Wi-Fi/无线和 Bluetooth。Wi-Fi/无线、Bluetooth 永久排除；USB/PCIe 外接网卡不属于项目 A。板载有线千兆 Ethernet 是最终目标，但 B1 先隔离，B2 再按层引入。

## 3. Kernel 配置来源与流程

配置种子：
- 仓库：`ophub/kernel`
- 文件：`kernel-config/release/rk35xx/config-6.12`
- 来源 commit：`ba00be60d59300bd93633218a8905829d6cabd72`
- Git blob SHA：`dee127c6c644f38426eeb28000d73536084d34a3`
- 本仓库副本：`scripts/panther-x2-b1/kernel.config.seed`

生成流程：完整 seed → Linux 6.18.63 `olddefconfig` → 网络隔离 fragment → 再次 `olddefconfig` → 最终 .config 检查 → 构建 Image 与 modules → modules_install → 模块独立打包。禁止 Kernel 使用 `allnoconfig` 起步。

最终配置需正向证明 BLOCK/MMC/USB/文件系统/MODULES 保留，反向证明网络栈、Ethernet/GMAC/MDIO/PHY、无线和 Bluetooth 无 built-in/module 残留。

## 4. kobject_uevent 旧补丁

`0001-kobject-uevent-config-net-n.patch` 只保留为历史审计材料，不再应用。Linux 6.18.63 源码审计确认 `net/core/` 仍参与构建，`net/core/skbuff.c` 提供原始 `kfree_skb()` 释放路径。旧补丁在 skb 非空时提前返回而不释放，改变原有资源所有权语义。当前 B1 使用未修改的锁定上游源码；若未来 CI 出现真实错误，再根据日志和调用路径定点审计。

## 5. Panther X2 DTB 边界

从同一 6.18.63 commit 的原始 `rk3566-panther-x2.dts` 派生，不覆盖上游原文件。

禁用 GMAC1、MDIO1、RTL8211F PHY 和 Wi-Fi 专用 SDIO host `sdmmc1`；移除 Wi-Fi/BT 专用 power-sequence、pinctrl、GPIO、Bluetooth 子节点和 Wi-Fi LED。

保留 eMMC `sdhci`、TF/SD `sdmmc0`、USB host/PHY、UART1 通用功能、UART2、完整 aliases（ethernet0/mmc0/mmc1/mmc2 与继承串口 aliases）、Ethernet LED、GMAC 外部时钟及 PMIC/regulator/clock/reset/pinctrl/DMA/中断共享资源。

CI 必须同时验证“网络节点已禁用”和“存储/USB/通用 UART 仍启用”，不能只验证前者。

## 6. RAM initramfs 与 eMMC 安全

`/init` 只挂载 procfs/sysfs，输出 Kernel、设备型号、CPU、内存、cmdline、挂载表和 dmesg，随后进入 BusyBox ash。不自动挂载持久化文件系统、不主动写入存储、不自动加载模块。

**保留 MMC/block 意味着 Linux 可能枚举 eMMC、TF/SD 并进行设备识别或分区扫描。** 不自动挂载、不主动写入，不等于完全不访问 eMMC。因此 eMMC pre-Linux 安全门和逐次实机授权仍是启动测试前置条件。

## 7. B2 路线



| 子阶段 | 唯一目标 | 验收重点 |
|---|---|---|
| B2-1 | 恢复 NET/INET/NETDEVICES 最小网络核心，暂不启用 Panther GMAC | 网络核心初始化、loopback |
| B2-2 | 加入 STMMAC/Rockchip DWMAC 与必要 SoC 资源，GMAC DTB 仍 disabled | 驱动 probe、netdev 注册，不要求 link |
| B2-3 | 引入 MDIO/PHYLIB/RTL8211F 最小依赖并激活目标节点 | MDIO 扫描、PHY 发现、驱动绑定和寄存器访问 |
| B2-4 | 验证 RGMII、时钟方向/频率、TX/RX delay 和 PHY 协商 | 物理链路、1000 Mbps Full Duplex |
| B2-5 | 验证 MAC DMA 与真实数据收发 | TX/RX、ARP、ICMP、TCP/UDP、持续传输和稳定性 |

每轮只引入一个组件或不可再拆分的最小依赖闭包；通过后保存源码 commit、patch、最终 .config、DTS/DTB、Image、initramfs、SHA-256 和原始日志。不得将 GMAC probe 成功等同网络打通。Wi-Fi、Bluetooth 和 USB/PCIe 外接网卡永久排除。B2 属于项目 A 的分层功能验证，不是恢复项目 B 的历史故障根因调查。


## 8. 当前状态

已完成仓库文件：完整 seed、网络 fragment、配置验证脚本、DTB 派生脚本、/init、workflow 与旧补丁说明；权威路线、实施计划、决策记录和索引正在同步。

尚未验证：merge_config/olddefconfig 最终配置、Image/modules 编译、模块清单、DTB 派生与编译、BusyBox/initramfs/uInitrd/boot.scr、CI artifact、eMMC 安全门和 Panther X2 实机启动。

本次授权仅涉及 GitHub 独立分支；未运行 CI、未写 TF/eMMC、未操作设备。
