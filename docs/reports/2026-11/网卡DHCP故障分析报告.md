# Panther-X2 刷机镜像网卡 DHCP 故障分析报告

## 一、问题概述

| 项目 | 版本 A（正常） | 版本 B（故障） |
|---|---|---|
| 镜像 | Armbian_24.2.0_..._jammy_6.1.65_server | Armbian_26.11.0_..._noble_6.12.81_server |
| 内核 | 6.1.65-ophub | 6.12.81-rk35xx-ophub |
| 发行版 | Ubuntu 22.04 (jammy) | Ubuntu 24.04 (noble) |
| 目标板 | rk3566-panther-x2 | rk3566-panther-x2 |
| 现象 | 网卡正常，DHCP 正常 | 网卡拿不到 DHCP 地址 |

分析方法：解压两个 .img.gz 镜像 → 解析 GPT 分区表 → 用 pytsk3 读取 ext4 的 boot/rootfs 分区 → 对内核 config、设备树(DTB)、网络配置逐项做语义级 diff。

---

## 二、已排除的因素（两版等价或都正常）

1. **设备树 GMAC 硬件描述等价**：两个 DTB 里 `ethernet@fe010000` 节点都是 `rockchip,rk3568-gmac / snps,dwmac-4.20a`，`phy-mode="rgmii"`、`clock_in_out="input"`、`tx_delay=48(0x30)`、`rx_delay=16(0x10)`、PHY 复位 GPIO/时序、pinctrl 组（gmac1m0）全部一致。语义级对比后差异仅为 phandle 编号重排，非实质性差异。
2. **PHY / GMAC 驱动都在**：REALTEK_PHY、MOTORCOMM_PHY、PHYLIB、GENERIC_PHY、DWMAC_ROCKCHIP、STMMAC_ETH、CLK_RK3568 在 6.12 内核里全部为 `=y`，没有丢失驱动。
3. **启动参数一致**：armbianEnv.txt 的 fdtfile、`net.ifnames=0`、boot.cmd 完全相同。
4. **网络管理策略方向一致**：两版最终都由 NetworkManager + netplan(renderer: NetworkManager) 接管 DHCP，理念相同。

结论：**问题不是"驱动/设备树缺失"或"硬件配置写错"这类硬故障**，而是内核跨大版本升级 + 发行版升级带来的**软件栈行为变化**。

---

## 三、最可能的根因（按可能性排序）

### 根因 1（可能性最高）：内核 6.12 的 stmmac/dwmac-rk GMAC delay 处理逻辑变更，导致 RGMII 链路无法 up

这是 6.1 → 6.12 之间真实存在的内核变更：

- 2025-03 主线合入补丁 `net: stmmac: dwmac-rk: Use DELAY_ENABLE macro for RK3566/RK3568`（Jonas Karlman），改变了 RK3566/RK3568 GMAC 的 rx/tx delay 使能与 RGMII_ID/RXID/TXID 的联动方式。
- 6.12 内核 GMAC 配置新增 `CONFIG_STMMAC_FULL=y`、`CONFIG_STMMAC_ETHTOOL=y`，stmmac 驱动内部结构体、DMA/队列/PTP/XPCS 初始化路径大幅重构（新版 DTB 也相应新增了 `pclk_xpcs`、`clk_xpcs_eee` 时钟和 `uio@fe010000` 节点）。

旧镜像的 6.1.65 实际上是一个"opub 通用大内核"（armbian-release 里 BOARDFAMILY 竟然写着 meson-g12b/odroidn2，内核同时编入 DWMAC_MESON、MESON_GXL_PHY 等），对新板的适配是靠这套较老的 GMAC 逻辑工作的；换成 6.12 的 rk35xx 专用内核后，同一份 delay 数值在新驱动下可能不再让 PHY 正常 link up，表现为"网卡起不来 → 拿不到 DHCP"。

**典型症状**：`ip link` 显示网卡状态 `LOWERLAYERDOWN`/无 `RUNNING`，`dmesg | grep -i stmmac` 出现 `Link is Down` 或 PHY 初始化失败。

### 根因 2（次可能）：网络管理栈重构，DHCP 客户端在故障版上没有真正接管网卡

- 正常版：`networking.service`(ifupdown) 和 `NetworkManager.service` 都启用，NM 配置 `managed=true`，存在 `/etc/network/interfaces`（声明 lo），DHCP 路径成熟稳定。
- 故障版：**移除了 `networking.service`**，NM 改为 `managed=false`，删除了 `/etc/network/interfaces`，改为 netplan 的 `00-default-use-network-manager.yaml` 把设备全交给 NM，并且系统里新出现了 `dhcpcd.conf`（但 dhcpcd 服务未启用）。
- 如果 NM 因配置细节（如 netplan 生成的连接未覆盖该接口、`managed=false` 与 ifupdown 插件的边界）没有接管 eth0，则**根本没有任何 DHCP 客户端在跑**，自然拿不到地址。

