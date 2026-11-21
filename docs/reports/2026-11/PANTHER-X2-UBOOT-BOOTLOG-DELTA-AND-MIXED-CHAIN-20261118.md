# Panther X2 原版与 JP-TvBox U-Boot 启动日志差异及混合启动链审计（2026-11-18）

> 状态：只读日志、既有介质哈希、设备树静态记录与公开启动顺序资料交叉分析。
> 未执行写入、刷机、启动区修改、驱动/系统配置修改。
> 本报告只记录本轮新增结论，不重复已完成的网卡、PHY、MAC 环回及 TX/RX 测试。

## 1. 本轮最重要的新发现：实机使用了混合启动链

JP-TvBox UART 日志并没有显示 JP-TvBox SPL 正在运行。日志明确显示：

| 启动阶段 | UART 实际输出 | 对应含义 |
|---|---|---|
| SPL / DDR | `U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)` | 旧版 SPL |
| DDR loader | `DDR Version V1.13 20220218` | 旧版 DDR 初始化代码 |
| SPL 后续介质 | `Trying to boot from MMC2` | SPL 尝试从 MMC2 读取后续固件 |
| U-Boot proper | `U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)` | JP-TvBox 新版 U-Boot proper |
| U-Boot proper 板型 | `Model: Radxa ROCK3 Model C` | JP/ROCK3C 板级 FDT |
| 网卡枚举 | `Net: eth1: ethernet@fe010000` | U-Boot proper 已枚举 GMAC1 |

这与候选文件静态指纹不同：
- JP-TvBox `idbloader.img`：309,248 bytes，SHA-256 `e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`；内部字符串为 SPL 2023-11-12、DDR V1.10。
- JP-TvBox `u-boot.itb`：1,464,832 bytes，SHA-256 `a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`。
- 两文件此前已写入 TF：`idbloader.img` 位于 LBA 64，`u-boot.itb` 位于 LBA 16384；写入后回读 SHA-256 与目标文件一致。

因此，**当前这次实机启动不能记为“JP-TvBox SPL + JP-TvBox U-Boot proper”完整启动测试**。实际日志显示的是旧 SPL/DDR V1.13 + JP U-Boot proper 的混合链。

## 2. 混合启动链的来源解释

已有 eMMC 原始用户区只读审计结果：

| eMMC 原始用户区位置 | 内容 | SHA-256 |
|---|---|---|
| LBA 64 | 原版 Panther X2/E25 `idbloader.img` | `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e` |
| LBA 16384 | 原版 Panther X2/E25 `u-boot.itb` | `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af` |

这两段 eMMC 内容此前已与 Ophub Panther X2 目录的旧文件逐字节匹配。eMMC LBA 64 的 SPL 指纹为：
- `U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`
- 内嵌 FDT model：Radxa E25
- compatible：`radxa,e25`、`rockchip,rk3568`

与 JP-TvBox 实机 UART 中 SPL 的构建时间及 DDR V1.13 完全吻合。

### 2.1 与 RK3566 BootROM 启动优先级交叉核对

Rockchip《RK3566 Hardware Design Guide V1.1.0》（2022-02-06）§2.1.5 给出的 BootROM 启动优先级为：
1. SPI NOR
2. SPI NAND
3. NAND
4. eMMC
5. SDMMC

来源：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf

Rockchip 存储应用说明对 SPL 日志进一步给出编号解释：
- MMC2 对应 SD Card；
- MMC1 对应 eMMC；
- SPL 支持从 SD 卡读取后续固件，即使最初启动链由其他介质引入。

来源：https://blog.armsom.org/zh/articles/099-rockchip-storage-application/

### 2.2 最符合现有证据的启动路径

```text
RK3566 BootROM
    |
    | BootROM 优先检查 eMMC（RK3566 官方启动顺序）
    v
eMMC LBA 64
原版 idbloader / E25 SPL / DDR V1.13
    |
    | UART: Trying to boot from MMC2
    | MMC2 对应 SD/TF
    v
TF LBA 16384
JP-TvBox u-boot.itb / U-Boot proper 2023-11-12
    |
    | Model: Radxa ROCK3 Model C
    | Net: eth1: ethernet@fe010000
    v
TF /boot.scr
    |
    v
Panther X2 Linux DTB + Linux 6.12.81
```

**判断：高度吻合，尚未获得 BootROM 硬件级读取轨迹。**

理由：
- eMMC LBA 64 已确认保存旧版 E25 SPL；
- 实机 SPL 的构建时间和 DDR 版本与旧版吻合；
- RK3566 BootROM 优先尝试 eMMC，之后才是 SD；
- SPL 日志明确显示后续阶段尝试 MMC2；
- U-Boot proper 的 2023-11-12 构建时间、ROCK3C Model 与 JP-TvBox 文件吻合；
- U-Boot proper 随后从 SD/TF 的 mmc1 读取 `/boot.scr`，并加载 Panther X2 Linux 启动文件。

所以最合理的解释是：BootROM 从 eMMC 启动旧 SPL，旧 SPL 再从 TF 加载 JP U-Boot proper。TF 上写入的 JP `idbloader.img` 很可能没有被本次启动执行。

这不是已直接捕获的 BootROM 读介质事件；报告保留“高度吻合”而非“直接证实”。

## 3. 这也解释了为什么两版 U-Boot 的 Net 输出不同

此前原版 U-Boot 日志：
`Net: No ethernet found.`

JP-TvBox 实际日志：
`Net: eth1: ethernet@fe010000`

与已有设备树静态结果对照：
- 原版 E25 U-Boot control FDT 的 GMAC1：`status = "disabled"`。
- JP-TvBox SPL 内嵌 FDT 的 GMAC1：`status = "okay"`。
- 原版与 JP 的 GMAC1 reset GPIO、TX/RX delay 等板级参数也存在差异。
- JP U-Boot proper 的实际日志明确显示 `Model: Radxa ROCK3 Model C`，并且成功枚举了 `ethernet@fe010000`。

这为“原版 U-Boot proper 不绑定 GMAC1，而 JP U-Boot proper 可以绑定 GMAC1”提供了强证据。

**重要边界：** JP `u-boot.itb` 内 U-Boot proper 使用的 FIT control FDT 尚未独立完成提取；JP SPL FDT 的 `status=okay` 不能直接代替 FIT control FDT 证据。当前 `Net: eth1` 是 U-Boot proper 实机枚举结果，已经直接证明其网络设备枚举行为不同。

## 4. `eth1` 不代表 Panther X2 的第二个物理网口

- U-Boot JP 板级 FDT 将 GMAC1 作为 `ethernet1` 序号。
- 因此 U-Boot 显示 `eth1` 是其设备树 alias/序号结果。
- Panther X2 Linux 运行时 FDT 将同一个 GMAC1 配置为 `ethernet0`，所以 Linux 接口显示为 `eth0`。

两者指向同一个物理控制器 `fe010000.ethernet`，不是 U-Boot 发现了另一块网卡，也不是 Linux 网卡发生了硬件交换。

## 5. `failed to find reset-gpios property` 与 GMAC 无关

JP UART 日志在网卡枚举前后出现：
`failed to find reset-gpios property`

在 Rockchip U-Boot 源码中，完全相同的报错字符串位于：
`drivers/pci/pcie_dw_rockchip.c`

该代码调用 `gpio_request_by_name(dev, "reset-gpios", ...)` 解析 PCIe 控制器自身的复位 GPIO。它不是 GMAC 驱动，也不是 RTL8211F PHY reset 处理。

参考源码：
https://github.com/rockchip-linux/u-boot/blob/next-dev/drivers/pci/pcie_dw_rockchip.c

所以：
- 该日志不能解释为 GMAC PHY 复位失败；
- 不能据此判定 RTL8211F reset GPIO 缺失；
- 它是独立的 PCIe 设备树/复位 GPIO 问题；
- 它出现后 U-Boot 仍打印 `Net: eth1`，也与 PCIe 报错和 GMAC 枚举相互独立相符。

## 6. U-Boot 枚举网卡不等于网络链路已恢复

`Net: eth1: ethernet@fe010000` 只说明 U-Boot proper 枚举到了网络设备。

本日志没有显示：
- PHY 自动协商成功；
- U-Boot 获取到 DHCP 地址；
- U-Boot 发出/收到 DHCP 报文；
- U-Boot 通过该网卡完成网络启动。

Linux 后续启动使用 Panther X2 kernel DTB，实际 PHY/千兆链路状态应以 Linux 日志和既有实测为准。此前实测确认 JP U-Boot 启动后 Linux PHY/千兆链路正常，但 DHCP/IP 未恢复；本轮没有改变这一结论。

## 7. 其他启动日志的边界

- `Failed to load DTB, ret=-19` / `Failed to get kernel dtb, ret=-19` 出现在 U-Boot proper 自身尝试获取 FIT/kernel DTB 的路径中。随后 U-Boot 成功执行 TF 上的 `/boot.scr`，读取独立的 Panther X2 kernel DTB 并启动 Linux。因此不能把这两行解释为 Linux 最终没有设备树。
- `/dtb/rockchip/overlay/rk3566-fixup.scr` 未找到，属于启动脚本查找的可选 overlay/fixup 文件缺失；本次启动仍继续。
- `Device 0: unknown device` 是 U-Boot 设备扫描输出，不是 GMAC 探测失败证据。
- `No misc partition` 也不是网络错误。

