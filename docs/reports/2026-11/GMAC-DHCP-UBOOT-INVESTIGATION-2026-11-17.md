# Panther X2（RK3566）GMAC / DHCP 与 TF U-Boot 启动链调查记录

- 整理日期：2026-11-17
- 设备/系统：Panther X2（RK3566），Armbian / Ophub Linux 6.12.81-rk35xx-ophub
- 调查目标：eth0 DHCP Discover 到达 Linux 抓包点，但 hEX 未观察到报文；审查 GMAC1、RTL8211F、RGMII 和实际 TF 启动链
- 操作性质：只读取证、源码对照和记录整理；未安装软件、未修改系统/网络/内核/驱动/DTB/U-Boot，未写入 TF 卡或 eMMC
- 状态：阶段性；待 TF 卡前 16 MiB 只读提取及实际 boot.scr 解码
- 隐私：真实 MAC 地址不公开

> 本文汇总 2026-11-16 至 2026-11-17 数轮对话的实机输出、源码对照和推理修正。结论仅限各自证据范围。软件读回不等于物理波形测量。

## 1. 当前结论

1. **已验证：** Linux eth0 抓到 DHCP Discover：0.0.0.0:68 → 255.255.255.255:67。证明 DHCP 客户端已启动，报文到达 Linux 本机抓包点；不证明帧已从 PHY 引脚成功发出。
2. **已验证：** hEX 未观察到 Panther 发出的 DHCP 报文（此前抓包结果）。故障边界在 Linux 本机抓包点之后、hEX 收包之前，尚不能直接归因为 PHY 或 U-Boot。
3. **已验证：** 更换网线后千兆链路问题解决；当前 Link Up，1000Mbps Full Duplex。不要再把旧链路协商问题作为当前 DHCP 故障的默认解释。
4. **已验证：** Linux 运行时 FDT 配置 GMAC1 为 M0 RGMII，RTL8211F PHY 地址 0；驱动日志报告 TX delay=0x30、RX delay=0x10，clock input from PHY。
5. **已验证：** Linux 初始化后的 GRF_MAC1_CON0/CON1 读回值为 0x00001030 / 0x00000013，与 DT delay 参数和 Linux 驱动写入逻辑吻合。
6. **已验证：** Linux clk_summary 中 GMAC1 相关时钟均显示预期 125MHz 且已使能。
7. **未验证：** PHY 引脚 TXC/TXD/RXC/RXD 实际波形、setup/hold、clock-to-data skew、占空比和 jitter。软件时钟、GRF 值、TX DMA 完成和 Link Up 都不能代替物理测量。
8. **已验证：** 当前 Linux 系统和 /boot 来自 TF 卡 /dev/mmcblk0（type=SD、name=SN64G）；eMMC 是 /dev/mmcblk1（type=MMC、name=DF4032）。
9. **强证据支持：** 内核 root UUID、ubootpart PARTUUID、/boot 挂载均指向 TF 卡。当前 boot.cmd 逻辑从 U-Boot 当前设备加载 Image、uInitrd、DTB。实际 TF 原始启动区 SPL/U-Boot 尚未提取，故本轮 U-Boot 二进制身份仍待确认。
10. **未验证：** U-Boot 是否初始化 GMAC1，及是否留下影响 Linux/PHY/RGMII 的状态。Linux 已重写 GRF delay，不能用 Linux 最终读回反推 U-Boot 交接瞬间的寄存器值。

## 2. DHCP 故障边界与既有排除项

- GMAC1 MMIO：0xfe010000。
- PHY：RTL8211F，MDIO 地址 0。
- Linux 接口：eth0；end0/end1/enxe... 是 alternative names。NetworkManager profile 实际绑定 eth0，接口命名不是当前故障原因。
- NetworkManager DHCPv4 曾报告 ip-config-unavailable，最后仅 IPv6 激活。
- Panther 本机 tcpdump 捕获 DHCP Discover（UDP 68 → 67，0.0.0.0 → 255.255.255.255）。
- hEX 未收到 Panther DHCP 报文；其他多台 LAN 设备 DHCP 正常。
- 更换网线后链路达到 1000Mbps Full Duplex。
- DHCP 基础检查、hEX 抓包、NetworkManager/Netplan/udev 和接口命名检查此前已做，不应无理由重复。

**证据边界：** 本机 tcpdump 只证明报文抵达 Linux 抓包点，不证明 MAC DMA 正确发到 PHY、RGMII 引脚时序满足采样要求、PHY 正确转换为 MDI 信号或交换机端收到帧。TX DMA 完成和 Link Up 也不构成物理时序证据。

## 3. Linux 运行时 FDT 与 pinctrl

运行时 FDT：
- 路径：/sys/firmware/fdt
- SHA-256：c8da977cd6b65e768c2399d128b11de05941fd9a03c4d7cf405af910ceb10020

GMAC1 节点关键属性：

~~~dts
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
    rx_delay = <0x10>;
    tx_delay = <0x30>;
    mdio {
        ethernet-phy@0 {
            compatible = "ethernet-phy-ieee802.3-c22";
            reg = <0x00>;
        };
    };
};
~~~

pinctrl phandle：
- 0x7b gmac1m0-miim
- 0x7c gmac1m0-tx-bus2
- 0x7d gmac1m0-rx-bus2
- 0x7e gmac1m0-rgmii-clk
- 0x7f gmac1m0-clkinout
- 0x80 gmac1m0-rgmii-bus

实机 pinmux：
- pin 106–107：GMAC1 M0 RX bus
- pin 109–111：GMAC1 M0 TX bus
- pin 112：GMAC1 M0 clkinout
- pin 97 不是 GMAC1 M0 signal，而是 PHY reset GPIO。

结论：内核接收到的 GMAC1 pinctrl 为 M0 RGMII，实机 pinmux 与之吻合；不代表信号电气波形正确。

## 4. RGMII delay、GRF 与 Linux 6.1/6.12 源码对照

驱动日志：

~~~text
[00:00:02] rk_gmac-dwmac fe010000.ethernet: clock input or output? (input).
[00:00:02] TX delay(0x30)
[00:00:02] RX delay(0x10)
[00:00:02] clock input from PHY
[00:00:02] init for RGMII
[00:00:15] PHY [stmmac-1:00] driver [RTL8211F Gigabit Ethernet] (irq=POLL)
[00:00:19] Link is Up - 1Gbps/Full
~~~

只读 regmap：

~~~text
REGMAP: /sys/kernel/debug/regmap/dummy-syscon@0x00000000fdc60000
NAME: nodev
0388: 00001030
038c: 00000013
~~~

寄存器：
- SYS_GRF base 0xFDC60000
- GRF_MAC1_CON0 offset 0x0388（物理地址 0xFDC60388）
- GRF_MAC1_CON1 offset 0x038C（物理地址 0xFDC6038C）

字段解码：
- CON0=0x00001030：bits [14:8]=0x10（RX delay cfg，对应 rx_delay=0x10）；bits [6:0]=0x30（TX delay cfg，对应 tx_delay=0x30）。
- CON1=0x00000013：bit4=1（RGMII interface）；bit1=1（RX delay enable）；bit0=1（TX delay enable）；bits6/5=0。
- tx_delay=0x30 是 GRF 字段编码，不是 0x30 ns。

**结论：** Linux 初始化后的 GRF 配置由日志和寄存器读回双重确认，与 DT 和驱动逻辑一致。Linux 已重写 CON0/CON1，因此不能反推 U-Boot 交接时寄存器原值，也不能证明 delay 适合板上走线。

