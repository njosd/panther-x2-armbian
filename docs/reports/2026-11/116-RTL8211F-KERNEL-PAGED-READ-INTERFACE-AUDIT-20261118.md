# Panther X2 6.1.116 RTL8211F — Kernel-Mediated Paged Read Interface Audit

Date: 2026-11-18  
Runtime target: Panther X2, `6.1.116-ophub`  
Source baseline inspected: `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`

## Question

Can the live RTL8211F PHYCR2 register (page `0x0a43`, register `0x19`) be read atomically with respect to other MDIO users, without installing userspace tools or changing PHY state?

## Findings

### 1. Kernel paged-read helper is present and exported — source verified

In `drivers/net/phy/phy-core.c`, `phy_read_paged()` is implemented as:

- call `phy_select_page()`;
- if page selection succeeded, read the register using `__phy_read()`;
- call `phy_restore_page()` to restore the old page and release the MDIO bus lock.

The implementation is exported with `EXPORT_SYMBOL(phy_read_paged)` (not GPL-only). The page-selection and restore helpers themselves are GPL-only exports, but a module that calls the public `phy_read_paged()` helper does not need to call those helpers directly.

This is the correct kernel-side operation for the requested paged read. It holds the MDIO bus lock across the complete save/select/read/restore sequence.

### 2. The exact RTL8211F driver already uses this helper — source verified

In the same source baseline, `drivers/net/phy/realtek.c`:

- `rtl821x_read_page()` reads the page selector using `__phy_read()`.
- `rtl821x_write_page()` writes the page selector using `__phy_write()`.
- `rtl821x_probe()` reads page `0xa43` / PHYCR2 using `phy_read_paged(phydev, 0xa43, RTL8211F_PHYCR2)`.
- It caches only `RTL8211F_CLKOUT_EN` in `priv->phycr2`; it does not expose the complete register value as a userspace attribute.

This proves the in-tree PHY driver has a working kernel-mediated paged-read path for this exact register, but the cached private value is not a supported interface for retrieving the live full register.

### 3. MDIO device lookup primitives exist — source verified, module use not yet validated

In `drivers/net/phy/mdio_bus.c`:

- `mdio_bus_type` is exported.
- `mdiobus_get_phy(bus, addr)` is exported and returns the PHY object mapped at the specified address.

The runtime sysfs identity previously confirmed is PHY device `stmmac-0:00`, address 0, PHY ID `0x001cc916`. A temporary module could in principle locate the MDIO device by its bus/device identity, obtain a stable device reference, and call `phy_read_paged()`.

However, the exact safe object-lookup/lifetime implementation and every required symbol's availability in the built running kernel have not yet been verified. Do not treat this as ready-to-build module code.

### 4. No existing userspace atomic paged-read interface found

The audited standard MII ioctl path exposes individual Clause 22 register operations. A sequence of page-select, data-read, and page-restore ioctls does not retain the MDIO bus lock across the complete sequence.

The existing `mii-tool -vv` output reads the currently selected standard register page; its register 25 output is not the requested page `0xa43` register `0x19`.

The already checked PHY sysfs and debugfs locations expose no arbitrary paged-register read interface. The Realtek driver's cached PHYCR2 field is private and only retains bit 0, not the full register.

No supported `ethtool` or standard sysfs path has been established that returns this arbitrary paged register atomically.

## Feasibility and blocker

A small temporary kernel module remains the technically appropriate route:

1. Locate the already registered PHY device `stmmac-0:00` and safely hold a device reference.
2. Verify it is PHY address 0 with PHY ID `0x001cc916`.
3. Call only `phy_read_paged(phydev, 0x0a43, 0x19)`.
4. Log the returned value or negative errno.
5. Release references and unload the module.

No PHY write, BMCR reset, link flap, or persistent configuration change is required.

But the target's external-module build environment is absent: `/lib/modules/6.1.116-ophub/build` is a broken symlink, and the target headers/Makefile/Module.symvers do not exist. Therefore the module cannot currently be built or checked against the running kernel. Do not install packages or alter the target just to proceed.

## Current classification

- **Source verified:** `phy_read_paged()` is exported and performs locked page save/select/read/restore.
- **Source verified:** the exact RTL8211F driver uses that helper to read PHYCR2 during probe.
- **Source verified:** `mdio_bus_type` and `mdiobus_get_phy()` are exported in the inspected source.
- **Runtime verified:** PHY device name `stmmac-0:00`, address 0, ID `0x001cc916`, and driver identity.
- **Not verified:** exact running-kernel Module.symvers exports/CRCs, safe module-side object lookup and lifetime handling, and successful execution of a read-only module.
- **Not available:** a confirmed existing userspace atomic paged-read interface.
- **Not performed:** page selection, PHYCR2 read, PHYCR2 write, BMCR reset, MDIO trace enable, interface down/up, package installation, or reboot.

## Next step

Continue offline source/API review of the device-reference lookup and module symbol requirements. In parallel, search for the exact matching 6.1.116 build artifacts on the build/source side rather than changing the Panther X2 runtime. Only after the module can be built against the exact running kernel should a one-shot read-only test be considered.
