# Panther X2 Project-A G2 minimal runtime packaging preparation (2026-11-27)

## 1. Purpose and boundary

G2-B build-only passed on 2026-11-27 (run `45924949130`, artifact `15167050233`). This document records the next preparation step: assemble a reproducible Project-A Linux 6.18.63 minimal RAM runtime using the frozen G2 kernel and DTB plus the already verified B1 static BusyBox and JP-TvBox U-Boot proper.

This is **PREPARE-ONLY**. The packaging workflow runs entirely on a GitHub Actions runner. It does not access Panther X2, write any physical TF/eMMC, start a boot, probe RK809, enable regulators, or activate GMAC/MDIO/PHY. Creating the workflow is not authorization to write media or boot the board.

The runtime package is a safe base for subsequent stage-specific work. It is not the G2-PROBE image with the PMIC enabled.

## 2. Frozen input artifacts

| Input | Run / artifact | Identity |
|---|---|---|
| G2-B kernel build | run `45924949130`, artifact `15167050233` | ZIP SHA256 `db4edb124497821158225d0a2d16b2f3f4f98ccbeabd5e3a95e09cdd1d46e346` |
| B1 boot-support bundle | run `45328201244`, artifact `14890817693` | ZIP SHA256 `9274e557ea5b62b6c2fc086d5aa3fd9a502215ff0070870ae36a9d6dfcfd4b9c` |
| Linux source | `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f` | Linux 6.18.63 |
| Kernel Image | G2 output | `c8ad5e8c6d4f7b095374abd66e2fc44379e83954c3991b453c3d7c8da3b7edf7` |
| Final kernel config | G2 output | `ffa99212686a1347145628fd50ecf3341437efe4a4f130002e4b27003c4f553b` |
| Panther X2 DTB | G2 output | `f6d83d86231b50c903abdf158893b6caa1e8c2aab931c9bf2dbb1b6ca36576dc` |
| Static BusyBox | B1 output, v1.37.0 | `2d77cb64f5ab5ca33efae040083abe31912ab02677dd21c1b79ade6ed0e98b15` |
| JP-TvBox U-Boot proper | B1 output | `a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce` |

The B1 bundle was downloaded and inspected locally during this preparation. Its internal `output/SHA256SUMS` validated, including the BusyBox, DTB, U-Boot proper, boot script and existing B1 initramfs. The G2 workflow artifact's internal `output/SHA256SUMS` is independently verified again by the new packaging workflow.

The G2 build toolchain was recovered from the successful run's apt installation log (job `140263994034`): runner `ubuntu-24.04`, package `gcc-13-aarch64-linux-gnu` version `13.3.0-6ubuntu2~24.04.1cross1`, wrapper package `gcc-aarch64-linux-gnu` version `4:13.2.0-7ubuntu1`. The new runtime manifest records these exact package versions and their provenance. This avoids marking the compiler as unknown merely because the earlier G2 artifact manifest omitted it.

## 3. Runtime composition

| Component | Source / treatment |
|---|---|
| Linux Image | G2-B exact output |
| Panther X2 DTB | G2-B exact output; RK809/GMAC1/MDIO/RTL8211F disabled |
| BusyBox | frozen B1 static ARM64 binary; no rebuild or applet expansion |
| `/init` | new Project-A G2 diagnostic shell init; mounts procfs/sysfs, reports kernel/model/cmdline/memory/interfaces/DTB statuses/mounts/dmesg, then interactive shell |
| initramfs | rebuilt from the static BusyBox plus the new init and only required applet symlinks |
| `uInitrd` | generated from the gzip initramfs using `mkimage` |
| `boot.scr` | generated from the frozen Project-A G2 `boot.cmd` |
| U-Boot proper | frozen JP-TvBox FIT, embedded at raw LBA 16384 (8 MiB) |
| TF partition | 2 GiB GPT image; `PANTHER_BOOT` ext4 partition 1, LBA 32768 through 4192255 |
| Root filesystem | initramfs in RAM; no persistent rootfs or modules tree |

**Important B1 baseline clarification:** the actual B1/R1 kernel config intentionally retains `CONFIG_BLOCK`, `CONFIG_MMC`, `CONFIG_MMC_DW`, `CONFIG_MMC_DW_ROCKCHIP`, `CONFIG_USB`, USB host/PHY and filesystem support. This is not an accidental G2 regression: the B1 DTB keeps the intended eMMC/TF/SD and USB host/PHY nodes according to the established board baseline. The G2 runtime preserves this. Linux may enumerate storage/USB devices, but `/init` does not mount or write persistent filesystems; the root remains initramfs in RAM. This distinction must not be misstated as “storage drivers disabled.” The same DTB statuses are now explicit packaging gates and are printed by `/init`. USB network adapter support remains excluded (`CONFIG_USB_USBNET` and the relevant USB NIC drivers are not enabled); retaining USB host/PHY support does not add USB Ethernet to project scope.

