# Panther X2 B2-0 方向二：Linux 网络核心多版本静态差异评估进度（2026-11-24）

## 1. 当前状态与边界

**方向二进行中；本报告只结清已审查的网络初始化、loopback 和 IPv4/通用 TX 上层路径子项，不代表方向二整体结项。**

本轮严格留在 B2-0 方向二：Linux 网络核心。没有进入方向三 STMMAC/DWMAC4/DMA，没有执行设备操作、构建、启动、配置修改、网络测试或实机取证。

本轮目标是比较正常基线与故障版本的 Linux 网络核心代码差异，判断差异是否命中普通本机小 UDP 报文的发送路径。源码差异只作为待评估事实，不自动等同于故障根因。

## 2. 固定源码比较端点与证据等级

| 版本 | 比较端点 | 来源说明 |
|---|---|---|
| 6.1.116 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` | 正常运行基线的源码比较端点；精确安装包构建 source commit 尚未闭环 |
| 6.1.174-rk35xx | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` | 原始 Actions run #296 日志确认的构建 source_hash |
| 6.12.81-rk35xx | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` | 原始 Actions 构建日志锁定的 source commit |

6.1.65、6.1.79、6.1.112 已有正常实机证据，但目前没有足以逐一锁定的精确源码 commit；本报告不伪造其源码端点，也不将 6.1.116 的源码差异直接外推为所有 6.1.y 小版本均相同。

6.18.63 属于 6.18.y，不纳入本轮 6.1.y 最早回归判断，也不为本轮方向二重复追查其历史包身份。

## 3. 网络子系统配置入口与初始化

### 3.1 Kconfig / Makefile 入口

对照 6.1.116、6.1.174、6.12.81：

- `NET` 顶层网络支持入口定义一致。
- `INET` IPv4/IPv6 协议入口定义一致。
- `NETDEVICES` 顶层门控定义一致，均依赖 `NET`。
- 三版 `drivers/net/Makefile` 均以 `CONFIG_NET` 控制 `loopback.o` 编译；loopback 并不是由 `NETDEVICES` 或独立的 `CONFIG_LOOPBACK` 符号控制。
- 以上只确认配置入口关系，不代表已经对三版完整 `.config` 做逐符号全量比较。

### 3.2 Loopback 代码

三版 `drivers/net/loopback.c` 中：
- `loopback_xmit()` 函数体一致；
- `loopback_net_init()` 函数体一致。

其他差异：
- 6.1.174 增加 blackhole netdevice 相关实现和 lockdep 初始化；
- 6.12 调整 loopback per-CPU 统计结构、netns 属性表达及 GSO software feature 标记。

这些变化没有改变 loopback 本地发送函数，也没有进入 Panther 板载 GMAC 的 TX 路径。

### 3.3 网络设备核心初始化

`net/core/dev.c:net_dev_init()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 新增 net_device 结构检查、按 CPU 创建 system page pool、可选 backlog NAPI 线程注册，以及 housekeeping timestamp 初始化。

6.12 的 `net_page_pool_create()` 在 `CONFIG_PAGE_POOL` 启用时，为每个可能 CPU 创建 system page pool，并注册到 XDP page-pool 管理路径。创建失败会使 `net_dev_init()` 在注册 loopback netdevice 之前返回错误。

6.12.81 实际构建配置中 `CONFIG_PAGE_POOL=y`。该初始化路径是 6.12 新增的网络初始化依赖，但已有故障版本运行记录证明网络协议栈及接口实际工作过，因此不能把该初始化失败路径写成已发生故障。它也不是普通本机 TX 数据路径。

### 3.4 IPv4 协议初始化

`net/ipv4/af_inet.c:inet_init()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 将 UDP/TCP `net_protocol` 对象放入 `net_hotdata` 后注册，并为 TCP protocol 设置 `icmp_strict_tag_validation`。

该变化是协议对象存储/初始化结构调整；新增 strict-tag 字段位于 TCP protocol 对象，不是 DHCP 使用的 UDP 发送处理分支。当前没有证据表明它改变普通 UDP 报文发出路径。

## 4. IPv4 输出与 netdevice 发送上层路径

### 4.1 IPv4 输出

比较 `net/ipv4/ip_output.c`：

- `ip_local_out()` 三版函数体一致。
- 6.1.116 到 6.1.174 的 `ip_output()` 增加 RCU read-side 临界区，并通过 `skb_dst_dev_rcu()` 取得目标设备后执行 POSTROUTING hook；这是路由目标设备引用保护变化，没有发现报文内容或输出设备选择规则被改写。
- 6.12 对 `ip_output()` / `ip_finish_output()` 的统计更新位置作调整，将 OUTOCTETS 统计移到分片之后；同时把部分 `dst` 直接访问改为 `dst_rtable()` / `dst_dev()` accessor。当前差异属于路由对象访问和统计时点调整，没有发现改变普通报文提交给 netdevice 的逻辑。

### 4.2 `__dev_queue_xmit()`

- 6.1.116 到 6.1.174 增加对 GSO 分段后 skb list 的特殊处理：当 `validate_xmit_skb()` 将一个 skb 转成多个 segment 时，避免把部分 segment 已发送后的驱动返回值错误地解释成整个 TCP 数据未发送。
- 对单个 skb（`skb->next == NULL`），新旧分支仍按原有驱动返回状态处理；新增逻辑的主要命中条件是 GSO skb list。
- 6.12 在 ingress metadata 初始化处用 `tcx_set_ingress(skb, false)` 替代旧的 `tc_at_ingress` 字段清零，属于 TCX/traffic-control 元数据迁移。

DHCP Discover 是普通小型 UDP 报文，不属于 TCP GSO 分段 skb list；因此目前没有证据表明上述 GSO list 修正命中历史 DHCP 故障报文。

### 4.3 qdisc dequeue / direct transmit

比较 `net/sched/sch_generic.c`：

- `sch_direct_xmit()` 三版函数体一致。
- 6.1.174 起，`qdisc_restart()` / `dequeue_skb()` 增加 packet budget 参数，`try_bulk_dequeue_skb()` 增加按 budget 限制批量 dequeue 的逻辑；6.12 延续该实现。
- 该差异控制 qdisc 批量出队/调度公平性，不改变单个 skb 的驱动调用和返回处理。

### 4.4 TX checksum helper 与不可读 fragment 检查（位置更正）

本轮进一步逐函数比较 `net/core/dev.c`，确认 6.12 新增的 `skb_frags_readable(skb)` 检查**不在 `validate_xmit_skb()` 函数入口**，而是在它可能调用的 `skb_checksum_help()` 软件 checksum fallback 内。此前将该检查归到 `validate_xmit_skb()` 入口的表述不准确，以本节为准。

`skb_checksum_help()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 在 `CHECKSUM_COMPLETE` 和 GSO 快速分支之后、实际读取 skb 数据计算 checksum 之前，增加：
  `if (!skb_frags_readable(skb)) return -EFAULT;`
