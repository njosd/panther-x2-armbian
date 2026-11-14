# Panther X2 BSP / RKNPU source provenance audit

Audit date: 2026-11-14

Scope: compare the earliest Panther X2 BSP 6.1 integration with the Ophub RK35xx 6.12.81 candidate, trace the RKNPU source, and determine whether the recent external-module build failures apply to either in-tree BSP route. This is a source/configuration audit only; no kernel was installed and no Panther X2 device was modified.

## 1. Earliest BSP build chain

The earliest audited BSP integration is the public repository:

- Integration repository: https://github.com/clfang666/Panther-x2-NPU-VPU
- Audited integration commit: `208f3007f4e9d09c04da8bd23ed6808ec43ca2ed`
- Armbian build framework: `70a242faa308c57be5ed636897dfee77de350773`
- Kernel source repository: `https://github.com/armbian/linux-rockchip`
- Kernel source commit: `5280f9b4336199c4025c8eed894d2b4e2268dcc6`
- Expected kernel release: `6.1.115-vendor-rk35xx`
- U-Boot source: Radxa `stable-4.19-rock3`, commit `c55987146f4f9b20f7cb2f917ca88300419afe8d`

The pinned kernel commit's own commit message is an unrelated wireless-device-tree correction. It is the chosen source-tree snapshot, not the commit that originally authored the NPU driver. The RKNPU driver is inherited from the Rockchip vendor kernel history.

## 2. RKNPU driver source provenance: confirmed Rockchip origin

The driver version in the Panther X2 BSP tree is:

- `DRIVER_DATE = 20240828`
- `DRIVER_MAJOR = 0`
- `DRIVER_MINOR = 9`
- `DRIVER_PATCHLEVEL = 8`

The matching upstream Rockchip commit is:

- Repository: https://github.com/rockchip-linux/kernel
- Commit: `736d89f344156b75393b01ab2c0e3a06c39e110f`
- Date: 2024-08-28
- Author/sign-off: Shuangjie Lin, `rock-chips.com`
- Commit message: `driver: rknpu: Update rknpu driver, version: 0.9.8`
- Stated changes: fix multi-process run error and multi-process domain-switch error.

The same commit SHA exists in both `rockchip-linux/kernel` and the Armbian Rockchip kernel history. The RKNPU version header in the Panther BSP tree identifies 0.9.8. The RKNPU Kconfig and Makefile blob contents in the Panther BSP kernel snapshot match the Rockchip 0.9.8 upstream commit. Some C source files contain subsequent Rockchip maintenance changes, so the correct provenance statement is “Rockchip vendor driver lineage, version 0.9.8, carried in Armbian's Rockchip kernel tree”, not “all files byte-identical to the original 0.9.8 commit”.

Rockchip's RKNN Toolkit2 documentation independently states that the kernel driver is open source in Rockchip kernel code and lists RK3566/RK3568 as supported platforms. The Toolkit2 repository is the userspace model-conversion/runtime stack; it is not the authoritative place to obtain the kernel driver source.

## 3. How the original BSP avoids the external-module failure

### 3.1 Built-in driver, not a separately built `rknpu.ko`

The Rockchip driver Kconfig defines `CONFIG_ROCKCHIP_RKNPU` as a tristate. Its Makefile uses:

```make
obj-$(CONFIG_ROCKCHIP_RKNPU) += rknpu.o
rknpu-$(CONFIG_PM_DEVFREQ) += rknpu_devfreq.o
```

The Panther BSP integration workflow explicitly checks the generated image config for:

```text
CONFIG_ROCKCHIP_RKNPU=y
```

That is a built-in driver (`=y`), not a loadable module (`=m`). The driver is linked into the kernel image as part of the same in-tree build. Therefore the normal in-tree build does not depend on an external module build using a separately packaged headers `Module.symvers` to resolve `pm_runtime_force_resume`.

The driver calls `pm_runtime_force_resume()` in its system-sleep PM callbacks when `CONFIG_PM_SLEEP` is enabled. The same kernel tree builds `drivers/base/power/runtime.o`; that source defines and exports `pm_runtime_force_resume` with `EXPORT_SYMBOL_GPL`. The in-tree build sees both sides of this dependency.

