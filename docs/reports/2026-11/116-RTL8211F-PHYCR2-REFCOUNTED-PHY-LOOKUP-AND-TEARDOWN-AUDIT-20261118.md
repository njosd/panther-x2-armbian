# RTL8211F PHYCR2 readout: refcounted PHY lookup and teardown audit

Date: 2026-11-18

## Scope

Continue the safety review for a possible temporary read-only module on Panther X2 running `6.1.116-ophub`. This checkpoint focuses on obtaining a refcounted PHY object and understanding device removal.

No module was built or loaded. No PHY register was accessed. No network interface, driver, kernel, boot configuration, or service was changed.

## Exact device identity already established on the target

The target's earlier read-only inventory reported:
- PHY sysfs device: `/sys/devices/platform/fe010000.ethernet/mdio_bus/stmmac-0/stmmac-0:00`
- PHY address: 0
- PHY ID: `0x001cc916`
- `OF_FULLNAME=/ethernet@fe010000/mdio/ethernet-phy@0`
- driver: RTL8211F Gigabit Ethernet

## Source findings

Source baseline: `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`.

### MDIO child topology and naming

In `drivers/net/phy/mdio_device.c`, `mdio_device_create()` sets:
- `mdiodev->dev.parent = &bus->dev`
- `mdiodev->dev.bus = &mdio_bus_type`
- device name via `PHY_ID_FMT`, i.e. bus ID plus two-digit PHY address.

This confirms the PHY is a child device of the MDIO bus and explains the observed name `stmmac-0:00`.

`device_find_child_by_name()` returns a referenced child device and is exported GPL-only. This is safer than obtaining a raw pointer from `mdiobus_get_phy()`, but by itself it does not settle the complete teardown synchronization problem.

### Refcounted PHY lookup API

A better API is present:
- `fwnode_mdio_find_device(fwnode)` searches `mdio_bus_type` by firmware node and returns an MDIO device with its embedded device reference incremented.
- `fwnode_phy_find_device(fwnode)` verifies the MDIO device is a PHY and returns the `phy_device` with that same device reference held.
- `fwnode_phy_find_device()` is exported with `EXPORT_SYMBOL`.
- `device_phy_find_device(dev)` resolves the PHY from a MAC device's firmware-node PHY reference and returns a referenced PHY device; it is exported GPL-only.
- The caller must release the returned PHY device reference with `put_device(&phydev->mdio.dev)`.

The already verified target firmware-node path is `/ethernet@fe010000/mdio/ethernet-phy@0`. A future prototype can investigate resolving that node and using `fwnode_phy_find_device()`, avoiding `mdiobus_get_phy()`'s unreferenced raw pointer.

### MDIO bus lifetime versus hardware lifetime

`mdio_find_bus("stmmac-0")` returns a referenced `mii_bus` object; the caller must release it with `put_device(&bus->dev)`.

However, retaining the bus device reference does not itself prevent `mdiobus_unregister()` or the STMMAC parent driver's remove path from unregistering the bus and tearing down the hardware callback's backing resources. The source shows:
- `mdiobus_unregister()` marks the bus unregistered, removes its MDIO children, and calls `device_del(&bus->dev)`.
- The PHY removal path calls `device_del()`, asserts the PHY reset, and removes the PHY from the bus map.
- A reference to the PHY object prevents its memory from being freed immediately, but does not by itself guarantee that the PHY remains registered or that the STMMAC hardware is still operational.

The bus stores an owner module and a parent device. Pinning a module owner and holding references to devices may help with module-unload lifetime, but it does not automatically prevent a manual device unbind/removal sequence. The exact synchronization protocol for excluding the STMMAC remove path while performing the MDIO read remains unproven.

## Current safety conclusion

- **Verified:** A refcounted PHY lookup API exists; use `fwnode_phy_find_device()` rather than `mdiobus_get_phy()` if a module prototype is pursued.
- **Verified:** The PHY's firmware-node path and PHY ID/address are known from the target's prior read-only inventory.
- **Verified:** A reference to the MDIO bus object and a reference to the PHY object are distinct lifetime protections.
- **Not yet verified:** A complete synchronization method that prevents the STMMAC parent remove/unbind path from tearing down the MDIO hardware while the read is in progress.
- **Not performed:** Module build/load, PHYCR2 read, PHYCR2 write, BMCR reset, link flap, or any system change.

Therefore, do not yet load a module. Continue with a narrowly scoped audit of the STMMAC parent-device lifetime, owner-module handling, and the exact device-lock/removal ordering. If a race-free read cannot be established without relying on an unsafe assumption, stop rather than access the PHY.

## Next checkpoint

Audit the target's STMMAC registration/removal ownership path and identify whether the one-shot read can hold a stable parent-device lifetime across the complete `phy_read_paged()` call. Only then decide whether an isolated external-module build is justified.
