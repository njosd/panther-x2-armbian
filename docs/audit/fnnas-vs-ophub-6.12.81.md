# FNNAS v389 Panther X2 reference vs Ophub 6.12.81

## Scope and evidence

This is a static comparison of:
- The DTB extracted from the known-booting FNNAS v389 64 GB TF card.
- The Panther X2 DTB extracted from the Ophub RK35xx 6.12.81 standard and Flippy package audit completed on 2026-11-14.
- The FNNAS `armbianEnv.txt` and `boot.cmd` extracted from the same TF boot partition.
- The 6.12.81 kernel configuration included in the existing standard-vs-Flippy package audit.

No target device was modified or booted for this comparison.

### Integrity identifiers

| Item | Identifier |
|---|---|
| FNNAS uploaded archive SHA256 | `463614cd651abc693661b3f6a6af9582d5a8d03280b7a0794732e0134fc98c84` |
| FNNAS DTB SHA256 | `1b17eb39799f34420d73553c81ba53a48da917b67c4274e792bddc98325763f5` |
| FNNAS DTB decompiled DTS SHA256 | `6b914fa8241c47e714bfb714d05d642c4029dd1755c6e6c7faed13794f793a3e` |
| Ophub 6.12.81 package SHA256 | `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b` |
| Ophub standard Panther X2 decompiled DTS SHA256 | `d701f187e2a4a06723b7f33cf4e3ec731a461f0942dd863b9bc5e86ad2e9b033` |
| Ophub Flippy Panther X2 decompiled DTS SHA256 | `d701f187e2a4a06723b7f33cf4e3ec731a461f0942dd863b9bc5e86ad2e9b033` |

The standard and Flippy Panther X2 decompiled DTS files are byte-identical. The 6.12.81 package metadata records source commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`; the existing package audit explicitly notes that the source/config references alone do not prove package provenance.

## 1. FNNAS boot configuration

The extracted `armbianEnv.txt` sets:
- `fdtfile=rockchip/rk3566-panther-x2.dtb`
- `rootdev=UUID=421f79ca-11b3-4f49-a705-962c30b4feb2`
- `rootfstype=btrfs`
- `rootflags=compress=zstd:1`
- `console=both`, `consoleargs=console=tty0 console=ttyS02,1500000`
- `earlycon=on`
- `extraargs=rw rootwait ignore_loglevel panic=-1 systemd.unit=emergency.target`

Important interpretation:
- `boot.cmd` has fallback defaults `rootdev=/dev/mmcblk0p1` and `rootfstype=ext4`, but imports `armbianEnv.txt` before building the final bootargs. The effective root selection is therefore the Btrfs UUID and Btrfs root flags above, not the fallback ext4 path.
- Kernel, initrd and DTB are loaded from the current U-Boot `${devtype} ${devnum}` boot device. The script does not hard-code the TF card's U-Boot device number.
- `part uuid ${devtype} ${devnum}:1` records the boot partition PARTUUID in `ubootpart=${partuuid}`; this is distinct from the root filesystem UUID.
- `systemd.unit=emergency.target` deliberately requests an emergency target. This is a useful minimal-rescue boot reference, not evidence that a complete normal multi-user server boot was validated.

## 2. TF/eMMC controller mapping

Both DTBs describe the same controller addresses:
- `fe2b0000`: removable SD/TF controller, 4-bit bus, high-speed SD, `broken-cd`, 150 MHz maximum, `vqmmc-supply`.
- `fe310000`: 8-bit non-removable eMMC controller, HS200 1.8 V, `vmmc-supply` and `vqmmc-supply`.
- `fe2c0000`: non-removable SDIO/Wi-Fi controller.

The notable difference is the Linux MMC alias numbering:

| Alias | FNNAS v389 DTB | Ophub 6.12.81 DTB |
|---|---|---|
| `mmc0` | `fe310000` (eMMC) | `fe2b0000` (TF/SD) |
| `mmc1` | `fe2b0000` (TF/SD) | `fe310000` (eMMC) |
| `mmc2` | `fe2c0000` (SDIO) | `fe2c0000` (SDIO) |

This changes likely Linux `/dev/mmcblkN` enumeration. It does not by itself prove a boot defect: the FNNAS boot script loads from the current U-Boot boot device and the effective root filesystem is selected by UUID. Keep UUID-based root selection; do not change aliases without runtime evidence from the exact boot path.

## 3. SD power and regulator findings

The FNNAS and Ophub 6.12.81 DTBs agree on the critical TF power description:
- RK809 `SWITCH_REG2`, regulator name `vcc3v3_sd`, is `status = "disabled"`.
- RK809 `LDO_REG5`, regulator name `vccio_sd`, has `regulator-always-on` and `regulator-boot-on`.
- The `fe2b0000` TF controller has `vqmmc-supply = <&vccio_sd>`, but no `vmmc-supply`.
- The eMMC controller has both `vmmc-supply` and `vqmmc-supply`.

The FNNAS v389 TF boot success is therefore a real-world reference showing that this DTB arrangement is compatible with at least one successful Panther X2 TF boot. It does **not** reveal the physical electrical state of RK809 SW2, nor prove which stage (boot ROM, U-Boot, board circuitry or firmware default) maintained the TF 3.3 V rail. Do not infer regulator hardware state from the disabled DTB node alone.

## 4. Accelerator and multimedia nodes

### FNNAS v389 DTB
- No `npu@fde40000` node is present.
- GPU node is present and `status = "okay"`.
- Older VPU decoder (`rockchip,rk3568-vpu`), RGA (`rockchip,rk3568-rga`) and VEPU nodes are present without an explicit `status` property (which is not the same as an explicit disabled node).
- This does not establish that the corresponding kernel drivers were loaded or hardware acceleration was exercised.

### Ophub 6.12.81 DTB
- NPU node `npu@fde40000` and its OPP/IOMMU descriptions are present, but the NPU node and NPU IOMMU are `status = "disabled"`.
- `mpp-srv` is `disabled`.
- VDPU, VEPU, RGA, IEP, RKVENC and RKVDEC nodes are also explicitly `disabled`.
- GPU remains `status = "okay"`.

### Ophub 6.12.81 kernel configuration
The audited config includes:
- `CONFIG_ROCKCHIP_RKNPU=y`
- `CONFIG_ROCKCHIP_MPP_SERVICE=y`
- `CONFIG_ROCKCHIP_MPP_RKVDEC=y`, `...RKVDEC2=y`, `...RKVENC=y`, `...RKVENC2=y`
- `CONFIG_VIDEO_ROCKCHIP_RGA=y`

This establishes that relevant driver code is built into the audited 6.12.81 kernel configuration, while the shipped Panther X2 DTB keeps the NPU and most MPP/media nodes disabled. Kernel config presence plus a DTB node is not proof of successful device probe or usable acceleration.

## 5. Conclusions for the minimal-system mainline

1. The FNNAS boot script is a useful reference for booting from whichever MMC device U-Boot selected, loading kernel/initrd/DTB from that device, and locating the root filesystem by UUID.
2. The FNNAS reference uses Btrfs with zstd and an emergency systemd target. Treat the latter as a rescue/minimal boot profile, not a finished server configuration.
3. The two DTBs have different Linux MMC alias ordering. This is a point to observe during boot logs, not a reason to edit the 6.12.81 DTB pre-emptively.
4. The known-working FNNAS DTB and Ophub 6.12.81 DTB both mark RK809 SW2 `vcc3v3_sd` disabled and omit `vmmc-supply` from the TF controller. This weakens the theory that Linux must enable SW2 via this DTB property for the observed TF boot, but does not identify the physical rail's power source/state.
5. Ophub 6.12.81 is better positioned for future NPU work than the FNNAS DTB: its kernel config has RKNPU built-in and its DTB contains NPU/OPP/IOMMU descriptions. However, those DTB nodes are disabled in the audited package. NPU use remains **not validated** and requires a separate, carefully scoped DTB/driver enablement study.
6. The next safe step is static source-level review of the exact 6.12.81 Panther X2 DTS and its matching driver/PM-domain dependencies, then a minimal boot-only validation plan. Do not change the running 9.6 system or enable accelerator nodes as part of this audit.

## Evidence classification

- **Verified from extracted files:** FNNAS boot environment and script contents; FNNAS DTB properties; Ophub 6.12.81 DTB properties; 6.12.81 kernel config symbols; standard/Flippy decompiled DTS equality.
- **Known project baseline:** FNNAS v389 TF card has previously booted successfully on Panther X2.
- **Not verified:** Exact FNNAS bootloader's power-rail actions; physical RK809 SW2 state; successful NPU/MPP driver probe; successful NPU inference or video acceleration; normal multi-user boot from the FNNAS root filesystem.


## 6. Exact 6.12.81 RKNPU driver / supply cross-check

The recorded source commit is resolvable in `ophub/linux-6.12.y-rockchip`:
- Commit: `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- Board DTS: `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`
- SoC DTSI: `arch/arm64/boot/dts/rockchip/rk356x.dtsi`
- Vendor RKNPU driver: `drivers/rknpu/rknpu_drv.c`
- Devfreq implementation: `drivers/rknpu/rknpu_devfreq.c`

