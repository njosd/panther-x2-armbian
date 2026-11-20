# Panther X2：P3 STMMAC link-up / probe handoff 收尾（2026-11-20）

## 1. 范围与源码端点

完成 P3 最后遗留的精确函数核对。全程只读，没有操作 Panther、读取/写入寄存器、发包、抓包、修改内核或制作补丁。

- 正常 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
- 最早异常 6.1.174-rk35xx 高置信度候选：`ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- 持续异常 6.12.81-rk35xx：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`

## 2. stmmac_mac_link_up()

### 2.1 6.1.116 → 6.1.174-rk35xx

主要函数体一致。新增的有效代码是在 MAC link-up 配置前：

```c
if (priv->plat->serdes_up_after_phy_linkup &&
    priv->plat->serdes_powerup)
        priv->plat->serdes_powerup(priv->dev, priv->plat->bsp_priv);
```

这是 SerDes 在 PHY link-up 后上电的条件分支。Panther X2 使用 RK3566 GMAC + 外接 RTL8211F-CG 的 RGMII，不使用 SerDes；当前 Panther platform data 没有证据表明设置 `serdes_up_after_phy_linkup` 或提供该 callback。此新增分支不命中 Panther 的 RGMII 链路。

### 2.2 6.1.174-rk35xx → 6.12.81-rk35xx

- SerDes 条件由旧布尔字段改为 `STMMAC_FLAG_SERDES_UP_AFTER_PHY_LINKUP` flags，语义相同。
- `fix_mac_speed` callback 在 6.12 增加 `mode` 参数。
- 对照三个版本的 Rockchip `rk_fix_speed()`：6.1.116 与 6.1.174 接收 `speed`；6.12 另接收 `mode`，但函数体没有读取或使用 `mode`。RGMII 分支仍调用 `ops->set_rgmii_speed(bsp_priv, speed)`。
- 其余 MAC speed、duplex、pause/flow-control、MAC enable、EEE 和 FPE link-up 主体没有发现能解释 Panther 普通 TX 帧不出线的版本差异。

**结论：** 未发现命中 Panther RGMII 的 link-up handoff 新行为。

## 3. stmmac_dvr_probe()

### 3.1 6.1.116 → 6.1.174-rk35xx

精确函数差异主要为：
- 读取 DT `label` 并设置 netdev 名称；
- 初始化 per-queue xstats 同步统计；
- 移除旧版 `lpi_irq` 资源赋值；
- 新增 `LED_FIX` 宏及 PHY LED fixup 注册段。

前几项不改变 TX DMA/MAC/RGMII 发送路径。LED fixup 需单独记录如下。

### 3.2 LED_FIX 是实际启用的代码，不是未定义条件

c2f148d 的 `stmmac_main.c` 明确写有：

```c
#define LED_FIX 1
```

所以其后 `#ifdef LED_FIX` 分支在该源码候选中编译启用。

RTL8211F fixup：
- 注册 UID：`0x001cc916`，mask `0xffffffff`；
- Panther 已归档的 6.1.116 运行日志记录 RTL8211F PHY ID 为 `0x001cc916`；
- fixup 函数名为 `phy_rtl8211f_led_fixup`，注释明确为 LED1/LED2 配置；
- 函数先选择 page `0xd04`，写 Reg `0x10 = 0xc160`、Reg `0x11 = 0x0008`，再切回 page 0；
- 同一段还为 RTL8211E、RTL8201F、DP83848、RK631/YT8521 注册相应 fixup。

注册时机在 `register_netdev(ndev)` 成功之后、`stmmac_dvr_probe()` 返回之前。随后 PHY attach 的 `phy_attach_direct()` 会调用 `phy_init_hw()`；而该内核 `phy_init_hw()` 的执行顺序是先 `phy_scan_fixups()`，再调用 PHY driver 的 `config_init()`。因此，在设备注册完成后正常打开网卡并 attach 匹配的 RTL8211F 时，该 fixup 有实际执行路径，不是永远不会触发的死代码。

### 3.3 对数据通路的影响判断

