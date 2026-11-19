# Panther X2：仓库回溯、已完成项目去重与下一步边界（2026-11-19）

## 1. 本轮目的

按用户要求回溯 2026-11-17 至 2026-11-19 的仓库报告和证据，确定下一步研究入口，避免重复既有测试或静态审计。本轮仅读取 GitHub 仓库和公开资料；未操作设备、未写入启动介质、未修改系统或驱动。

## 2. 已完成、不得重复的工作

### 2.1 启动介质与 SPL

- JP idbloader 实验已完成；实机执行 JP SPL/DDR V1.10，识别 4GB LPDDR4 并成功进入 ATF、U-Boot proper 和 Linux 6.12.81。
- 该启动周期中 U-Boot proper 枚举 GMAC1，Linux RTL8211F PHY 识别成功，链路为 1000Mbps Full；IPv4 DHCP 仍失败。
- 原版 eMMC 116 idbloader 已恢复，LBA64–667 回读 SHA256 与备份源一致。不得重做恢复/覆盖实验。
- 启动链阶段已梳理；不要再次把 SPL 从 TF 加载 proper 与 BootROM 从 eMMC 加载 SPL 混为一谈。

关联报告：JP-IDBLOADER-BOOT-AND-DHCP-DIFF、UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN、BOOT-MEDIA-AND-SOFTWARE-INVENTORY。

### 2.2 BL31 反汇编

- 已检查 0x55700–0x557a0、0x5c238–0x5c280、0x5c400–0x5c7d4 及相关 BL 调用引用。
- 目前只能确认存在参数表搬运和固定地址写入；没有符号、寄存器映射或可靠源码关联，不能将相关地址认定为 DDR/GMAC 初始化。
- DDR training 在 SPL 阶段完成，早于 BL31；该 BL31 代码不能直接解释 SPL 最终训练频率。
- 原报告已明确要求停止无目标扩展反汇编。

本项结案：不再索要相邻反汇编窗口。只有找到该 ELF 的确切 TF-A 平台构建来源、符号/链接映射或对应源码，才重新打开。

### 2.3 Linux STMMAC / DMA / GMAC

以下已在仓库中审计，不重复：
- 普通 skb TX DMA mapping、descriptor 地址、OWN、barrier、tail pointer；
- DWMAC4 TX/RX channel 初始化、DMA reset polling、SR/ST/RE/TE start；
- queue 0 到 DMA channel 0 映射；
- RK3566 实际使用 rk3568_ops；
- Panther RGMII 的 PCS / SerDes / integrated PHY 新增路径适用性；
- GMAC1 DTS AXI、IOMMU 绑定、pinctrl 和基础 RGMII delay；
- RK3568 CRU GMAC1 gate/mux 父链；
- PHY reset GPIO、PHY link、PHY ID、MAC 来源；
- 已完成的 MAC loopback、TX/RX 相关测试。

### 2.4 需要采用后续修订的旧结论

部分早期报告把 6.1 的 5ms 与 6.12 的 100–200us settle delay 直接作为主要回归线索。后续 RTL8211F-CLKOUT-WORKAROUND 报告已指出：
- 5ms 在 generic upstream gmac_clk_enable() 历史中早已存在；
- 6.12 vendor 分支的 100–200us 是后续 vendor 分支差异；
- Panther GMAC DTS 没有 rockchip,csu / rockchip,csu-names，CSU handle 失败后置 NULL，helper 对 NULL no-op。
因此不能将 CSU disable 或等待时间差异说成已证实的硬件时序根因。GMAC1-CRU-GATE 报告也已把忽略 clk_prepare_enable() 返回值从强根因线索降级。

## 3. DDR 频率差异：可确认范围

既有实机日志：
- 旧 E25 SPL / DDR V1.13（2022-02-18）：最终 1560MHz；
- JP SPL / DDR V1.10（2021-08-10）：训练经过 324、528、780、1056MHz，最终 1056MHz。

当前可以确认：
1. 两套 SPL/DDR 初始化固件及其训练行为不同；
2. 频率差异在 SPL 阶段形成；
3. 不能把 BL31 反汇编作为该频率差异的直接原因；
4. 目前没有两份 DDR binary 对应源码/参数表的完整映射，尚不能解释 V1.13 为什么选择 1560MHz、V1.10 为什么止于 1056MHz。

补充公开资料：Rockchip《RK3566 Hardware Design Guide V1.1》2.1.9.7 写明，RK3566 DDR 最高频率受 PCB layout 影响较大，官方提供的大多数模板最高工作频率可到 1056MHz，并建议优先采用官方 DDR 模板。该说明不等于 Panther 板只能跑 1056MHz，也不证明 1560MHz 必然不稳定；但不能把 1560MHz 当作默认应追求的目标，更不能据此直接修改 DDR 参数。
- 文档：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_CN.pdf
- 段落：2.1.9.7，PDF 第 20 页。
- Armbian rkbin release notes 记录后续 DDR v1.20/v1.21 对 LPDDR4 兼容性、低频 ODT 和 CA training 的修正，说明 DDR blob 版本差异可能包含训练算法/兼容性变化，不只是目标频率数字：https://github.com/armbian/rkbin/blob/master/patch-notes/RK3566_EN.md

DDR 研究收口：若继续，只做两份现有 idbloader/DDR binary 的静态指纹、版本字符串、可提取参数和构建来源对照；不做 DDR 压力测试，不尝试把 1056 拉到 1560，不改 SPL/DDR 参数。若无匹配源码/参数表，则将频率选择原因标记为无法从现有材料证明。

## 4. 当前网络故障的证据边界

