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

## 3. 结论边界

**已验证：**
- `dumpimage` 报告选择并提取了 FIT Image 6（名称 `fdt`）。
- FIT 中该 image 的元数据哈希为 `e611e583...`。
- 输出文件的 SHA256 为 `a0c4eff4...`，与 FIT 元数据哈希不一致。
- `dtc` 无法将输出文件识别为有效 FDT blob，报错 `Blob has incorrect magic number`。

**尚未验证：**
- 输出文件是否包含额外头部、偏移或其他非 DTB 数据。
- 当前 `dumpimage` 的版本、参数组合和 FIT extraction 行为是否导致输出格式/偏移问题。
- FIT 中原始 FDT payload 是否完整且有效。
- U-Boot FDT 的 GMAC1 节点属性及 U-Boot 是否 probe GMAC1。

**不能下的结论：**
- 不能据此认定 FIT 内原始 FDT 已损坏。
- 不能据此认定 TF 卡或 U-Boot 镜像错误。
- 不能据此推断 GMAC1 节点启用/禁用或任何 RGMII 配置。

## 4. 后续排查要求

1. 保留现有 `/tmp/tf-u-boot.itb` 和 `/tmp/tf-uboot-control.dtb`，不必重新读取 TF 卡或重新切分前 16 MiB。
2. 下一步先只读检查输出文件大小和开头字节（例如使用 `stat`、`od`），确认是否有头部/偏移；不要覆盖原文件。
3. 对照本机 `dumpimage` 版本及 U-Boot 工具文档/源码，确认 FIT image payload 提取的正确调用方式。
4. 如需再次提取，输出到新文件名；成功后必须先验证 SHA256 与 FIT image hash 一致，再交给 `dtc` 解析。
5. 在有效 FDT 得到之前，不讨论其中 GMAC1 的具体配置，也不把这次提取异常等同于原始 FIT 损坏。

## 5. 防止重复调查

后续 Panther X2 U-Boot 调查应先读取本记录及关联基线报告。已确认的 TF 启动介质、FIT 哈希、默认 configuration、FDT image 名称和内部哈希不得重复询问或重新采集，除非用户报告启动介质/镜像已变更。
