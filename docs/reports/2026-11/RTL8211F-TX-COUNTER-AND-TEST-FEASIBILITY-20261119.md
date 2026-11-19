# RTL8211F TX 计数能力与单帧边界测试可行性（2026-11-19）

## 1. 本轮范围

本轮只研究一个问题：为了实施“发送一个带唯一标记的特殊帧，再从外向内定位”的测试，RTL8211F 是否提供可只读读取、能够证明该帧到达 PHY 或从 PHY 线侧发出的统计计数。

本轮仅审查 RTL8211F 数据手册及 Linux 6.12 Realtek PHY 驱动。没有读取 Panther 实机 PHY 寄存器，没有发送测试帧，没有安装软件、写寄存器或修改配置。

## 2. 数据手册审查

参考 Realtek RTL8211F(I)-CG / RTL8211FD(I)-CG Datasheet，Track ID JATR-8275-15，Rev. 1.4（2014-11-17）。

手册列出的寄存器包括：
- Clause 22 基本控制/状态、PHY ID、自动协商和 1000BASE-T 状态；
- RTL8211F 专用页寄存器：PHYCR、PHYSR、INER/INSR、LED 控制、RGMII 延时控制等；
- MMD：PCS 状态、EEE 能力/唤醒错误等。

在手册完整寄存器目录及寄存器定义中，没有找到 TX frame count、TX octet count、TX packet counter、MIB statistics 或能与某个 MAC 输入帧逐帧关联的 PHY 发射计数器。

### 2.1 容易误判的计数/状态

- **GBSR Register 10，Idle Error Count（bits 7:0）：** 标记为 RO, RC（read-only, clear-on-read），计数到 0xff 自动停止。它是 1000BASE-T 链路的 idle error 计数，不是 TX packet/frame counter；读取会清除该计数，因此不能作为无副作用的重复快照来源，也不能证明指定测试帧已发送。
- **EEEWER，MMD device 3 register 0x16：** EEE wake error counter，类型 RC，统计 PHY 未能按要求完成 EEE wake sequence 的错误，不是数据帧 TX 计数。
- **PHYSR / link status / 1000BASE-T receiver status：** 反映链路或接收器状态，不代表本机某个 RGMII TX 帧已被 PHY 接收或在线侧发射。
- **LED Activity：** 手册与 Linux 驱动均说明 RTL8211F 的 Active 指示将 RX 与 TX 合并，不能区分方向；LED 闪烁也无法识别特定帧，不适合作为本次边界证据。

因此，按公开 Rev.1.4 手册，结论为：**未发现可用的 PHY TX 帧/字节计数器；现有可见计数仅是其他链路错误或 EEE 状态，不能用来验证指定 TX 帧。**

## 3. Linux 6.12 PHY 驱动审查

审查 Linux v6.12 `drivers/net/phy/realtek.c`：
- RTL8211F 相关代码处理 PHY 初始化、ALDPS、RGMII TX/RX delay、时钟输出、链路中断和 LED 配置。
- 没有发现 PHY driver 的 `get_sset_count`、`get_strings`、`get_stats` 等 PHY 专用统计回调。
- 驱动没有导出 RTL8211F TX packet/octet/MIB counters。
- LED Active 的 RX/TX 合并语义进一步说明它不能作为方向明确的 TX 计数来源。

Linux PHY/ethtool 的一般统计接口能力，不等于该 PHY 硬件实际提供了可读的 TX 统计。不能因为系统支持 ethtool statistics 就推定 RTL8211F 存在这类计数。

## 4. 对单帧边界测试的影响

### 4.1 能做什么

测试仍然可以从外向内进行：
1. iMac 有线接口检查指定唯一标记帧；
2. hEX 检查同一帧；
3. 若两端均未收到，使用 Panther 已有 MAC MMC good-only / good+bad TX counters、Linux TX 统计、DMA completion 和驱动入口记录作为不同层级的辅助证据。