**Conclusion:** the Panther BSP did not fix the 6.18.63 external-module MODPOST failure by patching or replacing `pm_runtime_force_resume`. It avoids that separate-module build path by building RKNPU into the kernel image.

### 3.2 Devfreq is also built in-tree

The BSP's `rknpu_devfreq.c` includes the kernel-internal header:

```c
#include <../drivers/devfreq/governor.h>
```

The RKNPU Makefile only includes `rknpu_devfreq.o` when `CONFIG_PM_DEVFREQ` is enabled. With the complete kernel source/build tree, this internal header is available. This differs from trying to compile a copied driver source as an external module against a pruned headers package, which caused the earlier `linux/devfreq-governor.h` include failure.

The old BSP therefore does not demonstrate that the driver can be built as an external module. It demonstrates the in-tree Rockchip BSP integration path.

### 3.3 Device-node interpretation

The Kconfig default memory-manager choice is DRM GEM. In this mode the driver registers a DRM device/render node. A missing `/dev/rknpu` alone is not proof that the kernel driver is absent; inspect the selected memory-manager config, `/dev/dri/renderD*`, debugfs driver version, probe logs and the NPU's resource bindings. The DMA-heap alternative has different misc-device behavior.

## 4. The Ophub RK35xx 6.12.81 candidate uses the same integration model

At the currently observed source reference:

- Source repository: `ophub/linux-6.12.y-rockchip`
- Reference commit: `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- Driver header reports RKNPU `0.9.8`, date `20240828`.
- Kconfig and Makefile are the same Rockchip in-tree RKNPU structure.
- `rknpu_devfreq.c` still includes the in-tree private `../drivers/devfreq/governor.h`.
- `drivers/base/power/runtime.c` defines and exports `pm_runtime_force_resume`.

The corresponding observed Ophub RK35xx config reference blob is:

- Path: `kernel-config/release/rk35xx/config-6.12`
- Blob SHA: `dee127c6c644f38426eeb28000d73536084d34a3`

That config explicitly contains:

```text
CONFIG_PM=y
CONFIG_PM_SLEEP=y
CONFIG_MODULES=y
CONFIG_PM_DEVFREQ=y
CONFIG_ROCKCHIP_IOMMU=y
CONFIG_ROCKCHIP_RKNPU=y
CONFIG_ROCKCHIP_RKNPU_DRM_GEM=y
CONFIG_ROCKCHIP_RKNPU_SRAM=y
# CONFIG_ROCKCHIP_RKNPU_DMA_HEAP is not set
```

Thus the 6.12.81 source/config candidate also selects RKNPU as a built-in driver and enables devfreq. It should be validated as a complete in-tree kernel build, not by insisting that a separate `rknpu.ko` must exist.

Important provenance limitation: the observed source commit and config blob are reference snapshots. They are not yet proven to be the exact inputs used to produce the public `6.12.81.tar.gz` release asset. The package audit workflow must compare the downloaded package's own `.config`, `Module.symvers`, `kernel.release`, boot content and module archive before making package-level claims.

## 5. Panther X2 device-tree source lineage and remaining gap

### 5.1 Base Panther X2 DTS lineage

The symbolic Panther X2 board DTS is present in:

- Repository: https://github.com/unifreq/linux-6.1.y
- Path: `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`
- Original addition: Ophub commit `afaa1a194f812e30a9faedd88d6c09e7a49d909a`, 2023-07-07
- Follow-up by `tdleiyao`: commit `80101d21c55ec1c87a00a52a0c3e137a37ac7a80`, 2023-07-11; changed USB mode to host and enabled GPU
- Later Ophub update: `ffffa29dfec714c7b2682625faff73111174e783`, 2024-11-17
- DTS copyright header identifies `tdleiyao`, 2023.

A public Panther X2/RK3566 Rockchip BSP build note dated 2026-07-15 explicitly describes copying this `unifreq/linux-6.1.y` board DTS into `rockchip-linux/kernel` `develop-6.1`, then enabling the MPP-related nodes and building the BSP kernel. This establishes a documented community path for reusing the existing Panther board DTS with the Rockchip vendor kernel.

### 5.2 The dedicated Panther BSP acceleration patch

The Panther X2 BSP integration repository adds:

`armbian/userpatches/kernel/rk35xx-vendor-6.1/0001-arm64-dts-rockchip-add-panther-x2-bsp61-accel.patch`

The patch adds a full flattened `rk3566-panther-x2.dts` (about 7,546 lines) with numeric phandles, plus a DTB Makefile entry. Its NPU node includes:

- compatible: `rockchip,rk3568-rknpu`, `rockchip,rknpu`
- register range: `0xfde40000`, size `0x10000`
- IRQ 151 / `npu_irq`
- SCMI/NPU/AXI/AHB clocks and reset lines
- NPU power domain and `rknpu-supply`
- NPU OPP table
- IOMMU at `0xfde4b000`
- bus-NPU node and bus OPP table.

The integration repository contains `reference/source-input.sha256` with hashes for `rk3566-panther-x2-bsp61-accel.dtb` and `rk3566-panther-x2-bsp61-accel.dts`, but those two source-input files are not present in the repository tree. The final patch DTS is flattened/decompiled rather than the original symbolic source. Consequently, the exact origin of that particular BSP 6.1 acceleration DTB is **not yet proven**. It may combine the established Panther board DTS with Rockchip vendor SoC/device-tree content and local NPU/VPU enablement, but this remains a hypothesis until the hashed input files or their generating commands are recovered.

### 5.3 A concrete IRQ fix already present in the Panther BSP history

The Panther integration repository has commit:

`3abad73574036e43739847516d8f871bc4d4e87c`

with message `Fix Panther X2 NPU IRQ binding`. Its patch adds:

```dts
interrupt-names = "npu_irq";
```

to the NPU node and adds a CI assertion for that property.

The exact driver source at the pinned Armbian/Rockchip BSP commit `5280f9b4336199c4025c8eed894d2b4e2268dcc6` was then inspected. Its `rknpu_register_irq()` first tries `platform_get_irq_byname(..., "npu_irq")`; for Linux >= 6.1 it falls back to `platform_get_irq(pdev, 0)` when the name is absent. The exact Ophub 6.12.81 driver at `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` has the same fallback. Therefore the Panther BSP commit's explicit `interrupt-names` addition is useful for unambiguous binding and its CI contract, but it is not proven to be strictly required for probe on these exact >=6.1 driver revisions. It may address older driver variants, improve resource-name clarity, or be a defensive correction. The actual IRQ specifier and successful `devm_request_irq()` still require validation.

## 6. Similar community failure: driver present does not mean NPU usable

Ophub issue #3123 describes an RK3566 OECT system on `6.1.99-rk35xx-ophub`:

- debugfs reports RKNPU v0.9.8;
- the log says the DRM RKNPU driver initialized;
- nevertheless the user cannot use the NPU;
- the log also reports missing `npu_irq`, inability to request the NPU register region, missing `mem-supply`, and OPP/regulator problems.

This is a different RK3566 board, not Panther X2, so it is comparative evidence rather than proof of the same defect. It demonstrates that driver version 0.9.8 and a visible platform device are insufficient: board-specific DTS resource, IRQ, power and OPP bindings must be correct. It also demonstrates why `/dev/rknpu` alone is an unreliable diagnostic when the driver is built with DRM GEM.

Ophub's maintainer stated that the reported 6.1.99 image/DTB was not an image they had built or tested, and suggested testing the then-current stable 6.12 or RK35xx 6.1.115 kernel lines. A later issue comment speculated about memory-resource overlap; that comment is not a confirmed root-cause fix.

## 7. Comparison result

| Question | Earliest Panther BSP 6.1 | Ophub RK35xx 6.12.81 candidate |
|---|---|---|
| RKNPU driver source | Rockchip vendor lineage | Same Rockchip vendor lineage |
| Driver version | 0.9.8 | 0.9.8 |
| Build model | Built-in, `CONFIG_ROCKCHIP_RKNPU=y` expected by image validation | Built-in, config reference says `CONFIG_ROCKCHIP_RKNPU=y` |
| PM runtime | In-tree kernel function and driver linked together | Same source/build model |
| Devfreq | In-tree private governor header | Same in-tree private governor header |
| External `rknpu.ko` required | No, if built-in config is retained | No, if built-in config is retained |
| Panther X2 DTS | Dedicated flattened BSP acceleration patch | Package DTB and Panther X2 compatibility still to be audited |
| Runtime NPU inference | Not proven by config/DTB checks alone | Not proven |

### Main conclusion

The `pm_runtime_force_resume` MODPOST failure seen in the generic Ophub 6.18.63 external-module experiment is **not the build method used by the original Panther BSP** and is **not the intended build method indicated by the RK35xx 6.12.81 config**. Both BSP paths select an in-tree built-in RKNPU driver. The external-module experiment introduced a separate dependency on the headers package's `Module.symvers`, and its failure should not be used to conclude that the integrated RK35xx BSP driver cannot build.

The unresolved high-value issue is now Panther X2 device-tree provenance and runtime correctness, not how to manufacture a separate `rknpu.ko`.

## 8. Next audit actions

1. Run `.github/workflows/audit-rk35xx-kernel.yml` and interpret module archive contents in light of `CONFIG_ROCKCHIP_RKNPU=y`: absence of `rknpu.ko` is expected for a built-in driver.
2. Compare the public 6.12.81 package's own config and `Module.symvers` with the source/config reference snapshots; do not assume they are the same build.
3. Recover the two hashed BSP DTS/DTB inputs or the exact command that generated them.
4. Diff the Panther flattened BSP DTS against the symbolic `unifreq` Panther DTS and Rockchip `rk356x.dtsi` / `rk3566-box.dtsi` sources, especially NPU IRQ, resource ranges, IOMMU, power supply, clocks, resets, power domain and OPP.
5. Prefer a full in-tree kernel CI build with `CONFIG_ROCKCHIP_RKNPU=y` and `CONFIG_PM_DEVFREQ=y`; do not treat external-module MODPOST as the primary RK35xx BSP validation.
6. Keep real probe, DRM render-node access, RKNN runtime version match and inference on Panther X2 marked unverified until there is a controlled hardware test.

No installation, system modification, driver loading or service change was performed on 192.168.9.6.


## 9. External community cross-checks (2026-11-14)

These sources corroborate the in-tree build model and the importance of board-specific DTS. They are comparative reports, not proof that the exact Panther X2 BSP image was runtime-tested.

### 9.1 Panther X2 board DTS is reused from the Ophub/unifreq lineage

A 2026-07-15 RK3566 Rockchip BSP build walkthrough explicitly says it used the third-party ArmSoM kernel initially, then verified the official `rockchip-linux/kernel` `develop-6.1` source could also build. For Panther X2 it copies `rk3566-panther-x2.dts` from `unifreq/linux-6.1.y`, adds the DTB to the Rockchip DTS Makefile, enables IOMMU/MPP configuration, and enables MPP service / RKVDEC / RKVENC nodes. This independently corroborates the board-DTS reuse path recorded above. It also reports a hardware-specific warning that Panther X2 has USB 2.0 only, and removes an inherited `usb_host0_xhci` host-mode fragment; this is a useful reminder not to treat every inherited DTS property as correct for the physical board.

Source: https://lxnchan.cn/rockchip-mpp-kernel.html (created 2026-07-15, updated 2026-08-17).

### 9.2 Rockchip driver 0.9.8 plus a present NPU node is not enough

Ophub issue #3123 reports an RK3566 OECT board where RKNPU 0.9.8 initializes a DRM device but logs include:
- missing `mem-supply`;
- failed resource request for `0xfde40000-0xfde4ffff`;
- `IRQ npu_irq not found`;
- missing NVMEM calibration data;
- OPP not supported by regulators.

The issue's reporter initially assumes `rknpu.ko` is missing, but the logs show the driver itself did initialize. Ophub maintainer comments say the 6.1.99 image/DTB had not been built/tested by them and warns that different image packagers may have different board-specific handling. This supports a careful separation between driver presence, DT binding correctness and successful inference.

Source: https://github.com/ophub/amlogic-s9xxx-armbian/issues/3123

### 9.3 Armbian community: RKNPU can be built-in and disabled by DTB

A 2025 Armbian forum discussion for RK3566 notes that `modules.builtin` can contain `kernel/drivers/rknpu/rknpu.ko` even though the driver is built into the kernel image (the filename suffix is retained in the built-in list). The same report finds the NPU node disabled in the DTB and describes enabling it with a board-specific overlay. It also points to an Armbian RK3566 NPU-enabled DTS as a reference. This matches the conclusion that an absent loadable `rknpu.ko` in the modules archive does not prove the driver is absent.

Source: https://forum.armbian.com/topic/44950-rk3566-kernel-with-npu-support/

A separate H96 Max V56 community thread shows the same classes of DTB issues across RK3566 devices: absent `npu_irq`, supply lookups, IOMMU mode and regulator/OPP messages. The exact wiring differs by board; these logs are a checklist of failure modes, not a recipe to copy the H96 DTS to Panther X2.

Source: https://forum.armbian.com/topic/28895-efforts-to-develop-firmware-for-h96-max-v56-rk3566-8g64g/page/11/

### 9.4 Rockchip upstream issue: DRM node symptoms can mask DT resource errors

Rockchip kernel issue #371 reports RKNPU 0.9.8 and a DRM initialization message while also showing a memory resource request warning and missing power-model properties. It remains an open report, so it is evidence of a real diagnostic pattern, not a confirmed fix.

Source: https://github.com/rockchip-linux/kernel/issues/371

### 9.5 RKNN driver source vs Toolkit2

Rockchip's `rockchip-linux/rknpu` repository explains that RK3566/RK3568/RK3588 should use the `rknpu2` kernel driver line and RKNN Toolkit2 userspace stack, rather than the older rknpu repository's older-platform driver. The driver source is maintained in the Rockchip kernel tree or SDK's `external/rknpu/drivers`; Toolkit2 is the model conversion/runtime interface and does not replace the kernel driver.

Source: https://github.com/rockchip-linux/rknpu

### External evidence conclusion

The community reports strongly support the following diagnostic order for Panther X2:
1. confirm `CONFIG_ROCKCHIP_RKNPU=y` and built-in list, not just search for a loadable `.ko`;
2. confirm actual boot DTB and NPU node status;
3. validate `reg`, `interrupts` and `interrupt-names = "npu_irq"`;
4. validate `rknpu-supply`, any `mem-supply` expected by this exact driver revision, power-domain supply, clocks/resets, IOMMU and NPU/bus OPP/regulator ranges;
5. validate that the selected DRM GEM backend creates a DRM render node and that the driver reports v0.9.8;
6. only then test RKNN runtime/Toolkit2 ABI and execute an inference workload.

No community workaround should be copied verbatim without comparing the Panther X2 board wiring and the exact driver/DTS revision.


### 9.6 Hashed Panther BSP DTS inputs: public search result

A global GitHub code search for the two SHA-256 values recorded in `reference/source-input.sha256` finds the same hash manifest in a second repository, `theflegend/pantherx2-build`. That repository has a single initial commit dated 2026-09-14. Its BSP patch blob SHA is exactly the same as the `clfang666/Panther-x2-NPU-VPU` repository (`84ee74c07cba9cace4f7cb6b205ce2fc8ba1900f`), and its README blob is also identical. This is a byte-identical copy/mirror, not an independent origin for the DTB/DTS.

The two original hashed inputs remain absent from both repository trees. The matching hashes narrow the search terms but do not yet identify the original board-vendor DTB or source project. Keep the flattened DTS provenance as unresolved; do not label it as Rockchip official or vendor-provided until its exact hash is found in an upstream package/repository or the original file is recovered.


### 9.7 RKNN Toolkit2 is the userspace stack, not the Linux kernel driver

The maintained `airockchip/rknn-toolkit2` README separates the stack into:
- RKNN-Toolkit2: PC-side model conversion, quantization, inference and performance evaluation;
- RKNN-Toolkit-Lite2: Python deployment API on the board;
- RKNN Runtime: C/C++ board-side runtime;
- RKNPU kernel driver: separate open-source code in the Rockchip kernel tree.

Its supported platform list includes RK3566/RK3568. The older `rockchip-linux/rknpu2` repository says it is no longer maintained and has moved into `airockchip/rknn-toolkit2/rknpu2`. Its runtime directory contains the Linux `librknn_api` and `rknn_server` userspace components; `rknpu.mk` packages `librknnrt`. This confirms that the user's `rknpu2` folder is not the place to build the Panther BSP's kernel-side `drivers/rknpu/rknpu_drv.c` driver.

For Panther X2, keep the compatibility chain separate:
1. kernel RKNPU driver (Rockchip kernel tree; 0.9.8 in the audited 6.1/6.12 candidates);
2. board DTS and kernel configuration;
3. matching ARM64 RKNN Runtime / Lite2 userspace package;
4. RKNN model generated by a compatible Toolkit2 version.

Rockchip documentation warns that userspace and kernel driver versions must match; after the kernel path is validated, we must lock and verify the runtime package version and its reported HAL kernel/userspace versions. Do not assume that installing Toolkit2 on the iMac or Panther host automatically supplies the board-side kernel driver.


## 10. Important correction for the Ophub RK35xx 6.12 driver

The exact RKNPU source at Ophub `linux-6.12.y-rockchip` commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` was inspected after the package/config comparison.