The new init script and boot script are stored at:
- `scripts/panther-x2-g2-runtime/init`
- `scripts/panther-x2-g2-runtime/boot.cmd`

## 4. Frozen boot contract

The boot script preserves the already exercised U-Boot loading arrangement:

- Kernel Image: `mmc 1:1`, load address `0x00280000`, file `/Image`.
- uInitrd: `mmc 1:1`, load address `0x0a200000`, file `/uInitrd`.
- Panther X2 DTB: `mmc 1:1`, load address `0x0a100000`, file `/dtb/rockchip/rk3566-panther-x2.dtb`.
- bootargs: `console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init`.
- Existing boot chain: eMMC SPL -> JP-TvBox U-Boot proper from TF -> Image/uInitrd/DTB from TF -> RAM initramfs.

The script does not save U-Boot environment, reset the device, or fall through to another boot target after a failed load. It holds in the U-Boot script if a load or `booti` returns.

The eMMC SPL remains an existing boot dependency. This workflow does not install or alter SPL/IDBLoader.

## 5. Safety and isolation gates

The packaging workflow must verify before assembling the image:

1. G2 and B1 artifact internal SHA256 manifests.
2. Exact G2 Image/config/DTB, B1 BusyBox and JP U-Boot proper hashes listed above.
3. Required kernel configuration: ARM64, OF, initrd, proc/sysfs, TTY/UART, NET, PACKET, I2C, REGMAP_I2C, REGMAP_IRQ, MFD_CORE, MFD_RK8XX, MFD_RK8XX_I2C and MODULES.
4. Forbidden kernel configuration remains absent: STMMAC, Rockchip DWMAC, MDIO, PHYLIB, RTL8211F, RK808 regulator, PWRKEY child, wireless and Bluetooth.
5. DTB model/compatible are Panther X2/RK3566 and RK809, GMAC1, MDIO and PHY nodes remain disabled.
6. BusyBox is AArch64 and statically linked; required applets exist; the init script passes BusyBox ash syntax validation.
7. Initramfs round-trip extraction preserves the exact init and BusyBox.
8. GPT/ext4 layout, embedded JP U-Boot proper readback, read-only remount and payload hashes.
9. Final artifact SHA256 manifest validates.

No PMIC probe is triggered merely because MFD code is built-in: the RK809 DT node remains disabled. No physical network interface is available: GMAC1/MDIO/PHY remain disabled. Network core and AF_PACKET are built in, but the runtime does not configure addresses/routes or send packets.

## 6. New workflow

- Workflow: `.github/workflows/package-panther-x2-g2-runtime.yml`
- Trigger: manual `workflow_dispatch`
- Artifact name: `panther-x2-project-a-g2-runtime-PREPARE-ONLY`
- Intended outputs: PREPARE-ONLY compressed 2 GiB TF image, standalone Image/DTB/uInitrd/boot script/initramfs/BusyBox, final kernel config, System.map/vmlinux debug references, input lock, runtime manifest, logs and SHA256 inventory.
- Retention: 30 days.

The workflow has been committed but has **not yet been run**. Therefore the runtime package is not yet built, not yet validated as an assembled image, and not authorized for physical media.

## 7. Stage boundary after packaging

The safe runtime package retains RK809 MFD code in the kernel but keeps the RK809 node disabled. This is intentional: it gives us a stable, reproducible base without PMIC side effects.

The next steps are:
1. Run the PREPARE-ONLY packaging workflow and inspect every gate and artifact.
2. Archive the final runtime manifest and all hashes.
3. Separately complete the G2 stock-probe static side-effect review and submit the exact PMIC write/IRQ side-effect list and stop conditions.
4. Only after that review, ask for explicit authorization for a dedicated PMIC-enabled DTB variant and a single controlled G2-PROBE run.

No G2-PROBE, regulator activation, IO-domain activation, GMAC enable, AF_PACKET physical send, TF write or Panther X2 boot is authorized by this packaging preparation.

## 8. Status

- G2-B build-only: **PASS**.
- B1 BusyBox/U-Boot support artifact identity: **verified**.
- New G2 runtime init/boot scripts: **committed**.
- G2 runtime packaging workflow: **committed; awaiting manual Actions run**.
- Runtime image build and offline artifact audit: **PENDING**.
- G2-PROBE: **HOLD / NOT AUTHORIZED**.
- Physical media write / Panther X2 boot: **NOT AUTHORIZED**.
