# Panther X2 U-Boot FIT FDT 提取调查记录

- 日期：2026-11-17
- 关联基线报告：[PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md](./PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md)
- 状态：**已成功提取并通过 FIT 内部 SHA256 验证真实 U-Boot control FDT；下一步检查 GMAC1 节点**
- 原则：只记录实机输出与源码可证实行为；不推断原始 FIT 损坏或 GMAC 配置

## 1. 输入镜像基线

TF 启动区切分得到的 `/tmp/tf-u-boot.itb` SHA256：

```text
3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af
```

FIT 文件大小：1,431,552 bytes。

FIT 默认 configuration：
- 名称：`conf`
- 描述：`rk3568-radxa-e25`
- 引用 FDT image：`fdt`

FIT 中 FDT image 元数据：
- `data-size = 0x4fc5 = 20,421 bytes`
- `data-offset = 0x157e00`
- SHA256：`e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228`

## 2. 首次 dumpimage 提取异常（实机）

用户执行 `dumpimage -T flat_dt -p 6 -o ...` 后：
- 输出文件大小 20,421 bytes。
- SHA256：`a0c4eff46050d0bd9ede8d59bc1bbc4e4cc249f6b1032e7f05f8e55d86ba9330`，与 FIT 声明 hash 不同。
- 前 12 bytes 全零；FDT magic `d0 0d fe ed` 位于文件偏移 12。
- FDT header totalsize 为 `0x4fc5`。
- `dtc` 报 `FATAL ERROR: Blob has incorrect magic number`。
- 工具版本：`dumpimage version 2025.10`。

该异常输出不是有效 DTB。直接从此文件去掉 12 bytes 会缺少 FDT 尾部 12 bytes。

## 3. FIT 节点与 header 实机证据

对原始 FIT 容器执行 `dtc -I dtb -O dts`，确认 `/images/fdt`：

```dts
fdt {
    data-size = <0x4fc5>;
    data-offset = <0x157e00>;
    description = "U-Boot dtb";
    type = "flat_dt";
    arch = "arm64";
    compression = "none";
    hash {
        value = <0xe611e583 0xd008c7b7 0x384a74c8 0x7fe5cd25
                 0x05a7838e 0x2a8ec369 0xcc3f7587 0x74948228>;
        algo = "sha256";
    };
};
```

原始 FIT header 的 totalsize 字段为 `0x9f3`。原始 FIT 文件开头以 FDT/FIT magic 开始，原始容器可以由 dtc 正常解析。

## 4. 偏移计算假设及其被实测修正

此前按 4-byte 对齐计算：
```text
ALIGN(0x9f3, 4) + 0x157e00 = 0x1587f4
                                      = 1,411,060
```

从该偏移提取 20,421 bytes 后，得到的文件仍然是 12-byte 零前缀，SHA256 仍为 `a0c4eff4...`。

进一步从原始 FIT 中观察到：
- 在偏移 1,411,060（`0x1587f4`）处，前 12 bytes 为零；
- FDT magic 位于偏移 1,411,072（`0x158800`）；
- 这比 4-byte 对齐计算结果恰好晚 12 bytes。

**因此，先前将 payload 起点算为 1,411,060 的计算假设与该 FIT 实际数据布局不符。** 不再把该偏移当成真实 payload 起点。

目前真实 payload 起点由下一节的独立 SHA256 验证确定为 `0x158800`（1,411,072）。至于为什么该 FIT 的外部数据布局在 4-byte 对齐结果之后另有 12-byte 间隔，仍需进一步结合生成该 FIT 的 mkimage 参数/实现查明；不能在没有证据时归因于 dumpimage bug、镜像损坏或某一种对齐参数。

## 5. 真实 FDT payload 已通过哈希验证（2026-11-17 实机）

用户执行：

```sh
dd if=/tmp/tf-u-boot.itb \
   of=/tmp/tf-uboot-control-raw2.dtb \
   bs=1 skip=1411072 count=20421 status=none

stat -c '%n %s bytes' /tmp/tf-uboot-control-raw2.dtb
sha256sum /tmp/tf-uboot-control-raw2.dtb
dtc -I dtb -O dts /tmp/tf-uboot-control-raw2.dtb >/dev/null
```

实机输出：
```text
/tmp/tf-uboot-control-raw2.dtb 20421 bytes
e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228  /tmp/tf-uboot-control-raw2.dtb

dtc exit code: 0
```

`dtc` 有若干关于 SPI bus、DMA、power-domain、interrupt-parent 的 warning，但退出码为 0；DTB 已成功解析。SHA256 与 FIT 节点内声明值完全一致。

