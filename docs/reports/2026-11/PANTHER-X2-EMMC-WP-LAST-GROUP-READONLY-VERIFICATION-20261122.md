# Panther X2 DF4032 eMMC 最后 WP group 只读实测（2026-11-22）

## 结果

用户在当前运行的 Armbian root shell 中完成只读查询。目标设备先通过 sysfs 精确识别：

- block device：`/dev/mmcblk0`
- type：`MMC`
- name：`DF4032`
- CID：`450100444634303332010f37d8066500`

随后执行 `mmc writeprotect user get`、`mmc writeprotect boot get` 和仓库 helper `mmc-wp-read-last`。

## 原始实测结果

### mmc-utils user area 查询

```text
Write Protect Group size in blocks/bytes: 16384/8388608
Write Protect Groups 0-3726 (Blocks 0-61063167), No Write Protection
USER_QUERY_EXIT=0
```

### mmc-utils boot area 查询

```text
Boot write protection status registers [BOOT_WP_STATUS]: 0x00
Boot Area Write protection [BOOT_WP]: 0x00
Power ro locking: possible
Permanent ro locking: possible
ro lock status: not locked
BOOT_QUERY_EXIT=0
```

### 最后一个 user-area WP group 的 CMD31 只读查询

```text
Target identity verified: /dev/mmcblk0 type=MMC name=DF4032 CID=450100444634303332010f37d8066500
EXT_CSD revision=8 SEC_COUNT=61071360 sectors
HC_ERASE_GRP_SIZE=1 HC_WP_GRP_SIZE=16 WP_group=16384 sectors (8388608 bytes)
USER_WP=0x00 BOOT_WP=0x00 BOOT_WP_STATUS=0x00
Capacity=61071360 sectors; addressable WP groups=3728; last group=3727; last group start LBA=61063168
Issuing read-only CMD31 at LBA=60817408 for groups 3712..3743
CMD31 payload=0000000000000000
Last WP group 3727 status=0: No write protection
Read-only audit complete: only CMD8 and CMD31 were issued; no CMD6/CMD28/CMD29 or data-write command.
LAST_GROUP_QUERY_EXIT=0
```

## 结论

1. EXT_CSD 实测容量为 61,071,360 sectors；WP group 为 16,384 sectors（8 MiB）。
2. 按 ceil(61,071,360 / 16,384) 计算，共有 3,728 个可寻址 group，编号 0–3727。
3. mmc-utils 原生查询覆盖 0–3726，全部为 No Write Protection。
4. 自编只读 helper 通过 CMD31 读取覆盖 3712–3743 的最后一批，实际有效的最后 group 3727 状态为 0（No write protection）。其起始 LBA 61,063,168 小于设备 SEC_COUNT，查询地址有效。
5. 因而此前“最后 4 MiB 尾段未核验”的缺口已由本次实机只读 CMD31 结果补齐。当前 user area 所有有效 WP group 均未启用写保护。
6. boot area 的 BOOT_WP 与 BOOT_WP_STATUS 均为 0，当前 boot area 也未启用 eMMC 写保护。

## 安全边界

- 本轮只执行了读取：mmc-utils get、CMD8 SEND_EXT_CSD、CMD31 SEND_WRITE_PROT_TYPE。
- helper 的 `write_flag=0`；没有发送 CMD6、CMD28、CMD29，也没有数据写入命令。
- 没有设置、清除或永久锁定任何 eMMC 写保护。
- 本结果只证明当前保护状态和最后 group 可读回，不证明 SPL/BL31/U-Boot 启动链无写入。
- eMMC pre-Linux 写入安全门仍未通过。任何 Power-on WP 设置、boot-area WP 设置、TF 写入或实机启动，均须分别满足源码/命令审计和明确授权。
