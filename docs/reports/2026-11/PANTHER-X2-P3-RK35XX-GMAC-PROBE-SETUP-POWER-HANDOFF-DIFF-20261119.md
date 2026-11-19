# Panther X2：6.1.174-rk35xx GMAC probe/setup/PHY 电源交接差异审计（2026-11-19）

## 1. 基线与范围

本轮按当前高置信度源码候选比较：
- 正常 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 最早异常 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633
- 持续异常 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

本轮只审查 dwmac-rk.c 的 probe/setup/powerup/powerdown/suspend/resume 与 Panther RGMII 条件分支。没有访问设备或做任何实机操作。

## 2. rk_gmac_probe() 差异及 Panther 适用性

6.1.116：
- stmmac_probe_config_dt()
- 设置 has_gmac fallback、fix_mac_speed
- setup → clock init → powerup → stmmac_dvr_probe

6.1.174-rk35xx c2f148d：
- 在上述流程前增加 plat_dat->sph_disable = true
- 增加 get_eth_addr = rk_get_eth_addr
- 增加 integrated_phy_power = rk_integrated_phy_power
- 增加 rk_gmac_csu_init()
- stmmac_dvr_probe 成功后创建 loopback sysfs

6.12.81：
- devm_stmmac_probe_config_dt() 取代 stmmac_probe_config_dt()
- 用 STMMAC_FLAG_SPH_DISABLE 表达与 6.1.174 plat_dat->sph_disable 相同的禁用语义
- 保留 get_eth_addr、integrated_phy_power、CSU init、loopback sysfs。

### 2.1 SPH disable 不命中 TX

对 c2f148d 的 stmmac_main.c 检查 plat_dat->sph_disable / priv->sph 的全部使用：
- 控制 DMA RX split-header 是否启用；
- 控制 RX second buffer page 分配；
- 控制 RX descriptor second address；
- 控制 RX header/frame length 解析；
- 控制 RX 侧 GRO 能力暴露。

没有进入 stmmac_xmit / TSO TX descriptor 提交路径。故 6.1.174 新增 SPH disable 是有效平台差异，但不能解释当前 TX frame 不出线。

### 2.2 get_eth_addr 已有专项审计，不重复

c2f148d 与 6.12.81 的 rk_get_eth_addr() 逻辑相同：若原 MAC 有效则直接返回；无效才尝试 rk_vendor_read，失败则随机生成并写回。该方向已有专项报告及实机 MAC/网络对照，本轮不重复，也不把它当作新发现。

### 2.3 integrated PHY callback 不命中 Panther

Panther 的 RTL8211F 是外接 PHY，runtime DTS 没有 phy-is-integrated 属性，rk_gmac_setup() 得到 integrated_phy=false。因此：
- integrated_phy_power callback 不执行有效 PHY 操作；
- integrated PHY 的 reset、BGS OTP/NVMEM 读取分支不命中；
- 6.1.116 powerup/powerdown 中额外的 integrated PHY 电源动作也不命中。

### 2.4 CSU 与 loopback sysfs

- c2f148d / 6.12.81 增加 CSU init；Panther 没有对应 CSU phandle，已完成的专项审计确认 NULL/no-op，不重复。
- loopback sysfs 只增加管理接口，不在普通 TX path 自动运行。

## 3. rk_gmac_setup() 差异

### 3.1 TX/RX delay 默认值

6.1.116 在设备树未提供 tx_delay/rx_delay 时分别回退 0x30 / 0x10；c2f148d 与 6.12.81 回退 -1。
Panther runtime DTS 明确提供 tx_delay=0x30、rx_delay=0x10，因此这项默认值差异不命中 Panther 当前启动路径。

### 3.2 GRF / PHP-GRF

- c2f148d 对 rockchip,grf lookup 未立即检查错误；6.12.81 增加了明确错误检查。
- c2f148d 使用 rockchip,php_grf 字符串，而 6.1.116 使用 rockchip,php-grf；但 RK3568 Panther 选用的 rk3568_ops 不要求 php_grf，也不访问该属性。
- Panther DTS 有有效 rockchip,grf phandle，且现有启动日志显示 RGMII 初始化和正常 1Gbps link；不能把该字符串差异推断成当前问题。

