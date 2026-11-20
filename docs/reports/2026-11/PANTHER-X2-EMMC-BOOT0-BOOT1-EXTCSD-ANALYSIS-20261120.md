# Panther X2 eMMC boot0/boot1 与 EXT_CSD 启动配置分析

- 日期：2026-11-20
- 设备：Panther X2 / RK3566
- 数据来源：用户从当前 Armbian 系统提供的 `sudo mmc extcsd read /dev/mmcblk1` 完整输出；此前已归档的 eMMC user area、boot0、boot1 镜像信息；仓库既有 eMMC 审计报告及 UART 启动链报告
- 操作性质：本阶段仅分析现有读取结果；未执行 eMMC 写入、启动配置修改或重新采集
- 状态：EXT_CSD 已读取；boot0/boot1 全分区内容扫描已完成（两者均全零）

## 1. 本次最重要的结果

EXT_CSD 输出明确显示：

```text
Boot configuration bytes [PARTITION_CONFIG: 0x00]
  Not boot enable
  No access to boot partition
Boot bus Conditions [BOOT_BUS_CONDITIONS: 0x00]
Boot partition size [BOOT_SIZE_MULTI: 0x20]
```

按 JEDEC eMMC EXT_CSD 定义，`PARTITION_CONFIG`（EXT_CSD byte 179）字段划分为：

- bit 6：BOOT_ACK
- bits 5:3：BOOT_PARTITION_ENABLE
- bits 2:0：PARTITION_ACCESS

当前值 `0x00` 表示：

| 字段 | 当前值 | 解释 |
|---|---:|---|
| BOOT_ACK | 0 | 未启用 boot acknowledge |
| BOOT_PARTITION_ENABLE | 0 | 未配置从 boot0 或 boot1 启动 |
| PARTITION_ACCESS | 0 | 当前分区访问选择为 user area |

**证据边界：** 这证明本次读取时 eMMC 的 EXT_CSD 启动分区配置为未启用 boot0/boot1 启动，且分区访问字段选择 user area。它本身不证明 RK3566 BootROM 在上电时具体从哪个 eMMC 地址读取，也不排除 SoC 使用 Rockchip 专有/alternative boot 流程从 user area 读取启动数据。不能仅凭 `PARTITION_CONFIG=0x00` 宣称已经完整证明 BootROM 的物理读取路径。

## 2. 其他启动相关 EXT_CSD 字段

| 字段 | 读数 | 可确认含义 |
|---|---:|---|
| BOOT_INFO | `0x07` | eMMC 声明支持 alternative boot、boot 时 DDR 模式及 high-speed timing |
| BOOT_SIZE_MULT | `0x20` | 每个 boot partition 容量为 0x20 × 128 KiB = 4 MiB |
| BOOT_BUS_CONDITIONS | `0x00` | 当前 boot bus 条件寄存器为 0 |
| BOOT_CONFIG_PROT | `0x00` | 未设置 boot 配置保护位 |
| BOOT_WP_STATUS | `0x00` | 未报告 boot 写保护状态位 |
| BOOT_WP | `0x00` | 未配置 boot area 写保护 |
| RST_N_FUNCTION | `0x01` | eMMC RST_n 功能已启用（EXT_CSD 报告值） |
| SEC_COUNT | `0x03a3e000` | user area 扇区数；按 512 bytes/sector 计算约 31.27 GB |
| RPMB_SIZE_MULT | `0x20` | RPMB 容量为 4 MiB |

BOOT_INFO=0x07 说明器件支持相应能力，不等于当前启动过程实际启用了这些模式。BOOT_BUS_CONDITIONS=0x00 是当前寄存器读数，不足以单独推断 BootROM 实际使用的总线时序。

## 3. eMMC 健康状态字段

本次读取：

- `DEVICE_LIFE_TIME_EST_TYP_A = 0x01`
- `DEVICE_LIFE_TIME_EST_TYP_B = 0x01`
- `PRE_EOL_INFO = 0x01`

