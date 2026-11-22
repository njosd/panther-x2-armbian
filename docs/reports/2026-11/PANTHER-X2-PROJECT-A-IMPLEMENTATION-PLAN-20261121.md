# Panther X2 项目 A：分阶段实施计划（B0—B7）

- 日期：2026-11-21
- 从属文档：[项目 A 总路线图](PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)
- 当前状态：B1 干净 RAM 构建流程已写入仓库，尚未运行 CI；eMMC pre-Linux 安全门未通过，未获准写卡或实机启动

## 执行纪律

**总原则：步子小一点，风险可控。单次试验只改变一个变量，结果必须可归因。**

1. 每次开始先回读总路线图、本计划和相关阶段最新报告。
2. 复用仓库已有证据和 artifact；不得重复已完成测试。
3. 每个子步骤只设一个目标和一个待验证变量；B1—B3 固定 JP-TvBox U-Boot proper，并尽量固定 Kernel、DTB、initramfs、BusyBox 与工具版本。
4. B1 第一份基线不预置任何网络工具、网络协议栈、Ethernet 驱动、存储驱动、USB 驱动、模块或固件；Linux 只从 RAM initramfs 运行。
5. 每次试验前写明目标、固定条件、唯一变量、预期结果和停止条件；试验后记录命令、退出码、操作前后状态、日志和原始结果。
6. 按启动/设备识别、接口/link、ARP、静态 IPv4/路由、ICMP、TCP、UDP 分层推进；上一层失败即停止，不叠加变量、不越级测试。
7. 失败先界定故障层级并分析现有证据；不得同时更换内核、DTB、驱动、工具和网络配置来碰运气。
8. 若一次试验改变多个变量，或无法区分各变量影响，该次结果不得作为可靠根因证据；先恢复已知基线，再拆分试验。
9. 顺序为静态审计 → CI 构建 → artifact 审查 → 安全门 → 明确授权写卡 → 实机验证。
10. CI 成功不等于实机启动成功；实机启动成功不等于网络验收成功。
6. 未经明确授权，不安装软件、不修改系统/内核/驱动/网络服务，不写 TF/eMMC，不启动实验固件。
7. eMMC pre-Linux 写入安全门未通过，禁止进入写卡与上电启动。
8. 项目 A 不开展网卡故障根因调查；仅执行本计划定义的基础网络功能验收。

### 项目 B 成果复用与禁止重复实验

- 开始每个子步骤前，除回读项目 A 文档外，还必须检索项目 B 归档中的相关报告、实验记录、源码审计、原始日志和产物摘要。
- 项目 B 已完成且证据充分的实验直接引用其结果，不得在项目 A 中重复执行；记录原报告路径、实验条件、结论等级和适用范围。
- 继承结论时保持原证据等级：已验证、静态审计确认、待验证、推测/候选不得混淆。
- 若认为必须补测，先写明旧实验为何不能回答当前问题、环境变化或证据缺口，以及本次补测的最小范围；未经项目 A 既定授权不得执行。
- 项目 B 继续封存。读取和使用其成果不构成恢复项目 B；不得主动扩展其专项排障任务。

## B0 — 基线与安全前置审计

### B0.1 冻结启动资产基线
- 回读 JP-TvBox U-Boot 归档清单与 SHA-256。
- 回读 Panther X2 原版 U-Boot 归档清单与 SHA-256。
- 回读 2026-11-17/18 UART 启动日志，确认实际执行的 SPL/proper 组合。
- 核对 Kernel、DTB、initrd/uInitrd、boot script 已有 artifact 与历史摘要。
- 形成 B0 manifest，不重复下载已归档且哈希已确认的固件。

验收：每项资产注明来源、版本、介质、SHA-256 和证据等级；明确区分 eMMC 前级 SPL 与 TF JP proper。