仓库现有证据将故障边界限定为：
- Linux 本机 outgoing capture 曾看到 DHCP Discover；
- 驱动 TX 路径返回成功、descriptor 被清理；
- 同一启动周期 TX 统计增长；
- 6.12.81 的 MMC good-only 与 good+bad 累计计数曾相等，错误计数为零；
- hEX 和持续监听的 iMac 未观察到对应外发帧。

这些事实仍不能证明帧已越过 GMAC RGMII TXD/TXC 引脚，也不能证明 PHY 已从 MDI 侧发出。MAC MMC good 计数是 MAC 内部统计，不是线侧确认。

既有报告已指出，最有区分度的下一项不是重跑 ping、DHCP 或 loopback，而是同一 DHCP Discover 的两端关联：Panther 侧记录报文时间、ID 和源 MAC；同一时间窗口在 hEX 入口确认是否收到同一报文。Linux outgoing capture 单独不能替代 PHY 线侧证据。

## 5. 当前候选与状态

| 方向 | 已知结论 | 当前处理 |
|---|---|---|
| 116 的 JL2xx1 workaround | 116 有地址 0 MDIO 广播写 PHYCR2=0x1801 和额外 PHY soft reset；174/6.12 无；实物最终寄存器状态未知 | 保留为历史差异；不得直接移植 |
| RTL8211F PHYCR2 / CLKOUT | Panther clock input from PHY；0x1801 涉及 PHYCR2，但不同 datasheet revision 对 bit1 定义不同；默认 CLKOUT bit0/11 也为 1 | 仅凭源码无法定因；需要现存回读或经授权只读 MDIO |
| GMAC clock settle / CSU | 源码差异存在；CSU 当前 DT 路径为 NULL/no-op；无证据 100–200us 不足 | 降级，不继续扩大全 SoC 时钟审计 |
| ARM64 DMA coherent prep | descriptor ring 调用路径存在 clean+invalidate → clean 差异；上游解释 clean 已满足 DMA API | 暂结案，不改内核 |
| BL31 early init | 无法把地址/表项可靠映射到子系统 | 停止扩展反汇编 |
| DDR V1.13 1560 vs V1.10 1056 | SPL 阶段差异已确认；原因未闭环 | 只允许静态 blob/参数来源对照 |
| 物理 TX 边界 | MAC good 统计与远端不可见并存；RGMII/MDI 线侧仍未确认 | 需要一次同步双端报文关联，不重复已有测试 |

## 6. 有限的下一步计划

### A. 不需要设备操作的静态收尾
1. 只读核对仓库现有启动日志是否已包含 DMA reset failure、MAC TX enable 错误、clock provider 错误；已有筛选结果不能把不完整日志写成“绝对没有”。
2. 对照 116 / JP 的 SPL DDR blob 可用字符串、文件长度、哈希、版本标记和公开 rkbin release notes；若 blob 没有源码/参数解码器，则停止，不进行猜测式反汇编。
3. 维护一份“已做/未做/不再做”的主索引，后续新报告先更新索引，避免同一主题反复开新报告。

### B. 唯一有明确区分度的后续现场验证（需单独确认）
在不改配置、不写寄存器、不重启网卡的前提下，对同一 DHCP Discover 做 Panther 与 hEX 两端同步被动观察。必须先明确采集点、命令和报文关联字段；若没有自然产生的 Discover，是否主动触发需另行确认。

判读：
- hEX 看到同一帧：证明帧已穿过 Panther 物理链路到达 LAN，后续转查 DHCP server/relay/filter；
- Panther outgoing capture 有、hEX 入口没有：故障仍在本机 MAC/RGMII/PHY 线侧或中间物理链路，不能再靠普通源码猜测定因；
- Panther outgoing capture 本身没有：才回到 Linux packet path / 驱动调用条件。

不运行 loopback scan、不写 PHY、不改 MAC、不改内核、不改 DTS、不改 U-Boot、不写 eMMC/TF。

## 7. 当前阶段结论

目前没有足够证据宣布 DHCP 故障已定位到某个源代码函数。继续无目标源码/反汇编扩展，收益低且容易重复劳动。最合理策略：
- 保留已恢复的 116 eMMC 启动基线；
- 结束 BL31 泛化反汇编；
- DDR 只做静态 blob 来源对照；
- 网络主线转向一次同一报文的双端被动关联；
- 在线侧边界证据出现前，不提出未经验证的驱动补丁或启动链写入实验。

## 8. 关联仓库报告

- PANTHER-X2-BL31-EARLY-INIT-DISASSEMBLY-AND-TEST-STOP-20261119.md
- PANTHER-X2-JP-IDBLOADER-BOOT-AND-DHCP-DIFF-20261119.md
- PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md
- PANTHER-X2-UBOOT-CANDIDATE-RESEARCH-20261117.md
- PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md
- PANTHER-X2-RTL8211F-CLKOUT-WORKAROUND-REGRESSION-20261119.md
- PANTHER-X2-JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261119.md
- PANTHER-X2-ARM64-DMA-COHERENCY-116-VS-61281-20261119.md

## 9. DDR 频率研究的新增关键交叉证据（公开 Panther X2 日志）

进一步检索公开 Panther X2 启动记录后，发现一个重要反例，修正“DDR V1.10 本身只支持/只选择 1056MHz”这种可能的误解：

### 9.1 同一 DDR V1.13 banner，在另一台 Panther X2 上最终为 1056MHz

