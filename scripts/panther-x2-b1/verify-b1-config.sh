#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -lt 4 ]]; then echo "usage: verify-b1-config.sh <kernel.config> <busybox.config> <busybox-binary> <modules-root> [cross-prefix]" >&2; exit 2; fi
KERNEL_CONFIG="$1"; BUSYBOX_CONFIG="$2"; BUSYBOX_BIN="$3"; MODULES_ROOT="$4"; CROSS_PREFIX="${5:-aarch64-linux-gnu-}"
require_y(){ grep -qx "$1=y" "$2" || { echo "::error::Required option missing: $1=y in $2"; exit 1; }; }
require_value(){ grep -qx "$1=$2" "$3" || { echo "::error::Required option missing: $1=$2 in $3"; exit 1; }; }
require_unset(){ if grep -Eq "^$1=[ym]$" "$2"; then echo "::error::Forbidden option is enabled: $1"; grep -E "^$1=" "$2"; exit 1; fi; }
for key in CONFIG_ARM64 CONFIG_ARM64_4K_PAGES CONFIG_ARM64_VA_BITS_48 CONFIG_ARM64_PA_BITS_48 CONFIG_ARCH_ROCKCHIP CONFIG_ROCKCHIP_ERRATUM_3568002 CONFIG_OF CONFIG_OF_FLATTREE CONFIG_BLK_DEV_INITRD CONFIG_RD_GZIP CONFIG_DEVTMPFS CONFIG_DEVTMPFS_MOUNT CONFIG_PROC_FS CONFIG_SYSFS CONFIG_PRINTK CONFIG_TTY CONFIG_SMP CONFIG_SERIAL_8250 CONFIG_SERIAL_8250_CONSOLE CONFIG_SERIAL_8250_DW CONFIG_SERIAL_OF_PLATFORM CONFIG_SERIAL_EARLYCON CONFIG_COMMON_CLK_ROCKCHIP CONFIG_CLK_RK3568 CONFIG_PINCTRL_ROCKCHIP; do require_y "$key" "$KERNEL_CONFIG"; done
require_unset CONFIG_ARM64_LPA2 "$KERNEL_CONFIG"
require_unset CONFIG_KEYBOARD_GPIO_BUTTON_HOTPLUG "$KERNEL_CONFIG"
for key in CONFIG_MODULES CONFIG_BLOCK CONFIG_MMC CONFIG_MMC_BLOCK CONFIG_MMC_SDHCI_OF_DWCMSHC CONFIG_MMC_DW_ROCKCHIP CONFIG_USB CONFIG_USB_XHCI_HCD CONFIG_USB_XHCI_PLATFORM CONFIG_USB_EHCI_HCD CONFIG_USB_OHCI_HCD CONFIG_USB_DWC3 CONFIG_USB_DWC2 CONFIG_USB_PHY CONFIG_USB_STORAGE CONFIG_SCSI CONFIG_ATA CONFIG_NVME_CORE CONFIG_MTD CONFIG_MTD_BLOCK CONFIG_MTD_OF_PARTS CONFIG_EXT4_FS CONFIG_FAT_FS CONFIG_VFAT_FS; do require_y "$key" "$KERNEL_CONFIG"; done
FORBIDDEN='^CONFIG_(NET($|_)|NETDEVICES|ETHERNET|PACKET|INET|IPV6|NETFILTER.*|NETLABEL|NETWORK_SECMARK|NETWORK_PHY_TIMESTAMPING|STMMAC.*|DWMAC.*|MDIO_BUS|PHYLIB|REALTEK_PHY|CAN.*|PPP.*|TUN|BT($|_).*|WLAN.*|WIRELESS.*|CFG80211.*|MAC80211.*|RFKILL.*|USB_NET.*|USB_U_ETHER|USB_ETH|USB_FUNCTIONFS_ETH|USB_CONFIGFS_ECM|USB_CONFIGFS_RNDIS|USB_CONFIGFS_NCM|USB_CONFIGFS_EEM|USB_CONFIGFS_SUBSET)=[ym]$'
if grep -Eq "$FORBIDDEN" "$KERNEL_CONFIG"; then echo "::error::Network-related Kconfig residue found:"; grep -E "$FORBIDDEN" "$KERNEL_CONFIG"; exit 1; fi
MODULE_DIR="$(find "$MODULES_ROOT/lib/modules" -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null || true)"
test -n "$MODULE_DIR" || { echo "::error::No installed module release"; exit 1; }
find "$MODULE_DIR" -type f -name '*.ko*' -print -quit | grep -q . || { echo "::error::No kernel modules installed"; exit 1; }
if find "$MODULE_DIR" -type f -name '*.ko*' \( -path '*/kernel/net/*' -o -path '*/kernel/drivers/net/*' -o -path '*/kernel/drivers/bluetooth/*' \) -print -quit | grep -q .; then echo "::error::Network/Ethernet/Bluetooth module found"; exit 1; fi
for key in CONFIG_STATIC CONFIG_BUSYBOX CONFIG_ASH CONFIG_SH_IS_ASH CONFIG_CAT CONFIG_DMESG CONFIG_MKDIR CONFIG_MOUNT CONFIG_TAIL CONFIG_UNAME; do require_y "$key" "$BUSYBOX_CONFIG"; done
readelf -h "$BUSYBOX_BIN" | grep -q 'AArch64'
if readelf -l "$BUSYBOX_BIN" | grep -q 'INTERP'; then echo "::error::BusyBox is dynamically linked"; exit 1; fi
"$CROSS_PREFIX"gcc --version >/dev/null; qemu-aarch64-static "$BUSYBOX_BIN" --list | sort > busybox-applets.actual
for applet in ash sh cat dmesg mkdir mount tail uname; do grep -qx "$applet" busybox-applets.actual || { echo "::error::Missing BusyBox applet: $applet"; exit 1; }; done
APPLET_COUNT="$(wc -l < busybox-applets.actual)"
if [[ "$APPLET_COUNT" -gt 16 ]]; then echo "::error::BusyBox applet set too large ($APPLET_COUNT)"; cat busybox-applets.actual; exit 1; fi
for applet in ip ifconfig route arp arping ping ping6 nc netstat telnet wget ftpget ftpput udhcpc udhcpd nslookup brctl traceroute tc tunctl ipcalc nameif ether-wake ifup ifdown; do if grep -qx "$applet" busybox-applets.actual; then echo "::error::Forbidden network applet: $applet"; exit 1; fi; done
echo "B1 full-base, network-isolation, modules and BusyBox checks: PASS"