**这已经证明：**
- 从 TF 卡实际启动 FIT 的 FDT payload 完整存在；
- 真实 FDT 起点为文件偏移 `1,411,072 = 0x158800`；
- 长度 20,421 bytes；
- payload 与 FIT 内部 SHA256 完全一致；
- `/tmp/tf-uboot-control-raw2.dtb` 是可用于后续分析的真实 U-Boot control FDT。

该结论不代表 FDT 配置本身正确，也尚未说明 U-Boot 是否实际 probe GMAC1。

## 6. 下一步：检查已验证 FDT 中 GMAC1 节点

后续只读取已经验证的 `/tmp/tf-uboot-control-raw2.dtb`，不需要重新读 TF 卡、重新切 FIT 或再次提取。

建议实机执行：

```sh
echo "===== VERIFIED U-BOOT CONTROL FDT: GMAC1 ====="
dtc -I dtb -O dts /tmp/tf-uboot-control-raw2.dtb |
grep -n -A85 -B12 -E 'ethernet@fe010000|gmac@fe010000'

echo "===== VERIFIED FDT ROOT COMPATIBLE ====="
dtc -I dtb -O dts /tmp/tf-uboot-control-raw2.dtb |
grep -n -A8 -B2 'compatible ='
```

重点核对 GMAC1 的：
- `status`
- `compatible`
- `phy-mode`
- `clock_in_out`
- `pinctrl-0`
- `reset-gpios` / `snps,reset-gpio`
- `assigned-clocks` / `assigned-clock-parents`
- `tx_delay` / `rx_delay`
- PHY 节点及地址。

之后还需把该 control FDT 的节点状态与对应 U-Boot driver 的 probe 机制对照。DTS 中存在节点或 driver 字符串，不等于该设备实际被 probe；尤其 `status = "disabled"` 的节点通常不会按普通 DM 设备路径 probe。

## 7. 官方源码背景与未决的 12-byte 间隔

已查阅 U-Boot 官方 v2025.10：
- `tools/fit_image.c`：`fit_image_extract()` 通过 `fit_image_get_data()` 取得 payload 地址与长度后写出。
- `boot/image-fit.c`：`fit_image_get_data()` 根据 `data-position`、`data-offset` 或内嵌 `data` 属性定位数据。

源码：
- https://github.com/u-boot/u-boot/blob/v2025.10/tools/fit_image.c
- https://github.com/u-boot/u-boot/blob/v2025.10/boot/image-fit.c

实测已确定原始 payload 起点，但 12-byte 间隔为何存在仍未查明。后续可追查 FIT 生成端的 mkimage 版本、参数及其外部数据布局规则。此项不妨碍当前使用 hash 正确的 FDT 继续分析。

## 8. 文件持久性

- `/tmp/tf-u-boot.itb`、`/tmp/tf-uboot-control.dtb`、`/tmp/tf-uboot-control-raw.dtb` 和 `/tmp/tf-uboot-control-raw2.dtb` 都是普通临时文件。
- 它们不会因为系统持续运行、网络活动或 U-Boot 已启动而自行变化。
- 除非进程显式写入/覆盖、用户修改/删除，内容应保持不变。
- `/tmp` 通常是临时目录，重启后可能清理。
- 后续分析优先复用 `/tmp/tf-uboot-control-raw2.dtb`；新提取尝试使用不同文件名。

## 9. 当前结论状态

**已验证：**
- 当前 TF FIT 整体 SHA256 与已知参考一致。
- FIT 默认 configuration 为 `rk3568-radxa-e25`。
- FIT 的 `fdt` 节点 `data-offset=0x157e00`、`data-size=0x4fc5`、内部 SHA256 如上。
- 真实 FDT payload 位于 FIT 文件偏移 `0x158800`（1,411,072）。
- 提取文件长度 20,421 bytes，SHA256 与 FIT 内部 hash 完全一致。
- 该 DTB 可由 dtc 解析（exit code 0）。

**尚未验证：**
- 12-byte 间隔的生成端原因。
- U-Boot control FDT 中 GMAC1 的完整配置（等待节点输出）。
- U-Boot 启动时 GMAC1 是否实际被 probe/初始化。
- U-Boot GMAC 初始化是否与后续 DHCP 故障存在因果关系。

**不能下的结论：**
- 不能因为 FDT 可解析就认定其 GMAC 配置正确。
- 不能因为节点存在或 driver 编入就认定 U-Boot probe 过 GMAC1。
- 不能仅凭此处的 12-byte 偏移异常认定 FIT 损坏或 dumpimage 存在 bug。

