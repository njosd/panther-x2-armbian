# Panther X2 最小系统与上游融合主线（P1—P8）

- 建立日期：2026-11-20
- 主线性质：项目长期进度与执行顺序的权威记录
- 当前阶段：P2 — RK3566 双介质自包含启动链与 eMMC Vendor 数据传递只读架构审计
- 当前允许操作：只读核对 RK3566 BootROM/SPL/U-Boot 启动规则、已有 eMMC Vendor 数据布局和公开源码；不下载组件源码、不执行构建、不写卡、不启动实验系统

## 0. 主线目标

以 Panther X2（RK3566）为目标，先建立一个最小、可重复构建、可审计的 Linux 系统，只验证有线网络功能和既有 GMAC TX 广播异常；在网络基线明确后，再逐项加入系统组件，最终形成仅面向 RK3566 Panther X2、可长期维护、硬件相关部分优先采用 Rockchip RK3566 官方组件，通用用户空间优先采用各项目上游代码和标准构建方式的系统。

这条主线同时承担两个目标：

1. **短期：定位网络故障层级。** 将完整发行版的复杂变量剥离，判断 6.12.81 的 TX 广播异常在最小用户空间中是否仍然存在。
2. **长期：形成可持续维护的系统。** 逐层加入成熟组件，保留来源、版本、差异和测试证据；尽量将必要的通用修复回馈上游。

## 0.1 长期启动架构目标：按启动介质自包含，vendor 数据统一

**这是新系统的目标架构，不是对当前混合启动链的复刻。**

期望的最终行为：

- 从 TF 启动时：BootROM/SPL/U-Boot proper 以及 U-Boot 所需的板级启动资产，全部由 TF 启动路径提供；不能隐式依赖 eMMC 上另一半 U-Boot。
- 从 eMMC 启动时：对应的 SPL/U-Boot proper 和启动资产全部来自 eMMC。
- 两种启动路径都读取同一份权威板级 vendor 数据（例如 MAC 地址、板卡标识及其他确实存在的校准/配置数据），并以明确、可验证的接口传递给 Linux。
- 介质选择与启动固件来源必须可观测；每个阶段记录介质、文件/扇区、版本和摘要。不得形成“TF 启动却悄悄调用 eMMC 中另一阶段固件”的隐式依赖。

### Vendor 数据传递原则

1. 先只读盘点 eMMC 现有分区、原始区域、U-Boot 环境和 vendor 数据实际存放位置；不能先假定它叫 vendor 分区，也不能假定 MAC 地址只有一份。
2. 明确数据格式、偏移/分区、字节序、校验、版本、多个 MAC 的映射及缺失/损坏时的回退策略。
3. 优先由 U-Boot 在启动时读取权威数据，并写入/修正最终交给 Linux 的 FDT：
   - Ethernet MAC 应写入对应 Ethernet 节点的标准 `local-mac-address` / `mac-address` 属性，且核实驱动实际读取路径；
   - 其他通用板级标识可使用有版本定义的 FDT 节点/属性；若数据需要由 Linux 驱动直接读取，评估标准 NVMEM/设备树绑定，而不是发明临时私有 ABI。
4. 不通过复制多份 MAC 配置来掩盖来源不清；保留唯一权威数据源及读取失败时的明确日志。
5. eMMC vendor 数据区在研究和构建阶段只读；未经单独授权不写入、不格式化、不迁移、不“修复”。

### 与当前诊断启动链的关系

P1 已确认的 eMMC SPL + TF JP-TvBox proper 仅是当前设备的**临时诊断入口**，用于验证最小 initramfs 的可行性；它不代表最终架构认可这种混合链。

在 P3 写入实验 TF 卡之前，必须先完成“独立 TF 完整启动链”的只读可行性审计，并确认不会写 eMMC。若 BootROM 的实际启动规则或板级硬件限制导致 TF 无法独立提供完整启动链，必须先给出证据和替代方案，再由用户决定是否接受，不得默默退回混合链。

## 0.2 用户最新确认：优先争取 TF/eMMC 各自完整启动，受硬件限制时回退原设计（2026-11-20）

用户首选目标：
- TF 卡启动：尽可能让完整 BootROM→SPL/DDR 初始化→U-Boot proper 链全部来自 TF；
- eMMC 启动：尽可能让完整启动链全部来自 eMMC；
- 避免 SPL 与 U-Boot proper 跨介质混合读取，降低版本耦合和维护风险。

可行性服从 RK3566 BootROM 和 Panther X2 原厂板级硬件限制。当前已完成的静态结论：
- RK3566 普通 BootROM 顺序为 eMMC 优先于 SDMMC；Panther X2 2026-11-18 实机 source tag 为 eMMC ID 2，eMMC user-area LBA64 有有效 IDB。
- `SDMMC0_DET` 仅切换 SDMMC/JTAG 引脚复用，不是启动源选择脚。
- Rockchip SD boot pre-loader 流程可由已启动的 pre-loader 从 SD 加载 U-Boot proper，但不证明 BootROM 会从 TF 加载 SPL。
- RK3566 不支持旧式 SD IDB card-type flag；Android BCB 的 `recovery\\n--rk_fwupdate\\n` 是 SD 升级/recovery 标记，不是普通 TF SPL 选择开关。
- 现有 eMMC SPL→TF proper 混合链已有完整证据，不能重复做介质映射调查。

**当前唯一值得继续的可行性核查：** Panther X2 原厂板级是否存在上电前 eMMC 电源/复位/数据线隔离或 BootROM 启动源选择机制。公开资料尚未提供原理图/PCB 证据，因此不能先验断言有或没有。

若原厂硬件有可用且不破坏 eMMC 数据的隔离/选择机制，再评估 TF 完整启动；若没有，则在保留有效 eMMC IDB 的条件下，当前没有已知可靠的 TF 独立 BootROM→SPL 路径，应保留原有启动逻辑，并把混合链来源、版本绑定、更新顺序和恢复方式显式管理。

工作要求：
- 原有 Bootloader 软件包、职责划分、组件及 USB 双公头恢复机制作为基线，不主动重构。
- 不重复已完成的 BootROM 顺序、source ID、MMC/ATAGS 映射、eMMC IDB 位置、SDMMC0_DET 定义及 SD Boot Card/BCB 兼容性调查。
- 最小系统仅在有明确诊断收益时作为临时工具，不是最终系统强制组成。
- 未经明确授权，不清除/禁用 eMMC IDB、不改 eMMC boot area/EXT_CSD、不短接、不编译、不写 TF/eMMC、不启动实验固件。
- Vendor 数据始终只读来自 eMMC 权威区域，并沿既有 U-Boot 环境变量/FDT fixup 路径传递。

### 0.2.1 新增公开证据（2026-11-20）

- 第三方 Panther X2 项目记录 Debian 12/Linux 6.9.4 从 uSD 启动；PiLoader 也提供 TF 启动系统并声称不修改 eMMC。资料没有完整 BootROM/SPL/U-Boot UART 日志，不能证明 SPL 与 proper 都来自 TF。
- Lorenzo Gangemi 对 BROWAN H1GW V04 的记录显示，普通 Armbian SD 镜像在其设备上未能触发 SD 启动，设备继续进入 eMMC 原厂系统；该作者随后选择直接写入 eMMC。此为第三方单机观察，不可推广成所有专用 TF 启动布局都不可行。
- 已找到 H1GW V04 PCB 顶面照片；另有 Panther X2 拆机文章展示背面，但尚无可核验的 H1GW V04 原理图、PCB netlist 或 BOM，无法从现有公开照片确认 eMMC 电源/复位隔离电路。
- 准确区分三件事：TF 上运行 Linux（有第三方记录）；eMMC SPL→TF proper（本项目已实测）；TF SPL→TF proper（完整 TF 自包含启动，仍未证明）。


## 1. 不可变执行原则

### 1.1 上游优先

