# Panther X2 B2-1 / R3：RK809 / I2C / Regulator 前置审计（2026-11-26）

## 1. 状态与范围

**状态：R3 静态审计完成；运行时验收 HOLD/BLOCKED；R3 整体未通过，不放行 R4。**

本轮只读核验：
- 复用既有 6.18.63 Kconfig/Makefile 与 GMAC PHY supply 静态审计；
- 直接解包 R1 最终 Actions artifact，核对最终 `.config`、`modules.builtin`、模块归档和实际编译 DTB；
- 解析 R1 最终 DTB 的 I2C0、RK809、SWITCH_REG1 与 GMAC1 `phy-supply` phandle；
- 从 Dropbox 原始 `kernel-config-evidence.zip` 复核 6.1.65 Golden 的最终配置和 built-in 对象；
- 复核 Linux 6.18.63 RK809 I2C/MFD/regulator 驱动 probe 路径及其副作用。

没有访问 Panther X2，没有启用 RK809 driver，没有发起 I2C/PMIC 事务，没有写 PMIC 寄存器，没有改变 regulator、reset 或电源状态；没有修改 Kconfig、源码、DTB、镜像或系统配置，没有构建或刷写新镜像。

## 2. R1 最终构建身份

R1 artifact：Actions run `45611898629`，job `139197305317`，artifact ID `15023630465`（`b2-1-r1-network-core`）。

- Kernel：Linux 6.18.63
- 源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`
- `kernel.config` SHA256：`480645537537abdadc9e2e07f404b85c1bc9411232df04ecb284c5270d2af23a`
- Image SHA256：`63cbb8bbb012186d568cdbd149d09571c75a43a403969885a696cb36361781f1`
- Panther DTB SHA256：`7aa4e8a15469bfdda828dcdaf4f4bfea546df378a0ebb040e0ef6df68585179d`
- `modules.tar.zst` SHA256：`4f403cac59809616cf4de36a8e89520ecffc13965597be4b8d88845fb3ce3787`

以上 hash 与 R1 artifact 内的验证清单一致。

## 3. R1 最终 .config 与对象核验

从 artifact 内实际 `output/kernel.config` 和 `output/modules.tar.zst` 提取：

| 符号/对象 | R1 最终状态 | 证据 |
|---|---|---|
| `CONFIG_I2C` | y | 最终 .config |
| `CONFIG_I2C_RK3X` | y | 最终 .config；`modules.builtin` 有 `i2c-rk3x.ko` |
| `CONFIG_REGMAP_I2C` | y | 最终 .config；`modules.builtin` 有 `regmap-i2c.ko` |
| `CONFIG_REGULATOR` | y | 最终 .config |
| `CONFIG_MFD_RK8XX_I2C` | not set | 最终 .config 明确为 not set |
| `MFD_RK8XX` core | 未构建 | `modules.builtin` 与模块归档无 `rk8xx-core` |
| `rk8xx-i2c` | 未构建 | `modules.builtin` 与模块归档无对应对象 |
| `REGULATOR_RK808` / `rk808-regulator` | 未构建 | 最终配置无启用项，`modules.builtin` 与模块归档无对应对象 |

**结论：** R1 已内建 RK3566 I2C controller 和 regmap-I2C 通用基础，但没有 RK8xx I2C/MFD parent 与 RK809 regulator driver。R1 尚不能提供完整 RK809 PMIC/regulator provider 链。

## 4. R1 最终 DTB 二进制解析结果

直接解析 artifact 内 `output/dtb/rockchip/rk3566-panther-x2.dtb`，不是仅凭源码 DTS 推断：

1. I2C0 节点：`/i2c@fdd40000`，`status = "okay"`。
2. RK809 节点：`/i2c@fdd40000/pmic@20`，`compatible = "rockchip,rk809"`，`reg = <0x20>`；节点未声明 disabled status。
3. RK809 的 regulator 子节点 `SWITCH_REG1`：`regulator-name = "vcc_3v3"`，phandle `0x19`；未声明 disabled status。
4. GMAC1：`/ethernet@fe010000`，`status = "disabled"`，`phy-supply = <0x19>`。
5. phandle 解析结果：GMAC1 的 `phy-supply` 精确指向 `/i2c@fdd40000/pmic@20/regulators/SWITCH_REG1`，不是名称相似推断。
6. `SWITCH_REG2` 仍为 `status = "disabled"`；MDIO 与 PHY 子节点也保持 disabled。

**结论：** R1 最终 DTB 中 I2C0/RK809/SWITCH_REG1 的拓扑和 phandle 引用正确；GMAC/MDIO/PHY 隔离状态保持不变。该静态证据不证明 I2C0 adapter 已在实机注册、RK809 有响应或 SWITCH_REG1 实际输出电压正常。

## 5. 6.1.65 Golden 对照

来源：Dropbox 原始归档 `/kernel-config-evidence.zip`，其中的 `config-6.1.65-ophub` 与 `modules.builtin`。

| 配置/对象 | 6.1.65 Golden | 6.18.63 R1 | 解释 |
|---|---|---|---|
| `I2C` | y | y | 相同 |
| `I2C_RK3X` | y | y | 相同，RK3x controller 已内建 |
| `REGMAP_I2C` | y | y | 相同 |
| `REGULATOR` | y | y | 相同 |
| `MFD_RK808` | y | 旧符号不再沿用 | 6.18 改为 RK8xx core + I2C transport 分层 |
| `MFD_RK8XX_I2C` | 不适用旧版符号 | not set | 6.18 新 transport driver 尚未启用 |
| `REGULATOR_RK808` | y | 未构建 | 6.18 对应驱动依赖 MFD_RK8XX |
| built-in 对象 | `rk808.ko`、`rk808-regulator.ko`、`i2c-rk3x.ko`、`regmap-i2c.ko` | `i2c-rk3x.ko`、`regmap-i2c.ko`；无 RK8xx MFD/regulator 对象 | Golden 包含完整 PMIC 链，R1 只保留 I2C 通用基础 |

6.1.65 的 Panther X2 有线网络实机成功是该整机组合的正向集成证据；它不等于已经独立执行 RK809 ID、每个 regulator 或实际 rail 电压测试。6.1.65 原始内核的精确源码构建 commit 仍未达到二进制级绑定，因此本报告只比较已归档的真实 config/built-in 证据，不宣称两版源码实现完全相同。

## 6. 6.18.63 精确依赖闭包

固定源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`。

