# Panther X2：U-Boot 启动任务与 Linux 接管参数交接清单（2026-11-22）

- 项目：Project A（仅板载有线千兆网口）
- 文档性质：启动链交接审计清单 v0.1；先建立参数目录和证据等级，不宣称已完成交接认证。
- 当前现场节点：U0（U-Boot proper 启动完成、网络测试前）。
- 约束：Wi-Fi、蓝牙、USB/PCIe 外接网卡排除；不重复已完成的 MAC 来源调查；不写 TF/eMMC，不改 SPL/U-Boot/FDT，不做 GMAC 根因专项。

## 1. 审计目的与结论标准

本清单要回答三个不同问题：
1. U-Boot 启动链已经完成了哪些工作？
2. 哪些数据/状态必须传递给 Linux，哪些由 Linux 自己重新探测或初始化？
3. 是否有证据证明 Linux 在正确的时点、从正确的来源接收了完整且一致的数据？

**重要区分：U0 不是 Linux handoff 完成点。** U0 只证明当前 SPL 已将控制权交给 U-Boot proper，且 proper 已进入交互提示符。只有后续启动命令实际装载 Kernel/FDT/initramfs、完成最终 FDT fixup，并将控制权交给 Linux，才发生 U-Boot → Linux 的最终交接。

即使 U-Boot DHCP/网关/外网 ping 全部成功，也只能证明 U-Boot 自己的网络路径可用；不能自动证明最终 FDT、MAC、时钟/复位/引脚状态或 Linux 接管参数正确。

## 2. 启动阶段与责任边界

| 阶段 | 主要职责 | 必须留下的证据 | 当前判断 |
|---|---|---|---|
| BootROM | 采样启动源，装载前级启动代码 | source ID、介质/IDB位置、启动日志 | Panther X2 既有 source ID=2 指向 eMMC 的实测已归档；本轮不重做 |
| SPL / DDR | 初始化 DRAM、识别容量/拓扑/频率；装载后级固件 | SPL build/DDR blob身份、训练日志、容量/频率、加载目标与地址 | 当前 U0 为 eMMC 前级 SPL + TF proper 混合链；本次会话的 SPL 精确身份/DDR 参数仍需与对应证据绑定 |
| ATF BL31 | EL3/安全监控器运行时服务、PSCI/SMC交接 | BL31版本、EL切换、PSCI conduit、服务状态 | 既有历史启动日志有 BL31 v2.3 与 PSCI 信息；是否与当前 U0 完全同一构建需核对 |
| U-Boot proper | 初始化运行环境、枚举设备、选启动设备、装载启动工件、准备最终 FDT/bootargs | proper版本、control FDT、环境、设备枚举、装载地址/长度、最终FDT哈希 | 当前 U0 已确认 proper 版本与部分设备枚举；完整启动任务尚未执行 |
| Linux entry | 接收寄存器约定/FDT/内存/initrd/bootargs并开始内核初始化 | Linux early log、最终FDT、内存/命令行/initrd解析结果 | 历史启动日志有实例；当前 U0 尚未发生本次 handoff |

## 3. 参数与状态交接总清单

状态标记：
- `已知`：已有实机输出或静态证据支持，但仍需确认是否适用于当前 U0 启动链。
- `待本链核对`：有历史实例或源码机制，但未绑定当前 U0 对应启动工件。
- `Linux 自行初始化`：原则上不作为 U-Boot 必须传递的运行时寄存器快照；Linux 驱动应按最终 DT/固件接口自行配置。
- `不适用/排除`：不属于 Project A 范围。

