# Panther X2 Project-A G2 minimal runtime packaging preparation (2026-11-27)

## 1. Purpose and boundary

G2-B build-only passed on 2026-11-27 (run `45924949130`, artifact `15167050233`). This document records the next preparation step: assemble a reproducible Project-A Linux 6.18.63 minimal RAM runtime using the frozen G2 kernel and DTB plus the already verified B1 static BusyBox and JP-TvBox U-Boot proper.

This is **PREPARE-ONLY**. The packaging workflow runs entirely on a GitHub Actions runner. It does not access Panther X2, write any physical TF/eMMC, start a boot, probe RK809, enable regulators, or activate GMAC/MDIO/PHY. Creating the workflow is not authorization to write media or boot the board.

The runtime package is a safe base for subsequent stage-specific work. It is not the G2-PROBE image with the PMIC enabled.

## 2. Frozen input artifacts

| Input | Run / artifact | Identity |
|---|---|---|
| G2-B kernel build | run `45924949130`, artifact `15167050233` | ZIP SHA256 `db4edb124497821158225d0a2d16b2f3f4f98ccbeabd5e3a95e09cdd1d46e346` |
| B1 boot-support bundle | run `45328201244`, artifact `14890817693` | ZIP SHA256 `9274e557ea5b62b6c2fc086d5aa3fd9a502215ff0070870ae36a9d6dfcfd4b9c` |
| Linux source | `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f` | Linux 6.18.63 |
| Kernel Image | G2 output | `c8ad5e8c6d4f7b095374abd66e2fc44379e83954c3991b453c3d7c8da3b7edf7` |
| Final kernel config | G2 output | `ffa99212686a1347145628fd50ecf3341437efe4a4f130002e4b27003c4f553b` |
| Panther X2 DTB | G2 output | `f6d83d86231b50c903abdf158893b6caa1e8c2aab931c9bf2dbb1b6ca36576dc` |
| Static BusyBox | B1 output, v1.37.0 | `2d77cb64f5ab5ca33efae040083abe31912ab02677dd21c1b79ade6ed0e98b15` |
| JP-TvBox U-Boot proper | B1 output | `a1ae35a8522e4353611042e62c3b7b7eaa7e4b6955bae5e5c4f8499500dbfdce` |

The B1 bundle was downloaded and inspected locally during this preparation. Its internal `output/SHA256SUMS` validated, including the BusyBox, DTB, U-Boot proper, boot script and existing B1 initramfs. The G2 workflow artifact's internal `output/SHA256SUMS` is independently verified again by the new packaging workflow.

The G2 build toolchain was recovered from the successful run's apt installation log (job `140263994034`): runner `ubuntu-24.04`, package `gcc-13-aarch64-linux-gnu` version `13.3.0-6ubuntu2~24.04.1cross1`, wrapper package `gcc-aarch64-linux-gnu` version `4:13.2.0-7ubuntu1`. The new runtime manifest records these exact package versions and their provenance. This avoids marking the compiler as unknown merely because the earlier G2 artifact manifest omitted it.

## 3. Runtime composition

| Component | Source / treatment |
|---|---|
| Linux Image | G2-B exact output |
| Panther X2 DTB | G2-B exact output; RK809/GMAC1/MDIO/RTL8211F disabled |
| BusyBox | frozen B1 static ARM64 binary; no rebuild or applet expansion |
| `/init` | new Project-A G2 diagnostic shell init; mounts procfs/sysfs, reports kernel/model/cmdline/memory/interfaces/DTB statuses/mounts/dmesg, then interactive shell |
| initramfs | rebuilt from the static BusyBox plus the new init and only required applet symlinks |
| `uInitrd` | generated from the gzip initramfs using `mkimage` |
| `boot.scr` | generated from the frozen Project-A G2 `boot.cmd` |
| U-Boot proper | frozen JP-TvBox FIT, embedded at raw LBA 16384 (8 MiB) |
| TF partition | 2 GiB GPT image; `PANTHER_BOOT` ext4 partition 1, LBA 32768 through 4192255 |
| Root filesystem | initramfs in RAM; no persistent rootfs or modules tree |