公开文章《rk3566-panther-x2 黑豹X2 刷飞牛oec包挂逼救砖记》（2026-01-15）记录：
- DDR banner：`DDR Version V1.13 20220218`；
- `ddrconfig:0`；
- `LPDDR4X`；
- 4096MB，CS0 Row=17，单 rank；
- 最终频率：1056MHz；
- 同一日志显示 BL31 fsp_param[0] 为 1056MHz，另有 324/528/780MHz FSP。
来源：https://godsun.pro/blog/panther-x2-oec.html

这说明同一个 V1.13 banner 并不意味着一定训练到 1560MHz。公开样本与本机旧日志的区别至少包括 DRAM type（LPDDR4X vs 本机日志记录的 LPDDR4）和 rank topology（单 rank vs 本机报告记录的 CS0/CS1）。所以不能只用 V1.13 版本号推断最终频率。

### 9.2 V1.10 公开样本的适用性限制

此前检索到一份 V1.10 / 1560MHz 的公开日志，但来源为 RK3568 开发板而非 Panther X2/RK3566，不能用它证明 RK3566 V1.10 固件在本机配置下可达到 1560MHz。另一个 RK3566 4GB LPDDR4 样本记录 V1.10 最终 1056MHz：
https://github.com/tanshihaj/1e6f6a66196f0d5f4574508c71423aa9

这些公开样本不替代本机两份日志。关于本机 JP V1.10 为什么最高只有 1056MHz，应以第 10 节的 FSP 参数表对照为准。

### 9.3 由此修正 DDR 降频问题的当前解释

当前本机实测：
- 旧 SPL：V1.13，LPDDR4，4GB，CS0/CS1，最终 1560MHz；
- JP SPL：V1.10，LPDDR4，4GB，CS0/CS1，最终 1056MHz。

但公开样本证明：
- V1.13 可在 Panther X2 LPDDR4X 4GB 单 rank 样本上最终 1056MHz；
- V1.10 可在其他 RK3566 4GB LPDDR4 双 rank样本上最终 1560MHz。

因此，**不能将本机 1560→1056 的变化直接归因于 DDR blob 版本号或固定频率上限。** 更合理的待查项是两份实际 DDR 初始化固件所采用的参数/能力表、DRAM 识别结果、FSP 参数集合及 training 结果/选择策略。尤其需要把以下字段逐项对照：
- DRAM type / MR14；
- ddrconfig；
- BW / Col / Bank / Row / CS / Die BW；
- 初始 TDQSS；
- 每个频点 PHY drive、ODT、Vref、clock skew；
- read/write/CA training window；
- BL31 输出的 FSP frequency 列表及其顺序。

不能仅凭训练输出最终频率较低就断言 DDR 降频是失败或降级；它可能是该固件针对识别出的 DRAM/参数组合所选择的可用 FSP。也不能据此认定 1056MHz 与 DHCP 故障存在因果关系。

### 9.4 下一步收窄为现有日志字段差分

不做新设备测试，先从仓库现有的两份完整 UART 日志提取上述字段，形成逐项差异表；随后仅查公开 DDR bin release notes/配置表是否能解释这些差异。如果现有日志缺少 DDR颗粒完整型号、bin 内参数表或 training selection 细节，则明确标记无法从公开信息证明，不继续猜测式反汇编。


## 10. 本机两份完整 UART 日志的 DDR FSP 差异：已定位“1056MHz 从何而来”

本轮直接重新读取仓库两份现存完整启动日志（不是要求用户重跑）：
- JP SPL/V1.10：`evidence/boot/2026-11-19-panther-x2-jp-idbloader-uart.log`
- 原版 SPL/V1.13：`evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt`

### 10.1 两份日志识别到的是同一类 DRAM 配置

两份日志的以下字段相同：
- `ddrconfig:7`
- `LPDDR4`
- `BW=32 Col=10 Bk=8`
- `CS0 Row=16 CS1 Row=16 CS=2 Die BW=16 Size=4096MB`
- CS0 TDQSS：434/361/385/289 ps
- CS1 TDQSS：458/361/385/289 ps

因此本次 1560→1056 差异不能简单归因于两次启动识别出了不同 DRAM 类型、容量、rank topology 或不同的初始 TDQSS 测量值。这里是两份历史 UART 输出对照，不是颗粒 BOM/PCB 级身份鉴定。

### 10.2 决定性差异在 BL31 输出的 FSP 参数列表

| 来源 | DDR banner | 最终频率 | FSP 列表 |
|---|---|---:|---|
| 原版 E25 SPL | V1.13 20220218 | 1560MHz | [1560, 324, 528, 780]MHz |
| JP SPL | V1.10 20210810 | 1056MHz | [1056, 324, 528, 780]MHz |

两份 BL31 日志分别明确输出：
- 原版：`fsp_param[0].freq_mhz=1560MHz`，其余 324/528/780；
- JP：`fsp_param[0].freq_mhz=1056MHz`，其余 324/528/780。

**这意味着 JP SPL/DDR V1.10 本轮并不是“尝试 1560MHz 后训练失败，自动退回 1056MHz”的已知情形。它传递给 BL31 的 FSP 集合本身就以 1056MHz 为最高频点；日志没有 1560MHz FSP，也没有 1560MHz training attempt。** 因而 1056MHz 是这套 JP DDR 固件配置提供的最高 FSP，而不是本轮 1560MHz training failure 的证据。

### 10.3 训练参数也存在系统性差异

相同的 528/780MHz 频点：
- 原版 V1.13：PHY ODT=0，Vref inner/out=41%；
- JP V1.10：PHY ODT=60，Vref inner=16%，Vref out=41%。

