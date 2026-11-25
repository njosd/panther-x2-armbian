# Panther X2 B2-0 方向三 D3-2：STMMAC MDIO / PHY attach 四版本差异（2026-11-25）

## 1. 范围与复用原则

本项只审 STMMAC common 层的 MDIO bus 解析/注册、PHY node/fwnode 传递、phylink attach 与相关初始化顺序。Rockchip dwmac-rk glue 内部、Realtek PHY driver 内部、PHY 寄存器厂商语义和设备侧 MDIO 实测不在本项重复展开。

固定源码端点：
- 6.1.65：unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc（高置信度候选）。
- 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e。
- 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（原始 Actions job source_hash 已验证）。
- 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c。

复用而不重做：
- PANTHER-X2-STMMAC-6.1.124-MDIO-REFACTOR-PANTHER-DT-BEHAVIOR-EQUIVALENCE-20261119.md：已证明 6.1.116 与普通 stable 6.1.174 的旧/新 MDIO parser 对 Panther DTS 的最终节点和 needs_reset 结果等价。
- PANTHER-X2-P3-INIT-CALLCHAIN-MDIO-PHY-ORDER-20261119.md：已整理 6.1.116/旧 stable 端点的 probe、MDIO register、PHY attach 顺序，并纠正其 stable 6.1.174 不是实际 rk35xx 故障源码。
- PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md：已解码 6.1.116 中四次 MDIO 写入的公开来源链、RTL8211F PHYCR2 语义、地址 0 广播语义及证据不足；本项只把该结果扩展到四个精确源码端点，不重做寄存器解释。

## 2. Panther DTS 输入：四版本实际命中同一分支

已核对 Panther board DTS 与 RK356x SoC DTSI：
- board alias ethernet0 指向 gmac1；GMAC 节点 enabled。
- phy-mode = rgmii；不是 fixed-link。
- phy-handle 指向 MDIO 子节点中的 ethernet-phy@0，reg = 0。
- GMAC 子节点包含 compatible = snps,dwmac-mdio。
- GMAC 设备树起点是 ethernet@fe010000，兼容 rockchip,rk3568-gmac / snps,dwmac-4.20a。

因此四个版本均应以真实 MDIO bus + 外接 PHY 的路径解析；不是 legacy 无 phy-handle 扫描，也不是 fixed-link 分支。

## 3. MDIO node / bus_data 解析对照

| 行为 | 6.1.65 / 6.1.116 | 6.1.174-rk35xx / 6.12.81-rk35xx | Panther 最终结果 |
|---|---|---|---|
| PHY node | of_parse_phandle(phy-handle) | 同样先解析 phy_node | 同一 ethernet-phy@0 |
| MDIO node | stmmac_dt_phy() 扫描 snps,dwmac-mdio 子节点 | stmmac_of_get_mdio() 扫描同一 compatible 子节点 | 同一 mdio1 |
| bus_data 分配 | 非 fixed-link 即分配；找到 mdio node 后强制 mdio=true | mdio_node 存在即分配；legacy_mdio 另用于无 phy node 的旧 DTS | 均分配 |
| needs_reset | true | true | 均为 true |
| bus_id | ethernet alias，fallback 0 | 新增无 alias 时的 static/highest-alias fallback | ethernet0 存在，均为 0 |
| phylink fwnode | phylink_node = GMAC node | 6.12 改为 port_node = of_fwnode_handle(GMAC node) | 最终都以 GMAC node 为起点 |

结论：旧 parser 与新 parser 在 Panther DTS 输入上仍保持 MDIO node、PHY node、bus_data、needs_reset 和 bus id 的关键行为等价。该结论与既有 6.1.124 专项报告一致；本次把实际 6.1.174 c2f148d 与 6.12.81 精确端点纳入确认。

## 4. 重要四版本差异：JL2xx1/PHYCR2 四次 MDIO 写入

本轮对四个精确版本的 stmmac_mdio.c 直接检索并检查 stmmac_mdio_register()：

| 版本 | 四次 MDIO 写入序列 | 源码行 |
|---|---|---:|
| 6.1.65 候选 | 存在 | 507–510 |
| 6.1.116 | 存在 | 511–514 |
| 6.1.174-rk35xx c2f148d | 不存在 | 全文件未检出对应 magic values |
| 6.12.81-rk35xx | 不存在 | 全文件未检出对应 magic values |

