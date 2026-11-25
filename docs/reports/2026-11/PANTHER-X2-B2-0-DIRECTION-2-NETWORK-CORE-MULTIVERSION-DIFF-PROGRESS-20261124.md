# Panther X2 B2-0 方向二：Linux 网络核心多版本静态差异评估进度（2026-11-24）

## 1. 当前状态与边界

**方向二进行中；本报告只结清已审查的网络初始化、loopback 和 IPv4/通用 TX 上层路径子项，不代表方向二整体结项。**

本轮严格留在 B2-0 方向二：Linux 网络核心。没有进入方向三 STMMAC/DWMAC4/DMA，没有执行设备操作、构建、启动、配置修改、网络测试或实机取证。

本轮目标是比较正常基线与故障版本的 Linux 网络核心代码差异，判断差异是否命中普通本机小 UDP 报文的发送路径。源码差异只作为待评估事实，不自动等同于故障根因。

## 2. 固定版本比较矩阵、源码端点与证据等级

方向二软件 TX 的核心横向比较对象是四个代表版本，不能缩减为三个源码仓库端点：

| 版本 | 基线角色 | 实机证据 | 当前可用源码端点/证据边界 |
|---|---|---|---|
| **6.1.65** | **黄金基准 A** | 正常实机；原始 Armbian Panther X2 镜像，2026-11-24 TF 启动与有线 IPv4 实测通过 | 原始镜像、内核配置、modules.builtin、DTB、uInitrd 及实机网络证据已归档；源码强候选为 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`（与 2023-12-03 Kernel build 时间及 `up to 6.1.65` 提交吻合），但精确构建源码 commit / Actions checkout SHA 仍未锁定。可作为明确标注的高置信度候选源码端点参与差异筛查，不得称为已验证构建源码，也不能用 6.1.116 源码代替 |
| **6.1.116** | **黄金基准 B** | 正常实机；历史稳定运行基线 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`；当前源码比较端点，精确安装包构建 source commit 尚未闭环 |
| **6.1.174-rk35xx** | **故障对照 A** | 已确认网络故障；目前最早有明确故障实机证据的 6.1.y 样本 | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`；原始 Actions run #296 日志确认的构建 source_hash |
| **6.12.81-rk35xx** | **故障对照 B** | 已确认网络故障；跨系列故障样本 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；原始 Actions 构建日志锁定的 source commit |

辅助正常实机样本：6.1.79、6.1.112。它们用于判断正常 6.1.y 实现/配置是否稳定延续；在各自精确源码来源未锁定前，不伪造源码端点，也不将它们冒充四个核心代表版本之一。

### 2.1 必须遵守的比较规则

1. 每个软件 TX 子项都以四版本矩阵组织结论：黄金 A、黄金 B、故障 A、故障 B。不能只写 6.1.116→6.1.174→6.12.81 的三版本差异。
2. 对 6.1.65，先复用已归档原始镜像和二进制/配置资产；凡必须依赖源码函数逐行比较的项目，先标记“6.1.65 源码端点未锁定”，继续追溯其原始构建源码或可验证的发行版源码包。
3. 在 6.1.65 源码身份未闭环前，6.1.116 与故障版本之间的源码差异只能标为“三端点源码比较结果”，不得宣称已经完成两条黄金基准对两条故障线的四版本对照。
4. 6.1.79、6.1.112 是已确认正常的辅助样本；只有取得可核验的源码/配置证据后，才将其加入对应子项比较，不以版本号相近推定实现相同。
5. 对普通 UDP/DHCP TX 的适用性必须单独判断；仅存在于 TCP GSO、特殊 skb backing memory、PREEMPT_RT 或其他条件编译分支的差异，不得直接归因于普通 DHCP 报文。

6.18.63 属于 6.18.y，不纳入本轮 6.1.y 正常/故障对照矩阵，也不为本轮方向二重复追查其历史包身份。

## 3. 网络子系统配置入口与初始化

**四版本回溯状态：** 本节原始源码比较仅覆盖 6.1.116、6.1.174、6.12.81。6.1.65 已有原始 config 与 modules.builtin 归档，可补做 NET/INET/NETDEVICES 等实际配置符号核对；但本节所比较的 Kconfig/Makefile 与 C 初始化函数源码尚无 6.1.65 精确源码端点。故本节现有结论只能标为三端点源码结论，6.1.65 配置层待补、源码层未闭环。

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

**四版本回溯状态：** 本节 ip_output、__dev_queue_xmit、qdisc 与 checksum helper 的函数级比较未包含 6.1.65。6.1.65 原始镜像的正常网络实测证明该完整系统能够完成 IPv4 通信，但不能替代对应内核函数源码证据。现有差异均为三端点源码发现，不能据此断言两条黄金基准共同具备或故障版本共同缺失。

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

### 4.4 TX checksum helper 与不可读 fragment 检查（后续 TX 审计修正）

本节原先把 6.12 的 `skb_frags_readable()` 检查仅定位到 `skb_checksum_help()`，这一表述不完整。第 22 节继续沿 TX 实际交付链核对后确认：6.12 在 `validate_xmit_skb()` 入口另有一处更早、无条件的可读性检查；`skb_checksum_help()` 内仍保留独立检查。具体调用路径和影响范围以第 22 节为准。

`skb_checksum_help()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 在 `CHECKSUM_COMPLETE` 和 GSO 快速分支之后、实际读取 skb 数据计算 checksum 之前，增加 `skb_frags_readable(skb)` 检查，不可读时返回 `-EFAULT`；
- `skb_frags_readable()` 实际检查 `!skb->unreadable`；
- 6.12 的 `__skb_fill_netmem_desc()` 在 fragment 使用 `netmem_is_net_iov(netmem)` 时设置 `skb->unreadable=true`。该标记针对 host 不可直接读取的 net_iov/device-memory fragment，不是普通 page fragment 或普通线性 skb。

调用关系之一：
`validate_xmit_skb()` → `skb_csum_hwoffload_help()` →（设备不支持当前 skb checksum offload 时）`skb_checksum_help()`。
软件 checksum fallback 内的检查是第二道保护；不能把它误写成 6.12 唯一的 TX unreadable-fragment 检查。

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

**四版本回溯状态：** 本节涉及的 checksum、fragment 可读性及 UDP GSO 代码比较没有 6.1.65 源码端点；现有 6.1.65 config/实机结果不足以证明这些内部实现与 6.1.116 相同。保留为三端点源码结论，6.1.65 待补。

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

**四版本回溯状态：** 本节 feature negotiation、ARP/neighbour 输出和 route-key 函数比较未包含 6.1.65。6.1.65 的成功 DHCP/IPv4 实测仅证明端到端行为，不提供上述函数实现的源码等价性证据。现有结论按三端点源码结果保留，不能外推为四版本结论。

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

**四版本回溯状态：** 本节 RX 分派、IPv4 输入、UDP socket 查找/GRO/receive queue 比较未包含 6.1.65。其成功 IPv4 实测是黄金基准行为证据，但不补足 RX 函数源码比较。现有结论仅适用于三端点源码范围。

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

**四版本回溯状态：** 本节所用候选配置模板不能自动代表 6.1.65 原始镜像的实际 .config。6.1.65 已归档的 config-6.1.65-ophub 应作为独立真实配置输入；在逐符号提取并映射前，本节不得将模板差异视为四版本实际配置差异。

### 12.1 证据等级与模板身份

- 6.1.116 真实运行配置已由既有报告完成全量解析：7,677 个符号与对应 Ophub general `config-6.1` 模板完全一致，符号差异为 0。模板 blob SHA：`c5e4598301c3ef3675be0058b99b9b6044a14bbf`。
- 6.12.81 既有运行配置报告只确认了一组关键符号与当时锁定模板一致（包括 `CONFIG_PAGE_POOL=y`、`CONFIG_NET_RX_BUSY_POLL=y`、`CONFIG_XDP_SOCKETS=y`）；该报告没有宣称完成整个最终 `.config` 的逐符号比较。
- 本轮另行读取的 RK35xx `config-6.12` 候选模板来自 `ophub/kernel@bfc9b24f64cf30c3499295b484bbcabddbcc18b6`，当前文件 blob SHA 为 `6c7714f5668362dd4ae9c4d1a7eb8249e6b23de5`。既有运行配置报告记录的模板 blob SHA 是 `966f4b6ac7c0ad59179d6ae272423500601fab07`，与本轮取得的 blob SHA 不同。两者属于不同模板版本/快照的可能性尚待核对；本节只把本轮读取结果称为“候选模板”，不冒充 6.12.81 最终构建配置。

### 12.2 两个候选模板中已核对的网络符号

| 符号 | 6.1.116 general config-6.1 | 当前读取的 6.12 RK35xx config-6.12 | 差异含义 / 证据边界 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| `CONFIG_NET` / `CONFIG_INET` / `CONFIG_NETDEVICES` | y | y | 核心网络支持均启用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_NET_NS` | y | y | network namespace 均启用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_BPF` / `CONFIG_BPF_SYSCALL` | y | y | BPF 基础能力均启用，不代表有程序附着 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_XDP_SOCKETS` | y | y | AF_XDP 支持均编入 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_NET_RX_BUSY_POLL` | y | y | RX busy-poll 支持均启用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_PAGE_POOL` | y | y | page-pool 支持均启用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_NET_DEVMEM` | 不存在 | y | 6.12 新增 netdev memory 相关能力；是否进入特定 skb 路径仍取决于运行时使用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_IP_PNP` / DHCP / BOOTP / RARP | 全部 not set | y | 6.12 候选模板增加内核启动阶段 IP autoconfiguration 能力；与用户空间 DHCP 客户端是不同机制，是否实际生效还取决于最终配置和启动参数 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_IPV6` | y | m | IPv6 从 built-in 变为 module（候选模板） | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_VLAN_8021Q` | y | m | VLAN 802.1Q 从 built-in 变为 module（候选模板） | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_INET_DIAG` | y | m | inet diagnostics 从 built-in 变为 module（候选模板） | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_NETFILTER` | y | y | 两套模板均启用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_BRIDGE` | m | m | 两套模板均为模块 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `CONFIG_NET_CLS_BPF` / `CONFIG_NET_ACT_BPF` | m / m | m / m | 两套模板一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

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

**四版本回溯状态：** 本节 AF_PACKET、VLAN/bridge RX、Netfilter ingress 代码与配置对照未包含 6.1.65 的精确源码/实际配置映射。现有结果仅为三端点源码比较；6.1.65 对应源码和实际 Kconfig 值均待补。

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