### 3.3 BGS OTP

c2f148d 在 integrated_phy 分支新增 BGS increment / OTP NVMEM 读取。Panther integrated_phy=false，不执行。

## 4. PHY regulator 与 runtime-PM 交接

三个版本的 rk_gmac_phy_power_on() 函数体相同：
- 调用 regulator_enable/disable；
- 失败时打印错误；
- 最终始终 return 0，不把 regulator 错误向上传播。

三个版本的普通外接 PHY powerup 主流程均为：
1. gmac_clk_enable(true)
2. 设置 RGMII interface/delay
3. rk_gmac_phy_power_on(true)
4. pm_runtime_get_sync(dev)
5. stmmac_dvr_probe()

6.1.116 额外的 integrated_phy_powerup 仅在 integrated_phy=true 时执行；不适用于 Panther。

三个版本 rk_gmac_suspend()/rk_gmac_resume() 的外接 PHY普通路径相同：先 stmmac_suspend/resume；非 wakeup 情况执行 powerdown/powerup。c2f148d 与 6.12.81 的 rk_gmac_powerdown() 相比 6.1.116 少了 integrated PHY 专用 powerdown，但 Panther integrated_phy=false，不命中。

pm_runtime_get_sync() 的返回值在这几版的 Rockchip powerup 中都没有被检查；这是共有的错误处理弱点，不是 6.1.174 新增差异。当前没有证据表明它在 Panther 上失败。

## 5. 本轮结论

### 已排除为 Panther TX 根因候选
1. SPH disable：RX split-header/GRO 路径，不进入普通 TX 提交。
2. integrated PHY power callback / reset / BGS OTP：外接 RTL8211F，不命中。
3. TX/RX delay 默认值：Panther DTS 有明确值。
4. PHP-GRF 属性拼写差异：RK3568 Panther ops 不使用 PHP-GRF。
5. regulator 返回值不传播、pm_runtime_get_sync 返回值不检查：三个版本共有，不是本次回归引入。
6. CSU：Panther NULL/no-op；loopback sysfs 不自动影响正常数据路径。

### 已确认但不是根因结论
- c2f148d / 6.12.81 的 probe 增加平台标志、MAC address callback、integrated PHY callback、CSU 和 sysfs 管理功能；在 Panther 外接 RGMII 的普通 TX 路径中，没有找到这些新增项能解释当前物理 TX 不可见的直接机制。

## 6. P3 下一步

当前 c2f148d 来源已通过 run #296 / release asset 时间关联提升为高置信度候选，但实际 workflow_dispatch inputs/source_hash 仍未直接取得。

此前 TX core 审计有部分比较使用普通 stable 6.1.174，而非 c2f148d。下一步应只针对这个源码归属纠正，检查 c2f148d 的 STMMAC core：
- stmmac_xmit / TSO TX descriptor 提交
- TX clean/reclaim
- DMA engine init / channel start
- open / hw_setup / link-up handoff

只对比已知正常 6.1.116 与 c2f148d，并将已有 6.12.81 结果作为第三端交叉核对。重点找 6.1.174-rk35xx 与 6.12.81-rk35xx 共有、但 6.1.116 没有的有效 TX 路径变化。不要重复已完成的普通 descriptor OWN/tail pointer/barrier、DMA register helper、queue parser 和物理 TX 边界结论；如果核心函数无法确认存在差异，应明确关闭该项。

不操作 Panther、不读写寄存器、不发包、不抓包、不制作补丁。

## 7. 参考

- 6.1.116 dwmac-rk.c: https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 RK35xx candidate dwmac-rk.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
- 6.1.174 RK35xx candidate stmmac_main.c: https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c
- 6.12.81 RK35xx dwmac-rk.c: https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c
