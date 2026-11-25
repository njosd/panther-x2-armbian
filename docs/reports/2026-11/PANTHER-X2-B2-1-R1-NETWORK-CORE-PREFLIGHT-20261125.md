# Panther X2 项目 A：B2-1 / R1 最小网络核心准备与验收（2026-11-25）

- 阶段：R1
- 基线：R0 PASS；6.18.63 B1 实际 artifact 已冻结
- 本轮目标：只引入 Linux 通用网络核心、Ethernet framing/core 和 AF_PACKET 原始帧 socket 支持，为后续最小 MAC TX 路径准备用户态帧注入接口
- 当前状态：**Run 45611898629 全部步骤成功；R1 配置、Kernel Image/modules、AF_PACKET 符号、模块隔离、DTB 与 artifact 上传均通过。R1 构建验收 PASS，尚待用户审阅放行 R2；未启用板载 GMAC/MDIO/PHY**
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
- [x] R1 Actions 配置收敛与禁止项门（Run 45606030640）
- [x] R1 Kernel Image/modules 编译（Run 45606030640）
- [x] R1 built-in AF_PACKET/network-core 符号及模块隔离初审（Run 45606030640）
- [x] R1 最终 artifact 哈希、DTB 原样复用与完整归档验收（Run 45611898629）
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


## 11. R1 配置基线修正（2026-11-25）

针对第二次 Actions 的 `CONFIG_MDIO_BUS=y` 失败，重新检查了工作流输入和冻结的 B1 artifact，发现原工作流虽然下载并校验了 R0 的最终 `.config`，却没有用它作为 R1 的配置合并基线；实际仍从原始 Ophub 6.12.81 seed + B1 fragment + R1 fragment 重新合并。这会重新引入已经在 B1 形成过程中处理过的历史配置状态，增加 Kconfig 隐式选择和旧选项复活的风险。

已修正工作流：
- R1 的 merge_config 输入改为冻结 artifact 中的 `work/b1-reference/output/kernel.config` + R1 fragment。
- B1 最终配置 SHA256 必须等于 `7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731`，且必须确认 `# CONFIG_NET is not set`，否则停止。
- 原始 Ophub seed 仍做来源哈希校验并作为审计材料保存，但不再作为 R1 的直接合并输入；B1 fragment 也保留归档，不再重复叠加。
- 最终仍执行 Linux 6.18.63 `olddefconfig`，以收敛后的 `.config` 作为唯一验收对象；禁止项检查和 B1/R1 config diff 保留。
- 功能分支工作流修正 commit：`928cb011bbe75a81ed4f27297b508f46d3030b93`。
- 默认分支 main 的 workflow_dispatch 注册副本同步 commit：`cf00e4f313d0f43f44e660462e17ec0c4eaa7b38`。


- 对 Linux 6.18.63 `drivers/net/ethernet/Kconfig` 的补充审计发现，通用 Ethernet 子树中还有不属于 `NET_VENDOR_*` 组、却会直接 `select PHYLIB` 的 `DNET`、`ETHOC`、`OA_TC6`。已在 R1 fragment 显式关闭这三项，并加入最终配置禁止检查，避免仅关闭 72 个厂商组仍遗漏通用驱动。
- 补充 fragment commit：`77c8fda3420775dcc55c216f7c1a894a7323ba8a`；补充 workflow gate commit：`87da2bfb1b48135bfc09ec30a4c4e65035b92a8d`。两份文件均已同步到 main（fragment commit `b081b723d5945be39ca6b490dc5c9bb79c1739b1`；workflow commit `dac40520a15650f7e97e9378d72df8cca59c3126`）。

这项修正尚未由新的 Actions 运行验证。下一次必须新建 workflow_dispatch，选择功能分支 `project-a/b2-1-r1-network-core-build`，输入仍为冻结的 R0 Run ID `45309219886`。不得对旧 Run 45598258364 使用 Re-run。新运行首先只审阅 merge/olddefconfig 日志、最终配置差异及全部禁止项；只有配置门通过后才允许进入 Kernel build。当前 R1 仍未 PASS，不得进入 R2。

## 12. 第三次 R1 Actions 运行结果与目录修复（Run 45606030640）

