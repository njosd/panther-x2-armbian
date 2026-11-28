# Panther X2 Project A — G4-P2 Pre-GMAC 供电与 IO-domain 安全审计（静态阶段记录，2026-11-28）

- 状态：**STATIC AUDIT IN PROGRESS / HOLD；无硬件授权**
- 目标：在 GMAC 仍 disabled 时，判断真实恢复 IO-domain supply / PHY supply 是否存在安全、可解释且与黄金基线一致的路径
- 本轮范围：固定源码、归档 Kconfig、既有 DTS/DTB 审计报告；不访问设备，不执行任何 regulator/PMIC/GRF/MDIO 操作

## 1. 本轮新确认的关键事实

### 1.1 6.1.65 黄金配置也启用了 ROCKCHIP_IODOMAIN

从 Dropbox 归档的 kernel-config-evidence.zip 通过只读内容提取，config-6.1.65-ophub 中：
- CONFIG_MFD_RK808=y
- CONFIG_REGULATOR_RK808=y
- CONFIG_ROCKCHIP_IODOMAIN=y

因此，6.1.65 黄金基线并非缺少 IO-domain driver 的配置组合。它包含 RK809 MFD/regulator 和 IO-domain driver。

### 1.2 6.1.65 与 6.1.116 的 PMIC/IO-domain 源码相同，且与 6.18 关键路径一致

既有报告 PANTHER-X2-G0-GOLDEN-65-116-PMIC-PHY-SOURCE-COMMONALITY-20261127.md 已用 Git blob SHA 证明：
- 6.1.65 与 6.1.116 的 drivers/regulator/rk808-regulator.c 逐字节相同；
- 两者的 drivers/soc/rockchip/io-domain.c 逐字节相同；
- 两者的 Panther X2 board DTS 逐字节相同。

本轮再对照固定源码端点 6.1.65 与 6.18.63：
- RK3568 PMU IO-domain supply 顺序相同：index 0–8 为 pmuio1、pmuio2、vccio1–vccio7；
- index 1 的 rk3568_iodomain_write 会对 PMU GRF IO_VSEL2 执行两次 hiword-mask write；
- index 2 vccio1 继续引用 SWITCH_REG1/vcc_3v3；
- RK809 SWITCH_REG1 使用 rk817_switch_ops，只有 enable/disable/is_enabled/suspend enable/disable，没有 get_voltage/get_voltage_sel/list_voltage；
- 两版 Panther DTS 均将 vccio1、vccio5、vccio6、vccio7 指向 vcc_3v3/SWITCH_REG1。

因此，已识别的“index 1 先写 VSEL2，index 2 取得 SWITCH_REG1 后无法读取电压而退出”的风险不是已证实的 6.18 新增 regression；它在 6.1.65/6.1.116 候选黄金源码中也存在。6.18 不能因此直接回退或伪造 SWITCH_REG1 voltage getter。

### 1.3 黄金系统网络正常不能证明 IO-domain consumer 曾成功 probe

两条黄金系统有正常 Ethernet 的独立实机证据，但现有归档没有：
- 6.1.65 原始 DTB 的 PMIC/IO-domain 子树完整 binary diff；
- 6.1.65/6.1.116 实际启动时 IO-domain child 的 runtime bind/probe 日志；
- PMU GRF VSEL0/1/2 readback 或 selector transaction trace；
- VCCIO5 实际 rail 电压测量。

所以不能从“黄金 Ethernet 正常”推断“黄金启动时九路 IO-domain supply 一定全部成功处理”。黄金系统可能没有进入该 consumer probe 路径；也可能存在实际 DTB/config/runtime 条件差异。当前证据不足以在这两种情况之间作出判断。

## 2. 现有 partial-write 风险的准确适用条件

固定 Linux 6.18.63 源码与两套黄金候选源码的控制流表明，只有在以下条件同时成立时，才会触发已识别的 partial-write：
1. PMU IO-domain child 被枚举并绑定 rockchip-iodomain；
2. DTB 为该 child 提供完整九路 supply；
3. RK809 regulator provider 成功注册并让 index 0/1 的 vcc3v3_pmu 获取、电压读取通过；
4. 后续 index 2 的 vcc_3v3/SWITCH_REG1 获取成功，但 regulator_get_voltage 无法从 descriptor ops、fixed_uV 或上游 supply 得到电压；
5. driver 因负电压返回错误，导致此前 index 1 的 selector write 不回滚。

该路径由静态源码与 provider/DTS 属性支持，但没有在本机实测触发。不能为了验证而启动 full-supply candidate。

