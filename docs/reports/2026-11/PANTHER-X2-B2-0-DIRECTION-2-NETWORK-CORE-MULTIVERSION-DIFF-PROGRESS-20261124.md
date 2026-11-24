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


## 18. 本轮追加核验：IPv4 header checksum、分片重组与本机交付

本轮继续使用第 2 节固定的三个源码端点，直接读取并比较：
- `net/ipv4/ip_input.c`：`ip_rcv_core()`、`ip_rcv()`、`ip_local_deliver()`、`ip_local_deliver_finish()`、`ip_protocol_deliver_rcu()`
- `net/ipv4/ip_fragment.c`：`ip4_frag_init()`、`ip_frag_queue()`、`ip_frag_reasm()`、`ip_defrag()`、`ipv4_frags_init_net()`
- `net/ipv4/inet_fragment.c`：`inet_frag_find()`、`inet_frag_queue_insert()`、`inet_frag_reasm_finish()`、队列创建和释放路径
- `net/ipv4/netfilter/nf_defrag_ipv4.c`：IPv4 conntrack defrag hook 的启用、注册与停用
- `net/Kconfig`、`net/ipv4/Kconfig`、`net/ipv4/netfilter/Kconfig`、对应 Makefile，以及已固定来源的 6.1/6.12 配置模板。

### 18.1 IPv4 header checksum 与长度检查

`ip_rcv_core()` 三个端点均保留相同的基本检查顺序：
1. 确保 skb 至少包含 IPv4 基本头；
2. 检查 `ihl >= 5`、IPv4 version；
3. 拉取完整 IPv4 header；
4. 通过 `ip_fast_csum()` 校验 IPv4 header checksum；
5. 检查 IP total length 不小于 header 长度，且 skb 实际长度足够；
6. 按 IP total length 修剪以太网填充，并设置 transport header。

6.1.116 与 6.1.174 的 `ip_rcv_core()` 源码一致。6.12 仍使用 `ip_fast_csum()`，但将长度读取从 `ntohs(iph->tot_len)` 改为 `iph_totlen(skb, iph)`。

`iph_totlen()` helper 本身在 6.1.116 和 6.12 的 `include/linux/ip.h` 中均存在且实现一致：只有当 skb 是 TCP GSO、且 IPv4 `tot_len` 字段为 0 时，才以 skb 长度作为总长度回退值。普通 UDP/DHCP skb 不满足 TCP GSO 条件，仍使用 IPv4 header 的 `tot_len`。因此这是针对特殊 TCP GSO 表示方式的兼容处理，不是普通 UDP 新增或改变的长度校验条件。

### 18.2 本机交付与 UDP 协议分派

`ip_local_deliver()`、`ip_local_deliver_finish()`、`ip_protocol_deliver_rcu()` 三个端点函数体一致：
- 只有 `ip_is_fragment(ip_hdr(skb))` 为真时，`ip_local_deliver()` 才调用 `ip_defrag(..., IP_DEFRAG_LOCAL_DELIVER)`；
- 分片重组成功或报文未分片后，进入 `NF_INET_LOCAL_IN`；
- LOCAL_IN hook 放行后，`ip_local_deliver_finish()` 去掉 IPv4 header，再由 `ip_protocol_deliver_rcu()` 按 IPv4 protocol number 分派到 UDP/TCP/raw handler。

因此普通未分片 IPv4/UDP 包不进入 IPv4 fragment queue。LOCAL_IN 是否会改变报文命运仍取决于实际注册的 hook 与规则 verdict；函数本身三个版本没有变化。

### 18.3 IPv4 分片队列与重组

6.1.116 与 6.1.174：
- `ip_frag_queue()`、`ip_frag_reasm()`、`ip_defrag()` 的函数体一致；
- `inet_fragment.c` 的 blob SHA 相同：`834cdc57755f7f0cee83b495981427be904308cb`；
- `nf_defrag_ipv4.c` 的 blob SHA 相同：`e61ea428ea1872077ec6c2917b8c511518a692d8`。

6.1.116 的 `ip4_frag_init()` 使用旧式 `inet_getpeer_v4(..., 1)` 获取 peer；6.1.174 改为在 RCU read-side 临界区内获取 peer，并显式执行 `refcount_inc_not_zero()`，之后将引用写入队列。这是 fragment peer 对象生命周期/引用计数保护调整，不改变普通未分片报文路径。