Job `139177002918`，head commit `e30e716c8b1da1cc44e4901b7f80ead9f2b8ae1c`。结论：**R1 配置门通过、内核与模块编译成功；最后的 DTB 产物审计因目标目录未创建而失败。R1 仍不 PASS。**

已审阅完整 job log 和 artifact `15019831642`：
- R0 frozen B1 config/DTB artifact 恢复及 SHA256 核验通过。
- R1 merge log 明确显示以 `work/b1-reference/output/kernel.config` 为基线，仅叠加 R1 fragment；没有重新合并旧 seed。
- `olddefconfig` 完成；最终配置门日志为 `R1 Kconfig gate checks: PASS`。
- 最终 `.config` 中 `CONFIG_NET=y`、`NETDEVICES=y`、`NET_CORE=y`、`ETHERNET=y`、`PACKET=y`；`MDIO_BUS)、`PHYLIB)、`DNET)、`ETHOC` 等禁用门通过。注意部分选项在最终 .config 中表现为 absent（该源码树中无该符号定义），不应误报为启用。
- Linux 6.18.63 Kernel Image 和 modules 均成功构建；AF_PACKET/network core 符号检查通过。
- 解包 modules.tar.zst 后检查，未发现 `drivers/net/{ethernet,phy,usb,wireless}` 或 Bluetooth 驱动模块路径。
- 失败只发生于 `cp work/b1-reference/output/dtb/rockchip/rk3566-panther-x2.dtb work/output/dtb/rockchip/...`：`work/output/dtb/rockchip` 目录未创建。并非 DTB 内容或哈希错误；失败前 DTB 复用检查尚未执行。

已修正：
- 在 DTB copy 前增加 `mkdir -p work/output/dtb/rockchip`。
- 功能分支修正 commit：`c1b0b608d4282d297fac51cbab3eb951972f9187`。
- main 注册副本同步 commit：`0b8e855e379f30e339f435b9ca2fcf1b8cefb062`。

下一轮必须新建 workflow_dispatch，选择功能分支 `project-a/b2-1-r1-network-core-build`，继续输入 R0 Run ID `45309219886`。不要重跑旧 Run 45606030640，因为旧 run 使用的 workflow commit 不含目录修复。新运行重点核验 DTB 原样复用、GMAC/MDIO/PHY 状态、哈希和完整 artifact 上传；然后再审阅 R1 最终状态。当前不得进入 R2，不访问设备、不写卡。


## 13. R1 产物复用与断点恢复流程（2026-11-25）

Run 45606030640 已经成功生成 Kernel Image、modules、最终 .config、System.map 和符号/配置审计材料；失败仅在最后 DTB 复制时因目标目录不存在而发生。该次 artifact（ID 15019831642，名称 `b2-1-r1-network-core`）必须作为既有构建成果复用，不再重新编译。

新增专用恢复工作流：
- 文件：`.github/workflows/resume-panther-x2-b2-1-r1-network-core.yml`
- 功能分支提交：`dbd05115463323aa8bd0b561c3c15fd6a2ee8b4e`
- main 注册副本提交：`01aef54f77689a994674b40081921d403fce9ce7`
- 默认输入 R1 Build Run ID：`45606030640`；B1 Reference Run ID：`45309219886`。
- 仅下载既有 R1 artifact 和冻结 B1 artifact；重新检查 R1 provenance、关键 .config 符号、已归档的 built-in 网络核心符号证据，并重新解包审计 modules.tar.zst。
- 从 B1 artifact 原样复制 Panther DTB，校验 B1 最终配置及 DTB SHA256，生成最终 R1 verification 文件并上传 `b2-1-r1-network-core-final`。
- 不 checkout 或下载 Linux 源码，不运行 merge_config/olddefconfig，不执行 Kernel Image 或 modules 编译，不访问设备、不写 TF/eMMC。
- 恢复工作流只对历史 artifact 做验收与补齐；若历史 artifact 缺少预期文件或 provenance 不匹配，会明确失败，不会回退到重编译。

工作流已同时提交到功能分支和 main。请从 Actions 选择 `resume-panther-x2-b2-1-r1-network-core.yml`，运行时选择功能分支 `project-a/b2-1-r1-network-core-build`，保持默认两个 Run ID。**当前只是流程已提交，尚未执行；R1 最终 PASS 仍以该恢复工作流成功及 artifact 审阅为准。** 不得提前进入 R2。


## 14. 第四次 R1 Actions 运行：完整构建验收通过（Run 45611898629）

用户提供 Job：`139197305317`。Run head commit：`5f0ee9b04f2ce7987cdd85170c8235ee29c8116f`。运行结论：`completed / success`；全部 11 个 job steps 均成功。

**重要流程说明：本次执行的是原始完整 R1 build workflow，不是第 13 节新增的 artifact-only resume workflow。** 完整日志确认本次重新 fetch pinned Linux source、重新 merge_config/olddefconfig，并重新编译 Kernel Image 与 modules。它是一次新的完整构建；不能把它记作“复用了 Run 45606030640 的 R1 编译产物”。但 R0/B1 冻结参考 artifact 被成功下载复用，DTB 也从该参考 artifact 原样复制。

通过证据：
- R0/B1 reference artifact 下载成功；下载 ZIP digest：`dd67ac049775898f3793fc6524d70437630eeb46d64bca8bc79b8b6ae038cee9`。
- 冻结 B1 最终 config SHA256：`7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731`；冻结 Panther DTB SHA256：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`。
- 固定源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`，Linux 6.18.63；已有 B1 compatibility patch 检查与应用成功。
- R1 最终 Kconfig gate 明确输出 `R1 Kconfig gate checks: PASS`；NET、NETDEVICES、NET_CORE、ETHERNET、PACKET 均要求为 y；workflow 对 INET/IPv6/NETFILTER、STMMAC/DWMAC、MDIO/PHY、DSA、DNET/ETHOC/OA_TC6、Wi-Fi/BT 和 R1 fragment 中全部 NET_VENDOR 组选项执行关闭检查。
- Kernel Image 文件识别为 ARM64 Linux kernel Image，little-endian、4K pages；构建步骤成功。
- `modules.tar.zst` 成功生成并解包；Ethernet/PHY/USB-network/Wireless/Bluetooth 驱动模块与对应 built-in 路径隔离检查成功。
- AF_PACKET/network-core 符号检查成功：`packet_create`、`packet_sendmsg`、`eth_type_trans`、`dev_queue_xmit`。
- DTB 成功复制，fdtget 读出 `model=Panther X2`、`gmac1_status=disabled`、`mdio_status=disabled`、`phy_status=disabled`；DTB SHA256 与冻结值一致。
- Image SHA256：`63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`。
- R1 kernel.config SHA256：`480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`。
- modules.tar.zst SHA256：`4f403cac59809616cf4de36a8e89520ecffc13965597be4b8d88845fb3ce3787`。
- DTB SHA256：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`。
- 完整 artifact：`b2-1-r1-network-core`，ID `15023630465`，大小 210,059,326 bytes，ZIP SHA256 `80bd2d33d0e85d8fd4c10fdd33a60c159393db3a45ae5f6e95dd0bf490cc656c`；保留至 2026-12-25。

### R1 结论

**R1 构建与 CI 级静态验收：PASS。** 本阶段目标是形成启用通用网络核心、Ethernet framing/core 和 AF_PACKET 的 6.18.63 内核，同时不引入板载 MAC/PHY、其他网卡、无线或蓝牙驱动；本次所有对应工作流门均成功。

边界仍然明确：
- 未恢复 Panther X2 GMAC1/MDIO/PHY 节点，未构建板载 MAC 驱动。
- 未在实机启动本次 R1 Image；未验证真实 Ethernet interface、PHY link 或线侧 TX。
- 不代表 TX 已经打通，不代表可以进入硬件 TX 阶段。
- 不访问设备、不写 TF/eMMC。

第 13 节 artifact-only resume workflow 是单独新增的断点验收入口，本次没有调用它。该流程的可运行性尚未由 Actions 实测；不影响本次完整构建 workflow 已经成功的结论。当前先由用户审阅 R1 结果，未授权前不自动启动 R2。