**典型症状**：网卡 link 是 up 的（有 `RUNNING`），但 `ip addr` 只有 link-local 地址，没有 192.168.x.x；`systemctl status NetworkManager` 正常但 `nmcli dev status` 显示网卡 `unmanaged` 或无连接。

### 根因 3（可能性较低）：MAC 地址来源变化

两个 DTB 都没有写死 `local-mac-address`，MAC 由内核/uboot 环境提供。若新内核读取 MAC 的方式变化导致 MAC 无效或每次变化，部分 DHCP 服务器会拒绝分配。可用 `ip link` 对比两版 MAC 是否稳定。

---

## 四、在板子上验证的方法（建议按顺序执行）

分别在两块板（或同一板分别刷两个版本）上执行，对比输出：

```bash
# 1. 网卡是否被识别、名字叫什么、是否 link up
ip -br link
ip -br addr

# 2. 内核里 GMAC/PHY 驱动的探测日志（根因1的关键证据）
dmesg | grep -iE 'stmmac|gmac|phy|rgmii|eth' | head -80
# 重点看是否有 "Link is Down" / "PHY init failed" / "Could not attach to PHY"

# 3. 链路状态与速率
ethtool eth0            # 看 Link detected: yes/no, Speed, Duplex
ethtool -i eth0         # 看 driver 版本

# 4. DHCP 客户端与 NM 状态（根因2的关键证据）
systemctl status NetworkManager networking dhcpcd --no-pager
nmcli dev status
nmcli con show
journalctl -u NetworkManager --no-pager | tail -50

# 5. 手动发起一次 DHCP，观察是否能拿到地址
dhclient -v -d eth0     # 或: dhcpcd -d eth0

# 6. MAC 地址对比
cat /sys/class/net/eth0/address
```

判读：
- 若第 2/3 步显示 link down / PHY 失败 → **根因 1**，是 6.12 GMAC 驱动/delay 问题。
- 若 link up 但第 4 步显示 unmanaged 或服务没跑 → **根因 2**，是 DHCP 客户端没接管。
- 若手动 dhclient 能拿到地址 → 确认是根因 2（服务/配置层），不是硬件。

---

## 五、对应的修复方向

**针对根因 1（GMAC delay/驱动）：**
- 在 `/boot/armbianEnv.txt` 的 `overlays=` 里尝试加入或修改 GMAC 相关 overlay，调整 `tx_delay`/`rx_delay`（用 dtc 改 DTB 或用 overlay 覆盖）。
- 保留 6.1.65 的 DTB（`/boot/dtb*/rockchip/rk3566-panther-x2.dtb`）替换到 6.12 系统里试（两个 DTB 的 GMAC 节点等价，兼容性风险低）。
- 更换为对该板适配更成熟的 Armbian 版本/内核分支（如 edge/current 中已修复 delay 的版本）。

**针对根因 2（网络管理栈）：**
- 临时：`nmcli dev set eth0 managed yes` 后 `nmcli con add type ethernet con-name eth0 ifname eth0 ipv4.method auto`，或直接 `dhclient eth0` 验证。
- 永久：把 NetworkManager.conf 改回 `managed=true`，或在 `/etc/netplan/` 下显式声明 eth0 的 DHCP 配置，或恢复 `networking.service` + `/etc/network/interfaces` 的 ifupdown 方式（照搬 6.1.65 镜像的这几个文件）。

---

## 六、结论

- 两个镜像的**网卡硬件描述和驱动都完整**，不是设备树/驱动缺失导致的硬故障。
- 故障版（6.12.81）相比正常版（6.1.65）发生了两处关键变化：① 内核从老 ophub 通用内核换成 6.12 rk35xx 内核，GMAC(stmmac/dwmac-rk) 驱动逻辑重构、delay 处理变更；② 网络管理栈从 ifupdown+NM(managed=true) 重构为纯 NM(managed=false)+netplan。
- **最可能的直接原因是根因 1：6.12 内核 GMAC 驱动变更使 RGMII 链路无法 up（或根因 2：DHCP 客户端未接管网卡）。** 两者都可通过第四节的命令在几分钟内确诊。
- 由于是同一块硬件、6.1.65 正常，最快且稳妥的解决方案是：若确诊为驱动问题，回退/更换到适配该板的内核；若确诊为服务问题，照搬 6.1.65 的网络配置文件即可。
