# Panther X2 四版本内核与启动资产盘点（2026-11-20）

## 1. 本轮目的

在两条黄金基准（6.1.65、6.1.116）和两条故障线（6.1.174-rk35xx、6.12.81-rk35xx）之间，盘点 Kernel Image、modules、DTB、initramfs、bootloader 与 rootfs 的资产来源、可验证程度和替换边界。

本轮只读取现有仓库报告、归档索引、公开 GitHub Release 元数据及既有实机记录。未下载/运行故障内核，未修改设备或启动配置，未制作补丁。

## 2. 四版本资产矩阵

| 资产层 | 6.1.65 黄金 A | 6.1.116 黄金 B | 6.1.174 故障 A | 6.12.81 故障 B |
|---|---|---|---|---|
| 版本身份 | Armbian 24.2.0 Jammy，原始 Panther X2 镜像 | 实机正常运行的 Ophub 内核 | 最早明确异常的 RK35xx BSP 内核 | 后续异常的 RK35xx BSP 内核 |
| Kernel release | `6.1.65-ophub`（由 BOOT 文件名确认） | `6.1.116-ophub`（实机 uname/启动身份确认） | `6.1.174-rk35xx-ophub` | `6.12.81-rk35xx-ophub` |
| Kernel Image | 原始 IMG BOOT 分区含 `Image`、`vmlinuz-6.1.65-ophub` | 6.1.116 boot 备份归档已保留并校验 | 官方 RK35xx 发布包存在，内层清单尚未核验 | 官方 RK35xx 发布包已校验；boot 子包清单已索引 |
| modules | rootfs 内 `/lib/modules` 尚未提取核对 | `modules-6.1.116-ophub.tar.gz` 已保留并校验 | 官方包有独立发布资产；本项目尚未取得其内层清单 | `modules-6.12.81-rk35xx-ophub` 已索引；GMAC 主链未见模块，与内建配置一致 |
| DTB | 原始 BOOT 分区含 Panther X2 DTB，GMAC 配置已与 6.1.116 交叉核对 | 磁盘 DTB、runtime FDT 已归档 | 候选源码含 Panther DTS；最终构建 DTB 尚未做二进制 provenance 闭环 | 正式 TF DTB 与发布包内 DTB 尚未做 SHA256 同一性核对 |
| initramfs | BOOT 分区含 `uInitrd`、`uInitrd-6.1.65-ophub` | boot 归档保留 | 官方 boot 子包预期包含，但尚未读取其实际清单 | boot 子包已索引，配置文件路径已定位 |
| U-Boot/SPL | 原始 IMG 含 FIT/U-Boot 相关内容；另有原始刷机 MiniLoaderAll 资产 | 旧系统使用 `idbloader.img + u-boot.itb` 文件布局；当前归档未包含旧二进制 | 不能仅凭内核包确定实机启动固件 | TF 启动链另有独立证据；本轮不把它与内核包混为一谈 |
| rootfs | Jammy 原始镜像 root 分区；网络配置由用户报告另行比较 | 现有正常系统 rootfs | 具体实机 rootfs 与 6.1.174 内核组合尚未完全锁定 | Noble/其他现场 rootfs 信息不能替代实际镜像 rootfs 检查 |

## 3. 已核实资产细节

### 3.1 6.1.65 原始镜像

用户本地原始镜像：

- 文件名：`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz`
- gzip 内部 IMG 名：`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img`
- gzip 压缩大小：892,499,345 bytes
- 解压长度：2,969,567,232 bytes
- SHA256：`0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`
- gzip 完整性、GPT 与 BOOT ext4 已验证。

BOOT 分区目录已确认含：
- `Image`
- `vmlinuz-6.1.65-ophub`
- `uInitrd`
- `uInitrd-6.1.65-ophub`
- `dtb/rockchip/rk3566-panther-x2.dtb`
- `armbianEnv.txt`、`boot.cmd`、`boot.scr`

启动环境选择 `rk3566-panther-x2.dtb`；`boot.scr` payload CRC 通过且与 `boot.cmd` 正文一致。原始镜像内 Linux 启动脚本加载 Panther X2 DTB 的配置意图已确认。

**尚缺：** root 分区内 `/lib/modules/6.1.65-ophub` 的实际目录清单、`modules.dep`、内核 config（若有）及其与 BOOT 内 Image 的对应关系。当前只确认 BOOT 文件名和启动配置，不把它们当作模块/配置来源闭环。

### 3.2 6.1.116 正常实机基线

已确认实际运行内核为 `6.1.116-ophub`，设备树为 Panther X2。正常运行状态包括 GMAC 链路、DHCP、局域网 ping 正常，接口错误计数为零。

旧备份中三份内核相关归档的 SHA256 均已校验：

| 归档 | SHA256 |
|---|---|
| `boot-6.1.116-ophub.tar.gz` | `68e991e78c19ecaf96d766a058b9b1149a57efcef5a729fd971edf47808ed6d2` |
| `dtb-rockchip-6.1.116-ophub.tar.gz` | `2c60c79d67fee948689fa3ac17cd834e33553f1c65f03bf852529372ae37d5e5` |
| `modules-6.1.116-ophub.tar.gz` | `d8056b6abe03cdee392e56e4d5cf20ccfd5d1f577d579fbf29923cfba6a1b529` |

这些是已存在的旧版基线资产，不应要求用户重新采集。既有归档目录核对未发现 U-Boot 二进制，故不能从这些归档推导旧 U-Boot 哈希。

### 3.3 6.1.174-rk35xx 故障版本

