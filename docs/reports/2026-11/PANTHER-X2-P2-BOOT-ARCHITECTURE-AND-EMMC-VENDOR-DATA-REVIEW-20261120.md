# Panther X2 P2：启动介质自包含架构与 eMMC Vendor 数据传递审计（2026-11-20）

- 主线：PANTHER-X2-MINIMAL-SYSTEM-MAIN-ROADMAP-P1-P8-20261120.md
- 性质：只读架构审计起始报告；不是实现设计定稿
- 操作范围：回读仓库已有证据、核对公开 RK3566/U-Boot 文档与源码机制
- 安全边界：未连接 Panther X2；未写 eMMC/TF；未修改 U-Boot、SPL、FDT、MAC 或启动配置

## 1. 用户明确的目标架构

这条新系统主线不复刻 6.1.116。6.1.116 只作为已知正常的硬件/内核/网络行为参照；新系统组件优先选择当前仍维护的上游主线或最新正式稳定版本，实验时固定具体 tag/commit、工具链、配置和哈希，完成一轮测试后再主动升级回归。

启动链的长期目标：
- 从 TF 启动：完整启动固件链尽可能全部来自 TF；
- 从 eMMC 启动：完整启动固件链来自 eMMC；
- 不接受把 eMMC 的 SPL 与 TF 的 U-Boot proper 长期拼成隐式混合链；
- 无论启动介质是哪一个，板载 eMMC 中的权威 vendor 数据（至少包括两个 GMAC 的 MAC）都应由启动固件明确只读获取，并传递给后续阶段/Linux；
- vendor 数据的来源唯一、可追踪，读取失败不能静默生成随机 MAC 冒充板载地址。

## 2. 已有 eMMC Vendor 数据事实

依据 `EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md`：

- eMMC Rockchip Vendor Storage 中存在 LAN_MAC 条目，ID=3；
- Vendor Storage 头部 magic 为 `DVKR`，version=2；
- 当前已解析到一个条目，ID=3、size=12 bytes，内容为两个 GMAC 地址；
- 真实 MAC 字节未写入公开仓库，继续保持隐私；
- 这是已验证的 eMMC 数据存在事实，不代表当前 TF 启动的 U-Boot 已经读取了它。

**已补充闭环（源码级物理布局）：** Rockchip U-Boot 固定参考提交 `8af253525b7de5f29f7f97dffd18adb77db6456` 的 `arch/arm/mach-rockchip/vendor.c` 明确将 eMMC Vendor Storage 起点定义为 `EMMC_VENDOR_PART_OFFSET = 7 * 1024 = LBA 7168`，每份 128 sectors（64 KiB），共 4 份，合计 512 sectors（256 KiB），覆盖 user area LBA 7168–7679（结束位置为 exclusive LBA 7680）。Rockchip kernel 固定参考提交 `77168c8d5ab82399f65a80e9f807b50ba37cf483` 的 `drivers/soc/rockchip/sdmmc_vendor_storage.c` 使用同一 `EMMC_VENDOR_PART_START = 7 * 1024`、128-sector block 和 4 份副本，并通过 `rk_emmc_transfer()` 读取。该区域是 eMMC user area 的原始保留区，不是当前 GPT 文件系统分区。

**仍待验证（实物副本级）：** 现有报告已确认 Vendor Storage 中有 `DVKR`、version=2、LAN_MAC ID=3、12-byte 双 MAC 条目，但尚未把已有 eMMC user-area 原始备份的 LBA 7168–7679 逐份解析并与此前读出的条目逐字节交叉核对。因此，物理布局已由两套 Rockchip 源码确认，实际四份副本的当前内容、有效副本编号和最高版本仍需从已有备份做只读核验；不得重新读取或写入实机 eMMC。

## 3. 当前 Rockchip U-Boot 的默认 Vendor Storage 机制不满足“始终读取 eMMC”

已有项目报告锁定的参考源码：
`rockchip-linux/u-boot@8af253525b7de5f29f7f97dffd18adb77db6456`。

该源码链已审计：
1. `rockchip_set_ethaddr()` 通过 `vendor_storage_read(LAN_MAC_ID, ...)` 读取两个 GMAC MAC，设置 U-Boot 环境 `ethaddr` / `eth1addr`；
2. 标准 `vendor_ops()` 通过 `rockchip_get_bootdev()` 取得当前启动设备；
3. 同一源码的 MMC 映射将 U-Boot `devnum=1` 识别为 SD，`devnum=0` 识别为 eMMC；
4. 因此当前 TF 启动时，标准 Vendor Storage 路径会指向 TF 启动介质上的 Vendor Storage，而不是自动转向 eMMC；
5. U-Boot Linux FDT setup 的 `fdt_fixup_ethernet()` 可按 Linux DTB 的 ethernet aliases 将环境 MAC 写入 `mac-address` / `local-mac-address`。

这与既有实机记录相符：用户已确认当前 TF 启动路径读取的是 TF Vendor 数据；Linux 运行时 GMAC1 FDT MAC 与 eth0 MAC 一致。故“存在 eMMC LAN_MAC”与“当前 Linux 使用 eMMC LAN_MAC”是两件不同的事。

**架构要求：** 新 U-Boot 不能直接沿用“Vendor Storage = 当前 bootdev”这一默认行为。需要一个明确指定 eMMC 设备的只读读取路径，先校验 eMMC 身份、读取结果、MAC 合法性和双 MAC 顺序，再写入 U-Boot 环境/FDT。读取路径应禁止写回 eMMC Vendor Storage；失败时明确报错并停止宣称使用了板载 MAC。是否采用 U-Boot 标准 block API + Rockchip Vendor Storage parser，或上游已有的 eMMC vendor 专用 API，须进一步审查，当前不写代码。

## 4. RK3566 BootROM 启动顺序与 TF 独立启动的硬件边界（2026-11-20，结合既有现场证据修订）

Rockchip《RK3566 Hardware Design Guide V1.1.0》§2.1.5 给出的普通启动介质优先级为：
1. Serial NOR Flash（FSPI）
2. Serial NAND Flash（FSPI）
3. NAND Flash
4. eMMC Flash
5. SDMMC Card

同一指南 §2.1.6 明确：`SDMMC0_DET` 是 SDMMC/JTAG 复用功能选择信号。低电平使相关引脚复用为 SDMMC，高电平切换为 JTAG/UART；它不是 eMMC/SD 启动优先级选择脚。

### 4.1 Panther X2 的直接证据

此前现场证据已完成，不能重复采集：
- 2026-11-18 U-Boot proper 只读读取 SRAM `0xFDCC0010`，值为 `0x00000002`；Rockchip U-Boot 对照源码定义 eMMC source ID=2、SD=5。这是该次启动 BootROM 来源指示的实机证据。
- eMMC user-area LBA64 存在有效 RKNS IDB，完整数据与 JP idbloader 镜像匹配；boot0/boot1 全零，EXT_CSD 未启用 boot partition。
- 2026-11-19 实机运行 JP SPL/DDR V1.10，SPL 随后从 MMC2（TF/SD）加载 U-Boot proper；proper 的 ATAGS/MMC 映射、枚举和 TF 文件读取已闭环。
- 因此，本机已观察到的混合链为 BootROM/eMMC IDB → eMMC SPL → TF U-Boot proper。BootROM 来源并非仅凭介质优先级推测，2026-11-18 已有现场 source tag 读数。

### 4.2 Rockchip SD Boot Card 机制不能解决“TF 自带 SPL”问题

Rockchip《U-Boot v2017(next-dev) 开发指南》§6.5.4 描述的 SD 卡流程是：
- BootROM 先从可用启动介质中找到并加载一份 pre-loader/miniloader；
- 已运行的 miniloader 再扫描 SD 卡的 IDB 格式固件及卡型标志；
- 若满足对应 SD 卡类型条件，miniloader 从 SD 卡读取 U-Boot 固件并启动 proper。

因此，该流程能实现“BootROM 先执行某介质上的 pre-loader，再由它从 SD 卡加载 U-Boot”的跨介质流程；它不能证明 BootROM 会跳过 eMMC、直接执行 TF 上的 TPL/SPL。

此外，Rockchip《SD Card Boot Reference V1.2.0》平台支持表明确列出 RK3566/RK3568 不支持旧式 IDB block card-type flag；表中支持的 Android BCB 标记 `recovery\\n--rk_fwupdate\\n` 属于 SD 固件升级/recovery 流程，不是普通冷启动时选择 TF SPL 的开关。当前 Panther X2 TF GPT 仅记录 BOOT 与 ROOTFS，没有标准 misc 分区；不得把 BCB 升级标记误作 TF 独立启动方案。

### 4.3 当前可作出的判断与证据边界

- **已验证：** 普通 BootROM 介质优先级 eMMC 高于 SDMMC；本机 2026-11-18 BootROM source tag 读数指向 eMMC；本机 eMMC user area LBA64 存在有效 IDB。
- **已排除的错误方案：** 把 `SDMMC0_DET` 当作 eMMC/SD 启动源切换脚；把 RK3566 不支持的旧式 IDB card flag 或 SD upgrade BCB 标记当作普通 TF 冷启动选择器。
- **高置信度判断：** 在 eMMC 有效 IDB 保持可被 BootROM 读取的情况下，单纯向 TF 写入完整 idbloader + U-Boot proper，不能让 BootROM 越过 eMMC 而直接从 TF 启动；常规 Rockchip SD boot card 流程仍可能由先启动的 eMMC pre-loader 接管并从 TF 加载后级，不能满足“TF 上完整 SPL + proper”的目标。
- **尚未验证：** Panther X2 原理图/PCB 是否存在可在上电复位前隔离 eMMC（例如电源、复位或数据线门控）的原厂硬件机制；当前公开资料未找到可证明存在该机制的板级原理图。不能把未知写成不存在。
- **不允许的试错：** 清除 eMMC LBA64 IDB、改写 eMMC boot area/EXT_CSD、短接 eMMC 信号或改变板级硬件，均不属于当前只读评估范围。

### 4.4 后续真正值得查的唯一硬件问题

继续只读核实 Panther X2 板级是否存在原厂 eMMC 上电隔离/复位控制或 BootROM 采样启动选择输入，并明确其信号来源、上电时序、按键/跳线关联。优先寻找原厂原理图、PCB 文件、板级 BOM/设计资料；不再重复查 BootROM 优先级、source ID、SDMMC0_DET 定义、eMMC IDB 位置或 SD Boot Card 标记兼容表。

若找不到板级 eMMC 隔离/启动选择机制，或原厂设计明确没有该能力，则在保持 eMMC IDB 不动的约束下，TF 独立 BootROM→SPL 路径应判为当前硬件条件下不可实现；正式回退为原有可行启动逻辑，并明确记录 SPL/proper 的介质依赖与版本绑定。若找到可用机制，再进入静态方案比较，不直接动板或写介质。


## 5. 目标启动架构的逻辑草图（非实现承诺）

期望路径：

```text
BootROM selects TF:
  TF idbloader (TPL/SPL + DDR init)
    -> TF U-Boot proper
       -> explicitly read eMMC Vendor Storage (read-only)
       -> validate LAN_MAC ID 3 (two GMAC MACs)
       -> set U-Boot env + fix up final Linux FDT
       -> boot Linux/initramfs from TF

BootROM selects eMMC:
  eMMC idbloader (TPL/SPL + DDR init)
    -> eMMC U-Boot proper
       -> explicitly read the same eMMC Vendor Storage
       -> validate LAN_MAC ID 3
       -> set U-Boot env + fix up final Linux FDT
       -> boot Linux/rootfs from eMMC
```

