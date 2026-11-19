# Panther X2：P2 U-Boot / Linux GMAC 与 RTL8211F 时钟交接静态审计（2026-11-19）

## 范围与约束

本轮承接 P1 收口，只研究 U-Boot 与 Linux 对 GMAC1 / RTL8211F 的初始化责任和时钟方向交接。只读公开源码、既有 UART 日志和仓库报告；没有进行 Panther 实机操作、MDIO 访问、PHY reset、寄存器读写、接口重启或系统修改。

## 1. 既有事实先去重

以下项目已在此前报告中完成，本轮不重复：
- U-Boot 基础枚举差异：原版日志 `Net: No ethernet found.`；JP U-Boot proper 日志 `Net: eth1: ethernet@fe010000`。
- 启动链身份：2026-11-18 为旧 E25 SPL/DDR V1.13 + JP U-Boot proper 混合链；2026-11-19 已单独实机执行 JP SPL/DDR V1.10，后续仍进入同一 JP U-Boot proper。
- Linux GMAC1 runtime FDT：`phy-mode=rgmii`、`clock_in_out=input`、GMAC1 资源 `0xfe010000`；Linux 驱动日志为 `clock input from PHY`。
- Linux 两个源码版本的 CRU GMAC1 parent mux、DTS 外部 125MHz fixed-clock 描述相同。
- RGMII delay 数值、GRF、PHY reset GPIO 与 Linux runtime clock-names 已有独立审计。
- 6.12 CSU 对应 Panther DT 路径为 NULL/no-op；5ms 与 100–200µs 等待差异已在仓库 retrace 中降级，不再作为 P2 主线。

## 2. Radxa U-Boot 参考源码：MAC 时钟方向的实际含义

审查精确参考源码 `radxa/u-boot@c55987146f4f9b20f7cb2f917ca88300419afe8d`：

文件：
- `drivers/net/gmac_rockchip.c`
- `drivers/net/phy/realtek.c`

在 `gmac_rockchip_ofdata_to_platdata()` 中，驱动读取 GMAC 节点 `clock_in_out`：
- 字符串为 `input` 时设置 `pdata->clock_input=true`；
- 否则为 false。

在 `gmac_rockchip_probe()` 的 RGMII 分支中：
1. 执行 `clk_set_defaults(dev)`，应用 DTS 的 assigned-clocks / assigned-clock-parents / assigned-clock-rates；
2. 获取 GMAC clock；
3. 若 `clock_input=false`，调用 `clk_set_rate(..., 125000000)`，并要求返回 125MHz；
4. 调用 SoC `set_to_rgmii()` 写入 RGMII interface 和 delay 配置；
5. 进入 DesignWare EQOS 或普通 DesignWare Ethernet probe。

因此在这份 U-Boot 参考实现中，`clock_in_out` 控制的是 **GMAC 侧时钟方向/来源策略**：input 时绕过内部 GMAC clock 的 125MHz rate 设置，output 时要求内部时钟设为 125MHz。它不是对 RTL8211F PHYCR2 CLKOUT 的直接配置，也不能单凭这个属性证明 PHY pin35 实际输出了时钟。

边界：该源码是 Radxa stable-4.19-rock3 参考候选，不是已锁定的 JP-TvBox 2023 U-Boot proper 精确源码提交。不能把该实现的具体行为无条件归因于当前 JP 二进制。

## 3. 已知 Radxa U-Boot RTL8211F driver 的 PHY 初始化行为

同一参考源码的 `rtl8211f_config()`：
1. 写 BMCR `BMCR_RESET`；
2. 选择 Page `0xd08`，读取 Reg `0x11`；
3. 按 RGMII interface mode 设置/清除 RTL8211F TX delay 位；
4. 写回 Reg `0x11`，切回 Page 0；
5. 选择 Page `0xd04`，写 Reg `0x10=0x617f` 配置 LED，再切回 Page 0；
6. 调用 `genphy_config_aneg()`。

其 `rtl8211f_parse_status()` 会选择 Page `0xa43` 并读取 Reg `0x1a` 获取 link/speed/duplex 状态；在该文件中没有发现 Page `0xa43` / Reg `0x19`（PHYCR2）的写入，也没有发现 `0x1801`。

