# Panther X2：6.1.116 → 6.12.81 Rockchip GMAC 时钟启用序列差异审计（2026-11-19）

## 1. 本轮范围

比较两个已锁定的源码基线：
- 正常工作的 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`（高置信度重建）
- 故障的 6.12.81-rk35xx-ophub：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`（Actions 构建来源锁定）

本轮聚焦 `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c` 的：
- `rk_gmac_clk_init()`
- `gmac_clk_enable()`
- `rk_gmac_powerup()`
- `rk_fix_speed()`
- `rk3568_set_gmac_speed()`
并结合 Panther X2 的合并 DTB/运行时 DTS 证据。

没有运行设备命令、读取 MMIO、修改寄存器、修改设备树或重启网络。

## 2. 最重要的新发现：GMAC 初始化的稳定等待从 5ms 缩短为 100–200µs

### 6.1.116

`gmac_clk_enable(true)` 的顺序：
1. `clk_bulk_prepare_enable(num_clks, clks)`，启用 bulk clocks；
2. `clk_prepare_enable(clk_phy)`；
3. 若存在 `set_clock_selection` callback，设置 clock input/output 选择；
4. `mdelay(5)`；
5. 设置 `clk_enabled=true`。

bulk clock list：
`aclk_mac`, `pclk_mac`, `pclk_xpcs`, `mac_clk_tx`, `clk_mac_speed`。
RMII 模式另加 RX/reference clocks；Panther 是 RGMII，不走 RMII 扩展列表。

### 6.12.81

`gmac_clk_enable(true)` 改为逐项启用：
1. RGMII 下不启用 RMII 专用 `mac_clk_rx` / `clk_mac_ref` / `clk_mac_refout`；
2. 逐项 `clk_prepare_enable()`：`clk_phy`（若非 ERR_PTR）、`aclk_mac`、`pclk_mac`、`mac_clk_tx`、`clk_mac_speed`、`pclk_xpcs`、`clk_xpcs_eee`；
3. 设置 clock input/output selection；
4. 调用 `rockchip_csu_disable(csu_aclk)` 和 `rockchip_csu_disable(csu_pclk)`；
5. `usleep_range(100, 200)`；
6. 设置 `clk_enabled=true`。

源码注释将 `stmmaceth`（`clk_mac`）标记为由 STMMAC core 启用，因此 Rockchip glue 继续不在此处主动启用它。

**明确变化：** 旧版在时钟使能与 clock selection 后等待 5ms；新版执行额外 CSU disable 后只等待 100–200µs，等待窗口缩短约 25–50 倍。

## 3. RGMII 配置与 PHY 供电的调用顺序

两版 `rk_gmac_powerup()` 对 Panther RGMII 的总体次序：

```
gmac_clk_enable(true)
  ├─ clocks enable
  ├─ clock selection
  └─ settle delay
set_to_rgmii(tx_delay, rx_delay)
rk_gmac_phy_power_on(true)   // enable external PHY regulator
pm_runtime_get_sync()
stmmac_dvr_probe()
```

差异：
- 6.1：clock settle delay 5ms 后，写 RGMII interface/delay GRF 配置；随后打开 PHY regulator。
- 6.12：CSU disable + 100–200µs wait 后，写 RGMII interface/delay GRF 配置；随后打开 PHY regulator。
- 两版均在 `stmmac_dvr_probe()` 前先完成上述 Rockchip glue powerup。
- Panther 设备树 reset GPIO 和 reset delay 仍由相同板级 DTS 定义；当前没有证据证明 6.12 的 reset 时序等价于 6.1 实机的完整上电时序。

这使得“clock/power-domain 稳定等待被大幅缩短”成为目前最具体、且确实位于物理 TX/RX 通路启动之前的版本差异。

## 4. 与 Panther 实际设备树时钟连接核对

