# Panther X2 项目 A：B2-0 黄金基线对照与组件恢复顺序

- 日期：2026-11-24
- 当前阶段：**B2-0**
- 目标：建立两条正常网络实机黄金基线（6.1.65、6.1.116）与 6.18.63 B1 干净启动基线的对照矩阵，确定 B2 网络组件恢复顺序。
- 本报告性质：历史实机证据整合 + 静态规划；不执行设备操作、不构建 B2 镜像、不修改 Kernel/DTB。

## 1. 关键结论：两条正常网络实机黄金基线

**6.1.65 与 6.1.116 都是在同一台 Panther X2 上实际运行过、且有线网络功能正常的正向黄金基线。不能把 6.1.65 降格为仅有静态镜像审计的参照。**

### 1.1 第一黄金基线：原版 Armbian 6.1.65（2026-11-24）

实机记录：[PANTHER-X2-6.1.65-ORIGINAL-TF-BOOT-ETHERNET-BASELINE-20261124.md](PANTHER-X2-6.1.65-ORIGINAL-TF-BOOT-ETHERNET-BASELINE-20261124.md)

启动环境：
- Panther X2 / RK3566，Linux `6.1.65-ophub`，Armbian-unofficial 24.2.0-trunk Jammy。
- 本次实际布局是 TF 卡 rootfs（`mmcblk0p2`）+ eMMC `/boot`（`mmcblk1p1`）的混合运行环境；不能称为 TF 完全独立启动，也不据此推断完整 BootROM/SPL/U-Boot 加载链。
- 运行时设备树 model 为 Panther X2，compatible 包含 `panther,x2`、`rockchip,rk3566`。

有线 Ethernet 实测：
- `eth0` UP / LOWER_UP，平台驱动 sysfs 绑定 `rk_gmac-dwmac`。
- PHY 驱动为 RTL8211F Gigabit Ethernet，PHY ID `0x001cc916`，地址 0。
- GMAC 节点 `fe010000.ethernet`，RGMII，TX delay `0x30`、RX delay `0x10`，clock input，PHY reset GPIO3_PA1 active-low，reset delays `0, 20000, 100000 us`。
- 链路 1000Mb/s Full Duplex，autoneg on，link detected yes。
- DHCP 成功获得 IPv4 地址及默认网关。
- ping hEX 网关：4/4 成功，0% 丢包。
- ping 外部 IPv4 `223.5.5.5`：4/4 成功，0% 丢包。
- `getent ahostsv4 www.baidu.com` 成功返回 IPv4 地址。
- 计数器快照 RX/TX errors、dropped、carrier、collisions 均为 0。

证据边界：
- **已实机验证**：原版系统启动、GMAC 平台驱动绑定、RTL8211F 识别、RGMII、千兆全双工、DHCP IPv4、网关 ICMP、外部 IPv4 ICMP、DNS 名称解析。
- **未验证**：IPv6 端到端、吞吐/压力/长期稳定性、TCP/UDP 独立双向 payload 验收。
- 以上结论只适用于本次 6.1.65 混合启动环境，不代表 B1/B2 或 6.18.63 已通过。

### 1.2 第二黄金基线：Linux 6.1.116（2026-11-16）

实机和采集归档：
- [6.1.116 USB + Ethernet 正常运行基线](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [网络与启动链阶段测试总记录](PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)
- 完整脱敏采集归档：`evidence/hardware/panther-usb-audit-6.1.116-20261116-142425-complete-with-boot-config.tar.gz`

实机结果：
- `eth0` / `fe010000.ethernet`，平台驱动 `rk_gmac-dwmac)，PHY RTL8211F，PHY ID `0x001cc916)，RGMII。
- 链路在初期 100Mbps downshift 后，经延迟复测和更换网线恢复为 1000Mb/s Full Duplex；EEE 最终 disabled。
- DHCP 获得 LAN IPv4 和默认路由。
- 用户确认 ping hEX 网关和 iMac 均为 0% 丢包；RX/TX errors、dropped、carrier errors 为 0。该部分为用户确认的历史测试结果，原始终端计数器输出未完整归档。
- 不要求用户重做已完成的 DHCP/网关/iMac 基础验证。