6.12 相比 6.1：
- `ip_frag_queue()` 增加 SKB drop-reason 记录（例如重复 fragment），并使用新的 skb drop reason 释放接口；分片 offset/end 计算、末片长度一致性检查、fragment 插入、重组触发条件和 overlap 处理主逻辑保持一致。
- `ip_frag_reasm()` 的核心重组、ECN 合并、最大长度检查、重建 IPv4 header checksum 的逻辑一致。
- `ip_defrag()` 对目标设备的读取改用 `skb_dst_dev()` accessor；其查找队列、加锁、排队、返回结果结构一致。
- `ip4_frag_init()` 延续 6.1.174 的 RCU/refcount peer 获取方式。
- `inet_frag_queue_insert()` 三个端点函数体一致，仍区分重复 fragment 与 overlap；`inet_frag_find()` 的高水位检查、rhashtable 查找/创建和引用计数结构一致。
- `inet_frag_reasm_finish()` 的时间戳字段从旧的 `mono_delivery_time` 改为 `tstamp_type`，属于 skb 时间戳元数据结构调整，不改变分片完整性判定或普通 UDP 交付。

IPv4 fragment queue 在内存分配失败、超过内存阈值、队列超时、长度不一致、重复/重叠 fragment、ECN 组合非法或重组包超过 65535 字节时，仍可能丢弃该分片数据报。这些是分片报文本身的条件性失败路径；没有证据表明它们会处理普通未分片 DHCP/UDP 报文。

### 18.4 Netfilter IPv4 defragmentation hook

三个端点的 `nf_defrag_ipv4.c` 都在 IPv4 PRE_ROUTING 与 LOCAL_OUT 注册 defrag hook，优先级为 `NF_IP_PRI_CONNTRACK_DEFRAG`；仅当 `ip_is_fragment(ip_hdr(skb))` 为真时才收集分片。启用采用 users 引用计数，首次启用注册 hook，最后一次 disable 注销 hook。

6.12 的差异：
- 对 socket `nodefrag` 状态的读取改用 `inet_test_bit(NODEFRAG, sk)`；
- 新增 `nf_defrag_hook` 描述对象，并通过 RCU 发布/撤销 `nf_defrag_v4_hook`，用于 defrag hook 的动态启用接口；
- hook 位置、优先级、fragment 条件判断和用户计数注册/注销主流程保持一致。

该 hook 并非因 `CONFIG_NF_DEFRAG_IPV4` 编译启用就必然对每个 skb 执行；需要相关 Netfilter/conntrack 使用者实际启用它。未分片 UDP 不进入 gather-fragments 分支。

### 18.5 Kconfig / Makefile 依赖

源码结构确认：
- `CONFIG_INET` 是 IPv4/IPv6 Internet protocol stack 的基础 bool 入口。
- `net/ipv4/Makefile` 将 `ip_input.o`、`ip_fragment.o`、`inet_fragment.o` 列入 `obj-y`；这些 IPv4 输入和核心分片实现属于 INET 核心构建对象，不由 `CONFIG_NF_DEFRAG_IPV4` 单独决定。
- `CONFIG_NF_DEFRAG_IPV4` 在 `net/ipv4/netfilter/Kconfig` 中为 tristate，所在菜单依赖 `INET && NETFILTER`，默认 n。它控制 Netfilter conntrack defrag hook 支持，不等同于 IPv4 核心 `ip_defrag()` 本身。
- `CONFIG_IP_MULTIPLE_TABLES` 为 bool，依赖 `IP_ADVANCED_ROUTER` 并 select `FIB_RULES`；它控制策略路由规则实现，不控制 IP header checksum、fragment queue 或 local-delivery 函数。
- 6.1 general 模板 blob SHA `c5e4598301c3ef3675be0058b99b9b6044a14bbf` 与 6.12 RK35xx 候选模板 blob SHA `6c7714f5668362dd4ae9c4d1a7eb8249e6b23de5` 中，`INET`、`IP_ADVANCED_ROUTER`、`IP_MULTIPLE_TABLES`、`NETFILTER`、`NF_CONNTRACK`、`NF_DEFRAG_IPV4` 均为 y。
- 以上仍是指定模板值，不冒充 6.12.81 最终构建 `.config`；实际模块/内建形态必须以最终配置和模块清单为准。

