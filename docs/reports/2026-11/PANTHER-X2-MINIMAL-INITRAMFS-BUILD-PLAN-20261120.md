# Panther X2 最小 initramfs 渐进式构建蓝图（2026-11-20）

## 1. 目的与边界

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

### Layer 0 — 只读资产与启动链核验（当前阶段）

只检查已有仓库、Actions Artifact 和已归档资产，回答：

- 6.12.81 官方包中 Kernel Image、Panther X2 DTB、initramfs/boot 文件的准确路径、格式、版本及 SHA-256。
- 6.12.81 内核配置是否支持外部 initramfs（例如 `CONFIG_BLK_DEV_INITRD`、所需压缩格式）；不得凭常见默认值推断。
- 6.12.81 GMAC、MDIO、Realtek PHY、MMC/SD 控制器是否 built-in；已有 built-in 结论优先引用既有审计，不重复做全量模块审计。
- 已有 Panther X2 U-Boot 是否支持从该 TF 卡分区格式加载 Kernel、initramfs、DTB；启动命令和 console 参数必须来自可核验的现有启动脚本/日志，不猜测。
- 6.1.116 正常基线中的 Kernel Image、DTB、boot 文件是否能以相同启动链做对照；不跨版本混用模块。
- 8GB 卡的分区/文件系统布局需服从已核实的 U-Boot 读取能力。当前不预设 FAT 或 EXT4，不预设写入扇区布局。

本层结束条件：形成资产清单、依赖关系、哈希、已知/未知项和安全写卡方案。未结束前不构建、不写卡。

### Layer 1 — 最小 RAM rootfs / initramfs

构建一个 ARM64、可从 RAM 启动的 initramfs。原则上仅包含：

- `/init` 和必要目录结构；
- BusyBox（优先静态构建，减少动态库依赖）；
- `/proc`、`/sys`、`/dev` 挂载能力；
- `iproute2`、`ethtool` 等必要网络诊断工具；
- 一个可控的 UDP/广播测试工具；
- 可选 DHCP 客户端，仅在需要验证 DHCP 用户态时加入；
- 串口控制台、内核日志和只读诊断输出。

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

## 4. 变量控制原则

每轮尽量只改变一个层级变量：

- 启动固件固定；
- Kernel 与对应 DTB 成套匹配；
- initramfs 在跨内核对照时尽量保持相同；
- 不加载跨版本外置模块；
- 网络测试程序、线缆、交换网络和第三方监听器保持一致；
- 不在同一轮同时升级内核、改 DTB、改 U-Boot、改 PHY 参数和替换用户空间。

源码差异只用于提出候选；只有受控实机 A/B 结果才能证明某个变量对故障有影响。

## 5. 当前不做事项

- 不修改或覆盖现有 `build-panther-x2-minimal.yml`。
- 不触发旧的完整 Armbian 镜像构建。
- 不下载新的大体积内核/发行版资产，除非 Layer 0 盘点确认缺失且用户同意。
- 不写 TF 卡，不启动实验内核，不改 eMMC。
- 不安装或修改 Panther X2 当前系统中的软件、内核、驱动、网络服务。
- 不重跑已完成的 GMAC TX/RX、RGMII delay、PHY MDIO、DMA descriptor、环回和 pinctrl 源码审计。
- 不在第一阶段加入 NPU/RKNN、Immich、Docker、桌面或其他非必要服务。

## 6. 当前状态

| 项目 | 状态 |
|---|---|
| 用户确认独立 8GB TF 卡用于实验 | 已确认 |
| 现有完整 Armbian workflow 与最小 initramfs 路线区分 | 已完成只读审计 |
| 6.12.81 与 stable/6.18.y 路线区分 | 已确认 |
| initramfs 所需内核配置与压缩格式核验 | 待做 |
| U-Boot 对目标 TF 分区/加载命令核验 | 待做 |
| 最小 ARM64 rootfs 工具与依赖锁定 | 待做 |
| 独立 CI workflow 设计/审查 | 待做 |
| 构建 initramfs | 未授权、未执行 |
| 写入 8GB TF 卡 | 未授权、未执行 |
| Panther X2 实机启动与网络测试 | 未授权、未执行 |

## 7. 下一项唯一工作

继续 Layer 0：只读核对 6.12.81 内核配置中 initramfs 支持、实际 boot 文件布局，以及现有 Panther X2 U-Boot/启动脚本的加载能力。先形成“最小 initramfs 能否直接复用当前启动链”的明确结论，再决定构建方式。

