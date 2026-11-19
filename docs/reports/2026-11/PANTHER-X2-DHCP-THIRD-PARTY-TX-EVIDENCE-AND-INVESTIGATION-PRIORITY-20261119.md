# Panther X2：DHCP 第三方接收测试对 TX 故障边界的补充证据（2026-11-19）

## 1. 来源与本轮范围

本报告整理用户新增的独立实机测试报告：
- 原始报告：[RK3566 DHCP 故障排查报告（脱敏版）](./RK3566_DHCP故障排查报告_脱敏版.md)
- 测试覆盖：故障版 6.12.81-rk35xx-ophub 与正常版 6.1.116-ophub；板卡侧 tcpdump、同二层有线主机 UDP/67 应用层监听、双向广播与 IPv6 NDP 现象。
- 本报告只重新判读已完成测试，不要求重跑测试、不连接设备、不发送报文、不抓包、不读取寄存器、不修改系统。

## 2. 新增的关键实验证据

### 2.1 故障版板卡发包未到达同二层第三方接收端

用户报告记录：
- 6.12.81 板卡侧可抓到结构合规的 DHCP Discover；
- 同二层有线调试主机 UDP/67 应用层监听 60 秒窗口收到 0 个板卡包；
- 同一监听路径的阳性对照有效：调试主机自身从有线口发送广播，监听器收到自发报文；
- 恢复板卡原 MAC 后再次发送 5 个 Discover，第三方监听仍为 0；
- 更早的 55 秒窗口中记录 8 个 Discover、0 Reply/Offer/ACK；
- 正常 6.1.116 版本使用同一监听器曾收到板卡发出的 2 个 DHCP Request。

这比单纯“路由器没有 Offer”更有判别力：它把故障定位到板卡发送方向，且通过同二层有线监听与阳性对照，降低了无线桥接、路由器 DHCP 策略和监听器本身故障等解释的可能性。

### 2.2 反向方向的接收能力有阳性证据

用户报告记录：
- 调试主机发送带标记广播，Panther 故障版完整收到；
- 板卡侧抓到 NS，并在 0.1ms 内产生 NA；
- 主机向板卡 IPv6 地址发起 ping 时，主机收不到 NA，NDP 无法完成。

这些结果说明故障版至少能够接收测试中的外部广播帧，并能在 Linux 网络栈观察到收到的 NS。它不支持把“RX 整条路径完全失效”作为当前主解释。

### 2.3 报文内容与常见软件变量已被覆盖

原报告还记录了：
- DHCP Discover 字段和选项逐项解析合规；
- NetworkManager 与 dhcpcd 两种客户端均失败；
- MAC 改动、克隆正常版本 MAC 均不能稳定恢复；
- broadcast flag 改动无效；
- 关闭 TX checksum offload 无效；
- RGMII delay、DTB 关键属性、Link 状态与 6.1.116 基线相符；
- tx_errors=0、tx_dropped=0，没有 TX timeout / DMA reset 日志。

这些证据降低了 DHCP 客户端、MAC 过滤、单一 checksum offload 和明显 DT 参数差异的优先级。

## 3. 对当前故障边界的更新

### 已有证据支持

1. **故障主要表现为单向 TX 发送失败。** 板卡接收外部广播的测试成功，而板卡发往同二层主机的 DHCP 报文未被第三方接收。
2. **Linux 本机抓包可见不等于物理网口发出。** tcpdump 观察到 DHCP Discover，只证明报文进入本机 outgoing capture 路径；不能证明它已越过 GMAC MAC/RGMII/PHY。
3. **外部接收端零接收有有效对照。** 同二层有线监听的阳性对照有效，正常 6.1.116 曾收到板卡报文，故障 6.12.81 多轮收到 0。
4. **当前研究应聚焦 GMAC TX 与 PHY/RGMII 发送链。** RX 普通接收路径从主线根因候选降级，不再扩展 RX-only 分支或重复 RX 测试。

### 仍不能从现有证据推出

- 不能精确断言帧停在 GMAC MAC core、RGMII TXD/TXC、RTL8211F PHY，还是 PHY 介质侧；
- 板卡侧 tcpdump、stmmac_xmit() 返回成功、DMA descriptor completion、MAC/MMC 累计计数，都不能单独证明某个指定 DHCP 帧已经出现在 RGMII 引脚或 MDI 线上；
- 主机收不到 NA 也不能单独证明 NA 已经由 PHY 发射；它与 DHCP 第三方监听结果共同支持单向 TX 故障，但不定位具体硬件边界；
- tx_errors=0 / tx_dropped=0 表示 Linux/driver 没报告相应错误，不等于 PHY 线路发送成功。

## 4. 研究优先级调整

### 降级或暂停

- 不再把 RX/NAPI/page-pool 分配作为当前主故障方向。既有 napi_alloc_skb() 探针命中 62 次、NULL 返回 0，以及本报告中的反向广播接收成功，足以将该分支降级；不需要重复常规 RX 测试。
- 不再重复 DHCP 客户端、MAC 克隆、broadcast flag、checksum offload、普通外部监听、RX 广播接收测试。
- 不恢复任何外部发帧、PHY counter、PHY register、RGMII/MDI 物理探测；此前用户已明确暂停这些测试。

### 保留为主线的静态研究

1. **Rockchip GMAC glue / clock enable：** 继续审查 6.12.81 实际构建候选中的 gmac_clk_enable()、必需时钟获取和使能错误处理。既有报告指出 6.12 vendor 候选逐项调用 clk_prepare_enable() 后未检查返回值，并使用 100–200µs settle；6.1 upstream rework 检查返回值并等待 5ms。此项仍是软件候选，但不是已证实根因。注意：此前将后期 Ophub c2f148d 误归入 6.1.174 的报告已更正；不能把不同源码快照混用。
2. **RGMII TX clock 与 PHY 侧接口：** 从真实构建源码追踪 mac_clk_tx、clk_mac_speed、GMAC1 RGMII 时钟父链、GRF 配置与 RTL8211F 接口模式之间的关系；重点寻找 6.12 相对 6.1.116 的实际变化和可建立的因果链。
3. **实际构建来源闭环：** 区分 Linux stable upstream、Rockchip vendor patch、ophub 构建补丁与最终 6.12.81 镜像。不能仅凭某个公开分支的源码片段就宣称它是运行镜像的唯一源码。
4. **PHY 初始化中可能影响 TX 的配置：** 只审查已存在的静态代码差异与历史日志，不读取实机 PHY 寄存器、不触发 PHY reset、不更改配置。

## 5. 当前阶段结论

**高置信度故障方向：Panther X2 6.12.81 的 Ethernet TX 发送链异常；RX 不再是当前优先排查方向。**

**尚未定位的边界：** GMAC MAC core → RGMII TXD/TXC → RTL8211F → 线侧发射。

**根因状态：未确定。** 目前最有价值的工作不是再证明“第三方收不到”，而是从 6.1.116 正常与 6.12.81 故障的真实软件构建差异中，找出能让 TX 时钟、MAC/RGMII 接口或 PHY TX 方向失效的具体代码路径。

在获得可靠的物理边界证据前，继续遵守用户指令：只做静态软件/仓库证据研究，不发送测试帧，不执行新的外部抓包，不读取 PHY/GMAC 危险寄存器，不修改设备。