## 10. 防止重复调查

后续 Panther X2 U-Boot 调查应先读取本记录及关联基线报告。已确认的 TF 启动介质、FIT 整体哈希、默认 configuration、FDT image 元数据、真实 FDT payload 偏移、FDT 哈希、dtc 解析成功状态和工具版本不得重复询问或重新采集，除非用户报告启动介质/镜像/工具环境已变更。


## 11. 已验证 U-Boot control FDT 的 GMAC1 配置（2026-11-17）

用户对已通过 FIT SHA256 校验的 `/tmp/tf-uboot-control-raw2.dtb` 执行了完整节点输出。关键实机内容：

```dts
/ {
    compatible = "radxa,e25", "rockchip,rk3568";
    model = "Radxa E25";

    aliases {
        ethernet0 = "/ethernet@fe2a0000";
        ethernet1 = "/ethernet@fe010000";
    };

    ethernet@fe010000 {
        compatible = "rockchip,rk3568-gmac", "snps,dwmac-4.20a";
        reg = <0x00 0xfe010000 0x00 0x10000>;
        ...
        status = "disabled";
        u-boot,dm-pre-reloc;
        phy-mode = "rgmii";
        clock_in_out = "output";
        snps,reset-gpio = <0x1000005d 0x19 0x01>;
        snps,reset-active-low;
        snps,reset-delays-us = <0x00 0x4e20 0x186a0>;
        pinctrl-names = "default";
        pinctrl-0 = <0x1000005e 0x1000005f 0x10000060
                     0x10000061 0x10000062>;
        tx_delay = <0x4f>;
        rx_delay = <0x26>;
        phy-handle = <0x10000063>;
        ...
        mdio {
            compatible = "snps,dwmac-mdio";
            ...
            phy@0 {
                compatible = "ethernet-phy-ieee802.3-c22";
                reg = <0x00>;
            };
        };
    };
};
```

以上摘录中的省略号代表用户原始输出未在此重复列出，不表示节点缺少属性。

### 11.1 直接可确认的事实

- U-Boot control FDT 的根兼容字符串是 `radxa,e25`、`rockchip,rk3568`，model 是 `Radxa E25`。
- `aliases.ethernet1` 指向 GMAC1（`/ethernet@fe010000`）；alias 只提供名称/序号映射，不代表设备启用。
- Panther Linux 正在使用的 GMAC1 MMIO 地址是 `0xfe010000`，与该节点一致。
- 该 GMAC1 节点明确含有 `status = "disabled"`。
- 同一节点含有 `u-boot,dm-pre-reloc`，但该标记不是启用开关，不能覆盖 disabled 状态。
- 节点还描述了 RGMII、output clock、reset GPIO、pinctrl、delay 和 PHY 地址 0；这些只是 DT 属性，不能据此证明 U-Boot 曾实际操作它们。
- 此 control FDT 的 `tx_delay=0x4f`、`rx_delay=0x26` 与 Linux 当前运行时 DT 的 `0x30`、`0x10` 不同；但因为节点 disabled，不能把这种静态差异直接解释成 U-Boot 写入了不同 GRF 值。

### 11.2 U-Boot Driver Model 语义（源码/官方文档）

U-Boot Driver Model API 对 `ofnode_is_enabled()` 的定义是：检查节点的 `status`；若存在该属性，只有值为 `okay` 才返回 enabled；若没有 status 才按默认启用处理。U-Boot 文档亦说明 `ofnode_set_enabled()` 通过设置 status 决定节点是否可用于 Driver Model 初始化。

参考：
- U-Boot v2025.04 Driver Model API： https://docs.u-boot.org/en/v2025.04/api/dm.html
- U-Boot v2025.10 Driver Model 源码： https://github.com/u-boot/u-boot/tree/v2025.10/drivers/core
- U-Boot v2025.10 Rockchip DWC EQOS driver（仅用于区分 GMAC 控制器路径）： https://github.com/u-boot/u-boot/blob/v2025.10/drivers/net/dwc_eth_qos_rockchip.c
- U-Boot v2025.10 Rockchip GMAC driver： https://github.com/u-boot/u-boot/blob/v2025.10/drivers/net/gmac_rockchip.c

**当前合理判断：** 在标准、基于此 control FDT 的 U-Boot Driver Model 设备扫描路径中，`status = "disabled"` 的 GMAC1 节点不会作为正常启用设备绑定/初始化；`u-boot,dm-pre-reloc` 本身不改变这一点。

