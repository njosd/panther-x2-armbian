# Panther X2 实机启动介质、系统与软件基线调查报告

- 调查日期：2026-11-17
- 设备：Panther X2（RK3566）
- 仓库：njosd/panther-x2-armbian
- 用途：固定后续网络故障排查的实机基线，避免反复询问启动介质、U-Boot 和系统版本
- 状态：阶段性记录；只记录已取得的实机证据，不把尚未验证的内容写成事实

## 1. 结论摘要（后续排查默认采用）

1. **当前启动介质是 TF 卡，不是从 eMMC 启动。** 用户已明确说明当前 U-Boot 从 TF 卡启动；本轮还从 TF 卡 pre-partition area 读取了前 16 MiB 到临时文件并完成镜像切分与哈希核验。
2. **TF 卡中的 SPL/idbloader 与 U-Boot FIT，与此前审计的 Ophub/eMMC 参考文件逐字节一致（SHA256 一致）。** 因此，不能再把“当前 TF 卡使用另一套未知 U-Boot”作为默认假设。
3. 当前 Linux 系统为 **Armbian，运行内核 6.12.81**。此前源码对照使用的项目固定 Linux 源码提交为 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；该源码提交与运行内核构建产物之间的完整构建溯源关系仍需独立验证。
4. TF 卡 U-Boot 字符串中包含 Radxa E25/RK3568 相关标识，但这**不等于**已证明 FIT 默认启动配置实际选用了哪个 FDT，也不等于证明 U-Boot 曾成功 probe GMAC1。
5. 当前 DHCP 故障尚未归因于 U-Boot。后续重点是解析已确认身份的 `u-boot.itb`，识别默认 FIT configuration 实际引用的 U-Boot FDT，并检查其中 GMAC1 节点与 U-Boot 驱动探测路径。

## 2. 实机与启动介质

### 2.1 已确认

| 项目 | 实机调查结果 | 证据/说明 |
|---|---|---|
| 板卡 | Panther X2 | 用户持续实机调查对象 |
| SoC | Rockchip RK3566 | 板级信息、运行时设备树及 TF 启动镜像字符串均有对应证据 |
| 当前启动介质 | TF 卡 | 用户明确确认当前 U-Boot 从 TF 卡启动；本次直接读取 TF 卡前 16 MiB |
| TF 原始区域采集 | 前 16 MiB | 采集后保存为 `/tmp/panther-tf-first16m.bin` |
| 原始 16 MiB SHA256 | `75c7e878c4ea78aea76fb9ecb3b037becfe413ba467603df34a4258d9688a70f` | 用户实机输出 |
| 当前运行 Linux | Armbian | 实机 shell、运行时信息 |
| 当前运行内核 | 6.12.81 | 用户提供的实机环境/本专题调查记录 |

### 2.2 当前不能据此断言的事项

- TF 卡品牌、型号、容量、速度等级、文件系统类型及分区完整布局：**本报告现有证据未记录**。不要自行推测。
- Linux 根文件系统是否始终位于 TF 卡第一分区：尚不能仅凭 `boot.scr` 中的默认值断言。脚本默认 `rootdev=/dev/mmcblk0p1`，但会读取启动设备上的 `armbianEnv.txt` 并导入环境，最终值可能被覆盖；应以对应启动时的实际挂载信息为准。
- eMMC 是否在当前系统中存在、是否挂载、是否参与本次启动链：不能从本次 TF 启动证据推断；本报告不将 eMMC 内容视为当前实际执行文件。

## 3. TF 卡启动区与 U-Boot 身份核验

### 3.1 本次采集与切分

用户已在 Panther X2 上从既有临时采集文件切分镜像，没有重新读取 TF 卡：

```sh
dd if=/tmp/panther-tf-first16m.bin of=/tmp/tf-idbloader.img bs=512 skip=64 count=596 status=none
dd if=/tmp/panther-tf-first16m.bin of=/tmp/tf-u-boot.itb bs=512 skip=16384 count=2796 status=none
sha256sum /tmp/tf-idbloader.img /tmp/tf-u-boot.itb
```

### 3.2 SHA256 对照结果

| 文件 | TF 卡切分文件 SHA256 | 此前审计的 Ophub/eMMC 参考 SHA256 | 结论 |
|---|---|---|---|
| `idbloader.img` | `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e` | `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e` | 完全一致 |
| `u-boot.itb` | `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af` | `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af` | 完全一致 |

**判定：** 在上述切分偏移和长度所覆盖的两个启动镜像范围内，TF 卡内容与此前参考文件 SHA256 完全相同。这是当前 U-Boot 身份的强证据，不再需要重复读取 TF 卡来证明这两个镜像是否一致。