源码对照：
- 项目 Linux 6.12 固定版本：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c
- 6.1 BSP 与该 6.12 版本中，phy-mode="rgmii" 都将 tx_delay/rx_delay 交给 rk3568_set_to_rgmii() 配置 MAC 侧 GRF。
- RTL8211F Linux realtek.c 核心行为相同：rgmii 清除 PHY 内部 TX/RX delay；rgmii-id 开启两侧；rxid/txid 分别开启一侧。
- Panther 当前 DTB 是 rgmii，不是 rgmii-id。
- 两版本 GMAC1 clock mux 定义未发现实质差异。
- 暂未发现 6.12 相比 6.1 在上述 RGMII mode / RTL8211F delay 处理上的明显代码回归；不涵盖全部运行时行为和板级物理差异。

## 5. Linux GMAC1 时钟树读回

用户从 /sys/kernel/debug/clk/clk_summary 读取：

~~~text
clk_gmac1_ptp_ref 62500000 enable
clk_mac1_out 125000000
clk_mac1_2top 125000000
clk_mac1_refout 125000000
aclk_gmac1 297000000 enable
pclk_gmac1 99000000 enable
gmac1_clkin 125000000 enable
  clk_gmac1 125000000 enable (consumer fe010000.ethernet stmmaceth)
    clk_gmac1_rgmii_speed 125000000 enable
      clk_gmac1_rx_tx 125000000 enable (consumer clk_mac_speed/mac_clk_tx/mac_clk_rx)
~~~

结论：软件时钟树显示 GMAC1 相关时钟已使能且频率符合 DT 设计。gmac1_clkin 是 DT external fixed clock；clk_summary 的 125MHz 不等于物理引脚实测。Linux 接管后的错误 parent/频率嫌疑降低，物理时钟仍未测量。

## 6. PHY Reset GPIO 调查

运行时 FDT：

~~~dts
snps,reset-gpio = <0x81 0x01 0x01>;
snps,reset-active-low;
snps,reset-delays-us = <0x00 0x4e20 0x186a0>;
~~~

- phandle 0x81 指向 gpio@fe760000（GPIO3）。
- GPIO line 1，全局 GPIO97（GPIO3-1）。
- delay：0x4e20=20000µs，0x186a0=100000µs。
- pinmux：pin 97 当前 (MUX UNCLAIMED) (GPIO UNCLAIMED)。
- pinconf：input bias pull down、output drive 12mA、input schmitt enabled、pin output 1、slew rate 1。

Linux 6.12 stmmac_mdio_reset() 核心逻辑：

~~~c
reset_gpio = devm_gpiod_get_optional(priv->device,
                                     "snps,reset",
                                     GPIOD_OUT_LOW);
/* ... */
gpiod_set_value_cansleep(reset_gpio, 1);
/* delay */
gpiod_set_value_cansleep(reset_gpio, 0);
/* delay */
devm_gpiod_put(priv->device, reset_gpio);
~~~

结合 active-low，物理过程为高（inactive）→低（assert）→高（release）。驱动结束后释放 GPIO，所以最终 GPIO UNCLAIMED 不代表 reset 没执行。当前状态与 reset 完成并释放相容，没有证据证明 GMAC PHY reset 失败。

纠错：
- 曾误将 GPIO73 识别为 GMAC reset；已纠正。GPIO73 是 GPIO2 的另一条 reset consumer。
- WLAN 日志 rkwlangpiod_request failed to request WIFI,reset gpio, err -2 属于 WLAN 驱动申请失败，与 GMAC reset 不同。

## 7. TF 卡与 eMMC 身份、挂载和启动参数（2026-11-17）

### 7.1 MMC 设备身份

| Linux 设备 | name | type | CID | manfid | oemid | serial | date | 身份 |
|---|---|---|---|---|---|---|---|---|
| /dev/mmcblk0 | SN64G | SD | 035344534e36344780af5519750159b7 | 0x000003 | 0x5344 | 0xaf551975 | 09/2021 | TF / SD |
| /dev/mmcblk1 | DF4032 | MMC | 450100444634303332010f37d8066500 | 0x000045 | 0x0100 | 0x0f37d806 | 06/2018 | eMMC |

块设备布局：
- /dev/mmcblk0：59.5G，GPT；p1 511M BOOT，p2 59G ROOTFS。
- /dev/mmcblk1：29.1G；p1 255M BOOT，p2 28.9G ROOTFS。
- 当前 /boot=/dev/mmcblk0p1，/=/dev/mmcblk0p2；eMMC 两分区未挂载。

### 7.2 UUID / PARTUUID / cmdline

/proc/cmdline 关键内容：

~~~textroot=UUID=9c7ff1a4-9beb-4346-b396-cdd1d4d1feea
rootwait rootfstype=ext4 rootflags=rw,errors=remount-ro
ubootpart=57ba8610-bc1c-4f13-9ce4-c864b229d25e
~~~

| 分区 | UUID | PARTUUID | 用途 |
|---|---|---|---|
| mmcblk0p1 | 55586ba5-0259-40c3-a67a-30e92526320b | 57ba8610-bc1c-4f13-9ce4-c864b229d25e | TF BOOT |
| mmcblk0p2 | 9c7ff1a4-9beb-4346-b396-cdd1d4d1feea | 87fd0694-5515-4644-b27f-a897a86a248d | TF ROOTFS |
| mmcblk1p1 | a5110630-ef2e-4941-9a22-15784ef687a5 | 1ef0258e-6807-493d-bb0c-a2903d5d5988 | eMMC BOOT |
| mmcblk1p2 | ddcbfa1d-95e7-4863-97c8-ec9b7767968b | 462e43d5-1545-4d14-b115-5515a12c7743 | eMMC ROOTFS |

root UUID 精确对应 TF mmcblk0p2；ubootpart 精确对应 TF mmcblk0p1 PARTUUID。

### 7.3 /boot 文件与启动脚本

当前 /boot：
- armbianEnv.txt：419 bytes，2026-11-15 13:47
- boot.cmd：3.3K，2026-11-15 13:54
- boot.scr：3.4K，2026-11-15 13:54
- Image -> vmlinuz-6.12.81-rk35xx-ophub
- uInitrd -> uInitrd-6.12.81-rk35xx-ophub
- dtb/rockchip/rk3566-panther-x2.dtb
- extlinux/extlinux.conf.bak（不是 extlinux.conf）

armbianEnv.txt 关键配置：

~~~ini
verbosity=7
bootlogo=true
fdtfile=rockchip/rk3566-panther-x2.dtb
rootdev=UUID=9c7ff1a4-9beb-4346-b396-cdd1d4d1feea
rootfstype=ext4
rootflags=rw,errors=remount-ro
earlycon=on
console=both
consoleargs=console=ttyS02,1500000 console=tty0
docker_optimizations=on
extraargs=rw rootwait
extraboardargs=net.ifnames=0 max_loop=128
overlay_prefix=rk3566
overlays=
user_overlays=
usbstoragequirks=0x2537:0x1066:u,0x2537:0x1068:u
~~~

当前 boot.cmd 逻辑：
- 从 U-Boot 当前设备（devtype/devnum）读取并导入 armbianEnv.txt。
- 通过 part uuid 获取当前启动设备第一分区 PARTUUID。
- 从同一设备加载 uInitrd、Image、dtb/${fdtfile}，最后 booti。