- `skb_frags_readable()` 实际检查 `!skb->unreadable`；
- 6.12 的 `__skb_fill_netmem_desc()` 在 fragment 使用 `netmem_is_net_iov(netmem)` 时设置 `skb->unreadable=true`。因此该保护针对包含 host 不可直接读取的 net_iov/device-memory fragment 的 skb，而不是普通 page fragment 或普通线性 skb。

调用关系：
`validate_xmit_skb()` → `skb_csum_hwoffload_help()` →（设备不支持当前 skb checksum offload 时）`skb_checksum_help()`。
只有实际进入软件 checksum fallback 且 skb 带 unreadable fragment 时，新检查才会返回 `-EFAULT`，上层 TX 校验路径随后丢弃 skb。

配置差异：
- 6.1.116 与 6.1.174 的 `net/Kconfig` 没有 `NET_DEVMEM` 符号；
- 6.12.81 源码中新增 `CONFIG_NET_DEVMEM`，定义为 `def_bool y`，依赖 `DMA_SHARED_BUFFER`、`GENERIC_ALLOCATOR` 和 `PAGE_POOL`；
- 已核对的 Ophub RK35xx 6.12 配置模板 `kernel-config/release/rk35xx/config-6.12` 同时启用上述依赖及 `CONFIG_NET_DEVMEM=y`。这是模板配置证据；在未取得 6.12.81 最终构建 `.config` 原件前，不把它冒充为运行 Image 的逐项实测配置。

对普通 UDP/DHCP 小包的适用性：
- 6.12 的 `udp4_hwcsum()` 与 6.1.116、6.1.174 函数体一致；
- `udp_send_skb()` 在 6.1.174 和 6.12 的变化位于 `cork->gso_size` 非零的 UDP GSO 分支，以及错误状态读取方式；普通非 GSO UDP datagram 的 checksum 分支没有相应变化；
- `__ip_append_data()` 在 6.12 新增 `MSG_SPLICE_PAGES` 路径，可把用户页 splice 到 skb fragments；普通 UDP sendmsg 不设置该标志时不走该新增分支；
- 常规 DHCP 小型 UDP 报文通常走普通 datagram 路径，不属于 UDP GSO，也没有理由仅凭 NET_DEVMEM=y 推断它包含 net_iov fragment。

因此，这是一条真实存在的 6.12 新增条件性 TX 丢弃路径，但需要同时满足“skb 带 unreadable net_iov fragment”及“软件 checksum fallback 被调用”两个条件。当前没有历史证据证明 Panther 的 DHCP skb 满足任一条件；不得将它认定为故障根因。

## 5. 已复用的方向二既有审计，不重复

以下既有报告直接复用，不重新展开相同函数：

1. `PANTHER-X2-NAPI-SKB-ALLOCATOR-DIFF-AND-READONLY-TRACE-CHECK-20261119.md`：6.1.116 / 6.12.81 的 NAPI skb allocator API、per-CPU cache 保护和失败返回路径。
2. `PANTHER-X2-KERNEL-6.1.116-TO-6.1.174-REGRESSION-WINDOW-STMMAC-DIFF-20261119.md`：6.1.116→6.1.174 提交窗口及 6.1.174 最终 SKB shared-frag/GRO 元数据传播提交。
3. `PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md`：6.1.116 配置闭环与 6.12.81 普通 RX skb 分配失败分支差异。

普通 TX descriptor、DMA mapping/提交/回收、STMMAC 驱动调用属于方向三，不在本报告重复。

## 6. 当前差异判断

| 差异 | 影响范围 | 对普通本机小 UDP / DHCP TX 的当前判断 |
|---|---|---|
| 6.12 system page pool / backlog NAPI 初始化 | 网络设备核心初始化、XDP/backlog | 初始化依赖新增；不是正常 TX 发送步骤，实际初始化已成功 |
| 6.12 net_hotdata / TCP strict-tag 字段 | 协议对象存储、TCP/ICMP 处理 | 不命中 UDP DHCP 发送 |
| 6.1.174 GSO skb-list 处理 | GSO 多 segment 发送 | 不命中单 skb 小型 DHCP 报文 |
| qdisc bulk dequeue budget | 批量出队和调度公平性 | 不改变单 skb 发送语义 |
| 6.12 `skb_checksum_help()` unreadable-frag 检查 | 含 net_iov/device-memory fragment 且进入软件 checksum fallback 的 skb | 条件性路径；普通线性 DHCP 小包未见命中证据 |
| IPv4 output RCU / 统计位置 | 路由引用保护、统计时点 | 未发现改变报文内容或普通设备提交路径 |

**阶段性结论：** 本轮审查到的网络核心差异中，尚未发现一个已证实且命中普通本机小 UDP 报文发送路径的版本回归点。6.12 的 unreadable-frag 检查是新增条件性丢弃路径，保留观察；其余已见变化主要属于 GSO、qdisc batching、初始化和统计/结构调整。

这不是故障根因排除结论，也不表示方向二完成。

## 7. 未验证边界与下一项

未验证：
- 6.1.116 正常运行 Image 的精确源码 commit；
- 历史 DHCP skb 的完整内存形态（是否带 page fragments、是否 linear）；
- 6.12.81 故障窗口是否曾出现 `skb->unreadable`；
- 6.1.65 / 6.1.79 / 6.1.112 的精确源码端点。

