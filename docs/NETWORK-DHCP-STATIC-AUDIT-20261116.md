# Panther X2 DHCP 故障静态审计（2026-11-16）

## 0. 范围与结论

本记录只使用已有历史排障结果、仓库构建脚本、固定版本源码/内核配置、Actions 日志及 2026-11-16 的 6.12.81 UART 分段日志；**没有要求用户重复实机测试，也没有修改设备、网络配置或内核**。

当前结论：

1. **6.12.81 的网络内核配置没有发现明显缺项。** `CONFIG_NET`、`CONFIG_INET`、`CONFIG_PACKET`、`CONFIG_STMMAC_ETH`、`CONFIG_DWMAC_ROCKCHIP`、`CONFIG_PHYLIB`、`CONFIG_REALTEK_PHY`、`CONFIG_MDIO_BUS`、`CONFIG_OF_MDIO`、`CONFIG_PHYLINK` 均启用。
2. **本次实机 GMAC/RTL8211F 已完成 probe 和千兆链路协商。** 当前 UART 报告 eth0、RTL8211F、RGMII、1Gbps/Full；DTS 中 TX/RX delay 与实机日志的 0x30/0x10 一致。没有证据支持“网卡驱动缺失”或“PHY 没起来”。
3. **历史 hEX 侧排障已经把重点指向 DHCP 报文未从 Panther X2 正常发出/到达 hEX**：其他客户端 DHCP 正常，Panther 对应 lease 为 waiting；同步抓包未见 Panther MAC 的 DHCP 报文。IPv6/L2 已有可用证据，不再重复排查网线、端口和 DHCP 服务。
4. **目前最值得优先审计的是镜像 rootfs 的 Netplan/NetworkManager 实际配置，以及内核版本差异；根因尚未证实。** 当前构建脚本没有明确生成 Panther X2 的 eth0 DHCP profile，而是依赖 Armbian/NetworkManager 的默认自动连接行为；既有构建验证还存在一个实际执行失败的问题。

## 1. 已有实机和历史证据

### 1.1 历史网络排障（此前会话）

- Panther X2 有线物理链路建立，IPv6/L2 有可用性证据。
- hEX DHCP Server 在 bridge 上能正常服务其他客户端。
- Panther X2 对应 DHCP lease 状态为 `waiting`。
- 与 hEX 同步抓包时，未看到 Panther MAC 的 DHCP 报文；抓包中其他客户端报文正常。
- 旧系统排查记录：NetworkManager 管理有线接口，IPv4 method 为 `auto`；DHCP transaction 启动后超时并报 `ip-config-unavailable`；ifupdown 仅配置 loopback；networking journal 没有接管接口的证据。
- 旧系统记录的 NetworkManager 版本为 1.36.6。该版本不能直接当作当前 6.12.81 Noble 镜像的版本。

### 1.2 2026-11-16 本次 6.12.81 UART

- `rk_gmac-dwmac fe010000.ethernet` 初始化。
- `PHY [stmmac-1:00] driver [RTL8211F Gigabit Ethernet]`。
- `phy/rgmii`，TX delay `0x30`，RX delay `0x10`。
- `Link is Up - 1Gbps/Full`。
- TF 根分区成功读写挂载，系统进入首次登录。
- 启动横幅等待 IP 后超时。

这证明 MAC/PHY 初始化和物理链路成立；它本身不证明 DHCP Discover 已经从 MAC 发出，也不证明 DHCP 收包路径正常。

## 2. 6.12.81 内核配置静态核对

配置来源：
- Ophub kernel config ref：`c23196e10d7702ee2906de4a05421d8971fb2717`
- 文件：`kernel-config/release/rk35xx/config-6.12`
- blob SHA：`dee127c6c644f38426eeb28000d73536084d34a3`

关键配置：

```text
CONFIG_NET=y
CONFIG_INET=y
CONFIG_PACKET=y
CONFIG_NETDEVICES=y
CONFIG_ETHERNET=y
CONFIG_STMMAC_ETH=y
CONFIG_STMMAC_PLATFORM=y
CONFIG_DWMAC_ROCKCHIP=y
CONFIG_PHYLINK=y
CONFIG_PHYLIB=y
CONFIG_REALTEK_PHY=y
CONFIG_MDIO_BUS=y
CONFIG_OF_MDIO=y
CONFIG_IP_PNP_DHCP=y
```