按 eMMC 标准编码，A/B 的 0x01 表示估计寿命消耗处于 0–10% 档；PRE_EOL_INFO=0x01 表示正常（尚未进入预警档）。这只是器件自报告的粗粒度寿命估计，不等价于完整健康诊断或对未来寿命的保证。

其他观察：
- CACHE_SIZE：512 KiB
- CARD_TYPE：`0x57`，输出识别出 HS、DDR52、HS200、HS400 等能力
- CACHE_CTRL：`0x01`，cache 当前使能状态字段为 1
- CMDQ_SUPPORT：`0x01`，支持 CMDQ；输出同时提示 CMDQ_MODE_EN 不一定代表运行时状态

这些性能/健康字段不是本轮启动路径判定的核心证据。

## 4. 与既有 eMMC 镜像归档及启动链证据的关系

此前已完成并记录：

- eMMC user area 镜像：31,268,536,320 bytes；SHA-256 `70b8ff396900ea3cd17ad2acefc44e515697e7350a0a63492290ef4cda93251`
- eMMC boot0 镜像：4,194,304 bytes；SHA-256 `bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8`
- eMMC boot1 镜像：4,194,304 bytes；SHA-256 与 boot0 相同
- boot0 与 boot1 镜像此前 `cmp` 结果为相同
- user area LBA 64 处已验证存在与既有 Ophub Panther X2 `idbloader.img` 对应的内容
- user area LBA 16384 处已验证存在与既有 Ophub Panther X2 `u-boot.itb` 对应的内容

这些证据与本次 `PARTITION_CONFIG=0x00` 相互吻合：当前配置没有选择 eMMC boot0/boot1 作为标准 eMMC boot partition 启动目标；而此前已在 user area 标准偏移处发现 Rockchip 启动镜像数据。

**仍需严格区分：**
1. boot0/boot1 镜像相同，不代表它们为空，也不代表它们参与当前启动。
2. user area LBA64/LBA16384 存在已识别的镜像，不单独证明某次上电时 BootROM 一定读取了它们。
3. `PARTITION_CONFIG=0x00` 不单独证明 Rockchip BootROM 的启动介质优先级、alternative boot 流程或实际读取命令序列。
4. EXT_CSD 是本次运行系统读取时的当前状态；若设备上电后固件曾改变易失/非易失配置，需要结合上电前后读取条件进一步确认。本次未做重启前后对比。

既有详细报告：
- `docs/reports/2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md`
- `docs/reports/2026-11/PANTHER-X2-JP-IDBLOADER-BOOT-AND-DHCP-DIFF-20261119.md`
- `docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`

## 5. 当前启动链判断（分证据等级）

### 已验证事实

- Linux 当前设备映射此前确认：`/dev/mmcblk1` 为内部 eMMC；本次 EXT_CSD 命令对该设备读取成功。
- eMMC 的 EXT_CSD `PARTITION_CONFIG=0x00`。
- eMMC boot0、boot1 各 4 MiB，已有镜像 SHA-256 相同。
- eMMC user area LBA64 和 LBA16384 的数据身份此前已与相应 U-Boot 文件交叉匹配。
- 2026-11-19 UART 日志观察到 JP SPL 后续从 U-Boot MMC 设备加载后续 U-Boot proper，并从 TF 卡启动脚本及 Linux。

### 当前最合理的工作假设（尚非完整物理启动证明）

RK3566 BootROM 依据板级启动配置/介质选择逻辑进入 eMMC 相关启动路径，从 eMMC user area 的 Rockchip 启动数据位置加载 SPL；SPL 随后访问 TF 卡（UART 中的 U-Boot MMC 编号显示为 MMC2）加载 U-Boot proper；后续 U-Boot 从 TF 卡加载 `boot.scr`、内核、initrd 和 DTB，最终 Linux 根文件系统也来自 TF 卡。

