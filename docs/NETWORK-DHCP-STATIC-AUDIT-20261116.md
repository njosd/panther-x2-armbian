# Panther X2 DHCP 故障静态审计（2026-11-16）

## 0. 范围与结论

本记录只使用已有历史排障结果、仓库构建脚本、固定版本源码/内核配置、Actions 日志及 2026-11-16 的 6.12.81 UART 分段日志；**没有要求用户重复实机测试，也没有修改设备、网络配置或内核**。

当前结论：

1. **6.12.81 的网络内核配置没有发现明显缺项。** `CONFIG_NET`、`CONFIG_INET`、`CONFIG_PACKET`、`CONFIG_STMMAC_ETH`、`CONFIG_DWMAC_ROCKCHIP`、`CONFIG_PHYLIB`、`CONFIG_REALTEK_PHY`、`CONFIG_MDIO_BUS`、`CONFIG_OF_MDIO`、`CONFIG_PHYLINK` 均启用。
2. **本次实机 GMAC/RTL8211F 已完成 probe 和千兆链路协商。** 当前 UART 报告 eth0、RTL8211F、RGMII、1Gbps/Full；DTS 中 TX/RX delay 与实机日志的 0x30/0x10 一致。没有证据支持“网卡驱动缺失”或“PHY 没起来”。
3. **历史 hEX 侧排障已经把重点指向 DHCP 报文未从 Panther X2 正常发出/到达 hEX**：其他客户端 DHCP 正常，Panther 对应 lease 为 waiting；同步抓包未见 Panther MAC 的 DHCP 报文。IPv6/L2 已有可用证据，不再重复排查网线、端口和 DHCP 服务。
4. **当前最需要确认的是最终 rootfs 中 NetworkManager 是否真正管理 eth0，以及 DHCP 客户端实际使用的配置/后端；根因尚未证实。** Armbian 的 Netplan 仅设置 renderer 是其有意设计（注释明确说明 carrier 出现后 NetworkManager 会自动 DHCP），不能仅因没有显式 eth0 stanza 就认定配置缺陷。既有构建验证确实有 shell 语法错误，尚未完成 rootfs 网络配置检查。

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

Armbian 上游该文件的注释明确写明：“Let NetworkManager manage all devices on this system. Any device will come up with DHCP, once carrier is detected.” 因此只有 renderer 的 Netplan 文件是上游预期设计，并不自动等于配置错误；NetworkManager 应对所有检测到 carrier 的接口创建/使用自动 DHCP 连接。真正要验证的是最终 rootfs 中有没有把 eth0 标记为 unmanaged、是否存在禁用自动默认连接的配置、是否有冲突网络管理器/遗留规则，以及 NM 的 DHCP backend 设置。

当前 workflow 的验证条件：
- 检查 Netplan 目录存在；
- 检查任意 YAML 文件中存在 `renderer: NetworkManager`；
- 检查任意 YAML 文件中存在 `dhcp4: true`。

最后一项与 Armbian 这个默认配置设计并不匹配：Netplan 不显式列出每个接口，而是将设备交给 NetworkManager，由 NM 在 carrier 出现后自动 DHCP。因此不能把 `dhcp4: true` 缺失作为故障证据。这个 grep 检查本身也不能证明 eth0 真的由 NM 管理。应改为对最终 rootfs 的 NM 配置、udev unmanaged 规则、NetworkManager service enablement、Netplan renderer 和冲突配置做静态检查。

### 4.2 现有 build run 的验证步骤实际上没有完成

build run：`43682186779`，job：`132714994034`。

该 run 的最终镜像已构建并上传 artifact（ID `14149202691`），但 validation step 在输出 boot/rootfs inventory 时，于 shell line 39 报：
```text
syntax error near unexpected token '('
```

脚本在打印 `KERNEL PACKAGE STATE` 后终止，**尚未执行后续的 NetworkManager service、Netplan、NetworkManager 配置文件、DHCPv4 profile 检查**。artifact 上传步骤仍执行，所以“artifact 已上传”不代表网络配置验证通过。

这是当前构建流水线中明确存在的验证缺口。已在诊断分支修正这段 find 检查，避免 shell 分组转义问题；同时移除了不符合 Armbian 默认策略的 dhcp4: true grep，改为检查 NetworkManager 配置目录是否存在。此修正只调整 CI 静态检查，不改变镜像内网络行为。不能把之前的构建成功或 artifact 上传误认为 DHCP 配置已经审查通过。

## 5. 当前故障判断（按证据强弱）

### 已排除或优先级显著降低

- DHCP Server 整体故障：hEX 对其他客户端正常。
- 网线/物理 link 未建立：本次 RTL8211F 1Gbps Full。
- 6.12.81 缺少基本 IPv4、AF_PACKET、STMMAC、Rockchip GMAC、Realtek PHY 内核配置：静态 config 均已启用。
- 设备树 PHY reset/delay 与实机日志明显不匹配：目前未发现这种差异。

### 当前重点

