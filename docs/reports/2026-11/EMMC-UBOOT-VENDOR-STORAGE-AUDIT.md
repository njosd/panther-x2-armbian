# Panther X2 eMMC U-Boot 与 Vendor Storage 审计

- 日期：2026-11-16
- 设备：Panther X2 / RK3566
- 审计方式：从当前 TF 启动系统在线读取未挂载的 eMMC 分区；使用 `debugfs` 只读检查并提取文件到 TF 卡临时目录
- 状态：只读审计；未写入 eMMC，未修改启动配置
- 隐私：真实 MAC 地址、分区 UUID 和其他可识别设备标识均不在本文公开

## 1. 结论摘要

1. **已验证：** 当前运行系统及 `/boot` 均来自 TF 卡；内部 eMMC 的 BOOT 与 ROOTFS 分区未挂载。
2. **已验证：** eMMC ROOTFS 中的 `idbloader.img` 和 `u-boot.itb` 与 Ophub `u-boot` 仓库 Panther X2 目录对应文件逐字节一致。两份文件的 Git Blob SHA-1 均匹配。
3. **已验证：** eMMC BOOT 配置中的 rootdev 指向 eMMC ROOTFS；`boot.cmd` 会导入 `armbianEnv.txt`，随后从启动介质加载 `uInitrd`、`Image` 和 Panther X2 DTB。
4. **已验证：** eMMC BOOT 中存在 6.1.116 与 6.1.192 两套内核文件，但当前通用链接 `Image`、`uInitrd` 指向 6.1.116；ROOTFS 的 Ophub release 元数据标记内核版本为 6.1.192。存在版本不一致，形成原因未明。
5. **已验证：** eMMC Rockchip Vendor Storage 中存在 LAN_MAC（ID 3）条目，包含两个 GMAC 地址。为保护设备隐私，具体地址不在仓库公开。
6. **尚未验证：** ROOTFS 中保存的 U-Boot 文件是否就是设备上电时从 eMMC 原始启动区域实际执行的镜像；也尚未证明该 U-Boot 在本机启动时成功读取了 Vendor Storage。

## 2. 设备与介质状态

本次检查时：

| 项目 | 结果 |
|---|---|
| 当前根文件系统 | TF 卡 `/dev/mmcblk0p2` |
| 当前 `/boot` | TF 卡 `/dev/mmcblk0p1` |
| 内部 eMMC | `/dev/mmcblk1` |
| eMMC BOOT | `/dev/mmcblk1p1`，未挂载 |
| eMMC ROOTFS | `/dev/mmcblk1p2`，未挂载 |

eMMC 分区通过 `debugfs` 只读访问。提取出的 U-Boot 文件写入的是当前 TF 系统的 `/tmp` 临时目录，不是 eMMC。

## 3. eMMC BOOT 分区检查

### 3.1 启动文件

eMMC BOOT 中可见：

- `armbianEnv.txt`（408 bytes）
- `boot.cmd`（3310 bytes）
- `boot.scr`（3382 bytes）
- `dtb/rockchip/rk3566-panther-x2.dtb`
- `dtb-6.1.192-ophub` 符号链接，目标为 `dtb`
- `Image` 符号链接，目标为 `vmlinuz-6.1.116-ophub`
- `uInitrd` 符号链接，目标为 `uInitrd-6.1.116-ophub`
- 6.1.116 与 6.1.192 两个版本的内核、initrd、配置及 System.map 文件

### 3.2 armbianEnv.txt

关键配置（隐去 UUID）：

```ini
verbosity=7
bootlogo=true
fdtfile=rockchip/rk3566-panther-x2.dtb
rootdev=UUID=<redacted: points to eMMC ROOTFS>
rootfstype=ext4
rootflags=rw,errors=remount-ro
earlycon=on
console=both
consoleargs=console=ttyS02,1500000 console=tty0
docker_optimizations=on
extraboardargs=net.ifnames=0 max_loop=128
overlay_prefix=rk3566
overlays=
user_overlays=
```

