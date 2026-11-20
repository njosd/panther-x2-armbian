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

### 14.4 后续审查顺序

1. 回溯原有 Bootloader 设计和历史已验证路径，建立“原设计应有行为”的基线；不重复已经完成的实机测试。
2. 单独定位 U-Boot 读取“一边读一半”问题，明确读取对象、偏移/长度、执行阶段、调用路径、日志证据和边界条件。
3. 单独闭环 eMMC Vendor 数据读取源、四副本选择、只读约束、双 MAC 映射，以及向 U-Boot 环境/FDT/Linux 的传递路径。
4. 只有当证据表明原设计无法满足某项业务要求时，才提出局部适配或架构变更。
5. 不在根因未明时编写补丁；任何实机写入、刷机、短接或配置变更仍须另行取得用户明确授权。

**本节性质：** 用户确认的架构决策与工作约束；不是对“一边读一半”根因的判定，也不代表相关问题已经修复。
