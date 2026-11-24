# Panther X2 B2-0：四版本内核主链 built-in / modules 与启动资产闭包对照（2026-11-24）

## 1. 本轮位置与范围

本报告承接 B2-0 已有的四版本资产矩阵和 2026-11-24 新取得的 6.1.174 原始 Actions job log。

本轮只完成 B2-0 既定子项：对照 6.1.65、6.1.116 两条黄金基线，以及 6.1.174、6.12.81 两条故障线的：
- Kernel release 与来源证据等级；
- Panther X2 GMAC / MDIO / PHY 主链的 Kconfig built-in 状态；
- modules 包中是否存在可单独替换的 GMAC 主链 .ko；
- initramfs 与内核模块的打包/依赖边界；
- 是否存在可作为第一轮单变量替换的独立驱动模块。

不重复 DTB、RGMII delay、STMMAC TX、PHY workaround、pinctrl、CRU 时钟复位等已结项源码专题。不启动故障内核，不访问 Panther X2，不读取 MMIO/MDIO，不发包/抓包，不修改设备或存储介质。

## 2. 四版本证据矩阵

| 项目 | 6.1.65 黄金 A | 6.1.116 黄金 B | 6.1.174 故障 A | 6.12.81 故障 B |
|---|---|---|---|---|
| Kernel release | `6.1.65-ophub` | `6.1.116-ophub` | `6.1.174-rk35xx-ophub` | `6.12.81-rk35xx-ophub` |
| 参考性质 | 用户保存的原始完整 Armbian IMG | Panther X2 实机已验证正常运行基线 | 最早有明确实机异常证据的 RK35xx BSP 版本 | 后续实机持续异常的 RK35xx BSP 版本 |
| Kernel 二进制证据 | Image SHA-256 已直接复核 | boot 归档、运行 release 和 Image SHA-256 已归档 | 官方自动包及内部 boot 子包已校验 | 官方自动包、现场运行 Image SHA-256 与 build timestamp 已归档 |
| 源码构建身份 | 精确 Actions run/checkout SHA 未证实；源码强候选不等于构建证明 | 精确构建 source SHA 尚未闭环；已有源码候选仅作参考 | **已由原始 run #296 job log 直接确认**：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` | 已由 run #43405957386 日志锁定：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` |
| STMMAC / platform | `=y` | `=y` | `=y` | `=y` |
| Rockchip DWMAC | `CONFIG_DWMAC_ROCKCHIP=y` | `=y` | `=y` | `=y` |
| PHYLIB / Realtek PHY | `PHYLIB=y`、`REALTEK_PHY=y` | 两者 `=y` | 两者 `=y` | 两者 `=y` |
| MDIO / OF-MDIO | `MDIO_BUS=y`、`OF_MDIO=y` | 两者 `=y` | 两者 `=y` | 两者 `=y` |
| 主链形态 | built-in | built-in | built-in | built-in |
| 独立 GMAC 主链 .ko | 未见；模块清单中的 Realtek r8125/r8168 是独立 PCI/平台网卡驱动，不是 RTL8211F PHY 或 Rockchip DWMAC 主链 | 配置为 `=y`，不是模块构建形态 | modules 套件索引未发现 STMMAC / DWMAC Rockchip / Realtek PHY 主链独立模块 | modules.builtin 列出 built-in 主链；官方 modules 包未见 GMAC 主链独立模块 |
| initramfs / boot 资产 | 原始 IMG BOOT 含 Image、uInitrd、Panther DTB；真实 uInitrd 为 initramfs-tools，含 386 个 .ko | 独立 boot / DTB / modules 归档已校验；boot 归档含 initrd 资产 | 官方 release 外层包含 boot、DTB、modules、header 内层套件；boot 含 config、vmlinuz、initrd.img、uInitrd、System.map | 官方发布包有 boot、DTB、modules 套件；现场 UART 已证实内核成功解包 gzip initramfs |
| 资产来源边界 | 用户原始镜像 SHA-256 已记录；不证明历史实机当年实际执行的每个启动阶段二进制 | 实机正常行为已验证；旧 U-Boot 历史二进制身份与 kernel 源码精确 commit 仍有边界 | run #296 证明自动构建输入；不等于历史实机安装文件逐字节 hash 闭环 | run #43405957386 与 build timestamp、源码和配置对应；设备当前 Image 的逐字节身份仍以现场哈希记录为准 |

注：本表仅列与 Panther X2 GMAC/MDIO/PHY 主链有关的关键配置，不是四份完整 `.config` 的逐行 diff。不同版本的其他网络、DMA、IOMMU、调试、测试选项仍须按对应专题证据解释，不能从本表推导为完全相同。

## 3. 6.1.65 原始镜像：模块清单的直接核验补充