### B0.2 JP proper 测试基线论证
- 将 JP-TvBox proper 固定为 B1—B3 测试入口。
- 明确它是测试基线而非最终 U-Boot 选型，也不是完整 JP SPL+proper 组合。
- B1—B3 不升级/替换 JP proper；启动失败先审查 Linux 侧资产和参数，不自动换另一套 U-Boot。
- 长期 U-Boot 比较留至 B5。

验收：总路线与实施计划的启动链表述一致，不把 JP IDB/SPL 说成当前 eMMC 正在执行的 SPL。

### B0.3 Kernel 与 Panther X2 DTB 复核
- 目标系列固定为 Linux 6.18.y，不以 6.12 或 6.1 作为项目 A 构建目标。
- 按相邻修订顺序审计 6.18.64、6.18.63、6.18.62（必要时 6.18.61），优先选距离 6.18.64 最近且当前发布资产完整合格的版本。
- 6.18.64 曾有一个历史发布包未找到 Panther X2 DTB，但同名 Release asset 后续更新；必须核验当前新资产，不能沿用旧包结论。
- 6.18.63 历史 artifact 的 DTB 证据只适用于旧包；当前同名资产 digest 已变化，必须重新核验内部成员。
- 每个候选均须实际下载并独立计算外层 SHA-256，与 Release API digest 比对；检查真实归档成员、唯一 boot/DTB 资产、ARM64 Image、实际 config、Panther X2 DTB 及其哈希。
- B1 不再把 Ophub 预编译 Image 作为构建输入。第一轮源码候选锁定为 `ophub/linux-6.18.y` commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`（Makefile 确认为 6.18.63）；CI 从该 commit 自建 Kernel，最终 .config 必须证明网络、无线、蓝牙、USB、MMC/块设备和模块均未启用。
- 该 commit 仅为首轮可复现构建候选；CI 配置、编译、DTB 与 artifact 审查通过前，不视为已锁定可用内核。
- 审计范围仅限板载有线千兆 Ethernet 所需 Kconfig：网络基础协议、MAC/GMAC、MDIO/PHY/PCS，以及共享总线/中断/DMA/时钟/复位依赖；明确干净基线必须关闭的项目和后续可逐项引入的最小依赖闭包。
- Wi-Fi/无线网络、蓝牙及其控制器/驱动/固件/协议/用户空间组件永久排除，不开展 Kconfig 依赖研究、不构建、不测试、不作为后续引入项；USB/PCIe 外接网络适配器同样排除。
- 若 6.18.64 当前资产合格则优先使用；否则只向相邻 6.18.y 回退。6.1.116 仅作历史正常行为对照，6.12.81 仅作项目 B 历史证据来源。
- 只有发布包实物、配置、DTB 和硬件兼容证据闭环后，才锁定 B1 Kernel+DTB。

验收：固定源码 commit、交叉工具链、最终 .config、Kernel Image、从同一源码构建的 clean-test DTB、initramfs 和 BusyBox 的哈希；记录 DTB model/compatible、禁用节点和未验证边界。

### B0.4 eMMC pre-Linux 写入安全审计
- 确认当前实际 eMMC IDB/SPL 身份，不用 JP IDB 哈希替代。
- 尽可能追溯实际 SPL/proper 源码 commit、defconfig、最终 .config。
- 审查 SPL A/B、MMC fallback、Vendor Storage、环境保存、升级/recovery 等自动写路径。
- 核对 GPT、misc、Vendor Storage LBA 7168–7679、boot0/boot1/RPMB 等可能写入目标。
- 回读已完成 EXT_CSD/WP 查询记录；信息不完整时只设计只读补查。
- 芯片级 power-on write protect 必须先证明支持能力、WP group、覆盖范围和复位保持语义；设置本身是硬件配置写操作，须另行授权，严禁永久写保护。
- 不得清除 eMMC IDB、改写 boot area、短接或拆焊试错。

验收：形成正常启动、TF 读取失败、proper/FIT 校验失败、MMC 初始化失败/回退等路径的写入目标矩阵。无法证明 eMMC 不写入且没有可靠隔离保护时，安全门不通过。

### B0.5 实验介质确认
- 8GB SU08G：CID `035344535530384780b16ad9b700c15f`，sectors 15,523,840；每次写入前重新核对身份。
- 64GB SD64G 对照卡：冻结，不写入、不格式化。
- eMMC DF4032：冻结，不写入。
- 每次写卡前重新确认 CID、型号、容量、设备节点、分区及挂载状态，不依赖历史 mmcblk 编号。

验收：目标介质唯一且卸载；B0.4 通过；用户明确授权本次具体写入。

## B1 — 最小 RAM Linux 启动

### B1.1 组件清单

B1 只构建一个纯 RAM 的最小启动底座。网络、存储和 USB 组件均不预置；后续只在 B2 为板载有线千兆 Ethernet 按单变量计划重新构建并引入。

必须包含：
- 固定版本 ARM64 Kernel；
- 与 Kernel 匹配的 Panther X2 DTB；
- 与当前启动方式兼容的 gzip legacy initramfs/uInitrd；
- 静态 BusyBox；
- 简洁、可审计的 `/init`；
- UART console/earlycon；
- 必要 procfs、sysfs、devtmpfs、tmpfs；
- Linux B1 不启用 MMC/eMMC/SD/SDIO、块设备、USB 或模块；TF 仅由启动前的 JP U-Boot proper 读取 Image、uInitrd 和 DTB，Linux 启动后不再访问任何存储设备。
- Kernel 从源码以独立 allnoconfig + 最小 fragment 构建；网络栈及 Ethernet MAC/GMAC、MDIO、PHY/PCS 驱动必须未编入内核，而不只是模块未加载。
- B1 clean-test DTB 必须禁用 GMAC/MDIO/PHY、MMC/eMMC/SDIO、USB host/PHY 和蓝牙 UART 节点；删除 Wi-Fi/蓝牙相关板级节点与 GPIO/power-sequence 描述，保留 UART2 console、必要 SoC 时钟与 pinctrl。
- 网络工具（ip、ARP/ICMP、TCP/UDP）仅在网络子系统及对应设备驱动按序通过验证后逐项加入，不得为了减少重建次数预置到第一份干净基线。

不包含：
- 任何网络用户空间工具、DHCP/DNS/SSH；
- Wi-Fi/无线网络、蓝牙及其驱动/固件/协议；
- USB、MMC/eMMC/SD、块设备驱动、文件系统驱动和模块；
- ethtool、NetworkManager、systemd、udev；
- Docker、存储管理、NPU/RKNN、Immich、包管理器和无关服务。

### B1.2 `/init` 行为
- 作为 PID 1，输出启动标识、Kernel/DTB/构建版本。
- 挂载必要虚拟文件系统；devtmpfs 失败即停止。
- 输出 CPU、内存、设备树 model、Kernel command line 和挂载表；确认 `/` 为 initramfs/RAM，且没有 MMC、block、USB 或网络设备被枚举。
- 只挂载 procfs、sysfs；devtmpfs 由内核自动挂载。不得挂载任何 TF/eMMC 文件系统，不自动挂载，不写持久化日志。
- B1 不编译、不调用 `blockro`：Linux 根文件系统完全在 RAM，内核也不包含 MMC/block 驱动。该设计不替代 eMMC SPL/BootROM/U-Boot 的 pre-Linux 写入安全门。
- 提供交互 ash shell；异常时打印原因并停留在诊断状态，不自动重启循环。
- B1 干净基线不得加载或 probe 网络设备/驱动；不得配置接口地址、添加路由、触发 ARP/ICMP/TCP/UDP 测试或启动监听服务。
- 必须从启动日志、Kernel config、模块清单、sysfs/设备树状态等证据确认网络专用组件未进入初始基线；若发现未计划的网络驱动或设备被 probe，B1 干净基线验收失败。

### B1.3 构建输入与复现
- 固定 Kernel/DTB/BusyBox/交叉工具链版本和哈希。
- BusyBox 选择正式稳定版；核验 Kconfig、静态链接、实际 applet 清单和许可证。
- CI 从锁定的 Linux 源码 commit 构建 Kernel Image 和 clean-test DTB；从固定 BusyBox 1.37.0 源码构建静态 ash，并按 applet 白名单生成 initramfs。
- CI 只输出 Kernel、DTB、uInitrd、initramfs、boot.scr、JP proper 参考文件、manifest 和审计证据；不制作 raw/hybrid 磁盘镜像，不写 TF/eMMC。
- 保存 manifest、下载校验、构建日志、ELF 架构/静态依赖、initramfs 文件清单、权限和 SHA-256。
- 对 workflow YAML、shell、init 脚本执行静态语法检查。

### B1.4 静态验收
- Kernel 为 ARM64 Linux Image；最终 .config 中网络栈、Ethernet 驱动、无线/蓝牙、USB、MMC/block 和 MODULES 均未启用，且无 `.ko`。
- DTB 的 model/compatible 对应 Panther X2/RK3566；GMAC/MDIO/PHY、MMC/eMMC/SDIO、USB 和 Bluetooth UART 节点全部禁用，Wi-Fi/蓝牙板级节点不存在。
- `/init` 存在且可执行。
- BusyBox 为 ARM64 静态 ELF；`/init` 所需 `ash/sh/cat/dmesg/mkdir/mount/tail/uname` 全部存在；网络 applet 不存在，实际 applet 清单不超过最小白名单范围。
- initramfs 可解包，目录/权限正确，压缩格式与启动脚本兼容。
- boot script 对 Kernel、DTB、uInitrd 加载逐项检查。
- 输入和产物摘要齐全。

停止条件：来源/哈希不明、Kernel/DTB 不匹配、initramfs 格式不兼容或脚本不 fail-closed，不得写卡。

### B1.5 实机启动（安全门及授权后）
1. 重新识别 SU08G CID/name/sectors，确认不是 eMMC 或 64GB 对照卡；
2. 确认 TF 分区卸载；
3. 写入经审查的测试启动介质；
4. 复核写入后关键文件/区域；
5. UART 完整采集 SPL 到 Linux shell 日志；
6. 不执行 eMMC 写入命令，不挂载持久化 rootfs。

B1 通过标准：Linux 执行 `/init` 并进入 UART ash shell；Panther X2/RK3566 model、CPU、内存和 UART2 正常；Kernel/DTB/initramfs 与 BusyBox 均为本轮锁定资产；没有 MMC/block、USB、网络或无线/蓝牙设备 probe；未挂载持久化文件系统；无 panic、解包错误或重启循环。实机启动仍须先通过 B0.4 eMMC pre-Linux 安全门并取得本次授权。


### B1.6 组件级分批验收与故障隔离门

本节是 B1 到 B2 的强制放行规则，也是项目 A 总目标的核心执行机制。先证明干净启动基线稳定，再逐项加入网络组件，观察哪个组件/最小依赖闭包的加入首次改变系统行为。任何未经验证的网络变量不得预先混入基线。

**总规则：B1 干净基线先排除网络功能变量；此后仅允许为板载有线千兆 Ethernet 逐项引入必要组件，禁止预置或批量启用。Wi-Fi/无线网络、蓝牙及其所有相关组件永久排除，不属于任何阶段的候选。每个有线组件逐项验证、逐项归档；前一项通过后才允许进入下一项。任何一项失败，立即停在该组件边界，不得继续叠加。**

验收分为三个证据层级，不能互相替代：
- **构建/静态检查**：确认文件格式、架构、配置、依赖、入口和哈希正确；不能据此声称目标硬件运行正常。
- **组件独立功能检查**：在固定环境下单独检查组件自身行为；不能把构建成功当作功能通过。
- **目标硬件实机检查**：记录 Panther X2 上的实际启动、运行状态和原始日志；只有此层证据才能支持对应硬件行为“已验证”。

按以下顺序逐项放行：

1. **Kernel 与 Panther X2 DTB**
   - 静态阶段分别核对 Kernel 架构/配置/哈希，以及 DTB 的 model、compatible、结构和哈希；再核对二者匹配关系。
   - 实机阶段以固定启动链加载这一对资产，观察 Kernel 是否启动、是否识别 CPU/内存/UART/设备树及必要设备。
   - Kernel 与 DTB 在启动时作为匹配组合运行；不得在同一轮同时更换 Kernel 和 DTB。若需替换其中一个，另立试验并固定另一个。
   - 未通过：停止，不进入 initramfs 用户空间功能验收。

2. **最小 initramfs**
   - 静态核对归档格式、压缩方式、目录结构、/init 路径与权限、必要设备节点/挂载点。
   - 实机确认 Kernel 能解包并切换到该 initramfs，执行 /init；确认系统从 RAM 运行，不依赖 TF/eMMC 文件系统作为根文件系统，不挂载持久化 rootfs。
   - 未通过：停止，不进入 BusyBox 功能验收。

3. **静态 BusyBox**
   - 静态核对 ELF 架构、静态链接属性、动态依赖情况、配置和实际 applet 清单；逐一核对 /init 调用的 applet。
   - 实机在 RAM initramfs 中单独验证 ash 交互及本阶段必需的基础命令（例如 mkdir、mount、cat、grep、dmesg）；命令清单以实际构建配置为准。
   - 未通过：停止，不进入网络工具验收。

4. **网络子系统与设备驱动的分层引入（先驱动依赖、后用户空间工具）**
   - 干净基线验收后，先对网络协议栈、MAC/GMAC、MDIO、PHY/PCS 及其必要共享依赖建立独立变更集；每次只加入一个最小依赖闭包。GMAC/STMMAC/DWMAC 只能作为单独受控变量重新引入，不得随候选内核默认配置进入基线。
   - 每次引入前后比较最终 .config、模块/内建状态、DTB、设备 probe 日志、sysfs 设备状态及启动日志；明确本轮只改变了哪一项。
   - 若组件引入后出现异常，立即停止，不继续加入工具或其他驱动；保留失败版本与日志，回退到最近已验证基线。项目 A 记录“引入该组件后行为发生变化”的证据，不自动扩展为项目 B 的根因专项调查。
   - 未通过：停止当前组件引入，不进入下一网络组件或任何网络收发测试。

5. **ip 工具**
   - 在网络子系统及目标设备驱动已分别通过后，才单独加入 ip；静态核对二进制架构、链接依赖、版本/来源和所需功能。
   - 其功能验收放在 B2：先只读检查接口/link，再按 B2.2 顺序分别验证接口启用、静态地址、路由等。每个动作独立记录；不得一次性配置接口、地址和路由。
   - 未通过：停止 B2 当前子项，不进行 ARP、ICMP、TCP 或 UDP 测试。

每一项均使用同一份已锁定的基线资产，除本项明确允许的唯一变量外，不更换版本、不改变启动链、不引入其他新组件。记录至少包括：组件名称与版本/哈希、静态检查结果、实机命令与退出码、操作前后状态、UART/kernel 日志、必要时的两端收发证据、判定等级和停止/放行结论。

**放行条件：**本组件所有规定检查通过、证据完整且可归因，才允许进入下一项。若失败，先定位在构建、装载、初始化还是组件运行边界；不得用增加工具、替换多个组件或继续跑完整网络测试来绕过失败。组件级通过只代表该组件及其规定范围通过，不自动代表整个最小系统或网络功能通过。


## B2 — Panther X2 板载有线千兆网口分层连通性

前置：B1 通过；测试端点、LAN 参数和安全边界已确认。B2 每次只执行下面一个验证子项；前一项通过并归档后，才进入下一项。

### B2.1 工具范围
只加入接口/link 查询、接口启用、静态 IPv4/掩码、路由、邻居表/ARP、ICMP ping 所需最少命令。先验证 BusyBox `ip`/`ping`，缺功能再加入必要上游工具。不得将 DHCP、DNS、SSH、NetworkManager 或完整 iproute2 作为默认依赖。

### B2.2 单项试验顺序
1. 只读读取接口名、MAC 传递结果、link/carrier；
2. 单独启用接口，确认状态变化；
3. 单独配置经确认且不与现网冲突的临时静态 IPv4；
4. 单独检查内核自动生成的直连路由；如需手动添加路由，作为独立试验；
5. 单独检查 ARP/邻居解析；
6. 单独 ping 同网段测试主机；
7. 单独 ping 网关；
8. 需要时以已知 IP 测外部路由，不依赖 DNS，作为独立子项；
9. 确认所有配置只存在于 RAM，重启不持久化。

每个子项开始前记录基线；若失败，停止在该子项，不继续执行后续步骤。不得在同一轮中同时改接口状态、地址、路由和测试端点。

所有地址参数以执行前读取的当前 LAN 配置为准，不在计划中预设固定地址。

### B2.3 通过标准
接口/link 可观测；静态地址/路由正确；ARP 解析成功；同网段主机和网关双向 ICMP 连通；外部路由子项（如执行）以 IP 目标成功；多轮可重复并记录丢包/时延/计数；无持久化写入。

停止条件：接口/link 不存在或静态配置失败时，只收集最小必要状态并停止本阶段，不擅自升级内核/U-Boot或转入驱动根因排障。

## B3 — 板载有线千兆网口分项 TCP/UDP 验证

前置：B2 通过。TCP 与 UDP 是两个独立试验，不得在同一轮同时引入或修改两种协议测试条件。

### B3.1 工具选择
- 先评估 BusyBox nc 的 TCP/UDP 模式；
- 不足时选上游轻量工具，最后才考虑独立小程序；
- ethtool 只用于只读状态查询；
- tcpdump 不进入 initramfs，需要监听时由 iMac/局域网另一主机承担；
- 不默认引入完整 iproute2。

### B3.2 步骤
1. 固定测试主机、端口、协议、接口和静态地址；
2. 先单独进行 TCP 建连与简短双向数据交换，完成归档后停止；
3. 在保持其他条件不变的独立试验中，再进行 UDP 单播双向收发；
4. 仅在确有需求时另立试验做限定范围 UDP 广播，明确目的地址、端口、payload、次数，由外部同二层主机记录；
5. 按需读取只读接口状态，但不得与协议变量变更捆绑；
6. 保存命令、双方日志、时间戳、包数和结果。

### B3.3 通过标准
TCP 双向数据交换成功；UDP 单播双向收发成功；如执行广播子项须有外部接收证据；多轮可复现；工具依赖可追溯。单个协议成功不外推为全部网络功能通过。

## B4 — 板载有线网络相关基础用户空间按需扩展

只有 B1—B3 通过且存在明确需求时逐项评估 DHCP client、DNS resolver、SSH、日志/设备管理、网络管理服务等。一次只增加一个组件或依赖组，记录来源、版本、资源占用、验证和回退方法。

## B5 — 长期 U-Boot 与启动架构评估

### B5.1 候选
Panther X2/Ophub 原版、JP-TvBox、Rockchip 官方 RK3566 DDR/SPL/BL31、NixOS/mainline Panther X2 配方及其他有实机证据的候选。

### B5.2 审计顺序
源码与配置锁定 → DDR/双 CS/rank 匹配 → SPL pinctrl/MMC/TF/eMMC 时序 → proper/FDT handoff → 启动介质来源 → Vendor 数据只读与传递 → 更新/回滚/救援/掉电恢复 → 形成受控实机 A/B 方案。

### B5.3 决策原则
不以单次启动为唯一标准；综合板级匹配、可复现构建、维护性、升级恢复和 eMMC 数据安全。JP proper 保持已知测试基线，直到新候选完成证据闭环。

## B6 — 正式用户空间与上游体系融合

根据 B1—B5 结果选择 Debian/Ubuntu 或 Ophub/Armbian 基础用户空间；从 RAM 验证环境逐步迁移，不直接膨胀 B1。硬件部分优先明确适配 RK3566/Panther X2 的代码，通用用户空间使用上游。正式 eMMC 安装需另行制定分区、启动、更新、备份、恢复和数据保护方案。

## B7 — 长期运行能力与其他项目衔接

基础系统稳定后再分别评估存储、温控/功耗、NPU/RKNN、Docker、Immich、家庭照片备份、恢复与迁移。它们不是 B1—B3 的组件，不得提前塞入最小验证系统。

## 当前任务状态

- [x] 统一名称为项目 A；
- [x] 固定 JP proper 为 B1—B3 测试基线；
- [x] 区分 eMMC SPL 与 JP proper 的混合链；
- [x] 明确从头构建、上游优先、版本锁定；
- [x] 明确 B1/B2/B3 分层边界；
- [x] B0.3 已锁定首轮源码候选 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`（6.18.63），并新增干净内核/BusyBox配置、DTB隔离脚本与独立 B1 workflow；
- [ ] 静态审查新 workflow、Kconfig fragment、DTB 派生脚本与 initramfs；
- [ ] 运行 B1 clean RAM workflow；
- [ ] 审查 B1 artifact 中的最终 config、Image、DTB、BusyBox applet 清单、initramfs 和哈希；
- [ ] B0.4 完成 eMMC pre-Linux 写入安全门；
- [ ] 安全门通过且获本次授权后，写入 SU08G 并完成实机启动；
- [ ] B1 通过后执行 B2；
- [ ] B2 通过后执行 B3；
- [ ] B3 通过后进入 B5。

