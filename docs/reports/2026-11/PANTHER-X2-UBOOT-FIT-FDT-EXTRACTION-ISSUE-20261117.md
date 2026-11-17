# Panther X2 U-Boot FIT FDT 提取异常记录

- 日期：2026-11-17
- 关联基线报告：[PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md](./PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md)
- 状态：FIT FDT 提取输出异常；偏移元数据原因待实机确认
- 原则：只记录实机输出与源码可证实行为；不推断原始 FIT 损坏或 GMAC 配置

## 1. 已知输入基线

当前启动介质为 TF 卡。TF 卡启动区切分得到的 `/tmp/tf-u-boot.itb` SHA256：

```text
3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af
```

此前 `dumpimage -l /tmp/tf-u-boot.itb` 已确认：
- 默认 FIT configuration：`conf`
- configuration 描述：`rk3568-radxa-e25`
- configuration 引用 FDT image：`fdt`
- FDT image 数据大小：20,421 bytes
- FIT 内部 FDT hash（SHA256）：`e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228`

## 2. 实机提取操作与输出

用户执行：

```sh
dumpimage -T flat_dt \
  -p 6 \
  -o /tmp/tf-uboot-control.dtb \
  /tmp/tf-u-boot.itb

sha256sum /tmp/tf-uboot-control.dtb

dtc -I dtb -O dts /tmp/tf-uboot-control.dtb |
grep -n -A70 -B10 -E 'ethernet@fe010000|gmac@fe010000'
```

实机输出摘要：

```text
Extracted:
  Image 6 (fdt)
  Description: U-Boot dtb
  Data Size: 20421 Bytes
  Hash value: e611e583d008c7b7384a74c87fe5cd2505a7838e2a8ec369cc3f758774948228

a0c4eff46050d0bd9ede8d59bc1bbc4e4cc249f6b1032e7f05f8e55d86ba9330  /tmp/tf-uboot-control.dtb

FATAL ERROR: Blob has incorrect magic number
```

## 3. 文件大小、字节布局与工具版本（实机）

用户执行 `stat`、`od` 和 `dumpimage -V`，得到：

```text
/tmp/tf-u-boot.itb 1431552 bytes
/tmp/tf-uboot-control.dtb 20421 bytes

Extracted file first 64 bytes:
00 00 00 00 00 00 00 00 00 00 00 00 d0 0d fe ed
00 00 4f c5 00 00 00 38 00 00 47 50 00 00 00 28
00 00 00 11 00 00 00 10 00 00 00 00 00 00 08 75
00 00 47 18 00 00 00 00 00 00 00 00 00 00 00 00

FIT file first 64 bytes:
d0 0d fe ed 00 00 09 f3 00 00 00 38 00 00 09 30
00 00 00 28 00 00 00 11 00 00 00 10 00 00 00 00
00 00 00 c3 00 00 08 f8 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00

dumpimage version 2025.10
```

### 3.1 直接观察

- 提取文件大小是 20,421 bytes，与 FIT 列出的 FDT image Data Size 数字相同。
- 提取文件的前 12 bytes 全为 `00`。
- FDT magic `d0 0d fe ed` 出现在提取文件偏移 12，而不是偏移 0。
- 偏移 16 开始的 FDT header totalsize 字段为 `0x00004fc5`（20,421 bytes）。
- 因此，若 FDT 从偏移 12 开始，header 声明的完整 FDT 长度将超出当前提取文件末尾 12 bytes。
- FIT 容器本身开头即为 FDT/FIT magic；文件大小为 1,431,552 bytes。
- 当前工具版本为 `dumpimage 2025.10`。

## 4. 初步源码调查：FIT 外部数据偏移处理

已查阅 U-Boot 官方仓库 tag `v2025.10` 的源码：

- `tools/fit_image.c`：`fit_image_extract()` 调用 `fit_image_get_data()` 获取 payload 指针和长度，再由 `imagetool_save_subimage()` 将该内存区域原样写出。
- `boot/image-fit.c`：`fit_image_get_data()` 的处理逻辑为：
  1. 如果 image 节点有 `data-position`，把它作为相对于 FIT 起始地址的绝对偏移；
  2. 否则如果有 `data-offset`，则把它加到 FIT 结构体总长度向 4 字节对齐后的基址；
  3. 两者都没有时，从 image 节点的内嵌 `data` 属性取数据。
