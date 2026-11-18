# 6.1.116 RTL8211F PHY driver binding 与 PHYCR2 保留行为审计（2026-11-18）

## 1. 本轮目标

承接 JL2xx1 workaround 与 RTL8211F 寄存器语义审计，核实两个问题：

1. 6.1.116 实机是否确实绑定 Linux Realtek RTL8211F PHY driver；
2. 该驱动在 probe/config_init 中是否会覆盖 116 workaround 写入 PHYCR2 的 bits[13:12]、bit11。

本轮先查仓库已归档的实机采集文本，再对照 6.1.116、6.1.174、6.12.81 三个源码版本。未要求用户重跑命令，未进行实机测试，未修改设备。

## 2. 6.1.116 实机绑定信息：已由历史采集记录确认

仓库文件：
`evidence/network/panther-eth-baseline-redacted.txt`

原始 dmesg 记录（脱敏文本）：

```
[   20.968267] rk_gmac-dwmac fe010000.ethernet eth0:
PHY [stmmac-0:00] driver [RTL8211F Gigabit Ethernet] (irq=POLL)
```

同一采集记录还保留：
- PHY 节点路径：`/sys/firmware/devicetree/base/ethernet@fe010000/mdio/ethernet-phy@0`
- PHY 设备路径：`/sys/devices/platform/fe010000.ethernet/mdio_bus/stmmac-0/stmmac-0:00`

另一个仓库测试日志明确记录 6.1.116 PHY ID 为 `0x001cc916`。

因此，6.1.116 实机确实绑定了内核 Realtek 驱动中的 `RTL8211F Gigabit Ethernet` 项目，不是 generic PHY fallback。PHY 地址为 0。

## 3. 三个内核版本的 RTL8211F 驱动对照

检查文件：
- 6.1.116：`drivers/net/phy/realtek.c`
- 6.1.174：`drivers/net/phy/realtek.c`
- 6.12.81：`drivers/net/phy/realtek.c`

三版的关键行为一致：

### 3.1 rtl821x_probe()

RTL8211F PHY driver probe 会读取：
- page 0xa43 / reg 0x18（PHYCR1）；
- page 0xa43 / reg 0x19（PHYCR2）。

对 PHYCR2，驱动只把 bit 0 保存到 `priv->phycr2`：

```c
priv->phycr2 = ret & RTL8211F_CLKOUT_EN;
```

它不会把 bits[13:12] 或 bit 11 保存到私有状态。

### 3.2 rtl8211f_config_init()

在 RGMII 模式下，驱动配置 PHYCR1 和 page 0xd08 的 TX/RX delay。随后对 PHYCR2 执行：

```c
ret = phy_modify_paged(phydev, 0xa43, RTL8211F_PHYCR2,
                       RTL8211F_CLKOUT_EN, priv->phycr2);
```

该操作的 mask 只有 `RTL8211F_CLKOUT_EN = BIT(0)`。

因此它只修改 bit 0，保留 PHYCR2 的其他位。它不会把 bits[13:12] 或 bit 11 清零，也不会恢复这几个字段的原值。

之后驱动调用 `genphy_soft_reset()`。

6.1.116 和 6.1.174 在这一关键代码路径基本一致；6.12.81 增加了其他 PHY clock/LED 处理，但 PHYCR2 仍然只 mask bit 0，随后执行 soft reset。没有发现 6.12 对这几个字段提供清理/恢复逻辑。

## 4. 与 116 workaround 的时序合并

结合前两份报告已确认的执行顺序：

```
MDIO bus 注册
  └─ 扫描 PHY / 创建 MDIO PHY device
      └─ RTL8211F driver probe
          └─ 读取 PHYCR2，仅保存 bit 0
  └─ of_mdiobus_register() 返回
      └─ 116 stmmac workaround:
          ├─ page 2627 / reg 25 = 0x1801
          ├─ page 0
          └─ BMCR = 0x8000（PHY soft reset）
  ...
接口启动 / PHY config_init
  └─ PHYCR2 仅修改 bit 0
      └─ genphy_soft_reset()
```

这里有一个很重要的时序特点：

- RTL8211F driver probe 在 MDIO 扫描/注册过程中完成；
- 116 workaround 位于 `of_mdiobus_register()` 成功返回之后；
- 因此 probe 读取 PHYCR2 的时间早于 workaround 写入；
- config_init 随后使用 probe 时缓存的 bit 0，并且只更新 bit 0；
- 其余 PHYCR2 字段不受 config_init 的 mask 影响。

因此不能认为 RTL8211F 标准驱动会自动覆盖/清除 116 workaround 写入的 bits[13:12]、bit11。按源码逻辑，它们会被保留到后续寄存器操作之后；是否在 PHY 内部 reset/电源状态转换中保持，则需由芯片行为或实机读回确认。

## 5. 三版行为对照

| 项目 | 6.1.116 | 6.1.174 | 6.12.81 |
|---|---|---|---|
| Panther PHY driver 绑定证据 | 历史实机 dmesg 确认 | 本轮无独立 6.1.174 实机证据 | 历史实机 dmesg 确认 |
| RTL8211F driver probe 读取 PHYCR2 | 是 | 是 | 是 |
| priv 缓存 PHYCR2 bit 0 | 是 | 是 | 是 |
| config_init 修改 PHYCR2 bit 0 | 是 | 是 | 是 |
| config_init 清理 bits[13:12]/bit11 | 否 | 否 | 否 |
| stmmac JL2xx1 workaround 四次写入 | 有 | 无 | 无 |

## 6. 本轮结论

### 已确认

1. 6.1.116 Panther 实机确实绑定 RTL8211F Linux PHY driver，PHY 地址 0；证据来自仓库原始脱敏 dmesg。
2. 116 workaround 在 RTL8211F driver probe 之后写入 PHYCR2。
3. 三个内核版本的 RTL8211F config_init 都只修改 PHYCR2 bit 0，不清除 bits[13:12] 或 bit 11。
4. 因而不能用“RTL8211F 标准驱动后续会覆盖这组 JL2xx1 写入”来解释 116 的行为。

### 尚未确认

1. RTL8211F 对 0x1801 中 reserved 编码的实际硅片响应；
2. PHYCR2 相关位在 workaround 的 BMCR reset 和后续 config_init soft reset 后是否保持；
3. 这组设置对 CLKOUT、电气时序及 GMAC RX/TX 的实际影响；
4. 这组设置与 116 正常、174/6.12 异常之间是否存在因果关系。

### 调查方向修正

目前最准确的模型是：

> 6.1.116 实机使用 RTL8211F。通用 stmmac workaround 在 PHY driver probe 之后，将 JL2xx1 专用的 0x1801 写入 RTL8211F 的 PHYCR2；RTL8211F 标准驱动后续只修改 PHYCR2 bit 0，不会清除该写入的其他位。6.1.174/6.12 移除了这段写入，因此三版的 PHYCR2 可能处于不同状态。

这是一个真实、可复核的版本行为差异，但仍不是已证明的网络故障根因。

## 7. 下一步

优先查明 RTL8211F datasheet 对 PHYCR2 reserved bits、CLKOUT 输出及 reset persistence 的正式约束，并回看 6.1.116 归档中是否有 PHYCR2 读回值（现有归档摘要未显示有专门的 PHY 寄存器 dump）。如果没有读回，下一项实机验证应严格限定为只读 PHY page 0xa43/reg 0x19，不改寄存器、不触发 reset、不重启接口；执行前需用户明确授权。