- `I2C_RK3X`：依赖 `OF && COMMON_CLK`；Makefile 对象 `i2c-rk3x.o`。R1 已满足。
- `MFD_RK8XX_I2C`：依赖 `I2C && OF`，select `MFD_CORE`、`REGMAP_I2C`、`REGMAP_IRQ`、`MFD_RK8XX`；Makefile 对象 `rk8xx-i2c.o`。
- `MFD_RK8XX`：core 对象 `rk8xx-core.o`。
- `REGULATOR_RK808`：depends on `MFD_RK8XX`；Makefile 对象 `rk808-regulator.o`。
- Generic `REGULATOR`、`REGMAP_I2C`、`I2C`、`I2C_RK3X` 已在 R1 为 y。

若后续获准引入完整 provider，静态上最小的显式配置缺口为 `MFD_RK8XX_I2C=y` 与 `REGULATOR_RK808=y`；`MFD_RK8XX`、`MFD_CORE`、`REGMAP_IRQ` 等按 Kconfig select/dependency 闭合。**本轮没有应用这些配置，也没有生成新构建。**

## 7. 关键安全发现：RK809 driver probe 并非只读

源码复核发现，不能把“加载 RK809 driver”当作只读识别：

- `rk8xx_i2c_probe()` 根据 DT compatible 匹配 RK809 variant，初始化 regmap 后调用 `rk8xx_probe()`。
- 对 `RK809_ID`，`rk8xx_probe()` 选择 `rk817_pre_init_reg`。
- probe 随后循环执行 `regmap_update_bits()`，逐项写入该 pre-init 表。
- 该表至少包含 `RK817_RTC_CTRL_REG` 的 `RTC_STOP` 位写入，并包含多项 codec register 写入。