| 类别 | 交接项 | U-Boot 应提供/保证什么 | Linux 接收/验证方式 | 当前状态 |
|---|---|---|---|---|
| 启动身份 | BootROM来源、SPL、DDR blob、ATF、proper版本 | 可追溯的来源、版本、构建哈希与实际执行顺序 | Linux启动日志不一定能完整证明前级身份；需与UART/镜像哈希关联 | 待本链核对 |
| DRAM | 可用内存范围、容量、地址映射 | DDR完成初始化；把可用内存范围正确反映到最终FDT | Linux early memory map 与 FDT memory nodes 对照 | 历史实例显示4GiB；当前链精确DDR配置待绑定 |
| 保留内存 | secure/firmware/reserved-memory/CMA等区域 | 避免把保留区错误交给普通内存分配器；最终FDT准确描述 | Linux reserved-memory/CMA日志和memblock记录 | 待本链核对 |
| CPU/异常级 | CPU启动状态、EL、PSCI可用性 | 按ARM启动协议进入正确异常级；固件服务接口可用 | Linux PSCI probe、CPU bring-up、SMC conduit | 历史BL31/PSCI日志存在；当前链待核对 |
| Kernel镜像 | 地址、长度、格式、入口 | 装载正确Kernel并保证目标地址不冲突/不被后续覆盖 | Linux版本、入口启动日志、镜像哈希/构建身份 | U0尚未装载 |
| 最终FDT | FDT物理地址、长度、最终内容与哈希 | 选择正确板级DTB，完成必要 fixup，保证地址有效且不被覆盖 | Linux machine model、early FDT解析、运行时DT与传入FDT对照 | 历史实例有FDT地址；当前最终FDT未生成 |
| initramfs | 起止地址、长度、格式及FDT chosen引用 | 如启用initramfs，正确装载并在最终FDT中描述；无initramfs时明确为空 | Linux initrd起止地址、解包日志、chosen节点 | 历史实例有uInitrd；当前U0未装载 |
| bootargs | 完整命令行、来源、拼接规则 | 不丢失、不重复、不意外覆盖参数；记录最终字符串 | Linux `Kernel command line` 原样核对 | 历史实例有完整命令行；当前链待核对 |
| 控制台 | UART设备/地址、波特率、console参数 | 维持可用串口并传递正确console参数 | earlycon/console日志与实机UART一致 | 历史实例为ttyS02/1500000；当前链待核对 |
| 时钟/复位/电源 | 哪些由前级保持，哪些由Linux重配 | 对必须保持的资源不提前关闭；DT描述与硬件状态契合 | Linux clock/reset/regulator驱动probe与状态读回 | 不可把DT属性当成已执行动作；逐项区分交接与重初始化 |
| pinctrl/GPIO | 启动阶段是否改过引脚/复位GPIO | 若依赖前级状态，必须记录实际配置；否则由Linux按DT配置 | Linux pinctrl/GPIO状态及驱动初始化证据 | 历史GMAC静态DT差异不等于实际寄存器状态；待本链证据 |
| Ethernet MAC身份 | MAC来源、接口映射、最终FDT属性 | 依已完成的MAC来源审计，保证对应MAC进入正确接口的最终FDT/环境，不重新调查来源 | 对照最终FDT `mac-address`/`local-mac-address` 与Linux接口地址 | 来源调查不重开；当前U0 `ethaddr`值已记录，但需在本链最终交接时核对映射/落点 |
| Ethernet PHY描述 | MDIO总线、PHY地址、phy-mode、连接关系 | 最终FDT准确描述板级连接；若U-Boot网络测试使用PHY，记录实际探测结果 | Linux PHY attach、MDIO地址、协商状态 | 当前仅枚举MDIO/MII设备；PHY/link未确认 |
| DMA/IOMMU | DMA可访问内存、IOMMU映射/保留区 | 避免内存布局与DMA约束冲突；按平台协议交接 | Linux DMA/IOMMU初始化与设备probe | 由Linux驱动建立为主；最终FDT/保留内存需核对 |
| 熵/KASLR | RNG/seed及chosen节点 | 若平台提供随机种子，按协议放入最终FDT；没有则明确缺失 | Linux随机数/KASLR日志 | 历史日志曾显示KASLR因缺少seed关闭；当前链待核对 |
| 固件接口 | `/firmware`、PSCI、SMC、OP-TEE等 | 只声明实际存在且可用的接口；版本/内存约定正确 | Linux firmware/PSCI/OP-TEE probe与调用 | 历史BL31日志显示未提供OP-TEE；不能假定当前链服务一致 |
| 启动介质信息 | bootdev、分区、UUID、启动槽 | 正确选择Kernel/DTB/initrd/rootfs并传递必要标识 | Linux命令行、root设备解析和实际挂载 | 历史日志显示MMC1/TF、EFI分区；当前链需单独记录 |

