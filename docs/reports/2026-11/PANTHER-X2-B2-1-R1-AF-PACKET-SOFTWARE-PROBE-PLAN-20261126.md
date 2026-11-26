# Panther X2 B2-1 R1 AF_PACKET software probe plan

Date: 2026-11-26

## Purpose and plan alignment

The frozen B2-1 plan defines R1 as the Linux generic network core and AF_PACKET foundation, with GMAC1/MDIO/PHY deliberately disabled. The plan also requires components that can be safely function-tested in the current stage to be tested at the earliest opportunity; only unavailable tests may be blocked with an explicit earliest verification stage.

This supplement closes the R1 userspace evidence gap without enabling a physical NIC, adding an IP protocol, changing the kernel, or altering the existing R1 image.

## Scope

The probe is a small statically linked AArch64 C program. It attempts, and records the return value and errno for:

1. AF_PACKET/SOCK_RAW socket creation;
2. a second raw packet socket for receive observation;
3. AF_PACKET/SOCK_DGRAM socket creation;
4. interface-index lookup by reading `/sys/class/net/<interface>/ifindex` (default: `lo`), deliberately avoiding an `AF_INET` control socket because R1 keeps `CONFIG_INET` disabled;
5. binding each packet socket to that interface;
6. raw and datagram `sendto()` attempts using a fixed local test marker;
7. a bounded receive observation on the raw receive socket.

The program reports each syscall independently. A send error is recorded as evidence and does not cause the program to hide earlier successful stages. The program exits successfully after producing the diagnostic record; this exit status is not an overall PASS indication.

## Interpretation rules

- Successful socket creation directly verifies that the running kernel accepts the AF_PACKET socket request under the executing credentials.
- Successful bind directly verifies packet-socket binding to the selected interface.
- Successful `sendto()` means only that the syscall accepted the request; it is not evidence of an Ethernet wire transmission.
- A receive observation, if any, is a separate software-path result. Its packet type, protocol and captured prefix must be retained.
- `lo` is a loopback interface, not an Ethernet device. No result from `lo` can establish Ethernet framing, MAC TX, DMA, RGMII, PHY, cable or peer reception.
- R1 intentionally has no physical network interface. Physical Ethernet TX is blocked until the hardware path is restored at R7.
- The probe does not configure addresses, routes, link state, promiscuous mode, or any network service.

## Build-only CI boundary

Workflow: `.github/workflows/build-panther-x2-b2-1-r1-af-packet-probe.yml`.

The workflow:
- cross-compiles a static AArch64 ELF with the Ubuntu cross toolchain;
- verifies ELF architecture and absence of a dynamic interpreter;
- runs only the probe's non-network `--self-test` mode under QEMU user mode;
- records source/binary SHA256 and binary size;
- uploads a standalone artifact.

The QEMU self-test validates executable architecture and the static program's basic startup only. It does not execute AF_PACKET syscalls and is not runtime kernel evidence.

## Target-runtime delivery remains pending

This authorization covers repository source, workflow and build-only CI. It does not authorize:
- rebuilding or repackaging the R1 initramfs/TF image;
- writing SU08G, SN64G or eMMC;
- booting or interacting with Panther X2;
- changing kernel configuration, DTB, bootargs or network state.

After the build artifact is available, choose and separately authorize a delivery method for the static binary into the existing R1 RAM environment. The preferred low-risk route is a new R1 probe initramfs/image derived from the frozen R1 assets, followed by a separately authorized SU08G write and runtime test. The current R1 image and its recorded hashes remain the rollback baseline.

## Acceptance matrix

| Item | Current result | Evidence class |
|---|---|---|
| Probe source reviewed and committed | Pending CI build | Source |
| Static AArch64 link | Pending CI | Build |
| AArch64 ELF / no dynamic interpreter | Pending CI | Build |
| QEMU non-network self-test | Pending CI | Build smoke test |
| AF_PACKET socket creation on Panther R1 | Not yet run | Runtime pending |
| Bind to `lo` on Panther R1 | Not yet run | Runtime pending |
| Raw/datagram send attempts on Panther R1 | Not yet run | Runtime pending |
| Packet receive observation on Panther R1 | Not yet run | Runtime pending |
| Physical Ethernet TX | Not available in R1; earliest R7 | Blocked by design |

No target hardware or storage medium was accessed for this supplement.