其中“eMMC user area LBA64 的 SPL 被本次上电实际读取”仍需结合 BootROM 文档/源码、板级启动配置和更直接的启动介质证据确认。U-Boot 的 MMC 编号不能直接等同于 Linux 的 `/dev/mmcblkN` 编号。

## 6. boot0/boot1 下一步静态分析

已知两个 4 MiB 镜像相同，但尚未解析其内部内容。下一步应在 iMac 上对已归档镜像进行只读静态检查，先观察：

- boot0 起始区域是否存在 Rockchip IDB / SPL 特征；
- boot1 是否与 boot0 全文件相同（此前哈希已相同，内容分析可只取一份）；
- user area LBA64（偏移 32768 bytes）是否存在 IDB/SPL 数据特征；
- user area LBA16384（偏移 8388608 bytes）是否存在 U-Boot FIT 数据特征；
- 如需继续，再提取并比较候选镜像内部可读字符串、FDT、FIT 元数据和二进制片段。

首轮只读命令建议：

```bash
cd ~/Desktop/Panther-X2/08-eMMC-Backup-20261120 || exit 1

# 比较四个已归档文件的开头；不写入任何镜像
xxd -g 1 -l 512 eMMC-boot0-20261120.img
xxd -g 1 -s 32768 -l 512 eMMC-user-area-20261120.img
xxd -g 1 -s 8388608 -l 512 eMMC-user-area-20261120.img
```

boot1 与 boot0 已有完整 SHA-256 相同的证据，首轮不必重复 dump boot1。

## 7. 操作约束

- 不对真实 eMMC 执行写入。
- 不执行 `mmc bootpart enable`、`mmc partconf` 的设置形式或任何改变 EXT_CSD 的命令。
- 不修改 boot0、boot1、user area 中的任何字节。
- 不为分析而重新刷写 SPL/U-Boot。
- 优先分析已归档镜像和既有 UART 日志；只有出现明确证据缺口时才安排新的只读采集。
- 所有后续结论继续区分“已验证”“工作假设”“待验证”。


## 8. 已归档镜像首扇区十六进制检查（2026-11-20，用户提供）

用户在 iMac 上对已归档镜像执行只读 `xxd`，本节仅记录实际贴回的输出，不将未读取区域推断为全零。

### 8.1 eMMC boot0 / boot1

- `eMMC-boot0-20261120.img` 起始 512 bytes 全部为 `00`。
- `eMMC-boot1-20261120.img` 起始 512 bytes 全部为 `00`。
- 两份 4 MiB 镜像此前已确认 SHA-256 相同。

**结论边界：** 目前只能确认 boot0 和 boot1 的前 512 bytes 为零，不能据此认定两个 4 MiB 分区整体为空。由于两份镜像哈希相同，后续内容扫描优先只分析 boot0 即可，无须重复分析 boot1。

### 8.2 eMMC user area LBA 64（偏移 32768 bytes）

用户贴回的起始 16 bytes：

```text
52 4b 4e 53 00 00 00 00 80 01 02 00 01 00 00 00
 R  K  N  S
```

`52 4b 4e 53` 是 ASCII `RKNS`，对应 Rockchip New IDB 镜像 magic（`NEWIDB_MAGIC_RKNS = 0x534e4b52`，按小端字节显示为 `RKNS`）。公开 Rockchip 镜像工具代码将其作为 IDB 头 magic；Rockchip 启动镜像说明也记录 raw disk image 中 idbloader 位于 sector 64。

因此，**已直接从用户提供的十六进制输出确认：eMMC user area LBA64 处存在 RKNS IDB 头。** 这与此前对 LBA64 整段数据计算出的 JP idbloader 哈希身份相互印证。

本节不尝试解释头部其余数值字段；不同版本的 IDB 头结构及校验字段应以对应工具源码/格式定义逐项核对，不能凭单个 32-bit 数值猜测。