两者在 1056MHz 最终档位都使用 PHY ODT=60、Vref inner=16%、Vref out=29%、DRAM ODT=80、Vref_CA=0x68；但 clock skew 记录分别为原版 0x2 / JP 0x2c（按对应日志原文）。这进一步说明 DDR blob 的参数表/训练策略有差异，而不只是打印版本号不同。

### 10.4 结论更新

- **已确认：** 本机两份日志识别出的 DRAM 几何配置、ddrconfig 和 TDQSS 起始测量一致。
- **已确认：** 两套启动固件提供给 BL31 的 FSP 列表不同：原版含 1560MHz，JP 仅含 1056MHz。
- **已确认：** 本轮 JP 固件没有 1560MHz 训练失败的记录，因为它没有 1560MHz FSP/训练阶段。
- **当前最直接解释：** 1056MHz 上限来自 JP SPL 所携带/传递的 DDR FSP 配置，而不是 Linux、BL31 后续初始化或 DHCP 网络栈。
- **仍未确认：** V1.10 为什么只提供 1056MHz FSP——是该二进制面向特定板级/颗粒的保守参数集、固件构建选择，还是可通过不同 DDR blob 变体提供更高频点。仅凭版本 banner 和日志不能进一步区分。
- **网络因果：** 没有证据把 1056MHz FSP 与 DHCP 故障建立因果关系；JP SPL 更换后 DHCP 仍失败也说明它不是 DHCP 故障的单一解释。

### 10.5 对外部公开样本的证据限制修订

公开 Panther X2 文章中 V1.13 最终 1056MHz 的样本使用 LPDDR4X、单 rank，与本机日志的 LPDDR4、双 rank 配置不同；它只能证明同一版本 banner 不唯一决定频率，不能用于推断本机具体 FSP 选择原因。
公开 RK3568 的 V1.10/1560MHz 日志不是 Panther X2/RK3566 的同板证据，本报告不再用它支持“RK3566 V1.10 也能达到 1560MHz”的判断。后续仅以本机两份日志和可确认的 RK3566 DDR blob 资料为准。

### 10.6 下一步

DDR 频率问题已经从“为什么训练降频”收敛为“为什么 JP idbloader 内 DDR 配置只给出 1056MHz FSP”。下一步只需要：
1. 在已有 JP idbloader、原版 idbloader 备份中识别 DDR blob 边界和可验证文件指纹；
2. 查明 V1.10 DDR binary 对应的构建来源/板级配置，确认它是否就是 1056MHz-only 的配置变体；
3. 若无法映射到可读参数表，则以“JP 固件提供的 FSP 上限为 1056MHz”结案，不做反汇编猜测或频率强行提升。

## 11. Rockchip rkbin 构建配置交叉核对：找到两个 FSP profile 的官方来源

继续查阅 Rockchip rkbin 历史提交，发现 DDR V1.10 / V1.13 不只是版本 banner；对应的 SoC profile 配置文件明确选择了不同的 DDR binary：

### 11.1 RK3566 profile：V1.10 DDR binary 的最高频点是 1056MHz

Rockchip rkbin commit：
- `664922185a089ac5348ce869461ce303fe80f971`
- 日期：2021-08-10
- 提交标题：`rk3566: ddr: update ddr bin to v1.10`

该 commit 的 `RKBOOT/RK3566MINIALL.ini` 明确将：
- CODE471 / FlashData 指向 `bin/rk35/rk3566_ddr_1056MHz_v1.10.bin`
- SPL 指向 `bin/rk35/rk356x_spl_v1.11.bin`

源码配置：https://github.com/rockchip-linux/rkbin/blob/664922185a089ac5348ce869461ce303fe80f971/RKBOOT/RK3566MINIALL.ini

这与本机 JP SPL 日志中 V1.10、FSP 列表最高 1056MHz 完全吻合。

### 11.2 RK3568 profile：V1.13 DDR binary 的最高频点是 1560MHz

Rockchip rkbin commit：
- `ddf03c1d80b33dac72a33c4f732fc5849b47ff99`
- 日期：2022-02-18
- 提交标题：`rk3568: ddr: update ddr bin to v1.13`

该 commit 的 `RKBOOT/RK3568MINIALL.ini` 明确将：
- CODE471 / FlashData 指向 `bin/rk35/rk3568_ddr_1560MHz_v1.13.bin`
- SPL 指向 `bin/rk35/rk356x_spl_v1.12.bin`

源码配置：https://github.com/rockchip-linux/rkbin/blob/ddf03c1d80b33dac72a33c4f732fc5849b47ff99/RKBOOT/RK3568MINIALL.ini

这与本机原版 E25 SPL 日志中 V1.13、FSP 列表最高 1560MHz 吻合。

### 11.3 当前最强解释

把三层证据放在一起：
1. 本机原版 E25 SPL 日志：V1.13，FSP[0]=1560MHz；
2. 本机 JP SPL 日志：V1.10，FSP[0]=1056MHz；
3. Rockchip 官方 rkbin 的 RK3568 / RK3566 MINIALL 配置分别选择 `rk3568_ddr_1560MHz_v1.13.bin` 和 `rk3566_ddr_1056MHz_v1.10.bin`。

**目前最强的解释是：原版 E25 启动链携带 RK3568 1560MHz DDR profile，而 JP-TvBox 启动链携带 RK3566 1056MHz DDR profile；频率差异来自 SPL 所集成的 DDR profile/FSP 表不同，而不是同一 DDR training 在 1560MHz 失败后退回 1056MHz。**

