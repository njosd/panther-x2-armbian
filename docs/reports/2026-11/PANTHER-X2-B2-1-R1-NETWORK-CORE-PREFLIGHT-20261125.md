# Panther X2 项目 A：B2-1 / R1 最小网络核心准备与验收（2026-11-25）

- 阶段：R1
- 基线：R0 PASS；6.18.63 B1 实际 artifact 已冻结
- 本轮目标：只引入 Linux 通用网络核心、Ethernet framing/core 和 AF_PACKET 原始帧 socket 支持，为后续最小 MAC TX 路径准备用户态帧注入接口
- 当前状态：**静态 Kconfig/Makefile 审计完成；R1 构建尚待 Actions 执行；未启用板载 GMAC/MDIO/PHY**
- 操作边界：不访问 Panther X2，不写 TF/eMMC，不修改运行系统，不恢复 GMAC DTB 节点

## 1. R0 已放行的基线身份

- Kernel/DTB 原始构建：Actions Run 45309219886，Artifact 14884706818
- PREPARE-ONLY 镜像组装：Actions Run 45328201244，Artifact 14890817693
- Kernel 源码：ophub/linux-6.18.y commit aee4e352a15d636cbc484f56819c6e59474dfd9f，Linux 6.18.63
- 实际 TF 镜像 expanded SHA256：26b35287d0f1b952d5cd97fc0e89763751d237e490f35bd5120c7ffb3bdc29eb
- 实际启动已到达 /init 和 BusyBox ash 交互 shell；B1 验收 PASS
- B1 最终配置为 # CONFIG_NET is not set；GMAC1/MDIO1/RTL8211F disabled；TF/eMMC/USB Host 和共享 SoC providers 保留
- R0 详细哈希、DTB、配置和实机证据见 PANTHER-X2-B2-1-R0-BASELINE-PREFLIGHT-20261125.md

## 2. 6.18.63 精确源码审计依据

源码 commit：aee4e352a15d636cbc484f56819c6e59474dfd9f。

本轮重新定位并核对：
- net/Kconfig：CONFIG_NET 是网络核心总门控；在 if NET 内 source net/packet/Kconfig；INET 是单独的 TCP/IP 高层门控。
- drivers/net/Kconfig：NETDEVICES depends on NET；NET_CORE 位于 if NETDEVICES 内，default y。
- drivers/net/ethernet/Kconfig：ETHERNET depends on NET，default y。
- net/packet/Kconfig：PACKET 是独立 tristate packet socket 选项，位于 if NET 内；R1 明确设为 y。
- net/packet/Makefile：CONFIG_PACKET -> af_packet.o。
- net/Makefile：网络核心目录 net/core 始终进入网络构建；CONFIG_PACKET -> net/packet/。
- drivers/net/Makefile：CONFIG_ETHERNET -> drivers/net/ethernet/。
- drivers/net/ethernet/stmicro/stmmac/Kconfig：STMMAC_ETH 需要 HAS_IOMEM、HAS_DMA、PTP_1588_CLOCK_OPTIONAL、ETHTOOL_NETLINK；R1 不启用它。
- STMMAC Makefile：CONFIG_STMMAC_ETH 才生成 stmmac.o；CONFIG_STMMAC_PLATFORM 生成 stmmac-platform.o；CONFIG_DWMAC_ROCKCHIP 生成 dwmac-rk.o。R1 必须保持三者关闭。

## 3. R1 最小配置闭包

本阶段仅允许引入以下用户选择项：
- CONFIG_NET=y
- CONFIG_NETDEVICES=y
- CONFIG_NET_CORE=y
- CONFIG_ETHERNET=y
- CONFIG_PACKET=y

允许 Kconfig 因上述选项自动选择/默认启用必要的通用基础符号，但必须在最终 .config delta 中逐项展示，不允许静默接受无关网络设备驱动、协议或无线功能。

明确禁止：
- CONFIG_INET / IPv4、IPv6、ARP 上层路径、ICMP、DHCP、DNS；
- STMMAC_ETH、STMMAC_PLATFORM、DWMAC_ROCKCHIP；
- MDIO_BUS、PHYLIB、REALTEK_PHY；
- Wi-Fi、WLAN、Bluetooth、无线协议；
- USB Ethernet、USB 网络 gadget、PCIe/USB 外接网卡；
- iproute2、tcpdump、ping、DHCP/DNS 客户端等工具。

说明：Ethernet framing/core 是通用二层网络支持，不等于启用板载 MAC 驱动。R1 不会产生 Panther X2 物理 Ethernet 接口，不能进行真实线侧 TX 验收。

## 4. R1 配置与构建验收

新增配置片段：scripts/panther-x2-b2-1/r1-network-core.fragment。