### 8.3 eMMC user area LBA 16384（偏移 8388608 bytes）

用户贴回的前 4 bytes：

```text
d0 0d fe ed
```

这是 Flattened Device Tree (FDT) 的标准 magic；后续可见字符串 `FIT Image with ATF/OP-TEE/U-Boot`、`images`、`uboot`、`atf-1`，与 U-Boot FIT 容器内容吻合。

因此，**已直接从用户提供的十六进制输出确认：eMMC user area LBA16384 处是 FIT/FDT 格式的 U-Boot 镜像头部。** 这与此前该区域完整镜像哈希匹配 Ophub Panther X2 `u-boot.itb` 的结果相互印证。

### 8.4 本次十六进制检查更新后的介质布局

| 位置 | 本次可见特征 | 当前结论 |
|---|---|---|
| eMMC boot0 offset 0 | 512 bytes 全零 | 仅确认首扇区为零 |
| eMMC boot1 offset 0 | 512 bytes 全零 | 仅确认首扇区为零 |
| eMMC user area LBA64 | `RKNS` | Rockchip IDB header |
| eMMC user area LBA16384 | `d0 0d fe ed` + FIT 描述字符串 | U-Boot FIT header/container |

该布局进一步支持“启动数据放在 eMMC user area 的 Rockchip 标准偏移，而不是 boot0/boot1 起始处”的判断。它与 EXT_CSD `PARTITION_CONFIG=0x00` 一致，但仍不能仅凭静态镜像断言 BootROM 每次上电实际读取了哪一块区域。既有 U-Boot SRAM source 现场读数（来源值 `0x02`，对应 eMMC）是独立的启动来源证据，应与本节镜像结构证据合并判断。

### 8.5 参考格式资料

- Barebox Rockchip IDB 工具头定义及 `NEWIDB_MAGIC`：https://lore.barebox.org/barebox/20211006142254.1751864-1-s.hauer%40pengutronix.de/t/
- Barebox 对 RKNS magic 的说明及支持代码：https://lists.infradead.org/pipermail/barebox/2025-July/051907.html
- Rockchip raw disk image 中 idbloader（sector 64）及 U-Boot FIT（sector 16384）布局说明：https://rock-chip.com/tools/firmware

### 8.6 下一步（不重复首扇区读取）

首轮十六进制检查已完成。下一步应直接做一次针对 boot0 全 4 MiB 的只读内容分布/非零区域扫描，并抽取字符串；不再重复读取 boot1。目标是判断 boot0 是“仅首扇区为零、后部另有数据”还是“整个分区均为零”，并识别是否存在可解析的启动/厂商数据。扫描只针对 iMac 上已归档的镜像文件，不接触实际 eMMC。


## 9. boot0 全分区只读扫描结果（2026-11-20，用户提供）

用户在 iMac 上对已归档的 `eMMC-boot0-20261120.img`（4,194,304 bytes）运行只读 Python 扫描。结果：

```text
文件大小: 4194304 bytes
非零字节: 0
全零: True
非零数据区域: 整个镜像均为零
RKNS / FDT-FIT / U-Boot / Rockchip / DDR / SPL / ATF: 均未发现
长度至少 6 的连续可打印 ASCII 字符串: 未发现
```

### 已验证结论

1. **eMMC boot0 的完整 4 MiB 镜像全部为零字节**，不只是首 512 bytes 为零。
2. 此前已确认 boot1 与 boot0 的完整 4 MiB 镜像逐字节相同（`cmp` 返回相同），且 SHA-256 相同。因此可据此确认 **boot1 的完整 4 MiB 也全部为零**，本轮无需再扫描 boot1。
3. 结合 EXT_CSD `PARTITION_CONFIG=0x00`（BOOT_PARTITION_ENABLE=0），当前 eMMC boot0/boot1 既未被配置为标准 boot partition 启动目标，且两者内容均为空白。
4. eMMC user area LBA64 存在 RKNS IDB 头，LBA16384 存在 FIT/U-Boot 容器头；此前两段完整数据分别与 Ophub Panther X2 的 `idbloader.img`、`u-boot.itb` 完整哈希匹配。

