# Panther X2 项目 A：最小系统与基础网络验证总路线图

- 建立日期：2026-11-21
- 项目统一名称：**项目 A（Panther X2 最小系统与基础网络验证）**
- 文档角色：唯一权威总路线图
- 配套执行文档：[项目 A 分阶段实施计划](PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)
- 当前状态：架构收敛完成；最小系统尚未完成实机启动认证

## 0. 统一项目定义

从 2026-11-21 起，关于 Panther X2 的“最小系统”“最小验证系统”“最小 RAM Linux”“最小网络系统”“JP U-Boot 测试基线”及其架构、组件选择、实施步骤，统一称为**项目 A**。后续对话和仓库维护均以本总路线图及配套实施计划为工作基线。旧文档如有冲突，以本文件为准。

项目 A 的目标是建立尽可能精简、可重复构建、可审计、可回退的 Linux 验证环境，按顺序证明：
1. 固定已验证启动入口，启动最小 RAM Linux；
2. 在不依赖 DHCP/DNS/SSH 等复杂服务的情况下，验证基础静态网络连通性；
3. 扩展验证少量 TCP/UDP 端到端通信；
4. 完成基础验证后，再评估长期 U-Boot 与正式系统架构；
5. 按真实需求逐层增加用户空间，形成可维护系统的基础。

**项目 A 不是完整 Armbian/Ubuntu 部署，也不是 Immich 部署。** 家庭照片中心、NPU/RKNN、数据库、照片存储与备份恢复属于后续独立阶段。

## 1. 项目边界与项目拆分

项目 A 只负责最小 Linux 启动、基础硬件枚举、Panther X2 板载有线千兆以太网口连通性、构建可复现性和长期启动架构评估。**网络硬件范围唯一限定为板载有线千兆以太网口。** Wi-Fi/无线网络、蓝牙及其控制器、总线设备、驱动、固件、协议和用户空间组件全部永久排除在项目 A 的研究、构建、测试、验收和后续逐项引入范围之外；USB/PCIe 外接网卡也不属于项目 A。

网卡历史故障根因调查、GMAC/MDIO/PHY 专项根因排障及驱动专项回归，仍属于独立历史专题；项目 A 不恢复这些根因调查，也不重复其专项实验。但项目 A 必须继承这些历史故障线索作为风险输入，并在 B1 建立干净基线时隔离所有可能干扰网络验证的组件。隔离是项目 A 的变量控制和实验设计，不是继续调查项目 B 的故障根因。干净基线通过后，才按单变量计划逐项引入网络组件，观察哪个组件/组合首次改变结果。

### 1.1 项目 B 历史成果继承规则（重要）

项目 B 是此前历史故障排除与技术研究的归档项目，目前封存，不主动恢复专项调查；但**项目 A 必须充分继承和使用项目 B 的全部相关既有成果**。项目归属与成果使用范围不同：封存限制的是继续开展项目 B 的新任务，不限制项目 A 查阅、引用和应用项目 B 的历史成果。

- 项目 A 开展任何相关研究前，先检索项目 B 的历史报告、原始日志、源码分析、实验记录、构建产物和已验证结论。
- 项目 B 中已经完成且证据充分的实验，项目 A 直接采用其结果，禁止重复执行；不得仅因任务现在归入项目 A 就重新跑一遍。
- 已验证结论可作为既有事实和设计输入；未验证、条件性结论、推测和候选方案必须保留原证据等级及适用条件，不得因跨项目引用而升级可信度。
- 只有当既有证据无法回答项目 A 的具体问题、目标环境发生实质变化，或证据存在明确缺口时，才允许提出最小化补充验证。执行前说明引用了哪些旧成果、旧实验为何不足、新验证要区分什么问题，并遵守项目 A 的授权与安全约束。
- 项目 A 可以将项目 B 的技术结论用于架构选择、风险判断、组件筛选和测试设计；但不得借此自动恢复项目 B 的专项故障排查。

## 2. 固定主线顺序

**JP-TvBox U-Boot proper 已验证测试基线 → 最小 RAM Linux 启动 → 最小静态网络连通性 → 基础 TCP/UDP 验证 → 长期 U-Boot 评估 → 正式用户空间融合。**

B1—B3 固定当前已验证的 JP-TvBox U-Boot proper，不同时更换 SPL、U-Boot proper、Kernel、DTB、initramfs 多个变量。先证明最小 Linux 和基础网络可运行，再决定是否改变启动固件。

## 3. U-Boot 论证与当前启动链

### 3.1 为什么先用 JP-TvBox U-Boot proper

选择 JP-TvBox proper 作为首轮测试入口，是基于已有 Panther X2 实机证据和控制变量原则，不代表它是最终选型：

- 2026-11-17/18 UART 记录证明，Panther X2 实际进入过 JP-TvBox U-Boot proper，并从 TF 读取启动文件、加载 Kernel/DTB/initrd。
- JP proper 归档 SHA-256：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`；大小 1,464,832 bytes。
- 实际观察到的是**现有 eMMC 前级 SPL → TF 上 JP-TvBox U-Boot proper** 的混合链，不是完整 JP SPL+proper 组合。UART 记录中的 SPL build date 为 2023-04-23、DDR V1.13；proper build date 为 2023-11-12，并自报 Radxa ROCK3 Model C。
- 2026-11-18 一次 U-Boot proper 对 BootROM source tag 的只读读取指向 eMMC（source ID 0x02）；SPL 后续从 MMC2/TF 加载 proper。不能描述成 TF 自包含启动。
- JP-TvBox `idbloader.img` 与当前 eMMC 安装的 Panther X2 `idbloader.img` 是不同二进制，不能混为一谈。
- 先固定 JP proper、仅替换 Linux 侧最小系统资产，可以减少变量，便于定位最小 Linux 本身的启动问题。

### 3.2 当前已观察启动链

```text
BootROM 从 eMMC 启动
  -> eMMC 当前活动 SPL / DDR 初始化
  -> SPL 从 TF/SD（MMC2）读取 JP-TvBox U-Boot proper
  -> JP proper 从 TF ext4 分区加载 Kernel、Panther X2 DTB、uInitrd
  -> Linux 以 RAM initramfs 作为根文件系统运行
```

关键哈希：
- JP-TvBox U-Boot proper：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`
- 当前 eMMC Panther X2 IDB：`990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e`
- 当前 eMMC Panther X2 proper：`3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af`
- JP-TvBox IDB 归档：`e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`

混合链是已观察到的测试入口，不代表最终启动架构已经确定。

### 3.3 长期 U-Boot 候选与评估

B1—B3 不换 U-Boot。完成最小 Linux 与基础网络验证后，再比较：
- Panther X2/Ophub 原版 U-Boot；
- JP-TvBox U-Boot 及完整 SPL 组合；
- Rockchip 官方 RK3566 loader/SPL/DDR/BL31 组合；
- NixOS/mainline U-Boot Panther X2 配方；
- 其他具备 Panther X2 实机证据且可复现构建的候选。

比较必须覆盖源码 commit、defconfig、最终 .config、control FDT/SPL DTS、RK3566 BootROM/SPL/DDR/BL31/proper 衔接、Panther X2 4GB LPDDR4 双 CS/rank 匹配、MMC/TF/eMMC 时序、FDT 交接、Vendor 数据读取、升级回滚和救援恢复。不能只凭版本新旧或一次启动成功下结论。

NixOS 配方仅作为研究样本；其曾出现 ROCK 3C EVB control FDT/target 等配置，需逐项验证，不得因配方名称认定已完整适配 Panther X2。Rockchip DDR/BL31 候选必须有本机颗粒、双 CS 拓扑和板级依据。

## 4. 架构与组件选择原则

### 4.1 最小化、分层启用与单变量试验

