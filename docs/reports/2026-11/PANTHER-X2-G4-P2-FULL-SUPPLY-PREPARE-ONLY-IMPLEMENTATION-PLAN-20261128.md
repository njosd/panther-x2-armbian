# Panther X2 Project A — G4-P2 Full-Supply IO-domain PREPARE-ONLY 实施计划（2026-11-28）

- 状态：**DESIGN READY FOR BUILD-WORKFLOW REVIEW；尚未创建/运行 workflow，尚无 artifact**
- 当前阶段：静态供电解析链已闭合；准备一份只改变 IO-domain child status 的 PREPARE-ONLY runtime 候选
- 目的：在 GMAC1/MDIO/RTL8211F 仍全部 disabled 时，单独验证 Linux 6.18.63 的真实九路 IO-domain supply lookup / notifier / selector 路径
- 重要边界：PREPARE-ONLY 只允许云端构建和封装；不能自动授权写入 SU08G 或启动 Panther X2

## 1. 依据与已完成证据

1. G3 provider runtime 已证明 RK809 regulator provider 可在 Linux 6.18.63+ 绑定；运行设备树 IO-domain child 当时为 disabled，因此该会话没有执行 IO-domain consumer probe。
2. G4-P0 build-only artifact（run `46091659151`，artifact `15242113092`）提供了固定 6.18.63 Image、kernel.config、System.map、vmlinux 与依赖对象哈希；最终 Kconfig 只相对 G3 增加 `CONFIG_ROCKCHIP_IODOMAIN=y`。
3. G4-P0 binding-only 的一次授权 RAM-only runtime 会话已证明 IO-domain child 能枚举并绑定 `rockchip-iodomain`，RK809 regulator provider 同时绑定；但因九路 supply properties 全部删除，没有执行电压读取、notifier 或 selector write。该会话不是完整供电路径验收。
4. G4-P2 专项报告 §7 已纠正 SWITCH_REG1 上游 supply 遗漏：RK809 SWITCH_REG1 descriptor 的 `supply_name=vcc9`，RK809 PMIC parent node 的 `vcc9-supply` 指向 fixed regulator `vcc3v3_sys`（3.3V）。RK809 regulator probe 通过 `device_set_of_node_from_dev(&pdev->dev, pdev->dev.parent)` 将 PMIC OF node 赋给 regulator platform device；regulator core 可在无本地 voltage getter 时沿已解析的 upstream supply 读取电压。
5. 两份 6.12.81 历史 UART 日志均打印九路 IO-domain 正电压，其中 vccio1、vccio5、vccio6、vccio7 为 3.3V。这是历史非 GMAC 运行证据；6.12.81 仍是 Project B 故障样本，不作为黄金功能基准，不重开 TX 调查。
6. 6.1.116 磁盘 DTB 与 6.18.63 完整 DTB 已字节级相同（SHA256 `5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`）；6.1.65 原始 DTB PMIC 子树 binary diff 仍保留证据限制。

## 2. 候选资产组成

优先复用已验收资产，不重新编译相同 Image：

- Kernel Image / kernel.config / System.map / vmlinux / IO-domain dependency object hashes：来自 G4-P0 build-only artifact。
- 基础 DTB：来自冻结 G3 provider artifact（PMIC/regulator provider enabled，GMAC/MDIO/PHY disabled，IO-domain disabled，九路 supply phandle 保留）。
- Initramfs / BusyBox / U-Boot proper：复用已验收 B1/G3 runtime packaging 资产；若既有 G4-P0 runtime 包装资产已存在，则优先复用并逐项核对哈希，禁止重建或替换不必要的启动组件。
- Bootargs 与 load address：沿用已验证 RAM-only 启动参数和 U-Boot 地址，不变更 U-Boot environment，不增加自动 fallback。

## 3. 唯一允许的 DTB 差异

从冻结 G3 DTB 开始，仅执行：

`/syscon@fdc20000/io-domains/status: disabled → okay`

必须原样保留：
- `pmuio1-supply`、`pmuio2-supply`、`vccio1-supply` … `vccio7-supply` 全部九个属性与原 phandle；
- PMUGRF parent / IO-domain compatible；
- RK809 PMIC 节点及其所有 regulator children、`vcc9-supply = <&vcc3v3_sys>`；
- regulator constraints、GPIO、pinctrl、clock、reset、USB、MMC、其他 SoC 节点；
- GMAC1、MDIO、RTL8211F 继续 disabled；
- eMMC SDHCI、TF SDMMC0、SDIO、GPU、SARADC 继续 disabled。

离线 diff allowlist 必须只有上述一个 status 属性变化。需额外断言九个 supply property 均存在且与 G3 baseline 值相同，不能只断言属性数量。

## 4. 运行时预期行为与副作用清单