配置中的 rootdev UUID 与 eMMC ROOTFS 分区相符。具体 UUID 不公开。

### 3.3 boot.cmd 启动流程

脚本先从当前启动设备读取并导入 `armbianEnv.txt`，再构造 bootargs。随后执行：

```bash
load ${devtype} ${devnum} ${ramdisk_addr_r} ${prefix}uInitrd
load ${devtype} ${devnum} ${kernel_addr_r} ${prefix}Image
load ${devtype} ${devnum} ${fdt_addr_r} ${prefix}dtb/${fdtfile}
booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}
```

因此，按当前 eMMC BOOT 文件系统内容，通用链接会使脚本加载 6.1.116 内核和 initrd，而 DTB 从 `dtb/rockchip/rk3566-panther-x2.dtb` 加载。

## 4. eMMC ROOTFS 中 U-Boot 文件身份

eMMC ROOTFS 的 `/usr/lib/u-boot/` 包含：

| 文件 | 大小 |
|---|---:|
| `idbloader.img` | 305,152 bytes |
| `u-boot.itb` | 1,431,552 bytes |

文件通过 `debugfs dump` 提取到 TF 卡的 `/tmp`，再计算普通 SHA-256 和 Git Blob SHA-1。

### 4.1 哈希结果

| 文件 | SHA-256 | Git Blob SHA-1 |
|---|---|---|
| `idbloader.img` | `990afd3e1a96094a1b6ef0b32ea55cb9cb2d6de53bd7e368d6c77fea4eddd91e` | `d22b624fc90c46e656baf98894bee182316e692e` |
| `u-boot.itb` | `3a662accda44a1efcb7822972f701dc95ef07a81830f7679440de04d916ab0af` | `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c` |

Git Blob SHA-1 由 `git hash-object` 计算。两个结果均与 Ophub 仓库 Panther X2 目录对应文件的 Git Blob SHA-1 完全相同，因此可以确认：**eMMC ROOTFS 中这两份文件与该 Ophub 仓库版本逐字节一致。**

参考：

- Ophub U-Boot 仓库： https://github.com/ophub/u-boot
- 对应目录： https://github.com/ophub/u-boot/tree/6e70f41585f15c43f45fcae609adec1865e83eb5/u-boot/rockchip/panther-x2
- 对应提交： https://github.com/ophub/u-boot/commit/6e70f41585f15c43f45fcae609adec1865e83eb5

**重要边界：** 以上只证明 eMMC ROOTFS 中保存的文件与 Ophub 仓库文件完全一致，不证明 eMMC 原始启动区域已经烧录相同内容，也不证明本机启动时实际执行了这两个文件。

## 5. U-Boot FIT 元数据线索

此前对该 Ophub Panther X2 `u-boot.itb` 的 FIT 元数据检查记录：

- FIT description：`FIT Image with ATF/OP-TEE/U-Boot`
- 创建时间：2023-04-23 21:08:08（FIT 内嵌时间）
- U-Boot DTB image description：`rk3568-radxa-e25`

该字符串是 U-Boot FIT 内部的构建/配置线索，**不能单独证明 Panther X2 实物是 Radxa E25，也不能证明该二进制来自 E25 目录**。Panther X2 与 Ophub E25 目录的对应二进制文件大小及哈希此前已确认不同。

## 6. Rockchip Vendor Storage 与 LAN_MAC

此前对 eMMC Vendor Storage 区域的只读检查发现：

- Vendor Storage magic 为 `DVKR`（little-endian 数值 `0x524b5644`）。
- 版本字段为 2。
- item_num 为 1。
- 条目 ID 为 3，size 为 12 bytes。
- Rockchip Vendor Storage ID 3 对应 LAN_MAC。
- 12-byte 数据区包含两个 GMAC 地址。