- 每个组件优先采用对应项目当前仍维护的上游主线或最新正式稳定发布版本；6.1.116 只作已知正常行为参考，不作为新系统版本模板。
- 记录仓库 URL、tag/commit、构建参数、依赖和产物摘要。
- 优先使用上游已有功能和配置；能通过配置解决，不另写代码。
- 本地代码和补丁单独管理，不直接散落修改第三方源码。
- 每个本地 patch 必须记录基线版本、文件差异、原因、影响范围、测试证据、撤销方法及上游提交可行性。
- 有通用价值的修复，评估去除项目私有依赖后向对应上游提交。未合并前明确标注为本地 patch。
- 追求上游新版本，但不在同一轮实验中同时滚动升级多个组件；每轮锁定 commit/tag、工具链、配置与哈希，完成测试后再主动升级并回归。

### 1.1 目标硬件范围：仅 RK3566 / Panther X2

- 最终交付只面向 **Panther X2 的 RK3566 硬件**，不承担 RK3588、RK3399 或其他 SoC/板型的兼容目标。
- 对 SoC 启动、DDR 初始化、BootROM 配套、时钟/复位、GRF、pinctrl、GMAC、USB、存储控制器等硬件相关组件，优先采用 **Rockchip 针对 RK3566 提供并维护的官方代码、BSP、固件及配套配置**；板级部分使用 Panther X2 对应资产。
- 如果 RK3566 官方来源没有合适组件、功能缺失或维护状态不适合，才选用其他上游兼容实现；必须记录缺口、替代来源、兼容依据、额外依赖和后续维护责任。
- 对 Linux 通用用户空间工具（例如 BusyBox、iproute2、ethtool）仍优先使用其项目自身的上游正式版本；“RK3566 专用”不意味着要 fork 通用工具，也不意味着要人为添加 SoC 判断代码。
- 不为未支持硬件保留抽象层、设备树分支、构建矩阵或运行时兼容逻辑；但遵守上游组件本身必要的通用接口，不为单板目标破坏上游可维护性。
- 构建目标、内核配置、DTB、U-Boot defconfig、DDR blob/配置和固件清单均以 RK3566 + Panther X2 为唯一目标组合。若某组件的官方支持边界不清楚，先查证，不把“Rockchip 通用”直接等同于“RK3566 官方适配”。

### 1.2 Panther X2 实际外露接口、调试与复位功能

最终系统只需覆盖 Panther X2 实际外露、可能使用的硬件：

- **UART 串口调试接口：必须保留。** 它是启动和故障诊断的关键生命线，必须保证 BootROM/SPL、U-Boot proper、Linux 各阶段串口输出可观察，并正确配置 UART pinctrl、控制器驱动、console/earlycon、波特率及阶段交接；不能出现 Linux 接管后串口消失。
- **1 个千兆以太网口：必须保留。** 第一阶段唯一必须验证的业务外设；保留 GMAC、MDIO、实际 PHY 及其时钟、复位、供电和 pinctrl 依赖。
- **1 个 TF 卡接口：必须保留。** 用作实验启动/系统介质，保留完整启动链所需 SDMMC 支持。
- **硬件复位按钮：保留原有硬件功能。** 不重新设计、不改造成软件按键，也不凭外观猜测 GPIO、极性或复位范围；以现有软件包中明确描述为准。
- **1 个 USB 2.0 接口：可选。** 初始最小系统不要求启用，后续确有需要再加入。
- **Wi-Fi：可选且基本不会使用。** 初始最小系统不要求启用。