本轮已完成 SKB TX checksum fallback、UDP checksum 生成、UDP GSO 与 splice-fragment 分支的源码差异检查。下一项继续方向二中尚未审查的网络核心子系统与配置差异；复用已有 NAPI allocator、GRO/shared-frag 报告，不重做已完成内容。完成方向二全部子项之前，不进入方向三；B2-0 全程只做源码、Kconfig、配置和设备树静态审计，不执行 B1 包的配置、构建、启动或实机试验。


## 8. 本轮追加核验记录：checksum / fragment / UDP GSO

源码端点仍为第 2 节固定的三个 commit。本轮直接读取并比较：
- `net/core/dev.c`：`skb_checksum_help()`、`skb_csum_hwoffload_help()`
- `net/ipv4/udp.c`：`udp4_hwcsum()`、`udp_send_skb()`
- `net/ipv4/ip_output.c`：`__ip_append_data()`
- `net/core/skbuff.c`：`skb_segment()`
- `include/linux/skbuff.h`：`skb_frags_readable()`、`__skb_fill_netmem_desc()`
- `net/Kconfig` 与 Ophub RK35xx 6.12 配置模板。

主要结论：
1. 6.1.116→6.1.174 的 `skb_csum_hwoffload_help()` 变化只涉及 IPv6 extension/jumbo header 的 offload 判定，不适用于 IPv4 DHCP。
2. 6.1.174 的 `skb_segment()` shared-frag 标记传播修正已在既有 6.1.174 提交审计中记录；本轮不重复归因。
3. 6.12 的 unreadable fragment 保护准确位于 `skb_checksum_help()` 软件 checksum fallback；它针对 net_iov/device-memory fragments。
4. 6.12 UDP GSO 条件分支和 `MSG_SPLICE_PAGES` 分支有变化，但不等于普通 UDP datagram 路径发生变化。
5. 目前这几项变化均未形成普通小 UDP/DHCP TX 故障的已证实解释。

本轮仍是源码及配置模板静态审计；没有读取、改写或生成任何 B1 实机测试包，也没有执行任何设备侧操作。


## 9. 本轮追加核验：netdevice feature negotiation、ARP/邻居输出与 IPv4 route key

本轮继续沿网络核心的 TX 前置路径，比较：
- `net/core/dev.c`：`netif_skb_features()`、`netdev_fix_features()`、`netdev_update_features()`、`validate_xmit_vlan()`、`netdev_features_change()`
- `net/core/neighbour.c`：`neigh_resolve_output()`、`neigh_connected_output()`
- `net/ipv4/arp.c`：`arp_solicit()`
- `net/ipv4/route.c`：`ip_route_output_key_hash()`

### 9.1 netdevice feature negotiation

- `netif_skb_features()` 三个端点函数体一致。
- `netdev_update_features()`、`validate_xmit_vlan()`、`netdev_features_change()` 三个端点函数体一致。
- `netdev_fix_features()` 在 6.1.116 与 6.1.174 一致；6.12 新增对 `NETIF_F_GSO_UDP_L4` 的约束：设备没有 IP checksum（IPv4+IPv6）或通用硬件 checksum 能力时，清除 UDP L4 GSO feature。6.12 同时把 TLS TX checksum 依赖检查整理为共用 helper `netdev_has_ip_or_hw_csum()`。
- 这些规则只影响设备声明的 offload feature 组合，尤其 UDP segmentation offload；不会清除普通 UDP checksum 能力本身，也不是普通 UDP datagram 的通用发送开关。
- Panther RK3566 MAC 的具体 feature 位图属于后续驱动方向的审计对象；本节不根据 generic helper 推断该设备实际声明了哪些 feature。

### 9.2 ARP / neighbour 输出

`neigh_resolve_output()`、`neigh_connected_output()` 和 `arp_solicit()` 在三个源码端点函数体一致。

因此，在本轮固定端点中，没有发现 Linux neighbour/ARP 核心的这三个关键函数发生 6.1.116→6.1.174 或 6.1→6.12 的实现变化。该结论只限这些函数，不代表整个 neighbour 子系统所有文件均已审计。

### 9.3 IPv4 route TOS / DSCP key 归一化

`ip_route_output_key_hash()`：
- 6.1.116 与 6.1.174 一致，调用 `ip_rt_fix_tos(fl4)`；
- 6.12 改为 `fl4->flowi4_tos &= INET_DSCP_MASK`，并在 route header 中使用 DSCP/ECN 分离后的 mask；socket scope 由 `ip_sock_rt_scope()` 提供。

这属于 IPv4 route lookup key 对 DSCP 与 ECN 的归一化重构。普通 DHCP Discover 的 IPv4 TOS 通常为 0；目前没有证据表明该变化会改变 Panther 普通 DHCP 广播报文的路由设备选择。不能仅凭函数改写认定路由回归，也不把它标记为已排除的全部策略路由影响。

## 10. 方向二当前覆盖范围更新

本轮新增覆盖：
- TX checksum helper / UDP checksum / UDP GSO / splice fragment；
- netdevice generic feature negotiation；
- neighbour / ARP 输出关键函数；
- IPv4 route TOS/DSCP key 归一化。

目前未发现普通 DHCP 小型 UDP 报文发送路径上已证实的网络核心回归点。仍需继续方向二剩余网络核心子系统和跨版本配置差异核对；本轮结论不代表方向二结项。


## 11. 本轮追加核验：Linux 网络核心 RX 分派、IPv4 输入与 UDP 接收

固定源码端点仍为第 2 节所列 commit。本轮读取：
- `net/core/dev.c`：`__netif_receive_skb_core()`、`__netif_receive_skb_one_core()`、`netif_receive_skb_internal()`、`__netif_receive_skb_list_core()`
- `net/ipv4/ip_input.c`：`ip_rcv()`、`ip_rcv_core()`、`ip_local_deliver_finish()`
- `net/ipv4/udp.c`：`udp_rcv()`、`__udp4_lib_rcv()`、`udp4_csum_init()`、`udp_queue_rcv_one_skb()`、`udp_rcv_segment()`、`__udp_enqueue_schedule_skb()`
- `include/net/inet_hashtables.h`、`net/ipv4/inet_hashtables.c`：UDP socket lookup / reuseport 辅助路径。

### 11.1 通用 RX 分派