当前 cmdline 的 root UUID 和 ubootpart 均与 TF 卡对应，强烈支持当前启动脚本从 TF 卡 BOOT 分区加载内核、initrd、DTB，并以 TF ROOTFS 启动 Linux。

### 7.4 文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| /boot/boot.scr | 0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a |
| /boot/boot.cmd | 4896dde2b99bebbb34b2ed2f837f30fa1a5b3ad14b80dd2da391effa94d37d0a |
| /boot/vmlinuz-6.12.81-rk35xx-ophub | f3164d866f075e01472ed04ba380535a1d5dfcf1b622f10484368a3a5543bb4c |
| /boot/uInitrd-6.12.81-rk35xx-ophub | a6091faeb544866f4f4af296089fb9106870c5f129ae039c33a5b86f700246c7 |
| /boot/dtb/rockchip/rk3566-panther-x2.dtb | 00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185 |

### 7.5 boot.cmd / boot.scr 时间差异

file /boot/boot.scr 输出：

~~~text
u-boot legacy uImage, , Linux/ARM, Script File (Not compressed),
3318 bytes, Tue Apr 25 02:03:55 2023,
Load Address: 00000000, Entry Point: 00000000
~~~

boot.scr 镜像头时间为 2023-04-25，而 boot.cmd 文件时间为 2026-11-15。不能假设当前 boot.scr 由当前 boot.cmd 生成。必须解码实际 boot.scr 内容再比较设备选择、加载路径和 bootargs。dumpimage 实机解码结果尚未提供。

### 7.6 TF 卡 GPT / 启动区候选范围

- /dev/mmcblk0，总扇区 124735488，logical block size 512 bytes，容量 59.48 GiB / 63864569856 bytes。
- GPT first-lba 34，last-lba 124735454。

| 分区 | 起始 LBA | sectors | 结束 LBA | 大小 |
|---|---:|---:|---:|---:|
| mmcblk0p1 BOOT | 32768 | 1046528 | 1079295 | 511M |
| mmcblk0p2 ROOTFS | 1081344 | 123654111 | 124735454 | 59G |

LBA 0–32767（16 MiB）位于首分区之前，是本轮重点检查的 Rockchip 启动区域候选范围；该范围也包含 GPT 前部/未分区空间，不能把全部内容等同于 bootloader。

**尚未执行：** 从 /dev/mmcblk0 只读提取前 32768 sectors 到 /tmp/panther-tf-first16m.bin。此前 dd 命令只是待执行建议，不是已完成测试。

## 8. U-Boot 与 Rockchip 启动链线索

### 8.1 eMMC 历史镜像边界

既有报告 EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md 记录：
- eMMC 用户区 LBA64 的 idbloader.img 与 Ophub Panther X2 目录文件逐字节一致。
- eMMC 用户区 LBA16384 的 u-boot.itb 与 Ophub Panther X2 目录文件逐字节一致。
- idbloader 字符串：U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)。
- 内嵌 FDT model=Radxa E25，compatible=radxa,e25 / rockchip,rk3568。
- 旧 UART 日志有相同版本/构建时间及 Model: Radxa E25。

**纠正：** 以上只证明 eMMC 中存在该旧镜像。用户已明确本轮实际启动 U-Boot 从 TF 卡读取数据，不能把 eMMC 镜像当成本轮实际执行文件。当前 TF 卡启动区尚未提取。

### 8.2 E23 / E25 defconfig 对照

Radxa U-Boot commit：c55987146f4f9b20f7cb2f917ca88300419afe8d
- radxa-e23-rk3566_defconfig 与 radxa-e25-rk3568_defconfig 相关配置基本相同。
- 两者均启用 CONFIG_ROCKCHIP_RK3568=y、CONFIG_GMAC_ROCKCHIP=y、CONFIG_DWC_ETH_QOS=y 等。
- 不能仅凭 CONFIG_ROCKCHIP_RK3568=y 判断 E23/RK3566 defconfig 一定错误。
- 读取 arch/arm/dts/rk3566-radxa-e23.dts 与 rk3568-radxa-e25.dts 曾返回异常/近乎空，尚未完成 E23/E25 GMAC DTS 逐项比较。
- drivers/net/gmac_rockchip.c 存在 RK3568 GMAC delay/GRF 配置分支；尚未确认当前 TF U-Boot 是否实际 probe/初始化 GMAC1。

### 8.3 U-Boot clock parent 上游案例

Linux Rockchip 邮件列表 2026-11-02 的 RK3568 GMAC clock PATCH v3 指出：某些 DTS 只为 SCLK_GMACx_RX_TX 设置 parent，而 SCLK_GMACx 未显式设置 parent，后者可能沿用 Bootloader 或硬件 reset 的 parent。

这是 RK3568 上真实的风险类别，但不能直接套用 Panther：
- Panther 当前 FDT 对 GMAC1 assigned-clocks / assigned-clock-parents 有显式配置。
- Linux clk_summary 显示 GMAC1 相关时钟均为预期 125MHz。
- Linux 接管后的错误 clock parent/频率嫌疑降低；仍需确认 Linux 写入之前的状态及物理时钟信号。

### 8.4 TF U-Boot 待审计内容

1. SPL/idbloader 构建版本、SHA-256、字符串、内嵌 FDT。
2. U-Boot 主镜像（可能 u-boot.itb 或其他格式）的 FIT metadata、config、内嵌 DTB。
3. 实际板级配置是 Panther X2、Radxa E23 还是 E25，以及真实适配关系。
4. 当前 U-Boot 是否 probe GMAC1、调用哪个 Rockchip GMAC 驱动、是否配置 RGMII delay / GRF / CRU / pinctrl。
5. SPL、U-Boot proper、Linux 三阶段对 GMAC/PHY reset、clock、GRF、pinctrl 的交接。
6. 即使 U-Boot 未 probe GMAC1，也要审查 SPL/board init 是否可能写入 CRU/GRF/pinctrl。

## 9. 外部源码 / 资料

- 项目固定 Linux 6.12：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c
- Linux dwmac-rk.c 字段定义/写入逻辑：此前检索 turn982038search0。
- RK3568 TRM：此前检索 turn982038search12；GRF_MAC1_CON0 offset 0x0388、CON1 offset 0x038C。
- U-Boot Rockchip GMAC 驱动参考：此前检索 turn982038search3、turn982038search4。
- RK3568 GMAC clock parent 上游讨论（2026-11-02）：https://lore.landau.one/lkml/20261102174450.3000397-2-coiaprant%40gmail.com/T/
- RK3568 TRM PDF：https://dl.radxa.com/rock3/docs/hw/datasheet/Rockchip%20RK3568%20TRM%20Part1%20V1.1-20210301.pdf
- Radxa U-Boot E23/E25 defconfig commit：https://github.com/radxa/u-boot/commit/c55987146f4f9b20f7cb2f917ca88300419afe8d

## 10. 已完成检查（不要无故重复）