| 符号 | 6.1 模板 | 6.12 候选模板 | 判断 | 6.1.65 黄金 A 状态 |
|---|---:|---:|---| --- |
| `NET_INGRESS` / `NET_EGRESS` | y / y | y / y | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NETFILTER_INGRESS` / `NETFILTER_EGRESS` | y / y | y / y | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `PACKET` / `PACKET_DIAG` | y / y | y / y | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `BRIDGE` | m | m | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `BRIDGE_VLAN_FILTERING` | y | y | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `VLAN_8021Q` | y | m | 模块形态变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `BRIDGE_NETFILTER` | m | m | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NF_CONNTRACK` | y | y | 一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NF_TABLES` | m | y | nftables 核心从模块变为 built-in | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

模板差异本身不证明 nftables 规则集内容、hook 是否注册或规则是否实际加载。尤其 `NF_TABLES=y` 仅代表内核具备相应功能，不代表有一条规则会丢弃 DHCP/UDP。

### 14.6 本轮结论

| 子系统 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通未桥接、未打 VLAN 标签 IPv4/UDP 的判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| AF_PACKET | packet_rcv 核心行为一致 | unreadable fragment 时限制抓包 snaplen | 用户态抓包可见性变化，不是协议栈通用 drop | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| VLAN RX | vlan_do_receive 一致 | vlan_do_receive 一致 | 无 VLAN tag 不走该子设备切换路径 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Bridge RX | MST helper 改为 port-aware | bridge offload/TC miss bookkeeping 调整 | 仅 bridge port 条件路径 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Netfilter ingress | hook dispatch 结构一致 | NF_STOLEN 错误返回处理整理 | 实际 hook 注册和规则 verdict 才会影响报文 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Kconfig | ingress/egress 与 packet 功能相同 | VLAN 模块化、NF_TABLES built-in 化 | 配置能力差异，不等于运行时规则差异 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

当前没有发现能够解释“未桥接、未打 VLAN 标签、普通 IPv4/UDP”收包故障的已证实 AF_PACKET/VLAN/bridge/Netfilter 核心回归点。条件性变化已保留，待结合对应最终配置和既有运行证据判断。

## 15. 方向二下一项

本轮完成 AF_PACKET、VLAN RX、bridge RX、Netfilter ingress/注册核心与相关 Kconfig 模板差异核对。方向二仍未结项。

下一项继续审计 IPv4 Netfilter PREROUTING/LOCAL_IN 与 conntrack/NAT hook 的核心注册、调用顺序和 Kconfig 依赖，区分“内核具备功能”与“实际 hook/ruleset 生效”。B2-0 仍然只做多版本源码、Kconfig、配置及设备树静态审计，不涉及 B1 包的实机配置、构建、启动或网络试验。

## 16. 本轮追加核验：IPv4 PREROUTING/LOCAL_IN、conntrack 与 NAT hook

**四版本回溯状态：** 本节 conntrack、NAT hook 注册/顺序及 tuple lookup 函数比较未包含 6.1.65。6.1.65 实机 IPv4 成功不能证明其 conntrack/NAT 内部实现与其他版本一致。现有结论限定为三端点源码比较。

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

| 符号 | 6.1 模板 | 6.12 候选模板 | 说明 | 6.1.65 黄金 A 状态 |
|---|---:|---:|---| --- |
| `NF_CONNTRACK` | y | y | 核心 conntrack 均内建 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NF_CONNTRACK_MARK/ZONES/PROCFS/EVENTS` | y | y | 选定子功能一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NF_NAT` | m | y | NAT 核心从模块变为内建 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NETFILTER_XTABLES` | m | y | xtables 核心从模块变为内建 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NETFILTER_XT_NAT` | m | y | xtables NAT glue 从模块变为内建 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `IP_NF_IPTABLES` | m | m | legacy iptables 顶层仍为模块 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `IP_NF_IPTABLES_LEGACY` | 无独立符号 | m | 6.12 拆分出 legacy 实现符号 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `IP_NF_FILTER` | m | m | filter 表仍为模块 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `IP_NF_NAT` | m | m | iptables NAT 表仍为模块 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `NF_DEFRAG_IPV4` | y | y | IPv4 defrag 均内建 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

Kconfig 结构变化：
- 6.12 的 `IP_NF_FILTER`、`IP_NF_NAT` 显式 select `IP_NF_IPTABLES_LEGACY`，将旧式 iptables 实现拆分成单独符号；这是构建/模块依赖关系变化，不代表 hook 优先级或规则匹配语义变化。
- `IP_NF_MATCH_RPFILTER` 在 6.12 增加 `NFT_COMPAT` 作为可选依赖路径；只影响 rpfilter match 的配置可用性，不是默认收包路径的强制组件。
- `NF_NAT`、`NETFILTER_XTABLES`、`NETFILTER_XT_NAT` 在候选模板中从 m 变为 y，而具体 `IP_NF_FILTER`/`IP_NF_NAT` 仍为 m。此差异可能影响模块依赖、装载顺序和镜像/模块打包完整性；是否影响某个运行系统，必须以该版本最终 `.config`、模块清单及实际加载证据确认。
- 由于 6.12 模板 SHA 与先前运行配置报告记录的模板 SHA 不同，以上 6.12 值仍只能称为候选模板值，不能回填成 6.12.81 的最终配置结论。

### 16.6 本轮阶段性结论

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 结论 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| IPv4 conntrack hook 位置/优先级 | 一致 | 一致 | 未发现普通 PREROUTING/LOCAL_IN 顺序变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| conntrack tuple lookup | 一致 | debug 输出和状态读取方式整理 | 未发现普通 UDP tuple 匹配语义变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| conntrack allocation failure | 错误指针传播语义已存在 | 延续既有行为 | 不是 6.12 新增的资源压力 drop | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| conntrack confirm | 一致 | IPv4 wrapper 并入通用 nf_confirm | 普通 IPv4 无 helper/seqadj 路径等价 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| iptables filter hook | 一致 | 一致 | 规则表/模块是否加载决定是否执行 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| iptables NAT hook | 一致 | 一致 | 规则表/模块是否加载决定是否执行 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Kconfig | 本轮未见该窗口核心配置逻辑变化 | legacy 拆分及核心模块化形态变化 | 需结合最终配置与模块打包核验 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**对普通未桥接、无 VLAN 标签的 IPv4/UDP 流量：** 当前没有发现 6.1.116→6.1.174 的 conntrack/NAT hook 核心回归，也没有发现 6.12 在普通 PREROUTING/LOCAL_IN 顺序上引入新的丢包点。保留的主要差异是 6.12 Netfilter/iptables 组件的 built-in/module 组合变化，后续需与确切最终配置及模块打包证据对齐。

## 17. 方向二下一项

本轮完成 IPv4 conntrack hook 注册、confirm、tuple lookup、NAT hook 和 legacy filter/NAT Kconfig 差异核对。方向二仍未结项。

下一项继续核对 netfilter 之外、但处于 IPv4 路由与本机交付边界的关键网络核心配置/代码：IPv4 defragmentation、IP checksum/fragment handling、local delivery 与相关 Kconfig/module 依赖，优先围绕普通 DHCP/UDP 包的实际路径。B2-0 继续限定为源码、Kconfig、配置及设备树静态差异审计，不涉及 B1 包的实机配置、构建、启动或网络试验。


## 18. 本轮追加核验：IPv4 header checksum、分片重组与本机交付

**四版本回溯状态：** 本节 IPv4 checksum、分片重组和本机交付代码未包含 6.1.65 源码端点。6.1.65 的正常 IPv4 实测仅作黄金行为基准，不作为函数级实现证据。现有结论限定为三端点源码比较。

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

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通未分片 DHCP/UDP 的判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| IPv4 header checksum | `ip_rcv_core()` 一致 | 仍调用 `ip_fast_csum()` | 未发现新 checksum 丢弃条件 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| IP total length | 一致 | 改用 `iph_totlen()`；仅 TCP GSO 且 tot_len=0 时回退 skb 长度 | 普通 UDP 仍读取 header tot_len | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| 本机交付 / LOCAL_IN | 核心函数一致 | 核心函数一致 | 路径与 hook 入口未变 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| fragment queue | 主函数一致；peer 引用获取改为 RCU/refcount 安全方式 | drop-reason 与 skb 时间戳/accessor 调整，重组主逻辑一致 | 普通未分片包不进入 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Netfilter defrag | hook 位置、优先级、启用计数一致 | 增加 RCU 动态 hook 发布及 NODEFRAG bit accessor | 只对实际启用 hook 且确为 fragment 的 skb 生效 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| Kconfig | 关键入口一致 | INET / policy routing / NF_DEFRAG_IPV4 入口语义一致 | 模板均启用；最终配置仍需独立闭环 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**阶段性结论：** 本轮没有发现 6.1.116→6.1.174 在 IPv4 header checksum、分片主处理或本机 UDP 交付路径上的新增丢包条件。6.12 的 `iph_totlen()` 调整针对特殊 TCP GSO；Netfilter defrag 的变化针对 hook 生命周期与 fragment 条件路径。当前均不能解释普通未分片 DHCP/UDP 故障。

本轮仍为固定源码端点、Kconfig、Makefile 与候选配置模板的静态审计；未执行实机操作。6.12.81 最终 `.config`、模块清单和历史报文是否分片仍未由本轮新证据闭环。

## 19. 本轮追加核验：IPv4 route lookup、FIB trie 与 policy routing

**四版本回溯状态：** 本节 FIB trie、policy routing 与 route lookup 代码比较未包含 6.1.65。6.1.65 的 DHCP 默认路由和 IPv4 连通实测可作为行为侧参照，但不能代替源码及实际配置比较。现有结论限定为三端点源码比较。

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

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 对普通无 DSCP 策略 DHCP/UDP 的判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| 入站 route lookup | 核心函数一致 | BC_FORWARDING 改为 READ_ONCE accessor | 未发现新增普通入站路由丢弃条件 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| FIB trie lookup | 函数体一致 | DSCP selector 改用 DSCP/ECN-aware helper | 仅配置 DSCP route 时相关 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| policy rule traversal | 通用遍历一致 | 通用遍历一致 | 未发现规则执行顺序回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| IPv4 rule matching | 一致 | 增加完整 FRA_DSCP selector，保留旧式 TOS 匹配 | 需实际存在相应 DSCP rule 才影响 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| output route lookup | 一致 | 核心函数一致；TOS mask 变化见第 9 节 | 未发现普通无策略 UDP 的设备选择变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| source validation | 一致 | 一致 | 未发现 RPFILTER/源校验新增条件 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| IPv4 forwarding | 一致 | 仅新增转发统计递增 | 不适用于本机交付的 DHCP/UDP | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**阶段性结论：** 本轮未发现 6.1.116→6.1.174 的 IPv4 FIB/policy-routing 数据路径回归。6.12 的主要真实差异集中在 DSCP/TOS selector 语义扩展和配置读取 accessor 整理；前者必须有相应 DSCP rule/route 才会改变路由匹配，后者不构成新增 drop。现有证据没有证明 Panther 历史 DHCP 报文命中 DSCP selector 或 IPv4 forwarding 路径。

本轮仍为固定源码端点、Kconfig、Makefile 和候选配置模板的静态审计；未执行设备操作、构建、补丁或实机网络试验。方向二仍未结项。

## 20. 本轮追加核验：ARP RX 处理与 neighbour 状态机

**四版本回溯状态：** 本节 ARP RX 与 neighbour NUD 状态机比较未包含 6.1.65 源码端点。黄金 A 的网络成功结果不等于已证明内部 ARP/neighbour 实现与黄金 B 一致。现有结论限定为三端点源码比较。

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

| 子项 | 6.1.116→6.1.174 | 6.1→6.12 | 当前判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| ARP RX 入口 `arp_rcv()` | 一致 | 一致 | 未发现新增入口丢弃条件 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| ARP request/reply `arp_process()` | 一致 | 一致 | 核心处理语义一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| ARP filter | 一致 | 显式传入原默认 RT_SCOPE_UNIVERSE | 调用签名变化，默认 scope 语义等价 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| ARP solicit | 一致 | 一致 | 未发现探测报文构造变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| neighbour NUD 状态机 | 本节关键函数一致 | 本节关键函数一致 | 未发现状态转换/重试回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| neighbour output | 第 9 节已核对 | 第 9 节已核对 | 不重复计数 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**阶段性结论：** 本轮未发现 ARP RX 或 neighbour NUD 状态机在 6.1.116→6.1.174 的回归，也未发现 6.12 新增普通 ARP request/reply 的丢弃条件。6.12 的 ARP filter 变化是 route helper 新增显式 scope 参数，调用处传入原先零初始化所代表的 `RT_SCOPE_UNIVERSE`，不是已证实的语义变化。

对 DHCP Discover 而言，ARP 不是该广播报文的协议处理入口；ARP/neighbour 路径主要影响后续单播通信的下一跳解析。本轮静态审计不能替代历史运行时 ARP/neighbour 状态证据。

本轮仅做固定源码端点、头文件及 Kconfig/Makefile 静态比较；未构建、未修改配置、未执行设备操作或实机网络试验。方向二仍未结项。

## 21. 本轮追加核验：UDP IPv4 sendmsg 与 IP skb 构造/追加路径

**四版本回溯状态：** 本节 UDP sendmsg、checksum/GSO 尾段、IP skb 构造与追加函数比较未包含 6.1.65 源码端点。6.1.65 的 DHCP/IPv4 实测只能证明系统层面可通信，不能填补 sendmsg 内部代码差异。现有结论限定为三端点源码比较。

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

| 核验项 | 6.1.116→6.1.174 | 6.1→6.12 | 普通 DHCP UDP 判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| `udp_sendmsg()` 主流程 | 函数体一致 | scope helper、BPF hook 参数和 READ_ONCE 调整 | scope helper 定义尚待追踪，不提前下等价结论 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| cgroup BPF sendmsg | 一致 | 增加 msg_namelen 参数 | 仅实际附着相应 BPF 程序时生效 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `udp_send_skb()` checksum | 仅 UDP GSO MTU/error code 变化 | 主要为 UDP GSO 分支变化 | 普通非 GSO datagram checksum 主路径未见变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `ip_make_skb()` / `ip_send_skb()` | 一致 | 一致 | 普通构造/提交入口未见变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `__ip_make_skb()` | ICMP raw 统计条件调整 | dst/accessor、READ_ONCE、timestamp API | 非 UDP 的变化或元数据读取调整 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `__ip_append_data()` | timestamp key 回滚 | 新增 MSG_SPLICE_PAGES | 普通 DHCP sendmsg 不设置 splice flag | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**阶段性结论：** 当前没有发现 6.1.116→6.1.174 在普通 UDP sendmsg、IP skb 构造和数据追加主路径上的已证实回归。6.12 新增的 MSG_SPLICE_PAGES 与 UDP GSO 变化均有明确条件，不能外推到普通 DHCP datagram。唯一保留为本方向未闭环项的是 6.12 `ip_sendmsg_scope()` helper 的定义及其对广播/单播路由 scope 的具体语义；在追到定义前，不将 UDP TX 路由选择差异判为等价或回归。

本轮为源码静态审计；未修改代码/配置，未构建、未启动或操作 Panther X2 实机。方向二仍未结项。

## 22. 本轮追加核验：TX queue → qdisc → validate → ndo_start_xmit 交付链

**四版本回溯状态：** 本节 TX queue、qdisc、validate_xmit_skb 与 ndo_start_xmit 交付链的函数级比较未包含 6.1.65。6.1.65 原版系统已实机完成 DHCP/IPv4 通信，是关键黄金行为基准；但在其精确源码端点未锁定前，不得把本节三端点源码结果写成两条黄金线共同实现。6.1.65 对应 TX 核心函数待补。

本轮按用户要求将方向二重点转向 TX 发送环节，继续向下追踪普通 UDP skb 从 `__dev_queue_xmit()` 进入 netdevice TX queue、qdisc dequeue、发送前校验，直到 Linux 网络核心调用驱动 `ndo_start_xmit` 的边界。仍使用第 2 节固定的 6.1.116、6.1.174、6.12.81 源码端点。

本轮读取：
- `net/core/dev.c`：`__dev_queue_xmit()`、`netdev_core_pick_tx()`、`netdev_pick_tx()`、`netif_skb_features()`、`validate_xmit_skb()`、`validate_xmit_skb_list()`、`dev_hard_start_xmit()`、`xmit_one()`；
- `net/sched/sch_generic.c`：`dequeue_skb()`、`qdisc_restart()`、`sch_direct_xmit()`、`__qdisc_run()`；
- `include/linux/skbuff.h`：`skb_frags_readable()`、`__skb_fill_netmem_desc()`；
- `net/Kconfig`：`NET_DEVMEM`、`ETHERNET_PACKET_MANGLE` 配置入口。

### 22.1 TX queue 选择

`netdev_core_pick_tx()`、`netdev_pick_tx()` 三个固定端点函数体一致：
- 单 TX queue 设备直接使用 queue 0；
- 多队列设备才调用驱动 `ndo_select_queue` 或通用 XPS/hash 选择；
- 最终通过 `netdev_cap_txqueue()` 限制 queue index，并写入 skb queue mapping。

Panther X2 板载 GMAC 的实际 `real_num_tx_queues`、驱动 `ndo_select_queue` 是否注册及运行时 queue mapping 不在本轮静态源码结论范围内；这些属于后续驱动/运行时证据。本轮未发现三个版本通用 TX queue 选择 helper 的函数体差异。

### 22.2 qdisc 出队与 direct transmit

- `sch_direct_xmit()` 三版函数体一致：先在 qdisc 锁外执行可选 skb 校验，再获取 TX queue 锁；若 TX queue 未 frozen/stopped，调用 `dev_hard_start_xmit()`；若驱动返回 `NETDEV_TX_BUSY`，将未完成 skb 重新入队。
- `qdisc_restart()` / `dequeue_skb()`：6.1.116→6.1.174 增加 packet budget 参数，并将 budget 传给 bulk dequeue；6.12 延续该实现。
- `__qdisc_run()`：6.1.116→6.1.174 将 quota 传入 qdisc restart；6.12 将 `dev_tx_weight` 移入 `net_hotdata`，仍使用相同 quota/budget 控制结构。
- 上述变化是 qdisc 批量出队预算和调度公平性调整；`sch_direct_xmit()` 的单 skb 锁、队列停止判断、驱动调用及 BUSY 重排函数体没有变化。

因此，在本轮覆盖的 generic qdisc 路径中，没有发现 6.1.116→6.1.174 或 6.1→6.12 改写单个普通 UDP skb 的驱动交付/返回处理。

### 22.3 发送前校验：发现并明确 6.12 新增的 TX 丢弃门

`validate_xmit_skb()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 在计算 `netif_skb_features()`、VLAN/GSO/linearize/checksum/XFRM 处理之前，新增：
  `if (!skb_frags_readable(skb)) goto out_kfree_skb;`
- 该分支会释放 skb，递增 `dev_core_stats_tx_dropped`，并返回 NULL；因此它是发送前校验入口的明确丢弃门，不依赖设备是否支持 checksum offload，也不要求进入软件 checksum fallback。
- qdisc 正常 direct transmit 路径通过 `sch_direct_xmit()` → `validate_xmit_skb_list()` → `validate_xmit_skb()`；无队列直发路径也直接调用 `validate_xmit_skb()`。因此该检查覆盖这两类 generic TX 交付路径。

`skb_frags_readable()` 返回 `!skb->unreadable`。6.12 的 `__skb_fill_netmem_desc()` 在 fragment backing memory 是 `net_iov` 时将 `skb->unreadable=true`；普通 page fragment 不触发该标记，普通线性 skb 也不触发。6.12 的 `NET_DEVMEM` Kconfig 依赖 `DMA_SHARED_BUFFER`、`GENERIC_ALLOCATOR` 和 `PAGE_POOL`，并以 `def_bool y` 定义。

同一版本的 `skb_checksum_help()` 另有 unreadable-fragment 检查，属于软件 checksum 读取路径的第二道保护。必须区分：
1. `validate_xmit_skb()` 入口：对 unreadable skb 直接拒绝 TX；
2. `skb_checksum_help()`：只有进入软件 checksum fallback 时才会触发其内部检查。

**对普通 DHCP UDP TX 的适用性：** 普通 `udp_sendmsg()` 创建的小型 DHCP datagram 使用常规 skb 数据构造路径；本轮已审计的普通 UDP 路径没有设置 `MSG_SPLICE_PAGES`，普通用户页/线性数据也不等于 `net_iov`。因此不能仅凭 6.12 `NET_DEVMEM=y` 就认定 DHCP skb 会被该门拒绝。该差异是真实的、位于驱动调用之前的条件性 TX drop；但是否可能命中 Panther 历史报文，需要 skb backing-memory 证据，当前没有该证据。

### 22.4 6.1.174 的 GSO skb-list 返回语义修正

`__dev_queue_xmit()`：
- 6.1.116→6.1.174 增加 `is_list` 标志和 GSO segment list 的返回码处理：如果一个 skb 经 GSO 分段形成多个 frame，部分 frame 已交付后，避免将后续 `NETDEV_TX_BUSY` 误解释为原始 TCP 数据完全未发送；当 list 已部分处理时将返回状态归一为 `NETDEV_TX_OK`。
- 6.12 保留该处理。
- 该新增分支只在无 qdisc/noqueue 的直发分支中处理 GSO skb list；普通 DHCP 小型 UDP datagram 是单 skb、非 GSO，不命中 `is_list` 分支。
- 对 qdisc 路径，驱动 BUSY 的 skb 仍按 `sch_direct_xmit()` 的原有机制重新入队。

未发现这一变化改变单个普通 UDP skb 的发送返回语义。

### 22.5 驱动调用边界与可选 Ethernet packet mangle hook

`dev_hard_start_xmit()` 三版函数体一致：逐个处理 skb/list 节点，调用 `xmit_one()`，并按 `dev_xmit_complete(rc)` 判断是否继续；若 TX queue 已停止且仍有待发送 skb，则返回 `NETDEV_TX_BUSY` 与剩余 list。