- 代码自身把该 fixup 明确命名为 LED fixup，注释也只描述 LED1/LED2 颜色/状态配置。
- 写入对象是 RTL8211F 扩展页 D04 的 LED 相关配置寄存器；没有看到它写 BMCR、PHYCR1/PHYCR2、RGMII delay、TX/RX analog、MAC/DMA 或链路协商寄存器。
- Realtek `rtl8211f_config_init()` 也可能根据 DT `realtek,led-data` 再配置同一 LED 页；fixup 在 PHY `config_init()` 前执行。是否存在该 DT 属性应以实际运行时 FDT 为准，本报告不推定其存在或缺失。
- 当前没有厂商原始资料或实测证据证明这两项 LED 寄存器写入会改变 RGMII TX 数据路径。

**结论：** 这是 6.1.174-rk35xx 一个真实、编译启用且针对 RTL8211F PHY ID 的版本专属 MDIO 行为变化，不能遗漏；但现有证据把它指向 LED 配置，未发现它改变普通 TX 数据通道的机制。它在 6.12.81 候选中没有同样的 stmmac 注册代码，因此不是 6.1.174 与 6.12.81 两个异常版本共同具备的故障原因。记录为版本专属、非当前 TX 根因候选，不进行实机试验。

## 4. 6.1.174 → 6.12.81 的 probe 变化

6.12 的 `stmmac_dvr_probe()` 继续演进，包含：
- 新的 stats 结构/pcpu stats；
- flags 形式的 TSO/SPH 配置；
- XDP/XSK metadata 和 features；
- PCS setup/cleanup 调整；
- MDIO registration 及错误路径重构；
- FPE verify 初始化等。

这些变化中，尚未发现一个在 Panther 外接 RGMII、普通 queue 0 DHCP/UDP 广播发送时必然命中、且能解释 MAC 软件统计完成但外部接收端完全不可见的机制。PCS 相关重构不等于 Panther 一定使用 PCS；本机平台是否走该分支应按 RGMII/硬件能力条件判断，不能只凭代码存在就认定命中。

## 5. P3 最终结论

P3 的限定目标是：查找从正常 6.1.116 到异常 6.1.174-rk35xx、并在持续异常 6.12.81-rk35xx 中继续存在的有效 GMAC/STMMAC TX 路径变化。

已经完成：
- Rockchip GMAC clock/probe/setup/PHY power handoff；
- SPH、integrated PHY、CSU、delay、GRF/PHP-GRF 等 Panther 适用性核查；
- 普通 `stmmac_xmit()`、`stmmac_tx_clean()`、`stmmac_hw_setup()`；
- TSO 与 SerDes 分支适用性核查；
- `stmmac_mac_link_up()`；
- `stmmac_dvr_probe()` 及 PHY LED fixup 注册/执行顺序。

结论：
1. 没有发现 6.1.174-rk35xx 与 6.12.81-rk35xx 共有、6.1.116 不存在、且命中 Panther 普通 RGMII TX 路径的有效 STMMAC core 差异。
2. 发现 6.1.174-rk35xx 独有的 RTL8211F LED fixup 注册及 MDIO 写入；它确实可在 PHY 初始化时执行，但现有源码语义指向 LED 控制，不足以解释 TX 数据不出线，也不是 6.12 的共同差异。
3. 先前误报的 TX callback queue 参数变化已撤销，不纳入结论。
4. 普通 TX descriptor OWN、barrier、tail pointer、DMA helper、queue0→DMA channel0 等已完成专项核对，不重复。
5. 当前源码候选的比较不能代替 6.1.174/6.12.81 发布二进制的精确 build inputs 证明；该构建来源不确定性单独保留，不无限扩展本 P3 子项。

**P3 正式关闭：未找到可解释当前 TX 物理出线故障的有效共同软件差异。** 这不是 GMAC 根因已解决，也不证明 MAC/RGMII/PHY 任何物理段正常。

## 6. 下一阶段

按既定路线转 P4：只读静态审计 pinctrl 首 pin 错误处理。硬件审计仍排最后；不操作 Panther，不读取危险 dummy-syscon debugfs，不写寄存器，不发包、不抓包，不制作补丁。

## 7. 源码参考

- [6.1.116 stmmac_main.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.1.174-rk35xx phy_device.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/phy/phy_device.c)
- [6.1.174-rk35xx realtek.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/phy/realtek.c)
- [6.12.81-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx dwmac-rk.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c)
