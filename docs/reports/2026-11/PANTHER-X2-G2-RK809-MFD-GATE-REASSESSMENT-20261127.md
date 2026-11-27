# Panther X2 项目 A — G2 RK809 MFD 准入再评估（2026-11-27）

## 1. 为什么重新评估

回读原始 G0.2、R3 §11/§21–§26、6.1.116 黄金运行记录后，发现 2026-11-27 新建的 G2 计划把“黄金行为相符 + 用户单独授权”写成了可执行前提，弱化了既有 G0.2 的更严格 HOLD 决策。这是不一致，现予纠正。

本报告仅做仓库证据复核和计划修订；没有设备访问、构建、存储写入、PMIC 操作或网络发送。

## 2. 黄金基准带来的正向证据

已验证：
- 6.1.116 正常运行系统配置包含 MFD_RK808；固定源码端点为 `unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`。
- 6.1.65 config 与 modules.builtin 已归档，`MFD_RK808=y`、`REGULATOR_RK808=y`。
- 6.1.65 候选与 6.1.116 固定源码端点的 `drivers/mfd/rk808.c` 完全相同。
- 6.1.116 实机中断日志有 IRQ 38 `rk817 / rk805_pwrkey_rise` 与 IRQ 39 `rk817 / rk805_pwrkey_fall`；说明黄金系统 MFD/PMIC PWRKEY 子设备和 IRQ 事件链确实工作。
- 6.1.65 候选与 6.18.63 的 RK809 pre-init table、24-bit IRQ mapping、SWITCH_REG1 descriptor 已在 R3 §21–§26 做过定点比较。

这些是强正向证据：同一 Panther X2、同一 RK809 类 PMIC，在黄金系统里已经运行过 MFD/regulator 软件链。不能把 PMIC/电源链当作未知硬件，也不能仅因发现驱动写寄存器就断言 6.18 一定失败。

## 3. 黄金证据仍未证明的部分

6.1.116 的 IRQ 38/39 日志证明 PWRKEY IRQ 事件被 Linux 接收；它没有记录 PMIC IRQ status/ACK 寄存器启动时的原始值、每次 mask/ACK 写入值，也没有证明所有保留位在每次启动都为零。

6.1.116 与 6.18.63 不是同一 MFD 实现：
- 黄金使用旧 `CONFIG_MFD_RK808` / `drivers/mfd/rk808.c`；
- 6.18 使用 `MFD_RK8XX_I2C` / `rk8xx-i2c.c` + `rk8xx-core.c`；
- 6.18 对 RK809 复用 RK817 IRQ layout，并在 probe 中注册 regmap IRQ、读取 status、初始化 mask/ACK；其路径与黄金旧驱动的实机行为不能仅凭 IRQ mapping 相同就认定完全等价。
- 6.18 probe 还会运行完整 RK817-family pre-init 表，其中包含 RTC、codec、GPIO interrupt polarity、thermal threshold 等网络以外寄存器写入。

Datasheet Rev 2.4 对部分 0xFA/0xFC 位标注 reserved/W1C/RC，而 Linux IRQ table 对相应位有映射。现有黄金运行记录没有给出这些寄存器的实际上电状态或 ACK 访问轨迹，故无法用 IRQ 38/39 日志消除该语义边界。

## 4. 修订后的 G2 状态

**G2 stock RK8xx MFD probe：HOLD / NOT AUTHORIZED。**

这不是硬件 FAIL，也不是确认 6.18 driver 有 bug。准确含义：
- 黄金基准已证明同板 PMIC/MFD/IRQ 功能链有正常运行历史；
- 6.18 的相关代码和黄金旧实现有明显共性，但不是完全相同的驱动入口/初始化生命周期；
- stock 6.18 probe 会产生已知 PMIC 写入，且 IRQ ACK 对部分保留位的具体硬件语义尚未闭合；
- 现有只读白名单仍仅为 0xED、0xEE、0xF0、0xF6；不能把既往 RO 读取授权扩展为 MFD probe 授权；
- 单独口头说“继续”不等于授权这组 PMIC 写入。

