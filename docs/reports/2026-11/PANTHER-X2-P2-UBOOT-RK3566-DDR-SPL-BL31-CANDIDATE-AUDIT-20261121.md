# Panther X2 启动固件候选：NixOS 配方源码追溯与 RK3566 DDR/SPL/BL31 版本比较

> 日期：2026-11-21  
> 状态：静态源码与构建配方审计；未构建、未写 TF/eMMC、未操作实机。  
> 目标：完成 P2-1（专用构建配方追溯）及 P2-2（RK3566 DDR/SPL/BL31 候选比较）的第一轮证据收敛。  
> 阶段原则：当前 TF 测试阶段 eMMC 绝对只读；最终正式版本必须安装并从 eMMC 启动，允许设计明确、受控且可恢复的写入。见 [开发阶段与启动介质原则](../../DEVELOPMENT-STAGES-AND-BOOT-MEDIA-POLICY.md)。

## 1. 结论摘要

1. `5aaee9/nixos-aarch64` 的 Panther X2 配方确实提供 `panther-x2-rk3566_defconfig`，但它不是完整的 Panther X2 板级 U-Boot：其目标仍是 `TARGET_EVB_RK3568`，U-Boot control FDT 和默认 FDT 文件均指向 `rk3568-evb1-v10`，未发现 Panther X2 专用 U-Boot control DTS、board C 或 SPL boot-order 补丁。
2. 该配方的 U-Boot 源码基线已经从历史 Radxa `stable-4.19-rock3` 分支迁移到 Nixpkgs 锁定的主线 U-Boot `v2026.10`。因此不能把它简单归类为旧 Radxa U-Boot，也不能将历史和当前两个构建方案混为一谈。
3. 当前配方启用了 `CONFIG_SPL_ROCKCHIP_BACK_TO_BROM=y`，但 U-Boot 文档描述的典型特殊启动序列适用对象为 RK3288/RK3036；主线 RK3566 的 ROCK 3C、Radxa CM3 IO、NanoPi R3S defconfig 均未启用该选项。该选项在 RK3566/Panther X2 上仍属未验证高风险配置，不应直接继承。
4. 当前配方未显式启用 `CONFIG_SPL_PINCTRL=y`。主线 RK3566 的上述板级 defconfig 均显式启用；Rockchip 官方 SPL v1.14 的发布说明也明确修复了 SPL 阶段 SD 初始化失败、pinctrl 节点未在 SPL 启用的问题。Nix 配方自行编译 mainline SPL，并没有使用官方预编译 `rk356x_spl_v1.14.bin`，因此不能认为它自动获得该修复。
5. Rockchip 官方当前 RK3566 loader 配方 `RK3566MINIALL.ini` 已明确采用 **DDR v1.26 + SPL v1.14**。这是一组应纳入后续评估的官方 RK3566 组合，但仍不能仅凭官方通用 profile 认定其适配 Panther X2 的具体 DRAM 颗粒和 PCB。
6. Panther X2 现有 UART 证据已经确认 4GB LPDDR4、`ddrconfig=7`、BW=32、CS0/CS1 双 rank、CS=2、Die BW=16。DDR v1.26 的普通版和 ultra 版都有进一步评估价值；颗粒料号、PCB template、DQ mapping 仍未闭环。
7. BL31 v1.29 是 Nix 配方使用的旧版本。Rockchip 后续 v1.45 发布说明包含 LPDDR4/LPDDR4X multi-CS CA 稳定性修复，对本机双 CS 拓扑尤其值得评估；v1.46 又更新 DMC 状态读取及 RETON 后状态轮询。它们是候选，不代表已证明必须升级或与 DDR v1.26 完成配套认证。
8. 当前不选定唯一探针构建输入。NixOS 配方保留为研究样本，不作为直接构建基线。

## 2. NixOS Panther X2 配方：源码和锁定版本

仓库：<https://github.com/5aaee9/nixos-aarch64>

当前审计的配方仓库 commit：
- `02b7d0d450b906834157132fe58f11acd00e8124`

