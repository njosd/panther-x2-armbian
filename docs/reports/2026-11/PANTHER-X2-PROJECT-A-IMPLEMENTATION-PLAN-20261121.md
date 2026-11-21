# Panther X2 项目 A：分阶段实施计划（B0—B7）

- 日期：2026-11-21
- 从属文档：[项目 A 总路线图](PANTHER-X2-PROJECT-A-MASTER-ROADMAP-20261121.md)
- 当前状态：B0 收尾；B1 构建准备；未获准写卡或启动实验系统

## 执行纪律

1. 每次开始先回读总路线图、本计划和相关阶段最新报告。
2. 复用仓库已有证据和 artifact；不得重复已完成测试。
3. 每个子步骤限定一个目标和主要变量；B1—B3 固定 JP-TvBox U-Boot proper。
4. 顺序为静态审计 → CI 构建 → artifact 审查 → 安全门 → 明确授权写卡 → 实机验证。
5. CI 成功不等于实机启动成功；实机启动成功不等于网络验收成功。
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
- 优先复核当前仍维护的 Ophub stable Kernel 发布资产。
- 重点复核 6.18.63 当前 Release asset：核对官方 digest、归档成员、Image、config、Panther X2 DTB 路径及 DTB SHA-256。
- 6.18.64 因既有检查未找到 Panther X2 DTB，不作为已验证输入，除非出现新证据。
- 6.12.81 仅作历史 initramfs 能力参照，不自动成为新系统首选。
- 只有 Kernel/DTB 来源匹配、配置与硬件兼容可确认，才锁定 B1 输入。

验收：固定一个 B1 Kernel+DTB 组合，记录发布包哈希、内部文件哈希、配置证据及 DTB model/compatible。

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
必须包含：
- 固定版本 ARM64 Kernel；
- 与 Kernel 匹配的 Panther X2 DTB；
- 与当前启动方式兼容的 gzip legacy initramfs/uInitrd；
- 静态 BusyBox；
- 简洁、可审计的 `/init`；
- UART console/earlycon；
- 必要 procfs、sysfs、devtmpfs、tmpfs；
- 必要 MMC/eMMC 驱动内建支持。

不包含：
- 网络配置和流量测试；
- iproute2、ethtool、DHCP、DNS、SSH；
- NetworkManager、systemd、udev；
- Docker、存储管理、NPU/RKNN、Immich；
- 包管理器、无关常驻服务和不必要辅助工具。

### B1.2 `/init` 行为
- 作为 PID 1，输出启动标识、Kernel/DTB/构建版本。
- 挂载必要虚拟文件系统；devtmpfs 失败即停止。
- 输出 CPU、内存、设备树 model、MMC 设备枚举和 block 节点。
- 不挂载 TF/eMMC 文件系统，不自动挂载，不写持久化日志。
- 如启用 block-layer RO helper，明确它仅在 Linux init 后生效；目标节点逐一设置并回读，失败即停止。
- 提供交互 ash shell；异常时打印原因并停留在诊断状态，不自动重启循环。

### B1.3 构建输入与复现
- 固定 Kernel/DTB/BusyBox/交叉工具链版本和哈希。
- BusyBox 选择正式稳定版；核验 Kconfig、静态链接、实际 applet 清单和许可证。
- CI 只构建 B1 必需文件，不构建完整 rootfs 或无关镜像。
- 保存 manifest、下载校验、构建日志、ELF 架构/静态依赖、initramfs 文件清单、权限和 SHA-256。
- 对 workflow YAML、shell、init 脚本执行静态语法检查。

### B1.4 静态验收
- Kernel 为 ARM64 Linux Image。
- DTB 的 model/compatible 对应 Panther X2/RK3566。
- `/init` 存在且可执行。
- BusyBox 为 ARM64 静态 ELF，脚本调用的 applet 全部存在。
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

B1 通过标准：Linux 执行 `/init`；UART shell 可交互；设备树/CPU/内存/UART/MMC 枚举合理；无 panic、解包错误或重启循环；未挂载 TF/eMMC 文件系统；保护检查符合设计；日志和哈希归档完整。

## B2 — 最小静态网络连通性

前置：B1 通过；测试端点、LAN 参数和安全边界已确认。

### B2.1 工具范围
只加入接口/link 查询、接口启用、静态 IPv4/掩码、路由、邻居表/ARP、ICMP ping 所需最少命令。先验证 BusyBox `ip`/`ping`，缺功能再加入必要上游工具。不得将 DHCP、DNS、SSH、NetworkManager 或完整 iproute2 作为默认依赖。

### B2.2 步骤
1. 读取接口名、MAC 传递结果、link/carrier；
2. 确认接口后启用；
3. 使用经确认且不与现网冲突的临时静态 IPv4；
4. 配置子网路由及必要网关；
5. 检查 ARP/邻居解析；
6. ping 同网段测试主机；
7. ping 网关；
8. 需要时使用已知 IP 测外部路由，不依赖 DNS；
9. 确认配置只存在于 RAM，重启不持久化。

所有地址参数以执行前读取的当前 LAN 配置为准，不在计划中预设固定地址。

### B2.3 通过标准
接口/link 可观测；静态地址/路由正确；ARP 解析成功；同网段主机和网关双向 ICMP 连通；外部路由子项（如执行）以 IP 目标成功；多轮可重复并记录丢包/时延/计数；无持久化写入。

停止条件：接口/link 不存在或静态配置失败时，只收集最小必要状态并停止本阶段，不擅自升级内核/U-Boot或转入驱动根因排障。

## B3 — 基础 TCP/UDP 验证

前置：B2 通过。

### B3.1 工具选择
- 先评估 BusyBox nc 的 TCP/UDP 模式；
- 不足时选上游轻量工具，最后才考虑独立小程序；
- ethtool 只用于只读状态查询；
- tcpdump 不进入 initramfs，需要监听时由 iMac/局域网另一主机承担；
- 不默认引入完整 iproute2。

### B3.2 步骤
1. 固定测试主机、端口、协议、接口和静态地址；
2. TCP 建连并完成简短双向数据交换；
3. UDP 单播双向收发，记录两端结果；
4. 仅在确有需求时做限定范围 UDP 广播测试，明确目的地址、端口、payload、次数，由外部同二层主机记录；
5. 按需读取只读接口状态；
6. 保存命令、双方日志、时间戳、包数和结果。

### B3.3 通过标准
TCP 双向数据交换成功；UDP 单播双向收发成功；如执行广播子项须有外部接收证据；多轮可复现；工具依赖可追溯。单个协议成功不外推为全部网络功能通过。

## B4 — 网络与基础用户空间按需扩展

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
- [ ] B0.3 复核 Kernel/DTB 发布资产并锁定 B1 输入；
- [ ] B0.4 完成 eMMC pre-Linux 写入安全门；
- [ ] B1 workflow 静态审计并运行 CI；
- [ ] 审查 B1 artifact；
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
