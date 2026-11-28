# Panther X2 项目 A — R7-A Platform Probe 准入静态审计（2026-11-28）

## 1. 结论

**R7-A 存在一个可控的 PREPARE-ONLY 候选边界；当前仅通过静态设计审查，不构成实机启动授权。**

建议以已通过 G4-P0 runtime 为唯一输入，下一候选只改变：
- Kconfig：加入 STMMAC / Rockchip DWMAC platform 所需最小闭包；
- DTB：仅将 GMAC1 父节点 `/ethernet@fe010000/status` 从 disabled 改为 okay；
- 保持 MDIO 子节点 disabled、RTL8211F PHY 子节点 disabled；
- IO-domain child 继续 okay，但全部九个 `*-supply` 属性继续缺失；
- 继续使用 RAM initramfs、SU08G、现有 U-Boot/bootargs，不启用接口、不发送报文。

这样可以验证 GMAC platform probe、STMMAC netdev 注册以及 PHY supply consumer 的请求/使能，同时把 MDIO、PHY reset、RTL8211F probe、DMA open 和真实 TX 留到后续门。

## 2. 输入基线与禁止变更项

固定输入：
- Kernel：Linux 6.18.63+
- Source：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- G4-P0 Image SHA256：`b34b8faaa34bcb843d82f11423489b434c1e2f329fedab1d81754fd192723090`
- G4-P0 DTB SHA256：`c967aff4bb99748828fdf083a8e1701b915966e47c6828375399bef5e0048ff8`
- G4-P0 config SHA256：`c990c913b283a7042a81be12369886e1faa95bbf5b2cc031fd9e1155a4357be2`
- 已通过 G4-P0 RAM runtime 与 corrected collector package：Actions run `46120998151`。

本门禁止：
- 不启用 MDIO child、PHY address 0 node 或 `CONFIG_REALTEK_PHY`；
- 不执行 `ip link set up`、PHY reset、MDIO 读写、PHY 寄存器配置；
- 不读写 PMUGRF VSEL，不恢复九路 IO-domain supplies；
- 不加入 IPv4、ARP、ICMP、DHCP、DNS、TCP/UDP 工具或测试；
- 不触碰 SN64G 或 eMMC，不改变 SPL/U-Boot，不挂载持久化 rootfs。

## 3. 关键源码调用链（6.18.63 固定 commit）

### 3.1 GMAC parent probe 会执行的动作

`dwmac-rk.c` 的 `rk_gmac_probe()`：
1. 获取 platform resources；
2. 解析 Panther X2 GMAC1 DT；
3. `rk_gmac_setup()` 获取 `phy-supply` 对应 regulator handle（`devm_regulator_get(dev, "phy")`）；
4. 设置 `plat_dat->init = rk_gmac_init`；
5. 进入 `devm_stmmac_pltfr_probe()` / `stmmac_dvr_probe()`。

`stmmac_dvr_probe()` 在进入 STMMAC core probe 前先调用 platform init callback。Panther RK3568 的 `rk_gmac_init()` 调用 `rk_gmac_powerup()`，预期动作包括：
- enable GMAC bulk clocks；
- 通过 main-GRF 写入 GMAC1 interface selection / RGMII mode / delay 配置；
- 调用 `regulator_enable()` 请求打开 PHY supply，即 RK809 SWITCH_REG1 / `vcc_3v3`；
- 获取 runtime-PM 引用。

因此 R7-A **不是只读 probe**。它会触发时钟、main-GRF 和 PHY supply 操作。对 PMIC 而言，是否实际产生 enable register 写取决于 rail 当时状态与 regulator core；但 regulator enable API 一定会被调用。必须把可能的 SWITCH_REG1 enable/disable 写入列入授权清单。

### 3.2 MDIO disabled 可隔离 PHY reset 与 PHY probe

