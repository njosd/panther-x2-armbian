# Panther X2 eMMC boot0/boot1 与 EXT_CSD 启动配置分析

- 日期：2026-11-20
- 设备：Panther X2 / RK3566
- 数据来源：用户从当前 Armbian 系统提供的 `sudo mmc extcsd read /dev/mmcblk1` 完整输出；此前已归档的 eMMC user area、boot0、boot1 镜像信息；仓库既有 eMMC 审计报告及 UART 启动链报告
- 操作性质：本阶段仅分析现有读取结果；未执行 eMMC 写入、启动配置修改或重新采集
- 状态：EXT_CSD 已读取；boot0/boot1 镜像内容尚待静态解析

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
