# Panther X2 Project A — G4-P0 RAM-only runtime binding observation (2026-11-28)

## 1. Result

**G4-P0 target-board RAM-only boot and binding verification: PASS.**

The authorized single boot of the PREPARE-ONLY G4-P0 image on the SU08G test TF reached the BusyBox RAM initramfs shell on Linux 6.18.63+. Follow-up read-only sysfs/FDT inspection confirms:

- the RK3568 PMU IO-domain child was enumerated as a platform device;
- `rockchip-iodomain` is bound to that device;
- the RK808 regulator platform device is bound to `rk808-regulator`;
- 21 regulator-class objects are registered, including the four regulator objects referenced by the prior nine-supply mapping.

This is a successful **binding-only** runtime result. It is not approval for the full nine-supply mapping or physical rail validation.

## 2. Runtime boot evidence

- Kernel: Linux 6.18.63+; machine model reported as Panther X2.
- RAM: 4 GiB detected.
- Four CPUs started; PSCI hotplug tests passed.
- `/init` ran from the initramfs and reached the interactive shell `panther-x2-g4-p0-runtime`.
- The first bundled collector was defective: it used shell `[` tests although this static BusyBox build has the `test` applet but no `[` applet. Its repeated `[: not found` errors invalidate its conditional-derived claims. The later manual `ls` observations in this report supersede those collector claims.
- No persistent filesystem was mounted or written during the reported session. The capture directory was in RAM at `/run/g4-p0`.

## 3. IO-domain child and driver binding

Device-tree path:

- `/proc/device-tree/syscon@fdc20000/io-domains`

The node directory contains `name`, `phandle`, `status`, and `compatible`. The earlier attempted path `/proc/device-tree/pmu/io-domains` was incorrect; it is not evidence of a missing node.

Platform device:

- `/sys/bus/platform/devices/fdc20000.syscon:io-domains`

Bound driver:

- `/sys/bus/platform/devices/fdc20000.syscon:io-domains/driver`
- symlink target: `../../../../bus/platform/drivers/rockchip-iodomain`

The device also appears in `/sys/bus/platform/drivers/rockchip-iodomain`. This confirms successful driver binding, not merely driver availability. Since the RK3568 IO-domain probe obtains the parent PMUGRF syscon regmap before processing supplies, successful binding also supports that the probe's PMUGRF regmap acquisition completed.

## 4. RK808 regulator provider

Platform device:

- `/sys/bus/platform/devices/rk808-regulator.3.auto`

Bound driver:

- `/sys/bus/platform/devices/rk808-regulator.3.auto/driver`
- symlink target: `../../../../../../bus/platform/drivers/rk808-regulator`

The regulator class contains `regulator.0` through `regulator.20` (21 objects). Names observed:

| Class | Name |
|---:|---|
| .0 | regulator-dummy |
| .1 | vbus |
| .2 | vcc5v0_sys |
| .3 | vcc3v3_sys |
| .4 | vdd_cpu |
| .5 | vdd_logic |
| .6 | vdd_gpu |
| .7 | vcc_ddr |
| .8 | vdd_npu |
| .9 | vcc_1v8 |
| .10 | vdda0v9_image |
| .11 | vdda_0v9 |
| .12 | vdda0v9_pmu |
| .13 | vccio_acodec |
| .14 | vccio_sd |
| .15 | vcc3v3_pmu |
| .16 | vcca_1v8 |
| .17 | vcca1v8_pmu |
| .18 | vcca1v8_image |
| .19 | vcc_3v3 |
| .20 | SWITCH_REG2 |

The four relevant objects from the previously audited IO-domain supply map are present: `vcc3v3_pmu` (.15), `vcc_3v3` (.19), `vcc_1v8` (.9), and `vccio_sd` (.14). This session identified their names and class numbers; it did not re-read their voltage/state attributes.

## 5. Selector-write and electrical evidence boundary

The runtime FDT node directory lists only `name`, `phandle`, `status`, and `compatible`; none of the nine `*-supply` properties is present. This matches the frozen G4-P0 DTB audit.

The Linux 6.18.63 source audit established that absent optional supply properties are skipped by the IO-domain driver, so the voltage-read/notifier/selector-write path is not entered. The successful binding result is consistent with that design.