6.18.63 `stmmac_of_get_mdio()` 会找到 GMAC 子节点 `mdio`；即使该子节点 status 为 disabled，指针仍会被保存。随后：
1. `stmmac_mdio_register()` 调用 `of_mdiobus_register()`；
2. `__of_mdiobus_register()` 首先检查 `of_device_is_available(mdio_node)`；
3. 节点 disabled 时立即返回 `-ENODEV`，不会调用 `__mdiobus_register()`；
4. STMMAC 将该 `-ENODEV` 作为“MDIO bus is disabled”正常处理并继续 probe。

因此该边界下：
- 不会注册 MDIO bus，也不会执行外部 PHY 的 MDIO read/write 事务；
- `stmmac_mdio_register()` 在调用 `of_mdiobus_register()` 前仍会执行 `stmmac_mdio_bus_config()`，因此可能读取/写入 MAC 内部 MDIO clock-divider/config 寄存器；这不是 MDIO bus transaction；
- 不会触发 bus reset callback；
- GMAC 的 `snps,reset-gpio` 不会由 `stmmac_mdio_reset()` 操作；
- MDIO 子节点下的 RTL8211F PHY 不会被创建或绑定；
- 不会执行 RTL8211F probe 的 WOL event 写入或 config_init 的 EEE/RGMII delay MDIO 写入。

同时 Panther PHY 为外置 PHY（`phy-is-integrated` 未设置），Rockchip glue 的 integrated-PHY reset/clock 专用分支不应进入。该结论是固定源码控制流审计，不是实机已观察结果。

### 3.3 不会进入 DMA open / TX

R7-A 不调用 `ndo_open`，接口保持 DOWN。按已归档 R5-2：
- descriptor ring 分配和 DMA open 初始化在 ndo_open 路径；
- PHY 初始化/连接也在后续 open 生命周期；
- 不执行 TX/RX descriptor、DMA doorbell、IRQ/NAPI 数据面和 AF_PACKET 发送。

本门 netdev 注册成功仅证明 platform/STMMAC probe 路径，不证明 MDIO、PHY link、DMA 或 Ethernet TX。

## 4. 允许的预期硬件副作用与停止条件

| 动作 | R7-A 预期 | 说明 |
|---|---|---|
| RK809 MFD/provider 初始化 | 会发生 | 已在 G4-P0 运行时验证过同一 provider binding；PMIC pre-init 写入仍属预期启动副作用 |
| IO-domain selector | 不应发生 | 九路 supply 属性保持缺失；不读取/写入 PMUGRF VSEL |
| GMAC clocks | enable | 由 Rockchip glue powerup |
| main-GRF GMAC1 mode/delay | 写入 | 包括 RGMII mode/delay 字段；与 PMUGRF IO-domain selector 是不同寄存器域 |
| SWITCH_REG1 / vcc_3v3 | 调用 regulator_enable | 可能写 PMIC enable bit；consumer 计数/状态必须采集 |
| MDIO bus | 不注册；内部 MDIO clock config 仍可能发生 | MDIO 子节点 disabled；`stmmac_mdio_bus_config()` 先于 OF bus 注册调用 |
| PHY reset GPIO3_PA1 | 不操作 | MDIO bus disabled，reset callback 不会运行 |
| RTL8211F MDIO 寄存器 | 不访问 | PHY 节点 disabled、无 PHY device |
| DMA ring / TX / RX | 不执行 | interface 不 open |

立即停止条件：
- regulator 获取/enable 返回错误；
- DWMAC/STMMAC probe 失败或 deferred probe 未收敛；
- MDIO bus 意外注册或出现任何 PHY/MDIO 事务；
- 发生预期外 GPIO/reset、PMIC、GRF 操作或供电状态变化；
- netdev 被自动置为 UP；
- 出现未解释的 kernel warning/error 或系统稳定性异常。

若 STMMAC probe 在 powerup 后失败，源码的 platform exit callback 会调用 Rockchip powerdown，包含 regulator_disable 与 clock disable；这属于可能的回滚写入，也必须纳入授权范围。该回滚路径尚未在 Panther 实机验证。

## 5. 配置准入清单（仅作为 build-only 审计目标）