- `drivers/rknpu/rknpu_drv.c` has an IRQ compatibility path: when named IRQ resources exist it looks up `npu_irq`; otherwise it falls back to `platform_get_irq(pdev, 0)`. Therefore absence of `interrupt-names = "npu_irq"` is not, by itself, proof of probe failure on this 6.12 driver. The actual interrupt specifier and resource mapping still need validation.
- The driver obtains the `rknpu` regulator with `devm_regulator_get_optional()`, and also probes an optional `mem` regulator.
- `rknpu_devfreq.c` checks whether both `rknpu-supply` and `mem-supply` exist. If both exist, it configures the two-regulator OPP helper; otherwise it configures the single `rknpu` regulator path.
- The Ophub Panther X2 board DTS defines a regulator label `vdd_npu`, but does not attach it to the NPU device using `rknpu-supply`; it also does not enable `&rknpu` or `&rknpu_mmu`.
- The shared RK356x SoC DTS has the NPU node and MMU node, but both default to `status = "disabled"`.

This makes the presently visible 6.12 Panther X2 gap more specific: NPU and MMU are disabled in the board's effective DTS, and the existing `vdd_npu` regulator is not linked to the NPU device for its devfreq/OPP regulator path. Do not assume `mem-supply` is mandatory; the exact driver supports a single-regulator path. Do not add an IRQ name mechanically; first inspect the actual packaged DTB and this driver's IRQ fallback logic.