### 对启动链的影响

现有证据强烈支持：本机 eMMC 启动代码存放在 **user area**，而不是 eMMC boot0/boot1：

- boot0：全 4 MiB 为零；
- boot1：全 4 MiB 为零；
- user area LBA64：Rockchip IDB / idbloader；
- user area LBA16384：U-Boot FIT / u-boot.itb；
- EXT_CSD：未选择 boot0/boot1 启动；
- 既有 U-Boot SRAM boot-source 只读记录为 `0x02`（此前报告解读为 eMMC）。

**证据边界：** 这已经排除了“当前 boot0/boot1 内有启动镜像”的可能，也使 user area 路径成为明确且高度吻合的解释；但静态镜像和 EXT_CSD 仍不是 BootROM 读取总线轨迹。实际从 user area 的何处、以何种命令和顺序加载 IDB，仍应依据 RK3566 BootROM 资料/源码和现有启动日志完成最后的机制核验。

### 本阶段状态

- [x] 读取 EXT_CSD，确认 PARTITION_CONFIG。
- [x] 确认 boot0/boot1 镜像大小、哈希和逐字节相同。
- [x] 对 boot0/boot1 起始扇区做十六进制检查。
- [x] 对 user area LBA64、LBA16384 做十六进制检查，识别 RKNS 与 FIT。
- [x] 扫描 boot0 全 4 MiB，确认全零；由 boot0/boot1 完整逐字节相同，确认 boot1 全零。
- [ ] 结合 RK3566 BootROM 启动介质机制和已有 SRAM/UART 证据，核实 BootROM 从 eMMC user area 读取 IDB 的具体规则。

本阶段没有访问实际 eMMC 进行新的读取，没有写入或修改任何分区，也没有重新生成备份或哈希清单。


## 10. RK3566 BootROM 启动介质与 eMMC IDB 定位机制（2026-11-20，离线证据 + 公开资料核对）

本节将 11 月 18 日现场 SRAM 读数、11 月 19 日 eMMC idbloader 替换及实机 UART、11 月 20 日完整 eMMC 备份，与 RK3566 文档和 Rockchip 存储实现交叉核对。没有进行新的设备读取或启动试验。

### 10.1 BootROM 启动介质：现场证据已经存在

2026-11-18 U-Boot proper 暂停现场执行过一次只读命令：

```text
=> md.l 0xfdcc0010 4
fdcc0010: 00000002 00000040 c08dfd97 5ef93ffc
```

原始命令和输出已保存在：
`docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md` 第 16 节。

Rockchip U-Boot 源码定义：
- `BROM_BOOTSOURCE_ID_ADDR = CONFIG_ROCKCHIP_IRAM_START_ADDR + 0x10`；
- eMMC source ID = 2，SD = 5，SPI NOR = 3，SPI NAND = 4；
- SPL 的 `board_spl_was_booted_from()` 从该 SRAM 地址读取来源字段。

本机该次运行时地址为 `0xFDCC0010`，读数第一个 word 为 `0x00000002`。**这是本机 U-Boot proper 阶段的实际 SRAM 只读读数，不是仅从源码枚举值推断。** 该读数指向 BootROM 启动来源 eMMC。BL31 执行之后仍读到该值，亦已在第 16.3 节记录。

### 10.2 RK3566 BootROM 启动顺序

Rockchip《RK3566 Hardware Design Guide V1.1.0》§2.1.5 给出的顺序为：
1. SPI NOR
2. SPI NAND
3. NAND
4. eMMC
5. SDMMC

