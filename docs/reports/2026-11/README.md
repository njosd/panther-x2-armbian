# 2026-11 报告

本月阶段性测试与调查报告目录。每份报告需链接原始证据和相关 Actions run。

## Panther X2 网络与启动链

- [P4：Rockchip pinctrl 首 pin 错误处理静态审计收尾（2026-11-20，P4 正式关闭）](./PANTHER-X2-P4-PINCTRL-FIRST-PIN-ERROR-CLOSEOUT-20261120.md)：确认 6.1.174-rk35xx 与 6.12.81-rk35xx 在首 pin mux 写入失败时可能吞掉错误并跳过同组后续 pin；Panther GMAC1 M0 group 顺序使该机制理论上可能影响 TXD/TXCLK。没有现场 regmap 错误证据，不能认定根因。全程只读，未操作设备。P1–P4 静态审计结束，P5 需另行决策和授权。

- [P3：STMMAC link-up / probe handoff 收尾（2026-11-20，P3 正式关闭）](./PANTHER-X2-P3-STMMAC-LINKUP-PROBE-CLOSEOUT-20261120.md)：精确比较 link-up 与 probe，确认 SerDes 分支不命中 Panther RGMII；发现 6.1.174-rk35xx 编译启用的 RTL8211F LED fixup，但它只写 LED 扩展页且不属于 6.12 共同差异。未发现可解释普通 TX 故障的有效共同软件差异。下一步转 P4 pinctrl 首 pin 错误处理只读审计。

- [P3：实际 RK35xx BSP 的 STMMAC core TX 路径复核（2026-11-20）](./PANTHER-X2-P3-RK35XX-STMMAC-CORE-TX-PATH-REVIEW-20261120.md)：以高置信度 c2f148d 纠正普通 stable 源码端点，复核普通 TX 提交/回收、TSO、DMA init、open 与 hw_setup；普通 TX 主路径未发现有效新增差异，link-up/probe handoff 仍待精确比较。全程只读。

- [P3：RK35xx GMAC probe/setup/PHY 电源交接差异（2026-11-19）](./PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md)：按 c2f148d 实际源码候选审查 probe flags、SPH、Vendor MAC、integrated PHY、regulator、runtime-PM 与外接 RGMII 分支；未发现能解释 Panther 普通 TX 故障的新增有效机制。下一步转为 c2f148d STMMAC core TX 路径复核。

- [6.1.174-rk35xx Actions 构建与源码提交关联核验（2026-11-19）](./PANTHER-X2-6.1.174-RK35XX-ACTIONS-RUN-AND-SOURCE-PROVENANCE-CORRELATION-20261119.md)：将 6.1.174 自动 release asset 精确关联 Actions run #296 的编译/上传时间；run workflow 默认源码为 ophub/linux-6.1.y-rockchip，构建时 main 最新提交为 c2f148d。实际 workflow_dispatch inputs/source_hash 未直接取得，故 c2f148d 定为高置信度源码候选，不宣称逐字节证明。
- [P3：RK35xx GMAC clock enable、CCF callback 与 settle 时序（2026-11-19）](./PANTHER-X2-P3-RK35XX-GMAC-CLOCK-ENABLE-CALLBACK-AND-SETTLE-ANALYSIS-20261119.md)：将 c2f148d Panther RGMII 实际 clocks 映射到 DTS/CRU，重新评估忽略 enable 返回值的实际失败可能性；确认 PCLK_USB critical parent chain 在 CRU 注册阶段建立，PLL callback 不在 GMAC probe 首次触发；100–200µs settle 保留为未证实差异。全程只读。

- [P3：RK3568 GMAC bus clock 与 PLL CCF 差异（2026-11-19）](./PANTHER-X2-P3-RK3568-GMAC-BUS-CLOCK-AND-PLL-CCF-DIFF-20261119.md)：区分外部 RGMII MAC clock 与 GMAC ACLK/PCLK bus clock；确认 RK3568 GMAC1 ACLK/PCLK 经 USB clock domain，RK35xx BSP PLL provider 的 enable/disable 增加 normal/slow mux 切换，而通用 CCF 与 GMAC1 mux/gate 定义相同。运行时 GPLL parent 未知，尚非根因；全程只读。