证据等级：强关联/高置信度推断，尚未达到 binary-level 直接证明。因为当前仓库尚未对 eMMC 原始 idbloader 与 JP idbloader 内部 DDR payload 做独立提取并与上述 rkbin 文件逐字节 hash 对照；同样的版本 banner 不能单独证明 payload 文件名。

### 11.4 这是否意味着原版 1560MHz 一定更好？

不能这样下结论：
- RK3566 Hardware Design Guide 指出 DDR 最高频率高度依赖 PCB layout，官方大多数模板最高约 1056MHz；
- 原版 E25 的 1560MHz profile 在 Panther 上曾成功初始化并运行，是历史事实，但不等于已完成 DDR 长期稳定性/裕量认证；
- JP 的 1056MHz profile 是 RK3566 官方配置方向，更保守；但目前没有证据表明它造成 DHCP 故障。
- 不建议为了追求 1560MHz 把 RK3568 DDR profile 直接移植到 RK3566，也不建议在未授权情况下更换 DDR blob。

### 11.5 DDR 研究结论

DDR 降频问题已基本定位到**启动固件选择了不同的 DDR profile/FSP 集合**。后续仅需对两份现存 idbloader 中的 DDR payload 做静态提取和 hash 对照，确认其是否分别对应上述官方文件。若无法取得原始 JP payload 或旧备份文件，则保留“高置信度推断”，不继续反汇编猜测，也不做频率修改。

参考：
- RK3566 V1.10 commit：https://github.com/rockchip-linux/rkbin/commit/664922185a089ac5348ce869461ce303fe80f971
- RK3568 V1.13 commit：https://github.com/rockchip-linux/rkbin/commit/ddf03c1d80b33dac72a33c4f732fc5849b47ff99
- RK3566 hardware guide frequency/layout note：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_CN.pdf

## 12. DDR 官方支持频率范围核对：修正上一节的解释边界

进一步直接读取 Rockchip rkbin 历史版本中的 `tools/ddrbin_tool_user_guide.txt`（commit `664922185a089ac5348ce869461ce303fe80f971`），而非只依据当前网页摘要。该工具文档对 SoC 的频率支持范围明确区分：

- RK3566：324、396、528、630、780、920、1056MHz；
- RK3568 的 DDR4/LPDDR4/LPDDR4X：324、396、528、630、780、920、1056、1184、1332、1560MHz。

这使得本机日志中的差异更有解释力：
- JP 日志最高 FSP=1056MHz，符合 RK3566 官方频点表；
- 原版 E25 日志最高 FSP=1560MHz，属于 RK3568 的 LPDDR4 频点范围，不属于 RK3566 的官方频点范围。

并且在 RK3566 V1.10 的官方 `RK3566MINIALL.ini` 中，CODE471 / FlashData 指向 `rk3566_ddr_1056MHz_v1.10.bin`，SPL 指向 `rk356x_spl_v1.11.bin`。原版 E25 的 V1.13/1560MHz 日志与 RK3568 1560MHz profile 相符。

### 12.1 重要修正

此前把原版 1560MHz 描述为“原版 E25 携带 RK3568 1560MHz DDR profile”是高置信度推断；结合官方 SoC 频率支持表，现在可以更明确地说：

**原版 E25 的 DDR 初始化配置选择了 RK3568 级别的 1560MHz FSP，而 JP 选择了 RK3566 级别的 1056MHz FSP。对 RK3566 芯片而言，JP 1056MHz profile 与官方支持频率表一致；原版 1560MHz 虽然历史上成功启动，但不属于 RK3566 官方列出的 LPDDR4 支持频率。**

这里的“成功启动”只证明当时样机能完成该次初始化和启动，不证明 1560MHz 满足长期稳定性、温度/电压/老化裕量或官方设计约束。不能因为 116 原版能启动，就将 1560MHz 当成应恢复的目标频率。

官方文件也指出 RK3566 DDR 最高工作频率受 PCB layout 影响很大，多数官方模板最高到 1056MHz；这进一步支持采用 RK3566 profile 的保守策略，但不单独证明 Panther X2 的 PCB 极限。

### 12.2 对 DHCP 故障的影响

JP 采用官方 RK3566 1056MHz profile 后，Linux 6.12.81 仍然无法 DHCP，故：
- DDR 1560→1056MHz 不是 DHCP 故障的充分解释；
- 当前没有证据表明 1056MHz 本身造成 GMAC RX/TX 故障；
- 不应为了网络排障把 DDR 频率升回 1560MHz；
- DDR 频率差异作为启动固件配置差异归档，不再作为 DHCP 主线排查项。

### 12.3 payload 文件级证明的限制

本仓库当前 Git tree 中有完整 JP UART 日志、旧 eMMC UART 日志及 idbloader 实验报告，但没有将原版和 JP 的 DDR payload 作为独立二进制文件存档。因此目前无法在 GitHub 文件层直接做 SHA256/字节比较，也不能声称已完成 payload binary match。

本项静态研究到此收口：保留“日志 FSP + 官方 rkbin profile + 官方支持频率表”的交叉证据；若未来重新取得两个原始 loader 文件，再做纯离线 payload 提取/hash 对照。当前不需要用户重跑或再次写介质。

直接依据：
- Rockchip rkbin 工具说明（历史 commit）：https://github.com/rockchip-linux/rkbin/blob/664922185a089ac5348ce869461ce303fe80f971/tools/ddrbin_tool_user_guide.txt
- RK3566 loader profile：https://github.com/rockchip-linux/rkbin/blob/664922185a089ac5348ce869461ce303fe80f971/RKBOOT/RK3566MINIALL.ini
- RK3566 硬件指南 2.1.9.7：https://github.com/rockchip-linux/rkbin/blob/master/specific/Rockchip_Specific_PCB_Template_and_DDR_bin_Configuration_Table.md

