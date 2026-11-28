# Panther X2 Project-A — G4-P2 Full-Supply IO-domain Runtime Result

Date: 2026-11-28  
Status: **RUNTIME PASS-CONDITIONAL**  
Scope: one authorized SU08G RAM-only boot session; full nine-supply IO-domain consumer enabled; GMAC/MDIO/PHY remain disabled.

## 1. Executive result

The G4-P2 PREPARE-ONLY image booted successfully on Panther X2 using the authorized SU08G TF card and entered the RAM initramfs shell. Linux 6.18.63 identified the machine as Panther X2 and brought up all four CPUs.

Most importantly, the Linux platform device `fdc20000.syscon:io-domains` was created and its `driver` symlink pointed to `rockchip-iodomain`. This proves that the full-supply IO-domain consumer completed probe sufficiently to bind to the driver. The RK809 regulator provider also bound to `rk808-regulator`; all nine supply properties were present in the runtime DT node; the expected regulator class objects were registered and software-reported regulator states were collected.

**G4-P2 full-supply IO-domain probe/binding = PASS. Overall G4-P2 runtime = PASS-CONDITIONAL**, because the driver source's selector write return path is not fully checked, and no PMUGRF VSEL readback, bus transaction trace, or physical rail measurement was performed. Do not promote this to physical-voltage or selector-register verification.

## 2. Evidence provenance

User-provided serial/runtime capture:

- Filename: `粘贴的 Markdown (1)(20261128-113433).md`
- Length: 2,065 lines; 55,979 bytes
- SHA256: `8cfba60483e94eb4fb27d1b06e6432f13c6d7a790c81cedc5cb5e51e69ca2272`
- Captured output includes U-Boot loading the G4-P2 Image, uInitrd and Panther X2 DTB from `mmc 1:1`, Linux boot, the initial RAM collector, and the second collector after the requested settling interval.
- This report summarizes the supplied evidence; the full raw serial log is not duplicated in the repository.

Frozen build inputs and package are documented in `PANTHER-X2-G4-P2-FULL-SUPPLY-PREPARE-ONLY-IMPLEMENTATION-PLAN-20261128.md` (Actions run `46139238851`, artifact `15260906859`).

## 3. Boot identity and RAM-only boundary

Observed:

- U-Boot script selected experiment TF device `mmc 1`.
- Kernel Image loaded at `0x00280000`.
- uInitrd loaded at `0x0a200000`.
- Panther X2 DTB loaded at `0x0a100000`.
- Linux: `6.18.63+`, build timestamp `Sat Nov 28 01:25:39 UTC 2026`.
- `Machine model: Panther X2`.
- 4 GiB RAM detected; four CPUs started.
- `psci_checker: Hotplug tests passed OK`.
- `Run /init as init process`; G4-P2 RAM runtime shell became ready.

The initramfs collector mounts only procfs, sysfs and debugfs as needed. It performs no persistent filesystem mount and no storage write. The candidate DTB keeps eMMC SDHCI, TF SDMMC0 and SDIO disabled. The collector itself performs no sysfs stores, I2C writes, raw MMIO access, PMUGRF/PMIC register access or selector read/write.

## 4. IO-domain and regulator runtime evidence

### 4.1 DT node

Runtime collector reported:

- `/proc/device-tree/syscon@fdc20000/io-domains`: PRESENT.
- `status` property: PRESENT (the expected value `okay`; the frozen offline DTB audit established the actual string value).
- All nine properties present:
  - `pmuio1-supply`
  - `pmuio2-supply`
  - `vccio1-supply` through `vccio7-supply`

The frozen PREPARE-ONLY DTB audit already established that the nine phandles match the G3 baseline exactly and that the only logical DTB difference is this IO-domain node's `status: disabled → okay`.

### 4.2 Platform driver binding

Observed sysfs links:

```
/sys/bus/platform/devices/fdc20000.syscon:io-domains/driver
  -> ../../../../bus/platform/drivers/rockchip-iodomain

/sys/bus/platform/devices/rk808-regulator.3.auto/driver
  -> ../../../../bus/platform/drivers/rk808-regulator
```

Both the IO-domain consumer and RK809 regulator provider are bound. The IO-domain device is absent from the deferred-probe list.

### 4.3 Software-reported regulator state

The collector recorded the following relevant regulator objects:

| Regulator | State | Reported voltage | num_users |
|---|---|---:|---:|
| `vcc3v3_pmu` | enabled | 3,300,000 µV | 1 |
| `vcc_3v3` | enabled | no `microvolts` sysfs attribute | 0 |
| `vcc_1v8` | enabled | 1,800,000 µV | 1 |
| `vccio_sd` | enabled | 3,300,000 µV | 1 |
| `vcc3v3_sys` | provider registered | 3,300,000 µV | 15 |

Other PMIC regulator class entries were also present. `vcc_3v3` having no exported `microvolts` sysfs attribute is not, by itself, a failed lookup: the RK809 SWITCH_REG1 descriptor has an upstream `vcc9-supply` path to the fixed 3.3V `vcc3v3_sys` regulator, and the regulator core can resolve voltage through the upstream supply. The decisive runtime evidence is successful IO-domain driver binding with all nine supply properties retained.

These are Linux regulator-core software values and enable/use counts. They are not direct measurements of physical rails.

## 5. Deferred probe and relevant log review

After the settling interval, the deferred-probe capture listed:

- `fd840000.usb` — deferred probe, reason unknown.
- Rockchip power-domain `sync_state()` pending due to video codec devices.

The IO-domain device was not listed as deferred. No IO-domain-specific probe failure or regulator lookup error appears in the supplied capture.

Other observed warnings/errors are outside this gate:
- U-Boot's earlier automatic FIT/DTB scan reported missing FIT/DTB before the custom boot script explicitly loaded the candidate Image/initramfs/DTB; Linux subsequently booted and identified Panther X2.
- BL31 reported no OP-TEE runtime service.
- Linux DRM reported no available VOP.
- USB PHY runtime-PM usage underflow and an SCMI malformed reply were reported.
These are recorded as unrelated observations; they do not change the G4-P2 IO-domain binding result and must not trigger scope expansion in this gate.

## 6. What this runtime PASS proves — and does not prove

### Proven (PASS)

1. The G4-P2 full-supply DTB booted on the actual Panther X2 hardware.
2. The full-supply IO-domain platform device was enumerated.
3. `rockchip-iodomain` bound to that device; probe did not defer or fail.
4. The RK809 regulator provider bound successfully.
5. All nine IO-domain supply properties were visible at runtime.
6. Relevant regulator class entries and software-reported states were available.
7. The test remained in RAM initramfs and did not intentionally mount/write persistent storage.
8. GMAC1/MDIO/RTL8211F were not activated; no netdev was opened and no TX test was run.

### Not verified

1. Successful PMUGRF selector register transaction at the bus/register level. The driver path is expected to issue selector writes during successful probe, but the relevant write return values are not fully checked.
2. PMUGRF VSEL selector readback.
3. Physical IO-domain rail voltages at board test points.
4. Long-duration stability or behavior under suspend/resume.
5. Any Ethernet/GMAC functionality.

Do not perform raw PMIC/PMUGRF register access to close these gaps in this stage. Any future electrical measurement requires a separate, carefully scoped plan.

## 7. Gate decision and next stage

**G4-P2 full-supply runtime = PASS-CONDITIONAL.** The specific blocker that prevented advancing from G4-P0 (full nine-supply mapping not yet runtime-proven) is now resolved at the Linux probe/binding level.

Next task: **R7-prep build-only**, not hardware activation. Build and audit the STMMAC + Rockchip DWMAC software dependency closure while GMAC1, MDIO and PHY DT nodes remain disabled. Keep the one-variable hardware rule: R7-A/G5-A later changes only GMAC1 parent DT status after R7-prep assets are frozen. GMAC remains the last hardware component to be activated.

R7-A/G5-A, R7-B/G5-B, R7-C/G6-A and R7-D/G6-B/G7 remain NOT RUN and NOT AUTHORIZED.

## 8. Safety and media scope

The user's explicit authorization covered one G4-P2 RAM-only boot session using SU08G and read-only dmesg/sysfs/deferred-probe collection. The supplied log is consistent with that scope.

- SU08G: used for the authorized boot.
- SN64G: untouched.
- eMMC: untouched.
- Persistent filesystem: not mounted by the initramfs collector.
- Raw PMIC/PMUGRF: not accessed by the collector.
- GMAC/MDIO/PHY: remained disabled.
- Netdev open / TX: not performed.
