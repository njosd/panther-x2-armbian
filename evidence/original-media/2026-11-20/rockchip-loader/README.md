# Original Rockchip Loader binaries — 2026-11-20

This directory is reserved for the three original binary files found on the user's external USB drive.

Please upload the files unchanged, preserving these exact filenames:

- `MiniLoaderAll.bin`
- `rk356x-MiniLoaderAll.bin`
- `rk356x_spl_loader_ddr1056_v1.10.111.bin`

## Source and observed fingerprints

Original source: external USB drive, under `/Volumes/Untitled/黑豹x2/` (the latter two files were found in `黑豹x2/armbian/bootloader/`).

| File | Size observed | SHA256 observed | Embedded DDR string | Boot1 build-date string |
|---|---:|---|---|---|
| `MiniLoaderAll.bin` | 442 KiB | `ab62386a8868b01516b560451082fbdb6342b16e850a0622577b538dd2b10d39` | `DDR Version V1.09 20210630` | `Jun 18 2021` |
| `rk356x-MiniLoaderAll.bin` | 444 KiB | `1cdd418032195210f191445ed96e2da5ea83d2cfe880c912ebec635839d76542` | `DDR Version V1.10 20210810` | `Sep 13 2021` |
| `rk356x_spl_loader_ddr1056_v1.10.111.bin` | 442 KiB | `d7cfd619870cebe5a69e365796709d5ba1fc0294a84ae63357a9d189074dc100` | `DDR Version V1.10 20210810` | `Dec 9 2021` |

All three were observed to begin with the `LDR ` signature. These are user-reported measurements from macOS terminal output; verify each uploaded object's SHA256 and byte size before treating the repository copy as an exact archival copy.

## Handling rules

- Preserve each uploaded binary byte-for-byte; do not rename, patch, repackage, or replace it with another build.
- After upload, independently verify SHA256 and file size against the table above.
- Keep all three versions. Do not infer interchangeability from matching DDR strings.
- The files are loader/SPL-family artifacts; this directory does not assert that any one is the currently running U-Boot proper.
- Do not flash these files to eMMC, SD, or any device as part of archival or analysis work.
