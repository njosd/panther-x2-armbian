# Panther X2 项目 A：B2-0 早期正常 6.1.y 版本源码对照补充审计

- 日期：2026-11-24
- 阶段：B2-0，只读源码研究
- 对照版本：6.1.79、6.1.112、6.1.116、6.1.174
- 设备：Panther X2 / RK3566 / GMAC1 / RGMII / RTL8211F
- 结论性质：源码静态对照；不等同于已证明每个历史二进制由对应 commit 原样构建

## 1. 本轮新增的重要历史事实

用户确认：
- 6.1.79、6.1.112 若出现在本机 eMMC 系统备份中，即属于本机实际运行过的历史版本；
- 用户不记得 6.1.116 之前出现过网络不通；网络中断会使该机器的应用服务整体不可用；
- 因此 6.1.79、6.1.112 纳入“实机运行且网络正常”的正向历史基线，专项网络抓包/验收证据完整度低于 6.1.65、6.1.116。

仓库历史资料还记录 /ddbr/backup 中有 6.1.65、6.1.79、6.1.112 三个备份节点，目录时间分别为 2024-02-27、2024-10-18、2024-11-11。6.1.79/112 的精确内核资产本体、Image/DTB 哈希和 config 仍需从原备份归档恢复。

## 2. 找到的 6.1.y 源码版本提交

在 `unifreq/linux-6.1.y` 中找到与版本更新对应的精确 commit：

| 版本 | Commit | Commit 日期 UTC | 说明 |
|---|---|---|---|
| 6.1.79 | `e77fb4335d38f79b66ab5e1e3c627f54140fcb2a` | 2024-02-23 | commit message: `up to 6.1.79` |
| 6.1.112 | `a29ec4768872f856a3a17326334d53482d25fcfa` | 2024-10-02 | commit message: `up to 6.1.112` |
| 6.1.116 | `5eb841b59d6ead6e264163785a634e78f0253c8e` | 2024-11-09 | 已有实机正常基线源码映射，高置信度 |
| 6.1.174 | `3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7` | 2026-05-23 | 对应 stable 6.1.174 源码版本；历史异常镜像的最终构建输入仍需单独闭环 |

**证据边界：** 6.1.79/112 的 commit 是相应版本在 unifreq 源码树中的精确版本提交，但尚未取得 eMMC 备份内 Image 与源码 commit 的构建映射。当前可将其作为高价值源码候选端点，不应声称已完成二进制逐字节来源证明。

## 3. 关键发现：6.1.79、6.1.112、6.1.116 的 GMAC 主干高度稳定

对上述三个正常历史版本的相同源码路径逐文件取回，Git blob SHA 结果如下：

| 文件 | 6.1.79 | 6.1.112 | 6.1.116 | 结论 |
|---|---|---|---|---|
| `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c` | `514f1ac0dea2d49cd4f581a48db2b02160187d0a` | 同左 | 同左 | 文件完全相同 |
| `drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c` | `c60ad9357f1a845b9c58b25b09adc50793805f92` | 同左 | 同左 | 文件完全相同 |
| Panther X2 DTS `rk3566-panther-x2.dts` | `1e3153c392d8de617f72b3133eaeddf45569bde8` | 同左 | 同左 | 文件完全相同 |
| `stmmac_main.c` | `4e4afbe97b5b0a920dc919a995de92301bea1f26` | `655edb3dc63c622945ffdf1f82aa729c0e233194` | `b42383fbcff86b11dd0b09ea0e1981c714625d80` | 文件有变化，但下列关键函数体完全相同 |
| `pinctrl-rockchip.c` | `0276b52f37168423346316089a39417082e6f1f6` | `ca5a01c11ce60ada0a0dec9c7e9701c1285cfc38` | 同 6.1.112 | 文件有变化，GMAC pinmux 错误返回语义未变 |
| `drivers/net/phy/realtek.c` | `cd4e6e4919539f69b515c70974f3f71a7de38c5f` | `12030bd4dca5ffebb55412a2684cb15918869ab2` | `3d29f78108e746b7a2f99772dabb8374fd78f278` | PHY 文件有变化，需区分具体函数语义 |

对 `stmmac_main.c` 提取函数体并逐版本比较：
- `stmmac_xmit()`：6.1.79 / 6.1.112 / 6.1.116 函数体完全相同；
- `stmmac_init_dma_engine()`：完全相同；
- `stmmac_mac_link_up()`：完全相同；
- `stmmac_tx_clean()`：完全相同。

因此这些核心 TX 提交、DMA 初始化、link-up 和 TX 回收函数在 6.1.79→6.1.112→6.1.116 的正常历史区间没有变化。文件整体 SHA 不同不应被误读成这些核心函数发生变化。

## 4. Rockchip GMAC glue 的冷启动路径没有变化

在 `dwmac-rk.c` 中进一步提取并比较：
- `gmac_clk_enable()`：6.1.79 / 112 / 116 完全相同；
- `rk_gmac_powerup()`：完全相同；
- `rk_fix_speed()`：完全相同；
- `rk_gmac_clk_init()`：完全相同。

其关键语义包括：
- bulk clock prepare/enable；
- 检查 clock enable 返回值；
- 对适用的 PHY clock 做 prepare/enable 并检查返回值；
- clock selection callback（若存在）；
- 固定 `mdelay(5)`；
- RGMII GRF 配置和 PHY regulator 上电的既有顺序。

6.1.174 stable 源码端点的 `rk_gmac_powerup()`、`rk_fix_speed()`、`rk_gmac_clk_init()` 与三个正常端点相同；`gmac_clk_enable()` 的函数差异位于 disable 分支，enable/cold-start 分支仍完全相同。