其中 MAC MMC 必须采用同一测试时间窗内的前后差值；累计值不能替代单帧关联。即使 MMC good-only 增长，也只能证明 MAC 内部将帧归类为 good，不能证明 PHY 已在 RGMII 输入端正确接收，更不能证明 MDI 线侧发射成功。

### 4.2 不能做什么

- 不能用 RTL8211F link-up、PHY ID、receiver status 或 Idle Error Count 的变化，声称测试帧已到达 PHY TX 输入或从线侧发出。
- 不能把 EEE wake error counter 当作普通 TX error counter。
- 不应为了“找一个 PHY 计数器”而现场遍历未知扩展页/MMD 地址。未公开寄存器的语义、读清零行为和副作用未经确认；MMD 间接访问本身还需要写 Clause 22 的地址/控制寄存器。当前没有理由在实机上尝试未知寄存器。
- 本轮不读取任何现场 PHY 寄存器，也不建议读取 RO, RC 的 Idle Error Count，以免破坏其累计状态。

## 5. 当前测试方案的可行性结论

| 层级 | 是否能按唯一帧直接确认 | 可用证据 |
|---|---|---|
| iMac | 可以 | 抓到完整 EtherType/payload 唯一标记 |
| hEX | 可以 | 抓到同一唯一标记帧 |
| RTL8211F PHY | **公开接口不可以** | 手册未发现 TX 帧计数；链路/错误状态不能代替 |
| GMAC MMC | 不能按帧内容识别 | 同一时间窗的 good-only / good+bad 计数增量 |
| TX DMA / driver | 不能按线侧帧确认 | 已有 descriptor completion、xmit 入口/返回证据 |

**最终判断：RTL8211F 这一层目前属于“无公开、可安全使用的逐帧 TX 计数器”。** 因此，软件反向定位在 iMac/hEX 外部接收点之后，无法仅靠 PHY 统计把边界进一步切分成“RGMII 输入未收到”与“PHY 内部处理/MDI 发射失败”。

如果将来确实需要区分这两个位置，可靠方法将是直接观测 RGMII TXC/TXD/TX_CTL 或 PHY MDI 侧的物理信号；这属于最后阶段的物理测量，不是本轮授权范围，也不要求现在进行。

## 6. 下一步建议

本轮研究已回答 PHY 计数器可行性问题，不需要继续扩大 RTL8211F 源码审查。

下一步测试准备只需围绕既有证据做最小设计：
- 复用已用过的 EtherType 0x88B5，载荷增加本次唯一 ASCII 标记；
- 只发送一帧；
- 先核对历史 iMac/hEX 测试是否已经具有等价帧型、方向和抓包条件，避免重复；
- 若确有必要执行新帧测试，先明确发送会造成的网络可见性和影响，并取得用户授权；
- 不访问未知 PHY 扩展寄存器，不修改驱动/PHY 配置。

## 7. 参考资料

1. Realtek, *RTL8211F(I)-CG / RTL8211FD(I)-CG Datasheet*, Track ID JATR-8275-15, Rev.1.4, 2014-11-17.  
   https://www.wch.cn/uploads/file/20210908/1631089341753290.pdf
2. Linux v6.12, `drivers/net/phy/realtek.c`.  
   https://github.com/torvalds/linux/blob/v6.12/drivers/net/phy/realtek.c
3. Linux kernel documentation, *Interface statistics*.  
   https://www.kernel.org/doc/html/latest/networking/statistics.html

## 8. 证据状态

- **已审查：** 公开 RTL8211F Rev.1.4 寄存器目录和定义。
- **已审查：** Linux v6.12 Realtek PHY 驱动的 RTL8211F 支持路径及统计回调情况。
- **结论：** 未找到可用于指定帧验证的 PHY TX packet/octet counter。
- **未验证：** Realtek 未公开的内部测试页/未公开寄存器是否另有统计；由于语义和读取副作用不明，不把它们纳入安全测试方案。
- **未执行：** 实机寄存器读取、测试帧发送、配置修改、物理探测。
