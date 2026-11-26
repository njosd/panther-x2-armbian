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


## Post-packaging Panther X2 runtime result — 2026-11-26

The corrected image was subsequently written by the user to the dedicated 8GB SU08G TF card using balenaEtcher and booted on Panther X2. The 64GB SN64G comparison card and eMMC were not written or intentionally modified.

### Observed runtime evidence

- Existing eMMC SPL successfully handed off to JP-TvBox U-Boot proper on the TF card.
- U-Boot loaded the R1 Kernel, uInitrd and Panther X2 DTB from the TF boot partition and passed control to Linux.
- Linux identified the machine as Panther X2, initialized four CPUs and recognized approximately 4GiB RAM.
- Linux executed `/init`; the RAM initramfs root was active and an interactive BusyBox v1.37.0 ash prompt `(panther-x2-r1-network-core) #` appeared.
- The boot log contains repeated `/init: printf: not found` errors (including script lines 33, 35 and 38). The R1 `/init` source calls `printf`, but the package workflow's BusyBox applet/link allowlist omitted `printf`. This is a packaging omission, not evidence of a kernel boot failure.
- Deferred-probe messages for USB, MMC/PMIC regulators and Rockchip power domains were also logged. They are retained as observations and are not promoted to fatal failures by this report.
- No evidence in this log indicates that persistent storage was mounted or written by Linux.

### Runtime status and limits

**Verified:** kernel handoff and execution; Panther X2 DTB recognition; four-CPU/4GiB memory enumeration; initramfs root execution; BusyBox ash interactive shell availability.

**Defect confirmed:** the R1 initramfs does not provide the `printf` command required by the current `/init`. The diagnostic/status output is therefore incomplete. The root cause is the package workflow's applet/link allowlist, not a missing kernel feature.

**Not verified:** completion of every `/init` diagnostic; physical Ethernet TX/RX or any network connectivity. R1 intentionally keeps GMAC1/MDIO/PHY disabled and is not an Ethernet test image.

### Minimal correction

The R1 packaging workflow was amended to include `printf` in the BusyBox applet link allowlist and to assert that the extracted initramfs contains `bin/printf -> busybox`. No change was made to the R1 `/init` script, kernel Image, kernel configuration, DTB, U-Boot proper, bootargs, load addresses, GPT geometry or storage layout.

The workflow change is committed as `4efd7c7e56abfbc43a8309b4d797cd4cc5c40891`. This fixes the identified packaging omission at source level. The subsequent CI package run and second target-hardware boot are recorded below; the corrected /init path is now runtime-verified.

### Safety boundary

The observed boot used the user-authorized SU08G TF card. SN64G and eMMC remain outside the write scope. The boot log does not establish that Linux accessed persistent storage; no storage write is reported. This record does not authorize further storage writes or eMMC changes.

Source: user-provided UART boot log, full 1,567-line record reviewed in this conversation.


## CI repackaging result — 2026-11-26

Workflow run: `45739520034`; job: `139640803045` (`package-r1`); checked-out source revision: `f6a98bb2bf48a36e2b4598b2ce815ce2516855bc`.

**Result: SUCCESS.** All 11 substantive job steps completed successfully. The log explicitly confirms:
- BusyBox `--list` contains `printf`;
- the packaging loop creates the `printf` applet link;
- the extracted initramfs validation passes `readlink .../bin/printf = busybox`;
- the final image payload is read back and checked, the compressed image passes `gzip -t`, and decompression reproduces the raw image SHA256.

Published artifact:
- Name: `panther-x2-r1-hybrid-PREPARE-ONLY`
- Artifact ID: `15079994261`
- ZIP size: `26,716,923` bytes
- ZIP SHA256: `9b0f4d4310dad56b866934b0b46832079ae6e6a02073d376351ae8fab3d7852b`
- Raw image SHA256: `e6744be80273f1cb0a6a40b4d6ed46e82361751a359305d538d7578b1892ec44`
- Artifact expiry: 2026-12-26

