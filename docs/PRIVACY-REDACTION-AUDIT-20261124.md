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


## Multi-branch review after authorization

The repository exposes 11 branch heads:

- `main`
- `architecture/b1-full-base-network-isolation`
- `audit/6.1.116-reference-dtb`
- `audit/fnnas-boot-reference`
- `audit/panther-x2-uboot-fit`
- `audit/preflight-gpt-ext4-readonly`
- `diagnostic/6.12.81-uart-rootfs`
- `evidence/kernel-config/config-6.1.116-ophub`
- `fix/panther-x2-usb2-host-phy`
- `fix/uart-terminal-reliability`
- `workflow/fnnas-reference-audit`

No tag refs were returned by the repository refs endpoint. Three merged pull requests (PR #1–#3) still have GitHub-managed `refs/pull/*` references; these are not ordinary branch refs and cannot be force-updated through the branch-ref API.

Additional stale-branch exposures found:

- `architecture/b1-full-base-network-isolation` still contains the unredacted 2026-11-19 UART log (root filesystem UUIDs, partition UUIDs and CPU serial), the unredacted DHCP status file (wireless MAC and NetworkManager connection UUID), the compressed 2026-11-13 UART capture, its Base64 chunks, and the large UART strings dump.
- `fix/uart-terminal-reliability` still contains the same old UART archive and Base64 chunks.
- `diagnostic/6.12.81-uart-rootfs` contains a reconstructed UART excerpt with a filesystem UUID.
- `fix/panther-x2-usb2-host-phy` contains the home LAN address `192.168.9.6` in a project document.

These are historical branch-tip findings and must be handled by the all-branch rewrite; cleaning `main` alone is insufficient.

## Authorized history rewrite — not yet executed

The user approved rewriting Git history and force-updating remote branches on 2026-11-24. The rewrite has **not** been run yet.

The GitHub integration available in this session can inspect and update files/branch refs, but does not expose a workflow-dispatch action or a local Git push operation. A safe rewrite therefore requires a prepared, manually dispatched GitHub Actions workflow (or an equivalent local Git-filter-repo run). Do not create a replacement commit whose parent is the old history and call that a history purge; that would leave the exposed commits reachable.

The rewrite must preserve all 11 branch tips as separate branches, preserve their branch-specific files and commit relationships where possible, redact historical text blobs, remove unredacted raw UART capture paths, and push only `refs/heads/*` and tags. GitHub-managed `refs/pull/*` and cached views may remain accessible after branch rewriting; after the rewrite, GitHub Support may need to purge cached sensitive objects/PR refs. A repository history rewrite alone cannot guarantee deletion of third-party clones or external caches.

Before force-pushing, binary evidence archives and bootloader images still require a content-aware scan. In particular, the three `evidence/hardware/*.tar.gz` archives and binary bootloader assets were inventoried but not fully unpacked/string-scanned in this session. They must be checked before declaring the repository fully clean.


## Workflow prepared for the authorized rewrite

A manually gated workflow has been added at `.github/workflows/privacy-history-rewrite.yml`.

- Trigger: GitHub Actions → **Privacy-safe Git history rewrite** → **Run workflow**.
- Required confirmation input: `REWRITE-PUBLIC-HISTORY`.
- It mirror-clones all published branches/tags, rewrites text blobs without mutating NUL-containing binary blobs, removes identified raw UART files/chunks and unreviewed hardware tar archives, scans reachable text blobs, and only then force-pushes all branches and tags.
- The workflow checks that at least 11 branch refs are present before beginning.
- The workflow has **not been dispatched**. The history rewrite and force-push have **not occurred**.
- The workflow's scan is targeted, not a complete secret-scanning guarantee. Binary assets are preserved and not modified; the removed hardware tar archives are excluded pending separate review.
- GitHub-managed PR refs/caches and external clones remain outside this workflow and may require GitHub Support follow-up after a successful rewrite.