构建时必须使用冻结的 R0 B1 seed + B1 fragment + 本 R1 fragment，执行 6.18.63 olddefconfig；不以手写 fragment 代替最终 .config。

验收要求：
1. NET、NETDEVICES、NET_CORE、ETHERNET、PACKET 最终均为 y。
2. INET、IPV6、NETFILTER、STMMAC_ETH、STMMAC_PLATFORM、DWMAC_ROCKCHIP、MDIO_BUS、PHYLIB、REALTEK_PHY 均未启用。
3. Wi-Fi/BT 相关配置仍关闭。
4. 完整记录 B1 .config 与 R1 .config 的差异；除 R1 明确闭包及 Kconfig 自动选择项外，任何其他差异都需解释。
5. 核对 built-in 对象中包含 net/core 和 net/packet/af_packet.o；Ethernet framing/core 对象存在。
6. modules.tar.zst 中不得出现板载 GMAC/STMMAC/DWMAC、PHY 或其他 Ethernet 硬件驱动模块；发现任何意外网卡驱动即失败并停止。
7. 新 Kernel Image 构建成功，记录 Image、.config、modules、源码、补丁和工具链哈希。
8. DTB 必须原样复用 R0 B1 DTB，SHA256 必须仍为 7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d；确认 GMAC/MDIO/PHY 仍 disabled。
9. 本阶段只构建 Kernel/模块和验证配置，不打包写卡镜像，不执行设备操作。

R1 PASS 只代表通用网络核心与 AF_PACKET 编译闭包准备通过，不代表 Panther 有网卡设备，也不代表 TX 已经通。

## 5. 后续 TX 目标的技术连接

后续 R7 在 GMAC 硬件链和最小 MAC driver 逐步通过后，使用专用静态 C 程序通过 AF_PACKET/SOCK_RAW 发出 EtherType 0x88B5 广播帧。R1 的 PACKET=y 是提供该接口的必要准备条件之一。

TX-PASS 的决定性证据仍然是局域网另一终端逐帧捕获 Panther 发出的正确广播帧。R1 配置成功、af_packet.o 编译成功、驱动 probe 成功、PHY link up 或 TX counter 增长，都不能代替对端真实收帧。

## 6. 本阶段状态

- [x] R0 B1 artifact、配置、DTB 与实机 shell 基线已核验
- [x] 6.18.63 NET/NETDEVICES/ETHERNET/PACKET Kconfig 和 Makefile 静态路径已核对
- [x] R1 最小配置 fragment 已建立
- [ ] R1 Actions 配置收敛与差异审计
- [ ] R1 Kernel build
- [ ] R1 built-in/module 对象闭包审计
- [ ] R1 artifact 哈希与 DTB 原样复用核验
- [ ] 用户审阅 R1 构建结果后放行 R2

当前不得进入 R2，更不得恢复 GMAC/MDIO/PHY 节点。R1 构建通过后，仍需单独审阅结果和授权，再进入 R2。

## 7. R1 构建入口与复用策略

- 专用工作流：`.github/workflows/build-panther-x2-b2-1-r1-network-core.yml`
- 工作分支：`project-a/b2-1-r1-network-core-build`
- Actions 入口：`https://github.com/njosd/panther-x2-armbian/actions/workflows/build-panther-x2-b2-1-r1-network-core.yml`
- 默认输入 B1 Kernel/DTB Run ID：`45309219886`，只下载已冻结的 B1 artifact 作 .config/DTB 对照。
- 因 R1 的最终 .config 改变，必须重新编译 Kernel Image 和 modules；不得错误复用 B1 Image。
- Panther DTB 不变，直接从 R0 artifact 复用并强制校验原始 SHA256。
- 工作流只上传 R1 Kernel/配置/模块和审计证据；不制作 TF 镜像，不写卡，不访问设备。
- 工作流为 workflow_dispatch；最初工作流文件只提交在功能分支，GitHub 默认分支的 Actions 列表因此显示 This workflow does not exist。现已将同一工作流文件注册到默认分支 main（提交 fcae75d9db6e10b2ad59bd0fe3470bf53641def1），同时保留功能分支版本供选择构建。现在 workflow_dispatch 入口应可见；运行时仍需选择功能分支 project-a/b2-1-r1-network-core-build。工作流尚未运行，不代表构建或验收通过。

R1 构建完成后先审阅 config diff、对象符号、模块清单、Image 哈希和 DTB 哈希；不得自动放行 R2。

## 9. 首次 Actions 运行失败与修正（Run 45596384034）

用户提交的 Job：`139143446592`。结论：R1 尚未构建，失败发生在源码准备步骤，不是 Kconfig 或编译失败。

