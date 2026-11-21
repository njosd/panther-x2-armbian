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


## 9. RK3566 DDR v1.26 专用变体与 PCB Template 约束复核（2026-11-21）

本轮只补充启动前 DDR 初始化固件的选型证据，不涉及网络、GMAC 或系统用户空间。

### 9.1 官方 DDR v1.26 并非只有 standard / ultra 两个通用候选

重新核对 Rockchip rkbin 当前公开文档后，发现 RK3566 还有一组 2026-06 发布的专用混合模式固件：

- DDR：`rk3566_ddr_1056MHz_lp4_4x_specific_mixed_mode_v1.26.bin`，Build commit `a7079cfc6e`；
- BL31：`rk3568_bl31_lp4_4x_specific_mixed_mode_v1.46.elf`，Build commit `b80232164`。

官方说明明确限定：该 DDR BIN 仅适用于两个 CS 需要不同 Latency Mode 配置的特定 LPDDR4/LPDDR4X 混合封装；对应 BL31 也仅为这类混合封装的 DDR frequency scaling 配套版本，必须成对使用。

来源：
- https://github.com/rockchip-linux/rkbin/blob/master/specific/rk3566/RK3566_CN.md
- https://github.com/rockchip-linux/rkbin/blob/master/specific/rk3566/RK3566_EN.md

**重要纠正：** Panther X2 已知 CS0/CS1 双 rank，只能证明有两个片选，不能证明 CS0 与 CS1 使用不同 Latency Mode，更不能证明是官方所说的特定混合封装。故不能因为本机 CS=2 就选择 specific_mixed_mode DDR/BL31；在取得 DRAM 颗粒完整料号、封装信息及对应 vendor/application note 前，该组合只能列为条件性候选，禁止作为默认输入。

### 9.2 官方 RK3566 PCB Template 表进一步限制了可选范围

Rockchip 当前公开的《Rockchip Specific PCB Template and DDR bin Configuration Table》为 RK3566 列出若干 LPDDR4/LPDDR4X PCB template，例如：

- LP4XD200P132SD4_29x43_1333MHz
- LP4XD200P132SD6_39x25_1066MHz
- LP4XD200P132SS8_35x20_1066MHz
- LP4XD200P232DD61346_43R0x28R0_1848Mbps_2112Mbps
- LP4XD320P164SD6H1_41x24_1066MHz
- LP4D342P164SD6H1_44x32_533MHz
- LP4D366P164SD6H1_44R6x27R4_800MHz
- LP4M254P132SS6H1_34x19_800MHz

该表说明 DDR BIN 与 PCB template / DRAM 颗粒组合有关；需要 WDQS 的特定颗粒还必须使用表中指定的 WDQS BIN。该表没有给出 Panther X2 / BROWAN H1GW V04 对应关系。

来源：
- https://github.com/rockchip-linux/rkbin/blob/master/specific/Rockchip_Specific_PCB_Template_and_DDR_bin_Configuration_Table.md

目前本项目只有 LPDDR4、4GB、BW32、CS0/CS1 双 rank 等 UART 运行信息，没有 DRAM 厂商/完整料号、颗粒封装、PCB template、DQ mapping 的证据。因此尚不能从上述列表中选出任何一个模板，也不能据模板名称中的容量/宽度猜测本板布局。

### 9.3 standard / ultra / specific mixed-mode 的当前判定