- 先构建一个纯 RAM 的最小 Linux 启动底座，不构建完整 Ubuntu/Armbian rootfs。
- B1 不预置任何 B2/B3 网络工具、网络协议、Ethernet 驱动、存储驱动、USB 驱动、模块或固件。
- Linux B1 从 initramfs/RAM 运行；TF 只由启动前的 JP U-Boot proper 读取 Image、uInitrd 和 DTB。Linux 阶段不启用 MMC/eMMC/SD/SDIO、块设备、USB、网络协议栈或网络设备驱动。
- B1 保留 ARM64、RK3566 SoC 启动支持、UART2 console、必要时钟/pinctrl、initramfs/gzip、devtmpfs/procfs/sysfs 和静态 BusyBox ash；不加载或 probe GMAC/STMMAC/DWMAC、MDIO/PHY/PCS。
- 有线千兆网口链路的后续依赖审查范围仅限 Ethernet MAC/GMAC、MDIO、PHY、PCS 及相关 pinctrl/clock/reset/regulator/DMA/interrupt；共享于 UART/SoC 启动的基础设施不得盲目关闭，必须按设备节点/依赖关系精确处理。
- Wi-Fi/无线网络、蓝牙及其控制器、驱动、固件、协议和用户空间组件永久排除，不进行依赖追踪或逐项引入；只在 clean-test DTB/镜像准入检查中确认相关节点、驱动、固件和用户空间内容未混入。
- USB 与 USB/PCIe 外接网卡不属于项目 A；B1 禁用 USB host/PHY。干净基线通过后，只围绕板载有线千兆 Ethernet 按单变量实验逐项加入最小依赖闭包，完成构建审计和目标硬件验证后再继续。
- B2、B3 只在相应网络组件已逐项放行后，按层次验证接口/link、静态地址、ARP、ICMP、TCP/UDP；不把多项组件、配置或测试捆绑为一次试验。
- 同一轮 B1—B3 尽量固定 Kernel、DTB、initramfs、BusyBox、工具版本和启动链。只有当前证据明确要求时才变更其中一项，并将变更作为独立试验。
- 不因完整发行版通常包含某组件，就提前加入它；不为追求“最小体积”而删除后续阶段明确需要、且不会干扰当前阶段的工具。

### 4.2 新系统从头构建、上游优先

- 不复刻 6.1.116 的用户空间、包版本或历史构建方法。
- 6.1.116 只作为已知正常行为参照和必要时的对照资产。
- 组件优先选对应项目当前维护的上游主线或正式稳定版；固定版本、commit/tag、工具链、配置、依赖和哈希。
- 不在同一轮同时滚动升级多个组件；完成一轮验证后再升级并回归。
- 上游已有标准能力时优先配置使用；只有明确缺口才考虑本地 glue/patch。补丁必须单独管理并记录来源、原因、影响和回退方式。

### 4.3 硬件目标单一化

唯一目标硬件为 Panther X2 / RK3566，不建立其他 SoC/板型兼容矩阵。硬件相关组件优先采用明确支持 RK3566 的 Rockchip 资料/代码及 Panther X2 板级资产；通用用户空间组件使用各自上游项目，不为单板 fork 通用工具。

必须保留或验证：
- UART2 串口控制台及跨启动阶段日志；
- TF/SD 读取由启动前 U-Boot proper 完成；Linux B1 不启用 MMC/eMMC/SD/SDIO 控制器；
- Panther X2 板载有线千兆以太网口（仅在 B1 干净基线通过后，按阶段引入并验证）；
- 原有硬件复位功能，不凭外观猜测 GPIO 或改变按键语义；
- RK809/PMIC 电源由启动固件完成必要初始化；B1 不为此引入非启动必需的 PMIC 用户空间或存储组件。

Wi-Fi/无线网络、蓝牙、USB/PCIe 网络适配器及其他非板载有线千兆网口网络设备全部排除，不列为项目 A 候选或后续任务。

### 4.4 RAM initramfs 优先

- 第一阶段根文件系统运行在 RAM。
- 不挂载 TF/eMMC 持久化文件系统作为根，不自动挂载，不写持久化日志。
- 主要证据经 UART 输出。
- `/init` 必须存在、可执行，并明确作为早期用户空间入口（例如 `rdinit=/init`）。
- 按需挂载 procfs、sysfs、devtmpfs、tmpfs。
- Linux block-layer RO 只能作为 Linux 启动后的软件层保护，不能保护 BootROM/SPL/BL31/U-Boot。

### 4.5 可复现构建和证据分级

固定源码仓库、tag/commit、下载地址、SHA-256、工具链、配置和依赖；保存 build manifest、文件清单、构建日志、产物摘要及必要 SBOM。严格区分：
- 静态检查通过；
- CI 构建成功；
- 产物结构/哈希审查通过；
- Panther X2 实机启动成功；
- 网络验收通过。

所有结论标记为：已验证、静态审计确认、待验证、推测/候选。新任务先回读仓库，不重复已完成测试。

## 5. 组件候选边界

### 5.1 Kernel 与 DTB

- 必须使用 Panther X2 专用 `rk3566-panther-x2.dtb`，不得用 E23/E25/ROCK 3C DTB 替代。
- Kernel、DTB、模块和必要固件必须来自匹配版本。
- 干净基线内核必须具备 ARM64、RK3566 SoC、initramfs/initrd、gzip、devtmpfs、UART2 console、必要时钟和 pinctrl 支持；Linux B1 不启用 BLOCK/MMC/eMMC/SD/SDIO、USB、网络协议栈、Ethernet/GMAC、MDIO/PHY、无线/蓝牙或模块。TF 文件由 U-Boot 在 Linux 启动前读取。
- 有线千兆以太网相关 Kconfig 必须建立分类清单，区分启动必需、共享依赖和 Ethernet 专用项。干净基线不编入网络栈及 Ethernet 驱动；后续只对板载 Ethernet 所需依赖闭包逐项审查、引入并记录配置差异。
- Wi-Fi/无线网络、蓝牙及其他非目标网络设备配置一律列入永久排除清单，不进入后续逐项引入计划。
- 目标系列固定为 Linux 6.18.y，不以 6.12 或 6.1 作为项目 A 构建目标。
- 首轮源码构建候选为 ophub/linux-6.18.y commit aee4e352a15d636cbc484f56819c6e59474dfd9f（Makefile 明确为 6.18.63）；这是精确源码输入候选，不等于 CI 构建或 Panther X2 实机验收通过。
- Ophub 6.18.64 预编译包已完成只读审计，其 config 含 CONFIG_NET=y、CONFIG_STMMAC_ETH=y、CONFIG_DWMAC_ROCKCHIP=y、CONFIG_PHYLIB=y、CONFIG_REALTEK_PHY=y，不能作为 B1 干净 Kernel。
- B1 不使用预编译 Image/DTB；必须从锁定源码自建 Kernel，并以独立 allnoconfig + 最小 fragment 生成最终 config。
- clean-test DTB 从同一源码 commit 的 Panther X2 DTS 派生；自动核验 Panther X2/RK3566 model/compatible、UART2 stdout-path，以及 GMAC/MDIO、MMC/SDIO、USB、Bluetooth UART 节点隔离状态。
- 最终 config 必须证明网络栈、Ethernet 驱动、无线/蓝牙、USB、MMC/block、模块和持久化文件系统均未启用；最终二进制与 DTB 需分别提供证据。
- 首轮源码候选只有在 CI 构建、artifact 审查和目标硬件启动安全门完成后，才可锁定为 B1 Kernel+DTB。

### 5.2 Initramfs 与 BusyBox

- 使用小型 gzip initramfs；静态 BusyBox 提供 ash 和最小命令集。
- 首轮 BusyBox 固定为 1.37.0，源码包 SHA-256 `3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4`；构建使用 allnoconfig + 明确 applet fragment，并在 QEMU 下核验 ARM64 静态二进制及实际 applet 清单。
- B1 只建立 `/init` 实际调用的 ash/sh/cat/dmesg/mkdir/mount/tail/uname 命令链接，不建立完整 applet 链接树；网络 applet 必须不存在。
- `/init` 短小、可读、可审计；只挂载 procfs/sysfs，不探测或挂载持久化存储。
- BusyBox 不是正式系统用来替代 Debian/Ubuntu 用户空间的决定。

### 5.3 板载有线千兆以太网工具按阶段引入（干净基线不预置）