注意：哈希一致证明文件内容一致；它本身不证明 FIT 内哪个 configuration 被实际选中，也不证明 U-Boot 的 GMAC 驱动是否 probe 或 PHY/MAC 物理时序是否正确。

### 3.3 U-Boot 字符串与构建标识

此前从 TF 卡原始前 16 MiB 提取的字符串包括：

- `U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)`
- `U-Boot 2017.09-armbian`
- `rockchip,rk3566`
- `radxa,e25`、`rockchip,rk3568`、`7Radxa E25`
- `fdtfile=rockchip/rk3568-radxa-e25.dtb`
- `gmac_rockchip`、`rockchip,rk3568-gmac`
- FIT 相关字符串，包括 `U-Boot FIT Image with ATF/OP-TEE/U-Boot`

这些是镜像内字符串证据。**不能只凭字符串认定某个 FDT 是默认配置实际使用的 FDT，也不能凭驱动字符串认定 GMAC1 已经被 probe。**

## 4. boot.scr 与 Linux 启动文件

用户此前提供过 `boot.scr` 的反编译内容，已确认其启动流程特征：

1. 设置默认 `rootdev=/dev/mmcblk0p1`。
2. 从启动设备读取 `armbianEnv.txt` 并导入环境变量。
3. 获取分区 UUID。
4. 加载 `uInitrd`、`Image` 和 `${prefix}dtb/${fdtfile}`。
5. 应用 overlays 与 fixup scripts。
6. 最终执行 `booti`。

重要区分：

- `boot.scr` 是启动脚本，不是 SPL/U-Boot 本体。
- U-Boot FIT 内的 control FDT 与通过启动脚本从 TF 文件系统加载、传给 Linux 的 kernel DTB 是不同对象。
- Linux 最终使用的设备树应以运行时 FDT（例如 `/sys/firmware/fdt`）为准，不能用 U-Boot 字符串或 `boot.scr` 默认变量替代。

## 5. Linux 运行时设备树与 GMAC1 基线

### 5.1 运行时 FDT

已取得的运行时 FDT SHA256：

`c8da977cd6b65e768c2399d128b11de05941fd9a03c4d7cf405af910ceb10020`

GMAC1（MMIO `0xfe010000`）关键属性：

```dts
ethernet@fe010000 {
    phy-supply = <0x30>;
    phy-mode = "rgmii";
    pinctrl-0 = <0x7b 0x7c 0x7d 0x7e 0x7f 0x80>;
    assigned-clocks = <0x25 0x189 0x25 0x187 0x25 0x186>;
    assigned-clock-parents = <0x25 0x187 0x25 0x186 0x7a>;
    clock_in_out = "input";
    compatible = "rockchip,rk3568-gmac", "snps,dwmac-4.20a";
    rockchip,grf = <0x37>;
    snps,reset-gpio = <0x81 0x01 0x01>;
    snps,reset-active-low;
    snps,reset-delays-us = <0x00 0x4e20 0x186a0>;
    rx_delay = <0x10>;
    tx_delay = <0x30>;
};
```

- PHY 地址：0；PHY 型号：RTL8211F。
- `phy-mode = "rgmii"`，不是 `rgmii-id`。
- `tx_delay=0x30`、`rx_delay=0x10` 是 Rockchip GRF 字段配置值，不是纳秒数。
- GMAC1 pinctrl 对应 M0 组：MIIM、TX、RX、RGMII clock、clkinout、RGMII bus。
- 实机 pinmux 已确认 GMAC1 的 RX/TX、clkinout 对应 M0 pin groups。

### 5.2 Linux 初始化后的 GRF 读回

实机只读 regmap 结果：

```text
SYS_GRF base: 0xFDC60000
GRF_MAC1_CON0 offset 0x0388: 0x00001030
GRF_MAC1_CON1 offset 0x038C: 0x00000013
```

解释：

- CON0 的 RX delay 字段为 `0x10`，TX delay 字段为 `0x30`，与运行时 DT 一致。
- CON1 的 RGMII interface selection、RX/TX clock delay enable 位与 Linux 驱动配置吻合。
- 这是 Linux 初始化后的寄存器读回，不能反推 U-Boot 交接瞬间的寄存器值，也不能证明物理引脚上的 RGMII setup/hold、skew、占空比或 jitter 合格。

### 5.3 Linux 时钟树

用户提供的 `clk_summary` 显示 GMAC1 相关时钟已使能，关键频率包括：

- `gmac1_clkin`：125 MHz
- `clk_gmac1`：125 MHz
- `clk_gmac1_rgmii_speed`：125 MHz
- `clk_gmac1_rx_tx`：125 MHz
- `aclk_gmac1`：297 MHz
- `pclk_gmac1`：99 MHz