| 候选 | 官方用途/变更 | 本机证据是否满足选型条件 | 当前状态 |
|---|---|---|---|
| DDR v1.26 standard | 通用 RK3566 v1.26；新增单通道 LPDDR4/4X 支持，修复启动概率和较大 tdqs2dq 兼容 | 本机不是单通道；颗粒/PCB 匹配未证实 | 保留通用候选，未选定 |
| DDR v1.26 ultra | 优化 training、CKE/CA timing；修复 ultra wake-up CS1 数据异常、启动概率及大 tdqs2dq 兼容 | 已知双 CS，但没有 ultra wake-up 使用条件或板级匹配证据 | 条件性候选，未选定 |
| DDR v1.26 specific mixed-mode | 仅适用于 CS0/CS1 需要不同 Latency Mode 的特定混合封装 | 没有不同 Latency Mode 或混合封装证据 | 不纳入默认候选；需料号证据才重新评估 |
| DDR v1.10 | Panther X2 既有 JP 启动日志中有初始化成功记录 | 既有实际启动证据，但长期稳定性未证明 | 现有基线/回退参照，不自动作为新方案 |

### 9.4 BL31 v1.45 / v1.46 的配套关系需要按 DDR 类型区分

- 普通 RK3566 DDR v1.26 与 BL31 v1.45/v1.46：公开 release note 分别说明其更新内容，但目前没有找到足以证明这两个普通 BL31 版本与本机 DDR v1.26 profile 完成 Panther X2 专项认证的资料；仍需检查源码/接口及官方 loader profile 的实际组合。
- specific mixed-mode DDR v1.26：必须与对应的 specific mixed-mode BL31 v1.46 配套，不能替换为普通 BL31 v1.45/v1.46。
- 不同 DDR bin / BL31 组合不可只按版本号拼装；必须确认 DDR frequency scaling、DMC/PMU handoff 与配套关系。

### 9.5 下一步收敛为一个可验证问题

当前最优先的阻塞项不是再比较更多版本号，而是取得 Panther X2 实际 LPDDR4 颗粒的完整标识并映射到 Rockchip approved/reference vendor list 与 PCB template：

1. 追溯已有拆机照片/板上丝印和历史 BOM 资料，确认 LPDDR4 颗粒的完整厂商料号、封装及是否多颗/混合封装；不得把 SoC 或 SanDisk eMMC 丝印误认成 DRAM。
2. 用完整料号查 Rockchip DDR Approved/Reference Vendor List 中的 application note，确认是否需要 WDQS、是否有特殊 Latency Mode、是否属于 specific mixed-mode。
3. 只有料号与 PCB template 映射成立后，才能在 standard / ultra / specific mixed-mode 中缩小到正确 DDR BIN，再审查与 BL31 的成对关系。
4. 若公开资料无法取得料号或模板映射，结论应保持“无法证明匹配”，而不是按 4GB / LPDDR4 / 双 CS 猜选 v1.26。

本轮未下载或运行 DDR 工具、未反汇编二进制、未构建固件、未操作设备、未写 TF/eMMC。


## 10. 官方 rkbin 原始文件复核：mixed-mode 限定条件与通用 loader 输入（2026-11-21）

本节依据本轮直接读取的 Rockchip rkbin 当前原始文件，补充 §9 的证据出处；仅限启动固件。

### 10.1 RK3566 专用 DDR/BL31 文档原文确认

文件：`specific/rk3566/RK3566_EN.md`

当前文档列出：
- `rk3566_ddr_1056MHz_lp4_4x_specific_mixed_mode_v1.26.bin`，build commit `a7079cfc6e`，日期 2026-06-15；
- `rk3568_bl31_lp4_4x_specific_mixed_mode_v1.46.elf`，build commit `b80232164`，日期 2026-06-13。

文档的限制语义明确：
- DDR BIN 仅适用于两个 CS 使用不同 Latency Mode 的特定 LPDDR4/LPDDR4X mixed-package；
- 对应 BL31 仅适用于该特定 mixed-package 的 DDR frequency scaling，且必须与对应 DDR BIN 配套。

因此 §9 的选型边界得到原始官方文件直接支持。双 CS/rank 数量不等于 mixed-package，也不等于两个 CS 的 Latency Mode 不同；当前 Panther X2 证据不满足该专用变体的选型前提。

原始文件：https://github.com/rockchip-linux/rkbin/blob/master/specific/rk3566/RK3566_EN.md

