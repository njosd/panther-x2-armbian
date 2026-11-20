# Panther X2 P2：最小网络用户空间上游组件初审（2026-11-20）

- 主线：PANTHER-X2-MINIMAL-SYSTEM-MAIN-ROADMAP-P1-P8-20261120.md
- 阶段：P2 只读设计
- 本报告性质：上游版本/能力初筛，不是最终锁版，也不是构建记录
- 操作边界：只查询公开上游资料和仓库源码；未下载源码包、未编译、未触发 CI、未连接 Panther X2、未写 TF/eMMC

## 1. P2 第一版最小用户空间的原则

第一版只提供：
- 串口控制台与交互 shell；
- procfs、sysfs、devtmpfs、tmpfs；
- 网卡 link/address/route 的查看与最小配置；
- ethtool 读取驱动/链路/统计信息；
- 一个受控 UDP 广播发送工具；
- 日志与测试结果经 UART 输出。

第一版不加入 DHCP/DNS/SSH/NetworkManager/systemd/udev/tcpdump/存储管理。第三方同二层监听器继续在外部调试主机运行；本轮没有必要把监听器或抓包服务塞入 Panther initramfs。

不为“功能完整”引入 iproute2 全套依赖。如果 BusyBox 的 ip applet 足以满足基础 link/address/route 操作，就先用它；只有出现明确功能缺口才引入独立 iproute2。

## 2. 组件初筛

### 2.1 BusyBox：首选基础用户空间

上游：
- 官方主页：https://busybox.net/
- 官方源码下载：https://busybox.net/downloads/
- 许可证：BusyBox 源码以 GPLv2-or-later 为主；最终仍需在选定源码包中保存 LICENSE/COPYING 与各 applet 版权声明。

版本候选：
- **1.36.1：当前保守候选。** 官方发布说明将其标为 stable，发布日期 2023-05-19。
- 1.37.0（2024-09-27）和 1.38.0（2026-05-13）在官方页面仍标为 unstable；第一轮故障定位不追求新版本，暂不把 unstable 版本带入。
- 1.36.1 仅为候选，未锁定。最终锁版前需对该官方 tarball 核验 nc applet、ip applet、配置项和构建结果。

第一版计划启用的 BusyBox 功能（名称以实际版本 Kconfig 为准）：
- shell：ash；
- 文件/控制台：cat、echo、printf、mkdir、mount、sleep、dmesg、uname、stty（按需）；
- 网络：ip、iplink、ipaddr、iproute、ipneigh；
- UDP 广播发送：nc（需确认所选版本的 NC_110_COMPAT / UDP / broadcast 选项）；
- 其他仅按 /init 脚本实际依赖开启。

**重要源码线索（尚非 1.36.1 版本闭环）：** 当前 BusyBox 上游镜像中的 networking/nc_bloaty.c 提供 -u（UDP）、-b（允许广播）、-p（本地端口）、-s（本地地址）；-b 路径调用 SO_BROADCAST。该实现由 NC_110_COMPAT 选项控制。若 1.36.1 源码确认保留该能力，可用 BusyBox 自带 nc 发送固定 UDP 广播，不必写自定义 C 程序。若不满足，先比较 1.37.0 的对应源码；只有上游工具均不满足时才设计最小自有 sender，并将源代码、许可证和差异独立归档。

### 2.2 ethtool：保留为独立诊断工具

上游：
- 官方发布页：https://www.kernel.org/pub/software/network/ethtool/
- 当前候选：**7.2**，官方发布日期 2026-10-19。
- Git tag：v7.2；tag commit：d54c8bd1d0da950280a34484026f3b3b7bdf9a19。
- 官方源码 tarball：ethtool-7.2.tar.xz。
- 已查到的上游 tarball SHA-256：fcb1a8c8798e8f70495b910d1e3b1d4a52140c5645aa5847119392b907a64823（来自 Debian 源包对 upstream orig tarball 的校验记录；正式构建前仍应独立下载并复核）。

候选构建方式：
- 先评估 `--disable-netlink --disable-pretty-dump`，以关闭可选 netlink/libmnl 与 pretty-dump 依赖，优先保留传统 ioctl 路径。
- 这可以减少 libmnl 及动态依赖；是否能满足本项目需要的 `-i`、`-S`、`-k`、`-a`、`-g` 等查询，须在源码与构建后做静态/功能验收。
- 若后续确需 ethtool netlink，再单独引入 libmnl，不在首版默认加入。

### 2.3 iproute2：首版暂缓独立引入

上游：
- 官方 Git 仓库（发布公告）：https://github.com/shemminger/iproute2
- 官方发布：7.3.0，发布日期 2026-10-21。
- 官方发布公告说明 7.3.0 对应 7.3 kernel cycle。

决策：
- 首版先使用 BusyBox ip applet完成 link/address/route 基础操作。
- iproute2 7.3.0 作为后续升级候选，不立即编入 initramfs。
- 完整 iproute2 可带来更完整的 ip/tc/ss/devlink 等功能，但其构建可选项会引入 libmnl、libbpf、libcap、libelf 等额外依赖；本轮 GMAC TX 定向验证尚不需要这套复杂度。
- 如果 BusyBox ip 的确缺少测试所需功能，再只引入 iproute2 的必要组件和依赖，不默认把整个工具集全部打包。