`xmit_one()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 移除了 `CONFIG_ETHERNET_PACKET_MANGLE` 条件下的 `dev->eth_mangle_tx` 可选发送前改写 hook；
- 6.1 的 `net/Kconfig` 定义该隐藏 bool，说明它可由需要改写 Ethernet TX/RX 报文的 PHY driver 选择；6.12 的 `net/Kconfig` 不再定义该选项，`xmit_one()` 也不再调用该 hook。
- 该差异属于可选 PHY/设备专用报文改写扩展的移除，不是通用 TX skb 处理或 DMA 提交算法变化。是否曾被 Panther 所用 PHY/驱动选择，需要方向三核对驱动 Kconfig/代码；本轮不提前展开或猜测。

三版最终均通过 `netdev_start_xmit()` 调用设备的 `ndo_start_xmit`，并围绕调用发出 `net_dev_start_xmit` / `net_dev_xmit` trace。该处是本轮 Linux 网络核心审计的驱动边界；TX descriptor、DMA map、doorbell、completion/reclaim 不属于方向二，本轮不进入。

### 22.6 TX 核心路径结论

| 子项 | 6.1.116→6.1.174 | 6.1→6.12 | 普通单 skb UDP 判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| TX queue selection | 三个 helper 一致 | 一致 | 未发现通用队列选择差异 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| qdisc dequeue budget | 增加 packet budget | 延续；quota 移入 net_hotdata | 调度/批量预算变化，不改单 skb 驱动调用 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `sch_direct_xmit()` | 一致 | 一致 | 驱动交付及 BUSY 重排一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `validate_xmit_skb()` | 一致 | 新增 unreadable-frag 入口拒绝 | 条件性新增 TX drop，需 skb 是否含 net_iov 证据 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `__dev_queue_xmit()` noqueue GSO list | 新增 partial GSO list 返回码处理 | 延续 | 普通单 skb DHCP 不命中 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `dev_hard_start_xmit()` | 一致 | 一致 | 单 skb 调用/返回处理一致 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `xmit_one()` | 一致 | 移除可选 ETHERNET_PACKET_MANGLE hook | 需驱动 Kconfig 证据；非通用 DMA 差异 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `ndo_start_xmit` 调用边界 | 一致 | 一致 | 本轮未发现通用驱动调用接口回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**本轮结论：**
1. 6.1.116→6.1.174 的通用 TX 核心差异主要是 noqueue GSO list 的部分发送返回码修正；不命中普通 DHCP 单 skb。
2. 6.1.174→6.12.81 的 qdisc budget、net_hotdata、TX queue selection 和单 skb driver handoff 没有发现新的通用行为回归。
3. 6.12.81 确实新增 `validate_xmit_skb()` 对 unreadable net_iov fragment 的提前拒绝，是本轮最值得保留的 TX 条件性丢弃差异；但普通 DHCP skb 是否可能带此类 fragment 尚无证据，不能定为根因。
4. 6.12 移除可选 `ETHERNET_PACKET_MANGLE` hook，是否与 Panther PHY driver 有关联留给方向三，不在本轮越界审计。

本轮仅进行固定源码端点静态比较；没有构建、修改配置、执行设备操作或实机网络试验。方向二仍未结项；TX DMA descriptor/mapping/doorbell/completion/reclaim 留在后续既定驱动方向，不在本节提前展开。

## 23. 本轮追加核验：netdev_start_xmit、TX queue flow control、watchdog 与 skb completion/free

**四版本回溯状态：** 本节 netdev_start_xmit、queue stop/wake、BQL、watchdog 和 skb free/completion 比较未包含 6.1.65 源码端点。现有结果仅覆盖 6.1.116、6.1.174、6.12.81；不能据此推断 6.1.65 代码相同。

承接第 22 节的 `ndo_start_xmit` 驱动边界，本轮继续核对其上层调用封装、TX queue stop/wake、BQL（Byte Queue Limits）、watchdog timeout，以及驱动完成发送后 skb 的释放/消费路径。目标是确认网络核心是否可能在“已进入驱动调用”之后，由通用队列管理或 skb 生命周期机制改变发送推进状态。

固定源码端点仍为第 2 节的 6.1.116、6.1.174、6.12.81 commit。本轮读取：
- `include/linux/netdevice.h`：`__netdev_start_xmit()`、`netdev_start_xmit()`、`netdev_tx_sent_queue()`、`netdev_tx_completed_queue()`、`__netdev_tx_sent_queue()`、`netif_tx_stop_queue()`、`netif_tx_queue_stopped()`、`netif_xmit_stopped()`、`txq_trans_update()`；
- `net/core/dev.c`：`netif_tx_wake_queue()`；
- `net/sched/sch_generic.c`：`dev_watchdog()`；
- `include/linux/skbuff.h` 与 `net/core/skbuff.c`：skb refcount、`skb_release_all()`、`skb_release_data()`、`consume_skb()`、`napi_consume_skb()` 与 drop-reason 相关路径。

### 23.1 netdev_start_xmit：通用驱动调用封装

三个版本的 `netdev_start_xmit()` 函数体一致：
1. 取 `dev->netdev_ops`；
2. 调用 `__netdev_start_xmit()`，后者最终执行 `ops->ndo_start_xmit(skb, dev)`；
3. 只有驱动返回 `NETDEV_TX_OK` 时才执行 `txq_trans_update(txq)`；
4. 原样返回驱动的 `NETDEV_TX_OK / NETDEV_TX_BUSY` 等结果。

`txq_trans_update()` 三版一致：仅当 `xmit_lock_owner != -1` 时更新 `trans_start`。未发现 6.1.116→6.1.174 或 6.1→6.12 改变驱动返回码解释、成功发送时间戳更新条件或调用次序。

**6.12 的条件性变化：** `__netdev_start_xmit()` 不再直接写 `__this_cpu_write(softnet_data.xmit.more, more)`，改为调用 `netdev_xmit_set_more(more)`。6.12 helper 的实现为：
- 非 `CONFIG_PREEMPT_RT`：仍使用 `__this_cpu_write(softnet_data.xmit.more, more)`，与 6.1 实现相同；
- `CONFIG_PREEMPT_RT`：改为写入 `current->net_xmit.more`，并由 `netdev_xmit_more()` 从当前 task 读取。

这是 PREEMPT_RT 下 xmit_more 状态存储位置的适配；非 RT 配置行为保持原样。其作用是让驱动在一次 TX 批次中判断是否还有后续 skb、决定是否延后 doorbell/kick。它不改变本次 skb 是否调用 `ndo_start_xmit`，也不改变驱动返回码。当前没有 Panther 目标内核的 `CONFIG_PREEMPT_RT` 证据，故只记录为条件性差异，不推定其启用。

### 23.2 TX queue stop/wake 与状态位

以下通用 helper 三个端点函数体一致：
- `netif_tx_stop_queue()`：更新 `trans_start`，执行与 watchdog 配对的内存屏障，再置位 `__QUEUE_STATE_DRV_XOFF`；
- `netif_tx_queue_stopped()`：读取 driver XOFF；
- `netif_xmit_stopped()`：检查 `QUEUE_STATE_ANY_XOFF`；
- `netif_tx_wake_queue()`：原子清除 driver XOFF；只有原先确实 stopped 时才在 RCU 读锁内取 qdisc 并调用 `__netif_schedule()`；
- `netif_tx_stop_all_queues()`：逐队列调用 stop helper。

本轮没有发现版本变化造成 generic TX queue stop/wake 状态位语义、唤醒后 qdisc 重新调度动作或 memory-ordering 配对发生变化。网卡驱动是否正确调用 stop/wake、是否在资源恢复时唤醒，属于驱动实现和运行时行为，本轮不作推断。

### 23.3 BQL：发送记账与完成记账

`netdev_tx_sent_queue()` 三版函数体逐字一致：在 `CONFIG_BQL` 开启时调用 `dql_queued()`；若可用额度不足，则更新时间戳、设置 STACK_XOFF，并通过屏障和二次额度检查避免与 completion 并发时永久停队列。

`__netdev_tx_sent_queue()` 三版一致：
- `xmit_more=true` 时只记入 queued bytes，并返回当前 driver queue 是否已 stopped；
- 最后一包（`xmit_more=false`）调用 `netdev_tx_sent_queue()` 并返回 true，提示驱动应 kick/doorbell。

`netdev_tx_completed_queue()`：
- 6.1.116 与 6.1.174 函数体一致；
- 6.12 仅在既有 `smp_mb()` 行增加注释，明确 `netdev_txq_completed_mb()` 依赖该屏障；可执行语句和顺序未变。

因此，本轮未发现 BQL queued/completed 计数、额度判断、STACK_XOFF 设置/清除或完成后 qdisc 唤醒逻辑的行为变化。实际是否编译启用 `CONFIG_BQL`、驱动是否调用 sent/completed helper，仍需目标配置和驱动源码证据。

### 23.4 TX watchdog timeout

`dev_watchdog()` 三个固定端点函数体完全一致：
- 仅在设备 present、running、carrier OK 且 qdisc 非 noop 时检查；
- 遍历 TX queues，仅检查 `netif_xmit_stopped()` 的队列；
- 使用与 queue stop/sent 路径配对的屏障读取 `trans_start`；
- 超时后增加 `trans_timeout`、发出 `net_dev_xmit_timeout` trace 和内核日志；
- 冻结 queues 后调用驱动 `ndo_tx_timeout(dev, queue)`，再解冻；
- 按最早发送时间重设 watchdog timer。

6.1.116→6.1.174 与 6.1→6.12 均未发现 watchdog 判断条件、timeout 时间计算、驱动 timeout callback 调用或 timer 重排逻辑变化。故本轮没有发现通用 watchdog 在新版本中更容易误判/漏判 TX 停滞的源码差异。

### 23.5 skb completion 与释放路径

驱动成功完成发送后，常见语义是通过 `dev_consume_skb_any()` / `napi_consume_skb()` 消费 skb；丢弃路径则使用 kfree/drop-reason 相关接口。当前方向二只审计网络核心提供的通用生命周期，不据此推定 Panther 驱动具体使用哪一个 helper。

已核对的版本变化：
- `consume_skb()`：6.1.116 与 6.1.174 一致；6.12 的消费 tracepoint 增加调用者地址参数，随后仍执行 `__kfree_skb()`。
- `napi_consume_skb()`：三版均先处理零 budget 的非 NAPI 情况，再检查 skb 引用计数；clone 仍走 `__kfree_skb()`，普通 skb 释放资源后进入 NAPI skb cache。6.12 增加 trace caller 参数，并将 `skb_release_all(skb)` 改为 `skb_release_all(skb, SKB_CONSUMED)`，以便释放路径携带消费原因。
- `skb_release_all()` / `skb_release_data()`：6.12 增加 `enum skb_drop_reason` 参数，并将 reason 传给 frag_list 的 `kfree_skb_list_reason()`；普通 fragment unref、zcopy 清理、head 释放及 page-pool recycle 主体仍保留。
- skb data refcount：6.1 在 `skb_release_data()` 内直接使用 `atomic_sub_return()`；6.12 抽出 `skb_data_unref()` helper，针对 clone/dataref 已处于最后一个引用的情形先读计数并使用 `smp_rmb()`，否则执行原有 atomic decrement。其目的为重构共享数据引用判断；没有发现普通单 skb 的 fragment/head 释放动作被删除。
- 6.12 的 skb head 分配器增加 small-head cache 分支，属于 skb 内存分配/回收优化；不是 TX queue handoff 或发送状态机变化。

这些变化主要涉及释放路径的 drop/consume reason 可追踪性、共享数据引用计数整理和内存缓存优化。当前没有发现它们会在 skb 尚未交给驱动前改变普通 UDP TX 的发送结果；若驱动 completion 错误地重复释放、漏释放或错误回收 DMA buffer，那属于驱动所有权/完成处理，不能由本节 generic skb helper 静态比较代替。

### 23.6 本轮结论

| 子项 | 6.1.116→6.1.174 | 6.1→6.12 | TX 判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| `netdev_start_xmit()` / driver return | 一致 | 调用封装一致 | 无通用交付/返回码变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `xmit_more` 状态 | 一致 | PREEMPT_RT 下改为 task-local；非 RT 仍 per-CPU | 条件性执行上下文适配 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| queue stop/wake | 一致 | 一致 | 未发现队列状态机回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| BQL sent/completed | 一致 | 可执行逻辑一致 | 未发现记账/唤醒变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| watchdog | 一致 | 一致 | 未发现 timeout 判定变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| skb consume/free | 一致 | reason/caller tracing、dataref helper、small-head cache | 生命周期诊断/内存管理重构，未发现普通 TX handoff 回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**本轮结论：**
1. 从 `netdev_start_xmit()` 到 `ndo_start_xmit` 的通用封装和返回码处理，三个版本一致。
2. TX queue stop/wake、BQL 和 watchdog 的核心可执行逻辑没有发现版本回归。
3. 6.12 的 `xmit_more` 改动仅在 PREEMPT_RT 配置下改变状态存储位置；非 RT 保持原 per-CPU 行为。
4. 6.12 skb 生命周期变化集中在 reason/caller trace、共享 dataref helper 和小型 head cache；目前未发现会阻断普通 UDP skb 交付的新增 generic TX 丢弃门。
5. 至此方向二 TX 通用网络核心已覆盖到驱动调用封装、队列流控、watchdog 与 skb completion/free 边界；但方向二整体仍需按原计划核对剩余网络核心子项，不能据此宣布方向二结项，也不提前进入方向三。

本轮仅做固定源码端点静态比较；没有构建、修改配置、执行设备操作或实机网络试验。

## 24. 本轮追加核验：NET_TX_SOFTIRQ、qdisc reschedule、completion_queue 与 TX trace

**四版本回溯状态：** 本节 NET_TX_SOFTIRQ、output_queue/completion_queue、qdisc reschedule 和 tracepoint 比较未包含 6.1.65 源码端点。现有结论只对三个已锁定源码端点成立；6.1.65 黄金 A 的对应实现仍待补，不能形成四版本共同结论。

本轮继续按 TX 方向核对第 23 节之后的软中断调度和 skb 延迟释放路径，重点确认 `NET_TX_SOFTIRQ` 的两条工作队列分别承担什么职责，以及 6.12 的改动是否可能影响普通 UDP 报文继续进入 qdisc/驱动。

固定源码端点仍为第 2 节的 6.1.116、6.1.174、6.12.81 commit。本轮读取：
- `net/core/dev.c`：`net_tx_action()`、`__netif_schedule()`、`__netif_reschedule()`、`netif_schedule_queue()`、`netif_schedule()`、`netif_tx_wake_queue()`，以及 IRQ-context skb free helper；
- `net/sched/sch_generic.c`：`qdisc_run()`、`__qdisc_run()`、`qdisc_restart()`、`dequeue_skb()`；
- `kernel/softirq.c`：softirq dispatch/raise 框架；
- `include/trace/events/net.h`、`include/trace/events/skb.h`：TX 与 skb free/consume tracepoint。

### 24.1 NET_TX_SOFTIRQ 的两个队列不可混为一谈

三版 `net_tx_action()` 均按顺序处理当前 CPU 的 `softnet_data`：
1. `completion_queue`：取出 IRQ-context 延迟释放的 skb，完成 trace 后释放 skb backing resources；
2. `output_queue`：取出被标记为需要调度的 qdisc 链表，清除 qdisc scheduled bit 并调用 `qdisc_run(q)`；
3. 处理 XFRM device backlog。

必须明确：**completion_queue 不是网卡 TX DMA completion ring，也不负责 reclaim TX descriptor。** 它是 skb 生命周期的延迟 free/consume 队列。真正的硬件 TX completion、descriptor 回收及 DMA unmap 由具体网卡驱动的 IRQ/NAPI 路径处理，不属于本轮 generic softirq 的 completion_queue。

### 24.2 qdisc reschedule 到 NET_TX_SOFTIRQ 的触发链

三版以下 helper 函数体一致：
- `__netif_schedule()` / `netif_schedule()`：通过 `test_and_set_bit(__QDISC_STATE_SCHED)` 避免重复排队；
- `__netif_reschedule()`：在本地 IRQ 保护下，将 qdisc 追加到当前 CPU 的 `softnet_data.output_queue`，更新 tail pointer，并调用 `raise_softirq_irqoff(NET_TX_SOFTIRQ)`；
- `netif_schedule_queue()`：仅在 TX queue 未 stopped 时取出 qdisc 并 schedule；
- `netif_tx_wake_queue()`：只有成功清除 driver XOFF 状态时才重新 schedule qdisc。

`net_tx_action()` 从 output_queue 摘取链表时，三版都先在关闭本地 IRQ 的短临界区内摘取并重置 tail pointer，再在 RCU 读侧逐个处理 qdisc；对非 NOLOCK qdisc 获取 root lock，对已 deactivate 的 NOLOCK qdisc 清除 scheduled bit 后跳过，正常情况清除 scheduled bit 并调用 `qdisc_run()`。

以上 schedule bit、per-CPU output_queue 入队、softirq raise、qdisc deactivate 保护和重新运行逻辑，在三个固定端点没有发现行为差异。未发现 6.12 改变 qdisc 被唤醒后重新进入 TX 主路径的通用机制。

### 24.3 qdisc_run 的 budget 差异属于前述调度预算项

- 6.1.116→6.1.174：`qdisc_restart()` / `dequeue_skb()` 增加 packet budget 参数；`qdisc_run()` 和 `__qdisc_run()` 将 quota 传入 restart/dequeue。
- 6.1.174→6.12.81：该 budget 传递实现一致；6.12 仅将 `dev_tx_weight` 的读取改为 `net_hotdata.dev_tx_weight`。
- `qdisc_run()` 在 quota 耗尽时，对 NOLOCK qdisc 设置 MISSED bit；普通锁定 qdisc 重新调用 `__netif_schedule()`，以便后续 softirq 再次推进。
- `qdisc_restart()` 在 dequeue 成功后按 skb queue mapping 选择 TX queue，再进入 `sch_direct_xmit()`。

这些变化与第 22 节的 qdisc budget 结论一致：影响单轮批量出队/调度公平性，不改变普通单 skb 的最终 driver handoff 规则。未发现新增的单包 drop 条件。

### 24.4 completion_queue 的 IRQ 延迟释放语义与版本变化

6.1.116 与 6.1.174 使用 `__dev_kfree_skb_irq()` 将最后一个 skb 引用放入当前 CPU 的 `softnet_data.completion_queue`，并 raise `NET_TX_SOFTIRQ`。其关键步骤为：
- 检查/递减 skb users refcount；
- 将 free reason 写入 skb control block；
- 在本地 IRQ 保护下将 skb 链入 completion_queue；
- raise NET_TX_SOFTIRQ。

6.12 将相关 API 改为显式 reason 形式（例如 `dev_kfree_skb_irq_reason(skb, reason)`），并使用 `enum skb_drop_reason` 传递释放原因。其入队、refcount 处理、IRQ 临界区、completion_queue 链接和 softirq raise 主体保持一致。

`net_tx_action()` 对 completion_queue 的版本差异：
- 6.1.116 与 6.1.174：根据旧 free-reason 标记区分 consume/free trace；fclone skb 直接 `__kfree_skb()`，普通 skb 使用 `__kfree_skb_defer()`，释放资源后进入 NAPI skb cache。
- 6.12：reason 改用 `enum skb_drop_reason`；consume/free trace 增加 caller/location 信息；fclone skb 仍直接 `__kfree_skb()`，普通 skb 改用 `__napi_kfree_skb(skb, reason)`，将 reason 传入 `skb_release_all()` 后进入 NAPI skb cache。

这属于 IRQ 延迟 skb 释放与 drop-reason 诊断 API 的演进。没有发现其改变 output_queue 的 qdisc 调度链，也没有发现它承担或取代网卡 DMA completion。不能把 6.12 的 helper 重命名/参数变化误判成 TX descriptor completion 算法改变。

### 24.5 NET_TX_SOFTIRQ 注册与 generic softirq 框架

三个版本均在网络核心初始化时将 `NET_TX_SOFTIRQ` 注册到 `net_tx_action`，并将 `NET_RX_SOFTIRQ` 注册到 `net_rx_action`。IRQ-context skb free 和 qdisc reschedule 都通过 `raise_softirq_irqoff(NET_TX_SOFTIRQ)` 请求处理。

6.12 的 `net_tx_action` 回调签名从接收 `struct softirq_action *` 改为无参数回调，属于 softirq action API 的版本接口变化；其内部仍读取当前 CPU 的 `softnet_data` 并处理相同的 completion_queue、output_queue 与 XFRM backlog。没有发现 generic softirq 的 raise/dispatch 改动导致 NET_TX_SOFTIRQ 被移除、延迟条件改变或队列处理顺序变化。

### 24.6 TX tracepoint 对比

`include/trace/events/net.h`：
- `net_dev_start_xmit`、`net_dev_xmit`、`net_dev_xmit_timeout` 三版的主要事件字段与语义保持一致；`net_dev_xmit` 仍记录 skb 地址、长度、驱动返回码和设备名。
- 这组 trace 可用于区分“进入 ndo_start_xmit”与“驱动返回 OK/BUSY”，但事件本身不能证明 PHY 已将帧实际发送到线缆。

`include/trace/events/skb.h`：
- 6.1.116 与 6.1.174 的 `kfree_skb` 记录 skb、释放位置和 drop reason；`consume_skb` 只记录 skb 地址。
- 6.12 的 `kfree_skb` 增加 `rx_sk` 字段；`consume_skb` 增加调用位置字段，并以符号形式输出位置。
- 这些是 skb 生命周期追踪信息增强，不改变 TX packet 发送动作。尤其 `consume_skb` 表示 skb 被消费/释放，不等于硬件 TX success；硬件发送结果仍需结合 `net_dev_xmit` 返回码、驱动统计和具体驱动 completion 证据判断。

### 24.7 本轮结论

| 子项 | 6.1.116→6.1.174 | 6.1.174→6.12.81 | TX 判断 | 6.1.65 黄金 A 状态 |
|---|---|---|---| --- |
| `NET_TX_SOFTIRQ` output_queue | 一致 | 一致 | qdisc reschedule 机制无变化 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| qdisc schedule bit / per-CPU queue | 一致 | 一致 | 未发现唤醒链回归 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| qdisc_run budget | 增加 packet budget | 延续；dev_tx_weight 迁移 | 调度预算变化，不是单包 drop | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| completion_queue | 一致 | free-reason API 改为 skb_drop_reason | 延迟 skb free，不是 DMA completion | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| `net_tx_action()` | 一致 | 回调签名、reason trace 与 free helper 调整 | 队列处理职责/顺序保持 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |
| net TX tracepoints | 一致 | skb trace 增加 rx_sk/caller location | 诊断信息增强，不代表物理发送成功 | 未纳入该表的函数/模板逐项比较；源码端点待锁定，不能由 6.1.116 代替 |

**本轮结论：**
1. generic `NET_TX_SOFTIRQ` 的 qdisc output_queue 调度与重新运行路径在三个版本保持一致。
2. completion_queue 负责 IRQ-context skb 延迟释放，不负责硬件 TX DMA completion；6.12 的变化主要是 drop reason 类型和释放 helper/API 演进。
3. 本轮未发现 6.1.116→6.1.174 或 6.1→6.12 的 generic TX softirq 调度回归，也未发现普通单 skb UDP 的新增丢弃门。
4. TX tracepoint 可帮助建立软件交付证据链，但 `net_dev_xmit rc=NETDEV_TX_OK` 或 `consume_skb` 均不能单独证明 Ethernet PHY 已完成物理发送。

本轮仅做固定源码端点静态比较；未构建、未修改系统配置、未执行实机操作。方向二仍未结项；尚需按原定顺序完成 TX 统计/drop reason/Kconfig 等剩余网络核心子项，再回读 B2-0 原始计划确认方向三。


## 25. 对已完成方向二子项的四版本回溯修订（2026-11-25）

### 25.1 修订原因

复核方向二既有报告后确认：第 3～24 节多数源码对照实际以 6.1.116、6.1.174、6.12.81 三个已锁定源码端点开展。虽然这些分析可保留为候选差异，但此前章节标题和阶段结论容易让读者误以为已完成两条黄金基准对两条故障线的完整横向比较。现按第 2 节标准逐项修订证据等级，并明确补入 6.1.65 黄金基准 A。

### 25.2 6.1.65 可复用的已知证据

以下证据已存在于仓库，不要求用户重复采集：

- 原版 Armbian 6.1.65 原始镜像静态审计：已归档 `config-6.1.65-ophub`、`modules.builtin`、Panther X2 DTB、uInitrd 等资产；精确 Actions run / checkout SHA 不可证。
- 2026-11-24 原版 TF 实机记录：确认运行 `6.1.65-ophub`，板载 Ethernet 驱动绑定、RTL8211F、1Gbps Full、DHCP IPv4、网关 IPv4、外部 IPv4 与 DNS 查询成功。
- 四版本资产矩阵已确认 6.1.65 与 6.1.116 均为正常实机黄金基准；两者的 GMAC DTB 语义已完成既有交叉核对。本轮方向二不重复这些已结项工作。

这些证据证明 6.1.65 是真实、有效的黄金基准 A；但它们不能单独给出 6.1.65 的 Linux 网络核心 C 函数实现。

### 25.3 已完成子项逐项回溯结果

| 原报告章节 | 已审计主题 | 原有源码比较范围 | 6.1.65 回溯状态 | 修订后结论等级 |
|---|---|---|---|---|
| §3 | Kconfig/Makefile、loopback、net_dev_init、inet_init | 6.1.116 / 6.1.174 / 6.12.81 | config 与 built-in 资产可复用；网络核心符号需从原始 config 补齐；源码函数待精确端点 | 三端点源码结论；6.1.65 配置/源码待补 |
| §4、§8 | IPv4 output、qdisc、checksum、fragment、UDP GSO | 三端点 | 实机 IPv4 正常是行为证据，不是函数源码证据 | 三端点源码结论 |
| §9 | netdevice feature、ARP/neighbour output、route key | 三端点 | DHCP/IPv4 成功可作行为参照，内部函数待补 | 三端点源码结论 |
| §11 | RX dispatch、IPv4 input、UDP socket/GRO/receive queue | 三端点 | 没有 6.1.65 对应源码审计 | 三端点源码结论 |
| §12 | 网络核心 Kconfig 模板 | 候选模板/三端点证据 | 不得以模板替代 6.1.65 原始 config；需逐符号映射 | 配置对照未完成四版本闭环 |
| §14 | AF_PACKET、VLAN/bridge RX、Netfilter ingress | 三端点 | 源码和实际配置均待补 | 三端点源码结论 |
| §16 | conntrack、NAT hook、tuple lookup | 三端点 | 实机 IPv4 成功不能替代内部源码比较 | 三端点源码结论 |
| §18 | IPv4 checksum、fragment reassembly、本机交付 | 三端点 | 实机 IPv4 成功仅为行为证据 | 三端点源码结论 |
| §19 | FIB trie、policy routing、route lookup | 三端点 | DHCP 默认路由可复用为行为参照；源码/配置待补 | 三端点源码结论 |
| §20 | ARP RX、neighbour NUD | 三端点 | 实机通信成功不证明函数实现一致 | 三端点源码结论 |
| §21 | UDP sendmsg、IP skb 构造/追加 | 三端点 | DHCP/IPv4 成功不等于 sendmsg 函数源码已比较 | 三端点源码结论 |
| §22 | TX queue、qdisc、validate、ndo_start_xmit | 三端点 | 黄金 A 已通过真实 DHCP/IPv4；对应 TX 核心源码未审 | 三端点源码结论；TX 核心待补 |
| §23 | netdev_start_xmit、queue flow control、BQL、watchdog、skb free | 三端点 | 没有 6.1.65 函数源码比较 | 三端点源码结论 |
| §24 | NET_TX_SOFTIRQ、qdisc reschedule、completion_queue、trace | 三端点 | 没有 6.1.65 函数源码比较 | 三端点源码结论 |

### 25.4 对此前结论措辞的统一修订

1. 第 3～24 节原有的函数级差异仍保留，不要求重复下载或重跑三个已审计源码端点。
2. 所有“正常线与故障线的差异”“两条黄金线共同具备”“故障版本共同缺失”等表述，在 6.1.65 对应证据未补齐前，均只能视为待验证假设；本报告已在各章节开头标明范围。
3. 第 22～24 节中关于普通单 skb UDP、qdisc、驱动调用封装、queue flow control、NET_TX_SOFTIRQ 的结论，均限定为三个源码端点之间的比较结果，不能宣称为四版本结论。
4. 6.1.65 的正常实机网络结果是强行为基准，但不反向证明其网络核心内部实现与 6.1.116 相同。
5. 6.1.79、6.1.112 继续作为辅助正常样本；本轮不因其已知实机正常就推定其源码等同于 6.1.65 或 6.1.116。

### 25.5 后续修订顺序

1. 先对 6.1.65 原始镜像现有 `config-6.1.65-ophub` 做只读提取与网络核心符号映射，覆盖本报告已完成子项涉及的 Kconfig 选项；不得重做已完成的原始镜像、DTB 或实机网络测试。
2. 继续追溯 6.1.65 的原始源码身份。优先利用镜像构建时间、release 字符串、内嵌 IKCONFIG、包元数据及 Armbian/Ophub 对应发行版源码线索；没有可验证的 commit 时明确保留“源码端点未锁定”。
3. 对能锁定源码的 6.1.65 子项，按 §3～§24 原顺序补入函数级差异；不能锁定的子项保留证据缺口，不用 6.1.116 代替。
4. 只有在四版本矩阵的对应子项确实补齐后，才允许给出该子项的四版本横向结论；之后再按原计划推进尚未审计的方向二子项。
5. 方向二仍未结项；不进入方向三、B2-1 或任何实机试验。

**修订性质：** 本次为既有方向二报告的证据等级与比较矩阵纠偏。没有执行构建、设备操作、配置修改或网络测试。


## 26. TX 统计、skb drop reason 与相关 Kconfig：四版本横向审计（2026-11-25）

### 26.1 审计范围与四版本源码身份

本项只审计 Linux 网络核心的 TX 统计记账、generic `tx_dropped` 计数、skb 释放原因传递、统计读取接口及相关 Kconfig。**不进入 STMMAC 驱动私有统计、DMA descriptor、completion/reclaim 或硬件计数器**；这些不是 generic network core 的职责。

| 样本 | 本项使用的源码端点 | 证据等级 |
|---|---|---|
| 6.1.65 黄金 A | `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` | 高置信度候选；与原始 Kernel build 时间和版本提交吻合，但不是原始 Actions / 二进制构建证明 |
| 6.1.116 黄金 B | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` | 固定源码比较端点；6.1.116 原始 Image 的精确构建 source SHA 仍未闭环 |
| 6.1.174 故障 A | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` | 原始 Actions run #296 job log 确认 |
| 6.12.81 故障 B | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` | 原始 Actions 构建来源已锁定 |

