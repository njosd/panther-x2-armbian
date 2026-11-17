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