此图描述目标，不代表 RK3566 当前能在 eMMC IDB 保留时按用户选择直接走第一条路径。BootROM 选择条件仍是首要未解问题。

## 6. Vendor 信息向 Linux 传递的优先方式

- MAC：在 U-Boot 读取并校验 eMMC 数据后，设置 `ethaddr` / `eth1addr`，再通过标准 FDT fixup 写入 Linux Ethernet 节点的 `local-mac-address` / `mac-address`；Linux 端核对最终 FDT 与接口地址一致。
- 其他板级 vendor 数据：先逐项盘点实际存在的数据类型及消费者。能通过标准设备树绑定表达的优先采用标准属性；需要驱动访问非易失数据时评估 NVMEM framework/cell。不能把所有厂商私有字节都塞进任意 FDT 属性。
- 任何数据传递均记录来源、长度、校验、版本、失败状态；不公开 MAC 原始值。
- 绝不在启动时对 eMMC Vendor Storage 执行自动修复、随机地址写回或版本迁移。

## 7. 当前工作状态与下一步（按用户 2026-11-20 最新澄清修订）

### 7.1 首选目标仍然是双介质各自完整启动

用户最新澄清：优先目标仍是尽可能实现：
- TF 卡启动时，BootROM、SPL/DDR 初始化、U-Boot proper 及必要启动固件来自 TF，避免跨介质拼接；
- eMMC 启动时，上述组件来自 eMMC，形成完整一致的 eMMC 启动链。

这样可以避免 SPL 与 U-Boot proper 版本/构建来源隐式耦合，降低维护复杂度。**不能将此前“TF 自包含不再作为目标”的表述理解为用户放弃该目标。**

但这是有条件的首选目标，不是预设可行的结论。只有在 RK3566 BootROM 选择机制、Panther X2 板级启动电路和原厂启动布局允许时才实施。若原厂硬件/BootROM 限制使得在保留 eMMC 正常启动内容的前提下无法让 TF 成为独立首启介质，则退回原有可行启动逻辑，接受其必要的混合链，并把依赖关系明确记录。

### 7.2 已完成、不得重复的事实调查

- 当前 SPL → U-Boot proper → Linux 启动文件的跨介质读取路径已有 UART、ATAGS/MMC 映射、设备枚举和文件读取证据；
- eMMC Vendor Storage 的固定布局、四副本解析和 LAN_MAC ID 3 结构已完成；
- 当前标准 U-Boot Vendor Storage 路径跟随 bootdev、TF 启动时读取 TF Vendor 的源码机制与实机结果已完成；
- U-Boot 环境变量及 FDT Ethernet fixup 既有传递机制已确认。

不得重新做 MMC/ATAGS 映射、重复解析 Vendor Storage 副本或重复 MAC 来源调查。

### 7.3 可行性边界评估的当前结论（SoC/启动协议已核对，新增 TF 系统启动证据）

已完成且不重复：
1. RK3566 普通 BootROM 介质优先级：eMMC 高于 SDMMC；
2. Panther X2 2026-11-18 BootROM source tag 实测为 eMMC source ID 2；
3. Panther X2 eMMC user-area LBA64 有效 IDB，boot0/boot1 全零；
4. `SDMMC0_DET` 仅为 SDMMC/JTAG pinmux 选择，不是启动源选择；
5. Rockchip SD Boot Card / SD Upgrade Card 机制边界：RK3566 不支持旧式 IDB card-type flag；BCB 标记用于升级/recovery，不是 TF SPL 选择器；
6. 现有 SPL→proper 跨介质路径已经闭环；
7. 第三方 Panther X2 项目已公开记录 Linux 从 uSD 启动，PiLoader 也公开提供 TF 卡启动系统且声称不修改 eMMC；但这些资料均未提供完整 U-Boot 阶段日志，不能证明 SPL/proper 都来自 TF。

由此，高置信度判断仍然是：在 eMMC 有效 IDB 保持可被 BootROM 读取的条件下，标准 RK3566 启动流程不能仅靠在 TF 写入一套完整 idbloader + U-Boot proper，就让 BootROM 直接执行 TF SPL。TF 上运行 Linux 是另一回事，现有公开实践很可能利用了 eMMC 前级加载 TF 后级的路径，但尚不能替第三方资料确认具体启动链。

当前唯一值得继续查的可行性缺口是 Panther X2 板级是否存在原厂 eMMC 上电隔离/复位控制/BootROM 启动源选择机制。公开资料已找到 H1GW V04 PCB 顶面照片，但没有可核验原理图、netlist、BOM 或背面走线，故不能断言该机制存在或不存在。

### 7.4 方案决策门

- **若可行：** 继续设计 TF/eMMC 各自完整一致的启动链；复用原有 Bootloader 软件包和组件，尽量只调整介质选择/固件部署布局，不重构 Bootloader。
- **若受原厂硬件限制：** 保留原有启动链；明确 SPL/proper 各自来源、版本绑定和更新顺序，降低混合链维护风险，不为追求形式自包含而破坏原厂可启动性。
- **无论哪种结果：** Vendor 数据均应明确只读来自 eMMC 权威区域，并沿既有 U-Boot 环境变量/FDT fixup 路径传给 Linux；读取失败不得伪造/随机化 MAC 冒充板载地址。
- 最小系统只在有明确诊断收益时作为临时工具，不是最终系统的强制组成。

### 7.5 操作边界

当前只做源码、公开文档、已有备份和已有报告的静态评估。未经明确授权，不下载构建产物、不编译、不写 TF/eMMC、不修改配置、不启动实验固件。

## 8. eMMC Vendor Storage 物理布局与副本选择规则（2026-11-20，源码交叉核对）

### 8.1 固定物理位置（源码级确认）

两套 Rockchip 实现给出一致布局：

- Rockchip U-Boot：`rockchip-linux/u-boot@8af253525b7de5f29f7f97dffd18adb77db6456`，`arch/arm/mach-rockchip/vendor.c`：
  - `EMMC_VENDOR_PART_OFFSET = 1024 * 7 = 7168`；
  - `EMMC_VENDOR_PART_BLKS = 128` sectors；
  - `VENDOR_PART_NUM = 4`；
  - 源码注释明确说明起点为 3.5 MiB、总区大小为 256 KiB。
- Rockchip Linux：`rockchip-linux/kernel@77168c8d5ab82399f65a80e9f807b50ba37cf483`，`drivers/soc/rockchip/sdmmc_vendor_storage.c`：
  - `EMMC_VENDOR_PART_START = 1024 * 7`；
  - `EMMC_VENDOR_PART_SIZE = 128` sectors；
  - `EMMC_VENDOR_PART_NUM = 4`；
  - 通过 `rk_emmc_transfer()` 对这些 sector 做读取。

按 512-byte sector 计算：

| 副本 | 起始 LBA | sector 数 | 结束 LBA（不含） |
|---|---:|---:|---:|
| vendor0 | 7168 | 128 | 7296 |
| vendor1 | 7296 | 128 | 7424 |
| vendor2 | 7424 | 128 | 7552 |
| vendor3 | 7552 | 128 | 7680 |
| 合计 | 7168 | 512 | 7680 |

因此 Vendor Storage 覆盖 eMMC user area LBA 7168–7679，字节偏移 3,670,016–3,932,159，长度 262,144 bytes（256 KiB）。这是 raw user-area 保留区，不是 GPT 文件系统分区；不得对其格式化、清零或当作普通空闲空间使用。

该区域位于已确认的 eMMC user-area IDB LBA64 之后、FIT/U-Boot proper LBA16384 之前。源码中的 `EMMC_SYS_PART_OFFSET=8064` 也位于 Vendor Storage 结束位置之后。

### 8.2 副本有效性与选择规则（源码级确认）

U-Boot `vendor_storage_init()` 对 vendor0–vendor3 逐份读取，按以下条件识别有效副本：
- header tag 等于 `0x524B5644`（ASCII 字节序表现为 `DVKR`）；
- 尾部 `version2` 与 header `version` 相等；
- 在满足上述条件的副本中选择最高 `version`。

选定副本后再完整读入内存，后续按 item ID 查找数据。四份副本是版本轮换/冗余布局；不能假定 vendor0 永远是当前有效副本，也不能只读取第一份就认定数据状态。

Linux `sdmmc_vendor_storage.c` 也逐份检查四份副本的 tag 与 `version2 == version`，选择最高版本，再读入对应完整 64 KiB 数据块。两套实现的选择规则相互吻合。

注意：源码注释把 `version2` 相等作为有效性条件；不能把这里描述成 SHA-256/密码学完整性验证。U-Boot 结构中的 hash 字段被注释为 future expansion，不能夸大其当前校验能力。

### 8.3 当前 U-Boot 与 Linux 的读取源差异

- U-Boot `vendor_ops()` 对 MMC/SCSI 设备将物理偏移设为 LBA 7168；proper 阶段使用 `rockchip_get_bootdev()`，SPL 阶段使用当前 `_spl_load_info->dev`。因此标准 U-Boot Vendor Storage 路径仍跟随当前启动设备，而不是自动固定到 eMMC。
- Linux Rockchip `sdmmc_vendor_storage.c` 的 eMMC 读取路径则直接使用固定 LBA 7168 起点及 `rk_emmc_transfer()`，其设计目标是读取 eMMC user area Vendor Storage。
- 这进一步说明：Linux 已有能力读 eMMC Vendor Storage，不代表当前 U-Boot 在 TF 启动时也读取了 eMMC 中同一份数据。

### 8.4 与 Panther X2 已有实测条目的对应关系

既有 `EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md` 已确认此前读取到的结构为：
- magic：`DVKR`；
- version：2；
- item_num：1；
- item ID：3（`LAN_MAC_ID`）；
- size：12 bytes，包含两个 GMAC MAC 地址。

真实 MAC 继续脱敏，不写入报告。

**证据等级：**
- Vendor Storage 物理起点、容量、四份副本布局：两套 Rockchip 源码静态交叉确认。
- LAN_MAC ID 3、12-byte 数据条目存在：此前设备软件读取结果已验证。
- 现有 eMMC 原始备份 LBA 7168–7679 中四份副本的逐份原始字节、实际有效副本编号及最高版本：尚未完成只读交叉核验。
- 以上 Rockchip 源码证明标准实现布局，不自动证明设备当前运行的 2017.09 U-Boot 二进制一定编入了相同版本代码；当前二进制配置/源码 provenance 仍需单独区分。

### 8.5 下一步只读动作

下一步不访问实机 eMMC。仅使用已存在的 eMMC user-area 备份文件，读取备份文件偏移 `7168 * 512 = 3,670,016` 起的 256 KiB：
1. 分别解析四个 64 KiB 副本的 `DVKR` tag、version、next_index、item_num、version2；
2. 检查每份副本的 `version2 == version`；
3. 选出最高版本副本，解析 ID=3 的 item descriptor 与 12-byte 内容；
4. 与此前脱敏的 LAN_MAC 读取结果交叉核对，不在公开仓库记录真实 MAC；
5. 核实备份文件长度、来源和 SHA-256，确保输入确为此前归档的 eMMC user area，而非 TF 或其他镜像。