本项直接读取的关键源码文件及 Git blob SHA：

| 文件 | 6.1.65 候选 | 6.1.116 | 6.1.174 | 6.12.81 |
|---|---|---|---|---|
| `net/core/dev.c` | `0f4a91f0bef343719707bc9e88ee5eb7ced9e9d6` | `3c3eacad5e9e539b92135c44074dc9ddec57cf61` | `9ad32aa60c2c8864fff81845adfdb51538a8584f` | `6788518e52b8b368248b40ab6f4cac739bfcf73f` |
| `include/linux/netdevice.h` | `d1f2f6dba96ab95c2aed7d6444f491aa26a843d7` | `3c6663ed3cf6e4482c434dfa350a3a55a73c58ce` | `54793dc5c6c4724dae00d4615e463e2ecf9e7edb` | `23e5367df4cf23d2ce43f321ce3aa8ad5e6363c6` |
| `net/core/skbuff.c` | `73b1e0e53534ed914b70b5e60a1ae80bd92e0330` | `e5436c5f52399290be27d3c40dbb95dcff63c774` | `c4b982a90f63f2f606f87aac860067e4375e5722` | `c3e1395d8ac5c43377ca0717ead756d530aaafa2` |
| `include/trace/events/skb.h` | `50a974f7dfb4759db0417bdfb4cc473f912f930c` | 同左 | 同左 | `b877133cd93a80f6b130fab64f334ecdeab8c8fd` |
| `net/Kconfig` | `73b06c41cdedb971a927a48fc9d4d7c30b195048` | `12699f98453c32be863d6434f20d5b9192aabf3e` | 同 6.1.116 | `fc0ee6d81a74b28d47b8d69af5cfbae8cdb2a7b9` |

### 26.2 TX packets / bytes 统计记账

核对函数：
- `include/linux/netdevice.h:dev_sw_netstats_tx_add()`
- `net/core/dev.c:dev_fetch_sw_netstats()`
- `net/core/dev.c:dev_get_stats()`
- `net/core/dev.c:dev_get_tstats64()`
- `net/core/net-procfs.c:dev_seq_printf_stats()`

结果：

1. 四端点的 `dev_sw_netstats_tx_add()` 函数体一致：在当前 CPU 的 `pcpu_sw_netstats` 上通过 `u64_stats_update_begin/end()` 更新 `tx_bytes` 与 `tx_packets`。未发现 6.1.65→6.1.116→6.1.174→6.12.81 的 generic TX 计数增加/累加语义变化。
2. 6.1.65、6.1.116、6.1.174 的 `dev_fetch_sw_netstats()` 使用 `u64_stats_fetch_begin_irq()` / `u64_stats_fetch_retry_irq()`；6.12 改为 `u64_stats_fetch_begin()` / `u64_stats_fetch_retry()`。读取字段、每 CPU 遍历及累加到 `rtnl_link_stats64` 的语义相同；这是统计读取同步 API 的演进，不是发送路径改变。
3. 6.1 三端点的 `dev_get_stats()` 先按 `ndo_get_stats64`、`ndo_get_stats`、再退回 `dev->stats` 的顺序取得设备统计，之后汇总 generic per-CPU `rx_dropped/tx_dropped/rx_nohandler/rx_otherhost_dropped`。
4. 6.12 的 `dev_get_stats()` 在没有 `ndo_get_stats64`、`ndo_get_stats` 时新增 `pcpu_stat_type` 分支：`NETDEV_PCPU_STAT_TSTATS` 调用 `dev_get_tstats64()`，`NETDEV_PCPU_STAT_DSTATS` 调用 `dev_get_dstats64()`，否则仍回退 `dev->stats`。该变化改变部分设备的 generic 统计取值来源，不改变 TX skb 的构造、排队或驱动交付。对 Panther 实际设备是否命中该 fallback，必须以对应驱动是否提供 `ndo_get_stats64` 为准；不能仅凭 generic core 代码推断。
5. 四端点 `dev_get_tstats64()` 与 `dev_sw_netstats_tx_add()` 的核心累计字段保持一致。
6. 四端点 `dev_seq_printf_stats()` 的 `/proc/net/dev` 输出字段和顺序一致：TX bytes、packets、errors、dropped 等仍来自 `rtnl_link_stats64`。该接口显示聚合计数，不显示 skb drop reason。

**判断：** 没有发现 generic TX packets/bytes 记账变化会阻断普通 UDP/DHCP 报文发送。6.12 的差异属于统计读取 fallback 与同步 API 调整。

### 26.3 generic TX dropped 计数器

四端点均保留 `dev_core_stats_tx_dropped_inc(dev)` 的四处调用点，函数所在路径及计数职责一致：

| 调用场景 | 四版本对照 | 含义 |
|---|---|---|
| 发送前 skb 校验失败路径（`out_null`） | 四端点均有 | skb 未通过 generic TX validation，计入 TX dropped |
| netdevice/qdisc 发送队列异常退出并释放 skb list | 四端点均有 | generic TX 队列路径丢弃 skb |
| qdisc/direct-transmit 的 drop 返回路径 | 四端点均有 | 发送调度路径返回 `NET_XMIT_DROP` 并释放 skb |
| generic XDP TX 失败释放路径 | 四端点均有 | XDP_TX 失败后释放 skb 并记 TX dropped |

6.1.65、6.1.116、6.1.174 的 `include/linux/netdevice.h` 通过 `dev_core_stats()` 读取 per-CPU 指针；指针为空时调用 `netdev_core_stats_alloc()`，成功后 `this_cpu_inc(p->FIELD)`。6.12 将其改为 `netdev_core_stats_inc(dev, offsetof(...))`，在 `net/core/dev.c` 中完成相同的 READ_ONCE、按需分配和当前 CPU 计数增加。分配失败时不增加该统计值；这是计数记录失败，不是丢弃或阻断数据包的新条件。

**判断：** 6.12 的 helper 重构没有改变 TX dropped 的四个 generic 计数触发点，也没有新增普通单 skb UDP 的通用丢弃点。计数器的增加表示 skb 已在相应 software drop 分支被丢弃，不能反过来将计数本身解释成导致丢包的原因。

### 26.4 skb drop reason 与 deferred free

#### 6.1.65 / 6.1.116 / 6.1.174

- 核心 drop reason 定义位于 `include/net/dropreason.h`；三个源码端点文件 blob SHA 相同。
- `kfree_skb_reason()` 在 skb 最后一个引用释放时，将调用位置与 `enum skb_drop_reason` 传给 `kfree_skb` tracepoint，再释放 skb。
- deferred completion queue 使用 `enum skb_free_reason` 区分较粗的 dropped / consumed 生命周期原因；`__dev_kfree_skb_irq()` 将该值存入 skb cb，之后由 `NET_TX_SOFTIRQ` completion_queue 处理。

#### 6.12.81

- drop reason 核心枚举移至 `include/net/dropreason-core.h`，`include/net/dropreason.h` 另行提供 subsystem 扩展注册接口；新增 subsystem reason list 注册/注销能力，并扩充部分 reason 枚举。
- deferred free API 改为 `dev_kfree_skb_irq_reason()` / `dev_kfree_skb_any_reason()`，使用 `enum skb_drop_reason` 传递更具体的释放原因，而不是旧版较粗的 `enum skb_free_reason`。
- `kfree_skb` tracepoint 增加 `rx_sk` 字段；`consume_skb` tracepoint 增加调用位置，提升释放路径诊断信息。

这些改动增强了丢弃原因表达和延迟释放追踪能力。它们发生在 skb 已经进入释放/记录阶段，不改变是否将普通 UDP skb 放入 TX queue，也不改变 `ndo_start_xmit` 的调用条件。此前 §22 已审计的 6.12 unreadable-fragment 新丢弃门属于另一项发送前校验条件，不能与本节 drop-reason API 重构混为一谈。

