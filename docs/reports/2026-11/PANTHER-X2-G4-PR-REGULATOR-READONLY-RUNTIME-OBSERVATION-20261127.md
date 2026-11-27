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


## 11. IO-domain 节点实际运行状态确认（2026-11-27）

本轮在同一 `panther-x2-g3-provider-runtime` 环境继续执行只读核对：

- `/sys/firmware/devicetree/base/syscon@fdc20000/io-domains/status` 的实际内容为 **`disabled`**。
- `/sys/bus/platform/devices/fdc20000.syscon/` 存在，父 syscon platform device 已枚举；其目录没有 `driver` symlink。
- `/sys/bus/platform/drivers/rockchip-iodomain` 整个目录不存在。
- 之前对 platform devices 的 IO-domain 名称通配查询无匹配项；当前没有对应 IO-domain platform child 的 sysfs 证据。

### 11.1 结合 6.18.63 源码的解释

固定源码 `ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9`：

- `rk356x-base.dtsi` 中 PMU GRF 父节点使用 `simple-mfd`，其 `io-domains` 子节点基础定义为 `status = "disabled"`。
- `of_platform_default_populate()` 通过匹配 `simple-mfd` 父节点创建其符合条件的子 platform device；disabled 子节点不会作为正常启用的 OF platform device 创建。
- `ROCKCHIP_IODOMAIN` 的 Kconfig 控制 `drivers/soc/rockchip/io-domain.c` 是否编入/注册驱动；但在当前设备树状态下，尚无必要把“驱动未编入”作为首要解释，因为 disabled 节点本身已足以解释当前没有 child device。

### 11.2 修正后的运行时结论

- **已验证：** 当前实际运行设备树将 PMU IO-domain 子节点设为 `disabled`。
- **已验证：** 当前 sysfs 中没有 IO-domain child platform device，也没有 `rockchip-iodomain` driver 目录。
- **高置信度解释：** disabled 状态阻止子设备正常枚举，因而没有 consumer probe；这也意味着本次运行环境没有通过该驱动执行 VSEL selector 写入。
- **仍未验证：** 实际启动 DTB 为什么保留 disabled；它与此前报告中记录的候选/冻结 DTB 节点启用状态是否存在镜像/DTB 版本偏差；`CONFIG_ROCKCHIP_IODOMAIN` 当前最终值。
- **未验证：** PMUGRF regmap 是否已创建、VSEL0/VSEL1/VSEL2 当前值、历史启动阶段是否曾有其他代码写入这些寄存器。

这纠正了第 5、7、10 节中“IO-domain consumer 当前 bind 状态未知”的部分：**就本次运行时设备树与 sysfs 状态而言，IO-domain consumer 没有被枚举，因而没有当前 bind。** 但不能据此推断 PMU GRF 寄存器从未被其他启动阶段或其他驱动写过。

### 11.3 安全边界与下一项工作

没有启用该节点、没有修改 DTB/Kconfig、没有触发 probe，也没有访问 PMU GRF MMIO。G4-P 继续 NO-GO；G4-P-SAFE patch 继续 deferred。下一步只做只读证据对齐：核对当前实际运行 DTB 与冻结 artifact DTB 中 `/syscon@fdc20000/io-domains/status` 的差异，并核对该 runtime 对应的最终 kernel.config 中 `CONFIG_ROCKCHIP_IODOMAIN` 值。未完成对齐前，不讨论启用节点或 probe。


## 12. Runtime FDT / kernel.config 读取能力边界与 artifact 来源复核（2026-11-27）

### 12.1 当前 G3 RAM 用户空间能力

用户在同一 `panther-x2-g3-provider-runtime` shell 中检查了工具可用性。当前 BusyBox `--list` 仅列出：

`ash cat dmesg echo ls mkdir mount printf sh tail test uname`

以下工具/命令均不存在：

`gzip sha256sum cksum hexdump od grep awk sed tr base64 python3 dtc`

此外该 shell 不支持外部 `command` 命令。因此此前尝试读取 `/proc/config.gz` 和计算 `/sys/firmware/fdt` 哈希均未成功；不能将这些命令报错误判为配置缺失或文件损坏。

已确认的可读文件属性仍为：
- `/sys/firmware/fdt` 存在，大小 118,912 bytes；
- `/proc/config.gz` 存在，大小 47,255 bytes；
- `uname -a` 为 Linux 6.18.63+，build timestamp Fri Nov 27 11:12:32 UTC 2026；
- `/proc/cmdline` 含 `regulator_ignore_unused`。