This is source-level evidence only. The effective DTB shipped in either standard or Flippy package has not yet been decompiled in CI, and no Panther X2 hardware probe has been performed.


## 11. Panther X2 NPU DTS source trace against the official/maintained board lineage

### 11.1 Original Panther X2 board DTS does not enable NPU

The Panther X2 board DTS was added to `unifreq/linux-6.1.y` by Ophub commit `afaa1a194f812e30a9faedd88d6c09e7a49d909a` on 2023-07-07. The original file copyright identifies `tdleiyao`. Follow-up commit `80101d21c55ec1c87a00a52a0c3e137a37ac7a80` on 2023-07-11 explicitly enabled GPU and adjusted USB host mode. The subsequent 2024 Ophub update is `ffffa29dfec714c7b2682625faff73111174e783`.

The original/current unifreq Panther X2 board DTS defines the PMIC `vdd_npu` regulator, but contains no board-level `&rknpu`, `&rknpu_mmu`, or `&bus_npu` enable fragments. The generic Rockchip `rk356x.dtsi` defines those SoC nodes and their clocks/resets/power-domain/OPP/IOMMU references, but defaults NPU, NPU MMU and NPU bus to disabled.

This explains why the ordinary Panther X2 DTS lineage can contain a `vdd_npu` rail without exposing an active NPU platform device.