在这一步完成前，不把某个副本编号写成“当前有效副本”，也不提供任何写入/修复操作。

### 8.7 已有 eMMC 备份四份副本解析结果（用户实测输出，2026-11-20）

用户在 iMac 上运行 §8.6 只读脚本，输入文件 `eMMC-user-area-20261120.img`，文件大小 `31,268,536,320` bytes，与脚本预期大小一致。解析输出：

| 副本 | tag | version | version2 | next_index | item_num | free_offset | free_size | 结果 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| vendor0 | `0x524b5644` | 2 | 2 | 1 | 1 | 64 | 64440 | 有效 |
| vendor1 | `0x00000000` | 0 | 0 | 0 | 0 | 0 | 0 | 无效/全零 |
| vendor2 | `0x00000000` | 0 | 0 | 0 | 0 | 0 | 0 | 无效/全零 |
| vendor3 | `0x00000000` | 0 | 0 | 0 | 0 | 0 | 0 | 无效/全零 |

vendor0 中 LAN_MAC descriptor：
- item ID：3（LAN_MAC）
- offset：0
- size：12 bytes
- flags：0
- bounds check：通过
- 两个 MAC 的格式检查：均为有效单播地址（非全零、非广播、组播位未置位），且彼此不同；真实地址未输出、未归档。

最高有效版本：2；唯一最高版本副本：vendor0。LAN_MAC payload 存在于该副本中。

**结论（现有备份内容级确认）：** Rockchip 源码所定义的四份副本布局与 Panther X2 当前归档的 eMMC user-area 备份相符；当前备份中只有 vendor0 是有效副本，版本为 2，且包含 LAN_MAC ID 3 的 12-byte 双 MAC 数据。vendor1–vendor3 当前为零数据。此前软件读取到的 LAN_MAC 条目与本次备份解析在结构、ID、长度和地址格式上相互吻合；由于本次脚本刻意不输出地址字节，尚未做 MAC payload 的逐字节明文比对。

**证据边界：** 以上结论只针对该归档备份在备份时刻的内容。它证明备份文件中的副本状态，不额外证明设备当前 eMMC 在备份之后没有变化，也不证明当前 2017.09 U-Boot 二进制的源码版本与参考源码完全一致。没有重新读取实机 eMMC，没有写入或修复 Vendor Storage。

**P2 状态变化：** Vendor Storage 物理布局和备份副本解析这一项已完成。下一项唯一任务转为只读闭环 RK3566 BootROM 对 eMMC/SD 启动源的选择与失败回退条件，以及不修改 eMMC 时 TF 自包含完整启动链是否可行。


### 8.6 已有 eMMC 备份的只读解析脚本

固定备份目录已在此前 eMMC 报告中记录为 `~/Desktop/Panther-X2/08-eMMC-Backup-20261120`，目标文件为 `eMMC-user-area-20261120.img`。下面脚本只读取该镜像文件，不访问块设备、不写文件、不输出真实 MAC 地址。它按固定 U-Boot 结构解析四份副本，并只输出 descriptor 与 MAC 格式检查结果。

```bash
cd ~/Desktop/Panther-X2/08-eMMC-Backup-20261120 || exit 1
python3 - <<'PY'
import os
import struct

path = "eMMC-user-area-20261120.img"
expected_file_size = 31_268_536_320
base = 7168 * 512
copy_size = 128 * 512
data_offset = 16 + 126 * 8
data_capacity = copy_size - data_offset - 8
tag_expected = 0x524B5644

if not os.path.isfile(path):
    raise SystemExit(f"STOP: file not found: {path}")

actual_size = os.path.getsize(path)
print(f"Input: {path}")
print(f"File size: {actual_size}")
if actual_size != expected_file_size:
    raise SystemExit("STOP: file size differs from the previously archived eMMC user-area image; do not parse an uncertain input.")

with open(path, "rb") as f:
    f.seek(base)
    region = f.read(copy_size * 4)

if len(region) != copy_size * 4:
    raise SystemExit("STOP: short read from backup image.")

copies = []
for i in range(4):
    block = region[i * copy_size:(i + 1) * copy_size]
    tag, version, next_index, item_num, free_offset, free_size = struct.unpack_from("<IIHHHH", block, 0)
    stored_hash, version2 = struct.unpack_from("<II", block, copy_size - 8)
    valid = tag == tag_expected and version > 0 and version2 == version and item_num <= 126

    entry = {
        "index": i,
        "block": block,
        "version": version,
        "valid": valid,
        "lan": None,
    }

    print(f"vendor{i}: tag=0x{tag:08x} version={version} version2={version2} "
          f"next_index={next_index} item_num={item_num} "
          f"free_offset={free_offset} free_size={free_size} valid={valid}")

    if valid:
        for j in range(item_num):
            item_id, offset, size, flags = struct.unpack_from("<HHHH", block, 16 + j * 8)
            if item_id == 3:
                bounds_ok = offset <= data_capacity and size <= data_capacity - offset
                mac_pair_ok = False
                if bounds_ok and size == 12:
                    payload = block[data_offset + offset:data_offset + offset + size]
                    mac1, mac2 = payload[:6], payload[6:]
                    def valid_unicast(mac):
                        return (len(mac) == 6 and
                                mac != b"\x00" * 6 and
                                mac != b"\xff" * 6 and
                                (mac[0] & 1) == 0)
                    mac_pair_ok = valid_unicast(mac1) and valid_unicast(mac2) and mac1 != mac2
                    entry["lan"] = payload
                print(f"  LAN_MAC ID=3: offset={offset} size={size} flags={flags} "
                      f"bounds_ok={bounds_ok} two_unicast_macs={mac_pair_ok}")
                break
        else:
            print("  LAN_MAC ID=3: not present")
    copies.append(entry)

valid_copies = [x for x in copies if x["valid"]]
if not valid_copies:
    print("RESULT: no valid Vendor Storage copy found; do not infer or repair anything.")
else:
    max_version = max(x["version"] for x in valid_copies)
    winners = [x for x in valid_copies if x["version"] == max_version]
    print(f"Highest valid version: {max_version}")
    print("Highest-version copies:", ", ".join(f"vendor{x['index']}" for x in winners))
    payloads = [x["lan"] for x in winners if x["lan"] is not None]
    if len(payloads) > 1:
        print("LAN_MAC payloads identical across highest-version copies:", all(p == payloads[0] for p in payloads))
    elif len(payloads) == 1:
        print("LAN_MAC payload present in highest-version copy: yes (bytes intentionally not displayed)")
    else:
        print("LAN_MAC payload present in highest-version copies: no")
PY
```

输出仅含副本元数据和 MAC 地址格式检查布尔值；不得追加 `xxd`、`hexdump` 或打印 payload 的命令。此脚本不改动备份文件或设备。

## 9. RK809 PMIC PWRKEY 软件路径（2026-11-20，补充核对）

### 9.1 Panther X2 板级 DTS 与正常实机证据

- Panther X2 的 6.1.116 正常参考 DTS 和 6.12.81 DTS 均声明 `compatible = "rockchip,rk809"`，并设置 `rockchip,system-power-controller`。
- 正常内核 Kconfig 符号为 `CONFIG_MFD_RK808`（依赖 I2C/OF，提供 RK809 MFD 与 IRQ 子设备）及 `CONFIG_INPUT_RK805_PWRKEY`（依赖 MFD_RK808，生成 `rk805_pwrkey` 输入驱动）。首轮最小内核配置必须显式保留这两个功能；MFD 所需的 I2C、OF、MFD_CORE、REGMAP_I2C、REGMAP_IRQ 及 PMIC IRQ 父控制器链也不可误删。6.1.116 的实机 IRQ 记录是运行时存在证据；新内核仍需在其最终 `.config` 与实机 probe 中分别验收。
- 6.1.116 正常系统实机中断记录（`evidence/network/panther-eth-baseline-redacted.txt`）包含：
  - IRQ 38：`rk817`，`rk805_pwrkey_rise`
  - IRQ 39：`rk817`，`rk805_pwrkey_fall`
- 这说明正常运行系统确实注册了 RK817/809 PMIC 的 PWRKEY rise/fall 中断。它不是 `gpio-keys` GPIO 按键节点。

### 9.2 驱动路径（源码级确认）

正常参考内核固定源码 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`：
- `drivers/mfd/rk808.c` 将 RK809/RK817 variant 纳入 RK817 MFD cell 集合，创建名为 `rk805-pwrkey` 的子设备，并为其分配 PWRON rise/fall IRQ resources。
- `drivers/input/misc/rk805-pwrkey.c` 注册 `EV_KEY / KEY_POWER`，下降沿上报按下，升高沿上报释放。
- 对应 6.12 Rockchip 内核固定快照 `rockchip-linux/kernel@77168c8d5ab82399f65a80e9f807b50ba37cf483` 也保留 RK809/RK817 PWRKEY MFD 与输入驱动路径。

### 9.3 对最小系统的要求与边界

- 新系统必须保留 RK809 PMIC 主驱动/MFD、中断控制器连接及 PWRKEY input 子设备驱动和所需内核配置；不能仅因 Panther X2 DTS 未显式写出 `pwrkey` 子节点或没有 `gpio-keys` 就裁剪。
- 目前已证实的是 PMIC PWRKEY 产生 Linux `KEY_POWER` 事件。
- Panther X2 专项公开资料 `yjdwbj/panther-x2` 将板载 Push-button 标为 SARADC Channel 0，并明确其功能为 Loader mode；同一资料将 USB-A 2.0 标为 RK3566 DWC3 OTG，可工作于 host/gadget。该按钮路径与 RK809 PMIC PWRKEY 是两条不同的软件/硬件路径。
- 该项目进一步记录：Linux 运行时长按按钮约 5 秒，或在上电进入 U-Boot 时按住按钮，可进入 Rockchip Loader（rockusb）模式；社区 Panther X2 刷机记录也描述了背部按钮 + USB 连接进入 Loader，再由 RKDevTool 请求切换 MaskROM。此证据支持“板载按钮用于 Loader 恢复入口”，但不证明它直接控制 BootROM eMMC/SD 启动优先级。
- 因此，新系统必须分别保留 RK809 PWRKEY 的 `KEY_POWER` 功能，以及 SARADC0 按钮的 Loader 模式功能；不能把 SARADC0 按钮简单改成普通 reset/reboot，也不能将其误认作 `SDMMC0_DET` 或 eMMC_D0 启动 strap。
- 社区刷机教程把该实体按钮称作 Reset，但目前缺少 Panther X2 原理图/PCB 网络表，尚不能从电气层面确认按钮网络、PMIC PWRKEY、SoC RESETn 之间的关系。应按已验证的软件功能分别保留，不推断它能禁用 eMMC。

## 9. 证据与来源

- 项目报告：`docs/reports/2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md`
- 项目报告：`docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
- 项目报告：`docs/reports/2026-11/PANTHER-X2-UBOOT-FIT-FDT-EXTRACTION-ISSUE-20261117.md`
- Rockchip RK3566 Hardware Design Guide V1.1.0 (2022-02-06), §2.1.5 / §2.1.6:
  https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- Rockchip U-Boot reference board.c:
  https://github.com/radxa/u-boot/blob/next-dev-v2026.01/arch/arm/mach-rockchip/board.c
- Rockchip U-Boot reference commit used for vendor/bootdev/FDT source-path audit:
  https://github.com/rockchip-linux/u-boot/tree/8af253525b7de5f29f7f97dffd18adb77db6456
