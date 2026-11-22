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