### 18.6 本轮结论

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通未分片 DHCP/UDP 的判断 |
|---|---|---|---|
| IPv4 header checksum | `ip_rcv_core()` 一致 | 仍调用 `ip_fast_csum()` | 未发现新 checksum 丢弃条件 |
| IP total length | 一致 | 改用 `iph_totlen()`；仅 TCP GSO 且 tot_len=0 时回退 skb 长度 | 普通 UDP 仍读取 header tot_len |
| 本机交付 / LOCAL_IN | 核心函数一致 | 核心函数一致 | 路径与 hook 入口未变 |
| fragment queue | 主函数一致；peer 引用获取改为 RCU/refcount 安全方式 | drop-reason 与 skb 时间戳/accessor 调整，重组主逻辑一致 | 普通未分片包不进入 |
| Netfilter defrag | hook 位置、优先级、启用计数一致 | 增加 RCU 动态 hook 发布及 NODEFRAG bit accessor | 只对实际启用 hook 且确为 fragment 的 skb 生效 |
| Kconfig | 关键入口一致 | INET / policy routing / NF_DEFRAG_IPV4 入口语义一致 | 模板均启用；最终配置仍需独立闭环 |

**阶段性结论：** 本轮没有发现 6.1.116→6.1.174 在 IPv4 header checksum、分片主处理或本机 UDP 交付路径上的新增丢包条件。6.12 的 `iph_totlen()` 调整针对特殊 TCP GSO；Netfilter defrag 的变化针对 hook 生命周期与 fragment 条件路径。当前均不能解释普通未分片 DHCP/UDP 故障。

本轮仍为固定源码端点、Kconfig、Makefile 与候选配置模板的静态审计；未执行实机操作。6.12.81 最终 `.config`、模块清单和历史报文是否分片仍未由本轮新证据闭环。

## 19. 本轮追加核验：IPv4 route lookup、FIB trie 与 policy routing

承接第 18 节，继续核对 IPv4 入站路由、本机/转发分流、FIB trie、策略路由规则和源地址校验。固定源码端点仍为第 2 节列出的 6.1.116、6.1.174、6.12.81 commit。本轮读取并比较：
- `net/ipv4/route.c`：`ip_route_input_slow()`、`ip_route_input_rcu()`、`ip_route_output_key_hash_rcu()`、`ip_route_output_key_hash()`
- `net/ipv4/fib_frontend.c`：`fib_validate_source()`
- `net/ipv4/fib_trie.c`：`fib_table_lookup()`
- `net/ipv4/fib_rules.c`：`fib4_rule_match()`、`fib4_rule_configure()`、`fib4_rule_fill()`
- `net/core/fib_rules.c`：`fib_rules_lookup()`
- `net/ipv4/ip_forward.c`：`ip_forward()`
- `include/net/ip_fib.h`、`include/linux/inetdevice.h`、相关 IPv4 Kconfig / Makefile。

### 19.1 入站 IPv4 route lookup

`ip_route_input_slow()`：
- 6.1.116 与 6.1.174 函数体一致。
- 6.12 保留地址合法性检查、flowi4 字段构造、`fib_lookup()` 调用、RTN_LOCAL 本机交付判定、转发开关检查及路由结果构造主流程。
- 本轮发现的函数体差异是读取全局 `BC_FORWARDING` 时，从 `IPV4_DEVCONF_ALL(net, BC_FORWARDING)` 改为 `IPV4_DEVCONF_ALL_RO(net, BC_FORWARDING)`；6.12 对应头文件将后者定义为对配置值执行 `READ_ONCE()`。这是并发读取 accessor 调整，不是新增广播转发条件。
- `ip_route_input_rcu()` 三个端点函数体一致；组播识别及转入慢速 FIB lookup 的条件未变。

### 19.2 FIB trie 路由表查找

