# Panther X2 项目 A — G0.3 IO-domain Supplier / Deferred-probe / GMAC1 Bank 映射审计（2026-11-26）

- 状态：**G0.3 静态拓扑与写入路径 COMPLETE；R1 deferred-probe 最终重试/绑定状态 UNKNOWN；条件结项。**
- 范围：冻结 6.18.63 / 6.1.65 候选源码、DTS、R1 已归档日志摘要及 Rockchip RK3568 Hardware Design Guide Rev V1.2 的只读交叉核验。
- 未执行：未启动设备、未读取或写入 GRF/PMIC、未启用 regulator/IO-domain consumer、未恢复 GMAC、未发送测试帧。
- 固定源码端点：6.18.63 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`；6.1.65 候选 `unifreq/linux-6.1.y@4428b96f34a16e9a0beeed1dcb0ae3d4326145fc`。

## 1. R1 已有运行时证据与限制

1. R1 最终 `.config`：`CONFIG_ROCKCHIP_IODOMAIN=y`；`rockchip_iodomain_probe`、`rockchip_iodomain_write` 存在于 `System.map`，证明 IO-domain driver built-in。
2. 同一 R1 最终配置没有启用 `CONFIG_MFD_RK8XX_I2C`、`CONFIG_REGULATOR_RK808`，modules archive 也没有对应模块对象。
3. R1 启动日志摘要记录 MMC、SARADC、IO-domain 等设备等待 `/i2c@fdd40000/pmic@20/regulators/...` supplier 并进入 deferred-probe；I2C0 与 RK809 client DT 节点存在，但 MFD/regulator provider 未构建。
4. 冻结 `rockchip_iodomain_probe()` 先取得 GRF regmap，再按 `soc_data_rk3568_pmu.supply_names[]` 顺序调用 `devm_regulator_get_optional()`。缺 provider 时 `-EPROBE_DEFER` 直接退出，早于 `regulator_get_voltage()` 和 `iod->write()`。因此**该次因缺 provider 退出的 probe 没有执行 IO-domain GRF 写入**。
5. 现有归档只保留 deferred-probe 摘要，未保留完整的每个 consumer 日志行，也没有后续 deferred-probe 重试和最终 bind 状态。因此不能说 IO-domain “一直未绑定”，也不能说它最终成功。

## 2. RK3568 PMU IO-domain supply 顺序与 Panther DTS 映射

6.18.63 的 `soc_data_rk3568_pmu` 定义 9 个供电索引：

| supply index | driver supply name | Panther DTS supply phandle | 软件意图电压/说明 | driver write 行为 |
|---:|---|---|---|---|
| 0 | pmuio1 | vcc3v3_pmu | 3.3V PMUIO1 | index 0 不写 VSEL |
| 1 | pmuio2 | vcc3v3_pmu | 3.3V PMUIO2 | 写 PMU_GRF_IO_VSEL2 |
| 2 | vccio1 | vcc_3v3 | 3.3V | 写 VSEL0/VSEL1 |
| 3 | vccio2 | vcc_1v8 | 1.8V | index 3 不写 VSEL；硬件 FLASH_VOL_SEL 决定 |
| 4 | vccio3 | vccio_sd | 由对应 rail selector/配置决定 | 写 VSEL0/VSEL1 |
| 5 | vccio4 | vcc_1v8 | 1.8V | 写 VSEL0/VSEL1 |
| 6 | vccio5 | vcc_3v3 | 3.3V | 写 VSEL0/VSEL1 |
| 7 | vccio6 | vcc_3v3 | 3.3V | 写 VSEL0/VSEL1 |
| 8 | vccio7 | vcc_3v3 | 3.3V | 写 VSEL0/VSEL1 |

说明：
- 这是 DTS/driver 的软件拓扑与预期值，不是实际 rail 电压测量。
- vcc_3v3 在 RK809 regulator 子树中对应 SWITCH_REG1；它同时被 GMAC1 的 `phy-supply` 与 PMU IO-domain 的 `vccio5-supply` 引用。
- `vcc3v3_pmu`、`vccio_sd` 的真实供电来源仍按对应 DTS regulator 节点追踪；本报告不将其他存储/无线 consumers 纳入项目 A 功能测试。

## 3. 关键发现：Panther GMAC1 M0 明确落在 VCCIO5

板级 GMAC1 节点选择：
`gmac1m0_miim`、`gmac1m0_tx_bus2`、`gmac1m0_rx_bus2`、`gmac1m0_rgmii_clk`、`gmac1m0_clkinout`、`gmac1m0_rgmii_bus`。

RK3568 pinctrl 定义显示这些 M0 信号全部位于 GPIO3：
- MIIM: GPIO3_PC4/PC5；
- CLKINOUT: GPIO3_PC0；
- RX: GPIO3_PB1/PB2/PB3、GPIO3_PA4/PA5；
- TX: GPIO3_PB5/PB6/PB7、GPIO3_PA2/PA3；
- RGMII clocks: GPIO3_PA6/PA7。

Rockchip RK3568 Hardware Design Guide Rev V1.2 §2.3.12 的 GMAC1 M0 pin map 明确标注其电源域为 **VCCIO5**。板级 PHY reset GPIO `GPIO3_PA1` 同属 GPIO3 bank，因此也属于该 GPIO bank 的 VCCIO5 电平域。

因此，项目 A 的主要 IO-domain 关系已经明确：

```text
RK809 SWITCH_REG1 (DTS regulator name: vcc_3v3)
       ├── pmu_io_domains / vccio5-supply
       │       └── VCCIO5 selector (PMU GRF)
       │               └── GMAC1 M0 / GPIO3 pin bank
       │
       └── GMAC1 / phy-supply
               └── RTL8211F PHY power input (board-level supply path)