G4-P0 binding-only 已证明另一条安全边界：child status okay、九路 supply 属性全部缺失时，driver 可绑定并取得 PMUGRF regmap，但不会进入 regulator voltage read/notifier/iodomain_write。该结果不证明 selector 已配置。

## 3. 当前可行路径评估

| 候选 | 当前判定 | 原因 |
|---|---|---|
| 恢复完整九路 supply 并启动 IO-domain | NO-GO | 已知 partial-write 风险未解除 |
| 只删除 SWITCH_REG1 的 supply 属性，其余保留 | NO-GO | index 0/1 等前置 supply 仍可能先写 selector；而 VCCIO5 bank selector也未得到验证 |
| 伪造 fixed-regulator / 固定 3.3V getter | REJECT | 没有独立电气证据支撑，可能掩盖真实 rail 状态 |
| 修改上游 IO-domain driver，遇到无 get_voltage 的 regulator 时跳过 selector | NOT ACCEPTED / NOT DESIGNED | 会改变内核源码和硬件配置语义；必须先证明 bank 当前电压与 selector 目标一致，并有黄金 DTB/runtime 证据，不能先 patch 再看能否启动 |
| 保持 IO-domain child disabled，先只评估 GMAC 的 PHY supply consumer | CONDITIONAL CANDIDATE ONLY | 可避免该 IO-domain probe 的 selector partial-write，但不能假设 VCCIO5 selector/default state 正确；须先与黄金真实 DTB/runtime 行为对照 |
| G4-P0 binding-only | 已验证 PASS | 仅作 binding 验证，不配置任何 bank selector |

## 4. G4-P2 当前阻塞项

在任何 R7-A 硬件候选前，必须补齐以下只读证据：
1. 6.1.65 原始 DTB 中 PMU IO-domain child 的实际 status、九个 supply properties 与相关 phandle；不重新提取完整 851 MiB 镜像，只使用已有 DTB 归档/阶段包。
2. 6.1.65 原始 config 中 ROCKCHIP_IODOMAIN 的 built-in 状态（当前已从 config-6.1.65-ophub 确认 y，但仍需与原始 Image/build identity 的限制一并记录）。
3. 6.1.116 实际 DTB 中 PMU IO-domain child status 与 supply properties 的精确解码；已知完整 DTB SHA256 与 6.18.63 某一归档 DTB 相同，但应从既有 tar 包/报告核对具体对象和解析结果，不从源码 DTS 推断。
4. 6.1.116 黄金启动日志是否包含 rockchip-iodomain probe、deferred-probe、regulator voltage 错误或对应成功记录；当前已归档日志尚未给出这项直接证据。
5. 若黄金 DTB 实际未启用 IO-domain child，确认黄金系统依赖的 selector/default state 来源属于 SPL/U-Boot、PMIC 初始化或 SoC reset default 中的哪一项；只能使用已有启动证据和源码静态审计，不擅自读写 PMUGRF。
6. 若黄金 DTB 确实启用 IO-domain child 且完整 supply，必须找到其成功条件与当前静态模型的差异；未找到之前不得声称黄金路径可复现。

## 5. 当前阶段决策

- G4-P1 共享基础 provider readiness：CONDITIONAL PASS（详见 G4-P1 报告）。
- G4-P2 供电/IO-domain safety：**HOLD / NOT PASS**。
- G4-P full nine-supply mapping：**NO-GO**。
- G4-P0 no-supply binding-only：PASS，已完成一次授权实机验证，不重复启动。
- R7-prep：仅 build-only 准备；尚未执行。
- R7-A/G5-A GMAC probe：NOT AUTHORIZED / NOT RUN。

**当前最稳妥决策：不恢复完整 IO-domain supply，不修改 regulator 语义，不手动操作 GPIO/reset/clock，不启动 GMAC。先完成黄金 DTB/config/runtime 证据对齐。** 如果黄金证据最终证明 IO-domain consumer 在正常系统中并未启用，则应优先保持该节点 disabled，避免人为引入一个黄金系统未依赖的风险路径；这仍需真实 DTB 证据确认，当前只是条件性方向，不是已定结论。

## 6. 安全边界

本报告只读取仓库固定源码、已有报告和 Dropbox 中的配置归档文本；没有下载或改写原始镜像，没有访问 Panther X2，没有启动设备，没有读取/写入 PMIC、GRF、GPIO、clock、reset、MDIO，没有启停 regulator，没有发送网络帧，没有写入 SU08G/SN64G/eMMC。