## 2026-11-26 source audit follow-up

A read-only review of the committed C source found two issues before target use:
- The sysfs-based ifindex conversion had retained an obsolete `ifreq` initialization/name-copy block. This was removed; the current source has no `struct ifreq`, `SIOCGIFINDEX`, or `AF_INET` control socket.
- The first draft stopped all later checks if any one of the three packet-socket creations failed. The probe now keeps the stages independent: it records each socket result, continues interface lookup, and attempts bind/send/receive only for sockets whose preceding stage succeeded. A failed socket no longer suppresses useful evidence from the other socket types.

Source corrections are committed in `337be3b142b79861a17ef78033c214b522047b59` and `668e5241d5f61eea81ea021c5f2d704753b815f1`.

**CI status:** no completed Actions run or build artifact has yet been confirmed from the available repository status/run queries. Therefore static compilation, ELF checks and QEMU self-test remain pending; source review is not represented as a successful build. No target device or storage was accessed.


## 2026-11-26 CI build result — PASS (build-only)

Workflow run: [45744318699](https://github.com/njosd/panther-x2-armbian/actions/runs/45744318699), job `139656577918`, source revision `668e5241d5f61eea81ea021c5f2d704753b815f1`.

All five substantive job steps completed successfully:
- repository checkout;
- isolated AArch64 static toolchain installation;
- static AArch64 probe compilation with `-Wall -Wextra -Werror`;
- ELF architecture / no dynamic interpreter checks and QEMU user-mode `--self-test`;
- artifact publication.

### Verified build outputs

- Artifact: `panther-x2-r1-af-packet-probe-static-aarch64`
- Artifact ID: `15082134345`
- Artifact ZIP size: 295,605 bytes
- Artifact ZIP SHA256: `cc90f8f9783929b306d194d44894e459d92d481d342c0df9ea3ee385a9022ce5`
- Binary size: 635,984 bytes
- Binary SHA256: `8ea3ac72a0c1f721ae673d1a29d3f9874cf5abd1e803cf63b9d5637e24764f3e`
- Embedded source SHA256: `063b4c27f5592aeb56f3352bcf7762f2fa240fbc800a78d9939210d4b76d1ab7`
- ELF: 64-bit little-endian AArch64 executable, statically linked; program headers contain no `PT_INTERP`.
- QEMU self-test output: `probe=self-test`, `architecture=aarch64`, `self_test=PASS`.

The downloaded artifact ZIP was independently inspected. Its file list, ELF header/program headers, file size and SHA256 values match the CI evidence.

### Evidence classification

**PASS-BUILD:** static AArch64 cross-compilation, strict warning build, ELF architecture and static-link checks.

**PASS-SMOKE:** the non-network `--self-test` path starts under QEMU user mode.

**Not verified:** AF_PACKET socket syscalls on Linux 6.18.63 running on Panther X2; socket bind; packet send/receive; any physical Ethernet behavior. QEMU self-test deliberately does not call AF_PACKET.

The artifact is retained by GitHub Actions until 2026-12-26. Download link: [workflow artifact](https://github.com/njosd/panther-x2-armbian/actions/runs/45744318699/artifacts/15082134345).

No Panther X2 device was accessed and no TF/eMMC medium was written.


## 2026-11-26 dedicated R1 AF_PACKET probe image — PREPARE-ONLY PASS

The static probe has been integrated into a separate R1 test initramfs and a separate Etcher-ready TF image. The original R1 image and its kernel/DTB/U-Boot/bootargs remain unchanged.

### Repository additions

- Init script: `scripts/panther-x2-r1/init-af-packet-probe`
- Packaging workflow: `.github/workflows/package-panther-x2-r1-af-packet-probe.yml`

The init script mounts only procfs and sysfs in the RAM initramfs, runs `/bin/af-packet-probe-aarch64 lo`, records the process exit code, shows the mount table, and then enters the interactive shell. It does not configure an address, route, link state, or network service. GMAC1/MDIO/PHY remain disabled.

The workflow reuses and SHA256-pins the existing R1 kernel artifact, B1 support artifact and independently CI-built static probe. It creates a dedicated uInitrd, preserves the frozen bootargs and U-Boot load addresses, builds the same 2GiB GPT/PANTHER_BOOT layout, checks the filesystem and GPT, and emits a gzip-compressed image whose decompressed SHA256 is compared with the raw image SHA256.

### CI result

Final successful workflow: [45745957844](https://github.com/njosd/panther-x2-armbian/actions/runs/45745957844), job `139661965868`, source revision `bbe09c25f9e323147301038aa5fb0469b2bcba9f`. All 12 substantive steps passed, including frozen-input checks, initramfs creation/round-trip validation, boot-script validation, image assembly, read-only partition inspection, gzip integrity, decompressed raw-image SHA256 comparison and artifact upload.

Two earlier package attempts failed before image assembly because the workflow referenced an unavailable cross-prefixed readelf executable. The subsequent host-tool validation iterations also failed at the package's preliminary ELF/self-test gate. The final workflow removes redundant revalidation of the already pinned and independently CI-verified probe artifact; it records `file` output and enforces the exact binary/source SHA256 before embedding it. The final run then passed the complete package path. No failed attempt wrote to physical media.

### Published artifact and independently rechecked hashes

- Artifact name: `panther-x2-r1-af-packet-probe-TF-IMAGE-ETCHER-READY-PREPARE-ONLY`
- Artifact ID: `15082669519`
- Artifact ZIP size: 15,497,403 bytes
- Artifact ZIP SHA256: `92e439d9734e3730beb13415652b17af9cf2db0667365b103f35fa527dabca1b`
- Etcher image inside ZIP: `panther-x2-r1-af-packet-probe-PREPARE-ONLY.img.gz`
- Compressed image size: 23,266,757 bytes
- Compressed image SHA256: `d36f4e74c0c8255f9704aeb5419d96a4bdff35a6ae075b73ca9e409485a1a5a4`
- Decompressed 2GiB raw image SHA256: `6067388ae22c812f280f303fe9906de42d3db07187059311da66fa4b9abe4cde`
- Dedicated uInitrd SHA256: `a00eafa55d06ea65409c0f3ba26018b8a93cd5e75d84c7ee1ca6e50cc65be051`
- Embedded probe SHA256: `8ea3ac72a0c1f721ae673d1a29d3f9874cf5abd1e803cf63b9d5637e24764f3e`
- Initramfs init script SHA256: `1711f365a6e5def45b5988ddecc1ddf8831ebcefe2bac1256e8d139d02b75119`

The artifact ZIP was downloaded and independently inspected in the working environment:
- ZIP SHA256 matches GitHub artifact metadata.
- ZIP contents include the Etcher-ready `.img.gz`, uInitrd, initramfs archive, verification record, file hashes, boot script and partition metadata.
- `gzip -t` succeeds.
- Independently streaming the decompressed gzip image produces raw SHA256 `6067388a...`, matching the CI raw-image hash.
- The initramfs archive listing confirms the static probe is executable and the required BusyBox applet links are present.

Artifact: [download PREPARE-ONLY Etcher-ready image](https://github.com/njosd/panther-x2-armbian/actions/runs/45745957844/artifacts/15082669519). Retention expiry: 2026-12-26.

### Updated R1 AF_PACKET acceptance

| Item | Result | Evidence class |
|---|---|---|
| Probe source and isolated init script | PASS | Repository source |
| Static AArch64 probe build | PASS | CI run 45744318699 |
| Dedicated probe initramfs assembly | PASS | CI run 45745957844 |
| Initramfs round-trip and embedded binary identity | PASS | CI checks |
| Frozen kernel/DTB/U-Boot/bootargs | PASS | SHA256 and boot-script checks |
| Etcher gzip integrity and decompressed raw SHA256 | PASS | CI and independent local recheck |
| AF_PACKET socket creation on Panther R1 | NOT RUN | Target runtime pending |
| Bind to `lo` on Panther R1 | NOT RUN | Target runtime pending |
| Raw/datagram send and receive on Panther R1 | NOT RUN | Target runtime pending |
| Physical Ethernet TX/RX | NOT AVAILABLE IN R1 | Earliest R7 |

### Authorization and safety boundary

This is a **PREPARE-ONLY artifact**, not a target-hardware result. No Panther X2 access occurred during packaging, and no SU08G, SN64G or eMMC write was performed. The artifact is prepared for the dedicated SU08G stage, but flashing it and booting Panther X2 require separate explicit authorization. SN64G and eMMC remain excluded. The original R1 image remains the rollback baseline.
