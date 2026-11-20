# Panther X2 最小 initramfs 渐进式构建蓝图（2026-11-20）

## 1. 目的与边界

用户补充并确认两项原则：

- **上游优先**：每个组件尽量采用对应项目主线/正式发布的原始源码与标准构建方式；优先配置和组合现有上游组件，不先写 Panther X2 私有替代实现。
- **最小系统只验证网络**：第一阶段只保留启动 Linux、识别网卡/PHY、查看链路状态和执行定向网络收发测试所需内容。DHCP、DNS、SSH、存储、NPU/RKNN、Immich 等均不是第一阶段目标，只有网络基线明确后才逐项增加。


用户确认另备一张独立 8GB TF 卡，用于与助手逐步搭建实验系统。

本路线的近期目标不是直接制作可日用发行版，而是构建一个尽可能小、可审计、可回退的 Linux 启动环境，用来隔离 6.12.81 GMAC TX 异常是否依赖完整 rootfs、系统服务或网络管理用户空间；长期目标是在此基础上逐层加入系统组件，逐步向 Ophub / Armbian 的成熟系统结构靠拢。

硬约束：

- 只使用独立 TF 卡；不写入 eMMC，不替换 Panther X2 当前 6.1.116 正常系统。
- 第一阶段只做仓库/构建输入只读审计与 CI 构建方案设计；未另行确认前不下载大型资产、不构建、不写卡、不启动实验内核。
- 不安装软件、不修改 Panther X2 当前系统、内核、驱动、网络或存储配置。
- 8GB TF 卡只作为实验介质；首个 Linux 根文件系统优先放在 RAM initramfs 中运行，避免把 EXT4/JBD2 写入问题混入 GMAC 实验。
- 不重复已完成的 TX/RX/环回/PHY/RGMII 测试。最小系统阶段只重做一次具有判别价值的既有 TX 广播测试，作为“完整用户空间 vs 最小用户空间”的单变量对照。
- 每个阶段保留源码/配置版本、构建产物摘要、实机结果、日志和回退点。

## 2. 现有资产与路线区分

仓库已存在完整 Armbian 镜像构建工作流：

- `.github/workflows/build-panther-x2-minimal.yml`
- 固定 Armbian Build commit：`3f3849bf50bfadff94d0d488eb968bdaf970dc72`
- 固定 Ophub Armbian commit：`9e71b57f73683f9c4d14a30311e4c2ccbff29566`
- 固定 Panther X2 U-Boot commit：`6e70f41585f15c43f45fcae609adec1865e83eb5`
- 固定 firmware commit：`a9d0e8337cc8aa2ca4b482acd7b19c74ce05860f`
- 现有镜像工作流使用 6.12.81 RK35xx 内核包，构建 Noble Server 完整 rootfs，并配置 NetworkManager、SSH、Armbian first-run。
- 现有 rootfs 目标大小为 6144 MiB；这不是本路线所需的 RAM initramfs。

现有 Quickstart 的完整系统登录说明含初始 root 密码 `1234`。本路线不沿用该登录设计，不把该 Quickstart 当作最小 initramfs 操作指南。

必须分开记录两条内核路线：

1. **诊断对象：Ophub RK35xx 6.12.81**。这是当前 GMAC 故障对照版本，作为第一阶段主要目标。
2. **Ophub Panther X2 正式板型路径：stable/6.18.y**。仓库现有设备数据库审计指向该系列。它不是 6.12.81 RK35xx 的同一配置，不在第一阶段混入。

两条正常黄金基准仍然保留：6.1.65 与 6.1.116。6.1.116 是优先正常对照，6.1.65 是第二条黄金参考。6.1.174 保留为历史故障对照。

## 3. 总体分层

### Layer 0 — 只读资产与启动链核验（已完成）

只检查已有仓库、Actions Artifact 和已归档资产，回答：

- 6.12.81 官方包中 Kernel Image、Panther X2 DTB、initramfs/boot 文件的准确路径、格式、版本及 SHA-256。
- 6.12.81 内核配置是否支持外部 initramfs（例如 `CONFIG_BLK_DEV_INITRD`、所需压缩格式）；不得凭常见默认值推断。
- 6.12.81 GMAC、MDIO、Realtek PHY、MMC/SD 控制器是否 built-in；已有 built-in 结论优先引用既有审计，不重复做全量模块审计。
- 已有 Panther X2 U-Boot 是否支持从该 TF 卡分区格式加载 Kernel、initramfs、DTB；启动命令和 console 参数必须来自可核验的现有启动脚本/日志，不猜测。
- 6.1.116 正常基线中的 Kernel Image、DTB、boot 文件是否能以相同启动链做对照；不跨版本混用模块。
- 8GB 卡的分区/文件系统布局需服从已核实的 U-Boot 读取能力。当前不预设 FAT 或 EXT4，不预设写入扇区布局。

