# Panther X2：P2 PHY 时钟责任边界与 U-Boot/Linux 初始化交接审计（2026-11-19）

## 范围与约束

本轮只做仓库历史、现有 UART/FDT 证据和精确版本源码的静态审计。没有进行 Panther 实机操作、MDIO 读取/写入、PHY reset、网络抓包、接口重启或系统配置修改。

P2 的问题：U-Boot 阶段是否留下了会影响 Linux RTL8211F / GMAC TX 的 PHY 时钟或初始化状态；Linux 接管时又会覆盖哪些状态？

## 1. U-Boot 阶段现有证据

### 1.1 两套 U-Boot 的网卡枚举结果不同

仓库已归档 UART 证据：

- 原版 E25 U-Boot proper：`Net: No ethernet found.`
- JP-TvBox U-Boot proper：`Net: eth1: ethernet@fe010000`
- JP 日志中的 `eth1` 与 Linux 的 `eth0` 指向同一个 GMAC1 控制器地址 `fe010000`，不是第二个物理网口。
- JP U-Boot proper 的实际板型字符串为 `Radxa ROCK3 Model C`；原版 control FDT 中 GMAC1 为 disabled，JP 启动日志则证明其 proper 能枚举 GMAC1。

来源：
- `PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
- `evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt`
- `PANTHER-X2-JP-IDBLOADER-BOOT-AND-DHCP-DIFF-20261119.md`

### 1.2 网卡枚举不等于 PHY 初始化或网络发送成功

JP UART 中 `Net: eth1: ethernet@fe010000` 后没有对应的 PHY link/speed、DHCP/BOOTP、TFTP 或 ping 成功记录。该行直接证明的是 U-Boot proper 枚举到 GMAC 设备，不能据此声称它启动了 PHY 自动协商、配置 PHY CLKOUT，或成功从 MDI 发出帧。

已知 Radxa U-Boot `realtek.c` 候选（commit `c55987146f4f9b20f7cb2f917ca88300419afe8d`）的 RTL8211F config 函数包含 BMCR reset、Page D08 RGMII TX delay 配置和 Page D04 LED 配置；该文件没有 Page A43 / Reg 0x19（PHYCR2）写入。**但这份源码不是当前 JP/Ophub U-Boot 二进制的可证明源码来源，不能外推为 JP binary 的确切行为。**

JP/Ophub U-Boot 当前只有二进制资产，未取得对应完整源码 commit、defconfig、FIT control FDT 与构建补丁集。因此 JP proper 是否执行 PHY driver config、是否改写 PHYCR2、是否配置 CLKOUT，均标记为未验证。

## 2. Linux 接管时的 PHY 状态重置边界

### 2.1 Linux MDIO 注册路径会先执行板级 PHY GPIO reset

已有源码审计确认 Panther 的 GMAC 使用 MDIO firmware node，`stmmac_mdio_setup()` 对该配置设置 `needs_reset=true`，MDIO bus 注册时挂接 `stmmac_mdio_reset()`。

运行时 FDT 证据：
- 6.1.116 当前正常启动基线：存在 `snps,reset-gpio`、`snps,reset-active-low`、`snps,reset-delays-us=<0 20000 100000>`。
- 6.12.81 故障启动基线：存在同语义配置，解码为 GPIO3 line 1、低有效、20ms assert / 100ms release delay。
- 6.1.116 当前正常运行时 FDT 与 6.12.81 的 reset GPIO 语义相同。此前某份 6.1.116 采集缺少该属性，已被后续完整采集纠正，不再当作版本差异。

Linux 的执行顺序为：
1. STMMAC probe 调用 `stmmac_mdio_register()`；
2. `of_mdiobus_register()` 注册 MDIO bus；
3. MDIO bus reset callback 执行（若已设置）；
4. 扫描/注册 DT 中的 PHY 设备；
5. RTL8211F driver probe 读取 PHYCR1/PHYCR2；
6. 后续 PHY config_init 执行厂商配置。

因此，按当前 Linux 源码路径，U-Boot 阶段若曾写入 PHY vendor registers，Linux MDIO bus reset 会在 PHY driver probe 前重新复位 PHY；U-Boot 的 PHY 内部寄存器状态不会被简单当作 Linux 的有效配置继承。

证据边界：运行时 FDT 和源码证明 Linux 会请求该 reset callback；尚无 GPIO 物理波形/现场时序采样证明 reset pin 实际电气动作。本报告不要求进行此类实机验证。

## 3. Linux 自己重新建立 PHY / GMAC 状态

### 3.1 RTL8211F Linux PHY driver 在两个版本均有自己的初始化流程

对照：
- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 6.12.81：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

两版 Realtek PHY driver 对 Panther PHY ID `0x001cc916` 都匹配 RTL8211F driver，并执行：
- probe 读取 PHYCR1；
- probe 读取 PHYCR2，但只缓存 CLKOUT enable bit 0；
- config_init 按 `phy-mode=rgmii` 配置 PHY 内部 TX/RX delay；
- config_init 对 PHYCR2 的 RMW mask 只有 bit 0；
- 随后执行 generic PHY software reset。

这意味着 Linux config_init 不会主动重写 PHYCR2 bit 11（125MHz CLKOUT select）或 bit 12（SSC capability select）。但软件 RMW mask 不等于芯片 reset retention 证明；reset 后硬件是否保留这些 vendor bits 仍需数据手册明确保证或只读现场证据。

### 3.2 6.1.116 与 6.1.174/6.12 的唯一已知 PHYCR2 初始化差异仍是 P1 项

按已归档精确调用顺序：
- 6.1.116：MDIO bus reset → PHY driver probe → STMMAC 的 JL2xx1 四次 MDIO 写入（包括 PHYCR2=0x1801 和 BMCR soft reset）→ 后续 PHY config_init（再次 soft reset）。
- 6.1.174 / 6.12.81：MDIO bus reset → PHY driver probe → 没有这组 STMMAC PHYCR2 workaround → 后续 PHY config_init。

因此，P2 没有发现新的 U-Boot PHYCLKOUT 初始化证据。版本间 PHYCR2 的已知差异仍是 P1 已归档的 6.1.116 Linux workaround；P1 已因 JLSemi 原始意图及 Reserved bits 语义缺少可靠证据而收口，不能在 P2 将其升级为根因。

## 4. Linux GMAC 时钟方向与 U-Boot 状态继承

已有 Panther 运行时 DT / Linux 日志确认：
- GMAC1 `phy-mode=rgmii`；
- `clock_in_out=input`；
- Linux 打印 `clock input from PHY`；
- GMAC1 的 Linux glue driver 自己执行 clock enable、RGMII GRF 配置、PHY regulator 管理和 link-up speed callback。

这说明 Linux 软件配置将 GMAC 置于外部 PHY 提供参考时钟的输入方向。RTL8211F 数据手册中的 PHY CLKOUT（可选择 125MHz）是与该方向相关的候选来源；但仅凭 `clock input from PHY` 日志，不能证明 PCB pin 35 CLKOUT 与 SoC GMAC clock input 的实际走线，也不能证明该引脚在故障版本中有正确波形。

Linux GMAC probe 会重新执行自身时钟与 GRF 初始化，因此 U-Boot GMAC 枚举状态也不能视为 Linux GMAC 时钟状态的直接继承。

## 5. P2 结论

### 已验证
1. 原版 U-Boot proper 未枚举 GMAC1；JP U-Boot proper 枚举了同一个 GMAC1。
2. JP U-Boot 的枚举日志没有证明 PHY link、PHY CLKOUT 配置或网络发送成功。
3. 当前 JP/Ophub U-Boot 缺少可核验源码 provenance；其 PHYCR2 行为未知。
4. 6.1.116 当前正常 FDT 与 6.12.81 故障 FDT 的 PHY reset GPIO 语义相同；此前旧采集造成的差异已纠正。
5. Linux MDIO 注册路径在 PHY driver probe 前调用 bus reset callback；RTL8211F driver 随后重新 probe/config_init。
6. Linux PHY config_init 对 PHYCR2 只改 bit0，不主动改 bit11/bit12。
7. Linux GMAC driver 按 `clock_in_out=input` 重新配置自身时钟/GRF 路径。

### 未验证
1. JP/Ophub U-Boot 二进制是否执行 RTL8211F PHY config，以及是否写 PHYCR2 / CLKOUT。
2. U-Boot proper 是否真正启动 PHY 自动协商；现存日志没有对应结果。
3. PHY CLKOUT pin 35 与 SoC GMAC clock input 的板级实际连接。
4. PHY reset GPIO 的现场电气波形，以及 soft reset 后 PHYCR2 bit11/bit12 的实际 retention。
5. U-Boot 阶段留下的 SoC CRU/GRF 状态是否对 Linux 启动有任何未被覆盖的副作用。

### 当前判断
**U-Boot proper 的 GMAC 枚举差异不足以解释 Linux TX 故障。** Linux 在接管时通过 MDIO bus reset 和自身 PHY/GMAC 初始化重新建立状态；因此不应把 `Net: eth1` 当作 PHY 时钟已正确配置的证据，也不应把 `Net: No ethernet found` 当作 Linux 无法工作的原因。

P2 没有找到可独立定因的 U-Boot→Linux 交接差异。PHY CLKOUT 仍是需要结合 P1 PHYCR2 差异理解的时钟候选，但缺少硅片 reset retention 与板级连线证据，不能定案。

## 6. P2 收口与下一阶段

P2 静态交接审计到此收口，不再泛查 JP U-Boot 二进制字符串或重复 U-Boot 网卡枚举基础测试。JP U-Boot 源码 provenance 只有在取得对应源码/构建元数据时才值得重新打开。

按唯一路线图转入 P3：只审计 6.1.174 与 6.12 尚未解释的 Linux GMAC 初始化差异，严格排除已经做过的：
- RGMII delay 数值与 GRF 最终值；
- PHY reset GPIO 语义；
- 普通 TX descriptor / OWN / barrier / tail pointer / DMA kick；
- MAC TE、DMA ST、MTL TXQEN 基础状态；
- 已确认不适用于 Panther 的 CSU NULL/no-op；
- GMAC clock 5ms 与 100–200µs 等待差异（已确认不解释最早 6.1.174 回归）。

P3 只允许从尚未闭环的初始化顺序、时钟父子关系/引用计数/使能错误、MDIO 注册与 PHY attach 的细微时序差异中选择一个有源码或运行时证据支撑的最小子项。任何设备读取/操作仍需用户明确授权。