1. **NetworkManager 是否把 eth0 标记为 unmanaged，或没有为它启动自动默认连接。** 这比“缺少显式 Netplan eth0 stanza”更值得查。当前镜像用 Armbian 上游的全设备 renderer 设计，理应在 carrier 时自动 DHCP。
2. **最终 rootfs 是否存在影响 eth0 的全局/设备级配置。** 包括 `unmanaged-devices`、`no-auto-default`、udev NM unmanaged rules、Netplan 额外 yaml、cloud-init、ifupdown、systemd-networkd 残留，以及 DHCP backend 选择。
3. **内核 TX 路径差异暂列次级。** 对照 Ophub 6.1.y-rockchip `main` 与 6.12.81 源码快照时，Rockchip `dwmac-rk.c` 中 GMAC power-up/RGMII 配置函数保持一致；通用 `stmmac_xmit()` 有变化，6.12 新增针对 checksum-offload 不支持队列/非 IP EtherType 的软件 checksum fallback，并增加 EST max-SDU drop 判断。普通 DHCPv4 是 IPv4 流量，这些改动本身没有显示出必然丢弃 DHCP Discover 的路径；但 queue capability 与实际发送统计仍未验证。此源码比较不是严格的 6.1.116 release source 对 6.12.81 release source 的精确对比，不能据此排除内核回归。

## 6. 下一轮静态审计计划

不要求用户重复抓包、ping、nmcli 或 hEX DHCP 检查。已新增独立的只读 GitHub Actions 工作流：
`.github/workflows/audit-existing-6.12.81-network-rootfs.yml`

它按既有构建 run ID 下载已生成的镜像 artifact，在 runner 上只读挂载 rootfs，采集 Netplan、NetworkManager、udev、cloud-init、ifupdown、networkd 和 systemd enablement 信息，输出小型文本报告；不重建镜像、不写设备。工作流已提交但尚未运行；可在 GitHub Actions 中手动运行该 workflow，输入现有构建 run ID 43682186779。

下一步静态审计重点：
1. 从现有 6.12.81 镜像 rootfs 报告确认 NetworkManager 是否被启用、eth0 是否可能被标记 unmanaged、是否有 `no-auto-default` 或冲突配置。
2. 检查 NM 的 DHCP backend 与 Ubuntu Noble package defaults，结合既有旧版本 1.36.6 结果区分版本变化。
3. 取得 6.12.81 发布 DTB 的实际 SHA，与 6.1.116 已知工作 DTB 做二进制/反编译差异核对。
4. 若 rootfs 网络管理配置正常，再继续深挖 stmmac 的 TX checksum/descriptor 路径；目前不建议直接改 PHY delay 或重写 Netplan。

所有后续结论仍分为“已验证 / 未验证 / 推测”。不修改 hEX、不改 Panther X2 当前系统、不重刷 TF/eMMC。


## 7. 本轮进一步静态核对记录

### 7.1 修正 Armbian 网络策略判断

此前“没有显式 eth0 DHCP stanza”被列为疑点，这个表述需要收窄。固定 Armbian 源码的注释明确规定所有设备交由 NetworkManager 管理，并在 carrier 出现时自动 DHCP。因此缺少显式 Netplan eth0 stanza 本身不是故障证据。

已修正诊断分支中的构建验证：
- 删除可能触发 Bash 解析问题的括号式 find 表达式，拆成两个独立 find。
- 删除错误地强制要求 dhcp4: true 的检查（与 Armbian 全设备 NM renderer 策略不符）。
- 保留 NetworkManager 配置目录和 renderer 的基本检查。
- 这些只是 CI 验证脚本修订，不改变镜像或设备网络配置。

### 7.2 stmmac 发送路径源码对照（探索性）

比较对象：
- ophub/linux-6.1.y-rockchip 的 main 分支；
- ophub/linux-6.12.y-rockchip commit 661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

发现：
- Rockchip dwmac-rk.c 的 rk_gmac_powerup()（包括 RGMII interface switch 和 delay 调用）函数文本一致。
- 通用 stmmac_main.c 的 stmmac_xmit() 有变化。6.12 增加 EST max-SDU drop 检查，以及针对不支持 checksum offload 的 TX queue/非 IP EtherType 的软件 checksum fallback。
- stmmac_tx_map()、stmmac_tx_err()、stmmac_dma_interrupt()、stmmac_xmit_frags() 在抽取函数对照中一致；stmmac_tx_clean() 有 XSK metadata completion 等变化。
- DHCP Discover 是普通 IPv4/UDP 报文；新加的非 IP EtherType checksum fallback 不应针对它触发。EST max-SDU 是否会生效取决于设备是否启用了 EST/max_sdu，当前没有此项实机证据。
- 所以目前没有发现一个可以直接解释 DHCP Discover 完全未到 hEX 的明确 stmmac 改动。

**重要限制：** 6.1 main 并不等同于已知工作的精确 6.1.116 构建源码快照；这个对照只用于缩小方向，不是严格 release-to-release bisect。不能用它证明 6.12 驱动完全无回归。

### 7.3 当前最可能的待确认点

