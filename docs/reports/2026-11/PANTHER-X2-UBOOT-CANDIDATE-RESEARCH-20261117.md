# Panther X2 U-Boot 候选来源初步调查（2026-11-17）

> 状态：只读公开资料与仓库元数据调查；没有下载/刷写候选固件，没有修改设备。
> 目标：为 Panther X2 / RK3566 寻找比当前 E23/E25 衍生 U-Boot 更有依据的候选启动固件。

## 1. 已知当前基线

当前 TF 卡使用的 idbloader.img / u-boot.itb 与旧 6.1.116 系统保存的文件逐字节相同，并与 Ophub U-Boot 仓库 6e70f41585f15c43f45fcae609adec1865e83eb5 的 u-boot/rockchip/panther-x2/ 文件相同。

| 文件 | 当前 Panther X2 文件大小 | Git blob SHA-1 |
|---|---:|---|
| idbloader.img | 305,152 | d22b624fc90c46e656baf98894bee182316e692e |
| u-boot.itb | 1,431,552 | 04cd10bddd4e823d2ea495ee95b264cb2bce1f4c |

当前 SPL/FIT 已解析出 Radxa E25 / RK3568 板级 FDT 指纹。Linux 启动时加载的是 Panther X2 kernel DTB，不能与 U-Boot control FDT 混为一谈。

## 2. 高优先级候选 A：Ophub JP-TvBox U-Boot

### 2.1 直接实机案例

Ophub amlogic-s9xxx-armbian Issue #2027（2024-01-15）记录了 Panther X2 / RK3566 使用 RK35xx 内核时 eth0 不工作：

- 作者先后尝试修改 Panther X2 DTB、换用 JP-Box DTB，均未解决。
- 随后只换成 JP-Box U-Boot，保持原 DTB 不变，RK35xx 内核即可识别 eth0。
- 讨论中作者确认：默认 U-Boot + 默认 6.1.y 内核正常；默认 U-Boot + RK 内核时 eth0 不工作。
- 2024-01-28 的跟帖给出明确操作来源：ophub/u-boot 仓库 u-boot/rockchip/jp-tvbox/，使用该目录的 idbloader.img 与 u-boot.itb。跟帖作者特别警告该操作只针对 Panther X2，不要给其他盒子尝试，并提示没有线刷条件不要尝试。

来源：
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/2027
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/2027#issuecomment-1899941064
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/2027#issuecomment-1900040954
- https://github.com/ophub/amlogic-s9xxx-armbian/issues/2027#issuecomment-1919182435

这是目前发现的最强候选证据：同一 Panther X2 型号、同一类 RK 内核网络故障，并且报告了只替换 U-Boot 后恢复网卡的对照结果。它仍是社区用户报告，不是我们设备上的复现实验；案例没有证明 USB 也会因此恢复。

### 2.2 候选文件元数据

Ophub U-Boot 当前 main 分支目录：
https://github.com/ophub/u-boot/tree/main/u-boot/rockchip/jp-tvbox

| 文件 | 大小 | Git blob SHA-1 |
|---|---:|---|
| idbloader.img | 309,248 | 4bf6c334d4bf16b83c4317286907a361de8be489 |
| u-boot.itb | 1,464,832 | 2e453265e2e87e0ebd41897131fa6447dff4c0d1 |

与当前 Panther X2 文件不同：
- idbloader 大 4,096 bytes；
- u-boot.itb 大 33,280 bytes；
- 两个 Git blob SHA-1 均不同。

Ophub 设备数据库将 JP-TvBox 列为 RK3566，配置 rk3566-jp-tvbox.dtb、idbloader.img、u-boot.itb；描述为 8GB LPDDR4、SATA、1Gb NIC。Panther X2 条目为 RK3566、4GB LPDDR4、32GB eMMC、双千兆网口。

来源：
- https://github.com/ophub/amlogic-s9xxx-armbian/blob/277a2f610d70d45d4662daeadb2688226c5a3d61/build-armbian/armbian-files/common-files/etc/model_database.conf
- https://github.com/ophub/u-boot/tree/main/u-boot/rockchip/jp-tvbox