## 13. 6.1.116 / 6.12.81 link-up 与 speed callback 的再次核对

为避免遗漏，按仓库记录的精确构建 commit 直接读取两版 `dwmac-rk.c` 和 `stmmac_main.c`。本轮只做源码静态对照，不进行设备操作。

### 13.1 RK3568 1Gbps speed callback

两版 `rk_fix_speed()` 对 Panther 的 RGMII 路径都执行 `ops->set_rgmii_speed(bsp_priv, speed)`。6.12 新增的 `mode` 参数在该函数体中未使用。
两版 `rk3568_set_gmac_speed()` 对 10/100/1000Mbps 都设置 2.5/25/125MHz；6.1 从 clock array 取 `RK_CLK_MAC_SPEED`，6.12 改为独立 `clk_mac_speed` handle。DTS clock ID 对应关系已由既有 RGMII/clock parent 报告确认相同。
因此 1Gbps 目标频率仍为 125MHz，未发现 link-up callback 的速率选择回归。

### 13.2 STMMAC MAC link-up

两版 `stmmac_mac_link_up()` 的关键顺序一致：
1. 读取 MAC_CTRL；
2. 按 link speed 更新 speed bits；
3. 调用 Rockchip `fix_mac_speed`；
4. 更新 duplex / flow control；
5. 写回 MAC_CTRL（若变化）；
6. 调用 `stmmac_mac_set(..., true)` 启用 MAC。