### 10.2 RK3566 通用官方 loader 配方直接确认

文件：`RKBOOT/RK3566MINIALL.ini`

原始配置明确：
- `Path1=bin/rk35/rk3566_ddr_1056MHz_v1.26.bin`
- `FlashData=bin/rk35/rk3566_ddr_1056MHz_v1.26.bin`
- `FlashBoot=bin/rk35/rk356x_spl_v1.14.bin`
- 输出 loader 名称：`rk356x_loader_v1.26.114.bin`

这直接证明 Rockchip 当前通用 RK3566 MINIALL loader profile 的 DDR/SPL 输入组合是 DDR v1.26 standard + SPL v1.14。该 ini 没有在上述条目中列出 Panther X2 专用 DRAM 参数，也没有证明该 profile 已针对 H1GW V04 的颗粒/PCB 认证。

原始文件：https://github.com/rockchip-linux/rkbin/blob/master/RKBOOT/RK3566MINIALL.ini

### 10.3 PCB template 表的解释边界

文件：`specific/Rockchip_Specific_PCB_Template_and_DDR_bin_Configuration_Table.md`

RK3566 LPDDR4/LPDDR4X 项列出若干 Rockchip PCB template，并说明只有使用需要 WDQS 功能的特定颗粒时，才使用该表指定的 WDQS DDR BIN。文档将 WDQS 需求与 Rockchip Approved/Reference Vendor List 中特定 Application Note 编号关联。

这意味着不能仅因板上是 LPDDR4 就选 WDQS 版本，也不能仅因 DTS/DDR 日志显示双 CS 就选 specific mixed-mode 版本。必须先确定 DRAM 颗粒 P/N，再查 Approved/Reference Vendor List 的 Application Note 与 PCB template 对应关系。

原始文件：https://github.com/rockchip-linux/rkbin/blob/master/specific/Rockchip_Specific_PCB_Template_and_DDR_bin_Configuration_Table.md

### 10.4 本轮静态核验的最终状态

| 启动资产 | 官方当前参考 | Panther X2 匹配状态 |
|---|---|---|
| DDR | RK3566 MINIALL 使用 v1.26 standard | SoC/profile 方向吻合；颗粒和 PCB template 未闭环 |
| SPL | RK3566 MINIALL 使用 v1.14 | 官方 RK3566 参考；Panther X2 专用 SPL DTS/pinctrl/bootph 仍需核验 |
| BL31 | mixed-mode 有专用 v1.46，且限定特定混合封装 | 本机是否属于该封装未知；不能选用该专用 BL31 |
| U-Boot proper | 另由 U-Boot 源码、control DTS、FIT/ATF 配置构建 | Panther X2 专用 control DTS 和板级配置仍未完成 |
| DRAM PCB template | 官方列出若干 RK3566 LPDDR4/4X 模板 | 没有证据将 H1GW V04 映射到其中任一模板 |

**当前可成立的结论只有：** DDR v1.26 standard + SPL v1.14 是 Rockchip 当前通用 RK3566 loader 的官方参考组合；不能据此宣布它就是 Panther X2 的最终正确组合。DDR v1.26 specific mixed-mode + BL31 v1.46 是有严格颗粒条件的专用组合，当前没有证据证明 Panther X2 满足条件。

本轮只读取 GitHub 上游文档/ini；未下载二进制、未构建、未写 TF/eMMC、未操作实机。


## 11. Panther X2 实物 LPDDR4 颗粒丝印解码：Micron D9WMH（2026-11-21）

用户提供的 PCB 近照中，DRAM 封装可读丝印为 `MT 7VD77` 与 `D9WMH`。本轮以 Micron 官方产品目录交叉核验，确认 D9WMH 是 Micron FBGA code。

### 11.1 官方型号匹配

Micron 官方 LPDRAM 产品目录将 FBGA code `D9WMH` 唯一对应到：

