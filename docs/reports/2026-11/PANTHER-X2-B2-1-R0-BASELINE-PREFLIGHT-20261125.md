# Panther X2 项目 A：B2-1 / R0 基线资产与 TX 前置核查记录（2026-11-25）

- 阶段：B2-1 / R0
- 本轮性质：只读仓库、Actions 日志与既有报告核查
- 状态：**R0 通过（2026-11-25 复核）；B1 有一条非致命 init 脚本 applet 提示，留档**
- 目标：锁定实际 B1 资产及其源码输入，避免后续网络组件引入建立在错误基线上
- 本轮未访问 Panther X2；未构建新 Kernel；未修改配置、驱动、DTB、网络服务；未写 TF/eMMC；未进行网络测试

## 1. 本轮确认的固定技术目标

- 目标内核：Linux 6.18.63
- 源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 最终第一项网络实测：最小 Ethernet TX 路径发送自定义 EtherType 广播帧，由局域网对端真实捕获
- 首轮 TX 不依赖 IPv4、ARP、ICMP、DHCP、DNS 或路由
- 后续组件按单项/最小不可拆分依赖闭包逐个加入；TX 未通过不得加入更高层协议
- Wi-Fi、蓝牙及 USB/PCIe 外接网卡继续排除

## 2. B1 Actions 资产来源核对

### 2.1 Kernel/DTB 原始构建运行