重要限制：
- JP-TvBox 与 Panther X2 SoC 同为 RK3566，但内存容量及板级连接不同。
- 2024 案例对 Panther X2 的成功测试是有力兼容性证据，但仍需检查 SPL/DDR 初始化配置，不能仅因 SoC 相同就直接认定安全。
- 当前尚未静态提取 JP-TvBox 两个二进制中的 SPL build string、DDR loader、FIT configuration、control FDT、时钟/复位/pinctrl/GMAC/USB 配置。
- 不能使用 JP-TvBox 的 Linux DTB 替换 Panther X2 DTB；案例中特别指出有效对照是换 U-Boot、保持原 DTB。

## 3. 候选 B：Radxa ROCK 3C / Armbian 官方 Panther X2 构建路线

当前 Armbian 官方板级配置 config/boards/panther-x2.eos 使用：
- BOOTCONFIG="rock-3c-rk3566_defconfig"
- U-Boot source：https://github.com/radxa/u-boot.git
- branch：stable-4.19-rock3
- Panther X2 kernel DTB：rockchip/rk3566-panther-x2.dtb

来源：
- https://github.com/armbian/build/blob/main/config/boards/panther-x2.eos
- https://github.com/radxa/u-boot/tree/stable-4.19-rock3

该路线是正式 Armbian 构建配置，来源和 defconfig 明确，适合作为可复现源码构建候选；但它采用 ROCK 3C defconfig，并非独立的 Panther X2 U-Boot 板级 defconfig。尚无当前 Panther X2 实机的网络/USB 对照验证，因此证据等级低于候选 A 的社区实测报告。

## 4. 候选 C：Radxa stable-4.19-rock3 的 Panther X2 BSP 构建记录

公开项目 clfang666/Panther-x2-NPU-VPU 的 panther-x2-vendor.csc 固定：
- Armbian build commit：70a242faa308c57be5ed636897dfee77de350773
- U-Boot source：Radxa stable-4.19-rock3
- U-Boot commit：c55987146f4f9b20f7cb2f917ca88300419afe8d
- defconfig：rock-3c-rk3566_defconfig
- kernel：Rockchip vendor BSP 6.1.115

来源：
- https://github.com/clfang666/Panther-x2-NPU-VPU
- https://github.com/clfang666/Panther-x2-NPU-VPU/blob/main/armbian/config/boards/panther-x2-vendor.csc

这是一个固定源码提交的构建参考，不是已证明适合 mainline Linux 6.12 的 U-Boot；其目标是 vendor BSP 6.1，不能直接当作 6.12 最终候选。

## 5. 当前候选排序与判断

| 候选 | 证据 | 目前定位 |
|---|---|---|
| Ophub JP-TvBox 两个 U-Boot 文件 | Panther X2 用户报告换 U-Boot、保留 DTB 后 RK 内核网卡恢复 | 优先静态分析；最强经验候选 |
| Radxa stable-4.19-rock3 + rock-3c-rk3566_defconfig | Armbian 官方 Panther X2 board config 指定该来源 | 可复现源码候选 |
| Radxa stable-4.19-rock3 固定 commit 的 vendor BSP 6.1 构建 | 第三方项目固定了源码和构建配置 | 作为源码参考，不直接作为 6.12 候选 |
| 当前 Ophub Panther X2 文件 | 已确认旧 6.1.116 与当前 6.12.81 共用；控制 FDT 显示 E25 | 保留为对照基线，不作为首选修复方案 |

## 6. 下一步只读工作

1. 固定 JP-TvBox U-Boot 文件的 commit/ref，下载到研究环境并记录 SHA-256、文件大小；不写入设备。
2. 静态解析 JP-TvBox idbloader.img：SPL 版本、内嵌 FDT、DDR 初始化/loader 指纹、板级 pinmux/PMIC/时钟信息。
3. 静态解析 JP-TvBox u-boot.itb：FIT config、U-Boot 版本、control FDT、GMAC/USB/PCIe/USB PHY 节点、reset GPIO、clock parent 和 pinctrl。
4. 将 JP-TvBox 与当前 Panther X2 U-Boot、Radxa ROCK 3C source build 逐项对照。
5. 确认候选 SPL 对 Panther X2 4GB LPDDR4 的适配风险；不能以 JP-TvBox 8GB LPDDR4 板级规格直接替代 Panther X2 内存验证。
6. 形成只读审计结论后，再讨论是否在独立 TF 卡上进行受控 A/B 启动。保持原始 TF/eMMC 启动区不动；在明确授权前不刷写、不修改系统。