此前 6.1.65 原始镜像报告已确认：
- 实际 Kernel Image SHA-256：`d11b0c781a8ac0ffc153ff60e1b1bd88a926afd8f810dd13896d2f0ea16e8bef`；
- 从该 Kernel 二进制内嵌 IKCONFIG 成功提取配置；
- `CONFIG_STMMAC_ETH=y`、`CONFIG_STMMAC_PLATFORM=y`、`CONFIG_DWMAC_ROCKCHIP=y`、`CONFIG_PHYLINK=y`、`CONFIG_PHYLIB=y`、`CONFIG_ROCKCHIP_PHY=y`、`CONFIG_MDIO_BUS=y`、`CONFIG_OF_MDIO=y`；
- `modules.builtin` 明确列出 stmmac、stmmac-platform、dwmac-rk、dwmac-generic、phylink、libphy、realtek、of_mdio 等 built-in 对象。

本轮进一步只读读取 Dropbox 中已有的 `06-modules-dependencies-MANIFEST.tsv`（662,037 bytes），没有重新解压 202 MiB 模块阶段包。清单显示：
- `/lib/modules/6.1.65-ophub` 与 `/usr/lib/modules/6.1.65-ophub` 两套路径均有记录；
- 存在 `mdio-bitbang.ko`、`mdio-gpio.ko`、`mdio-ipq4019.ko`、`mdio-ipq8064.ko`、`mdio-mvusb.ko` 等其他 MDIO 驱动模块；
- 未发现 `stmmac.ko`、`stmmac-platform.ko`、`dwmac-rk.ko`、`dwmac-rockchip.ko`、`phylink.ko`、`libphy.ko`、`realtek.ko` 或 `of_mdio.ko` 作为独立可加载文件；
- 清单中有 `r8125.ko` 与 `r8168.ko`，它们是 Realtek Ethernet MAC/网卡驱动，不是 RTL8211F PHY 驱动，不能混为一谈。

这与 Kernel 内嵌 IKCONFIG 和 `modules.builtin` 证据一致：Panther X2 使用的 STMMAC/Rockchip DWMAC/PHYLIB/Realtek PHY/OF-MDIO 主链由内核 built-in 提供，而不是依靠运行时加载一个 GMAC .ko。

6.1.65 真实 uInitrd cpio 中另有 386 个 .ko 文件；这是 initramfs 自身包含的模块子集，不代表完整 rootfs modules 包的全部内容，也不改变 GMAC 主链 built-in 的结论。

## 4. 6.1.116 正常基线：配置证据闭环

既有 6.1.116 完整基线报告记录：
- 实际运行内核为 `6.1.116-ophub`，网络双向通信正常；
- 已归档完整 `kernel.config`；
- 实际配置与 Ophub general `config-6.1` 模板 7,677 个符号全量比较，差异为 0；
- `CONFIG_STMMAC_ETH=y`、`CONFIG_STMMAC_PLATFORM=y`、`CONFIG_DWMAC_ROCKCHIP=y`、`CONFIG_DWMAC_GENERIC=y`、`CONFIG_MDIO_BUS=y`、`CONFIG_PHYLIB=y`、`CONFIG_PHYLINK=y`、`CONFIG_ROCKCHIP_PHY=y`；
- boot、DTB、modules 三个专用归档均已保存并校验 SHA-256。

因此，6.1.116 正常线与三条其他版本在 Panther GMAC 主链是否 built-in 这一关键属性上相同。其精确 kernel source commit 仍未由原始 build run 日志锁定；这不影响已归档运行时配置与正常行为作为黄金基线使用。

## 5. 6.1.174 原始构建来源补齐

2026-11-24 已直接读取 Ophub 原始 Actions run #296 / job #129816642520 的完整 job log，确认实际值：

- `kernel_source=ophub/linux-6.1.y-rockchip`
- `kernel_version=6.1.y`
- `kernel_auto=true`
- `kernel_sign=-rk35xx-ophub`
- `kernel_config=kernel-config/release/rk35xx`
- `source_hash=c2f148dece4b67ebd30aefad1bdd1990f41e5633`

日志在 source-hash step、cache、compile、upload 等后续步骤持续记录同一 source hash。故原始 6.1.174 自动构建源码身份已从“高置信度候选”升级为“由原始 Actions job log 直接验证”。

完整补充报告：
`PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md`

## 6. 6.12.81 故障版本：既有证据复用