**判断边界：** 这不是对该二进制实际运行行为的直接观测。仍需检查 TF FIT 中 U-Boot 二进制对应的确切源码/配置，以及是否有 board-specific 代码、手工 bind、传统非-DM 驱动或 SPL/ATF 代码绕过该节点直接操作 GMAC1。不能仅凭 DTB 排除这些路径。

### 11.3 对 DHCP 故障假设的影响

这项证据显著降低了“U-Boot 标准 DM 路径按该节点初始化 GMAC1，并把 E25 的 delay/reset/pinctrl 状态交给 Linux”这一假设的可信度。

但尚不能排除：
- SPL、ATF 或更早启动阶段直接配置过 GMAC1/GRF/CRU/GPIO；
- U-Boot board code 或非-DM代码直接访问 GMAC1；
- U-Boot 对其他共享资源的配置间接影响 Linux；
- Linux 自己初始化后的 MAC/PHY 时序、DMA、收发路径问题。

因此目前不能把 DHCP 故障归因于 U-Boot，也不能据此宣告 U-Boot 与故障无关。

### 11.4 后续有针对性的只读检查

下一步不需要用户重复 FIT 提取。优先在源码侧完成：
1. 确认 FIT 中 U-Boot 二进制实际来源版本/提交，而不是用晚于 2023-04-23 的 Radxa 源码猜测。
2. 对该版本检查 `gmac_rockchip` / `dw_eth_qos`、Rockchip board init、`board_late_init`、SPL 和 ATF 是否有 GMAC1 直接寄存器访问。
3. 查明 phandle `0x1000005d` 的 GPIO provider 和 `pinctrl-0` 五个 phandle 的具体组名；不能仅凭 phandle 数字推断 bank/line。
4. 如源码没有绕过 DM 的初始化路径，再把 U-Boot GMAC1 初始化假设进一步降级，转向 Linux 接管后的收发链路与 PHY/MAC 物理时序证据。

无需为了验证 disabled 节点而在实机修改 FDT、启用 GMAC 或执行网络测试。

## 12. 当前结论状态补充（2026-11-17）

**已验证：**
- 已取得真实、哈希正确的 U-Boot control FDT。
- 根节点标识为 Radxa E25 / RK3568。
- GMAC1 节点位于 `0xfe010000`，明确 `status = "disabled"`。
- 节点同时含 `u-boot,dm-pre-reloc`；这不等于 enabled。
- GMAC1 节点声明 RGMII、output clock、reset GPIO、pinctrl、delay 0x4f/0x26、PHY address 0。

**源码语义支持的判断：**
- 标准 U-Boot DM 扫描逻辑以 status 决定节点是否 enabled；disabled 节点不会按普通启用设备路径初始化。

**尚未验证：**
- TF 中 U-Boot binary 的确切源码提交/构建配置。
- 任何 SPL/ATF/board-specific/非-DM代码是否绕过 disabled 节点直接配置 GMAC1。
- reset GPIO phandle 与 pinctrl phandle 的具体 provider/group 映射。
- U-Boot 对 GMAC1 的任何实际寄存器写入。
- U-Boot 与 Linux DHCP 故障的因果关系。

**后续分析重点修正：**
- 不再把 control FDT 中的 `tx_delay=0x4f`、`rx_delay=0x26` 或 reset GPIO 属性当作 U-Boot 已执行配置的证据。
- 不再把单纯的 E25/Linus DT 参数差异当作启动交接冲突证据。
- 先查是否存在绕过 Driver Model 的初始化代码，再决定是否继续追 U-Boot 初始化路径。

## 13. GMAC1 reset GPIO 与 pinctrl phandle 已解析（2026-11-17）

用户对已验证 FDT 执行 phandle 上下文检索，实机输出确认：

- 0x1000005d 指向 GPIO 控制器节点 gpio@fe750000。
- 0x1000005e → gmac1m1-miim。
- 0x1000005f → gmac1m1-tx-bus2。
- 0x10000060 → gmac1m1-rx-bus2。
- 0x10000061 → gmac1m1-rgmii-clk。
- 0x10000062 → gmac1m1-rgmii-bus。

GMAC1 节点引用顺序：
```dts
pinctrl-0 = <0x1000005e 0x1000005f 0x10000060
             0x10000061 0x10000062>;
```
因此它引用的是上述五个 M1 pin groups。gmac1m1-clkinout 虽在 FDT 中存在，但没有出现在这五个 pinctrl-0 phandle 中；不可把“组存在”说成“该组被该节点引用”。

