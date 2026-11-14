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

This is meaningful: the Rockchip RKNPU driver requests its core IRQ by the name `npu_irq`. The generic Rockchip `rk356x.dtsi` NPU node has the IRQ number but does not declare this `interrupt-names` entry in the inspected version. The Panther-specific fix supplies the name expected by the driver.

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
