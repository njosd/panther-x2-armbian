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