### 26.5 Kconfig 与最终配置证据

#### BQL

四版本 `net/Kconfig` 的 `BQL` 定义：
- 6.1.65 候选、6.1.116、6.1.174：`bool`，依赖 `SYSFS`，select `DQL`，`default y`；
- 6.12.81：增加 `prompt "Enable Byte Queue Limits"`，其 `depends on SYSFS`、`select DQL`、`default y` 保持不变。

可确认的配置证据：
- 6.1.65 原始 Kernel 内嵌 IKCONFIG：`CONFIG_BQL=y`；
- 6.1.116 实际完整配置与 general `config-6.1` 模板 7,677 个符号零差异，模板值 `CONFIG_BQL=y`；
- 6.1.174 官方包确实包含实际 `config-6.1.174-rk35xx-ophub`（已有包内文件 SHA256 记录），但现有归档摘要没有逐项抄录 `CONFIG_BQL`；同一时点的 RK35xx config-6.1 候选模板为 y，不能冒充已核对的包内最终值；
- 6.12.81 RK35xx config-6.12 候选模板为 `CONFIG_BQL=y`；此前审计未取得完整 6.12.81 最终 `.config`，因此不将模板值升级为最终构建值。

BQL 的功能仍是 TX queue byte accounting / queue limit 控制，相关发送队列 stop/wake 已在 §23 审计；本节未发现 BQL Kconfig 依赖或默认值变化导致的版本回归。

#### NET_DROP_MONITOR

四端点 `net/Kconfig` 的 `NET_DROP_MONITOR` 定义一致：tristate，依赖 `INET && TRACEPOINTS`，作为向用户空间 netlink 广播网络丢包告警的可选服务。它不参与报文转发、TX 排队或驱动交付。

配置证据边界：
- 6.1.116 实际配置与对应 general 模板完全一致，模板明确为 `# CONFIG_NET_DROP_MONITOR is not set`；
- 6.12.81 RK35xx 候选模板也明确为 not set，但不是完整最终构建配置；
- 6.1.65 实际内嵌 config 中未找到该符号配置行，故只记录“未见启用证据”，不把缺失行擅自解释为最终 n 值；
- 6.1.174 官方包内最终 config 文件已存在并归档 SHA256，但现有报告没有记录此符号的具体值；当前 RK35xx 候选模板为 not set，不代替包内最终配置。

**配置结论：** 没有证据表明四个实际系统都启用了 NET_DROP_MONITOR；它即使启用也只提供告警，不改变数据面。6.1.174 与 6.12.81 的该项最终配置值仍是配置证据缺口，不能从模板推定。

### 26.6 四版本结论矩阵

| 审计点 | 6.1.65 黄金 A | 6.1.116 黄金 B | 6.1.174 故障 A | 6.12.81 故障 B |
|---|---|---|---|---|
| `dev_sw_netstats_tx_add()` | 候选源码与 B 相同；实际配置 BQL=y | 固定源码端点；实际配置 BQL=y | 固定源码端点；BQL 最终配置待从包内 config 补录 | 固定源码端点；模板 BQL=y，最终配置未闭环 |
| generic `tx_dropped` 四处调用点 | 候选源码四处 | 四处 | 四处 | 四处 |
| per-CPU core stats increment | 旧 inline helper | 旧 inline helper | 旧 inline helper | helper 外移，按需分配/this_cpu_inc 语义保持 |
| `dev_get_stats()` | 旧 fallback | 旧 fallback | 旧 fallback | 新增 TSTATS/DSTATS fallback，属统计读取 |
| `/proc/net/dev` TX 字段 | 相同 | 相同 | 相同 | 相同 |
| skb drop reason / deferred free | 旧枚举与粗粒度 free reason | 同左 | 同左 | 枚举拆分/扩展，传递更细 reason |
| NET_DROP_MONITOR | 配置行未找到 | 实际配置 not set | 包内最终值待补 | 模板 not set，最终配置待补 |

### 26.7 本项结论与剩余边界

1. **未发现 generic TX 统计、drop reason 或 BQL 代码变化构成普通 UDP/DHCP 发送失败的解释。** TX packet/byte 计数更新一致，generic TX dropped 的四处调用点一致。
2. 6.12 的主要差异是统计读取 fallback、per-CPU 统计 helper 外移、drop reason 枚举/接口扩展和 tracepoint 诊断字段增强；它们不改变普通 UDP skb 的发送/交付决策。
3. `NET_DROP_MONITOR` 是可选告警服务，不是数据面过滤器；不能把其 Kconfig 存在等同于运行时启用或丢包。
4. BQL Kconfig 默认和依赖保持一致；6.12 增加 prompt 不代表 BQL 算法或默认状态发生回归。
5. 6.1.65 的源码仍是高置信度候选端点；6.1.174 包内 config 与 6.12.81 最终 `.config` 的个别符号值仍待从原始最终配置补录。不得用候选模板代替实际构建配置。
6. 本项完成了四版本源码差异筛查；最终配置层按上述证据等级保留缺口。方向二整体仍未结项，下一步须回到原始 B2-0 方向二待办顺序，核实剩余网络核心子项；不提前进入方向三或 B2-1。

**本轮性质：** 只读多版本源码、Kconfig 与已归档配置证据审计；未构建、未安装软件、未访问设备、未修改系统/网络配置、未执行发包或实机试验。


## 27. 按 §25.5 顺序补齐 6.1.65 黄金 A 的网络核心实际配置映射（2026-11-25）

### 27.1 任务来源与边界

本项不是新增专题，而是执行本报告 §25.5 第 1 项：对原始 6.1.65 镜像已经归档的 `config-6.1.65-ophub` 做只读提取，并映射此前 §3～§26 已审计子项涉及的网络核心 Kconfig 符号。

证据来自 Dropbox 中既有 `/kernel-config-evidence.zip`（文件 ID `id:9qHOnx-HLYoAAAAAAAAAFQ`，原始归档不修改）。通过 Dropbox 文件内容读取接口取得压缩包内文本，逐行提取配置项；没有重新解压或修改原始镜像，没有访问 Panther X2，也没有构建或运行任何代码。

### 27.2 6.1.65 实际配置：网络基础与协议入口

以下均为归档的 `config-6.1.65-ophub` 实际配置行，不是候选模板：

| 符号 | 6.1.65 实际值 | 说明 |
|---|---:|---|
| `CONFIG_NET` | y | 网络核心启用 |
| `CONFIG_INET` | y | IPv4/IPv6 Internet 协议栈启用 |
| `CONFIG_NETDEVICES` | y | 网络设备框架启用 |
| `CONFIG_NET_CORE` | y | 网络核心设备支持启用 |
| `CONFIG_PACKET` / `CONFIG_PACKET_DIAG` | y / y | AF_PACKET 与诊断支持启用 |
| `CONFIG_UNIX` | y | Unix domain socket 启用 |
| `CONFIG_NET_NS` | y | network namespace 启用 |
| `CONFIG_IPV6` | y | IPv6 built-in |
| `CONFIG_IP_ADVANCED_ROUTER` / `CONFIG_IP_MULTIPLE_TABLES` | y / y | 高级路由与多路由表启用 |
| `CONFIG_BPF` / `CONFIG_BPF_SYSCALL` | y / y | BPF 基础能力与 syscall 启用 |
| `CONFIG_XDP_SOCKETS` / `CONFIG_XDP_SOCKETS_DIAG` | y / y | AF_XDP 与诊断支持启用 |
| `CONFIG_NET_RX_BUSY_POLL` | y | RX busy-poll 支持启用 |
| `CONFIG_PAGE_POOL` | y | page-pool 支持启用 |
| `CONFIG_NET_SCHED` | y | traffic-control/qdisc 框架启用 |
| `CONFIG_BQL` | y | Byte Queue Limits 启用 |

### 27.3 Netfilter、conntrack、VLAN/bridge 与调度配置

| 符号 | 6.1.65 实际值 | 对照意义 |
|---|---:|---|
| `CONFIG_NETFILTER` | y | Netfilter 核心 built-in |
| `CONFIG_NETFILTER_INGRESS` / `CONFIG_NETFILTER_EGRESS` | y / y | ingress/egress hook 支持启用 |
| `CONFIG_NF_CONNTRACK` | y | conntrack built-in |
| `CONFIG_NF_DEFRAG_IPV4` | y | IPv4 conntrack defrag 支持 built-in |
| `CONFIG_NF_NAT` | m | NAT 核心为模块 |
| `CONFIG_NETFILTER_XTABLES` / `CONFIG_NETFILTER_XT_NAT` | m / m | xtables 核心及 NAT glue 为模块 |
| `CONFIG_IP_NF_IPTABLES` / `CONFIG_IP_NF_FILTER` / `CONFIG_IP_NF_NAT` | m / m / m | legacy IPv4 iptables/filter/NAT 为模块 |
| `CONFIG_NF_TABLES` | m | nftables 核心为模块 |
| `CONFIG_BRIDGE` / `CONFIG_BRIDGE_NETFILTER` | m / m | bridge 与 bridge-netfilter 为模块 |
| `CONFIG_VLAN_8021Q` | y | 802.1Q VLAN built-in |
| `CONFIG_BRIDGE_VLAN_FILTERING` | y | bridge VLAN filtering 支持启用 |
| `CONFIG_NET_CLS_BPF` / `CONFIG_NET_ACT_BPF` | m / m | BPF classifier/action 为模块 |
| `CONFIG_NET_SCH_INGRESS` | y | ingress qdisc 支持 built-in |

### 27.4 与此前章节关键配置差异的直接关系

1. **§12 网络核心 Kconfig：** 6.1.65 的实际配置确认 `NET`、`INET`、`NETDEVICES`、`NET_NS`、`BPF`、`XDP_SOCKETS`、`NET_RX_BUSY_POLL`、`PAGE_POOL`、`NETFILTER`、`BRIDGE`、`VLAN_8021Q` 等入口均有真实配置值。此前将 6.1.65 整列留空的配置证据缺口，现已在这些符号范围内补齐。
2. **§14 AF_PACKET/VLAN/bridge/Netfilter ingress：** `PACKET=y`、`VLAN_8021Q=y`、`BRIDGE=m)、`BRIDGE_VLAN_FILTERING=y)、`NETFILTER_INGRESS=y) 均为 6.1.65 实际值。它们表示功能构建形态，不证明运行时加载 bridge、创建 VLAN、注册 ingress hook 或安装过滤规则。
3. **§16 conntrack/NAT：** `NF_CONNTRACK=y)、`NF_DEFRAG_IPV4=y)，而 `NF_NAT=m)、`NETFILTER_XTABLES=m)、`NETFILTER_XT_NAT=m)、`IP_NF_IPTABLES=m)、`IP_NF_FILTER=m)、`IP_NF_NAT=m)。这确认 6.1.65 采用“conntrack/defrag built-in，NAT/iptables 相关功能模块化”的实际组合；是否有模块加载和 hook 生效仍是运行时问题。
4. **§18 IPv4 defrag：** `NF_DEFRAG_IPV4=y) 是实际配置证据；它不改变普通未分片 UDP 不进入 fragment queue 的源码判断。
5. **§19 FIB/policy routing：** `IP_ADVANCED_ROUTER=y)、`IP_MULTIPLE_TABLES=y) 确认相关构建能力启用；不证明运行时存在自定义 rule 或 DSCP selector。
6. **§22～§24 TX/qdisc/BQL：** `NET_SCHED=y)、`NET_SCH_INGRESS=y)、`BQL=y) 确认调度框架、ingress qdisc 与 BQL 均启用；具体 qdisc 选择及驱动是否调用 BQL helper，仍不能由配置单独推断。
7. **§26 TX 统计/drop reason：** `BQL=y) 与本节此前记录一致。对 `NET_DROP_MONITOR`，在本次取得的 6.1.65 配置文本中未找到对应配置行；按证据纪律只记录“未找到配置行”，不将其擅自解释为 n。对 6.1.65 不存在于该源码时代的 `NET_DEVMEM`，本配置未出现该符号；不能把 6.12 的 unreadable net_iov 路径外推到 6.1.65。

### 27.5 仍然保留的配置证据边界

- 本项只映射了 §3～§26 中明确涉及、且已从归档配置文本提取的网络核心符号；不等于对 6.1.65 全部 7,000+ 配置符号重新做全量差异分析。
- `NET_DROP_MONITOR`、`ETHERNET_PACKET_MANGLE` 等未在配置文本中找到行的符号，均保留为“未找到配置行”；需要结合该符号在对应源码 Kconfig 中是否存在、是否为隐藏符号及生成配置规则判断，不能一律视为 n。
- 配置值只说明编译形态；模块是否实际存在、装载、注册 hook、运行规则和历史 skb 状态，必须分别依赖相应资产或运行证据。
- 6.1.65 源码身份仍为高置信度候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc)，不是原始 Actions checkout SHA 的已证实构建来源。本节配置证据来自原始 Kernel 配置归档，不会因此提升源码 commit 的证据等级。

### 27.6 本项结论与下一顺序

**本项结项：6.1.65 黄金 A 的网络核心配置映射已按 §25.5 第 1 项完成。** 这补齐了 §12、§14、§16、§18、§19、§22～§26 多个章节中 6.1.65 配置栏的真实证据基础，但没有补齐 6.1.65 的函数级源码比较。

按 §25.5 原顺序，下一项是第 2 项：继续追溯 6.1.65 原始源码身份，优先复核镜像构建时间、release 字符串、内嵌 IKCONFIG、包元数据及 Armbian/Ophub 对应发行版源码线索；若仍不能取得可验证的精确 commit，继续明确保留“源码端点未锁定”，不得用 6.1.116 代替。该项完成后，才按 §3～§24 顺序补入能够可靠锁定的 6.1.65 函数级比较。

**方向二仍进行中。** 本轮仅读取既有 Dropbox 配置归档、源码报告与 Kconfig/配置证据；未访问设备、未构建、未修改系统/网络配置、未执行网络试验，也未新增审计专题。


## 28. 6.1.65 源码身份复核：证据等级不变（2026-11-25）

按 §25.5 第 2 项回读既有 6.1.65 来源证据后，确认：
- 原始 Kernel banner：`6.1.65-ophub`，编译器 Arm GNU Toolchain 13.2.1，构建时间字符串 2023-12-03 10:14:23 UTC；
- uInitrd uImage 时间 2023-12-03 10:19:56 UTC，与先生成 Kernel、随后生成 initramfs 的顺序相容；
- 原始镜像 `/etc/ophub-release` 记录 `KERNEL_REPO=ophub/kernel`、`KERNEL_TAGS=stable`、`PACKAGED_DATE=2023-12-07)，构建流程指向 Armbian + Ophub Rebuild；
- Panther X2 DTS 已进入 `unifreq/linux-6.1.y` 的历史来源链；候选源码提交 `4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` 的提交标题为 `up to 6.1.65)，时间与 Kernel banner 相容；
- 既有来源审计已查询构建日期附近的 Ophub Actions 运行记录，但未取得可用原始 run ID、dispatch inputs、实际 checkout SHA 和产物绑定证据。

**结论：** `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` 继续作为高置信度候选源码端点；仍不能称为 6.1.65 原始 Image 已证实的精确构建 commit。没有新证据可把等级提升为“已锁定”。本项不再扩大历史构建溯源；后续源码比较必须持续标注“候选端点”，不能以 6.1.116 代替。

## 29. §3 网络子系统配置入口与初始化：补入 6.1.65 候选源码端点

### 29.1 本次静态读取的四端点

