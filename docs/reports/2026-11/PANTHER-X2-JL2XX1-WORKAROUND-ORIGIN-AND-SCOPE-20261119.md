# Panther X2：JL2xx1 workaround 原始背景与适用范围溯源（2026-11-19）

## 本轮范围与边界

本轮只做公开源码、提交历史和原始开发讨论的离线审计。没有执行 Panther X2 设备命令，没有启动故障内核，没有写 PHY 寄存器，没有改动系统。

## 1. 原始来源链

### 1.1 代码来源

6.1.116 工作树中的 commit：

- `49b5f340f346cc9a5b777499fce46150b691b70e`
- 标题：`drv: net: ethernet: stmmac fix for jl2xx1 phy`
- 日期：2022-12-24
- 父提交：`22e67a04d5f9912c7eaeb4603894ea2a4c3ffe36`（`drv: net: phy: Add JLSEMI JL2xx1 driver`）

它包含两项不同改动：
1. `stmmac_init_dma_engine()` 在 DMA reset 前增加固定 `msleep(1500)`。
2. `stmmac_mdio_register()` 中增加 PHY addr 0 的四次 MDIO 写入。

### 1.2 1500ms 延时的上游背景

CoreELEC/linux-amlogic PR #13 的作者说明，延时是为 JL2XX1/JL2101 PHY 的早期初始化时序问题准备；推荐值 1500ms。后续独立提交 `3e1d125ed02c04e799ef1eb9fab936488ee11fbe` 将延时改为仅在 PHY ID 匹配 JL2XX1（`0x937c4030`）或 JL2101（`0x937c4032`）时执行。

PR 讨论中的测试记录：
- JL2101 目标设备在快速启动时存在 quick-boot 问题；慢启动（例如首次刷机后启动）通常正常。
- 该问题表现为 PHY 驱动未正确绑定，进而不能正常取得 DHCP 地址或落入 169 地址。
- 1500ms 延时后，JL2101 目标设备恢复；两个 RTL8211F 对照设备（BPi M5、HK1 Box X4）在有无该延时的测试中均正常。
- 这说明延时的原始目标是 JL2101/JL2XX1 启动时序，不是一般性的 STMMAC DMA reset 稳定延时。

来源：
- https://github.com/CoreELEC/linux-amlogic/pull/13
- https://github.com/CoreELEC/linux-amlogic/commit/3e1d125ed02c04e799ef1eb9fab936488ee11fbe

### 1.3 MDIO 四次写入的来源

PR #13 中，作者在 2023-01-03 回答寄存器写入来源问题时，指出这些写入来自 Lean（coolsnowwolf/lede）OpenWrt 仓库中的补丁，且最初源自 JLSemi 提供的代码；当时作者并不知道每个数值的确切含义。

对应补丁提交：
- https://github.com/coolsnowwolf/lede/commit/b889ab8789155707f5a73f69d87f33d18e33bb78
- 补丁文件：`target/linux/rockchip/patches-5.19/801-fix-stmmac_mdio.patch`

因此，不能把该组写入称为 Realtek 官方初始化序列；目前可追溯到的是 JLSEMI/JL2XX1 相关的厂商代码来源。

## 2. 两项改动必须分开判断

### A. DMA reset 前 1500ms

**原始目的已查明：**给 JL2XX1/JL2101 的早期初始化/识别过程留出时间。后续上游化版本明确按 PHY ID 条件启用，而不是对所有 PHY 无条件延时。

**对 Panther 的适用性：低。**
- Panther 实机 PHY ID 已确认是 `0x001cc916`，对应 RTL8211F-CG 型号编码。
- 该 ID 不属于 JL2XX1/JL2101 的 `0x937c4030/0x937c4032`。
- CoreELEC 原始讨论中的 RTL8211F 对照设备并不需要该延时。

因此，1500ms 这一子项不再作为 Panther TX 故障的优先根因候选。它在 6.1.116 存在、6.1.174/6.12 缺失，只是版本相关性；原始用途与 Panther PHY 不匹配。

### B. PHY addr 0 的 MDIO 写入