证据边界：
- **已实机验证/用户确认**：驱动与 PHY 识别、最终千兆全双工、DHCP IPv4、LAN 网关和 iMac IPv4 连通。
- **未完整留存**：与其他轮次完全同条件的 DHCP 双端抓包、所有硬件 MAC 计数器原始输出。
- **未由现有证据证明**：TCP/UDP 双向 payload 独立验收、长时间压力稳定性。

### 1.3 第三条基线：Linux 6.18.63 B1（2026-11-24）

实机自动启动证据：
- Actions Run: https://github.com/njosd/panther-x2-armbian/actions/runs/45328201244
- Artifact ID：`14890817693`
- 解压镜像 SHA-256：`26b35287d0f1b952d5cd97fc0e89763751d237e490f35bd5120c7ffb3bdc29eb`
- Kernel source commit：`aee4e352a15d636cbc484f56819c6e59474dfd9`

已实机验证：
- 现有 eMMC SPL → TF 上 JP-TvBox U-Boot proper；
- 自动执行 boot.scr，从 TF 加载 Image/uInitrd/Panther X2 DTB；
- Linux 6.18.63、Panther X2 machine model、4 CPU online；
- initramfs 解包，执行 `/init`，进入 BusyBox 1.37.0 ash；
- 根文件系统位于 RAM，没有挂载持久化文件系统。

边界：
- B1 的 `CONFIG_NET=n`，Ethernet/STMMAC/DWMAC、MDIO/PHY 驱动和 GMAC/MDIO/PHY DT 节点均被隔离。
- B1 通过只证明干净 RAM 启动基线成立，不证明网络协议栈、网卡驱动、PHY/link 或网络通信正常。
- `/init` 中 `[` applet/设备树型号显示问题、MMC deferred-probe PMIC 依赖静态审计，作为下次打包非阻断待办，不阻止转入 B2-0。

## 2. 三条基线对照矩阵

| 比较维度 | 6.1.65 原版系统 | 6.1.116 正常系统 | 6.18.63 B1 |
|---|---|---|---|
| 证据类型 | 实机网络完整基础功能 + 原始镜像静态审计 | 实机网络正向验证 + 脱敏采集归档 | CI artifact + 自动启动实机 UART |
| 运行环境 | TF rootfs + eMMC /boot | eMMC 启动的已安装系统记录 | eMMC SPL + TF JP proper + TF Linux 资产，RAM initramfs |
| 网络栈 | 正常工作 | 正常工作 | `CONFIG_NET=n`，隔离 |
| MAC 平台驱动 | `rk_gmac-dwmac` | `rk_gmac-dwmac` | 未编入/不 probe |
| PHY | RTL8211F，ID `0x001cc916` | RTL8211F，ID `0x001cc916` | 未 probe |
| DTB GMAC | fe010000，RGMII，TX/RX delay 0x30/0x10，clock input | 与 6.1.65 GMAC 语义高度一致 | GMAC1/MDIO1/PHY disabled |
| 链路 | 1000Mb/s Full | 最终 1000Mb/s Full | 无网络链路 |
| DHCP IPv4 | 成功 | 成功 | 不适用/未测试 |
| LAN 网关 ICMP | 成功，0% loss | 成功，0% loss（用户确认） | 未测试 |
| 外部 IPv4 ICMP | 成功，0% loss | 现有记录未形成与 6.1.65 同等级的外部 IP 结果 | 未测试 |
| DNS | `getent` 解析成功 | 未完整归档 | 未测试 |
| TCP/UDP 双向 payload | 未验证 | 未验证 | 未测试 |

## 3. 两条正常黄金基线的共同板级配置