`fib_table_lookup()`：
- 6.1.116 与 6.1.174 函数体一致。
- 6.12 将旧 DSCP 比较 `inet_dscp_to_dsfield(fa->fa_dscp) != flp->flowi4_tos` 改为调用 `fib_dscp_masked_match(fa->fa_dscp, flp)`。
- 新 helper 使用 `RT_TOS(fl4->flowi4_tos)` 后再转换为 DSCP，配合 6.12 的 DSCP/TOS 区分，避免把 ECN 位混入 DSCP route selector 的匹配值。
- trie 最长前缀搜索、leaf/alias 遍历、dead route 检查、scope 检查、nexthop 可用性选择及结果填充主流程没有发现其他本轮相关语义变化。

该变化针对配置了 DSCP 路由选择器的 FIB entry；不能从 helper 抽取推断普通无 DSCP 策略的路由发生改变。

### 19.3 IPv4 policy routing rule

通用 `fib_rules_lookup()` 在三个端点函数体一致：规则链顺序、GOTO/NOP/action/suppress 处理及继续查找/最终返回结构未变。

IPv4 专用 `fib4_rule_match()`：
- 6.1.116 与 6.1.174 一致。
- 6.12 增加 `dscp_full` 区分：完整 DSCP selector 按 flow DSCP 匹配；旧式 TOS selector 保留兼容匹配。
- 6.12 的 `fib4_rule_configure()` 增加 `FRA_DSCP` netlink 属性解析；`fib4_rule_fill()` 在完整 DSCP 模式下输出 `FRA_DSCP`，旧式 TOS 模式仍使用 `frh->tos`。
- 6.1.174 相对 6.1.116 的 `fib4_rule_configure()` 将 net namespace 来源由 `sock_net(skb->sk)` 改为 `rule->fr_net`。这是规则配置时取得目标 namespace 的上下文来源调整；rule match 与通用遍历没有相应变化，不是普通 skb 路由查找新增的丢弃条件。

因此 6.12 扩展了策略路由 DSCP 表达能力；只有实际配置相应 DSCP rule 时才会影响匹配结果。当前没有 Panther 运行时 `ip rule` / DSCP route 快照，不能声称历史 DHCP 报文命中过该条件。

### 19.4 FIB output lookup 与源地址校验

- `ip_route_output_key_hash_rcu()` 三个端点函数体一致；源地址合法性、指定 output interface、local/broadcast 特殊处理、`fib_lookup()`、RTN_LOCAL 与 nexthop 选择主流程未见差异。
- 外层 `ip_route_output_key_hash()` 的 TOS 归一化差异已在第 9 节登记：6.1 使用 `ip_rt_fix_tos()`，6.12 改为 `flowi4_tos &= INET_DSCP_MASK`。本轮 FIB trie / policy rule 检查表明，该变化属于 6.12 DSCP 与 ECN 分离调整的一部分，不重复计为独立故障点。
- `fib_validate_source()` 三个端点函数体一致；RPFILTER、ACCEPT_LOCAL、自定义 local route/rule 时转入 full source validation 的条件未见版本变化。

### 19.5 IPv4 forwarding 边界

`ip_forward()`：
- 6.1.116 与 6.1.174 函数体一致。
- 6.12 在严格路由检查通过后新增 `IPSTATS_MIB_OUTFORWDATAGRAMS` 统计递增；TTL 检查、XFRM policy、MTU/fragmentation-needed 判断、skb COW、TTL decrement、redirect 与 FORWARD hook 顺序保持一致。
- 新增项是转发统计，不是额外 drop 条件。该函数处理被路由为转发流量的 IPv4 skb；到本机的 DHCP/UDP 报文不会因为该统计变化进入转发路径。

### 19.6 Kconfig / Makefile 与证据边界

- 三版 `IP_ADVANCED_ROUTER`、`IP_MULTIPLE_TABLES` 的 Kconfig 依赖关系一致；`IP_MULTIPLE_TABLES` 仍依赖 `IP_ADVANCED_ROUTER` 并 select `FIB_RULES`。
- IPv4 Makefile 仍以 `CONFIG_IP_MULTIPLE_TABLES` 控制 IPv4 `fib_rules.o` 的编译接入；未发现本轮相关入口变化。
- 已核对的 6.1 general 模板与 6.12 RK35xx 候选模板均启用 `IP_ADVANCED_ROUTER` / `IP_MULTIPLE_TABLES`。这仍是模板证据，不替代 6.12.81 最终运行 `.config`，也不证明运行时配置了自定义 rule。

