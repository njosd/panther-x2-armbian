# eMMC 6.1.116 启动日志：udev eth0 offload 告警历史证据（2026-11-20）

## 目的与范围

本记录仅归档备份整理过程中发现的历史日志线索，供今后对照其他内核版本的启动记录使用。当前不开展 GMAC 故障分析，不据此提出补丁或设备操作。

## 来源身份

- 设备：Panther X2
- 启动介质：eMMC
- 系统/内核：6.1.116（当前 eMMC 系统）
- 日志位置：`/var/log.hdd/`
- 主要来源：`syslog.2.gz`、`syslog.4.gz`、`syslog.1`、`kern.log.1`、`kern.log.3.gz`，以及历史硬件监控日志。
- 事件时间：2026-11-18 启动过程。

## 原始现象

`syslog.2.gz` 在 16:17:06 记录：

```text
systemd-udevd[420]: eth0: Failed to query device driver: Device or resource busy
systemd-udevd[420]: eth0: Could not set offload features, ignoring: Device or resource busy
```

同次启动的 GMAC 日志记录：

- boot-relative 约 4.19 秒：GMAC 初始化参数输出，包括 TX delay 0x30、RX delay 0x10、RGMII、DWMAC4/5、TX checksum insertion supported、TSO supported，以及 DMA host/device width 32/32。
- boot-relative 约 21.32 秒：`configuring for phy/rgmii link mode`。
- boot-relative 约 24.42 秒：`Link is Up - 1Gbps/Full - flow control rx/tx`。

随后 NetworkManager 检测到 carrier，接口完成激活并通过 DHCP 获得 192.168.x.6。

同一事件在 `syslog.4.gz`、`kern.log.3.gz` 等轮转日志中有对应记录；这些是同一启动事件的重复留存，不应误认为多个独立故障样本。

## 证据边界

**已观察到：**
- udev 在启动早期查询 eth0 驱动和设置 offload 时收到 `Device or resource busy`。
- 同一次启动后续完成 GMAC 初始化、PHY 链路协商和网络接口激活。

**尚未确认：**
- 告警是否仅由驱动初始化时序造成。
- udev 放弃本次 offload 设置后，网卡最终实际采用的 feature 状态。
- 该现象是否与其他内核版本的网络行为存在关联。

本记录不将 `TX Checksum insertion supported`、`TSO feature enabled` 或 PHY link-up 解释为实际 TX 帧已从 PHY 物理发出。

## 后续使用

待备份整理完成后，如重新开展版本对照，再从 TF 卡中的 6.12 系统启动日志核对同类 udev/GMAC 启动事件。届时必须分别标注启动介质、内核版本、启动周期和日志来源，不将本记录中的 eMMC 6.1.116 现象替代 6.12 的现场证据。

## 当前状态

- 分类：历史启动日志证据
- 结论：现象已记录，原因未确认
- 当前故障调查状态：不因本记录启动新的调查或设备测试
- 设备操作：无
