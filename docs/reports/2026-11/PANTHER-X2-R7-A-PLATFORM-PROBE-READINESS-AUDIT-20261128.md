# Panther X2 项目 A — R7-A Platform Probe 预审记录（非阶段放行，2026-11-28）

## 1. 结论

**本报告仅为 R7-A 的初步源码边界研究，不构成 R7-A 准入通过，也不构成 build-only / 实机启动授权。**

回读原始 R2–R7 计划后发现，本报告原拟从 G4-P0 直接增量加入 STMMAC Kconfig 并修改 GMAC1 DTB。这会使本轮候选同时改变 kernel.config 与 DTB，违反原计划“R7 唯一变量为目标 DTB”的约束。因此不得按本报告原提议直接构建或启动。正确做法是先准备并冻结一个 GMAC/MDIO/PHY 仍 disabled、但 STMMAC/Rockchip glue 最小驱动对象已预编译的 R7-prep 基线；随后 R7-A 只改变 GMAC1 DTB 节点状态。该 R7-prep 构建属于 R7-A 前置准备，不得与 R7-A 硬件变量混在同一轮。

R7-A 实机验收候选的最终单变量边界应为：
- kernel.config / Image：来自事先冻结的 R7-prep 基线，不在 R7-A 本轮改变；
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

## 5. R7-prep 构建准备（不是 R7-A 本轮变量）

当前 G4-P0 kernel.config 未启用 STMMAC。必须先从 G4-P0 派生一个独立 R7-prep build-only 基线，增加以下配置并完成黄金基线对照；GMAC1/MDIO/PHY DT 节点仍保持 disabled。R7-prep 不覆盖 G4-P0，也不触发设备启动：
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

**结论：** G4-P0 的 binding-only 目标已完成，但 G4-P full-supply mapping 仍 NO-GO。当前报告只能作为 R7-A 的源码预审材料。下一步先按 R2–R7 计划完成 R7-prep 基线和 6.1.65/6.1.116 黄金对照；核实 G5-A/R7-A 前置条件与 IO-domain/PHY supply 风险后，才能决定是否放行 build-only。R7-A 实机阶段只允许 DTB 作为变量，MDIO/PHY 保持 disabled、九路 IO-domain supply 属性缺失、接口 DOWN。任何实机启动和 clocks/main-GRF/SWITCH_REG1 副作用均须另行明确授权。

本报告为固定源码、已有仓库证据和 DTB 结构的只读审计；未访问 Panther X2、未构建新内核/DTB、未写入任何存储、未执行 PMIC/GRF/GPIO/MDIO 操作。

## 2026-11-28 后续顺序修订：本报告不再作为直接进入 R7-A 的执行顺序

本报告 §1、§5、§8 保留原始预审时间点的候选设计和配置讨论，后续执行不得直接照此启动。用户要求将最可能发生问题的 GMAC 留到最后，因此当前有效的前置顺序已调整为：

1. R7-prep build-only：预构建完整软件闭包（包括为 R7-B 预置 REALTEK_PHY built-in），GMAC/MDIO/PHY DT 节点仍全部 disabled；不发生硬件 probe。
2. G4-P1 / Pre-GMAC provider readiness：复用 R2/R3/G4-P0 既有证据，先确认共享 clock/CRU、pinctrl/GPIO、GRF/syscon、reset、I2C0、RK809 MFD/regulator、IO-domain provider 的就绪状态；已通过项目不重跑，缺口只做最小只读补证。
3. G4-P2 / Pre-GMAC supply & IO-domain safety：解决 SWITCH_REG1/vcc_3v3 consumer enable 与 IO-domain supply/selector partial-write 风险。当前 full nine-supply mapping NO-GO，未解除前不允许 GMAC probe。
4. 只有 G4-P1/G4-P2 均通过且取得独立授权，才执行 R7-A/G5-A：GMAC1 parent 单节点启用，MDIO/PHY DT nodes disabled，interface DOWN，不 open、不发帧。
5. 随后才按 R7-B/G5-B → R7-C/G6-A → R7-D/G6-B/G7 逐层启用 PHY、DMA open、ABCD TX。

本报告中“R7-A one-node DTB boundary STATIC DESIGN PASS”只表示源码与设备树隔离设计可行，不代表供电/IO-domain 前置门 PASS，不代表 R7-A gate-pass。R7-A 硬件状态继续 NOT AUTHORIZED / NOT RUN。R7-prep 的 REALTEK_PHY=y 仅为 built-in 预置；PHY DT 节点 disabled 时不触发 PHY probe。

本顺序不授权切换 regulator、GPIO/reset、PMIC/GRF/MDIO 写入、刷写或启动设备。

## 9. G4-P2 runtime 通过后的 R7-A DTB 基线修订（优先于 §1/§4/§7 中旧供电边界）

本报告早期设计曾要求 R7-A 继续使用 G4-P0 binding-only DTB，即 IO-domain child okay 但九路 supply 属性缺失。该边界现已被 G4-P2 full-supply runtime 实测结果取代，不再是当前有效基线。

R7-prep 和后续 R7-A 的 DTB 基线必须继承 G4-P2 full-supply DTB（SHA256 41253336c0e69b7431e0d095573724c087734bb310143e1848d8da7639a7c9be）：IO-domain child 保持 okay，九路 supply phandle 全部保留。R7-A 唯一 DTB 变量仍是 GMAC1 parent /ethernet@fe010000/status 从 disabled 改为 okay；MDIO child 和 RTL8211F PHY 节点继续 disabled。除此之外，DTB 每个节点/属性/phandle 均须与 G4-P2 DTB 字节级逻辑相同。

这意味着 R7-A probe 会在已通过 G4-P2 的 full-supply IO-domain 配置上进行；它仍会触发此前 §3/§4 记录的 GMAC clocks enable、main-GRF RGMII mode/delay writes、SWITCH_REG1/vcc_3v3 regulator_enable（以及失败回滚可能产生的 disable）。G4-P2 PASS-CONDITIONAL 不等于这些 GMAC 专属副作用已验证或授权。R7-A 仍需单独审查供电 consumer 影响并取得独立授权。

R7-prep build-only 尚未执行；本节不构成硬件授权。