- 网线更换、千兆链路问题解决；当前 1000Mbps Full Duplex。
- Panther 本机 DHCP Discover 抓包；hEX 抓包（未见 Panther 报文）。
- NetworkManager / Netplan / udev / 接口命名检查。
- RTL8211F PHY 地址与驱动识别。
- Linux 6.1 与项目固定 6.12 的 RGMII / Realtek PHY delay 代码对照。
- 运行时 FDT GMAC1 节点与 phandle/pinctrl 对照。
- GMAC1 pinmux 实机状态检查。
- PHY reset GPIO phandle、GPIO line、pinmux/pinconf 和驱动 reset 时序检查。
- Linux GMAC1 clock_summary 检查。
- Linux GRF_MAC1_CON0/CON1 只读寄存器检查。
- TF/eMMC 身份、分区、UUID、PARTUUID、挂载来源核对。
- 当前 TF /boot 的 boot.cmd、boot.scr、内核、initrd、DTB 哈希。
- TF GPT 与分区起始 LBA 核对。

## 11. 下一步

### A. TF U-Boot 直接取证（只读，尚未执行）

~~~bash
dd if=/dev/mmcblk0 of=/tmp/panther-tf-first16m.bin \
   bs=512 count=32768 iflag=fullblock status=progress

sha256sum /tmp/panther-tf-first16m.bin

strings -a -t x /tmp/panther-tf-first16m.bin |
grep -Ei 'U-Boot|Model:|rk356|radxa|panther|E23|E25|SPL|DDR|DRAM|Rockchip'

file /tmp/panther-tf-first16m.bin
xxd -g 1 -l 128 /tmp/panther-tf-first16m.bin
xxd -g 1 -s $((64 * 512)) -l 128 /tmp/panther-tf-first16m.bin
xxd -g 1 -s $((16384 * 512)) -l 128 /tmp/panther-tf-first16m.bin
~~~

读取源固定为已确认的 TF 卡 /dev/mmcblk0，输出写入当前系统 /tmp。执行前复核设备身份；不得误将 /dev/mmcblk1（eMMC）作为目标。

### B. 解码实际 boot.scr（只读，尚未提供结果）

~~~bash
dumpimage -l /boot/boot.scr
dumpimage -T script -p 0 -o /tmp/panther-boot.scr.txt /boot/boot.scr
cat /tmp/panther-boot.scr.txt
~~~

如果没有 dumpimage，先报告工具缺失，不要为此擅自安装软件。

### C. 精确源码核对

确定 TF 卡实际 SPL/U-Boot 版本后，再找精确源码、defconfig、DTS、构建脚本，避免用 eMMC 历史镜像或泛化 E25 源码猜测本轮启动。

### D. 如 U-Boot 配置基本排除

聚焦物理 RGMII/PHY 链路证据，区分 MAC 内部配置与 GRF delay、PHY 内部 delay、PCB 走线延迟、TXC/RXC 与数据线 setup/hold、PHY 到交换机的 MDI 发送质量。无波形或 PHY 专用诊断证据前，不擅自改变 tx_delay/rx_delay 或切换 rgmii/rgmii-id。

## 12. 结论状态矩阵

| 项目 | 状态 | 说明 |
|---|---|---|
| DHCP Discover 到达 Linux 抓包点 | 已验证 | 本机 tcpdump 捕获 |
| DHCP Discover 成功发出 PHY 引脚 | 未验证 | 抓包点不等于 PHY 引脚 || hEX 收到 Panther DHCP Discover | 未观察到 | 既有抓包结果 |
| 1000Mbps Full Duplex Link | 已验证 | 换网线后恢复 |
| PHY RTL8211F / 地址 0 | 已验证 | MDIO / 驱动识别 |
| Linux GMAC1 DT M0 RGMII | 已验证 | 运行时 FDT + pinmux |
| Linux GRF delay | 已验证 | CON0=0x1030，CON1=0x13 |
| Linux GMAC1 软件时钟树 | 已验证 | 125MHz 相关时钟已使能 |
| PHY reset 脉冲失败 | 无证据支持 | 驱动时序及释放状态相容 |
| RGMII 物理时序正确 | 未验证 | 无引脚波形测量 |
| TF 卡为当前 Linux 启动介质 | 已验证 | MMC type、UUID、PARTUUID、挂载来源 |
| TF 卡原始 SPL/U-Boot 身份 | 待验证 | 前 16 MiB 尚未提取 |
| eMMC 旧 U-Boot 文件身份 | 已验证 | 见 eMMC 审计报告 |
| eMMC 旧 U-Boot 是本轮实际执行镜像 | 不是当前结论 | 本轮 U-Boot 读取 TF 卡数据 |
| U-Boot 遗留状态导致 DHCP 故障 | 推测/待验证 | 需审计实际 TF U-Boot |

## 13. 维护约定

- 新实机输出追加本报告或独立证据文件，注明采集时间、命令、设备身份和是否只读。
- 原始 UART 日志原样存放 evidence/uart/；报告只引用，不改写原始文件。
- 真实 MAC 地址及其可还原字节不写入公开仓库。
- 新发现与旧结论冲突时，保留旧证据并新增纠错记录，不覆盖历史事实。
- 不重复已完成测试；优先用能区分假设的最小只读证据推进。


---

## 14. 2026-11-17 补充：TF 卡前 16 MiB 与实际 boot.scr 取证

本节为本日后续实机输出的追加记录，优先级高于本文前文中“TF 原始启动区尚未提取”“boot.scr 解码尚未提供”等旧状态描述。原有历史记录保留，避免静默改写调查过程。

### 14.1 TF 卡前 16 MiB 只读取证

用户确认读取命令的目标是 TF 卡启动介质，读取结果：

~~~text
32768+0 records in
32768+0 records out
16777216 bytes (17 MB, 16 MiB) copied, 0.730722 s, 23.0 MB/s
~~~

输出文件：`/tmp/panther-tf-first16m.bin`

SHA-256：

~~~text
75c7e878c4ea78aea76fb9ecb3b037becfe413ba467603df34a4258d9688a70f  /tmp/panther-tf-first16m.bin
~~~

`file` 识别结果：

~~~text
DOS/MBR boot sector; partition 1 : ID=0xee, startsector 1, 124735487 sectors
~~~

这是 GPT protective MBR 的正常表现；不能据此认为该 TF 卡不是 Rockchip 启动盘。读取范围是 LBA 0–32767（16 MiB），其中既有 GPT/前部空隙，也包含 Rockchip 启动镜像区域。

### 14.2 关键启动镜像字符串

在这份 TF 原始前 16 MiB 数据中，`strings -a -t x` 找到以下相互印证的字符串：

~~~text
0x3ec09  U-Boot SPL 2017.09-armbian (Apr 23 2023 - 13:08:07)
0x3f138  rockchip,rk3566
0x4d50c  radxa,e25
0x4d516  rockchip,rk3568
0x4d563  7Radxa E25
0x80007c FIT Image with ATF/OP-TEE/U-Boot
0x8000f4 U-Boot(64-bit)
0x800768 U-Boot dtb
0x800848 rk3568-radxa-e25
0x8ddd8f board=evb_rk3568
0x8ddda0 board_name=evb_rk3568
0x8dde8d fdtfile=rockchip/rk3568-radxa-e25.dtb
0x8df174 Model: %s Firm: %s Ser#: %s
0x8f5c3e gmac_rockchip
0x8f5c4c rockchip,rk3568-gmac
0x8f9cf5 U-Boot 2017.09-armbian (Apr 23 2023 - 13:08:07 +0000)
~~~

另有 SPL DDR 初始化字符串 `DDR Version V1.13 20220218`，以及 Rockchip RK3568 CRU、GRF、pinctrl、GMAC 驱动相关字符串。