Panther 合并 DTB 的 GMAC1：
- `phy-mode = "rgmii"`
- `clock_in_out = "input"`
- GMAC1 资源 `0xfe010000`
- 运行时板级节点 clock-names 包含 `stmmaceth`, `mac_clk_rx`, `mac_clk_tx`, `clk_mac_refout`, `aclk_mac`, `pclk_mac`, `clk_mac_speed`, `ptp_ref`；SoC 6.12 基础 DTS 另外列出 `pclk_xpcs`, `clk_xpcs_eee`。
- `clock_in_out=input` 在两版中均被解析为 `clock_input=true)，并打印 `clock input from PHY`。
- RGMII 模式不会走 6.12 的 RMII 专用 clock enable 分支，也不会走 SGMII/QSGMII 的 XPCS 初始化分支。

因此本次看到的 100–200µs 并不是由于 Panther 误入 RMII/SGMII 分支；它确实位于当前 RGMII clock bring-up 路径。

## 5. 其他已对照的函数：目前不是差异来源

### 5.1 `rk_fix_speed()`

- 6.1 签名：`rk_fix_speed(priv, speed)`
- 6.12 签名：`rk_fix_speed(priv, speed, mode)`
- RGMII 分支均调用 `set_rgmii_speed(bsp_priv, speed)`。
- 新增的 `mode` 参数在 Rockchip `rk_fix_speed()` 函数体中未使用。

### 5.2 `rk3568_set_gmac_speed()`

两版实现均按协商速度设置 `clk_mac_speed`：
- 10 Mbps → 2.5 MHz
- 100 Mbps → 25 MHz
- 1000 Mbps → 125 MHz

均通过 `clk_set_rate()` 设置，失败时打印错误。6.12 将 clock pointer 从数组索引改为独立字段，但目标时钟和速率映射一致。

### 5.3 `stmmac_mac_link_up()`

两版对普通 RGMII 1000Mbps 路径均：
1. 根据 phylink speed 更新 MAC speed bits；
2. 调用 Rockchip `fix_mac_speed()`；
3. 配置 duplex/flow control；
4. 写回 MAC control；
5. 调用 `stmmac_mac_set(..., true)` 打开 MAC。

6.12 额外有 SerDes-up-after-PHY-linkup 通用 flag 分支，但 Panther 当前 RGMII DTS/平台配置没有证据启用该 flag。故当前不能把这段通用分支认定为 Panther 的问题。

## 6. 错误处理差异

6.1：
- bulk clock enable 返回错误时会返回；
- `clk_prepare_enable(clk_phy)` 返回错误时会返回；
- 对 `clk_phy` 的准备启用结果有明确检查。

6.12：
- 多个独立 `clk_prepare_enable()` 的返回值没有逐项检查；
- 之后仍继续执行 CSU disable、等待，并把 `clk_enabled` 置为 true；
- clock pointer 以 `IS_ERR()` 方式判断，但 enable 结果不作为初始化失败条件。

这不是已经证明的根因，但意味着如果某个必需 clock enable 失败，6.12 glue 可能没有把错误上报到 probe/open 路径。需要结合 clock provider 实际返回值或启动日志确认；目前无现场证据证明某个 clock enable 失败。

## 7. CSU 操作的解释边界

6.12 新增：
`rk_gmac_csu_init()` 通过 `rockchip_csu_get(dev, "aclk"/"pclk")` 取得 CSU handle，随后在启用 GMAC clocks 后调用 `rockchip_csu_disable()`。

6.1 的 `dwmac-rk.c` 没有这组 CSU get/disable 操作。

目前仅凭 `dwmac-rk.c` 可以确认调用位置和目标是 aclk/pclk 两个 CSU handle；尚未在本轮中把 `rockchip_csu_disable()` 的实现与 RK3566 TRM 中对应 CSU 寄存器/时钟域逐项闭环，因此不猜测其具体硬件效果，也不把它称为“关闭 GMAC 时钟”。需要后续独立追踪 CSU provider 实现和 RK3566 TRM 后才能作更具体解释。

## 8. 当前判断

<已确认的源码事实>
1. Panther 6.1.116 与 6.12.81 的 Rockchip GMAC bring-up 等待时间发生显著变化：5ms → 100–200µs。
2. 6.12 在 clock enable 与 RGMII setup 之间新增 CSU aclk/pclk disable。
3. 6.12 对多个 clock enable 返回值不做检查；6.1 bulk enable 有统一错误检查。
4. Panther 实际使用 RGMII、clock input from PHY，故差异发生在当前有效路径。
5. 链路协商后 10/100/1000Mbps 对 `clk_mac_speed` 的映射与 MAC link-up 主流程没有发现功能差异。

<尚未验证>
1. 5ms 是否是 Panther 板级 PHY reference clock / GRF / GMAC clock domain 稳定所必需。
2. 100–200µs 是否不足以让 Panther 当前 PHY/clock topology 稳定。
3. CSU disable 的实际寄存器效果是否影响 GMAC AXI/PCLK 或 reset domain。
4. 6.12 各 clock enable 是否在实机全部成功。
5. 6.1.116 原始板级上电流程中，bootloader 是否已让相关时钟稳定，从而掩盖 Linux 侧等待时间差异。

**当前优先级：高。** 这是目前第一次找到一项发生在 Panther 确认有效 RGMII 路径上的明确 6.1→6.12 时序差异；比此前已经降级的 MTU-reopen PHY resume 线索更值得继续。

但它仍然是“强候选”，不是根因定案。不能因为时间窗口变短就直接断言 TX 波形缺失。

## 9. 下一步（继续静态，不要求用户操作）

1. 追踪 `rockchip_csu_disable()` 的实现、provider 和 RK3566 TRM 目标域，确认其是否可能影响 GMAC aclk/pclk/寄存器访问。
2. 对照两版 `rk_gmac_clk_init()` 及 SoC clock provider，确认 `clk_mac_tx`、`clk_mac_speed`、`aclk_mac`、`pclk_mac` 的实际 parent/mux/rate/enable 语义。
3. 检查 6.12 新增的 `mac_clk_tx` / `clk_mac_speed` 独立时钟获取是否可能指向同一硬件时钟对象，以及 enable/disable 次序是否安全。
4. 回读现有 UART 日志中是否已有 clock enable failure、CSU 相关输出；不重跑基础链路和 DHCP 测试。
5. 若静态证据支持，再提出一次只读验证；不擅自加回 5ms、修改驱动、操作寄存器或运行 loopback。

## 10. 相关报告

- [6.12.81 精确构建源码中的 PHY resume 修复适用性核查](./PANTHER-X2-6.12.81-STMMAC-PHY-RESUME-PATCH-APPLICABILITY-20261119.md)
- [Ethernet TX 物理边界与 STMMAC 源码审计](./PANTHER-X2-ETHERNET-TX-PHYSICAL-BOUNDARY-AND-SOURCE-AUDIT-2026-11-17.md)
- [GMAC/DHCP 与 U-Boot 启动链调查](./GMAC-DHCP-UBOOT-INVESTIGATION-2026-11-17.md)

## 11. 源码链接

- 6.1.116 `dwmac-rk.c`: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.116 `stmmac_main.c`: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.12.81 `dwmac-rk.c`: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.12.81 `stmmac_main.c`: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