### 19.7 本轮结论

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通无 DSCP 策略 DHCP/UDP 的判断 |
|---|---|---|---|
| 入站 route lookup | 核心函数一致 | BC_FORWARDING 改为 READ_ONCE accessor | 未发现新增普通入站路由丢弃条件 |
| FIB trie lookup | 函数体一致 | DSCP selector 改用 DSCP/ECN-aware helper | 仅配置 DSCP route 时相关 |
| policy rule traversal | 通用遍历一致 | 通用遍历一致 | 未发现规则执行顺序回归 |
| IPv4 rule matching | 一致 | 增加完整 FRA_DSCP selector，保留旧式 TOS 匹配 | 需实际存在相应 DSCP rule 才影响 |
| output route lookup | 一致 | 核心函数一致；TOS mask 变化见第 9 节 | 未发现普通无策略 UDP 的设备选择变化 |
| source validation | 一致 | 一致 | 未发现 RPFILTER/源校验新增条件 |
| IPv4 forwarding | 一致 | 仅新增转发统计递增 | 不适用于本机交付的 DHCP/UDP |

**阶段性结论：** 本轮未发现 6.1.116→6.1.174 的 IPv4 FIB/policy-routing 数据路径回归。6.12 的主要真实差异集中在 DSCP/TOS selector 语义扩展和配置读取 accessor 整理；前者必须有相应 DSCP rule/route 才会改变路由匹配，后者不构成新增 drop。现有证据没有证明 Panther 历史 DHCP 报文命中 DSCP selector 或 IPv4 forwarding 路径。

本轮仍为固定源码端点、Kconfig、Makefile 和候选配置模板的静态审计；未执行设备操作、构建、补丁或实机网络试验。方向二仍未结项。

## 20. 本轮追加核验：ARP RX 处理与 neighbour 状态机

承接第 9 节已经完成的 ARP/neighbour 输出关键函数，本轮补齐 ARP 输入和邻居项状态维护，避免将“ARP 输出函数一致”误写成整个 ARP/neighbour 子系统已审计。

固定源码端点仍为第 2 节列出的 6.1.116、6.1.174、6.12.81 commit。本轮读取：
- `net/ipv4/arp.c`：`arp_rcv()`、`arp_process()`、`arp_ignore()`、`arp_filter()`、`arp_fwd_proxy()`、`arp_solicit()`
- `net/core/neighbour.c`：`__neigh_event_send()`、`__neigh_update()`、`neigh_probe()`、`neigh_timer_handler()`、`neigh_periodic_work()`、`neigh_resolve_output()`、`neigh_connected_output()`
- `include/net/route.h`：`ip_route_output()` helper
- `net/ipv4/Kconfig` 与 `net/ipv4/Makefile`：ARP/IP 初始化配置接入。

### 20.1 ARP RX 入口与报文校验

`arp_rcv()` 三个端点函数体完全一致，处理顺序保持：
1. 忽略 `IFF_NOARP`、`PACKET_OTHERHOST`、`PACKET_LOOPBACK`；
2. `skb_share_check()` 获取可写 skb；
3. `pskb_may_pull()` 确保完整 ARP header 与地址字段可读；
4. 检查 hardware address length 与 IPv4 protocol address length；
5. 初始化 neighbour skb control block；
6. 通过 `NFPROTO_ARP / NF_ARP_IN` hook 进入 `arp_process()`。

未发现 6.1.116→6.1.174 或 6.1→6.12 在 ARP RX 入口校验或 hook 入口上的实现变化。

### 20.2 ARP 请求/应答处理

`arp_process()` 三个端点函数体逐字一致。以下处理条件和顺序未变：
- 检查 ARP hardware/protocol type 与 request/reply opcode；
- 提取 sender/target hardware address 和 IPv4 address；
- 丢弃目标 IPv4 multicast，以及未允许 `route_localnet` 时的 loopback 地址；
- 按 `DROP_GRATUITOUS_ARP` 处理 gratuitous ARP；
- 处理 RFC2131 地址冲突检测（sender IP 为 0）；
- 对 ARP request 做 IPv4 route lookup，按 RTN_LOCAL、`arp_ignore`、`arp_filter` 决定是否应答；
- 仅在 forwarding/proxy ARP 相关条件满足时处理转发代理；
- 按 `arp_accept`、GARP 与 ARP reply 条件更新 neighbour cache；
- 对普通 request/broadcast reply 使用 STALE，而不是直接宣告 REACHABLE。