6.12 增加的差异：
- 只有设置 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` 且提供 `serdes_powerup` callback 时，才在 link-up 开始阶段执行 SERDES power-up；
- EEE 对 `rx_clk_runs_in_lpi` 的判断改用 flag；
- 增加 HWTSTAMP latency correction。
Panther 使用外置 RTL8211F + RGMII，未配置 SERDES 路径；EEE/HWTSTAMP latency correction 也没有证据与当前 DHCP Discover 不出线相关。因此这些新增分支不适用于当前 Panther 路径。

### 13.3 DMA operation mode 与 channel start

两版 `stmmac_start_all_dma()` 都先按 RX channel 数启动 RX，再按 TX channel 数启动 TX；`stmmac_enable_all_queues()` 对普通 NAPI queue 的启用顺序一致。
6.12 `stmmac_dma_operation_mode()` 增加对 GMAC4/XGMAC 共享 FIFO 的按 channel 数拆分；6.1 对所有设备无条件除以 RX/TX channel 数。Panther 是 GMAC4，且既有设备树/运行配置使用单 RX/TX queue，因此除以 1 后结果相同，不构成该设备的差异。

### 13.4 当前结论

本轮没有发现 6.12 在 Panther 的 1Gbps link-up callback、MAC TX enable、普通 queue enable 或 TX DMA channel start 上存在新的可直接解释故障的差异。该路径与既有 TX descriptor / ring-mode 审计结论一致，不再重复扩展。
唯一保留的真实版本差异仍是已归档的 RK3568 RGMII delay 寄存器写入顺序及 GMAC clock enable 等待时间；它们已有专门报告，不在本轮重复分析。

源码：
- 6.1.116 dwmac-rk.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.12.81 dwmac-rk.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 stmmac_main.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.12.81 stmmac_main.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c

## 14. TX fast path 6.1.116 / 6.12.81 再核对：descriptor 发布与 DMA kick 语义

本轮根据第 18 节保留的 TX 主线，只核对精确源码中普通 skb 的 `stmmac_xmit()`、`stmmac_flush_tx_descriptors()`、DWMAC4 descriptor helper、`dwmac4_dma_start_tx()`。不重新做设备寄存器测试，也不重复 ring/chain、DMA mapping 或 TX completion 的既有审计。

### 14.1 普通 DHCP skb 的主要发送顺序

两版普通 skb 路径均完成：
1. 选取 TX queue 和当前 descriptor；
2. DMA map skb data；
3. 写入 descriptor buffer address / length / FS / LS / checksum flags；
4. 设置 first descriptor OWN；
5. `netdev_tx_sent_queue()`；
6. 启动 TX DMA；
7. `stmmac_flush_tx_descriptors()` 写 TX tail pointer。

两版 `stmmac_flush_tx_descriptors()` 内容一致：计算 descriptor size；执行 `wmb()`；更新 `tx_tail_addr = dma_tx_phy + cur_tx * desc_size`；调用 `stmmac_set_tx_tail_ptr()`。未发现 6.12 删除发布前 barrier 或改变 tail pointer 计算方式。

DWMAC4 descriptor helper 中，first descriptor OWN 的发布仍有 `dma_wmb()` 保护此前同一 frame 的其他 descriptors；本轮读取的 6.1.116 / 6.12.81 `dwmac4_rd_prepare_tx_desc()` 关键语义一致。不能把 6.12 的该段视为已发现的 OWN 顺序回归。

### 14.2 DMA start 与寄存器偏移

6.1.116 的 `dwmac4_dma_start_tx(ioaddr, chan)`：
- 对 `DMA_CHAN_TX_CONTROL(chan)` 设置 `DMA_CONTROL_ST`；
- 对 `GMAC_CONFIG` 设置 `GMAC_CONFIG_TE`。

6.12.81 增加 `priv` 参数，并从 `priv->plat->dwmac4_addrs` 取得可选寄存器布局，再设置相同的 ST / TE 位。6.12 的寄存器宏在 `dwmac4_addrs == NULL` 时回退到与 6.1 相同的默认 DMA channel base/offset（0x1100 / 0x80）。Rockchip `dwmac-rk.c` 的 Panther RK3566 compatible 路径没有设置 `dwmac4_addrs`，平台数据为零初始化；因此按当前源码，Panther 默认使用同一寄存器偏移。此处仍是源码配置推断，最终以实际运行 DT/平台数据为准。

普通发送路径的调用由 6.1 `stmmac_enable_dma_transmission(priv, ioaddr)` 变为 6.12 `stmmac_enable_dma_transmission(priv, ioaddr, queue)`。Panther 既有运行配置为单 TX queue，queue=0；故 channel 选择仍是 channel 0。没有发现该 API 变化本身会将 Panther 的 TX DMA kick 到错误 channel。

### 14.3 6.12 新增 checksum fallback 的适用性

6.12 在 `stmmac_xmit()` 增加判断：若当前 TX queue 的 `coe_unsupported` 为 true，或 skb EtherType 不是 IPv4/IPv6，则对 `CHECKSUM_PARTIAL` skb 调用 `skb_checksum_help()`，回退到软件校验和。

DHCP Discover 是 IPv4/UDP Ethernet frame；`stmmac_has_ip_ethertype()` 对正常未标记/普通 VLAN IPv4 skb 返回 true。因此“非 IP EtherType”分支不适用于 DHCP Discover。若实际 TX queue 标记 `coe_unsupported`，仍可能走软件 checksum fallback，但这属于校验和计算路径，不是 descriptor 发布或 DMA kick 的直接差异；当前没有证据表明本机 DHCP skb 在该分支失败。不可仅凭代码新增就将其定为根因。

### 14.4 其他发送时序差异

普通 skb 路径中 `skb_tx_timestamp()` 相对 `stmmac_enable_dma_transmission()` 的调用位置在两版本略有调整；它是软件 TX timestamp bookkeeping，不改变 descriptor 地址、OWN、tail pointer 或 DMA channel。当前无证据将其与 DHCP 帧不出线关联。

### 14.5 本轮结论

- **已核对且等价：** descriptor buffer/length 编程的主路径、first descriptor OWN 发布屏障、flush 的 `wmb()`、tail pointer 算法。
- **已核对且对 Panther 等价：** DWMAC4 TX start 的 ST/TE 位语义；6.12 新增可选 `dwmac4_addrs` 在 Panther RK3566 路径未设置时回退到 6.1 默认寄存器布局；单 queue 下 queue 参数为 0。
- **存在但未证明相关：** 6.12 的 checksum fallback 和 timestamp 调用位置调整。
- **没有发现：** 能直接解释“Linux outgoing capture 可见 DHCP Discover，但 hEX 未观察到该帧”的确定 TX fast-path 软件回归点。

### 14.6 证据边界和下一步

仓库历史证据需要按启动周期严格区分：
- 2026-11-16/17 的历史报告记载曾在 Panther outgoing capture 看到 DHCP Discover，而同期 hEX 未观察到；这构成已有的跨端现象证据，但并非同一帧的同步逐包关联。
- 2026-11-19 JP idbloader 启动周期的 DHCP 状态文件没有 tcpdump 输出，不能声称该启动周期也捕获到了 Discover。
- 当前报告不能把旧启动周期的 outgoing capture 移植成 11 月 19 日证据。

下一步不再重复普通 TX descriptor / barrier / tail pointer 源码核对。若继续需要新增信息，应使用同一测试窗口内现存的 outgoing DHCP capture（若尚保留原始 pcap）与 hEX ingress pcap 做时间/transaction-id/Ethernet source MAC 关联；若旧 pcap 不存在，则需另行授权一次只读同步抓包。抓包本身不证明 PHY MDI 线侧波形，必要时才继续下探交换机端口/PHY 物理边界。

源码：
- 6.1.116 stmmac_main.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.12.81 stmmac_main.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.1.116 dwmac4_lib.c：https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c
- 6.12.81 dwmac4_lib.c：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac4_lib.c

**状态：** 本轮是纯静态源码与仓库证据核对；无设备操作、无 DHCP renew、无接口重启、无配置/驱动/介质修改。

## 15. 实际 6.12 RK35xx kernel config / GMAC 编译分支核对

本轮重新核对仓库配置、官方 workflow 和两条源码路径，澄清上一轮提出的 `CONFIG_CPU_RK3568=y` 是否意味着把 RK3566 误编译成 RK3568。

### 15.1 6.12 配置文件内容（可直接验证）

在 `ophub/kernel` 配置仓库 commit `c23196e10d7702ee2906de4a05421d8971fb2717` 中，`kernel-config/release/rk35xx/config-6.12` 的 blob SHA 为 `dee127c6c644f38426eeb28000d73536084d34a3`，共 10,333 行。关键值：
- `CONFIG_ARCH_ROCKCHIP=y`
- `CONFIG_CPU_RK3568=y`
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_DWMAC_ROCKCHIP=y`
- `CONFIG_DMA_DIRECT_REMAP=y`
- `CONFIG_ROCKCHIP_IOMMU=y`
- `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y`
- `CONFIG_ARCH_DMA_ADDR_T_64BIT=y`
- 未设置 `CONFIG_DMA_GLOBAL_POOL`；该 config 中没有 `CONFIG_ARCH_HAS_DMA_ALLOC` 或 `CONFIG_DMA_API_DEBUG` 项。