## 7. 证据边界

- 已验证：当前与旧 6.1.116 U-Boot 文件逐字节相同；JP-TvBox 候选文件在 Ophub 仓库存在，文件大小及 Git blob SHA-1 已取得；公开 Issue #2027 有 Panther X2 换 JP-Box U-Boot 后 RK 内核 eth0 恢复的用户报告。
- 未验证：JP-TvBox U-Boot 在当前 Panther X2 实物上的启动稳定性；对 USB 的影响；对 4GB LPDDR4 的 DDR 初始化适配；与 Linux 6.12.81 的完整兼容性。
- 不推断：不能因为旧 U-Boot 与新内核组合出现网络故障，就仅凭版本相同认定 U-Boot 是唯一根因。应通过同一 Linux Image/DTB 下替换 U-Boot 的对照实验建立因果关系。


## 8. 第一轮二进制静态对照：JP-TvBox SPL 内嵌 FDT（2026-11-17）

本轮通过 Ophub GitHub 文件接口以 base64 只读取得两份 idbloader.img，并在内存中解析 Rockchip RKNS 镜像字符串及其内嵌 FDT。未写入任何设备。

### 8.1 SPL / DDR loader 指纹

| 项目 | JP-TvBox 候选 | 当前 Panther X2 基线 |
|---|---|---|
| idbloader 大小 | 309,248 bytes | 305,152 bytes |
| Git blob SHA-1 | 4bf6c334d4bf16b83c4317286907a361de8be489 | d22b624fc90c46e656baf98894bee182316e692e |
| SPL build string | U-Boot SPL 2017.09-armbian (Nov 12 2023 - 15:05:14) | U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07) |
| DDR loader 字符串 | DDR Version V1.10 20210810 | DDR Version V1.13 20220218 |
| 内嵌 FDT 起始偏移 | 283,840 (0x454c0) | 283,840 (0x454c0) |
| 内嵌 FDT totalsize | 23,946 (0x5d8a) | 20,421 (0x4fc5) |
| FDT root compatible | radxa,rock3c / rockchip,rk3566 | radxa,e25 / rockchip,rk3568 |
| FDT model | Radxa ROCK3 Model C | Radxa E25 |

关键判断：
- JP-TvBox 候选的 SPL 不是当前旧 Panther X2 SPL 的简单重打包；其 SPL build 时间晚约 7 个月，DDR loader 字符串也不同。
- JP-TvBox SPL 的 FDT 是 RK3566 ROCK 3C，而当前 Panther X2 SPL 的 FDT 是 RK3568 E25。
- DDR Version 字符串只识别出 DDR 初始化代码/loader 版本，不能据此推断它实际按 8GB 或 4GB 参数训练，也不能证明 JP-TvBox SPL 一定适配 Panther X2 的 4GB LPDDR4。容量/颗粒/总线宽度/Rank/频率和训练结果仍需源码或实际日志验证。
- 两个镜像均含 LPDDR2/LPDDR3/LPDDR4/LPDDR4X 支持字符串；这只说明固件包含相应类型支持代码，不等于具体板级参数相同。

### 8.2 GMAC1 FDT 对照

| 属性 | JP-TvBox SPL FDT | 当前 Panther X2 SPL FDT |
|---|---|---|
| 节点 | ethernet@fe010000 | ethernet@fe010000 |
| status | okay | disabled |
| phy-mode | rgmii | rgmii |
| clock_in_out | output | output |
| pinctrl | GMAC1 M1 | GMAC1 M1 |
| tx_delay | 0x47 | 0x4f |
| rx_delay | 0x27 | 0x26 |
| reset GPIO controller | gpio@fe760000（GPIO3） | gpio@fe750000（GPIO2） |
| reset GPIO offset | 0x10 | 0x19 |
| reset active low | 是 | 是 |
| reset delays | 0 / 20000 / 100000 us | 0 / 20000 / 100000 us |