- `__netif_receive_skb_one_core()`、`netif_receive_skb()` 三个端点函数体一致。
- `netif_receive_skb_internal()` 在 6.1.116 与 6.1.174 一致；6.12 仅把 timestamp prequeue 状态从 `netdev_tstamp_prequeue` 移入 `net_hotdata.tstamp_prequeue`。
- `__netif_receive_skb_core()` 在 6.1.116 与 6.1.174 一致。6.12 的结构变化包括：generic XDP 调用改为传入 skb 双重指针（允许 XDP 路径替换 skb），以及 packet-type 全局链表改由 `net_hotdata.ptype_all` 持有。
- 这些改动没有改变无 generic XDP 程序时的普通协议分派顺序。generic XDP 分支只有在相应程序实际附着并启用时才执行；仅有 XDP 相关 Kconfig 符号不等于运行时存在 XDP 程序。
- `__netif_receive_skb_list_core()` 的批量分派结构没有发现会改变单包普通 IPv4 分派的语义差异。

### 11.2 IPv4 输入路径

`ip_rcv()`、`ip_rcv_core()`、`ip_local_deliver()` / `ip_local_deliver_finish()` 在三个源码端点的核心函数体一致。普通 IPv4 输入仍经过相同的头部校验、PRE_ROUTING hook 与本地协议分派流程。

本轮没有发现 6.1.116→6.1.174 或 6.1→6.12 在这些 IPv4 输入核心函数中引入新的普通 IPv4 丢包条件。

### 11.3 UDP socket 查找与接收分派

- `udp4_csum_init()` 三版函数体一致。
- 6.1.116 与 6.1.174 的 `udp_rcv()` 使用全局 `udp_table`；6.12 改为从 `dev_net(skb->dev)->ipv4.udp_table` 取得表。
- 6.12 新增 per-network-namespace UDP hash table 管理；但 `udp_set_table()` 对 `init_net` 明确回退到全局 `udp_table`。因此 Panther 常规初始 network namespace 的表选择仍使用全局表；新增分配主要服务于子 network namespace。
- 6.12 的 `__udp4_lib_rcv()` 把旧的 `skb_steal_sock()` 改为 `inet_steal_sock()`。新增 helper 在 skb 已预先关联 socket、且该 socket 是 UDP full socket / reuseport 组成员时，允许按当前报文信息重新执行 reuseport 选择；若 skb 没有预取 socket，或不满足相应 socket 状态/类型条件，则继续走原有 UDP socket lookup。
- 该差异是条件性 socket 选择变化，不是普遍改变所有 UDP 包的端口匹配。当前没有证据证明 Panther DHCP 接收 skb 带有预取 socket，或 DHCP socket 使用 UDP SO_REUSEPORT 组。

### 11.4 UDP GRO / 分段接收

`udp_rcv_segment()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 新增对 `SKB_GSO_UDP`（旧式 UDP fragmentation offload / UFO）类型的显式丢弃，随后才处理 UDP GRO 分段；该分支会增加 socket drop 与 UDP input error 计数。
- 这是 6.12 新增的条件性 RX 丢弃路径，但只针对进入 UDP 接收分段函数、且带有该 GSO 类型的 skb。普通小型 DHCP UDP datagram 不属于 UDP GRO/UFO 分段报文，不能据此认定 DHCP 报文会命中该分支。

### 11.5 UDP socket receive queue 内存管理

`__udp_enqueue_schedule_skb()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 重构接收队列容量检查及内存记账：使用 `rmem + size` 的边界检查、重新读取 `skb_condense()` 后的 truesize，并通过 `udp_rmem_schedule()` / `__sk_mem_schedule()` 申请接收内存，再将 skb 加入 socket receive queue。
- 该差异可能影响接收队列接近上限或 socket 内存分配失败时的丢包/错误返回；不改变正常空闲接收队列中单个小报文的协议解析和 socket 匹配。
- 6.12 `udp_queue_rcv_one_skb()` 对 UDP-Lite 状态位改用 `udp_test_bit()` 并读取 `pcrlen` 的快照；对普通 UDP socket 不进入 UDP-Lite partial coverage 分支。队列失败后的释放改用统一 `sk_skb_reason_drop()`，属于状态读取与 skb 释放/原因记录整理。

### 11.6 RX 路径阶段性判断

| 差异 | 条件 | 对普通 DHCP 小 UDP 接收的判断 |
|---|---|---|
| generic XDP skb 双重指针 | generic XDP 程序实际附着 | 未发现无程序时改变普通分派 |
| UDP `inet_steal_sock()` | skb 预取 socket 且命中 UDP reuseport 条件 | 条件性 socket 选择变化；无 DHCP 命中证据 |
| UDP UFO 丢弃 | skb 带 `SKB_GSO_UDP` 并进入接收分段路径 | 不属于普通小 UDP datagram |
| UDP receive queue 记账重构 | 接收队列接近上限或内存调度失败 | 保留为资源压力候选；无历史 DHCP 队列耗尽证据 |
| IPv4 input 核心函数 | 常规 IPv4 RX | 三版关键函数一致 |

**阶段性结论：** 当前接收路径审查发现了 6.12 的 XDP skb 可替换、UDP reuseport 预取 socket 选择、UFO 丢弃及 socket receive queue 内存管理变化；这些均有明确触发条件。尚无证据表明它们解释 Panther 历史普通 DHCP 小 UDP 接收异常。

## 12. 本轮配置差异补充：网络核心 Kconfig 模板

### 12.1 证据等级与模板身份

