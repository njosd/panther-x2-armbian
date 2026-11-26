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

## 2026-11-26 target-runtime result and corrected loopback retest package

### First Panther X2 runtime result

The user booted the dedicated probe image on the authorized SU08G TF and supplied the UART output.

Verified:
- AF_PACKET SOCK_RAW, second receive SOCK_RAW, and SOCK_DGRAM socket creation all succeeded (rc values 3, 4, and 5).
- All three packet sockets bound successfully to lo (bind_*_rc=0).
- Interface index lookup succeeded (ifindex=1).
- Both raw and datagram sendto() returned -1, errno=100 (ENETDOWN).
- No packet was received during the 500ms observation.
- The probe process exited 0, meaning its diagnostic routine completed; it is not an all-subtests-pass indicator.
- Physical Ethernet TX was explicitly not tested; GMAC1/MDIO/PHY remain disabled.

After the probe, the user read /sys/class/net/lo/flags; result was 0x8. This contains IFF_LOOPBACK but not IFF_UP (0x1). The loopback interface was therefore administratively down during the first send attempt. This directly explains the ENETDOWN result; it does not indicate an AF_PACKET send implementation defect.

### Source correction

Commit 0e6c590cdc27ddd43d819c4d11e4163fad262133 updates scripts/panther-x2-b2-1/af-packet-probe.c:
- After successful packet socket creation/bind, query lo flags through the existing AF_PACKET socket using SIOCGIFFLAGS.
- If IFF_UP is absent, temporarily set only IFF_UP.
- Record original and post-change flags.
- Run RAW/DGRAM send and packet receive observation.
- Report poll() revents explicitly, so readiness/error/hangup can be distinguished.
- Restore the original interface flags before normal process exit.
- No IPv4 socket, IP address, route, GMAC, MDIO, PHY, or persistent configuration is added.

The init script now explains that lo may be temporarily raised and its original flags are restored.

### Rebuild and image packaging

