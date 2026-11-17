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