- 6.1.116 真实运行配置已由既有报告完成全量解析：7,677 个符号与对应 Ophub general `config-6.1` 模板完全一致，符号差异为 0。模板 blob SHA：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`。
- 6.12.81 既有运行配置报告只确认了一组关键符号与当时锁定模板一致（包括 `CONFIG_PAGE_POOL=y`、`CONFIG_NET_RX_BUSY_POLL=y`、`CONFIG_XDP_SOCKETS=y`）；该报告没有宣称完成整个最终 `.config` 的逐符号比较。
- 本轮另行读取的 RK35xx `config-6.12` 候选模板来自 `ophub/kernel@bfc9b24f64cf30c3499295b484bbcabddbcc18b6`，当前文件 blob SHA 为 `6c7714f5668362dd4ae9c4d1a7eb8249e6b23de5`。既有运行配置报告记录的模板 blob SHA 是 `966f4b6ac7c0ad59179d6ae272423500601fab07`，与本轮取得的 blob SHA 不同。两者属于不同模板版本/快照的可能性尚待核对；本节只把本轮读取结果称为“候选模板”，不冒充 6.12.81 最终构建配置。

### 12.2 两个候选模板中已核对的网络符号

| 符号 | 6.1.116 general config-6.1 | 当前读取的 6.12 RK35xx config-6.12 | 差异含义 / 证据边界 |
|---|---|---|---|
| `CONFIG_NET` / `CONFIG_INET` / `CONFIG_NETDEVICES` | y | y | 核心网络支持均启用 |
| `CONFIG_NET_NS` | y | y | network namespace 均启用 |
| `CONFIG_BPF` / `CONFIG_BPF_SYSCALL` | y | y | BPF 基础能力均启用，不代表有程序附着 |
| `CONFIG_XDP_SOCKETS` | y | y | AF_XDP 支持均编入 |
| `CONFIG_NET_RX_BUSY_POLL` | y | y | RX busy-poll 支持均启用 |
| `CONFIG_PAGE_POOL` | y | y | page-pool 支持均启用 |
| `CONFIG_NET_DEVMEM` | 不存在 | y | 6.12 新增 netdev memory 相关能力；是否进入特定 skb 路径仍取决于运行时使用 |
| `CONFIG_IP_PNP` / DHCP / BOOTP / RARP | 全部 not set | y | 6.12 候选模板增加内核启动阶段 IP autoconfiguration 能力；与用户空间 DHCP 客户端是不同机制，是否实际生效还取决于最终配置和启动参数 |
| `CONFIG_IPV6` | y | m | IPv6 从 built-in 变为 module（候选模板） |
| `CONFIG_VLAN_8021Q` | y | m | VLAN 802.1Q 从 built-in 变为 module（候选模板） |
| `CONFIG_INET_DIAG` | y | m | inet diagnostics 从 built-in 变为 module（候选模板） |
| `CONFIG_NETFILTER` | y | y | 两套模板均启用 |
| `CONFIG_BRIDGE` | m | m | 两套模板均为模块 |
| `CONFIG_NET_CLS_BPF` / `CONFIG_NET_ACT_BPF` | m / m | m / m | 两套模板一致 |

以上表格是两个指定配置模板之间的静态差异，不等于 6.12.81 运行 Image 的最终符号差异。尤其 `CONFIG_IP_PNP_DHCP` 只表示内核 IP autoconfiguration 功能可用，不应与 initramfs/userspace DHCP client 混为一谈。

### 12.3 配置差异结论

- 两个模板的基础网络栈、BPF、AF_XDP、RX busy-poll、page-pool、netfilter 等多数关键入口相同。
- 6.12 候选模板增加 `NET_DEVMEM` 与 kernel IP autoconfiguration 选项，并把 IPv6、802.1Q、INET_DIAG 从 built-in 调整为 module。
- 这些差异需在后续配置闭环中按“最终 .config 是否实际包含、相关模块是否可用、运行时是否启用”分层判断；不能仅凭模板差异推断故障。
- 本轮不修改任何 B1 构建配置、不生成配置文件，也不做实机验证。

## 13. 方向二覆盖范围与下一项

本轮新增覆盖 Linux RX 通用分派、IPv4 输入、UDP socket lookup、UDP receive queue 与网络核心 Kconfig 模板差异。此前 TX、checksum、GSO、ARP/neighbour、IPv4 route key、初始化与 NAPI allocator 证据继续复用。

下一项仍在方向二：整理并核对网络核心中 packet socket / AF_PACKET、VLAN/bridge 接收分派以及 netfilter ingress/PREROUTING 相关 Kconfig 与调用链，优先判断它们是否改变普通未打 VLAN 标签、未桥接的 IPv4/UDP 流量。方向二未完成前不进入方向三。B2-0 全程只做不同版本源码、Kconfig、最终配置证据及设备树静态差异审计，不涉及 B1 生成包的实机配置、构建、启动或网络试验。


## 14. 本轮追加核验：AF_PACKET、VLAN/bridge RX 与 Netfilter ingress

固定源码端点仍为第 2 节所列三个 commit。本轮读取：
- `net/packet/af_packet.c`：`packet_rcv()`、`packet_rcv_spkt()`、`tpacket_rcv()`、`packet_create()`
- `net/8021q/vlan_core.c`：`vlan_do_receive()`
- `net/bridge/br_input.c`：`br_handle_frame()`、`br_pass_frame_up()`
- `net/bridge/br_private.h`：`br_mst_is_enabled()`
- `net/core/dev.c`：`nf_ingress()` 与 ingress hook 调用位置
- `net/netfilter/core.c`：`nf_hook_slow()`、`nf_register_net_hook()`
- 相关 packet / bridge / VLAN / netfilter Kconfig。

### 14.1 AF_PACKET 接收

- `packet_rcv_spkt()` 与 `tpacket_rcv()` 三个端点函数体一致（TPACKET 声明位置相邻，不应将声明区域当成实现差异）。
- `packet_rcv()` 在 6.1.116 与 6.1.174 一致；6.12 改变抓包 snaplen 计算：
  - 6.1：`snaplen = skb->len`
  - 6.12：`snaplen = skb_frags_readable(skb) ? skb->len : skb_headlen(skb)`
- 该变化在 skb fragment 不可由 host 读取时，只让 AF_PACKET 的抓包/过滤可见长度限制在线性 head 部分，避免按完整 skb 长度读取不可读 fragment。它改变的是 PF_PACKET 用户态抓包可见内容，不是普通 IPv4/UDP 协议接收函数的丢包条件。
- `packet_create()` 在 6.12 有初始化/错误标签整理；三版均保留 CAP_NET_RAW 权限检查、SOCK_DGRAM/SOCK_RAW/SOCK_PACKET 类型检查、packet socket 建立及 protocol hook 注册。未发现普通 IP 收包路径因此改变。
- `CONFIG_PACKET`、`CONFIG_PACKET_DIAG` 在两个已读取配置模板中均为 y。AF_PACKET 功能编入不表示系统一定运行 tcpdump 或其他 packet socket 监听程序。

### 14.2 VLAN RX

`vlan_do_receive()` 三个源码端点函数体一致。它仅在 skb 存在硬件 VLAN tag 时按 VLAN protocol/ID 查找 VLAN net_device；匹配后切换 skb->dev、必要时恢复 VLAN header、清理硬件 tag 并更新 VLAN 统计。

因此，普通未打 VLAN 标签的 IPv4/UDP skb 不会因为本函数的版本变化而改变路径；本轮没有发现该函数在 6.1.116→6.1.174 或 6.1→6.12 有实现差异。

配置模板差异：
- 6.1 general `config-6.1`：`CONFIG_VLAN_8021Q=y`
- 当前 6.12 RK35xx `config-6.12` 候选模板：`CONFIG_VLAN_8021Q=m`
- 两个模板均为 `CONFIG_BRIDGE_VLAN_FILTERING=y`。该选项依赖 BRIDGE 与 VLAN_8021Q；6.12 中 VLAN 驱动模块化，意味着相关 VLAN 功能需模块可用/加载后才能使用，不代表无 VLAN 标签的物理接口普通 IPv4/UDP 自动经过 VLAN 子设备路径。

### 14.3 Bridge RX

`br_handle_frame()` 的变化仅在网卡设备注册了 bridge RX handler、数据包确实进入 Linux bridge port 时相关：
- 6.1.116→6.1.174：MST helper 从接收 bridge 对象改为接收 bridge port；helper 同时增加对 port VLAN group 指针的 RCU 检查，以规避 port 删除竞争。调用点相应调整。
- 6.12：`br_handle_frame()` 移除原先的 `br_offload_input(p, skb)` 快速处理调用，并在 bridge skb control block 初始化后设置 `br_tc_skb_miss_set(skb, false)`；MST helper 继续使用 port 参数。
- `br_pass_frame_up()` 三个端点函数体一致。
- 这些是 bridge/switchdev/TC offload 集成路径变化。当前没有证据证明 Panther 故障接口处于 Linux bridge port，也没有证据证明 bridge RX handler 对普通物理接口生效。不能把这组变化当成未桥接接口的普通 IPv4/UDP 根因。

### 14.4 Netfilter ingress / hook dispatch

- `net/core/dev.c` 的 `nf_ingress()` 仅在 `nf_hook_ingress_active(skb)` 为真时执行；active 状态来自实际注册的 ingress hook。代码先交付待处理 packet_type，再执行 ingress hook；无活动 hook 时直接返回，不增加 Netfilter ingress 拦截。
- `__netif_receive_skb_core()` 在三个端点均保留 ingress hook 与 VLAN RX handler 的先后处理结构。6.12 相关 timestamp 状态变量迁入 `net_hotdata`，不是新增默认 ingress drop。
- `nf_register_net_hook()` 与 `nf_register_net_hooks()` 三版函数体一致；`NFPROTO_INET` 的 ingress hook 注册仍按 INET ingress 规则处理，其他 INET hook 同时注册 IPv4/IPv6。
- `nf_hook_slow()` 在 6.1.116 与 6.1.174 一致；6.12 将 `NF_STOLEN` 从 default 分支单独列出，并返回 verdict 中的 error 编码；其他非标准 verdict 改为 WARN_ON_ONCE。常规 `NF_ACCEPT`、`NF_DROP`、`NF_QUEUE` 分支保持相同。普通规则未返回带错误码的 NF_STOLEN 时，不应推断此变化会改变报文命运。
- `CONFIG_NETFILTER_INGRESS`、`CONFIG_NETFILTER_EGRESS` 在 Kconfig 三个源码端点均为 default y，并 select `NET_INGRESS` / `NET_EGRESS`。编译支持不等于实际有 ingress hook 或规则注册。
- IP `PREROUTING` 仍需有对应 IPv4 Netfilter hook 注册者（例如 iptables/nftables 规则链）才会执行相应 hook；`CONFIG_NETFILTER=y` 本身不是丢包规则。

### 14.5 配置模板交叉对照

以下仅比较已固定来源的模板文件，不冒充 6.12.81 最终构建 `.config`：
- 6.1：`ophub/kernel@8f6eb6e392d68b89a4708c8c45caf9d3f46eadaa`，`kernel-config/release/general/config-6.1`，blob SHA `c5e4598301c3ef3675be0058b99b9b6044a14bbf`。
- 6.12 候选：`ophub/kernel@bfc9b24f64cf30c3499295b484bbcabddbcc18b6`，`kernel-config/release/rk35xx/config-6.12`，blob SHA `6c7714f5668362dd4ae9c4d1a7eb8249e6b23de5`。

| 符号 | 6.1 模板 | 6.12 候选模板 | 判断 |
|---|---:|---:|---|
| `NET_INGRESS` / `NET_EGRESS` | y / y | y / y | 一致 |
| `NETFILTER_INGRESS` / `NETFILTER_EGRESS` | y / y | y / y | 一致 |
| `PACKET` / `PACKET_DIAG` | y / y | y / y | 一致 |
| `BRIDGE` | m | m | 一致 |
| `BRIDGE_VLAN_FILTERING` | y | y | 一致 |
| `VLAN_8021Q` | y | m | 模块形态变化 |
| `BRIDGE_NETFILTER` | m | m | 一致 |
| `NF_CONNTRACK` | y | y | 一致 |
| `NF_TABLES` | m | y | nftables 核心从模块变为 built-in |

模板差异本身不证明 nftables 规则集内容、hook 是否注册或规则是否实际加载。尤其 `NF_TABLES=y` 仅代表内核具备相应功能，不代表有一条规则会丢弃 DHCP/UDP。

### 14.6 本轮结论

| 子系统 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通未桥接、未打 VLAN 标签 IPv4/UDP 的判断 |
|---|---|---|---|
| AF_PACKET | packet_rcv 核心行为一致 | unreadable fragment 时限制抓包 snaplen | 用户态抓包可见性变化，不是协议栈通用 drop |
| VLAN RX | vlan_do_receive 一致 | vlan_do_receive 一致 | 无 VLAN tag 不走该子设备切换路径 |
| Bridge RX | MST helper 改为 port-aware | bridge offload/TC miss bookkeeping 调整 | 仅 bridge port 条件路径 |
| Netfilter ingress | hook dispatch 结构一致 | NF_STOLEN 错误返回处理整理 | 实际 hook 注册和规则 verdict 才会影响报文 |
| Kconfig | ingress/egress 与 packet 功能相同 | VLAN 模块化、NF_TABLES built-in 化 | 配置能力差异，不等于运行时规则差异 |

当前没有发现能够解释“未桥接、未打 VLAN 标签、普通 IPv4/UDP”收包故障的已证实 AF_PACKET/VLAN/bridge/Netfilter 核心回归点。条件性变化已保留，待结合对应最终配置和既有运行证据判断。

## 15. 方向二下一项

本轮完成 AF_PACKET、VLAN RX、bridge RX、Netfilter ingress/注册核心与相关 Kconfig 模板差异核对。方向二仍未结项。

下一项继续审计 IPv4 Netfilter PREROUTING/LOCAL_IN 与 conntrack/NAT hook 的核心注册、调用顺序和 Kconfig 依赖，区分“内核具备功能”与“实际 hook/ruleset 生效”。B2-0 仍然只做多版本源码、Kconfig、配置及设备树静态审计，不涉及 B1 包的实机配置、构建、启动或网络试验。

## 16. 本轮追加核验：IPv4 PREROUTING/LOCAL_IN、conntrack 与 NAT hook

固定源码端点仍为第 2 节列出的 6.1.116、6.1.174、6.12.81 commit。本轮重点核对：
- `net/netfilter/nf_conntrack_proto.c`：IPv4 conntrack hook ops、注册/注销；
- `net/netfilter/nf_conntrack_core.c`：`nf_conntrack_in()`、`resolve_normal_ct()`、`init_conntrack()`；
- `net/netfilter/nf_nat_core.c`：`nf_nat_inet_fn()`、`nf_nat_register_fn()`；
- `net/ipv4/netfilter/iptable_filter.c`、`iptable_nat.c`：legacy filter/NAT 表及 hook 注册；
- `net/netfilter/Kconfig`、`net/ipv4/netfilter/Kconfig` 与两个配置模板中的 conntrack/NAT 符号。

### 16.1 IPv4 conntrack hook 注册与顺序

三个源码端点的 IPv4 conntrack hook 集合及优先级一致：

| Hook | 函数 | 优先级 | 作用位置 |
|---|---|---:|---|
| `NF_INET_PRE_ROUTING` | `ipv4_conntrack_in()` → `nf_conntrack_in()` | `NF_IP_PRI_CONNTRACK` | IPv4 路由决策前跟踪 |
| `NF_INET_LOCAL_OUT` | `ipv4_conntrack_local()` | `NF_IP_PRI_CONNTRACK` | 本机发出的 IPv4 包 |
| `NF_INET_POST_ROUTING` | confirm hook | `NF_IP_PRI_CONNTRACK_CONFIRM` | 发送路径连接确认 |
| `NF_INET_LOCAL_IN` | confirm hook | `NF_IP_PRI_CONNTRACK_CONFIRM` | 本机接收路径连接确认 |

`nf_ct_netns_do_get()` 在三个端点的 IPv4 注册流程一致：首次引用时先启用 IPv4 defragmentation，再通过 `nf_register_net_hooks()` 注册上述 hook；后续引用只增加 users 计数；最后一次释放时注销 hook 并关闭 defragmentation。注册失败会回退 users 计数。

重要边界：conntrack 内核代码存在，并不自动意味着 IPv4 PREROUTING hook 已注册。是否注册取决于 conntrack netns 引用者/初始化路径；本轮源码确认了注册机制，但没有将其等同于 Panther 某次运行时的 hook 状态。

### 16.2 6.12 confirm hook 的重构

6.1.116 与 6.1.174 使用 `ipv4_confirm()` 包装函数，hook ops 的 POST_ROUTING/LOCAL_IN 项均指向该函数；6.12 将 hook ops 改为指向通用 `nf_confirm()`。

6.1 wrapper 的处理要点：
- skb 没有关联 conntrack，或状态为 `IP_CT_RELATED_REPLY` 时直接调用 `nf_conntrack_confirm()`；
- POST_ROUTING 的 L3 master/VRF 特殊情况返回 ACCEPT；
- 其他情况计算 IPv4 transport offset，再调用通用 confirm/helper 处理。

6.12 的通用 `nf_confirm()` 将 IPv4/IPv6 处理统一：
- 无 conntrack 或 VRF postrouting 仍返回 ACCEPT；
- 无 helper 且无需 sequence adjustment 时直接 `nf_conntrack_confirm()`；
- related-reply 直接 confirm；
- 有 helper/sequence adjustment 时按 conntrack L3 协议计算 transport offset，再执行 helper/seq-adjust，最后 confirm。

对普通 IPv4 UDP 包，如果没有 conntrack helper、没有 sequence adjustment，6.1 与 6.12 均走直接 confirm；6.12 的变化主要是将 IPv4 wrapper 逻辑并入通用 IPv4/IPv6 实现。当前未发现普通 DHCP UDP 在此处新增丢弃条件。

### 16.3 conntrack tuple lookup 与内存分配错误处理

- `nf_conntrack_in()` 在 6.1.116 与 6.1.174 函数体一致；6.12 去掉若干仅用于调试的 `pr_debug()`，并保留 invalid/drop 计数、tuple 解析、conntrack 建立、协议跟踪和 verdict 处理流程。
- `resolve_normal_ct()` 在 6.1.116 与 6.1.174 一致；6.12 将 tuple 解析失败的调试输出去掉，并将状态判断从 `test_bit()` 整理为 `READ_ONCE(ct->status)` mask 检查。
- 特别核对了 `init_conntrack()`：6.1 已经会将 `__nf_conntrack_alloc()` 的错误指针向上传递；`resolve_normal_ct()` 对 `IS_ERR(h)` 返回负错误码；`nf_conntrack_in()` 将此类资源压力错误计入 drop 并返回 NF_DROP。6.12 保留相同错误传播结构。因此不能把“6.12 开始在 conntrack 分配失败时丢包”作为新回归；该语义在 6.1.116 已存在。
- 6.12 `resolve_normal_ct()` 仍在找不到既有 tuple 时调用 `init_conntrack()`；对普通 UDP 首包，只有 conntrack hook 实际启用且建立连接跟踪项时才会进入该分配路径。

### 16.4 NAT hook 与 legacy filter 表

`iptable_nat.c` 的 IPv4 NAT hook ops 三个端点一致，覆盖：
- PREROUTING：`NF_IP_PRI_NAT_DST`；
- POSTROUTING：`NF_IP_PRI_NAT_SRC`；
- LOCAL_OUT：`NF_IP_PRI_NAT_DST`；
- LOCAL_IN：`NF_IP_PRI_NAT_SRC`。

NAT 表初始化先建立表，再逐项调用 `nf_nat_ipv4_register_fn()` 注册 hook；注册中途失败会注销已注册项并释放资源。6.1.116、6.1.174、6.12 的 `iptable_nat` 注册结构与 hook 位置一致。6.12 `nf_nat_register_fn()` 仅将 `kmemdup()` 改为带元素数量参数的 `kmemdup_array()`，属于数组分配 API 整理；`nf_nat_inet_fn()` 三个端点函数体一致。

`iptable_filter.c` 的 per-net 初始化、filter 表模板注册和 hook ops 分配在三个端点一致。filter 表本身覆盖 LOCAL_IN、FORWARD、LOCAL_OUT；它不是 PREROUTING hook。故普通到本机的入站包先经过已注册的 PREROUTING conntrack/DNAT hook，再路由到本机，随后才可能经过 LOCAL_IN filter hook，最后进行 conntrack confirm。具体规则 verdict 取决于实际加载的表和规则集。

### 16.5 Kconfig 与模板差异

两个指定模板仍是静态候选对照，不代表 6.12.81 最终运行 `.config`：
- 6.1 模板 blob SHA：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`；
- 6.12 RK35xx 候选模板 blob SHA：`6c7714f5668362dd4ae9c4d1a7eb8249e6b23de5`。