### 13.1 M1 pin group 的 rockchip,pins 编码

每组 tuple 按 Rockchip pinctrl 约定表示 bank、pin、mux、配置 phandle。实机 FDT 内容：

| 组 | FDT 中的 pin tuples | 含义 |
|---|---|---|
| MIIM | <4 14 3 ...>、<4 15 3 ...> | GPIO4 pin14、pin15，mux3 |
| TX bus | <4 4 3 ...>、<4 5 3 ...>、<4 6 3 ...> | GPIO4 pin4–6，mux3 |
| RX bus | <4 7 3 ...>、<4 8 3 ...>、<4 9 3 ...> | GPIO4 pin7–9，mux3 |
| RGMII clock | <4 3 3 ...>、<4 0 3 ...> | GPIO4 pin3、pin0，mux3 |
| RGMII bus | <4 1 3 ...>、<4 2 3 ...>、<3 30 3 ...>、<3 31 3 ...> | GPIO4 pin1–2、GPIO3 pin30–31，mux3 |

这些是 FDT 描述的 M1 复用组，不是实机 pinmux 当前状态的读回。

### 13.2 Reset GPIO 的解码

GMAC1 属性：
```dts
snps,reset-gpio = <0x1000005d 0x19 0x01>;
snps,reset-active-low;
```
provider 是 gpio@fe750000，reg 为 0xfe750000，compatible 为 rockchip,gpio-bank。

解码：
- GPIO bank provider：gpio@fe750000，即 GPIO2。
- line offset：0x19 = 十进制 25。
- GPIO2 pin25 对应 GPIO2_D1（按每 bank 32 pins、A/B/C/D 每组 8 pins 编号）。
- 传统全局编号：2 × 32 + 25 = 89，即 GPIO89。
- flags cell 0x01 与节点 snps,reset-active-low 一致表达低有效复位。

这与 Linux 当前运行时 FDT 的 GMAC reset GPIO（GPIO3-1 / GPIO97）不同。两者目前只能认定为静态设备树描述差异；因为 U-Boot GMAC1 节点 status = disabled，尚无证据证明 U-Boot 实际请求或驱动过 GPIO89。

### 13.3 与 Linux 运行时 pinmux 的差异

既有实机 pinmux 输出已确认 Linux 当前 GMAC1 使用 gmac1m0-*，而此 U-Boot control FDT GMAC1 节点引用 gmac1m1-*。这确认两份设备树的静态 pinmux 方案不同。

但须保持证据边界：
- U-Boot control FDT 节点 status = disabled。
- u-boot,dm-pre-reloc 不是启用状态，也不证明 pinctrl 被应用。
- 当前 Linux pinmux 读回证明 Linux 接管后 M0 已生效，不可反推 U-Boot 早期阶段从未短暂设置过 M1。
- 是否存在 SPL、ATF、board-specific 或非-DM代码直接设置 M1/GRF/GPIO89，仍需源码核对。

### 13.4 对故障调查的意义

新增事实使“U-Boot FDT 中 GMAC1 的静态硬件接线描述与 Panther Linux 实际使用方案不一致”成为已验证结论；但“U-Boot 真正把 GMAC1 配成 M1、GPIO89 reset、0x4f/0x26 delay”仍未验证。

因此接下来应优先做源码路径审计：检查对应 U-Boot 构建的 SPL、Rockchip board init、pinctrl、GMAC driver，以及可能的直接 GRF/CRU/GPIO 寄存器访问。不要为此修改实机配置或重复 DHCP 测试。
## 14. 找到 U-Boot Vendor MAC → Linux FDT 的完整源码路径（2026-11-17）

本节使用在当前 FIT 构建时间（2023-04-23）之前已提交的 Rockchip U-Boot 参考源码：
- Rockchip U-Boot commit `8af253525b7de5f29f7f97dffd18adb77db6456a`，committer date 2023-03-23。
- 对照源码文件均取自该 commit，而不是使用晚于 FIT 构建时间的当前主线。

### 14.1 U-Boot 在 board_late_init 中读取 Vendor MAC

`arch/arm/mach-rockchip/board.c` 在该提交中已有：
```c
int board_late_init(void)
{
#ifdef CONFIG_ROCKCHIP_SET_ETHADDR
    rockchip_set_ethaddr();
#endif
    ...
}
```
`rockchip_set_ethaddr()`：
- 读取 `LAN_MAC_ID`，缓冲区容量为两个 Ethernet MAC（`MAX_ETHERNET = 2`）。
- 调用 `vendor_storage_read(LAN_MAC_ID, ethaddr, sizeof(ethaddr))`。
- 若读取失败或地址无效，生成随机 MAC；启用 Vendor Partition 时将 MAC 写回 Vendor Storage。
- 将第一个 MAC 写入 U-Boot 环境变量 `ethaddr`，第二个写入 `eth1addr`。

