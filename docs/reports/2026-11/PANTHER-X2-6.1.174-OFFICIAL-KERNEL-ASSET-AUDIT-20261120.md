# Panther X2：Ophub RK35xx 6.1.174 官方内核包只读审计（2026-11-20）

## 1. 审计执行结果

- Workflow：Audit Ophub RK35xx 6.1.174 kernel package
- Run：44728503121
- Job：136261930960
- Commit：bd9ac4d198a5e840be0e93c068b34973b3234fb8
- 结果：success；全部 5 个步骤成功。
- Artifact：ophub-rk35xx-6.1.174-kernel-asset-audit
- Artifact ID：14625845189
- Artifact ZIP SHA256：4d0da74e574037eeea37bbd2a5cd868b02bf7ea1c48532b08f9ede97e3f8fce2
- Artifact 大小：125,663 bytes；保留至 2026-12-20。

本次是 GitHub runner 对 Ophub 官方发布包进行只读下载、校验和索引；没有安装、执行或启动任何内核/模块，没有操作 Panther X2。

## 2. 官方发布包身份与完整性

固定资产：
- URL：https://github.com/ophub/kernel/releases/download/kernel_rk35xx/6.1.174.tar.gz
- 期望大小：135,267,299 bytes；实际相同。
- 期望 SHA256：49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a；实际完全相同。
- gzip 完整性检查通过。

外层发布清单中的四个内层套件全部 SHA256 MATCH：

| 内层套件 | 大小（bytes） | SHA256 |
|---|---:|---|
| dtb-rockchip-6.1.174-rk35xx-ophub.tar.gz | 25,300,490 | bba13ef6ab41261677883a0ba15d50e2aee77398dbc5c29165b4b4fc495f402f |
| boot-6.1.174-rk35xx-ophub.tar.gz | 57,067,437 | 3d9fe727ca1564344f5f0550cf2a2c7b0bf0bddddb9b314e4d8989a91135af40 |
| modules-6.1.174-rk35xx-ophub.tar.gz | 42,246,113 | ac50943bab81118f541dda70f358bb1fa7f94bffdbababd3f5344bdfa8eb2eba |
| header-6.1.174-rk35xx-ophub.tar.gz | 11,554,451 | 62cfac6a29e4871df8dcd2d418292c0264c957bc2ce55c00dd166dbf9ffe8aaa |

## 3. Kernel、modules 与 GMAC 主链

boot 套件含 5 项：
- config-6.1.174-rk35xx-ophub
- initrd.img-6.1.174-rk35xx-ophub
- System.map-6.1.174-rk35xx-ophub
- uInitrd-6.1.174-rk35xx-ophub
- vmlinuz-6.1.174-rk35xx-ophub

config 文件 SHA256：
8bbb46648ed7e28e0a49d16fe895802657a53f8ad788a9023ed730033473cf83

已提取的关键配置：

~~~text
CONFIG_ARM64=y
CONFIG_MODULES=y
# CONFIG_MODVERSIONS is not set
CONFIG_STMMAC_ETH=y
CONFIG_STMMAC_PLATFORM=y
CONFIG_DWMAC_ROCKCHIP=y
CONFIG_PHYLIB=y
CONFIG_REALTEK_PHY=y
CONFIG_MDIO_BUS=y
CONFIG_OF_MDIO=y
CONFIG_LOCALVERSION=""
~~~

modules 套件共 3,718 项，modules.builtin 明确列出以下 GMAC 主链 built-in 路径：

~~~text
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac.ko
kernel/drivers/net/ethernet/stmicro/stmmac/stmmac-platform.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-rockchip.ko
kernel/drivers/net/ethernet/stmicro/stmmac/dwmac-generic.ko
kernel/drivers/net/phy/libphy.ko
kernel/drivers/net/phy/realtek.ko
kernel/drivers/net/mdio/of_mdio.ko
~~~