| 符号 | 6.1 模板 | 6.12 候选模板 | 说明 |
|---|---:|---:|---|
| `NF_CONNTRACK` | y | y | 核心 conntrack 均内建 |
| `NF_CONNTRACK_MARK/ZONES/PROCFS/EVENTS` | y | y | 选定子功能一致 |
| `NF_NAT` | m | y | NAT 核心从模块变为内建 |
| `NETFILTER_XTABLES` | m | y | xtables 核心从模块变为内建 |
| `NETFILTER_XT_NAT` | m | y | xtables NAT glue 从模块变为内建 |
| `IP_NF_IPTABLES` | m | m | legacy iptables 顶层仍为模块 |
| `IP_NF_IPTABLES_LEGACY` | 无独立符号 | m | 6.12 拆分出 legacy 实现符号 |
| `IP_NF_FILTER` | m | m | filter 表仍为模块 |
| `IP_NF_NAT` | m | m | iptables NAT 表仍为模块 |
| `NF_DEFRAG_IPV4` | y | y | IPv4 defrag 均内建 |

Kconfig 结构变化：
- 6.12 的 `IP_NF_FILTER`、`IP_NF_NAT` 显式 select `IP_NF_IPTABLES_LEGACY`，将旧式 iptables 实现拆分成单独符号；这是构建/模块依赖关系变化，不代表 hook 优先级或规则匹配语义变化。
- `IP_NF_MATCH_RPFILTER` 在 6.12 增加 `NFT_COMPAT` 作为可选依赖路径；只影响 rpfilter match 的配置可用性，不是默认收包路径的强制组件。
- `NF_NAT`、`NETFILTER_XTABLES`、`NETFILTER_XT_NAT` 在候选模板中从 m 变为 y，而具体 `IP_NF_FILTER`/`IP_NF_NAT` 仍为 m。此差异可能影响模块依赖、装载顺序和镜像/模块打包完整性；是否影响某个运行系统，必须以该版本最终 `.config`、模块清单及实际加载证据确认。
- 由于 6.12 模板 SHA 与先前运行配置报告记录的模板 SHA 不同，以上 6.12 值仍只能称为候选模板值，不能回填成 6.12.81 的最终配置结论。