**证据结论：**
- **已验证：** TF 卡前 16 MiB 中包含 SPL 和 U-Boot proper 的可识别字符串，构建标识均为 U-Boot 2017.09-armbian（2023-04-23）。
- **已验证：** 该启动数据包含 Radxa E25 / RK3568 的板级标识、内嵌 U-Boot DTB 名称 `rk3568-radxa-e25`，环境默认值包含 `board=evb_rk3568` 与 `fdtfile=rockchip/rk3568-radxa-e25.dtb`。
- **已验证：** 同一镜像包含 Rockchip RK3568 GMAC 驱动匹配字符串。
- **重要限制：** 字符串存在不等于对应驱动一定在本次启动中 probe，也不等于 GMAC1 一定被初始化；仍需结合启动日志、U-Boot DM probe 结果、精确 DTS 和代码调用路径确认。
- **重要限制：** TF 卡内嵌 E25/RK3568 U-Boot 控制 DTB 与 Linux 最终使用的 Panther X2/RK3566 DTB 是不同阶段、不同用途的设备树。不能混为一谈。
- **风险判断：** 对 RK3566 Panther X2 而言，实际启动链包含 E25/RK3568 板级配置，是明确的板级适配错配风险，值得优先审计；但目前仍不足以单独证明它导致 DHCP 报文未到达 hEX。

本次 `xxd` 检查未成功执行，终端提示 `zsh: command not found: xxd`。没有因此安装软件；也没有原始 16 MiB 二进制附件上传到仓库。本记录保存哈希、字符串偏移及可复核的命令输出摘要。

### 14.3 实际 TF boot.scr 已解码

用户提供的 `dumpimage -l` 信息：

~~~text
Image Name:
Created:      Tue Apr 25 10:03:55 2023
Image Type:   ARM Linux Script (uncompressed)
Data Size:    3318 Bytes = 3.24 KiB
Load Address: 00000000
Entry Point:  00000000
Contents:
   Image 0: 3310 Bytes = 3.23 KiB
~~~

已解码脚本的关键行为：
1. 从 U-Boot 当前 `${devtype} ${devnum}` 设备读取 `armbianEnv.txt` 并导入环境变量。
2. 通过 `part uuid ${devtype} ${devnum}:1 partuuid` 取得当前设备第一分区 PARTUUID。
3. 从同一当前设备加载 `uInitrd`、`Image` 和 `dtb/${fdtfile}`。
4. 应用 kernel overlays / fixup script（若配置并存在）。
5. 最后执行 `booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}`。

解码输出中的默认变量包括 `rootdev=/dev/mmcblk0p1`，但脚本随后会尝试从启动分区读取 `armbianEnv.txt` 并导入其配置；不能仅凭脚本默认值推断最终 root 设备。此前运行时 `/proc/cmdline` 的 root UUID 和 `ubootpart` PARTUUID 均已对应 TF 卡分区。

**时间差异：** boot.scr 镜像头创建时间为 2023-04-25；当前 boot.cmd 文件系统时间为 2026-11-15。两者时间明显不同，不能假定当前 boot.scr 是由当前 boot.cmd 生成。应以实际 boot.scr 解码内容作为本次 U-Boot 执行脚本证据。

### 14.4 U-Boot 线索更新后的判断

| 项目 | 状态 | 结论 |
|---|---|---|
| 本轮实际启动数据来自 TF 卡 | 已验证（结合此前设备身份、PARTUUID、挂载证据及本次 TF 原始区读取） | 不应再用 eMMC 历史镜像代替本轮 U-Boot |
| TF 前 16 MiB 中 SPL 版本 | 已验证 | U-Boot SPL 2017.09-armbian，2023-04-23 |
| TF 前 16 MiB 中 U-Boot proper 版本字符串 | 已验证 | U-Boot 2017.09-armbian，2023-04-23 |
| TF U-Boot 内嵌控制 DTB 标识 | 已验证 | rk3568-radxa-e25 / Radxa E25 |
| U-Boot 默认 fdtfile | 已验证（镜像字符串） | rockchip/rk3568-radxa-e25.dtb |
| 当前 Linux 使用 Panther X2 DTB | 已验证（运行时 FDT 与 /boot 文件） | 不代表 U-Boot 控制 DTB 也是 Panther X2 |
| U-Boot proper 是否实际 probe GMAC1 | 未验证 | 字符串只能证明代码/匹配表被编入镜像 |
| U-Boot 是否更改 GMAC1 CRU/GRF/pinctrl 并遗留状态 | 未验证 | Linux 最终读回值不能还原交接瞬间状态 |
| E25/RK3568 板级适配导致 DHCP 故障 | 高优先级假设，未证实 | 需精确核对实际 U-Boot DTS、probe 路径及寄存器交接 |

### 14.5 下一轮最有价值的只读审计

1. 对照 TF U-Boot proper 内嵌 DTB 的完整 GMAC1 节点：status、reg、phy-mode、clock、clock-names、assigned-clocks、assigned-clock-parents、pinctrl、reset GPIO、PHY 节点及 MDIO。
2. 查明 TF U-Boot 构建对应的确切源码/补丁集；追踪 SPL board init、U-Boot board init 和 `gmac_rockchip` / DWC ETH QoS probe 是否会触及 GMAC1。
3. 对比 E25 U-Boot DT 与 Panther X2 Linux DT：尤其 GMAC1 M0/M1 pinmux、PHY reset GPIO、时钟源、RGMII delay、PHY 供电/复位时序。不能只比较 compatible 字符串。
4. 如能从历史 UART 找到 U-Boot 启动时的 `Model:`、`Net:`、GMAC probe、PHY link 或 `fdtfile` 日志，优先用来判断实际运行路径；没有日志则标为未验证。
5. 不因发现 E25 标识而直接刷写/替换 U-Boot，也不修改 delay、时钟、DTB 或网络配置。先完成源码和证据链审计。

详细采集摘要另见：[TF 前 16 MiB 与 boot.scr 只读证据记录](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)。

## 15. 6.12.81 GMAC RX / DMA / NAPI 与时钟只读复核（2026-11-17）

用户补充了当前 Armbian 系统的接口状态、内核日志筛选结果、ip -s link、/proc/interrupts 和完整 ethtool -S eth0。仅记录本次实际输出；未执行 DHCP renew、接口重启、驱动重载或任何配置修改。

### 15.1 接口与 NetworkManager 状态

| 项目 | 结果 |
|---|---|
| 接口 | eth0，UP / LOWER_UP |
| Carrier | on |
| 当前 MTU | 1500 |
| NetworkManager profile | Wired connection 1 |
| profile 的 MTU 设置 | auto |
| MAC | 已脱敏，不在报告公开 |

nmcli 查询 profile MTU 返回 auto，表示 profile 未固定 MTU；运行时接口 MTU 为 1500。此前使用 connection.id 作为 nmcli -f 字段时收到 invalid field，因此未将该命令输出作为有效证据。

### 15.2 RX 软件、驱动和 MAC 计数

ip -s link show dev eth0：

| 指标 | 结果 |
|---|---:|
| RX bytes | 2,244,918 |
| RX packets | 25,539 |
| RX errors | 0 |
| RX dropped | 1,694 |
| RX missed | 0 |
| TX packets | 283 |
| TX errors / dropped | 0 |

ethtool -S eth0 关键字段：