## 每次状态更新记录

| 字段 | 内容 |
|---|---|
| 日期 | YYYY-MM-DD |
| 阶段/子步骤 | Bx.y |
| 目标 | 本次唯一验证目标 |
| 输入 | 文件、版本、commit、哈希、设备身份 |
| 操作 | 实际执行的审计/命令 |
| 结果 | 原始输出摘要 |
| 证据 | 仓库路径、日志、artifact、SHA-256 |
| 结论等级 | 已验证 / 静态审计确认 / 待验证 / 推测 |
| 安全影响 | 是否写介质/修改配置 |
| 下一步 | 唯一最合理后续任务 |


## 单次试验记录模板与放行规则（2026-11-21 修订）

每次试验必须先建立记录，字段至少包括：

| 字段 | 必填内容 |
|---|---|
| 试验编号 | 唯一编号 |
| 唯一目标 | 本次只回答的一个问题 |
| 固定基线 | Kernel/DTB/initramfs/BusyBox/工具版本及哈希、启动链、硬件与介质身份 |
| 唯一变量 | 本次唯一允许改变的项目；若为只读观察，明确写“无配置变量” |
| 操作前状态 | 接口、地址、路由、设备状态、日志等相关基线 |
| 操作与结果 | 完整命令、时间、退出码、两端结果及 UART/kernel 日志 |
| 判定 | 通过/失败/无法判断及证据等级 |
| 停止条件 | 是否触发；失败时明确停止，不叠加下一项 |
| 下一步 | 只提出一个最有价值的后续验证 |

若发现多变量同时变化、试验端点不稳定、证据缺失或结果无法归因，本轮标记为“不可用于根因判定”，先恢复已知基线，不得据此扩大组件或修改驱动。任何破坏性操作、系统配置变更、Actions 触发、TF 写入和设备启动仍遵守各自的单独授权要求。