- Rockchip U-Boot Vendor Storage layout and replica selection source:
  https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456/arch/arm/mach-rockchip/vendor.c
- Rockchip Linux Vendor Storage eMMC fixed-sector reader and replica selection source:
  https://github.com/rockchip-linux/kernel/blob/77168c8d5ab82399f65a80e9f807b50ba37cf483/drivers/soc/rockchip/sdmmc_vendor_storage.c
- Rockchip Linux Vendor Storage IDs and on-disk structure:
  https://github.com/rockchip-linux/kernel/blob/77168c8d5ab82399f65a80e9f807b50ba37cf483/include/linux/soc/rockchip/rk_vendor_storage.h


## 10. RK3566 BootROM / SD Boot 选择机制：公开资料交叉审计（2026-11-20）

### 10.1 BootROM 固定介质优先级

Rockchip《RK3566 Hardware Design Guide V1.1.0》§2.1.5 明确列出复位后 BootROM 的自动启动优先级：

1. Serial NOR (FSPI)
2. Serial NAND (FSPI)
3. NAND
4. eMMC
5. SDMMC

因此，在没有其他启动选择机制的前提下，Panther X2 当前 eMMC user-area LBA 64 存在有效 IDB 时，eMMC 是先于 TF/SD 被 BootROM 检查的介质。该文档说明的是介质顺序，没有提供 Panther X2 可由软件设置的 eMMC/SD 优先级切换开关。

### 10.2 SDMMC0_DET 不是启动介质选择 strap

同一硬件设计指南 §2.1.6 对 SDMMC0_DET 的定义是 JTAG/SDMMC 复用功能选择：
- 低电平：引脚切换为 SDMMC 功能，供 SD 卡接口使用；
- 高电平：引脚切换为 JTAG/UART 功能。

它会影响 SDMMC0 接口能否正常工作，但文档没有把它定义为 eMMC/SD BootROM 优先级选择信号。不得通过改变该引脚电平来推断可以绕过 eMMC。

### 10.3 Rockchip SD Boot Card 流程的边界

Rockchip《Rockchip SD Card Boot Reference》RK-KF-YF-171 V1.2.0（2021-04）说明：
- Rockchip 的 SD Boot Card 在 LBA 64 的 IDB 区域带有专用标志；传统卡型标志位于该区域后续偏移；
- 文档的兼容表标明 RK3566/RK3568 不支持旧式 IDB block flag，支持 Android BCB 方式；文档给出的 BCB 标记 `recovery\\n--rk_fwupdate\\n` 是 SD 固件升级标记；
- 该指南把流程拆分为 BootROM 先加载 pre-loader/SPL，随后 pre-loader/SPL 检查 SD 卡及其启动标记，再由 SPL 决定是否从 SD 加载下一级固件。

这说明 Rockchip 的“SD Boot Card/SD 优先加载下一阶段”属于 BootROM 已经启动 pre-loader/SPL 之后的阶段策略；它不能直接证明 BootROM 会在 eMMC 中存在有效 IDB 时跳过 eMMC、改为执行 TF 上的 SPL。该机制可解释“eMMC SPL → TF U-Boot proper”的混合链，但不等于“TF SPL 自包含启动”。

尤其要注意：Rockchip 指南对 RK3566 的旧式 IDB flag 支持状态有限制，不能把其他 RK 芯片的卡型标志方案直接套用到 Panther X2。当前 eMMC SPL 是否支持相应 SD 启动/BCB路径，仍应以该 SPL 的精确源码/配置或受控实机证据为准。

### 10.4 Panther X2 已有启动证据如何解释

现有证据：
- eMMC user area LBA 64 存在有效 Rockchip IDB/idbloader，SHA-256 与归档文件及 Ophub Panther X2 对应文件一致；
- eMMC user area LBA 16384 存在 U-Boot FIT/proper，且与对应 Ophub 文件一致；
- 既有 UART 日志中出现 SPL 阶段的 `Trying to boot from MMC2`，随后主 U-Boot 从 TF 对应 MMC 设备加载启动脚本、内核、initrd 和 DTB；
- 当前日志与静态二进制指纹高度相关，但尚无 BootROM 读取介质的硬件轨迹，也没有在日志中直接记录 BootROM source register。

因此当前可确认的是：主 U-Boot proper 和 Linux 启动资产可以来自 TF；SPL 实际来源仍按既有报告标为“高度相关/待直接闭环”，不能把“Linux 从 TF 启动”升级为“TF SPL 已独立执行”。

另一个 Panther X2 公共项目展示了从 uSD 卡启动 Linux 的实例，并使用 U-Boot 2024.01/后续 Rockchip U-Boot；但其公开 README 没有给出 BootROM source 或 SPL 实际来源证据。它证明该板型支持 uSD 系统启动，不证明在 eMMC 有效 IDB 保留时能由 TF 提供第一阶段 SPL。

### 10.5 MaskROM / Loader 恢复入口与正常 TF 冷启动的区别

Panther X2 专项公开资料表明：
- USB-A 2.0 是 RK3566 DWC3 OTG 接口，可用于 gadget；
- SARADC Channel 0 的板载按钮用于进入 Loader mode；
- Linux 中可通过 `reboot-loader` 进入 Loader；也可长按按钮或在 U-Boot 阶段按住按钮进入 Loader；
- 社区刷机记录描述了先由该按钮进入 Loader，再通过 RKDevTool 请求切换 MaskROM。

这是一条可用于恢复、调试或主机辅助装载的路径，不等于正常上电时 BootROM 会自动从 TF 执行 TF idbloader。进入 MaskROM 后由主机通过 USB 下载/运行 loader，也不属于用户定义的“TF 完整自包含冷启动”。

### 10.6 eMMC_D0 强制失败方法：仅有参考板证据

Rockchip RK3566 EVB2 用户指南描述：上电前将 eMMC_D0 拉低/接地可使 eMMC 引导失败并进入 MaskROM。该方法说明硬件上存在通过令 eMMC 无法响应来迫使 BootROM 转向恢复路径的设计思路。

但这是 RK3566 EVB2 的参考设计，不是 Panther X2 原理图。当前没有证据确认 Panther X2 是否引出 eMMC_D0 测试点、是否有专用开关、是否能安全地在复位期间控制该信号。不得把 EVB2 的按键/短接点位置照搬到 Panther X2，也不得在未确认网络与风险前短接任何焊盘。

### 10.7 当前启动架构判断

- **已验证：** RK3566 官方硬件设计指南列出 eMMC 优先于 SDMMC；SDMMC0_DET 是 JTAG/SDMMC mux，不是介质优先级 strap。
- **已验证：** Panther X2 eMMC 当前归档备份中有有效 IDB；eMMC LBA64 与 LBA16384 启动资产已完成哈希身份核对。
- **已验证：** Panther X2 存在 SARADC0 Loader 按钮路径及可用的 USB OTG Gadget 接口（板级公开软件资料）；它提供 Loader/恢复入口，不是已证明的 BootROM SD 优先选择开关。
- **未验证：** Panther X2 是否存在可在复位期间安全禁用 eMMC、强制 BootROM 跳过 eMMC 的硬件控制/测试点。
- **未验证：** 当前 eMMC SPL 对 SD 启动标记、BCB 或 TF 下一级固件的精确支持机制，以及 eMMC SPL 加载失败后的细粒度回退条件。
- **未验证：** 当前任何一次正常上电中 BootROM 实际选择的介质；现有 SPL/U-Boot 日志尚非 BootROM 读介质轨迹。

**暂定结论：** 在 eMMC 有效 IDB 保留且没有确认到可用硬件 eMMC-disable/BootROM override 之前，不能承诺 TF 能独立提供完整 SPL + U-Boot proper。当前唯一已有实机依据的可复用路线仍是“现有第一阶段 loader/SPL → TF 上的 U-Boot proper → TF 上的 Kernel/initramfs”。真正 TF 自包含启动暂列为**可行性未证实**，不是已否决，也不是已通过。

## 11. eMMC Vendor 数据只读传递：实现约束草案（不含代码）

### 11.1 必须绕过默认“当前启动设备”读取路径

固定参考 Rockchip U-Boot `vendor.c` 的 `vendor_ops()` 通过 `rockchip_get_bootdev()` 取得当前 boot device，再按设备类型确定 Vendor Storage 位置。因此从 TF 启动 U-Boot proper 时，标准接口不能保证读到 eMMC 的 Vendor Storage。

新实现必须显式识别并选择 Panther X2 的 eMMC 控制器/块设备，而不是调用“当前启动设备”路径。优先依据 U-Boot Device Tree 的 eMMC 控制器节点/alias 或板级固定设备引用识别，不依赖 Linux 运行时 `/dev/mmcblkN` 编号。

### 11.2 读取和校验流程

TF U-Boot 与 eMMC U-Boot 应共用同一只读实现：
1. 只读访问 eMMC user-area LBA 7168–7679，共 256 KiB；
2. 读取 vendor0–vendor3 四份 64 KiB 副本；
3. 依据 tag=`DVKR`、version>0、version2==version 筛选有效副本，选择最高 version；
4. 校验 item_num、descriptor 数组边界、ID=3 的 offset/size 边界；
5. 要求 LAN_MAC ID 3 为 12 bytes，校验两个地址均为合法单播地址且彼此不同；
6. 记录副本编号、版本、校验结果，不在公开日志输出真实 MAC 字节。

当前备份中 vendor0 是唯一有效副本（version=2），但启动代码必须按规则扫描四份，不能把 vendor0 永远有效写死。

### 11.3 阻止默认随机 MAC 和 Vendor 写回

固定参考 Rockchip U-Boot `board.c` 的 `rockchip_set_ethaddr()` 在 Vendor Storage 读取失败或 MAC 无效时会生成随机 MAC；启用 Vendor Partition 时还会调用 `vendor_storage_write()` 写回。该默认行为不符合本项目“eMMC 是权威来源、启动时只读、失败不能静默伪造板载 MAC”的原则。

新系统必须禁用或替换这条默认 fallback/writeback 路径：
- 不能在启动时写入或修复 eMMC Vendor Storage；
- 不能因读取失败而自动生成并保存随机地址；
- 失败必须输出明确状态，不能把临时地址记录成板载 MAC；
- 若 eMMC Vendor 数据不可读或校验失败，应让网络接口保持未配置/不启用，或进入明确标记的人工恢复流程；不得静默切换数据源。

### 11.4 Linux 传递

- 对 MAC，优先由 U-Boot 设置 `ethaddr` / `eth1addr`，并通过标准 FDT Ethernet fixup 写入对应节点的 `mac-address` / `local-mac-address`；最终 Linux FDT、接口地址和 GMAC 节点映射需要实机核对。
- 双 MAC 的顺序必须由 Panther X2 两个 GMAC 节点/aliases 明确映射，不以网卡枚举顺序猜测。
- 其他板级数据先盘点消费者；可表达为标准设备树属性的使用标准属性，需要 Linux 驱动访问的再评估 NVMEM cell。
- Rockchip Linux Vendor Storage 驱动虽然固定读取 eMMC LBA 7168，但其 `/dev/vendor_storage` ioctl 同时提供读写接口，不应未经隔离就作为日常系统的只读权威接口。

以上为架构约束草案，尚未编写补丁，也未构建或启动任何新固件。

## 12. P2 当前唯一剩余工作