## 8. 本轮结论与证据等级

### 已验证
- JP 实机 UART 中 SPL build time 是 2023-04-23，DDR V1.13。
- 同一日志中 U-Boot proper build time 是 2023-11-12，Model 是 Radxa ROCK3 Model C。
- JP U-Boot proper 实际枚举 `ethernet@fe010000`，序号为 eth1。
- eMMC LBA 64 与 LBA 16384 中存在原版 E25 U-Boot 文件，哈希已与旧文件匹配。
- TF 上 JP 两个文件写入后回读哈希匹配；偏移分别为 LBA 64 和 LBA 16384。
- RK3566 官方文档给出的 BootROM 优先级为 eMMC 在 SDMMC 之前。
- `failed to find reset-gpios property` 对应 Rockchip PCIe 驱动源码，而不是 GMAC 驱动。

### 高度吻合的解释
- 本次启动链为 eMMC 原版 SPL/DDR V1.13 → TF JP U-Boot proper → TF Panther X2 kernel DTB。
- 本次启动没有实际运行 JP-TvBox idbloader/SPL（DDR V1.10）。
- 原版与 JP 的 `Net` 差异主要发生在 U-Boot proper/control FDT 阶段，而不是 SPL/DDR 阶段。

### 尚未验证
- 本次上电 BootROM 实际读取 eMMC LBA 64 的直接硬件轨迹。
- JP FIT 内 U-Boot proper control FDT 的独立提取与完整属性对照。
- JP U-Boot proper 的 PHY reset/MDIO 初始化是否与 Panther X2 板级线路完全兼容。
- JP SPL/DDR V1.10 在 Panther X2 4GB LPDDR4 上的实际启动兼容性。

## 9. 下一步（不重复已完成工作）

1. 优先获取/提取 JP `u-boot.itb` 的 FIT control FDT，确认 U-Boot proper 的 GMAC1 status、alias、reset GPIO、pinctrl、clock_in_out 和 delay。
2. 对照 U-Boot proper 的 Rockchip GMAC 驱动，追踪为什么该版本能枚举 GMAC1，以及是否真的执行 PHY reset/MDIO 探测。
3. 将本次实验的标签修正为“原版 eMMC SPL + JP TF U-Boot proper”，不能标为 JP SPL 完整启动测试。
4. JP SPL/DDR V1.10 仍属于未执行候选；若未来需要验证，必须先单独设计不破坏 eMMC 的启动路径，明确介质选择和回退方式。当前不清除、不覆盖、不修改 eMMC 启动区。

本轮不重复 TF 文件写入、SHA-256 回读、MAC 环回、TX/RX、PHY、DHCP 或 hEX 抓包测试。


## 10. BootROM 优先级与 Rockchip SD Boot Card 标记的边界补充

进一步核对 Rockchip RK3566 官方《Hardware Design Guide V1.1.0》§2.1.5 与《Rockchip SD Card Boot Reference V1.2.0》（2021-04）后，补充以下关键边界：

- RK3566 Hardware Design Guide 给出的普通启动介质 BootROM 优先级为 SPI NOR、SPI NAND、NAND、eMMC、SDMMC。
- Rockchip SD Card Boot Reference 区分普通 SD 卡、SD Boot Card、SD Upgrade Card 和 SD Repair Card。
- Rockchip SD Boot Card 在 LBA 64 写入特殊 IDBLOCK boot flag；文档列出 magic `0xFCDC8C3B`，在 sector 64 + 616 bytes 处写入类型标记，boot card 的 flag 为 1。
- 该文档明确说明：SPL 会检测 SD 卡及启动标记；如果 SD 卡被识别为可启动 SD Boot Card 且包含有效固件，SPL 会优先从 SD 卡加载下一阶段。
- 文档的平台表对 RK3566/RK3568 标记支持 Android BCB 方法；传统 IDB flag 机制并非所有平台都支持，且文档说明该机制逐渐被淘汰。

来源：
- RK3566 Hardware Design Guide V1.1.0 §2.1.5：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- Rockchip SD Card Boot Reference V1.2.0：https://doc.9tripod.com/en/docs/rockchip-official-docs/MMC/Rockchip_Developer_Guide_SD_Boot_CN/

### 10.1 对本次日志的精确解释

必须区分两个阶段：
1. BootROM 选择并加载 SPL；
2. 已经运行的 SPL 决定从哪个介质加载 U-Boot proper。

UART 中的 `Trying to boot from MMC2` 是 SPL 的输出，不是 BootROM 自身的启动介质报告。它直接说明当前运行的 SPL 正尝试从 MMC2 加载后续固件；结合 MMC2=SD/TF 的既有日志映射，与“eMMC SPL → TF U-Boot proper”相符。

但仅凭这一行不能证明 BootROM 一定从 eMMC 读取 SPL。BootROM 介质选择仍须考虑 TF 卡是否被制作成 Rockchip 可启动 SD Boot Card、IDBLOCK/BCB 标记以及该芯片/ROM 版本所采用的启动策略。

### 10.2 当前结论修订

- **仍高度吻合：** 当前实机运行的 SPL 是 2023-04 / DDR V1.13 旧版本；随后由该 SPL 从 MMC2（TF/SD）加载 2023-11 JP U-Boot proper。
- **尚未直接证实：** BootROM 最初从 eMMC LBA 64 读取该 SPL。eMMC LBA 64 的镜像哈希与 SPL 内部指纹吻合，RK3566 常规 BootROM 优先级也支持该解释，但仍缺本次 TF IDBLOCK/BCB boot-card 标记的完整审计及硬件级读介质轨迹。
- **不再使用过度简化的表述：** 不能仅用“eMMC 优先于 SD”作为 BootROM 实际读取 eMMC 的唯一证明；需要同时核对 SD Boot Card 标记与 SPL 日志。

### 10.3 下一项只读取证（不要求重复已有镜像哈希）

如需进一步闭环，优先对现有 TF 卡原始 LBA 64 区域做只读检查：
- 检查 IDBLOCK magic；
- 检查 offset 616 bytes 的 boot-card flag；
- 检查 BCB/misc 分区是否包含 Rockchip SD boot/recovery 标记；
- 将实际值与 Rockchip SD Boot Reference 的定义对照。

不重写 LBA 64，不改 BCB，不改 eMMC 启动区，也不为了验证而改变启动顺序。



## 11. RK3566 SD Boot 标记机制重新判读（2026-11-18 追加勘误）

重新逐段核对 Rockchip《SD Card Boot Reference V1.2.0》后，修正第 10 节对 IDBLOCK/BCB 机制的概括，避免把“SD Boot Card”和“SD Upgrade Card”混为一谈。

### 11.1 RK3566 不支持旧式 IDBLOCK card-type flag

文档 §4 的平台支持表明确列出：
- RK3566/RK3568：IDB block flag 栏为空；Android BCB 栏为支持。
- 传统 LBA64 + 616 bytes 卡类型标记（flag 0/1/2）不是 RK3566 可依赖的机制。

因此，虽然可以只读查看 TF LBA64 + 616 bytes 的原始字节，但不能把该字段是否为 1 当作 RK3566 是否会优先从 TF 启动的判据。之前将其列为本机关键判据的建议不够准确，现予修正。

### 11.2 BCB 机制的文档语义是 SD 升级/恢复，不等同于普通 SD Boot 选择

同一文档明确说明，Android BCB 中的 `recovery\n--rk_fwupdate\n` 是 SD upgrade flag，用于进入 recovery/固件升级路径。它不能直接等同于“让 BootROM 跳过 eMMC、从 TF 执行 SPL”的普通启动优先级开关。

Rockchip 文档的 SD Boot Card、SD Upgrade Card、SD Repair Card 是不同用途。不能把 BCB 的升级标记泛化为 RK3566 的普通 SD Boot Card 启动选择标志。

### 11.3 与当前 Panther X2 TF 分区布局的关系

既有 2026-11-17 设备记录显示 TF（/dev/mmcblk0）为 GPT，仅有：
- p1：BOOT
- p2：ROOTFS

没有记录到 misc 分区。因此当前 Armbian TF 布局没有可供上述标准 Rockchip Android BCB 流程读取的 misc 分区。除非另有未记录的保留区/厂商实现，否则不能假设当前 TF 上存在 `recovery\n--rk_fwupdate\n` 标记。

### 11.4 当前最合理的启动链解释

现有直接证据仍然是：
- 实机 SPL 输出为 2023-04-23，DDR V1.13；
- eMMC LBA64 的原版 SPL 哈希与该版本指纹吻合；
- TF LBA64 和 LBA16384 的 JP 文件写入后回读哈希均曾与目标文件一致；
- 实机随后运行 2023-11-12 JP U-Boot proper；
- RK3566 Hardware Design Guide 给出的常规 BootROM 启动顺序中 eMMC 排在 SDMMC 之前。

