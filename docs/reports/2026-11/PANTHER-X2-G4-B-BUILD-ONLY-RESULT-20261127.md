# Panther X2 G4-B IO-domain build-only result (2026-11-27)

## 1. Result

**G4-B: PASS (build-only). G4-P: HOLD / NOT AUTHORIZED.**

GitHub Actions run: [45997129528](https://github.com/njosd/panther-x2-armbian/actions/runs/45997129528)  
Job ID: `140499220529`  
Workflow commit: `8a5326c3322f659fdd865bd64a8c6c00f2bbfaf4`  
Branch at execution: `g4-iodomain-build-only`  
Artifact: `panther-x2-g4-iodomain-build-only` (ID `15196608755`, 211,500,487 bytes)  
Artifact ZIP SHA-256: `f374a900c20a9090e74d7ac668721d8cb6a9317fe15c0f998c32aaecd77361fa`

The Actions run completed with conclusion `success`. All required steps passed: restore and verify frozen G3 artifact; fetch pinned source and apply audited R1 compatibility patch; merge the G4 config delta; build Linux Image; audit object/symbols and isolated DTB; save incremental cache; upload artifact. The diagnostics upload was correctly skipped because the build succeeded.

## 2. Reproducibility and artifact integrity

- Kernel: Linux `6.18.63`
- Source: `ophub/linux-6.18.y`
- Pinned source commit: `aee4e352a15d636cbc484f56819c6e59474dfd9f`
- G3 reference run: `45984035650`
- G3 Image SHA-256: `d1830f649e3bfa789fec3589c2ef16b1e46465846c6bb150e666f8df4c610a61`
- G3 config SHA-256: `bfcadc0626f0a96b369e1475accf0efcedc9adaae8464ea85291c4afa12d9794`
- G3 DTB SHA-256: `9364c6d7aadddb8520388418e8db570e0b4020a38c5ceb8acbd2343165bb5209`
- G4 config SHA-256: `c990c913b283a7042a81be12369886e1faa95bbf5b2cc031fd9e1155a4357be2`
- G4 Image SHA-256: `9e1250fa0deae9cfc70bd59f006dcd49e9719bc9a070aeca21030475529f5362`
- G4 DTB SHA-256: `41253336c0e69b7431e0d095573724c087734bb310143e1848d8da7639a7c9be`

The uploaded ZIP digest was independently recomputed and matched the Actions artifact digest. The archive contains 21 files. Every entry in `output/SHA256SUMS` independently passed checksum verification. The workflow's own `sha256sum --check` also passed for all packaged outputs.

The config diff contains exactly one change:
`# CONFIG_ROCKCHIP_IODOMAIN is not set` → `CONFIG_ROCKCHIP_IODOMAIN=y`.

The kernel build log contains 3,994 lines; a scan found no compiler warning, error, failed target, or undefined-reference message. The build reached `OBJCOPY arch/arm64/boot/Image` and exited normally.

## 3. Object and symbol audit

The artifact contains `drivers/soc/rockchip/io-domain.o`. Its symbol table includes:
- `rockchip_iodomain_probe`
- `rockchip_iodomain_write`
- `rk3568_iodomain_write`
- `rockchip_iodomain_driver`
- `rockchip_iodomain_notify`

Dependency object hashes were recorded for:
- `io-domain.o`: `e5f50e5c08dd4d7ed3ae443f808409be8683959819390c735dfe4e65326886a0`
- `rk808-regulator.o`: `dcd77bdc1b87bedda24d55cc0ed4515a273ad1ef57a50e8903bf3eb1af3f1a07`
- `regulator/core.o`: `3f940eb3b2d2636978881d071d74772df6408738bc077e2db90986dfb8294f86`

## 4. DTB isolation audit

The artifact DTB reports:
- Panther X2 model; RK809 node `okay`.
- IO-domain node `okay`, with 9 declared supplies.
- eMMC SDHCI, TF SDMMC0, SDIO SDMMC1, GPU and SARADC disabled.
- GMAC1, MDIO and PHY disabled.

This is an intentionally isolated G4 candidate. **It is suitable as a RAM-only G4-P candidate, not as the final DTB for booting a root filesystem from TF.** Linux TF SDMMC0 is disabled in this DTB. After G4-P is separately authorized and validated, a further build-only DTB variant must restore only TF SDMMC0 while keeping eMMC disabled before moving to the complete SU08G TF userspace. Do not conflate U-Boot reading the kernel/initramfs from TF with Linux being able to mount a TF rootfs after kernel handoff.

## 5. Explicit non-claims and safety boundary

The manifest states:
- `hardware_access=none`
- `pmu_grf_access=none`
- `pmic_register_access=none`
- `physical_media_writes=none`
- `runtime_probe=not_executed`
- `runtime_authorization=not_granted`
- `ABCD=NOT_EXECUTABLE`

Therefore this result proves a reproducible build, Kconfig delta, object/symbol presence, DTB isolation and artifact integrity only. It does not prove IO-domain runtime probe, regulator voltage, physical rail state, GRF write success, hardware function or network operation.

Project A remains TF-only. SU08G is the sole experimental storage medium; SN64G remains frozen. No eMMC write, mount, install or modification is authorized or required by G4-B. G4-P remains HOLD / NOT AUTHORIZED and requires a separate risk/write-range/readback/stop-and-rollback plan and explicit user authorization. This report does not grant that authorization.

## 6. Next controlled sequence

1. Record G4-B PASS and retain this exact artifact as a frozen candidate.
2. Keep G4-P on HOLD until the complete runtime side-effect and rollback plan is reviewed and the user explicitly authorizes it.
3. If G4-P passes, create a separate TF-rootfs DTB build-only candidate that enables TF SDMMC0 only and keeps eMMC disabled; independently audit its config/DTB/hash.
4. Build and validate the complete Linux test userspace on SU08G only.
5. Continue subsequent hardware/network stages on SU08G, one variable at a time.