```

这是一条重要的共享供电链：同一 vcc_3v3/SWITCH_REG1 在软件描述中既提供 GMAC1 M0 的 VCCIO5 电平参考，也提供 PHY supply。**但 DTS phandle 不能证明板上实际供电连接、电压稳定性或 PHY 引脚处电压。** 仍须以原理图/板级实测确认。

## 4. RK3568 IO-domain 写入行为（不能视为只读 consumer）

6.18.63 `rk3568_iodomain_write()` 对 VCCIO5（supply index 6）计算：
- `b = index - 1 = 5`；
- 当 regulator_get_voltage 返回 3.3V（大于 1.8V threshold）时，`is_3v3=1`；
- 对 PMU GRF `RK3568_PMU_GRF_IO_VSEL0=0x0140` 写 high-word mask/value `0x00200000`；
- 对 `RK3568_PMU_GRF_IO_VSEL1=0x0144` 写 high-word mask/value `0x00200020`。

这两次 regmap_write 是该驱动为 VCCIO5 选择 3.3V IO 电平的程序动作。它不是 PMIC rail enable，也不会自行把 SWITCH_REG1 打开；它根据 regulator 报告的电压设置 SoC IO-domain selector。

**安全含义：** 在未来允许 consumer probe 之前，必须先确认 SWITCH_REG1 已提供真实且稳定的 3.3V；regulator framework 返回 3.3V selector 值不能替代外部电压测量。VCCIO5 selector 与硬件供电不匹配可能导致 IO 不工作或长期过压风险。不能仅为了消除 defer 就允许该驱动写入。

## 5. 黄金基线与版本比较

- 6.1.65 候选 DTS 与 6.18.63 DTS 的 `&pmu_io_domains` supply phandle 拓扑相同；两者均将 vccio5 指向 vcc_3v3。
- 6.1.65 候选源码与 6.18.63 的 RK3568 PMU IO-domain supply index、VSEL 写入函数核心语义一致；本轮未发现明确的 6.18 regression。
- 6.1.65 整机有线网络正常是集成行为证据；但没有单独的 IO-domain consumer probe、VCCIO5 selector readback 或实际电压测量记录，不能推断该节点每次启动都执行过写入或独立验证成功。
- 6.1.65 原始 DTB 的 PMIC/IO-domain 完整二进制对照仍需在 R7-A 硬件准入前完成；本节 DTS 对照仍是候选源码级证据。

## 6. G0.3 结论

| 项目 | 状态 |
|---|---|
| R1 IODOMAIN built-in 配置/对象 | 已验证 |
| R1 曾发生 regulator supplier deferred-probe | 已验证（日志摘要） |
| 本次 defer 路径未进入 GRF 写入 | 源码控制流可证明 |
| 后续 deferred-probe 最终状态 | UNKNOWN |
| PMU IO-domain 9 个 supply 索引与 DTS 映射 | 静态确认 |
| GMAC1 M0 → GPIO3 → VCCIO5 | 静态确认（Rockchip pin map + DTS pinctrl） |
| VCCIO5 / PHY supply 共用 vcc_3v3 / SWITCH_REG1 | DTS 静态确认 |
| VCCIO5 selector 实际状态与 3.3V rail 实测 | NOT VERIFIED |
| 6.1.65 原始 DTB PMIC/IO-domain 二进制对照 | PENDING |

**判定：G0.3 STATIC COMPLETE / RUNTIME CONDITIONAL。不是硬件 FAIL，不是网络 FAIL；IO-domain 仍未放行实机 consumer probe。**

## 7. 下一步唯一任务：G0.4

进入 G0.4，只读梳理 GMAC1 M0 相关的 CRU clock、reset、PHY reset、VCCIO5/PHY 供电和 125MHz 时钟物理来源。优先利用已有 R6 证据，避免重审已完成的 GRF bit7/DTB核心属性。重点回答：
1. GMAC1 所有时钟的 parent/rate/enable 与外部 fixed-clock 的关系；
2. 125MHz 输入时钟可能的板级来源，DTS 未声明的连线必须标为 UNKNOWN；
3. GPIO3_PA1 PHY reset 与 VCCIO5 的 bank 关系、极性和时序；
4. 进入 R7-A 前需要的最小外部电气测量点和安全观察方法。

G0.3 完成过程中未访问设备、未读取/写入 PMU GRF、未读取/写入 PMIC、未执行任何 GPIO/reset/clock 操作，也未发送 ABCD 测试帧。