优先等待最终 rootfs 的离线报告，特别关注：
- /usr/lib/NetworkManager/conf.d/、/etc/NetworkManager/conf.d/ 是否有 unmanaged 规则；
- 是否存在 no-auto-default 或针对 eth0/MAC 的限制；
- NetworkManager 服务是否启用且实际读取 Netplan；
- 是否有 cloud-init、ifupdown、networkd 或 udev 规则冲突；
- NetworkManager DHCP backend 的默认选择。

在取得这些信息前，不应擅自给 Panther X2 加静态地址、重写 Netplan、改 PHY delay 或重编译 GMAC。


## 8. 原始 6.12.81 镜像 rootfs 离线审计（Actions run 43787544512）

已成功下载并只读挂载原始构建 run 43682186779 的 artifact；没有重建镜像或接触设备。审计报告 artifact：`14190734155`（`panther-x2-6.12.81-network-rootfs-audit`）。

### 8.1 实际镜像配置

包版本（从原始 rootfs dpkg 数据库读取）：
- `netplan-generator`：`1.1.2-8ubuntu1~24.04.3`
- `netplan.io`：`1.1.2-8ubuntu1~24.04.3`
- `network-manager`：`1.46.0-1ubuntu2.8`
- `systemd`：`255.4-1ubuntu8.18`

Netplan 文件只有：
```yaml
network:
  version: 2
  renderer: NetworkManager
```
这符合 Armbian 的全设备 NetworkManager 自动 DHCP 设计，并非缺少 DHCP 配置的证据。

NetworkManager 主配置：
```ini
[main]
plugins=ifupdown,keyfile

[ifupdown]
managed=false

[device]
wifi.scan-rand-mac-address=no
```
镜像中没有发现 `/etc/network/interfaces` 静态接口配置；`managed=false` 因而没有已知的 eth0 stanza 可排除。没有发现 `/etc/systemd/network` 中的 networkd 配置文件；`systemd-networkd.service` 为 disabled，传统 `networking.service` 不存在。NetworkManager.service 为 enabled。

udev 的 `85-nm-unmanaged.rules` 是发行版默认规则，仅排除 VirtualBox/VMware、非 eth 名称的 veth、USB gadget 等特殊设备；没有匹配 Panther X2 的普通 `eth0`。

### 8.2 发现的全局 unmanaged 规则及其 Netplan 机制

镜像包含 Ubuntu 的：
`/usr/lib/NetworkManager/conf.d/10-globally-managed-devices.conf`
内容：
```ini
[keyfile]
unmanaged-devices=*,except:type:wifi,except:type:gsm,except:type:cdma
```

单独看这条规则确实会把普通 Ethernet 排除在 NetworkManager 管理之外。但**不能据此判定它是故障根因**：Netplan 在使用全局 `renderer: NetworkManager` 时，会于早期启动生成一个空的：
`/run/NetworkManager/conf.d/10-globally-managed-devices.conf`
用来禁用上述 Ubuntu 默认限制。Netplan 的上游源码注释明确说明此目的。Ubuntu Noble manpage 也确认 Netplan renderer 在 early boot 读取 YAML 并向 `/run` 写入后端配置。

原始 rootfs 已确认安装 `netplan-generator`，且存在 systemd generator 入口：
`/usr/lib/systemd/system-generators/netplan -> ../../../libexec/netplan/generate`
NetworkManager 服务也已启用。

**尚未从离线 rootfs 直接证明**该 symlink 的目标文件存在且可执行、systemd 启动时确实执行了 generator，以及运行时空 override 成功生成。因此目前将此处标记为“有条件正常、待验证”，不是直接定罪。最新审计工作流进一步检查 generator 目标文件和 `/etc`/`/run` 的 mask override。

### 8.3 本轮排除项与剩余重点

目前静态审计没有发现：
- NetworkManager 服务未启用；
- systemd-networkd 与 NetworkManager 同时管理 eth0；
- ifupdown 的 eth0 配置与 NM 冲突；
- udev 规则明确把 Panther 的 eth0 标记 unmanaged；
- Netplan YAML renderer 指向错误后端。

剩余首要问题变为：
1. Netplan systemd generator 目标文件是否存在/可执行、启动时是否成功执行，是否生成 `/run/NetworkManager/conf.d/10-globally-managed-devices.conf` 空 override。
2. 若 Netplan/NM 运行时管理状态正常，则从 DHCPv4 客户端状态机与 stmmac TX 统计/描述符发送路径继续静态比对。历史 hEX 抓包未见 Panther DHCP 报文，优先定位 DHCP Discover 是否产生以及是否进入 GMAC TX，而不是再重复检查 DHCP server。
3. 继续精确寻找已知工作的 6.1.116 对应源码/配置快照；目前 6.1 `main` 对照不能替代精确版本比对。

本节依据的上游说明：
- Netplan Noble manpage：early boot renderer 读取 YAML 并写入 `/run` 后端配置。
- Netplan 上游 `src/configure.c`：全局使用 NetworkManager renderer 时写入空的 `/run/NetworkManager/conf.d/10-globally-managed-devices.conf`，以禁用 Ubuntu 限制 Ethernet 的默认规则。