已从完整日志确认：
- R0 artifact 下载成功，artifact ID `14884706818`，下载 ZIP digest `dd67ac049775898f3793fc6524d70437630eeb46d64bca8bc79b8b6ae038cee9`。
- B1 .config SHA256 与冻结值一致：`7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731`。
- B1 DTB SHA256 与冻结值一致：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`。
- Linux 源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f` fetch/checkout 成功。
- 失败点：`git -C work/linux apply "$PATCH"` 会令 Git 在 `work/linux` 目录解释相对补丁路径；原脚本却把仓库根目录相对路径 `scripts/panther-x2-b1/patches/0001-broadcast-uevent-net-only-api.patch` 传给它，因此报 `No such file or directory`。文件本身确实存在于项目仓库根目录下，并非补丁缺失。
- 后续 config merge、Kernel build、对象审计均被跳过。上传的 335-byte artifact 只有空目录/元数据，不含可用构建产物。

修正：
- 工作流现在用 `$GITHUB_WORKSPACE/scripts/panther-x2-b1/patches/0001-broadcast-uevent-net-only-api.patch` 绝对路径传给 `git -C work/linux apply`。
- seed 文件也改为明确的 workspace 绝对路径，避免再次发生 cwd 歧义。
- 修正已提交功能分支，commit `dedb591b40bf76d30eb2cc4f36e0d49e4113f2b9`；同步到 main，commit `768e6748e40393fe5b03be78df04c93d37fabb54`。

重要：不能对 Run 45596384034 使用 Re-run failed jobs 来验证这个修复，因为重跑仍使用旧的 workflow commit。必须新建一次 workflow_dispatch，选择功能分支 `project-a/b2-1-r1-network-core-build`，输入仍为 R0 Run ID `45309219886`。这是从失败步骤修正后重新启动；R0 artifact 会复用，不会重跑 R0，也不会访问设备或写卡。

## 10. 第二次 Actions 运行与配置根因（Run 45598258364）

Job `139149992105` 的源码准备步骤已全部通过：
- R0 artifact 恢复及 .config/DTB 哈希核验 PASS；
- 6.18.63 固定 commit fetch/checkout PASS；
- B1 compatibility patch 检查和应用 PASS；
- 进入 B1 + R1 merge_config 与 olddefconfig。

失败发生在配置验收门：
`Forbidden CONFIG_MDIO_BUS enabled`，最终收敛配置为 `CONFIG_MDIO_BUS=y`。Kernel build 和对象审计均未执行。该次上传 artifact `15013982661` 只含配置/日志等审计文件，不含可用 Image 或 modules。

根因不是 R1 fragment 直接开启 MDIO，而是 B1 使用的广泛 Ophub seed 中仍保留多个网络设备选择项；B1 fragment 关闭网络总门控，但 seed 中的子系统选项仍在。R1 重新打开 `NETDEVICES` 与 `ETHERNET` 后，旧选择项重新参与 Kconfig：
- `CONFIG_PHYLINK=y` 会 select `PHYLIB`，而 PHYLIB select `MDIO_BUS`；
- `CONFIG_NET_DSA_REALTEK=m` 及 Realtek DSA 相关选项也留在 seed；
- `CONFIG_SHORTCUT_FE=y` 由 Qualcomm Ethernet vendor group 暴露，并 select `NF_CONNTRACK*`，与 R1 禁止 IPv4/NETFILTER 的目标发生 unmet dependency warning；
- 多个 `CONFIG_NET_VENDOR_*` 仍为 y，导致不必要的硬件驱动 Kconfig 子树重新可见。
因此只检查 STMMAC/PHYLIB/MDIO_BUS 几个目标符号不足以证明 R1 是最小网络闭包。

修正已提交到功能分支：
- R1 fragment commit：`e7cb1449a5c0fbe687e8c4f8167ec82efe64b659`。新增显式关闭 DSA、Shortcut FE、PHYLINK/PHYLIB、MDIO、netdevsim/failover/netconsole/netpoll，以及全部 72 个 `CONFIG_NET_VENDOR_*` 厂商组。
- workflow gate commit：`103d4e4b48c81d5a07a1b1f41145c286ae8bc251`，扩展禁止项检查。
- workflow vendor gate 修正 commit：`70583a2efa288ac2b5e5c685ded5df342d4e901a`，通过 fragment 中列出的 vendor 符号逐项检查最终 .config，防止厂商组选项悄然恢复。
- 当前 workflow 与 fragment 均已在功能分支更新；尚需同步 main 的 workflow 注册副本和主报告。

下次 R1 运行必须是新的 workflow_dispatch（不能重跑旧 run），继续引用同一个 R0 Run ID `45309219886`。重点观察 olddefconfig 警告、全部 72 个 vendor group、MDIO/PHY/DSA/Shortcut FE gates。只有配置门全部通过后才允许编译。即使编译通过，R1 仍不代表有物理 TX 能力。
