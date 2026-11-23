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
