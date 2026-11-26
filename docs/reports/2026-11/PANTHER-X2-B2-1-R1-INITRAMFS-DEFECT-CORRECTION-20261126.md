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

## CI acceptance status

The source changes are committed, but the corrected packaging workflow has not yet been run. Therefore the corrected uInitrd and regenerated full TF image are **not yet validated**. The previous artifact `panther-x2-r1-hybrid-PREPARE-ONLY` remains superseded and must not be used for runtime testing.

Run `.github/workflows/package-panther-x2-r1-tf-image.yml` from `main` with:
- `r1_run_id=45611898629`
- `b1_run_id=45328201244`

Only after the workflow succeeds and the new artifact's initramfs and image hashes are reviewed can the corrected package be considered ready for a separately authorized TF-card operation. This report does not authorize writing SU08G or any other storage.
