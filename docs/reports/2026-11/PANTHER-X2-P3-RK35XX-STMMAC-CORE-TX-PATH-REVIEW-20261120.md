# Panther X2：实际 RK35xx BSP 的 STMMAC core TX 路径复核（2026-11-20）

## 1. 目的与边界

纠正此前部分 STMMAC core 审计使用普通 stable 6.1.174、而非最早异常 6.1.174-rk35xx 高置信度源码候选的问题。

本轮只读比较：
- 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 最早异常 6.1.174-rk35xx 候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 持续异常 6.12.81-rk35xx：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

未进行 Panther 实机操作、寄存器访问、发包、抓包、驱动修改或补丁制作。

## 2. 比较结果

### 2.1 普通 TX 提交与回收

对实际候选源码中的 `stmmac_xmit()`、`stmmac_tx_clean()` 做函数边界提取后比较：
- 主要 descriptor 提交、回收控制流没有发现能解释当前普通广播帧 TX 丢失的新增差异；
- 可见差异集中在统计处理；
- 之前初步提到的“c2f148d 给 `stmmac_enable_dma_transmission()` 增加 queue 参数”是错误差分，已撤销。重新核对 `hwif.h` callback 和 `dwmac_lib.c` 实现后，接口仍为无 queue 参数，写入传统 TX poll demand。

注意：该结论只针对上述精确函数/端点和普通 TX 主路径，不等于证明所有 STMMAC 子路径完全相同。

### 2.2 TSO

`stmmac_tso_xmit()` 存在专用变化，但 Panther 当前已知故障测试是普通 DHCP/UDP 广播，不走 TSO 分段路径。暂不将 TSO 差异列为本故障的有效解释。

### 2.3 DMA engine init

实际 c2f148d 与 6.12.81 的 DMA engine init 均不含正常 6.1.116 中的 1500ms 延时。该差异已在 P1/JL2xx1 workaround 溯源中确认：原始目的针对 JL2XX1/JL2101 快速启动时序，后续按 PHY ID 条件启用；Panther PHY ID 为 RTL8211F-CG，不匹配，故已降级，不重复扩展。

### 2.4 hw_setup 与 open

- `stmmac_hw_setup()` 函数体在 6.1.116 与 c2f148d 之间完全一致。
- `__stmmac_open()` 存在 SerDes 条件分支差异；Panther 使用 RGMII 外接 RTL8211F，该分支不命中。

### 2.5 尚未完成的边界

以下函数的精确函数体差分本轮尚未完成闭环：
- `stmmac_mac_link_up()`
- `stmmac_dvr_probe()`
- 与它们直接相关的 MAC/DMA start handoff（仅在函数差异实际存在时追踪）

原因是远程文件分段获取/超时导致最后一轮函数体提取未完成。不能把“尚未比较”写成“相同”或“已排除”。

## 3. 当前结论

截至本轮，尚未发现实际 c2f148d 的普通 STMMAC TX 提交/回收核心存在一个同时满足以下条件的新增差异：
1. 6.1.174-rk35xx 与 6.12.81-rk35xx 共有；
2. 正常 6.1.116 不存在；
3. Panther RGMII + 外接 RTL8211F + 普通 DHCP/UDP 广播路径实际命中；
4. 具备导致 TX frame 未被同二层第三方监听器收到的合理机制。

**P3 尚未正式关闭。** 只剩上述 link-up / probe handoff 函数的精确比较。若其无相关差异，则关闭 P3 core 子项，不继续扩大 STMMAC 函数范围。

## 4. 下一步唯一工作

只完成 `stmmac_mac_link_up()`、`stmmac_dvr_probe()` 及必要的直接调用关系差分；比较正常 6.1.116、c2f148d，必要时以 6.12.81 交叉核对。

- 若发现命中 Panther RGMII 的有效变化：追踪其实际回调/寄存器作用，不直接认定根因。
- 若未发现：明确记录 P3 源码差异审计无有效 TX 核心命中，关闭 P3，转 P4（pinctrl 首 pin 错误处理静态审计；低优先级、只读）。
- 不重复 descriptor OWN/tail pointer/barrier、DMA helper、queue parser、PHY MDIO、时钟、RX/NAPI 和物理边界测试。
- 不进行实机操作。

## 5. 相关报告

- `PANTHER-X2-P3-RK35XX-GMAC-PROBE-SETUP-POWER-HANDOFF-DIFF-20261119.md`
- `PANTHER-X2-STABLE-116-174-STMMAC-TX-CORE-DIFF-20261119.md`
- `PANTHER-X2-JL2XX1-WORKAROUND-ORIGIN-AND-SCOPE-20261119.md`
- `PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md`
