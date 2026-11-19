# Panther X2：6.12.81 精确构建源码中的 STMMAC PHY resume 修复适用性核查（2026-11-19）

## 1. 本轮核查目标

验证上轮提出的上游修复：
`06232cb44bc8e81adc2f1d40a01bed830b607ea2`
`net: stmmac: resume PHY before hardware setup when opening the interface`

是否包含在 Panther 实际运行的 6.12.81-rk35xx-ophub 源码中，以及该修复描述的 MTU-change / PHY suspend / DMA reset 场景是否与 Panther 已知启动故障吻合。

## 2. 实际构建来源：沿用并直接使用已归档的精确构建指纹

仓库 2026-11-17 报告第 16 节已锁定：
- GitHub Actions run：43405957386
- Job ID：131820239401
- Source repo：`ophub/linux-6.12.y-rockchip`
- Source commit：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- Kernel：6.12.81
- LOCALVERSION：`-rk35xx-ophub`
- 构建参数：`kernel_patch=false`、`auto_patch=false`，日志明确 `No custom kernel patches provided.`
- 实机 `uname -v` 时间与 Actions 编译日志更新 `utsversion.h` 的时间秒级吻合。

因此本报告直接检查上述确切 source commit，而不是使用当前 mainline 或另一个 6.12 开发分支替代。

边界：没有当前设备已安装 `/boot/Image` 的 SHA256，所以仍属于高置信度构建来源匹配，而非已完成的 Image 二进制哈希认证。

## 3. 精确源码结果：上游 PHY resume 修复确实不存在

在 `ophub/linux-6.12.y-rockchip@661b2d8` 中检查：

`drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`
`drivers/net/phy/phylink.c`
`include/linux/phylink.h`

结果：
- `stmmac_main.c` 的 `__stmmac_open()` 中没有 `phylink_prepare_resume(priv->phylink)`；
- `phylink.c` 中没有 `phylink_prepare_resume()` 实现；
- `include/linux/phylink.h` 中没有该 helper 声明；
- `__stmmac_open()` 在调用 `stmmac_hw_setup()` 前没有等效的 PHY prepare-resume 操作；
- 初始化顺序为：`pm_runtime_resume_and_get()` → `stmmac_init_phy()`（连接 PHY）→ 参数设置 → `stmmac_hw_setup()`（包含 DMA reset）→ `phylink_start()`。

因此可以确定：**该精确 source commit 不包含 2026-08 上游提交 06232cb44bc8 的修复，也没有发现等效的 prepare-resume 调用。**

## 4. 重要差异：Panther 这份源码的 MTU reopen 路径，与上游补丁描述的触发条件并不相同

这是本轮最关键的适用性判断。

### 4.1 Panther 精确源码中的 MTU change 路径

在 `stmmac_change_mtu()` 中，当 `netif_running(dev)` 为真：
1. 分配新的 DMA config；
2. 调用 `stmmac_release(dev)`；
3. 调用 `__stmmac_open(dev, dma_conf)` 重新打开接口。

而 Panther 精确源码中的 `stmmac_release()` 明确执行：
```c
phylink_stop(priv->phylink);
phylink_disconnect_phy(priv->phylink);
```

在随后 `__stmmac_open()` 中又执行 `stmmac_init_phy(dev)`，重新连接 PHY，然后才执行硬件初始化/DMA reset。

### 4.2 上游 06232cb44bc8 修复描述的路径

该上游提交的说明明确指出，其回归源自另一个先前提交：
`db299a0c09e9`（`net: stmmac: move PHY handling out of __stmmac_open()/release()`）。

该重构后的 MTU reopen 路径中，`__stmmac_release()` 只停止 phylink、并不 disconnect PHY；PHY 因 `phylink_stop()` 进入 suspended/power-down 状态，却仍保留在 phylink 中。随后 `__stmmac_open()` 先做 DMA reset，`phylink_start()` 才恢复 PHY，造成 RXC 尚未运行时 DMA reset 超时。

上游修复在 hardware setup 前调用 `phylink_prepare_resume()`。

### 4.3 两条路径的实质差异

| 项目 | Panther 精确 661b2d8 源码 | 上游 06232cb44bc8 修复所针对的重构路径 |
|---|---|---|
| MTU change 时 stop phylink | 是 | 是 |
| release 时 disconnect PHY | **是** | **否** |
| reopen 时重新执行 stmmac_init_phy | **是** | PHY 保留连接 |
| DMA reset 前 prepare-resume | 否 | 修复后是 |
| 是否符合上游补丁所述“PHY 保持连接但 suspended”触发条件 | **未显示符合** | 是 |

这意味着虽然 Panther 的精确构建缺少该上游 helper，但它的 MTU-change reopen 生命周期与该上游补丁所描述的触发路径不同。不能因为缺少 helper 就直接推断 Panther 必然存在相同故障。

源码证明 `phylink_disconnect_phy()` 会调用 `phy_disconnect()`；重新 open 时再调用 `stmmac_init_phy()`。但这份静态源码本身还不足以证明 RTL8211F 在 disconnect/reconnect 后的实际 RXC 时序，所以不将该路径判定为绝对无风险。

