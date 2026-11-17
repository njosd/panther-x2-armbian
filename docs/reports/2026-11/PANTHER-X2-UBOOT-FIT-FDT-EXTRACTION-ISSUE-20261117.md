# Panther X2 U-Boot FIT FDT 提取异常记录

- 日期：2026-11-17
- 关联基线报告：[PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md](./PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md)
- 状态：已定位 FIT 外部 FDT payload 的理论文件偏移；待直接提取并校验哈希
- 原则：只记录实机输出与源码可证实行为；不推断原始 FIT 损坏或 GMAC 配置

## 1. 输入镜像基线

TF 启动区切分得到的 `/tmp/tf-u-boot.itb` SHA256：

```text
3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af
```

FIT 文件大小（实机 stat）：1,431,552 bytes。

此前 `dumpimage -l` 已确认：
- 默认 FIT configuration：`conf`
- configuration 描述：`rk3568-radxa-e25`
- configuration 引用 FDT image：`fdt`
- FDT image 数据大小：20,421 bytes
- FIT 内部 FDT SHA256：`e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228`

## 2. 实机提取异常

用户执行：

```sh
dumpimage -T flat_dt -p 6 -o /tmp/tf-uboot-control.dtb /tmp/tf-u-boot.itb
sha256sum /tmp/tf-uboot-control.dtb
dtc -I dtb -O dts /tmp/tf-uboot-control.dtb
```

实机结果：
- `dumpimage` 报告选择 FIT Image 6（`fdt`），Data Size 20,421 bytes，内部 hash 为 `e611e583...`。
- 输出文件大小：20,421 bytes。
- 输出文件 SHA256：`a0c4eff46050d0bd9ede8d59bc1bbc4e4cc249f6b1032e7f05f8e55d86ba9330`，与 FIT 声明 hash 不同。
- 输出文件开头 12 bytes 全为零；FDT magic `d0 0d fe ed` 位于偏移 12。
- FDT header 的 totalsize 为 `0x4fc5`（20,421 bytes）。
- `dtc` 报 `FATAL ERROR: Blob has incorrect magic number`。
- 实机工具版本：`dumpimage version 2025.10`。

该输出不能作为有效 DTB。不能简单剥掉 12 bytes，因为这样只剩 20,409 bytes，短于 FDT header 声明的 20,421 bytes。

## 3. FIT 原始容器中的 fdt 节点属性（2026-11-17 实机确认）

用户直接对原始 FIT 容器执行：

```sh
dtc -I dtb -O dts /tmp/tf-u-boot.itb |
grep -n -A35 -B3 -E '^[[:space:]]*fdt \\{|data-offset|data-position|data-size'
```

输出中 `/images/fdt` 节点为：

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

原始 FIT header 开头 64 bytes（此前实机 `od`）：

```text
d0 0d fe ed 00 00 09 f3 00 00 00 38 00 00 09 30
00 00 00 28 00 00 00 11 00 00 00 10 00 00 00 00
00 00 00 c3 00 00 08 f8 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00
```

FIT header 的 `totalsize` 字段为 `0x000009f3`（2,547 bytes）。

## 4. 按 U-Boot FIT 规则计算 FDT payload 文件偏移

U-Boot 官方 v2025.10 `boot/image-fit.c` 中 `fit_image_get_data()` 对外部数据的处理：
- `data-position` 存在时，使用其绝对偏移；
- 否则 `data-offset` 存在时，将其加到 FIT structure 总长度向 4 字节对齐后的基址；
- 再使用 `data-size` 作为 payload 长度。

源码：
- https://github.com/u-boot/u-boot/blob/v2025.10/boot/image-fit.c
- https://github.com/u-boot/u-boot/blob/v2025.10/tools/fit_image.c

本例没有看到 `data-position`，而 `fdt` 节点明确有 `data-offset` 和 `data-size`。

计算：

```text
FIT totalsize                 = 0x9f3
4-byte aligned FIT totalsize  = (0x9f3 + 3) & ~3 = 0x9f4
fdt data-offset               = 0x157e00
absolute FDT payload offset   = 0x9f4 + 0x157e00 = 0x1587f4
decimal offset                = 1,411,060
fdt data-size                 = 0x4fc5 = 20,421 bytes
payload end (exclusive)       = 1,411,060 + 20,421 = 1,431,481
FIT file size                 = 1,431,552 bytes
remaining trailing bytes      = 71 bytes
```

**当前可得结论：** 根据 FIT 元数据与 U-Boot v2025.10 的偏移规则，FDT payload 理论上从原始 FIT 文件偏移 `0x1587f4`（十进制 1,411,060）开始，长度 20,421 bytes。它完整落在 1,431,552-byte FIT 文件范围内，后面还有 71 bytes。

