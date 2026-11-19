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