| 指标 | 结果 |
|---|---:|
| mmc_rx_framecount_gb | 25,663 |
| mmc_rx_octetcount_gb | 2,358,886 |
| rx_pkt_n | 25,663 |
| q0_rx_pkt_n | 25,663 |
| rx_normal_irq_n | 25,649 |
| q0_rx_irq_n | 25,649 |
| normal_irq_n | 25,660 |
| napi_poll | 51,984 |
| mmc_rx_crc_error | 0 |
| mmc_rx_align_error | 0 |
| mmc_rx_fifo_overflow | 0 |
| mmc_rx_error | 0 |
| rx_desc | 0 |
| rx_gmac_overflow | 0 |
| rx_missed_cntr | 0 |
| rx_overflow_cntr | 0 |
| rx_overflow_irq | 0 |
| rx_buf_unav_irq | 0 |
| rx_process_stopped_irq | 0 |
| rx_watchdog_irq | 0 |
| fatal_bus_error_irq | 0 |

/proc/interrupts 中出现两条 eth0 相关 IRQ：
- IRQ 67：CPU 计数列为 154 / 0 / 0 / 25875。
- IRQ 68：各 CPU 计数均为 0。
### 15.3 证据解释与限制

1. **已验证：** 本次快照中 GMAC MAC 统计、驱动 RX 统计、RX IRQ 和 NAPI poll 均有显著非零计数。RX 接收通路不是完全静默状态。
2. **已验证：** 当前快照未报告 CRC、alignment、FIFO overflow、RX buffer unavailable、RX process stopped 或 fatal bus error 计数。
3. **已验证：** Linux netdev 累计 RX dropped 为 1,694，RX errors 和 missed 为 0。
4. **待解释：** ip -s link 的 RX packets=25,539，与 rx_pkt_n / q0_rx_pkt_n / mmc_rx_framecount_gb=25,663 不同，差 124。两组计数来自不同层次，命令也非严格同时采样；不能把 124 直接解释为线上丢包数。
5. **待解释：** netdev RX dropped=1,694 是累计统计，本次没有紧邻的前后两次采样，因此不能由此计算本次时间窗口的 dropped 增量，也不能直接归因于 DHCP 报文。
6. **重要边界：** MAC 接收计数增长证明接收硬件路径正在处理流量，但不证明 DHCP Discover 已发出 PHY，也不证明 DHCP Offer 已被接收；本次数据不能单独定位 DHCP 故障方向。
7. 用户终端粘贴过程中有多条命令发生错位；内核日志筛选输出仅明确显示 Nov 16 07:00:12 的 Link is Up - 1Gbps/Full。未看到 DMA reset 错误，但不能将该次筛选视为完整、无遗漏的日志审计。

### 15.4 GMAC 初始化日志与时钟复核

用户提供的 dmesg 关键记录包括：
- GMAC1 fe010000.ethernet probe；
- clock input from PHY、init for RGMII；
- TX delay 0x30、RX delay 0x10；
- Synopsys User ID 0x30、Synopsys ID 0x51，识别为 DWMAC4/5；
- DMA capability、RX/TX checksum offload、TSO 等能力识别；
- Register MEM_TYPE_PAGE_POOL RxQ-0；
- RTL8211F PHY，MDIO 地址 0，IRQ=POLL；
- PTP clock registered；
- configuring for phy/rgmii link mode；
- Link Up 1Gbps/Full，flow control rx/tx。

运行时 clock-names 共 10 项：
stmmaceth、mac_clk_rx、mac_clk_tx、clk_mac_refout、aclk_mac、pclk_mac、clk_mac_speed、ptp_ref、pclk_xpcs、clk_xpcs_eee。

clk_summary 中 GMAC1 主要活动消费者及频率：
- stmmaceth / clk_gmac1：125 MHz，enable/prepare 计数非零；
- mac_clk_rx、mac_clk_tx / clk_gmac1_rx_tx：125 MHz，计数非零；
- clk_mac_speed / clk_gmac1_rgmii_speed：125 MHz，计数非零；
- gmac1_clkin：125 MHz，计数非零；
- aclk_mac / aclk_gmac1：297 MHz，计数非零；
- pclk_mac / pclk_gmac1：99 MHz，计数非零；
- ptp_ref / clk_gmac1_ptp_ref：62.5 MHz，计数非零。
- pclk_xpcs 与 clk_xpcs_eee 为 0/0；当前 PHY/RGMII 模式下不能仅凭未使能就判为故障，XPCS 时钟不应与基本 RGMII GMAC 时钟混为一谈。
- clk_mac_refout 未显示为活动消费者；结合日志的 clock input from PHY，这种状态可能符合当前输入时钟配置，但仅凭 clk_summary 不能证明该 clock handle 从未被获取。

**阶段判断：** 当前日志、clock_summary 和 RX 计数共同证明 GMAC 已完成 probe、PHY 识别、RGMII 配置、链路建立，并持续处理 RX 流量。当前证据不支持 GMAC RX 完全未启动或基本 GMAC 时钟全部缺失。它们仍不能排除更细粒度的 DMA 描述符、包过滤、特定帧处理或 TX 物理边界问题。

### 15.5 6.1 / 6.12 源码对照的证据等级

本轮查看了 Linux 6.1.116 上游源码与 Rockchip Linux 6.12 开发分支快照：
- stmmac_rx_refill() 主体未发现实质差异；
- stmmac_init_dma_engine() 主体流程相近，存在描述符配置等差异；
- stmmac_rx() 存在后续版本功能路径变化（包含 XDP/VLAN/checksum 相关逻辑），当前没有证据证明这些变化导致普通 DHCP 报文被丢弃；
- RTL8211F PHY suspend 实现存在版本差异：6.1.116 路径使用 genphy_suspend，所查 6.12 分支增加 rtl821x_suspend 及可选 PHY clock 关闭逻辑。

**限制：** 上述 6.12 开发分支快照尚未证明与设备当前运行的 6.12.81-rk35xx-ophub Image 精确对应；因此这些只是候选源码差异，不能写成当前运行二进制的确定行为。当前运行时 PHY 节点未见 clocks / clock-names 属性，故可选 PHY clock 关闭路径在本机是否实际生效也未证实。

另发现上游同类问题报告：RK3566 + RTL8211F-VD + RGMII 在接口重开、PHY 接收时钟尚未恢复时，可能触发 Failed to reset the dma；报告场景涉及 NetworkManager 设置 MTU 后重开接口。该问题是条件性候选，不是本机已发生事实。本次 MTU profile 为 auto、运行时 MTU=1500，提供的日志片段未出现 DMA reset 错误；但本轮日志筛选过程有粘贴错位，不能据此彻底排除。上游修复参考：https://github.com/torvalds/linux/commit/06232cb44bc8

### 15.6 下一步定位调整

1. 将研究重点从 GMAC 是否完全收不到包，调整为 DHCP 报文在 Linux、MAC/PHY、交换网络和 hEX 之间的具体边界。
2. 下一项有区分度的证据是被动监听 eth0 的 UDP 67/68 报文，确认 Discover/Offer 是否实际经过接口；不主动 renew，不重启接口。
3. 若需定位 TX 边界，应把同一个 DHCP Discover 与 hEX 入口同步抓包关联；本机 outgoing packet capture 本身不等于 PHY 线侧发送成功。
4. 只有在确认 DHCP 报文实际 RX 到达而未交给客户端，或 dropped 继续增长时，才进一步定位普通 RX skb / NAPI 处理路径。
5. 不重复已完成的基础 DHCP、链路、PHY ID、RGMII delay、GRF、时钟、pinmux 和 PHY reset GPIO 检查；不运行会停止网卡的 phy_lb。
6. 未经明确授权，不安装软件、不修改内核/驱动/DTB/网络配置、不重启 NetworkManager 或 eth0。