这解释了如何直接从原始 FIT 中取出 payload，绕开异常的 `dumpimage` 输出。但在直接提取并验证 SHA256 前，仍将其标为“按元数据计算的预期位置”，不是已经通过哈希验证的实际 payload。

## 5. 下一步只读提取与验证

保留现有 `/tmp/tf-u-boot.itb` 和异常文件 `/tmp/tf-uboot-control.dtb`。不要覆盖它们。使用新文件名直接按 FIT 元数据取 payload：

```sh
dd if=/tmp/tf-u-boot.itb \
   of=/tmp/tf-uboot-control-raw.dtb \
   bs=1 skip=1411060 count=20421 status=none

echo "===== RAW FDT SIZE ====="
stat -c '%n %s bytes' /tmp/tf-uboot-control-raw.dtb

echo "===== RAW FDT SHA256 ====="
sha256sum /tmp/tf-uboot-control-raw.dtb

echo "===== RAW FDT HEADER ====="
od -An -tx1 -N32 /tmp/tf-uboot-control-raw.dtb

echo "===== PARSE GMAC1 ====="
dtc -I dtb -O dts /tmp/tf-uboot-control-raw.dtb |
grep -n -A70 -B10 -E 'ethernet@fe010000|gmac@fe010000'
```

成功条件：
1. 文件大小必须为 20,421 bytes。
2. SHA256 必须与 FIT 内部 FDT hash 完全一致：`e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228`。
3. 文件偏移 0 必须以 FDT magic `d0 0d fe ed` 开始。
4. `dtc` 成功解析后，才分析 U-Boot GMAC1 节点。

若 hash 不一致，停止，不要解析或修改文件；再检查 offset 计算和 FIT 数据布局。

## 6. 源码调查：dumpimage 提取路径

已查阅 U-Boot 官方仓库 tag `v2025.10`：
- `tools/fit_image.c`：`fit_image_extract()` 调用 `fit_image_get_data()` 取得 payload 指针和长度，再将该内存区域写出。
- `boot/image-fit.c`：`fit_image_get_data()` 根据 `data-position`、`data-offset` 或内嵌 `data` 属性决定 payload 地址。

当前现象是 `dumpimage` 输出前面多 12 个零字节，而后面的 FDT header 声明完整长度仍为 20,421 bytes。FIT 元数据计算出的原始 payload 位置可通过上述 dd 命令独立验证。尚未证明该 12-byte 前缀的具体成因，也不能据此认定 `dumpimage 2025.10` 存在 bug。

## 7. 文件是否会在运行中改变

- `/tmp/tf-u-boot.itb` 与 `/tmp/tf-uboot-control.dtb` 是普通临时文件，不会因为系统持续运行、网络活动或 U-Boot 已启动而自行变化。
- 除非进程显式写入/覆盖、用户修改/删除，内容应保持不变。
- `/tmp` 通常是临时目录，重启后可能清理；这不代表文件在正常运行期间会自动变化。
- 新的提取尝试使用不同输出文件名。

## 8. 当前结论边界

**已验证：**
- 当前 TF FIT 身份与整体 SHA256。
- FIT 默认配置、fdt image 名称及其声明的数据大小和 SHA256。
- FIT 的 `fdt` 节点采用 `data-offset=0x157e00`、`data-size=0x4fc5`。
- FIT header `totalsize=0x9f3`。
- 按 U-Boot v2025.10 规则计算的 payload 绝对偏移为 `0x1587f4`（1,411,060）。
- 直接提取命令尚待实机执行；payload hash 和 DTB 内容尚待验证。

**尚未验证：**
- 直接从计算偏移提取后的 payload 是否与 FIT hash 一致。
- U-Boot FDT 的 GMAC1 属性及 U-Boot 是否 probe GMAC1。

**不能下的结论：**
- 不能认定 FIT 内原始 FDT 损坏。
- 不能认定 TF 卡或 U-Boot 镜像错误。
- 不能认定 dumpimage 2025.10 有 bug。
- 不能推断 GMAC1 节点启用/禁用或 RGMII 配置，直到取得哈希正确的 DTB。

## 9. 防止重复调查

后续 Panther X2 U-Boot 调查应先读取本记录及关联基线报告。已确认的 TF 启动介质、FIT 哈希、默认 configuration、FDT image 名称、内部哈希、FIT 外部数据属性、理论 payload 偏移、提取文件异常字节布局及工具版本不得重复询问或重新采集，除非用户报告启动介质/镜像/工具环境已变更。