同一提交的 `arch/arm/mach-rockchip/Kconfig` 中 `CONFIG_ROCKCHIP_SET_ETHADDR` 默认 `y`。`CONFIG_ROCKCHIP_VENDOR_PARTITION` 取决于 `RKIMG_BOOTLOADER`。当前二进制的精确 `.config` 尚未从二进制直接恢复；但用户此前已实机确认当前 U-Boot 读取的是 TF 卡上的 Vendor Storage，而不是 eMMC Vendor Storage。

### 14.2 Vendor Storage 绑定当前启动设备，而非固定 eMMC

同一提交 `arch/arm/mach-rockchip/vendor.c` 的 `vendor_ops()` 调用 `rockchip_get_bootdev()`，然后依据所返回设备的 `if_type` 选择 Vendor Storage 地址。
`arch/arm/mach-rockchip/boot_rkimg.c` 的 `rockchip_get_bootdev()` 使用 `devtype` 和 `devnum` 环境变量获取 block device；同一文件 `get_bootdev_type()` 明确规定 MMC `devnum=1` 的 boot media 为 `sd`，MMC `devnum=0` 为 `emmc`。

因此，若启动设备识别为 MMC 1/SD，Vendor Storage 读写就落在该 SD/TF 启动设备。它不会自动转去 eMMC 读取板载 MAC。此源码机制与用户已确认的 TF Vendor Storage 读取结果一致。

### 14.3 U-Boot 会把环境 MAC 写入传给 Linux 的设备树

同一提交 `common/image-fdt.c` 的 Linux FDT setup 路径调用 `fdt_fixup_ethernet(blob)`。`common/fdt_support.c` 中该函数：
- 遍历 Linux DTB 的 `/aliases` 中 `ethernet*` 属性；
- 读取相应 U-Boot 环境变量（根据 `FDT_SEQ_MACADDR_FROM_ENV` 配置选择 `ethaddr`/`eth1addr` 等）；
- 通过 `do_fixup_by_path()` 将 MAC 写入对应节点的 `mac-address` 和 `local-mac-address`。

因此，U-Boot 读取到的 Vendor MAC 不只停留在 U-Boot 环境中；在标准 Linux FDT setup 路径中，它可以被写入即将交给 Linux 的 kernel DTB。

### 14.4 Panther X2 的 Linux DTB alias 使这条路径直接指向 GMAC1

项目固定内核源码 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 中 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts` 明确：
```dts
aliases {
    ethernet0 = &gmac1;
    mmc0 = &sdmmc0;
    mmc1 = &sdhci;
    mmc2 = &sdmmc1;
};
```
且 `&gmac1` 为 `status = "okay"`，没有在该节点中静态定义 `local-mac-address` 或 `mac-address`。

这意味着在这份 Panther X2 kernel DTB 上，U-Boot 的 `fdt_fixup_ethernet()` 会按 `ethernet0` alias 把对应环境 MAC 写到 GMAC1 节点。若 `FDT_SEQ_MACADDR_FROM_ENV` 开启，代码会按其序号规则选择 `eth1addr`；若未开启，则通常按 `ethernet0` 选择 `ethaddr`。两者均由 `rockchip_set_ethaddr()` 从同一启动设备的 Vendor Storage 读取/生成。

### 14.5 当前因果判断

**源码机制已建立：** TF 启动设备 → Rockchip Vendor Storage 读取 → U-Boot 环境 `ethaddr`/`eth1addr` → Linux FDT `ethernet0` alias → Panther X2 GMAC1 的 `local-mac-address`/`mac-address`。

**与用户实机现象高度吻合：** 用户已确认 eMMC 中保存的板载 MAC 与 U-Boot 从 TF 读取到的 MAC 来源不同。该机制可解释为什么 Linux 最终使用的 MAC 可能不是 eMMC 中的板载 MAC。

**仍需实机闭环：** 需要将 `/sys/firmware/fdt` 中 `/aliases/ethernet0`、GMAC1 的 `mac-address`/`local-mac-address` 与 `ip link` 的 eth0 MAC 对照，并与 TF Vendor Storage MAC/eMMC 板载 MAC 比较。若运行时 FDT 的 GMAC1 MAC 等于 TF Vendor MAC，而不等于 eMMC 板载 MAC，即可直接证实 U-Boot FDT fixup 影响了 Linux 最终 MAC。

**重要限制：** 错误/不同的 source MAC 本身并不能自动解释 DHCP Discover 未到达 hEX。普通以太网帧允许使用合法的本地管理单播源 MAC；即使 MAC 与 eMMC 板载值不同，也不必然阻止 DHCP 广播发出或被交换机接收。因此这条路径首先解释 MAC 来源错位，不能未经进一步证据就宣布它是 DHCP 丢包根因。

### 14.6 源码链接与版本边界

- `board.c`（2023-03-23 之前已提交的代码）：https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456a/arch/arm/mach-rockchip/board.c
- `vendor.c`：https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456a/arch/arm/mach-rockchip/vendor.c
- `boot_rkimg.c`：https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456a/arch/arm/mach-rockchip/boot_rkimg.c
- `common/fdt_support.c`：https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456a/common/fdt_support.c
- `common/image-fdt.c`：https://github.com/rockchip-linux/u-boot/blob/8af253525b7de5f29f7f97dffd18adb77db6456a/common/image-fdt.c
- Panther X2 6.12 DTS：项目固定源码 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，文件 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`。