1. 获取 Panther X2 对应 PCB 版本的原理图/硬件资料，或在用户授权下仅做不拆焊、不短接的外观核对，确定 SARADC0 按钮、eMMC_D0、USB OTG0、复位网络的实际对应关系。
2. 通过精确到 Panther X2 的证据判断是否有不改写 eMMC、可安全使 BootROM 跳过有效 eMMC IDB 的方法。没有该方法时，应把“TF 独立完整冷启动”标为当前硬件条件下不可行/未证实，并向用户提出可选架构，而不是擅自清除 eMMC IDB。
3. 完成后才冻结双启动介质的 SPL/U-Boot/Vendor 读取设计，再重新评估最新维护中的用户空间组件、最小 /init 与 CI。
4. 当前不下载组件源码、不编译、不触发 CI、不写 TF/eMMC、不执行任何短接/复位/刷机实验。

## 13. 本轮新增公开来源

- Rockchip RK3566 Hardware Design Guide V1.1.0, §2.1.5 / §2.1.6:  
  https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- Rockchip Developer Guide SD Boot, RK-KF-YF-171 V1.2.0, §4–5:  
  https://doc.9tripod.com/en/docs/rockchip-official-docs/MMC/Rockchip_Developer_Guide_SD_Boot_CN/
- Rockchip RK3566 EVB2 User Guide V1.1, MaskROM section (eMMC_D0 to GND is EVB-specific reference only):  
  https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_EVB2_User_Guide_V1.1_EN.pdf
- Panther X2 board-specific public software/hardware notes (SARADC0 Loader button, DWC3 OTG USB-A, U-Boot/Buildroot releases):  
  https://github.com/yjdwbj/panther-x2
- Panther X2 community Loader/MaskROM procedure (button + USB, then RKDevTool MaskROM request):  
  https://www.xwenw.com/249466.html
  https://forum.naixi.net/thread-9716-1-1.html
- Rockchip U-Boot reference `vendor.c` and `board.c` at commit `8af253525b7de5f29f7f97dffd18adb77db6456`:  
  https://github.com/rockchip-linux/u-boot/tree/8af253525b7de5f29f7f97dffd18adb77db6456


## 14. 用户确认：沿用原有 Bootloader 设计，聚焦已知问题（2026-11-20）

### 14.1 设计基线

用户明确确认：原有 Bootloader 设计整体没有问题，可以延续原设计；当前需要重点处理的例外是：
- U-Boot 读取过程中“一边读一半”的既有问题（具体表现、阶段、数据对象和触发条件必须以历史日志/源码/测试记录为准，不在本节擅自解释或改写）；
- Vendor 数据读取及向后续启动阶段/Linux 传递的问题。

因此，后续工作不再以“重新设计 Bootloader”为默认方向，而以原有 Bootloader 设计为基线，围绕上述问题做证据审查、根因定位和最小范围修正评估。

### 14.2 保留原则

除非发现与明确业务目标存在可证明的冲突，否则保留原有：
- SPL / U-Boot proper 的职责划分与既有启动流程；
- 启动介质及启动资产的组织方式；
- 原有软件包、工具和接口的设计；
- 已有恢复/救援入口及其工作方式。

不因架构研究或“最小系统”目标而主动重构、替换、拆分或删除原有组件。若发现冲突，先列出证据、受影响的业务要求、风险和可选适配方式，再与用户讨论，不擅自变更。

### 14.3 最小系统的定位

最小系统是否进入最终系统，不作为预设结论：
- 若它能有效隔离启动链问题、验证硬件初始化、网络或存储，或帮助定位 U-Boot 与 Linux 交接问题，可作为阶段性诊断/验收环境；
- 若现有启动流程和原有软件包已能完成所需验证，且加入最小系统没有明确收益，则不强行引入；
- 是否纳入最终架构，须根据调试结果、维护成本和实际业务需求评估。

### 14.4 后续审查顺序（按用户最新纠正更新）

两个问题的原因已在此前工作中完成检查。本阶段不得重新定位根因、重复实机测试或把已知事实重新列为待查事项。

1. 直接回读并采用历史专项报告中已经形成的根因结论、调用路径和证据，不要求用户重做采集。
2. 基于既有结论，评估原有 Bootloader 设计内消除 SPL/proper 跨介质读取不一致的最小调整。
3. 基于既有 Vendor Storage 读取源结论，评估将权威 eMMC 数据接入原有 Vendor API，并沿既有 U-Boot 环境变量/FDT fixup 传递链交付 Linux 的最小调整。
4. 比较候选方案对现有 eMMC 正常系统、TF 启动、原有软件包及 USB 双公头恢复流程的影响，明确回退方式。
5. 先交付静态方案和影响分析；未获用户明确授权前，不写补丁、不构建、不写 TF/eMMC、不刷机、不短接、不改系统配置。

**本节性质：** 用户确认的架构决策与工作约束；两个问题的根因调查视为已完成，后续进入原设计下的局部方案评估，尚不代表问题已经修复。


## 15. 用户确认：沿用原有 Bootloader 设计，不以 TF 自包含为先决目标（2026-11-20）

本节为用户最新架构决策；如与本报告前文将“TF 自包含完整启动链”列为硬性目标的表述冲突，以本节为准。

### 15.1 设计基线

用户明确指出，原有 Bootloader 设计整体没有问题，可以延续原有设计。当前需要处理的例外集中在：
1. 启动链存在 SPL 与 U-Boot proper 跨 eMMC/TF 介质分布的“一边读一半”问题；
2. Vendor 数据读取来源及向后续启动阶段/Linux 的传递问题。

因此：
- 保留原有 Bootloader 软件包、职责划分、配置思路和既有启动流程；
- 不以重做 Bootloader 或另造一套启动架构为目标；
- 不把“TF 必须独立提供 BootROM→SPL→U-Boot proper 全链”作为默认验收条件；
- 仅针对已确认的跨介质固件来源问题和 Vendor 数据路径，评估原设计内的最小范围调整。

### 15.2 启动链问题的处理边界

既有日志、镜像指纹、MMC/ATAGS 映射和文件读取记录已完成对当前混合启动链的分析。不得重新执行相同的启动介质映射调查，也不得把已查明的原因重新列为待调查事项。

后续应直接利用已有结论，比较原有软件包的预期启动流程与当前实际 SPL/proper 来源，评估如何让启动阶段使用一致、明确的原有固件组合。任何候选调整均须：
- 说明它保留了原设计的哪些部分；
- 说明它如何消除跨介质的隐式依赖；
- 说明是否影响现有 eMMC 正常系统、TF 启动和既有 USB 双公头恢复方式；
- 在用户授权前仅做源码/配置/镜像静态评估，不写介质、不刷机、不启动实验固件。

### 15.3 Vendor 数据路径

已完成的证据包括：
- eMMC user-area 备份 LBA 7168–7679 的四份副本解析：vendor0 是唯一有效副本，version/version2 均为 2，含 LAN_MAC ID 3、12-byte 双 MAC；其余三份为全零；
- Rockchip U-Boot 标准 Vendor Storage 路径按当前 bootdev 选择介质；TF 启动时不会自动转向 eMMC；
- 既有实机确认当前 TF 启动路径读取 TF Vendor 数据；
- U-Boot 的 MAC 环境变量与 FDT Ethernet fixup 是既有传递机制。

这些均为已完成结论，不得重做。后续工作是评估在保留原有 U-Boot Vendor Storage 设计的前提下，如何让其读取权威 eMMC 数据，并沿既有环境变量/FDT fixup 路径传递给 Linux。优先评估原生接口/配置能否满足，不另造私有 ABI；读取失败不得静默以随机 MAC 冒充板载 MAC；研究阶段保持只读。

### 15.4 最小系统定位

最小系统是否加入最终架构，由实际调试需要和评估结果决定：
- 若有助于隔离 Linux 用户空间变量、验证网络/存储或定位启动交接问题，可作为临时诊断环境；
- 若原有系统环境足以完成验证，或最小系统不能带来明确诊断价值，则不强制加入最终系统；
- 不得为了“最小化”而破坏原有软件包设计或删除已有功能。

**本节性质：** 用户确认的架构决策与后续工作边界；不是新一轮根因调查，也不表示两个已知问题已经修复。


## 16. 双介质独立启动可行性：SoC 机制核对结果（2026-11-20）

本节基于公开 Rockchip 资料与仓库已有 Panther X2 实测证据；没有执行新的设备操作。

### 16.1 公开资料的交叉结论

- RK3566 Hardware Design Guide V1.1.0 §2.1.5：普通 BootROM 介质顺序 eMMC 在 SDMMC 前。
- 同指南 §2.1.6：`SDMMC0_DET` 只切换 SDMMC/JTAG 引脚复用，不切换启动介质优先级。
- Rockchip U-Boot v2017(next-dev) 开发指南 §6.5.4：pre-loader/miniloader 先由 BootROM 加载，随后扫描 SD 卡并可从 SD 加载 U-Boot proper。此机制是“前级 pre-loader → SD proper”，不等于 BootROM 直接从 TF 加载 SPL。
- Rockchip SD Card Boot Reference V1.2.0 的平台表：RK3566/RK3568 不支持旧式 IDB block card-type flag；Android BCB 的 `recovery\\n--rk_fwupdate\\n` 是 SD upgrade/recovery 标记，不是普通 TF SPL 启动选择信号。

### 16.2 Panther X2 既有现场证据的意义

- 2026-11-18 实机 `0xFDCC0010=0x00000002`，对应 eMMC BootROM source ID。
- eMMC user-area LBA64 的有效 IDB 已确认；boot0/boot1 全零。
- 2026-11-19 的启动链已确认运行 eMMC 上的 SPL，再从 TF/SD 加载 U-Boot proper。

这组证据说明当前混合链符合 RK3566 的普通 BootROM 顺序和 Rockchip pre-loader 从 SD 加载后级的机制。它不是单纯配置疏忽就能靠改变 U-Boot proper 搜索顺序解决的问题。

### 16.3 候选路线评估

| 路线 | 是否满足 TF SPL + proper 同介质 | 评估 |
|---|---|---|
| 仅把完整 idbloader 与 proper 放到 TF，eMMC IDB 保留 | 否，BootROM 优先 eMMC | 不成立为可靠方案 |
| Rockchip SD Boot Card / SD upgrade BCB | 否，属于 pre-loader 后级加载或升级/recovery | 不满足目标 |
| 调整 eMMC SPL 的 proper 搜索顺序 | 否，只改变 SPL→proper，不改变 BootROM→SPL | 不能解决第一段跨介质 |
| 上电前由原厂硬件隔离 eMMC，使 BootROM 可继续探测 SD | 理论上可能，但 Panther X2 是否具备此硬件未验证 | 唯一值得继续核实的硬件方向 |
| 清除/禁用 eMMC IDB 或改 eMMC 启动配置 | 可能改变启动源，但违反当前保护 eMMC 的研究约束 | 不纳入当前方案，不做试验 |
| 保留原有混合链并固定版本/来源/更新顺序 | 否，但可维护性可通过显式依赖管理改善 | 若硬件不支持独立 TF 冷启动，则作为回退方案 |

### 16.4 下一步

仅寻找 Panther X2 原厂原理图、PCB、BOM 或板级设计资料，确认 eMMC 是否有独立电源门控、复位门控或上电启动选择电路，并与板上按键/USB 恢复信号做对应。不要重复查芯片启动顺序和 SDMMC0_DET；不要把 Loader/MaskROM 恢复模式当作普通冷启动源选择。