## 4. 已有历史启动实例：可用作交接样本，不等于当前 U0 结果

仓库 `evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt` 保存了一次完整启动日志。它是历史样本，启动前级链与当前 U0 混合链不应未经核对就视为相同。

历史样本中可读出的关键交接数据：

| 项目 | 历史日志值 | 说明 |
|---|---|---|
| U-Boot proper | 2017.09-armbian (Nov 12 2023) | 与当前U0 proper版本字符串一致 |
| DRAM | 4 GiB | 历史该次启动结果 |
| Linux FDT地址 | `0x0a100000` | 装载并使用的FDT地址 |
| initramfs | `0x0a200000`，数据大小约19 MiB | 历史uInitrd装载实例 |
| 内存范围 | `0x00200000–0xefffffff` 与 `0x1f0000000–0x1ffffffff` | U-Boot日志报告的两个DRAM bank |
| FDT保留区 | `0xa100000`，size `0x8f000` | U-Boot日志中的FDT reservation |
| Kernel命令行 | `root=UUID=... rootwait ... console=ttyS02,1500000 ...` | 完整原文保留在UART证据；不可把UUID复制为当前环境配置 |
| Linux识别 | `Machine model: Panther X2` | 说明该历史FDT最终被Linux识别为Panther X2 |
| Linux PSCI | PSCIv1.1，standard PSCI v0.2 function IDs | 历史固件/内核交互结果 |
| KASLR | 因缺少seed而关闭 | 历史实例暴露的交接缺项候选 |

该历史日志可作为以后对照表的样本，但必须在当前 U0 对应的真实启动过程中重新记录最终Kernel/FDT/initrd/bootargs和Linux接收结果，才能建立当前链的闭环。

## 5. U0 当前已取得的现场参数（截至2026-11-22）

| 参数/状态 | 当前观测 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| U-Boot proper | 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000) | 当前运行proper身份字符串 | 不能单独证明其精确源码commit/二进制来源完整闭环 |
| 提示符 | `=>` | proper已进入交互命令阶段 | 不代表已执行最终Linux启动交接 |
| `ethaddr` | `[REDACTED-MAC]` | 当前环境中存在该值 | 不重新解释MAC来源；也不单独证明最终Linux FDT落点 |
| MDIO | `ethernet@fe010000` | MDIO bus已注册 | 不证明PHY已识别/link up |
| MII | `ethernet@fe010000`为当前设备 | MII设备枚举成功 | 不证明MAC数据收发 |
| DHCP/ping | 尚未执行 | 无 | 不可宣称U-Boot网络已通 |
| Kernel/FDT/initrd/bootargs | 当前会话尚未执行装载 | 无当前handoff参数 | 历史日志不能代替本轮数据 |

## 6. 如何判定 U-Boot 启动任务真正完成

需要同时通过以下阶段门，不以单一的“出现Linux登录提示符”替代：

1. **前级完成**：确认BootROM来源、SPL/DDR初始化、DRAM容量与映射、ATF版本及实际启动顺序。
2. **装载完成**：确认Kernel、最终DTB、initramfs（如有）各自来源、哈希、地址、长度，且地址区间无重叠/覆盖。
3. **最终FDT完成**：记录control FDT与Linux最终FDT的区别；核对memory、reserved-memory、chosen、bootargs、initrd、aliases、Ethernet节点及MAC fixup。
4. **启动参数完成**：U-Boot实际传递的完整bootargs与Linux打印的Kernel command line逐字一致，解释有意由内核消费/传给用户空间的参数。
5. **Linux接收完成**：Linux early boot确认正确machine model、内存bank、保留区、initrd、console、PSCI/firmware接口；无DT解析或地址错误。
6. **设备接管边界完成**：明确每项硬件资源由U-Boot保持还是由Linux重新初始化。对Project A Ethernet，至少核对最终FDT描述、Linux驱动probe、MAC映射和PHY连接信息；实际网络收发另由U-Boot网络基准及后续Linux B2/B3分别验证。
7. **可追溯**：当前链的所有实际输入/输出、镜像哈希、UART日志和最终FDT副本归档。