关键文件：
- [packages/panther-x2-uboot/default.nix](https://github.com/5aaee9/nixos-aarch64/blob/02b7d0d450b906834157132fe58f11acd00e8124/packages/panther-x2-uboot/default.nix)
- [Panther X2 defconfig patch](https://github.com/5aaee9/nixos-aarch64/blob/02b7d0d450b906834157132fe58f11acd00e8124/packages/panther-x2-uboot/316-rockchip-rk3566-Add-support-for-panther-x2.patch)
- [trust.ini patch](https://github.com/5aaee9/nixos-aarch64/blob/02b7d0d450b906834157132fe58f11acd00e8124/packages/panther-x2-uboot/add-trust-ini.patch)

### 2.1 配方演变

历史初始配方使用：
- Radxa U-Boot `stable-4.19-rock3`，源码 commit `c55987146f4f9b20f7cb2f917ca88300419afe8d`；
- Armbian rkbin 历史 commit `ff684f607af661ac0ef5ce59f0533adb2beb6e12`。

2026-10-24 的提交 `1f5dab1043083feabf66e478e0bda4dd50991750` 将构建方式迁移为 Nixpkgs 的 `buildUBoot`。当前 `flake.lock` 锁定 Nixpkgs commit `c85cbe0b7944a65ede3b0f7d2f4b384b6d31614b`；该版本 `pkgs/misc/uboot/default.nix` 的默认 U-Boot 版本为 `v2026.10`。

因此，当前配方实际源码基线是主线 U-Boot v2026.10，而不是历史 Radxa stable-4.19-rock3。今后引用该配方时必须注明具体仓库 commit 和 lockfile，不能只写“NixOS Panther U-Boot”。

### 2.2 当前固件输入

| 部件 | 当前配方输入 | 静态证据 |
|---|---|---|
| U-Boot source | Nixpkgs 锁定的 v2026.10 | lockfile + Nixpkgs buildUBoot 默认版本 |
| DDR/TPL | `rk3566_ddr_1056MHz_v1.10.bin` | Armbian rkbin commit `c5bd0dac0c9030291550aedbb3f3d7d9413ff159` |
| BL31 | `rk3568_bl31_v1.29.elf` | 同一 rkbin commit |
| U-Boot SPL | 由 v2026.10 源码构建 | 配方输出 `spl/u-boot-spl.bin`、`idbloader.img` |
| proper | v2026.10 构建 | 输出 `u-boot.itb` |
| control/default DT | `rk3568-evb1-v10` | defconfig |
| board target | `TARGET_EVB_RK3568` | Panther defconfig patch |

在所锁定 Armbian rkbin commit 中：
- DDR v1.10：Git blob SHA-1 `ff659c50ccf9e1f809c93801672c360863fbd806`，59,392 bytes；
- BL31 v1.29：Git blob SHA-1 `7852fa033f62837816727613896efd85b06b87cc`，402,216 bytes。

以上是 Git blob SHA-1 和仓库记录的文件大小，不是本项目构建产物的 SHA-256。

### 2.3 板级配置并非 Panther X2 完整适配

defconfig 的关键项：
- `CONFIG_TARGET_EVB_RK3568=y`
- `CONFIG_ROCKCHIP_RK3568=y`
- `CONFIG_DEFAULT_DEVICE_TREE="rockchip/rk3568-evb1-v10"`
- `CONFIG_DEFAULT_FDT_FILE="rockchip/rk3568-evb1-v10.dtb"`

当前可见补丁没有增加：
- Panther X2 专用 U-Boot control DTS / SPL DTS；
- Panther X2 专用 board C；
- Panther X2 的 `board_boot_order()`；
- Panther X2 专用 SPL MMC/pinctrl/电源时序处理。

这不代表它一定无法在 Panther X2 运行；它只说明“defconfig 名称含 panther-x2”不能等同于完整板级适配。Linux kernel 包另行提供 Panther X2 DTB，也不能替代 SPL/U-Boot 自身使用的 control FDT。

### 2.4 BACK_TO_BROM 配置风险

当前 Panther X2 defconfig 设置 `CONFIG_SPL_ROCKCHIP_BACK_TO_BROM=y`。

U-Boot v2026.10 的源码行为：
- `spl_boot_device()` 在该选项开启时返回 `BOOT_DEVICE_BOOTROM`；
- Rockchip `board_return_to_bootrom()` 调用 `back_to_bootrom(BROM_BOOT_NEXTSTAGE)`，把控制权交回 BootROM。

这只是源码调用链的静态结论，不证明 RK3566 BootROM 会按项目期望在回交后选择 TF/eMMC 的下一阶段。U-Boot `doc/README.rockchip` 对这一特殊序列的说明明确举例 RK3288 和 RK3036；主线 RK3566 的 ROCK 3C、Radxa CM3 IO、NanoPi R3S defconfig 均没有设置该选项。

判定：**在 Panther X2/RK3566 上未验证，不得把它作为当前探针方案的默认机制。** 需要独立证明 RK3566 BootROM revision 的 NEXTSTAGE 语义、回交后介质选择行为，以及它和当前 eMMC 启动链的关系。

### 2.5 SPL pinctrl 配置风险

NixOS Panther X2 defconfig 没有显式设置 `CONFIG_SPL_PINCTRL=y`。

U-Boot v2026.10：
- `CONFIG_SPL_PINCTRL` 依赖 SPL 与 SPL_DM；
- Rockchip SPL pinctrl 驱动在 `SPL_PINCTRL_GENERIC` 路径下启用；
- `ROCKCHIP_RK3568` 本身没有替代该选项的自动保证。

对照主线 RK3566 defconfig：
- `rock-3c-rk3566_defconfig`：显式启用 `CONFIG_SPL_PINCTRL=y`；
- `radxa-cm3-io-rk3566_defconfig`：显式启用；
- `nanopi-r3s-rk3566_defconfig`：显式启用。

Rockchip rkbin 官方 SPL v1.14 发布说明（2024-05-30）明确记录修复：SPL 阶段 SD 初始化失败，原因是 SPL DTS 中 pinctrl 节点未启用。NixOS 配方不是使用预编译的 `rk356x_spl_v1.14.bin`，而是从 U-Boot v2026.10 自行编译 SPL；不能将官方 v1.14 预编译固件的修复自动算到该配方头上。

判定：**当前 NixOS defconfig 对 TF/SPL pinctrl 支持存在静态配置缺口。** 后续 Panther 专用 defconfig 必须显式审查 SPL pinctrl、SPL DTS bootph 标记和 MMC pin groups。

### 2.6 其他未闭环点

- 配方的 `add-trust-ini.patch` 仅增加 `trust.ini` 文件；当前可见构建流程未显示调用 `trust_merger`，安装输出也未列出 `trust.bin/trust.img`。不能仅凭存在 trust.ini 就声称独立 Trust image 已构建。主线 U-Boot 的 `BL31` 输入可以用于 FIT/ATF 集成，但需以真实构建日志/产物清单确认。
- 当前配方的 `CONFIG_NET_RANDOM_ETHADDR=y` 不是本项目要求的“从 eMMC 权威 Vendor Storage 只读读取 LAN_MAC”实现。最终板级方案仍需单独实现和审计 eMMC Vendor 数据只读读取及 FDT 传递。
- 当前没有该仓库构建成功、产物哈希或 Panther X2 实机启动证据。所有配方输入仍是静态证据。

## 3. RK3566 DDR 候选比较

### 3.1 Panther X2 已有 DRAM 证据

两份已有 UART 日志已记录：
- DRAM：LPDDR4，4GB；
- `ddrconfig=7`；
- `BW=32`、`Col=10`、`Bk=8`；
- `CS0 Row=16`、`CS1 Row=16`、`CS=2`；
- `Die BW=16`。

因此已知是双 CS/rank 的 32-bit LPDDR4 配置；不是“DRAM 拓扑完全未知”。但下列关键资料仍未闭环：
- DRAM 颗粒厂商及完整料号；
- PCB DDR template / layout 对应关系；
- DQ/DQS mapping；
- 板级走线和信号完整性余量。

不能把同容量、同 LPDDR4 类型当作参数完全匹配。

### 3.2 DDR 版本和 profile

| 候选 | Rockchip 配置/发布证据 | 对 Panther X2 的意义 | 当前判断 |
|---|---|---|---|
| RK3566 DDR v1.10 | `RK3566MINIALL.ini` 历史 profile 使用 `rk3566_ddr_1056MHz_v1.10.bin`；Nix 配方也明确使用该文件 | 与现有 JP SPL V1.10/最高 FSP 1056MHz 日志处于同一版本/SoC profile 家族 | 已有一次实机初始化证据，但不能据此认定长期稳定；JP payload 与该仓库文件尚未完成逐字节 hash 对照 |
| RK3568 DDR v1.13 | 历史 E25 启动链 banner V1.13，日志提供 1560MHz FSP | 该 profile 对应 RK3568 1560MHz 频率表；RK3566 官方频率范围不含 1560MHz | 不作为 Panther X2 新构建默认候选；历史能启动不等于适配正确 |
| RK3566 DDR v1.21 | 官方发布 2024-01-20，修复 reboot 时 CA training 可能未执行、结果为零的问题 | 是比 v1.10 更新的 RK3566 多频率 profile | 可作为版本演进对照，不是当前最新候选 |
| RK3566 DDR v1.26 standard | 2026-05-21；Build source commit `1e5d6e92ad`；增加 single-channel LPDDR4/LPDDR4X 支持，修复异常启动概率和较大 tdqs2dq 颗粒报错 | 官方当前 RK3566 MINIALL profile 使用该标准文件；其更新值得在本机颗粒/PCB 对照后评估 | **优先静态评估候选，不等于已选定** |
| RK3566 DDR v1.26 ultra | 2025-05-26；优化 training、CKE/CA timing，修复 ultra wake-up 时 CS1 数据异常、启动概率和大 tdqs2dq 兼容问题 | CS1/双 rank 使相关修复值得关注；但 ultra profile 的使用条件和本板是否需要仍待证 | 保留为专项候选，不默认替代 standard |

官方当前 `RKBOOT/RK3566MINIALL.ini` 明确选择：
- DDR：`rk3566_ddr_1056MHz_v1.26.bin`
- SPL：`rk356x_spl_v1.14.bin`
- 输出：`rk356x_loader_v1.26.114.bin`

这证明 Rockchip 官方提供了 v1.26 + v1.14 的 RK3566 loader 配套方案；不证明该通用 profile 已针对 Panther X2 的颗粒和 PCB 验证。

当前官方 rkbin 文件树中的静态标识：
- `rk3566_ddr_1056MHz_v1.26.bin`：59,240 bytes，Git blob SHA-1 `a019743ffaf5a33c228c07bd7064cce1a9d5429d`；
- `rk3566_ddr_1056MHz_ultra_v1.26.bin`：56,656 bytes，Git blob SHA-1 `d1c4f20ea9fbd377f35e4c6e7ffd28771468c390`。

### 3.3 DDR 结论

- v1.10 是目前有 Panther X2 实机初始化日志的 RK3566 profile，但其 FSP 上限为 1056MHz；不能仅凭成功初始化就认定长期稳定。
- v1.13 的 1560MHz profile 来自 RK3568 方向，不应作为 RK3566 新系统的默认频率目标。
- v1.26 standard 是当前 Rockchip 官方 RK3566 MINIALL profile，具有最强的上游维护和版本依据，值得优先做静态参数/颗粒兼容性核查。
- v1.26 ultra 对 CS1/CA/CKE 有针对性更新，但不能仅凭本机双 rank 就断言 ultra 更合适。
- 不能以最高频率作为选型目标；优先稳定性、匹配的 DRAM 参数和可追溯构建来源。

## 4. SPL 候选比较

### 4.1 Rockchip 官方 SPL v1.14

发布提交：
- rkbin binary commit：`e232d547c10c9d0dab0c23e1ce334ea2958e1d1c`；
- release-note commit：`1961bbd229b1f1698ce1b5ff1df9aaae07922e66`；
- Build from U-Boot commit：`606f72bd97a`；
- 日期：2024-05-30。

官方更新内容包括：
- 修复 SPL 阶段 SD 初始化失败（SPL DTS pinctrl 节点未启用）；
- MMC 默认 sample phase；
- SPL 数据读取 timeout 从 10ms 调整为 50ms；
- DWMCI 内部 phase 支持；
- MMC controller reset 延时；
- tuning error 后发送 STOP command；
- card detect 和相关 MMC 初始化处理。

官方当前 `rk356x_spl_v1.14.bin`：
- 256,718 bytes；
- Git blob SHA-1 `d56528c29e8f926c75689c815328d3c0eeb2eda5`。

注意：这是 Rockchip 发布的预编译 SPL 二进制。NixOS 配方并未使用该文件，而是使用主线 U-Boot v2026.10 自行编译 SPL。两者不能视为同一个 SPL。

### 4.2 SPL v1.13 与 v1.14 的职责边界

既有仓库审计已确认：
- v1.13 修复 SPL 加载/校验第一个 uboot.img 的 u-boot.dtb 失败时，不加载备份镜像的问题；
- v1.14 修复 SPL pinctrl/SD 初始化，并增加 MMC 初始化可靠性改进；
- 两者都没有证据表明改变 BootROM 冷启动介质优先级、SPL successful-loader ATAGS 语义或 proper bootdev 优先级。

因此，v1.14 的价值主要在 SPL 阶段 MMC/pinctrl 可靠性，而不是解决 BootROM 首阶段介质选择。

### 4.3 主线 U-Boot v2026.10 的 RK3566 板级参考

主线已有多个 RK3566 板级 defconfig：
- `rock-3c-rk3566_defconfig`
- `radxa-cm3-io-rk3566_defconfig`
- `nanopi-r3s-rk3566_defconfig`

三者均：
- 使用 `CONFIG_ROCKCHIP_RK3568=y`（主线将 RK3566/RK3568 共用该 SoC 支持项）；
- 显式启用 `CONFIG_SPL_PINCTRL=y`；
- 不启用 `CONFIG_SPL_ROCKCHIP_BACK_TO_BROM=y`；
- 使用各自 RK3566 板级 control DT，而不是 RK3568 EVB DT。

这些板级 defconfig 可作为 SoC/SPL 配置参考，但任何一个都不能直接替代 Panther X2 板级适配。

## 5. BL31 候选比较

NixOS 配方使用 `rk3568_bl31_v1.29.elf`：
- 官方发布日期 2021-09-06；
- Build from ATF commit `81e0b993a`；
- 在其锁定的 Armbian rkbin 中大小 402,216 bytes，Git blob SHA-1 `7852fa033f62837816727613896efd85b06b87cc`。

后续官方版本：
- **v1.45**（2025-03-04，Build commit `70d3deb59`）：新增 DCF DDR ECC poison 支持，并修复 LP4/LP4X multi-CS 系统 CA 不稳定问题。
- **v1.46**（2025-09-20，Build commit `0a207bf3c`）：更新 DMC debug 信息读取（sys_reg_v3），并在请求退出 RETON 后增加状态轮询。
- v1.46 文件：402,376 bytes，Git blob SHA-1 `72c9b03d4682f133cf494cd510b8a8007f3f0b16`。

本机 DRAM 日志为 LPDDR4、CS0/CS1 双 rank，因此 v1.45 的 multi-CS CA 稳定性修复值得优先研究；v1.46 的更新也应纳入候选。但目前没有证据证明：
- v1.29 对本机存在具体故障；
- v1.45/v1.46 与 DDR v1.26 的具体组合已在 Panther X2 验证；
- 只因版本更新就可以不检查 PSCI、PMU、电源域、DDR handoff 和 BL31 运行地址。

判定：BL31 v1.45/v1.46 是后续静态比较候选；不直接选定，也不因旧版本“曾启动”而停止比较。

## 6. 当前候选组合矩阵

| 组合方向 | DDR | SPL | BL31 | U-Boot proper | 当前评价 |
|---|---|---|---|---|---|
| NixOS 现有配方 | RK3566 v1.10 | mainline v2026.10 编译 SPL（非 rkbin v1.14） | v1.29 | mainline v2026.10 | 真实配方证据；但 EVB 板级身份、BACK_TO_BROM、SPL_PINCTRL 缺口使其不能直接作为探针基线 |
| Rockchip 官方 RK3566 loader | RK3566 v1.26 standard | rk356x SPL v1.14 | 需单独配套确认 | 可与主线/厂商 proper 方案组合研究 | 当前官方 RK3566 loader profile；板级适配仍需 Panther X2 control DTS |
| 主线 RK3566 板级参考 | 待定 v1.21/v1.26 | U-Boot v2026.10 SPL | v1.45/v1.46 候选 | U-Boot v2026.10 | 更清晰、可审计的源码路线；需 Panther X2 专用 DTS/defconfig，不能直接复制别的板 |
| 旧 E25-derived 组合 | RK3568 v1.13 / 1560 profile | 旧 SPL v1.13 | 旧 BL31 | Radxa-derived proper | 有历史实机启动证据，但 DDR SoC profile 不适合作为 RK3566 新构建默认输入 |

## 7. 阶段结论

### 已确认 / 静态审计确认
- NixOS 配方当前源码基线为 Nixpkgs 锁定的 U-Boot v2026.10。
- NixOS 配方 DDR v1.10、BL31 v1.29、EVB1 V10 control/default DT、BACK_TO_BROM 配置均已核对。
- NixOS Panther X2 defconfig 没有显式 `CONFIG_SPL_PINCTRL=y`。
- Rockchip 官方 RK3566 MINIALL profile 使用 DDR v1.26 standard + SPL v1.14。
- 官方 v1.14 的 SD/pinctrl 修复、v1.26 DDR 更新、BL31 v1.45/v1.46 更新说明已核对。
- Panther X2 当前已有 DRAM 日志记录 LPDDR4 4GB、BW32、CS0/CS1 双 rank。

### 待验证
- Panther X2 DRAM 颗粒完整料号、PCB template、DQ mapping 与 DDR v1.26 standard/ultra 的匹配。
- DDR v1.26 与 BL31 v1.45/v1.46 的具体 handoff/版本配套。
- Panther X2 专用 U-Boot control DTS 的最终内容及 SPL bootph/pinctrl/MMC 顺序。
- RK3566 BootROM NEXTSTAGE 在 Panther X2 实际 BootROM revision 上的回交后介质选择语义。
- NixOS 配方实际构建是否成功、trust.ini 是否参与产物生成、实际产物的 SHA-256 与启动行为。

### 当前不做
- 不直接使用 NixOS 配方作为探针构建输入；
- 不把 RK3568 v1.13 1560MHz DDR profile 作为 RK3566 默认方案；
- 不盲目启用 BACK_TO_BROM；
- 不构建、不写 TF、不写 eMMC、不进行实机启动；
- 不重跑已有 DDR 初始化或 SPL v1.14 静态审计。

## 8. 下一步唯一研究任务

继续 P2-2，但把工作收敛到 **DDR v1.26 / BL31 v1.45-v1.46 的静态配套与 Panther X2 DRAM 参数匹配**：

1. 追踪官方 DDR v1.26 source commit `1e5d6e92ad` 的可读源码/配置入口，确认 standard 与 ultra 的选择条件及其对 LPDDR4 双 CS、BW32 的适用边界。
2. 查找 v1.26 对应 ddrbin 工具、配置表和可公开的颗粒/PCB template 映射；若没有可读参数资料，明确记录无法证明，不做猜测式反汇编。
3. 对照 BL31 v1.45/v1.46 的 ATF source commit，检查 DDR handoff、DMC/PMU/PSCI 相关接口变化；不以版本号直接推断兼容。
4. 再比较主线 RK3566 control DTS 的 SPL pinctrl/MMC 标记，整理 Panther X2 专用 DTS 必须具备的节点和属性。
5. 完成静态兼容矩阵后，才决定唯一探针构建输入；构建与写卡另行确认。

当前阶段仍然是源码和构建配方研究。当前 TF 测试 eMMC 绝对只读；最终正式产品目标仍是 eMMC 安装、eMMC 启动、eMMC 运行。