因此 ARP 核心接收处理没有发现版本回归。ARP Netfilter hook 的实际规则仍是运行时条件；本轮不将编译支持等同于 hook 注册或规则加载。

### 20.3 ARP filter 的 6.12 调用签名变化

`arp_filter()`：
- 6.1.116 与 6.1.174 函数体一致，调用五参数 `ip_route_output(net, sip, tip, 0, l3mdev_master_ifindex_rcu(dev))`。
- 6.12 增加第六个参数 `RT_SCOPE_UNIVERSE`。
- 对应 `include/net/route.h` 的 `ip_route_output()` helper 在 6.1 中通过零初始化 `struct flowi4`，scope 字段默认值为 `RT_SCOPE_UNIVERSE`；6.12 将 scope 变为显式参数并写入 `flowi4_scope`。因此此调用是把原默认 scope 显式传入，未发现 scope 语义变化。
- `arp_filter()` 仅在 `arp_process()` 已将请求路由为 RTN_LOCAL、且接口 `IN_DEV_ARPFILTER` 开启时调用。该条件性 ARP reply 策略不适用于 DHCP Discover 本身（DHCP Discover 是 IPv4/UDP 广播，不是 ARP request）；它可能影响后续依赖 ARP 解析的邻居通信，但本轮没有发现新行为。

### 20.4 neighbour NUD 状态机与探测

以下函数三个端点的函数体均一致：
- `__neigh_event_send()`：从 stale/incomplete 到 probe、timer 和失败状态的转换；
- `__neigh_update()`：邻居 MAC/NUD 状态更新、override、router flag、timer 与通知；
- `neigh_probe()`：从 ARP queue 复制待处理 skb、释放锁后调用协议 solicit；
- `neigh_timer_handler()`：REACHABLE/DELAY/PROBE/FAILED 等状态的超时推进；
- `neigh_periodic_work()`：周期扫描与 GC；
- `neigh_resolve_output()` / `neigh_connected_output()`：构造链路层 header 后调用 `dev_queue_xmit()`。

未发现这些邻居解析、重试、状态转换或最终交付函数在三个固定源码端点之间发生实现差异。注意：这只覆盖本节列出的关键函数，不声称对 neighbour.c 每个函数逐字审计。

### 20.5 Kconfig / Makefile 边界

- IPv4 ARP 核心随 INET IPv4 协议栈编译接入；本轮没有发现单独的 `CONFIG_ARP` 开关或三版本间 ARP 对象接入变化。
- `IP_PNP_RARP` 是启动阶段 RARP 自动配置选项，不是普通 ARP RX/TX 核心的开关，也不能与用户空间 DHCP 客户端混淆。
- 本轮只确认 ARP 核心源码接入和相关 IPv4 配置边界；不将候选配置模板中某个 IP_PNP 选项的值解释为 ARP 协议路径是否存在。

### 20.6 本轮结论

| 子项 | 6.1.116→6.1.174 | 6.1→6.12 | 当前判断 |
|---|---|---|---|
| ARP RX 入口 `arp_rcv()` | 一致 | 一致 | 未发现新增入口丢弃条件 |
| ARP request/reply `arp_process()` | 一致 | 一致 | 核心处理语义一致 |
| ARP filter | 一致 | 显式传入原默认 RT_SCOPE_UNIVERSE | 调用签名变化，默认 scope 语义等价 |
| ARP solicit | 一致 | 一致 | 未发现探测报文构造变化 |
| neighbour NUD 状态机 | 本节关键函数一致 | 本节关键函数一致 | 未发现状态转换/重试回归 |
| neighbour output | 第 9 节已核对 | 第 9 节已核对 | 不重复计数 |

**阶段性结论：** 本轮未发现 ARP RX 或 neighbour NUD 状态机在 6.1.116→6.1.174 的回归，也未发现 6.12 新增普通 ARP request/reply 的丢弃条件。6.12 的 ARP filter 变化是 route helper 新增显式 scope 参数，调用处传入原先零初始化所代表的 `RT_SCOPE_UNIVERSE`，不是已证实的语义变化。

