# Panther X2 Project-A G4-P0 RAM runtime PREPARE-ONLY package (2026-11-28)

## 1. Result

**G4-P0 runtime packaging: PASS / PREPARE-ONLY.** The G4-P0 kernel Image and DTB were combined with the already frozen G3 boot-support assets (static BusyBox and JP-TvBox U-Boot proper), a dedicated G4-P0 RAM initramfs, and the established SU08G GPT/ext4 layout. The package was built entirely on a GitHub Actions runner.

- Workflow: `.github/workflows/package-panther-x2-g4-p0-runtime.yml`
- Run: [46116353755](https://github.com/njosd/panther-x2-armbian/actions/runs/46116353755)
- Commit: `8079314c0789b45f9f5e6648dac06a0f98312b48`
- Job: `140890962190` — completed / success
- Artifact: `panther-x2-project-a-g4-p0-runtime-PREPARE-ONLY`
- Artifact ID: `15251553200`
- Artifact size: 26,387,518 bytes
- GitHub artifact ZIP digest: `sha256:c3ad1ee99a0878d012c63bda060d2d46746d595f26c87e8ce56770f2ac915226`
- Downloaded ZIP SHA256 independently recomputed: same value.

## 2. Frozen inputs

G4-P0 build-only input (run `46091659151`, artifact `15242113092`):
- Image SHA256: `b34b8faaa34bcb843d82f11423489b434c1e2f329fedab1d81754fd192723090`
- DTB SHA256: `c967aff4bb99748828fdf083a8e1701b915966e47c6828375399bef5e0048ff8`
- kernel.config SHA256: `c990c913b283a7042a81be12369886e1faa95bbf5b2cc031fd9e1155a4357be2`

G3 runtime boot-support input (run `45996817932`, artifact `15196482298`):
- Static BusyBox SHA256: `2d77cb64f5ab5ca33efae040083abe31912ab02677dd21c1b79ade6ed0e98b15`
- JP-TvBox U-Boot proper SHA256: `a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce`

The packaging workflow checked both source artifacts' internal SHA256 inventories, the fixed G4 Image/DTB/config hashes, BusyBox static AArch64 identity, Panther X2 DTB model, IO-domain child status, absence of all nine IO-domain supply properties, and the required disabled peripheral nodes.

## 3. Runtime package contents and validation

The package includes:
- G4-P0 Linux 6.18.63 Image and Panther X2 DTB;
- G4-P0 kernel.config and build/isolation manifests;
- G3 frozen static BusyBox and JP-TvBox U-Boot proper;
- dedicated `init`, `capture-g4-p0.sh`, `boot.cmd`;
- gzip cpio initramfs and legacy U-Boot `uInitrd`;
- compiled U-Boot `boot.scr`;
- SU08G-sized GPT/ext4 PREPARE-ONLY image compressed with zstd;
- per-file checksum inventory and runtime manifest.

Validation:
- BusyBox `ash -n` syntax checks for both G4-P0 scripts: PASS.
- Initramfs cpio/gzip round-trip and file comparisons: PASS.
- Legacy AArch64 gzip uInitrd header: PASS.
- U-Boot ARM script image header: PASS.
- GPT partition layout and U-Boot proper raw-LBA readback: PASS.
- ext4 `e2fsck -fn`: no filesystem errors.
- Read-only remount and checks of Image, uInitrd, boot.scr, boot.cmd, TEST-INFO and DTB: PASS.
- All 22 entries in artifact `output/SHA256SUMS`: PASS.
- Downloaded artifact ZIP digest: matches GitHub artifact digest.
- Independently streamed zstd decompression: 7,948,206,080 bytes; raw image SHA256 matches manifest.

## 4. Image identity and layout

- Raw image: 7,948,206,080 bytes.
- Raw image SHA256: `99caff75dd4c49ba229c3453f8bc82a1e904c0b73a3f641bc1ae904e44a501d8`
- zstd image SHA256: `d3d61efaa6576a8e53f39f147d8692339c03239e71c5e37376fe89e82194f742`
- zstd file: `output/panther-x2-project-a-g4-p0-runtime-PREPARE-ONLY.img.zst`
- GPT total sectors: 15,523,840 (512 bytes/sector).
- PANTHER_BOOT ext4: LBA 32768 through 15523806.
- JP-TvBox U-Boot proper: raw LBA 16384.
- Boot chain: existing eMMC SPL → TF JP-TvBox U-Boot proper → TF Image/uInitrd/DTB → RAM initramfs.
- U-Boot load addresses: Image `0x00280000`, uInitrd `0x0a200000`, DTB `0x0a100000`.
- Kernel bootargs: `console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init regulator_ignore_unused`.

The runner's e2fsck/sgdisk output includes a non-fatal alignment caution: the partition end is not on a 2048-sector boundary. GPT verification and filesystem check passed; this mirrors the previously used G3 SU08G capacity/layout. Keep this as a documented compatibility note, not as a claim of a filesystem error.

## 5. Runtime observation scope

The G4-P0 initramfs writes observations only to RAM path `/run/g4-p0`. It records:
- runtime identity, command line and mounts;
- IO-domain DT node status and absence of all nine supply properties;
- RK809 and other peripheral DT status;
- expected IO-domain platform device enumeration and driver symlink;
- deferred-probe list and dmesg.

The collector mounts procfs, sysfs and debugfs as needed. It does not write sysfs attributes, access I2C directly, read raw PMUGRF/PMIC registers, inspect regmap register files, or issue selector reads/writes. It only lists the debugfs regmap directory. The runtime shell asks for a second capture after 12 seconds to observe settled deferred-probe state.

## 6. Safety boundary / what is not proven

This artifact is explicitly **PREPARE-ONLY**:
- No Panther X2 device was accessed or booted.
- No physical TF, SN64G or eMMC was written.
- The image was created and mounted only on the cloud runner.
- Runtime IO-domain child enumeration and driver binding were subsequently verified in one separately authorized RAM-only boot; see `PANTHER-X2-G4-P0-RUNTIME-BINDING-OBSERVATION-20261128.md`. PMUGRF regmap acquisition is supported by successful IO-domain probe/binding, but no selector register read/write was observed.
- No physical rail voltage or selector state was measured.
- Source audit predicts no selector register transaction when all nine supply properties are absent; this is not runtime evidence.
- RK809 regulator provider remains enabled. If booted, its already-known PMIC initialization writes may occur. G3's prior one-session authorization does not authorize this G4-P0 boot.
- The separate one-session runtime authorization was subsequently granted and used; no further boot is authorized by that prior approval.
- G4-P full nine-supply mapping: **NO-GO**.

## 7. Next gate

The single authorized boot has already been completed. The runtime evidence confirms IO-domain child enumeration and driver binding, RK808 regulator binding and regulator class registration. Do not repeat the boot merely to rerun the collector. Do not proceed to full supply mapping or physical voltage testing in this gate.


## 8. Corrected collector package (2026-11-28)

The first target-board session exposed that the collector used `[ ... ]` while the frozen BusyBox build provided `test` but no `[` applet. The collector was corrected in commit `205053232799114ce8ecb15354831900a9db4d0f` by replacing all 14 conditional tests with the existing `test` applet form. No new applet, hardware access, or write operation was introduced.

The path-filtered packaging workflow ran automatically and passed:
- Actions run `46120998151`, run number 2, event `push`, completed / success.
- Job `140905253535`: all steps passed, including BusyBox `ash -n` syntax checks, immutable input checks, image assembly, checksum manifest and artifact upload.
- Corrected PREPARE-ONLY artifact ID `15253991870`, size 26,388,130 bytes, ZIP SHA256 `d0bbc160b5c67899a8423b8858b016da646ea7dccf7dc57521eec3e039f13c69`.
- This was cloud-runner packaging only; no physical device or media was accessed.

The corrected collector therefore has SOURCE + target BusyBox ash syntax + package CI PASS. The new artifact remains PREPARE-ONLY; it does not authorize another hardware boot. The previous manual observations remain the authoritative runtime evidence.