这证明 Linux clock framework 报告的时钟频率/使能状态，不等于对芯片外部引脚波形的测量。

## 6. 当前网络故障已知事实（避免重复测试）

- GMAC1 MMIO：`0xfe010000`；PHY 地址 0；RTL8211F。
- 更换网线后，千兆链路问题已解决；当前链路可协商为 1000 Mbps Full Duplex。
- hEX 未收到 Panther 发出的 DHCP 报文；其他 LAN 设备 DHCP 正常。
- Panther 本机 tcpdump 曾捕获 eth0 发出的 DHCP Discover（`0.0.0.0:68 -> 255.255.255.255:67`）。这只证明报文到达本机抓包点，不证明报文已从 PHY 引脚发送到网线上。
- NetworkManager DHCPv4 曾报告 `ip-config-unavailable`，最终只激活 IPv6。
- `eth0` 是 primary interface name；`end0/end1/enxe...` 是 alternative names。profile 绑定 eth0，现有证据不支持将接口命名视为根因。
- TX DMA 完成、PHY Link Up、千兆全双工均不能单独证明 RGMII PHY 引脚采样时序正确。

以上项目已做过的基础 DHCP 抓包、hEX 抓包、链路/网线、NetworkManager/Netplan/udev 检查，不应无理由重复。

## 7. U-Boot 来源历史：已知与待核实

- TF 卡镜像字符串包含 E25/RK3568 标识。
- 2023-04-25 Ophub issue #1319 中，最初适配者的原话是以 Armbian 主线为基础、参照 Radxa E25 修改，主要适配设备树：
  https://github.com/ophub/amlogic-s9xxx-armbian/issues/1319
- 另有 Armbian Panther X2 板级配置提交 `211ce5ede50637934b67d877ce8a00c602fae89b`，其 `panther-x2.csc` 曾包含 `BOOTCONFIG="rock-3c-rk3566_defconfig"`。该提交时间晚于 TF U-Boot banner 所示构建日期，不能据此认定当前二进制的构建配置。
- 后续 Radxa E23/E25 U-Boot 源码参考版本（commit `c55987146f4f9b20f7cb2f917ca88300419afe8d`）中的 GMAC1 参考节点有 `tx_delay=0x4f`、`rx_delay=0x26`、`clock_in_out="output"`、M1 pinctrl 等配置；该版本晚于 TF 镜像构建日期，且节点状态为 disabled。**这些值不能直接当作当前 TF U-Boot 实际使用的配置。**
- 先前对适配来源的描述曾混淆 E23 与 E25；应以 issue 原文“参照 Radxa E25 修改”为准，不再沿用“已证实借用 E23 U-Boot”的说法。

## 8. 下一步只读调查

1. 对 `/tmp/tf-u-boot.itb` 执行 `dumpimage -l`，列出 FIT images/configurations，确认默认 configuration。
2. 按默认 configuration 引用关系提取对应 FDT，而不是仅凭字符串猜测。
3. 解析该 FDT 的 GMAC1：`status`、`compatible`、`phy-mode`、`clock_in_out`、`assigned-clocks`、`assigned-clock-parents`、`pinctrl`、reset GPIO、delay。
4. 对照该 U-Boot 二进制对应源码中的 driver probe 条件与调用路径，判断 GMAC1 是否可能在 Linux 前被初始化。
5. 若要判断 PHY 侧 RGMII 时序，最终仍需物理测量 TXC/TXD/RXC/RXD；Linux 设备树和寄存器读回不能替代示波器证据。

## 9. 操作约束

- 本报告是调查基线，不授权安装软件、改配置、刷写镜像或修改启动介质。
- 后续优先只读分析，不重复已完成的基础网络测试。
- 所有结论标注“已验证 / 未验证 / 推测”；不得把软件报告的时钟、链路状态或本机抓包提升为物理层证明。
- 涉及写入 TF/eMMC、修改 U-Boot/DTB/内核、改网络配置或重启测试时，必须先明确目标设备、操作内容和影响范围并取得用户确认。

## 10. 后续对话引用规则

后续 Panther X2 网络/U-Boot 排查默认以本报告为基线：

- 当前启动介质：TF 卡。
- 当前系统：Armbian，内核 6.12.81。
- 当前 TF 启动镜像：`idbloader.img` 与 `u-boot.itb` 哈希已与此前 Ophub/eMMC 参考文件核对一致。
- Linux 最终运行时 DTB：以本报告所列 FDT SHA256 和 GMAC1 配置为当前已验证基线。
- 未完成项：FIT 默认配置/FDT 提取、U-Boot GMAC1 实际 probe 证明、RGMII 物理时序测量。

除非用户提供新的镜像、哈希、启动日志或系统变更，不再重复询问以上已确认项目。
