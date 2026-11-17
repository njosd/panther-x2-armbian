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