### 16.6 本轮阶段性结论

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 结论 |
|---|---|---|---|
| IPv4 conntrack hook 位置/优先级 | 一致 | 一致 | 未发现普通 PREROUTING/LOCAL_IN 顺序变化 |
| conntrack tuple lookup | 一致 | debug 输出和状态读取方式整理 | 未发现普通 UDP tuple 匹配语义变化 |
| conntrack allocation failure | 错误指针传播语义已存在 | 延续既有行为 | 不是 6.12 新增的资源压力 drop |
| conntrack confirm | 一致 | IPv4 wrapper 并入通用 nf_confirm | 普通 IPv4 无 helper/seqadj 路径等价 |
| iptables filter hook | 一致 | 一致 | 规则表/模块是否加载决定是否执行 |
| iptables NAT hook | 一致 | 一致 | 规则表/模块是否加载决定是否执行 |
| Kconfig | 本轮未见该窗口核心配置逻辑变化 | legacy 拆分及核心模块化形态变化 | 需结合最终配置与模块打包核验 |

**对普通未桥接、无 VLAN 标签的 IPv4/UDP 流量：** 当前没有发现 6.1.116→6.1.174 的 conntrack/NAT hook 核心回归，也没有发现 6.12 在普通 PREROUTING/LOCAL_IN 顺序上引入新的丢包点。保留的主要差异是 6.12 Netfilter/iptables 组件的 built-in/module 组合变化，后续需与确切最终配置及模块打包证据对齐。

## 17. 方向二下一项

本轮完成 IPv4 conntrack hook 注册、confirm、tuple lookup、NAT hook 和 legacy filter/NAT Kconfig 差异核对。方向二仍未结项。

下一项继续核对 netfilter 之外、但处于 IPv4 路由与本机交付边界的关键网络核心配置/代码：IPv4 defragmentation、IP checksum/fragment handling、local delivery 与相关 Kconfig/module 依赖，优先围绕普通 DHCP/UDP 包的实际路径。B2-0 继续限定为源码、Kconfig、配置及设备树静态差异审计，不涉及 B1 包的实机配置、构建、启动或网络试验。