所以不能仅以“用户另行授权”作为唯一前置条件。必须先完成下面的只读软件证据审查，再提交精确的 G2 变更与副作用清单供用户决定。

## 5. 下一项工作：G2-S 静态对照补齐（允许继续）

仅用已锁定源码与现有黄金日志，补齐以下差异表，不访问设备：
1. 对照 6.1.116 `rk808.c` 与 6.18 `rk8xx-core.c` 的 IRQ chip 定义、regmap_irq flags、init_ack_masked、status read、mask write、ACK write 条件与顺序。
2. 对照旧驱动与 6.18 的 pre-init 表：每个寄存器地址、mask、value、芯片手册定义、是否涉及 RTC/codec/thermal/IRQ/rail。
3. 对照 MFD cell 列表与 6.1.116 实机存在的 pwrkey IRQ，确认 6.18 是否保留相同 IRQ resource mapping。
4. 明确列出 6.18 额外写入、缺少的 ID read、system-power-controller 属性处理差异。
5. 每一项结论标注：黄金实机证据、黄金源码证据、6.18 源码证据、datasheet 证据；不可互相替代。

若以上对照没有发现超出黄金行为的关键写入/IRQ 语义差异，才提交一个“有明确写入集合、预计访问条件、停止条件、失败回退和独立授权点”的 G2 实机方案；若差异无法解释，G2 继续 HOLD，不做定制驱动规避，不做 PMIC 测试。

## 6. ABCD 检查

G2-S 为纯静态软件审计，没有 netdev、interface open 或 DMA，ABCD = NOT EXECUTABLE（阶段性记录）。G2 结束仍必须重评是否已有更早可用的 AF_PACKET 目标；不能为了让 ABCD 可执行而提前启用 GMAC。

G3 regulator provider 与 G4 IO-domain 仍分别设门。首次 netdev/open/DMA 具备时立即执行单帧 A→B→C→D，并在 LAN 对端捕获同一 run_id/sequence/hash（E6）；不能等到 TCP/IP 阶段。

## 7. 结论

当前可继续的是 G2-S 静态对照，不是 G2 stock probe。无设备操作授权，无构建授权，无 PMIC 写入授权。


## 8. G2-S 静态源码对照结果（2026-11-27，补充）

### 8.1 固定源码与对象身份