参照文件：[6.1.65 / 6.1.116 GMAC DTB 交叉核对](PANTHER-X2-GOLDEN-DTB-CROSSCHECK-6.1.65-6.1.116-20261120.md)，并结合 6.1.65 本次运行时 FDT 采集：

| 项目 | 正常黄金基线共同配置 | 证据 |
|---|---|---|
| GMAC | `fe010000.ethernet` | 6.1.65 runtime FDT + 6.1.116 runtime FDT |
| compatible | `rockchip,rk3568-gmac`, `snps,dwmac-4.20a` | 两条线的设备树语义对照 |
| PHY | RTL8211F，MDIO 地址 0 | 两次实机识别 |
| PHY ID | `0x001cc916` | 两次实机 |
| phy-mode | `rgmii` | 两条 runtime FDT |
| clock_in_out | `input` | 6.1.65 FDT 与 6.1.116 FDT/log |
| TX/RX delay | `0x30 / 0x10` | 两条基线 |
| Pinctrl | GMAC1 M0 六组 pin groups | 6.1.65 DTB 与 6.1.116 源码/运行时引用交叉核对 |
| 外部时钟 | gmac1_clkin 125 MHz 设计 | 静态 DTB/源码对照；频率行为证据依各自采集边界 |
| PHY reset | GPIO3_PA1 active-low | 6.1.65 runtime FDT + 6.1.116 DTS |
| reset delays | `0, 20000, 100000 us` | 6.1.65 runtime FDT + 6.1.116 DTS |
| PHY supply | `vcc_3v3` | 两条板级 DTS/DTB |

说明：共同字段是可用于 6.18 B2 的黄金配置参照，不等于 6.18.63 运行行为已验证；也不等于两份 DTB 二进制完全相同。

## 4. B2-0 组件恢复顺序

以下为待执行顺序。每阶段都先审计 Linux 6.18.63 精确源码 commit 的 Kconfig、Makefile、probe 和 DTB 依赖，按最小依赖闭包构建；不得按组件名称猜测依赖。

| 顺序 | 阶段 | 恢复内容 | 暂不引入 | 验收 |
|---|---|---|---|---|
| 0 | **B2-0** | 三基线矩阵、Kconfig/Makefile 依赖图、DTB/共享资源引用图、试验卡 | 不改配置、不构建、不启动网络 | 证据与顺序审计完成 |
| 1 | B2-1 | 最小网络核心、loopback、必要 IPv4/ARP/ICMP 协议能力 | 物理 Ethernet/GMAC/MDIO/PHY | 网络栈构建，loopback 本机验证 |
| 2 | B2-2 | netdev/Ethernet 框架、STMMAC core/platform、Rockchip DWMAC 驱动闭包 | GMAC DT 节点仍 disabled | 编译/链接通过；不声称硬件 probe |
| 3 | B2-3 | GMAC1、MDIO1、PHYLIB/PHYLINK、RTL8211F 及必要闭包 | 无关无线/蓝牙和外接网卡 | MAC/MDIO/PHY probe/绑定状态 |
| 4 | B2-4 | pinctrl、clock、reset、regulator、DMA、IRQ 与 RGMII 连接 | 不同时改无关 SoC/存储/USB配置 | PHY attach、carrier、1000Mb/s Full |
| 5 | B2-5 | 最小接口查询/启用工具、静态 IPv4、直连路由、ARP、同网段 ICMP、网关 ICMP | DHCP/DNS/SSH/NetworkManager | 双端抓包及接口计数器证明 TX/RX、ARP、ICMP |
| 6 | B3 | TCP 与 UDP 分开验证 | 不将 ping 视为传输层验收 | 双向 payload 与对端抓包 |

注：若 Kconfig/源码依赖表明某些选项无法拆分，则把经过证据支持的最小依赖闭包作为单次变量，并在试验卡中解释，不强行人为拆分。

## 5. B2-0 必须完成的静态审计