`MT53D1024M32D4DT-046 AAT:D`

官方产品页数据：
- Technology：LPDDR4
- Density：32Gb
- Width：x32
- Data rate：DDR4-4166（Micron 产品页标注）
- FBGA code：D9WMH
- Orderable part：MT53D1024M32D4DT-046 AAT:D

Micron 官方产品页：https://www.micron.com/products/dram/lpdram/part-catalog/mt53d1024m32d4dt-046-aat

Micron 官方产品目录镜像/产品信息同时列出 LPDDR4 200-ball、1.1V/0.6V、32Gb x32、2133MHz（数据率 4266MT/s）等规格；Micron AUT:D 同系列官方详细页列出 1Gb x32 component configuration、200-ball、10.00 x 14.50 x 0.95 mm、Number of Components=4。后者为同基础型号的 AUT 温度等级页面，不能将其后缀/温度等级直接当作实物 AAT:D 的完整订货后缀，但基础颗粒型号一致。

### 11.2 容量与组织结构

- 单颗容量：32Gb = 4GiB（标称字节容量为 4GB，系统常见显示约 3.7GiB）。
- 组织：1Gb × 32。
- 数据总线：x32，与 RK3566 32-bit DRAM 总线宽度相符。
- 封装系列：200-ball VFBGA/WFBGA，封装尺寸约 10.0 × 14.5 mm（以该型号官方详细资料为准）。

该型号中的 `D4` / 4-die stack 信息不能直接等同于 SoC 侧 CS0/CS1 rank 数；封装内部 die 数、LPDDR4 channel、SoC chip-select/rank 是不同层次的概念。当前仍需以实机 DDR training/UART 输出、原理图和控制器配置交叉确认 CS/rank 映射，不能仅凭 D4 推断双 rank 或 specific mixed-mode。

### 11.3 对 DDR BIN 选择的影响

这次识别解决了此前最重要的缺口之一：实物 DRAM 不再只是“4GB LPDDR4”，而是精确到 Micron `MT53D1024M32D4DT-046 AAT:D`。

但仍不能直接从型号跳到 DDR BIN：
1. 必须把完整料号 `MT53D1024M32D4DT-046 AAT:D` 与 Rockchip DDR Approved/Reference Vendor List、对应 Application Note 和 PCB template 交叉映射。
2. 核对该颗粒是否要求 WDQS 或特殊训练参数。
3. 核对本板实际布线、DQ mapping、CS/CKE/CA 连接与该 application note/template 一致。
4. 只有上述匹配成立，才能决定 standard/ultra/专用 BIN；D9WMH 本身不能证明 specific mixed-mode 条件成立。

### 11.4 丝印中尚未解码部分

`D9WMH` 已由 Micron 官方产品目录确认是 FBGA code。封装上的另一行 `MT 7VD77` 尚未从当前可访问的 Micron 官方资料中可靠解码；本报告不把它臆断为完整料号、批次日期或 wafer lot。

### 11.5 证据状态

- 已验证：实物照片可读 D9WMH；Micron 官方目录将 D9WMH 映射到 MT53D1024M32D4DT-046 AAT:D；LPDDR4、32Gb、x32。
- 有官方同基础型号资料支持：1Gb ×32 组织、200-ball、封装外形信息。
- 未验证：实物完整订货后缀是否与照片中所有 lot/assembly 标记完全一致；MT 7VD77 的含义；本板 PCB template / DQ mapping；该颗粒在本板上实际 CS/rank 映射；最终 DDR BIN 兼容性。

本轮仅分析用户提供的芯片照片并查询 Micron 官方产品资料；未操作硬件、未构建、未写 TF/eMMC。


## 12. Micron D9WMH 与 Rockchip DDR Support List 的精确匹配审查（2026-11-21）