This closes the source-level applet correction and CI packaging verification. **This CI record alone does not prove runtime execution of `/init` after the fix.** The second target-hardware boot and runtime network-core checks are recorded in the final section below. R1 remains PREPARE-ONLY; GMAC1/MDIO/PHY are disabled, so Ethernet TX/RX remains outside this test.

Source: GitHub Actions run 45739520034, job 139640803045 and its uploaded artifact metadata.


## Corrected R1 second boot and network-core runtime acceptance — 2026-11-26

**Overall result: PASS for R1 boot/initramfs and the runtime checks within the R1 network-core scope.** This is not a physical Ethernet TX/RX result.

### Corrected runtime boot

The user booted the corrected image from the authorized SU08G 8GB TF card. The UART record confirms:
- Linux 6.18.63+ #1 SMP Wed Nov 25 12:42:00 UTC 2026, AArch64, reached the interactive R1 shell.
- /init completed sufficiently to present the (panther-x2-r1-network-core) # prompt; the previous printf: not found defect did not recur.
- Root is RAM-backed rootfs; proc and sysfs are mounted. No persistent filesystem mount is shown.
- /proc/net/dev exists and lists only lo.
- /sys/class/net contains only the lo virtual interface symlink.
- /proc/net/packet exists and exposes the PF_PACKET socket table; it contains only the header, consistent with no packet socket currently open.
- Kernel log explicitly states NET: Registered PF_PACKET protocol family.

### R1 runtime acceptance matrix

| Item | Result | Evidence / boundary |
|---|---|---|
| Linux 6.18.63 runtime | PASS | UART uname -a |
| Panther R1 interactive shell | PASS | R1 ash prompt; corrected printf available through the initramfs applet link |
| RAM-only root and proc/sysfs | PASS | mount output |
| Network device statistics interface | PASS | /proc/net/dev |
| Network sysfs inventory | PASS | /sys/class/net contains only lo |
| PF_PACKET protocol family registration | PASS | NET: Registered PF_PACKET protocol family in dmesg |
| PF_PACKET socket table | PASS | /proc/net/packet readable; no socket open during this observation |
| Physical Ethernet interface | Correctly absent | GMAC1/MDIO/PHY are intentionally disabled in R1 |
| AF_PACKET socket create/send | NOT TESTED | No socket test program was run |
| Physical Ethernet TX/RX | NOT TESTED / OUT OF SCOPE | R1 has no GMAC/MDIO/PHY path enabled |

### Diagnostic command note

The first grouped inspection attempted to use echo, which was not linked as a BusyBox applet and produced /bin/sh: echo: not found. This did not affect kernel or network-core operation. The follow-up used /bin/busybox echo and completed the sysfs, packet-table and network-device checks. No initramfs change is warranted solely to add the optional echo applet.

### Remaining observations

The boot log contains deferred-probe messages for USB, MMC/PMIC regulators and Rockchip power domains, as well as unrelated subsystem initialization messages. They did not prevent the R1 shell or the network-core checks and are not treated as R1 acceptance failures. No new investigation is authorized or required by this result.

### Safety and storage boundary

The runtime test used the user-authorized SU08G TF card. SN64G and eMMC were not written. The observed Linux mount table shows RAM root, procfs and sysfs only; no persistent filesystem mount is evidenced. This report does not authorize any further storage write or eMMC modification.

### R1 closeout and next stage

R1 is accepted as **network-core component/runtime preparation passed**, not as a physical network test. Preserve the existing R1 image and evidence; do not rebuild or rewrite the card for this acceptance.

Proceed only to the next planned R2 item after its own plan/source/config review and the required explicit operation authorization. Do not skip R2–R6, do not restore GMAC/MDIO/PHY early, and do not perform the R7 TX-first test until all preceding stage gates are independently passed.
