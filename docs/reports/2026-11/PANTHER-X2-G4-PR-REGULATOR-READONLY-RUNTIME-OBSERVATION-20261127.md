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

## 7. Syscon / PMU GRF 设备树身份核对（2026-11-27）

本轮继续只读检查 `/sys/bus/platform/devices` 与 `/sys/firmware/devicetree/base`，没有访问 MMIO。

### 7.1 七个 syscon 节点身份

七个目录均存在，且对应 platform device 的 `of_node` 指向相应设备树节点。设备树目录均包含 `name`、`phandle`、`reg`、`compatible` 属性；其中 `fdc20000` 另有 `io-domains` 子目录。

| 设备树节点 | compatible | name | 识别 |
|---|---|---|---|
| `syscon@fdc20000` | `rockchip,rk3568-pmugrf` | `syscon` | PMU GRF |
| `syscon@fdc50000` | `rockchip,rk3566-pipe-grf` | `syscon` | PIPE GRF |
| `syscon@fdc60000` | `rockchip,rk3568-grf` | `syscon` | 主 GRF |
| `syscon@fdc80000` | `rockchip,rk3568-pipe-phy-grf` | `syscon` | PIPE PHY GRF |
| `syscon@fdc90000` | `rockchip,rk3568-pipe-phy-grf` | `syscon` | PIPE PHY GRF |
| `syscon@fdca0000` | `rockchip,rk3568-usb2phy-grf` | `syscon` | USB2 PHY GRF |
| `syscon@fdca8000` | `rockchip,rk3568-usb2phy-grf` | `syscon` | USB2 PHY GRF |

`fdc20000` 的 `compatible=rockchip,rk3568-pmugrf`，并具有 `io-domains` 子节点；与本项目此前静态审计的 PMU IO-domain / PMU GRF 关系吻合。该节点身份已由设备树属性直接确认，不再只是按地址推测。

### 7.2 当前 platform-device 状态

- 七个 syscon platform-device 目录均未显示 `driver` symlink；这不能用于判断 regmap 是否存在，因为通用 syscon 的 regmap 可由 consumer 通过 `syscon_node_to_regmap()` 懒创建，并不依赖 syscon platform driver bind。
- `/sys/bus/platform/devices/fdc20000.syscon/waiting_for_supplier` 的实机读取值为 `0`。这只说明该父 platform device 的该属性当前报告为 0，不等价于 IO-domain child 已绑定，也不证明 PMUGRF regmap 当前可用。
- 设备树节点存在、platform device 已枚举、supplier-wait 状态为 0，均不能代替驱动绑定和寄存器访问能力的验证。

### 7.3 本轮结论与边界

- **已验证：** PMU GRF 对应设备树节点为 `fdc20000`，compatible 为 `rockchip,rk3568-pmugrf`；其下存在 `io-domains` 子节点。
- **已验证：** 其余六个 syscon 节点的 compatible 已读取并归类。
- **已验证：** `fdc20000.syscon/waiting_for_supplier=0`。
- **未验证：** syscon platform driver 是否可绑定、regmap 是否注册、是否存在无需改变运行环境的只读 VSEL 访问接口。
- **未验证：** PMU GRF VSEL0/VSEL1/VSEL2 当前值；没有进行任何 MMIO 读取。
- **未验证：** IO-domain consumer 当前 bind 状态及历史 selector 写入状态。

因此，当前仍没有安全、已开放的 PMU GRF VSEL 只读入口证据。不得为取得读数而挂载 debugfs、调用 devmem、直接访问 MMIO、触发 IO-domain consumer probe 或引入会执行 selector 写入的路径。G4-P 继续 NO-GO；G4-P-SAFE patch 继续 deferred。

## 8. 操作记录

- 本轮只读检查发生在 `panther-x2-g3-provider-runtime` shell 环境。
- 没有安装软件、没有修改内核/驱动/DTB/Kconfig/网络配置。
- 没有挂载 debugfs。
- 没有写入或读取 PMIC 原始寄存器、GRF/MMIO。
- 没有启停 regulator、GPIO、clock、reset 或 IO-domain consumer。
- 没有执行网络发送测试。
- 没有写入 TF/eMMC；SN64G/eMMC 未触碰。


## 9. 本轮补充操作记录

