# Panther X2 项目 A — G4 IO-domain 黄金源码与写入路径审计（2026-11-27）

- 阶段：G4-S（static/source + DTS audit）
- 结论：**G4-S PASS；G4-P runtime activation HOLD / NOT AUTHORIZED**
- 依据：G0.1 provider/consumer 矩阵、G0.3 IO-domain 静态报告、G3-P provider runtime PASS，以及固定源码/DTS 对照。
- 本轮严格只读：未启动设备、未读取/写入 PMU GRF、未读取/写入 PMIC、未启用 IO-domain consumer、未恢复 GMAC/MDIO/PHY、未发送测试帧。

## 1. 固定输入与源码身份

### 1.1 `drivers/soc/rockchip/io-domain.c`

| 版本 | 仓库/commit | Git blob SHA |
|---|---|---|
| Linux 6.18.63 | `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f` | `f94985a905c29685558b924e309c871c4718a3f6` |
| Linux 6.1.116 | `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e` | `6619256c2d1180f2a24e5c1a595bafe1d2c65c16` |
| Linux 6.1.65 source candidate | `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc` | `6619256c2d1180f2a24e5c1a595bafe1d2c65c16` |

6.1.65 candidate 与 6.1.116 对应文件 blob 完全相同。此项仍保留 6.1.65 源码端点的 candidate 身份限制，不将它升级为完整构建输入身份认证。

对三个源码端点逐函数提取并比较，以下函数体均逐字节相同：
- `rk3568_iodomain_write()`
- `soc_data_rk3568_pmu`
- `rockchip_iodomain_notify()`
- `rockchip_iodomain_probe()`

6.18 文件整体 blob 与 6.1.116 不同，但已识别差异位于其他 SoC（RK3308）代码移除及 platform remove callback API 签名调整；上述 RK3568 目标路径没有版本差异。未发现 6.18 新引入的 RK3568 IO-domain 写入行为。

### 1.2 Kconfig / Makefile

6.18 与 6.1.116 的 `drivers/soc/rockchip/Kconfig` 中 `ROCKCHIP_IODOMAIN` 配置块一致：
- `tristate "Rockchip IO domain support"`
- `depends on OF`

两版 Makefile 均通过 `obj-$(CONFIG_ROCKCHIP_IODOMAIN) += io-domain.o` 构建该驱动。R1 已有 `CONFIG_ROCKCHIP_IODOMAIN=y` 和 built-in probe/write 符号证据；G3-B 则为隔离目的将其关闭。

## 2. Panther X2 DTS 黄金对照

### 2.1 DTS 源文件身份

`arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`：
- 6.18.63 blob：`a0a08476f45fb2d602fd7312def6f587f33fb91e`
- 6.1.116 blob：`1e3153c392d8de617f72b3133eaeddf45569bde8`
- 6.1.65 candidate 与 6.1.116 blob 相同：`1e3153c392d8de617f72b3133eaeddf45569bde8`

完整 board DTS 文件并非 6.18/6.1 字节相同，但以下关键节点块在三个输入中逐字节相同：
- `&pmu_io_domains` supply phandle 与 `status = "okay"`
- `vcc_3v3: SWITCH_REG1` 节点
- `&gmac1` 的功能属性相同；6.18 相比黄金文件仅少一条 reset delay 注释，不改变属性值

### 2.2 九个 IO-domain supply phandle

Panther X2 DTS 将 RK3568 PMU IO-domain 9 个 supply 映射为：

| Driver supply index | supply name | DTS property → regulator node |
|---:|---|---|
| 0 | pmuio1 | `pmuio1-supply → vcc3v3_pmu` |
| 1 | pmuio2 | `pmuio2-supply → vcc3v3_pmu` |
| 2 | vccio1 | `vccio1-supply → vcc_3v3` |
| 3 | vccio2 | `vccio2-supply → vcc_1v8` |
| 4 | vccio3 | `vccio3-supply → vccio_sd` |
| 5 | vccio4 | `vccio4-supply → vcc_1v8` |
| 6 | vccio5 | `vccio5-supply → vcc_3v3` |
| 7 | vccio6 | `vccio6-supply → vcc_3v3` |
| 8 | vccio7 | `vccio7-supply → vcc_3v3` |

G3-P 运行时已确认 RK809 provider 注册了相关名称的 regulator objects，包括 `vcc3v3_pmu`、`vcc_1v8`、`vccio_sd`、`vcc_3v3`。这证明 provider 端对象存在，不证明 IO-domain consumer 已成功取得这些 supply，也不证明 rail 实际电压。

## 3. Probe 控制流与写入副作用

固定版本的 RK3568 probe 路径：