因此对该参考源码只能得出：
- U-Boot 会对 PHY 执行 BMCR reset；
- U-Boot 会按 interface mode 配置 PHY RGMII TX delay，并配置 LED；
- U-Boot 会读取 PHY Page A43 的 link status；
- 没有发现该参考驱动主动配置 PHYCR2 CLKOUT。

这不是 JP 二进制的行为证明。

## 4. Linux 接管时会重新配置 MAC 时钟方向，并重新初始化 PHY

### 4.1 MAC 侧

Panther Linux runtime DTS 的 `clock_in_out=input` 会由 Linux Rockchip GMAC glue 解析为 `clock_input=true`，并打印 `clock input from PHY`。Linux assigned-clock-parents 将外部 `gmac1_clkin`（设备树描述为 125MHz fixed-clock）选入 GMAC1 CRU parent chain。

因此即使 U-Boot proper 此前曾按 output 方向初始化 GMAC，Linux GMAC probe 仍会依据自己的 Panther X2 kernel DTB 重新应用 assigned clock parent 和 clock direction。U-Boot 的方向配置不是可以假定会原样保留到 Linux 运行态的状态。

### 4.2 PHY 侧

Linux 的 RTL8211F PHY driver 在 MDIO 扫描时 probe，后续 `rtl8211f_config_init()` 会按 Linux 的 `phy-mode=rgmii` 配置 PHY RGMII delay，并执行 PHY soft reset。故 U-Boot 曾配置的 PHY delay / PHY 基本初始化也会在 Linux PHY 初始化阶段被重新设定。

P1 已经确认：6.1.116 在 MDIO PHY probe 后另执行 JL2xx1 workaround；6.1.174/6.12 没有该组写入。此处只记录它是 Linux 接管阶段的版本差异，不重复 P1 寄存器语义。

Linux PHY driver 对 PHYCR2 的常规 config_init 仅修改 bit0；不主动设置 PHYCR2 bit11。该行为已在独立报告精确核对，本轮不再重复推导。

## 5. 启动日志能证明什么，不能证明什么

### 已验证
- JP U-Boot proper 输出 `Net: eth1: ethernet@fe010000`，证明该 U-Boot 阶段枚举了 GMAC1 网络设备。
- Linux 随后以 `fe010000.ethernet` 绑定 GMAC1，识别 RTL8211F，建立 1000Mbps Full Duplex 链路。
- Linux 明确采用 `clock input from PHY`。
- JP U-Boot proper 仍使用 ROCK3 Model C 字符串；其启动日志没有显示 U-Boot 通过 DHCP、ping 或其他网络命令完成网络收发。

### 未验证
- JP U-Boot proper 的确切源码提交、defconfig 和 FIT control FDT。
- JP U-Boot proper 实际采用的 GMAC `clock_in_out` 值。仓库已有的 JP SPL 内嵌 FDT 属性不能代替 U-Boot proper 使用的 FIT control FDT。
- U-Boot proper 是否真正启动 GMAC DMA、PHY autoneg、PHY reset 及发出网络帧；`Net:` 枚举输出本身不足以证明这些动作全部发生。
- U-Boot 退出时 pin35 CLKOUT、RGMII RXC、MAC clock mux 的真实硬件状态。
- Linux 接管前后物理时钟波形是否发生切换、是否存在无时钟间隙。

## 6. 对 P2 的阶段性结论

