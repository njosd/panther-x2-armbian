# 6.1.116 RTL8211F PHYCR2 Readout — Kernel Build Environment Check

Date: 2026-11-18  
Device: Panther X2  
Running kernel: `6.1.116-ophub`

## Purpose

Determine whether a temporary, read-only kernel helper module can be built against the currently running kernel to read RTL8211F PHYCR2 (Clause 22 page `0x0a43`, register `0x19`) using the kernel's paged PHY access helper.

## Observations supplied by the device

Initial checks reported:

- `gcc` and `cc` available at `/usr/bin/gcc` and `/usr/bin/cc`.
- `ip` available at `/usr/sbin/ip`.
- `make` available at `/usr/bin/make`.
- `modinfo` available at `/usr/sbin/modinfo`.
- `/lib/modules/6.1.116-ophub/build` is a symlink to `/usr/src/linux-headers-6.1.116-ophub`.
- Kernel configuration reports `CONFIG_MODULES=y` and `CONFIG_PHYLIB=y`.

Follow-up checks established:

- `readlink -e /lib/modules/6.1.116-ophub/build` fails and reports `BUILD TARGET MISSING`.
- `/usr/src/linux-headers-6.1.116-ophub` does not exist.
- `/usr/src` contains no available kernel source `Makefile` or `Module.symvers` within the checked depth.
- `/boot/config-6.1.116-ophub` exists.
- `/proc/config.gz` exists.

## Conclusion

The machine has a broken kernel build symlink, not a usable kernel build tree. Kernel configuration files alone are insufficient to build an external module. The planned temporary kernel helper cannot currently be compiled or checked for exported symbols.

## Safety decision

No headers or packages were installed. No symlink, kernel configuration, driver, PHY register, network interface, or service was modified.

Do not fall back to a sequence of separate userspace MII ioctls for page-select/read/page-restore while the PHY state machine may be accessing the same MDIO bus: each ioctl serializes an individual MDIO transaction, not the complete multi-transaction page operation. Bringing `eth0` down is not a viable workaround on this STMMAC path because its ioctl handler rejects MII ioctls when the netdevice is not running.

## Status

- Kernel build prerequisites: **not available**.
- PHYCR2 value: **not read**.
- MDIO trace: **not enabled or changed**.
- PHYCR2 writes / BMCR reset: **not performed**.
- Next safe route: obtain the exact matching 6.1.116 build artifacts for offline inspection/controlled module build, or identify a kernel-provided atomic paged-read interface. Any installation or system change requires separate authorization.