干净基线不包含网络用户空间工具。项目 A 后续网络验证只针对 Panther X2 板载有线千兆以太网口。只有当必要内核网络子系统、板载 Ethernet MAC/GMAC 驱动及其依赖已分别通过前置验证后，才按单变量计划逐项引入 ip、ARP/ICMP、TCP/UDP 工具。Wi-Fi、蓝牙及其他网络设备永不纳入后续引入。不得为了避免重建镜像而把尚未验证的网络工具提前塞入干净基线；每次新增工具均记录版本、依赖、二进制属性和行为验证。

| 功能 | 镜像策略 | 启用/验收阶段 |
|---|---|---|
| 接口、链路、地址、路由 | 预置最小 `ip` 能力；先验证 BusyBox `ip`，缺功能再引入必要 iproute2 | B2，逐项启用 |
| ARP/ICMP | 预置最少可用工具或 BusyBox applet；必要时预置 `arping` | B2，分别验收 |
| 只读接口状态查询 | 初始不强制加入 ethtool；确有信息缺口再单独引入正式稳定版 | B2/B3 按需，单独验证 |
| TCP/UDP | 可预置 BusyBox nc 或经审查的轻量工具；不启动监听、不执行收发 | B3，TCP 与 UDP 分开验收 |
| DHCP/DNS | 不预置、不作为静态连通性前置条件 | B4 有明确需求时分别评估 |
| SSH/NetworkManager/systemd/udev | 不预置、不启动 | B4 有明确需求时逐项评估 |
| tcpdump | 初始不预置；优先由外部主机抓包，确有缺口再单独评估 | 条件触发 |

禁止因工具已预置而在 B1 提前执行 B2/B3 测试。工具缺失或功能不足时，先证明缺口，再单独改变组件集合；不得与内核、DTB、驱动或网络配置同时变更。

历史候选版本不自动构成当前锁版。每个工具在实施阶段重新核实上游稳定版本、依赖和构建选项。

### 5.4 构建与打包

- 使用独立手动触发 workflow `.github/workflows/build-panther-x2-b1-clean-ram.yml`，不覆盖完整 Armbian 构建流程。
- workflow 从锁定源码构建 Kernel、派生 clean-test DTB、构建静态 BusyBox 和 gzip initramfs；旧的预编译包/hybrid workflow 已禁用并仅留作历史记录。
- 6.18.63 在 CONFIG_NET=n 下的 kobject_uevent stub 需应用一项最小兼容补丁：无网络分支拒绝非空 skb、对空指针直接返回，不引用网络 skb 释放函数；该补丁不启用网络栈或修改 Ethernet 驱动，必须随构建输入和哈希一起审计。
- 产物仅包括 Kernel、DTB、initramfs/uInitrd、boot.scr、JP proper 参考文件、manifest、文件清单、SHA-256 和构建日志；不生成 raw/hybrid 磁盘镜像，不写 TF/eMMC。
- eMMC pre-Linux 安全门未通过前，CI artifact 只能标记 PREPARE-ONLY，不得写卡或实机启动。

## 6. 启动介质、Vendor 数据与安全边界

### 6.1 启动介质目标

当前测试使用已有 eMMC 前级 SPL + TF JP proper 路径；长期目标是正式系统从 eMMC 启动，TF 作为开发/救援介质。TF 能否实现 BootROM→SPL→proper 完整自包含，必须服从 RK3566 BootROM 规则和 Panther X2 板级硬件事实。已有证据显示普通 BootROM 启动优先级 eMMC 高于 SD；`SDMMC0_DET` 不是启动源选择脚；旧式 IDB card flag 或 Android BCB recovery 标记不能当作通用 TF 冷启动开关。

不得清除 eMMC IDB、改写 boot area/EXT_CSD、短接或拆焊来试验 TF 启动。若后续找到原厂 eMMC 隔离/启动选择硬件机制，再评估 TF 完整启动；若没有，明确接受硬件限制，不把未实现目标写成既定方案。

### 6.2 Vendor 数据原则

现有只读解析记录发现 eMMC Vendor Storage 中有 LAN_MAC 条目 ID=3、12 bytes，包含两个网口 MAC。Rockchip 参考实现将 Vendor Storage 放在 eMMC user area LBA 7168 起始的 4 份 64 KiB 副本；当前四份副本逐份有效性仍需只读核验。

长期 U-Boot 设计必须只读明确的 eMMC 权威 Vendor 数据，校验格式、版本、长度、校验和、MAC 合法性及顺序，通过标准 U-Boot 环境/FDT fixup 传给 Linux。读取失败明确报错，不随机生成并冒充板载 MAC；不自动修复、迁移或写回 Vendor Storage；仓库不公开真实 MAC 字节。

### 6.3 实验介质安全

- 8GB SU08G 是指定实验 TF，CID：`035344535530384780b16ad9b700c15f`，sectors：15,523,840。用户已授权清空该卡，但每次破坏性操作前仍须重新核对 CID、型号、容量、设备节点和挂载状态。
- 64GB SD64G 对照卡保持原样，不格式化、不分区、不写入。
- eMMC DF4032 保持只读，不擦除、不重分区、不替换 IDB，不修改 boot area、EXT_CSD、Vendor Storage 或原系统。
- 仅在用户逐次明确授权后，才执行写 TF、启动实验系统或硬件写保护设置。
- eMMC 芯片级 power-on write protect 的支持、覆盖范围和实际保护状态尚未完成验收；不得假设已启用。
- Linux `blockro` 不能替代 pre-Linux 写保护。

B1 写卡/启动放行前必须完成实际执行 eMMC SPL/前级资产身份核对、自动写入路径审计或经验证的硬件隔离保护、eMMC 各区域写入目标矩阵、异常/回退路径分析，并取得本次操作授权。任一项不清楚即停止。

## 7. 阶段总览（B0—B7）

| 阶段 | 名称 | 目标 | 当前状态 |
|---|---|---|---|
| B0 | 基线与安全前置审计 | 固定启动入口、Linux 资产候选、介质身份和 eMMC 安全边界 | 部分完成；安全门未通过 |
| B1 | 最小 RAM Linux 干净基线 | 进入 `/init`，UART shell 可交互；Linux 不启用网络、Ethernet、MMC/block、USB、无线/蓝牙和模块，根文件系统完全在 RAM | 构建流程已提交；CI/实机未验证 |
| B2 | 板载有线千兆网口分层验证 | 仅对板载 Ethernet 的内核网络基础、MAC、MDIO/PHY 依赖按单项引入；再验证 link、静态地址、ARP、同网段与网关 ICMP | 未开始 |
| B3 | 板载有线千兆网口 TCP/UDP 验证 | 仅通过板载有线千兆网口进行 TCP 与 UDP 双向端到端验证，分开测试且结果可重复 | 未开始 |
| B4 | 网络组件按需扩展 | 根据明确需求加入 DHCP/DNS/SSH 等 | 条件触发 |
| B5 | 长期 U-Boot 与启动架构评估 | 候选源码、配置、板级适配、安全和恢复比较 | B1—B3 后启动 |
| B6 | 最小正式用户空间与上游体系融合 | 从 RAM 验证环境逐层迁移到可维护 rootfs | 后续 |
| B7 | 长期运行能力与其他项目衔接 | 存储、温控、NPU/RKNN、容器、Immich 等独立评估 | 后续 |

## 8. 当前状态与下一步

### 已验证（有直接实机证据）
- Panther X2 曾通过现有 eMMC 前级 SPL 启动 JP-TvBox U-Boot proper。
- JP proper 曾从 TF ext4 分区加载 Kernel、DTB、uInitrd 并进入 Linux。
- BootROM source tag 的一次实机只读读取指向 eMMC；SPL 后续从 MMC2/TF 加载 proper。
- 设备为 RK3566、4GB LPDDR4；历史启动日志记录双 CS/rank 参数。
- SU08G 8GB TF 的 CID/name/sectors 已识别；已确认两个分区卸载。