只有这些项目在当前启动链上闭环，才能把“U-Boot 已完成其启动任务、Linux正确接管”作为一个有边界的结论。它仍不代表U-Boot内部所有未观测硬件瞬态都已被数学意义排除；结论应明确限定在已验证的启动链、镜像版本和硬件配置。

## 7. 目前不能遗漏的窗口/时序问题

- SPL完成DDR初始化后，DRAM才成为可用装载目标；任何Kernel/FDT/initrd地址都必须在对应DRAM映射内。
- BL31进入EL3 runtime后，Linux依赖的PSCI/SMC服务必须在Linux启动前可用；不能仅看BL31打印版本。
- U-Boot重定位前后可能使用不同的FDT地址；必须记录最终交给Linux的FDT地址，而不是只记录control FDT或SPL FDT地址。
- FDT fixup必须发生在最终启动前，且发生在U-Boot最终调用booti/bootm之前；需要保存fixup后的FDT，而非只保存原始DTB。
- initramfs地址/大小必须与FDT chosen节点及实际装载范围一致；Kernel、FDT、initramfs、U-Boot relocation、reserved-memory之间不能互相覆盖。
- MAC/FDT fixup必须在最终FDT交接之前完成；Linux读取到的节点值应与最终FDT文件一致。
- 时钟、reset、pinctrl等不能只比较DTS静态属性；必须判断对应阶段是否真的执行配置，以及Linux是否会重新申请/重设。
- Linux打印的命令行是接收端证据；不能只凭U-Boot环境中的bootargs推断传递成功。

## 8. 本项目后续执行顺序与范围

1. 先完成当前U0下的U-Boot有线网络基准；结束后按U0清理规则恢复并核对。
2. 建立B1 clean RAM Linux；B1明确排除网络驱动/网络栈时，不把网络交接参数误带入B1。
3. 在后续有真实Kernel启动的阶段，采集当前启动链最终FDT、bootargs、memory/initrd/PSCI等交接数据，填充本清单。
4. B2只引入Project A板载有线Ethernet所需的Linux组件；逐项确认Linux自行初始化与前级遗留状态边界。
5. B3验证TCP/UDP双向链路。

本清单不授权重启、替换固件、写TF/eMMC、修改FDT/环境、启用无线/蓝牙/外接网卡，也不恢复旧GMAC根因排查。
## 9. 强制阶段门：Linux 首次启动前完成全部 U-Boot 侧核查

用户明确要求：系统正式进入 Linux 之前，必须完成本清单所有信息项的核查核对。此要求设为强制阶段门，不能为了尽快启动 Linux 而跳过。

### 9.1 Linux 启动前必须完成（PRE-HANDOFF GATE）

逐项审查本清单第2、3、5、7节所有适用信息。每一项必须标记为以下之一，并附证据/来源：
- `已核实`：当前实际启动链的实测输出、镜像/文件哈希、最终配置或源码证据直接支持。
- `已核实不适用`：有证据证明当前启动路径不使用该项，并说明原因。
- `由 Linux 重新初始化`：明确由 Linux 驱动负责；同时必须核实 Linux 将使用的最终 DT/固件描述和所需前置条件。
- `有意缺省/已知限制`：确认当前设计有意不提供，记录影响与接受理由。
- `未核实`：缺少证据。不得通过阶段门。