若没有可用板级机制，结论应明确为“在保留当前 eMMC IDB 的前提下，TF 独立 BootROM→SPL 启动不具备已知可行路径”，随后保留原有启动链并明确版本绑定。若有，再设计不触碰 eMMC 数据的受控验证计划，另行等待用户授权。


## 17. 新增公开 Panther X2 TF/uSD 启动资料与板级资料检索结果（2026-11-20）

本节只记录公开资料，不将第三方启动描述扩大解释为已验证的 BootROM/SPL 介质来源。

### 17.1 第三方 uSD 启动系统证据

1. `yjdwbj/panther-x2` 项目 README（tag `v1.0`，2024-06-14）：
   - 记录 U-Boot 2024.01、Kernel 6.9.4、Debian 12；
   - 明确标注 “Boot log (booting from uSD Card)”；
   - Linux kernel command line 的 root UUID 为 `248cdb28-ac33-4448-adbc-2972f265f0ff`；启动日志显示该 UUID 挂载自 `mmcblk0p2`，并将 `mmcblk0p1` 挂载为另一文件系统；
   - 同时内核识别到另一块 32GB eMMC，设备号为 `mmcblk1`，并枚举其 boot0/boot1/RPMB；
   - 这强力支持其 boot/root 系统分区均位于 uSD，而 eMMC 仍在机内；但 README 没有提供 BootROM/SPL/U-Boot 阶段 UART 日志，不能判定 U-Boot proper 的来源，也不能证明 SPL 与 proper 均由 uSD 提供。

2. PiLoader Panther X2 / MerryIoT 安装指南：
   - 声称 Panther X2 与 MerryIoT Hotspot Miner V1 使用相同硬件；
   - 将镜像写入新的 microSD，替换原卡后启动；
   - 声称不改动设备内部存储，并保留原卡用于恢复原厂软件；
   - 未说明 BootROM source、SPL/proper 实际介质，也未展示 U-Boot 阶段日志。

两项资料支持的结论是：**Panther X2 存在从 TF/uSD 运行 Linux、同时保留 eMMC 内容的第三方实践；其中 v1.0 明确把 rootfs 与另一分区放在 uSD。** 它们不证明完整 U-Boot 自包含于 TF。结合本项目已验证的 eMMC SPL→TF proper 路径，一个与现有证据吻合的解释是：BootROM/eMMC SPL → TF U-Boot proper → TF boot/kernel/rootfs；但第三方未提供 U-Boot UART 阶段日志，因此仍不能把这个解释升级为已验证事实。

### 17.2 第三方资料之间的表面矛盾

Lorenzo Gangemi 于 2026-06-14 发布的 Panther X2 记录称，其将普通 Armbian 镜像写入 SD 后，设备仍启动原厂 eMMC 系统；作者据此认为 eMMC bootloader 优先，并未找到按钮/短接强制 SD 启动方法。

这与专用 Panther X2 SD 镜像/PiLoader 可以从 TF 运行 Linux 并不必然矛盾：
- 普通 Armbian 镜像可能不符合设备现有 pre-loader 对 SD 后级固件布局/格式的要求；
- 专用镜像可能适配现有 eMMC pre-loader 的 SD 加载路径；
- 两者都没有证明 BootROM 直接从 TF 加载 SPL。

因此不能再笼统表述“Panther X2 完全不能从 TF 启动”。准确区分：
- TF 上运行 Linux：有第三方公开实践；
- eMMC SPL → TF proper：本项目已有实机验证；
- TF SPL → TF proper（完整 TF 自包含 U-Boot）：尚无证据证明在当前 eMMC 有效 IDB 保留时可行。

### 17.3 板级资料检索

- 找到 Panther X2 PCB 顶面清晰照片，丝印为 `BROWAN H1GW V04`，与本项目板型吻合；照片可用于板型/元件位置参考，但没有电路网络、背面走线或电源控制原理图信息。
- FCC 的 BROWAN MerryIoT L0001（Panther X2 相关同系列产品）页面公开内部照片；schematics 项仅列为 metadata，页面标注长期保密。不能据此获得可核验的完整原理图。
- 公开用户手册只列出 RK3566、32GB eMMC、TF 插槽、GPIO 按键和 USB 等规格，没有 eMMC 电源门控/复位隔离或 BootROM 启动选择电路说明。
- 当前公开检索未找到可核验的 H1GW V04 原理图、PCB netlist、BOM 或背面高清图；这只是公开资料检索结果，不代表 Browan 内部不存在这些设计文件。

### 17.4 当前决策影响

新增资料进一步说明 TF 启动 Linux 本身是可用能力，不能把“BootROM eMMC 优先”误解为“TF 卡完全没有启动用途”。但它不改变完整 U-Boot 自包含的核心门槛：BootROM 必须先执行 TF 上 SPL，或必须有原厂硬件机制使 BootROM 不读取/跳过 eMMC IDB。

当前没有新证据证明 H1GW V04 存在 eMMC 上电隔离/复位门控/启动选择电路。下一步只需继续寻找 H1GW V04 板级背面/原理图/BOM 或 Browan 正式资料；若无法获得，需把“板级硬件机制未知”作为明确证据边界，不能通过推测补齐。

### 17.5 公开来源

- yjdwbj Panther X2 项目（uSD 启动日志、U-Boot 2024.01、Kernel 6.9.4、Debian 12）：https://github.com/yjdwbj/panther-x2
- PiLoader Panther X2/MerryIoT 指南：https://piloader.com/browanx2-install/browanx2-get-started
- Panther X2 H1GW V04 PCB 顶面照片及作者对普通 SD 镜像启动的记录：https://lorenzogangemi.com/blog/repurposing-panther-x2/
- BROWAN MerryIoT L0001 FCC 资料（内部照片及 schematics 元数据）：https://fccid.io/2AAS9-L0001

**证据等级：**
- TF/uSD 上运行 Linux：第三方公开项目/安装指南记录；非本项目实机复验。
- U-Boot 2024.01 是否完全从 TF 启动：未证明。
- Panther X2 是否有 eMMC 硬件隔离/启动选择电路：未验证。


## 18. 第三方 yjdwbj Panther X2 v1.0 U-Boot 截图的逐行静态核对（2026-11-20）

本节基于 v1.0 标签中的原始 PNG（`images/panther-x2-rk3566-uboot.png`，156,082 bytes）逐行辨读，并与同标签 README 中的 Linux 启动日志交叉核对。没有下载或运行第三方固件。

### 18.1 U-Boot 截图直接显示的启动路径

截图中的关键内容：
- `U-Boot SPL 2024.01-040842-g31b5240876-dirty (May 30 2024)`
- `Trying to boot from MMC1`
- SPL 随后对 FIT 中 config、ATF、U-Boot、多个 FDT 和 BL32 image 执行 SHA256 hash 检查，均显示 OK。
- U-Boot proper 显示 `U-Boot 2024.01-040842-g31b5240876-dirty`。
- proper 的 MMC 控制器映射：
  - `mmc@fe2b0000: 0`
  - `mmc@fe2c0000: 1`
  - `mmc@fe310000: 2`
- 随后明确显示：
  `Booting bootflow 'mmc@fe2b0000.bootdev.part_1' with extlinux`
- 读取 `/boot/extlinux/extlinux.conf`、`/Image`、`/dtbs/rockchip/rk3566-panther-x2.dtb`，并加载 `/rootfs.cpio.gz` initramfs。
- proper 的 Model 字符串显示 `Radxa ROCK 3 Model C`，但后续实际加载 Panther X2 专用 DTB；这是第三方 U-Boot 构建配置的一个待解释细节，不应误认为它使用了 Radxa 实物板。

### 18.2 与同标签 Linux 日志交叉核对

同标签 README 的 uSD Linux 启动日志明确显示：
- `mmcblk0` 是 116 GiB SDXC，分区为 p1/p2；
- `mmcblk1` 是 32 GB eMMC，并枚举 `mmcblk1boot0`、`mmcblk1boot1` 和 RPMB；
- kernel command line 的 root UUID 为 `248cdb28-ac33-4448-adbc-2972f265f0ff`；
- `EXT4-fs (mmcblk0p2)` 挂载该 UUID，确认根文件系统在 TF/uSD 的 p2。

结合该版本日志中 MMC 控制器地址和设备映射，`fe2b0000` 对应 SD/TF 控制器；U-Boot proper 从该控制器分区 1 读取 extlinux、Kernel、DTB 和 initramfs。SPL 的 `Trying to boot from MMC1` 则指向其 SPL 启动设备为 MMC1；按 Rockchip RK3566 启动源编号与本项目已验证的 MMC1/eMMC、MMC2/SD 对照，证据高度支持其为 eMMC 前级加载 TF 后级。

### 18.3 证据结论与边界

- **已由截图直接证明：** SPL 2024.01 执行；proper 2024.01 执行；proper 从 `fe2b0000` 的 TF/SD 控制器分区 1 读取 extlinux、Kernel、DTB、initramfs。
- **已由 Linux 日志直接证明：** 系统 rootfs 位于 TF/uSD 的 `mmcblk0p2`，同时 eMMC 仍被识别为 `mmcblk1`。
- **高置信度判断：** 这是 eMMC/MMC1 前级 + TF/SD 后级的混合启动案例，与本项目现有实机路径相同类别；它不是 TF SPL + TF proper 自包含启动的证据。
- **尚未直接看到：** BootROM source tag 的独立 UART 行、SPL 镜像的原始 LBA/介质校验，以及 eMMC IDB 与该第三方 SPL 的 hash 对照。因此不要把第三方 SPL 的物理存放位置表述成 100% 直接实证；准确标记为“根据 MMC1 启动提示及 RK3566 介质映射，高置信度推断来自 eMMC”。
- `Trying to boot from MMC1` 是 SPL 阶段的启动设备提示，不是 U-Boot proper 的 MMC 设备枚举；两者编号体系不能混为一谈。

### 18.4 v1.0 下载包实际内容核对

- v1.0 Git tree 只有 `README.md` 和 `images/` 目录（内含三张 PNG）；没有 `idbloader.img`、`u-boot.itb`、`trust.img`、整卡镜像、分区表文件或 U-Boot 源码。
- README 所谓 U-Boot “Pre-built” 链接实际指向 GitHub 的 `archive/refs/tags/v1.0.tar.gz` 仓库标签源码归档，不是独立 U-Boot 固件发布包。
- 因而目前无法对第三方 v1.0 固件做二进制头部、FIT 内容、SPL hash、扇区布局的离线取证；但其启动截图已经足以识别其 proper 从 TF 加载启动文件的路径。

### 18.5 第三方项目当前 main 分支的后续演进

当前 main 分支已经不是 v1.0 的 TF 启动布局：
- README 声明当前版本为 Buildroot 2026.08 + Linux 6.12.69 + Rockchip U-Boot `next-dev`，使用 FIT `boot.img` 并通过 RKFW/Rockchip tools 刷写。
- 当前 GPT 分区说明明确列出 `uboot` 4 MB（U-Boot FIT）、`boot` 64 MB（Kernel+DTB FIT）、`rootfs` 16 GB 等。
- 当前 `dmesg.log` kernel command line 明确有 `storagemedia=emmc`、`androidboot.storagemedia=emmc`，root PARTUUID 对应 `mmcblk1p4`，且日志确认 eMMC 是 `mmcblk1`。
- 版本字符串记录 DDR v1.26、SPL v1.14、BL31 v1.46、BL32 v2.18 和 U-Boot commit/time。

