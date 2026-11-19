# Panther X2：6.1.116→6.1.174 回归窗口内 STMMAC / 网络栈提交筛查（2026-11-19）

## 1. 本轮纠正研究窗口

根据已归档的实机测试矩阵：
- 6.1.116：已验证正常；
- 6.1.174：最早有明确历史实机证据的异常版本；
- 6.1.117–6.1.173：没有逐版本实机结果，不能把首次回归点提前指定到某个版本。

因此本轮改用同一 unifreq/linux-6.1.y 仓库中两个精确提交作为静态差分端点：
- 6.1.116：5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174：3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7

两端点相距 139 commits。6.1.174 版本提交的自身补丁只更新 Makefile SUBLEVEL，并同步 SKBFL_SHARED_FRAG 标志传播到 GRO/SKB copy/segment/coalesce 路径；它没有直接修改 STMMAC、Rockchip GMAC 或 PHY 驱动。

## 2. 6.1.174 自身补丁：不是 GMAC TX 回归点

6.1.174 提交改动文件：
- net/core/gro.c
- net/core/skbuff.c
- net/ipv4/udp_offload.c
- Makefile

补丁作用是让 SKB 在 GRO 合并、复制、分段和 coalesce 时正确继承 SKBFL_SHARED_FRAG。它属于通用网络缓冲区共享 fragment 标记传播。

与 Panther 当前现象的关系：
- DHCP Discover 是出站小型 IPv4 广播帧，不经过 RX GRO 合并路径；
- 本次故障的主要边界是本机 TX 统计增长但外部接收端未看到帧；
- 因而 6.1.174 最后这个版本号提交本身，不足以解释 Panther 的 TX 物理外发异常。

不能由此排除 6.1.117–6.1.173 期间的其他提交；只能排除 6.1.174 这个最终版本标记提交本身作为直接 TX 原因。

## 3. 116→174 期间已筛到的 STMMAC / PHY 变更

按仓库路径提交历史筛选，识别到以下与 stmmac/PHY 相关的版本提交或本地补丁：

| 提交 | 相关改动 | 对 Panther 当前路径的判断 |
|---|---|---|
| 6.1.117 | STMMAC 单 IRQ 路径初始化 `wol_irq_disabled=true`；同时 Panther DTS 有一次整理 | WoL IRQ 状态，当前没有 WoL 证据；DTS 的 GMAC reset/delay/phy-mode 主配置未变 |
| 6.1.124 | STMMAC DT/MDIO 节点解析重构，增加 devm 配置路径 | 需要继续精查最终 mdio node / PHY attach 语义；当前 PHY 能识别且 link up，基本路径已工作 |
| 6.1.142 | STMMAC bus_id fallback 改为查 alias highest id；MDIO 读写增加地址范围与 NULL callback 检查 | Panther DTS 有 `ethernet0 = &gmac1` alias，通常会命中明确 alias；尚无证据解释帧不出线 |
| 6.1.150 | 删除 DWMAC XGMAC2 RX overflow interrupt enable | Panther 是 DWMAC4/5，非该 XGMAC2 path，不适用 |
| 6.1.158 | Rockchip GMAC powerdown 时将 set_clock_selection 移到 clock disable 之前 | 只改变 powerdown 顺序；不改变当前初始 powerup 路径，优先级低 |
| 6.1.164 | STMMAC MSI IRQ affinity hint 写法调整 | Panther 是普通 RK3566 platform GMAC，非 PCI multi-MSI 路径 |
| 6.1.167 | 移除 STMMAC LPI 专用 IRQ handling；修改 PCIe DTS ranges | Panther 不是 Intel mGbE / PCI multi-MSI，未见普通 TX 数据通路影响 |
| 6.1.169 | STMMAC chain_mode jumbo frame DMA mapping 修复；删除 LPI IRQ 资源；PHY LED trigger 生命周期调整 | Panther 基线 `chain_mode=0`（ring mode），普通 DHCP 小帧不走 chain jumbo 分支；LPI IRQ 与 LED trigger 不解释 TX 物理边界 |

## 4. 当前最值得继续精查的两个提交簇

### 4.1 6.1.124：STMMAC DT / MDIO 解析重构

