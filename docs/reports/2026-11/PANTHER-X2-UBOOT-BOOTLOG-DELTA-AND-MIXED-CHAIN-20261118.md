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