6.1.65/6.1.116 的序列为：

1. MDIO address 0，写 reg 31 = 2627（切换到 page 0xA43）；
2. MDIO address 0，写 reg 25 = 0x1801；
3. MDIO address 0，写 reg 31 = 0（回到 page 0）；
4. MDIO address 0，写 reg 0 = 0x8000（BMCR software reset）。

在 6.1.65/6.1.116 中，这组写入位于 of_mdiobus_register() 成功之后、检查 phy_node/mdio_node 并跳过后续扫描之前；Panther 非 fixed-link，且 mdio_bus_data 已分配，因此实际会走到该位置。6.1.174 c2f148d 与 6.12.81 的 stmmac_mdio_register() 中没有这组写入。

该差异的证据意义：
- 这是四版本间真实的 STMMAC MDIO 初始化行为差异；6.1.65/6.1.116 两条黄金基线存在，6.1.174/6.12.81 两条故障基线缺失。
- 它会改变 PHY 上电/MDIO 初始化阶段的寄存器配置与 reset 序列；目标 PHY 是 RTL8211F，地址 0 的广播语义及 PHYCR2 位解释已在 P1 报告详细审计。
- P1 报告指出 0x1801 包含厂商数据手册标记为 Reserved 的 bit 组合，且没有证据证明该值在 RTL8211F-CG 上具备完整厂商保证。因此“黄金版本存在该 workaround”不等于“该 workaround 一定正确”，也不能据此建议直接恢复写入。
- 目前没有 Panther 运行时 PHYCR2 回读、reset 后状态、CLKOUT/RXC 波形或两种初始化策略的对照实测。本差异是高优先级待关联项，不是根因结论。

## 5. 其他 MDIO / PHY attach 差异

### 5.1 of_mdiobus_register() 的 -ENODEV 处理

6.1.65 的 stmmac_mdio_register() 对 of_mdiobus_register() 非零返回直接进入失败清理；6.1.116/6.1.174/6.12.81 增加 -ENODEV 作为“MDIO bus disabled”处理并返回非错误路径。Panther 存在 mdio1 子节点和 PHY 子节点，不应命中 disabled/no-node 分支；当前无证据认为该变化改变 Panther 实际行为。

### 5.2 6.12 MDIO C22/C45 API 重构

6.12 将通用 MDIO read/write 函数分为 C22/C45 接口，并增加 PCS mask 处理。Panther 使用 RK3568 DWMAC4.20a + 外接 RTL8211F RGMII，属于常规 Clause 22 PHY 路径；XGMAC2 专用分支不适用。PCS mask 是否非零及更细的 MDIO API 差异不作为本轮根因结论，后续如需可在相应 PHY/PCS 子项按真实条件补证。

### 5.3 mac_requires_rxc 与 PHY resume/attach

- 6.1.65/6.1.116 的 stmmac_phy_setup() 未设置 mac_requires_rxc。
- 6.1.174 c2f148d 在 stmmac_phy_setup()（stmmac_main.c 约第 1214 行）设置 mac_requires_rxc = true；同一源码在 resume 路径调用 phylink_prepare_resume()（约第 7906 行）。该 phylink 版本使用此 flag 在 PHY suspended 时提前 resume PHY，以满足 MAC 初始化需要 RXC 的平台条件。
- 6.12.81 的 stmmac_phy_setup()（约第 1237 行）同样设置 mac_requires_rxc = true；但不再调用 phylink_prepare_resume()。6.12 phylink 改为在 PHY attach 时把 PHY_F_RXC_ALWAYS_ON 传给 PHY core，PCS pre-init 也可读取该 flag。

Panther 为 RGMII 外接 RTL8211F，RXC 是该接口数据路径的重要时钟，但这项标志主要影响 PHY suspend/resume 与 RXC always-on 管理；不能直接等同于普通初次启动时的 TX 数据路径差异。6.1.174 与 6.12 的实现机制也不完全相同。没有运行时 suspend/resume 记录或 RXC 波形，不认定其触发历史故障。

### 5.4 integrated PHY callback

6.1.174/6.12 的 stmmac_init_phy() 增加 integrated_phy_power callback 调用；Panther 使用外接 RTL8211F，Rockchip 平台数据的 integrated_phy 分支不适用。该差异降级，不扩大审计。

