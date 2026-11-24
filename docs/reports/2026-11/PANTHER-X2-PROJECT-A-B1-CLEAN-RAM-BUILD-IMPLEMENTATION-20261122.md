# 项目 A / B1：纯 RAM 干净基线构建实施记录

- 日期：2026-11-22
- 阶段：B1
- 状态：B1 构建流水线曾成功产出 PREPARE-ONLY artifact；经后续基线一致性复核，当前 Kernel/DTB 产物不予验收，需按未修改上游源码重新构建；实机启动未进行
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


## 2026-11-23 B1 基线纠偏（覆盖旧裁剪规则）

本节与 `PANTHER-X2-PROJECT-A-B1-BASELINE-RESET-20261123.md` 一致；较早章节中“B1 关闭 MMC/USB/模块”等旧表述不再作为执行指令。

- **配置种子：** `ophub/kernel` 的 `kernel-config/release/rk35xx/config-6.12`，来源 commit `ba00be60d59300bd93633218a8905829d6cabd72`，Git blob `dee127c6c644f38426eeb28000d73536084d34a3`。
- **配置流程：** 完整 seed → Linux 6.18.63 `olddefconfig` 适配 → 网络隔离 fragment → 再次 `olddefconfig`；禁止从 `allnoconfig` 起步。
- **保留：** ARM64 4KB 页、VA48、PA48、LPA2 off、RK3566 erratum、BLOCK/MMC/eMMC/TF/SD、USB、文件系统、MODULES，以及 UART、时钟、复位、pinctrl、regulator、PMIC、DMA 和中断基础支持。
- **隔离：** 网络协议栈、网络设备、板载 Ethernet/GMAC/STMMAC/DWMAC、MDIO/PHY/PCS、Wi-Fi/无线和 Bluetooth。Wi-Fi/无线与 Bluetooth 永久排除；USB/PCIe 外接网卡也不属于项目 A。
- **DTB：** 保留 eMMC `sdhci`、TF/SD `sdmmc0`、USB host/PHY、UART1（仅移除 Bluetooth 子节点）、UART2、完整 aliases、Ethernet LED、GMAC 时钟节点及共享资源；禁用 GMAC1/MDIO1/PHY 和 Wi-Fi 专用 `sdmmc1`，移除 Wi-Fi/BT 专用节点。
- **模块：** 构建 Image 与 modules，安装并单独打包；不由 `/init` 自动加载。
- **RAM init：** 只挂载 procfs/sysfs，不自动挂载持久化文件系统、不主动写入存储。MMC 恢复后 Linux 仍可能枚举 eMMC；eMMC pre-Linux 安全门继续是实机启动的必要前置条件。
- **uevent：** 旧 kobject_uevent 补丁不再应用，仅保留历史审计；B1 使用未修改的锁定上游源码。

当前仅完成仓库分支中的实现和静态文件审查；CI、artifact、eMMC 安全门和 Panther X2 实机结果均未验证。


## 2026-11-24 CI 产物复核与基线修正

### Run #62 的实际结果