本层结束条件已满足：资产清单、依赖关系、哈希、已知/未知项和安全写卡静态候选均已归档于 P1 报告。结论为可复用当前 eMMC SPL + TF JP-TvBox proper，从 SD/TF ext4 第一分区加载 legacy gzip uInitrd、Kernel 和 Panther X2 DTB。P1 不代表自制 initramfs 已构建或启动。

### Layer 1 — 最小 RAM rootfs / initramfs（当前只做只读设计；构建待授权）

当前只做上游组件来源/版本/依赖/许可证初审。组件初审见 P2 报告 PANTHER-X2-P2-UPSTREAM-USERSPACE-COMPONENT-AUDIT-20261120.md：BusyBox 1.36.1 为基础用户空间稳定版候选；ethtool 7.2 为诊断工具候选；独立 iproute2 与 tcpdump 暂缓。当前唯一工作是核验 BusyBox 1.36.1 源码中的 ip/nc applet、UDP broadcast 功能与 Kconfig 依赖。未经用户明确授权，不下载源码包、不触发 CI、不编译、不生成 initramfs 产物。授权后再构建 ARM64、可从 RAM 启动的 initramfs。原则上仅包含：

- `/init` 和必要目录结构；
- BusyBox（优先静态构建，减少动态库依赖）；
- `/proc`、`/sys`、`/dev` 挂载能力；
- `iproute2`、`ethtool` 等必要网络诊断工具；
- 一个可控的 UDP/广播测试工具（优先采用上游已有工具；确有缺口才编写最小测试程序）；
- 串口控制台、内核日志和只读诊断输出。

第一阶段明确不加入 DHCP 客户端、DNS、SSH、NetworkManager、Netplan 或存储管理；只有网络基础收发验证通过后，才按后续阶段逐项引入。

具体工具及其依赖在 Layer 0 后锁定；不为“看起来完整”而加入 systemd、NetworkManager、SSH、桌面或存储服务。初始阶段不挂载 TF 上的 EXT4 rootfs，不把测试日志写回 TF；日志通过 UART 或其他已确认安全的方式留存。

构建优先采用独立、手动触发的 GitHub Actions workflow，所有源码、工具链、包版本和 Action 固定到可追溯版本。现有完整镜像 workflow 保持不变。

### Layer 2 — 6.12.81 最小系统启动与定向网络对照

前提：Layer 0 静态检查通过，Layer 1 构建产物校验通过，用户明确授权写入独立 TF 卡并启动实验系统。

- 保持已核实的启动固件不变；不同时替换 U-Boot、Kernel、DTB 和 rootfs。
- 仅加载 6.12.81 Kernel + 对应 Panther X2 DTB + 最小 initramfs。
- 确认内核进入 `/init`、关键设备枚举、GMAC/PHY probe 和 link 状态。
- 只针对既有故障现象复核一次：驱动报告 TX 成功但第三方同二层监听器收不到广播帧。
- 不重复整套 DMA、PHY、RGMII、环回测试。
- 不把 DHCP 是否成功当作 TX 广播链路是否正常的替代指标。

判别：

- 最小 initramfs 下仍复现相同 TX 广播异常：完整 rootfs、NetworkManager、systemd 网络管理不是该 TX 现象的必要条件；后续重心回到 Kernel/DTB/启动链及底层路径。
- 最小 initramfs 下广播正常：说明完整用户空间或启动后的配置/服务可能参与故障；此时进入逐层加回，而不是立即归因某一个服务。
- 无法启动或 GMAC 未 probe：先判定启动参数、DTB、内核配置或 initramfs 构建问题，不把它误判为 GMAC TX 结论。

### Layer 3 — 黄金内核对照

在 Layer 2 测试条件稳定后，使用同一份尽可能通用、无外置内核模块依赖的 initramfs，增加 6.1.116 正常内核对照：

- 6.1.116 Kernel + 其匹配的 Panther X2 DTB；
- 6.12.81 Kernel + 其匹配的 Panther X2 DTB；
- 启动固件、initramfs、测试程序和第三方监听器保持一致。

不得将 6.1.116 与 6.12.81 的内核模块交叉混用。若两版 DTB/boot 格式不同，必须保留各自匹配资产并明确记录，不能为追求“完全相同”而强行混搭。

6.1.65 作为第二黄金参考，只在 6.1.116 对照无法解释结果或需要确认共同基线时再加入，不提前扩大测试矩阵。

### Layer 4 — 逐层加回用户空间组件

仅当最小系统网络表现与完整系统不同，才按组加回：

1. 基础设备管理/udev；
2. systemd（若最小 initramfs 起始方案未使用）及日志服务；
3. 网络管理组件（NetworkManager/Netplan 或明确选定的另一套机制）；
4. DHCP、DNS、SSH；
5. 存储挂载与管理；
6. 其他常驻服务。

每次只加一组组件，复用相同 TX 定向测试；若故障出现，退回上一个通过层级，缩小引入范围。不得一次性加入整个 Armbian rootfs 后再猜原因。

### Layer 5 — 向 Ophub / Armbian 完整系统靠拢