1. 锁定 6.18.63 源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9`，核对网络核心、IPv4/ARP/ICMP、netdev、STMMAC、Rockchip DWMAC、MDIO、PHYLIB/PHYLINK、Realtek PHY 的 Kconfig 依赖、select/imply 和 Makefile 对象。
2. 形成 Kconfig 符号 → 源码对象 → built-in/module → DTB 节点 → 运行时验收点的追踪矩阵。
3. 核对 GMAC1 `fe010000`、MDIO1、RTL8211F PHY、M0 pinctrl、clock parent、fixed 125 MHz、reset GPIO/delays、`phy-supply`、DMA/IRQ 及共享 regulator/PMIC 依赖。
4. 比较 B1 clean DTB 与原始 Panther X2 DTS 的网络节点差异；不因隔离 GMAC 而禁用其共享 SoC 基础设施。
5. 为 B2-1 写单项试验卡：精确 config diff、构建输入、预期 loopback 行为、验证命令、日志证据、停止条件、回退点。
6. 明确用户空间工具的最小需求；DHCP、DNS、SSH 不作为早期静态连通测试前置。

## 6. 统一验收与安全纪律

- 两条黄金基线已有的通用 DHCP/网关连通测试不要求用户重复执行；B2 的新验证只证明 6.18.63 逐层恢复后是否复现这些能力。
- 驱动构建成功 ≠ probe 成功；probe 成功 ≠ PHY link 成功；carrier/千兆协商 ≠ 双向数据成功。
- 先静态审计，再 CI 构建，再 artifact 审查，再通过独立安全门和用户逐次授权后实机验证。
- 不改 hEX、LAN 主机或现有系统服务；不写 eMMC；写 TF/启动实验镜像需单独安全审查和明确授权。
- 不恢复 GMAC 根因专项排障，不制作未经证据支持的补丁。
- Wi-Fi/无线、蓝牙及其所有组件永久排除；USB/PCIe 外接网卡排除。

## 7. B2-0 完成/放行条件

以下全部完成才放行 B2-1：
- [x] 6.1.65 正常网络实机基线已纳入（DHCP、网关、外部 IPv4、DNS、千兆链路）。
- [x] 6.1.116 正常网络实机基线已纳入（DHCP、LAN 网关/iMac 连通、千兆链路）。
- [x] 6.18.63 B1 自动启动实机基线已纳入，并明确其网络隔离边界。
- [x] 两条黄金基线共同 GMAC/PHY/DTB 配置已列入对照。
- [ ] 6.18.63 精确源码的 Kconfig/Makefile 最小依赖闭包审计完成。
- [ ] B1 clean DTB 与原始 DTS 的 Ethernet 节点/共享资源差异审计完成。
- [ ] B2-1 单变量试验卡完成并审查。
- [ ] 总路线图、实施计划、报告索引完成同步。

**当前状态：B2-0 已建立黄金基线矩阵和恢复顺序；源码依赖审计仍待完成。不得将 B2-0 标记为全部完成，不得提前放行 B2-1。**

## 8. 相关报告

- [6.1.65 原版 TF 启动 Ethernet 实机基线](PANTHER-X2-6.1.65-ORIGINAL-TF-BOOT-ETHERNET-BASELINE-20261124.md)
- [6.1.65 原始镜像静态审计](PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md)
- [6.1.116 Ethernet 正常基线](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [6.1.116 网络与启动链测试记录](PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)
- [6.1.65/6.1.116 GMAC DTB 交叉核对](PANTHER-X2-GOLDEN-DTB-CROSSCHECK-6.1.65-6.1.116-20261120.md)
- [B1 自动启动实机验证](https://github.com/njosd/panther-x2-armbian/actions/runs/45328201244)

## 9. 变更记录

- 2026-11-24：建立 B2-0 对照矩阵；明确 6.1.65 与 6.1.116 均为正常网络实机黄金基线，6.18.63 B1 为网络隔离启动基线；列出 B2-1 至 B2-5 的组件恢复顺序及 B2-0 放行条件。