## 6. 初始化调用顺序与实际路径

对 Panther 的静态路径归纳如下：

1. stmmac_probe_config_dt() 解析 MAC node，获取 phy_node、mdio_node、bus_id、phy_interface 等平台数据。
2. Rockchip platform probe 完成其平台资源和供电/时钟准备（glue 内部不在本项重审）。
3. stmmac_dvr_probe() 注册 netdev 前后按既有驱动顺序执行 stmmac_mdio_register()；MDIO bus 由 of_mdiobus_register() 同步解析子 PHY 节点。
4. stmmac_phy_setup() 创建 phylink，fwnode 指向 GMAC node；6.12 使用等价的 port_node。
5. __stmmac_open()/PHY attach 路径通过 fwnode_get_phy_node() 取得 phy-handle 指向的 PHY，再连接 phylink。

6.1.65/6.1.116 的四次 MDIO 写入发生在步骤 3 的 bus register 后、PHY node early-exit 前；6.1.174/6.12 不存在该写入段。

## 7. 本项结论与状态

### 已验证
- 四版本 Panther DTS 输入均命中真实 MDIO bus + phy-handle + 外接 PHY 的分支；不是 fixed-link 或 legacy scan-only。
- 旧/新 MDIO parser 在 Panther 上产生相同的 mdio1、PHY address 0、bus_data、needs_reset 和 bus_id 结果。
- 四次 PHYCR2/BMCR MDIO 写入存在于 6.1.65/6.1.116，缺失于实际 6.1.174-rk35xx c2f148d 和 6.12.81 源码；这项差异此前 P1 已完成寄存器语义研究，本项完成了真实四版本 source endpoint 核对。
- 6.1.174/6.12 新增 mac_requires_rxc 语义，影响 PHY RXC 管理/resume/attach 条件；不直接等同普通 DHCP TX 回归。
- Panther 无 fixed-link、无 eth_lpi/sfty IRQ 等条件，多个通用分支差异不命中。

### 未验证
- 四次 MDIO 写入在 6.1.65 原始 Image 的精确构建源码身份仍为高置信度候选，不是二进制级 commit 绑定。
- 没有两种初始化策略的现场 PHYCR2/BMCR 回读和 CLKOUT/RXC 波形证据。
- 没有历史日志证明 mac_requires_rxc 的 suspend/resume 分支在故障窗口实际执行。

**D3-2 状态：静态源码审计结项。** 已完成四版本 MDIO/PHY attach 路径和 Panther 分支适用性对照。最重要的新差异是黄金版本包含、故障版本缺失的四次 PHY 广播写入；它可能影响外接 RTL8211F 的启动配置，但写入值含 Reserved bit 且缺少现场证据，必须保持候选，不得直接认定根因或提出恢复补丁。按顺序进入 D3-3 DWMAC4 DMA core initialization。

## 8. 来源与关联报告

- [6.1.65 stmmac_mdio.c](https://github.com/unifreq/linux-6.1.y/blob/4428b96f34a16e9a0beeed1dcb0ae3d4326145fc/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c)
- [6.1.116 stmmac_mdio.c](https://github.com/unifreq/linux-6.1.y/blob/5eb841b59d6ead6e264163785a634e78f0253c8e/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c)
- [6.1.174-rk35xx stmmac_mdio.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c)
- [6.12.81-rk35xx stmmac_mdio.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c)
- [6.1.174-rk35xx stmmac_main.c](https://github.com/ophub/linux-6.1.y-rockchip/blob/c2f148dece4b67ebd30aefad1bdd1990f41e5633/drivers/net/ethernet/stmicro/stmmac/stmmac_main.c)
- [6.12.81-rk35xx phylink.c](https://github.com/ophub/linux-6.12.y-rockchip/blob/661b2d8bf1284556f8876d5ed5fb80c64b22f94c/drivers/net/phy/phylink.c)
- 复用：PANTHER-X2-P1-MDIO-WRITES-CLOSEOUT-20261119.md
- 复用：PANTHER-X2-STMMAC-6.1.124-MDIO-REFACTOR-PANTHER-DT-BEHAVIOR-EQUIVALENCE-20261119.md
- 复用：PANTHER-X2-P3-INIT-CALLCHAIN-MDIO-PHY-ORDER-20261119.md