这是值得关注的差异：
- 当前 E25 GMAC1 节点 status=disabled；JP ROCK3C 节点 status=okay。虽然 U-Boot DM 是否实际 probe 仍需结合 U-Boot 源码/运行日志确认，但 JP 配置明确把 GMAC1 作为启用设备描述。
- 两者均用 M1 与 clock output；因此不能笼统说 JP 候选只是把 M1 改成 M0。真正差异是 enable 状态、delay 值和 reset GPIO。
- JP 的 reset GPIO 是 GPIO3 line 16；当前 E25 是 GPIO2 line 25。Linux 运行时 Panther X2 FDT 又使用 GPIO3 line 1。三个阶段/配置不能混为一谈。
- JP 的 tx/rx delay 0x47/0x27 与 Panther X2 Linux 当前 0x30/0x10 不同。尚不能仅凭数值判断哪个物理时序正确。

### 8.3 USB FDT 对照

JP-TvBox SPL FDT 相比当前 Panther X2/E25 SPL FDT，除两者均包含 USB3 DWC3 OTG/Host 外，还明确包含：
- USB2 EHCI：usb@fd800000、usb@fd880000，status=okay。
- USB2 OHCI：usb@fd840000、usb@fd8c0000，status=okay。
- 第二个 USB2 PHY：usb2-phy@fe8b0000，host-port 和 otg-port 均 status=okay。
- 固定 5V host regulator：vcc5v0-host-regulator，GPIO0 bank line 21 控制，enable-active-high。
- 两组 USB2 PHY 分别服务两组 EHCI/OHCI host 控制器。

当前 Panther X2/E25 SPL FDT 中未发现上述 EHCI/OHCI 节点、第二个 USB2 PHY 和 vcc5v0-host-regulator；只看到 USB3 DWC3 OTG/Host 及 usb2-phy@fe8a0000。

这与用户报告的 USB 异常形成了新的、具体的板级配置对照方向。需要强调：这是 U-Boot/SPL 内嵌 FDT 差异，不等于 Linux 6.12 运行时设备树也缺少这些节点；也不能仅凭 U-Boot FDT 证明 Linux USB 故障由此造成。下一步应把 JP FIT 内的 U-Boot control FDT 与 Linux 运行时 Panther X2 FDT 的 USB 节点逐项对照。

### 8.4 FIT 文件静态解析限制

本轮 GitHub 文件接口能够读取两份 idbloader.img，但对大于 1 MB 的 u-boot.itb 返回空内容，因此本轮尚未解析 JP-TvBox FIT 内的：
- U-Boot proper 版本/build string；
- FIT configuration 与 ATF image 版本；
- FIT 内 U-Boot control FDT；
- U-Boot proper 中 GMAC/USB driver-model 节点和实际配置。

因此 8.1–8.3 的对照严格限定为 SPL/idbloader 内嵌 FDT，不能替代 FIT/u-boot.itb 分析。

### 8.5 当前阶段结论

JP-TvBox 是目前最值得继续研究的候选，但不能直接刷写：
1. 它提供了 RK3566 ROCK 3C 的 SPL/FDT，而当前基线是 RK3568 E25。
2. 它将 GMAC1 设为 okay，并使用不同的 reset GPIO 和 delay 值。
3. 它提供了当前 E25 SPL FDT 缺少的 USB2 EHCI/OHCI、第二 PHY 和 host 5V regulator 描述。
4. 它的 DDR loader 版本较旧（V1.10），而当前基线为 V1.13；必须查清实际 DDR 参数与 4GB LPDDR4 适配，不能只看它曾被 Panther X2 用户用于网卡恢复的报告。

下一步优先级：
- 获取/分析 JP-TvBox u-boot.itb 的 FIT control FDT（当前 GitHub binary fetch 路径无法直接返回该大文件，需寻找可审计的替代来源或源码构建产物）。
- 对照 Armbian 官方 Panther X2 rock-3c-rk3566_defconfig 所指向的 Radxa U-Boot 源码，确认 SPL DDR loader 与 board DTS。
- 检查 JP-TvBox 与 Panther X2 的 DDR 配置源文件、LPDDR4 参数和 U-Boot build config。
- 对照 Linux 6.12.81 运行时 FDT 的 USB 控制器、PHY、vbus/5V regulator、GPIO 和 pinctrl；不重复已完成的 GMAC Linux 配置验证。


## 9. 新发现：Armbian 官方 Panther X2 U-Boot 修复路线（2026-11-17）