- 只读取七个 syscon platform-device 目录及其设备树 `name`/`compatible` 属性，并读取 `fdc20000.syscon/waiting_for_supplier`。
- 没有读取设备树 `reg` 二进制属性，没有进行 MMIO/GRF/regmap 读取。
- 没有挂载 debugfs，没有执行 devmem，没有触发 syscon/IO-domain consumer probe。
- 没有写入 TF/eMMC；SN64G 与 eMMC 未触碰。


## 10. 6.18.63 syscon / IO-domain 源码路径复核（2026-11-27）

固定源码：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`。本节为仓库源码只读审计，不涉及设备操作。

### 10.1 为什么 syscon platform device 没有 driver symlink

`arch/arm64/boot/dts/rockchip/rk356x-base.dtsi` 定义：

- `pmugrf: syscon@fdc20000`
- compatible：`rockchip,rk3568-pmugrf`, `syscon`, `simple-mfd`
- 子节点 `io-domains` compatible：`rockchip,rk3568-pmu-io-voltage-domain`

`drivers/mfd/syscon.c` 中：
- `syscon_node_to_regmap(np)` 调用 `device_node_get_regmap()`；
- 如果 syscon list 中尚无该节点，且节点含通用 compatible `syscon`，会调用 `of_syscon_register()`；
- `of_syscon_register()` 通过 `of_iomap()` 建立 MMIO 映射，再通过 `regmap_init_mmio()` 创建 regmap 并登记到内部 syscon list。

因此 syscon regmap 是由 consumer API 按需取得/创建的机制；syscon 节点没有 platform driver symlink 并不异常，也不能作为 regmap 不存在的证据。创建 regmap/MMIO mapping 本身不等于已经读取 VSEL 寄存器。

### 10.2 R2 pinctrl 证据边界纠正

`drivers/pinctrl/pinctrl-rockchip.c` 的 `rockchip_pinctrl_probe()`：
- 对 `rockchip,grf` phandle 调用 `syscon_node_to_regmap()`，并检查错误；R2 pinctrl 成功绑定证明 main-GRF lookup 成功。
- 对 `rockchip,pmu` phandle 调用 `syscon_regmap_lookup_by_phandle_optional()`，但 probe 没有紧接着检查该返回值是否为错误指针。

所以此前把 R2 pinctrl bind 概括成“GRF/PMU 两路 syscon consumer 均成功”是不严谨的。已在 R2 报告中纠正：**main-GRF lookup PASS；PMUGRF lookup 仍未独立验证**。虽然 RK3568 pinctrl 的 GPIO0 IOMUX/pull/drive/schmitt 路径会使用 PMUGRF regmap，但 R2 没有执行这些 PMUGRF 读写。

### 10.3 IO-domain child 的真实 probe 顺序与副作用

`drivers/soc/rockchip/io-domain.c` 的 RK3568 匹配数据包含九路 supply；probe 首先从父节点获取 PMUGRF regmap，然后逐路执行：
1. `devm_regulator_get_optional()`；
2. 对成功取得的 regulator 调用 `regulator_get_voltage()`；
3. 设置 supply index / notifier；
4. 调用 `iod->write(supply, uV)`；
5. 注册 regulator notifier。

RK3568 VCCIO5（index 6）会走 `rk3568_iodomain_write()`，向 PMU GRF VSEL0/VSEL1 写入 high-word-mask selector 值。因此不能为了“看看 probe 是否成功”而触发该 consumer；它不是纯读取探测。

父节点 `fdc20000.syscon/waiting_for_supplier=0` 不能替代 IO-domain child 的 driver/bind 状态。当前 G3 provider runtime 尚未取得 IO-domain child 的 sysfs bind 证据。

### 10.4 当前修正结论

- **已验证：** PMUGRF DT node 身份、generic `syscon` compatible、simple-mfd 子节点关系。
- **已由源码验证：** syscon regmap 懒创建机制；无 platform driver symlink 不等于 regmap 不存在。
- **已验证：** R2 main-GRF lookup 成功。
- **未验证：** 当前 G3 runtime 中 PMUGRF regmap 是否已成功创建；R2 optional PMUGRF lookup 是否成功。
- **未验证：** IO-domain child 当前是否 bind；没有读 VSEL0/1/2。
- **安全边界：** 不触发 IO-domain probe、不挂载 debugfs、不使用 devmem、不直接访问 MMIO。G4-P 继续 NO-GO，G4-P-SAFE patch deferred。