这是本轮列表中唯一可能改变 Panther 初始化拓扑的 STMMAC 结构性重构。后续要精确核对：
1. 旧版 `stmmac_dt_phy()` 与新版 `stmmac_of_get_mdio()` / `stmmac_probe_config_dt()` 对 Panther `mdio1` 子节点的选择是否完全相同；
2. `mdio_bus_data->needs_reset` 是否保持一致；
3. `phy-handle` / `port_node` 最终是否仍连接同一 `ethernet-phy@0`；
4. 对应改动是否可能改变 PHY reset/attach 先后顺序。

目前 Panther 在异常版本仍能识别 RTL8211F、读取 PHY ID、建立 1Gbps Full Link，因此这类变化即使存在，也不能直接解释 TX frame 经过 MAC 统计但外部不可见；必须找到影响 MAC/PHY数据方向的具体路径才保留。

### 4.2 6.1.169：chain-mode TX mapping 与 IRQ 变化

6.1.169 的 `chain_mode.c` 修复 jumbo frame 时首段长度 `bmax` 超过 `nopaged_len` 的潜在 DMA mapping 长度问题，改用 `buf_len=min(nopaged_len,bmax)`。

但 Panther 6.1.116 运行配置记录为 `chain_mode=0`，即 ring mode；当前 DHCP Discover 是普通小帧，不属于 chain-mode jumbo frame。因此可将该修复从 Panther 当前故障的主要候选中排除。

同一版本中 LPI IRQ handling 的删除是独立中断资源变化；没有证据表明 Panther 使用独立 LPI IRQ。

## 5. 本轮结论

1. 6.1.174 版本号提交自身只修改 SKB shared-frag 元数据传播，不修改 STMMAC/Rockchip GMAC/PHY；不能把故障简单归因于“升级到 6.1.174 的最后一个提交”。
2. 116→174 期间已识别的 STMMAC 修改大部分针对 PCI multi-MSI、LPI IRQ、XGMAC2 或 chain-mode jumbo TX，不适用于 Panther 当前 RK3566 DWMAC4/5、ring-mode、外置 RTL8211F、普通小帧发送路径。
3. 6.1.124 的 DT/MDIO 重构是剩余值得精查的初始化差异，但已有异常版本 PHY ID 与 1Gbps link-up 证据，解释力有限。
4. 当前不能确定首次软件回归点；6.1.117–6.1.173 之间仍未做逐版本实机二分，不能把源码提交日期等同于实机首次故障日期。

## 6. 下一步（不重复设备测试）

下一步只做 6.1.124 的旧/新 STMMAC DT/MDIO 解析函数逐项差分，并确认是否影响 Panther 的 MDIO reset/PHY attach 生命周期。若该路径最终等价，就把 116→174 的 STMMAC 主初始化候选再降级，转向 6.12 与 6.1 共有的上层 DMA/网络缓冲区路径差异；不再回头重查已关闭的 clock、RGMII delay、MAC 地址来源、TX descriptor 和 ring/chain mode。

无设备命令、无驱动修改、无配置更改、无网络重测。

## 7. 源码与提交链接

- 6.1.116 commit：https://github.com/unifreq/linux-6.1.y/commit/5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.1.174 commit：https://github.com/unifreq/linux-6.1.y/commit/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7
- 6.1.117 update：https://github.com/unifreq/linux-6.1.y/commit/71ff8d028d9e8e629cee677034b385f468bce4bd
- Panther DTS cleanup：https://github.com/unifreq/linux-6.1.y/commit/ffffa29dfec714c7b2682625faff73111174e783
- 6.1.124 update：https://github.com/unifreq/linux-6.1.y/commit/7ad51a3881512659f4a1b4f7c62deb45ebb679e9
- 6.1.142 update：https://github.com/unifreq/linux-6.1.y/commit/23d903e9acb6e411a65609b9d93493a6e72e3286
- 6.1.158 update：https://github.com/unifreq/linux-6.1.y/commit/7edf1d71c9e7a0320477f4653a833393b65ce8f9
- 6.1.169 update：https://github.com/unifreq/linux-6.1.y/commit/6bfd4a956d896a21b0228d089a21e11b39df0d17
- 6.1.174 update：https://github.com/unifreq/linux-6.1.y/commit/3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7