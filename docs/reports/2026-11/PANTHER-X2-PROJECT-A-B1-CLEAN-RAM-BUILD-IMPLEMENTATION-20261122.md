# 项目 A / B1：纯 RAM 干净基线构建实施记录

- 日期：2026-11-22
- 阶段：B1
- 状态：构建方案与文件已提交；尚未运行 CI、尚无 B1 artifact、尚未进行 Panther X2 实机启动
- 目标：建立与存储系统、网络系统完全解耦的最小 ARM64 RAM Linux，再以它作为后续有线千兆 Ethernet 逐项引入的干净起点

## 1. B1 范围冻结

B1 只验证 Kernel、Panther X2 DTB、gzip initramfs、静态 BusyBox 和 UART2 shell 组成的独立 RAM 启动链。

Linux B1 不启用或打包：
- 网络协议栈及任何网络设备驱动；
- 板载 Ethernet GMAC/STMMAC/DWMAC、MDIO、PHY/PCS；
- Wi-Fi/无线网络、蓝牙及其控制器、驱动、固件、协议、用户空间；
- USB host/PHY；
- MMC/eMMC/TF/SD/SDIO、块设备、文件系统驱动；
- Kernel modules、.ko、/lib/modules、网络固件；
- ip、ARP/ICMP、TCP/UDP、DHCP、DNS、SSH 等网络工具或服务。

Wi-Fi/无线网络和蓝牙是项目 A 永久排除项，不进入后续逐项引入。USB/PCIe 外接网卡也不属于项目 A。板载有线 Ethernet 才是项目 A 的最终目标，但 B1 必须先隔离，B2 才按最小依赖闭包逐项引入。

## 2. Linux 与 TF 的边界

- JP-TvBox U-Boot proper 在 Linux 启动前从 TF 读取 Image、uInitrd 和 clean-test DTB。
- Linux Kernel 与 initramfs 进入 RAM 后运行；Linux 阶段不再访问 TF/eMMC。
- Kernel config 关闭 CONFIG_BLOCK、CONFIG_MMC、CONFIG_USB、CONFIG_NET、CONFIG_MODULES 等。
- 不编译或调用旧 blockro helper。Linux 不枚举 block devices，因此无需在 init 后设置 block-layer RO。
- 这不替代 eMMC pre-Linux 写入安全门：BootROM/SPL/BL31/U-Boot 的写入风险仍须单独排除。

## 3. 锁定的首轮构建输入

| 输入 | 锁定值 | 说明 |
|---|---|---|
| Linux source | https://github.com/ophub/linux-6.18.y.git | 从源码构建，不使用 Ophub 预编译 Image |
| Linux commit | aee4e352a15d636cbc484f56819c6e59474dfd9f | 已核对 Makefile 为 6.18.63；首轮候选，待 CI |
| Kernel config | scripts/panther-x2-b1/kernel.config.fragment | allnoconfig + fragment，再 olddefconfig |
| No-NET compatibility patch | scripts/panther-x2-b1/patches/0001-kobject-uevent-config-net-n.patch | 仅修正 CONFIG_NET=n 时 kobject_uevent stub 的 skb 释放路径，不启用网络栈 |
| Panther X2 DTS | 同一 Linux commit 的 rk3566-panther-x2.dts | 由脚本派生，不修改上游原文件 |
| BusyBox | 1.37.0 | 源码包 SHA-256：3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4 |
| BusyBox config | scripts/panther-x2-b1/busybox.config.fragment | allnoconfig，静态 ash 和最小 applet |
| JP U-Boot proper | docs/research-assets/bootloader/panther-x2/JP-TvBox-U-Boot/u-boot.itb | SHA-256：a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce |

首轮 commit 是构建输入候选，不代表已构建成功、已锁定最终 Kernel 或已通过目标硬件启动。

## 4. 新增/调整的实现文件