从 G4-P0 frozen config 增量加入，不重建或覆盖 G4-P0：
- `CONFIG_STMMAC_ETH=y`；
- `CONFIG_STMMAC_PLATFORM=y`；
- `CONFIG_DWMAC_ROCKCHIP=y`；
- 按 R4/R5 的 6.18 Kconfig 依赖闭包显式核验 `CONFIG_ETHTOOL_NETLINK`、`CONFIG_PHYLINK`、`CONFIG_PHYLIB`、`CONFIG_MDIO_BUS`、`CONFIG_OF_MDIO` 及相关对象；
- `CONFIG_REALTEK_PHY` 保持 disabled；
- 不引入与本门无关的 network user-space applet。

最终以 `.config`、built-in object、vmlinux symbols、DTB structured diff 和 manifest 为准，不以 fragment 或 Kconfig select 文本代替最终产物证据。

## 6. Runtime 观测项目（未来另行授权后）

只观察：
1. `fe010000.ethernet` platform device 创建与 `dwmac-rk` driver bind；
2. STMMAC probe 日志及 netdev 注册；
3. MDIO bus 明确保持 disabled / 未注册；
4. PHY 节点未创建、无 RTL8211F driver bind、无 PHY reset GPIO 操作；
5. `regulator.19`（`vcc_3v3`）的 name/state/num_users/consumer 信息；确认 GMAC phy-supply consumer 是否建立 use count；
6. 相关 clock / main-GRF 初始化日志；
7. deferred-probe、完整 dmesg、netdev flags（确认 DOWN）。

不调用接口 UP，不执行 ping，不发送帧。保留 bootargs 中现有 `regulator_ignore_unused`，避免在本门引入第二个变量；此参数仅为本轮诊断保护，不代表最终系统配置。需通过 regulator num_users/consumer 直接观察供电 consumer，不能以 ignore_unused 代替成功证据。

## 7. 黄金基线差异与解释

- 6.1.65 与 6.1.116 已在同一 Panther X2 证明板载 Ethernet 正常；6.1.65 的来源链保留 candidate 限制，6.1.116 有更完整的运行配置证据。
- 6.1.65/6.1.116 与 6.18 的 Rockchip glue probe/powerup 生命周期存在差异：6.18 将 powerup 放到 STMMAC platform init callback；regulator_enable 错误会传播并阻止后续初始化，较 6.1.65 更严格。
- R7-A 的目标不是复刻黄金系统的每一项写入，而是验证 6.18 默认实现能否完成最小 platform probe，并把预期副作用与后续 MDIO/PHY/DMA 分开。
- 6.1.65 原始 DTB PMIC/IO-domain 全子树 binary diff 仍为 CONDITIONAL 缺口；不要求重新提取 851MiB 镜像，也不把该缺口转化为硬件测点任务。

## 8. 阶段判定与下一步

| 项目 | 状态 |
|---|---|
| G4-P0 binding-only runtime | PASS |
| corrected collector BusyBox ash/package CI | PASS |
| R7-A one-node DTB boundary | STATIC DESIGN PASS |
| R7-A exact Kconfig/object closure | PENDING BUILD AUDIT |
| R7-A artifact / rollback package | NOT BUILT |
| R7-A hardware probe | NOT AUTHORIZED / NOT RUN |
| MDIO / PHY / link | NOT TESTED |
| interface open / DMA / TX | NOT TESTED |

**结论：** G4-P0 已完成；可以进入 R7-A 的独立 build-only 候选准备，但不得直接写 SU08G 或启动。R7-A 必须保持 MDIO/PHY disabled、IO-domain 九路 supply 缺失、接口 DOWN。任何实机启动和上述 clocks/main-GRF/SWITCH_REG1 副作用均须另行取得明确授权。

本报告为固定源码、已有仓库证据和 DTB 结构的只读审计；未访问 Panther X2、未构建新内核/DTB、未写入任何存储、未执行 PMIC/GRF/GPIO/MDIO 操作。