在确认 D9WMH → `MT53D1024M32D4DT-046 AAT:D` 后，进一步检查 Rockchip DDR Support List Ver2.61（2024-06-05）和 Ver2.54（2022-08-18）的公开可检索表项，避免把同基础型号、不同 Micron FBGA code 的条目误判为同一颗粒已获 Rockchip 验证。

### 12.1 必须区分两个不同 FBGA code

Micron 官方目录明确：
- `MT53D1024M32D4DT-046 AAT:D` → FBGA `D9WMH`；
- 同一基础料号的 `MT53D1024M32D4DT-046 WT:D` → FBGA `D9WQG`。

两者温度/订货变体不同，FBGA code 也不同，不能互相替代作为颗粒标识。

Micron 官方 AAT 页面：https://www.micron.com/products/dram/lpdram/part-catalog/mt53d1024m32d4dt-046-aat
Micron 官方 WT 页面：https://www.micron.com/products/dram/lpdram/part-catalog/mt53d1024m32d4dt-046-wt

### 12.2 Rockchip Support List 中找到的是 D9WQG，不是 D9WMH

Ver2.61 公开表中有：
`MT53D1024M32D4DT-046 WT:D (D9WQG)`
其组织为 1024M×32、32Gbit、LPDDR4/LPDDR4X、200-ball。表格列中对 RK3566 对应项有 T/A 标记及脚注 [11]。

Ver2.54 也列出同一 WT:D / D9WQG 变体。

**目前检索到的这两版 Rockchip Support List 没有列出 AAT:D / D9WMH。** 因此只能说 Rockchip 列表包含同基础料号的 WT:D / D9WQG 变体，不能说本机 AAT:D / D9WMH 已被 Rockchip Support List 明确认证。AAT 与 WT 可能是温度/测试等级变体，但是否电气等价、Rockchip 是否允许按同基础 die 复用该条目，需要 Micron datasheet 与 Rockchip 脚注 [11] / Application Note 支持；当前未证明。

公开资料：
- Rockchip DDR Support List Ver2.61：https://lo01.g77k.com/aeb/docs/en/Common/AVL/Rockchip_Support_List_DDR_Ver2.61.pdf
- Rockchip DDR Support List Ver2.54：https://files.kos.org.cn/rockchip/Rockchip_Support_List_DDR_Ver2_54_20220181.pdf

### 12.3 对 DDR BIN 决策的更新

- 已确认实物 D9WMH 属于 Micron `MT53D1024M32D4DT-046 AAT:D`，32Gb、x32、LPDDR4、200-ball。
- 找到 Rockchip Support List 中相同基础料号的 WT:D / D9WQG 对 RK3566 支持条目。
- 尚未找到 Rockchip 对 AAT:D / D9WMH 这一精确 FBGA 变体的明确列项。
- 因此 DDR v1.26 standard 仍可作为通用参考候选，但“该 BIN 对本机颗粒/PCB 已被 Rockchip 认证”不能成立。
- 在获取 Micron AAT:D 与 WT:D 的完整 datasheet/温度等级等价说明，以及 Rockchip 脚注 [11] 的定义和对应 Application Note 前，不把 WT:D 的 T/A 结果直接外推到 AAT:D。
- 不据此选择 WDQS、ultra 或 specific mixed-mode BIN；这些仍需各自的颗粒和板级条件证据。

### 12.4 当前最小待查项

1. 获取 Micron `MT53D1024M32D4DT-046` 完整 datasheet，核对 AAT:D 与 WT:D 的电气参数、温度等级、封装/ball map 是否完全一致。
2. 查清 Rockchip Ver2.61 脚注 [11] 与对应 Application Note，确认该支持标记的限制条件。
3. 若无法证明 AAT:D 可按 WT:D 支持条目处理，则维持“精确变体未获列表确认”，通过实机 DDR training 与稳定性验证来判定候选，而非宣称已认证。

本轮仅静态检索资料；未运行 DDR 工具、未构建、未操作实机。