- Workflow Run：[#62 / 45291347822](https://github.com/njosd/panther-x2-armbian/actions/runs/45291347822)
- Workflow checkout commit：`d6368734c2d02787b0f27ebc8d9fdc61ed724d3e`
- Kernel/DTB：Job skipped，复用 Run #58（45201970736）的 `b1-kernel-dtb`，Artifact ID `14833674072`，大小 206,769,641 bytes，Artifact digest `sha256:4b6fc34cca657a50f1d9429872d0e4539e60ee1eee59a6264113fb2e1879e2ef`。
- BusyBox：Run #62 构建成功并上传 `b1-busybox`，Artifact ID `14874457291`，大小 509,361 bytes，digest `sha256:d1ee511a3aeafed17daf88c72514bb59ea40230e8381f4bc9fd870f2db9e0087`。
- 打包：Job 成功；PREPARE-ONLY artifact ID `14873613236`，大小 220,367,249 bytes，digest `sha256:05c8846df9c9a6961ec0d3dd7a52ed9bda7757d8e598bfb25b98b0df6cce0774`。
- Job 结果：Kernel/DTB skipped（按复用输入执行）；BusyBox success；package success。initramfs gzip/cpio 检查、镜像分区与 ext4 检查、JP proper FIT 写入回读校验、最终 SHA256SUMS 校验均在该 Run 中通过。

### 为什么 Run #62 不作为当前 B1 基线验收

Run #58 的 Kernel/DTB 构建日志证明它使用了 2026-11-23 完整 RK35xx seed（blob `dee127c6c644f38426eeb28000d73536084d34a3`），并保留 `CONFIG_BLOCK=y`、`CONFIG_MMC=y`、`CONFIG_USB=y`、`CONFIG_MODULES=y`，关闭 `CONFIG_NET`。因此配置 seed/主要配置方向与基线纠偏一致。

但同一日志也证明构建前仍应用了历史 `0001-kobject_uevent-config-net-n.patch`（patch SHA-256 `2ca7ca9cb355d92e5cfe91fb605df3be9fb847c677e9b54864de2a02887276d9`）。2026-11-23 基线纠偏明确规定该补丁只保留为历史审计材料，B1 应使用未修改的锁定上游源码。故 Run #58 Kernel/DTB 与依赖它的 Run #62 镜像只能作为历史构建证据，不作为当前基线验收产物。

### 已完成的修正

- 2026-11-24 更新 `.github/workflows/build-panther-x2-b1-clean-ram.yml`：移除旧补丁的 dry-run、应用和针对补丁后源码的断言；新增工作区干净检查，确保固定 Linux commit 未被修改；manifest 明确记录 `kobject_uevent_patch=none; pinned upstream source unchanged`。
- 修正提交：`e6d94d2d337fe6caaff1d743aca1aef77451159d`。
- **没有触发新的 Actions。** Kernel/DTB 重新构建待用户手动运行；未重复执行已成功的设备树以外其他验证，也未触碰设备或介质。

### 当前状态与下一步

- 已验证：Run #62 的 CI job 关系、BusyBox 构建、镜像组装和 CI 内部完整性检查。
- 不予当前基线验收：Run #58 复用的 Kernel/DTB（因使用了已废弃补丁）。
- 待验证：按修正后 workflow、未修改上游源码重新构建 Kernel/DTB；之后再用新 Kernel/DTB 重新完成 BusyBox/打包的依赖链。已验证的阶段产物应继续复用，不得无故从头重建。
- 未验证：eMMC pre-Linux 安全门、TF 写入、Panther X2 实机启动、UART shell、B1 运行时行为。
- 安全边界保持不变：PREPARE-ONLY；不写 TF/eMMC，不启动实验固件；项目 A 只围绕板载有线千兆 Ethernet，Wi-Fi/无线和 Bluetooth 永久排除。


## 2026-11-24 Run #63 failure analysis and corrected uevent design

### Run result

- Workflow Run: [#63 / 45294164685](https://github.com/njosd/panther-x2-armbian/actions/runs/45294164685)
- Kernel/DTB job failed at final vmlinux link:
  `lib/kobject_uevent.o: undefined reference to sk_skb_reason_drop`.
- The final configuration had `CONFIG_NET=n`; top-level `Kbuild` contains `obj-$(CONFIG_NET) += net/`, so the networking core providing `sk_skb_reason_drop()` is not linked.
- BusyBox did not start building. The previous workflow condition `!cancelled()` incorrectly allowed the dependent job to run after a failed Kernel job; this has been corrected.
- No new Kernel/DTB, BusyBox or package artifact was produced. No device or storage medium was touched.

### Corrected source-level finding

The failure is caused by the no-network fallback implementation in upstream `lib/kobject_uevent.c`: it calls inline `kfree_skb()`, which calls `sk_skb_reason_drop()`. The normal network implementation also calls `kfree_skb()`, but is compiled only under `CONFIG_NET`.

The in-tree caller identified in the locked source is `drivers/input/keyboard/gpio-button-hotplug.c`; it is selected by `CONFIG_KEYBOARD_GPIO_BUTTON_HOTPLUG`. The B1 fragment explicitly sets this option not set. Its Makefile object is therefore excluded from B1. The no-network stub is not needed by the current B1 configuration.

### Corrected patch and workflow

- Added `scripts/panther-x2-b1/patches/0001-broadcast-uevent-net-only-api.patch`.
- The patch guards the `broadcast_uevent()` declaration, implementation and export with `CONFIG_NET`, removes the no-NET stub, and leaves the normal network implementation—including `kfree_skb(skb)`—unchanged.
- This avoids both the undefined network symbol and the skb leak risk in the old patch. It does not enable `CONFIG_NET`, any network protocol, Ethernet driver, Wi-Fi or Bluetooth.
- The workflow applies the patch only after checking the pinned source checkout is pristine. It checks the patch structure and records the runtime SHA-256 in the source manifest.
- BusyBox now runs only if the Kernel/DTB job succeeded, or if a prior Kernel/DTB Run ID was explicitly supplied for artifact reuse. A failed Kernel build therefore skips BusyBox and package.
- Workflow updates and the new patch have been committed to the project branch. No Actions run was triggered by these commits.

### Remaining validation

The source-level design is corrected, but not yet proven by a successful build. The next user-triggered workflow must rebuild Kernel/DTB from the pinned source with the new patch. Only after that stage succeeds may BusyBox and package proceed. If a later stage alone fails, reuse the successful Kernel/DTB artifact Run ID and resume from that stage.

The current B1 state remains **build not yet validated**. No TF/eMMC writes, no Panther X2 boot and no eMMC safety-gate bypass are authorized by this change.

## Run #64 — malformed compatibility patch (2026-11-24)

Run: `45307203767`  
Failed job: `138153844897` — Build and validate kernel plus DTB.

Observed sequence:
- Toolchain installation completed.
- The exact pinned Linux source commit `aee4e352a15d636cbc484f56819c6e59474dfd9f` was fetched and checked out successfully.
- The job stopped at `git apply --check` before kernel configuration or compilation.
- Exact error: `corrupt patch .../0001-broadcast-uevent-net-only-api.patch:37`.
- Kernel/DTB compilation and artifact upload did not run. BusyBox and package jobs were skipped. No new artifact was produced.

Root cause:
- The second unified-diff hunk header declared line counts that did not match its actual context/addition/deletion lines. This made the patch syntactically corrupt; it was not a source-context mismatch and the linker failure from Run #63 was not reached.

Correction committed on the same branch:
- Corrected the first hunk offset to match the pinned header source.
- Corrected the second hunk offset and its declared old/new line counts to match the pinned source and actual hunk body.
- Rechecked both unified-diff hunk counts against the patch text; both are internally consistent.
- Rewrote `scripts/panther-x2-b1/patches/README.md`, which still described the obsolete historical stub patch and contradicted the current API-only patch.

Current verification boundary:
- Static source review and hunk-count consistency: checked.
- Actual `git apply --check` in Actions: pending; the corrected patch has not yet been run in CI.
- Kernel compile/link, DTB, BusyBox, package artifact and hardware boot: not verified by Run #64.
- No workflow was triggered by the correction, and no storage write or hardware boot was performed.