另一个对照：同一 Ophub kernel-config 快照中的 `config-6.1` 也启用了上述核心网络选项。因而目前没有发现 6.12.81 因关闭 AF_PACKET、INET、STMMAC 或 RTL PHY 支持而无法运行 DHCP 的证据。

注意：`CONFIG_IP_PNP_DHCP` 是内核 IP 自动配置相关选项，不是 NetworkManager DHCP 客户端的替代；真正有参考意义的是 `CONFIG_PACKET`、INET 和网卡/PHY 驱动配置。

## 3. Panther X2 GMAC / PHY 设备树静态核对

固定源码：
- Ophub Linux 6.12.y-rockchip commit：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- DTS：`arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`

GMAC1 节点要点：
- MAC：`fe010000.ethernet`。
- `phy-mode = "rgmii"`。
- `clock_in_out = "input"`，外部 125 MHz GMAC clock。
- `phy-supply = <&vcc_3v3>`。
- `snps,reset-gpio = <&gpio3 RK_PA1 GPIO_ACTIVE_LOW>`。
- `snps,reset-delays-us = <0 20000 100000>`。
- `tx_delay = <0x30>`、`rx_delay = <0x10>`。
- MDIO PHY 节点地址为 0。

当前 UART 报告的 RGMII、clock input、delay 值、RTL8211F PHY address 0 与该 DTS 相符。由于链路已经协商成功，设备树/PHY 上电复位不是当前首要嫌疑；但 link-up 不能替代 TX/RX 帧计数或 DHCP 帧验证。

### 3.1 6.1.116 已知工作版本的 DTB 参考

仓库已有 6.1.116 DTB 参考归档：
- `audit/6.1.116-reference-dtb` 分支；
- DTB：`rk3566-panther-x2-6.1.116.dtb`；
- 审计工作流：run `43722925635`。

该工作流记录的 DTB SHA-256 为 `5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`。该值与仓库既有 6.18.63 发布包 Panther X2 DTB SHA-256 相同，说明已知工作版本 6.1.116 的 DTB 与该 6.18.63 DTB 是同一二进制。

**限制：** 目前尚未从 6.12.81 发布包的审计 artifact 取出并核对 Panther X2 DTB 的最终 SHA-256。因此不能把 6.1.116/6.18.63 DTB 相同，直接扩大成“6.12.81 DTB 也逐字节相同”。不过 6.12.81 实机日志中的 GMAC 关键参数与 6.12.81 DTS 相符。

## 4. 当前镜像的网络栈构建逻辑

构建文件：
- `.github/workflows/build-panther-x2-minimal.yml`
- Armbian Build commit：`3f3849bf50bfadff94d0d488eb968bdaf970dc72`
- rootfs：Ubuntu Noble
- `BUILD_MINIMAL=no`、`BUILD_DESKTOP=no`
- base board：`odroidn2`，之后由 Ophub `rebuild -b panther-x2` 替换 Panther X2 内核/DTB/启动链。

Armbian 固定源码 `lib/functions/configuration/main-config.sh` 的默认规则是：
- `BUILD_MINIMAL=yes` → `systemd-networkd`；
- `BUILD_MINIMAL` 不是 yes（当前 workflow 明确设为 no）→ `network-manager`。

因此当前 6.12.81 镜像选择的是 **NetworkManager + Netplan**，不是 systemd-networkd。

当前 build log 实际安装版本：
- NetworkManager：`1.46.0-1ubuntu2.8`
- Netplan：`1.1.2-8ubuntu1~24.04.3`

所以此前 1.36.6 的 NetworkManager 诊断属于旧系统记录，不能直接当作本次 Noble 镜像的软件版本。

### 4.1 Armbian 上游默认网络配置

固定 Armbian commit 中的：
- `extensions/network/net-network-manager.sh` 会安装 NetworkManager、Netplan，启用 systemd-resolved，禁用 NetworkManager-wait-online，并复制默认 Netplan/NM 配置。
- `extensions/network/config-nm/netplan/00-default-use-network-manager.yaml` 的内容只有顶层 `renderer: NetworkManager`；它没有明确写出 Panther X2 的 `eth0`、`match` 和 `dhcp4: true`。
- 同一目录的 NetworkManager 配置主要是说明文件及 Wi-Fi 随机 MAC/省电设置，没有 Panther X2 有线专用 profile。