当前工具集没有 gzip 解压、文本筛选或二进制解析能力。不得为补工具而修改此 RAM runtime；本轮没有安装软件、挂载新文件系统或改变运行配置。

### 12.2 仓库 artifact 来源核对

只读核对 main 分支后确认：
- 当前 workflows 目录没有独立命名为 G3 的构建/打包 workflow；
- G2 runtime packaging workflow `.github/workflows/package-panther-x2-g2-runtime.yml` 固定使用 G2-B artifact run `45924949130` / artifact `15167050233`，其中 DTB SHA256 为 `f6d83d86231b50c903abdf158893b6caa1e8c2aab931c9bf2dbb1b6ca36576dc`；
- G2 packaging report 说明 G2 DTB 继承 B1/R1 DTB，仅改变 RK809 节点；G2 artifact 本身是 PREPARE-ONLY，报告记录未授权写入实体介质或启动实机；
- 现有 G2 workflow 对 kernel.config 做了若干明确 Kconfig gate，但没有检查或记录 `CONFIG_ROCKCHIP_IODOMAIN` 的最终值；
- 6.18.63 Panther X2 board DTS 对 `&pmu_io_domains` 显式设为 `okay`，而 rk356x-base.dtsi 的通用默认值为 `disabled`。冻结 G2 DTB 的 IO-domain 节点属性尚未通过本轮证据直接解码。

因此，当前运行实例的 `io-domains/status=disabled` 已由设备端直接确认，但尚不能把它归因于某个特定冻结 artifact，也不能认定它与 G2 artifact 一致或不一致。当前没有可追溯到该 G3 provider runtime 的独立 manifest / workflow 记录；需要先明确其实际 Image、DTB、initramfs 对应的准备来源，不能以相同 kernel version 代替资产身份。

### 12.3 状态更新

- **已验证：** 当前运行 FDT 存在且大小 118,912 bytes；当前 `/proc/config.gz` 存在且大小 47,255 bytes；当前 BusyBox applet 集合如上；IO-domain 节点状态仍为 `disabled`。
- **未验证：** 当前运行 FDT SHA256；当前最终 `CONFIG_ROCKCHIP_IODOMAIN` 值；当前 G3 runtime 的冻结 DTB / Image / initramfs artifact 身份；冻结 G2 DTB 中 IO-domain 节点的精确属性。
- **不作推断：** `regulator_ignore_unused` 不等于启用 IO-domain consumer，也不能证明 IO-domain selector 已写入。
- **安全边界：** 不在当前 RAM runtime 安装工具、不启用 IO-domain、不触发 probe、不读取或写入 PMU GRF/MMIO、不写 TF/eMMC。

G4-P 继续 NO-GO，G4-P-SAFE patch deferred。下一步应在主机侧追溯 G3 provider runtime 实际使用的构建/打包来源，并用冻结 artifact 的离线 DTB/config 检查补齐证据；不要求当前设备增加工具。


## 14. G3 artifact 身份确认及 G4-P partial-write 风险审计（2026-11-27）

> 本节明确 supersede 第 12 节中“未找到 G3 workflow / artifact 来源”的阶段性结论。第 12 节记录的是当时尚未完成追溯的状态，不再代表当前结论。

### 14.1 G3 实际运行资产追溯与离线校验

已定位 G3 build-only 与 runtime packaging 两个 Actions run，并下载 runtime artifact 离线核对：

- Build-only run：`45984035650`，branch `g3-provider-build-only`，workflow `.github/workflows/build-panther-x2-g3-rk809-regulator-provider.yml`，artifact ID `15192123549`。
- Runtime packaging run：`45996817932`，branch `g3-provider-runtime-package`，workflow `.github/workflows/package-panther-x2-g3-provider-runtime.yml`，artifact ID `15196482298`。
- ZIP 内 `output/SHA256SUMS` 的 **33 个文件逐一离线复算全部通过**，没有哈希不匹配。
- G3 runtime 的冻结 Image 为 32,381,440 bytes，SHA256 `d1830f649e3bfa789fec3589c2ef16b1e46465846c6bb150e666f8df4c610a61`。
- 冻结 DTB 为 116,294 bytes，SHA256 `9364c6d7aadddb8520388418e8db570e0b4020a38c5ceb8acbd2343165bb5209`。
- 冻结 `kernel.config` 为 202,974 bytes，SHA256 `bfcadc0626f0a96b369e1475accf0efcedc9adaae8464ea85291c4afa12d9794`。
- 冻结 BusyBox SHA256 `2d77cb64f5ab5ca33efae040083abe31912ab02677dd21c1b79ade6ed0e98b15`；artifact 内 applet 清单与设备端实测清单完全一致：`ash cat dmesg echo ls mkdir mount printf sh tail test uname`。
- runtime manifest 的 bootargs 与设备端 `/proc/cmdline` 完全一致；设备端 kernel build timestamp 与 G3 build run 时间窗口一致；设备端 model 为 Panther X2；运行树 IO-domain status 为 disabled，与冻结 DTB isolation record 一致。