**阶段判断：** 目前没有源码证据支持 6.1.79→6.1.112→6.1.116→stable 6.1.174 之间的 Rockchip GMAC cold power-up/clock-enable 路径发生功能性回归。该结论针对已锁定的 unifreq stable 源码端点，不替代对具体 RK35xx 发布包构建补丁的来源确认。

## 5. Pinctrl 变化的真实语义：不是首 pin 错误吞掉

6.1.79 的 `rockchip_pmx_set()` 在 rollback 已配置 pins 时，循环内沿用当前 `bank` 指针；6.1.112 起，rollback 循环会对每个历史 pin 重新执行 `pin_to_bank()`。这是跨 bank pin group 出错后回滚时的正确性修正。

关键点：
- 三个正常版本的主配置循环都在 `rockchip_set_mux()` 返回错误时直接 `break`；
- 错误处理条件始终是 `if (ret)`，不是 `if (ret && cnt)`；
- 首 pin 写入失败时仍返回错误，不存在“首 pin 失败被忽略”的行为；
- 6.1.112 与 6.1.116 的整个 `rockchip_pmx_set()` 函数体完全相同。

6.1.79→6.1.112 的函数变化只涉及 rollback 阶段重新计算 bank，不改变成功配置路径，也不改变首 pin 错误返回语义。该改动不能解释后续网络故障。

### 重要来源纠正

此前项目 B 的某些 P4 讨论使用 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` 作为 6.1.174 故障源码候选，并发现 `if (ret && cnt)`。但该 commit 日期为 2026-11-10，晚于 stable 6.1.174 的版本提交 `3f06ed3`（2026-05-23），不能在没有 cherry-pick/build 日志证明时归因给 6.1.174 故障镜像。

本轮核验的 stable 6.1.174 源码 `rockchip_pmx_set()` 仍是 `if (ret)`。因此：
- 已确认：`if (ret && cnt)` 存在于 c2f148d 这一后期 BSP 快照；
- 已确认：它不存在于 6.1.79/112/116 和 stable 6.1.174 端点；
- 未确认：实际故障 6.1.174 二进制是否曾通过额外补丁引入此行为；
- 结论：在获得实际构建补丁集前，不能再称它为“6.1.174 与 6.12.81 已证实的共同缺陷”。

## 6. RTL8211F PHY 驱动的正常历史差异

6.1.79 的 `rtl8211f_config_init()` 在设置 ALDPS 和 RGMII delay 后，无条件调用 `genphy_soft_reset()`。

6.1.112/6.1.116 的实现改为：只有 `priv->has_phycr2` 时才更新 PHYCR2 并调用 `genphy_soft_reset()`；否则返回 0。该差异意味着正常历史版本之间 PHY 初始化 reset 语义曾发生变化，但 6.1.79 与 6.1.112/116 都被用户确认实际网络正常，因此不能单独将该变化视为故障根因。

6.1.116 新增 `realtek,led-data` 属性读取并设置 LED/EEE LED 寄存器；该逻辑不改变普通 RGMII delay 设置和常规链路协商流程。stable 6.1.174 的 `realtek.c` blob SHA 与 6.1.116 完全相同，故这项 PHY 驱动实现从 6.1.116 到 stable 6.1.174 没有变化。

6.12.81 的 Realtek PHY 驱动出现更大的生命周期/LED 管理变化（包括 LED restore helper 和 resume 相关逻辑），但当前已知 6.12.81 cold boot 能识别 RTL8211F 并建立 1Gbps Full link。该变化需要按初始化路径和 suspend/resume 是否实际发生来审查，不能仅凭文件差异认定为本次冷启动 TX 故障原因。

## 7. 本轮结论：已缩小的候选范围

### 可降低优先级/暂不重查
1. 6.1.79→6.1.116 正常区间的 STMMAC 普通 TX 核心函数：已确认关键函数体相同。
2. 6.1.79→6.1.174 stable 源码的 Rockchip GMAC cold power-up 主要函数：已确认 enable 路径保持相同。
3. 6.1.79→6.1.112 的 pinctrl rollback 修正：不改变正常 pinmux 配置和首 pin error return。
4. 6.1.116→stable 6.1.174 的 RTL8211F PHY driver：文件完全相同。

### 仍需优先查证
1. 6.1.79/112 实际备份中的 Image、DTB、config、modules 与上述源码 commit 的映射；
2. 后续多个异常 6.1.y 小版本的确切版本号、各自的实际源码仓库/commit/patchset；不能将所有 6.1.y 异常版本都假定为同一个 unifreq stable 树；
3. 6.1.174 故障镜像的真实构建输入：stable `3f06ed3`、RK35xx BSP 分支、或额外 patchset 的证据；
4. 6.12.81 相对正常 6.1.116 的 Realtek PHY 生命周期差异，以及 Rockchip GMAC glue 中实际命中的 clock/CSU 行为；
5. 对 6.18.63 精确 commit 做上述路径的继承/重构/修复映射；当前 B1 网络功能关闭，不能把 B1 当成 6.18 网络失败运行证据。

## 8. 下一步

继续只读研究，不重复实机网络测试：
1. 先恢复 6.1.79、6.1.112、6.1.116 实际资产与源码身份；
2. 按“正常历史端点 → 第一个实际异常端点”重新定义回归窗口；
3. 对后续异常版本逐一核对它们是否来自通用 unifreq 6.1.y 还是 RK35xx BSP 分支；
4. 以真实源码 commit/patchset 为准比较 GMAC、PHY、pinctrl、DMA、时钟和网络核心；
5. 再把确认存在的差异映射到 6.18.63，为 B2-n 形成可证伪的组件试验目标。

不进行构建、补丁、写卡、设备启动、配置修改、寄存器访问、MDIO/PHY 操作或网络重测。