1. **U-Boot 与 Linux 的 GMAC 时钟方向描述存在潜在差异**：已知 JP SPL FDT 候选描述为 output，Linux Panther X2 runtime DTS 明确为 input；但 JP U-Boot proper 实际 control FDT 未被可靠提取，不能认定 proper 阶段确实使用 output。
2. Radxa U-Boot 参考驱动说明 output/input 会改变 GMAC 内部时钟 rate 配置路径；它不是 PHY CLKOUT 的直接配置。
3. 已知 Radxa RTL8211F U-Boot PHY driver 会 BMCR reset、配置 RGMII TX delay 和 LED，但没有 PHYCR2 Reg19 写入。当前 JP 二进制没有对应精确源码，故不能外推。
4. Linux probe 会按自己的 DTS 重新配置 MAC clock parent/direction，并重新初始化 PHY。U-Boot 阶段的配置并非天然保持不变。
5. 两个 Linux 版本的 CRU parent tree 与 DTS fixed-clock 定义相同；没有发现静态 clock-parent 拓扑回归。P1 的 PHYCR2 写入有无仍是 Linux 接管阶段最明确的版本差异，但其因果性尚未证实。

**本轮没有定位根因。** P2 仍有一个明确证据缺口：JP-TvBox 2023 U-Boot proper 的真实 control FDT / 精确源码 provenance 不明。现有二进制仓库只有二进制资产，之前 GitHub 大文件提取路径无法返回完整 FIT；不得用 SPL FDT 或较新的 Radxa 源码替代。

## 7. 下一步（仍限 P2，不做实机操作）

1. 仅从已有仓库资产和公开构建记录，继续确认 JP `u-boot.itb` 的 FIT configuration、U-Boot proper control FDT 来源；若没有可审计来源，明确结束该证据点，不反复尝试同一失败下载路径。
2. 对照已知 U-Boot `gmac_rockchip_probe()` 与 Linux `rk_gmac_powerup()/gmac_clk_enable()`，只追踪 clock direction / assigned parent / GRF clock selection 的接管顺序；不扩展到已完成的 RGMII delay、MAC 来源或 reset GPIO 审计。
3. 若 JP proper 的 FDT/源码仍无法取得，则把 U-Boot→Linux 时钟交接标记为“静态证据不足”，保留已知 Linux 重新配置事实，结束 P2 这条子支线，再按路线图评估 P3。

## 8. 主要来源

- Radxa U-Boot GMAC driver（参考源码）：https://github.com/radxa/u-boot/blob/c55987146f4f9b20f7cb2f917ca88300419afe8d/drivers/net/gmac_rockchip.c
- Radxa U-Boot RTL8211F driver（参考源码）：https://github.com/radxa/u-boot/blob/c55987146f4f9b20f7cb2f917ca88300419afe8d/drivers/net/phy/realtek.c
- 已有启动链差分：`PANTHER-X2-UBOOT-BOOTLOG-DELTA-AND-MIXED-CHAIN-20261118.md`
- 已有 JP SPL / DDR 实机结果：`PANTHER-X2-JP-IDBLOADER-BOOT-AND-DHCP-DIFF-20261119.md`
- Linux CRU parent / DTS fixed-clock 对照：`PANTHER-X2-RK3568-RGMII-DELAY-ORDER-AND-GMAC-CLK-PARENT-CROSSCHECK-20261119.md`
- Linux GMAC clock enable sequence：`PANTHER-X2-6.1-TO-6.12-GMAC-CLOCK-ENABLE-SEQUENCE-REGRESSION-20261119.md`
- PHY driver probe / config_init 时序：`PANTHER-X2-RTL8211F-PHYCR2-PROBE-ORDER-AND-CURRENT-UPSTREAM-CROSSCHECK-20261119.md`


## 9. 2026-11-19 追加：JP U-Boot proper 二进制来源追踪与 P2 收口

### 9.1 Ophub 二进制归档历史

通过 GitHub Contents 与 path-specific commit history 重新核对：

- 公开路径：`ophub/u-boot/u-boot/rockchip/jp-tvbox/u-boot.itb`
- 当前文件大小：1,464,832 bytes
- 当前 Git blob SHA-1：`2e453265e2e87e0ebd41897131fa6447dff4c0d1`
- 该路径的可见历史仅返回 Ophub 仓库初始导入提交 `deba7457a52acacba84689a34b1aa0d6d28a4682`，时间 2023-11-20，提交说明 `Rename firefly to firefly-rk3399`。
- 同一初始导入提交把 JP-TvBox 的 idbloader.img 和 u-boot.itb 作为二进制资产加入；提交本身没有提供对应 U-Boot 源码树、构建脚本、defconfig、.config 或源代码提交 SHA。