| 版本 | 源码端点 | 本次文件 blob SHA |
|---|---|---|
| 6.1.65（高置信度候选） | `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` | `net/Kconfig` `73b06c41cdedb971a927a48fc9d4d7c30b195048`；`drivers/net/Makefile` `6ce076462dbfd26829472daa13096eea4136d266`；`drivers/net/loopback.c` `2e9742952c4e9b367c93db9ce589af1115bdb6e0`；`net/core/dev.c` `0f4a91f0bef343719707bc9e88ee5eb7ced9e9d6`；`net/ipv4/af_inet.c` `5d379df90c82624dcf52ff191c16734fb693768f` |
| 6.1.116 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` | `net/Kconfig` `12699f98453c32be863d6434f20d5b9192aabf3e`；`drivers/net/Makefile` `c2f4d4bbf65aa597c97912916e3f97ceebe235b4`；`drivers/net/loopback.c` `2e9742952c4e9b367c93db9ce589af1115bdb6e0`；`net/core/dev.c` `3c3eacad5e9e539b92135c44074dc9ddec57cf61`；`net/ipv4/af_inet.c` `cc013be9b02c48b6b56b7745d71a8ef6c59d2342` |
| 6.1.174 | `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` | `net/Kconfig` `12699f98453c32be863d6434f20d5b9192aabf3e`；`drivers/net/Makefile` `fb5531f35ab8ea2df0f15adc130f70b616d5b670`；`drivers/net/loopback.c` `206a1807a9b80248263eac7f10ce5332597427a2`；`net/core/dev.c` `9ad32aa60c2c8864fff81845adfdb51538a8584f`；`net/ipv4/af_inet.c` `a09b90552cf6e53d3a20ce30b9ea97ec29e0c084` |
| 6.12.81 | `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c` | `net/Kconfig` `fc0ee6d81a74b28d47b8d69af5cfbae8cdb2a7b9`；`drivers/net/Makefile` `13743d0e83b5fde479e9b30ad736be402d880dee`；`drivers/net/loopback.c` `013f00210b88d3d146e19b1823610d841dfc9c0d`；`net/core/dev.c` `6788518e52b8b368248b40ab6f4cac739bfcf73f`；`net/ipv4/af_inet.c` `81400aee0534b202abd72d4d4de9ed581684d484` |

### 29.2 Kconfig / Makefile 入口

- 四端点 `net/Kconfig` 的 `NET`、`INET` 入口结构一致；`drivers/net/Makefile` 均以 `obj-$(CONFIG_NET) += loopback.o` 接入 loopback。
- 6.1.65 与 6.1.116 的 `net/Kconfig` 唯一逐行差异是 6.1.116 新增隐藏 bool `ETHERNET_PACKET_MANGLE`（无 prompt、无 default；help 说明可由需要改写 Ethernet TX/RX 报文的 PHY driver 选择）。该符号在 6.1.65 候选源码中不存在；6.12.81 中也已移除。
- 6.1.65 与 6.1.116 的 `drivers/net/Makefile` 差异为 DSA 子目录接入写法：6.1.65 使用 `obj-$(CONFIG_NET_DSA) += dsa/`，6.1.116 改为 `ifdef CONFIG_NET_DSA / obj-y += dsa/ / endif`。四端点 loopback 编译入口没有变化；该差异不是 Panther GMAC 主链配置证据。
- 6.1.65 实际 config 文本未找到 `CONFIG_ETHERNET_PACKET_MANGLE` 行，且其候选源码 `net/Kconfig` 没有该符号定义；不能把 6.1.116 的可选 hook 反向套用到 6.1.65。

### 29.3 初始化与 loopback 函数级比较

直接按函数体边界提取并比较：
- `drivers/net/loopback.c:loopback_xmit()`：四端点函数体完全一致。
- `drivers/net/loopback.c:loopback_net_init()`：四端点函数体完全一致。
- `net/core/dev.c:net_dev_init()`：6.1.65、6.1.116、6.1.174 三端点函数体完全一致；6.12.81 新增 `net_dev_struct_check()`、每 CPU `net_page_pool_create()`、可选 backlog NAPI 线程注册、housekeeping timestamp 初始化及失败回滚清理，延续 §3.3 已有结论。
- `net/ipv4/af_inet.c:inet_init()`：6.1.65、6.1.116、6.1.174 三端点函数体完全一致；6.12.81 将 UDP/TCP `net_protocol` 对象放入 `net_hotdata` 后注册，并为 TCP 对象设置 `icmp_strict_tag_validation`，延续 §3.4 已有结论。

### 29.4 四版本结论修订

1. §3 的 loopback 两个关键函数现在有四端点源码证据；没有发现黄金 A 与黄金 B 在 loopback 发送/初始化函数上的差异。
2. §3 的 `net_dev_init()`、`inet_init()` 现有 6.1.116/6.1.174/6.12.81 差异结论已由 6.1.65 候选端点补齐 6.1 系列黄金 A；6.1.65 与 6.1.116/6.1.174 函数体一致。
3. 6.1.65→6.1.116 新增的 `ETHERNET_PACKET_MANGLE` 是网络核心 TX 交付前可选 hook 的源码/Kconfig 差异，值得保留在 §22 的四版本 TX 交付矩阵中；其实际编译启用与 Panther PHY 是否注册 callback，不能由本节 Kconfig 定义单独推断。驱动侧 callback 注册关系属于后续既定驱动方向，本节不提前审计。
4. DSA Makefile 书写方式差异不改变 loopback 接入，也没有证据表明它改变 Panther X2 的普通 IPv4/UDP TX 路径。

**本项结论：** §3 的 6.1.65 源码回溯完成（候选端点等级）。本节没有发现 6.1.65 与 6.1.116/6.1.174 在网络初始化、loopback 或 IPv4 初始化关键函数上的回归。唯一需要在方向二既有 TX 章节继续保留的是 6.1.65 与 6.1.116/6.1.174 的可选 `ETHERNET_PACKET_MANGLE` hook 存在性差异；不把它升级为已启用差异或故障根因。

**后续顺序：** 按 §25.5 第 3 项，继续以 §3～§24 原顺序补入能可靠锁定的 6.1.65 函数级差异；下一项是 §4 的 IPv4 output、`__dev_queue_xmit()`、qdisc 与 TX checksum/helper 路径。6.1.65 仍为高置信度候选源码端点，不改变其证据等级。方向二仍进行中，不进入方向三或 B2-1。


## 30. §4 IPv4 output、IP append 与 generic TX 前置路径：补入 6.1.65 候选源码端点（2026-11-25）

### 30.1 比较文件与函数

按 §25.5 第 3 项、§3～§24 原顺序，先补 §4 的 6.1.65 端点。只读读取四版本：
- `net/ipv4/ip_output.c`：`ip_local_out()`、`ip_output()`、`ip_finish_output()`、`__ip_append_data()`；
- `net/core/dev.c`：`__dev_queue_xmit()`、`validate_xmit_skb()`、`skb_checksum_help()`、`skb_csum_hwoffload_help()`；
- `net/sched/sch_generic.c`：`sch_direct_xmit()`、`qdisc_restart()`、`dequeue_skb()`；
- `net/core/skbuff.c`：`skb_segment()`。

6.1.65 使用第 29 节的高置信度候选源码端点；其余三个端点仍使用第 2 节固定来源。以下结论为候选源码函数比较，不提升 6.1.65 构建身份等级。

### 30.2 IPv4 output 与 IP 数据追加

- `ip_local_out()`：四端点函数体一致。
- `ip_finish_output()`：四端点函数体一致。
- `ip_output()`：6.1.65 与 6.1.116 函数体一致；6.1.174 增加 RCU read-side lock，并通过 `skb_dst_dev_rcu()` 获取目标设备；6.12 延续该 RCU 保护并将 OUT 统计更新移至后续路径（与 §4.1 既有结论一致）。6.1.65 黄金 A 与黄金 B 在该函数上没有差异。
- `__ip_append_data()`：6.1.65 与 6.1.116 的普通数据拷贝、fragment 计算、skb/page-frag 分配及队列追加主流程一致。两者可见差异集中在软件时间戳条件/读取：6.1.65 使用 `SKBTX_ANY_SW_TSTAMP` 与普通 `sk_tsflags` 读取；6.1.116 改为 `SKBTX_ANY_TSTAMP` 并使用 `READ_ONCE(sk->sk_tsflags)`。6.1.174 进一步整理 timestamp key 的持有/错误回滚（既有 §21 已记录）；6.12 新增 `MSG_SPLICE_PAGES` 条件分支，普通 UDP sendmsg 不设置该标志。未发现 6.1.65→6.1.116 改变普通小 UDP datagram 的 payload 拷贝或 IP fragment 计算语义。

### 30.3 Generic TX queue / checksum 入口

- `__dev_queue_xmit()`：6.1.65 与 6.1.116 函数体一致；6.1.174 新增 noqueue GSO skb-list 部分发送返回码处理，6.12 延续并将 ingress metadata 初始化迁移为 `tcx_set_ingress(skb, false)`。6.1.65 与黄金 B 在该函数没有差异。
- `validate_xmit_skb()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 新增 `!skb_frags_readable(skb)` 入口检查并直接释放 unreadable skb（§22.3 已说明触发条件及其为 generic TX 提前 drop 门）。
- `skb_checksum_help()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 新增 unreadable-fragment 检查，属于软件 checksum fallback 条件路径。
- `skb_csum_hwoffload_help()`：6.1.65 与 6.1.116/6.1.174 存在函数体差异，6.1.116→6.1.174 既有报告已定位为 IPv6 extension/jumbo-header offload 判定调整；该条件不适用于 IPv4 DHCP。6.12 延续相关演进。此项不得误写为 6.1.65 与 6.1.116 完全相同。
- `sch_direct_xmit()`：四端点函数体一致。
- `qdisc_restart()` / `dequeue_skb()`：6.1.65 与 6.1.116 函数体一致；6.1.174 起增加 packet budget 传递，6.12 延续。影响批量 dequeue / 调度预算，不改变单 skb direct-xmit 处理。
- `skb_segment()`：6.1.65 与 6.1.116 已存在实现差异；6.1.174 另有 shared-frag/GRO 元数据传播修正（此前 §5 已归档专项报告），6.12 延续并演进。该函数处理 GSO 分段，不可将其差异直接外推到普通非 GSO DHCP datagram。

### 30.4 本节对普通 UDP/DHCP TX 的判断

1. 黄金 A 与黄金 B 的 `ip_local_out()`、`ip_output()`、`__dev_queue_xmit()`、`validate_xmit_skb()`、`skb_checksum_help()`、`sch_direct_xmit()`、qdisc budget 前版本函数体一致。
2. 6.1.65→6.1.116 在 `__ip_append_data()` 的 timestamp flag/read accessor 与 `skb_csum_hwoffload_help()`、`skb_segment()` 存在差异；当前未发现这些差异改变普通小型 IPv4 UDP datagram 的 payload 构造、普通 checksum fallback 或单 skb generic TX 交付。
3. 6.1.174 的 GSO skb-list 返回码修正只命中分段列表；6.12 的 unreadable-fragment drop 门是实际新增条件性 generic TX 丢弃路径，但须 skb 含 unreadable net_iov fragment 才命中。当前无历史 DHCP skb 具备该 backing-memory 形态的证据。
4. 本节没有发现一个已证实、能解释普通 DHCP 单 skb 在 6.1.174 或 6.12.81 故障的 Linux 网络核心回归点。

### 30.5 对 §22 的补充：可选 ETHERNET_PACKET_MANGLE hook 的四版本差异

对 `net/core/dev.c:xmit_one()` 的四端点函数体再次提取比较：
- 6.1.65：没有 `CONFIG_ETHERNET_PACKET_MANGLE` 条件分支；
- 6.1.116、6.1.174：在 `dev_queue_xmit_nit()` 之后、`netdev_start_xmit()` 之前，若 `dev->eth_mangle_tx` callback 存在则调用它；callback 返回 NULL 时直接返回 `NETDEV_TX_OK`；
- 6.12.81：该分支被移除。

与 Kconfig 对照：
- 6.1.65 候选源码 `net/Kconfig` 不存在 `ETHERNET_PACKET_MANGLE` 符号；
- 6.1.116/6.1.174 的 `net/Kconfig` 存在隐藏 bool 定义，无 prompt/default，允许 PHY driver select；
- 6.12.81 的定义与调用均不存在；
- 6.1.65 原始实际配置中未找到该符号行，且候选源码不存在定义；不能推定 6.1.65 存在此 hook。

**证据边界：** 本项已确认网络核心通用 hook 的版本存在性差异，但 callback 是否被 Panther X2 的 PHY/网卡驱动注册、对应 config 是否最终置 y，必须依赖驱动侧证据。该问题按原计划留待方向三对应驱动专题，不在本轮提前读取 STMMAC/PHY 驱动代码或扩展专题。不得把 hook 的存在直接当作已启用，更不能认定其导致普通 DHCP TX 故障。

### 30.6 本项状态与后续顺序

**本项结项：** §4 的 6.1.65 候选源码函数回溯已完成；四版本矩阵已能区分黄金 A、黄金 B 与两条故障线的源码差异。结论仍保留候选源码身份限制。

**下一项严格按 §25.5 第 3 项原顺序：** 继续 §5 已引用的 NAPI skb allocator、GRO/shared-frag 与相关网络核心函数的 6.1.65 候选端点回溯；复用已有报告，不重做 6.1.116/6.12.81 已完成分析。之后依 §6、§7……原章节顺序推进，不能跳去驱动方向。

方向二仍进行中。本轮仅做四端点源码/Kconfig/既有配置证据只读审计；没有访问设备、构建、修改系统或执行网络试验。


## 31. §5 NAPI skb allocator 与 GRO/shared-frag：补入 6.1.65 候选源码端点（2026-11-25）

### 31.1 复用的既有报告与本次补查边界

复用：
- `PANTHER-X2-NAPI-SKB-ALLOCATOR-DIFF-AND-READONLY-TRACE-CHECK-20261119.md`：已有 6.1.116 / 6.12.81 allocator 比较；
- `PANTHER-X2-KERNEL-6.1.116-TO-6.1.174-REGRESSION-WINDOW-STMMAC-DIFF-20261119.md`：已有 6.1.116→6.1.174 shared-frag/GRO/SKB segment 变更提交背景。

本次仅补入 6.1.65 候选端点，并将相关函数放入四版本矩阵；不重做既有 NAPI allocator 结论，也不进入 STMMAC 驱动 RX 分支。

### 31.2 NAPI skb allocator

比较 `include/linux/skbuff.h` 与 `net/core/skbuff.c`：
- 6.1.65、6.1.116、6.1.174 的 `napi_alloc_skb()` inline wrapper 与 `__napi_alloc_skb()` 实现一致；都通过 per-CPU `napi_alloc_cache`，常规使用 `page_frag_alloc_1k()` / `page_frag_alloc()`，边界情形回退 `__alloc_skb()`，分配失败返回 NULL。
- 6.12.81 将 `napi_alloc_skb()` 改为 out-of-line 函数，并对 per-CPU NAPI allocator cache 增加 `local_lock_nested_bh()` 保护，分配标志增加 `__GFP_NOWARN`；仍使用 NAPI page-frag cache，分配失败仍返回 NULL。
- 因而 6.1.65 黄金 A 与黄金 B 在 allocator API/实现上没有发现差异；6.1.174 也没有新增 allocator 变化。6.12 的主要差异是 per-CPU cache 并发保护和 API 形态，不是已证实的不同分配策略或必然失败条件。

### 31.3 GRO 与 skb shared-frag 标记

四端点函数比较：
- `napi_gro_receive()`：四端点函数体一致。
- `dev_gro_receive()`：6.1.65、6.1.116、6.1.174 的核心实现一致；6.12 对 GRO offload list 的存储迁移至 `net_hotdata`，并增加 frag0 pull 优化入口，延续此前 6.12 结构变化记录。
- `skb_gro_receive()`：6.1.65 与 6.1.116 在 skb ownership 转移部分有差异；6.1.174 增加将 `SKBFL_SHARED_FRAG` 从聚合输入 skb 传播到 GRO 输出 skb 的标记继承，6.12 延续并重构 GRO size/flush 等条件。
- `skb_segment()`：6.1.65 与 6.1.116 已有 GSO partial 长度上限计算差异；6.1.174 进一步修复 shared-frag 标记在 segment 生成过程中的传播，6.12 继续演进相关实现。

这些差异属于接收侧 GRO 聚合与 GSO 分段缓冲区共享 fragment 元数据维护。普通 DHCP Discover 是本机发出的普通小型 UDP datagram，不经入站 GRO 聚合；普通非 GSO datagram 也不走 `skb_segment()` 的 GSO 分段路径。因此本节没有发现黄金 A/B 间的 NAPI allocator 差异，也没有发现 6.1.174 shared-frag/GRO 变化可直接解释普通 DHCP 单 skb TX 失败。

### 31.4 四版本状态矩阵

| 函数/子项 | 6.1.65 黄金 A | 6.1.116 黄金 B | 6.1.174 故障 A | 6.12.81 故障 B |
|---|---|---|---|---|
| `napi_alloc_skb()` / `__napi_alloc_skb()` | 旧 inline + per-CPU cache | 与 A 一致 | 与 A/B 一致 | out-of-line + local_lock + NOWARN |
| `napi_gro_receive()` | 与其余三版一致 | 一致 | 一致 | 一致 |
| `dev_gro_receive()` | 6.1 旧 offload list | 与 A 一致 | 与 A 一致 | net_hotdata / frag0 pull 变化 |
| `skb_gro_receive()` | ownership 旧实现 | ownership 有整理 | 增加 shared-frag 标记传播 | 后续 GRO 结构演进 |
| `skb_segment()` | GSO partial 旧实现 | 增加长度上限处理 | shared-frag 传播修正 | 延续并演进 |

**结论：** 本项补齐了 §5 的 6.1.65 候选源码比较。NAPI allocator 在两条 6.1 黄金/故障线之间没有发现变化；GRO/shared-frag 变化有明确接收聚合或 GSO 分段适用条件，当前不命中普通 DHCP 小 UDP TX。仍按 §25.5 顺序继续后续章节，不提前进入方向三。


## 32. §8 checksum / fragment / UDP GSO：补入 6.1.65 候选源码端点（2026-11-25）

### 32.1 四端点函数补查

本次只读比较：
- `net/ipv4/udp.c`：`udp4_hwcsum()`、`udp_send_skb()`；
- `net/core/dev.c`：`skb_checksum_help()`、`skb_csum_hwoffload_help()`；
- `include/linux/skbuff.h` / `net/core/skbuff.c`：fragment readable/netmem helper 与 `skb_segment()`；
- `net/Kconfig`：`NET_DEVMEM` 入口。

### 32.2 UDP checksum 与普通 UDP datagram

- `udp4_hwcsum()` 四端点函数体一致；6.1.65 与 6.1.116 黄金基准没有 UDP IPv4 checksum 生成差异。
- `udp_send_skb()`：6.1.65 与 6.1.116 函数体一致；6.1.174 的变化集中在 `cork->gso_size` 非零的 UDP GSO 长度/MTU 错误处理分支；6.12 继续调整 UDP GSO 条件分支。普通非 GSO UDP datagram 的 checksum 与最终 IP 提交路径未发现本项新增差异。
- `skb_checksum_help()`：6.1.65、6.1.116、6.1.174 一致；6.12 增加 unreadable-fragment 保护，只有 skb 标记为 unreadable 且进入软件 checksum fallback 时相关。
- `skb_csum_hwoffload_help()`：6.1.65 与 6.1.116 有差异；已定位为 IPv6 extension/jumbo-header checksum offload 判定调整，不适用于 IPv4 DHCP。6.1.174 延续相应变化。
- `skb_frags_readable()` / `__skb_fill_netmem_desc()` 与 `NET_DEVMEM` 均为 6.12 新增机制；前三个 6.1 端点不存在这些接口/配置入口。6.12 `NET_DEVMEM` 依赖 `DMA_SHARED_BUFFER`、`GENERIC_ALLOCATOR`、`PAGE_POOL`，定义为 `def_bool y`。6.1.65 实际 config 未出现这些新符号，符合该源码时代不存在 NET_DEVMEM 的事实。

### 32.3 GSO / fragment 处理边界

`skb_segment()` 在 6.1.65 与 6.1.116 已有 GSO partial 长度上限处理差异；6.1.174 进一步修正 `SKBFL_SHARED_FRAG` 标记传播，6.12 延续演进。该函数处理 GSO skb 分段；普通小型 DHCP UDP datagram 不属于 GSO skb，不能把这些差异外推为普通 UDP checksum 或发送回归。

### 32.4 本项结论

1. 两条黄金基准的普通 UDP IPv4 checksum helper `udp4_hwcsum()` 和 `udp_send_skb()` 主体一致。
2. 6.1.65→6.1.116 的 checksum offload helper 差异限于 IPv6 extension/jumbo header 分支，不命中 IPv4 DHCP。
3. 6.1.174 的 UDP GSO 改动和 shared-frag/GSO segment 差异有明确特殊条件，不构成普通非 GSO UDP 的已证实回归。
4. 6.12 新增 unreadable net_iov fragment 的 generic TX 拒绝门已在 §22 记录；它与普通 UDP 用户数据构造不同，当前没有历史 DHCP skb 使用 net_iov fragment 的证据。

**本项结项：** §8 中 6.1.65 候选源码端点的 checksum、UDP GSO 与 fragment helper 对照已补齐。方向二仍进行中；下一项严格按原报告顺序转到 §9 netdevice feature negotiation、ARP/neighbour output 与 IPv4 route key 的 6.1.65 回溯，不跳过章节。


## 33. §9 netdevice feature、ARP/neighbour output 与 IPv4 route key：补入 6.1.65 候选源码端点（2026-11-25）

### 33.1 本次补查函数

四端点只读比较：
- `net/core/dev.c`：`netif_skb_features()`、`netdev_fix_features()`、`netdev_update_features()`、`validate_xmit_vlan()`、`netdev_features_change()`；
- `net/core/neighbour.c`：`neigh_resolve_output()`、`neigh_connected_output()`；
- `net/ipv4/arp.c`：`arp_solicit()`；
- `net/ipv4/route.c`：`ip_route_output_key_hash()`。

### 33.2 四版本比较结果

- `netif_skb_features()`、`netdev_update_features()`、`validate_xmit_vlan()`、`netdev_features_change()`：四端点函数体一致。
- `netdev_fix_features()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 新增 `NETIF_F_GSO_UDP_L4` 能力约束，并整理 TLS TX checksum 依赖判断。该变化约束 UDP segmentation offload feature 组合，不是普通 UDP datagram checksum 的通用开关。
- `neigh_resolve_output()`、`neigh_connected_output()`、`arp_solicit()`：四端点函数体一致；黄金 A 与黄金 B 没有 ARP/neighbour 输出差异。
- `ip_route_output_key_hash()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 将 TOS 归一化改为 DSCP mask，并配合 DSCP/ECN 分离语义。该差异需要实际 DSCP selector/rule 才会影响路由匹配；普通 DHCP Discover 通常 TOS 为 0，当前无历史 DSCP policy 命中证据。

### 33.3 本项结论

1. 6.1.65 与 6.1.116 在本节列出的 generic netdevice feature negotiation、ARP/neighbour output 与 IPv4 route-key 函数上没有发现实现差异。
2. 6.12 的 UDP GSO feature 约束与 DSCP route-key 变化已有明确适用条件，未形成普通小型 UDP/DHCP 的已证实回归。
3. Panther 实际设备 feature bitmap、运行时 DSCP rule 与 hook 状态不由 generic helper 静态比较推断；驱动私有能力留在后续驱动方向。

**本项结项：** §9 的 6.1.65 候选源码回溯已完成。下一项按原顺序进入 §11 RX dispatch、IPv4 input 与 UDP receive；§10 是覆盖范围摘要，不是新增源码专题。方向二仍进行中。


## 34. §11 RX dispatch、IPv4 input 与 UDP receive：补入 6.1.65 候选源码端点（2026-11-25）

### 34.1 四端点函数比较

本次只读比较：
- `net/core/dev.c`：`__netif_receive_skb_core()`、`__netif_receive_skb_one_core()`、`netif_receive_skb_internal()`；
- `net/ipv4/ip_input.c`：`ip_rcv()`、`ip_rcv_finish()`、`ip_local_deliver()`、`ip_local_deliver_finish()`；
- `net/ipv4/udp.c`：`udp_rcv()`、`__udp4_lib_rcv()`。

### 34.2 比较结果

- 6.1.65、6.1.116、6.1.174 的 `__netif_receive_skb_core()`、`__netif_receive_skb_one_core()`、`netif_receive_skb_internal()` 函数体一致；6.12 的 core/internal wrapper 有 RX dispatch 结构调整，one_core 函数保持一致。
- `ip_rcv()`、`ip_rcv_finish()`、`ip_local_deliver()`、`ip_local_deliver_finish()` 四端点函数体一致。
- `udp_rcv()` 四端点函数体一致。
- `__udp4_lib_rcv()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 有后续 UDP receive 路径调整，延续原 §11 对 6.12 的既有分析。