## 13. 2026-11-17 后续补充：同一 Linux 6.12.81 启动环境的 GMAC RX / DMA / NAPI 统计与 MAC 身份线索

本节记录同一 Linux 6.12.81 内核环境下随后一轮只读实机输出。它是不同采样时点的统计快照，不代表更换或运行过另一套 6.12.69 内核；不同启动周期/驱动生命周期的累计计数仍不得直接相减。

### 13.1 接口与 MTU

- 本轮运行环境仍为 Linux 6.12.81-rk35xx-ophub；用户确认期间只更换过 U-Boot，没有更换 Linux 内核包。
- eth0：UP / LOWER_UP，Carrier on，运行时 MTU=1500。
- NetworkManager profile `Wired connection 1` 的 MTU 设置为 `auto`。
- 内核日志筛选输出只明确显示 RTL8211F 链路 Up：1Gbps / Full / flow control rx/tx；没有看到 DMA reset failure、DMA engine initialization failure、Hw setup failure 或 Link Down 的匹配行。由于本轮 grep 输出并非完整启动日志，不能将“未显示”提升为完整日志审计结论。

### 13.2 RX / IRQ / DMA / NAPI 计数快照

| 指标 | 本轮读数 |
|---|---:|
| netdev RX packets | 25,539 |
| netdev RX bytes | 2,244,918 |
| netdev RX errors | 0 |
| netdev RX dropped | 1,694 |
| netdev RX missed | 0 |
| netdev TX packets | 283 |
| netdev TX errors / dropped | 0 |
| `mmc_rx_framecount_gb` | 25,663 |
| `mmc_rx_octetcount_gb` | 2,358,886 |
| `rx_pkt_n` / `q0_rx_pkt_n` | 25,663 / 25,663 |
| `rx_normal_irq_n` / `q0_rx_irq_n` | 25,649 / 25,649 |
| `normal_irq_n` | 25,660 |
| `napi_poll` | 51,984 |
| IRQ 67（四 CPU 计数） | 154 / 0 / 0 / 25,875 |
| IRQ 68（四 CPU 计数） | 0 / 0 / 0 / 0 |

以下硬件/驱动错误计数本轮均为 0：MMC CRC、alignment、run、jabber、FIFO overflow、watchdog、discard；驱动 RX descriptor、overflow、checksum、CRC、length、MII、GMAC overflow、watchdog、missed、buffer unavailable、process stopped、fatal bus error 等相关项。

### 13.3 解释边界

1. GMAC MAC 接收统计、RX IRQ 与 NAPI 均有大量活动；本轮证据不支持“GMAC RX 完全未启动”或“RX DMA 整体没有工作”。
2. `ip -s link` 的 RX dropped=1,694 是真实 netdev 统计，但本轮没有相邻采样，也没有将其定位到 DMA descriptor、驱动丢弃、协议栈或其他网络层的证据。不得直接把它归因于 DMA。
3. netdev RX packets=25,539 与驱动/MMC RX frame=25,663 相差 124。各层统计口径可能不同；没有逐包关联和源码口径证明前，不将差值解释为线上丢包。
4. `mmc_rx_framecount_gb` 与 `rx_pkt_n` 本轮均为 25,663，说明这两个统计在该快照数值相同，但不代表它们与 netdev RX packet 计数必须完全相等。
5. IRQ 67 有活动、IRQ 68 为零；单凭这一点不能判定第二中断向量异常，需结合驱动实际中断申请与使用方式判断。

### 13.4 MAC 地址身份线索（脱敏）

- 已有 eMMC Vendor Storage 审计确认板载记录中存在以 `86:…` 开头的 GMAC 地址。
- 本轮 Linux eth0 运行时地址以 `E6:…` 开头；历史实机记录中也出现过相同运行时地址。
- 这两个地址前缀不同，是必须保留的启动链 / MAC 传递线索；本报告不公开完整地址。
- 已知当前启动 U-Boot 读取 TF 卡上的 Vendor 数据，而不是 eMMC 上的 Vendor 数据。该事实不能被误写为“eMMC 没有保存板载 MAC”。
- 运行时地址与 eMMC Vendor Storage 中的板载地址不同，本身尚不能证明 DHCP 故障由 MAC 不一致导致。DHCP Discover 是否发出、帧源 MAC、U-Boot/TF Vendor 数据、设备树 `local-mac-address` / `mac-address`、内核 NVMEM/平台数据及 NetworkManager 覆盖关系，仍需按实际启动链逐层建立对应关系。
- MAC 不一致也不能单独解释 hEX 未见 Discover：必须先确认 Discover 的实际 Ethernet source address，以及该帧是否到达 Panther PHY 线侧。

### 13.5 当前结论与下一步

- 已降低“GMAC RX 时钟未启用 / RX DMA 完全失效”的可能性；Linux RX 通路正在处理大量流量。
- RX dropped=1,694 的具体来源仍未知；它是接收侧独立问题，不应直接用来解释 DHCP Discover 的发送失败。
- DHCP 故障边界仍是 Panther 本机 outgoing 抓包点之后、hEX 观察点之前；尚未确定是 MAC TX、RGMII、PHY、链路转发还是报文身份/过滤问题。
- 下一步优先使用被动方式确认 DHCP 报文的 Ethernet source MAC，并与已知 eMMC Vendor Storage、TF Vendor 数据和运行时 FDT/NVMEM 来源对应；必要时再安排 Panther 与 hEX 同一时间窗口的双端抓包。
- 本轮没有执行 DHCP renew、接口重启、驱动重载、软件安装、配置修改、寄存器写入或系统重启。


## 16. 2026-11-17 补充：同一 Linux 6.12.81 环境的 ethtool 统计字段完整性与 DHCP 被动监听状态

本节补充 13.2 表格未逐项展开、但用户在同一轮 `ethtool -S eth0` 输出中提供的字段。它们属于同一 Linux 6.12.81 环境的同一采样快照；与其他采样时点或不同驱动生命周期的累计值分开处理。

### 16.1 其他 RX / 协议分类计数

| 字段 | 读数 | 解释边界 |
|---|---:|---|
| `ipv4_pkt_rcvd` | 3,536 | 驱动统计的 IPv4 接收包数 |
| `ipv6_pkt_rcvd` | 182 | 驱动统计的 IPv6 接收包数 |
| `ip_csum_bypassed` | 21,939 | checksum bypass 相关计数；不等于校验失败数 |
| `no_ptp_rx_msg_type_ext` | 25,663 | PTP message type extension 相关计数；不据此推断普通数据包异常 |
| `mmc_rx_broadcastframe_g` | 0 | MMC 广播帧计数 |
| `mmc_rx_multicastframe_g` | 2,168 | MMC 多播帧计数 |
| `mmc_rx_unicast_g` | 0 | MMC 单播帧计数 |

其中 `mmc_rx_framecount_gb=25,663`，但 `mmc_rx_unicast_g=0`、`mmc_rx_broadcastframe_g=0`，而多播计数为 2,168。此组合需要结合具体 MMC counter 定义、硬件统计使能和驱动读取方式再解释；不能仅凭 `mmc_rx_unicast_g=0` 推断接口没有接收单播流量，因为同一快照中 netdev、驱动 RX packet 和 IRQ/NAPI 计数均有大量活动。

### 16.2 其他 TX / NAPI 计数

