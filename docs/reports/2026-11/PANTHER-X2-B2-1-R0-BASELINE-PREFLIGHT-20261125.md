# Panther X2 项目 A：B2-1 / R0 基线资产与 TX 前置核查记录（2026-11-25）

- 阶段：B2-1 / R0
- 本轮性质：只读仓库、Actions 日志与既有报告核查
- 状态：**R0 未通过；已识别基线来源/分支差异，等待补齐证据**
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

**R0 结论：不通过，停留 R0。** 这不是网络组件失败，而是基线身份和 B1 完整验收门尚未闭合。

## 7. 下一步严格顺序

1. 只读提取并审查 artifact `14884706818` 与 `14890817693` 内的 manifest、最终 `.config`、Image、DTB、initramfs、boot script 和 SHA256；核对 toolchain metadata 缺口。
2. 锁定实际用于当前 TF 实测的 Image/DTB/uInitrd/bootargs 哈希与其来源，确认与上述 artifact 的对应关系；不得写入 eMMC。
3. 补齐 B1 `/init` / ash 交互 shell 实机验收。此项需要用户另行授权的设备启动/只读观察；本报告不授权。
4. R0 通过后，进入 R1：只引入最小 `NET` / Ethernet core / `PACKET` 依赖，不启用 STMMAC、DWMAC4、Rockchip glue、MDIO、PHY，不恢复 GMAC/MDIO DTB 节点。
5. R1 配置/构建验收通过后，才逐项进入 R2/R3/R4/R5/R6。各阶段仍保持 GMAC/MDIO/PHY DTB disabled，直到 R7 单独启用。
6. R7 首次真实网络测试仅发送 0x88B5 自定义 Ethernet 广播帧，由对端逐帧捕获；TX-PASS 前不加入 RX 上层、ARP、IPv4、ICMP、DHCP、DNS。

任何阶段都不得把静态审计、配置收敛或构建成功写成“TX 已通”。只有对端真实捕获正确测试帧才是 TX-PASS。