- [P3：6.1.174-rk35xx 源码来源与 GMAC 时钟路径差异（2026-11-19）](./PANTHER-X2-P3-RK35XX-6.1.174-SOURCE-PROVENANCE-AND-GMAC-CLOCK-DIFF-20261119.md)：纠正普通 stable 6.1.174 与实际 RK35xx BSP 的源码族混淆；追踪 RK35xx workflow、release asset、vendor 源码沿革，并确认 BSP 逐项 clock enable / 100–200µs 与正常 general 6.1.116 bulk enable / 5ms 的差异。根因尚未证明；全程只读。

- [RGMII TX delay 三版本源码对照（2026-11-19）](./PANTHER-X2-RGMII-TX-DELAY-THREE-KERNEL-COMPARISON-20261119.md)：6.1.116/6.1.174/6.12.81 的 Panther DTS、RTL8211F 内部 TX delay 和 RK3568 GRF delay 最终设置一致；仅 GRF CON0/CON1 写入顺序不同，当前不构成持续 TX 故障解释。下一步聚焦 GMAC TX clock source/enable 路径。
- [RTL8211F 原始 PHYID2 型号解码与 U-Boot MDIO 写入审计（2026-11-19）](./PANTHER-X2-RTL8211F-PHY-ID-MODEL-DECODE-AND-UBOOT-MDIO-AUDIT-20261119.md)：从已存 PHY ID 0x001cc916 直接解出 PHYID2=0xc916、Model=0x11，支持普通 CG 而非 VD-CG；检查已知 Radxa U-Boot realtek.c 未写 PHYCR2 Reg19。当前 JP/Ophub U-Boot 只有二进制资产，源码行为仍未验证；不安排 PHY 读取或设备操作。
- [RGMII TX pinctrl 静态差分与验证方案（2026-11-19）](./PANTHER-X2-RGMII-TX-PINCTRL-STATIC-AUDIT-AND-VALIDATION-PLAN-20261119.md)：核对 6.1/6.12 Panther GMAC pin groups、RK3568 IOMUX 和 pinctrl 写入路径；发现 6.12 通用 pmx_set 首 pin 错误可能被吞，但未有现场失败证据，列为低至中优先级。设计仅只读 pinctrl ownership 核查，不授权实施；TXC/TXD 电气观测继续暂停。
- [运行时 TX 故障变量测试覆盖交叉核对（2026-11-19）](./PANTHER-X2-DHCP-THIRD-PARTY-TX-EVIDENCE-AND-INVESTIGATION-PRIORITY-20261119.md)：补记用户已完成的全部 offload、强制 100M、MAC 更换/克隆、DHCP 客户端、broadcast flag 与电源管理对照；区分此前已做 EEE 测试及本轮补齐项目，后续不重复。
- [DHCP 第三方接收测试与 TX 故障边界更新（2026-11-19）](./PANTHER-X2-DHCP-THIRD-PARTY-TX-EVIDENCE-AND-INVESTIGATION-PRIORITY-20261119.md)：归档用户新增的同二层有线第三方监听、正常版本阳性对照、故障版零接收、反向广播接收及 IPv6 NDP 证据。将 RX/NAPI 降级，主线转向 GMAC TX、RGMII TX clock 与 PHY TX 方向；不安排新实机测试。
- [TRACE 缓冲区空状态确认（2026-11-19）](./PANTHER-X2-TRACE-BUFFER-EMPTY-BASELINE-20261119.md)：确认 tracer=nop、entries-in-buffer/entries-written=0/0；当前 trace buffer 无需保留的历史记录，尚未创建探针。
- [TRACEFS 双路径实例与缓冲区核验（2026-11-19）](./PANTHER-X2-TRACEFS-MOUNT-IDENTITY-AND-BUFFER-20261119.md)：确认两个路径为同一 tracefs 实例；trace 文件为 515 bytes，内容尚未读取，保留现有 tracing 状态。
- [TRACEFS 当前状态核验（2026-11-19）](./PANTHER-X2-TRACEFS-CURRENT-STATE-20261119.md)：记录 tracing_on=1、current_tracer=nop、无已注册 kprobe/启用事件；保留 tracing 状态与缓冲区，下一步只读确认双挂载实例关系。
- [napi_alloc_skb() 返回值短时探针结果（2026-11-19）](./PANTHER-X2-NAPI-ALLOCATOR-RETURN-PROBE-RESULT-20261119.md)：30 秒探针命中 62 次、missed 0、NULL 返回事件 0；临时探针已删除且原 tracing 状态保持不变。该结果只降低分配失败嫌疑，不证明整个 RX 路径正常。
- [6.12.81 实机 KPROBE / TRACEFS 只读能力检查（2026-11-19）](./PANTHER-X2-6.12-KPROBE-TRACEFS-READONLY-CAPABILITY-20261119.md)：确认实机 tracefs、KPROBES/KPROBE_EVENTS、目标函数 kallsyms 符号及现有 kmem/page_pool/NAPI/SKB tracepoint；下一步先只读检查 tracing 现状，尚未创建探针。
- [6.1.116 实际内核配置闭环与 STMMAC RX 差分（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md)：从原始硬件审计归档提取真实 kernel.config，与官方模板 7,677 个符号全量比较（差异 0）；对 6.1.116/6.12.81 候选 STMMAC RX 主函数进行定点差分。
- [NAPI skb 分配器差分与只读取证方案（2026-11-19）](./PANTHER-X2-NAPI-SKB-ALLOCATOR-DIFF-AND-READONLY-TRACE-CHECK-20261119.md)：比较两版 napi_alloc_skb 实现，记录 6.12 tracing/kprobe 构建能力及不改变运行状态的只读检查方案。
- [6.12.81 实际运行内核配置核验（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-RUNTIME-VERIFICATION-20261119.md)：记录 Panther 实机 6.12.81 运行配置与已锁定构建模板的关键符号核验结果。
- [内核配置来源与只读取证计划（2026-11-19）](./PANTHER-X2-KERNEL-CONFIG-PROVENANCE-AND-READONLY-CAPTURE-20261119.md)：记录两版内核正确构建来源、模板差异和配置提取边界。