Armbian 上游该文件注释的设计预期是“设备检测到 carrier 后由 NetworkManager 自动 DHCP”。这是一种依赖 NM 自动默认连接的通用策略，不是对 Panther X2 eth0 的显式 DHCP 配置。

当前 workflow 的验证条件：
- 检查 Netplan 目录存在；
- 检查任意 YAML 文件中存在 `renderer: NetworkManager`；
- 检查任意 YAML 文件中存在 `dhcp4: true`。

这个 grep 条件没有验证 `dhcp4: true` 是否位于 Panther X2 的以太网接口 stanza，也没有验证接口匹配是否为当前 `eth0`。因此即使通过，也不足以证明正确的 eth0 DHCP profile 已生成。

### 4.2 现有 build run 的验证步骤实际上没有完成

build run：`43682186779`，job：`132714994034`。

该 run 的最终镜像已构建并上传 artifact（ID `14149202691`），但 validation step 在输出 boot/rootfs inventory 时，于 shell line 39 报：
```text
syntax error near unexpected token '('
```

脚本在打印 `KERNEL PACKAGE STATE` 后终止，**尚未执行后续的 NetworkManager service、Netplan、NetworkManager 配置文件、DHCPv4 profile 检查**。artifact 上传步骤仍执行，所以“artifact 已上传”不代表网络配置验证通过。

这是当前构建流水线中明确存在的验证缺口。后续必须先修复验证脚本，再以离线方式检查最终 rootfs；不能把之前的构建成功或 artifact 上传误认为 DHCP 配置已经审查通过。

## 5. 当前故障判断（按证据强弱）

### 已排除或优先级显著降低

- DHCP Server 整体故障：hEX 对其他客户端正常。
- 网线/物理 link 未建立：本次 RTL8211F 1Gbps Full。
- 6.12.81 缺少基本 IPv4、AF_PACKET、STMMAC、Rockchip GMAC、Realtek PHY 内核配置：静态 config 均已启用。
- 设备树 PHY reset/delay 与实机日志明显不匹配：目前未发现这种差异。

### 当前重点

1. **最终 rootfs 是否真正生成并启用了适用于 eth0 的 NetworkManager DHCP profile。** 当前构建源码依赖自动默认连接，现有 validation 没有严格验证接口级 profile。
2. **NetworkManager 对 eth0 的实际管理状态及 DHCP backend 行为。** 历史记录显示它开始 DHCP transaction 后超时，但没有在 hEX 抓包中看到 Panther DHCP 帧。当前 Noble 的 NM 是 1.46.0，不是旧系统的 1.36.6。
3. **若 rootfs 的显式 DHCP profile 与 NM 管理状态静态核验无误，再比较 6.1.116 与 6.1.174/6.12.81 的 stmmac TX 路径源码差异。** 目前没有证据足以把故障直接归咎于 RTL8211F、RGMII delay 或某一个内核提交。

## 6. 下一轮静态审计计划

不要求用户重复抓包、ping、nmcli 或 hEX DHCP 检查。先离线完成：

1. 修复 build workflow 的 shell syntax error，确保网络配置检查实际执行。
2. 对最终 rootfs 的 `/etc/netplan`、`/etc/NetworkManager`、`/usr/lib/NetworkManager/conf.d`、`/etc/systemd/network`、`/etc/network/interfaces` 做完整 inventory。
3. 检查 Netplan 合并后的配置是否对当前命名 `eth0` 明确启用 DHCPv4；检查 NM effective config 中是否存在 `unmanaged-devices` 限制及 Netplan 生成的覆盖配置。
4. 检查 rootfs 中是否存在来自 Odroid N2 base image 的遗留接口匹配规则。
5. 若发现缺少显式 eth0 DHCP profile，提出最小镜像构建修正，并在 CI 静态验证生成的 NM connection/profile；未经授权不写入设备。
6. 同时核对 6.12.81 实际发布 DTB SHA 与 6.1.116 已知工作 DTB SHA；再决定是否需要继续追查 GMAC 驱动源码差异。

所有后续结论仍分为“已验证 / 未验证 / 推测”。不修改 hEX、不改 Panther X2 当前系统、不重刷 TF/eMMC。
