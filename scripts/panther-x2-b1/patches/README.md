# B1 kernel compatibility patch

## Current patch

`0001-broadcast-uevent-net-only-api.patch`

The patch is applied only after the workflow checks out the exact pinned Linux 6.18.63 source commit and verifies that the checkout is pristine.

## Why it is required

With `CONFIG_NET=n`, the networking core is not built. The pinned source nevertheless provided a no-network `broadcast_uevent()` stub in `lib/kobject_uevent.c`. That stub called `kfree_skb()`, whose inline implementation references `sk_skb_reason_drop()`. Since the networking core is excluded, the final kernel link failed with an unresolved reference to that symbol.

## Patch semantics

- Guard the declaration of `broadcast_uevent()` in `include/linux/kobject.h` with `#ifdef CONFIG_NET`.
- Keep the normal network implementation and its `kfree_skb(skb)` ownership release unchanged.
- Remove the no-network stub and guard the symbol export together with the network implementation.
- Do not enable `CONFIG_NET`, Ethernet, Wi-Fi, Bluetooth, or any network driver.

The identified in-tree caller, `drivers/input/keyboard/gpio-button-hotplug.c`, is disabled by the B1 configuration fragment. If a future no-network configuration enables a caller, the missing declaration should cause a compile-time failure rather than silently preserving an invalid no-network skb path.

The historical `0001-kobject-uevent-config-net-n.patch` is not applied. It returned `-EOPNOTSUPP` for a non-NULL skb without releasing it, so it did not preserve the original skb ownership contract.

## Workflow validation

The workflow:
1. checks out the pinned upstream commit;
2. verifies a pristine checkout;
3. runs `git apply --check` and applies this patch;
4. structurally checks the CONFIG_NET-guarded declaration, implementation and export, absence of the no-network stub, and preservation of `kfree_skb(skb)`;
5. records the patch SHA-256 in the source manifest.

The patch is a narrow B1 compatibility change. It is not a general-purpose upstream kernel patch.

## Verification status

- Static source and caller audit: completed for the pinned source revision.
- Patch syntax and unified-diff hunk counts: corrected after Run #64 reported a corrupt patch; the corrected hunk counts have been checked against the patch text.
- `git apply --check` in the GitHub Actions runner: pending.
- Kernel compile and final link: pending.
- DTB, BusyBox, package artifact and Panther X2 hardware boot: pending.