因此，“BootROM 本次从 eMMC 选中原版 SPL，随后原版 SPL 从 TF 加载 JP U-Boot proper”仍是高度吻合的解释。当前没有证据表明 Panther X2 将启动阶段永久写死为只能从 eMMC 启动；也没有证据表明旧式 LBA64+616 flag 是本机可用的切换方法。

### 11.5 下一步研究方向修订

暂不要求用户在当前 U-Boot 暂停状态执行任何命令，也不要求断电重启。

下一步优先在离线源码侧核对：
1. 当前 eMMC 原版 SPL（2023-04-23）对应的 Rockchip SPL 源码/配置，确认它如何枚举 MMC 控制器、为何日志显示 MMC2，以及它从哪个设备/偏移加载 U-Boot proper。
2. 当前 JP idbloader 的 SPL 构建配置与板级 FDT，确认它是否具备在 Panther X2 上初始化 DDR、探测 TF 并接管启动的能力。
3. RK3566 BootROM 对 eMMC/SDMMC 的选择条件及板级启动绑带/ROM 参数；不通过改写 eMMC 或改变启动顺序来试错。

不把 LBA64 + 616 bytes 的传统 flag 作为 RK3566 决定性检查项；不写 TF/eMMC，不改 BCB，不改启动配置。


## 12. SPL MMC2 与 U-Boot proper ATAGS 编号闭环（2026-11-18 追加）

本节基于原始 UART 日志中此前未充分利用的 MMC 枚举行，以及 Rockchip U-Boot SPL/ATAGS 源码，修正“MMC2 可能对应 Linux mmc2/SDIO”的歧义。

### 12.1 实机 U-Boot proper 明确枚举 SD 为 mmc 1

原始日志实际包含：

```
no mmc device at slot 1
dwmmc@fe2b0000: 1 (SD), dwmmc@fe2c0000: 2, sdhci@fe310000: 0
Bootdev(atags): mmc 1
...
mmc1 is current device
Scanning mmc 1:1...
Found U-Boot script /boot.scr
```

直接含义：
- U-Boot proper 把 `dwmmc@fe2b0000` 枚举为 `mmc 1 (SD)`；
- `sdhci@fe310000` 枚举为 `mmc 0`，对应 eMMC；
- U-Boot proper 随后确实从 `mmc1:1` 读取 TF 卡的 `/boot.scr`。

所以本次 U-Boot proper 的 mmc1=TF/SD、mmc0=eMMC，已由本机日志直接确认，不需要再用 Linux DTS aliases 推断。

### 12.2 Rockchip SPL 的 MMC2 与 proper 的 mmc1 是不同编号体系

在 Rockchip U-Boot 源码（rockchip-linux/u-boot，commit `1c535d65b8509f388d09e49fb6961f49fda35a1d`）中：
- `arch/arm/mach-rockchip/rk_atags.c` 的 `spl_bootdev_map[]` 将 SPL 的 `BOOT_DEVICE_MMC2` 映射为 `BOOT_TYPE_SD0`；
- `BOOT_DEVICE_MMC1` 映射为 `BOOT_TYPE_EMMC`；
- `spl_perform_fixups()` 调用 `atags_set_bootdev_by_spl_bootdevice(spl_image->boot_device)`；
- `arch/arm/mach-rockchip/param.c` 的 `param_parse_atags_bootdev()` 再将 `BOOT_TYPE_SD0/SD1` 转换成 U-Boot proper 的 `mmc 1`，将 `BOOT_TYPE_EMMC` 转换成 `mmc 0`。

这与本机日志的：
- SPL：`Trying to boot from MMC2`
- U-Boot proper：`Bootdev(atags): mmc 1`
- U-Boot proper：`dwmmc@fe2b0000: 1 (SD)`
完全吻合。

Rockchip U-Boot 开发指南也说明 SPL 使用 `u-boot,spl-boot-order` 选择下一阶段存储介质，并通过 ATAGS 向 U-Boot proper 传递启动设备信息；SPL 默认可优先探测 SD，随后再探测其他介质。

### 12.3 这条 ATAGS 不能证明 BootROM 最初从哪张卡加载 SPL

源码路径很关键：`spl_perform_fixups()` 传给 ATAGS 的是 `spl_image->boot_device`，即当前 SPL 加载后续镜像所使用的设备类型；不是 `get_bootdev_by_brom_bootsource()` 读取的 BootROM 启动来源寄存器。

因此：
- `Bootdev(atags): mmc 1` 证明当前 SPL 将后续 U-Boot proper 从 SD/TF 加载；
- 它**不证明**当前 SPL 自身是由 BootROM 从 TF 加载；
- 也**不证明**当前 SPL 自身是由 BootROM 从 eMMC 加载。

这避免把“谁加载了 SPL”与“SPL 从哪里加载 U-Boot proper”混为一谈。

### 12.4 当前启动链证据等级修订

| 环节 | 当前证据 | 结论 |
|---|---|---|
| BootROM → SPL | SPL banner 为 2023-04-23 / DDR V1.13；eMMC LBA64 保存的原版 SPL 指纹与之吻合；RK3566 普通 ROM 启动优先级 eMMC 高于 SD | eMMC 来源仍高度吻合，但未直接读取 BootROM source tag/寄存器 |
| SPL → U-Boot proper | SPL 打印 MMC2；proper ATAGS 映射为 mmc1；proper 明确枚举 mmc1 为 SD，并从 mmc1 读取 TF 上文件 | **已闭环：SPL 从 TF/SD 加载 U-Boot proper** |
| U-Boot proper → Linux 启动文件 | mmc1:1 扫描并读取 /boot.scr、kernel、initrd、Panther X2 DTB | **已验证：从 TF 启动 Linux** |

最符合现有证据的整条路径仍是：
`BootROM → eMMC 上的旧 SPL/DDR V1.13 → TF 上的 JP U-Boot proper → TF 上的 Panther X2 Linux 文件`。

其中第一段仍属于高度吻合推断；第二、三段已由 SPL 日志、ATAGS、MMC 映射和文件读取日志互相印证。

### 12.5 当前现场不需要执行命令

上述闭环完全来自已有 UART 原始记录和源码，不需要用户离开当前 U-Boot 暂停状态，不需要断电、reset、boot 或重新测试。

下一步应把研究重点转向：
1. 找到旧 SPL 所用精确构建源/配置中的 Rockchip boot source 逻辑；
2. 检查 eMMC LBA64 中的原版 SPL 与 TF 上 JP idbloader 的差异，解释 BootROM 为何执行旧 SPL；
3. 若要直接确认 BootROM 来源，优先寻找该 SPL 是否打印或保留 BROM bootsource 信息；不通过写入启动区或盲目改变启动顺序来验证。

参考：
- Rockchip U-Boot 源码 `rk_atags.c`：https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/mach-rockchip/rk_atags.c
- Rockchip U-Boot 源码 `spl.c`：https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/mach-rockchip/spl.c
- Rockchip U-Boot 源码 `param.c`：https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/mach-rockchip/param.c
- Rockchip U-Boot v2017(next-dev) 开发指南 §10.3.3–10.3.4：https://download.t-firefly.com/product/Board/RK356X/Document/Developer/Rockchip_Developer_Guide_UBoot_Nextdev_CN.pdf


## 13. BootROM 与 SPL 的两级介质优先级：解释旧 SPL 从 eMMC 启动、再从 TF 取 proper（2026-11-18 追加）

本节将 RK3566 官方硬件设计指南、Rockchip SD Card Boot Reference、Rockchip U-Boot 源码和 Panther X2 实机日志放在同一启动时序中核对。

### 13.1 BootROM 的启动顺序与 SPL 的下一阶段选择不是同一件事

Rockchip《RK3566 Hardware Design Guide V1.1.0》（2022-02-06）§2.1.5 明确列出芯片复位后 BootROM 的介质优先级：Serial NOR (FSPI) → Serial NAND (FSPI) → NAND → eMMC → SDMMC。该指南适用于 RK3566，并明确写明这是芯片内部 BootROM 的自动启动顺序。当前没有 Panther X2 板级证据表明另有 SPI/NAND 启动介质，因此在本机现有 eMMC + TF 的组合下，eMMC 排在 SDMMC 前面。

### 13.2 SPL 会再次选择“从哪里加载 U-Boot proper”

Rockchip《SD Card Boot Reference V1.2.0》（2021-04）§4.2 描述了另一个阶段：SPL 初始化后查找存储设备；若 SD 卡存在且有可启动的后续固件，则优先从 SD 加载下一阶段，否则再查找其他存储设备。

Rockchip U-Boot `include/configs/rockchip-common.h` 的 proper boot target 也有明确注释：先尝试 SD（mmc index 1），再尝试 eMMC（index 0）。这属于 U-Boot proper 的启动文件扫描阶段，不能拿来代替 BootROM 的 ROM 搜索顺序。

### 13.3 与 Panther X2 实机日志吻合

现有实机记录：
- eMMC LBA64 保存的 `idbloader.img` 与 2023-04-23 SPL / DDR V1.13 的版本、时间和内嵌 Radxa E25 FDT 指纹吻合。
- 本次 SPL banner 确为 2023-04-23 / DDR V1.13。
- SPL 输出 `Trying to boot from MMC2`。
- proper 输出 `Bootdev(atags): mmc 1`，并枚举 `dwmmc@fe2b0000: 1 (SD)`。
- proper 随后从 `mmc1:1` 找到 TF 上的 `/boot.scr`。