1. 获取 PMU GRF regmap（优先 parent syscon node）。
2. 按 `soc_data_rk3568_pmu.supply_names[]` 顺序遍历 9 个 supply。
3. 对每个非 NULL supply name 调用 `devm_regulator_get_optional()`。
4. 属性未声明、返回 `-ENODEV` 时跳过该 supply；provider 尚不可用或显式 defer 时，返回错误并退出 probe。
5. 成功取得 regulator 后调用 `regulator_get_voltage()`；负值报错退出，超过 3.6V 拒绝。
6. 立即调用 `iod->write(supply, uV)`，随后注册 regulator notifier。
7. 全部 supply 处理完成后 probe 返回成功。

### 3.1 缺 provider 与部分失败的区别

- G0.3 已证明：R1 当时因缺 RK809 regulator provider，在第一次 supply lookup 返回 `-EPROBE_DEFER`，控制流早于该次 supply 的 `regulator_get_voltage()` 和 GRF write；该次 defer 路径没有执行 IO-domain 写入。
- G3-P 后 provider 已注册，但尚无 IO-domain consumer 运行证据。
- 如果未来 probe 在前几个 supply 已经完成 `iod->write()` 后，才在后续 supply 获取、电压读取或 notifier 注册时失败，cleanup 只注销已注册 notifier；源码没有恢复此前 GRF 值的 rollback。失败 probe 可能留下部分已写 selector。

### 3.2 RK3568 写函数的一个重要实现限制

`rk3568_iodomain_write()` 对 GRF 调用 `regmap_write()`，但没有检查这些调用的返回值；函数对有效 supply index 最终返回 0。因此：
- probe 的 `iod->write()` 返回成功，并不能证明底层每次 `regmap_write()` 都成功；
- driver bind/probe success 也不能单独证明 PMU GRF selector 的写入已生效；
- G4 运行时若获准，必须设计独立的只读 GRF readback 观察；不能只看 driver symlink 或 dmesg 中没有错误。

### 3.3 按当前 DTS 预期的写调用范围

当前 DTS 声明全部 9 个 supplies。RK3568 专用写函数：
- index 0 / pmuio1：不写 selector；
- index 1 / pmuio2：对 PMU GRF IO_VSEL2 执行 2 次 write；
- index 2 / vccio1：对 PMU GRF IO_VSEL0、IO_VSEL1 各写 1 次；
- index 3 / vccio2：不写 selector（由硬件 FLASH_VOL_SEL 决定）；
- index 4–8 / vccio3–vccio7：每个 domain 对 IO_VSEL0、IO_VSEL1 各写 1 次。

若 9 个 regulator 均成功取得且电压有效，probe 初始路径共执行 **14 次 regmap_write 调用**，涉及 VSEL0、VSEL1、VSEL2。它不是只修改 GMAC1 所在的 VCCIO5。

对 VCCIO5（index 6）：
- 3.3V 判定：VSEL0 offset `0x0140` 写 `0x00200000`；VSEL1 offset `0x0144` 写 `0x00200020`。
- 1.8V 判定：VSEL0 写 `0x00200020`；VSEL1 写 `0x00200000`。

这里的 1.8V/3.3V 是由 regulator framework 报告的电压分类决定，不是由 IO-domain driver 对实体 rail 进行测量。

## 4. 关键风险：SWITCH_REG1 电压读数不等于其输出电压

DTS 中：
- `vcc_3v3` 对应 RK809 `SWITCH_REG1`；
- RK809 的 `vcc9-supply` 指向固定 regulator `vcc3v3_sys`；
- `vcc3v3_sys` 在 DTS 中描述为 3.3V、always-on、boot-on；
- `SWITCH_REG1` 本身没有 `regulator-always-on` 或 `regulator-boot-on`，并声明 `regulator-off-in-suspend`。

6.18 RK809 `SWITCH_REG1` descriptor 的 upstream supply 为 `vcc9`，它没有自身的 voltage selector/get_voltage 实现。Linux regulator core 在 switch 无自身电压读回时可沿 `rdev->supply` 递归读取 upstream voltage。因此 `regulator_get_voltage(vcc_3v3)` 可能报告上游固定 regulator 的 3.3V，**即使这并不证明 SWITCH_REG1 输出端当前已使能或实际达到 3.3V**。

IO-domain probe 不调用 `regulator_enable()`，它只是读取 regulator framework 电压值并据此设置 IO selector。它不会替代 SWITCH_REG1 的供电使能动作。

因此，G3-P 的 provider bind/对象注册 PASS 不能作为 VCCIO5 实际 3.3V 的证明；本轮也没有采集 SWITCH_REG1 的 enable state 或进行物理电压测量。

## 5. Notifier 后续写入

