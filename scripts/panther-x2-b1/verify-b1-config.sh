#!/usr/bin/env bash
set -euo pipefail

KERNEL_CONFIG="${1:?usage: verify-b1-config.sh <kernel.config> <busybox.config> <busybox-binary>}"
BUSYBOX_CONFIG="${2:?missing BusyBox config}"
BUSYBOX_BIN="${3:?missing BusyBox binary}"
CROSS_PREFIX="${4:-aarch64-linux-gnu-}"

require_y() {
  local key="$1" file="$2"
  grep -qx "${key}=y" "$file" || {
    echo "::error::Required option missing: ${key}=y in $file"
    exit 1
  }
}

for key in \
  CONFIG_ARM64 CONFIG_ARCH_ROCKCHIP CONFIG_EXPERT CONFIG_OF CONFIG_OF_FLATTREE \
  CONFIG_BLK_DEV_INITRD CONFIG_RD_GZIP CONFIG_DEVTMPFS CONFIG_DEVTMPFS_MOUNT \
  CONFIG_PROC_FS CONFIG_SYSFS CONFIG_TMPFS CONFIG_PRINTK CONFIG_SMP \
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

# Any enabled network, wireless, Bluetooth, USB, storage or module Kconfig
# option fails the clean baseline. BLK_DEV_INITRD is intentionally retained.
if grep -Eq '^CONFIG_(NET|NETDEVICES|ETHERNET|PACKET|INET|IPV6|STMMAC_ETH|DWMAC_ROCKCHIP|MDIO_BUS|PHYLIB|REALTEK_PHY|CAN|PPP|TUN|BT|WLAN|WIRELESS|CFG80211|MAC80211|RFKILL|USB|MMC|SCSI|SCSI_MOD|ATA|NVME|MTD|BLOCK|MODULES)=[ym]$' "$KERNEL_CONFIG"; then
  echo "::error::Network/USB/storage/module Kconfig residue found:"
  grep -E '^CONFIG_(NET|PACKET|INET|IPV6|STMMAC_ETH|DWMAC_ROCKCHIP|MDIO_BUS|PHYLIB|REALTEK_PHY|CAN|PPP|TUN|BT|WLAN|WIRELESS|CFG80211|MAC80211|RFKILL|USB|MMC|SCSI|SCSI_MOD|ATA|NVME|MTD|BLOCK|MODULES)=[ym]$' "$KERNEL_CONFIG"
  exit 1
fi

if grep -Eq '^CONFIG_(EXT4_FS|BTRFS_FS|F2FS_FS|FAT_FS|VFAT_FS|SQUASHFS|EROFS_FS|JFFS2_FS|UBIFS_FS|OVERLAY_FS|NFS_FS|CIFS|FUSE_FS)=[ym] CONFIG_ASH CONFIG_SH_IS_ASH CONFIG_CAT CONFIG_DMESG CONFIG_MKDIR CONFIG_MOUNT CONFIG_TAIL CONFIG_UNAME; do
  require_y "$key" "$BUSYBOX_CONFIG"
done

readelf -h "$BUSYBOX_BIN" | grep -q 'AArch64'
if readelf -l "$BUSYBOX_BIN" | grep -q 'INTERP'; then
  echo "::error::BusyBox is dynamically linked"
  exit 1
fi

# Execute the ARM64 BusyBox under QEMU; do not assume the CI host can execute
# an AArch64 binary natively.
"${CROSS_PREFIX}gcc" --version >/dev/null
qemu-aarch64-static "$BUSYBOX_BIN" --list | sort > busybox-applets.actual
for applet in ash sh cat dmesg mkdir mount tail uname; do
  grep -qx "$applet" busybox-applets.actual || {
    echo "::error::Required BusyBox applet missing: $applet"
    exit 1
  }
done
APPLET_COUNT="$(wc -l < busybox-applets.actual)"
test "$APPLET_COUNT" -le 16 || {
  echo "::error::BusyBox applet set is unexpectedly large ($APPLET_COUNT)"
  cat busybox-applets.actual
  exit 1
}