PINE64 Quartz64（同为 RK3566）启动文档也列出 SPI NOR、SPI NAND、eMMC、microSD 的顺序，并说明 BootROM 在支持介质上搜索有效 ID BLOCK。该资料属于板卡社区文档，不是 Rockchip 官方 BootROM 源码；此处用作与官方硬件指南及 Panther 实测相互印证，不把它提升为 ROM 源码级证明。

### 10.3 eMMC 的 IDB 位于 user area LBA64，而非 boot0/boot1

现有 Panther X2 实测：
- EXT_CSD `PARTITION_CONFIG=0x00`：BOOT_PARTITION_ENABLE=0，PARTITION_ACCESS=0（user area）。
- boot0 完整 4 MiB 全零；boot1 与 boot0 完整逐字节相同，因此 boot1 完整 4 MiB 也全零。
- eMMC user area LBA64（byte offset 32768）有 `RKNS` IDB header。
- eMMC user area LBA64 对应的完整数据已与 JP-TvBox `idbloader.img` SHA-256 匹配。
- eMMC user area LBA16384 有 FIT/FDT header，完整数据此前与 U-Boot FIT 镜像匹配。

外部交叉证据：
- PINE64 Quartz64 RK3566 文档给出的 eMMC 安装方式为 `dd if=idblock.bin ... seek=64`，即 user-area sector 64。
- Rockchip Linux `sdmmc_vendor_storage.c` 定义 `EMMC_IDB_PART_OFFSET 64`、`EMMC_BOOT_PART_SIZE 1024`；其 IDB 更新路径以 64 为基址，并按 1024-sector 间隔处理最多五份 IDB 副本。这是 Rockchip BSP 存储布局实现证据，不等同于直接看到 BootROM 内部代码。
- PINE64 对 Rockchip BROM 的存储协议说明指出，eMMC/SD BootROM 通过常规 MMC 初始化访问介质，并且不使用标准 eMMC boot partition 启动选项；这与本机 boot0/boot1 全零、EXT_CSD 未启用 boot partition、user area LBA64 存在 IDB 的组合证据一致。该细节属于社区逆向文档，证据等级低于官方芯片指南。

因此，当前可以作出高置信度判断：**Panther X2 的 RK3566 BootROM 从 eMMC 启动时，使用的是 eMMC user area 中的 Rockchip IDB（本机已确认位于 LBA64），而不是 eMMC boot0/boot1。**

### 10.4 11 月 18 日至 11 月 20 日启动链时间线

| 时间 | 介质状态 / 实测 | 可得结论 |
|---|---|---|
| 11 月 18 日 | U-Boot proper 现场读取 SRAM `0xFDCC0010=0x02`；当时 eMMC LBA64 为旧 E25 idbloader | 该次启动的 BootROM 来源记录指向 eMMC |
| 11 月 19 日写入前 | 确认目标为 eMMC user area；将 JP-TvBox idbloader 写入 LBA64–667，回读与源文件逐字节一致 | eMMC user area 的 IDB 被替换为 JP SPL/DDR V1.10 |
| 11 月 19 日启动 | UART 显示 JP SPL 2023-11-12、DDR V1.10；SPL 输出 `Trying to boot from MMC2`；随后运行 JP U-Boot proper | 已验证 JP SPL 实际执行，并从 MMC2/TF 加载下一阶段 |
| 11 月 20 日备份 | eMMC user area LBA64 的 RKNS 头及完整数据身份与 JP idbloader 匹配；boot0/boot1 全零 | 当前归档状态与 11 月 19 日 eMMC 替换记录一致 |

注意：11 月 18 日 SRAM 来源值是那次启动的直接现场读数；现有记录没有显示 11 月 19 日启动时再次读取该 SRAM 字段。11 月 19 日的“BootROM 读取已替换后的 eMMC LBA64 并运行 JP SPL”由写入回读、后续 SPL 构建指纹及启动时间线强烈支持，但不应伪称 11 月 19 日又做过一次 SRAM 读数。

### 10.5 SPL → U-Boot proper：MMC 编号体系已闭环