**Verified frozen B1/R1/G2 storage and USB boundary (artifact evidence, 2026-11-27):** the B1 kernel artifact used by R1 (`run 45309219886`, config SHA256 `7d6c37a10c0622ad31973b05fe20528e1aff9db984ace93b85bde0d1da599731`) has `CONFIG_BLOCK=y`, `CONFIG_MMC=y`, `CONFIG_USB=y`, and `CONFIG_MODULES=y`. The B1/R1 DTB SHA256 is `7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`; G2 inherits this DTB and changes only the RK809 node. Decoding the exact G2 DTB (SHA256 `f6d83d86231b50c903abdf158893b6caa1e8c2aab931c9bf2dbb1b6ca36576dc`) confirms TF `/mmc@fe310000` and eMMC `/mmc@fe2b0000` are enabled, SDIO `/mmc@fe2c0000` is disabled; USB host controller nodes `/usb@fcc00000`, `/usb@fd800000`, `/usb@fd840000` and USB2 PHY0 `/usb2phy@fe8a0000` are enabled, while the second controller/PHY and unrelated nodes remain disabled. UART1 `/serial@fe650000` and UART2 `/serial@fe660000` are enabled; the Bluetooth child under UART1 is absent; UART2 is the console. GMAC1/MDIO/RTL8211F and RK809 remain disabled. The RAM-only guarantee is about rootfs and userspace behavior: U-Boot loads Image/uInitrd/DTB from TF before Linux starts; Linux root is initramfs in RAM, and `/init` does not mount or write persistent filesystems. **Source/artifact drift:** the current default-branch B1 fragment, DTB preparation script and B1 workflow have since diverged from the frozen artifact contract (they now describe/require a more aggressively disabled storage/USB baseline). Do not rebuild B1 from those current files until that drift is reconciled against the frozen B1/R1 artifacts. This G2 packaging job consumes the immutable artifacts and must gate against their actual configuration/DTB, not the newer mismatched source descriptions.

The new init script and boot script are stored at:
- `scripts/panther-x2-g2-runtime/init`
- `scripts/panther-x2-g2-runtime/boot.cmd`

## 4. Frozen boot contract

The boot script preserves the already exercised U-Boot loading arrangement:

- Kernel Image: `mmc 1:1`, load address `0x00280000`, file `/Image`.
- uInitrd: `mmc 1:1`, load address `0x0a200000`, file `/uInitrd`.
- Panther X2 DTB: `mmc 1:1`, load address `0x0a100000`, file `/dtb/rockchip/rk3566-panther-x2.dtb`.
- bootargs: `console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init`.
- Existing boot chain: eMMC SPL -> JP-TvBox U-Boot proper from TF -> Image/uInitrd/DTB from TF -> RAM initramfs.

The script does not save U-Boot environment, reset the device, or fall through to another boot target after a failed load. It holds in the U-Boot script if a load or `booti` returns.

The eMMC SPL remains an existing boot dependency. This workflow does not install or alter SPL/IDBLoader.

## 5. Safety and isolation gates

The network isolation gate checks concrete driver/protocol symbols (STMMAC, Rockchip DWMAC, MDIO, PHYLIB/PHY driver, individual USB NIC drivers, wireless/Bluetooth), not broad menu-group symbols such as `CONFIG_NET_VENDOR_*` or `CONFIG_USB_NET_DRIVERS`. These umbrella options may be `y` without any concrete NIC driver being selected; treating them as a driver would create false positives. The full Linux 6.18.63 USB-network driver symbol list is checked individually. In the frozen G2 `.config`, `CONFIG_USB_NET_DRIVERS=y` is only the umbrella menu; none of the concrete USB NIC options in that Kconfig list is `y` or `m`. The runtime script also reports whatever interfaces actually exist rather than assuming loopback must be present.

The packaging workflow must verify before assembling the image:

1. G2 and B1 artifact internal SHA256 manifests.
2. Exact G2 Image/config/DTB, B1 BusyBox and JP U-Boot proper hashes listed above.
3. Required kernel configuration: ARM64, OF, initrd, proc/sysfs, TTY/UART, NET, PACKET, I2C, REGMAP_I2C, REGMAP_IRQ, MFD_CORE, MFD_RK8XX, MFD_RK8XX_I2C and MODULES.
4. Forbidden kernel configuration remains absent: IP protocols (INET/IPv6), STMMAC/Rockchip DWMAC, MDIO/PHYLIB/RTL8211F, USB network adapters, RK808 regulator, PWRKEY child, wireless and Bluetooth. BLOCK/MMC/USB host/USB storage are retained as in the frozen B1/R1 config; the USB NIC drivers remain disabled.
5. DTB model/compatible are Panther X2/RK3566; RK809, GMAC1, MDIO, PHY and SDIO are disabled; TF/eMMC, USB host/PHY0, UART1/UART2 are enabled; Bluetooth child under UART1 is absent; unused SDHCI and second USB controller/PHY nodes are disabled.
6. BusyBox is AArch64 and statically linked; required applets exist; the init script passes BusyBox ash syntax validation.
7. Initramfs round-trip extraction preserves the exact init and BusyBox.
8. GPT/ext4 layout, embedded JP U-Boot proper readback, read-only remount and payload hashes.
9. Final artifact SHA256 manifest validates.