### 静态审计确认
- eMMC Vendor Storage 存在 LAN_MAC ID=3、12-byte 双 MAC 项；真实 MAC 不公开。
- Rockchip 参考实现 Vendor Storage 起点为 eMMC user area LBA 7168，4 份 64 KiB 副本。
- 6.18.64 预编译包的实际 config 含 `CONFIG_NET=y`、`CONFIG_STMMAC_ETH=y`、`CONFIG_DWMAC_ROCKCHIP=y`、`CONFIG_PHYLIB=y`、`CONFIG_REALTEK_PHY=y`，不能作为 B1 干净 Kernel。
- 首轮 B1 源码候选为 6.18.63 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`；尚待 clean config/build/DTB/artifact 验证。
- Linux block-layer RO 与 pre-Linux 写保护属于不同保护层。

### B2-0 方向二：Linux 网络核心静态审计状态（2026-11-25）
- 原始范围内明确列出的 generic network-core 子项 §3～§24、§26 已完成四版本源码/Kconfig/已有配置静态审计；四版本矩阵、普通 DHCP/UDP TX 适用性与证据等级见方向二报告 §53。
- §54 完成报告内部一致性审校；§55 完成结项条件评估；用户于 2026-11-25 明确批准“证据边界明确的有条件结项”，正式结项记录见方向二报告 §56。
- **当前状态：方向二已结项（证据边界明确）。** 6.1.65/6.1.116 来源绑定、6.1.174 历史 config 缺口及运行时队列/特殊 skb 证据限制均按 §55.2 保留；不重复已完成 generic network-core 审计。
- 按 B2-0 原顺序进入方向三 STMMAC/DWMAC4/DMA 驱动核心静态审计。D3-1 platform probe/resource parsing 与 D3-2 MDIO/PHY attach 四版本静态审计均已结项；D3-2 确认黄金版本有、故障版本缺失的四次 PHYCR2/BMCR MDIO 写入差异，保留为待关联候选，不认定根因。D3-1 至 D3-4 已按静态源码范围结项。D3-3 确认黄金版本 DMA reset 前有 1500ms delay、实际故障源码缺失，reset poll interval 从 10ms 缩短至 0.5ms；DWMAC4 DMA/AXI/PBL/channel init 软件逻辑总体相同，硬件 addr64 运行时值保留未知。D3-4 确认 6.1.65 TSO 多 descriptor mapping 记录过早 unmap 风险、后续版本已修复；TX coalescing timer 默认值 1000→5000us，普通 DHCP 单 skb 不命中 TSO 条件分支。D3-5 RX descriptor/buffer/page-pool 四版本静态审计已结项：page-pool create/refill、DMA sync、普通 skb allocation failure 和 DWMAC4 RX OWN/status 未发现可解释普通 DHCP RX 丢失的无条件回归。D3-6 DMA API/coherency/IOMMU 四版本静态审计已结项：普通 streaming cache sync 四版本一致；GMAC1 无 dma-coherent/iommus，按 non-coherent direct DMA path；6.12 coherent prep 的 clean-only 变化不包含实际 6.1.174 故障源码，且有 ARM64 DMA API 设计理由；6.12 unaligned kmalloc bounce 条件不命中普通 DMA_TO_DEVICE。D3-7 STMMAC IRQ/NAPI/watchdog/recovery 四版本静态审计已结项：DMA status RI/TI/TBU/FBE/TPS 处理、NAPI schedule gate、timeout/global reset 与 per-channel recovery 顺序未发现普通 DHCP 的无条件阻断回归。D3-8 四版本总矩阵与一致性审校已完成。**方向三 D3-1～D3-8 静态技术审计已于 2026-11-25 按“证据边界明确的有条件结项”正式归档**，详见 `PANTHER-X2-B2-0-DIRECTION-3-CLOSEOUT-20261125.md`。未验证的源码 provenance、历史 config 与运行时证据边界继续保留，不重复已完成审计。按 B2-0 原顺序推进方向四 Rockchip GMAC glue / CCF / CRU / clock / reset（原组件方向 B2-3）。已完成四版本 GMAC clocks enable 主路径、CRU mux/gate/reset、CCF/PLL、probe/setup/power handoff 与 RGMII callback 首轮核对；识别出 bulk/逐项 enable 与错误检查、5ms/100–200µs 等待、RGMII GRF 写入顺序差异；补齐 HCLK_USB/PCLK_USB 两项 critical flag 的四版本差异，并区分 HCLK_USB 不在 GMAC1 parent chain、PCLK_USB critical 经 CCF parent recursion 保持与 GMAC1 共用的 ACLK_USB 父链；若 ACLK_USB 实际选择 GPLL 且当时 GPLL enable reference 为 0，PCLK_USB critical parent recursion 可能触发后期 GPLL callback；历史 parent/reference/时序未验证；HCLK_USB 不在 GMAC1 父链。regulator/runtime-PM 错误传播弱点为四版本共有项。方向四已完成与方向二 generic network-core、方向三 STMMAC/DWMAC4/DMA 的跨层一致性审校：两组 delay 分属不同调用层；STMMAC pclk/pclk_mac 不等同于 CRU PCLK_GMAC1/ACLK_GMAC1；未发现跨方向结论冲突。**方向四（原组件方向 B2-3）已完成既定静态审计范围，并于 2026-11-25 按“证据边界明确的有条件结项”正式归档**，详见 `PANTHER-X2-B2-0-DIRECTION-4-ROCKCHIP-GMAC-GLUE-CCF-CRU-AUDIT-PROGRESS-20261125.md`。补齐内容包括四版本 RGMII speed callback rate mapping、powerdown/suspend/resume 适用性、最终总矩阵及方向二/三跨层一致性。主要版本差异为 bulk→逐项 clock 获取/enable 与错误检查减弱、5ms→100–200µs settle、RGMII GRF 写入顺序反转、HCLK_USB/PCLK_USB critical flags 与后期 GPLL callback；这些均为源码差异或条件性候选，不是已证实 TX 根因。GMAC1 专属 CRU mux/gate/reset mapping、Panther DTS RGMII 输入配置及 speed-rate mapping 未发现确定性故障回归；regulator/runtime-PM 错误传播是四版本共同弱点。历史 clock enable/clk_set_rate 返回值、ACLK_USB 实际 parent/GPLL reference、GRF/PHY 波形和电源状态仍未验证。**方向五（原组件方向 B2-4）MDIO/PHYLIB/PHYLINK/RTL8211F 已于 2026-11-25 开始只读静态审计，尚未结项**，首轮四版本 Realtek PHY driver、paged MDIO API、PHYLIB 状态机、PHYLINK RGMII mode 与 6.18.63 目标 PHY driver 差异见 `PANTHER-X2-B2-0-DIRECTION-5-MDIO-PHYLIB-PHYLINK-RTL8211F-AUDIT-PROGRESS-20261125.md`。重点保留：历史四版本普通 RTL8211F 初始化主路径基本一致；6.18.63 新增 PHY-mode EEE bit5 清除、默认 config_init 不再无条件 soft reset、speed status 改读 MII_RESV2，以及 suspend/resume 新逻辑。以上均为静态源码差异，不证明运行时 PHY 状态或 TX 根因。方向五已完成 15 份既有 PHY 专题报告交叉审校、PHYCR2 0x1801 完整位域与执行顺序边界澄清、PHYLIB autoneg/status/start/stop 及 PHYLINK connect/disconnect/MLO_AN_PHY/link callback 覆盖，并形成四版本差异矩阵；关键更正是 Realtek config_init 局部主路径相近不代表完整 PHY 初始化序列相同，6.1.65/116 的 STMMAC 前置 workaround 与 6.1.174/6.12 缺失差异必须保留。6.18.63 的 bit5 单 bit EEE 清除不能等同恢复 0x1801。方向五仍需完成证据等级/版本边界综合与正式有条件结项评估。B2.1 未启动。 主要待关联候选为黄金版本的四次 PHY MDIO workaround 写入及 DMA reset 前 1500ms delay（故障源码缺失），以及 MDC CSR clock source 变化；均缺少现场 PHY/clock/reset 证据，不认定根因。方向四已按证据边界明确的有条件结项归档；方向五正在进行只读静态审计，尚未结项；B2.1 仍未启动。

### 尚未验证
- B1 clean Kernel/DTB/BusyBox/initramfs workflow 能否成功构建；
- clean Kernel/DTB/initramfs 组合能否在 Panther X2 启动；
- B2/B3 静态网络与 TCP/UDP 连通性；
- eMMC 芯片级写保护能力和完整覆盖；
- JP proper 新系统重复启动稳定性；
- 长期 U-Boot 候选完整板级适配。

**当前唯一优先事项：** 静态审查并运行新 B1 clean RAM workflow，审查构建 artifact；同时独立完成 B0.4 eMMC pre-Linux 写入安全门。安全门未通过前，不写 SU08G、不启动实验固件、不进行 Panther X2 实机启动。

## 9. 关联文档与维护

- [项目 A 分阶段实施计划](PANTHER-X2-PROJECT-A-IMPLEMENTATION-PLAN-20261121.md)
- [B1 最小 RAM 启动与 eMMC 安全关口审计](PANTHER-X2-MINIMAL-RAM-BOOT-PLAN-AND-EMMC-SAFETY-GATE-20261121.md)
- [P1 initramfs 启动链静态审计](PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)
- [P2 上游用户空间组件审计](PANTHER-X2-P2-UPSTREAM-USERSPACE-COMPONENT-AUDIT-20261120.md)
- [P2 启动架构与 eMMC Vendor 数据审计](PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md)
- [U-Boot 候选研究](PANTHER-X2-UBOOT-CANDIDATE-RESEARCH-20261117.md)
- [U-Boot 启动日志与混合链证据](PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md)

关联资产目录：
- JP-TvBox U-Boot：`docs/research-assets/bootloader/panther-x2/JP-TvBox-U-Boot/`
- Panther X2 原版 U-Boot：`docs/research-assets/bootloader/panther-x2/ophub-original/`
- 最小 initramfs：`scripts/panther-x2-minimal-initramfs/`
- 最小 RAM boot workflow：`.github/workflows/build-panther-x2-minimal-ram-boot.yml`（状态以当前文件和 Actions 实际结果为准）

## 10. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-21 | 建立项目 A 统一名称和唯一权威总路线；明确项目边界、JP proper 测试基线、最小 RAM 启动与静态网络顺序、组件原则、U-Boot 长期评估、安全门和证据分级。 |
| 2026-11-21 | 强化单变量试验纪律；明确组件预置与启用分离、失败即停和证据记录。 |
| 2026-11-22 | 修订项目 A 总目标：B1 必须先建立不含未经验证网络变量的干净基线，GMAC 及其他可能影响网络行为的组件均须隔离；基线通过后按单变量逐项引入。此决定优先于此前允许预置网络工具/驱动的表述。 |
| 2026-11-22 | 项目 A 网络范围收敛为 Panther X2 板载有线千兆以太网口；Wi-Fi/无线网络、蓝牙及其全部相关组件永久排除，不审计、不构建、不测试、不列入后续引入。USB/PCIe 外接网卡亦排除。 |


## 11. 单变量、可归因的试验纪律（2026-11-21 修订）

本节是项目 A 的强制执行约束，优先于本文及旧报告中与之冲突的“每阶段增加组件”或“先纯启动、后重建网络镜像”等旧表述。核心原则：**步子小一点，风险可控。**

### 11.1 干净基线与网络组件隔离（强制前置门）

- B1 第一阶段构建纯 RAM 启动基线：Kernel 网络栈、Ethernet/GMAC/MDIO/PHY 驱动、MMC/block、USB、无线/蓝牙和模块全部关闭；不预置网络用户空间工具、固件或服务。
- Kernel 最终 .config 必须证明网络专用代码未编入；DTB 反编译与结构检查证明 GMAC/MDIO/PHY、MMC/SDIO、USB 和 Bluetooth UART 节点已禁用或从 clean-test DTB 移除；不得用仅禁用 DTB 节点冒充驱动代码已移除。
- Linux B1 只保留 UART2 console、SoC 时钟/pinctrl 和 initramfs 必需支持；不得为了隔离网络而误关闭 UART/SoC 启动依赖。TF 只由 U-Boot 在 Linux 启动前读取，Linux 不启用任何 MMC/block 设备。
- 干净基线通过后，才按组件清单逐项引入网络子系统、设备驱动及最小依赖闭包、用户空间工具。每次只改变一个组件/最小依赖闭包，失败即停并回到最近已验证基线。
- DHCP、DNS、SSH、NetworkManager、systemd、udev、Docker、NPU/RKNN、GPU、Immich、数据库和存储服务继续排除，除非后续有独立需求与批准。

### 11.2 单次试验只改变一个变量

每次试验必须事先写明唯一目标、固定条件、唯一变量、预期结果和停止条件。不得在同一次试验中同时更换 Kernel/DTB/驱动、增加组件、修改网络配置或改变启动链。若必须变更多个项目，拆分为多个独立试验，每次只推进一个变化。

### 11.3 分层推进与失败即停

按启动与设备识别、接口/link、二层 ARP、静态 IPv4/路由、ICMP、TCP、UDP 的边界逐层验证。上一层未通过，不进入下一层；失败先确定故障边界并分析已有证据，不以叠加组件或多项配置“试试看”。

### 11.4 每次试验的记录要求

记录试验编号、目标、基线版本与哈希、硬件/介质身份、固定条件、唯一变量、操作前后状态、完整命令、退出码、UART/kernel 日志、两端收发证据、结果、证据等级、停止原因及唯一建议的下一步。任何结论必须能追溯到本次实际输入与原始证据。

### 11.5 无效试验判定

若一次试验同时改变多个变量，或缺少足够记录以区分变量影响，则该试验不能作为可靠的故障定位证据；应先恢复或重新建立已知基线，再设计单变量验证。不得把相关性直接写成根因。



## 12. 2026-11-22 优先级修订：先建立 U-Boot 网络基准

用户明确调整项目 A 当前优先级：历史版本已证明 Linux 可以启动，当前最重要的未知项是 U-Boot 能否独立打通板载有线千兆网口。**先在当前运行的 U-Boot 会话中完成网络基准实测，再继续 B1 clean RAM Linux；不再要求 B1 通过后才允许 U-Boot 网络验证。** 本修订覆盖第 2 节原先的先后顺序，但不取消 B1 的隔离价值。

新顺序：U-Boot 只读识别 Ethernet/MDIO/PHY → 确认 link → DHCP → ping LAN 网关 → ping 已知外部 IP；随后 B1 无网络 RAM Linux；再到 B2 单变量引入 Linux 网络组件；最后 B3 分开验证 TCP/UDP。

用户已明确授权当前 U-Boot 会话的板载有线网口初始化、DHCP 和基本连通性实测。授权不包含重启、换 U-Boot/SPL、启动新镜像、写 TF/eMMC、持久化环境修改或 MII/MDIO 寄存器写入。禁止 save/saveenv/fatwrite/tftpflash/tftpput/download/fastboot/rockusb/ums、任何存储写入及 boot/source/reset。DHCP help 显示 DHCP/TFTP 组合命令，必须先审计 autoload=no 是否能阻止 TFTP 自动下载；确认前不执行 DHCP。

现场初步证据：help dhcp、help mii、help mdio 已核对；mdio list 实际输出 ethernet@fe010000:，证明一个 MDIO bus 已注册，但 PHY、link、DHCP、IP 连通尚未验证。完整过程见 [U-Boot 网络基准实测记录](PANTHER-X2-UBOOT-NETWORK-BASELINE-20261122.md)。

本修订仅改变验证优先级，不恢复项目 B 的 GMAC/MDIO/PHY 根因专项调查；范围仍仅限板载有线千兆网口。未来重新启动和写介质仍受 B0.4 安全门约束。

## 13. 新增 U0：U-Boot proper 启动完成后的恢复检查点

在当前 U-Boot 网络基准测试前，正式建立 U0（U-Boot post-startup baseline）：当前 proper 已启动并停留在 => 提示符、尚未执行 DHCP/网络连通性测试的状态。当前只完成帮助、环境变量、MII/MDIO 枚举查询；没有 DHCP、下载、存储写入、环境修改或新增测试组件。具体快照见 U-Boot 网络基准实测记录 PANTHER-X2-UBOOT-NETWORK-BASELINE-20261122.md 的 U0 节。

U-Boot 网络测试完成后，必须先恢复临时环境变量和测试产生的临时网络参数，核对启动链、U-Boot proper、提示符及身份变量未改变，再宣布回到 U0。不得把 DHCP 后的环境状态直接带入 B1。无法在不重启/不写存储的条件下恢复的内部运行时状态要如实记录；不允许为了清理而擅自 reset/reboot。U0 回归核对通过后，才继续 B1 clean RAM Linux。

## 14. Linux 首次启动前的 U-Boot 交接强制阶段门

项目 A 正式进入 Linux 前，必须先完成 `PANTHER-X2-UBOOT-LINUX-HANDOFF-INVENTORY-20261122.md` 中所有适用信息项的发送端核查。未核实项不得留空带过；须明确归类为已核实、已核实不适用、Linux重新初始化、有意缺省/已知限制或未核实。存在未核实项、地址冲突、镜像身份不明、最终FDT/bootargs未冻结时，不允许启动Linux。

通过该门后签署 `PRE-HANDOFF READY`，归档同一启动链的固件身份、Kernel/DTB/initramfs哈希与地址长度、最终FDT副本及哈希、bootargs、内存布局、固件接口、硬件资源责任归属和UART证据。首次进入Linux后，再执行独立的 `POST-HANDOFF VERIFIED` 接收端核验。不能在Linux启动前声称Linux已正确接收。

当前U0与U-Boot网络测试完成后的清理/回归要求仍然有效；完成U0回归后，继续交接审计，不得直接跳过阶段门进入Linux。


## 15. 2026-11-22 网络验证策略纠偏：以 6.1.116 正向对照和双端报文为依据

用户指出：若项目 A 仍然依赖源码对照和猜测参数，可能重演项目 B 未能最终定位故障的教训。自本节起，项目 A 的网络验证方法以实机可重复实验、逐层输入/输出证据和双端报文为主，源码/Kconfig/设备树分析只用于确定最小依赖和参数来源，不作为网络成功的替代证明。具体方案见 [分层网络验证方案](PANTHER-X2-NETWORK-LAYERED-VALIDATION-PLAN-20261122.md)。

### 15.1 6.1.116 正向控制

仓库既有 6.1.116 记录确认：Panther X2 的 eth0 / fe010000.ethernet 使用 rk_gmac-dwmac，PHY 为 RTL8211F（PHY ID 0x001cc916），RGMII，曾验证 1000Mbps Full Duplex；用户确认 DHCP 获得 LAN IPv4，ping hEX 和 iMac 均 0% 丢包，错误/丢弃计数为 0。原始脱敏网络采集文本、内核配置、dmesg、运行时 FDT 和磁盘 DTB 已归档。该结果是 Linux 正向控制，禁止重复采集/重复跑已完成的泛化网络测试。

原版 U-Boot 曾输出 `Net: No ethernet found.`，而后续 Linux 6.1.116 能独立初始化网卡并正常通信。这支持 U-Boot 不枚举/不初始化网卡不必然阻止 Linux 自行初始化。历史前级 SPL/proper 二进制身份未完全闭环，因此不得称为与当前混合启动链同条件对照。

### 15.2 当前 JP proper 的 DHCP 异常及证据边界

2026-11-22 用户在 `autoload=no` 已读回确认的情况下执行 `dhcp`，首先出现 `EQOS_DMA_MODE_SWR stuck`，随后发生 AArch64 Data Abort 并停在 `Please RESET the board`。没有 DHCP 成功结果、DHCP 报文往返、TFTP 下载或存储写入证据。该结果只证明本次 U-Boot 网络初始化/命令路径在 EQOS DMA 软件复位等待阶段附近异常退出；不能判定 PHY/GMAC 硬件损坏、DHCP 服务器故障或 Linux 网络必然受影响。禁止重试 DHCP，不恢复 U-Boot GMAC 根因专项。

异常后实体 Reset 未恢复；断电重启恢复 U-Boot proper。重启后重新核对：proper 版本与原基线一致；ethaddr 不变；ethact/ethprime/autoload 及 ipaddr/serverip/gatewayip/netmask/bootfile 均未定义；bootcmd/bootdelay/distro_bootcmd/boot_targets 与 PXE/DHCP 自动启动入口已读取。当前 U0 为“身份和环境快照部分恢复”，尚未重核 MDIO/MII 设备枚举，不宣布完整 U0 回归。bootdelay=0 且 boot_targets 包含 pxe/dhcp，后续启动必须先运行已验证的 UART 自动 Ctrl-C 脚本，再上电；不能人工抢按。

### 15.3 对 Linux 独立初始化的含义

6.1.116 正向对照表明 Linux 曾在原版 U-Boot 不枚举 Ethernet 的情况下自行初始化并正常通信；因此 U-Boot 网络功能不是 Linux 网络可用的必要条件。当前 JP proper 的 DMA 异常与原版 U-Boot 的“未枚举网卡”不是同一现象。断电重启会重新启动硬件/启动链，冷启动后 Linux 成功只能证明该启动组合下 Linux 能独立初始化，不能证明 U-Boot DMA 异常后同一启动周期内的硬件残留状态无影响。项目 A 不为证明这一点重试崩溃路径。

### 15.4 B1/B2/B3 实际网络验证方法

- B1：纯 RAM、无网络基线，只验证启动、UART、内存和 BusyBox/initramfs；不预置网络工具/服务。
- B2：依据目标源码 Kconfig/Makefile 实际依赖，逐个引入最小依赖闭包；从网络核心、Ethernet MAC/stmmac-Rockchip、MDIO/PHYLIB/目标 PHY、板级 Panther X2 DTB资源，到 Link、静态 IPv4、ARP、ICMP，逐层推进。每层未通过不进入下一层。
- B3：TCP、UDP分别验证双向 payload。
- 参数必须有 Panther X2 板级 DTB、6.1.116 正向基线、目标驱动资源和实机日志来源；不得从 ROCK3C FDT 猜参数。
- 每个网络测试均需 Panther X2 端、LAN 对端和返回方向的证据；驱动 probe、carrier、TX/RX计数增长不能单独作为成功判据。ARP/ICMP/TCP/UDP 的报文到达/响应/接收要分别证实。
- DHCP、DNS等高层服务推迟到静态 IPv4、ARP、ICMP验证通过后。

### 15.5 阶段顺序与当前门槛

当前 JP proper U-Boot DHCP 测试因异常挂起，不再阻挡或替代 Linux 分层网络验证；但 Linux 首次启动仍必须先通过第14节 PRE-HANDOFF READY。先完成本轮异常和重启后快照归档、6.1.116正向对照整理及交接发送端审计，再启动 B1。B1通过后再进入 B2/B3，不提前启用网络组件。


### 15.6 B1 启动脚本与 TF 旧版本隔离（2026-11-22）

静态审查发现旧 `boot.cmd` 在加载失败时调用 `reset`，已从仓库版移除；但此前实机检查记录中的 TF `boot.scr` 仍为旧版本，不能因 Git 提交而视为已更新。当前不得执行旧 TF `boot.scr`。新 artifact 必须重新构建、审查、哈希锁定，且不能绕过 eMMC pre-Linux 写入安全门和单独授权。

旧 U-Boot 会话记录的 Kernel/FDT/initramfs 地址在 DHCP异常后断电重启，尚未绑定当前会话；旧 TF Kernel/uInitrd 的文件身份哈希也未闭环。因此 PRE-HANDOFF READY 仍未通过。B1 首次启动保持暂停，先完成新 artifact 与当前启动地址/内存布局审计。


## 16. 2026-11-22 6.18.y 网络配置不得作为正确基线：正向对照与故障归因策略

用户明确提醒：如果项目 A 直接沿用 Ophub 现有 6.18.y 的完整配置，Panther X2 网络很可能仍然不通；这也是启动项目 A 的原因。该提醒作为**风险前提和审计约束**记录，不将“6.18.y 必然故障”升级为已完成的根因结论；当前尚无一份在同一启动链、同一硬件条件下完成的 6.18.y 实机端到端失败报告。

### 16.1 禁止把 Ophub 6.18.y 当作正确答案

- Ophub 6.18.y 的 Kernel config、Panther X2 DTB、DTS、驱动和 patch 集只能作为待审计对象，不是可直接复用的已验证配置。
- CONFIG_STMMAC_ETH=y、CONFIG_DWMAC_ROCKCHIP=y、CONFIG_PHYLIB=y、CONFIG_REALTEK_PHY=y 或成功 probe/识别 PHY/Link Up 均不构成网络正确性证明。
- 不允许因 6.1.116 成功就把其全部旧配置、补丁或参数原样复制到 6.18.y；也不允许因 Ophub 6.18.y 是当前发行配置就默认它正确。
- 6.1.116 是行为正向基线；Ophub 6.18.y 是风险审计对象；Panther X2 原始板级 DTS/原厂资料用于确认板级连接。三类证据不可互相替代。
- SoC/板级硬件参数必须来自 Panther X2 专用 DTS、历史成功运行时 FDT、磁盘 DTB和有来源的实测，不得从 ROCK3C 等其他 RK3566 板级配置推断。

### 16.2 新增审计的核心问题

审计不以“找一套看起来正确的配置”为目标，而要确定 6.18.y 里**第一个与已知正常行为发生实质分歧的边界**。依次检查：

1. **资产身份：** 目标 6.18.y 的确切源码 commit、实际发布包、Image、最终 .config、Panther X2 DTB、patch 集和构建日志能否一一对应。Release asset 未下载、哈希未闭环的版本不得作为实测对象。
2. **板级设备树：** 历史 6.1.116 running FDT 与磁盘 DTB差异；6.18 Panther X2 DTB与之的结构差异；只比较目标相关节点和属性，不将全树差异误当故障。
3. **内核配置与依赖：** STMMAC/DWMAC Rockchip、PHYLIB/Realtek、phylink、DMA、clock/reset/pinctrl/regulator、网络核心及相关 Kconfig 依赖的 built-in/module/disabled 状态；配置存在不等于运行时路径正确。
4. **驱动行为变化：** 对照确切版本的 dwmac-rk.c、stmmac_main.c、stmmac_platform.c、stmmac_mdio.c、DWMAC4 DMA/descriptor、realtek.c 及相关 Rockchip clock/reset/GRF 代码；只把命中 Panther X2 实际 RGMII/RTL8211F/fe010000 路径的差异列为高优先级。
5. **初始化时序与硬件状态：** probe、MDIO PHY attach、PHY reset/power、RGMII clock/delay、DMA reset、DMA ring、MAC enable、link-up 回调和接口 open 的实际先后关系；不凭单条日志推断整个链条。
6. **真实报文边界：** 只有在 B1/B2 准入后，才能通过分层实机试验判断报文从协议栈、DMA descriptor、MAC、RGMII、PHY、网线、交换机到对端，以及响应返回的第一个失败边界。TX 统计、tcpdump 本机可见、carrier、DHCP timeout均不能单独定位物理边界。

### 16.3 6.1.116 正向基线的使用方式

6.1.116 只作为“相同 Panther X2 曾实现过何种行为”的参照：
- 固定其历史 Image/DTB/running-FDT/config/dmesg 与网络实测证据；
- 把可观察行为转化为 B2 的分层验收预期；
- 逐项比较目标 6.18 的实现与正向基线，找出候选差异；
- 每个候选差异必须说明它是否进入当前 Panther X2 实际执行路径，以及怎样通过单变量实验验证；
- 不复制未证明必要的历史补丁、驱动、配置或用户空间组件。

### 16.4 B1/B2 实施原则

- B1 仍是无网络的纯 RAM 启动基线。可按最新路线预置后续验证需要的最小工具，但 B1 不启用网络栈、接口、地址/路由，不发送网络流量。
- B2 从已通过的 B1 镜像出发，逐个加入网络协议核心、板载 GMAC 驱动与最小共享依赖、MDIO/PHY、目标 DTB 节点；每轮只有一个明确变量或一个源码/Kconfig 证明不可再拆的最小依赖闭包。
- B2 先验证接口和 PHY/link，再用静态 IPv4、ARP、ICMP建立可观测边界；不以 DHCP 作为首个网络测试。
- B3 单独验证 TCP 与 UDP双向 payload；不能以 ping、link up 或计数器增长替代。
- 失败后停在第一个失败边界，保留全部原始日志与两端抓包，回到最近通过检查点；禁止同时改 DTB delay、reset、clock、DMA 参数或叠加 workaround。
- 任何 workaround 只能在根因证据形成后，作为单独假设、单独 patch、单独试验；不得先加补丁再把结果当成根因证明。

### 16.5 本轮结论状态

- **已确认：** 6.1.116 Panther X2 有线网络曾端到端正常；项目 B 已有多个版本网络异常的历史证据；Ophub 6.18.y 的现有配置尚未通过 Panther X2 B2/B3 端到端验收。
- **用户提供的强风险判断：** 直接照搬 Ophub 6.18.y 配置，大概率无法打通网络。作为本项目的审计前提，不改写成已证实的具体故障根因。
- **未确认：** 6.18.y 究竟是哪一项板级 DT 属性、Kconfig、驱动代码、patch/config 组合、初始化顺序或硬件交接状态导致网络失败。
- **执行要求：** 先完成 6.1.116 正向基线与候选 6.18 发布资产的静态差异矩阵，再按 PRE-HANDOFF 安全门启动 B1，之后才允许 B2 的单变量实机归因。不得将 Ophub 6.18.y 原样配置直接作为 B2 终态。

### 16.6 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-22 | 将 Ophub 6.18.y 明确列为待审计对象而非正确基线；以 6.1.116 实机正向行为作为对照，要求定位 6.18.y 首个失败边界，禁止照搬整套配置、盲目复制旧参数或先叠加 workaround。 |


## 17. 2026-11-22 基线优先级修订：原始 6.1.65 是首要黄金基线

用户指出：当前机器运行的 6.1.116 是经过多个版本升级后形成的环境，不能将其视为原始出厂/首次安装软件状态；网上另找一台运行 6.1.116 的 Panther X2，也不能替代用户自己保存的原始刷机包。该判断成立，项目 A 的基线优先级据此修订。

### 17.1 基线层级

1. **第一黄金基线：用户持有的原始 6.1.65 完整 Armbian IMG。** 这是本机最早刷机软件的直接原件，也是后续重建软件来源和原始行为的首要参照。镜像 SHA256：`0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`；gzip 内部 IMG 名 `Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img`；解压长度 2,969,567,232 bytes。用户称其为原始刷机包，并已确认当年采用 RKDevTool Boot + System 流程安装到 eMMC。
2. **第二黄金基线：用户设备当前保存的 6.1.116 相关原始归档与实机记录。** 它证明同一台物理设备在后期某个状态下曾实现端到端网络正常，但经历多个版本升级，可能包含 kernel、modules、DTB、rootfs、boot config、U-Boot/SPL 的历史变化。不得把它称为原始系统状态，也不得默认它与 6.1.65 的启动链相同。
3. **第三类参考：网络上其他设备的 6.1.116 或 Ophub 6.18.y 发布资产。** 只作为外部源码/配置/行为比较样本，不可替代用户原件或本机实测。

### 17.2 原始 6.1.65 目前已闭环的事实

- 原始压缩镜像本体 SHA256 和 gzip 内部 IMG 名、时间、大小已由用户 iMac 只读核验；gzip 完整性通过。
- 原始镜像 GPT 和 BOOT ext4 分区结构已读取。
- BOOT 内含 `Image`、`vmlinuz-6.1.65-ophub`、`uInitrd`、`uInitrd-6.1.65-ophub`、Panther X2 专用 `rk3566-panther-x2.dtb`、`armbianEnv.txt`、`boot.cmd`、`boot.scr`。
- `armbianEnv.txt` 的 `fdtfile` 指向 `rockchip/rk3566-panther-x2.dtb`；`boot.scr` legacy header 与 CRC 通过，payload 与 `boot.cmd` 正文一致。
- 原始 Panther X2 Linux DTB 根节点声明 `model = "Panther X2"`、`compatible = "panther,x2", "rockchip,rk3566"`；GMAC1 节点 `fe010000` 启用，RGMII、clock input、TX/RX delay `0x30/0x10`、PHY 地址0、GMAC1 M0 pinctrl、外部 125MHz 时钟设计及 PHY 供电/reset 引用均已静态解析。
- 已有 6.1.65 原始 DTB 与 6.1.116 正常基线的 GMAC 专项交叉核对：两者的 GMAC 主节点语义、M0 pinmux、电气 drive/pull 配置和 125MHz clock-parent 设计高度一致。当前没有证据支持先替换 Panther X2 GMAC DTB。
- 原始镜像内偏移 `0x800000` 处的 FIT 默认配置包含 Radxa E25 / RK3568 的 U-Boot FDT payload；此对象是 FIT 中 U-Boot proper 所用 FDT，不是 Linux 启动脚本实际指定的 Panther X2 Linux DTB。两者不可混为一谈。

### 17.3 仍未闭环的原始来源链

- 尚未找到用户 6.1.65 IMG 的可验证公开原始下载 URL/发布页/发布者 checksum。公开可见的同项目相邻版本为 6.1.74，不可冒充 6.1.65 原件。
- `lintao1890/panther-x2-armbian` 是 Ophub fork/衍生项目，README 说明 kernel 更新机制接入 `ophub/kernel`；但不能据此证明 2023-12-07 的具体 6.1.65 Image、U-Boot、SPL 都由某个 Ophub commit 原样构建。
- 原始镜像 rootfs 中 `/lib/modules/6.1.65-ophub`、`modules.dep`、`modules.builtin`、内核 IKCONFIG/外置 config 尚未完整索引，Image/modules/config 对应关系未闭环。
- 原始 FIT 默认配置中的 U-Boot FDT 身份已知，但当年 RKDevTool Boot 栏实际选择的 Loader 文件无法回忆；现存三个 Loader 候选不能仅凭名称/DDR 字符串推定哪一个曾刷入。用户已确认 RKDevTool Boot + System 流程，但 Loader 精确身份、写入地址/介质和当年完整刷写配置仍未知。
- 当前 eMMC 在本次研究中曾进行过实验性 IDB 替换；当前 U-Boot 版本和 control FDT 不能自动代表 6.1.65 原始启动链。

### 17.4 项目 A 的研究顺序调整

1. 先完整恢复原始 6.1.65 镜像内部所有可验证来源：BOOT 文件、Kernel Image、DTB、initramfs、rootfs、modules、config、network userspace、FIT/Loader 元数据；建立文件哈希与版本对应关系。
2. 追踪 `lintao1890/panther-x2-armbian` 在 2023-12-07 前后的源码、workflow、构建脚本、release/Actions、依赖仓库和 `armbian-update` 版本；对 kernel 二进制来源必须追到确切 commit/build inputs，否则明确标为 unknown。
3. 查明原始 6.1.65 rootfs 中网络管理方案和服务配置，判断原始网络行为依赖哪些 userspace 服务/配置；不能将 6.1.116 后期系统中的 NetworkManager/netplan/interfaces 等状态倒推到原始系统。
4. 对照 6.1.65 原始内核源码/配置与当前候选 6.18.y，先做静态差异和依赖矩阵；6.1.116 只用于同一硬件曾正常工作的补充行为参照。
5. 只有在原始资产身份和 PRE-HANDOFF 安全门闭环后，才考虑恢复原始 6.1.65 软件栈进行实机复测。当前不因“黄金基线”定义而自动授权重刷 eMMC。
6. B1/B2 的最终实验仍遵循最小 RAM 系统、逐层单变量与双端抓包；原始 6.1.65 是软件/板级来源和正向行为的主要参照，不意味着把旧系统整体复制为项目 A 最终镜像。

### 17.5 证据标签

- **已确认：** 用户持有的 6.1.65 IMG 是其明确指定的最早原始刷机包；镜像本体哈希、BOOT 分区、启动配置和 Panther X2 Linux DTB 的关键属性已读取。
- **已确认：** 用户当前机器的 6.1.116 是后期升级状态；它不能单独代表首次安装状态。
- **已确认：** 6.1.65 与 6.1.116 的 GMAC DTB 核心配置高度一致；目前不把 GMAC DTB 当作首要故障差异。
- **未确认：** 原始镜像官方发布 URL/checksum、确切 build commit、原始 Loader 身份、rootfs modules/config/network service 完整清单、原始 eMMC 最终启动链。
- **强制约束：** 后续报告、实验矩阵和结论中，6.1.65 原始镜像列为第一黄金基线；6.1.116 标注为同机后期正常运行参照；外部 6.1.116 标注为第三方样本。

### 17.6 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-22 | 根据用户指出的版本升级历史，正式将用户原始 6.1.65 完整镜像设为第一黄金基线；将本机 6.1.116 降为后期同机正常参照；将网络上其他 6.1.116 降为外部样本。 |


## 18. 2026-11-22 原始 6.1.65 来源链阶段性闭环

原始 6.1.65 的来源追踪取得进展，详见 `PANTHER-X2-ORIGINAL-SOFTWARE-IMAGE-PROVENANCE-20261120.md` 第26—27节。

- 用户原始 IMG 的构建元数据指向 `ophub/kernel`、`kernel_stable`、`stable`，Panther X2 model_database 将内核 family/tag 设为通用 `6.1.y`，不是 `rk35xx` 专用内核包线。
- 2023-12-07 前最近的 Panther X2 Armbian fork 源码候选为 `31b1b96f258a6d66ecaf8a719145860b533100f6`；它的 workflow 先以 Armbian build 的 `odroidn2` Jammy 基础镜像构建，再调用 Ophub Rebuild action 生成 Panther X2 镜像。
- 对应 kernel source 的强候选为 `unifreq/linux-6.1.y` commit `4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`（2023-12-03，up to 6.1.65）。同一时间窗口没有发现 stmmac/DWMAC Panther X2 专用新改动。
- 当时可见的通用 `config-6.1` 模板标记 6.1.63；2023-12-08 才更新为 6.1.66。模板包含 STMMAC、DWMAC_ROCKCHIP、PHYLIB、REALTEK_PHY 等 built-in 选项，但原始 6.1.65 最终 `.config` 尚未直接抽取，不能将模板等同最终配置。
- Panther X2 的专用 DTS 在候选源码快照中存在，GMAC1 fe010000/RGMII/PHY0/125MHz/pinctrl/reset/delay 配置与已核验原始 DTB一致。
- 公开 Armbian Panther X2 archive 目前只见 6.1.50；同项目公开 Release 只见 2024-01-22 的 6.1.74。均不是用户 6.1.65 原件。尚未找到 6.1.65 同哈希公开副本、Actions run 或官方 checksum。
- Rebuild workflow 的 Armbian build、Ophub action、U-Boot、firmware 多处引用浮动 `main`，所以仅凭项目 commit 仍无法完整复现当日所有构建输入；U-Boot/Loader 精确身份仍未知。

**当前基线判断：** 6.1.65 已有较强的源码/配置/板级 DTS 候选来源链，但 Image 二进制与具体构建 commit/config 尚未实现密码学级绑定。它仍是项目 A 第一黄金基线；6.1.116 只作后期同机正向行为参照。

**下一步：** 从用户原始 IMG 本体直接提取 `config-6.1.65-ophub`、modules 清单、`System.map`、rootfs 网络服务/配置文件与 U-Boot 文件 hash；并审计 `f16bd...` 到 `4428...` 之间 stmmac/Rockchip clock/reset/PHY 的实际差异。未完成前不启动 Linux、不刷写介质。


## 19. 2026-11-24 原版 6.1.65 TF 启动有线网络实机基线

2026-11-24 用户在 Panther X2 上实际启动原版 Armbian 6.1.65（TF rootfs，日志显示 /boot 位于 eMMC），完成 eth0 驱动/链路、DHCP IPv4、hEX 网关 ICMP、外部 IPv4 ICMP 和 DNS 解析验证。完整现场数据与证据边界见：

- `docs/reports/2026-11/PANTHER-X2-6.1.65-ORIGINAL-TF-BOOT-ETHERNET-BASELINE-20261124.md`

**重要边界：** 这是原版 6.1.65 完整 Armbian 系统的实机正向基线，不是 B1 最小 RAM Linux 的测试结果。B1 当时仍处于打包构建阶段；B1 的构建、artifact 审计、目标硬件启动及后续网络验收均须独立完成。不得把本次原版系统测试转记为 B1/B2/B3 通过。
