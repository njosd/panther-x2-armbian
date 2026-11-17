# Panther X2 U-Boot FIT FDT 提取异常记录

- 日期：2026-11-17
- 关联基线报告：[PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md](./PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md)
- 状态：提取结果异常，FDT 内容尚未成功解析
- 原则：只记录实机输出；不推断文件损坏或 GMAC 配置

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

## 3. 后续文件检查结果（2026-11-17）

用户继续执行 `stat`、`od` 和 `dumpimage -V`，得到：

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
- 因此，若 FDT 从偏移 12 开始，header 声明的完整 FDT 长度将超出当前提取文件末尾 12 bytes。这与文件整体 SHA256 不匹配、dtc magic 检查失败相互吻合。
- FIT 容器本身开头即为 FDT/FIT magic；文件大小为 1,431,552 bytes。
- 当前工具版本为 `dumpimage 2025.10`。

### 3.2 结论边界

**已验证：** 提取输出存在 12-byte 零前缀；其后的 FDT header 声明总长度 20,421 bytes，而当前文件总长仅 20,421 bytes。因此不能简单删除前 12 bytes 后就认定得到完整 DTB；这样会只剩 20,409 bytes，短缺 12 bytes。

**仍未验证：**
- 为什么当前 `dumpimage -T flat_dt -p 6 -o` 产生此输出布局。
- 是否是命令参数组合/工具实现的提取行为，或 FIT 内部数据布局导致。
- FIT 原始 FDT payload 是否完整有效。
- FDT 中 GMAC1 属性。

不要直接对现有文件做 `dd` 截取后就把它当作完整 FDT；必须先找到 FIT payload 的正确提取方式，并以 FIT 内部 hash `e611e583...` 验证原始 payload。

## 4. 文件是否会在运行中改变

用户询问提取文件是否会在运行中改变。说明：
- `/tmp/tf-u-boot.itb` 与 `/tmp/tf-uboot-control.dtb` 是普通临时文件，不会因为系统持续运行、网络活动或 U-Boot 已启动而自行变化。
- 除非进程显式写入/覆盖、用户修改/删除，内容应保持不变。
- `/tmp` 通常是临时目录，重启后可能清理；这不代表文件在正常运行期间会自动变化。
- 后续命令应保留现有文件，新的提取尝试使用不同输出文件名。

## 5. 结论边界（总）

**已验证：**
- `dumpimage` 报告选择并提取了 FIT Image 6（名称 `fdt`）。
- FIT 中该 image 的元数据哈希为 `e611e583...`。
- 输出文件的 SHA256 为 `a0c4eff4...`，与 FIT 元数据哈希不一致。
- 输出文件偏移 12 处出现 FDT magic，且 dtc 无法识别文件开头的 magic。
- `dumpimage` 版本为 2025.10。

**不能下的结论：**
- 不能据此认定 FIT 内原始 FDT 已损坏。
- 不能据此认定 TF 卡或 U-Boot 镜像错误。
- 不能据此推断 GMAC1 节点启用/禁用或任何 RGMII 配置。

## 6. 后续排查要求

1. 保留现有 `/tmp/tf-u-boot.itb` 和 `/tmp/tf-uboot-control.dtb`，不必重新读取 TF 卡或重新切分前 16 MiB。
2. 对照 U-Boot 2025.10 `dumpimage` 工具的 FIT 提取语法/实现，找出输出多出 12-byte 零前缀且尾部少 12 bytes 的原因。
3. 新的提取尝试输出到新文件名；成功后必须先验证 SHA256 与 FIT image hash 完全一致，再交给 `dtc` 解析。
4. 在有效 FDT 得到之前，不讨论其中 GMAC1 的具体配置，也不把这次提取异常等同于原始 FIT 损坏。

## 7. 防止重复调查

后续 Panther X2 U-Boot 调查应先读取本记录及关联基线报告。已确认的 TF 启动介质、FIT 哈希、默认 configuration、FDT image 名称、内部哈希、提取文件的异常字节布局及工具版本不得重复询问或重新采集，除非用户报告启动介质/镜像/工具环境已变更。
