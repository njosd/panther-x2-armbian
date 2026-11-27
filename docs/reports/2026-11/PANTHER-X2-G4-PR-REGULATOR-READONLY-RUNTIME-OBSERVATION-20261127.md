# Panther X2 项目 A — G4-P-R Provider / Regulator 只读运行时观察（2026-11-27）

- 状态：**只读观察完成；不构成 G4-P 放行。**
- 当前运行环境：Panther X2 6.18.63+，shell 标识 `panther-x2-g3-provider-runtime`。
- 本轮目标：在不启动 IO-domain consumer、不触发 PMU GRF 写入的前提下，盘点已存在 RK809 regulator provider、供电映射及 framework 可读状态。
- 范围：只读取现有 procfs/sysfs 属性与目录；没有挂载 debugfs，没有读取或写入 PMIC 原始寄存器/GRF/MMIO，没有启停 regulator，没有修改 DTB、内核、驱动或系统配置。
- 存储边界：本轮未写入 TF/eMMC；SN64G 与 eMMC 未触碰。

## 1. 运行时接口环境

实机输出确认：

- 内核：`Linux 6.18.63+ #1 SMP Fri Nov 27 11:12:32 UTC 2026 aarch64`。
- `/proc/mounts` 仅列出 rootfs、proc、sysfs；debugfs 未挂载。
- `/sys/kernel/debug/regmap` 与 `/sys/kernel/debug/regulator` 当前不存在。
- `/sys/class/regulator` 存在多个注册对象。
- 平台设备 `rk808-regulator.3.auto` 的 `driver` symlink 指向 `rk808-regulator`，provider 已绑定。
- 由于 BusyBox 环境缺少 `grep` 与 `[`，首轮复杂脚本中的 UNAVAILABLE 分支输出无效；后续以分段 `ls`、`cat` 的原始结果为准。

## 2. RK809 regulator 实例映射

RK809 provider 下实机列出 16 个 regulator 实例：

| class 编号 | 名称 | OF 节点 | 是否属于 PMU IO-domain 九路供电 |
|---:|---|---|---|
| 5 | `vdd_logic` | 未逐项读取 | 否 |
| 6 | `vdd_gpu` | 未逐项读取 | 否 |
| 7 | `vcc_ddr` | 未逐项读取 | 否 |
| 8 | `vdd_npu` | 未逐项读取 | 否 |
| 9 | `vcc_1v8` | `DCDC_REG5` | 是 |
| 10 | `vdda0v9_image` | 未逐项读取 | 否 |
| 11 | `vdda_0v9` | 未逐项读取 | 否 |
| 12 | `vdda0v9_pmu` | 未逐项读取 | 否 |
| 13 | `vccio_acodec` | 未逐项读取 | 否 |
| 14 | `vccio_sd` | `LDO_REG5` | 是 |
| 15 | `vcc3v3_pmu` | `LDO_REG6` | 是 |
| 16 | `vcca_1v8` | 未逐项读取 | 否 |
| 17 | `vcca1v8_pmu` | 未逐项读取 | 否 |
| 18 | `vcca1v8_image` | 未逐项读取 | 否 |
| 19 | `vcc_3v3` | `SWITCH_REG1` | 是 |
| 20 | `SWITCH_REG2` | 未逐项读取 | 否 |

上述 OF 节点信息仅对本轮明确检查过的 regulator.9/.14/.15/.19 记录；其他实例未逐项解析其 OF 节点。

## 3. PMU IO-domain 九路 supply 与 provider 对应

复用 G0.3 已归档的 driver supply index / Panther DTS phandle 映射，并以本轮实机 regulator 名称核对：

| driver index | supply | DTS regulator | 实机 class | 本轮观察 |
|---:|---|---|---:|---|
| 0 | pmuio1 | `vcc3v3_pmu` | regulator.15 | enabled；num_users=1；3,300,000 µV |
| 1 | pmuio2 | `vcc3v3_pmu` | regulator.15 | enabled；num_users=1；3,300,000 µV |
| 2 | vccio1 | `vcc_3v3` | regulator.19 | enabled；num_users=0；无 `microvolts` 属性 |
| 3 | vccio2 | `vcc_1v8` | regulator.9 | enabled；num_users=1；1,800,000 µV |
| 4 | vccio3 | `vccio_sd` | regulator.14 | enabled；num_users=1；3,300,000 µV |
| 5 | vccio4 | `vcc_1v8` | regulator.9 | enabled；num_users=1；1,800,000 µV |
| 6 | vccio5 | `vcc_3v3` | regulator.19 | enabled；num_users=0；无 `microvolts` 属性 |
| 7 | vccio6 | `vcc_3v3` | regulator.19 | enabled；num_users=0；无 `microvolts` 属性 |
| 8 | vccio7 | `vcc_3v3` | regulator.19 | enabled；num_users=0；无 `microvolts` 属性 |

