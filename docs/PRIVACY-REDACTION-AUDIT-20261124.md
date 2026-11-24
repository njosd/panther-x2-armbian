# Public Repository Privacy Audit and Redaction Record

- Audit date: 2026-11-24
- Repository: `njosd/panther-x2-armbian`
- Scope: current default branch working tree; selected project reports, boot evidence, UART logs, and network evidence.
- Purpose: remove device-unique and home-network identifiers while preserving technical evidence.

## Redaction rules applied

- Device MAC addresses: replaced with `[REDACTED-MAC]`.
- Filesystem UUIDs and unique partition GUIDs: replaced with `[REDACTED-UUID]` or `[REDACTED-PARTITION-GUID]`.
- CPU serial numbers: replaced with `[REDACTED-CPU-SERIAL]`.
- Ephemeral build-host identifiers: replaced with `[REDACTED-BUILD-HOST]`.
- Home LAN addresses: host-specific addresses replaced with a non-identifying `192.168.x.*` form.
- Standard partition type GUIDs, public protocol constants, chip identifiers, register addresses, kernel versions, source hashes, and technical event ordering are retained where they are not device-unique.

## Updated documents

- `docs/reports/2026-11/PANTHER-X2-UBOOT-FIT-FDT-EXTRACTION-ISSUE-20261117.md`
- `docs/reports/2026-11/PANTHER-X2-UBOOT-NETWORK-BASELINE-20261122.md`
- `docs/reports/2026-11/PANTHER-X2-NETWORK-LAYERED-VALIDATION-PLAN-20261122.md`
- `docs/reports/2026-11/PANTHER-X2-UBOOT-LINUX-HANDOFF-INVENTORY-20261122.md`
- `docs/reports/2026-11/PANTHER-X2-6.1.65-ORIGINAL-TF-BOOT-ETHERNET-BASELINE-20261124.md`
- `docs/reports/2026-11/PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md`
- `docs/reports/2026-11/PANTHER-X2-ORIGINAL-SOFTWARE-IMAGE-PROVENANCE-20261120.md`
- `docs/reports/2026-11/PANTHER-X2-P2-BOOT-ARCHITECTURE-AND-EMMC-VENDOR-DATA-REVIEW-20261120.md`
- `docs/reports/2026-11/GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md`
- `docs/reports/2026-11/PANTHER-X2-B1-UBOOT-PREBOOT-CHECKPOINT-20261122.md`
- `docs/NETWORK-ACCEPTANCE.md`
- `docs/BUILD-PLAN.md`
- `docs/BOOT-DEPENDENCY-AUDIT.md`
- `docs/reports/2026-11/TF-BOOT-FAILURE-INVESTIGATION.md`
- `docs/reports/2026-11/EMMC-6.1.116-UDEV-ETH0-OFFLOAD-BOOT-LOG-EVIDENCE-20261120.md`
- `docs/reports/2026-11/PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md`

## Public evidence changes

- Added `evidence/boot/2026-11-19-panther-x2-jp-idbloader-uart-redacted.log`.
- Added `evidence/network/2026-11-19-panther-x2-dhcp-ipv4-status-redacted.txt`.
- Added `evidence/uart/panther-jp-tvbox-u-boot-boot-20261117-redacted.txt`.
- Verified the new text copies for MAC, UUID, CPU serial, and the relevant device-unique identifiers before removing their unredacted counterparts from the current branch.
- Removed the unredacted 2026-11-13 compressed UART archive, its Base64 chunks, and an oversized UART strings dump from the current branch because they could not be reliably inspected and redacted through the available text-file interface. Their SHA-256 metadata was retained. A redacted derivative has not yet been generated for that capture, and preservation of a private original was not verified.

## Evidence policy

The `evidence/README.md`, `evidence/uart/README.md`, and `evidence/boot/README.md` now state that public evidence must be privacy-reviewed and redacted. Unredacted source captures belong only in controlled private storage.

## Verification limits and outstanding work

1. Checks were performed against the current branch files that were fetched and inspected. This is not a byte-for-byte audit of every binary asset, workflow artifact, release, issue, or every file in every branch.
2. GitHub code-search results may lag behind recent commits; final checks used direct reads of the current files.
3. **Deleting or replacing a file on the current branch does not erase earlier Git commits.** Previously committed MAC addresses, UUIDs, serial numbers, and raw logs may still be retrievable from repository history. A full history rewrite and force-push has not been performed.
4. The 2026-11-13 UART capture was removed from the current branch pending a safe redaction workflow. Its private source retention remains unverified.
5. Publicly exposed device identifiers in historical commits should be treated as disclosed. If any credential or secret is later found, it must be rotated; history rewriting alone does not revoke it.

## Current status

- Current-branch text files explicitly checked: sensitive MAC/UUID/serial values removed from the reviewed set.
- Current-branch unredacted UART source files explicitly identified above: removed.
- Full repository-wide binary/artifact scan: incomplete.
- Git history cleanup: pending explicit authorization because it rewrites shared repository history.