Static build workflow: [45747785913](https://github.com/njosd/panther-x2-armbian/actions/runs/45747785913), job 139667947294, source commit 0e6c590cdc27ddd43d819c4d11e4163fad262133. Build, AArch64 ELF/static-link checks and QEMU non-network self-test passed.
- Static probe artifact ID: 15084530876
- Artifact ZIP SHA256: 2691bd4c55b781a786ea23971de232b1c826022bc59151be7be02a771150eeed
- Binary size: 636,120 bytes
- Binary SHA256: d74ad0a1012e1f345cab5ee3901872c800f872d4b57b023fe84ac91f6b617b3e
- Source SHA256: 9333a6f0d0d6a2196917443c8ab33479d953a8192a5338644954bc14da2f1ffd

The dedicated PREPARE-ONLY package workflow [45748363770](https://github.com/njosd/panther-x2-armbian/actions/runs/45748363770), job 139670126730, completed successfully. It verifies the probe artifact checksum manifest and exact source equality against the repository, pins the frozen R1 kernel/DTB and B1 U-Boot inputs, validates the initramfs round trip, preserves the existing bootargs/load addresses and GPT layout, then checks the Etcher gzip and decompressed raw image hashes.

New artifact:
- Name: panther-x2-r1-af-packet-probe-TF-IMAGE-ETCHER-READY-PREPARE-ONLY
- Artifact ID: 15084507127
- Artifact ZIP size: 15,502,100 bytes
- Artifact ZIP SHA256: b77a6ed8df90f72218c3fabc8b22419af91d937cadf8197da1cab95f0bc98a7b
- Etcher file: panther-x2-r1-af-packet-probe-PREPARE-ONLY.img.gz
- Compressed image SHA256: f7a3c6f21d9150af062b3dc7229a42bc4d7ba2cf83267fc984836a18036da821
- Decompressed 2GiB raw image SHA256: beac3df7e770dbcb39d4e22995bafbaebfd38317222e387e5a3ee497a7f40d22
- Dedicated uInitrd SHA256: f18503eee87bdb9d65e6b2b64604490a43465e94fac17f243cf3a55f793f4cbd
- Embedded probe SHA256: d74ad0a1012e1f345cab5ee3901872c800f872d4b57b023fe84ac91f6b617b3e

Artifact: [download corrected PREPARE-ONLY image](https://github.com/njosd/panther-x2-armbian/actions/runs/45748363770/artifacts/15084507127). Retention expiry: 2026-12-26.

### Current acceptance state

| Item | Result | Evidence |
|---|---|---|
| AF_PACKET RAW/DGRAM socket creation | PASS | Panther X2 UART output |
| Bind RAW/RX/DGRAM to lo | PASS | Panther X2 UART output |
| First RAW/DGRAM send | BLOCKED BY lo DOWN | ENETDOWN; lo/flags=0x8 |
| First receive observation | No packet | 500ms probe output; no POLLIN detail in original probe |
| Corrected probe source/build | PASS | Commit 0e6c590; CI 45747785913 |
| Corrected dedicated initramfs/image package | PASS — PREPARE-ONLY | CI 45748363770 |
| Corrected probe on Panther X2 | NOT YET RUN | Requires separate SU08G write/boot authorization |
| Physical Ethernet TX/RX | NOT TESTED IN R1 | Earliest physical TX stage remains R7 |

### Authorization boundary

The corrected image is only prepared. It has not been written to any physical medium and has not been booted. The earlier authorization to write/boot the previous probe image does not automatically authorize replacing it with this new image. Any new write is restricted to the dedicated SU08G TF and requires explicit confirmation. SN64G and eMMC remain excluded. No persistent system configuration has been changed.


## 2026-11-26 runtime root-cause audit — bind ordering

The corrected target-runtime log showed that the probe successfully raised `lo` to `IFF_UP` (flags changed from `0x0008` to `0x0049`), but RAW and DGRAM `sendto()` still returned `ENETDOWN`; the RX socket reported `POLLERR`.

A source-level audit against upstream Linux `v6.18` `net/packet/af_packet.c` established the cause:

- `packet_do_bind()` checks the selected device's `IFF_UP` state when a packet socket is bound.
- If the device is down, it records `sk->sk_err = ENETDOWN`.
- The `NETDEV_UP` notifier path re-registers the packet protocol hook for the socket, but does not clear the previously recorded `sk_err`.
- Therefore setting `lo` UP after binding does not repair the already-bound sockets. The earlier runtime result is explained by the probe's operation order, not evidence of a Panther X2 GMAC/PHY issue.

The probe source was corrected to:
1. create packet sockets and obtain the interface index;
2. save the original interface flags;
3. raise the selected test interface if required and verify `IFF_UP`;
4. bind RAW/RX/DGRAM sockets only after the interface is confirmed UP;
5. perform the send and receive observations;
6. restore the original interface flags before process exit.

If the interface cannot be confirmed UP, binding is skipped rather than creating sockets with a known-down device. The DGRAM bind errno reporting was also corrected in the final source commit.

Source commits:
- `ccdeca7b5e2e2a5ff0068e432a05804a9db9a8c3` — move packet-socket bind after confirmed interface UP.
- `78f425ebf149e1aae91b0fc9046681c707cfdb7b` — correct DGRAM bind errno reporting.

Build-only CI:
- Run [45750270491](https://github.com/njosd/panther-x2-armbian/actions/runs/45750270491) passed static AArch64 build and QEMU non-network self-test for the bind-order correction.
- Run [45750286867](https://github.com/njosd/panther-x2-armbian/actions/runs/45750286867) builds the final source including the DGRAM errno-reporting correction; status was in progress when this report section was prepared.

This diagnosis is source-confirmed. The corrected probe has **not yet been rerun on Panther X2**. No new initramfs/image has been packaged, and no TF/eMMC write has been performed. The previous runtime evidence remains historical evidence for the old probe ordering only.

### Loopback receive interpretation

Linux `v6.18` loopback TX feeds packets back into the local receive path, while the AF_PACKET `packet_rcv()` callback explicitly drops packets marked `PACKET_LOOPBACK`. The packet transmit tap can separately expose an outgoing clone marked `PACKET_OUTGOING`. Consequently, the R1 `lo` RX observation is only a software-path probe; a lack of a received packet must not be interpreted as physical NIC RX failure, and a received outgoing clone must not be interpreted as wire-level reception.

Physical Ethernet TX/RX remains unavailable in R1 by design and belongs to the later hardware-enabled stage.