### 9.1 Armbian PR #9243：直接的 Panther X2 启动实测线索

Armbian/build PR #9243（Fix Panther-X2）于 2026-01-14 合并，merge commit `0e2fec109e12e01bf982b3c565dbda17c7279aa4`。
PR 作者说明：原有 Panther X2 build 在 U-Boot 层面有问题；测试多个 build 后，Radxa `stable-4.19-rock3` branch 能够正常启动，因此将 Panther X2 的 U-Boot source 改为该分支，并禁用其他 U-Boot patch。

当前 Armbian `config/boards/panther-x2.eos` 仍采用：
- `BOOTCONFIG="rock-3c-rk3566_defconfig"`
- `BOOTSOURCE=https://github.com/radxa/u-boot.git`
- `BOOTBRANCH=branch:stable-4.19-rock3`
- `BOOTPATCHDIR="none"`、`BOOTPATCHES="none"`
- kernel DTB 仍为 `rockchip/rk3566-panther-x2.dtb`

来源：
- https://github.com/armbian/build/pull/9243
- https://github.com/armbian/build/commit/0e2fec109e12e01bf982b3c565dbda17c7279aa4
- https://github.com/armbian/build/blob/main/config/boards/panther-x2.eos

这比单个 JP-TvBox 社区报告更强：Armbian 官方 Panther X2 构建配置已明确将 Radxa ROCK 3C U-Boot 作为启动修复路线，而且 PR 作者说明有多组构建测试后能正常启动。限制是 PR 没有详细列出测试硬件的网络、USB、存储逐项结果，也没有明确说“仅换 U-Boot、其余所有变量完全不变”。

### 9.2 当前 Armbian 构建使用的 RK3566 固件组件

当前 Armbian `config/sources/families/include/rockchip64_common.inc` 的 RK3566 默认组件为：
- DDR TPL：`rk35/rk3566_ddr_1056MHz_v1.21.bin`
- ATF BL31：`rk35/rk3568_bl31_v1.44.elf`
- `BOOT_SOC_MKIMAGE="rk3568"`（用于 RK3566 的 mkimage 参数兼容）

来源：https://github.com/armbian/build/blob/main/config/sources/families/include/rockchip64_common.inc

这说明若以当前 Armbian 官方构建流程重建 Radxa `stable-4.19-rock3` U-Boot，使用的 DDR/ATF blob 与 2023 JP-TvBox 二进制中检测到的 DDR V1.10 不同。注意：这是当前构建默认值，不代表 2026-01 PR 合并时所用的确切 blob 版本，也不代表 V1.21 已经在本 Panther X2 上验证。

### 9.3 JP-TvBox 与 Panther X2 Linux DTS 的 USB/GMAC 差异需要谨慎解释