However:
- no tracing or register instrumentation was active to observe bus transactions;
- no PMUGRF VSEL register was read;
- no PMIC raw register was read;
- no physical rail was measured.

Therefore the accurate conclusion is: **no selector transaction is expected from the audited G4-P0 code path; the absence of such a transaction was not independently measured at runtime.** This result does not establish physical rail voltage, stability, ripple, or load capability.

## 6. Corrected collector status

The first collector's conditional checks are invalid because `[` is absent from the BusyBox build. Specifically, its claims about missing DT nodes, platform devices, drivers, or deferred-probe information must not be used as evidence. The manual observations above are the authoritative runtime record for this session.

The collector defect should be corrected in a future package revision by using the `test` applet or shell constructs supported by the frozen BusyBox applet set, followed by syntax and runtime self-tests. Do not repeat the hardware boot merely to rerun the collector; the current direct observations already establish the required binding state.

## 7. Scope and safety

- One authorized G4-P0 RAM-only boot session was used.
- The session remained in initramfs; no persistent root filesystem was mounted.
- No device-tree, kernel, driver, system, or network configuration was changed.
- No sysfs write, bind/unbind operation, regulator enable/disable, direct I2C transaction, devmem, raw PMUGRF/PMIC access, or selector access was performed by the manual observations.
- SU08G was the authorized test medium. SN64G and eMMC were not touched.
- This does not authorize G4-P full nine-supply mapping, physical voltage tests, or any further boot session.

## 8. Stage decision

| Gate | Result |
|---|---|
| G4-P0 package / offline audit | PASS |
| G4-P0 RAM-only boot to shell | PASS |
| IO-domain DT child enumeration | PASS |
| IO-domain platform-device creation | PASS |
| `rockchip-iodomain` binding | PASS |
| RK808 regulator binding | PASS |
| Regulator class registration | PASS |
| Runtime observation of no selector bus transaction | NOT VERIFIED |
| Physical rail voltage / electrical quality | NOT VERIFIED |
| Full nine-supply IO-domain mapping | NO-GO |

**G4-P0 binding-only runtime objective: PASS.** Preserve the full-supply mapping NO-GO decision. The next work should be documentation and collector correction on the host/CI side, not another hardware boot or any selector/rail experiment.


## 9. Collector BusyBox compatibility correction (2026-11-28)

The first authorized target-board session exposed a collector defect: the frozen BusyBox build contains the `test` applet but not the `[` applet, while the original collector used `[ ... ]` for shell conditionals. Those checks emitted `[: not found`; therefore conditional-derived output from that collector is invalid and must not be used as hardware evidence. Direct manual observations in Sections 3–4 supersede it.

Corrected `scripts/panther-x2-g4-p0-runtime/capture-g4-p0.sh` in commit `205053232799114ce8ecb15354831900a9db4d0f`:
- Replaced all 14 conditional `[ ... ]` tests with the already-built BusyBox `test` applet form.
- Preserved the collector's observation targets, output paths, read-only behavior, and hardware scope.
- Did not add BusyBox applets, change the initramfs, alter the kernel/DTB/config, or add any sysfs/register writes.
- The packaging workflow already runs BusyBox `ash -n` against the collector and verifies that `test` is present before packaging.

**Validation status:** source-level replacement audit PASS (zero remaining conditional `if [` expressions); target BusyBox ash syntax/build validation is pending the path-filtered GitHub Actions run. No second target-board boot is required or authorized for this correction. Do not use the corrected collector on hardware until the CI syntax/package check succeeds; the existing manual binding evidence remains valid independently.


The corrected collector then passed the dedicated packaging workflow:
- Actions run `46120998151`, job `140905253535`: completed / success.
- Steps included immutable input verification, BusyBox/initramfs syntax check, PREPARE-ONLY image assembly, manifest/checksum verification, and artifact upload; all completed successfully.
- Corrected package artifact ID `15253991870`, SHA-256 `d0bbc160b5c67899a8423b8858b016da646ea7dccf7dc57521eec3e039f13c69`.
- This was a cloud packaging/validation run only; no physical device or media access occurred.

The collector correction is therefore **SOURCE + TARGET-BUSYBOX ASH SYNTAX + PACKAGE CI: PASS**. It does not require or authorize another Panther X2 boot. Use the corrected artifact only for any future separately authorized test; the original successful manual binding observations remain the current hardware evidence.