注意：另一个 commit `b3372aa61eccf92db6a5461674e70854344cacd2` 虽在 GitHub history 中显示 author date 2023-04-11，但 committer date 为 2023-11-13，晚于当前 FIT 构建日期；不应把它当作 2023-04-23 前已发布的代码依据。本节改以 2023-03-23 前已提交的 `8af253...` 版本为依据。

## 15. Linux 实际运行 FDT 的 GMAC1 alias 与 MAC 已闭环（2026-11-17）

用户对当前运行时 FDT（/sys/firmware/fdt）及 Linux 接口执行只读检查，实机输出：

~~~dts
/ {
    aliases {
        ethernet0 = "/ethernet@fe010000";
        ...
    };

    ethernet@fe010000 {
        local-mac-address = [e6 e0 02 b2 71 f9];
        compatible = "rockchip,rk3568-gmac", "snps,dwmac-4.20a";
        reg = <0x00 0xfe010000 0x00 0x10000>;
        ...
        status = "okay";
        ...
        clock_in_out = "input";
        phy-mode = "rgmii";
        ...
    };
};
~~~

Linux interface 输出：

~~~text
eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
link/ether e6:e0:02:b2:71:f9
parentdev fe010000.ethernet
altname end0
altname enxe6e002b271f9
~~~

### 15.1 直接证实的事实

- Linux 运行时 FDT 的 aliases.ethernet0 指向 GMAC1（/ethernet@fe010000）。
- GMAC1 节点的 local-mac-address 是 e6:e0:02:b2:71:f9。
- Linux 的 eth0 当前 MAC 同样是 e6:e0:02:b2:71:f9。
- eth0 的 parent device 是 fe010000.ethernet，确认接口就是该 GMAC1。
- 因此运行时 FDT 中的 GMAC1 MAC 与 Linux 实际接口 MAC 完全一致；这不是仅看接口名称推测出来的关系。

### 15.2 与已验证 U-Boot control FDT 的对照

U-Boot control FDT（FIT 内 SHA256 已验证）描述：
- 根节点为 Radxa E25 / RK3568。
- aliases.ethernet1 = "/ethernet@fe010000"。
- GMAC1 节点 status = "disabled"。
- GMAC1 pinctrl 为 M1、clock_in_out 为 output、delay 为 0x4f/0x26。

Linux 实际运行 FDT 描述：
- aliases.ethernet0 = "/ethernet@fe010000"。
- GMAC1 节点 status = "okay"。
- GMAC1 pinctrl 为 M0、clock_in_out 为 input、delay 为 0x30/0x10。
- GMAC1 local-mac-address 为 e6:e0:02:b2:71:f9。

这说明 U-Boot control FDT 与传给 Linux 的运行时 FDT 不是同一份原样配置；Linux 启动时使用的是 Panther X2 kernel DTB，并且 MAC 属性已存在于最终运行时 FDT。不能把 control FDT 中的 disabled/M1/output/delay 属性直接套用到 Linux 当前 GMAC1。

### 15.3 与 U-Boot Vendor MAC fixup 源码路径的关系

第 14 节已建立 Rockchip U-Boot 的源码路径：读取当前启动介质 Vendor Storage → 写入 U-Boot 环境 ethaddr/eth1addr → Linux FDT setup 中按 kernel DTB 的 /aliases/ethernet* 进行 MAC fixup。