- 同一源码中，`fit_image_extract()` 没有在写文件前对 FDT payload 做额外的 12-byte 前缀处理；它直接写出 `fit_image_get_data()` 返回的指针及长度。

官方源码链接：
- https://github.com/u-boot/u-boot/blob/v2025.10/tools/fit_image.c
- https://github.com/u-boot/u-boot/blob/v2025.10/boot/image-fit.c

### 4.1 当前推断（尚未证实）

目前观察到的“12 个零字节前缀 + 后面才出现 FDT magic”与数据指针/外部数据偏移解释不正确的现象相符。需要读取 FIT 的 `/images/fdt` 节点，确认它使用的是：
- 内嵌 `data`；
- 外部 `data-position`；
- 或外部 `data-offset` 加 `data-size`。

在取得这些属性前，不能确定 12-byte 偏移究竟来自 FIT 元数据、镜像 payload 本身，还是工具对该 FIT 布局的处理。

**不能直接认定 dumpimage 2025.10 有 bug。** 也不能认定原始 FDT 已损坏。FIT 内部存储的 SHA256 是声明值；当前尚未独立验证原始 payload 的 SHA256 是否等于该值。

## 5. 文件是否会在运行中改变

用户询问提取文件是否会在运行中改变。说明：
- `/tmp/tf-u-boot.itb` 与 `/tmp/tf-uboot-control.dtb` 是普通临时文件，不会因为系统持续运行、网络活动或 U-Boot 已启动而自行变化。
- 除非进程显式写入/覆盖、用户修改/删除，内容应保持不变。
- `/tmp` 通常是临时目录，重启后可能清理；这不代表文件在正常运行期间会自动变化。
- 后续命令应保留现有文件，新的提取尝试使用不同输出文件名。

## 6. 当前结论边界

**已验证：**
- `dumpimage` 报告选择并提取了 FIT Image 6（名称 `fdt`）。
- FIT 中该 image 的元数据哈希为 `e611e583...`。
- 输出文件的 SHA256 为 `a0c4eff4...`，与 FIT 元数据哈希不一致。
- 输出文件偏移 12 处出现 FDT magic，且 dtc 无法识别文件开头的 magic。
- `dumpimage` 版本为 2025.10。
- 官方 U-Boot v2025.10 源码按 `data-position`、`data-offset` 或内嵌 `data` 属性确定 FIT payload 地址。

**尚未验证：**
- 当前 FIT 的 `fdt` image 实际使用哪种数据存储属性。
- 12-byte 零前缀是否由数据位置元数据或工具解析造成。
- 原始 FDT payload 的实际 SHA256。
- FDT 中 GMAC1 属性及 U-Boot 是否 probe GMAC1。

**不能下的结论：**
- 不能据此认定 FIT 内原始 FDT 已损坏。
- 不能据此认定 TF 卡或 U-Boot 镜像错误。
- 不能据此认定 dumpimage 2025.10 存在缺陷。
- 不能据此推断 GMAC1 节点启用/禁用或任何 RGMII 配置。

## 7. 下一步只读检查

读取 FIT 容器本身（不是提取文件）的设备树结构，检查 `/images/fdt` 节点的数据属性。FIT 容器开头本身是有效 FDT magic，故应直接对容器执行：

```sh
dtc -I dtb -O dts /tmp/tf-u-boot.itb |
grep -n -A35 -B3 -E '^[[:space:]]*fdt \{|data-offset|data-position|data-size'
```

目标是确认 `fdt` 节点的 `data` / `data-offset` / `data-position` / `data-size`。若输出未能明确归属到 fdt 节点，再完整导出 FIT DTS 到一个新的临时文本文件并查看该节点；不覆盖现有镜像文件。

确认属性后，再按 FIT 格式语义计算 payload 的真实文件偏移，使用只读方式取样并验证 SHA256。不要先对现有提取文件简单删除 12 bytes；若去掉前缀会缺少末尾 12 bytes，不能恢复完整 DTB。

## 8. 防止重复调查

后续 Panther X2 U-Boot 调查应先读取本记录及关联基线报告。已确认的 TF 启动介质、FIT 哈希、默认 configuration、FDT image 名称、内部哈希、提取文件的异常字节布局、工具版本及 U-Boot v2025.10 源码偏移处理逻辑不得重复询问或重新采集，除非用户报告启动介质/镜像/工具环境已变更。