不重复 6.12.81 的配置和模块审计。既有记录已确认：
- 原始运行版本：`6.12.81-rk35xx-ophub`；
- 对应 Actions run：`43405957386`；
- kernel source：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；
- 构建使用 `kernel-config/release/rk35xx/config-6.12`，相关 config blob SHA-1 `966f4b6ac7c0ad59179d6ae272423500601fab07`；
- 关键配置包括 `CONFIG_STMMAC_ETH=y`、`CONFIG_STMMAC_PLATFORM=y`、`CONFIG_DWMAC_ROCKCHIP=y`、`CONFIG_DWMAC_ROCKCHIP_TOOL=y`、`CONFIG_PHYLINK=y`、`CONFIG_PHYLIB=y`、`CONFIG_REALTEK_PHY=y`；
- 实际运行配置与已锁定正式模板的关键网络、STMMAC、DWMAC、DMA/IOMMU 项吻合；
- 官方 modules.builtin 与 modules 包审计确认 GMAC 主链 built-in，无可独立替换的 GMAC 主链 .ko；
- 实机 UART 已直接证明内核成功解包 gzip initramfs。

`CONFIG_DWMAC_ROCKCHIP_TOOL=y` 是 6.12 构建中值得记录的诊断工具配置差异，但它被编入 Rockchip DWMAC 驱动构建，不构成一个可跨版本独立替换的 GMAC .ko；已有报告也确认它与普通 TX 提交主路径无直接等价关系。不得仅凭此配置差异认定为故障根因或替换候选。

## 7. 四版本对照结论

### 7.1 已验证结论

1. 四个版本的 Panther X2 GMAC 主链均由 built-in 配置提供：STMMAC、STMMAC platform、Rockchip DWMAC，以及 PHYLIB/Realtek PHY/MDIO 关键支持。
2. 6.1.65 的原始 Kernel 内嵌配置和完整 modules manifest 相互印证；本轮无需解压完整 202 MiB 模块包。
3. 6.1.116 正常线的完整 kernel.config 已与对应 general config 模板做 7,677 个符号全量比较，差异为 0。
4. 6.1.174 官方包 modules 套件没有 GMAC 主链可加载模块；原始 run #296 的实际 source_hash 已闭环。
5. 6.12.81 同样是 built-in 主链，且其构建源码和配置来源已有原始 Actions 日志证据。
6. 因此，“从正常 6.1.116 单独提取一个 STMMAC / Rockchip DWMAC / Realtek PHY .ko，替换到 6.1.174 或 6.12.81”不是有效实验方案；跨 kernel release 混用其他 .ko 也不能绕过 ABI/依赖闭包问题。

### 7.2 尚未验证或不能扩大解释的部分

- 6.1.116 的精确构建 source commit 仍未闭环。
- 6.1.65 原始构建的精确 Actions run / checkout SHA 仍未闭环。
- 6.1.174、6.12.81 的历史实机安装文件是否逐字节等于官方自动资产，仍需现场安装文件哈希才能证明；run/source provenance 本身不等于安装文件 hash。
- 本轮不是四份完整 `.config` 的逐符号交叉 diff；未列出的配置差异不能推定相同。
- 内核配置 built-in 只能证明驱动编译形态，不证明每个版本的驱动在硬件上 probe、链路或网络功能均成功。

### 7.3 第一轮软件替换候选判断

**当前未找到符合门槛的独立 GMAC 主链模块替换候选。**

要进入单变量软件替换，必须另行找到：
- 两条黄金线共同具备、两条故障线共同缺失或行为不同的明确软件变量；
- 该变量可以独立定义，且不依赖跨版本混用内核 ABI；
- 其依赖闭包、配置来源和回退方式可验证。

若差异位于 built-in 内核驱动，则替换单位必须是经过匹配验证的内核套件或受控重建产物，而不能假定存在可直接替换的单个 .ko。当前报告不指定任何内核套件替换、不授权实机 A/B。

## 8. B2-0 本子项状态

**结项：四版本 GMAC 主链 built-in / modules 分布与主要启动资产闭包对照。**

本子项确认：四版本 GMAC 主链均为 built-in；不存在可作为首轮单变量替换的 GMAC 主链独立模块。已完成的 6.1.65、6.1.116、6.1.174、6.12.81 证据均按原报告复用，没有要求用户重做已完成测试。

这不代表 B2-0 整体完成，也不代表 GMAC TX 故障根因已定位。后续仍严格按 B2-0 原计划剩余子项推进；只有 B2-0 完成后才进入下一阶段，不提前跳到 B2-1。

## 9. 证据来源

- [6.1.65 原始镜像静态审计](./PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md)
- [四版本内核与启动资产盘点（原始矩阵）](./PANTHER-X2-FOUR-VERSION-KERNEL-ASSET-MATRIX-20261120.md)
- [6.1.174 官方内核包只读审计](./PANTHER-X2-6.1.174-OFFICIAL-KERNEL-ASSET-AUDIT-20261120.md)
- [6.1.174 原始构建源码身份结项](./PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md)
- [6.1.116 / 6.12.81 启动与配置归档](./PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)
- [6.12.81 实际构建来源、配置与源码核验](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- Dropbox `06-modules-dependencies-MANIFEST.tsv`（file ID `id:9qHOnx-HLYoAAAAAAAAAFA`，只读读取；本轮未重新解压大型模块包）
