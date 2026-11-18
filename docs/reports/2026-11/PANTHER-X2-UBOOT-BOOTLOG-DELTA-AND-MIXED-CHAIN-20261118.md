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
