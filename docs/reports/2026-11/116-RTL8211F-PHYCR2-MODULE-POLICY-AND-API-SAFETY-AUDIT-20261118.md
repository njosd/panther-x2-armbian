# RTL8211F PHYCR2 readout: module policy and API safety audit

Date: 2026-11-18

## Scope

Continue the read-only investigation of the RTL8211F PHYCR2 register on the Panther X2 running `6.1.116-ophub`. This checkpoint evaluates whether a temporary read-only kernel module is technically possible and audits the kernel APIs needed to locate the PHY and perform an atomic paged read.

No module was built or loaded. No PHY register was read or written in this checkpoint. No network interface, driver, kernel, boot configuration, or service was changed.

## Runtime configuration reported by the device

Kernel release:
- `6.1.116-ophub`

Relevant `/proc/config.gz` results:
- `CONFIG_MODULES=y`
- `CONFIG_PHYLIB=y`
- `CONFIG_KALLSYMS=y`
- `# CONFIG_MODVERSIONS is not set`
- `# CONFIG_MODULE_SIG is not set`

Runtime policy:
- `/proc/sys/kernel/modules_disabled=0`
- `/proc/sys/kernel/module_sig_enforce` is unavailable (consistent with module signature support being disabled in this configuration).

System.map contains:
- `phy_read_paged` at `ffffffc009c2d220 T`
- `mdiobus_get_phy` at `ffffffc009c31d64 T`

Interpretation:
- Module loading is not globally disabled.
- Symbol version CRC checking is not enabled by the reported kernel config.
- Kernel module signature enforcement is not enabled by the reported kernel config.
- The System.map entries prove that these symbols exist in the running kernel image, but do not by themselves prove that they are exported to modules.

## Source audit

Source baseline: `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`.

Verified in this source:
- `phy_read_paged()` is exported with `EXPORT_SYMBOL(phy_read_paged)`, not GPL-only.
- `mdio_find_bus()` is exported with `EXPORT_SYMBOL(mdio_find_bus)`. Its documented contract says it returns a referenced `mii_bus` device; the caller must release that reference with `put_device(&bus->dev)`.
- `mdiobus_get_phy()` is exported with `EXPORT_SYMBOL(mdiobus_get_phy)`.
- `phy_read_paged()` uses `phy_select_page()`, performs the register read, then calls `phy_restore_page()`. The select/restore helpers hold and release the MDIO bus lock around the paged transaction.
- The MDIO bus in this source has an `mdio_lock` mutex.
- `mdiobus_get_phy()` simply looks up `bus->mdio_map[addr]` and returns the embedded `phy_device` pointer. It does not acquire a reference to the PHY device and does not itself lock the bus.
- PHY removal clears the bus map entry and removes the PHY device; the lifetime of the returned raw pointer therefore cannot be assumed from `mdiobus_get_phy()` alone.

## Safety assessment

The API path for a paged read exists and is exported. `mdio_find_bus()` is preferable to guessing or manually traversing the device tree because it provides a referenced MDIO bus object.

However, the PHY object lifetime is not yet sufficiently proven for a robust module implementation. A bus reference protects the bus device object, but `mdiobus_get_phy()` returns a raw PHY pointer. A correct implementation must safely pin the PHY device and account for possible bus/PHY removal while avoiding a race between lookup and reference acquisition. The current audit has not yet established a complete synchronization/lifetime protocol for this specific STMMAC bus.

Consequently, do not yet build or load a module. Do not use separate userspace MII ioctls for page-select/read/page-restore, because the sequence would not be protected by one MDIO bus lock.

## Next work

1. Complete the lifetime/synchronization audit for `mdio_find_bus()`, `mdiobus_get_phy()`, PHY device removal, and STMMAC bus teardown.
2. Confirm all required symbols are exported in the exact source baseline, including the device reference helpers needed by the eventual module.
3. Only after that, assess an out-of-tree build using the exact source/configuration in an independent Linux build environment. The Panther X2 runtime remains untouched.
4. If a safe implementation cannot be established, stop rather than risk a stale PHY pointer or MDIO access during teardown.

## Status

- Runtime module policy: **verified from device output**.
- Export status of `phy_read_paged()`, `mdio_find_bus()`, and `mdiobus_get_phy()`: **verified in the cited source baseline**.
- Safe PHY object lifetime for an external read-only module: **not yet verified**.
- Actual PHYCR2 value: **not yet read**.
- PHYCR2 write, BMCR reset, link flap, module build/load: **not performed**.