这说明第三方后来转向一套在 eMMC 上布局和运行的系统，不能把当前 main 分支的 eMMC 部署说明倒推成 v1.0 的 TF 自包含启动证明。当前 main 的分区表和 dmesg 可用于参考 Rockchip FIT/RKFW 方案，但不是本项目 TF 独立启动可行性的证据。

### 18.6 对本项目的决策影响

第三方 v1.0 的价值不在于证明 TF 完整启动，而在于它提供了一个与 Panther X2 实机一致的独立交叉案例：
- eMMC 前级提供 SPL；
- U-Boot proper 从 TF 读取 extlinux 和系统启动文件；
- Kernel/rootfs 运行于 TF；
- eMMC 仍保留在设备内。

因此它强化了“Panther X2 从 TF 运行完整 Linux，并不代表 TF 自带完整 U-Boot”的区分，也进一步说明当前混合链是可工作的原厂/第三方兼容路径。若最终硬件无法实现 TF 独立 SPL 启动，这种路径可作为有证据支撑的回退模式，但需显式固定 SPL 与 proper 的版本关系和更新流程。

## 19. H1GW V04 板级照片/FCC 档案复核与 eMMC 上电隔离可行性边界（2026-11-20）

### 19.1 可确认的板型与公开照片

- Lorenzo Gangemi 2026-06-14 的 Panther X2 拆机记录明确标注板型为 BROWAN H1GW V04，并展示 PCB 顶面照片；照片可见 RK3566 散热片、TF 插槽、USB、Ethernet、DC 输入及若干电源器件。
- 该照片没有背面走线、原理图网络名、器件完整料号/BOM，也无法从顶面确认 eMMC VCC/VCCQ 是否由独立负载开关控制。
- FCC ID 2A3OG-PANTHER-X2 的 2022-04-18 Internal Photos 档案（Document ID 5825812）公开，4 页、772,563 bytes；FCC 页面同时列出 2021-11-17 的另一组 Internal Photos（Document ID 5542190）。这些是内部照片而不是原理图。当前可公开检索到的资料仍未提供可核验的 H1GW V04 原理图/netlist/BOM。
- FCC 档案的申请主体为 E-sun Electronics Limited；与 BROWAN H1GW V04 的板型关系需以照片丝印/实物为准，不能把 FCC 文件自动视为所有硬件修订完全相同。

### 19.2 RK3566 eMMC 电源控制对启动选择的约束

依据 RK3566 Hardware Design Guide V1.1.0 §2.1.5：
- BootROM 普通启动顺序中 eMMC 优先于 SDMMC。
- BootROM 在 SPL 执行之前就进行介质探测和 IDB 读取。

同指南 eMMC 电源章节说明：
- RK3566 eMMC 控制器位于 VCCIO2，SoC 侧 IO 电源本身没有独立的 eMMC 启动门控时序要求；
- eMMC 颗粒 VCC/VCCQ 必须在 RK3566 发出 CMD 命令前上电并稳定；
- eMMC 进入 sleep 后，RK3566 可关断其 VCC 以降低功耗；这是运行期电源管理描述，不代表上电启动前存在可供 BootROM 使用的 eMMC-disable 功能。

因此，要让 BootROM 在保留 eMMC 原始 IDB 数据的情况下跳过 eMMC，必须存在 BootROM 开始介质探测前就生效的板级硬件行为（例如 eMMC 电源未上电/被隔离，或其他经 Rockchip 认可的硬件隔离机制）。Linux DTS 的 regulator 描述、U-Boot GPIO 控制或启动后关断 eMMC 均不能满足这个时序条件。

### 19.3 当前硬件证据状态

| 项目 | 状态 |
|---|---|
| H1GW V04 顶面照片/板型丝印 | 已找到 |
| Panther X2 FCC 内部照片档案 | 已找到（2021、2022 两组） |
| H1GW V04 背面高分辨率、可追踪电源网络的照片 | 尚未找到可核验版本 |
| eMMC VCC/VCCQ 独立负载开关及 EN 网络 | 未验证 |
| eMMC RESETn 是否可在 BootROM 探测前被硬件保持有效 | 未验证 |
| SoC GPIO/按键是否能在 BootROM 前控制 eMMC 供电 | 没有证据；不能假定 |
| 原厂是否提供 TF/eMMC 启动源选择跳线/按键 | 没有证据 |

### 19.4 方案结论更新

当前仍不能确认 Panther X2 具备可在 BootROM 介质探测前隔离 eMMC 的硬件。顶面照片及 FCC 内部照片档案没有提供足以闭环的电源网络证据。

所以：
1. 不应仅凭照片猜测负载开关或测试焊盘，更不能建议短接；
2. 不应将 Linux/U-Boot 的运行期 regulator 控制误认为能影响本次 BootROM 选源；
3. 保留 TF 独立 SPL→TF proper 作为“硬件条件未知、未证明可行”的研究目标；
4. 在没有原理图/背面走线证据前，维护性更可靠的回退仍是保留原有 BootROM/eMMC SPL 设计，并明确管理其与 TF proper 的版本绑定；
5. 后续最有价值的板级证据是 H1GW V04 背面高清照片、eMMC 颗粒完整料号与周边电源器件标识，或原厂原理图/BOM。即使取得背面照片，也只做无损静态识别，不据此执行电气操作。

### 19.5 来源

- RK3566 Hardware Design Guide V1.1.0：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- BROWAN H1GW V04 PCB 顶面照片及拆机记录：https://lorenzogangemi.com/blog/repurposing-panther-x2/
- FCC 2022 Panther X2 Internal Photos #5825812：https://fccid.io/2A3OG-PANTHER-X2/Internal-Photos/Internal-Photos-5825812
- FCC 2021 Panther X2 Internal Photos #5542190：https://fccid.io/2A3OGPANTHERX2/Internal-Photos/Internal-Photos-5542190


## 20. 原有 Bootloader 内的 proper 介质选择与 eMMC 权威 Vendor 读取方案评估（2026-11-20）

本节只审查已有 Rockchip U-Boot 源码机制并形成静态方案；不修改源码、不构建、不写入 TF/eMMC、不操作设备。

### 20.1 原有启动设备选择机制已经具备按介质选择 proper 的基础

以已审计的 Rockchip U-Boot 参考提交 `8af253525b7de5f29f7f97dffd18adb77db6456a` 为准：

1. `arch/arm/mach-rockchip/param.c` 的 `param_parse_atags_bootdev()` 将 SPL 传入的启动介质标记映射为 U-Boot block device：
   - `BOOT_TYPE_EMMC` → `devtype=mmc`, `devnum=0`；
   - `BOOT_TYPE_SD0` / `BOOT_TYPE_SD1` → `devtype=mmc`, `devnum=1`。
2. `arch/arm/mach-rockchip/boot_rkimg.c` 的 `boot_devtype_init()` 优先级为：
   - 编译配置 `CONFIG_ROCKCHIP_BOOTDEV`；
   - SPL ATAGS（启用 `CONFIG_ROCKCHIP_PRELOADER_ATAGS` 时）；
   - `rk_board_scan_bootdev()` 扫描；
   - 全部失败时回退 `mmc 0`。
3. 该函数将选择结果写入 `devtype/devnum`。后续 `rockchip_get_bootdev()`、Rockchip Vendor Storage 和若干启动文件读取路径都使用这组结果。
4. 同一源码的 `get_bootdev_type()` 把 `mmc 1` 标记为 SD，把 `mmc 0` 标记为 eMMC。

这说明原设计并非只能从一个固定介质加载 proper。SPL 传入的 ATAGS 可以把 proper 阶段的启动设备明确标为 eMMC 或 SD。现有实机的 eMMC SPL → TF proper 路径也与 ATAGS → `mmc 1` 机制相吻合。

### 20.2 启动文件来源的最小方案

建议保留 SPL、ATAGS、`devtype/devnum`、Rockchip bootdev 和原有 proper 文件加载机制，不重写启动框架。

目标行为：

| 启动目标 | SPL/ATAGS 交接给 proper 的设备 | proper/启动文件来源 |
|---|---|---|
| TF 启动 | `mmc 1` / SD | TF |
| eMMC 启动 | `mmc 0` / eMMC | eMMC |

这里的“TF 启动”是指现有 SPL 已经选择 TF 作为 proper/系统启动介质；不表示 BootROM 已能绕过 eMMC 并从 TF 加载 SPL。当前 RK3566 BootROM 介质优先级和本机启动链证据仍然有效。

需要注意：当前实机日志已证明本机此刻走的是 eMMC SPL → TF proper。要实现另一分支，还需确认现有 SPL 对“TF 不存在/不选择 TF 时回到 eMMC proper”的实际回退规则，以及配置中是否存在固定 `CONFIG_ROCKCHIP_BOOTDEV` 覆盖 ATAGS 的情况。这是实现方案的源码配置核对，不是重新调查已知混合启动根因。

### 20.3 Vendor Storage 当前为何会随 proper 介质变化

同一参考提交的 `arch/arm/mach-rockchip/vendor.c`：

- `vendor_storage_init()` 调用 `rockchip_get_bootdev()` 选择 block device；
- `vendor_ops()` 也调用 `rockchip_get_bootdev()` 执行底层读写；
- MMC Vendor Storage 固定使用该 MMC 设备上的 `EMMC_VENDOR_PART_OFFSET`；
- 全局 `bootdev_type`、`vendor_info` 缓存初始化后的设备类型和数据。

因此，若 proper 的 `devtype/devnum` 为 `mmc 1`，标准 Vendor Storage 会读取 TF 的 Vendor 区；若为 `mmc 0`，才会读取 eMMC Vendor 区。该行为与本项目已确认的 TF Vendor 读取现象一致。

**不能**简单地在启动早期全局把 `devnum` 强制改为 0：这样会同时改变启动文件、分区、bootargs、升级/恢复等其他依赖 `rockchip_get_bootdev()` 的路径，破坏原有介质选择职责。

### 20.4 eMMC 权威 Vendor 数据的最小隔离方案

建议将两种“设备来源”明确分离：

- **Boot device（动态）**：继续由 ATAGS/`devtype/devnum` 决定，供 proper、Kernel、DTB、initramfs、bootargs 等现有启动路径使用。
- **Board identity storage（固定）**：LAN_MAC 的权威来源固定为 eMMC user area 的 Vendor Storage 区，不跟随当前启动介质变化。

实现方向（仅方案，不是已编写补丁）：

1. 保留现有通用 `vendor_storage_read/write()` 及其 bootdev 语义，不改变其他现有调用者。
2. 在 Vendor Storage 内部增加一个**只读、显式指定 eMMC mmc0 block descriptor** 的读取入口/内部 helper；独立解析 eMMC Vendor Storage 的四份副本，选择有效且版本最新的副本。
3. 该专用入口不提供写操作，不调用通用 `vendor_storage_write()`，不修改通用 Vendor Storage 的全局 `bootdev_type/vendor_info` 状态，避免 TF/eMMC 两套数据上下文串扰。
4. `rockchip_set_ethaddr()`（或保留原函数名的最小适配）改为从该 eMMC-only read-only 入口读取 LAN_MAC ID 3 的 12 bytes。
5. 两个 MAC 均通过长度、单播有效性及互异性校验；读取失败或数据无效时打印明确错误并不设置伪造 MAC，不生成随机值、不写回任何 Vendor Storage。
6. 保留现有 `ethaddr/eth1addr` 环境变量和 `fdt_fixup_ethernet()` 机制，将权威 MAC 交给 Linux DTB；继续按现有 `ethernet0` alias 与 `FDT_SEQ_MACADDR_FROM_ENV` 配置处理 GMAC 对应关系，不另造 Linux 私有传递接口。
7. eMMC 读取失败时不得回退到 TF Vendor MAC；否则会再次出现不同启动介质导致 MAC 身份变化的问题。

