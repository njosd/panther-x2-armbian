# Panther X2 B1 Run #73 — Manual U-Boot Boot and UART Results

- Date: 2026-11-24
- Workflow run: [Run #73](https://github.com/njosd/panther-x2-armbian/actions/runs/45309219886)
- Source commit: `aee4e352a15d636cbc484f56819c6e59474dfd9f`
- Kernel: Linux `6.18.63`
- Target media: dedicated SU08G 8 GB TF card; eMMC and the 64 GB reference TF card were not targets.
- Image artifact: [PREPARE-ONLY artifact](https://github.com/njosd/panther-x2-armbian/actions/runs/45309219886/artifacts/14884367233)
- Decompressed image: `panther-x2-b1-hybrid-PREPARE-ONLY.img`
- Expected and user-verified SHA-256: `e4f8323d56a5629f9a238cd6106fc626d45fb6ac884f33c384f49e17ef99ad44`
- Expected image size: 2 GiB (2147483648 bytes)
- Test result: manual U-Boot handoff reached interactive BusyBox shell; B1 boot core criteria passed, with a BusyBox applet packaging defect discovered afterward.

> Evidence scope: this report preserves the observed commands, console output excerpts, measurements and conclusions available from the 2026-11-24 test conversation. It is a structured test record, **not a byte-for-byte raw UART capture**. The complete raw serial log was not available as a separate file when this report was prepared. Do not cite excerpts below as a complete kernel log.

## 1. Boot chain and U-Boot session

The tested chain was the existing mixed boot path: eMMC SPL → TF-card JP U-Boot proper → B1 Linux files on TF. The user interrupted automatic U-Boot boot and entered the prompt.

Known U-Boot environment values already established by earlier tests:
- `devtype=mmc`
- `devnum=1`
- `kernel_addr_r=0x00280000`
- `ramdisk_addr_r=0x0a200000`
- `fdt_addr_r=0x0a100000`

DRAM ranges reported by the known U-Boot baseline:
- `0x00200000 - 0xf0000000` (size `0xefe00000`)
- `0x1f0000000 - 0x200000000` (size `0x10000000`)

### 1.1 TF identity and partition

Command: `mmc dev 1`

Observed:
```
switch to partitions #0, OK
mmc1 is current device
```

`mmc info` identified:
- Controller: `dwmmc@fe2b0000`
- Card name: `SU08G`
- SD 3.0, High Capacity, 4-bit, 52 MHz
- Capacity: 7.4 GiB

`mmc part` reported a GPT/EFI partition map:
- Partition 1 label: `PANTHER_BOOT`
- Start LBA: `0x00008000`
- End LBA: `0x003ff7ff`
- Type GUID: `0fc63daf-8483-4772-8e79-3d69d8477de4`

`ls mmc 1:1 /` showed:
- `Image` — 30,849,536 bytes
- `uInitrd` — 484,447 bytes
- `boot.scr` — 1,413 bytes
- `boot.cmd`
- `TEST-INFO.txt`
- `dtb/`

`ls mmc 1:1 /dtb/rockchip` showed `rk3566-panther-x2.dtb` — 116,254 bytes.

## 2. Exact manually entered boot sequence

The following commands were entered at the U-Boot prompt. No `saveenv` was run; the boot arguments were temporary for this boot.

```text
mmc dev 1
load mmc 1:1 0x00280000 /Image
load mmc 1:1 0x0a200000 /uInitrd
load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init'
booti 0x00280000 0x0a200000 0x0a100000
```

Observed successful loads:
```
30849536 bytes read in 2588 ms (11.4 MiB/s)
484447 bytes read in 48 ms (9.6 MiB/s)
116254 bytes read in 27 ms (4.1 MiB/s)
```

## 3. U-Boot and kernel handoff evidence

U-Boot identified the initramfs as:
```
Image Type: AArch64 Linux RAMDisk Image (gzip compressed)
Data Size: 484383 Bytes
Verifying Checksum ... OK
```

Device-tree handoff:
```
Booting using the fdt blob at 0x0a100000
Using Device Tree in place ...
```

U-Boot emitted framebuffer/logo reservation warnings:
```
can't found rockchip,drm-logo, use rockchip,fb-logo
WARNING: could not set reg FDT_ERR_BADOFFSET.
failed to reserve fb-loader-logo memory
```
These warnings did not prevent Linux from starting. They were not investigated because display/logo support is outside B1's boot-baseline acceptance scope.

Kernel identity and machine:
```
Linux version 6.18.63 ...
Machine model: Panther X2
Kernel command line: console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init
```

## 4. Kernel and RAM-root results

Observed:
- CPU0 through CPU3 came online.
- `SMP: Total of 4 processors activated`.
- Kernel memory map included both DRAM banks:
  - `0x00200000 - 0xf0000000`
  - `0x1f0000000 - 0x200000000`
- Kernel reported `Memory: 3746692K/4192256K available`.
- `/proc/meminfo` reported `MemTotal: 4019516 kB`.
- `Trying to unpack rootfs image as initramfs...`
- `Freeing initrd memory: 468K`
- `psci_checker: Hotplug tests passed OK`
- `Run /init as init process`
- UART console `ttyS2` remained active.

The init script mounted procfs and sysfs. The observed mount list was:
```
rootfs / rootfs rw,size=1875700k,nr_inodes=468925 0 0
proc /proc proc rw,relatime 0 0
sysfs /sys sysfs rw,relatime 0 0
```

This confirms the active root was the RAM-backed initramfs/rootfs and no persistent filesystem was mounted in the observed mount list.

## 5. Init and BusyBox result

The init script ran and eventually reached:
```
BusyBox v1.37.0 (2026-11-24 02:42:20 UTC) built-in shell (ash)
(panther-x2-b1-clean) #
```

However, the init script printed command-not-found errors for `printf` and `[`. Follow-up inspection:
- `busybox --list` showed only: `ash cat dmesg mkdir mount sh tail uname`.
- `busybox printf ...` returned `printf: applet not found`.
- `busybox test ...` returned `test: applet not found`.
- shell `echo` was also unavailable in the tested invocation.
- `busybox ls` returned `ls: applet not found`.

The `/init` file itself calls `printf`, `[`, `mkdir`, `mount`, `uname`, `cat`, `dmesg`, `tail`, and finally `exec /bin/sh -i`. The built BusyBox configuration and initramfs symlink list did not provide all commands expected by this script.

This is a confirmed BusyBox applet/configuration and initramfs packaging mismatch, not a Kernel/DTB boot failure. The later repository fix adds the missing applets and verification. It has not yet been validated by a subsequent build and physical boot.

## 6. Non-blocking kernel messages observed

The following messages appeared but did not prevent the interactive shell:
- Rockchip DRM: `No available vop found for display-subsystem.`
- USB PHY runtime-PM usage-count underflow warnings.
- SCMI malformed reply warning.
- PSCI checker noted cpuidle unavailable and suspend tests could not be performed; CPU hotplug tests passed.

These are recorded for traceability, not classified as B1 boot blockers. Display, USB PHY, SCMI and suspend behavior are not B1 acceptance targets.

## 7. B1 acceptance assessment

| Requirement | Result | Evidence |
|---|---|---|
| TF card identified as the intended SU08G | PASS | `mmc info` |
| Kernel Image loaded from TF | PASS | U-Boot byte count and successful `booti` |
| Panther X2 DTB loaded | PASS | exact DTB path, size, machine model |
| initramfs loaded and unpacked | PASS | legacy RAMDisk checksum OK; initramfs unpack message |
| Linux 6.18.63 starts | PASS | kernel banner and subsequent kernel output |
| Four CPU cores online | PASS | SMP reports four processors |
| Approximately 4 GiB DRAM recognized | PASS | memory map and MemTotal |
| RAM root active, no persistent filesystem mounted | PASS | `/proc/mounts` |
| `/init` executed and interactive shell reached | PASS WITH APPLET DEFECT | command-not-found messages, BusyBox ash prompt |
| Complete `/init` diagnostics execute cleanly | FAIL | missing `printf`, `[` and other applets |
| Static BusyBox | CI-VERIFIED, NOT INDEPENDENTLY RUNTIME-VERIFIED | build verifier checks AArch64 ELF and absence of INTERP |
| Automatic unattended U-Boot discovery and boot | NOT TESTED | this run used manual U-Boot commands |

### Overall conclusion

**B1's central manual boot objective passed:** the TF-loaded Linux 6.18.63 kernel, Panther X2 DTB and initramfs booted into a RAM-backed root and reached an interactive BusyBox shell. The test exposed a concrete BusyBox applet packaging defect, which is being corrected. Automatic unattended U-Boot startup is a separate next validation and must not be marked passed based on this manual boot.

## 8. Safety and scope

- No `saveenv` was executed.
- The test used the dedicated SU08G TF card.
- No eMMC write was part of this test.
- No network configuration or network test was performed.
- Wireless and Bluetooth were outside the B1 scope.
- The kernel's display/USB/SCMI warnings were not pursued because they did not block the B1 acceptance target.

## 9. Related records

- Run #73 Actions: https://github.com/njosd/panther-x2-armbian/actions/runs/45309219886
- Run #73 PREPARE-ONLY artifact: https://github.com/njosd/panther-x2-armbian/actions/runs/45309219886/artifacts/14884367233
- Pre-B1 U-Boot checkpoint (historical preboot state, not this successful boot result): [PANTHER-X2-B1-UBOOT-PREBOOT-CHECKPOINT-20261122.md](./PANTHER-X2-B1-UBOOT-PREBOOT-CHECKPOINT-20261122.md)
- Current boot script source: [boot.cmd](../../scripts/panther-x2-minimal-initramfs/boot.cmd)
- Current B1 workflow: [build-panther-x2-b1-clean-ram.yml](../../.github/workflows/build-panther-x2-b1-clean-ram.yml)

## 10. Evidence completeness / follow-up

This report preserves the available session evidence, but the original complete UART serial capture is not attached. If the original serial terminal transcript is later exported, add it under `evidence/boot/` with an unambiguous filename such as `2026-11-24-panther-x2-b1-run73-uart-raw.log`, retain it unchanged, and record its SHA-256 here. Do not replace this structured report with a reconstructed log.
