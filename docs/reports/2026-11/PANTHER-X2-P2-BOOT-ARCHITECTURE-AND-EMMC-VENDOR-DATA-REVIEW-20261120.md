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

## 4. RK3566 BootROM 启动介质顺序：对 TF 自包含启动的关键约束

Rockchip《RK3566 Hardware Design Guide V1.1.0》§2.1.5 明确列出 BootROM 自动启动优先级：

1. Serial NOR Flash（FSPI）
2. Serial NAND Flash（FSPI）
3. NAND Flash
4. eMMC Flash
5. SDMMC Card

同一文档 §2.1.6 说明 `SDMMC0_DET` 是 SDMMC/JTAG 复用功能选择信号：低电平选择 SDMMC，高电平选择 JTAG/UART。该信号不是文档所述的 eMMC/SD 启动优先级切换开关。

项目已有只读证据：
- eMMC 用户区 LBA64 存在有效 Rockchip IDB / idbloader；
- eMMC 用户区 LBA16384 存在对应 U-Boot FIT/proper；
- 现有 UART 启动日志显示旧 SPL/DDR V1.13，随后 `Trying to boot from MMC2`，再进入 TF 上 JP-TvBox U-Boot proper；
- 当前混合链的 BootROM 具体读介质事件尚未通过硬件轨迹直接捕获，但现有日志、eMMC LBA64 内容指纹和 RK3566 官方启动顺序高度吻合。

**重要架构风险：** 只要 eMMC 上仍有 BootROM 可识别的有效 IDB，RK3566 官方文档所列顺序意味着 BootROM 会先检查 eMMC，TF 上的完整 idbloader 很可能不会成为首个执行阶段。故“仅把完整 idbloader + U-Boot proper 写到 TF，就能在保留 eMMC 启动内容的情况下直接从 TF 独立启动”目前没有证据支持，且与已知启动优先级存在冲突。

要实现真正的 TF 自包含完整启动链，至少必须查明是否存在不破坏 eMMC 的硬件启动选择机制/BootROM 条件，能够让 BootROM 越过 eMMC 并选择 SDMMC。不能把 `SDMMC0_DET` 当作该机制。若没有这样的机制，可能需要清除/禁用 eMMC IDB 或修改 eMMC 启动配置；这些做法会触及用户明确保护的 eMMC，当前不允许，也不能默认作为方案。

在查清之前，TF 自包含启动列为**目标要求、可行性未证实**。当前 eMMC SPL → TF proper 仅作为已有临时诊断路径记录，不得悄悄将其定为最终方案。

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

## 7. 下一步唯一审计项

按顺序，只做只读研究：

1. **当前唯一执行项：** 使用已有 eMMC user-area 备份，解析 LBA 7168–7679 的四份 64 KiB Vendor Storage 副本，确认有效副本、最高版本和 LAN_MAC ID 3 descriptor；与此前已读出的脱敏条目交叉核对。不得重新读取实机 eMMC。
2. 回读现有 U-Boot SPL/BootROM 日志和 eMMC/TF 原始启动区域证据，结合 RK3566 官方文档及可用源码，明确 BootROM 对 eMMC 有效 IDB 与 SDMMC IDB 的选择/回退条件。
3. 审计 Panther X2 板级启动配置、可用启动按键/strap/恢复信号资料，判断是否存在不改 eMMC 的 SD 优先/强制 SD 启动方式。不要将 JTAG 复用脚误当作启动源选择脚。
4. 只有完成 1–3 后，才给出“真正 TF 自包含启动是否可行”的结论和备选方案。

此阶段不研究 BusyBox 具体版本、不下载源码包、不编译、不触发 CI、不写 TF、不写 eMMC、不执行启动实验。

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
## 9. RK809 PMIC PWRKEY 软件路径（2026-11-20，补充核对）

### 9.1 Panther X2 板级 DTS 与正常实机证据

- Panther X2 的 6.1.116 正常参考 DTS 和 6.12.81 DTS 均声明 `compatible = "rockchip,rk809"`，并设置 `rockchip,system-power-controller`。
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
- 用户提到的实体“硬件复位按钮”是否就是 PMIC PWRON 输入，或是否另有一颗直接连接 SoC/PMIC reset 的复位按钮，现有软件证据不能区分。不得把 `KEY_POWER` 事件擅自改为 reset/reboot，也不得据此宣称硬件复位线路已经查明。
- 需要原理图、板级电路资料或清晰的板级丝印/按键标识才能闭环实体按钮与 PWRKEY/RESET 的对应关系；在资料缺失前保留现有 PMIC PWRKEY 软件功能及原有硬件复位能力。

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