因此，最简洁且与公开启动顺序完全一致的解释是：

```text
RK3566 BootROM
  └─ 按 ROM 顺序先从 eMMC 找到有效 IDBLOCK
       └─ 执行 eMMC LBA64 的旧 2023-04 SPL / DDR V1.13
            └─ SPL 再按自身的下一阶段策略优先选择 SD/TF
                 └─ 从 TF 加载 JP U-Boot proper
                      └─ proper 从 TF 加载 /boot.scr、内核、initrd、Panther X2 DTB
```

这解释了为什么 TF 上虽然也写入了 JP `idbloader.img`，实机仍显示旧 SPL：在 eMMC 有有效 IDBLOCK 且 BootROM 的公开优先级为 eMMC 高于 SDMMC 的情况下，BootROM 会先选中 eMMC 的 SPL；TF 上的 JP SPL 不会因为 U-Boot proper 后来从 TF 启动而自动成为本次执行的 SPL。

### 13.4 对 SD Boot flag / BCB 结论的精确限定

Rockchip SD Card Boot Reference §4.1 明确将 RK3566/RK3568 的旧式 IDB block flag 支持栏留空，而 Android BCB 栏标记为支持。§4.2 又说明旧式 flag 逐渐废弃，并区分 SD Boot Card、SD Upgrade Card、SD Repair Card。

因此不能把 LBA64+616 的旧式 flag 当成 RK3566 通用 BootROM 介质优先级开关；BCB 的 `recovery\\n--rk_fwupdate\\n` 在该文档中是 SD 升级/恢复路径标记，不是已证实可令普通 Armbian TF 卡越过 eMMC 的 BootROM 选择开关。当前 Armbian TF 仅有 BOOT/ROOTFS 两个 GPT 分区，也没有已知 Android misc 分区。

### 13.5 证据等级

| 结论 | 状态 |
|---|---|
| RK3566 BootROM 公布顺序中 eMMC 在 SDMMC 前 | 已由 Rockchip Hardware Design Guide 直接确认 |
| Rockchip SPL 可在 BootROM 启动后优先从 SD 加载 U-Boot proper | 已由 Rockchip SD Card Boot Reference 描述；与实机日志吻合 |
| 本次运行 SPL 从 TF 加载 JP U-Boot proper | 已由 SPL MMC2、ATAGS mmc1、proper 的 SD 映射和 TF 文件扫描日志闭环 |
| 本次 BootROM 实际从 eMMC 加载旧 SPL | 高度吻合推断：eMMC LBA64 二进制指纹匹配 + ROM 优先级 + SPL banner；尚无该次启动的 BROM source register 直接读数 |
| TF 上 JP SPL 本身能否独立初始化 Panther X2 DDR 并完成冷启动 | 未验证；本次实机并未执行 TF 上 JP SPL |

### 13.6 研究决策

目前不应通过清除 eMMC 启动区、改写 eMMC IDBLOCK、制作 Android SD Upgrade/Repair Card 或改变启动绑带来验证。那些做法会改变启动介质或有恢复风险，超出当前只读研究范围。

后续应继续做离线源码/二进制审计：
1. 查明 eMMC 旧 SPL 是否保留或输出 BootROM bootsource ID（Rockchip 源码定义 SRAM `BROM_BOOTSOURCE_ID_ADDR = CFG_IRAM_BASE + 0x10`，枚举中 eMMC=2、SD=5）；但不要在当前暂停现场贸然读地址，必须先确认当前 SPL/ATF 的内存映射和 U-Boot 命令能力。
2. 追踪 eMMC 旧 SPL 的板级配置、MMC 控制器映射和 DDR V1.13 参数来源。
3. 独立评估 JP SPL 的 DDR/PMIC/FDT 是否适配 Panther X2；不能因 JP proper 能在旧 SPL 环境下运行就推断 JP SPL 也能冷启动。

参考：
- Rockchip RK3566 Hardware Design Guide V1.1 §2.1.5：https://dl.xkwy2018.com/downloads/RK3568/RK356X/Hardware/Rockchip_RK3566_Hardware_Design_Guide_V1.1_EN.pdf
- Rockchip SD Card Boot Reference V1.2 §4.1–4.2：https://doc.9tripod.com/en/docs/rockchip-official-docs/MMC/Rockchip_Developer_Guide_SD_Boot_CN/
- Rockchip U-Boot `bootrom.h`（BROM bootsource IDs 与 SRAM 地址）：https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/include/asm/arch-rockchip/bootrom.h
- Rockchip U-Boot `rk_atags.c`、`spl.c`、`param.c`：见第 12 节源码链接。


## 14. BootROM bootsource SRAM 读取路径与 Radxa stable-4.19-rock3 配置核验（2026-11-18）

### 14.1 找到 Rockchip SPL 对 BootROM 来源寄存器的读取实现

在 Rockchip U-Boot 源码中确认：
- `arch/arm/include/asm/arch-rockchip/bootrom.h` 定义 BootROM source ID：eMMC=2、SD=5、SPI NOR=3、SPI NAND=4。
- 同一头文件定义 `BROM_BOOTSOURCE_ID_ADDR = CONFIG_ROCKCHIP_IRAM_START_ADDR + 0x10`。
- `arch/arm/mach-rockchip/spl.c` 的 `board_spl_was_booted_from()` 通过 `readl(BROM_BOOTSOURCE_ID_ADDR)` 读取该值，并按 `BROM_BOOTSOURCE_MASK`（新版本还处理 download bit）解析。
- 该函数用于 SPL boot-order 中 `same-as-spl` 的来源识别；它不是 U-Boot proper 默认会打印的普通启动日志。

重要限制：这是 Rockchip 通用 SPL 源码路径。不能仅凭该函数存在，就断言本机 2023-04 旧 SPL 一定包含该实现、启用了相应配置，或在当前 proper 阶段仍保留该 SRAM 内容。必须对齐 eMMC 实际旧 SPL 的精确源码版本/配置，才可决定是否能在当前 U-Boot prompt 读该地址。

### 14.2 当前 Radxa stable-4.19-rock3 defconfig 的板级配置发现

直接读取 `radxa/u-boot` 分支 `stable-4.19-rock3` 的 `configs/rock-3c-rk3566_defconfig`，文件 SHA `f7131f261fdd83d4c454577f91a455d01f6d41c3`：
- `CONFIG_ROCKCHIP_RK3568=y`（Rockchip 对 RK3566/RK3568 共用该 SoC family Kconfig 名称）。
- `CONFIG_TARGET_EVB_RK3568=y`。
- `CONFIG_DEFAULT_DEVICE_TREE="rk3566-rock-3c"`。
- 因此构建目标宏仍为 EVB RK3568，但编译时默认 U-Boot device tree 是 ROCK3 Model C；这不是 Panther X2 专用 board target/control FDT。
- `CONFIG_GMAC_ROCKCHIP=y`、`CONFIG_DM_ETH=y`，具备 GMAC 驱动编译选项。

同分支 `arch/arm/dts/rk3566-rock-3c.dts`（SHA `91a21bb2767de12e4645f60d4e25173dad2e4a73`）GMAC1 节点设置：
- `clock_in_out = "output"`；
- reset GPIO3_PC0，低有效，reset delays `<0 20000 100000>`；
- GMAC1 M1 pinctrl；
- TX delay `0x47`、RX delay `0x27`。

这些设置与 Panther X2 Linux DTS 的 M0 / input / GPIO3_PA1 / TX 0x30 / RX 0x10 仍然存在已记录差异。因此该分支是 Armbian 官方修复路线的重要候选来源，但不能直接等同于 Panther X2 专用适配。

### 14.3 关于 SPL MMC 启动选择，不从 proper 的 SD 优先策略反推

Radxa `stable-4.19-rock3` 分支 `arch/arm/mach-rockchip/spl.c` 中 `spl_boot_device()` 默认返回 `BOOT_DEVICE_MMC1`，除特定 Chromebook 或 `ROCKCHIP_BACK_TO_BROM` 配置外没有固定返回 MMC2。其 `board_spl_was_booted_from()` 可读 BROM source SRAM，但默认 `boot_devices[]` 是 weak 空表。

该分支 `rk3566-rock-3c.dts` 未找到 `/chosen/u-boot,spl-boot-order` 项。因此仅凭该分支当前可见的 SPL 源码和 DTS，不能解释本机旧 SPL 日志 `Trying to boot from MMC2`；这进一步说明不能把 Armbian 当前 Radxa 分支直接当作本机 2023-04 旧 SPL 的精确源码。需要继续追踪旧 SPL 的实际来源、构建 commit 和厂商补丁。

### 14.4 当前可做与不可做的判断