本阶段门至少要求：
1. 当前真实启动链各级固件身份、来源、版本/哈希及实际执行顺序可追溯；不能把历史日志中的不同 SPL/proper 混合链当成当前链证据。
2. DDR 初始化结果、可用内存范围、保留区和地址映射已核实；Kernel/FDT/initramfs 预定装载区间经过边界及重叠检查。
3. 当前准备启动的 Kernel、最终 DTB、initramfs（若使用）身份、哈希、格式、地址、长度均明确；文件来源与目标板适配性有证据。
4. 最终交给 Linux 的 FDT 已经生成/完成所有 U-Boot fixup；保存最终 FDT 副本与哈希。检查 memory、reserved-memory、chosen、bootargs、initrd、aliases、PSCI、Ethernet MAC/PHY等适用节点。
5. 完整最终 bootargs 已确定，来源、拼接和覆盖规则明确；console、root设备标识等关键参数无歧义。
6. BL31/PSCI/SMC/OP-TEE等固件接口逐项确认实际存在、版本与设备树描述一致；不存在的服务明确标为不适用/缺省。
7. 时钟、reset、电源、pinctrl/GPIO、DMA/IOMMU等逐项明确责任归属：U-Boot保持、Linux重新初始化或无需使用；不能仅凭 DTS 属性推断硬件寄存器已配置。
8. Project A 板载 Ethernet 相关最终 FDT 节点、MAC映射、MDIO/PHY连接描述完成核查；U-Boot网络实测结果单独记录，不能替代Linux侧验证。
9. 所有待核查项均已关闭，或经明确说明后归类为有意缺省/已核实不适用；不存在无说明的`未核实`项。
10. 交接资料包、UART日志、最终FDT、启动工件哈希、环境变量快照和地址布局表归档；确认与同一实际启动链绑定。

### 9.2 禁止进入 Linux 的条件

只要有一项适用信息仍为`未核实`、存在地址冲突、镜像身份不明、最终FDT/bootargs未冻结、关键固件服务描述不一致，或证据来自不同且未证明等价的启动链，就不得执行正式Linux启动。

### 9.3 Linux 启动后的接收端验证（POST-HANDOFF）

以下项目逻辑上只能在Linux开始执行后验证，不能伪装成启动前已实测：Linux实际解析的FDT/memory/reserved-memory/initrd/bootargs、PSCI/firmware probe、设备驱动probe和资源重新初始化结果。启动前应先完成发送端内容审计并冻结交接包；首次进入Linux后立即采集接收端证据，与冻结内容逐项比对。

因此最终结论分成两个独立签核：
- `PRE-HANDOFF READY`：所有U-Boot侧信息及交接内容核实完毕，允许首次启动Linux。
- `POST-HANDOFF VERIFIED`：Linux已实际接收并正确解析，且与冻结的交接内容一致。

在`PRE-HANDOFF READY`之前，不得正式启动Linux。U0和U-Boot网络基准测试的清理/回归仍按既定要求执行；该清理不能代替本交接阶段门。


## 10. 2026-11-22 断电重启后地址变量与 bdinfo 快照

本节记录 DHCP/Data Abort 后断电重启、重新进入当前 U-Boot proper 后的只读输出。用户在同一会话中依次执行 `printenv kernel_addr_r ramdisk_addr_r fdt_addr_r` 与 `bdinfo`。终端重复回显按同一次输出处理，不计为重复独立试验。

### 10.1 当前环境变量

```
kernel_addr_r=0x00280000
ramdisk_addr_r=0x0a200000
fdt_addr_r=0x0a100000
```

### 10.2 当前 bdinfo

```
arch_number = 0x00000000
boot_params = 0x00000000
DRAM bank   = 0x00000000
-> start    = 0x00200000
-> size     = 0xEFE00000
baudrate    = 1500000 bps
TLB addr    = 0xEFFF0000
relocaddr   = 0xEDD4A000
reloc off   = 0xED34A000
irq_sp      = 0xEB9F63B0
sp start    = 0xEB9F63B0
FB base     = 0x00000000
Early malloc usage: 5758 / 80000
fdt_blob = 00000000eb9f63c0
```

### 10.3 可直接计算的范围与限制