硬件复位按钮与 PMIC 电源键的软件证据边界（2026-11-20 更新）：
- 固定 Linux 源码快照 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 和正常参考源码 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` 的 Panther X2 DTS 均未发现 `gpio-keys`、`gpio-key`、`reset-key` 这类独立 GPIO 按键节点。
- 但不能据此得出“软件包没有按键处理”。Panther X2 DTS 明确声明 `rockchip,rk809` PMIC，并设置 `rockchip,system-power-controller`。6.1.116 正常系统实机中断记录包含 `rk805_pwrkey_rise` 与 `rk805_pwrkey_fall` 两条 IRQ；对应正常内核源码的 `drivers/mfd/rk808.c` 会为 RK809/RK817 variant 创建 `rk805-pwrkey` MFD 子设备，`drivers/input/misc/rk805-pwrkey.c` 将 rise/fall 中断映射为 `EV_KEY / KEY_POWER`。6.12 Rockchip 内核同样保留该驱动机制。
- 因此新最小系统必须保留现有 RK809 PMIC 主驱动/MFD、中断链以及 RK805/RK817 PWRKEY input 子设备和对应内核配置，不能只因 DTS 没有 `gpio-keys` 节点就裁掉。
- **重要区分：** 以上证据确认的是 PMIC PWRKEY（Linux 电源键事件）软件路径，不足以证明用户所说的实体“硬件复位按钮”就是该 PMIC PWRON 键，也不足以证明它就是一颗独立 SoC/PMIC reset 按钮。板上是否存在第二颗按钮、各按钮的电路连接与按压行为，仍需原理图/板级资料确认。
- 当前执行原则：保留 RK809 PWRKEY 软件支持及所有原有硬件复位功能；不新增猜测的 GPIO 按键节点，不把电源键事件擅自改成 reset/reboot。后续精简 DTS/内核时，保留 RK809 相关节点、IRQ 与 PMIC/pinctrl/reset 依赖；只有板级资料明确指出独立复位按钮需要额外软件控制时，才增加对应支持。

### 1.3 最小系统第一阶段只验证网络

第一阶段只保留启动 Linux、识别 GMAC/PHY、观察链路和执行定向网络收发测试所需内容。

第一阶段不包含：DHCP、DNS、SSH、NetworkManager、systemd（除非启动机制确有必要）、存储管理、NPU/RKNN、Docker、Immich、桌面及其他常驻服务。

### 1.4 设备与数据安全

- 用户准备的独立 8GB TF 卡是实验介质。
- 不写入 eMMC，不替换当前 6.1.116 正常系统。
- 未经用户明确授权，不格式化/分区/写入 TF 卡，不启动实验内核。
- 未经授权不安装软件、不修改 Panther X2 当前系统、内核、驱动、启动链、网络服务或存储配置。
- 首轮优先使用 RAM initramfs，避免把 TF EXT4/JBD2 写入问题混入 GMAC 网络实验。
- 写卡前必须核对设备型号、容量、设备节点和影响范围；任何破坏性操作先单独征求确认。
- 不做示波器/逻辑分析仪等用户不具备的硬件波形测试。

### 1.5 证据与防重复

每项工作都必须标记为：已验证、静态审计确认、待验证、推测/候选或不适用。

每项结束必须归档：
- 工作目标和范围；
- 版本、commit、配置和输入资产；
- 执行步骤与环境；
- 原始证据路径及 SHA-256（适用时）；
- 结果、结论等级和未解决问题；
- 是否改变下一项优先级。

不得把源码差异直接写成根因；不得把配置意图代替运行时事实；不得把相关性写成因果。已完成测试先查仓库报告，不得重复跑圈。

## 2. 基准与对象

### 2.1 内核对照

| 标识 | 版本 | 项目角色 | 当前已知 |
|---|---|---|---|
| G-A | 6.1.65 | 黄金正常参考 A | 用户确认原始系统镜像实机正常 |
| G-B | 6.1.116-ophub | 黄金正常参考 B | 实机运行正常，优先用于最小系统正常对照 |
| F-A | 6.1.174-rk35xx | 故障参考 A | 历史实机异常 |
| F-B | 6.12.81-rk35xx | 故障参考 B / 首轮目标 | 已有 TX 广播异常测试记录 |

6.1.65 与 6.1.116 的系统资产来源不完全相同，不能将它们视为可随意互换的内核包。6.1.116 是首选正常对照，6.1.65 只在有明确判别价值时加入。

### 2.2 路线区分

- 首轮诊断对象是 Ophub RK35xx 6.12.81。
- Ophub Panther X2 正式板型的 stable/6.18.y 是另一条独立路线，不得混入首轮实验。
- Kernel、DTB、boot 文件和必要模块必须版本匹配；不得跨版本混用内核模块。
- 首轮尽量固定启动固件，只替换已明确界定的 Kernel/DTB/initramfs 实验资产。

### 2.3 已有研究边界

GMAC probe/setup、普通 STMMAC TX、RGMII delay、JL2xx1 workaround、U-Boot 时钟交接、pinctrl 首 pin、DMA descriptor 等既有审计与测试已有独立报告。新主线不重开这些已完成支线；只有出现新的直接证据，才通过单独决策记录重新开启。

## 3. 阶段主线

## P1 — 启动链与 initramfs 只读可行性审计（已完成）

**目标：** 确定能否利用现有启动链加载 6.12.81 Kernel + 匹配 Panther X2 DTB + 最小 RAM initramfs，并明确安全实验介质布局。

**工作范围：**
1. 回读 6.12.81 官方包审计报告和现有 Artifact，不重复下载或全量解包已审计内容。
2. 核对 kernel config 中 initramfs/initrd 支持、可用压缩格式及所需启动能力。
3. 核对 6.12.81 boot 包中的 Image、DTB、initrd/uInitrd、配置文件、实际文件格式和摘要；缺失的二进制摘要要明确标记。
4. 核对现有 Panther X2 U-Boot、启动脚本、启动日志中可证实的 TF 读取方式、文件系统支持、加载命令和 boot 参数。
5. 对照 6.1.116 已归档启动资产，判断后续最小用户空间 A/B 的可行边界。
6. 根据证据确定 8GB TF 卡启动布局；在核验前不预设 FAT/EXT4、不猜测扇区布局。

**验收条件：**
- 有一份准确资产清单和依赖/匹配关系；
- initramfs 能力由配置或实物证据确认，而非猜测；
- 启动方式和参数有证据出处；
- 未知项、风险和需要用户确认的操作列清；
- 得出是否可复用现有启动链的结论。

**禁止事项：** 不构建、不写卡、不启动实验内核、不更改现有设备。

**状态：** 已完成静态可行性验收。证据与保留项见 [P1 审计报告](PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)。已确认 6.12.81 实机解包 gzip initramfs、当前 U-Boot 从 SD/TF ext4 第一分区加载启动文件、6.1.116 配套 Kernel/DTB/initrd 资产、两版内核的 initramfs 与网络核心驱动基础，以及 8GB TF 静态布局候选。自制最小 initramfs 尚未构建或启动。

## P2 — 原有 Bootloader 基线下的局部问题方案评估（只读；实施待授权）

**目标：** 延续原有 Bootloader 设计、软件包和启动流程，利用既有根因分析，评估如何最小范围处理 SPL/U-Boot proper 跨介质读取不一致，以及 eMMC 权威 Vendor 数据读取和向 Linux 传递问题。不再把 TF 自包含完整启动链作为硬性目标，不重复 BootROM/MMC 映射、Vendor Storage 布局或 MAC 来源调查。最小系统仅在有明确诊断收益时作为临时工具评估。当前只做静态方案设计，不触发 workflow、不编译、不写介质、不启动实验固件。

**候选内容：**
- `/init` 与最小目录树；
- 上游 BusyBox（优先静态构建）；
- procfs/sysfs/devtmpfs 挂载和基础控制台；
- 必要的网络诊断工具（按需求选用上游 iproute2、ethtool 等）；
- 可控的 UDP/广播测试工具；优先采用上游现有工具，确有缺口才增加最小测试程序；
- 日志输出和测试脚本。

**构建原则：**
- 先固定上游源码版本、工具链和依赖；
- 尽量使用可复现的独立 CI 构建；
- 新建独立手动触发 workflow，不覆盖现有完整 Armbian 构建 workflow；
- 产物记录 SHA-256、构建日志、manifest、配置和来源；
- 不把 DHCP/DNS/SSH/NetworkManager 等放入第一版。

**验收条件：** 产物结构、架构、依赖闭包、启动脚本和哈希均通过静态验收；此时仍不自动代表已在 Panther X2 实机启动成功。

## P3 — 独立启动介质与最小系统验收（待授权）

**目标：** 在 P2 证明可行且用户授权后，按最终确认的启动介质策略启动最小 RAM initramfs；优先要求 TF 自身提供完整启动链，同时 eMMC Vendor 数据只读读取。若 RK3566 BootROM 规则使其不可行，必须先由用户审阅替代方案，不默认采用混合链。

**前置条件：**
- P1 当前启动链可行性审计通过；
- P2 已完成独立 TF 完整启动链与 vendor 数据传递方案审查，并说明 BootROM 实际介质选择；
- P2 构建及静态验收通过；
- 写卡方案和设备识别步骤明确；
- 用户明确授权写卡与启动。

**验收条件：**
- 启动来源与 SPL/U-Boot proper 的实际介质由日志/证据确认；
- 若采用 TF 自包含路径，须证明 SPL/U-Boot proper 均来自 TF；
- 启动时从 eMMC 只读读取权威 vendor 数据，并正确传递 MAC 等信息；
- 进入 initramfs 的 `/init`；
- 串口日志完整可读；
- 目标设备、内核、DTB、启动参数可确认；
- 不挂载或写入 eMMC；
- 不将 TF 文件系统写入故障混入本轮网络验证。

若启动失败，先定位启动/内核/initramfs 层，不得把它记为 GMAC 网络失败。

## P4 — 最小系统网络功能与 GMAC TX 定向验证（待授权）

**目标：** 在最小系统中完成网络基础功能验收，并用最少必要测试判断既有 6.12.81 TX 广播异常是否复现。

**范围：**
- GMAC/PHY probe 与 link 状态；
- 接口、地址和路由的基本可观测性（不要求 DHCP）；
- 定向单播/广播发送；
- 第三方同二层监听器确认帧是否真正到达；
- 驱动统计与抓包记录。

**特别约束：**
- 重点复核已有“驱动报告 TX 成功但第三方监听器收不到广播帧”的故障现象；
- 不重复已完成的 DMA、RX、环回、RGMII、PHY 专项测试；
- DHCP 是否成功不能代替 TX 帧到达证据；
- 结果必须注明测试条件，并与历史测试可比。

**验收条件：** 网络基础功能记录完整，TX 广播是否复现有第三方监听证据，结论边界明确。

## P5 — 黄金内核最小环境 A/B 对照（待开始）

**目标：** 在尽量一致的最小用户空间和测试程序下，对照 6.12.81 与 6.1.116。

**原则：**
- 使用 6.1.116 自己匹配的 Kernel/DTB/boot 资产；
- 使用 6.12.81 自己匹配的 Kernel/DTB/boot 资产；
- 尽量共用同一 initramfs、测试程序、网络拓扑和第三方监听器；
- 不跨版本混用 modules；
- 如果启动链或 DTB 不同，明确记录差异，不为表面一致强行混搭；
- 6.1.65 仅在必要时作为第二黄金参考加入。

**验收条件：** 同一最小用户空间下的对照结果可重复、条件透明，并能判断故障是否随内核/匹配启动资产变化。

## P6 — 按需逐层增加用户空间组件（条件触发）

**触发条件：** P4/P5 发现最小系统与原完整系统网络行为不同，或有明确的系统功能需求。

**候选顺序：**
1. 设备管理与 udev（如确有必要）；
2. systemd 与日志；
3. DHCP 客户端；
4. DNS；
5. SSH；
6. NetworkManager/其他网络管理组件；
7. 其他基础服务。

每次只增加一个明确组件或不可分割的依赖组。每层保留上一个通过版本，复用相同网络回归测试。出现回归即退回最近通过层，分析新增差异。

**验收条件：** 每一层的功能、来源、依赖、资源占用、网络回归结果及回退点均有记录。

## P7 — 向 Ophub / Armbian 体系融合（网络基线稳定后）

**目标：** 从最小验证环境逐步形成标准、可升级、可维护的发行版构建。

**工作内容：**
- 复用已核实的 Ophub/Armbian 构建脚本、包管理和系统集成机制；
- 优先采用上游组件和标准配置；
- Panther X2 专属改动集中为独立 patch/配置层；
- 每项本地差异都记录上游版本、原因、测试、撤销方式和上游回馈状态；
- 评估可通用化修复并向上游提交；
- 分阶段验证启动、网络、服务管理、升级和恢复。

**验收条件：** 构建可复现、差异可追溯、可升级回退，不依赖未记录的手工修改。

## P8 — 存储、NPU 与家庭照片中心功能（后续独立阶段）

只有在基础系统稳定后，才分别研究：
- 存储介质、文件系统、备份和恢复；
- RK3566 NPU/RKNN 驱动与用户态兼容性；
- Immich 部署及局域网临时算力协作；
- 家庭照片自动备份、去重、人工审核、归档和共享。

这些内容不属于 P1—P5 网络验证的前置条件，不得提前加入最小系统。

## 4. 当前唯一执行项

**P1 已完成，不重跑。P2 已完成本轮公开资料与现有证据的静态架构审计，仍有一个 Panther X2 板级硬件证据缺口。**

已完成：
1. 回读 eMMC/TF 原始启动区域、UART、Vendor Storage 备份和已有报告。
2. 核对 RK3566 BootROM eMMC/SD 启动顺序、SD Boot/BCB 文档及 SPL/U-Boot 机制边界。
3. 核对 Panther X2 SARADC0 Loader 按钮、USB OTG、RK809 PWRKEY 软件路径。
4. 形成 eMMC Vendor Storage 只读解析、校验、FDT 传递和禁止随机 MAC/写回的设计约束。

**当前剩余项：** 继续寻找 Panther X2 H1GW V04 原理图/PCB/BOM，确认是否存在安全且不改写 eMMC 的 eMMC-disable / BootROM SD 强制启动条件。第三方 yjdwbj Panther X2 v1.0 的 U-Boot 截图显示 SPL 从 MMC1 启动、proper 从 TF 控制器 `fe2b0000` 加载 extlinux/Kernel/DTB；同标签 Linux 日志确认 rootfs 位于 TF `mmcblk0p2`、eMMC 为 `mmcblk1`。这高度支持第三方采用 eMMC 前级 + TF 后级的混合链，而不是 TF 自包含完整 U-Boot。v1.0 标签没有提供可做二进制取证的 idbloader/u-boot.itb/整卡镜像。若无板级隔离/选择机制证据，TF 独立完整冷启动保持“未证实”，不得清除 eMMC IDB 或照搬 RK3566 EVB2 eMMC_D0 短接方案。

完成该硬件证据闭环后，才冻结双介质启动架构；随后重新评估最新维护中的 BusyBox、iproute2、ethtool 等上游版本，设计最小 /init、目录树、串口日志和独立 CI。实际构建、写卡、启动实验内核仍须另行明确授权。

不得触发构建、写卡、短接或启动实验内核。

## 5. 主线状态看板

| 阶段 | 状态 | 说明 |
|---|---|---|
| P1 启动链与 initramfs 只读审计 | 已完成 | 静态可行性验收通过；自制 initramfs 尚未构建/启动 |
| P2 双介质自包含启动链与最小系统架构设计 | 静态架构审计阶段性完成 | BootROM/SD Boot、Vendor Storage 已审计；第三方 v1.0 混合启动路径有截图交叉证据；仅待 H1GW V04 板级资料确认 eMMC 隔离/启动选择机制 |
| P3 独立 TF 完整启动链 | 待授权 | 必须先确认 SPL/U-Boot proper 均由 TF 提供；eMMC vendor 数据只读传递 |
| P4 最小系统网络验收 | 待授权 | 需 P3 通过及用户授权 |
| P5 黄金内核 A/B | 待开始 | P4 后执行 |
| P6 逐层加入用户空间 | 条件触发 | 网络对照显示必要时执行 |
| P7 融合 Ophub / Armbian | 待开始 | 网络基线稳定后 |
| P8 存储、NPU、Immich | 后续阶段 | 不进入当前网络最小系统 |

## P1 最新进展

- 2026-11-20：已归档 [P1 initramfs 与 TF 启动链审计进展](PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)，确认 6.12.81 实机成功解包 gzip initramfs，当前混合启动链需保留 TF LBA 16384 的 U-Boot proper。
- 2026-11-20：用户实机 sysfs 已确认 Linux mmcblk0 为 SD（SN64G）、mmcblk1 为 eMMC（MMC / DF4032，含 boot0/boot1）；findmnt 确认 /boot=/dev/mmcblk0p1 ext4。结合既有 U-Boot 从 SD 对应 mmc 1:1 找到并执行 boot.scr、加载 Kernel/initrd/DTB 的日志，当前 SD/TF ext4 启动文件读取能力已验证。详见 P1 报告 §3.5。
- P1 已完成静态验收：6.1.116 历史正常网络基线位于 eMMC；当前 6.12.81 从 TF 启动。两者资产匹配边界、initramfs 行为和 8GB TF 静态布局候选已记录。不得将历史 6.1.116 启动链误写为当前 JP-TvBox 启动链。

## 6. 关联文档

- [P2 启动架构与 eMMC Vendor 数据审计](PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md)
- [P2 上游用户空间组件初审（版本策略已修订）](PANTHER-X2-P2-UPSTREAM-USERSPACE-COMPONENT-AUDIT-20261120.md)
- [最小 initramfs 构建蓝图](PANTHER-X2-MINIMAL-INITRAMFS-BUILD-PLAN-20261120.md)
- [GMAC 调查路线图](PANTHER-X2-GMAC-INVESTIGATION-ROADMAP-20261119.md)
- [6.1.65 原始镜像来源审计](PANTHER-X2-ORIGINAL-SOFTWARE-IMAGE-PROVENANCE-20261120.md)
- [6.1.116 正常实机基线](../../01-hardware/panther-x2-6.1.116-usb-ethernet-baseline-20261116.md)
- [6.1.174 官方内核包审计](PANTHER-X2-6.1.174-OFFICIAL-KERNEL-ASSET-AUDIT-20261120.md)
- [四版本内核资产矩阵](PANTHER-X2-FOUR-VERSION-KERNEL-ASSET-MATRIX-20261120.md)
- [原有最小系统构建计划](../../BUILD-PLAN.md)
- [原有完整系统构建快速指南](../../BUILD-QUICKSTART.md)

## 7. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-20 | 建立 P1—P8 独立主线；明确上游优先、本地 patch 可追溯及上游融合原则；第一阶段限定为网络验证。 |
| 2026-11-20 | P1 静态可行性验收通过；纠正 6.1.116 历史 eMMC 启动现场与当前 6.12.81 TF/JP proper 启动链的差异。 |
| 2026-11-20 | 用户明确新系统不复刻 6.1.116，组件优先当前维护中的上游版本；启动架构目标改为 TF/eMMC 各自自包含完整 U-Boot，并统一从 eMMC 只读读取 Vendor 数据。P2 当前唯一任务改为 BootROM/SPL 启动选择与 Vendor Storage 物理布局审计；BusyBox 1.36.1 默认候选撤回。
| 2026-11-20 | 用户确认硬件复位按钮只需延续原有功能。只读检查 6.12.81 与 6.1.116 Panther X2 DTS 均未发现 gpio-keys/软件按钮节点；因此不添加猜测的 GPIO 按键实现，保留原硬件复位功能，物理线路连接方式待原理图/板级证据确认。
| 2026-11-20 | 修正按键软件审计结论：6.1.116 实机 IRQ 记录包含 rk805_pwrkey_rise/fall；RK809 MFD 会创建 rk805-pwrkey 子设备，配套驱动上报 KEY_POWER。新系统必须保留 PMIC PWRKEY 路径；但该 PMIC 电源键是否就是用户所说的实体硬件复位按钮仍未确认，两者不可混为一谈。
| 2026-11-20 | P2 源码交叉审计确认 Rockchip U-Boot/Linux 的 eMMC Vendor Storage 固定布局为 user-area LBA 7168 起、4×128 sectors（256 KiB），按 tag/version/version2 选择最高有效副本。当前下一项收敛为仅解析已有 eMMC 备份中的四份副本，不重新读取实机。
| 2026-11-20 | 用户运行只读解析脚本确认归档 eMMC 备份中 vendor0 为唯一有效副本（DVKR、version/version2=2），vendor1–3 全零；vendor0 含 LAN_MAC ID 3、12 bytes，两个 MAC 均通过单播格式检查。Vendor Storage 备份解析阶段完成；P2 当前唯一执行项转为 BootROM eMMC/SD 启动选择及失败回退审计。

后续每次推进必须先更新本文件中的阶段状态、当前唯一执行项和变更记录。


## P2 新增进展：第三方 Panther X2 v1.0 启动链静态核对（2026-11-20）

- 原始 U-Boot 截图显示 SPL 2024.01 的 `Trying to boot from MMC1`；U-Boot proper 从 `mmc@fe2b0000.bootdev.part_1` 加载 extlinux、Kernel、Panther X2 DTB 和 initramfs。
- 同标签 Linux 日志确认 `mmcblk0` 为 uSD、rootfs 位于 `mmcblk0p2`；`mmcblk1` 为 eMMC。
- 结合控制器映射，第三方启动路径高度支持 eMMC 前级 + TF 后级混合启动，与本项目当前实机路径属于同类；不构成 TF SPL + TF proper 自包含启动证据。
- v1.0 标签 Git tree 仅含 README 和 PNG，没有 idbloader/u-boot.itb/整卡镜像；README 的预构建链接是源码标签压缩包，不是固件包。
- 当前 main 分支已转向 Buildroot 2026.08、U-Boot next-dev、FIT/RKFW/eMMC 布局，不可与 v1.0 的 uSD 启动布局混为一谈。
- 详见 P2 报告 §18。未执行下载、运行、写卡或设备操作。

## P2 新增进展：H1GW V04 板级资料与 eMMC 上电隔离边界（2026-11-20）

- 已核对 BROWAN H1GW V04 顶面照片及 FCC Panther X2 两组内部照片档案（2021 #5542190、2022 #5825812）；均未提供原理图/netlist/BOM 或可闭环的 eMMC VCC/VCCQ/RESETn 控制网络。
- RK3566 eMMC VCC/VCCQ 必须在 BootROM 发 CMD 前稳定；运行期 sleep 后关断 VCC 的能力不能证明启动前存在可用的 eMMC-disable 机制。
- 当前没有证据证明 H1GW V04 可在 BootROM 介质探测前隔离 eMMC。继续保留该硬件问题为未验证，不猜测测试点、不短接。
- 详见 P2 报告 §19。


## P2 新增进展：原有 U-Boot proper 介质选择与 eMMC 权威 Vendor 数据隔离方案（2026-11-20）

- Rockchip U-Boot 参考提交 `8af2535` 的 `param.c` 已有 ATAGS → `mmc 0/eMMC`、`mmc 1/SD` 映射；`boot_rkimg.c` 的 bootdev 初始化优先级为配置 > ATAGS > scan。原有机制具备 proper 按介质选择的基础，不需重构启动框架。
- `vendor_storage_init/vendor_ops` 同样依赖 `rockchip_get_bootdev()`，因此 Vendor 数据会跟随 proper 当前启动介质。不可全局强制 `devnum=0`，否则会连带改变其他启动路径。
- 推荐设计：保留动态 bootdev；为板载 LAN_MAC 增加独立、只读、显式指定 eMMC mmc0 的 Vendor Storage 读取入口；不复用通用 Vendor 全局缓存、不写回、不生成随机 MAC；继续使用原有 env → FDT fixup 传递机制。
- 当前为静态设计结论。尚需核对拟用 U-Boot 分支的 SPL ATAGS 产生逻辑、proper fallback/配置覆盖及专用 eMMC read-only API 的代码落点；未授权前不写补丁、不构建、不写卡。
- 详见 P2 报告 §20。


## P2 补充核对：SPL 成功 loader 与 ATAGS 的语义边界（2026-11-20）

- 通用 SPL 在某 loader 成功加载 proper 后，将该 loader 编号写入 `spl_image->boot_device`；Rockchip SPL 再通过 `atags_set_bootdev_by_spl_bootdevice()` 写 ATAGS。MMC1→EMMC、MMC2→SD。因此 ATAGS 在此路径表达 SPL 实际成功加载 proper 的介质，而不是 BootROM 最初加载 SPL 的介质。
- 两份候选源码默认 `spl_boot_device()` 返回 MMC1；默认 `board_boot_order()` 只尝试 MMC1/eMMC。当前实机已见 MMC2 成功加载 proper，说明实际 SPL 有不同的板级 boot order/loader 路径，需只读核对其现有源码，不重新实机测试。
- Rockchip 8af2535 proper 选择顺序为编译期 `CONFIG_ROCKCHIP_BOOTDEV` > ATAGS > scan；Radxa c559871 则是 ATAGS > scan（另先处理 SCSI/NVMe），两者不能混为一谈。
- BROM source tag helper 与 SPL successful-loader ATAGS 是不同语义；本项目要保持 proper 与实际成功 loader 一致，应沿用 successful-loader 语义。
- Vendor 专用读取不得临时修改全局 devnum 后复用通用 Vendor API；必须独立 eMMC mmc0 descriptor + 独立只读解析上下文，避免全局缓存污染和意外写回。
- 详见 P2 报告 §21。当前仍未写补丁/构建/写卡。


## P2 新增进展：Rockchip 官方较新 U-Boot/rkbin 更新审查（2026-11-20）

- Rockchip U-Boot `next-dev` 仍保留 SPL 成功 loader → ATAGS → proper 选择的机制；默认 `spl_boot_device()` 仍为 MMC1/eMMC，weak `board_boot_order()` 默认只尝试一个设备；proper 仍是配置 > ATAGS > scan。没有发现上游默认自动完成双介质完整启动的变化。
- Rockchip rkbin SPL v1.14（2024-05-30）明确修复 SPL 阶段 SD 初始化失败（SPL pinctrl 节点被禁用）；v1.13 修复 uboot.img 的 u-boot.dtb 失败后不加载备份镜像。两项都不是 BootROM 选源优先级修复。
- RK3566 DDR v1.26（2025/2026）改善训练、启动概率、容量识别并增加单通道 LPDDR4/LPDDR4X 支持；是否适配 Panther X2 需按实物 DRAM 拓扑核对。
- 主线 U-Boot v2026.10 支持多款 RK3566 板，但官方列表不含 Panther X2/H1GW V04，不能直接替换现有板级固件。
- 新发现 Rockchip next-dev 有 `vendor_storage_buffer_read()`，使用局部 Vendor 解析上下文读取调用者提供的 buffer；可用于 eMMC-only MAC 方案，但仍需独立读取 eMMC 与扫描四份副本。
- 详见 P2 报告 §22。下一步只做仓库现有固件版本指纹与 rkbin v1.13/v1.14、DDR v1.26 静态对照；不盲目升级、不构建、不写卡。


## P2 更新：现有 SPL/DDR 指纹与官方新版比较（2026-11-20）

- 当前实机 UART 运行的是 SPL 2017.09-armbian（2023-04-23）+ DDR V1.13；JP-TvBox 候选 idbloader 静态指纹为 SPL 2023-11-12 + DDR V1.10，二者不能混为一谈。
- Rockchip 官方 SPL v1.14（Build commit 606f72bd97a，2024-05-30）修复 SPL 阶段 SD pinctrl 初始化失败。当前 SPL 已能从 MMC2/TF 读取 proper，故该修复不是当前混合链问题的直接解释；release note 未提及 BootROM 选源、loader order、ATAGS 或 proper bootdev 优先级。
- 官方 DDR v1.26 有 ultra、普通多频率、单通道 LPDDR4/LPDDR4X 等不同变体；必须依据实际 DRAM 颗粒、通道/Rank/CS、PCB template、频率及 BL31 配套关系筛选。当前 4GB LPDDR4 的完整拓扑未闭环，不推荐直接替换。
- rkbin 官方要求二进制提交可追溯到 source commit；后续优先选择有 Build commit 和明确更新说明的候选。
- 详见 P2 报告 §23。下一步只静态检查 SPL v1.14 对应源码变更与 Panther X2 DRAM 拓扑证据；不构建、不刷写。


## P2 补充：SPL v1.14 源码提交逐项差分（2026-11-20）

- 已找到 rkbin 发布提交 `1961bbd229b1f1698ce1b5ff1df9aaae07922e66`，其 `rk356x_spl_v1.14.bin` 明确 Build from U-Boot commit `606f72bd97a`，包含 14 项相关变更。
- 关键变更包括 SPL pinctrl 从 `u-boot,dm-pre-reloc` 改为 `u-boot,dm-spl`（RK3566 EVB LP4X V10 测试）、MMC 默认 sample phase、SPL 数据读取超时余量 10→50ms（针对特定 KOWIN eMMC）、数据错误后 reset 延时、HS200 tuning 失败后 STOP 命令等。
- 逐项差分未发现 `spl_boot_device`、`board_boot_order`、成功 loader ATAGS、proper bootdev 优先级或 Vendor eMMC 来源变化；v1.14 改善 MMC/pinctrl 可靠性，不改变双介质启动源选择规则。
- 修正 DDR 资料状态：现有 Panther X2 两份实机日志已记录 LPDDR4 4GB、ddrconfig 7、BW32、CS0/CS1 双 rank、CS=2、Die BW16；并非拓扑完全未知。v1.26 单通道新增支持与本机双 rank配置不构成匹配证据；颗粒料号、PCB template、DQ mapping 仍待证。
- 详见 P2 报告 §24。下一步静态核对 Panther X2 当前 SPL FDT pinctrl、MMC phase/card-detect/HS200 配置；不构建、不刷写、不重跑设备测试。


## P2 补充：Radxa U-Boot SPL 双介质启动顺序（2026-11-20）

- Radxa `stable-4.19-rock3` commit `c55987146f4f9b20f7cb2f917ca88300419afe8d` 的 `rk3568-u-boot.dtsi` 明确配置 `u-boot,spl-boot-order = &sdmmc0, &sdhci, ...`，即 SPL 先尝试 TF/SD，再尝试 eMMC；同一 DTS 将两个控制器及 SD pin groups 纳入 `u-boot,dm-spl`。
- aliases 为 mmc0=eMMC、mmc1=TF；不要把 Linux DTS alias 与 U-Boot SPL/proper alias 混淆。
- 该属性证明板级 SPL 可配置双介质 loader 搜索顺序，但只控制 SPL 加载 proper 的介质，不能改变 BootROM 最初从何处加载 SPL，也不保证 TF/eMMC 启动链自包含。若 BootROM 从 eMMC 加载 SPL 而 SPL 优先从 TF 取 proper，反而会形成混合链。
- Radxa DTS 的 `&pinctrl` 标记为 `u-boot,dm-pre-reloc`，而官方 v1.14 提交 `05891810f6d` 改为 `u-boot,dm-spl`；值得核对 SPL DTB 过滤和父节点保留规则，不能仅凭静态标签断言 pinctrl 失效。
- 详见 P2 报告 §25。下一步锁定 Panther X2 实际 SPL 的 `/chosen/u-boot,spl-boot-order`、board_boot_order 与最终 SPL DTB；不重复检查 Linux DTS，不构建、不写卡。


## P2 补充：Panther X2 专用 U-Boot 构建配方核查（2026-11-20）

- 已找到固定 NixOS Panther X2 专用配方 `5aaee9/nixos-aarch64@02b7d0d450b906834157132fe58f11acd00e8124`：defconfig `panther-x2-rk3566_defconfig`，DDR `rk3566_ddr_1056MHz_v1.10.bin`，BL31 `rk3568_bl31_v1.29.elf`，产出 SPL/idbloader/u-boot.itb。
- 其 defconfig 启用 `CONFIG_SPL_ROCKCHIP_BACK_TO_BROM=y`、SPL MMC/OF/FIT/ATF；但 `CONFIG_DEFAULT_DEVICE_TREE` 与 `CONFIG_TARGET` 仍指向 RK3568 EVB1 V10。补丁仅新增 defconfig 与 trust.ini，没有 Panther X2 专用 board C、`board_boot_order()` 或 SPL DTS。
- 因此它是 Panther X2 命名的构建配方及 DDR/BL31 配套证据，但尚不能证明 TF/eMMC 各自自包含启动。`BACK_TO_BROM` 必须结合确切 U-Boot source 版本追踪，不能凭选项名推断行为。
- Radxa ROCK 3C 家族 DTS 的 `u-boot,spl-boot-order` 只能作为通用 SPL proper loader 顺序参考；不能与 NixOS 专用 defconfig 混为一套板级固件，也不能改变 BootROM 首阶段选源。
- 详见 P2 报告 §26。下一步固定 Nix 配方真正使用的 U-Boot source revision，静态追踪 `CONFIG_SPL_ROCKCHIP_BACK_TO_BROM` 与最终 SPL DTB。


## P2 补充：RK3566 BACK_TO_BROM 机制边界（2026-11-21）

- U-Boot v2026.10 源码调用链已闭环：启用选项后 SPL 返回 BOOT_DEVICE_BOOTROM，BOOTROM loader 调用 Rockchip board_return_to_bootrom，再以 BROM_BOOT_NEXTSTAGE 将控制权交还 BootROM。
- 该命令的软件注释只承诺继续启动序列，不承诺沿用原介质。RK3566 官方硬件设计指南确认冷启动优先级为 SPI NOR、SPI NAND、NAND、eMMC、SDMMC；没有公开证据说明回交后的 ROM 是否锁定首次 source 或重新扫描。
- 因此 BACK_TO_BROM 仍是未验证候选，不可作为 TF→TF/eMMC→eMMC 已可实现的依据；不移植 NixOS defconfig、不启用选项。
- 详见 P2 报告 §27。当前唯一执行项：继续只读查证 RK3566 BootROM NEXTSTAGE 的状态续接语义；若公开资料无法闭环，再评估离线二进制静态分析。禁止重复实机测试、构建、写卡或刷机。


## P2 补充：Back-to-BootROM 通用机制与受控实机测试准备（2026-11-21）

- 修正前一轮过窄判断：U-Boot Kconfig 将 SPL/TPL 回交 BootROM 描述为 Rockchip 多阶段启动机制；ArmSoM Rockchip 启动说明明确列出启用 SPL_BACK_TO_BROM 后由 BootROM 加载 stage 3，并描述完整 eMMC/SD 启动布局。故该机制不应被限定为 RK3288/RK3036。
- 当前待证重点收敛为 Panther X2 所用 RK3566 BootROM revision 在 SPL 回交后如何选择下一阶段介质，以及原厂 SPL 是否采用该流程；不是再泛泛怀疑 Rockchip 是否有该机制。
- 用户允许字面研究后考虑可控小范围实机测试。先做零写入基线采集与 eMMC 隔离/救援路径核对；只有备用 TF、恢复方案、阶段标记和风险边界全部明确后，才提交具体测试步骤供确认。不得默认覆盖 eMMC 启动区域。
- 详见 P2 报告 §27.6–§27.7。当前仅研究与测试设计，未构建、未写卡、未刷机、未实测。


## P2 补充：第一轮 TF-only 实机测试边界（2026-11-21）

- 用户确认第一轮只用备用 TF 卡测试，eMMC 全程只读，暂不写入；若完整从 TF 启动即视为阶段性成果。
- RK3566 BootROM 冷启动优先级中 eMMC 高于 SD/TF，且 Panther X2 eMMC 已有有效启动内容。单纯插入 TF 卡不能确保 BootROM 从 TF 取首阶段。
- 先做零写入板级核查，确认有无可逆、非破坏性的 eMMC 硬件隔离方式；不能假定 RECOVERY/MaskROM/软件命令能禁用 eMMC。若无可靠隔离方式，不做 TF 独立启动实测，不擦除 eMMC。
- 通过标准必须排除 eMMC SPL→TF proper 混合链，且记录各阶段独特标记与 UART 全日志。
- 详见 P2 报告 §27.8。当前只研究隔离与救援条件，不制作镜像、不写 TF/eMMC、不进行物理改造。


## P2 补充：RK3566 SD Boot Card 机制与 TF 测试镜像设计（2026-11-21）

- Rockchip《SD Card Boot Reference》显示传统 SD Boot Card 使用 LBA64 IDBLOCK flag；RK3566/RK3568 对该旧式 flag 无支持标记。RK3566 支持的 Android BCB 标记用于 SD upgrade/recovery，不等于改变 BootROM 的 eMMC 优先级。
- 已运行的 pre-loader/SPL 可检测 SD 卡启动标志并提升 SD 后续启动优先级；这与 BootROM 冷启动选首阶段是不同层次。不能用通用 SD Boot Card 或 u-boot,spl-boot-order 直接证明 TF-only。
- 第一轮测试镜像仅设计为分阶段独特标记：TF LBA64 loader/SPL token、proper/FIT token、UART 日志；首轮止于 proper，不先引入 Linux。proper 偏移须先按所选 BACK_TO_BROM 方案核实，不能机械套用通用 0x4000。
- 下一步只读静态审计现有 eMMC LBA64 SPL/IDB 是否含 SD boot flag 检测/切换及 BACK_TO_BROM；不向 eMMC 写入。详见 P2 §27.9–§27.10。


## P9｜复用已实机验证的 UART 自动接管脚本（2026-11-21）

**状态：原版 Panther X2 U-Boot 实机已验证。**

接管不是依赖人工手速。此前已通过脚本自动实现：脚本持续监听 UART 输出，检测到

```text
Hit key to stop autoboot('CTRL+C'):
```

后，自动通过同一 UART 发送 Ctrl+C，中断 autoboot 并进入 U-Boot 命令行。后续 Boot Probe 应直接复用该自动化方法，不得把“人工看到提示后手动按 Ctrl+C”写成标准步骤，也不需要重新研究如何实现接管。

标准流程：启动 UART 监听/接管脚本 → 捕获上述提示 → 自动发送 Ctrl+C → 确认 U-Boot 命令行可交互 → 人工执行本轮只读检查并保存完整 UART 日志。禁止执行 `saveenv`、存储写入/擦除、升级、Fastboot 刷写和自动修复；eMMC 永远只读，任何获准写入仅限经明确确认的专用 TF。

该验证目前只适用于此前实测的原版 U-Boot 2017.09-armbian。JP-TvBox / Radxa 候选版本是否具有相同提示和时序，仍需分别核实。此机制只证明 proper 阶段的自动接管，不证明 BootROM/SPL 的启动介质来源。

详细记录见 P2 报告 §27.11。脚本具体文件路径、串口参数及源码尚待从既有项目资产中追溯，本条不臆造名称或参数。


## P2 更新：NixOS 配方与 RK3566 固件候选第一轮审计（2026-11-21）

- 已追溯 NixOS Panther X2 配方当前 U-Boot v2026.10 来源、历史 Radxa 分支迁移、DDR v1.10 / BL31 v1.29 输入及 EVB control DTS 继承情况。
- 发现该 defconfig 启用未经 RK3566/Panther X2 验证的 BACK_TO_BROM，且未显式启用 SPL_PINCTRL；不能直接作为探针构建输入。
- 官方 RK3566 当前 loader profile 为 DDR v1.26 standard + SPL v1.14；BL31 v1.45/v1.46 列为后续候选。Panther X2 的 LPDDR4 4GB 双 CS 拓扑已从旧 UART 日志确认，颗粒料号/PCB template/DQ mapping 仍待证。
- 详细报告：[P2 U-Boot 与 RK3566 DDR/SPL/BL31 候选审计](PANTHER-X2-P2-UBOOT-RK3566-DDR-SPL-BL31-CANDIDATE-AUDIT-20261121.md)。
- 下一步唯一研究项：静态确认 DDR v1.26 standard/ultra 与 Panther X2 DRAM 参数适配，以及 BL31 v1.45/v1.46 handoff 兼容；不构建、不写卡、不实机启动。


## 最小 RAM 启动实机测试推进（2026-11-21）

- 已冻结第一阶段目标：Ophub stable Linux 6.18.64 + Panther X2 DTB + BusyBox 静态 RAM initramfs；不挂载 eMMC/TF 文件系统，Linux init 后对所有 MMC block devices 执行并验证 block-layer read-only。
- 已准备构建脚本与 GitHub Actions workflow（PREPARE-ONLY），尚未触发构建、尚未写 TF、尚未实机启动。
- 重要核对：当前 eMMC 安装的 Panther-X2 U-Boot IDB SHA-256 为 `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e`，proper SHA-256 为 `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af`；JP-TvBox IDB/proper 是另一套不同二进制。不能混称为同一 SPL。
- Radxa ROCK 3C defconfig 的 SPL A/B、MMC write、Vendor Storage 等写路径是高相关候选风险，但尚未把当前 eMMC IDB 精确映射到该源码 commit/final .config。当前阶段仍不允许实机启动，需先完成当前 IDB 源码映射及 TF 失败/回退路径的 eMMC 写入目标审计。
- 详细方案与安全关口：[最小 RAM 启动系统方案与 eMMC 安全关口](PANTHER-X2-MINIMAL-RAM-BOOT-PLAN-AND-EMMC-SAFETY-GATE-20261121.md)。


### eMMC 芯片级临时写保护路径（2026-11-21）

为避免仅依赖 Linux initramfs RO，已在最小 RAM 启动方案中新增 eMMC Power-on Write Protect 评估：先只读查询 EXT_CSD、WP group、user-area 和 boot0/boot1 状态；如支持，在单独授权后设置 user-area `pwron` 保护及 boot0/boot1 非永久保护，验证完整覆盖后才执行实机启动。永久写保护一律禁止。详见同一最小 RAM 启动安全报告第 11 节。当前未查询 EXT_CSD、未设置 WP、未写 TF、未启动实机。


### DF4032 eMMC 最后一个部分 WP group 的规范分析已纠偏（2026-11-21）

实机 CID 解码与 SanDisk iNAND 7232 DF4032 32GB 数据手册相符：SEC_COUNT=61,071,360 sectors，WP group=16,384 sectors（8 MiB）。因此 user area 是 3,727 个完整组加一个最后有效组；最后组起始 LBA=61,063,168，设备末尾落在该组中间，尾部 4 MiB 是最后有效组的一部分，不是独立半组。

mmc-utils 默认 `writeprotect user get` 使用向下取整，漏查最后组。已修正此前“最后 4 MiB 无法保护”的表述：按 JEDEC CMD28 地址语义，最后组起始 LBA 仍在设备有效范围，理论上可对最后组操作；但需用只读 CMD31 查询实机验证最后组状态，并核对本机 mmc-utils 版本/源码。**尚未执行任何 CMD28 或 WP 设置。** 详见安全报告第 13 节。

当前最小系统测试仍未放行。下一步优先完成只读 CMD31 最后组查询与 mmc-utils 版本核对，再形成受控 Power-on WP 设置步骤；任何设置仍需用户单独明确授权。


### 测试介质冻结：8GB TF 测试卡与 64GB 6.12 对照卡（用户明确要求，2026-11-21）

- 后续所有测试镜像写入和实机启动测试只使用另一张 8GB TF 卡；该卡 CID/型号/实际容量待只读识别。
- 现有 64GB TF 卡是 6.12 对照系统，冻结保留，禁止格式化、重分区、镜像写入、升级、文件系统修复或作为临时测试盘。
- 板载 eMMC 是当前测试阶段的保护对象；正式交付版本最终安装/启动介质仍为 eMMC。TF 启动只是阶段性研究验证手段，不是最终架构方向。
- 任何块设备操作前必须按 CID、型号、容量、分区和挂载点识别，禁止仅依赖 `/dev/mmcblkN` 编号。详细安全要求见最小 RAM 启动报告第 14 节。


### 单 TF 卡槽的介质切换顺序（2026-11-21）

机器只有一个 TF 卡槽，不能在 64GB 6.12 对照卡仍插入时读取 8GB 测试卡。读取 8GB 卡须先正常关机、取出并保存 64GB 对照卡、从板载 eMMC 启动原版 6.1.116，再确认系统确实从 eMMC 启动后，才插入 8GB 卡并只读采集其 CID/型号/容量/分区信息。若不能确认 SD 热插拔安全，则关机状态插入 8GB 卡，再从 eMMC 启动。不得触碰 64GB 卡；8GB 卡身份确认前不得写镜像。详见最小 RAM 启动安全报告第 15 节。


### 最小 RAM 启动构建复核与 CMD31 只读工具（2026-11-21）

- 回读 eMMC 6.1.116 原版 `boot.cmd`，确认其使用 legacy uInitrd + `booti`；新测试沿用该已验证机制。
- 修正构建 workflow：GPT 分区类型恢复为已验证的 EF00；uInitrd legacy header 使用 AArch64；增加 header 检查及 JP proper 写入偏移的强制 SHA-256 比较。
- 新增 `scripts/panther-x2-minimal-initramfs/mmc-wp-read-last.c`：仅执行 CMD8/CMD31，校验 MMC type、DF4032 name 和预期 CID，查询最后一个 WP group；无 CMD6/CMD28/CMD29 或数据写入调用。已加入 ARM64 静态构建 artifact。
- 2 GiB GPT 镜像写入 8GB 测试卡后，需在确认目标卡身份后 relocate GPT backup header（`sgdisk -e`）并验证；64GB 6.12 对照卡保持取出、冻结。
- 当前尚未触发 Actions 构建、尚未运行 CMD31、尚未写入 8GB 卡、尚未执行任何 eMMC WP 设置、尚未实机启动。
- 下一步按单卡槽流程：取出 64GB 对照卡 → eMMC 启动 6.1.116 → 插入 8GB 卡并只读识别 → CMD31 查询 → 单独授权 eMMC 临时写保护 → 8GB 卡写入与 UART 测试。
- 详细记录见最小 RAM 启动安全报告第 16 节。


### 8GB TF 测试卡数据可销毁授权与 eMMC 实机基线（2026-11-21）

- 用户明确授权：后续 8GB TF 测试卡上的原有数据不需要保留，确认介质身份后允许全部删除、重分区、格式化及写入测试镜像。
- 此授权只适用于 8GB 测试卡；64GB 6.12.81 对照卡继续冻结，eMMC 也不因此获得写入授权。
- 用户提供的 eMMC 启动环境输出确认：Linux 6.1.116-ophub；root=/dev/mmcblk0p2、/boot=/dev/mmcblk0p1；eMMC /dev/mmcblk0 type MMC、name DF4032、CID 450100444634303332010f37d8066500、容量 61,071,360 sectors。
- boot0/boot1 的 Linux RO=1 仅是块设备层状态，不等于芯片级写保护。8GB 卡尚未插入或识别。
- 下一步先只读执行 mmc extcsd read /dev/mmcblk0、mmc writeprotect user get /dev/mmcblk0、mmc writeprotect boot get /dev/mmcblk0；严禁误用 set 子命令。再按单卡槽流程识别 8GB 卡 CID/容量，之后才安排格式化与镜像写入。
- 详细记录见最小 RAM 启动安全报告 §17。



## 9. 执行路线纠偏：run 44873044571 不属于当前批准的最小网络系统构建（2026-11-21）

用户指出近期构建内容与“最小网络测试系统”目标不符。回读本路线图、P2 启动架构审计报告、最小 initramfs 蓝图及 Actions run 后，确认近期独立 workflow 的构建范围发生了越级扩张；该 workflow/run 不应被当作当前路线的有效交付物或网络测试系统。

### 9.1 当前权威路线仍然有效

本路线图 §0、§1.3、§3 的约束没有变更：
- 第一阶段只为启动 Linux、识别 GMAC/PHY、查看链路、执行定向网络收发测试提供必要功能。
- 不加入 DHCP、DNS、SSH、NetworkManager、systemd（除非启动机制确有必要）、存储管理、NPU/RKNN、Docker、Immich、桌面或其他常驻服务。
- 当前 P2 唯一执行项是只读审计 RK3566 启动介质选择、Panther X2 板级 eMMC 隔离/启动选择机制，以及 eMMC Vendor 数据的权威只读读取与传递路径。
- P2 架构审计未完成前，不锁定/下载用户空间组件、不构建、不触发 CI、不写 TF、不启动实验固件。P2 完成后，才重新评估最小用户空间组件和构建设计。

### 9.2 Run 44873044571 的实际内容及失败

Run: https://github.com/njosd/panther-x2-armbian/actions/runs/44873044571

- workflow 输入为 Ophub stable/6.18.63，而路线图第一轮 GMAC 故障诊断对象明确是 Ophub RK35xx 6.12.81；stable/6.18.y 是另一条独立正式板型路线，不能混入首轮网络对照。
- 下载 6.18.63 kernel tarball 后，SHA-256 校验失败（日志：`sha256sum: WARNING: 1 computed checksum did NOT match`，文件约 118 MiB）。因此本次没有证明该下载包与锁定摘要一致，未进入 DTB 提取。
- BusyBox、initramfs、镜像和 artifact 后续步骤全部 skipped；无 artifact。
- 即使忽略本次校验失败，现有 workflow 的设计也明显超出“最小网络测试”边界：使用 BusyBox 完整 defconfig（只强制 STATIC，并未建立最小 applet 配置）；额外编译 `blockro` 和 `mmc-wp-read-last`；生成 2 GiB hybrid TF 镜像；将 JP-TvBox U-Boot proper 原始 FIT 写到镜像 LBA 16384；制作 ext4 分区。该方案还把 eMMC SPL→TF proper 混合链作为实际镜像设计，而 P2 启动架构审计仍未完成。
- initramfs 当前没有集成 ethtool，也没有可审查的定向 UDP 广播测试工具/网络测试流程；`/init` 明确写着“不启动网络配置或 GMAC traffic test”。因此它不是可直接执行网络联通/GMAC TX 对照的最小网络系统。
- workflow 使用 6.18.63 的 DTB 哈希与脚本中残留的 6.18.64 文案，版本信息也未统一。

### 9.3 纠偏决定

1. 将 run 44873044571 标记为**越级构建尝试/失败，无有效产物**；不继续修补该 workflow 以追求产出。
2. 暂停触发 `build-panther-x2-minimal-ram-boot.yml`；不写入或启动 SU08G。SU08G 已确认卸载，但不因此自动进入写卡阶段。
3. 回到 P2 唯一工作项：完成板级 eMMC 隔离/启动选择机制的只读证据核查，并收敛 eMMC Vendor Storage 只读来源/传递方案。不得重复已经完成的 BootROM 优先级、source ID、LBA64 IDB、SDMMC0_DET、Vendor Storage 布局和 MAC 来源调查。
4. P2 审计完成并经用户确认后，再按路线图重新设计真正最小的 ARM64 网络 initramfs：保留串口 shell、必要 proc/sys/devtmpfs、网卡/PHY状态检查、最小 IP 配置能力、ethtool 只读诊断和受控 UDP 广播发送；工具选择以当时上游稳定版本和依赖闭包为准。初始版本不带完整 BusyBox 默认 applet 集、不带存储管理/写保护辅助程序、不制作与目标无关的 hybrid 固件镜像。
5. 第一轮网络诊断内核必须回到 6.12.81 + 对应 Panther X2 DTB；6.1.116 作为后续黄金正常对照。启动固件在对照测试中固定，不同时更换 U-Boot、Kernel、DTB、rootfs。
6. 只有最小网络 initramfs 通过静态验收、启动链方案获得批准、用户明确授权写卡和启动后，才使用经 CID 确认的 8GB SU08G 测试卡。64GB 对照卡和 eMMC 继续不动。

本节是对近期执行偏差的纠正记录，不修改原有 P1—P8 目标和验收条件。



## P2 公开板级资料复核补充（2026-11-21）

- 新增回读 BROWAN H1GW V04 公开拆机资料：另一台同型号设备的作者报告普通 SD 镜像启动后仍进入 eMMC 系统，且未找到外部按钮/菜单/短接点强制 SD 启动；该记录是外部单机观察，不是本机电路级证明。
- Crankk Panther X2 资料把 Pair Button 定义为 ADC 配对输入，没有启动源选择证据；不能将其当作 eMMC 隔离开关。
- yjdwbj / Crankk 的 SD 运行记录缺少完整 BootROM→SPL→proper 来源日志，不能证明 TF 自包含启动，也不能证明存在 eMMC 隔离电路。
- 目前仍未找到可与 H1GW V04 PCB revision 一一对应的原理图、PCB netlist 或 BOM；因此 eMMC 电源/复位/总线隔离和 BootROM strap 均保持“未验证”，不得短接、拆焊或探测未知焊盘。
- 详见 P2 报告 §29。下一步需要精确匹配 H1GW V04 revision 的原厂设计资料，或可辨识 PCB revision 的正反面清晰照片；继续泛搜其他 RK3566 板卡的原理图没有足够证据价值。