对 DHCP Discover 而言，ARP 不是该广播报文的协议处理入口；ARP/neighbour 路径主要影响后续单播通信的下一跳解析。本轮静态审计不能替代历史运行时 ARP/neighbour 状态证据。

本轮仅做固定源码端点、头文件及 Kconfig/Makefile 静态比较；未构建、未修改配置、未执行设备操作或实机网络试验。方向二仍未结项。

## 21. 本轮追加核验：UDP IPv4 sendmsg 与 IP skb 构造/追加路径

本轮继续核对普通 DHCP Discover/Request 所使用的 UDP IPv4 用户态发送入口，重点补齐此前只审过 checksum、UDP GSO 与部分 IP output helper、但尚未完整比较的 `udp_sendmsg()` → `ip_make_skb()/ip_append_data()` → `ip_send_skb()` 构造链。

固定源码端点仍为第 2 节的 6.1.116、6.1.174、6.12.81 commit。本轮读取：
- `net/ipv4/udp.c`：`udp_sendmsg()`、`udp_send_skb()`、`udp_push_pending_frames()`、`udp_flush_pending_frames()`
- `net/ipv4/ip_output.c`：`ip_make_skb()`、`__ip_make_skb()`、`ip_append_data()`、`__ip_append_data()`、`ip_send_skb()`、`ip_setup_cork()`
- `include/net/route.h`：IPv4 route output helper。

### 21.1 UDP sendmsg 主入口

`udp_sendmsg()`：
- 6.1.116 与 6.1.174 函数体一致。
- 6.12 新增/调整内容：
  - cgroup BPF sendmsg hook 调用增加 `msg_namelen` 指针参数；
  - 新增 `ip_sendmsg_scope(inet, &ipc, msg)` 计算路由 scope，并在 scope 为 `RT_SCOPE_LINK` 时关闭 connected-route cache fast path；
  - 将 `inet->uc_index` 快照保存到 `uc_index`，并对 multicast interface/address 字段使用 `READ_ONCE()`；
  - route flow 初始化改为传入计算所得 scope，而不是固定 `RT_SCOPE_UNIVERSE`；
  - connected route cast 改用 `dst_rtable()` accessor。
- multicast/unicast interface 选择的主体条件保持一致；6.12 的 `READ_ONCE()` 属于并发读取语义整理。
- **未闭环项：** 本轮已确认 `ip_sendmsg_scope()` 在 6.12 UDP sendmsg 中被调用，但在本轮读取的 `udp.c`、`ip_output.c`、`ip_sockglue.c`、`include/net/inet_sock.h` 和 `include/net/route.h` 中未定位到该 helper 定义。故不能仅凭调用点宣称它与 6.1 的 `SOCK_LOCALROUTE / MSG_DONTROUTE / strict-route → RTO_ONLINK` 逻辑完全等价。需在方向二后续子项中继续追踪 helper 定义及其调用语义，尤其确认普通 DHCP broadcast socket 的 scope 取值。

### 21.2 UDP sendmsg 的条件性 cgroup BPF 路径

6.1.116 与 6.1.174 调用 `BPF_CGROUP_RUN_PROG_UDP4_SENDMSG_LOCK()` 时传入 sockaddr 与源地址指针；6.12 另传入 `msg_namelen` 指针。这属于 cgroup BPF hook API 参数变化。只有启用相应 cgroup BPF 程序、且 socket 不走 connected fast path 时才会调用；当前没有 Panther DHCP socket 附着该类程序的运行时证据，不能将其写成默认路径差异。

### 21.3 UDP checksum 与 GSO 发送尾段

`udp_send_skb()`：
- 6.1.116→6.1.174 的差异只在 `cork->gso_size` 非零的 UDP GSO 长度校验：使用 `min(datalen, gso_size)` 参与 MTU 判断，并将一类长度错误从 `-EINVAL` 改为 `-EMSGSIZE`。
- 6.1.174→6.12 仍集中在 UDP GSO 条件分支和 socket 状态 accessor；移除一项 GSO 分支对 `CHECKSUM_PARTIAL` 的前置判断，并调整 payload checksum/segment 处理。
- 非 GSO 普通 UDP datagram 的 checksum 生成、`udp4_hwcsum()` / `udp_csum()` 路径和最终 `ip_send_skb()` 调用未发现本轮相关变化；checksum helper 的既有差异已在第 8 节记录。
- `udp_push_pending_frames()`、`udp_flush_pending_frames()` 三个端点函数体一致。