这只能证明 Ophub 公开二进制的归档路径与时间，不能证明二进制由 Ophub 在该提交中编译，也不能由提交时间反推源代码版本。

### 9.2 2023 JP proper 与后续 Radxa 参考代码的版本边界

- 实机 proper banner：`U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`。
- 此前使用的 Radxa 参考源码 commit `c55987146f4f9b20f7cb2f917ca88300419afe8d` 的提交时间为 2023-05-28；它可用于理解该参考分支当时的通用 Rockchip GMAC / RTL8211F 代码，但不是 JP proper 的构建来源证明。
- 上游正式 ROCK3 Model C / ROCK3C board support 补丁在 2024 年才进入公开上游讨论（2024-07/08）。因此后来的上游 ROCK3C board DTS/defconfig 不可能直接作为 2023-11 JP binary 使用该上游板级文件的证据。
- JP proper 的 `Model: Radxa ROCK3 Model C` banner 只证明运行时 FDT model 字符串，不足以识别确切 DTS 来源、代码分支或 board-specific 修改。

### 9.3 JP FIT control FDT 的证据状态

已知 JP SPL/idbloader 内嵌 FDT 是 ROCK3C，GMAC1 status=okay、clock_in_out=output、M1 pinctrl 等；但它是 SPL 阶段 FDT，不是 proper 的 FIT control FDT。

原有报告已记录：
- JP `u-boot.itb` 大文件经现有 GitHub binary fetch 路径无法取得完整 UTF-8 内容；
- 现有仓库没有独立保存的 JP FIT control FDT 提取文件或其 FIT 内 hash；
- 当前 E25 FIT 的已验证 control FDT 属于原版 E25 U-Boot，不能替代 JP FIT；
- 不应重复尝试已失败的同一路径，也不应将 SPL FDT 冒充 proper control FDT。

因此，JP proper 的 FIT configuration、U-Boot proper control FDT、实际 `clock_in_out`、GMAC1 DM enable 状态及 PHY reset/MDIO 行为，仍属证据不足。

### 9.4 P2 最终判断

**已确认：**
1. Linux Panther X2 在接管时使用自己的 runtime FDT：GMAC1 `clock_in_out=input`，外部 `gmac1_clkin` 作为时钟 parent；日志显示 `clock input from PHY`。
2. Linux probe 会按自身 DTS/clock framework 配置 GMAC1 时钟路径，并由 Linux RTL8211F PHY driver 重新执行 PHY 初始化；不能假定 U-Boot 状态原样保留。
3. 已有 6.1.174 与 6.12 源码对照未发现 GMAC1 CRU parent mux / 外部 fixed-clock 描述差异。
4. JP proper 的真实来源、FIT control FDT 与实际时钟方向无法从当前可审计公开资产确定。

**不能确认：**
- JP proper 阶段实际采用 input 还是 output；
- JP proper 是否实际 probe 并配置 GMAC1 / RTL8211F，或仅枚举了设备；
- U-Boot 交给 Linux 时 PHY CLKOUT、RGMII RXC、CRU mux 的物理状态；
- U-Boot→Linux 之间是否发生过时钟中断或方向切换。

**结论：P2 没有发现足以解释 6.1.174 最早回归的、已证实的 U-Boot→Linux 时钟交接差异。JP proper 具体行为因缺乏对应 FIT/source provenance 而证据不足。P2 到此收口，不再猜测 JP proper 内部实现。**

### 9.5 下一阶段

按唯一路线图进入 P3：只读比较 6.1.116 正常版本、6.1.174 最早异常版本和 6.12.81 持续异常版本中尚未解释的 GMAC 初始化差异。优先检查初始化先后、时钟获取/父时钟/引用计数、MDIO 注册、PHY attach 与 reset 时机；排除已审计项目，不重复普通 TX DMA、RGMII delay、MAC、PHY reset GPIO、RX/NAPI 等已完成支线。

本轮未执行 Panther 实机操作、网络测试、MDIO 访问、PHY reset 或系统修改。