本次输出进一步闭环了该路径的后半段：
- Panther X2 kernel DTB 的运行时 alias 将 ethernet0 指向 GMAC1；
- 运行时 GMAC1 节点含 local-mac-address=e6:e0:02:b2:71:f9；
- Linux eth0 实际采用同一个 MAC。

**边界：** 这证明最终 FDT MAC 属性与接口 MAC 一致；单独这一份运行时输出仍不能证明该值究竟由 U-Boot fdt_fixup_ethernet() 写入、由其他 boot script/fixup 写入，还是由其他早期路径注入。结合第 14 节的源码机制和 kernel DTS 中没有静态 MAC 的事实，U-Boot Vendor MAC fixup 是目前有源码依据且与现象吻合的解释，但要把具体写入者提升为实机直接证实，仍需比对启动前原始 kernel DTB 与最终运行时 FDT，或读取可靠的 U-Boot 环境/启动日志。

### 15.4 这是否解释 DHCP Discover 未到达 hEX？

还不能。

e6:e0:02:b2:71:f9 是单播且本地管理的 MAC（首字节 E6 的 I/G 位为 0、U/L 位为 1），在以太网中属于合法的 locally administered unicast address。MAC 与 eMMC 板载 MAC 不同，本身不会使 DHCP Discover 广播帧失效。

当前已知：
- Linux eth0 以 e6:e0:02:b2:71:f9 发出 DHCP Discover（此前本机 tcpdump 已观察到 UDP 68 → 67 广播）。
- hEX 未观察到来自 Panther 的 DHCP 报文。
- MAC 来源错位可以解释设备身份/地址来源不符合预期，但尚无证据证明它导致帧在到达 hEX 前丢失。

后续应继续追踪实际帧离开 GMAC/PHY 的路径，而不是再次重复 DHCP 软件层检查。

### 15.5 下一步优先级

1. 在源码侧核对当前 U-Boot 构建是否启用 CONFIG_ROCKCHIP_SET_ETHADDR、CONFIG_FDT_FIXUP 及 MAC 序号配置；目前确切二进制 .config 尚未恢复。
2. 如果仓库中已有 TF Vendor Storage 的 MAC 值与 eMMC 板载 MAC 值，直接与 e6:e0:02:b2:71:f9 对照，不要求用户重复读取已保存的介质镜像。
3. 研究 Linux GMAC TX DMA/descriptor、stmmac transmit completion、PHY TX/RX 物理链路的证据链；目标是解释本机抓包可见但 hEX 抓包不可见的帧在哪一段消失。
4. 不修改 U-Boot FDT、Linux DTB、MAC、GRF、GPIO 或网络服务；不重复此前 DHCP/hEX 抓包基础测试。

## 16. 当前结论状态补充（2026-11-17）

**已验证：**
- Linux runtime FDT 的 ethernet0 alias 指向 GMAC1。
- Linux runtime FDT 的 GMAC1 local-mac-address 是 e6:e0:02:b2:71:f9。
- Linux eth0 的 parent 是 GMAC1，接口 MAC 与 runtime FDT 完全一致。
- U-Boot control FDT 与 Linux runtime FDT 对 GMAC1 的启用状态、alias 序号、pinmux、时钟方向和 delay 属性存在明确差异。

**源码机制支持、但尚未实机直接证明写入者：**
- Rockchip U-Boot 可从当前启动介质 Vendor Storage 读取 MAC，并在 Linux FDT setup 阶段按 kernel DTB aliases 写入 MAC 属性。
- 当前 runtime FDT 与 Linux DTS/alias 情况吻合该机制。

**尚未验证：**
- 当前 FIT 中 U-Boot 的确切构建配置及相关 CONFIG 值。
- e6:e0:02:b2:71:f9 与 TF Vendor Storage 中具体 MAC 值的逐字节对照（如尚未在仓库中记录）。
- 最终 MAC 属性的实际写入者。
- 错误 MAC 来源是否与 DHCP 帧未到达 hEX 有任何因果关系。
- Linux GMAC TX 到 PHY 物理引脚之间的实际帧传输状态。

**后续方向：** 停止在“MAC 地址来源”层面打转；该层面已基本解释到 Linux 最终接口。调查重点转向 GMAC TX DMA/descriptor、stmmac TX 完成状态及 PHY 物理发送路径，找出 Discover 在本机抓包点之后、hEX 抓包点之前消失的具体位置。