运行：[`45309219886`](https://github.com/njosd/panther-x2-armbian/actions/runs/45309219886)

- 分支：`architecture/b1-full-base-network-isolation`
- head commit：`73357b32a8639c641ec7c18f733f7a6bab08b164`
- Kernel/DTB job：`138160466731`，结论 success
- Kernel/DTB artifact：`b1-kernel-dtb`
- Artifact ID：`14884706818`
- Artifact ZIP digest：`dd67ac049775898f3793fc6524d70437630eeb46d64bca8bc79b8b6ae038cee9`
- 日志明确记录 Kernel 版本 6.18.63、源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`，并成功生成 Image 与 Panther DTB。
- 该运行的 DTB 派生脚本 blob：`441594df0074a891d6826a208546f37568c54f84`。

### 2.2 后续 BusyBox 与 PREPARE-ONLY 打包运行

运行：[`45328201244`](https://github.com/njosd/panther-x2-armbian/actions/runs/45328201244)

- 分支：`architecture/b1-full-base-network-isolation`
- head commit：`c3b4a8061d28f20c0a2f83bb962b010bd8f27467`
- BusyBox job：`138222782935`，结论 success
- Kernel/DTB job：skipped；明确执行“Reuse kernel and DTB from a previous successful run”
- 被复用的 Kernel/DTB artifact ID：`14884706818`，即运行 `45309219886` 的产物
- PREPARE-ONLY 打包 job：`138224714144`，结论 success
- 最终镜像 artifact ID：`14890817693`
- 最终镜像 artifact ZIP digest：`9274e557ea5b62b6c2fc086d5aa3fd9a502215ff0070870ae36a9d6dfcfd4b9c`
- BusyBox artifact ID：`14890941927`，ZIP digest：`d867f7895d736fdc364f2dd5726df251238ed0b79d009519b106935ff9bffacc`

**关键限制：** `45328201244` 是成功的 BusyBox/镜像组装运行，不是新的 Kernel/DTB 构建运行。其打包日志对复用 Kernel/DTB 的 toolchain metadata 标注为 `not-recorded-in-reused-artifact`。在读取并核验原始 artifact 内的 manifest、config、Image/DTB 哈希及工具链记录之前，不得把“最终镜像打包成功”升级为“所有 Kernel 输入元数据已闭环”。

## 3. B1 源码版本漂移与资产绑定问题

只读比较发现，不能把当前 main 分支上的 B1 文件直接当成上述运行的构建输入：

| 文件 | Actions 构建使用的 ref | 当前 main | 影响 |
|---|---|---|---|
| `prepare-clean-dtb.py` | `c3b4a806...` 对应 blob `441594df...` | blob `43916420...` | DTB 派生逻辑不同；当前 main 版本禁用 MMC/USB 节点，而历史运行版本保留这些非目标硬件资源 |
| `kernel.config.fragment` | `c3b4a806...` 对应 blob `e5bde40...` | 当前 main blob `2feca8dc...` | 历史版本为正常 RK35xx 基础配置并隔离网络；当前 main 已改为 allnoconfig/纯 RAM 配置，不能互相替代 |
| `verify-b1-config.sh` | `c3b4a806...` 对应 blob `831718b9...` | 当前 main blob `6e92310d...` | 验收范围和参数接口不同，不能用当前脚本结果反证历史 artifact |

Actions 日志还记录历史运行使用的 DTB 派生结果保留 eMMC、TF/SD、USB、UART1/2、Ethernet LED 与共享资源；GMAC/MDIO 是网络隔离目标。此边界与项目后来确认的 B1“保留非目标基础硬件、只隔离板载网络及无线/蓝牙变量”的意图一致。

**处理原则：** 后续以已实际构建并用于实机测试的 artifact 及其精确 commit/blob 为 B1 基线。当前 main 的 B1 文件漂移先登记，不在本轮擅自回写或重构 B1 文件；在 R0 结项前，必须明确未来 B2 构建应从哪一个受控分支/commit 继承，以及是否需要将必要修订单独合并。

## 4. B1 实机验收边界

已有用户提供的实机记录证明 6.18.63 Kernel 已进入启动阶段并输出 Panther X2 / ARM64 Kernel 信息。当前可见证据尚不足以确认 `/init` 已成功执行并进入可交互 BusyBox ash shell。

因此：
- Kernel banner ≠ B1 完整通过；
- PREPARE-ONLY artifact 成功 ≠ Panther X2 实机启动通过；
- 未取得可交互 shell、`/init` 完成及必要基线状态证据前，不放行 R1 网络组件引入或任何网络硬件启用。

## 5. 已有 6.18.63 网络依赖审计的复用结论

复用 `PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md`，不重复从头审计：

- 最小 TX 发送用户态注入路径拟采用 `AF_PACKET/SOCK_RAW`，需核对 `CONFIG_PACKET`。
- 最小网络核心需按精确 Kconfig 依赖闭包核验 `NET`、`NETDEVICES`、Ethernet framing/core、`PACKET`。
- 首轮不启用 `INET`/IPv4；IPv4 留到 TX-PASS 后。
- 6.18.63 的 `STMMAC_ETH` 有 `ETHTOOL_NETLINK` 等 Kconfig 门槛；STMMAC、platform wrapper、Rockchip glue 的对象映射已有报告。
- `REALTEK_PHY` 需显式核对；PHY supply 依赖 RK809 PMIC/I2C/regulator provider，不能假定 DWMAC 自动闭合。
- Panther GMAC1 使用 RGMII、外接 RTL8211F、MDIO address 0；XPCS 被 Kconfig 纳入编译闭包不等于 Panther 使用 PCS 数据路径。
- B1 已有 provider 必须以实际最终 `.config` 和 built-in 对象清单为准，不能只凭 fragment 推定。尤其 `GPIO_ROCKCHIP`、`MFD_SYSCON` 仍需核对。

方向三、方向四、方向五已结项的源码审计成果继续复用；不重复旧版本 GMAC TX、DMA、clock、PHY 专题，不恢复 Project B 设备根因调查。

## 6. R0 当前验收表

| 项目 | 当前结论 | 状态 |
|---|---|---|
| 6.18.63 源码 commit | Actions 日志已明确记录 | 已验证 |
| Kernel/DTB 构建 | Run 45309219886 成功 | 已验证 |
| 最终 PREPARE-ONLY 镜像 | Run 45328201244 组装成功 | 已验证 |
| Kernel/DTB artifact 来源 | 453282 复用 453092 artifact，链路已追溯 | 已验证 |
| 复用 artifact 内全部输入/哈希/工具链元数据 | 尚未完成逐文件核验 | 未完成 |
| B1 DTB 派生逻辑与当前 main 一致 | 不一致，需明确受控基线 | 不通过 |
| B1 最终 .config 与 built-in 对象清单 | 尚未完成对实际 artifact 的逐项核验 | 未完成 |
| Panther X2 `/init` 与 ash 交互 shell | 现有证据不足 | 未通过 |
| B1 网络隔离及非目标硬件保留状态 | 需按实际 artifact DTB/config 核验 | 未完成 |

**2026-11-25 追加证据后，R0 结论更新为 PASS。** Artifact 身份、最终配置、DTB 隔离边界、镜像哈希以及 /init/BusyBox ash 实机验收现已闭环。/init 第 18 行出现的 [: not found 是 init 脚本 applet 提示；脚本继续执行并进入交互 shell，不影响 B1 启动及网络隔离验收。不为此重建 B1 或改写当前基线。

## 7. 下一步严格顺序

1. 只读提取并审查 artifact `14884706818` 与 `14890817693` 内的 manifest、最终 `.config`、Image、DTB、initramfs、boot script 和 SHA256；核对 toolchain metadata 缺口。
2. 锁定实际用于当前 TF 实测的 Image/DTB/uInitrd/bootargs 哈希与其来源，确认与上述 artifact 的对应关系；不得写入 eMMC。
3. 补齐 B1 `/init` / ash 交互 shell 实机验收。此项需要用户另行授权的设备启动/只读观察；本报告不授权。
4. R0 通过后，进入 R1：只引入最小 `NET` / Ethernet core / `PACKET` 依赖，不启用 STMMAC、DWMAC4、Rockchip glue、MDIO、PHY，不恢复 GMAC/MDIO DTB 节点。
5. R1 配置/构建验收通过后，才逐项进入 R2/R3/R4/R5/R6。各阶段仍保持 GMAC/MDIO/PHY DTB disabled，直到 R7 单独启用。
6. R7 首次真实网络测试仅发送 0x88B5 自定义 Ethernet 广播帧，由对端逐帧捕获；TX-PASS 前不加入 RX 上层、ARP、IPv4、ICMP、DHCP、DNS。

任何阶段都不得把静态审计、配置收敛或构建成功写成“TX 已通”。只有对端真实捕获正确测试帧才是 TX-PASS。

## 8. 2026-11-25 追加：artifact 实体内容与 B1 实机验收闭环

本节基于本轮实际下载并展开的 GitHub Actions artifacts，以及用户 2026-11-24 已提供的 UART 实机记录。

### 8.1 Artifact 实体文件核验

- Kernel/DTB artifact：Run 45309219886 / Artifact 14884706818
- PREPARE-ONLY artifact：Run 45328201244 / Artifact 14890817693
- 两份 artifact 的 Image、DTB、最终 .config、config seed、config fragment、DTS 和 modules archive SHA256 完全一致。
- 工具链：aarch64-linux-gnu-gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0

| 文件 | SHA256 |
|---|---|
| Image | 9c99d1e36d553774a52f314e87f6866656b02d8f299c75d227e13f8e8a798955 |
| DTB | 7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d |
| kernel.config | 7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731 |
| kernel.config.seed | dd9f6b316171eabd4b18f3e9799d2f40dbf6211d3a49540fdb50837b5e07f5c2 |
| kernel.config.fragment | a432620750662dd40e90835684e920248ad3995c06ab265cdf882659ac89737f |
| DTS | 0d8b668a467f642cb32142d1d25588604fe0b14d1f1e873f6b9fea5e44cee959 |
| modules.tar.zst | ae4812905177c32c88a9b702fbb85ff7583056e4e634c93eab2da78b37d5d06e |
| uInitrd | 0eee97fabb867ca8b1024fbf89fb9897e2b4ee6f2a5740f0bb8282c7ec795518 |
| initramfs.cpio.gz | 5c84123a177ca67d8af617369703a6dd04a0f2152e07a227e05a83c74a3850e6 |
| boot.scr | 15940e422c07cf410f26e15c164a4f9411b17ef22d20148d73fcca50920bf6d4 |
| PREPARE-ONLY image compressed | 9a03ab47e9fc6222d46060ea90823b14e6665713ce40fb7e90f5906ef97bd511 |
| PREPARE-ONLY image expanded, 2 GiB | 26b35287d0f1b952d5cd97fc0e89763751d237e490f35bd5120c7ffb3bdc29eb |

用户已确认实际写入 SU08G TF 卡的 2 GiB 镜像 SHA256 与展开镜像哈希一致。

### 8.2 最终 .config 与 built-in/module 证据

- # CONFIG_NET is not set；NETDEVICES、ETHERNET、PACKET、INET 均未启用。
- MMC、USB、Rockchip clock/CRU、pinctrl、GPIO、reset、GRF、syscon、I2C_RK3X 和 regulator 基础支持已启用。
- modules.builtin 未发现 STMMAC、DWMAC 或 Ethernet MAC/PHY 驱动 built-in 项；模块清单也未发现板载 GMAC 驱动模块。
- B1 没有提前带入网络驱动。

### 8.3 实际 DTB 硬件资源状态

- TF 对应 &sdhci：okay；eMMC 对应 &sdmmc0：okay；SDIO 对应 &sdmmc1：disabled。
- USB host &usb_host0_xhci：okay；UART1/UART2：okay。
- GMAC1：disabled；MDIO1：disabled；RTL8211F PHY address 0：disabled。
- GMAC 的 RGMII、clock、reset、phy-supply 和 pinctrl 描述仍保留，但 GMAC/MDIO/PHY 节点 disabled，不触发目标网卡 probe。
- 这符合 B1 边界：保留 TF/eMMC、USB Host、必要 UART 和共享 SoC providers；隔离板载有线 MAC/MDIO/PHY；无线 SDIO 与蓝牙不纳入项目 A。

### 8.4 B1 实机启动验收

用户 2026-11-24 UART 记录确认：
1. U-Boot 自动发现并执行 TF 上的 boot.scr；
2. 从 mmc 1:1 加载 Image、uInitrd 和 Panther X2 DTB；
3. Linux 6.18.63 成功启动并解包 initramfs；
4. /init 成功执行，挂载 procfs 与 sysfs；
5. 输出 B1 network-isolated baseline ready. Interactive shell follows.；
6. BusyBox v1.37.0 ash 交互提示符 (panther-x2-b1-clean) # 实际出现；
7. /init 第 18 行出现 [: not found，但脚本继续运行并进入交互 shell。这是 initramfs 用户态脚本 applet/调用提示，不是 Kernel 启动失败，也不是网络功能失败。

**B1 完整启动验收：通过（带一条非致命脚本提示）。** 不要求重复烧卡、重启或重复 B1 测试。

### 8.5 R0 最终结论与放行

R0 原先未闭合的三项现已完成：artifact 的实际内容、manifest、工具链、哈希及复用链闭环；最终配置和模块/内建驱动隔离状态闭环；B1 /init 与 BusyBox ash 交互 shell 实机验收闭环。

**R0：PASS。允许进入 R1 静态配置/依赖复核及受控构建。** 这不表示任何网络功能已经启用或 TX 已经打通。