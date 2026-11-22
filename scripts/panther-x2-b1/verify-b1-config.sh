#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 3 ]]; then
  echo "usage: verify-b1-config.sh <kernel.config> <busybox.config> <busybox-binary> [cross-prefix]" >&2
  exit 2
fi

KERNEL_CONFIG="$1"
BUSYBOX_CONFIG="$2"
BUSYBOX_BIN="$3"
if [[ "$#" -ge 4 ]]; then
  CROSS_PREFIX="$4"
else
  CROSS_PREFIX="aarch64-linux-gnu-"
fi

require_y() {
  local key="$1"
  local file="$2"
  grep -qx "$key=y" "$file" || {
    echo "::error::Required option missing: $key=y in $file"
    exit 1
  }
}

for key in \
  CONFIG_ARM64 CONFIG_ARCH_ROCKCHIP CONFIG_EXPERT CONFIG_OF CONFIG_OF_FLATTREE \
  CONFIG_BLK_DEV_INITRD CONFIG_RD_GZIP CONFIG_DEVTMPFS CONFIG_DEVTMPFS_MOUNT \
  CONFIG_PROC_FS CONFIG_SYSFS CONFIG_PRINTK CONFIG_TTY CONFIG_SMP \
  CONFIG_BINFMT_ELF CONFIG_BINFMT_SCRIPT \
  CONFIG_SERIAL_8250 CONFIG_SERIAL_8250_CONSOLE CONFIG_SERIAL_8250_DW \
  CONFIG_SERIAL_OF_PLATFORM CONFIG_SERIAL_EARLYCON \
  CONFIG_COMMON_CLK_ROCKCHIP CONFIG_CLK_RK3568 CONFIG_PINCTRL_ROCKCHIP; do
  require_y "$key" "$KERNEL_CONFIG"
done

if grep -qx 'CONFIG_BLOCK=y' "$KERNEL_CONFIG"; then
  echo "::error::Generic block layer must be disabled for B1"
  exit 1
fi

# Reject active network, Ethernet, USB, storage and module subsystems.
# MODULES_USE_ELF_RELA and USB_OHCI_LITTLE_ENDIAN are architecture/helper
# symbols, not evidence that module loading or USB host drivers are enabled.
FORBIDDEN_KERNEL='^CONFIG_(NET|NETDEVICES|ETHERNET|PACKET|INET|IPV6|STMMAC_ETH|DWMAC_ROCKCHIP|MDIO_BUS|PHYLIB|REALTEK_PHY|CAN|PPP|TUN|BT|WLAN|WIRELESS|CFG80211|MAC80211|RFKILL|USB|MMC(_[A-Z0-9_]+)?|SCSI|SCSI_MOD|ATA|NVME|MTD|BLOCK|MODULES|USB_EHCI_HCD|USB_OHCI_HCD|USB_XHCI_HCD|USB_DWC2|USB_DWC3|USB_STORAGE|USB_NET|USB_GADGET|USB_PHY)=[ym]$'
if grep -Eq "$FORBIDDEN_KERNEL" "$KERNEL_CONFIG"; then
  echo "::error::Network/USB/storage/module Kconfig residue found:"
  grep -E "$FORBIDDEN_KERNEL" "$KERNEL_CONFIG"
  exit 1
fi

# No persistent filesystem drivers in the RAM-only baseline.
FORBIDDEN_FS='^CONFIG_(EXT4_FS|BTRFS_FS|F2FS_FS|FAT_FS|VFAT_FS|SQUASHFS|EROFS_FS|JFFS2_FS|UBIFS_FS|OVERLAY_FS|NFS_FS|CIFS|FUSE_FS)=[ym]$'
if grep -Eq "$FORBIDDEN_FS" "$KERNEL_CONFIG"; then
  echo "::error::Persistent filesystem support found in B1 kernel config"
  grep -E "$FORBIDDEN_FS" "$KERNEL_CONFIG"
  exit 1
fi

for key in CONFIG_STATIC CONFIG_ASH CONFIG_SH_IS_ASH CONFIG_CAT CONFIG_DMESG CONFIG_MKDIR CONFIG_MOUNT CONFIG_TAIL CONFIG_UNAME; do
  require_y "$key" "$BUSYBOX_CONFIG"
done

readelf -h "$BUSYBOX_BIN" | grep -q 'AArch64'
if readelf -l "$BUSYBOX_BIN" | grep -q 'INTERP'; then
  echo "::error::BusyBox is dynamically linked"
  exit 1
fi

# Execute the ARM64 BusyBox under QEMU; the CI host itself is x86_64.
"$CROSS_PREFIX"gcc --version >/dev/null
qemu-aarch64-static "$BUSYBOX_BIN" --list | sort > busybox-applets.actual

for applet in ash sh cat dmesg mkdir mount tail uname; do
  grep -qx "$applet" busybox-applets.actual || {
    echo "::error::Required BusyBox applet missing: $applet"
    exit 1
  }
done

APPLET_COUNT="$(wc -l < busybox-applets.actual)"
if [[ "$APPLET_COUNT" -gt 16 ]]; then
  echo "::error::BusyBox applet set is unexpectedly large ($APPLET_COUNT)"
  cat busybox-applets.actual
  exit 1
fi

for applet in ip ifconfig route arp arping ping ping6 nc netstat telnet wget \
  ftpget ftpput udhcpc udhcpd nslookup brctl traceroute tc tunctl ipcalc \
  nameif ether-wake ifup ifdown; do
  if grep -qx "$applet" busybox-applets.actual; then
    echo "::error::Forbidden network BusyBox applet present: $applet"
    exit 1
  fi
done

echo "B1 kernel config, static BusyBox architecture and minimal applet checks: PASS"