### 11.2 Later Panther X2 Vendor BSP board enablement

The later Panther X2 Vendor 6.1 board DTS in `Lyric-c/panther-x2` (snapshot commit `2ceb614fc294b4832268ec3e50716e7e9d3f1e8b`) adds the following board-level configuration:

```dts
&bus_npu {
    bus-supply = <&vdd_logic>;
    pvtm-supply = <&vdd_cpu>;
    status = "okay";
};

&rknpu {
    rknpu-supply = <&vdd_npu>;
    status = "okay";
};

&rknpu_mmu {
    status = "okay";
};
```

The same file's PMIC already defines `vdd_logic`, `vdd_cpu`, and `vdd_npu`. The NPU board fragment does not set `mem-supply`. This is consistent with the exact Ophub 6.12.81 RKNPU driver, which uses the single-`rknpu` regulator path when the optional `mem` supply is absent. It is not consistent with blindly copying the H96 Max V56 dual-supply fragment; H96 is a useful RK3566 example but its board-specific memory-supply wiring is not the Panther X2 reference.

The corresponding generic SoC DTSI already supplies the NPU node's register range, IRQ number, SCMI/CRU clocks, reset lines, power domain, OPP table and IOMMU phandle. The board fragment therefore activates and binds existing SoC resources rather than re-declaring the whole NPU node.

