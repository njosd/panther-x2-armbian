# Panther X2 6.1.116 RTL8211F MDIO Read-Path and Tracepoint Audit — 2026-11-18

## Scope

Continue the read-only 6.1.116 Panther X2 investigation of the historical STMMAC JL2xx1 workaround and its four Clause 22 writes. The target register is RTL8211F PHYCR2 at page 0x0a43, register 0x19. No package installation, PHY register write, page switch, link flap, reboot, or system configuration change was performed.

## Runtime identity — verified on Panther X2

User-provided command output confirms:

- Kernel: `6.1.116-ophub`, build timestamp `Sun Nov 10 08:21:17 EST 2024`.
- PHY device: `/sys/devices/platform/fe010000.ethernet/mdio_bus/stmmac-0/stmmac-0:00`.
- PHY address: 0.
- PHY ID: `0x001cc916`.
- Bound driver: `RTL8211F Gigabit Ethernet`.
- Current link: 1000 Mb/s, full duplex, autonegotiation on.
- `mii-tool` and `ethtool` are present; `phytool` and standalone `mdio` command are absent.

## Standard MII read and current EEE state — verified

`mii-tool -vv eth0` returned the standard Clause 22 register block for PHY address 0. Its displayed register 25 value is `0x1801`, but this is the currently selected standard page's register 25; it is **not** evidence for page 2627/register 25 from the historical workaround, nor for page 0x0a43/register 0x19.

`ethtool --show-eee eth0` reports `EEE status: enabled - active`, with 100baseT/Full and 1000baseT/Full supported and advertised. This agrees with the previously recorded 116 EEE status. It is useful contextual evidence, but it does not directly read PHYCR2 bit 5 and cannot prove whether the historical full-register write succeeded or whether a later reset restored a bit.

## Sysfs and debugfs availability — verified

The MDIO device sysfs directory exposes identity, interface, fixup and statistics attributes, but no paged-register read attribute. The searched debugfs paths exposed no MDIO/PHY register access node. Debugfs and tracefs are mounted.

MDIO counters at collection time:

| Counter | Value |
|---|---:|
| transfers | 1227 |
| reads | 812 |
| writes | 415 |
| errors | 0 |

These are lifetime/current-boot cumulative counters and cannot isolate the four historical workaround writes.

## MDIO tracepoint — verified

The running kernel exposes `/sys/kernel/tracing/events/mdio/mdio_access`. Its format reports:

- `busid`
- `read` (read/write direction)
- `addr` (PHY address)
- `regnum` (register number)
- `val` (transaction value)

The event's `enable` file was `0`; it was not enabled or changed. The filter file reports `none`.

Inspection of Linux v6.1 reference source confirms `__mdiobus_read()` and `__mdiobus_write()` emit this tracepoint after the bus callback. The trace event has condition `err >= 0`; therefore failed MDIO transactions are not emitted as `mdio_access` records. Successful bus-controller completion is recorded, but it does not prove that the PHY internally accepted or retained a register value.

## Paged-register access and concurrency — source-level finding

Linux v6.1 PHY core provides `phy_read_paged()`. Its helper sequence is:

1. Save the current page.
2. Select the requested page if different.
3. Read the requested register.
4. Restore the previous page.
5. Hold the MDIO bus lock across the page-save/select/read/restore sequence.

This is the correct kernel-side pattern for avoiding interleaving MDIO transactions while a page is temporarily selected.

A userspace sequence made from separate MII ioctl operations (e.g. write page selector, read register, restore page) does not automatically hold the kernel MDIO bus lock across all operations. Kernel PHY state-machine accesses could interleave. The available `mii-tool` interface shown here reads standard MII registers and does not provide a confirmed safe paged-read operation. Therefore it is not appropriate to improvise a raw page-switch/read/restore sequence on this live interface.

## Conclusions

1. The exact 6.1.116 runtime target (PHY address 0, RTL8211F, ID 0x001cc916) is confirmed.
2. The running kernel has a useful MDIO tracepoint with the fields needed to observe successful page-selector and data-register transactions.
3. The tracepoint is observational only; it does not provide a paged-read API and excludes failed transactions.
4. Standard `mii-tool -vv` register 25 output must not be confused with the historical page-2627/register-25 workaround write.
5. Current EEE-active status is consistent with the historical baseline but is not a substitute for PHYCR2 readback.
6. No safe, already-present userspace interface for an atomic paged read has been identified. Do not use independent raw userspace page-selector writes on the active PHY without a separately designed and explicitly approved method that preserves MDIO bus locking.

## Test classification

- **Verified:** runtime kernel/PHY identity, PHY address, driver, link, EEE state, available tools, sysfs/debugfs absence of a paged-read interface, tracepoint format and disabled state, MDIO counters.
- **Source-verified against Linux v6.1 reference:** MDIO tracepoint records successful bus transactions; paged PHY helper locks the MDIO bus over save/select/read/restore.
- **Not verified:** current RTL8211F PHYCR2 value; whether the historical 116 workaround write reached and was accepted by the PHY; whether a later BMCR reset changed PHYCR2; exact vendor 6.1.116 implementation equivalence for every helper detail.
- **Not performed:** enabling tracing, changing page selector, reading page 0x0a43/register 0x19, writing PHY configuration, resetting PHY, bringing interface down/up, installing tools, rebooting.

## Next safe direction

Continue source-level inspection of the exact 6.1.116 vendor kernel's MDIO/PHY helper and ioctl paths, or identify a kernel-mediated read path that retains the MDIO bus lock. Do not ask the user to install tools or execute raw paged-register operations until the access method and side effects are established.
