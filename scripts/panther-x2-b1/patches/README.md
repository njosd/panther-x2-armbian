# Historical B1 kernel patch

`0001-kobject-uevent-config-net-n.patch` is retained only as historical audit material and is **not applied** by the current B1 workflow.

The Linux 6.18.63 source audit found that `net/core/` and `net/core/skbuff.c` remain part of the build with `CONFIG_NET=n`; the original `kfree_skb()` release path has its corresponding implementation. The old patch also returned early for a non-NULL skb without freeing it, changing the original resource-ownership semantics.

Current B1 builds the unmodified locked upstream source. Any future build error must be established by CI logs and a focused source audit before considering a compatibility patch.