### 2.4 tcpdump：第一版暂不引入

理由：
- 既有测试已经完成板卡本机 outgoing capture 与第三方同二层监听器的对照；本项目不重复做整套测试。
- 新最小系统的首要证据是外部接收端是否收到固定测试帧，而不是再次依赖本机 outgoing hook。
- tcpdump 需要 libpcap，并增加编译/依赖闭包；只有后续出现明确抓包判别需求才加回。

## 3. 第一版工具职责边界

| 功能 | 首选组件 | 说明 |
|---|---|---|
| PID 1 / shell | BusyBox ash + 项目自有 /init | /init 是本项目 glue，必须可审查、短小、静态检查 |
| proc/sys/devtmpfs 挂载 | BusyBox mount | 不需要 systemd/udev |
| 网卡 link/address/route | BusyBox ip | 先覆盖最小必需命令 |
| 驱动信息/统计/offload/link | ethtool 7.2 | 初始只读查询，不执行修改型 ethtool 命令 |
| UDP 广播发送 | BusyBox nc（版本能力待核） | 优先使用 -u/-b，固定 payload/目的地址/端口并记录 |
| 本机抓包 | 暂不包含 | 不是外部帧到达的证明 |
| DHCP/DNS/SSH | 不包含 | 第一版不运行服务 |

## 4. 构建与依赖策略（尚未执行）

- BusyBox 首选静态链接；最终选择 glibc/musl 交叉工具链之前，先核对 CI runner、交叉编译器、静态 libc 与可复现性。
- ethtool 先尝试关闭 netlink 后静态链接；若静态构建不合适，再明确列出动态库和 ABI 依赖，不允许隐式依赖 runner 环境。
- /init 与测试脚本属于项目自有 glue，放在独立目录，建议使用宽松且清晰的许可证（如 MIT/BSD-2-Clause），并记录作者/修改历史；不得直接修改 BusyBox/ethtool 上游源码。
- 每个上游源码包需保存：官方 URL、版本、tag/commit（若有）、签名/校验来源、实际 SHA-256、许可证文件、构建参数、依赖清单。
- CI 固定 runner/container image、交叉工具链和 apt 包版本；构建产物附带 manifest、完整日志、SHA-256 和 SBOM/依赖清单。
- 不把构建成功当作实机启动成功；P2 产物必须经过架构、ELF、静态依赖、initramfs 目录、/init 权限和 gzip/cpio/legacy uInitrd 格式检查。

## 5. 尚未决定的事项

1. BusyBox 1.36.1 的精确 Kconfig 与 nc_bloaty.c 是否具备所需 -u/-b/-p/-s 行为；需要读取官方版本源码确认。
2. BusyBox 1.36.1 的静态交叉工具链选择与可复现锁定方式。
3. ethtool 7.2 关闭 netlink 后所需查询命令是否全部落在 ioctl 实现路径；是否必须保留 libmnl。
4. UDP 广播测试的源地址、接口选择、源/目的端口、payload 和外部监听脚本参数；必须结合历史测试条件设计，不能随意更换后声称等价。
5. /init 的串口控制台交互、日志输出、异常 fallback 和 /init 可执行性验收。

## 6. 本轮结论

- 首版可以先由 BusyBox 承担 shell、基础 IP 管理和 UDP 测试 sender，避免立即引入完整 iproute2。
- ethtool 7.2 是当前合适的独立诊断工具候选；优先评估关闭 netlink 以减少 libmnl 依赖。
- 不将 tcpdump、DHCP、DNS、SSH、NetworkManager、systemd、udev 放入首版。
- 目前只完成公开资料初筛，未锁定最终版本、未下载源码包、未构建、未生成 CI 产物。
- 下一步只继续核实 BusyBox 1.36.1 的源代码功能与配置，不并行扩展其他组件。

## 7. 用户纠正后的版本策略与本报告状态更新（2026-11-20）

用户明确：新系统从零构建，不复刻 6.1.116；6.1.116 只作为已知正常的对照参考。组件尽量采用当前仍维护的上游主线或最新正式稳定版本，以便未来融合 Ophub / Armbian 更简单。

因此：
- 本报告中 BusyBox 1.36.1 不再是默认候选；其“保守稳定版”选择撤回。
- ethtool 7.2、iproute2 7.3.0 也只是本次初筛时的版本记录，不构成新系统锁版。
- 后续应在启动架构审计完成后，重新检查各项目当时的最新正式稳定版/维护分支，并记录 tag/commit、发布日期、许可证、依赖和源码摘要。
- 开发时追上游；每次具体实验则固定全部输入版本和哈希。完成一轮后再主动升级并回归，不在同一轮实验里滚动升级多个组件。
- 不应为了降低依赖而预设 BusyBox 必须替代 iproute2；按所需功能和未来主线融合成本选取。

此外，P2 的当前第一项已调整为“独立启动链与 eMMC Vendor 数据来源/传递只读审计”，见：
`PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md`。
在这一项完成前，暂停 BusyBox、iproute2、ethtool 版本锁定和任何构建工作。