注意：modules.builtin 中以 .ko 结尾的路径是内核构建系统生成的 built-in 清单，不代表这些文件需要作为可加载模块安装。modules 套件实际文件索引中未发现 STMMAC、DWMAC Rockchip、Realtek PHY 这些 Panther GMAC 主链的独立模块文件；可见的 mdio.ko、mdio-bcm-unimac.ko 是其他独立 MDIO 驱动，不能误认成 GMAC 主驱动。

### 对照既有 6.12.81 结果

6.12.81 已有审计同样确认：
- STMMAC、STMMAC platform、Rockchip DWMAC、PHYLIB、Realtek PHY、MDIO 等主链关键配置为 =y；
- modules 包中没有 GMAC 主链可加载模块。

因此，6.1.174 与 6.12.81 两条故障线在“GMAC 主链编译为 built-in、不是独立 .ko 模块”这一点上相同。这与当前已知 6.1.116 正常基线也采用 built-in 主链的结果一致。故障线与正常线在此项没有形成可用于单独替换的差异。

6.1.65 的 kernel config / modules 闭包仍待从原始镜像 rootfs 提取，不能提前宣称四版本完全一致。

## 4. DTB 资产

DTB 套件共 972 项，包含：
- rk3566-panther-x2.dtb
- 大小：160,138 bytes
- SHA256：871bad4ded75e9da3aea61e26a9a26516c9f39968c49d5f32de2124420185e75

这证明官方 6.1.174 包包含 Panther X2 DTB；不证明历史故障实机使用的就是这份文件。此前两条黄金基准的 GMAC DTB 语义高度一致；本轮尚未把 6.1.174 DTB 解码后与两条黄金 DTB 做新的字段级比较。不能仅凭文件名或 SHA256 判定其正确/错误。

## 5. 当前结论与替换优先级

### 已验证事实
1. 官方 6.1.174 发布包身份、外层 hash、四个内层套件 hash 全部通过。
2. 6.1.174 的 STMMAC / Rockchip DWMAC / PHYLIB / Realtek PHY / MDIO 主链为 built-in。
3. 6.1.174 modules 包没有可单独替换的 Panther GMAC 主链 .ko。
4. 6.1.174 官方包含 Panther X2 DTB、kernel config、initramfs/uInitrd、vmlinuz、System.map 和 modules 套件。

### 对调查路线的影响
- 排除“从 6.1.116 拿一个 GMAC .ko 替换 6.1.174/6.12.81”作为有效实验。主链是 built-in，且不同 kernel release 的模块 ABI 不应混用。
- 暂不把 6.1.174 DTB 替换列为第一候选。两条黄金线的 GMAC DTB 语义一致，需先做 6.1.174 DTB 的定向字段差异，不能盲换。
- 下一项最有价值的工作是补齐 6.1.65 rootfs 的 /lib/modules/6.1.65-ophub 与 kernel config/IKCONFIG，再将四个版本的 kernel config 关键项做统一差异矩阵。
- 若四版本的 GMAC 主链配置均一致，则下一轮应从内核套件中更接近 MAC/DMA/clock/reset 的可区分组件行为继续找变量，而不是泛化检查整个 modules 包。

## 6. 审计脚本边界与修订项

当前 workflow 对 boot 套件文件过滤时只匹配 Image / Image.gz，没有把实际文件名 vmlinuz-6.1.174-rk35xx-ophub 加入关键文件 hash 清单。因此：
- vmlinuz 的存在已由 boot 套件完整成员清单确认；
- 本次报告未生成 vmlinuz 本体 SHA256；
- 后续若复用工作流，应增加 vmlinuz-* 匹配并记录其 hash/文件类型。不得把本轮缺失的 vmlinuz hash 当作零值或未包含该文件。

同样，本次只审计官方发布包内容，不证明该包就是历史 6.1.174 实机安装的二进制套件，也未完成源码 commit 到二进制的逐字节构建 provenance 闭环。
