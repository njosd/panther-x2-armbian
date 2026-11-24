# B1 kernel compatibility patch

`0001-kobject-uevent-config-net-n.patch` is applied by the B1 workflow to the exact locked Linux 6.18.63 source commit.

## Why it is required

With `CONFIG_NET=n`, the network-enabled uevent implementation and its `alloc_uevent_skb()` allocator are compiled out. The remaining `broadcast_uevent()` stub still called inline `kfree_skb()`. In this source revision, that inline helper calls `sk_skb_reason_drop()`, whose implementation is in the networking core and is not linked in this configuration. The CI failure was confirmed at the final vmlinux link:

```
lib/kobject_uevent.o: undefined reference to `sk_skb_reason_drop'
```

## Patch semantics

The no-network stub now accepts only a NULL skb and returns `-EOPNOTSUPP` if a non-NULL skb is unexpectedly supplied. This preserves an explicit failure for an impossible no-network input and avoids referencing a networking symbol. The skb allocation and netlink send paths remain compiled out; no network stack, device driver, or protocol is enabled.

This is a narrow compatibility patch for the B1 `CONFIG_NET=n` build, not a general-purpose kernel change. The workflow applies it only after verifying the pinned source commit and checks the patched stub before compiling.
# B1 CONFIG_NET=n uevent API compatibility patch

## Current patch

`0001-broadcast-uevent-net-only-api.patch`

This patch is applied only after the workflow verifies the exact Linux 6.18.63 source commit and a pristine checkout. Its purpose is to make the `broadcast_uevent()` API and exported implementation exist only when `CONFIG_NET` is enabled.

Changes:
- Guard the declaration in `include/linux/kobject.h` with `#ifdef CONFIG_NET`.
- Keep the existing network implementation unchanged, including its `kfree_skb(skb)` ownership release.
- Remove the `CONFIG_NET=n` stub, which called `kfree_skb()` and caused an unresolved `sk_skb_reason_drop` reference because `net/` is not built when `CONFIG_NET=n`.
- Guard the symbol export together with the network implementation.

The locked source's in-tree caller is `drivers/input/keyboard/gpio-button-hotplug.c`. Its Kconfig symbol is `CONFIG_KEYBOARD_GPIO_BUTTON_HOTPLUG`, and the B1 fragment explicitly disables that symbol. The corresponding Makefile entry is therefore excluded in B1. This is the caller-level reason the no-network stub is unnecessary for this baseline. If a future configuration enables another caller while `CONFIG_NET=n`, compilation should fail at the missing declaration rather than silently accept a no-network skb ownership path.

## Ownership and safety rationale

The old patch `0001-kobject-uevent-config-net-n.patch` is retained as historical evidence only and is not applied. It changed the no-network stub to return `-EOPNOTSUPP` for a non-NULL skb without releasing that skb. That was not an acceptable preservation of the original ownership contract.

The current patch does not change the normal network-enabled implementation or its skb release. It removes the impossible no-network API/stub and makes an accidental no-NET caller a compile-time error.

## Workflow validation

The workflow:
1. checks out the exact pinned upstream commit;
2. confirms the checkout is pristine;
3. runs `git apply --check` and applies this patch;
4. structurally checks the guarded declaration, guarded implementation/export, absence of the no-NET stub, and preservation of `kfree_skb(skb)`;
5. records the patch path and runtime SHA-256 in `source-lock.txt`.

The patch blob SHA reported by GitHub for this repository file is `5dc892f2b80a9bd3b92fed6bdecce56eb5920c5e`. This Git blob SHA is not a SHA-256 checksum; the workflow records the actual SHA-256 in each build manifest.

## Verification status

- Static source/callsite audit: confirmed for the identified in-tree caller and B1 Kconfig exclusion.
- Patch application in the GitHub Actions runner: not yet verified.
- Kernel link/build with the patch: not yet verified.
- DTB, BusyBox, package artifact and Panther X2 hardware boot: not yet verified.