代码为：

```c
stmmac_mdio_write(new_bus, 0, 31, 2627);
stmmac_mdio_write(new_bus, 0, 25, 0x1801);
stmmac_mdio_write(new_bus, 0, 31, 0);
stmmac_mdio_write(new_bus, 0, 0, 0x8000);
```

PR 讨论显示，最初尝试时把写入放在 MDIO bus 注册附近；后续作者报告进一步测试后发现 **MII injection 实际并非必需，只有 delay 是需要的**。因此，不能把四次写入与 1500ms 延时视为同一必要机制。

另一方面，原始 JLSEMI 代码的确切寄存器意图尚未得到 JLSemi FAE 回复的可读文本证实；PR 中 FAE 回复以附件/图片形式呈现，当前可访问文本没有给出具体寄存器解释。

Panther 方面，已有 RTL8211F Rev.1.7 数据手册解码显示 `0x0a43:0x19=0x1801` 涉及 CLKOUT、RXC、EEE 和保留位组合，且后续 BMCR reset 会触发 PHY reset。地址 0 对 RTL8211F 可能具有广播语义。**但仍未证明这四次写入在 Panther 6.1.116 启动时全部成功，也未证明 reset 后的寄存器状态。**

## 3. 当前版本回归解释力

| 子项 | 原始目标 | Panther PHY 匹配度 | 当前优先级 |
|---|---|---:|---|
| 1500ms DMA reset 前延时 | JL2XX1/JL2101 快速启动初始化时序 | 低；PHY ID 不匹配，RTL8211F 对照设备无需该延时 | 降级 |
| 四次 MDIO 写入 | JLSEMI 厂商 PHY 初始化/识别路径；具体含义原始作者未完全说明 | 未定；addr 0 broadcast 可能触及 RTL8211F，需继续审查语义 | 保留为独立子项 |

原始提交把两项放在同一 commit 中，不代表它们具有共同原因。后续 CoreELEC 代码把 delay 独立为 PHY-ID 条件逻辑，PR 作者又明确表示 MDIO injection 并非必要。这是本轮最重要的历史证据。

## 4. 对 Panther 排查路线的调整

1. **停止把 1500ms 延时作为主线。**不再优先追查它能否解释 Panther 的 TX 单向故障。
2. **P1 剩余工作聚焦四次 MDIO 写入。**继续查 JLSemi 原始补丁/公开驱动、FAE 可读资料、RTL8211F-CG 对该寄存器组的适用性，以及 PHY reset 对寄存器的影响。
3. 追查 6.1.174 为什么缺失该组写入时，必须区分“分支未携带厂商补丁”与“有意删除/替代”；目前没有证据表明 6.1.174 曾对其做过有目的的反向修正。
4. 若寄存器语义仍不能建立因果，再结束 P1 并按路线图转 P2（RTL8211F PHY 时钟输入链与 U-Boot/Linux 初始化交接）。
5. 不进行设备端 MDIO 写入、PHY reset、接口重启或故障内核实机测试，除非用户另行明确授权。

## 5. 证据状态

### 已验证
- 原始 commit 的两项改动、文件和执行位置。
- 1500ms 延时针对 JL2XX1/JL2101 的原始说明及后续按 PHY ID 条件启用的代码。
- PR 讨论中 JL2101 快速启动问题和 RTL8211F 对照设备测试记录。
- MDIO 写入来自 Lean OpenWrt 补丁，作者称源自 JLSemi 提供的代码。
- 原 PR 作者后续明确表示 MII injection 并非必需，只有 delay 需要。

### 未验证
- JLSEMI 原始 MDIO 写入每一步的确切寄存器意图。
- Panther 实机 RTL8211F 对四次 MDIO 写入的实际响应与最终寄存器状态。
- 该写入组是否足以解释 6.1.116 与 6.1.174 的差异。

### 结论
JL2xx1 workaround 不应再作为一个整体候选。1500ms 延时已因 PHY 型号不匹配而降级；真正值得继续研究的只剩 PHY addr 0 的 MDIO 写入组。当前没有根因定论。