- 已确认存在通用源码读取 BootROM source ID 的路径和地址计算公式。
- 未确认本机旧 SPL 是否编入该路径、当前运行的 proper 是否使用同一 IRAM base，或 SRAM 值是否仍有效。
- 因此目前不向用户提供 `md.l` 读地址命令，不在当前暂停现场尝试读 SRAM；先离线核实 eMMC 旧 SPL 的精确构建源和 RK3566 IRAM base。
- 不要求用户断电、reset、boot，不写 TF/eMMC，不改启动参数。

源码：
- https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/include/asm/arch-rockchip/bootrom.h
- https://github.com/rockchip-linux/u-boot/blob/1c535d65b8509f388d09e49fb6961f49fda35a1d/arch/arm/mach-rockchip/spl.c
- https://github.com/radxa/u-boot/blob/stable-4.19-rock3/configs/rock-3c-rk3566_defconfig
- https://github.com/radxa/u-boot/blob/stable-4.19-rock3/arch/arm/dts/rk3566-rock-3c.dts


## 14. 关键勘误：TF 前 16 MiB 原始镜像与 JP 写入记录存在未解决矛盾（2026-11-18）

在继续推断 BootROM 从 eMMC 启动之前，重新交叉核对 `TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md` 后发现，现有证据存在必须先解决的介质状态矛盾。

### 14.1 TF 原始镜像明确包含旧版 E25 两级启动镜像的字符串

2026-11-17 从 TF 读取前 16 MiB，镜像 SHA-256：
`75c7e878c4ea78aea76fb9ecb3b037becfe413ba467603df34a4258d9688a70f`

该镜像 strings 结果中：
- `0x1109b`：`DDR Version V1.13 20220218`
- `0x3ec09`：`U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`
- `0x3f138`：`rockchip,rk3566`
- `0x4d50c`：`radxa,e25`
- `0x80007c`：FIT Image with ATF/OP-TEE/U-Boot
- `0x800848`：`rk3568-radxa-e25`
- `0x8dde8d`：`fdtfile=rockchip/rk3568-radxa-e25.dtb`
- `0x8f9cf5`：`U-Boot 2017.09-armbian (Apr 23 2023 - 13:08:07 +0000)`

LBA64 对应 byte offset 32,768；LBA16384 对应 byte offset 8,388,608。上面 SPL 字符串位于前者之后的启动镜像区域；FIT/U-Boot proper 字符串位于后者附近。因此这份 TF dump 的内容指纹与旧 E25 `idbloader.img` + 旧 E25 `u-boot.itb` 一致，而不是 JP-TvBox 两个候选文件的预期指纹。

### 14.2 与“JP 两个文件写入 TF 并回读一致”的记录冲突

另一份记录称 JP 文件曾写入 TF：
- JP idbloader SHA-256：`e8450168f8ac0b35b4ebabe901654d58d6b73cc3d24a5154ef23384339975f63`，目标 LBA64；
- JP u-boot.itb SHA-256：`a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`，目标 LBA16384；
- 当时记录回读哈希与目标文件一致。

两组结果不能同时代表同一时刻、同一张 TF 卡、同一用户区偏移的最终内容。现有仓库记录没有提供足够的时间戳/设备序列号/采集先后关系，无法判断原因究竟是：
1. 前 16 MiB dump 发生在 JP 文件写入之前；
2. JP 写入和回读操作针对了另一张 TF 卡或不同块设备；
3. JP 文件写入后又被旧镜像覆盖；
4. 记录中的设备映射或采集时间有遗漏。

以上均为可能解释，不选择其中任何一个作为事实。

### 14.3 对 BootROM 来源判断的影响：撤回“eMMC 高度吻合”的结论

此前的推断是：BootROM 从 eMMC 加载旧 SPL，再由 SPL 从 TF 加载 JP proper。现在必须撤回其第一段“eMMC 来源高度吻合”的表述，理由是：
- TF dump 本身也包含旧版 SPL 和旧版 E25 proper 的完整字符串指纹；
- 如果该 dump 代表本次启动时 TF 的真实状态，则旧 SPL 也可能直接来自 TF；
- UART 中的旧 SPL banner 只能识别运行代码版本，不能单独识别 BootROM 读取介质；
- `Trying to boot from MMC2` / ATAGS `mmc 1` 说明 SPL 后续从 SD 加载 proper，不会反向证明 SPL 最初来自 eMMC。

因此，当前可保留的结论只有：
- 已验证：某次实机日志中执行的是 2023-04 旧 SPL/DDR V1.13，并随后执行 2023-11 JP proper；
- 已验证：某次 TF 前 16 MiB 采集的内容指纹是旧 E25 SPL + 旧 E25 proper；
- 已记录但需核对介质身份/时间：JP 两个文件曾被写入并回读到目标 SHA-256；
- 未知：该次 UART 启动、TF dump、JP 写入回读是否对应同一张 TF 卡和同一时间点；
- 未知：BootROM 本次到底从 eMMC 还是 TF 加载 SPL。

### 14.4 下一步：先解决证据关联，不进行启动试错

在当前 U-Boot 暂停现场不执行任何操作。后续先从既有原始终端记录中恢复以下关联信息：
1. JP 文件写入前后对应的块设备名称、`/dev/disk/by-id` 或卡的 CID/序列号（若当时有记录）；
2. 每次 `dd` 的输入、输出、`seek`、`count`、`bs`、`oflag` 和回读哈希；
3. TF 前 16 MiB dump 的确切采集时间相对于 JP 写入时间；
4. UART JP-TvBox 启动日志对应的 TF 卡身份，以及是否发生过换卡/重写。

只有把“设备身份 + 时间顺序 + LBA64/LBA16384 内容哈希”关联起来，才能决定下一步是否需要重新只读读取当前介质。不得重复写入，不要求断电或重启，不修改 eMMC/TF。

**研究优先级调整：先闭合介质身份和时间线，再讨论 BootROM eMMC/SD 选择。此前将 BootROM eMMC 启动作为高度吻合结论的表述已撤回。**


## 15. 2026-11-18 本轮 U-Boot 暂停现场补充日志：DDR training、SPL/ATF 与 proper 网卡枚举

本节记录用户于 2026-11-18 在本轮 U-Boot 暂停现场提供的串口输出。该日志作为本次实验的原始证据补充；不将此前其他轮次日志中的内容混入本次记录。

### 15.1 本次日志可直接确认的事实

- DDR 初始化：DDR Version V1.13 20220218；LPDDR4，4096MB，CS0/CS1 双 rank，最终频率 1560MHz。
- DDR 初始化依次切换 324MHz、528MHz、780MHz、1560MHz，输出 CS0/CS1 read training、write training 和 CA training 结果；日志中未出现明确的 training failure。
- SPL：U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)；输出 Trying to boot from MMC2。
- SPL 输出 unknown raw ID phN、unrecognized JEDEC id bytes: 00, 00, 00，随后仍继续启动；具体影响尚未查明。
- SPL 对 ATF、U-Boot、FDT 等镜像的校验均显示 + OK，随后跳转到 U-Boot。
- BL31：v2.3-167-g81e0b993a-dirty，构建时间 2021-09-06；正常走到 Preparing for EL3 exit to normal world。
- BL31 报告未由 BL2 提供 OP-TEE，并出现 Error initializing runtime service opteed_fast；但之后仍成功退出 EL3 并进入 U-Boot。
- U-Boot proper：U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)，板型 Radxa ROCK3 Model C，DRAM 4 GiB。
- proper 枚举 MMC：dwmmc@fe2b0000: 1 (SD), dwmmc@fe2c0000: 2, sdhci@fe310000: 0；并显示 Bootdev(atags): mmc 1。
- proper 输出 Net: eth1: ethernet@fe010000，直接证明该 proper 阶段枚举了 GMAC 控制器 fe010000。
- autoboot 倒计时被 Ctrl+C 中断；串口采集程序累计发送 Ctrl+C 160 次，识别到 U-Boot 命令提示符后停止发送并关闭串口。
- 本次没有执行 boot、reset 或其他 U-Boot 命令；没有在本次暂停现场继续启动 Linux。

### 15.2 证据边界

1. DDR training 输出证明初始化程序完成并继续执行，不等于长时间内存稳定性测试，也不能仅凭 range 数值判定硬件裕量。
2. Trying to boot from MMC2 是 SPL 对下一阶段介质的输出；结合已有 SPL→ATAGS 源码映射和 proper 的 mmc 1 (SD) 枚举，可确认 SPL 的下一阶段选择指向 SD/TF。它不单独证明 BootROM 最初从 eMMC 还是 TF 读取 SPL。
3. Net: eth1: ethernet@fe010000 证明 U-Boot proper 枚举 GMAC1，不证明 PHY link、MDIO 探测、DHCP 或网络收发成功。
4. failed to find reset-gpios property 在既有源码审计中定位于 PCIe reset GPIO 处理，不应误归因于 GMAC PHY reset。
5. 本次日志停在 autoboot 被中断后的命令提示符，没有包含本轮从 TF 执行 /boot.scr、加载 Linux 或 DHCP 的过程。
6. unknown raw ID phN、unrecognized JEDEC id bytes: 00, 00, 00、No misc partition、FIT: No boot partition、Failed to load DTB, ret=-19、Failed to get kernel dtb, ret=-19 等信息按原样保留；具体成因或影响不在本节扩大推断。