因此，不能把 UDP GSO 分支变化外推为普通 DHCP 小 UDP datagram 的 checksum 或发送行为回归。

### 21.4 IP skb 构造与发送

- `ip_make_skb()`、`ip_send_skb()`、`ip_setup_cork()` 三个端点函数体一致。
- `__ip_make_skb()`：
  - 6.1.116→6.1.174 的差异仅涉及 ICMP raw socket 统计读取条件，不适用于 UDP；
  - 6.12 使用 `dst_rtable()`、对 PMTU/TTL/TOS/priority 做 `READ_ONCE()` 快照，并将发送时间戳改为新的 delivery-time/type API；
  - IPv4 header 基本字段构造、地址拷贝、ID 生成、options 构造、dst 交付与 cork release 主流程保持一致。
- 这些 6.12 accessor/timestamp 变化没有显示普通 UDP datagram 的 IP header 构造或设备选择规则被改写。

### 21.5 IP 数据追加与 skb 分配

`ip_append_data()` 三个端点函数体一致；`__ip_append_data()` 的差异：
- 6.1.116→6.1.174：主要是 timestamp key 的持有/错误回滚整理；失败时新增对 timestamp key 的回退，不改变普通数据拷贝、分片长度计算或 skb 排队主流程。
- 6.1.174→6.12：
  - 将 cork dst 转换改用 `dst_rtable()`；
  - 新增 `MSG_SPLICE_PAGES` 数据路径，检查 HDRINCL、设备 SG 能力和 `ip_generic_getfrag`，并可通过 `skb_splice_from_iter()` 把用户页挂入 skb；
  - 对 splice 分支增加 paged fragment 处理和迭代器边界检查。
- 普通 `udp_sendmsg()` 的常规 datagram 路径没有设置 `MSG_SPLICE_PAGES`；该标志属于显式 splice/sendpage 类路径。故新增 splice fragment 分支不是普通 DHCP sendmsg 的默认路径。
- 普通小 UDP datagram 的 skb 仍按既有分配、getfrag 拷贝、UDP header/checksum、IP header 构造及 `ip_send_skb()` 路径执行。内存分配失败仍可能返回 ENOBUFS/ENOMEM 等错误，这是既有资源条件，不是本轮发现的 6.12 新增普通 DHCP 丢弃点。

### 21.6 本轮结论与待闭环项

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 普通 DHCP UDP 判断 |
|---|---|---|---|
| `udp_sendmsg()` 主流程 | 函数体一致 | scope helper、BPF hook 参数和 READ_ONCE 调整 | scope helper 定义尚待追踪，不提前下等价结论 |
| cgroup BPF sendmsg | 一致 | 增加 msg_namelen 参数 | 仅实际附着相应 BPF 程序时生效 |
| `udp_send_skb()` checksum | 仅 UDP GSO MTU/error code 变化 | 主要为 UDP GSO 分支变化 | 普通非 GSO datagram checksum 主路径未见变化 |
| `ip_make_skb()` / `ip_send_skb()` | 一致 | 一致 | 普通构造/提交入口未见变化 |
| `__ip_make_skb()` | ICMP raw 统计条件调整 | dst/accessor、READ_ONCE、timestamp API | 非 UDP 的变化或元数据读取调整 |
| `__ip_append_data()` | timestamp key 回滚 | 新增 MSG_SPLICE_PAGES | 普通 DHCP sendmsg 不设置 splice flag |

**阶段性结论：** 当前没有发现 6.1.116→6.1.174 在普通 UDP sendmsg、IP skb 构造和数据追加主路径上的已证实回归。6.12 新增的 MSG_SPLICE_PAGES 与 UDP GSO 变化均有明确条件，不能外推到普通 DHCP datagram。唯一保留为本方向未闭环项的是 6.12 `ip_sendmsg_scope()` helper 的定义及其对广播/单播路由 scope 的具体语义；在追到定义前，不将 UDP TX 路由选择差异判为等价或回归。

本轮为源码静态审计；未修改代码/配置，未构建、未启动或操作 Panther X2 实机。方向二仍未结项。