### 11.3 What the earliest Panther BSP patch contributes

The earliest audited BSP integration patch contains a flattened Panther X2 DTS with:
- `npu@fde40000`, `iommu@fde4b000`, and `bus-npu` enabled;
- NPU regulator phandle pointing to the board's DCDC_REG4 `vdd_npu`;
- NPU bus supply pointing to DCDC_REG1 `vdd_logic`;
- NPU bus PVTM supply pointing to `vdd_cpu`;
- an explicit `interrupt-names = "npu_irq"` property;
- the RK356x SoC NPU OPP and bus OPP tables.

The original `reference/source-input.sha256` files are still missing from that integration repository. The flattened DTS patch is therefore evidence of the resulting configuration, not proof of the original generator/source file's provenance. The later symbolic Panther X2 Vendor DTS is independently inspectable and contains the same three board-level enablement fragments, but it should not be asserted to be the exact authoring source of the earlier flattened patch without a matching hash or commit link.

### 11.4 What this tells us about the Ophub 6.12.81 gap

The Ophub 6.12.81 `rk356x.dtsi` already has the same generic SoC NPU structure as the Armbian Rockchip 6.1 BSP reference. The Panther X2 6.12 board DTS already defines the same `vdd_npu`, `vdd_logic`, and `vdd_cpu` regulator labels. The observed difference is primarily the missing board-level enablement/binding fragments above.

This narrows the likely minimal board-DTS delta to those fragments, but does **not** yet authorize applying them. Before any patch is authored, still verify:
- exact 6.12.81 packaged DTB and source revision relationship;
- that the board's `vdd_logic` and `vdd_cpu` OPP ranges match the RK356x NPU/bus OPP tables;
- whether `bus_npu` devfreq/OPP is supported and expected by this exact kernel config;
- NPU IOMMU behavior with Panther X2's 4 GB RAM and DMA address constraints;
- actual regulator, IRQ, clocks and power-domain probe behavior on hardware.

No DTS patch has been created or applied. All conclusions here are source-level/static comparisons only.


## 12. Panther X2 NPU OPP, regulator and DMA/IOMMU static audit (2026-11-14)

