# Panther X2 Project A — G4-P0 相对两条黄金基线的阶段偏离说明（2026-11-28）

## 1. 结论摘要

截至 G4-P0，本项目已经证明 **Linux 6.18.63+ 可以在 Panther X2 上通过现有启动链进入 RAM initramfs，并成功枚举、绑定 RK809 regulator provider 与 Rockchip IO-domain driver**。这证明 6.18 的最小启动底座以及本阶段所需 PMIC/IO-domain provider binding 路径可以在目标板运行。

但 G4-P0 不是黄金系统的功能等价复刻。它是一个有意隔离网络与真实 IO-domain supply/selector 路径的 binding-only 测试镜像。因此：

- 相对黄金基线，当前最显著的差异是**测试范围与设备树/Kconfig 的有意裁剪**，不是已经发现 6.18 硬件适配故障。
- G4-P0 尚未恢复 GMAC1、MDIO、RTL8211F，也没有真实 Ethernet link/TX/RX 测试；不能据此宣称 6.18 网络已达到黄金水平，也不能据此判定网络回归。
- IO-domain child 已绑定，但九路 supply 属性全部删除；本轮没有执行九路 regulator consumer 获取、rail 电压读取或 selector 写入路径。因此 IO-domain 的真实供电配置仍未与黄金系统做功能等价验证。
- **本阶段无已证实的黄金功能退化项；但存在明确的功能覆盖缺口。** 当前结果应标记为 G4-P0 binding-only PASS，而不是黄金等价 PASS。

## 2. 两条黄金基线的可信度与参照作用

| 黄金基线 | 已知实机事实 | 来源/限制 |
|---|---|---|
| Linux 6.1.65（TF） | 同一 Panther X2 上正常启动并取得 DHCP；是第一黄金基线 | 实机正常运行证据独立成立。候选源码端点为 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`，但尚未与原始 Image 做二进制级源码绑定 |
| Linux 6.1.116（eMMC） | 已知正常启动；板载 GMAC1 识别 RTL8211F，Link Up 1Gbps/Full；有完整网络运行记录 | 正常源码端点锁定为 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`；真实 config 7,677 个符号与对应 Ophub config 模板零差异 |

两条黄金源码端点的以下文件逐字节相同：RK809 MFD `drivers/mfd/rk808.c`、RK809 regulator `drivers/regulator/rk808-regulator.c`、Rockchip IO-domain `drivers/soc/rockchip/io-domain.c`、Rockchip GMAC glue `drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`、Panther X2 DTS `rk3566-panther-x2.dts` 和 SoC DTSI `rk3566.dtsi`。Regulator core 虽然整体文件不同，但已定点比较的四个约束/late-cleanup 函数文本相同。

证据边界：6.1.65 的源码比较仍属于高置信度候选源码比较，不能升级为原始 Image 二进制绑定 PASS；6.1.116 的源码端点和配置证据更完整。黄金系统的网络实机成功是独立于上述源码身份限制的事实。

## 3. 分层偏离对照