九路 supply 引用四个不同 regulator 对象。四个目标对象的 `state` 均报告 `enabled`。

## 4. 电压与状态读数的证据边界

已读到的属性：

| regulator | name | state | num_users | microvolts |
|---|---|---|---:|---:|
| .15 | vcc3v3_pmu | enabled | 1 | 3300000 |
| .19 | vcc_3v3 | enabled | 0 | 属性不存在 |
| .9 | vcc_1v8 | enabled | 1 | 1800000 |
| .14 | vccio_sd | enabled | 1 | 3300000 |

解释限制：

1. `microvolts` 是 regulator framework/driver 的软件回报值，不是万用表或示波器的 rail 实测。
2. `state=enabled` 是 framework/driver 回报的使能状态；不证明物理 rail 的电压精度、纹波或负载能力。
3. `num_users` 是 framework 的软件引用计数，不等于实际硬件消费者数或电流负载。
4. `vcc_3v3` 对应 SWITCH_REG1，当前 sysfs 没有 `microvolts`、`min_microvolts`、`max_microvolts` 属性；不能从 regulator 名称或 DTS 目标值反推实际输出电压。
5. regulator.15/.9/.14 暴露 `microvolts`，但本轮只读取其当前值，没有读取 suspend 电压属性。

## 5. 与 G0.3 的关系

G0.3 已静态确认：
- RK3568 PMU IO-domain 有 9 个 supply index；
- VCCIO5（index 6）指向 `vcc_3v3` / RK809 SWITCH_REG1；
- GMAC1 M0 → GPIO3 → VCCIO5；
- 成功执行 IO-domain consumer probe 会对 PMU GRF VSEL0/VSEL1 执行写入（VCCIO5 对应寄存器 offset 0x0140/0x0144）。

本轮补充了 provider 侧的实机 sysfs 映射与软件状态，但没有读取 PMU GRF VSEL0/1/2，也没有证明 IO-domain consumer 当前是否 bind/是否已执行 selector 写入。

## 6. 阶段状态与未完成项

- 已验证：当前 G3 provider runtime 环境中的 RK809 regulator provider 已绑定。
- 已验证：16 个 regulator 实例名称；其中九路 IO-domain supply 对应的四个对象已完成映射。
- 已验证：四个目标 regulator 的 framework `state` 均报告 enabled。
- 已验证：三路可读 regulator 的软件电压回报分别为 3.3V、1.8V、3.3V。
- 未验证：SWITCH_REG1 / `vcc_3v3` 实际电压。
- 未验证：PMU GRF VSEL0/VSEL1/VSEL2 当前值。
- 未验证：IO-domain consumer 的当前 bind 状态及历史 selector 写入状态。
- 未验证：任何 rail 的物理输出、纹波或负载。
- G4-S PASS、G4-B PASS、G4-P NO-GO 为当前阶段既定状态；本报告只归档 provider 侧只读观察，**不将 G4-P 改判为 PASS，也不构成 G4-P-SAFE patch 或 IO-domain consumer probe 授权**。

## 7. 下一步只读工作

先识别当前 sysfs 中已注册 syscon 对应的设备树节点身份，重点区分 PMU GRF 与普通 GRF：

- 对候选 syscon 的 `of_node` 目录只列出属性文件；
- 读取 `name`、`compatible` 等设备树描述属性；
- 必要时以只读方式解析 `reg` 属性地址范围；
- 不读取 MMIO 寄存器，不使用 `devmem`，不挂载 debugfs，不主动触发 regmap 访问，不启用 IO-domain consumer。

完成 syscon 身份核对后，再判断是否存在已开放且不改变运行环境的只读 VSEL 观察入口。若不存在，则保留 UNKNOWN，不绕过框架直接访问寄存器。

## 8. 操作记录

- 本轮只读检查发生在 `panther-x2-g3-provider-runtime` shell 环境。
- 没有安装软件、没有修改内核/驱动/DTB/Kconfig/网络配置。
- 没有挂载 debugfs。
- 没有写入或读取 PMIC 原始寄存器、GRF/MMIO。
- 没有启停 regulator、GPIO、clock、reset 或 IO-domain consumer。
- 没有执行网络发送测试。
- 没有写入 TF/eMMC；SN64G/eMMC 未触碰。