| 文件 | 用途 |
|---|---|
| .github/workflows/build-panther-x2-b1-clean-ram.yml | 独立 B1 手动构建流程；只生成组件 artifact |
| scripts/panther-x2-b1/kernel.config.fragment | ARM64/RK3566/UART/initramfs 最小 Kernel 配置，关闭网络/存储/USB/模块 |
| scripts/panther-x2-b1/busybox.config.fragment | 静态 ash 与最小 applet 配置 |
| scripts/panther-x2-b1/prepare-clean-dtb.py | 派生 clean-test DTB，禁用 GMAC/MDIO、MMC、USB、BT UART 并删除 Wi-Fi/BT 板级节点 |
| scripts/panther-x2-b1/verify-b1-config.sh | 检查 Kernel 最终配置、BusyBox ARM64 静态属性、必需 applet 和网络 applet 禁止清单 |
| scripts/panther-x2-b1/patches/0001-kobject-uevent-config-net-n.patch | 解决 6.18.63 在 CONFIG_NET=n 下的通用 uevent skb 释放链接依赖；只作用于无网络 stub |
| scripts/panther-x2-minimal-initramfs/init | 改为纯 RAM init；挂载 procfs/sysfs，输出诊断信息并进入 ash，不访问 MMC/block |
| scripts/panther-x2-minimal-initramfs/boot.cmd | 加载 Image/uInitrd/clean-test DTB 并启动 RAM Linux |

BusyBox applet 目标清单：ash、sh、cat、dmesg、mkdir、mount、tail、uname。CI 在 QEMU 下运行 ARM64 BusyBox，记录实际 applet 清单，并拒绝网络 applet。

## 5. DTB 隔离范围

clean-test DTB 必须保持：
- Panther X2 model 与 panther,x2 / rockchip,rk3566 compatible；
- UART2（ttyS02）作为启动控制台；
- SoC 必要时钟、pinctrl 和启动基础设施。

clean-test DTB 禁用：
- gmac1 与其 mdio1 子树；
- sdhci、sdmmc0、sdmmc1；
- Bluetooth 所在 uart1；
- Panther X2 启用的 USB host 与 USB2 PHY 节点。

clean-test DTB 移除 Wi-Fi/蓝牙 GPIO、SDIO power-sequence、Wi-Fi/BT pinctrl 和 Wi-Fi/Ethernet 指示灯节点。原始 DTS/DTB 不覆盖。CI 还需反编译最终 DTB，逐节点检查状态及无线/蓝牙残留。

## 6. 构建产物边界

新 workflow 在固定源码 commit 上应用一项最小构建兼容补丁：6.18.63 的 lib/kobject_uevent.c 无网络 stub 仍调用 kfree_skb()，但该释放路径依赖 CONFIG_NET 下的 skb drop-reason 符号。源码中的 alloc_uevent_skb() 本身只在 CONFIG_NET 下编译，因此 CONFIG_NET=n 时无有效网络 skb 可交给该 stub。补丁将无网络 stub 改为：收到非空 skb 时返回 -EOPNOTSUPP，空指针时直接返回 0；不再引用任何 skb 网络释放函数。该补丁不启用 CONFIG_NET、不启用任何网络协议/设备/驱动，也不修改 Ethernet 代码。补丁文件和 SHA-256 纳入 artifact。

新 workflow 在 GitHub Actions runner 的临时工作目录中生成并验证 PREPARE-ONLY 的 2 GiB hybrid TF 镜像（包含 GPT/ext4 分区、Image/uInitrd/boot.scr/Panther X2 DTB，以及 LBA 16384 处的 JP proper FIT），随后压缩为 `.img.zst` 作为构建 artifact 上传。**这只是 CI runner 内的文件生成，不会写入用户的 TF/eMMC，也不会连接或启动 Panther X2。** 同一 artifact 还包含独立组件、配置、manifest、SHA-256 和日志。不得把该 artifact 描述成已经写卡或可直接启动认证通过。

新 workflow 上传的内容包括：
- ARM64 Kernel Image；
- clean-test Panther X2 DTB；
- gzip initramfs 和 legacy uInitrd；
- PREPARE-ONLY hybrid TF image 压缩包（仅 CI runner 生成）；
- boot.cmd / boot.scr；
- 静态 BusyBox、BusyBox config 和 applet 清单；
- Kernel config/fragment、clean-test DTS、manifest、SHA-256、构建日志；
- 已验证 JP U-Boot proper 参考文件。

不会向物理 TF/eMMC 写入任何数据，也不触发实机启动。Artifact 名称为 panther-x2-b1-clean-ram-prepare-only；其中 hybrid 镜像是 runner 生成的待审查文件，不代表已写卡或 B1 实机通过。

旧 .github/workflows/build-panther-x2-minimal-ram-boot.yml 使用 Ophub 预编译 Kernel、MMC/blockro 和 hybrid image 设计，现已标记为 deprecated 并禁用，保留作历史记录，不得再用于项目 A B1。