成功取得 supply 并完成初始写入后，driver 会注册 regulator notifier。后续 regulator voltage change：
- PRE_VOLTAGE_CHANGE 阶段根据旧电压与请求最大电压，提前设置 IO selector；
- VOLTAGE_CHANGE / ABORT_VOLTAGE_CHANGE 阶段再按事件电压更新 selector；
- 对应的 RK3568 write 函数仍不检查 `regmap_write()` 返回值。

因此 G4 不只在 probe 时有 selector 写入；如果后续 regulator framework 发生电压变化，还可能再次写 PMU GRF。G4 实机试验期间必须避免引入额外 voltage-change 操作。

## 6. G4 的真实作用范围与隔离边界

启用 `pmu_io_domains` 节点不是“只打开 GMAC1 VCCIO5”。驱动会处理 DTS 声明的全部 PMU IO-domain supplies，并写多个 bank 的 selector。即使 G3 DTB 已禁用 TF/eMMC、SDIO、GPU、SARADC、GMAC1 等控制器，IO-domain probe 仍按自身 DTS supply properties 遍历并处理这些电压域。

因此后续 G4 candidate 必须：
- 只恢复 `CONFIG_ROCKCHIP_IODOMAIN=y` 和 `pmu_io_domains` 节点；
- 保持 GMAC1/MDIO/PHY、eMMC、TF SDMMC0、SDIO、GPU、SARADC 等节点继续 disabled；
- 不恢复任何下游 peripheral consumer；
- 不做 suspend/resume，不触发 regulator voltage changes；
- 在操作计划中列明全部 VSEL0/1/2 预期写值及部分失败残留风险。

该隔离可减少外围变量，但不会把 IO-domain driver 的 9-supply/多 bank 写入缩减为单一 VCCIO5 写入。

## 7. 黄金基线对照结论

| 对照项目 | 结果 |
|---|---|
| 6.1.65 candidate ↔ 6.1.116 io-domain.c | 整个文件 blob SHA 相同 |
| 6.1.116 ↔ 6.18.63 RK3568 write/data/notifier/probe 函数 | 函数体完全相同 |
| 6.1.65 candidate ↔ 6.1.116 Panther board DTS | 整个 DTS blob SHA 相同 |
| 三个版本 `&pmu_io_domains` block | 完全相同 |
| 三个版本 `vcc_3v3: SWITCH_REG1` block | 完全相同 |
| 6.18 与黄金 `&gmac1` block | 功能属性相同，仅注释有差异 |
| 黄金整机 Ethernet 正常是否等于 IO-domain 独立 PASS | 否；无独立 IO-domain bind/readback 证据 |

没有发现 6.18 新增的 RK3568 IO-domain 代码 regression。当前风险来自 stock driver 既有的多域写入、错误返回值未检查、部分失败无 GRF rollback，以及 regulator framework 电压值不等于实体 rail 测量；这些不是 6.18 新增差异。

## 8. G4 阶段判定与后续门

### 已完成
- G4-S：**PASS（静态源码/DTS/黄金基线对照）**。
- G3-P：RK809 regulator provider 已实机绑定，16 个 provider regulator 对象已注册。

### 尚未完成
- G4-P：IO-domain consumer 未启动、未 bind、未写 GRF；**HOLD / NOT AUTHORIZED**。
- PMU GRF VSEL0/VSEL1/VSEL2 实际值与写入 readback：未验证。
- SWITCH_REG1 实际 enable state/输出电压：未验证。
- 9 个 supply 在 consumer 侧实际 resolve 与 `regulator_get_voltage()` 返回值：未验证。
- deferred-probe 最终状态：未验证。

### 下一项建议：G4-B build-only candidate

在 Actions runner 上准备一个独立 build-only candidate：
1. 复用 G3 已锁定的 Linux 6.18.63 source、G3 Image/config/DTB 输入及固定 BusyBox/U-Boot 支持资产；
2. 只增加 `CONFIG_ROCKCHIP_IODOMAIN=y`，并将 `pmu_io_domains` 节点恢复为 `okay`；
3. 继续保持 GMAC1/MDIO/PHY、eMMC、TF SDMMC0、SDIO、GPU、SARADC disabled；
4. 检查最终 config、`io-domain.o` / `rockchip_iodomain_probe` 符号、DTS status、全部隔离节点、输入输出 SHA256；
5. 只生成 PREPARE-ONLY artifact，不写任何物理介质、不启动 Panther X2。

G4-B 只证明 build/link 与隔离资产正确，不触发 probe，不访问 PMU GRF。G4-P 需要另行提交完整写入清单、只读 readback 方案、失败停止/回退说明，并取得用户对该次 IO-domain probe/GRF 写入的明确授权。

**ABCD：NOT EXECUTABLE。** 目标 GMAC1/netdev 仍保持 disabled；不执行帧发送。