当且仅当未来另行授权启动此候选时，预期 IO-domain probe 会：
1. 取得 PMUGRF syscon regmap（可能建立 MMIO mapping）；
2. 依序对九路 supply 执行 regulator lookup 和 voltage read；
3. 对成功取得的 supply 注册 regulator notifier；
4. 在 probe 初始化过程中根据各 bank 电压调用 RK3568 IO-domain write handler，执行 PMU GRF selector regmap write；
5. 在 `CONFIG_REGULATOR_DEBUG` / dump 路径可用时输出各 supply 的软件电压信息。

明确限制：
- `rk3568_iodomain_write()` 对相关 `regmap_write()` 返回值不做充分检查；probe/bind 成功或日志打印 3.3V，不能证明 selector transaction 已成功。
- 不允许把 software microvolts 当作物理 rail 测量。
- 不允许直接读取或写入 PMIC/PMUGRF 原始寄存器来“补证”；本门只使用标准驱动路径及 sysfs/dmesg 只读观察。
- 不启用 GMAC clock/reset/pinctrl consumer，不 open netdev，不访问 MDIO，不触发 PHY reset，不发送测试帧。

## 5. 云端 build/package gate

建议新增独立 workflow，名称建议 `.github/workflows/package-panther-x2-g4-p2-full-supply.yml`，只做 PREPARE-ONLY 封装，不改写 G4-P0 build workflow。

必要 gate：
1. 下载并验证 G4-P0 build-only artifact、G3 provider baseline artifact、B1 boot support artifact（或已验收 G3 runtime package）。
2. 核对每份输入的 SHA256SUMS、artifact/run identity 和固定 source commit。
3. 以 G4-P0 Image/kernel.config/System.map/vmlinux 为内核资产；以 G3 DTB 为 base，仅修改 IO-domain status。
4. 确认最终 Kconfig：`CONFIG_ROCKCHIP_IODOMAIN=y`、`CONFIG_REGULATOR_RK808=y`、`CONFIG_MFD_SYSCON=y`、`CONFIG_REGMAP_MMIO=y`；STMMAC、DWMAC_ROCKCHIP、MDIO_BUS、PHYLIB、REALTEK_PHY 全部 disabled。
5. DTB diff 精确为单一 status 变化；九个 supply 属性逐项存在，phandle 与 G3 baseline 完全相同；PMIC `vcc9-supply`、fixed 3.3V `vcc3v3_sys` 节点均存在。
6. 对最终 Image、DTB、uInitrd、boot.scr、boot.cmd、manifest 和 TF image 生成 SHA256SUMS；对 TF image 只在 GitHub runner 创建、挂载、只读复核、压缩。
7. Manifest 明确写明：`PREPARE_ONLY`、`runtime_probe=not_executed`、`selector_writes=not_executed_during_build`、`physical_media_writes=none`、`hardware_authorization=not_granted`、`target=SU08G only`、`SN64G/eMMC untouched`。

## 6. 后续硬件门（不由本报告授权）

只有 workflow 全部通过、artifact 独立下载校验完成后，才提交单独的硬件操作申请。该申请需明确：
- 仅 SU08G，使用 Etcher 写入；绝不使用命令行写盘；
- 一次 RAM-only boot session；
- 预期会发生 IO-domain regulator voltage lookup、notifier registration 和 PMU GRF selector writes；
- G3 provider runtime / G4-P0 binding-only 均不被覆盖；SN64G/eMMC 不触碰；
- 启动后只读取 dmesg、platform driver binding、regulator sysfs 状态、deferred-probe；不做 raw PMIC/GRF read/write，不启用 GMAC；
- 若 probe 报错、deferred、supply voltage invalid、regulator lookup 失败或出现非预期日志，立即停止，不进入 R7-prep/R7-A；
- 若 probe/bind 成功，也只记 G4-P2 runtime PASS-CONDITIONAL；selector write 返回值及物理 rail 仍需证据边界说明。

## 7. 更新后的阶段顺序

G4-P1 provider readiness（CONDITIONAL PASS）  
→ G4-P2 full-supply PREPARE-ONLY build/package  
→ 单独授权的 G4-P2 RAM-only runtime  
→ R7-prep（STMMAC/Rockchip glue/MDIO/PHY 软件闭包 build-only，DT 全 disabled）  
→ R7-A/G5-A（最后启用 GMAC parent）  
→ R7-B/G5-B（MDIO/RTL8211F）  
→ R7-C/G6-A（interface open / DMA）  
→ R7-D/G6-B/G7（ABCD 同帧 / 独立对端 pcap）。

这保证非 GMAC 的 IO-domain 供电与 selector 软件路径先得到验证；GMAC 仍保持最后启用。

## 8. 本报告安全边界

本报告仅依据已归档源码、DTS、G3/G4-P0 build artifact 清单和历史日志制定。没有访问 Panther X2，没有创建或启动候选 artifact，没有刷写 SU08G，没有访问 SN64G/eMMC，没有执行 PMIC/GRF/GPIO/clock/reset/MDIO 操作，没有发送网络帧。