同一配置仓库 commit 的 `kernel-config/release/rk35xx/config-6.1` 也启用 `CONFIG_CPU_RK3568=y`、STMMAC、Rockchip glue、DMA_DIRECT_REMAP 和 ROCKCHIP_IOMMU。故 RK35xx 6.1→6.12 配置模板没有发生“从 RK3566 切成 RK3568”的新变化；两版都使用同一 RK35xx 平台配置思路。

### 15.2 为什么 RK3566 设备会启用 CONFIG_CPU_RK3568

6.12.81 候选源码 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 Panther DTS 将 GMAC1 compatible 写为 `rockchip,rk3568-gmac`，Rockchip glue 通过 `CONFIG_CPU_RK3568` 编译并注册 `rk3568_ops`，该 ops 的寄存器表含 GMAC1 `0xfe010000`。这是该 BSP 对 RK3566/RK3568 共用 GMAC IP/驱动 glue 的编译选择，不代表设备树把 SoC 型号改成 RK3568。

官方 `ophub/kernel` README 将 `kernel_rk35xx` 定义为 RK3528/RK3566/RK3568 共用的专用 BSP kernel；workflow `.github/workflows/compile-rockchip-rk35xx-kernel.yml` 的默认 `kernel_config` 为 `kernel-config/release/rk35xx`。因此该配置项在本项目场景中是预期行为，不是已发现的 SoC 识别错误。

### 15.3 workflow 对 build provenance 的证明范围

已读取官方 workflow commit `2031189e54e85793b281c07bbf538f4e28aaf704`：
- 默认 source 为 `ophub/linux-6.1.y-rockchip`，可选 `ophub/linux-6.12.y-rockchip`；
- 默认 `kernel_config=kernel-config/release/rk35xx`；
- workflow 的 source hash 步骤在运行时读取所选 kernel source 的 main HEAD；
- compile action 接收 source、version、config path 等输入；
- 发布资产被上传至 `kernel_rk35xx`，说明中注明非 Flippy 文件为自动编译产物。

这证明了该 workflow 的默认配置路径和构建机制，但**不能证明 2026-11-13 产生 6.12.81.tar.gz 的具体 workflow run 实际选择了哪个 source commit、哪个 config commit、哪些输入参数**。当前未取得该 run 的完整 job log/input snapshot；因此仍不能把 `661b2d8...` 和 `c23196e...` 两个候选端点写成已证实的 build lock。

### 15.4 与已验证正常的 6.1.116 基线之间的配置比较限制

6.1.116 基线记录明确为 `6.1.116-ophub`，而本次故障内核为 `6.12.81-rk35xx-ophub`。前者属于通用 mainline kernel 命名，后者明确属于 RK35xx 专用 BSP。Ophub README 区分 `kernel_stable` 通用主线与 `kernel_rk35xx` 专用 BSP；两者不可仅按内核版本号当成同一构建系列。

6.1.116 现场归档 `panther-usb-audit-...-complete-with-boot-config.tar.gz` 明确包含当时运行内核的真实 `kernel.config`，但该归档是二进制 tar.gz；当前 GitHub connector 无法以 UTF-8 文本读取该二进制归档（返回 UTF-8 decode error）。因此本轮不能直接取得归档内的 6.1.116 `.config`，也不能拿 `rk35xx/config-6.1` 模板代替 6.1.116 实际运行配置。

当前可比较的配置证据：
- 6.12 RK35xx config template：已直接读取，CPU_RK3568=y；
- 6.1 RK35xx config template：已直接读取，CPU_RK3568=y；
- 6.1.116 实际运行 kernel.config：归档存在但本轮未能从二进制包提取；
- 6.12.81 实际运行 `.config`：现场原始文件是否单独存档/是否与上述模板完全相同，尚未证实。

### 15.5 结论与研究决策

- **已排除一个误判方向：** `CONFIG_CPU_RK3568=y` 不是本次 6.12 新引入的 RK3566/RK3568 错配；RK35xx 6.1 与 6.12 模板都采用该选择，且 Panther GMAC compatible 本来就是 `rockchip,rk3568-gmac`。
- **已确认配置模板路径：** RK35xx workflow 默认使用 `kernel-config/release/rk35xx`。
- **仍未闭环：** 6.12.81 发布资产的具体构建 run 输入，以及 6.1.116/6.12.81 两个正在运行内核的真实 `.config` 逐项差异。
- **下一步不重跑设备测试：** 优先取得 6.1.116 归档内 `kernel.config` 与 6.12.81 现场实际 `.config` 的文本内容，再与相应源码 commit 对齐；重点只比较 STMMAC/DWMAC、DMA API、IOMMU、ARM64 cache、NAPI/XDP 相关项。若真实 config 与模板一致，便关闭“配置错配”支线。
- 不再继续扩大一般性 GMAC 源码比较；下一阶段重点转向真实运行 config/build provenance 和已有 RX dropped / skb allocation 路径证据。

### 来源

- Ophub kernel README（kernel_rk35xx 支持 RK3528/RK3566/RK3568，且与通用 stable 分支区分）：https://github.com/ophub/kernel
- RK35xx workflow：https://github.com/ophub/kernel/blob/2031189e54e85793b281c07bbf538f4e28aaf704/.github/workflows/compile-rockchip-rk35xx-kernel.yml
- 6.12 RK35xx config：https://github.com/ophub/kernel/blob/c23196e10d7702ee2906de4a05421d8971fb2717/kernel-config/release/rk35xx/config-6.12
- 6.1 RK35xx config：https://github.com/ophub/kernel/blob/c23196e10d7702ee2906de4a05421d8971fb2717/kernel-config/release/rk35xx/config-6.1
- 6.12 Panther DTS：https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts
- Ophub README search evidence：https://github.com/ophub/kernel