- [6.1.174 实际源码 GMAC 时钟路径复核与更正（2026-11-19）](./PANTHER-X2-6.1.174-BSP-GMAC-CLOCK-ENABLE-AND-RGMII-ORDER-DIFF-20261119.md)：更正早前将 2026-11-10 后期 Ophub BSP 的 100–200µs / 忽略 enable 错误代码误归为 6.1.174 的问题。实际 6.1.174 源码仍为 5ms 且检查返回值；RK3568 CRU 与通用 CCF provider 文件在 6.1.116/174 端点完全一致。仅静态审查。
- [6.1.174 BSP GMAC 时钟使能与 RGMII 初始化顺序差分（2026-11-19）](./PANTHER-X2-6.1.174-BSP-GMAC-CLOCK-ENABLE-AND-RGMII-ORDER-DIFF-20261119.md)：直接比较 6.1.116 正常源码与 6.1.174 BSP 候选，并映射 6.12.81；发现后两者 clock enable 错误忽略、100–200µs 等待及 RGMII delay 写入顺序一致。尚无实机 clock enable 失败证据。仅静态审查。
- [Linux stable 6.1.116→6.1.174 Rockchip GMAC glue 与队列初始化差分（2026-11-19）](./PANTHER-X2-STABLE-116-174-ROCKCHIP-GLUE-AND-QUEUE-INIT-DIFF-20261119.md)：核对 RK3568 RGMII GRF/speed/power-up、clock disable 顺序、MTL queue parser 与 DMA channel 初始化；唯一 clock callback 顺序变化不适用于 Panther RK3568，队列和 TX channel 初始化关键函数一致。仅源码审计，未做设备操作。
- [Linux stable 6.1.116→6.1.174 MAC / DMA / MTL TX 使能路径差分（2026-11-19）](./PANTHER-X2-STABLE-116-174-MAC-DMA-MTL-TX-ENABLE-DIFF-20261119.md)：对照 MAC TE、DMA TX ST、tail pointer、MTL TXQEN/TQS 和 phylink SerDes 回调；Panther 走默认寄存器映射，未发现相关 upstream 行为回归。仅源码审计，未做设备操作。
- [Linux stable 6.1.116→6.1.174 STMMAC TX 核心路径差分（2026-11-19）](./PANTHER-X2-STABLE-116-174-STMMAC-TX-CORE-DIFF-20261119.md)：直接对照 stable tag 的普通 TX 提交、descriptor reclaim、TX error recovery、DWMAC4 地址映射重构；未发现普通 TX 核心流程变化，Panther 使用新增地址映射的 NULL 默认偏移回退。仅源码审计，未做设备操作。
- [RTL8211F TX 计数能力与单帧边界测试可行性（2026-11-19）](./RTL8211F-TX-COUNTER-AND-TEST-FEASIBILITY-20261119.md)：只审查 RTL8211F Rev.1.4 数据手册和 Linux v6.12 Realtek PHY 驱动；未发现可用于指定帧验证的 PHY TX packet/octet counter，明确 PHY 计数器不能进一步切分 MAC/RGMII/PHY 线侧边界。未读取实机寄存器、未发送测试帧、未修改配置。