The exact source confirms:
- The NPU node's compatible `rockchip,rk3568-rknpu` is explicitly matched by the vendor `drivers/rknpu/rknpu_drv.c` driver.
- The driver obtains an optional regulator using `devm_regulator_get_optional(dev, "rknpu")`. This regulator name corresponds to a DT property `rknpu-supply`.
- The shipped Panther X2 DTB contains a regulator named `vdd_npu` (RK809 DCDC_REG4), but the NPU node has no `rknpu-supply` reference to it.
- The NPU node itself and its IOMMU remain disabled in the shipped DTB, so this supply mismatch is a static enablement gap, not an observed failure on the running system.
- In this driver revision, the optional supply can leave `rknpu_dev->vdd` null. The driver's `RKNPU_GET_VOLT` action calls `regulator_get_voltage(rknpu_dev->vdd)` without a local null check. The devfreq initialization path also reads the regulator voltage if its OPP/devfreq setup succeeds. Therefore, simply changing the NPU node to `okay` without auditing the supply path and ioctl/devfreq behavior is not an acceptable enablement plan.

The RK3568 mainline/Rocket enablement RFCs found during external research use a different binding/interface, including `rockchip,rk3568-rknn-core`, `npu-supply` and a PM-domain `domain-supply`. That is not the same compatible or driver interface as this 6.12.81 vendor RKNPU driver. Do not transplant those property names or patches into this vendor DTB without a deliberate driver/binding reconciliation.

**Result:** 6.12.81 contains the vendor RKNPU driver and a disabled RK3568 NPU hardware description, but the board DTB does not currently connect the NPU driver to the board's `vdd_npu` regulator. This is a concrete item for a separate NPU enablement patch study; it is not a reason to delay the minimal non-accelerated system.