设备端 `/sys/firmware/fdt` 为 118,912 bytes，而冻结 DTB 为 116,294 bytes。U-Boot 可能对传入 FDT 做 fixup；由于当前 RAM shell 没有 hash 工具，仍不声称设备端 FDT 与冻结 DTB 二进制逐字节一致。但 build/run manifest、bootargs、BusyBox applet、kernel build 时间、model 和 IO-domain status 形成多项一致性证据，足以确认本次运行就是 G3 provider runtime 资产链，而非 G2 artifact。

G3 Kconfig 明确为 `# CONFIG_ROCKCHIP_IODOMAIN is not set`；G3 build workflow 有 `require_off CONFIG_ROCKCHIP_IODOMAIN` gate，G3 packaging workflow 再次检查该配置为 off，并用 `fdtget` gate 要求 `/syscon@fdc20000/io-domains` 为 disabled。因此 G3 isolation 是有意设计。G3 artifact provenance：**PASS / TRACEABLE**；运行 FDT binary hash：仍未验证。

### 14.2 G4-P 关键发现：完整 supply 映射不是无副作用 probe

固定源码：Linux 6.18.63，commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`。

1. RK3568 PMU IO-domain 的 supply index 顺序在 `drivers/soc/rockchip/io-domain.c` 的 `soc_data_rk3568_pmu` 中固定为：0 `pmuio1`、1 `pmuio2`、2 `vccio1`、3 `vccio2`、4 `vccio3`、5 `vccio4`、6 `vccio5`、7 `vccio6`、8 `vccio7`。probe 按 index 从 0 到 8 顺序处理。
2. Panther X2 board DTS 为九路 supply 全部提供引用：
   - 0、1：`vcc3v3_pmu`（RK809 LDO_REG6，固定约束 3.3V）；
   - 2、6、7、8：`vcc_3v3`（RK809 `SWITCH_REG1`）；
   - 3、5：`vcc_1v8`；
   - 4：`vccio_sd`。
3. RK809 的 `SWITCH_REG1` 在 `rk808-regulator.c` 使用 `rk817_switch_ops`；该 ops 只有 enable、disable、is_enabled，没有 get_voltage、get_voltage_sel 或 list_voltage。板级 DTS 对 `vcc_3v3: SWITCH_REG1` 也没有提供固定电压约束或 `vin-supply`。所以不能从该 regulator 的 enabled 状态或名称推断其输出电压；regulator core 的 `regulator_get_voltage_rdev()` 在没有电压操作、fixed_uV 或可用上游 supply 时会返回负错误。
4. IO-domain probe 对每路 supply 先执行 `devm_regulator_get_optional()`，再调用 `regulator_get_voltage()`；只有电压读取成功后才执行该路 `iod->write()`。若电压小于 0，probe 立即走错误清理并返回。
5. 对 index 1（`pmuio2`），当前 G3 运行时已经验证其 provider `vcc3v3_pmu` 可读为 3,300,000 uV。RK3568 write handler 对 index 1 会向 PMU GRF IO_VSEL2（offset `0x0148`）执行两次 hiword-mask write：3.3V 输入对应写值 `0x00020000` 和 `0x00200020`。index 0（`pmuio1`）不写寄存器。
6. 随后 index 2（`vccio1`）引用 `vcc_3v3 / SWITCH_REG1`。该 regulator 没有可读电压操作，预计 `regulator_get_voltage()` 返回负值，IO-domain probe 在此处退出。于是按当前 provider 与 DTS，存在**先完成 index 1 的 VSEL2 写，再在 index 2 失败**的 partial-write 路径。该执行路径由源码和现有 regulator 属性支持，但尚未在设备上触发验证；绝不能为了验证而直接启用完整 consumer。
7. 额外风险：`rk3568_iodomain_write()` 对 VSEL2 的两次 `regmap_write()` 不检查返回值，函数最终仍返回 0；因此即使未来 probe 返回成功，也不能单凭 driver bind / probe success 证明 selector 写入成功。

关键源码定位：
- [io-domain.c: rk3568_iodomain_write / probe / supply 顺序](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/drivers/soc/rockchip/io-domain.c#L86-L120)；[probe supply loop](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/drivers/soc/rockchip/io-domain.c#L659-L710)
- [rk808-regulator.c: rk817_switch_ops / RK809 SWITCH_REG1](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/drivers/regulator/rk808-regulator.c#L1166-L1172)；[RK809 SWITCH_REG1 descriptor](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/drivers/regulator/rk808-regulator.c#L1710-L1718)
- [regulator core voltage read fallback](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/drivers/regulator/core.c#L4579-L4618)
- [Panther X2 board DTS SWITCH_REG1](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts#L380-L389)；[nine IO-domain supply mappings](https://github.com/ophub/linux-6.18.y/blob/aee4e352a15d636cbc484f56819c6e59474dfd9/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts#L462-L473)

### 14.3 G4-P-SAFE 的新边界（仅设计，不执行）

当前完整九路 supply mapping 的 IO-domain consumer **NO-GO**。禁止把 G3 DTB 的 IO-domain status 改为 okay 后直接启动，也禁止以完整 mapping 做一次“看看能否 probe”的试验。

可先评估一个严格无 selector write 的 G4-P0 binding-only 候选：
- 单独构建 `CONFIG_ROCKCHIP_IODOMAIN=y`；
- 仅在实验 DTB 中将 IO-domain child 设为 okay；
- 删除该 child 的全部九个 `*-supply` 属性（不伪造 rail voltage）；
- 其余 G3 isolation、RAM initramfs、SU08G-only、eMMC/TF/SDIO/GMAC 等隔离维持不变；
- 源码显示无 supply property 时 `devm_regulator_get_optional()` 返回 `-ENODEV`，driver 将该路跳过，不调用 `regulator_get_voltage()` 或 `iod->write()`；
- 该候选最多验证 child enumeration、driver bind、PMUGRF syscon regmap acquisition 路径，不验证任何 rail 电压或 selector 设置。

即便 G4-P0 也只能先生成 PREPARE-ONLY artifact 并完成离线审计；实体启动必须另行授权。若要测试真实 supply/selector 路径，必须先通过板级原理图或独立电气测量确认各 bank 实际电压，并解决 `SWITCH_REG1` 缺少可读 voltage 的问题，随后逐路制定有边界的实验，不能恢复完整九路 mapping 一次性探测。

### 14.4 当前判定

- G3 provider runtime：身份已追溯，artifact 内 33 项哈希全 PASS；IO-domain 禁用符合设计。
- G4-P full mapping：**NO-GO**；存在可预测的 partial-write 后失败路径。
- G4-P0 no-supply binding-only：可进入下一轮静态设计审计，**尚未构建、尚未启动、未授权硬件试验**。
- 当前 Panther X2 设备：保持原样；不安装工具、不改 DTB/Kconfig/驱动、不触发 probe、不访问 PMU GRF/MMIO、不写 TF/eMMC。


## 15. G4-P0 binding-only 静态设计审计（2026-11-27）

### 15.1 子设备枚举路径

固定源码 Linux 6.18.63，commit `aee4e352a15d636cbc484f56819c6e59474dfd9`：

- `drivers/of/platform.c` 的 `of_platform_default_populate_init()` 在 `arch_initcall_sync` 阶段调用 `of_platform_default_populate(NULL, NULL, NULL)`。
- `of_platform_default_populate()` 将 `simple-mfd` 识别为递归总线节点；`of_platform_bus_create()` 为节点创建 platform device，并递归处理子节点。
- 创建 platform device 前会检查 `of_device_is_available()`；因此 PMUGRF 下 `io-domains` child 只有在 DT status 为 `okay`（或省略 status）时才会被创建。G4-P0 必须明确设为 `okay`。
- Panther X2 PMUGRF parent compatible 包含 `syscon` 与 `simple-mfd`；IO-domain child compatible 必须保持 `rockchip,rk3568-pmu-io-voltage-domain`。

所以，在父节点保持原状、child status 改为 okay 的前提下，OF core 可创建 child platform device；这条路径不依赖父 syscon platform device 有 driver symlink。

### 15.2 Probe 路径与无 selector 写入证明

`rockchip_iodomain_probe()` 的顺序为：分配私有结构、匹配 SoC data、选择 write handler、取得 parent PMUGRF regmap、循环处理 16 个 supply slots，最后调用可选 SoC init。

RK3568 PMU data（`soc_data_rk3568_pmu`）有九个 supply name（pmuio1、pmuio2、vccio1..vccio7），没有设置 `.init` callback。

若 G4-P0 DTB 将九个 supply properties 全部删除：
1. 驱动仍会按九个名称逐一调用 `devm_regulator_get_optional()`。
2. 无对应 supply property/consumer mapping 时，optional get 返回 `-ENODEV`；driver 明确把 `-ENODEV` 视为“未配置 supply”，执行 `continue`。
3. 因而不会调用 `regulator_get_voltage()`、不会设置 `supply->reg`、不会注册 regulator notifier，也不会调用 `iod->write()`。
4. RK3568 PMU SoC data 没有 `.init` callback，循环结束后没有额外 PMUGRF selector 初始化写入。

这证明 G4-P0 的 IO-domain driver probe 成功路径不执行本驱动的 VSEL selector write。该结论只适用于九个 supply properties 全部缺失的候选 DTB；只删除 SWITCH_REG1 对应的属性是不够的，因为 index 0/1 等其他 supply 仍可能先写 selector。

### 15.3 PMUGRF syscon 是必要依赖，且要区分映射与寄存器事务

- IO-domain probe 在处理 supply loop **之前**就调用 `syscon_node_to_regmap(parent->of_node)`。
- `include/linux/mfd/syscon.h` 在 `CONFIG_MFD_SYSCON` 未启用时提供 stub，返回 `-ENOTSUPP`；因此仅打开 `CONFIG_ROCKCHIP_IODOMAIN` 不足以保证 probe 可通过。
- `CONFIG_MFD_SYSCON=y` 是 G4-P0 必需配置；该 Kconfig 选项选择 `REGMAP_MMIO`。
- parent node compatible 含 `syscon`，所以 `syscon_node_to_regmap()` 可在没有预先注册 regmap 时懒创建 regmap。其创建路径调用 `of_iomap()` 建立 PMUGRF 资源映射，并调用 `regmap_init_mmio()`。
- 对无 supply 的 G4-P0 路径，IO-domain driver 本身不会调用 `regmap_read()` 或 `regmap_write()`；但 **PMUGRF MMIO 区域会被 ioremap 并建立 regmap 对象**。因此准确表述是“建立 PMUGRF 映射，不发起 selector 寄存器读写事务”，不能称为“完全不接触/不映射 PMUGRF MMIO”。

### 15.4 G4-P0 最小配置与 DTB 构建约束

PREPARE-ONLY 候选应满足：

- `CONFIG_OF=y`
- `CONFIG_MFD_SYSCON=y`
- `CONFIG_REGMAP=y`
- `CONFIG_REGMAP_MMIO=y`（由 MFD_SYSCON select，仍需在最终 config 中验证）
- `CONFIG_ROCKCHIP_IODOMAIN=y`（建议 built-in，避免依赖 initramfs 中模块加载）
- 保留 G3 已验证的 `CONFIG_REGULATOR`、RK809 MFD/regulator provider 及相关配置，不借此阶段改变 provider。

DTB 只允许以下目标节点变更：
- `/syscon@fdc20000/io-domains/status` -> `okay`；
- 删除 `pmuio1-supply`、`pmuio2-supply`、`vccio1-supply`、`vccio2-supply`、`vccio3-supply`、`vccio4-supply`、`vccio5-supply`、`vccio6-supply`、`vccio7-supply` 九个属性。

不得更改 PMUGRF parent、其他 regulator 节点、任何 regulator 电压约束、pinctrl/GPIO、GMAC/PHY、USB、TF/eMMC/SDIO、bootargs 或 initramfs。构建后必须离线验证：compatible 精确匹配、status=okay、九个 supply properties 全部不存在、Kconfig 全部符合要求，并对 DTB 做反编译差异审计，证明除上述十项外没有其他变更。Artifact 只允许 PREPARE-ONLY，不在本节授权写 TF 或启动。

### 15.5 阶段判定

- G4-P0 静态设计：**PASS（可进入 build-only workflow 设计）**。
- G4-P0 artifact：尚未构建。
- G4-P0 实机启动/probe：未执行、未授权。
- 允许的 probe 副作用：创建 child platform device、绑定 driver、创建 PMUGRF ioremap/regmap 对象。
- 在九路 supply 属性全缺失且 RK3568 `.init` 为空的前提下，IO-domain driver 不读取 rail 电压、不注册 regulator notifier、不调用 selector write。
- 禁止表述为“无 MMIO 映射”；当前设计仅保证无 PMUGRF selector register transaction。

下一阶段入口：先实现/审计一个独立 G4-P0 PREPARE-ONLY build workflow，继承 G3 冻结资产并只修改上述 Kconfig/DTB 十项；build 后离线验证全部约束。构建 workflow 与 artifact 审计通过后，再单独请求是否授权硬件启动，不得自动进入实体测试。