### 34.3 本项结论

6.1.65 黄金 A 与 6.1.116 黄金 B 在网络核心 RX dispatch、IPv4 input 与 UDP receive 的上述主入口没有发现实现差异；6.1.174 也保持相同。6.12 的 RX dispatch/UDP receive 变化属于接收方向，不构成当前出站 DHCP Discover TX 失败的直接解释。

**本项结项：** §11 的 6.1.65 候选源码端点回溯已完成。下一项按原顺序进入 §12 网络核心 Kconfig 模板/符号对照；6.1.65 实际配置映射已在 §27 提供，但仍需核对本节及后续配置项对应的源码 Kconfig 定义和符号语义，不能把模板值当作最终配置。


## 35. §12 网络核心 Kconfig：6.1.65 实际配置列补齐（2026-11-25）

本节直接承接 §27 的原始 `config-6.1.65-ophub` 映射，不使用 general config 模板替代真实配置。对应符号的 6.1.65 实际值如下：

| 符号 | 6.1.65 原始实际配置 | 与 §12 两个模板对照 |
|---|---:|---|
| `CONFIG_NET` / `CONFIG_INET` / `CONFIG_NETDEVICES` | y / y / y | 与 6.1.116、6.12 候选模板一致 |
| `CONFIG_NET_NS` | y | 一致 |
| `CONFIG_BPF` / `CONFIG_BPF_SYSCALL` | y / y | 一致 |
| `CONFIG_XDP_SOCKETS` | y | 一致 |
| `CONFIG_NET_RX_BUSY_POLL` | y | 一致 |
| `CONFIG_PAGE_POOL` | y | 一致 |
| `CONFIG_NET_DEVMEM` | 6.1.65 源码时代不存在该符号 | 不是实际配置 n；6.12 新增能力 |
| `CONFIG_IP_PNP` | not set | 与 6.1.116 模板一致；6.12 候选模板为 y |
| `CONFIG_IPV6` | y | 与 6.1.116 模板一致；6.12 候选模板为 m |
| `CONFIG_VLAN_8021Q` | y | 与 6.1.116 模板一致；6.12 候选模板为 m |
| `CONFIG_INET_DIAG` | y | 与 6.1.116 模板一致；6.12 候选模板为 m |
| `CONFIG_NETFILTER` | y | 与两个模板一致 |
| `CONFIG_BRIDGE` | m | 与两个模板一致 |
| `CONFIG_NET_CLS_BPF` / `CONFIG_NET_ACT_BPF` | m / m | 与两个模板一致 |

补充说明：
- `CONFIG_IP_PNP_DHCP`、`CONFIG_IP_PNP_BOOTP`、`CONFIG_IP_PNP_RARP` 等子项在 6.1.65 原始配置文本中未出现；由于父项 `CONFIG_IP_PNP` 明确 not set，不能把这些未出现子项单独解释为配置缺失。
- 6.1.65 `NET_DEVMEM` 归类为“该版本源码没有此 Kconfig 符号”，不是“存在但未启用”。
- 上述是原始 config 证据与源码时代的组合判断；6.12 的 config-6.12 仍为候选模板，不能替代 6.12.81 最终运行配置。
- 配置 y/m 只表示 built-in/module 编译形态；不证明模块实际加载、程序附着、内核 IP autoconfiguration 启动或 bridge/VLAN/netfilter 规则实际运行。

**本项结项：** §12 表中 6.1.65 黄金 A 配置证据缺口已按原始配置归档补齐。下一项按原报告顺序进入 §14 AF_PACKET、VLAN/bridge RX 与 Netfilter ingress 的 6.1.65 回溯；不得跳到 §16 或其他专题。


## 36. §14 AF_PACKET / VLAN / bridge RX / Netfilter ingress：补入 6.1.65 候选源码与实际配置（2026-11-25）

### 36.1 6.1.65 实际 Kconfig 值

依据原始配置归档（§27）：
- `CONFIG_PACKET=y`、`CONFIG_PACKET_DIAG=y)；
- `CONFIG_VLAN_8021Q=y)；
- `CONFIG_BRIDGE=m)、`CONFIG_BRIDGE_VLAN_FILTERING=y)、`CONFIG_BRIDGE_NETFILTER=m)；
- `CONFIG_NETFILTER=y)、`CONFIG_NETFILTER_INGRESS=y)、`CONFIG_NETFILTER_EGRESS=y)；
- `CONFIG_NF_CONNTRACK=y)、`CONFIG_NF_TABLES=m)。

这些值与 6.1.116 general config 模板对应项相同。它们只描述编译形态，不证明 packet socket 监听、VLAN 子接口、bridge port、ingress hook 或过滤规则实际启用。

### 36.2 6.1.65 源码函数补齐

四端点比较补齐了 §14 之前缺少的 6.1.65 候选端点：
- AF_PACKET：`packet_rcv()` 在 6.1.65、6.1.116、6.1.174 一致；6.12 的 snaplen 对 unreadable fragment 限制仍按 §14.1 既有结论。 `packet_rcv_spkt()`、`tpacket_rcv()` 四端点一致；`packet_sendmsg()` 四端点一致。
- `packet_create()`：6.1.65 与 6.1.116 一致；6.1.174 开始存在后续变化，6.12 延续。该函数负责 packet socket 创建与权限/类型处理，不是普通 IP/UDP 数据面转发函数。
- VLAN：`vlan_do_receive()` 四端点函数体一致。
- Bridge：`br_handle_frame()`、`br_handle_frame_finish()`、`br_pass_frame_up()` 在 6.1.65 与 6.1.116 间存在变化。6.1.116 新增 bridge offload input 处理与 promisc 状态传递；6.1.174 将 MST helper 调整为 port-aware 并增加 VLAN group RCU 检查。上述变化仅在设备注册 bridge RX handler、报文确实进入 Linux bridge port 时适用。6.1.65→6.1.116 的变化不是通用 netdevice RX dispatch。
- Netfilter：`nf_ingress()`、`nf_register_net_hook()` 四端点一致；`nf_hook_slow()` 在 6.1.65、6.1.116、6.1.174 一致，6.12 对 `NF_STOLEN` 非标准 verdict/error 返回处理变化延续 §14.4。

### 36.3 修订后的四版本判断

1. 6.1.65 与 6.1.116 在 AF_PACKET receive、VLAN RX、Netfilter ingress 注册/执行主入口没有发现实现差异。
2. 两个 6.1 黄金基准在 bridge RX 有一组明确的 bridge offload/promisc bookkeeping 差异，但 6.1.65 原始配置中 `CONFIG_BRIDGE=m`；没有现有证据证明模块实际加载或 Panther 网卡处于 bridge port。不能把它作为普通物理接口 DHCP TX/RX 的故障解释。
3. 6.1.174 的 MST port-aware 修正属于 bridge 专用路径；6.12 的 AF_PACKET unreadable-fragment snaplen 和 Netfilter verdict 处理分别作用于抓包可见性及特定 hook verdict，不等于普通 IPv4/UDP 默认丢包。
4. 当前仍无证据显示 Panther 故障路径使用 Linux bridge、VLAN 子设备、AF_PACKET 过滤 socket 或已注册 Netfilter ingress drop hook。

**本项结项：** §14 的 6.1.65 候选源码与原始配置映射完成。下一项按原报告顺序进入 §16 IPv4 PREROUTING/LOCAL_IN、conntrack 与 NAT hook；不提前转向驱动专题。


## 37. §16 IPv4 conntrack / NAT hook：补入 6.1.65 候选源码与原始配置（2026-11-25）

### 37.1 6.1.65 实际配置映射

原始 `config-6.1.65-ophub` 的实际值：
- `CONFIG_NF_CONNTRACK=y`；
- `CONFIG_NF_DEFRAG_IPV4=y)；
- `CONFIG_NF_NAT=m`；
- `CONFIG_NETFILTER_XTABLES=m`、`CONFIG_NETFILTER_XT_NAT=m`；
- `CONFIG_IP_NF_IPTABLES=m`、`CONFIG_IP_NF_FILTER=m)、`CONFIG_IP_NF_NAT=m)；
- `CONFIG_NF_TABLES=m)。

6.1.65 没有 `IP_NF_IPTABLES_LEGACY` 独立符号；这是后续 6.12 Kconfig 拆分后出现的符号。以上实际配置形态与 6.1.116 模板对应项一致。

### 37.2 源码函数四端点补齐

本次补入 6.1.65 候选源码后，比较结果：
- `nf_ct_netns_do_get()` / `nf_ct_netns_put()`：四端点一致；IPv4 conntrack hook 注册/注销机制与引用计数无 6.1 黄金基准差异。
- `nf_conntrack_in()`、`resolve_normal_ct()`：6.1.65、6.1.116、6.1.174 函数体一致；6.12 存在既有报告记录的 debug/state read 整理。
- `init_conntrack()`：6.1.65 与 6.1.116 一致；6.1.174 起有函数体变化，需沿用 §16.3 已记录的分配错误传播/连接跟踪初始化差异判断，不将其误记为 6.12 才出现的行为。
- `nf_nat_inet_fn()`：四端点一致。
- `nf_nat_register_fn()`：6.1.65、6.1.116、6.1.174 一致；6.12 对数组分配 API 做整理。
- `iptable_nat_table_init()`：四端点一致。
- `iptable_filter_table_init()`：6.1.65、6.1.116、6.1.174 一致；6.12 存在既有报告记录的注册/初始化 API 调整。

### 37.3 修订后的判断

6.1.65 与 6.1.116 在 conntrack hook 注册/注销、普通 conntrack packet entry、tuple lookup、NAT hook 主函数及 iptables NAT/filter table init 的核心函数上保持一致。6.1.174 的 `init_conntrack()` 变化需按 §16.3 的实际错误传播语义分析，但没有证据证明它在普通无压力 DHCP 流量上会触发。6.12 的变化已在 §16 原文限定为 confirm wrapper、debug/state read、分配 API 与 Kconfig/module 结构整理；目前没有发现普通 IPv4/UDP 默认新增 drop 条件。

**本项结项：** §16 的 6.1.65 候选源码与真实配置映射完成。下一项严格按原顺序进入 §18 IPv4 header checksum、fragment reassembly 与本机交付路径。


## 38. §18 IPv4 checksum / fragment reassembly / local delivery：补入 6.1.65 候选源码与配置（2026-11-25）

### 38.1 6.1.65 实际配置