No PMIC probe is triggered merely because MFD code is built-in: the RK809 DT node remains disabled. No physical network interface is available: GMAC1/MDIO/PHY remain disabled. The frozen B1/R1 baseline retains MMC/eMMC/TF and USB host/PHY support, but `/init` leaves persistent filesystems unmounted and the root remains initramfs in RAM. Network core and AF_PACKET are built in, but the runtime does not configure addresses/routes or send packets.

## 6. New workflow

- Workflow: `.github/workflows/package-panther-x2-g2-runtime.yml`
- Trigger: manual `workflow_dispatch`
- Artifact name: `panther-x2-project-a-g2-runtime-PREPARE-ONLY`
- Intended outputs: PREPARE-ONLY compressed 2 GiB TF image, standalone Image/DTB/uInitrd/boot script/initramfs/BusyBox, final kernel config, System.map/vmlinux debug references, input lock, runtime manifest, logs and SHA256 inventory.
- Retention: 30 days.

The workflow has been committed but has **not yet been run**. Therefore the runtime package is not yet built, not yet validated as an assembled image, and not authorized for physical media.

## 7. Stage boundary after packaging

The safe runtime package retains RK809 MFD code in the kernel but keeps the RK809 node disabled. This is intentional: it gives us a stable, reproducible base without PMIC side effects.

The next steps are:
1. Run the PREPARE-ONLY packaging workflow and inspect every gate and artifact.
2. Archive the final runtime manifest and all hashes.
3. Separately complete the G2 stock-probe static side-effect review and submit the exact PMIC write/IRQ side-effect list and stop conditions.
4. Only after that review, ask for explicit authorization for a dedicated PMIC-enabled DTB variant and a single controlled G2-PROBE run.

No G2-PROBE, regulator activation, IO-domain activation, GMAC enable, AF_PACKET physical send, TF write or Panther X2 boot is authorized by this packaging preparation.

## 7.1 First packaging attempt and gate correction (2026-11-27)

Run `45933429153`, job `140291064301`, completed artifact downloads and validated both frozen ZIP SHA256 digests and every internal `SHA256SUMS` entry. It then stopped at the first forbidden Kconfig check: `CONFIG_BLOCK=y`. This was a false positive: the frozen B1/R1/G2 `.config` intentionally contains `CONFIG_BLOCK=y`, `CONFIG_MMC=y`, `CONFIG_USB=y`, `CONFIG_USB_STORAGE=y`, and `CONFIG_MODULES=y`. The job correctly skipped all later steps; no initramfs, TF image or runtime artifact was generated.

The workflow was corrected to allow the frozen storage/USB host baseline while continuing to reject concrete USB NIC drivers and all out-of-scope network/PHY drivers. DTB assertions now match the exact frozen state: TF/eMMC enabled, SDIO disabled, USB host/PHY0 enabled, unused SDHCI/second USB controller/PHY disabled, UART1/UART2 enabled with no Bluetooth child, and RK809/GMAC1/MDIO/PHY disabled. The next run remains PREPARE-ONLY and must still pass all remaining offline packaging and image-integrity gates.

## 8. Status

- G2-B build-only: **PASS**.
- B1 BusyBox/U-Boot support artifact identity: **verified**.
- New G2 runtime init/boot scripts: **committed**.
- G2 runtime packaging workflow: **first run `45933429153` failed at the Kconfig preflight because `CONFIG_BLOCK=y` was incorrectly listed as forbidden; immutable input artifact SHA256 checks all passed. No initramfs/image/package steps ran. The concrete-driver and DTB gates have since been corrected to match frozen B1/R1/G2 artifact evidence; awaiting a fresh manual Actions run.**
- Runtime image build and offline artifact audit: **PENDING; no runtime image artifact was produced by run `45933429153`**.
- G2-PROBE: **HOLD / NOT AUTHORIZED**.
- Physical media write / Panther X2 boot: **NOT AUTHORIZED**.
