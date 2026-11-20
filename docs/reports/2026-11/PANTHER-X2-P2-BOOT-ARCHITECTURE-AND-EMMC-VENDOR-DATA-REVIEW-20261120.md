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

**未闭环：** Vendor Storage 在 eMMC 用户区中的确切 sector/偏移、完整分区/保留区布局、数据副本/版本选择规则，以及 eMMC 设备在各 U-Boot 阶段的可靠枚举编号。后续必须先从现有只读原始证据中确定，不能猜偏移。

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

1. 从已有 eMMC 原始镜像/审计资产中确定 Vendor Storage 的实际物理位置、sector 范围、冗余副本和版本选择逻辑；不得让用户重复已完成读取。
2. 回读现有 U-Boot SPL/BootROM 日志和 eMMC/TF 原始启动区域证据，结合 RK3566 官方文档及可用源码，明确 BootROM 对 eMMC 有效 IDB 与 SDMMC IDB 的选择/回退条件。
3. 审计 Panther X2 板级启动配置、可用启动按键/strap/恢复信号资料，判断是否存在不改 eMMC 的 SD 优先/强制 SD 启动方式。不要将 JTAG 复用脚误当作启动源选择脚。
4. 只有完成 1–3 后，才给出“真正 TF 自包含启动是否可行”的结论和备选方案。

此阶段不研究 BusyBox 具体版本、不下载源码包、不编译、不触发 CI、不写 TF、不写 eMMC、不执行启动实验。

## 8. 证据与来源

- 项目报告：`docs/reports/2026-11/EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md`
- 项目报告：`docs/reports/2026-11/PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
- 项目报告：`docs/reports/2026-11/PANTHER-X2-UBOOT-FIT-FDT-EXTRACTION-ISSUE-20261117.md`
- Rockchip RK3566 Hardware Design Guide V1.1.0 (2022-02-06), §2.1.5 / §2.1.6:
  https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- Rockchip U-Boot reference board.c:
  https://github.com/radxa/u-boot/blob/next-dev-v2026.01/arch/arm/mach-rockchip/board.c
- Rockchip U-Boot reference commit used for vendor/bootdev/FDT source-path audit:
  https://github.com/rockchip-linux/u-boot/tree/8af253525b7de5f29f7f97dffd18adb77db6456