原始配置确认：
- `CONFIG_INET=y`；
- `CONFIG_NF_DEFRAG_IPV4=y`；
- `CONFIG_NETFILTER=y`；
- `CONFIG_IP_MULTIPLE_TABLES=y)。

其中 `NF_DEFRAG_IPV4=y` 表示 Netfilter conntrack defrag hook 支持编入内核，不表示每个 IPv4 skb 都执行 defrag；`ip_defrag()` 的核心实现属于 INET IPv4 栈。

### 38.2 6.1.65 源码函数比较

补入候选端点后：
- `ip_rcv_core()`：6.1.65、6.1.116、6.1.174 一致；6.12 才将总长度读取切换为 `iph_totlen()`。
- `ip_local_deliver()`、`ip_local_deliver_finish()`、`ip_protocol_deliver_rcu()`：四端点一致。
- `ip_frag_reasm()`：四端点一致。
- `ip4_frag_init()`：6.1.65 与 6.1.116 一致；6.1.174 起采用 RCU/refcount 安全获取 peer 的实现，6.12 延续。
- `ip_frag_queue()`、`ip_defrag()`、`inet_frag_queue_insert()`、`inet_frag_reasm_finish()`：6.1.65 与 6.1.116 存在差异；这些差异均位于分片队列插入、排队、重组完成/时间戳等分片专用路径。6.1.174/6.12 在这些基础上继续沿用或扩展既有变化。
- `inet_frag_find()`：四端点一致。
- `ipv4_conntrack_defrag()`：6.1.65、6.1.116、6.1.174 一致；6.12 对 hook 生命周期/状态读取作后续调整。

### 38.3 适用性结论

与此前 §18.2、§18.3 的路径条件结合：
- 普通未分片 DHCP/UDP 不进入 `ip_defrag()`、`ip_frag_queue()` 或 fragment queue insert/reassembly 路径；
- conntrack defrag hook 即使已注册，也先检查 IPv4 fragment 条件；未分片报文不会被送入分片收集分支；
- 因此 6.1.65→6.1.116 在 fragment queue 内部的实现差异是真实版本差异，但不命中普通未分片 DHCP Discover；
- IPv4 header checksum、长度基本检查、本机 LOCAL_IN 与 UDP protocol dispatch 主入口四版本没有发现会解释普通 DHCP 收发异常的新增逻辑。

**本项结项：** §18 的 6.1.65 候选源码与原始配置映射完成。方向二继续按原顺序进入 §19 IPv4 route lookup、FIB trie 与 policy routing。


## 39. §19 IPv4 FIB / policy routing：补入 6.1.65 候选源码与实际配置（2026-11-25）

### 39.1 原始配置映射

6.1.65 原始配置确认：
- `CONFIG_IP_ADVANCED_ROUTER=y)；
- `CONFIG_IP_MULTIPLE_TABLES=y)；
- `CONFIG_FIB_RULES=y)（由对应 Kconfig 选择/配置）；
- `CONFIG_INET=y)。

这与 6.1.116 已审计模板的关键路由配置一致；只表示策略路由功能可编译，不表示运行时存在自定义 rule、DSCP selector 或多路由表规则。

### 39.2 6.1.65 与 6.1.116 函数比较

本次对原报告列出的函数逐项补查：
- `ip_route_input_rcu()`、`ip_route_output_key_hash_rcu()`、`ip_route_output_key_hash()`：6.1.65 与 6.1.116 函数体一致。
- `ip_route_input_slow()`：6.1.116 新增 `in_dev` 空指针检查并在为空时返回 `-EINVAL`；6.1.65 没有该保护分支。这是异常/缺失 in_device 状态下的防御性错误返回，不改变正常有效入站接口的 route lookup。
- `fib_validate_source()`：两版一致。
- `fib_table_lookup()`：6.1.116 新增将 alias 的 `fa_dscp` 写入 `fib_result.dscp`；本次比较未发现它改变 trie 前缀查找、alias 匹配或 nexthop 选择条件。后续 6.12 的 DSCP mask 匹配调整仍按 §19.2 解释。
- `fib4_rule_match()`、`fib4_rule_configure()`、`fib4_rule_fill()` 与通用 `fib_rules_lookup()`：6.1.65 与 6.1.116 函数体一致。

### 39.3 四版本结论更新

6.1.65→6.1.116 在本节发现的差异为：
1. 入站 route slow path 增加 in_device NULL 防御检查；
2. FIB lookup 结果结构增加 DSCP metadata 赋值。

未发现正常接口条件下的路由决策、FIB trie 搜索、policy rule 匹配/遍历或源地址校验变化。6.1.174 延续 6.1.116 的上述实现；6.12 的 DSCP selector 语义扩展、BC_FORWARDING READ_ONCE 与 forwarding 统计变化仍按 §19 原文限定。当前没有证据表明 Panther 历史 DHCP 报文命中 DSCP rule 或缺失 in_device 异常状态。

**本项结项：** §19 的 6.1.65 候选源码与原始配置映射完成。下一项按原顺序进入 §20 ARP RX 处理与 neighbour 状态机。


## 40. §20 ARP RX / neighbour NUD 状态机：补入 6.1.65 候选源码与配置（2026-11-25）

### 40.1 6.1.65 原始配置映射

原始 config 已确认 `CONFIG_INET=y`、`CONFIG_NET=y`；`CONFIG_IP_PNP` 明确 not set。IPv4 ARP 核心随 INET IPv4 栈接入，不存在单独 `CONFIG_ARP` 开关。启动阶段 RARP/IP autoconfiguration 选项不等于普通 ARP 协议实现开关。

### 40.2 6.1.65 与 6.1.116 函数比较

本次补查：
- `arp_rcv()`、`arp_process()`、`arp_ignore()`、`arp_filter()`、`arp_solicit()`；
- `__neigh_event_send()`、`__neigh_update()`、`neigh_probe()`、`neigh_timer_handler()`、`neigh_periodic_work())；
- `include/net/route.h:ip_route_output()`。

以上函数在 6.1.65 与 6.1.116 函数体完全一致。结合第 9 节已补齐的 `neigh_resolve_output()` / `neigh_connected_output()` 一致性，6.1 黄金 A/B 在本报告列出的 ARP RX、邻居状态推进、探测重试、ARP filter 与邻居最终输出主路径没有实现差异。

### 40.3 四版本结论

6.1.65 与 6.1.116 一致；6.1.174 也保持本节关键 ARP/NUD 函数一致；6.12 的主要差异仍是 ARP filter 调用 route helper 时显式传入原默认 `RT_SCOPE_UNIVERSE`，不是默认 scope 改变。没有发现 6.1.174 或 6.12 新增普通 ARP request/reply 的默认丢弃条件。

ARP/neighbour 仍主要影响 DHCP 完成后的下一跳解析和单播流量，不是 DHCP Discover 广播报文的协议入口。实际 neighbour cache 状态属于运行时证据，本轮不推断。

**本项结项：** §20 的 6.1.65 候选源码与原始配置映射完成。下一项按原顺序进入 §21 UDP IPv4 sendmsg 与 IP skb 构造/追加路径。


## 41. §21 UDP IPv4 sendmsg / IP skb 构造：补入 6.1.65 候选源码（2026-11-25）

### 41.1 6.1.65 与 6.1.116 函数比较

本次按 §21 原范围比较：
- `net/ipv4/udp.c`：`udp_sendmsg()`、`udp_send_skb()`、`udp4_hwcsum())；
- `net/ipv4/ip_output.c`：`ip_make_skb()`、`ip_append_data()`、`ip_push_pending_frames()`、`ip_setup_cork()`；
- `net/ipv4/route.c`：`ip_route_output_flow()`；
- 并复核 §30 已补的 `__ip_append_data()`。

比较结果：
- `udp_send_skb()`、`udp4_hwcsum()`、`ip_make_skb()`、`ip_append_data()`、`ip_push_pending_frames()`、`ip_route_output_flow()` 函数体一致。
- `ip_setup_cork()` 的函数体语义与行内容一致；本次提取结果仅存在非语义文本/格式差异，未发现可改变普通 UDP datagram 构造的条件差异。
- `udp_sendmsg()` 存在 6.1.65→6.1.116 的并发访问与 cork/pending 状态读取/写入调整：6.1.65 直接读取 `up->corkflag` / `up->pending` 并直接写 pending；6.1.116 改用 `udp_test_bit(CORK, sk)`、`READ_ONCE(up->pending)` 与 `WRITE_ONCE(up->pending, ...)`，并在错误回退分支显式清理 connected 状态。这属于 UDP socket cork/pending 状态访问和并发可见性整理。

### 41.2 对普通 DHCP/UDP sendmsg 的适用性

- 普通单次 UDP sendmsg、无 `MSG_MORE`、socket 未设置 UDP_CORK 时，`corkreq` 在两版都由 false 的 cork 状态与 MSG_MORE 共同决定；本轮未发现普通 datagram 进入不同的 payload 构造或 IP 提交路径。
- `udp_sendmsg()` 的 READ_ONCE/WRITE_ONCE 变化可能影响并发 cork/pending 状态访问，但没有证据表明 Panther 历史 DHCP 客户端设置 UDP_CORK、并发共享同一 UDP socket 或通过 MSG_MORE 构造 DHCP Discover。
- `udp_send_skb()`、IPv4 UDP checksum、IP make/append/push 与 route output helper 均一致；结合 §30 的 `__ip_append_data()` 比较，6.1.65→6.1.116 未发现普通 IPv4 UDP skb 构造/校验主路径的功能性差异。

### 41.3 四版本结论更新

6.1.65 与 6.1.116 的 UDP socket sendmsg 状态访问存在明确小差异，但普通非 cork DHCP datagram 的 skb 构造、checksum 和 IP output helper 保持一致。6.1.174 的 UDP GSO 专用差异及 6.12 的 MSG_SPLICE_PAGES/后续 UDP 变化仍按 §32 既有适用条件记录；不能混同于普通 DHCP 单 skb 路径。

**本项结项：** §21 的 6.1.65 候选源码函数级回溯完成。下一项严格进入 §22 TX queue → qdisc → validate → ndo_start_xmit 交付链，重点将既有 §30 的函数比较结果纳入该节四版本矩阵。


## 42. §22 TX queue → qdisc → validate → ndo_start_xmit：补入 6.1.65 候选源码与真实配置（2026-11-25）

### 42.1 6.1.65 实际配置

原始 `config-6.1.65-ophub`：
- `CONFIG_NET=y)、`CONFIG_NETDEVICES=y)、`CONFIG_NET_CORE=y)；
- `CONFIG_NET_SCHED=y)、`CONFIG_NET_SCH_INGRESS=y)、`CONFIG_BQL=y)；
- `CONFIG_NETFILTER_INGRESS=y)、`CONFIG_NETFILTER_EGRESS=y)；
- `CONFIG_ETHERNET_PACKET_MANGLE`：6.1.65 候选源码中不存在该 Kconfig 符号；
- `CONFIG_NET_DEVMEM`：6.1.65 源码时代不存在该符号；
- `CONFIG_NET_DROP_MONITOR`：本次原始配置文本未找到对应行，不能据此直接写成 n。

### 42.2 6.1.65 与 6.1.116 TX 函数比较

补入黄金 A 后：
- `netdev_core_pick_tx()`、`netdev_pick_tx()`、`validate_xmit_skb_list()`、`dev_hard_start_xmit()`：6.1.65 与 6.1.116 函数体一致。
- `dequeue_skb()`、`qdisc_restart()`、`sch_direct_xmit())、`__qdisc_run()`：6.1.65 与 6.1.116 函数体一致；6.1.174 起的 packet budget 差异仍如 §22.2。
- `__dev_queue_xmit()`、`validate_xmit_skb()`、`sch_direct_xmit()`：6.1.65 与 6.1.116 一致（§30 已逐项记录）。
- `xmit_one()`：6.1.65 没有 `ETHERNET_PACKET_MANGLE` 条件 hook；6.1.116/6.1.174 有可选 `dev->eth_mangle_tx` callback，6.12 删除该 hook。6.1.65 原始源码不存在对应 Kconfig 定义，因此不是“6.1.65 配置没打开”而是该源码端点没有此扩展。
- `netdev_start_xmit` 是宏/inline 调用边界而非本次函数提取器可独立识别的函数；四版本仍以 `xmit_one()` → `netdev_start_xmit()` → `ndo_start_xmit` 作为驱动交付边界。

### 42.3 对普通 DHCP TX 的判断

6.1.65 与 6.1.116 在 TX queue 选择、qdisc 出队/调度、发送前校验、单 skb direct-xmit、驱动调用/返回处理上没有发现通用路径差异。唯一与通用发送交付点直接相邻的黄金 A/B 差异是 6.1.116 增加可选 `ETHERNET_PACKET_MANGLE` hook；是否启用及是否注册 callback 必须看驱动端配置/代码，不能由 Kconfig 符号存在推断。该驱动侧确认留待方向三，不在方向二提前审计。

6.1.174 的 noqueue GSO list 返回码变化只命中 GSO skb list；6.12 的 unreadable net_iov fragment 提前 drop 需要特定 skb backing memory；二者均未证明命中普通小型 DHCP UDP 单 skb。当前没有找到解释 6.1.174/6.12.81 普通 UDP 发送失败的通用 Linux 网络核心 TX 回归点。

**本项结项：** §22 的 6.1.65 候选源码与原始配置映射完成。下一项按原顺序进入 §23 netdev_start_xmit、TX queue flow control、watchdog 与 skb completion/free。


## 43. §23 TX queue stop/watchdog：补入 6.1.65 黄金 A 后发现的真实内存序差异（2026-11-25）

### 43.1 6.1.65 与 6.1.116 的函数比较

补查 `include/linux/netdevice.h`、`net/core/dev.c`、`net/sched/sch_generic.c`、`net/core/skbuff.c` 与 `include/linux/skbuff.h` 后：
- `__netdev_start_xmit()`、`netdev_tx_completed_queue()`、`__netdev_tx_sent_queue()`、`netif_tx_queue_stopped()`、`netif_xmit_stopped()`、`txq_trans_update()`、`netif_tx_wake_queue()`：6.1.65 与 6.1.116 一致。
- `netdev_tx_sent_queue()`、`netif_tx_stop_queue())、`dev_watchdog()`：6.1.65 与 6.1.116 存在实际函数体差异。
- `consume_skb()`、`napi_consume_skb()`、`skb_release_all()`、`skb_release_data()`：6.1.65 与 6.1.116 一致；6.12 的 reason/dataref 变化仍按 §23.5 记录。

### 43.2 新增的队列状态与 watchdog 内存序配对

6.1.116 相对 6.1.65 增加：
- `netdev_tx_sent_queue()`：使用 `WRITE_ONCE(dev_queue->trans_start, jiffies)`，并在设置 STACK_XOFF 前增加 `smp_mb__before_atomic()`；注释明确其与 `dev_watchdog()` 的 READ_ONCE/屏障配对。
- `netif_tx_stop_queue()`：同样使用 `WRITE_ONCE(trans_start)`，并在置位 DRIVER_XOFF 前增加 `smp_mb__before_atomic()`，以保证 watchdog 可观察到队列停止与时间戳更新的顺序。
- `dev_watchdog()`：从 6.1.65 的简单 `netif_xmit_stopped()` + 普通 `trans_start` 读取，改为在检查停止状态后执行 `smp_mb()`，再以 `READ_ONCE(trans_start)` 读取时间戳；并计算最老队列起始时间和 timeout 毫秒数，改善多队列 timeout 诊断及竞争处理。

这是一组相互配对的队列停止/发送记账/watchdog 内存序修正，不能拆开只看某一个 helper。6.1.174/6.12 延续 6.1.116 这组修正。

### 43.3 对发送故障的含义

该差异确实涉及 TX queue flow-control 状态与 watchdog 对停止状态/发送时间的观察，属于方向二网络核心中真实的 6.1.65→6.1.116 软件变化；与 §22 的 packet budget 或 GSO-list 变化不同，它触及队列停止与 watchdog 的并发可见性。

但静态源码不能证明 Panther 历史故障命中了该竞争条件：
- 需要发生 TX queue stop/STACK_XOFF 或 DRIVER_XOFF 状态变化；
- watchdog 需要在相关时间窗内检查该队列；
- 必须有对应 queue stop/wake 与时间戳状态证据，才能判断是否存在停队列未唤醒、timeout 误判或并发可见性问题。
- 当前历史故障证据未提供这些运行时队列状态/时间序列；不能把该差异直接定为 6.1.174/6.12.81 的故障根因。

与 DHCP 普通小包的关系：该变化不改变 `ndo_start_xmit` 的调用签名和驱动返回码，但可能影响队列在并发 stop/submit/watchdog 条件下的状态观察。因此应列为**方向二中保留的真实 TX 软件差异，需与已有运行时证据对照**，不能简单归类为纯日志变化。

### 43.4 本项结论与状态修订

§23 的“queue stop/wake 与 watchdog 三版函数完全一致”结论需修订为：
- 6.1.65→6.1.116：存在配对的 WRITE_ONCE/READ_ONCE 与 memory barrier 修正；
- 6.1.116→6.1.174：相关 helper/ watchdog 核心逻辑保持；
- 6.1→6.12：非 PREEMPT_RT 下 xmit_more 行为保持，PREEMPT_RT 有 task-local 适配；其余已记录的 watchdog/BQL 核心逻辑延续。

**本项结项：** §23 的 6.1.65 函数比较已补齐，并发现一组需要保留的 TX queue/watchdog 内存序差异。下一项按原顺序进入 §24 NET_TX_SOFTIRQ、qdisc reschedule、completion_queue 与 TX trace。方向二仍进行中，不提前进入方向三。


## 44. §24 NET_TX_SOFTIRQ / qdisc reschedule / completion_queue / TX trace：补入 6.1.65 候选源码（2026-11-25）

### 44.1 6.1.65 与 6.1.116 函数比较

本次补查：
- `net/core/dev.c`：`net_tx_action()`、`__netif_schedule()`、`__netif_reschedule()`、`netif_schedule_queue()`、`netif_tx_wake_queue()`、`__dev_kfree_skb_irq()`；
- `net/sched/sch_generic.c`：`__qdisc_run()`、`qdisc_restart()`、`dequeue_skb()`、`dev_watchdog()`；
- `kernel/softirq.c` 及 `include/trace/events/net.h` / `skb.h` 的相关框架与事件定义。

比较结果：
- `net_tx_action()`、qdisc schedule bit/per-CPU output_queue 入队、`__netif_reschedule()` 的 NET_TX_SOFTIRQ raise、`netif_schedule_queue()`、`netif_tx_wake_queue()`、`__dev_kfree_skb_irq()`：6.1.65 与 6.1.116 函数体一致。
- `__qdisc_run()`、`qdisc_restart()`、`dequeue_skb()`：6.1.65 与 6.1.116 函数体一致；6.1.174 起 packet budget 的变化已在 §22/§24 记录。
- `dev_watchdog()`：两黄金基准存在 §43 已确认的配对 WRITE_ONCE/READ_ONCE 与 memory barrier 差异；本节不重复计算为新的 softirq/qdisc 差异。
- tracepoint 定义中 TX start/xmit/timeout 事件的核心字段在两黄金端点保持一致；skb free/consume trace 在 6.12 的 caller/reason 字段扩展仍按 §24.6 记录。

### 44.2 四版本判断

6.1.65 与 6.1.116 在 NET_TX_SOFTIRQ 的 completion_queue/output_queue 处理顺序、qdisc schedule/reschedule、IRQ-context skb 延迟释放入队及 qdisc 重新运行路径上没有发现差异。6.1.174 与 6.12.81 的已有变化分别为 qdisc packet budget、softirq 回调 API 和 skb drop-reason/free helper 演进，均未发现改变 generic output_queue 调度职责或将 completion_queue 变成硬件 DMA completion 的证据。

**本项结项：** §24 的 6.1.65 候选源码回溯完成。至此 §3～§24 已有 6.1.65 候选源码覆盖补齐；但这不代表方向二已完成：仍须复核 §25.5 之外可能存在的原始方向二剩余任务，特别是 §26 TX 统计/drop reason/Kconfig 的 6.1.65 真实配置缺口与四版本符号映射，并检查是否存在尚未列入 §3～§24 的网络核心子项。