## 5. 与 Panther 已有运行证据交叉核对

### 已有记录

- profile MTU：`auto`
- eth0 运行时 MTU：1500
- eth0：`UP, LOWER_UP`
- 链路：1Gbps / Full
- 用户此前提供的 grep 输出只显示 `Link is Up - 1Gbps/Full - flow control rx/tx`
- 同一 grep 输出没有显示：
  - `Failed to reset the dma`
  - `DMA engine initialization failed`
  - `Hw setup failed`
  - `Link is Down`

但该记录是筛选片段，不是完整 UART/dmesg 全日志；只能说“现有筛选结果未见”，不能证明所有时间窗口均未发生。

### 与故障发生时点的关系

当前主故障是 Linux 启动后 DHCP Discover 未从 Panther 的物理链路被 hEX/iMac 观察到。现有记录没有证明：
- NetworkManager 在链路已经打开后再次更改 MTU；
- 内核实际进入 `stmmac_change_mtu()` 的 running-interface 分支；
- 发生 `stmmac_release()` → `__stmmac_open()` 的 MTU reopen；
- 出现 DMA reset timeout。

因此，当前没有证据把 DHCP 无报文现象与这个 MTU-reopen/RXC-stop 上游回归关联起来。

## 6. 本轮结论

### 已验证

1. 6.12.81 的精确构建源码 commit 为 `661b2d8`，构建来源证据已由仓库既有 Actions 日志归档。
2. 该源码确实没有 2026-08 的 `phylink_prepare_resume()` 修复。
3. 该源码 MTU-change 路径在 release 时会调用 `phylink_disconnect_phy()`，reopen 时重新调用 `stmmac_init_phy()`。
4. 上游补丁修复的是“release 不 disconnect PHY、保留但 suspend”的不同生命周期。
5. Panther 已有日志筛选未显示 DMA reset 错误，但日志不完整。

### 判断

**将 06232cb44bc8 从 Panther 当前 DHCP 主故障候选中降级。**

原因不是“修复已包含”，而是：
- 精确构建确实缺少该修复；
- 但该补丁所针对的关键 PHY 生命周期前提，在 Panther 精确源码的 MTU reopen 路径中并不相同；
- 当前没有 MTU reopen 或 DMA reset timeout 的实机证据；
- 正常初次 `ndo_open` 时 PHY 刚通过 `stmmac_init_phy()` 连接，上游补丁说明 `phylink_prepare_resume()` 对这种未 suspended 的正常 open 本来就不做任何事。

这条上游回归可作为未来若发现 MTU/reopen/DMA reset 事件时的条件性检查项，但不应继续占据当前 DHCP TX 无线侧报文的主调查时间。

## 7. 下一步建议：回到已有的物理发送边界证据

根据既有测试：
- Linux outgoing capture 可见；
- `stmmac_xmit()` 进入并返回 `NETDEV_TX_OK`；
- descriptor 被清理；
- Linux TX 与 MMC TX 计数在同一启动周期同步增长；
- hEX 未看到 DHCP Discover；
- iMac 持续监听期间未收到广播和单播自定义帧。

所以当前真正未跨越的边界仍然是：**MAC TX 统计/descriptor completion 之后，到 GMAC RGMII TXC/TXD / RTL8211F MDI 实际出线之前。**

下一项应继续基于 exact source commit 661b2d8，核对：
1. Rockchip GMAC 的 MAC TX enable 与 DMA channel start 是否在 link-up callback 中正确完成；
2. `rk_fix_speed()` / `rk3568_set_gmac_speed()` 的实际调用条件和 1000Mbps 配置；
3. GMAC1 `clock_in_out=input` 时 MAC TX clock/reference 的来源和 gating；
4. 与 6.1.116 相比，实际 link-up callback 是否发生顺序或条件变化。

不重复已核实一致的 descriptor 格式、OWN 位、barrier、tail pointer、queue0→DMA channel0、基础 RGMII DTS delay。也不读取 dummy-syscon debugfs registers，不使用 devmem，不改接口/PHY/设备树。

## 8. 相关报告

- [Ethernet TX 物理边界与 STMMAC 源码审计（2026-11-17）](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- [GMAC/DHCP 与 TF U-Boot 启动链调查（2026-11-17）](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)
- [RTL8211F 型号区分与 RXC/DMA reset 回归线索（2026-11-19）](./PANTHER-X2-RTL8211F-CG-VS-VD-AND-STMMAC-RXC-RESET-REGRESSION-20261119.md)

## 9. 外部参考

- Upstream commit 06232cb44bc8: https://kernel.googlesource.com/pub/scm/linux/kernel/git/libata/linux/%2B/06232cb44bc8e81adc2f1d40a01bed830b607ea2
- Patch discussion: https://lists.openwall.net/netdev/2026/08/03/147
- Exact Panther kernel source commit: https://github.com/ophub/linux-6.12.y-rockchip/commit/661b2d8bf1284556f8876d5ed5fb80c64b22f94c