### 15.3 本轮研究结论更新

- 已验证：本次实际运行旧 SPL/DDR V1.13，随后进入 2023-11-12 的 U-Boot proper。
- 已验证：本次 LPDDR4 4GB 初始化流程输出训练结果并继续进入 ATF/U-Boot。
- 已验证：本次 U-Boot proper 枚举 ethernet@fe010000，显示为 eth1。
- 已验证：本次 proper 把 SD 枚举为 mmc 1，ATAGS 启动设备为 mmc 1。
- 未验证：本次 BootROM 最初从 eMMC 还是 TF 加载 SPL；此前 TF 前 16 MiB dump 与 JP 写入回读记录的介质身份/时间线矛盾仍未解决。
- 未验证：DDR 长期稳定性、PHY link/MDIO、U-Boot DHCP 与实际网络收发。
- 操作状态：本轮 U-Boot 暂停现场日志已保存；后续在设备正常进入 Linux 后，再按计划只读确认 TF/eMMC 身份并采集两块介质前 16 MiB。

### 15.4 完整训练数据与串口原始关键行

以下保留本次用户粘贴的训练数值和串口关键行。原始行的字段值按用户提供内容记录。

\`\`\`text
DDR Version V1.13 20220218
ln
ddrconfig:7
LP4 MR14:0x4d
LPDDR4, 324MHz
BW=32 Col=10 Bk=8 CS0 Row=16 CS1 Row=16 CS=2 Die BW=16 Size=4096MB
tdqss: cs0 dqs0: 434ps, dqs1: 361ps, dqs2: 385ps, dqs3: 289ps,
tdqss: cs1 dqs0: 458ps, dqs1: 361ps, dqs2: 385ps, dqs3: 289ps,
change to: 324MHz
PHY drv:clk:38,ca:38,DQ:30,odt:0
vrefinner:41%, vrefout:41%
dram drv:40,odt:0
clk skew:0x58
change to: 528MHz
PHY drv:clk:38,ca:38,DQ:30,odt:0
vrefinner:41%, vrefout:41%
dram drv:40,odt:0
clk skew:0x6f
change to: 780MHz
PHY drv:clk:38,ca:38,DQ:30,odt:0
vrefinner:41%, vrefout:41%
dram drv:40,odt:0
clk skew:0x58
change to: 1560MHz(final freq)
PHY drv:clk:38,ca:38,DQ:30,odt:60
vrefinner:16%, vrefout:29%
dram drv:40,odt:80
vref_ca:00000068
clk skew:0x2

cs 0 read training:
DQS0:0x34, DQS1:0x33, DQS2:0x3a, DQS3:0x33
min: 0x10 0x11 0x13 0x10 0x1 0x5 0xb 0x5, 0xa 0xa 0x7 0x2 0x10 0xe 0x13 0x9
     0x16 0x13 0x11 0xd 0x7 0x1 0x7 0x7, 0x10 0xa 0xa 0x2 0x13 0x11 0x11 0x12
mid: 0x29 0x2a 0x2c 0x28 0x1b 0x1f 0x24 0x1e, 0x24 0x24 0x1f 0x1b 0x28 0x28 0x2b 0x24
     0x30 0x2e 0x2b 0x27 0x20 0x1c 0x20 0x21, 0x2b 0x26 0x25 0x1d 0x2e 0x2d 0x2b 0x2e
max: 0x43 0x44 0x46 0x41 0x36 0x3a 0x3d 0x37, 0x3e 0x3f 0x37 0x34 0x40 0x43 0x44 0x3f
     0x4b 0x4a 0x45 0x41 0x3a 0x38 0x39 0x3c, 0x46 0x42 0x40 0x39 0x49 0x4a 0x45 0x4a
range: 0x33 0x33 0x33 0x31 0x35 0x35 0x32 0x32, 0x34 0x35 0x30 0x32 0x30 0x35 0x31 0x36
       0x35 0x37 0x34 0x34 0x33 0x37 0x32 0x35, 0x36 0x38 0x36 0x37 0x36 0x39 0x34 0x38

cs 0 write training:
DQS0:0x58, DQS1:0x4a, DQS2:0x4e, DQS3:0x3b
min: 0xac 0xb0 0xb0 0xae 0x9e 0xa0 0xa6 0xa5 0xa7, 0x96 0x98 0x93 0x92 0x9c 0x9e 0x9e 0x9a 0x97
     0xa2 0xa0 0x9b 0x9c 0x93 0x90 0x92 0x97 0x9a, 0x8f 0x8d 0x8d 0x86 0x95 0x95 0x90 0x95 0x8d
mid: 0xc7 0xcb 0xcc 0xc8 0xb7 0xba 0xc0 0xbe 0xc0, 0xb1 0xb2 0xac 0xab 0xb4 0xb5 0xb7 0xb4 0xb0
     0xbe 0xbd 0xb6 0xb7 0xad 0xab 0xac 0xb0 0xb4, 0xab 0xa8 0xa4 0x9e 0xae 0xaf 0xa9 0xaf 0xa8
max: 0xe3 0xe6 0xe8 0xe3 0xd1 0xd5 0xdb 0xd7 0xd9, 0xcd 0xcd 0xc5 0xc4 0xcd 0xcd 0xd1 0xce 0xca
     0xda 0xda 0xd2 0xd2 0xc8 0xc6 0xc7 0xca 0xce, 0xc7 0xc3 0xbc 0xb7 0xc8 0xca 0xc3 0xc9 0xc3
range: 0x37 0x36 0x38 0x35 0x33 0x35 0x35 0x32 0x32, 0x37 0x35 0x32 0x32 0x31 0x2f 0x33 0x34 0x33
       0x38 0x3a 0x37 0x36 0x35 0x36 0x35 0x33 0x34, 0x38 0x36 0x2f 0x31 0x33 0x35 0x33 0x34 0x36

cs 1 read training:
DQS0:0x37, DQS1:0x35, DQS2:0x3b, DQS3:0x32
min: 0x11 0x13 0x15 0x13 0x3 0x7 0xa 0x6, 0x7 0x8 0x4 0x2 0xb 0xd 0x10 0xa
     0x16 0x13 0x11 0xd 0x7 0x1 0x7 0x7, 0xf 0xa 0xa 0x2 0x12 0x11 0x10 0xf
mid: 0x2c 0x2e 0x2f 0x2c 0x1e 0x22 0x26 0x20, 0x22 0x24 0x1f 0x1c 0x27 0x29 0x2b 0x25
     0x30 0x2e 0x2b 0x27 0x21 0x1c 0x20 0x22, 0x2a 0x24 0x24 0x1c 0x2c 0x2c 0x2a 0x2b
max: 0x47 0x49 0x4a 0x46 0x39 0x3d 0x43 0x3a, 0x3e 0x40 0x3a 0x36 0x44 0x45 0x46 0x41
     0x4b 0x49 0x46 0x42 0x3b 0x38 0x39 0x3e, 0x45 0x3f 0x3f 0x37 0x46 0x47 0x44 0x47
range: 0x36 0x36 0x35 0x33 0x36 0x36 0x39 0x34, 0x37 0x38 0x36 0x34 0x39 0x38 0x36 0x37
       0x35 0x36 0x35 0x35 0x34 0x37 0x32 0x37, 0x36 0x35 0x35 0x35 0x34 0x36 0x34 0x38

cs 1 write training:
DQS0:0x58, DQS1:0x4a, DQS2:0x4e, DQS3:0x3b
min: 0xac 0xb1 0xb2 0xaf 0xa0 0xa2 0xa7 0xa6 0xa7, 0x93 0x95 0x90 0x8e 0x98 0x9a 0x99 0x97 0x94
     0xa0 0x9f 0x9a 0x9a 0x91 0x8f 0x90 0x95 0x98, 0x8c 0x8b 0x8a 0x83 0x91 0x93 0x8d 0x91 0x8a
mid: 0xc8 0xcd 0xcd 0xc9 0xb9 0xbc 0xc2 0xbf 0xc1, 0xae 0xaf 0xa8 0xa5 0xb2 0xb2 0xb3 0xb0 0xad
     0xbc 0xbc 0xb6 0xb6 0xab 0xaa 0xab 0xaf 0xb1, 0xa8 0xa5 0xa1 0x9b 0xaa 0xac 0xa7 0xab 0xa5
max: 0xe5 0xe9 0xe9 0xe4 0xd3 0xd7 0xdd 0xd9 0xdb, 0xca 0xca 0xc1 0xbd 0xcd 0xcb 0xcd 0xca 0xc6
     0xd9 0xd9 0xd2 0xd2 0xc6 0xc5 0xc6 0xc9 0xcb, 0xc4 0xc0 0xb9 0xb4 0xc4 0xc6 0xc2 0xc6 0xc0
range: 0x39 0x38 0x37 0x35 0x33 0x35 0x36 0x33 0x34, 0x37 0x35 0x31 0x2f 0x35 0x31 0x34 0x33 0x32
       0x39 0x3a 0x38 0x38 0x35 0x36 0x36 0x34 0x33, 0x38 0x35 0x2f 0x31 0x33 0x33 0x35 0x35 0x36

CA Training:
cs:0 min: 0x5e 0x55 0x4c 0x45 0x4e 0x47 0x50, 0x54 0x4a 0x47 0x43 0x47 0x3e 0x4c
cs:0 mid: 0x98 0x96 0x87 0x85 0x87 0x88 0x7b, 0x8d 0x8a 0x7f 0x82 0x81 0x7f 0x78
cs:0 max: 0xd2 0xd7 0xc2 0xc6 0xc0 0xc9 0xa6, 0xc6 0xcb 0xb8 0xc1 0xbb 0xc1 0xa5
cs:0 range: 0x74 0x82 0x76 0x81 0x72 0x82 0x56, 0x72 0x81 0x71 0x7e 0x74 0x83 0x59
cs:1 min: 0x5b 0x58 0x4b 0x45 0x50 0x47 0x41, 0x55 0x4a 0x4c 0x46 0x49 0x3d 0x42
cs:1 mid: 0x96 0x98 0x85 0x85 0x8b 0x87 0x78, 0x8f 0x8b 0x85 0x84 0x82 0x7e 0x7a
cs:1 max: 0xd2 0xd8 0xbf 0xc6 0xc6 0xc8 0xb0, 0xc9 0xcd 0xbf 0xc3 0xbb 0xc0 0xb3
cs:1 range: 0x77 0x80 0x74 0x81 0x76 0x81 0x6f, 0x74 0x83 0x73 0x7d 0x72 0x83 0x71
\`\`\`

#### SPL / ATF / U-Boot proper 与暂停现场尾部

\`\`\`text
out
U-Boot SPL board init
U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)
unknown raw ID phN
unrecognized JEDEC id bytes: 00, 00, 00
Trying to boot from MMC2
## Verified-boot: 0
## Checking atf-1 0x00040000 ... sha256(5938a9cdfc...) + OK
## Checking uboot 0x00a00000 ... sha256(753e0cb3f4...) + OK
## Checking fdt 0x00b2e6f8 ... sha256(3ccee0dc53...) + OK
## Checking atf-2 0x00068000 ... sha256(0965dc8022...) + OK
## Checking atf-3 0xfdcd0000 ... sha256(be991af043...) + OK
## Checking atf-4 0xfdcc9000 ... sha256(695349eb36...) + OK
## Checking atf-5 0x00066000 ... sha256(315a4195a9...) + OK
Jumping to U-Boot(0x00a00000) via ARM Trusted Firmware(0x00040000)
Total: 405.136 ms
INFO: Preloader serial: 2
NOTICE: BL31: v2.3():v2.3-167-g81e0b993a-dirty:xsf
NOTICE: BL31: Built : 11:20:08, Sep 6 2021
INFO: GICv3 without legacy support detected.
INFO: ARM GICv3 driver initialized at EL3
INFO: pmu v1 is valid
INFO: dfs DDR fsp_param[0].freq_mhz= 1560MHz
INFO: dfs DDR fsp_param[1].freq_mhz= 324MHz
INFO: dfs DDR fsp_param[2].freq_mhz= 528MHz
INFO: dfs DDR fsp_param[3].freq_mhz= 780MHz
INFO: Using opteed sec cpu_context!
INFO: boot cpu mask: 0
INFO: BL31: Initializing runtime services
WARNING: No OPTEE provided by BL2 boot loader, Booting device without OPTEE initialization. SMCs destined for OPTEE will return SMC_UNK
ERROR: Error initializing runtime service opteed_fast
INFO: BL31: Preparing for EL3 exit to normal world
INFO: Entry point address = 0xa00000
INFO: SPSR = 0x3c9
U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)
Model: Radxa ROCK3 Model C
PreSerial: 2, raw, 0xfe660000
DRAM: 4 GiB
Sysmem: init
Relocation Offset: ed34a000
Relocation fdt: eb9f63c0 - eb9fecc8
CR: M/C/I
Using default environment
Hotkey: ctrl+c
failed to find reset-gpios property
no mmc device at slot 1
dwmmc@fe2b0000: 1 (SD), dwmmc@fe2c0000: 2, sdhci@fe310000: 0
Bootdev(atags): mmc 1
MMC1: Legacy, 52Mhz
PartType: EFI
No misc partition
boot mode: None
FIT: No boot partition
No resource partition
No resource partition
Failed to load DTB, ret=-19
Failed to get kernel dtb, ret=-19
I2c0 speed: 100000Hz
vsel-gpios- not found! Error: -2
vdd_cpu init 900000 uV
PMIC: RK8090 (on=0x40, off=0x00)
vdd_logic init 900000 uV
vdd_gpu init 900000 uV
vdd_npu init 900000 uV
io-domain: OK
Model: Radxa ROCK3 Model C
rockchip_set_serialno: could not find efuse/otp device
CLK: (sync kernel. arm: enter 816000 KHz, init 816000 KHz, kernel 0N/A)
apll 816000 KHz
dpll 780000 KHz
gpll 1188000 KHz
cpll 1000000 KHz
npll 1200000 KHz
vpll 24000 KHz
hpll 24000 KHz
ppll 200000 KHz
armclk 816000 KHz
aclk_bus 150000 KHz
pclk_bus 100000 KHz
aclk_top_high 300000 KHz
aclk_top_low 200000 KHz
hclk_top 150000 KHz
pclk_top 100000 KHz
aclk_perimid 300000 KHz
hclk_perimid 150000 KHz
pclk_pmu 100000 KHz
No misc partition
Net: eth1: ethernet@fe010000
Hit key to stop autoboot('CTRL+C'): 0
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=> <INTERRUPT>
=>
检测到疑似 U-Boot 命令提示符，停止发送。
本次发送 Ctrl+C：160 次
串口已关闭。
\`\`\`


## 16. BootROM 来源 SRAM 的 U-Boot 实机只读读取（2026-11-18）

本节记录本次在 U-Boot proper 命令提示符下完成的只读读取。它补上此前 BootROM 最初启动介质缺少直接现场证据的问题。

### 16.1 操作与原始输出

- 通过串口自动发送 Ctrl+C 中断 autoboot，脚本检测到 U-Boot 提示符后停止发送；本次累计发送 73 次 Ctrl+C。
- 进入 `=>` 提示符后，仅执行一次内存读取命令：

```text
=> md.l 0xfdcc0010 4
fdcc0010: 00000002 00000040 c08dfd97 5ef93ffc    ....@........?.^
=>
```

- 命令为 U-Boot 内存显示（memory display），读取 4 个 32-bit word；本次没有执行写内存、保存环境变量、写 MMC、启动或重置命令。
- 读取发生在 BL31 已执行、U-Boot proper 已运行之后。

### 16.2 来源字段解释

第一个 word（地址 `0xFDCC0010`）为 `0x00000002`。按此前核对的 Rockchip RK356x BootROM source 编码，`0x02` 对应 eMMC（MMC instance 0），`0x05` 对应 SD/TF（MMC instance 1）。

因此，本次现场读数支持并直接确认：**本次启动的 BootROM 来源记录指向 eMMC，而不是 TF/SD。**

这与本轮介质指纹和 SPL/U-Boot 日志相互吻合：
- BootROM 从 eMMC 启动旧版 SPL（2023-04-23 / DDR V1.13）；
- 该 SPL 输出 `Trying to boot from MMC2`；
- 后续 U-Boot proper 将 SD/TF 枚举为 `mmc 1`，并从 TF 读取启动文件。

### 16.3 SRAM 覆盖分析的结论边界

此前对 FIT 中 BL31 的静态分析发现，BL31 存在将 `0xFDCC0000–0xFDCCB000` 先备份至低地址缓冲区、再恢复回 SRAM 的代码；恢复范围包含 `0xFDCC0010`。但此前没有确认该代码路径是否在本次普通启动中执行。

现在可以确认的是：**BL31 执行之后，U-Boot proper 仍能从该地址读到有效的 eMMC 来源值 `0x02`。** 这说明该字段在本次启动结束时没有丢失或变成其他来源值。结合 BL31 的整段 SRAM 备份/恢复代码，不能简单地把“恢复范围包含该地址”解释成“来源记录必然被破坏”；恢复操作本身也可能是在保存并还原原有 SRAM 内容。

第二个 word `0x00000040` 及后两个 word 暂不解释，避免在缺少对应字段定义时猜测。

### 16.4 本轮结论更新

| 事项 | 更新后的结论 |
|---|---|
| BootROM 最初启动介质 | **已由 U-Boot 现场 SRAM 只读读数确认：eMMC（source ID 0x02）** |
| SPL 后续加载介质 | **已验证：TF/SD（MMC2，对应 proper 的 mmc 1）** |
| U-Boot proper / Linux 启动文件 | **已验证：从 TF 继续加载** |
| BL31 是否覆盖/恢复 SRAM 来源字段 | 已确认 BL31 代码存在覆盖该地址的备份/恢复范围；本次运行后读数仍为正确的 eMMC 来源值。没有必要再为此重启或重复读取。 |

本轮实验到此结束。没有写入 TF/eMMC，没有修改启动配置，也没有继续启动 Linux。


## 17. JP 完整 idbloader 的 DDR V1.10 与 Panther X2 构建先例核验（2026-11-18 追加）

本节专门核对“是否可以只把 JP-TvBox 的 idbloader.img 写入 eMMC LBA64，让 JP SPL 再从 TF/SD 加载已有 u-boot.itb”，不执行任何设备写入。

### 17.1 Panther X2 本身已有使用 DDR V1.10 的构建先例

公开 NixOS U-Boot 构建配方：
- 使用专用 `panther-x2-rk3566_defconfig`；
- `ROCKCHIP_TPL` 明确指定 `rk3566_ddr_1056MHz_v1.10.bin`；
- 同一配方还指定 BL31 `rk3568_bl31_v1.29.elf`。

来源：
https://github.com/5aaee9/nixos-aarch64/blob/02b7d0d450b906834157132fe58f11acd00e8124/packages/panther-x2-uboot/default.nix

这不是“其他 RK3566 板卡也用 V1.10”的泛化类比，而是 Panther X2 专用 defconfig 的实际构建依赖。它显著降低了 JP idbloader 所用 DDR V1.10 不适配 Panther X2 的疑虑。

### 17.2 JP idbloader 内嵌 DDR 与公开 rkbin V1.10 二进制比较

对照文件：
- JP-TvBox：Ophub U-Boot 仓库 `u-boot/rockchip/jp-tvbox/idbloader.img`，commit `8bb67df906cdc8c4e33a30e5e4d562c5cb0e32a6`，文件长度 309,248 bytes。
  https://github.com/ophub/u-boot/blob/8bb67df906cdc8c4e33a30e5e4d562c5cb0e32a6/u-boot/rockchip/jp-tvbox/idbloader.img
- 独立 DDR blob：Armbian rkbin 仓库 `rk35/rk3566_ddr_1056MHz_v1.10.bin`，commit `c5bd0dac0c9030291550aedbb3f3d7d9413ff159`，文件长度 59,392 bytes。
  https://github.com/armbian/rkbin/blob/c5bd0dac0c9030291550aedbb3f3d7d9413ff159/rk35/rk3566_ddr_1056MHz_v1.10.bin

离线二进制比较结果：
- JP idbloader 偏移 2048 处开始，与独立 DDR blob 比较；
- 59,392 bytes 中有 59,388 bytes 完全相同；
- 仅前 4 bytes 不同：JP 容器内为 ASCII `RKNS`，独立 blob 开头为 `01 00 00 14`；
- 两者 DDR 版本字符串均为 `DDR Version V1.10 20210810`。

因此可以确认：JP idbloader 内嵌的是与 Panther X2 专用构建配方指定的同一 V1.10 DDR 代码主体；仅存在 4-byte 容器/封装头差异。此结果不是仅凭版本字符串判断。

### 17.3 JP SPL 的后续介质选择与现有启动链

已闭环的 Rockchip SPL 编号映射（见本报告 §12）：
- SPL `BOOT_DEVICE_MMC2` 映射为 `BOOT_TYPE_SD0`；
- U-Boot proper 将 SD/TF 枚举为 `mmc 1`；
- 本机实机日志已证明当前 SPL 从 MMC2/SD-TF 加载后续 U-Boot proper。

JP idbloader 静态字符串中也包含 `Trying to boot from MMC2`。这与 JP SPL 使用 MMC2/SD-TF 作为后续启动介质的路径相符。JP SPL 在 Panther X2 上实际执行后的介质选择仍须由下一次串口日志确认，不能把静态字符串代替实机验证。

### 17.4 目标替换方案与范围

建议候选实验为：
1. 只将 JP-TvBox `idbloader.img` 写入 eMMC 用户区 LBA 64；
2. 不改 TF 卡；
3. JP SPL 从 TF/SD（MMC2）加载 TF 上现有的 JP `u-boot.itb`；
4. eMMC LBA 16384 的原版 `u-boot.itb`、GPT、分区、Linux 数据均不主动修改。

文件长度与扇区范围：
- JP idbloader：309,248 bytes = 604 个 512-byte sectors；
- 写入起点 LBA 64，覆盖 LBA 64–667（共 604 sectors）；
- eMMC 原版 idbloader：305,152 bytes = 596 sectors；
- eMMC 原版 u-boot.itb 起点 LBA 16384，远离本次写入范围，不会与 JP idbloader 文件长度重叠。

**写入前仍需核实原始 eMMC 备份中 LBA 660–667 这额外 8 个扇区的原始内容**，因为 JP 文件比原版长 8 sectors。不能仅凭两文件都远小于 LBA 16384 就忽略对原始间隙数据的覆盖。若该范围并非空闲/可覆盖，需先设计精确恢复办法或调整候选文件。

### 17.5 回滚与测试边界

- 双 USB-A 公头进入 Rockchip Loader、识别 eMMC、读取 eMMC：此前已实机验证。
- Loader 定点写入和写后回读尚未在本机实测；正式替换前需准备写入、回读校验和恢复步骤。
- 原版 eMMC 启动区备份及哈希记录已存在；回滚应以原始备份字节为准，不仅凭文件名或长度。
- 本节只完成离线源码/二进制核对；没有执行 eMMC 写入、重启、擦除或系统配置修改。

### 17.6 结论与状态

| 项目 | 状态 |
|---|---|
| Panther X2 专用 U-Boot 构建使用 DDR V1.10 | **已由公开构建配方确认** |
| JP idbloader 内 DDR V1.10 与该公开 blob 的代码主体一致 | **已完成离线逐字节比较，59,388/59,392 bytes 相同** |
| JP idbloader 文件长度及 LBA64 写入范围 | **已确认：604 sectors，LBA64–667** |
| JP SPL 后续从 TF/SD 启动 | **源码映射和静态字符串支持；需本机实机日志最终确认** |
| JP 完整 idbloader 在 Panther X2 上实际初始化 DDR 并进入 SPL | **尚未实测** |
| Loader 定点写入与回滚 | **尚未实测** |
| LBA660–667 原始 eMMC 数据是否可覆盖 | **待核对原始 eMMC 备份** |

**本节修订 §9 的旧建议：不再把 DDR V1.10 作为必须先做 SPL/DDR 混合的阻碍。首选实验改为完整 JP idbloader 替换；仅在写入范围审计和回滚准备完成后执行。**


## 17. UART 自动中断 autoboot 脚本的复用记录（2026-11-21 回溯补充）

本节补充此前实际使用的自动化接管方法，供后续 Boot Probe 直接复用。**不是人工观察提示后手动按键。**

### 17.1 已从历史执行记录恢复的参数

- 启动方式：在 macOS 终端通过 Python heredoc 运行，不依赖单独脚本文件：
  ```sh
  "$HOME/panther-uart-venv/bin/python" - <<'PY'
  ```
- Python 环境：`$HOME/panther-uart-venv`
- 串口库：pySerial（`import serial`）
- 串口设备：`/dev/cu.usbserial-1460`
- 波特率：1500000
- 串口格式：8N1
- 自动化动作：持续读取串口输出；识别 U-Boot 命令提示符（`=>` 或 `U-Boot>`）；在接管窗口内每 50 ms 发送一次 Ctrl+C 字节 `b'\\x03'`；最长尝试约 20 秒；检测到提示符后停止发送并关闭串口。
- 该流程先捕获 U-Boot 的 `Hit key to stop autoboot('CTRL+C'):` 倒计时，再自动发送中断字符。由于 U-Boot 可能在串口接收缓冲区/命令提示符阶段持续回显 `=> <INTERRUPT>`，不能把发送次数本身当作启动阶段数量。

### 17.2 历史测试结果

| 历史运行 | 已保存的参数差异 | 实机结果 |
|---|---|---|
| 2026-11-18 早间运行 | `timeout=0.02`、`write_timeout=1`；其余为上述串口配置 | 检测到提示符，发送 Ctrl+C 共 160 次，随后停止并关闭串口 |
| 2026-11-18 后续运行 | `timeout=0.05`；每 50 ms 发送；最多 20 秒 | 日志出现 `U-Boot prompt detected. Stopping Ctrl+C.`、`Ctrl+C sent: 73 times`、`Serial port closed.` |

两次均为自动脚本接管，不是人工手动抢按。报告 §15 已保存第一轮原始 UART 关键输出；后续运行的输出在历史对话中有记录。

### 17.3 源码归档状态与使用要求

- 已恢复脚本的启动命令、串口设备、波特率、8N1、pySerial、Ctrl+C 字节、发送间隔、最大尝试时间及提示符检测行为。
- 当前仓库尚未保存完整 heredoc 源码；不能用根据上述行为重新拼写的代码冒充原始已验证版本。应从 2026-11-18 历史对话原文取回完整代码后，再作为独立脚本归档并核对哈希。
- 在原始源码尚未归档前，后续执行应优先从历史对话原文复制已验证脚本，不要凭本节参数自行重写。
- 串口设备路径是当时 iMac 的实际设备名；换 USB-UART 适配器/USB 端口后，必须重新核实设备节点，不能盲目照搬。
- 此脚本只负责 UART 接收、检测提示符和发送 Ctrl+C，不应包含 U-Boot 存储写入命令；eMMC 仍受项目“绝不写入”硬约束。
