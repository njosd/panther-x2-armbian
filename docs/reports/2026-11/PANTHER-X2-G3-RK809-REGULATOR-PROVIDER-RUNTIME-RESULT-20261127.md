# Panther X2 Project A — G3 RK809 Regulator Provider Runtime Result

- Date: 2026-11-27
- Gate: G3-P (runtime)
- Target: Panther X2 / RK3566, SU08G TF, Linux 6.18.63, RAM-only initramfs
- Status: **G3-S PASS; G3-B BUILD PASS; G3-P RUNTIME PASS (provider binding and regulator object registration)**
- Scope: RK809 regulator provider only. This report does not claim physical rail voltage validation or IO-domain consumer validation.

## 1. Fixed inputs and preparation

G3 static audit (G3-S) completed against pinned Linux 6.18.63 sources and Panther X2 DTS. G3 build-only (G3-B) passed Actions run `45984035650`, artifact `15192123549`.

The isolated runtime package was built by PR validation run `45991658437`, artifact `15193991660`. The package was independently checked: artifact SHA256 manifest, Zstandard integrity, declared raw image size, GPT, ext4 `e2fsck -fn`, read-only filesystem contents, and U-Boot proper readback all passed. The package was PREPARE-ONLY until the user performed the authorized SU08G startup.

Runtime inputs:
- Kernel Image SHA256: `d1830f649e3bfa789fec3589c2ef16b1e46465846c6bb150e666f8df4c610a61`
- G3 DTB SHA256: `9364c6d7aadddb8520388418e8db570e0b4020a38c5ceb8acbd2343165bb5209`
- uInitrd SHA256: `332c09d5acae64fff0261849e1fb9c229f52f278acda76cb0a6ed8e9dde353e9`
- gzip initramfs SHA256: `3adeefd44fccec3eac79135642a5c6f37e17d8265e1d81e036d1c33faba35963`
- boot.scr SHA256: `4a8526de9d430f92af32b01798fe122758e927d098172f656d33a3b523635c5c`
- SU08G raw image SHA256: `c62c28e4ced0f7a3e9aa8c409ce89e53247a7dbcddf7fe4c41f7131d6fdf32c5`
- compressed image SHA256: `4b3c9198c09bf6f6dc5d9e1f99dd36010ed03593fc8999475c597ac3aa5b6e46`

Boot arguments included `regulator_ignore_unused`. This suppresses late unused-regulator cleanup; it does not suppress provider probe or its initialization writes.

## 2. Runtime evidence

The user booted the prepared image on SU08G. Captured runtime data reports:
- Kernel: Linux `6.18.63+`, ARM64, Panther X2 model, 4 GiB RAM.
- Root filesystem: initramfs/RAM. Mount table contained rootfs, proc and sysfs; no TF/eMMC persistent filesystem was mounted.
- RK809 I2C parent device `0-0020` was bound to `rk8xx-i2c`.
- Platform child `rk808-regulator.3.auto` existed below the RK809 device.
- The platform device exposed the explicit driver symlink:
  `driver -> ../../../../../../bus/platform/drivers/rk808-regulator`
  This is direct evidence that the RK809 regulator child platform device bound to the `rk808-regulator` platform driver.
- The provider's `regulator/` directory contained 16 regulator class symlinks, `regulator.5` through `regulator.20`, each resolving beneath `rk808-regulator.3.auto/regulator/`. This confirms registration of 16 regulator objects by this provider.
- The user enumerated all system regulator class names. Names for the provider-owned global IDs were:
  - regulator.5: `vdd_logic`
  - regulator.6: `vdd_gpu`
  - regulator.7: `vcc_ddr`
  - regulator.8: `vdd_npu`
  - regulator.9: `vcc_1v8`
  - regulator.10: `vdda0v9_image`
  - regulator.11: `vdda_0v9`
  - regulator.12: `vdda0v9_pmu`
  - regulator.13: `vccio_acodec`
  - regulator.14: `vccio_sd`
  - regulator.15: `vcc3v3_pmu`
  - regulator.16: `vcca_1v8`
  - regulator.17: `vcca1v8_pmu`
  - regulator.18: `vcca1v8_image`
  - regulator.19: `vcc_3v3`
  - regulator.20: `SWITCH_REG2`

Regulator class IDs are global kernel IDs, not RK809 channel numbers. This runtime listing is not sufficient by itself to map every global ID/name to an individual DCDC/LDO/SWITCH descriptor. In particular, no channel mapping is asserted here from numeric regulator IDs. The separately listed `regulator.4` name `vdd_cpu` was not among the 16 provider-owned links and is not attributed to this RK809 provider by this report.

## 3. Capture limitations and invalid observations

The capture script emitted repeated `[ : not found` errors because the minimal BusyBox image did not provide the expected `[` command/builtin. Therefore:
- The script's DTB/controller-isolation status lines are invalid and are not runtime proof of isolation.
- Its `devices_deferred` availability/status result is not evidence that the deferred list was empty.
- Its regulator-summary result is unavailable because debugfs regulator summary was not mounted/exposed in this runtime session.
- The script errors do not invalidate the separately captured sysfs driver symlink and provider-owned regulator symlink/name observations.

Isolation is supported by the G3-B build artifact checks, not by the failed runtime shell predicates. The kernel log contained the expected `regulator: Not disabling unused regulators` message due to `regulator_ignore_unused`, and no explicit RK809 regulator probe failure was observed. Absence of a probe error is supporting context, not the primary PASS criterion.

## 4. Scope and evidence boundaries

### PASS
- G3-S static audit.
- G3-B build/link and isolated-DTB checks.
- G3 runtime package structural/integrity audit.
- RK809 I2C parent driver binding.
- RK809 regulator platform child binding to `rk808-regulator`.
- Registration of 16 regulator objects beneath that provider.

### Not tested / not claimed
- Physical voltage or current measurement on any PMIC output.
- Electrical enable state or actual voltage of each rail.
- Per-channel DCDC/LDO/SWITCH name-to-descriptor mapping beyond the observed provider-owned class names.
- IO-domain supplier/consumer probe or GRF voltage-selector writes; IO-domain was intentionally disabled in G3.
- eMMC, TF SDMMC0, SDIO, GPU, SARADC, GMAC1, MDIO or PHY activation.
- Suspend/resume or regulator sleep-state behavior.
- Physical Ethernet link or TX.

No manual I2C/PMIC writes, no suspend, no persistent storage mount/write, and no eMMC/SN64G operation were part of this runtime test.

## 5. Final gate decision

**G3-P RUNTIME PASS — RK809 regulator provider binding and 16-object registration demonstrated on Panther X2.**

This is a provider registration result, not a physical rail validation result. G3 is complete for its defined provider-probe objective. The next planned work is the G4 IO-domain consumer static/dependency audit and controlled test design. G4 must remain a separate gate; no IO-domain enablement or GRF writes are authorized by this G3 result.
