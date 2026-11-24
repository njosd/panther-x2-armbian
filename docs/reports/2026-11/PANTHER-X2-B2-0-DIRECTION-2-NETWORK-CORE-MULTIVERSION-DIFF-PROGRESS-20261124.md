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