- [Ethernet TX 物理边界测试与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)：归档 AF_PACKET 自定义帧与 iMac 持续抓包结果、TX ftrace/kprobe 和 MMC 计数、6.1.116/6.12.81 精确源码对照、TX descriptor/DMA/MTL/FIFO/时钟审计、危险 debugfs 读取事故及后续 MAC TXC/TXD 物理边界研究路线。

- [Linux 6.12.81 网络测试结果汇总（脱敏，2026-11-16）](./PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md)：将分段提供的 6.12.81 网络测试结果合并归档，覆盖系统身份、启动介质、运行时 DT、GMAC/PHY、ethtool、MMC/DMA、IRQ、RX dropped、IPv4/IPv6 状态及待验证事项。

- [网络与启动链阶段测试总记录（2026-11-16 至 2026-11-17）](./PANTHER-X2-NETWORK-AND-BOOT-TEST-LOG-2026-11-16-17.md)：按时间汇总 6.1.116 正常网络基线、6.12.81 DHCP/NDP 与 GMAC/DMA 检查、TF/eMMC/U-Boot/DTB 取证、JP-TvBox 启动结果及源码对照；新增独立的 6.12.69 RX/IRQ/NAPI 只读快照与 DHCP 证据边界判读，明确区分不同内核启动周期、已验证、未验证和证据缺口。

- [GMAC / DHCP 与 TF U-Boot 启动链调查记录（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)：汇总 Linux 抓包边界、GMAC1/RGMII/RTL8211F、GRF/时钟、TF U-Boot 证据，并追加 6.12.81 GMAC RX/DMA/NAPI 只读复核。
- [TF 前 16 MiB 与 boot.scr 只读证据（2026-11-17）](./TF-FIRST16M-AND-BOOTSCR-READONLY-EVIDENCE-2026-11-17.md)：记录 TF 原始启动区 SHA-256、SPL/U-Boot 字符串偏移、E25/RK3568 内嵌 DTB 标识、boot.scr 镜像头及完整解码脚本行为。
- [eMMC U-Boot 与 Vendor Storage 审计](./EMMC-UBOOT-VENDOR-STORAGE-AUDIT.md)：eMMC 历史 U-Boot 文件及 Vendor Storage 只读审计。注意该报告不代表本轮 TF 启动时实际执行的 U-Boot。
- [TF 启动故障调查](./TF-BOOT-FAILURE-INVESTIGATION.md)：此前 TF 启动与系统故障阶段性记录。

- [6.1.116 Ethernet 基线原始采集（脱敏）](../../evidence/network/panther-eth-baseline-redacted.txt)：完整 eth0、GMAC/PHY、ethtool、计数器、路由与网络状态采集。
- [6.1.116 Ethernet 补充采集（脱敏）](../../evidence/network/panther-eth-supplement-redacted.txt)：内核/软件包/启动镜像/DTB 核对及网关、iMac 连通性测试。
