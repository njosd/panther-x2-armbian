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
