# Panther X2 R1 initramfs defect correction and repackaging gate

Date: 2026-11-26

## Scope

Correct the known BusyBox `[` applet dependency in the R1 boot initramfs before any TF-card runtime test. This is a packaging-only change. It does not rebuild or alter the frozen R1 kernel, kernel configuration, modules, DTB, U-Boot proper, or bootargs. No physical device or storage medium was accessed.

## Defect confirmed

The previous R1 package workflow copied `work/b1/output/uInitrd` unchanged. The frozen B1 `/init` script contains conditional tests such as `[ -r /proc/device-tree/model ]`, but the B1 BusyBox applet allowlist does not enable the `[`/test applet and the initramfs assembly only creates links for `ash sh mount mkdir cat uname dmesg tail`. Thus the package could pass static image/filesystem checks while failing at runtime with `[ : not found`.

This is a B1 userspace/initramfs defect. It does not invalidate the R1 kernel Image or the static kernel Kconfig audit, but the old package must not be used for the next runtime stage.

## Correction committed

- New R1-only init script: `scripts/panther-x2-r1/init`.
- The R1 script avoids the missing `[`/test applet entirely and retains the RAM-only, no-persistent-mount behavior.
- The package workflow now builds a fresh R1 initramfs using the already-built static BusyBox from the frozen B1 artifact; it does not rebuild BusyBox or the R1 kernel.
- The initramfs explicitly creates and validates links for `ash sh mount mkdir cat uname dmesg tail`.
- CI validates the script syntax with the ARM64 BusyBox `ash -n`, rejects `[` and `test` command dependencies, round-trips the cpio archive, compares the embedded `/init` byte-for-byte with the repository source, and verifies the executable mode and shell links.
- The assembled TF image must contain the newly generated `work/output/uInitrd`; the read-only partition verification compares the packaged uInitrd with the generated file and records its SHA256.

## Preserved inputs and boundaries

- R1 kernel Image SHA256 remains `63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`.
- Panther DTB SHA256 remains `7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`.
- JP-TvBox U-Boot proper remains the verified B1 asset; no TF IDB/SPL is added.
- Existing bootargs, load addresses, GPT layout, and hybrid boot-chain dependency remain unchanged. Existing eMMC SPL is still required.
- GMAC1/MDIO/PHY remain disabled in R1. This image is not an Ethernet TX test image.
- SN64G, SU08G and eMMC have not been accessed or modified.

## CI acceptance status — PASS

Corrected packaging run: [45736650568](https://github.com/njosd/panther-x2-armbian/actions/runs/45736650568), job `139631401388`. All 11 substantive steps completed successfully, including ARM64 BusyBox validation, fresh initramfs generation, image assembly, read-only partition verification, and artifact upload.

- Artifact: `panther-x2-r1-hybrid-PREPARE-ONLY`, ID `15079555836` (expires 2026-12-26).
- Artifact ZIP SHA256: `44b0d27da386e53177db3a6967bb2861296f4d932da875a25c2efa8b3fd6676a`.
- New R1 `uInitrd` SHA256: `ba1fbfe131b65d97c738176b20cdbf2c2279e77f9220eae2c6a37f25dc7cb2f0`.
- R1 `/init` SHA256: `3d20842d394e7b088aa0430dfdf79aa096be9bab6d05b4bfbc284f3281152ea5`.
- Full uncompressed TF image SHA256: `708a95cb120247e6d30f4b22095a4bc27132d58a69fe37c71c84afee09fcde7e`.
- The new uInitrd is an AArch64 gzip RAMDisk, data size 495,228 bytes. CI parsed `/init` with the actual ARM64 BusyBox ash, rejected `[`/`test` dependencies, round-tripped the cpio archive, compared embedded `/init` byte-for-byte, and verified executable mode and `ash`/`sh` links.
- The image's `uInitrd` was compared byte-for-byte with the freshly generated file and its SHA256 matched. The ext4 partition passed `e2fsck -fn`; GPT and U-Boot payload checks passed.
- R1 kernel Image, DTB, U-Boot proper, bootargs, load addresses and GPT geometry remain unchanged.

The previous artifact from run `45735410519` (ID `15078283453`) is superseded and must not be used. The corrected artifact is **packaging-verified and eligible for the next separately authorized TF-card stage**, but has not been boot-tested on Panther X2. This is not proof of runtime success. The hybrid boot dependency remains: existing eMMC SPL is required; the TF image does not contain an independent SPL/IDB.

No physical TF card or eMMC was accessed or written. This report does not authorize writing SU08G, SN64G, or eMMC.