### 20.5 两项调整组合后的目标行为

| 项目 | TF 作为系统启动介质 | eMMC 作为系统启动介质 |
|---|---|---|
| SPL 来源 | 按现有 BootROM/SPL 设计 | eMMC |
| U-Boot proper | TF | eMMC |
| Kernel/DTB/initramfs | TF | eMMC |
| Linux rootfs | TF | eMMC |
| LAN_MAC 权威来源 | eMMC Vendor Storage | eMMC Vendor Storage |
| Linux MAC 交接 | 现有 U-Boot env → FDT fixup | 相同机制 |
| USB 双公头救援 | 原有机制完整保留 | 原有机制完整保留 |

说明：表格中的 TF SPL 来源并非承诺；在当前硬件证据下，TF 模式仍由 eMMC 前级 SPL 进入。表格真正要解决的是 proper 及其后续启动文件的介质一致性，以及硬件身份数据不随启动介质变化。

### 20.6 风险、保护条件与待核对项

- **构建版本边界：** 上述调用链来自与当前 U-Boot 时代相符的 Rockchip 参考提交，不能直接当成当前 Panther X2 二进制的精确源码；实施前须对拟采用的原有 U-Boot 源码分支逐项确认函数和配置仍一致。
- **启动介质选择：** 核对原有 SPL 生成 ATAGS 的具体路径、proper 回退行为、`CONFIG_ROCKCHIP_BOOTDEV` 是否覆盖 ATAGS、TF/eMMC 分区/镜像格式是否匹配。只做源码/配置静态审查。
- **Vendor 并发/缓存：** 专用 eMMC read-only 入口应使用独立上下文，不能复用会被通用 Vendor Storage 写接口修改的全局缓存。
- **数据安全：** 禁止任何 Vendor 写回；禁止随机 MAC fallback；禁止把 eMMC user-area 以外的 boot0/boot1 当作 Vendor 来源。
- **FDT 对应关系：** 必须保留现有 Panther X2 `ethernet0 → gmac1` alias 及两个 MAC 的编号关系；不得因新读取入口改变 ethaddr/eth1addr 顺序。
- **恢复机制：** 不改变 USB 双公头、Loader/rockusb、MaskROM 等现有救援入口；任何 proper 更新都必须保留可恢复的原有组合。
- **尚未完成：** 尚未逐文件审计当前拟用 U-Boot 分支的 SPL ATAGS 产生逻辑、SPL proper fallback 顺序、配置是否覆盖 ATAGS，以及专用 eMMC read-only API 的具体代码落点。

### 20.7 当前静态方案结论

**方案方向可行，且不需要重构原有 Bootloader：**
- proper 的介质选择沿用原有 ATAGS/`devtype/devnum`；
- proper 和系统启动文件按选定介质保持一致；
- Vendor LAN_MAC 的读取源独立固定为 eMMC mmc0；
- MAC 仍走原有 U-Boot 环境变量和 Linux FDT fixup；
- 通用 Vendor API、其他启动路径和 USB 双公头救援机制保持不变。

目前这是设计层面的可行方案，不代表当前二进制已经具备 eMMC 固定只读 Vendor 入口，也不代表 proper 的 eMMC fallback 已经通过源码配置核验。下一步应只做这两处具体源码落点的只读审查，再形成补丁设计；未经用户明确授权不编写/应用补丁、不构建、不写卡。


## 21. SPL 实际成功加载介质、ATAGS 来源及 proper 选择优先级的补充核对（2026-11-20）

本节对 §20 中“ATAGS 反映实际启动介质”的成立条件作进一步限定。核对了 Rockchip U-Boot 参考提交 `8af253525b7de5f29f7f97dffd18adb77db6456`，以及 Radxa `stable-4.19-rock3` 固定提交 `c55987146f4f9b20f7cb2f917ca88300419afe8d`。二者不是当前 Panther X2 二进制的源码证明，只用于解释原有机制和候选实现的边界。

### 21.1 ATAGS 记录的是 SPL 成功加载镜像所用的 loader 编号

通用 U-Boot SPL `common/spl/spl.c` 的 `boot_from_devices()` 在某个 loader 成功加载镜像后执行：

`spl_image->boot_device = spl_boot_list[i]`

Rockchip `arch/arm/mach-rockchip/spl.c` 的 `spl_perform_fixups()` 再调用：

`atags_set_bootdev_by_spl_bootdevice(spl_image->boot_device)`

Rockchip `rk_atags.c` 的 `spl_bootdev_map[]` 映射：
- `BOOT_DEVICE_MMC1` → `BOOT_TYPE_EMMC`
- `BOOT_DEVICE_MMC2` → `BOOT_TYPE_SD0`

因此，在 ATAGS 功能启用且使用上述通用链路时，ATAGS 表示的是**本次成功加载 U-Boot proper 的 SPL loader 设备**，而不只是 BootROM 最初读取 SPL 的介质。这正是我们希望 proper 选择对应启动文件来源的语义。

### 21.2 必须区分默认 SPL 设备和最终成功 loader

两份候选源码的 `spl_boot_device()` 默认实现均返回 `BOOT_DEVICE_MMC1`；通用 `common/spl/spl.c` 的默认 `board_boot_order()` 只把该设备放入启动列表第一项。因此，**仅使用默认实现时，SPL 默认只尝试 MMC1/eMMC，不会自动尝试 MMC2/TF**。

但 SPL 框架允许板级 `board_boot_order()` 提供多个候选 loader。若列表中先后包含 MMC1、MMC2，`boot_from_devices()` 会把实际成功的那个 loader 写入 `spl_image->boot_device`，随后 ATAGS 就能准确传递 MMC1/eMMC 或 MMC2/TF。当前本机日志中出现 `Trying to boot from MMC2`，说明实际运行的 SPL 路径并非上述“默认只尝试 MMC1”的简单配置；该事实沿用已有实机记录，不在本节重复实机检查。

### 21.3 BROM source tag 是另一条路径，不能与 SPL loader 混淆

同一 `rk_atags.c` 还提供：
- `get_bootdev_by_brom_bootsource()`：读取 `BROM_BOOTSOURCE_ID_ADDR`；
- `atags_set_bootdev_by_brom_bootsource()`：把 BootROM 原始启动源写入 ATAGS。

其 `bootdev_map[]` 映射 BootROM source ID（例如 eMMC=2、SD=5）到 Rockchip boot type。

但所审查的通用 `spl_perform_fixups()` 使用的是 `atags_set_bootdev_by_spl_bootdevice(spl_image->boot_device)`，不是 BROM source helper。两条路径语义不同：
- BROM source：BootROM 最初从哪里加载 pre-loader；
- SPL loader source：当前 SPL 最终从哪里成功加载 proper。

本项目需要 proper 和系统启动文件与 SPL 实际成功加载 proper 的介质保持一致，因此应优先保留“成功 loader”语义，不能简单改用 BROM source 覆盖它。

### 21.4 proper 的启动设备选择优先级存在源码分支差异

**Rockchip 参考提交 8af2535：**
- `boot_devtype_init()` 优先调用 `param_parse_assign_bootdev()`，再尝试 ATAGS，最后扫描；
- `param_parse_assign_bootdev()` 使用编译期 `CONFIG_ROCKCHIP_BOOTDEV` 字符串；
- 因此若构建时设置该宏，固定配置会覆盖 SPL ATAGS，必须在目标 defconfig/构建参数中核实该宏是否存在及其实际值。

**Radxa stable-4.19-rock3 提交 c559871：**
- 该分支 `boot_devtype_init()` 先处理 SCSI/NVMe，再读取 ATAGS，最后扫描；
- 该函数没有 8af2535 中的 `param_parse_assign_bootdev()` 优先分支；
- 若 ATAGS 有效且对应块设备存在，就使用 ATAGS 指定设备；否则再扫描并在失败时默认 `mmc 0`。

不能把一个分支的优先级描述直接套到另一个分支，更不能据此推定当前 Panther X2 二进制的配置。

### 21.5 对原有双介质启动设计的修正结论

- 原有设计方向仍可保留：SPL 成功从哪一个 MMC loader 读取 proper，就将该 loader 设备写入 ATAGS；proper 依 ATAGS 选择相同介质上的启动文件。
- 关键不是重新设计 ATAGS，而是确认当前 Panther X2 SPL 的 `board_boot_order()` / loader 列表确实包含现有设计所需的 MMC1/MMC2 顺序，并且实际成功设备能进入 `spl_image->boot_device`。
- 对 8af2535 这一类存在编译期 bootdev 覆盖的 proper，必须确保目标构建没有固定配置压过 ATAGS；对 c559871 这类 ATAGS 优先分支则检查 ATAGS 缺失/设备不可用时的 scan 顺序。
- 这项核对是对候选源码机制的限定，不重新调查本机已确认的 SPL→proper 介质路径。

### 21.6 Vendor API 的额外安全发现

在 8af2535 与 c559871 两份源码中均确认：
- `vendor_storage_init()` 通过 `rockchip_get_bootdev()` 获取设备，并把解析结果放入全局 `vendor_info` / `bootdev_type`；
- `vendor_ops()` 每次也重新调用 `rockchip_get_bootdev()`；
- `vendor_storage_read()` 依赖上述全局初始化状态；
- `rockchip_set_ethaddr()` 在读取失败/地址无效时生成随机 MAC；启用 Vendor Partition 时还可能调用 `vendor_storage_write()` 回写。

因此，最小安全实现不应临时修改全局 `devnum` 后调用现有 `vendor_storage_read()`。这种做法会污染 bootdev 缓存及 Vendor 全局状态，也可能使其他调用者误读/写入另一介质。

推荐保持原 API 完全不变，为 LAN_MAC 专用路径增加独立的只读解析上下文：显式取得 MMC device 0 的 block descriptor，按已确认 LBA 7168、四份 128-sector 副本规则只读解析，验证 ID=3 的 12-byte 双 MAC，再设置 env 并沿用原 FDT fixup。该路径不得调用 Vendor write，不得随机 fallback，也不得把解析状态写入通用全局缓存。

### 21.7 尚未闭环的精确源码项目

1. 当前实际使用的 Panther X2 SPL 源码/构建提交中，`board_boot_order()` 的实际定义及 MMC loader 顺序；
2. 当前实际使用的 proper 源码分支中，ATAGS 是否启用、是否存在编译期固定 bootdev 覆盖，以及 ATAGS 缺失时的扫描顺序；
3. 当前二进制的准确 `.config` 尚未恢复，候选源码配置不能代替它；
4. 专用 eMMC-only Vendor read-only parser 的代码落点仍是设计项，未编写。

这些是进入补丁设计前最后需要核对的源代码/构建配置边界。当前未编写补丁、未构建、未修改设备。