当网络和基础硬件层级已明确后，再逐步吸收成熟发行版的构建结构：

- 优先复用已固定 commit 的 Armbian Build / Ophub 脚本和包管理机制；
- 尽量采用上游已有组件与配置，不制造无证据的 Panther 专属补丁；
- 记录每个 Panther X2 专属差异及其原因、来源、测试结果和撤销方法；
- 最后才形成可日常运行的 Server 系统，并独立验证存储、温控、升级、备份恢复；
- NPU/RKNN、Immich 不属于 GMAC 最小系统验证的前置条件。

## 4. 上游源码与本地改动管理

每个组件引入前，建立简短来源记录：

- 组件名称及用途；
- 上游项目、官方仓库 URL；
- 采用的稳定发布版本、tag 或精确 commit；
- 采用的构建方式及必要依赖；
- 是否有本地修改；若有，列出文件、差异、修改原因和测试证据；
- 本地修改是否具备向上游提交的条件，以及可能需要的通用化工作。

源码策略：

1. 优先选择 Linux kernel、BusyBox、iproute2、ethtool 等项目自身的上游源码/正式发布版本，不从不明来源复制代码。
2. 优先使用上游已有功能、标准配置和可复现构建参数；能通过配置解决的问题不写代码。
3. Panther X2 必需的本地改动集中保存为独立、可审查的 patch，不直接散落修改第三方源码。
4. 每个 patch 记录基于哪个上游版本、解决什么问题、为何不能用现有上游功能、影响范围、验证结果和撤销方法。
5. 对具备通用价值的修复，评估整理成不依赖本项目私有路径/设备环境的改动，后续向对应上游提交；未提交或未合并前明确标注为本地 patch，不能称为主线代码。
6. 不为了“贴近主线”而在故障定位期间同时升级多个组件；每次只引入一个明确版本和功能层级。

## 5. 变量控制原则

每轮尽量只改变一个层级变量：

- 启动固件固定；
- Kernel 与对应 DTB 成套匹配；
- initramfs 在跨内核对照时尽量保持相同；
- 不加载跨版本外置模块；
- 网络测试程序、线缆、交换网络和第三方监听器保持一致；
- 不在同一轮同时升级内核、改 DTB、改 U-Boot、改 PHY 参数和替换用户空间。

源码差异只用于提出候选；只有受控实机 A/B 结果才能证明某个变量对故障有影响。

## 6. 当前不做事项

- 不修改或覆盖现有 `build-panther-x2-minimal.yml`。
- 不触发旧的完整 Armbian 镜像构建。
- 不下载新的大体积内核/发行版资产，除非 Layer 0 盘点确认缺失且用户同意。
- 不写 TF 卡，不启动实验内核，不改 eMMC。
- 不安装或修改 Panther X2 当前系统中的软件、内核、驱动、网络服务。
- 不重跑已完成的 GMAC TX/RX、RGMII delay、PHY MDIO、DMA descriptor、环回和 pinctrl 源码审计。
- 不在第一阶段加入 NPU/RKNN、Immich、Docker、桌面或其他非必要服务。

## 7. 当前状态

| 项目 | 状态 |
|---|---|
| 用户确认独立 8GB TF 卡用于实验 | 已确认 |
| 现有完整 Armbian workflow 与最小 initramfs 路线区分 | 已完成只读审计 |
| 6.12.81 与 stable/6.18.y 路线区分 | 已确认 |
| P1：initramfs/gzip 内核能力与 U-Boot ext4/legacy uInitrd 加载能力 | 已完成静态验收；详见 P1 报告 |
| P1：6.1.116 资产匹配及历史 eMMC 启动边界 | 已完成静态核对；历史 U-Boot 实际执行轨迹仍未闭环但不阻塞当前固件下的受控对照 |
| 8GB TF 卡 GPT/ext4 静态布局 | 已形成候选；未对实体卡核验或写入 |
| BusyBox 1.36.1 上游源码/Kconfig 核验 | 当前唯一执行项 |
| ethtool 7.2 依赖与 ioctl/netlink 构建选项 | 待 BusyBox 项完成后 |
| iproute2 / tcpdump 首版是否需要 | 暂缓，只有明确功能缺口才重新评估 |
| 最小 /init 与目录树设计 | P2 只读设计待做 |
| 独立 CI workflow 设计/审查 | P2 只读设计待做 |
| 构建 initramfs | 未授权、未执行 |
| 写入 8GB TF 卡 | 未授权、未执行 |
| Panther X2 实机启动与网络测试 | 未授权、未执行 |

## 8. 下一项唯一工作

继续 P2，当前只核验 BusyBox 1.36.1 官方源码中的 ip applet、nc UDP/broadcast 功能与配置依赖。完成该组件后再进入 ethtool 7.2 的构建选项和依赖审查；不要并行展开其他组件。此阶段不下载源码包、不触发构建、不生成产物、不写卡、不启动实验内核。完成设计后再向用户确认是否授权实际 CI 构建。