- 当前 U-Boot 报告一个 DRAM bank：起始 `0x00200000`，长度 `0xEFE00000`，按半开区间计算结束地址为 `0xF0000000`（不包含）。
- 三个环境变量指定的装载起始地址均落在该 DRAM bank 内。
- U-Boot relocation 地址 `0xEDD4A000`、TLB 地址 `0xEFFF0000`、IRQ/stack 地址约 `0xEB9F63B0` 均位于该 bank 高端区域；`fdt_blob=0xEB9F63C0` 是当前 U-Boot control FDT 指针，不是 `fdt_addr_r=0x0A100000` 的 Linux 目标 FDT。
- 当前输出只提供地址，不提供 Kernel、DTB、initramfs 的实际文件长度/装载长度，也没有给出 U-Boot 所有保留区间的完整清单。因此现在只能确认起始地址位于 DRAM 范围内，不能签署镜像区间无重叠或装载安全。
- 旧历史记录中的 Kernel/FDT/initramfs 地址与本轮当前环境值一致；本轮首次将这些地址与断电重启后的当前 `bdinfo` 绑定。但历史镜像身份/长度不能由地址一致性补足。
- DRAM 单 bank 结果与历史日志的两个 bank 描述并不相同；必须以当前 `bdinfo` 实测为当前 U-Boot 视角，后续仍需核实最终 FDT 的 memory/reserved-memory 是否与当前实际内存映射一致，不能把历史两个 bank 直接复制进当前交接结论。

### 10.4 当前阶段判断

地址起点与当前 DRAM bank 边界已核实；镜像实际长度、Kernel 运行/解压地址需求、U-Boot relocation/栈/控制 FDT保留范围、最终 Linux FDT memory/reserved-memory 尚未闭环。PRE-HANDOFF READY 仍未通过。本轮没有装载镜像、执行 FDT 修改命令、启动 Linux 或写入任何介质。


## 11. 当前 U-Boot working FDT 身份核对（2026-11-22）

只读命令 `fdt header` 返回：

```
No FDT memory address configured. Default at 0xeb9f63c0
magic:              0xd00dfeed
totalsize:          0x8908 (35080)
off_dt_struct:      0x48
off_dt_strings:     0x56ec
off_mem_rsvmap:     0x28
version:            17
last_comp_version:  16
boot_cpuid_phys:    0x0
size_dt_strings:    0x8db
size_dt_struct:     0x56a4
number mem_rsv:     0x1
```

只读命令 `fdt print / model` 返回：

```
model = "Radxa ROCK3 Model C"
```

判定：
- 当前 working FDT 默认地址为 `0xEB9F63C0`，与本轮 `bdinfo` 的 `fdt_blob` 一致。
- FDT magic 有效，头部报告总长度 35,080 bytes、版本 17、一个 memory-reserve 项。
- 当前 U-Boot control FDT 的 model 是 Radxa ROCK3 Model C，**不是 Panther X2 专用 FDT**。
- 该结论只针对当前 U-Boot control FDT；不代表 TF 上 Linux 目标 DTB 的身份，也不证明最终传给 Linux 的 FDT内容。
- 只读查询，没有设置/移动/修改 FDT，没有执行加载或启动。
- 当前 control FDT 与 Panther X2 目标硬件身份不匹配，不能将其直接作为 Linux 启动 DTB。最终 Linux DTB 必须独立核实来源、哈希、model/compatible及硬件资源描述，并验证启动前 fixup 后副本。

阶段门：PRE-HANDOFF READY 仍未通过。


### 11.1 当前 U-Boot control FDT 的 compatible

只读命令 `fdt print / compatible` 返回：

```
compatible = "radxa,rock3c", "rockchip,rk3566"
```

与本节已核实的 model `Radxa ROCK3 Model C` 一致。当前 U-Boot control FDT 明确声明为 Radxa ROCK3C / Rockchip RK3566 兼容设备，不是 Panther X2 的目标硬件描述。此处不推断 SoC/板级资源是否可部分共用；该 FDT 不得未经独立核验直接作为 Panther X2 Linux 最终 DTB。