## 7. 当前状态与下一步

### 已提交（实现文件已进入仓库）
- B1 纯 RAM 方案和最小 Kernel/BusyBox config fragment；
- clean-test DTB 派生脚本；
- B1 config/applet 验证脚本；
- 新的 B1 clean RAM workflow；
- CONFIG_NET=n 下 kobject_uevent 的最小兼容补丁；
- /init 与 U-Boot boot script 更新；
- 2026-11-22 安全修订：boot.cmd 的文件加载失败分支不再调用 `reset`，仅输出错误并结束脚本，避免脚本在失败时触发未授权复位；
- 旧预编译 Kernel/hybrid workflow 禁用；
- 项目 A 总路线图、实施计划和旧启动方案状态同步。

### 尚未完成（不得写成已验证）
- 最新 workflow 的完整 CI 构建与 artifact 审查；
- Kernel allnoconfig 最终配置是否完整保留所需 TTY/UART/clock/pinctrl 选项；
- Kernel Image 实际编译；
- clean-test DTS/DTB 实际编译和节点审计；
- BusyBox 静态交叉编译、QEMU applet 检查；
- initramfs/uInitrd/boot.scr 构建；
- B1 artifact 完整性与 SHA-256 审查；
- B0.4 eMMC pre-Linux 写入安全门；
- 经安全门和单次授权后的 Panther X2 实机启动。

### CI 迭代记录
- 首轮源码检出成功，Kconfig 检查发现 ARM64 allnoconfig 默认启用了通用 BLOCK 层；启用 EXPERT 并显式关闭 CONFIG_BLOCK 后修正。
- 进一步检查发现 CONFIG_MODULES_USE_ELF_RELA 和 CONFIG_USB_OHCI_LITTLE_ENDIAN 是辅助配置符号，不代表模块系统或 USB host 驱动启用；验证规则已收窄为检查真实子系统/驱动选项。
- TMPFS 并非 initramfs rootfs 的必要条件，已从最小配置和验收门移除；串口驱动依赖 TTY，已显式加入 CONFIG_TTY。
- 6.18.63 在 CONFIG_NET=n 下出现 kobject_uevent stub 对 sk_skb_reason_drop 的未定义引用；已定位并添加上述最小兼容补丁。当前最新 CI 运行待完成，尚未证明补丁构建通过。

### 下一步顺序
1. 等待最新 B1 clean RAM workflow 完成；如失败，只处理该轮明确暴露的构建/配置问题。
2. 审查最终 .config、Image、DTB、BusyBox applet 清单、initramfs、uInitrd、boot.scr、manifest 和 SHA-256；任一网络/存储/USB/无线/蓝牙变量残留即判失败。
3. 单独完成 eMMC pre-Linux 写入安全门。未通过前不写 TF、不启动实验固件。
4. 安全门通过且用户明确授权后，才规划一次 B1 实机启动验证。B1 通过前不进入 B2。

## 8. 验收证据分级

- 文件/脚本已提交：仓库提交证据。
- 静态审计通过：实际检查结果和日志。
- CI 构建通过：Actions run 与 artifact。
- Panther X2 B1 启动通过：UART 原始日志及设备运行证据。
- B1 通过不等于有线千兆网口已通；有线 Ethernet 验证只在 B2 开始。


## 9. 2026-11-22 启动脚本安全修订与产物描述校正

静态审查发现旧版 `scripts/panther-x2-minimal-initramfs/boot.cmd` 在 Kernel、uInitrd 或 DTB 任一加载失败时会调用 `reset`。这与当前禁止脚本触发 reset/reboot 的安全边界冲突。现已改为嵌套条件：只有前一文件加载成功才继续下一步；任一加载失败只打印错误并停止，不主动复位。提交：`b3e7177d3cafc62c55948d5cbc3fe76b991cea65`。

同时纠正本报告此前对 workflow 产物的描述：当前 workflow 会在 GitHub Actions runner 临时环境中生成 2 GiB PREPARE-ONLY hybrid TF image，并上传压缩包；这不是物理 TF/eMMC 写入，也不连接或启动设备。后续仍须审查镜像分区布局、文件哈希和启动地址，再通过 eMMC pre-Linux 安全门及单独授权，才可考虑写入测试 TF。