| 字段 | 读数 |
|---|---:|
| `tx_pkt_n` | 283 |
| `tx_normal_irq_n` | 11 |
| `tx_clean` | 26,335 |
| `tx_set_ic_bit` | 11 |
| `q0_tx_pkt_n` | 283 |
| `q0_tx_irq_n` | 11 |
| `q0_rx_pkt_n` | 25,663 |
| `q0_rx_irq_n` | 25,649 |

这些是当前接口/驱动累计统计，不构成 DHCP Discover 已从 PHY 发出的证据。特别是 `tx_pkt_n=283` 只能说明驱动 TX completion 统计；不能替代对特定 DHCP 帧的线上确认。

### 16.3 DHCP 被动监听状态

- 当前尚未执行新的 DHCP 专项被动抓包。
- 尚未先行核实 `tcpdump` 是否已安装；下一步应先检查工具是否存在，再决定是否运行只监听 UDP 67/68 的抓包。
- 不主动触发 DHCP renew，不重启 eth0 / NetworkManager，不重载驱动，不修改网络配置。
- 目标是确认本轮 Discover/Offer 是否经过 eth0，并在需要时与 hEX 入口同一时间窗口的抓包对应；本机 outgoing capture 仍不能单独证明 PHY 线侧发送成功。

**本节状态：** 仅整理既有只读输出，没有在设备上执行新命令或改变配置。

## 17. 版本标签纠错：6.12.69 是源码比较基线，不是 Panther 实机内核

此前第 13、16 节曾将后续 RX/IRQ/NAPI 统计快照误标为 Linux 6.12.69。这是报告整理错误，现予更正。

- **实机运行内核：** `6.12.81-rk35xx-ophub`。2026-11-17 JP-TvBox U-Boot 实机启动 UART 原始日志中的 `Linux version` 行明确报告该版本；`/boot` 内核文件名也为 `vmlinuz-6.12.81-rk35xx-ophub`。
- **本轮实际使用的内核包基线：** Ophub `kernel_rk35xx` 标准资产 `6.12.81.tar.gz`，记录大小 141,437,450 bytes，SHA-256 `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`。Flippy 资产是另一个独立发布变体，虽曾被离线审计，但没有证据表明它被安装或用于本次实机启动。
- **6.12.69 的真实含义：** 源码对照章节中 Rockchip `develop-6.12` 分支 Makefile 的 `SUBLEVEL=69`，用于与 Ophub 6.12.81 源码做函数级比较；它不是本机 `uname -r`，也不是另一次内核安装或启动。
- **实机测试变量：** 用户确认相关测试期间没有更换 Linux 内核包，只更换过 U-Boot。因而网络测试报告中的各轮 6.12 统计均应按同一 Linux 6.12.81 内核环境理解；不同时间采样或驱动生命周期仍需分开，不能直接比较累计计数。
- **纠错范围：** 第 13、16 节的运行内核版本标签已改为 6.12.81；第 7 节保留 6.12.69 作为源码 Makefile 比较基线，并明确其不是实机版本。

证据来源：`evidence/uart/panther-jp-tvbox-u-boot-boot-20261117.txt`、`docs/reports/2026-11/PANTHER-X2-BOOT-MEDIA-AND-SOFTWARE-INVENTORY-20261117.md`、`config/versions.env`。本次更正不改变任何实机测试数据或故障分析结论。
## 18. 排查方向澄清：TX 仍是主线，RX 统计仅为辅助证据（2026-11-17）

此前第 13 节及总记录中新增 RX/IRQ/NAPI 统计，是为了核实 GMAC 接收侧是否整体失效、解释 RX dropped，并排除将 RX 时钟/DMA 整体故障误当作 DHCP 原因。**这不代表 DHCP 故障排查已从 TX 转向 RX。**

**当前主故障方向仍为 TX：** Panther 本机 outgoing packet capture 能看到 DHCP Discover，而既有 hEX 抓包未观察到 Panther 的 Discover。故障边界仍在本机 outgoing 抓包点之后、hEX 观察点之前。

### 已完成的 TX 证据（不等于 TX 根因已查明）

- MAC_CONFIG 的 TE 位置位；DMA TX channel ST 位置位。
- 已读取 TX descriptor ring base、tail pointer、current descriptor 和 buffer address 等现场寄存器；但寄存器快照只是采样瞬间，不能证明某一个 DHCP Discover 已到达 MAC/PHY。
- 已核对 TX software completion 与 MMC hardware TX frame counters 的语义，并纠正跨启动/驱动生命周期累计值误比较的问题。同一已确认启动周期内，netdev TX packets、驱动 `tx_pkt_n` 与 MMC TX frame count 在可比采样中吻合。
- 已检查现有 TX underflow、carrier error、fatal bus error、TX process-stopped、MTL TX FIFO 堵塞等计数，当前没有观察到对应异常。
- 已完成部分 `stmmac_xmit()`、`stmmac_tx_clean()` 等函数的版本级比较；完整 TX descriptor ownership、DMA mapping、memory barrier、doorbell/channel start、TX IRQ/NAPI completion 的全路径审计尚未完成。

### 明确未完成的 TX 关键问题

1. 没有把某一个 DHCP Discover 与同一时刻的 TX descriptor 提交、DMA completion、MMC frame counter 增量逐项关联。
2. 尚未通过同一时间窗口的 Panther 与 hEX 同步抓包，确认同一个 DHCP Discover 是否到达 hEX 入口；此前两端证据不是同步逐包关联。
3. 尚未证明该帧从 GMAC MAC 经 RGMII TXC/TXD 到达 RTL8211F PHY，并由 PHY 从 MDI 端实际发出；没有 TXC/TXD 物理波形或独立线侧观测。
4. 尚未完成当前实际运行的 6.12.81 发布构建与已审计源码之间的精确 commit/patch/config 对应，也未完成 TX DMA 全路径源码差异审计。

### RX 数据的正确定位

- RX IRQ/NAPI/GMAC 计数大量活动，说明 RX 通路并非整体停摆；RX dropped=1,694 的来源仍未知。
- 这些 RX 结果用于排除“整个 GMAC/RX 子系统完全不工作”的宽泛假设，以及保留独立 RX dropped 线索；**不能用来解释 DHCP Discover 未到达 hEX，也不能据此将主线改为 RX。**

### 下一步优先级（保持 TX 主线）

1. 先完成只读静态审计：对齐当前 6.12.81 实际构建来源，继续核对 `stmmac_xmit()` 到 TX descriptor OWN/doorbell、DMA channel、completion/cleanup 的完整路径及相关配置；不重复已完成的寄存器基础检查。
2. 在不主动触发 DHCP renew、不重启接口的前提下，利用自然出现的 DHCP Discover 做同一报文关联：Panther outgoing 捕获记录源 MAC/时间/报文标识，采集同窗口 TX 计数增量，并与 hEX 入口抓包对应。若无自然 Discover，再先讨论是否授权受控触发。
3. 若 hEX 仍看不到同一报文，再把观测点向下细分到交换机端口/PHY 线侧；RGMII 波形测量属于后续硬件验证，不以软件 counters 代替。
4. RX dropped 另列支线，只有在其增量或具体 RX 报文证据与主故障建立关联时才提升优先级。

**结论：TX 排查尚未完成；没有找到发包失败根因。当前 RX 证据只是辅助排除项，主线仍是 DHCP Discover 从 Linux outgoing 抓包点到 hEX 入口之间的 TX 路径。**