| 维度 | 黄金基线 6.1.65 / 6.1.116 | 当前 G4-P0（6.18.63+） | 偏离性质 |
|---|---|---|---|
| Kernel 版本 | 6.1.65 / 6.1.116 | 6.18.63+，固定源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9` | 目标版本升级，属于预期差异 |
| 启动/根文件系统 | 6.1.65 从 TF 正常运行；6.1.116 为 eMMC 正常系统 | 现有 eMMC 前级 SPL → TF 上 JP-TvBox U-Boot proper → TF 上 Image/uInitrd/DTB；Linux root 为 RAM initramfs | 测试启动链和 rootfs 有意不同；尚未验证最终长期启动方案 |
| CPU/RAM | 同一 RK3566 Panther X2 硬件 | Linux 识别 Panther X2、4 GiB RAM、4 CPUs；PSCI CPU hotplug 测试通过 | 当前启动底座已验证；未做性能/频率/负载等黄金量化比较 |
| RK809 MFD / regulator 配置 | 两条黄金配置均包含 built-in RK808/RK809 MFD 与 regulator provider | G4-P0 保留 RK809 provider；runtime 已绑定 `rk808-regulator` | 核心 provider 路径已恢复并通过 binding 验证 |
| Regulator 对象 | 黄金源码含完整 RK809 regulator 描述 | G4-P0 `/sys/class/regulator` 有 .0–.20 共 21 个全局对象；其中 RK809 provider 对应 16 个 regulator 名称，包含四个 IO-domain 相关对象 | 对象注册已验证；不能把全局 21 项误说成 RK809 独有 21 路 |
| IO-domain child | 黄金 Panther DTS 源码包含九路 supply 描述；6.1.116 DTB 与 6.18.63 基础 DTB 已记录为字节级相同 | G4-P0 将 child status 设为 okay，但删除全部九个 `*-supply` 属性；runtime child 枚举并绑定 `rockchip-iodomain` | **有意的 binding-only 差异**；没有验证黄金 supply/selector 功能等价 |
| PMUGRF | 黄金源码路径具有 IO-domain selector 写入逻辑；黄金整机网络正常，但当前归档没有独立的黄金 VSEL 运行时读数 | G4-P0 probe 成功，支持 PMUGRF syscon regmap acquisition 已完成；没有读 VSEL0/1/2，也没有运行时总线跟踪 | regmap/bind 已验证；selector 实际状态和写事务均未测 |
| Ethernet MAC / MDIO / PHY | 6.1.65/6.1.116 正常系统具有板载 Ethernet 功能；6.1.116 有 RTL8211F 1Gbps Full 记录 | G4-P0 中 GMAC1、MDIO、RTL8211F 节点/相关设备保持 disabled；没有 netdev、MDIO/PHY probe 或链路测试 | **最大功能覆盖缺口，属计划内隔离，不是失败证据** |
| PHY supply / SWITCH_REG1 | 黄金系统的 GMAC glue 通过 `phy-supply` 获取 RK809 SWITCH_REG1；黄金网络成功不等于已有独立 rail 实测 | G4-P0 未提供 IO-domain supplies，GMAC 也未启用；未测试 PHY consumer 的 `regulator_enable()` | 未验证，不能宣称供电路径已通过 |
| 物理电源质量 | 黄金整机运行正常，但无当前归档的各 rail 万用表/示波器数据 | G4-P0 未测任何物理 rail 电压、纹波或负载 | 两边均不能从软件状态推导物理测量；G4-P0 不新增此类证据 |

## 4. 与黄金 PMIC/IO-domain 路径相比，当前已证明到哪里

### 已证明

1. G4-P0 使用 Linux 6.18.63+，在目标 Panther X2 上启动进入 RAM initramfs。
2. RK809 regulator platform device 成功绑定 `rk808-regulator`。
3. Regulator class 注册 21 个对象；其中 RK809 provider 的 16 个 regulator 实例可识别，四个与原九路 IO-domain supplies 对应的对象均存在：
   - `vcc3v3_pmu`（regulator.15）
   - `vcc_3v3`（regulator.19）
   - `vcc_1v8`（regulator.9）
   - `vccio_sd`（regulator.14）
4. IO-domain DT child 位于 `syscon@fdc20000/io-domains`，platform device `fdc20000.syscon:io-domains` 已创建，并明确绑定 `rockchip-iodomain`。
5. IO-domain probe 成功支持其父 PMUGRF syscon regmap acquisition 已完成；但不能把它夸大为 VSEL 寄存器已读写或 selector 状态已验证。

### 尚未证明

1. 九路 supply 恢复后的 consumer 获取、voltage read、notifier 注册及 selector 写入结果。
2. PMUGRF VSEL0/VSEL1/VSEL2 当前值及与实际 IO bank 电压的一致性。
3. RK809 SWITCH_REG1（`vcc_3v3`）真实输出电压。其 regulator sysfs 没有 `microvolts` 属性。
4. GMAC1 PHY consumer 是否能成功获取/enable SWITCH_REG1，以及 6.18 glue 在真实 probe 生命周期中的行为。
5. RTL8211F MDIO 识别、PHY attach、RGMII link negotiation、1Gbps Full、实际 TX/RX。
6. 任一电源 rail 的物理电压、纹波或负载能力。

## 5. G3 → G4-P0 的本阶段增量，避免误读为大范围配置变化

G4-P0 相对冻结 G3 输入的增量受到严格限制：

- 最终 kernel.config 仅新增 `CONFIG_ROCKCHIP_IODOMAIN=y`；其余配置与 G3 冻结配置一致。
- DTB 仅将 `/syscon@fdc20000/io-domains/status` 从 disabled 改为 okay，并删除九个 supply 属性。
- RK809 节点/provider 保留。
- eMMC、TF SDMMC0、SDIO、GPU、SARADC、GMAC1、MDIO、RTL8211F 均保持 disabled。
- G4-P0 runtime 观察到的设备树节点属性集合只有 `name`、`phandle`、`status`、`compatible`，没有九个 supply 属性；与离线 DTB 审计相符。

因此 G4-P0 的主要进展不是“把完整网络栈恢复到 6.18”，而是以单变量方式证明：在保留 RK809 provider 的情况下，6.18 IO-domain child 能够被创建并成功绑定，而不进入危险的完整 supply/selector 路径。

## 6. 日志中的非目标警告

本轮启动日志另有 display VOP unavailable、USB PHY runtime-PM underflow、SCMI malformed reply，以及 cpuidle 不可用导致 PSCI suspend tests 未执行等记录。它们不改变本次 RK809/IO-domain binding 结论，也不能直接归因于 PMIC/IO-domain。当前未把这些非目标子系统扩展为新专题；若后续正式系统需要显示、USB 或 suspend 功能，再按实际需求独立评估。

## 7. 阶段判定

| 验收项 | 状态 |
|---|---|
| 两条黄金基线作为板级正常功能参照 | 已成立 |
| 6.18.63+ Panther X2 RAM-only 启动 | PASS |
| RK809 regulator provider binding | PASS |
| IO-domain child enumeration / driver binding | PASS |
| 与黄金 IO-domain 九路 supply 行为等价 | NOT VERIFIED |
| SWITCH_REG1 PHY consumer 功能 | NOT VERIFIED |
| GMAC1 / MDIO / RTL8211F 功能 | 本阶段未启用，NOT TESTED |
| 6.18 Ethernet 对黄金功能等价 | NOT TESTED |
| 物理 rail 电气质量 | NOT VERIFIED |
| G4-P0 binding-only objective | **PASS** |
| G4-P full nine-supply mapping | **NO-GO** |

**最终说明：** 截至 G4-P0，没有发现足以判定 6.18.63+ 相对黄金基线发生 PMIC/IO-domain 硬件适配退化的证据。已知的主要偏离均来自本阶段刻意采用的 RAM-only、minimal config、GMAC/MDIO/PHY disabled、IO-domain supplies removed 测试边界。黄金基线证明硬件和旧软件组合能够提供正常 Ethernet；G4-P0 只证明 6.18 的启动、RK809 provider binding 与 IO-domain binding 可行。二者之间尚缺真实 supply consumer、selector 状态、PHY/GMAC 及端到端 Ethernet 验证，不能把“尚未验证”写成“与黄金一致”，也不能写成“6.18 不正常”。

本报告仅整理已归档黄金证据与 G4-P0 本轮运行证据；不授权任何新硬件启动、selector 操作、物理测量、eMMC 或 SN64G 操作。