All checks below compare the pinned Ophub 6.12.81 source commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` with the Panther X2 Vendor 6.1 DTS snapshot `2ceb614fc294b4832268ec3e50716e7e9d3f1e8b`. These are source-level checks, not electrical or hardware validation.

### 12.1 NPU OPP and PMIC voltage envelopes

The shared RK356x NPU OPP table in `rk356x.dtsi` provides:
- NPU frequency points from 200 MHz through 1 GHz (the 1 GHz point is marked disabled in the inspected table);
- nominal NPU voltage requirements from 850 mV through 1.0 V for the enabled high-frequency points;
- OPP selection based on supported-hardware, leakage/PVTM/MBIST and NPU OPP-info NVMEM cells.

Panther X2's `vdd_npu` regulator is declared with a 500 mV minimum, 1.35 V maximum and 900 mV initial voltage. Its declared voltage envelope therefore includes the NPU OPP nominal range (up to 1.0 V). This is a static DT range comparison only; it does not prove the physical PMIC rail, board power integrity, silicon bin or actual voltage transitions are correct.

The NPU bus OPP table has 700/900/1000 MHz entries with nominal voltage requirements of 875–950 mV (1 GHz entry exists in the table). Panther X2 `vdd_logic` is declared 500 mV–1.35 V with 900 mV initial voltage, so its declared range also covers those nominal values. The `bus_npu` node uses `bus-supply = <&vdd_logic>` and `pvtm-supply = <&vdd_cpu>`; `vdd_cpu` is declared 800 mV–1.15 V.

### 12.2 Exact bus_npu policy and driver path

The RK356x SoC DTSI sets `rockchip,busfreq-policy = "clkfreq"` and provides the `bus` clock plus the bus OPP table. The pinned 6.12.81 `drivers/devfreq/rockchip_bus.c`:
- matches `rockchip,rk3568-bus`;
- obtains clock `bus` and regulator `bus`;
- initializes the OPP table using regulator name `pvtm`;
- selects the current OPP and registers a clock-rate notifier;
- adjusts the bus regulator voltage before an upward clock-rate change and after a downward change.

Thus the Panther Vendor board fragment's `bus-supply` and `pvtm-supply` are not decorative properties: they satisfy the exact `clkfreq` driver's regulator and OPP/PVTM path. The source-level configuration is internally coherent. Whether the boot firmware/SCMI clock provider exposes the expected clock and whether PVTM calibration values are valid on this particular board remain runtime questions.

### 12.3 Single NPU regulator is supported

The pinned 6.12.81 RKNPU driver calls `devm_regulator_get_optional(dev, "rknpu")` and separately attempts optional `"mem"`. The Rockchip OPP helper adds the second regulator name only if the device node has `mem-supply`. Panther X2 Vendor DTS provides `rknpu-supply` and no `mem-supply`, which is a supported single-regulator topology. H96's second memory rail must not be copied to Panther X2 without board evidence.

### 12.4 DMA mask and 4 GB RAM: correct the risk statement

The RK356x RKNPU driver config explicitly sets `dma_mask = DMA_BIT_MASK(32)`. This means the driver/device is limited to a 32-bit DMA address aperture. A 4 GB physical address space spans 0x00000000–0xffffffff, so “the board has 4 GB RAM” alone does **not** prove an incompatibility or require disabling IOMMU. With IOMMU enabled, the device normally uses a 32-bit IOVA aperture while the IOMMU maps backing physical pages; the exact DMA/IOMMU integration and reserved-memory fallback still need verification.

When IOMMU is disabled, this driver attempts `of_reserved_mem_device_init()`; the packaged Panther X2 DTB audit found an `rknpu` shared-dma-pool reservation. Therefore an IOMMU-disabled fallback may be described by the DTB, but its exact base/size, placement below the 32-bit DMA limit, CMA interaction and usable capacity must be inspected before treating it as a viable fallback.

**Correction to the earlier risk list:** do not carry forward the blanket claim that 4 GB RAM is a likely IOMMU blocker. The confirmed constraint is the driver's 32-bit DMA mask; actual compatibility depends on the memory map, IOVA configuration, IOMMU driver and reserved pool. No basis currently exists to recommend disabling IOMMU pre-emptively.

### 12.5 NVMEM OPP references

All six NPU OPP NVMEM phandles referenced by the shared RK356x DTSI (`npu_leakage`, `core_pvtm`, `mbist_vmin`, `npu_opp_info`, `specification_serial_number`, `remark_spec_serial_number`) are defined in the same SoC DTSI. There is no unresolved phandle at source level. Whether the Panther X2's OTP/eFuse data is populated and decoded as expected still requires runtime logs and silicon validation.

### 12.6 Current risk disposition

| Topic | Static result | Still unverified |
|---|---|---|
| NPU OPP vs vdd_npu | Declared voltage ranges overlap | Actual rail stability and silicon bin |
| bus OPP vs vdd_logic | Declared voltage ranges overlap | Actual transitions and clock provider |
| bus_npu driver | `clkfreq` path and supplies match source | Probe success on board |
| NPU supply | Single `rknpu` supply supported | Physical rail behavior |
| 4 GB RAM / IOMMU | 32-bit DMA aperture; 4 GB alone is not proof of failure | IOVA, memory map, pool placement |
| OPP NVMEM cells | All phandles defined | Actual OTP contents and calibration |

No DTS changes or deployable patches were made. The next safe engineering step is a temporary CI-only candidate-DTS build and static DTB comparison, keeping the product DTS untouched. Hardware probe and RKNN runtime tests remain separate, explicitly authorized stages.