因此，若把 `MFD_RK8XX_I2C` 作为 built-in 加入当前 DTB 并启动，RK809 节点会自动匹配并进入 probe，probe 会对 PMIC 寄存器执行写操作。这与当前“禁止 I2C/PMIC 写入、不得改变电源状态”的安全边界冲突。此处尚无证据表明这些 pre-init 写入会切换 SWITCH_REG1/2 电源轨，但它们确实不是只读操作。

**停止条件：** 在没有单独批准 PMIC probe 副作用之前，不得把 RK809 MFD driver 以 built-in 方式加入 R1 启动镜像，不得启动该 driver，不得运行 regulator 操作或 PMIC 寄存器读取/写入测试。不得为了完成 R3 而弱化现有安全约束。

## 8. R3 分项状态

| 分项 | 当前状态 | 证据/限制 |
|---|---|---|
| R3 静态 DTB 拓扑与 phandle | PASS-STATIC | R1 最终 DTB 二进制已解析 |
| R3 Kconfig/Makefile 依赖 | PASS-STATIC | 6.18.63 精确源码已核对 |
| R3 R1 最终配置/对象 | PASS-STATIC | 真实 R1 artifact 已解包 |
| R3 6.1.65 Golden 配置/对象对照 | PASS-STATIC | Dropbox 原始 config 与 modules.builtin |
| R3.1 I2C0 controller bind / adapter 注册 | NOT TESTED | 可先用现有 R1 镜像只读 sysfs 核验，不触碰 PMIC |
| R3.2 RK809 稳定通信/ID read | BLOCKED | driver probe 有 PMIC 写操作；独立只读事务方案尚未获准 |
| R3.3 MFD/regmap parent/child | BLOCKED | 当前 R1 未构建 driver；启动 built-in driver 会触发上述写操作 |
| R3.4 regulator 注册 | BLOCKED | 当前 R1 未构建 driver；不操作 regulator |
| R3.5 现有安全 regulator consumer | NOT TESTED | 需先有安全的 provider 注册证据 |
| R3.6 GMAC PHY supply consumer | BLOCKED / R7-A | GMAC1 仍 disabled，按原计划留到 R7-A |
| R3.7 PMIC 状态寄存器只读观察 | BLOCKED | 先确认寄存器语义及无副作用的安全访问方法 |

**阶段结论：** R3 已完成静态配置、Golden 对照、实际 DTB 和 probe 副作用审计；运行时功能未通过，R3 整体保持 HOLD/BLOCKED，不放行 R4。下一项安全动作仅为在现有 R1 镜像上只读检查 I2C0 adapter 与 DT 创建的 RK809 client 节点；该动作不等于 PMIC 通信成功，也不会启用 RK809 driver。

## 9. 复用与新增证据

### 复用既有证据
- `PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md`：RK809 PHY supply provider 的 6.18.63 Kconfig/Makefile 链。
- `PANTHER-X2-GMAC-GLUE-CLOCK-POWER-SUPPLEMENTAL-AUDIT-20261124.md`：Panther `phy-supply` 指向 RK809 SWITCH_REG1；不把静态引用当作实测供电。
- `PANTHER-X2-B2-1-R2-SHARED-SOC-PROVIDER-AUDIT-20261126.md`：R2 PASS 与现有 R1 镜像只读 provider 证据。
- Dropbox `/kernel-config-evidence.zip`：6.1.65 Golden 原始配置与 built-in 清单。

### 本轮新增
- 直接解包 R1 artifact 15023630465，提取最终 .config、modules.builtin 和 DTB。
- 对 R1 最终 DTB 二进制解析 I2C0/RK809/SWITCH_REG1/GMAC1 phandle。
- 对照 6.1.65 Golden 的 RK809 相关 config 与 built-in 对象。
- 发现 6.18.63 RK809 MFD probe 会执行 `regmap_update_bits()`，确认它不能按只读步骤直接启用。