for applet in ip ifconfig route arp arping ping ping6 nc netstat telnet wget ftpget ftpput udhcpc udhcpd nslookup brctl traceroute tc tunctl ipcalc nameif ether-wake ifup ifdown; do
  if grep -qx "$applet" busybox-applets.actual; then
    echo "::error::Forbidden network BusyBox applet present: $applet"
    exit 1
  fi
done

echo "B1 kernel config, static BusyBox architecture and minimal applet allowlist: PASS"
 "$KERNEL_CONFIG"; then
  echo "::error::Persistent filesystem support found in B1 kernel config"
  grep -E '^CONFIG_(EXT4_FS|BTRFS_FS|F2FS_FS|FAT_FS|VFAT_FS|SQUASHFS|EROFS_FS|JFFS2_FS|UBIFS_FS|OVERLAY_FS|NFS_FS|CIFS|FUSE_FS)=[ym] CONFIG_ASH CONFIG_SH_IS_ASH CONFIG_CAT CONFIG_DMESG CONFIG_MKDIR CONFIG_MOUNT CONFIG_TAIL CONFIG_UNAME; do
  require_y "$key" "$BUSYBOX_CONFIG"
done

readelf -h "$BUSYBOX_BIN" | grep -q 'AArch64'
if readelf -l "$BUSYBOX_BIN" | grep -q 'INTERP'; then
  echo "::error::BusyBox is dynamically linked"
  exit 1
fi

# Execute the ARM64 BusyBox under QEMU; do not assume the CI host can execute
# an AArch64 binary natively.
"${CROSS_PREFIX}gcc" --version >/dev/null
qemu-aarch64-static "$BUSYBOX_BIN" --list | sort > busybox-applets.actual
for applet in ash sh cat dmesg mkdir mount tail uname; do
  grep -qx "$applet" busybox-applets.actual || {
    echo "::error::Required BusyBox applet missing: $applet"
    exit 1
  }
done
APPLET_COUNT="$(wc -l < busybox-applets.actual)"
test "$APPLET_COUNT" -le 16 || {
  echo "::error::BusyBox applet set is unexpectedly large ($APPLET_COUNT)"
  cat busybox-applets.actual
  exit 1
}

for applet in ip ifconfig route arp arping ping ping6 nc netstat telnet wget ftpget ftpput udhcpc udhcpd nslookup brctl; do
  if grep -qx "$applet" busybox-applets.actual; then
    echo "::error::Forbidden network BusyBox applet present: $applet"
    exit 1
  fi
done

echo "B1 kernel config, static BusyBox architecture and exact applet allowlist: PASS"
 "$KERNEL_CONFIG"
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

# Execute the ARM64 BusyBox under QEMU; do not assume the CI host can execute
# an AArch64 binary natively.
"${CROSS_PREFIX}gcc" --version >/dev/null
qemu-aarch64-static "$BUSYBOX_BIN" --list | sort > busybox-applets.actual
for applet in ash sh cat dmesg mkdir mount tail uname; do
  grep -qx "$applet" busybox-applets.actual || {
    echo "::error::Required BusyBox applet missing: $applet"
    exit 1
  }
done
APPLET_COUNT="$(wc -l < busybox-applets.actual)"
test "$APPLET_COUNT" -le 16 || {
  echo "::error::BusyBox applet set is unexpectedly large ($APPLET_COUNT)"
  cat busybox-applets.actual
  exit 1
}

for applet in ip ifconfig route arp arping ping ping6 nc netstat telnet wget ftpget ftpput udhcpc udhcpd nslookup brctl; do
  if grep -qx "$applet" busybox-applets.actual; then
    echo "::error::Forbidden network BusyBox applet present: $applet"
    exit 1
  fi
done

echo "B1 kernel config, static BusyBox architecture and exact applet allowlist: PASS"