- 黄金 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`；`drivers/mfd/rk808.c` blob `e00da7c7e3b11c83530c211f62271c4251a8d80b`。
- 6.18.63：`ophub/linux-6.18.y@aee4e352a15d636cbc484f56819c6e59474dfd9f`；`drivers/mfd/rk8xx-core.c` blob `21182df45d1b6b75f25c3aaf41bc8a14f36b3deb`；`drivers/mfd/rk8xx-i2c.c` blob `161b25fbe146ec9b652822a44896013c581e3500`。
- 两版本 `drivers/input/misc/rk805-pwrkey.c` blob 完全相同：`76873aa005b419b0c1644b9eee7f886c389cabd7`。

### 8.2 IRQ mapping / mask / ACK：没有发现 6.18 新增差异

两版 RK817 IRQ chip 定义一致：
- 24 个 logical IRQ；
- 3 组 status/mask register，stride 2；
- status/ack base 0xF8，mask base 0xF9；
- `init_ack_masked = true`；
- IRQ id 0–23 以 `REGMAP_IRQ_REG_LINE(id, 8)` 对应三组 8-bit status/mask。

6.1.116 黄金实机 `/proc/interrupts` 已有 RK817 parent IRQ 与 PWRKEY 子 IRQ 记录：IRQ 38/39 分别登记 `rk805_pwrkey_rise` / `rk805_pwrkey_fall`，RTC alarm 子 IRQ 也已登记。计数为 0，因此这是 MFD/IRQ domain/child request 注册的运行证据，不是按键事件已实际触发的证据。

此前报告指出的 0xFA/0xFC datasheet reserved/W1C/RC 位与 Linux 24-bit mapping 不一致，确实是两版共有的历史实现疑点，不是 6.18 regression。黄金 IRQ 子设备注册成功降低了“整个 IRQ 框架不兼容”的风险，但没有提供初始化时 0xFA/0xFC 原始状态及 ACK 写入轨迹，故仍保留为证据限制；不应把它表述成已证明会造成故障。

### 8.3 RK809 pre-init 写入集合：两版完全相同

6.1.116 `rk808.c` 对 RK809/RK817 选择同一 `rk817_pre_init_reg[]`；6.18 `rk8xx-core.c` 对 RK809/RK817 选择同一表。此前 R3 §21–§26 已逐项核验数组内容逐字节相同。

两版 probe 顺序相同：先注册 regmap IRQ，再逐项执行 `regmap_update_bits()` pre-init，随后创建 MFD cells。没有发现 6.18 为 RK809 新增一组 PMIC pre-init 写入。写入涉及 RTC_STOP、codec 初始化、GPIO IRQ polarity 和 thermal threshold 等；不是网络供电 enable/selector 操作，但属于真实 PMIC 写入，不能称为只读。

### 8.4 识别、MFD cells 与 system-power-controller 差异

| 项目 | 6.1.116 黄金 | 6.18.63 | 影响 |
|---|---|---|---|
| 芯片 variant | 先读 0xED/0xEE，再按 masked ID 选 RK809/RK817 | 由 OF compatible 直接选择 RK809 variant，不在该 probe 中重读 ID | 6.18 缺少 driver 内身份复核；R1 已有独立 RO 实测 0xED=0x80、0xEE=0x94，能补充身份依据，不重复读取 |
| IRQ 初始化 API | `regmap_add_irq_chip()`，显式 remove 时 delete | `devm_regmap_add_irq_chip()` | 资源生命周期不同；IRQ chip 配置和初始化语义相同 |
| pre-init | RK817 表 | 同一 RK817 表 | 无新增写入集合 |
| MFD cells | clkout、regulator、pwrkey、RTC、codec、charger | 相同集合 | G2 不启用 regulator child driver 时不会注册 regulator provider；MFD cell 本身仍会被创建 |
| power controller 属性 | 检查 `rockchip,system-power-controller` | 同时接受标准与 vendor-prefixed 属性 | Panther DT 使用 vendor-prefixed 属性，兼容 |
| poweroff/restart handler | 全局旧式 handler | devm sys-off handler | 注册路径改变；G2 期间禁止主动 poweroff/restart |

### 8.5 新发现：PWRKEY IRQ resource 顺序差异

两版 `rk805-pwrkey.c` 完全相同，固定约定为：
- `platform_get_irq(pdev, 0)` 作为 FALL IRQ，绑定 `pwrkey_fall_irq`；
- `platform_get_irq(pdev, 1)` 作为 RISE IRQ，绑定 `pwrkey_rise_irq`。

但 MFD 的 `rk817_pwrkey_resources[]` 顺序不同：
- 6.1.116：先 `RK817_IRQ_PWRON_RISE`，再 `RK817_IRQ_PWRON_FALL`；
- 6.18.63：先 `RK817_IRQ_PWRON_FALL`，再 `RK817_IRQ_PWRON_RISE`。

header 中两版 enum 均定义 FALL=0、RISE=1。按 pwrkey driver 的 index 约定，6.18 的资源顺序与 consumer 约定一致；6.1.116 的资源顺序表面上相反。黄金 `/proc/interrupts` 标签与 hwirq 数字的组合仍需按 regmap/platform resource 映射机制谨慎解释，不能仅凭 IRQ label 断言按键物理边沿正确。此差异不影响 Ethernet TX 主链，但 G2 若启用 PWRKEY child，应记录为独立兼容性观察项；不要为了模仿旧数组顺序而回退 6.18。

### 8.6 G2-S 结论

**G2-S 静态对照：PASS（源码差异已明确）；G2 stock probe：仍待单独操作授权。**

本轮未发现 6.18 相较黄金版本增加额外 RK809 pre-init 写入或改变 IRQ chip 的 status/mask/ACK 布局。保留的差异是 ID 选择机制、资源生命周期、power handler API 与 PWRKEY resource 顺序。黄金运行记录证明 6.1.116 的 MFD/IRQ child 能注册；不能证明所有 PMIC ACK 保留位状态，也不能证明 PWRKEY 物理边沿行为。

### 8.7 下一步：G2-B build-only，不 probe

先进行纯构建验证，不接触设备：
1. 以冻结的 6.18.63 commit 为输入，单独启用 `MFD_RK8XX_I2C=y`；其 Kconfig 自动 select `MFD_CORE`、`REGMAP_I2C`、`REGMAP_IRQ`、`MFD_RK8XX`。
2. 如要验证 PWRKEY 子驱动，再加入 `INPUT_RK805_PWRKEY=y`（依赖 `MFD_RK8XX`）；不启用 `REGULATOR_RK808`，避免 G2 提前注册全部 regulator descriptors。
3. 使用 R1 原 DTB 的独立副本，将 RK809 节点临时保持/设为 `status = "disabled"`，GMAC1/MDIO/PHY 继续 disabled。这样 built-in 驱动会进入 Image，但不会匹配并 probe RK809。
4. 构建并检查 `.config`、built-in 对象与链接符号、Image/DTB 哈希。通用 QEMU `virt` 不模拟 RK3566/Panther X2，不执行无代表性的 QEMU system boot；如另做 QEMU user-mode 工具自检，单独标注为用户态测试。该步骤验证 Kconfig、编译、链接和产物封装，不验证 I2C、PMIC 或 MFD runtime。
5. 若 build-only 通过，再单独提交 G2-PROBE 计划：恢复 RK809 DT 节点后 stock probe 会执行第 8.3 节的黄金同款写入和 IRQ 初始化。该步骤必须由用户针对这组确切副作用另行授权；未授权不得替换 SU08G 当前 uInitrd/Image 或启动。

G2-B 阶段 ABCD = NOT EXECUTABLE：RK809/GMAC 节点 disabled，无 netdev/open/DMA。每阶段仍记录检查；一旦后续首次具备目标 netdev/open/DMA，立即执行同一帧 A→B→C→D 并由对端 pcap 验收，不等待 IP 层。


## 2026-11-27 环境切换原则修订：B1 RAM 基线不是最终运行环境

用户确认项目 A 第一轮总目标不变：在 Panther X2 实机上运行最小网络组件的 Linux 6.18，通过分层验证最终打通板载 GMAC1 的真实 TX 数据流。后续所有阶段不得把 B1 纯净 RAM 系统当成项目 A 的最终网络运行环境。

### 三种环境必须区分

1. **B1-clean（已完成启动基线）**：6.18.63 + Panther X2 DTB + 纯净 RAM initramfs；网络协议栈、GMAC、MDIO、PHY 均隔离。只用于确认启动链、内核、DTB、initramfs 和基础 shell，不再承担后续网络功能验收。
2. **G2-B build-only（构建隔离环境）**：仅验证新增 MFD 配置、依赖闭包、编译链接与产物；RK809 节点保持 disabled，不作为硬件运行环境，不以 QEMU 结果代替 Panther X2 实测。
3. **Project-A 6.18 minimal runtime（项目 A 正式实验运行环境）**：G2-B 通过后，在首次 G2-PROBE 前建立。固定 6.18.63 kernel、匹配 Panther X2 DTB、最小 RAM initramfs/BusyBox 用户空间、固定 JP-TvBox U-Boot proper；之后按门逐项引入所需驱动和用户态工具。此环境运行于 Panther X2 实机，是真实硬件验证环境。首轮不要求 eMMC 持久化 rootfs，也不提前引入完整 Armbian/systemd/NetworkManager/DHCP/DNS。

### 切换时点与执行要求

- B1-clean 通过后不再将 B1 作为后续网络测试镜像；B1 仅保留为可回退的纯净启动基线。
- G2-B build-only 完成后、G2-PROBE 之前，冻结 Project-A 6.18 minimal runtime 的资产清单、最终 `.config`、Image、DTB、initramfs、BusyBox、bootargs、源码 commit、工具链和 SHA-256；准备独立实验介质/镜像，保留 B1 回退资产。
- 从 G2-PROBE 开始，所有需要硬件功能证据的阶段都在 Panther X2 实机的 Project-A 6.18 minimal runtime 中进行；不得用 QEMU 或 B1-clean 的结果代替。
- G2/G3/G4 是 provider/PMIC/IO-domain 等前置组件激活门；GMAC/MDIO/PHY 恢复后才具备真实 TX 的硬件前提。**第一轮真实 TX 测试在 R7/G6 对应门完成后立即进行**，采用预先冻结的 AF_PACKET 专用发送程序和独立对端抓包；不等到 ARP/IP/TCP/UDP。
- 若某个硬件阶段必须重启，继续使用同一套 Project-A runtime 资产，仅修改本阶段允许的唯一配置变量；每轮记录实际启动的 Image/DTB/initramfs 哈希，避免“以为启动的是新镜像”。
- 只有 TX-PASS 后才扩展 RX、ARP、IPv4、ICMP、TCP/UDP；首轮 TX-PASS 前不为方便而引入完整发行版用户空间。

### 存储与安全边界

Project-A minimal runtime 首轮优先采用 RAM initramfs，以避免将 eMMC/TF 存储驱动、持久化挂载和文件系统行为混入 TX 验证变量。启动资产可由已固定的 U-Boot 从专用 SU08G TF 读取；不得写 eMMC，不触碰冻结的 64GB 对照卡。任何 TF 写入/实机启动仍按逐次授权规则执行。RAM 根文件系统不等于 B1-clean：两者内核版本可相同，但网络配置、驱动集合、用户空间和阶段用途不同。

**核心判断：项目 A 的“真实运行环境”指真实 Panther X2 上运行的项目 A 专用 6.18.63 最小系统，不等于必须先安装完整发行版或持久化 rootfs。**

## 9. G2-B build-only workflow 已准备（2026-11-27，尚未执行）

为避免从 B1 重新构建并扩大变量，G2-B 以成功的 R1 network-core artifact 作为配置和 DTB 输入：

- R1 workflow run：`45611898629`；job `139197305317`，状态 `completed / success`。
- 输入 artifact：`b2-1-r1-network-core`；artifact ID `15023630465`，截至本报告日期未过期。
- 新增配置片段：`scripts/panther-x2-g2/g2-rk8xx-mfd.fragment`。显式启用 `CONFIG_I2C=y` 与 `CONFIG_MFD_RK8XX_I2C=y`（不启用 RK3x 控制器），明确关闭 `CONFIG_REGULATOR_RK808` 与 `CONFIG_INPUT_RK805_PWRKEY`。
- 新增 workflow：`.github/workflows/build-panther-x2-g2-b-rk8xx-mfd.yml`，手动触发，默认读取上述 R1 run ID；从固定 Linux 6.18.63 commit 重建内核 Image（保留 R1 基线 `CONFIG_MODULES=y`；本门只构建 Image，不调用 modules/modules_install），并保留 R1 配置、源码补丁、DTB 输入的来源锁。
- workflow 将在 R1 DTB 的独立副本上把 `/i2c@fdd40000/pmic@20` 设置为 disabled，并再次确认 GMAC1、MDIO1、RTL8211F 节点仍 disabled；不会改写 R1 原始 artifact。
- workflow 增加以源码 commit、R1 config SHA、G2 fragment、兼容补丁和 workflow 文件哈希为键的 kernel object cache；首次运行因没有 G2 缓存仍需完整编译，后续同一输入的失败重跑可恢复部分 `work/kernel-out`，由 Kbuild 继续处理未完成对象。R1 artifact 本身没有保存完整 object tree，因此不能声称 G2 首次构建能直接复用 R1 的 .o 文件。
- 构建验收包括最终 .config 依赖闭包、RK8xx core/I2C transport built-in object 与链接符号、Image 格式、DTB 隔离状态、manifest 和 SHA256。工作流保留 R1 的 `CONFIG_MODULES=y`，但本门只构建 Image，不调用 modules/modules_install；RK8xx core/I2C transport 必须为 built-in，其他模块不作为本门输出。
- 输出 artifact 名称：`panther-x2-g2-b-rk8xx-mfd-build-only`。
- R1 网络核心兼容补丁已从成功 R1 构建分支同步到 main：`scripts/panther-x2-b1/patches/0001-broadcast-uevent-net-only-api.patch`，blob SHA `2018fb06ac0c8ac5e8bdad2f4529d00c97fff013`；G2 workflow 固定使用该补丁，并验证其可应用于锁定的 6.18.63 源码。

**执行边界：** workflow 只在 GitHub Actions runner 中构建；不连接 Panther X2、不写 TF/eMMC、不访问 PMIC、不运行 driver probe、不启用 regulator、不恢复 GMAC/MDIO/PHY。G2-B 只验证构建配置和产物，不是 PMIC runtime PASS。

**QEMU 边界修订：** 当前 G2-B 目标是 RK3566/Panther X2 内核与 DTB。通用 QEMU `virt` 机器并不模拟 Panther X2/RK3566 板级平台，不能把其启动结果作为本门验收；本 workflow 不执行误导性的 QEMU system boot。若以后对静态 AArch64 用户态工具做 QEMU user-mode smoke test，应单独标注为用户态测试，不得称为 RK3566 kernel boot。

工作流首次提交后发现 YAML 尾部重复残片、兼容补丁路径错误及构建目标问题，均已修复。首次运行 `45923164270` 成功下载 R1 artifact，DTB SHA256 与预期一致；失败原因是 R1 config gate 将未启用符号的文本表示误当成固定格式，已由 commit `fbb17c96cb047136d113d2401f9abec3b4613c1c` 修复。第二次运行 `45923873517`（workflow commit `7cae508d818c3d49b385b806e3abd8c99f690885`）通过 R1 输入核验、6.18.63 源码锁定、兼容补丁应用、Kconfig merge 和 `olddefconfig`；最终配置检查只在 `CONFIG_MODULES` 处失败。实际 R1 artifact 的 `.config` 明确包含 `CONFIG_MODULES=y`，R1 workflow 也成功生成 `modules.tar.zst`；此前把 R1 描述为关闭 modules 是错误的。G2 不应改变这项基线能力：已修复 workflow，将 `CONFIG_MODULES` 从 forbidden 列表移入 required-y 列表（commit `3833277a469932c16bf02f83a53f1e57e4658ce4`），仍只构建 `Image`，不调用 `modules`/`modules_install`，同时要求 RK8xx MFD core/transport built-in。第二次运行的 `olddefconfig` 后配置证据显示 `CONFIG_MFD_CORE` 从 R1 的 `m` 提升为 `y`，`CONFIG_MFD_RK8XX=y`、`CONFIG_MFD_RK8XX_I2C=y`，GMAC/MDIO/PHY 仍未启用；这符合 built-in MFD 的依赖方向。该次运行在 Image 编译前终止，上传 artifact `15164713872` 仅含配置与日志证据，不是内核构建产物。G2-B 仍为 **NOT PASS / NOT COMPLETE**；下一步应重跑，继续审查编译和对象链接。G2-PROBE 仍 HOLD / NOT AUTHORIZED。