**隐私处理：** 真实 MAC 地址及可还原地址的字节序列均不写入本仓库。该条目存在及其结构已验证；具体地址值仅保留在本地受控记录中。

此前 Radxa U-Boot 参考实现中存在读取 Vendor Storage LAN_MAC、设置网口地址以及在失败时生成随机地址的处理路径。但这只能说明参考源码具备相关机制，尚不能证明当前 eMMC 中的二进制启用了该配置、执行了该函数或成功读取了本机 Vendor Storage。

## 7. 证据等级与未解决问题

### 已验证

- TF 与 eMMC 的块设备映射及当前挂载来源。
- eMMC BOOT/ROOTFS 未挂载，使用 `debugfs` 只读访问。
- eMMC BOOT 的文件清单、符号链接目标、启动配置和脚本加载顺序。
- eMMC ROOTFS U-Boot 文件大小及哈希。
- 两个 Git Blob SHA-1 与 Ophub Panther X2 仓库目标文件完全匹配。
- eMMC Vendor Storage 存在 LAN_MAC ID 3 条目，具体地址已脱敏。

### 静态审计确认 / 尚不能推出

- eMMC ROOTFS 保存的是 Ophub Panther X2 仓库对应 U-Boot 文件。
- FIT 元数据包含 Radxa E25 字符串，但不能据此判定实物硬件身份。
- BOOT 文件系统的 Image/uInitrd 链接与 ROOTFS release 内核版本标记不一致；成因未知。

### 待验证

1. eMMC 原始启动区域中的 loader/U-Boot 内容及其与 ROOTFS 文件的关系。
2. 设备实际上电时使用的启动介质、加载路径与运行中的 U-Boot 身份。
3. 实际运行的 U-Boot 是否启用并成功执行 Vendor Storage LAN_MAC 读取流程。
4. MAC 从 Vendor Storage 到运行时 FDT/网卡接口的传递链，以及当前地址变化发生在哪个阶段。

## 8. 下一步

保持只读原则，下一轮优先审计 eMMC 原始启动区域，并与已存档的旧启动日志进行交叉核对。无需重复提取 ROOTFS 中的两个 U-Boot 文件，也不需要重新计算已经匹配的 Git Blob SHA-1。

在明确授权前，不写入 eMMC、不修改 U-Boot/DTB/启动配置、不挂载 eMMC 分区、不改写网卡 MAC，也不改变当前 TF 系统。

## 9. 采集与复核命令

以下命令仅供复核；路径为本次测试环境中的实际路径。执行前应确认仍处于从 TF 卡启动的系统：

```bash
# 只读列出 eMMC BOOT 文件
sudo debugfs -R 'ls -l /' /dev/mmcblk1p1

# 只读查看启动环境与脚本
sudo debugfs -R 'cat /armbianEnv.txt' /dev/mmcblk1p1
sudo debugfs -R 'cat /boot.cmd' /dev/mmcblk1p1

# 只读列出 eMMC ROOTFS U-Boot 文件
sudo debugfs -R 'ls -l /usr/lib/u-boot' /dev/mmcblk1p2

# 从 eMMC 文件系统提取到 TF 系统的临时目录（不写 eMMC）
sudo debugfs -R 'dump /usr/lib/u-boot/idbloader.img /tmp/emmc-idbloader.img' /dev/mmcblk1p2
sudo debugfs -R 'dump /usr/lib/u-boot/u-boot.itb /tmp/emmc-u-boot.itb' /dev/mmcblk1p2

# 哈希复核
sha256sum /tmp/emmc-idbloader.img /tmp/emmc-u-boot.itb
git hash-object /tmp/emmc-idbloader.img
git hash-object /tmp/emmc-u-boot.itb
```

本报告对应的脱敏证据摘录见 `evidence/boot/2026-11-16-panther-x2-emmc-boot-files-audit.txt`。