本轮重新对照当前 Linux Panther X2 DTS（固定 Linux source commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`）：
- Linux Panther X2 GMAC1 使用 M0 pinctrl、`clock_in_out="input"`、reset GPIO3_PA1、TX/RX delay 0x30/0x10。
- JP-TvBox SPL FDT GMAC1 使用 M1 pinctrl、`clock_in_out="output"`、reset GPIO3_PC0、TX/RX delay 0x47/0x27。
- Linux Panther X2 DTS 启用 USB host0 EHCI/OHCI 与 USB2 PHY0 host；JP ROCK3C SPL FDT 还启用 USB host1 EHCI/OHCI、第二 USB2 PHY 及 GPIO 控制的 host 5V regulator。

因此 JP-TvBox 的网卡成功案例虽强，但 JP 的 U-Boot FDT 与 Panther X2 Linux DTS 的 GMAC 参数并不相同；JP 的额外 USB host 电源 GPIO 也尚未证明与 Panther X2 板级线路相符。不能将 JP-TvBox 二进制直接认定为完整正确的 Panther X2 板级固件。

### 9.4 新发现：Nabu Casa / HAOS 的 Panther X2 专用 U-Boot patch

在 `wuwweizn/ZG-HAOS` 公开构建配置中发现一套针对 Panther X2 的 U-Boot v2025.01 patch，且固定使用：
- U-Boot base：upstream U-Boot v2025.01，基线 commit `6d41f0a39d6423c8e57e92ebbe9f8c0333a63f72`
- DDR TPL：`rk3566_ddr_1056MHz_v1.18.bin`
- ATF：`rk3568_bl31_v1.43.elf`
- 新增 Panther X2 board code、Panther X2 kernel DTS 与 `rk3566-panther-x2-u-boot.dtsi`
- board code 从 I2C EEPROM 读取板版本、序列号和 MAC（MAC offset 0x22）

来源：
- https://github.com/wuwweizn/ZG-HAOS/blob/main/buildroot-external/configs/panther_x2_defconfig
- https://github.com/wuwweizn/ZG-HAOS/blob/main/buildroot-external/board/panther/x2/patches/uboot/0001-add-panther-x2-uboot.patch
- https://github.com/u-boot/u-boot/commit/6d41f0a39d6423c8e57e92ebbe9f8c0333a63f72

但此 patch 中 `CONFIG_DEFAULT_DEVICE_TREE="rockchip/rk3568-evb1-v10"`，而 `CONFIG_DEFAULT_FDT_FILE="rockchip/rk3566-panther-x2.dtb"`。即 U-Boot control FDT 仍指向 RK3568 EVB，Panther X2 DTB 是默认启动时传给 Linux 的 FDT；虽然 patch 新增 Panther X2 U-Boot DTSI，但当前 defconfig 没有选它作为 control FDT。必须进一步审计 build flow，不能只凭 patch 文件名认定 U-Boot proper 已使用 Panther X2 control FDT。

此外，该 board code 的 I2C EEPROM MAC 读取机制与本项目已确认的 eMMC/TF vendor data MAC 路径不同；尚未证明 Panther X2 实物板上存在它预期的 I2C EEPROM 内容和地址，不能直接套用。

### 9.5 OpenWrt 衍生构建中的 Panther X2 U-Boot target

另在 OpenWrt 衍生仓库 `coolsnowwolf/lede` 的 U-Boot Rockchip package 中发现 `panther-x2-rk3566` target，包版本 `2026.07`，RK3566 默认 TPL `rk3566_ddr_1056MHz_v1.23.bin`、ATF `rk3568_bl31_v1.44.elf`。

但其 `316-rockchip-rk3566-Add-support-for-panther-x2.patch` 新增的 defconfig 仍设置 `CONFIG_DEFAULT_DEVICE_TREE="rockchip/rk3568-evb1-v10"` 和 `CONFIG_TARGET_EVB_RK3568=y`，仅把 `CONFIG_DEFAULT_FDT_FILE` 指向 `rk3566-panther-x2.dtb`。因此它是一个可研究的现代构建入口，但 control FDT 选择仍有板级匹配疑问，不能仅因 target 名称为 Panther X2 就认定已解决本项目问题。

来源：
- https://github.com/coolsnowwolf/lede/blob/d75c7ff94b00a475db7fef465cf17155cd733131/package/boot/uboot-rockchip/Makefile
- https://github.com/coolsnowwolf/lede/blob/d75c7ff94b00a475db7fef465cf17155cd733131/package/boot/uboot-rockchip/patches/316-rockchip-rk3566-Add-support-for-panther-x2.patch

### 9.6 候选排序更新

1. **第一优先：Armbian 官方 Panther X2 构建路线：Radxa `stable-4.19-rock3` + `rock-3c-rk3566_defconfig`，按当前 Armbian build 组件构建。** 有 Panther X2 官方 build 修复 PR 的实测说明，且当前 build 明确沿用；先审计其 control FDT、GMAC reset、USB PHY/host 和 DDR TPL 版本。
2. **第二优先：Nabu Casa/HAOS Panther X2 专用 patch。** 具备专门的 board code、Panther X2 DTS 和 EEPROM MAC 读取，但 control FDT 默认仍是 RK3568 EVB，MAC 数据来源也尚未与本机硬件对应。需先厘清构建选择和板级适配。
3. **第三优先：Ophub JP-TvBox 2023 二进制。** 有 Panther X2 网络恢复的直接社区报告，但 DDR V1.10 较旧，且 GMAC reset/delay、USB host 电源与 Panther X2 DTS 有明确差异；只作为对照样本。
4. **辅助参考：OpenWrt 2026.07 Panther X2 target。** TPL V1.23/BL31 V1.44 较新，但 defconfig 的 control FDT 仍为 RK3568 EVB，先审计，不直接作为候选固件。

### 9.7 下一步

- 获取 Radxa `stable-4.19-rock3` 对应 Armbian 构建的完整构建参数和生成物（尤其 idbloader、u-boot.itb、FIT control FDT、ATF/DDR blob 版本），以静态证据验证实际内容。
- 重点确认 ROCK3C U-Boot 的 GMAC reset GPIO3_PC0 是否会在 Panther X2 上驱动错误线路；结合 U-Boot DM probe/legacy 初始化路径判断是否真的执行。
- 比较 Panther X2 真实 USB 物理端口与 Linux DTS 中 USB host0/PHY0 映射，避免误启用 ROCK3C 特有的 host1/5V GPIO。
- 检查 DDR TPL v1.21/v1.23 与本机 4GB LPDDR4 的训练参数。版本号更高不等于已验证适配。
- 继续保持只读研究；未完成候选审计和明确授权前，不改 TF/eMMC 启动区。


## 10. 研究二进制集中归档（2026-11-21）

为避免后续反复索取原始文件，Ophub 原版与 JP-TvBox 两套 U-Boot 二进制现已归档到项目仓库：

- Ophub 原版：`docs/research-assets/bootloader/panther-x2/ophub-original/`
- JP-TvBox 候选：`docs/research-assets/bootloader/panther-x2/JP-TvBox-U-Boot/`

已从 Git tree 核对四个文件均存在，文件大小如下：

| 版本 | 文件 | 大小 | Git blob SHA1 |
|---|---|---:|---|
| Ophub 原版 | `idbloader.img` | 305152 | `d22b624fc90c46e656baf98894bee182316e692e` |
| Ophub 原版 | `u-boot.itb` | 1431552 | `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c` |
| JP-TvBox | `idbloader.img` | 309248 | `4bf6c334d4bf16b83c4317286907a361de8be489` |
| JP-TvBox | `u-boot.itb` | 1464832 | `2e453265e2e87e0ebd41897131fa6447dff4c0d1` |

Ophub 两个文件的 Git blob SHA1 与此前确认的公开来源对象相同；JP idbloader SHA1 与本报告§8.1已有记录相同。JP FIT 文件当前完成仓库对象身份归档，但尚未独立完成 FIT 内容解析。Git blob SHA1 是 Git 对象指纹，不代替 SHA256；SHA256 待在可直接读取完整二进制字节的环境中计算。

本次归档只固定研究输入，不代表任何候选固件已获准写入设备。实机实验继续遵守 eMMC 绝不写入的约束。


## 11. Armbian PR #9243 对应 Radxa U-Boot 源码审计（2026-11-21）

### 11.1 已锁定实际源码提交

Armbian PR #9243（merge commit `0e2fec109e12e01bf982b3c565dbda17c7279aa4`）修改的是 `config/boards/panther-x2.csc`，将 U-Boot source 指向 Radxa `stable-4.19-rock3`，关闭 U-Boot patch。该分支当前 HEAD 为 `c55987146f4f9b20f7cb2f917ca88300419afe8d`（2023-05-28）。PR 原文称测试多个构建后该分支允许 Panther X2 proper booting。

对应 defconfig `configs/rock-3c-rk3566_defconfig`，核心板级选择：
- `CONFIG_TARGET_EVB_RK3568=y`
- `CONFIG_DEFAULT_DEVICE_TREE="rk3566-rock-3c"`
- `CONFIG_ROCKCHIP_RK3568=y`

即目标宏仍为 EVB RK3568，但 control FDT 实际指定 RK3566 ROCK 3C。不能只看 TARGET 宏判定实际使用 EVB DTS；也不能把 ROCK 3C FDT 当作 Panther X2 专用 FDT。

### 11.2 SPL 启动设备选择与旧实机日志不同

该提交 `arch/arm/mach-rockchip/spl.c` 的 `spl_boot_device()` 默认返回 `BOOT_DEVICE_MMC1`，只有启用 `CONFIG_ROCKCHIP_BACK_TO_BROM` 时才返回 BOOTROM。该源码没有 Panther X2 专用覆盖证据。该提交 `common/spl/spl.c` 的 weak `board_boot_order()` 只将 `spl_boot_device()` 放入第一个候选项，因此默认只尝试一个 MMC boot device。

同提交 `common/spl/spl_mmc.c` 映射：
- `BOOT_DEVICE_MMC1` -> MMC device index 0
- `BOOT_DEVICE_MMC2` / `MMC2_2` -> MMC device index 1

这与 Panther X2 原版 UART 曾出现的 `Trying to boot from MMC2` 不同，且原版历史链已通过 ATAGS 映射为 MMC2->SD0、proper mmc1 为 TF。Radxa branch 默认 MMC1 路径的物理介质映射尚未在 Panther X2 实机上验证。**不能把 Armbian PR 的“能启动”理解成已证明它从 TF 启动，也不能据此认定它是 TF-only。**

该分支 `spl_mmc_load_image()` 对指定 MMC 执行初始化并读取 FIT/raw/partition/filesystem；如果当前单个 MMC 设备加载失败，通用 `board_boot_order()` 没有第二候选可回退。这是与原版实机出现 MMC2 失败后尝试 MMC1 的明显行为差异，需实机验证该构建在 Panther X2 的实际表现。

### 11.3 该 defconfig 不适合未经改造直接作为安全 Boot Probe

静态检查 `rock-3c-rk3566_defconfig` 发现：
- `CONFIG_BOOTDELAY=0`：默认不留交互等待窗口，不能直接满足 UART 人工接管要求。
- `CONFIG_SPL_MMC_WRITE=y`、`CONFIG_SPL_MTD_WRITE=y`：编译启用 SPL 写入能力。
- `CONFIG_FASTBOOT_FLASH=y` 且 `CONFIG_FASTBOOT_FLASH_MMC_DEV=0`：启用 Fastboot 存储写入能力，默认目标设备编号为 0。
- `CONFIG_CMD_TFTP_FLASH=y`、`CONFIG_CMD_GPT=y`、`CONFIG_CMD_MTD=y`、`CONFIG_CMD_MMC=y`：proper 包含多种可修改存储的命令能力。

这些配置项本身不证明启动时必然写 eMMC，但在本项目“eMMC绝不写入”的约束下，未经剥离/禁用和完整调用路径审计，不得将该 defconfig 构建物直接作为探针写入 TF 后上机。

更重要的是，同提交 `arch/arm/mach-rockchip/board.c` 的 `rockchip_set_ethaddr()` 在 `CONFIG_ROCKCHIP_VENDOR_PARTITION` 下先调用 `vendor_storage_read(LAN_MAC_ID,...)`；若读失败或 MAC 无效，会生成随机 MAC 并调用 `vendor_storage_write(LAN_MAC_ID,...)`。该函数由 `board_late_init()` 调用。由于本项目已确认 TF Vendor Storage 与 eMMC Vendor Storage 内容不同，且目标是 eMMC只读、MAC来源固定为eMMC权威Vendor Storage，这段代码存在两个必须先解决的问题：
1. 必须追清 `vendor_storage_read/write` 的设备选择，确认其是否跟随 bootdev，以及 TF 启动时会不会向 TF 写入；
2. 必须禁用随机MAC写回路径，并改为明确只读 eMMC 权威Vendor Storage，不能直接采用该通用行为。

在解决上述风险前，Radxa branch 只作为源码研究参考，不作为可直接写卡的探针镜像。

### 11.4 目前结论与下一项验证

已确认：PR #9243 实际切换到 Radxa stable-4.19-rock3；该分支默认 SPL MMC1、默认只尝试一个设备；其 defconfig 的启动延时和存储写入能力不符合本项目探针安全要求；board_late_init 有潜在 Vendor Storage 写回路径。

未确认：MMC1 在 Panther X2 实机对应 eMMC 还是 TF；vendor_storage 的具体设备选择与写入目标；PR 测试构建的确切产物和 SPL/DDR/ATF blob 版本；PR 测试是否专门验证了 Panther X2 TF 启动。

下一步先从该提交追踪 `rockchip_get_bootdev()`、`vendor_storage_read/write()`、vendor storage block device选择和 MMC device enumeration；再对照原版二进制中实际 MMC 映射。若静态代码仍不能确定物理设备编号，制作只读 UART Boot Probe 在 TF 上验证，启动前先对探针构建禁用所有存储写入能力与Vendor写回路径。eMMC保持绝对只读。