11 月 19 日 SPL 输出 `Trying to boot from MMC2`。既有 Rockchip SPL/ATAGS 源码映射及 proper 实机日志表明：
- SPL 的 MMC2 对应 SD/TF；
- U-Boot proper 将 SD/TF 枚举为 `mmc 1`；
- proper 的 `Bootdev(atags): mmc 1`，并扫描 `mmc 1:1` 找到 TF 上的 `/boot.scr`；
- 后续内核、initrd、Panther X2 DTB 和 Linux rootfs 均来自 TF。

所以本次混合链为：

```text
RK3566 BootROM
  └─ eMMC user area LBA64：JP idbloader / SPL + DDR V1.10
       └─ SPL 从 MMC2（SD/TF）加载
            └─ TF 上 JP U-Boot proper（FIT 位于 TF LBA16384）
                 └─ TF /boot.scr、kernel、initrd、Panther X2 DTB
                      └─ TF Linux rootfs
```

eMMC user area LBA16384 的 FIT 是已确认存在的镜像，但在这条已观察到的启动链中，SPL 后续加载设备为 TF；因此不能把 eMMC LBA16384 的 FIT 误标为本次实际执行的 U-Boot proper。

### 10.6 证据等级与剩余边界

**已验证：**
- 11 月 18 日 U-Boot proper 对 `0xFDCC0010` 的实机只读结果为 `0x00000002`，对应 eMMC BootROM source ID。
- RK3566 官方硬件指南将 eMMC 排在 SDMMC 之前。
- Panther X2 eMMC boot0/boot1 完整镜像均全零。
- Panther X2 eMMC user area LBA64 有 RKNS IDB，且完整数据与 JP idbloader 匹配。
- 11 月 19 日实际运行 JP SPL/DDR V1.10，并由其从 TF/SD 加载下一阶段。

**高置信度综合判断：**
- BootROM 从 eMMC user area LBA64 加载 IDB；11 月 19 日替换后，实际执行的是 JP idbloader。
- eMMC boot0/boot1 不承载本机当前这条启动链的 SPL。

**仍未直接观测：**
- 没有 BootROM 总线级 CMD/数据轨迹，也没有 BootROM 内部反汇编，因此不能把具体 MMC 命令序列、重试次数、IDB 副本扫描策略全部写成 Panther X2 实机已测事实。
- 11 月 19 日没有第二次 SRAM source-tag 现场读取；该次 eMMC 来源判断依靠 11 月 18 日实测、11 月 19 日介质替换及启动日志的时间关联。
- Rockchip BROM 在 eMMC LBA64 之外是否以及如何扫描冗余 IDB 副本，尚未针对 RK3566 BootROM 本体完成源码级验证。

### 10.7 参考资料

- Rockchip《RK3566 Hardware Design Guide V1.1.0》§2.1.5（BootROM 介质优先级）：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- PINE64 Quartz64 RK3566 BootROM 顺序及 LBA64 安装说明：https://pine64.org/documentation/Quartz64/_full/
- PINE64 Rockchip BROM eMMC/SD、ID block 搜索与启动阶段说明（社区逆向资料，非 RK3566 官方 ROM 源码）：https://pine64.org/documentation/General/_full/
- Rockchip Linux `sdmmc_vendor_storage.c`（IDB sector 64 基址及 1024-sector 副本布局）：https://github.com/rockchip-linux/kernel/blob/develop-6.1/drivers/soc/rockchip/sdmmc_vendor_storage.c
- 本仓库 11 月 18 日现场 SRAM 读数及启动链报告：`docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
- 本仓库 11 月 19 日 JP idbloader 实机启动报告：`docs/reports/2026-11/PANTHER-X2-JP-IDBLOADER-BOOT-AND-DHCP-DIFF-20261119.md`

本节全部分析基于既有镜像、日志和源码/文档；没有对设备执行新的命令，没有改动 eMMC、TF、EXT_CSD 或启动配置。
