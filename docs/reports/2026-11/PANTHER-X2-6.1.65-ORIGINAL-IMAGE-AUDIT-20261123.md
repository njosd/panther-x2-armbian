# Panther X2 原始 6.1.65 镜像静态审计报告

- 审计日期：2026-11-22 至 2026-11-23
- 目标设备：Panther X2 / RK3566
- 原始镜像：\`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz\`
- 审计性质：离线、只读、静态文件审计
- 状态：**阶段性审计已完成；完整启动资产闭包仍待补齐**
- 项目 A 关系：历史 6.1.65 基线资料；不改变项目 A 当前锁定的 6.18.63 源码自建 B1 路线
- 范围限制：不开展 GMAC/MDIO/PHY 故障根因调查，不制作驱动补丁；Wi-Fi/无线网络与蓝牙永久排除出项目 A

## 1. 结论摘要

本轮已完成原始镜像布局、启动配置、boot script、Panther X2 DTB 文件身份、Kernel 配置与 built-in 驱动清单、模块清单、用户空间/网络工具清单及项目范围排除项的阶段性审计。

关键结论：

1. 原始 gzip 文件的 SHA-256 和 gzip 完整性检查结果已由用户本机提供；gzip 内部原始文件名记录为 \`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img\`。
2. Kernel 配置明确启用 \`CONFIG_STMMAC_ETH=y\`、\`CONFIG_STMMAC_PLATFORM=y\`、\`CONFIG_DWMAC_ROCKCHIP=y\`，相关对象列入 \`modules.builtin\`。此前因模块文件清单未见独立 Rockchip GMAC 模块而产生的“驱动可能缺失”疑点已排除。
3. 原始 boot 配置指向 \`rockchip/rk3566-panther-x2.dtb\`；DTB 文件存在，大小与 SHA-256 已记录。
4. 原始 \`boot.scr\` 的 uImage header/data CRC 检查正确，其 payload 与 \`boot.cmd\` 正文一致。
5. rootfs/initramfs-tools manifest 中的 BusyBox helper、systemd 链接等信息，不等于真实 \`uInitrd\` cpio 内容；实际 uInitrd 尚未解包审计。

**本次并非所有文件均已完整审计。** 仍需从现有 Dropbox 阶段包提取两个关键二进制：\`vmlinuz-6.1.65-ophub\` 和 \`uInitrd-6.1.65-ophub\`。尤其 uInitrd 内部的真实 \`/init\`、早期用户空间及依赖，是完成启动资产闭包判断的必要证据。无需重新运行整个提取脚本，也无需重新上传大阶段包。

## 2. 原始输入身份与镜像布局

### 2.1 原始压缩包

- 压缩大小：892,499,345 bytes（约 851.2 MiB）
- gzip 内部记录的未压缩大小：2,969,567,232 bytes
- gzip 内部原始文件名：\`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img\`
- gzip header 时间：2023-12-07 05:18:54（Unix 时间）
- 用户本机计算的 SHA-256：\`0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea\`
- 用户报告 \`gzip -t\`：通过

gzip header 支持内部镜像文件名及 2023-12-07 构建标识，但不能单独证明上游官方发布身份。当前未取得可独立比对的上游官方 SHA-256。gzip 完整性通过只证明压缩流可完整解压，不证明内容与发布者原件一致。

### 2.2 分区布局

| 项目 | 结果 |
|---|---|
| 展开镜像大小 | 约 2.8 GiB |
| Boot 分区 | ext4，267,386,880 bytes |
| Root 分区 | ext4，2,683,305,984 bytes |
| Boot UUID | \`a5110630-ef2e-4941-9a22-15784ef687a5\` |
| Root UUID | \`ddcbfa1d-95e7-4863-97c8-ec9b7767968b\` |

以上为用户本机只读提取结果；本轮未重新计算原始镜像与展开镜像 SHA-256。

## 3. 启动配置与启动脚本

### 3.1 armbianEnv.txt

已核对的关键字段：

\`\`\`ini
fdtfile=rockchip/rk3566-panther-x2.dtb
rootdev=UUID=ddcbfa1d-95e7-4863-97c8-ec9b7767968b
rootfstype=ext4
rootflags=rw,errors=remount-ro
earlycon=on
console=both
consoleargs=console=ttyS02,1500000 console=tty0
overlay_prefix=rk3566
overlays=
user_overlays=
extraboardargs=net.ifnames=0 max_loop=128
\`\`\`

配置声明使用 Panther X2/RK3566 DTB 路径，并将 rootfs 指向独立 ext4 root 分区；这不证明目标设备实际执行过该镜像中的配置。

### 3.2 boot.cmd / boot.scr

- \`boot.cmd\`：3,310 bytes。
- \`boot.scr\`：3,382 bytes，legacy U-Boot script uImage。
- header CRC：\`0xA2C2FDFA\`，检查正确。
- data CRC：\`0xB7C261DC\`，检查正确。
- 提取 script SHA-256：\`0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a\`。
- script payload 去除 8-byte uImage header 后，与 \`boot.cmd\` 的 3,310-byte 正文一致。

启动脚本读取 \`armbianEnv.txt\`，设置 bootargs，加载 \`uInitrd\`、\`Image\` 和 \`\${prefix}dtb/\${fdtfile}\`，处理可选 overlays/fixups，最后执行 \`booti\`。

\`extlinux/extlinux.conf\` 不存在；只有 \`extlinux.conf.bak\`，不能将备份配置描述为实际生效配置。

### 3.3 符号链接提取缺口

- \`Image\` → \`vmlinuz-6.1.65-ophub\`
- \`uInitrd\` → \`uInitrd-6.1.65-ophub\`
- \`dtb-6.1.65-ophub\` → \`dtb\`

0.3.4 提取报告将上述 3 个符号链接记为 \`symlink path collision\`。这是提取器处理符号链接的缺陷，不是文件系统损坏证据；但必须核验目标文件本身，才能关闭缺口。

## 4. Kernel 配置与 built-in 驱动审计

用户从现有阶段包提取并上传 \`config-6.1.65-ophub\` 与 \`modules.builtin\`，组成 \`kernel-config-evidence.zip\`。已读取两份文件。

关键配置：

| 配置 | 值 | 静态含义 |
|---|---:|---|
| \`CONFIG_STMMAC_ETH\` | \`y\` | STMMAC 主驱动编译进内核 |
| \`CONFIG_STMMAC_PLATFORM\` | \`y\` | STMMAC 平台驱动编译进内核 |
| \`CONFIG_DWMAC_ROCKCHIP\` | \`y\` | Rockchip DWMAC 支持编译进内核 |
| \`CONFIG_DWMAC_GENERIC\` | \`y\` | Generic DWMAC 支持编译进内核 |
| \`CONFIG_PHYLINK\` | \`y\` | PHYLINK 编译进内核 |
| \`CONFIG_PHYLIB\` | \`y\` | PHYLIB 编译进内核 |
| \`CONFIG_ROCKCHIP_PHY\` | \`y\` | Rockchip PHY 驱动编译进内核 |
| \`CONFIG_MDIO_BUS\` | \`y\` | MDIO bus 支持编译进内核 |
| \`CONFIG_OF_MDIO\` | \`y\` | OF/MDIO 支持编译进内核 |
| \`CONFIG_BLK_DEV_INITRD\` | \`y\` | 内核支持 initrd/initramfs |
| \`CONFIG_RD_GZIP\` | \`y\` | 支持 gzip initramfs/initrd 解压 |
| \`CONFIG_DEVTMPFS\` | \`y\` | devtmpfs 支持编译进内核 |
| \`CONFIG_IKCONFIG\` | \`y\` | 内核配置归档支持启用 |
| \`CONFIG_IKCONFIG_PROC\` | \`y\` | 可通过 proc 暴露内核配置 |

\`modules.builtin\` 明确列出：

\`\`\`text
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac.ko
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac-platform.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-generic.ko
kernel/drivers/net/phy/rockchip.ko
kernel/drivers/net/phy/phylink.ko
kernel/drivers/net/phy/libphy.ko
kernel/drivers/net/phy/realtek.ko
kernel/drivers/net/mdio/of_mdio.ko
\`\`\`

这些路径位于 \`modules.builtin\`，表示相应对象编译进内核，不是运行时必须加载的独立模块。

**结论：** 6.1.65 内核配置包含 Rockchip DWMAC/STMMAC 及相关 PHY/MDIO 支持。此前从 06 模块文件清单未发现独立 Rockchip DWMAC/STMMAC \`.ko\` 而产生的驱动缺失疑点，已由 config 与 built-in 清单排除。此结论只描述构建配置，不代表 Panther X2 实机启动、驱动 probe、链路或网络功能通过。

## 5. Panther X2 DTB 文件

- 文件：\`dtb/rockchip/rk3566-panther-x2.dtb\`
- 大小：111,351 bytes
- SHA-256：\`d03ec12df0d69bfa0f0ab5ac462a8fffd8ae5d1c512032ff9468df89248d289f\`
- 本地启动分区 inode：50；regular file，0644
- 文件系统记录时间：2023-12-07 13:18:46

镜像启动配置引用该路径，独立 DTB 阶段包中也存在同尺寸文件。存在性与哈希已记录；这不等于已证明 DTB 与目标设备硬件修订完全匹配，也不等于实机加载成功。

## 6. Initramfs / 用户空间清单

05 manifest 共 247 条数据项，其中 132 个符号链接，其余为普通文件。清单可见 \`usr/lib/initramfs-tools/bin/busybox\`（337,968 bytes）及 \`sbin/init\` 指向 systemd 等内容。

**边界：** 05 manifest 是 rootfs/initramfs-tools 相关文件清单，不是解包后的 \`uInitrd\` cpio 清单。不能据此断言真实 uInitrd 的 init 入口为 systemd，也不能确认其依赖闭包、设备节点、挂载逻辑或独立启动能力。

实际 uInitrd 解包后仍需核验：外层格式/header、压缩算法、cpio 成员、\`/init\` 是否存在及权限、BusyBox 和库依赖、是否依赖 systemd/udev/模块/存储设备/持久化 rootfs，以及是否带入 B1 不需要的组件。

## 7. Kernel 与模块清单

- 03 Kernel manifest：21 条数据项；\`vmlinuz-6.1.65-ophub\` 大小 33,858,048 bytes；\`Image\` 是指向它的符号链接。
- 06 modules manifest：4,560 条数据项，其中 4,547 个普通文件、13 个符号链接。
- 存在 \`/lib/modules\` 与 \`/usr/lib/modules\` 两套重复目录布局及 modules.dep、modules.alias、modules.builtin 等元数据。
- 可见 Realtek \`r8125.ko\`、\`r8168.ko\`。
- 未发现独立 Rockchip DWMAC/STMMAC 模块文件，但第 4 节已确认其为 built-in。

对于 B1，当前路线明确不启用 Kernel modules、不打包 \`/lib/modules\`，因此无需把 202 MiB 模块包整体复制进新系统。模块包作为原始镜像证据保留。

## 8. 网络工具与项目范围隔离

07 network-userspace 包清单包含 \`ip\`、\`bridge\`、\`tc\`、\`ethtool\`、\`dhclient\`、\`ping\`、\`ss\`、\`curl\`、\`wget\`。这只确认文件存在，不代表其动态库依赖、静态属性或独立 initramfs 可运行性已验证。项目 A B1 不预置网络工具；后续阶段达到验收门槛后再逐项引入。

08 project-scope-exclusions 索引共 1,865 项，但自动分类存在误判（例如 \`logrotate.d/btmp\` 被宽泛规则纳入），不能视为精确无线/蓝牙组件清单。项目 A 已将 Wi-Fi/无线网络与蓝牙永久排除，不继续审计或测试其功能。

## 9. 提取器失败项与可信度限制

用户本机运行 \`panther_x2_audit_pack.py 0.3.4\` 的报告：

- Source entries：22,548
- Failed files：16
- Special objects not materialized：0
- Wireless/BT inventory entries：1,865

16 条失败包括：3 条启动分区符号链接（\`Image\`、\`uInitrd\`、\`dtb-6.1.65-ophub\`）；5 条 module 提取失败记录（\`xt_dscp.ko\` 因重复路径出现两条）；8 个 Linux netfilter 头文件。

汇总中的 “special objects not materialized: 0” 与 symlink 失败记录不一致，不能据此声称提取无损。symlink collision 不等于源镜像损坏；模块和头文件失败项是否重要，应按实际依赖判断。当前 B1 启动资产的两个目标二进制仍需单独提取和校验。

## 10. Dropbox 证据保留清单

用户明确要求：**本项目结束前，现有 6.1.65 原始镜像与阶段审计文件继续保留在 Dropbox，不删除、不移动、不覆盖。** Git 只保存报告和必要的小型文本证据，不将 851 MiB 原始镜像或 202 MiB 模块包复制进仓库。

### 10.1 原始镜像

| 文件 | Dropbox file ID | 大小 |
|---|---|---:|
| \`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz\` | \`id:9qHOnx-HLYoAAAAAAAAABw\` | 892,499,345 bytes |

### 10.2 八个阶段包

| 阶段包 | Dropbox file ID | 体积 | 用户提取报告 SHA-256 |
|---|---|---:|---|
| \`01-image-layout.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAACw\` | 1.0 MiB | \`5f7962adff81f3b2b129dafc5ae270f58dfa946588c88d836232f6a06f1129e0\` |
| \`02-boot-chain.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAACg\` | 11.6 KiB | \`6de2ed2c8d72ab51258aae900b972a3cea454f254fba62144271f75d219175c3\` |
| \`03-kernel.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADQ\` | 13.3 MiB | \`02320ca87cf9f87a296d6de7c703672b9c0e81d02f208a8b7a621bc0db8c86b7\` |
| \`04-device-tree.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADA\` | 2.2 MiB | \`b09451c53393353de55cbd4d7074eca593fd64a21ff9bc88cab223a9cdd6f3af\` |
| \`05-initramfs-userspace.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADg\` | 35.1 MiB | \`9dd82ac5d97e97c4fc7a1746423412b5e627343f6854c071092174fcdb1c6a08\` |
| \`06-modules-dependencies.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAADw\` | 202.1 MiB | \`a65fe3442741970f2a094c5853ef05e1a16db30ebd3fd77953e07621d24eab86\` |
| \`07-network-userspace.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAAEA\` | 3.7 MiB | \`66d300a64b4987220709833b174190d8f508dc2d4d1bf1c20d0bbea9ea43877\` |
| \`08-project-scope-exclusions.tar.gz\` | \`id:9qHOnx-HLYoAAAAAAAAAEQ\` | 18.8 KiB | \`b9d0093273fec3a6124811652fb4d34025718a5a450f4967e8d6d6076352d77\` |

上述 SHA-256 来自 0.3.4 用户本机提取报告，本轮未重新逐包复算。

### 10.3 附加证据

- \`FINAL-REPORT.txt\`：\`id:9qHOnx-HLYoAAAAAAAAACA\`
- \`UPLOAD-SHA256SUMS.txt\`：\`id:9qHOnx-HLYoAAAAAAAAACQ\`
- \`kernel-config-evidence.zip\`：\`id:9qHOnx-HLYoAAAAAAAAAFQ\`，包含 \`config-6.1.65-ophub\` 与 \`modules.builtin\`
- 单独上传的 manifest：\`03-kernel-MANIFEST.tsv\`、\`05-initramfs-userspace-MANIFEST.tsv\`、\`06-modules-dependencies-MANIFEST.tsv\`

## 11. 尚需提取的文件与完成条件

### 11.1 B1 启动资产闭包必须补齐的两个文件

只需从现有阶段包提取以下两个目标文件，不必重新运行全量脚本：

1. \`vmlinuz-6.1.65-ophub\)：来自 \`03-kernel.tar.gz\`，manifest 记录大小 33,858,048 bytes。用于核验实际 Kernel 镜像类型、内嵌版本/build 字符串、文件哈希，并与 config/modules 元数据对应。
2. \`uInitrd-6.1.65-ophub\`：来自 \`05-initramfs-userspace.tar.gz\`。用于检查 uImage/initramfs header、压缩算法、cpio 内容、真实 \`/init\` 与早期用户空间依赖，是当前最重要的未审计启动资产。

请从原 tar 包按精确成员路径提取这两个目标文件，单独上传 Dropbox；上传后核对文件非空、SHA-256 和 tar 成员路径。不要只上传符号链接本身。

### 11.2 当前不需要提取的内容

- 完整 202 MiB \`06-modules-dependencies.tar.gz\` 不需要再上传或整体解压进 B1 构建环境；B1 明确不启用模块系统和 \`/lib/modules\`。未来只有遇到明确问题才提取其中小文件。
- 07 包网络工具依赖审计属于 B2/B3 阶段，不进入 B1。
- 16 条失败中的非启动必需 netfilter headers 与模块，不为追求“零失败”而扩大当前范围。
- 08 包无线/蓝牙分类误判不应成为项目 A 新任务；这些功能永久排除。

### 11.3 完成定义

本报告完成“镜像布局、启动配置、DTB 文件身份、Kernel 配置/内建驱动、模块与用户空间清单”的阶段性静态审计。补齐 Kernel 实际二进制和真实 uInitrd 内容，并完成哈希/结构核验后，才可将 6.1.65 启动资产静态闭包标记为完成。即使静态闭包完成，也不等于 Panther X2 实机启动或网络功能通过。

## 12. 对项目 A B1 的结论

- 6.1.65 是历史原始镜像审计对象，不是项目 A 当前 B1 Kernel 构建目标。
- B1 仍按仓库既定方案，从锁定的 Linux 6.18.63 源码 commit 自建 Kernel、clean-test DTB、gzip initramfs 和静态 BusyBox。
- 不直接复用 6.1.65 发行版 Kernel、uInitrd、rootfs、模块或网络用户空间作为 B1 组件。
- 6.1.65 的网络/STMMAC/DWMAC 配置不符合 B1 的 \`CONFIG_NET=n\`、无 Ethernet driver、无 modules 的干净基线要求。
- 不因 6.1.65 启用了相关驱动而开展 GMAC 根因调查或制作补丁。
- Wi-Fi/无线网络、蓝牙及其控制器/驱动/固件/协议/用户空间继续永久排除。

## 13. 归档纪律

- 原始镜像、8 个阶段包和附加证据文件继续保留在 Dropbox，直至用户明确宣布项目结束或另行要求。
- 不删除、不移动、不覆盖 Dropbox 原始包和阶段包。
- Git 仓库只保存本报告及必要的小型文本证据，不加入大型原始镜像或 modules 压缩包。
- 后续提取只针对第 11 节明确列出的文件，不重复已完成的镜像布局、boot script CRC、DTB 文件存在性和 Kernel 配置核验。
- 结论必须区分用户本机报告、已读取文件静态证据、待验证事项和实机运行证据。