Ophub `kernel_rk35xx` Release 官方自动资产：

- `6.1.174.tar.gz`
- asset ID：`731478275`
- size：135,267,299 bytes
- SHA256：`49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a`
- 创建时间：2026-11-10 13:09:30Z
- 对应 Actions run #296（ID `42812333074`）上传步骤时间窗口吻合。

另有 `deb-6.1.174.tar.gz`（asset ID `731478525`），不是主内核包。Release 中也存在手动上传的 Flippy 变体，不能与官方自动包混用。

源码候选 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` 为高置信度构建来源候选，但未取得 workflow 实际 inputs 和 source_hash 输出，尚非逐字节构建证明。

**尚缺：** 对主包内部 boot/modules/dtb/header 子包的实际目录清单、内部 SHA256 校验、config 和模块索引；以及现场曾安装的具体资产是否就是该官方自动包的确认。

### 3.4 6.12.81-rk35xx 故障版本

Ophub `kernel_rk35xx` Release：

| 资产 | ID | 大小 | SHA256 |
|---|---:|---:|---|
| `6.12.81.tar.gz` | 743358387 | 141,437,450 | `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b` |
| `deb-6.12.81.tar.gz` | 743358636 | 92,782,935 | `e07d967c2a4d54aee3e910db414c100e01843db2a5b5e49e44d13942aec5e6bc` |
| `6.12.81-rk35xx-flippy-2611b.tar.gz` | 743329557 | 119,018,056 | `a5b0bc5d3c8311cee472c105e5ee2d1c9e6395a94efb4488253a0faae132d064` |

本项目已对官方主包完成外层 SHA256、gzip/tar 完整性核验；已索引 boot、dtb-rockchip、modules 等内部归档，并提取最终内核 config。最终 config 中：
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_STMMAC_PLATFORM=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_PHYLIB=y`
- `CONFIG_REALTEK_PHY=y`
- `CONFIG_MDIO_BUS=y`
- `CONFIG_OF_MDIO=y`

modules 包未发现 STMMAC / Rockchip DWMAC / Realtek PHY 主链模块，与这些驱动内建配置一致。该配置审计已完成，不重复。

源码候选为 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，与资产时间线吻合，但缺少构建 run 输入/日志的精确锁定证据。

## 4. 四版本共同信息与主要差异

### 已确认的共同正常线

- 6.1.65 和 6.1.116 都是 Panther X2 上的正常参考。
- 两者 Linux GMAC1 设备树语义高度一致：RGMII、clock input、TX/RX delay 0x30/0x10、PHY address 0、GMAC1 M0 pin groups 和 125MHz clock parent 设计一致。
- 这意味着当前没有证据支持先替换 DTB。

### 故障线的共同特征

- 6.1.174 和 6.12.81 均来自 Ophub RK35xx BSP 内核资产系列，内核 release 字符串带 `-rk35xx-ophub`。
- 两者的实际 TX 路径静态源码审计已完成；没有发现可解释普通 RGMII TX 回归的有效 STMMAC 核心共同差异。
- P4 pinctrl 首 pin 错误处理差异曾被确认，但 Panther 正常 MMIO regmap 路径缺乏触发该错误的现实证据，已降为极低优先级理论候选。
- 6.12.81 GMAC 主链为内建，不依赖加载独立网卡 .ko。

## 5. 替换边界判断

当前不应尝试“只换一个 .ko”：
- 6.12.81 的 GMAC 主链为 built-in，模块包没有对应驱动模块。
- 6.1.65 的 modules 与 Image 对应关系尚未闭环。
- 不同 kernel release 的模块 ABI/vermagic 不能默认兼容。

当前也不应直接只替换 6.1.65/6.1.116 的 Image 到故障版本：
- 需要先确认内核配置、built-in 驱动集合、模块 ABI、initramfs 依赖和启动参数；
- 不同版本的 `/lib/modules/<release>` 必须与内核映像匹配；
- 只替换 Image 的失败可能来自模块/启动依赖不匹配，不能作为 GMAC 根因判断。

因此，未来的最小受控实验必须先确认 GMAC 主链的 built-in 状态和依赖闭包，再决定“只替换 kernel Image”是否是有效单变量实验；若不满足条件，则应把匹配的 kernel + modules + DTB/initramfs 定义为一个版本化内核套件，不能拆开混用。

## 6. 当前最小缺口与下一步

下一步只补齐 6.1.65 原始 IMG 的 rootfs 内核资产索引，不重新检查 DTB 或启动脚本：

1. 确认 `/lib/modules/6.1.65-ophub` 是否存在及其目录清单；
2. 读取该目录的 `modules.dep`、`modules.builtin`、`modules.order`（若存在）；
3. 检查 BOOT 或 rootfs 中是否存在 `config-6.1.65-ophub`；
4. 如果原始 Image 启用了 IKCONFIG，尝试只读提取内嵌 config；不修改镜像；
5. 记录 Image、uInitrd、DTB、modules 的版本匹配关系。

补齐后再与 6.1.116 的已归档 config/modules 及 6.1.174、6.12.81 官方包内容比较。对 6.1.174 只需补做其官方主包内层清单/config/modules 索引；不重新进行源码 TX 审计。

## 7. 操作边界

所有后续工作继续只读。没有明确授权前：
- 不启动故障内核；
- 不刷写 TF/eMMC；
- 不替换 Image、modules、DTB、initramfs 或 U-Boot；
- 不修改设备配置；
- 不进行危险 MMIO/MDIO 读取或写入。
