# Panther X2 项目 A — G0–G10 硬件准入与 ABCD-TX 分层验证计划

- 日期：2026-11-26
- 状态：架构计划；不构成设备启动、刷写、PMIC 写入或网络发送授权
- 上位依据：项目 A 总路线图、B2-1 实施计划
- 原则：复用 R1–R6 既有研究；先完成 G0 只读准入，再逐门申请硬件操作；任何失败停在当前门。

## 1. 目标与边界

两条黄金基线 6.1.65（第一功能基准）和 6.1.116（第二正常行为参照）均证明 Panther X2 板载有线千兆网络曾正常工作。当前优先调查 6.18 软件配置、驱动实现、设备树和硬件资源激活适配。两条黄金基线已证明同一硬件的有线网络功能正常；因此先反向提取黄金系统真实配置、驱动实现和启动/运行行为，再与 6.18 对照。不得将重新测量 3.3V rail 或寻找 PCB 测点设为前置门；只有软件对照出现明确、无法解释的物理异常假设时，才提出针对性硬件补证。

仅研究板载 GMAC1 千兆 Ethernet。Wi-Fi/蓝牙永久排除；不恢复历史 Project B GMAC 根因调查；不重跑已完成的多版本审计。保持已验证 SPL→JP-TvBox U-Boot proper→TF 加载 Kernel/DTB/uInitrd→RAM initramfs 启动链，不写 eMMC，不触碰 SN64G。SU08G 任何写入/启动仍须逐次授权。

## 2. ABCD 同帧发送验证定义

ABCD 是同一帧在发送路径中的四个连续观察边界，不能以不同帧或单纯计数器拼接结论。

| 标记 | 边界 | 需要关联的证据 |
|---|---|---|
| A | 用户态 AF_PACKET/SOCK_RAW 提交 | interface、EtherType、源/目的 MAC、原始 payload、sequence、length、SHA-256、sendto/sendmsg 返回值/errno |
| B | Linux 网络核心 / skb | 同一 sequence/hash 的 skb、长度、目标 netdev、进入驱动前的证据 |
| C | STMMAC ndo_start_xmit / stmmac_xmit | 同一帧进入驱动、queue、长度、skb/payload 关联及返回状态 |
| D | DMA mapping | DMA API 返回、DMA address、长度、DMA_TO_DEVICE、映射结果；可安全观测时核对 DMA buffer payload |

D 之后继续记录 TX descriptor（buffer DMA address、length、FS/LS、OWN）、DMA completion、driver reclaim/unmap、MAC/PHY/link，最后由独立对端线侧抓包核验。descriptor 不保存 payload；OWN 清除/发送完成/netdev counter 增长均不能替代对端收到。

固定测试帧：实验 EtherType 0x88B5，广播目的 MAC，payload 含 ABCD、递增 sequence、length 和校验/hash；先单帧，之后才按门限增加少量重复帧。无 IPv4/ARP/DHCP/DNS 依赖。发送前固定 LAN 对端与抓包过滤器，确认广播域。每层必须使用同一 sequence/hash；无法直接观察 payload 时写明 NOT OBSERVED，不用计数器冒充。

## 3. G0：硬件前只读准入（当前阶段）

G0 完成前不激活 RK809 MFD/regulator，不恢复 GMAC/MDIO/PHY，不做硬件发送。

- **G0.1 依赖矩阵**：将 R2–R6 证据映射为 provider→consumer→实际动作→证据等级→阻塞项；分别记录 6.1.65、6.1.116、6.18.63 默认配置/对象和已知实机行为。
- **G0.2 PMIC 副作用：静态调用路径已识别，最终决策 HOLD。** 既有审计发现 6.18 MFD/regulator probe 有 PMIC 写入路径，但尚未与 6.1.65/6.1.116 黄金驱动的实际初始化、IRQ ACK、regulator constraints 和 powerup 行为完成逐项比较。不能仅因存在写操作就判为不安全；在黄金反向审计完成前仍不启动该驱动。详见 G0.2 与 Golden reverse audit 报告。
- **G0.3 IO-domain：静态拓扑/写入路径已完成，运行时最终 bind 状态 UNKNOWN。** 已确认 GMAC1 M0→GPIO3→VCCIO5；vccio5-supply 与 GMAC1 phy-supply 均指向 vcc_3v3/SWITCH_REG1；VCCIO5 selector 会写 PMU GRF 0x140/0x144。实际 rail 电压/selector readback 未验证，不放行 consumer probe。
- **G0.4 clock/reset/PHY：静态审计完成，物理来源/波形 UNKNOWN。** CRU clock IDs/mux/gate、SRST_A_GMAC1 ID236、GPIO3_PA1 active-low、RGMII delay/mode 已复用 R6 证据确认；RTL8211F CLKOUT pin35 仅为 125MHz 候选，DTS fixed-clock 不证明实际波形。
- **G0.5 ABCD 夹具：静态设计完成。** R1 loopback probe 仅作为软件 API 回归，不可充当目标 TX sender；新建独立 sender 规格，固定 0x88B5/ABCD/run_id/sequence/digest 帧格式，复用 R1 tracepoint/kprobe/DMA trace 能力和外部 pcap。运行时 tracefs/kprobe 可用性仍待后续授权阶段验证。
- **G0.6 Fixed-regulator：保留为历史备选研究，不进入当前主路线，不实现。** 不以 fixed-regulator 假设替代黄金系统已正常使用的 RK809 provider 链。
- **G0.7 板级测点检索：背景资料，不是准入条件。** 不要求用户提供原理图/PCB 照片，不安排电压测量。只有黄金软件反向追踪发现具体物理异常后，才决定是否补做测量。

G0 放行条件：完成黄金基线真实配置/对象/DTB/启动行为恢复；完成黄金 RK809/MFD/regulator/IO-domain 初始化与 6.18 默认实现逐项比较；必需 provider 缺口及 deferred-probe 原因可追溯；未解决项明确列 BLOCKED；ABCD 发送器/观测点/对端抓包方案可执行。存在未解释的软件差异时不放行，但不以无关的 PCB 测点资料阻塞。G0 通过仅允许提交 G1 单独操作计划，不自动授权设备操作。

## 4. G1–G10 分阶段放行

| 阶段 | 唯一目标与激活边界 | ABCD 检查点 |
|---|---|---|
| G1 I2C/RK809 只读边界 | 复用已完成 I2C0 bind、RK809 ID 0x8094、0xF0/0xF6 只读证据；除非出现明确缺口，不重复读取；不启用 MFD | 不具备 MAC/netdev，记 NOT EXECUTABLE |
| G2 RK809 MFD/regmap | 先按黄金基线审计结果评估 6.18 默认驱动；确认初始化写入与黄金行为的关系后，再形成单独授权方案。当前 HOLD，不预先否决 stock driver | 不发帧；目标 MAC 未激活 |
| G3 regulator provider | 以黄金版本实际 regulator descriptors/constraints/调用顺序为参照，审查 6.18 provider 差异及自动写入；不要求先做全 rail 物理测量 | NOT EXECUTABLE；检查目标网口仍隔离 |
| G4 IO-domain 与共享硬件资源 | 在 provider 安全放行后，核验 IO-domain supplier/deferred-probe/GRF 写入；再逐项确认 GMAC 所需 clock/reset/pinctrl/GPIO/PHY supply，物理电压/波形另证 | 复核一次 netdev/open/DMA 的前置条件 |
| G5-A Rockchip glue/STMMAC probe | 单独恢复目标 MAC 节点和最小依赖；核验资源、probe、bind、netdev 注册；不把 probe 当作 open/link | netdev 未 open 时不执行真实 A–D |
| G5-B MDIO/RTL8211F | 单独核验 MDIO bus、地址0 PHY ID、driver bind、link；不写 PHY 寄存器 | 若接口与 DMA 前置条件确已满足，另行批准后单帧 A→D；否则 BLOCKED |
| G6 interface open/DMA | 单独 open；记录 DMA reset outcome、ring、queue、IRQ/NAPI、MAC/MTL 初始化。6.18 reset failure warning-and-continue 必须独立检查 | 低速单帧完整 A→B→C→D + descriptor/OWN/completion/reclaim |
| G7 物理 TX | 保持同一软件/线缆/对端条件，对端逐帧捕获 EtherType、MAC、sequence、length、hash | 完整 ABCD + E6；对端收到正确帧才 TX PASS |
| G8 RX | 独立验证对端→Panther 的 PHY/MAC RX、DMA RX、NAPI、skb、AF_PACKET；首轮不混入 ARP | TX 回归帧复测，确认新增 RX 未破坏 TX |
| G9 ARP/IPv4/ICMP | 逐项加入 ARP、静态 IPv4、ICMP；地址从实际 LAN 读取；不依赖 DHCP/DNS | 每一子项完成后复测 ABCD TX |
| G10 TCP/UDP 与按需服务 | TCP、UDP 分开；DHCP/DNS/SSH 仅在基础功能通过后按需引入 | 每个新增协议阶段后复测 ABCD TX |

任何连续两个阶段不能执行真实 ABCD 后，下一阶段必须重新评估 netdev/open/DMA 条件；一旦具备条件，优先单帧验证，不等全部协议栈完成。若不具备，记录缺失条件，不绕过前置门。

## 5. 实际启动/激活顺序

预期依赖顺序为：既有 BootROM/eMMC SPL→JP proper→RAM Linux；SoC clock/CRU、pinctrl、GPIO、GRF/Syscon、reset、I2C 基础设施；经安全审查后 RK809 MFD/regmap；再 regulator provider；IO-domain consumer；GMAC PHY supply、clock/reset/pinctrl/GPIO 等资源；Rockchip DWMAC glue/STMMAC；MDIO/RTL8211F；interface open、DMA ring/IRQ/NAPI；ABCD TX；对端捕获；RX 与协议栈。

这不是 DTS 节点顺序，也不保证 Linux driver core 严格线性 probe。真实顺序以 supplier/consumer、deferred-probe、probe 日志、sysfs bind 和资源 API 返回为准。

## 6. 每门统一记录与停止条件

记录阶段/子门、授权范围、源码 commit、最终 config、Image/DTB/initramfs/tool hashes、6.1.65/6.1.116 对照、唯一变量、启动日志、probe/deferred-probe、provider/consumer、资源返回值、ABCD 同帧序列与 hash、DMA mapping/descriptor/completion/reclaim、对端抓包、最后通过边界和回退点。

配置/构建差异未解释不启动；黄金驱动行为尚未对照前不贸然启用 PMIC MFD；supplier defer 不绕过；PHY supply/clock/reset 软件依赖未确认不 open；DMA mapping/descriptor/OWN/completion 异常立即停止发送；对端无帧或内容不符判 TX FAIL，不进入 ARP/IPv4。写介质、重启、PMIC/PHY寄存器写、供电/复位动作、实机发送均须单独授权。

## 7. 当前进度

**执行优先级修订（2026-11-27）：以黄金基线反向软件审计为主线。** 详细计划见 [G0 Golden PMIC/Regulator Reverse Audit](./PANTHER-X2-G0-GOLDEN-PMIC-REGULATOR-REVERSE-AUDIT-PLAN-20261126.md)。此前 G0.6/G0.7 的 fixed-regulator 与 PCB 测点研究降级为背景/备选，不得阻塞黄金配置提取和驱动行为对照。

- [x] G0–G10 总体门序、启动依赖和 ABCD-TX 同帧定义已建立。
- [x] G0.1 provider/consumer 依赖矩阵第一轮归档；交叉复核仍待 G0 总审。
- [x] G0.2 6.18 stock RK809 MFD/regulator 副作用静态调用路径盘点；最终准入决策改为 HOLD，等待黄金驱动反向对照。
- [x] G0.3 IO-domain 静态 supplier/deferred-probe 路径、GMAC1 VCCIO5 mapping 与 GRF 写入行为已归档；运行时最终 bind 状态仍 UNKNOWN。
- [x] G0.4 clock/reset/PHY 静态依赖及 125MHz 候选来源审计完成；物理连线/波形和 reset 电气行为未验证。
- [x] G0.5 ABCD sender 规格、tracepoint/kprobe/DMA mapping 观测链和对端 pcap 夹具审查完成（静态设计）。
- [x] G0.6 fixed-regulator 替代路径静态可行性研究归档为备选，不进入当前执行路线。
- [x] G0.7 公开板级资料检索归档为背景，不作为准入条件。
- [x] G0-P1：6.1.65 最终 config/built-in 已归档；6.1.116 真实 config 7,677 项已提取且与官方模板零差异；实机启动/IRQ/GMAC/PHY 日志已归档。黄金 DTB binary 仍待补齐。
- [x] G0-P2：6.1.65/6.1.116 RK809 MFD、regulator、IO-domain、GMAC glue 源码共性已逐文件核验；关键文件完全相同，详见 G0 Golden Source Commonality 报告。
- [x] G0-P3：黄金与 6.18.63 的 RK809 IRQ/pre-init/SWITCH_REG1 descriptor、regulator late cleanup、PHY-supply consumer 路径已在 R3 §21–§26 对照；保留已知差异及证据边界。
- [x] G0-P4：CONDITIONAL PASS。6.1.116 与 6.18.63 完整 DTB 字节级相同；6.1.65 原始 DTB 身份及 GMAC1 核心解析已归档；仅 6.1.65 PMIC/IO-domain 原始子树 binary diff 仍缺，不重提大镜像。
- [x] G0 总体复核：CONDITIONAL PASS，仅允许形成 G2 受控实施/授权计划，不构成硬件操作授权。
- [ ] G2：stock RK809 MFD/regmap 受控实施；必须先完成独立计划评审并取得该次 PMIC pre-init 写入的明确授权。
- G0 CONDITIONAL PASS 不等于硬件激活放行；在 G2 独立授权前不启动、不写 PMIC、不恢复 GMAC。


## 2026-11-27 G0 总体复核结果

G0 现记为 **CONDITIONAL PASS（planning only）**。完整审查见 `PANTHER-X2-G0-OVERALL-REVIEW-AND-G2-CONTROLLED-PLAN-20261127.md`。这只允许进入 G2 实施计划评审；不授权 stock RK809 MFD probe。G2 probe 的 `rk817_pre_init_reg[]` 写入与黄金版本继承行为相符，但该次 6.18 probe 仍需单独授权。

G0-P4 证据状态已修正：6.1.116 与 6.18.63 完整 DTB 字节级相同；6.1.65 原始 DTB 的 GMAC1 核心属性复用既有解析结果；仅 6.1.65 原始 PMIC/IO-domain 子树 binary diff 未完成。此项不要求重新提取完整镜像，不作为 G2 计划编制阻塞。


## 2026-11-27 G2-S 完成与 G2-B 下一步

G2-S 静态对照已完成，详见 `PANTHER-X2-G2-RK809-MFD-GATE-REASSESSMENT-20261127.md`。黄金 6.1.116 与 6.18.63 的 RK817 IRQ chip / 24-bit mapping / pre-init 表 / MFD cell 集合一致；未发现 6.18 新增 PMIC pre-init 写入。6.18 的 pwrkey resource 顺序修正为 consumer 驱动所期望的 FALL、RISE；不回退。黄金 IRQ 记录提供 parent/child IRQ 注册的正向证据，但计数为 0，不证明物理按键边沿。

下一步 G2-B 仅做 build-only：启用 MFD_RK8XX_I2C，不启用 INPUT_RK805_PWRKEY 或 REGULATOR_RK808；RK809 节点保持 disabled，GMAC/MDIO/PHY 继续 disabled。检查最终 config、built-in 对象、Image/DTB 和 manifest。通用 QEMU virt 不模拟 RK3566/Panther X2，不安排无代表性的 kernel system boot。G2-B 不访问 PMIC、不触发 probe、不改写设备。G2-PROBE 仍须另行提交明确的 PMIC 写入清单并取得用户授权。


## 2026-11-27 GMAC 高风险准入原则（强制）

用户明确强调：第一轮项目 A 的目标始终是 Panther X2 实机运行最小网络组件的 Linux 6.18，并逐层打通真实 Ethernet TX；GMAC 是黄金版本之后变化较大、也是最主要的风险堵点。后续不得把 GMAC 当作普通驱动开关处理。

### A. 当前已知的高风险变化

1. **Rockchip glue 初始化路径变化**：6.1.65 在 RK3568 专属 `set_to_rgmii()` 路径中显式设置 interface mode；6.18 增加 `rk3568_init()`、`gmac_phy_intf_sel_mask`，并将 interface selection 迁入通用 `rk_gmac_powerup()` / write-mask 路径。寄存器最终意图相近，不代表写入顺序、掩码、时序完全相同。
2. **GRF mode 处理变化**：6.18 显式处理 CON1 bit7 的 RMII/RGMII mode；6.1.65 依赖复位默认值。TRM 证实 reset=0 且 0=RMII/RGMII，因此当前静态意图相符，但必须核对 6.18 实际写入时机和 readback 证据。
3. **STMMAC core/Kconfig/对象结构变化**：6.18 新增 `ETHTOOL_NETLINK` 依赖及 `NET_DEVLINK` select，并存在 STMMAC/DWMAC4 core 结构变化。必须以最终解析后的 `.config`、built-in 对象和实际调用路径为准，不按配置片段推断。
4. **DMA/TX 生命周期**：descriptor、DMA mapping、OWN、completion、reclaim 必须分别取证；不能把 netdev 注册、carrier、计数器增长或 descriptor OWN 清除视为物理 TX 成功。
5. **时钟链**：DTS 的 125MHz fixed-clock 只证明 CCF 逻辑描述，不证明板上实际时钟来源/波形。现有证据没有把 RK809 CLKOUT 与 gmac1_clkin 连起来；RTL8211F CLKOUT 只是候选。此项优先通过黄金系统实际 clock tree、PHY 驱动配置与启动/运行证据反向确认，不因抽象上的 UNKNOWN 就直接要求测板或量电压。

### B. GMAC 启用前的强制准入清单

在 G5-A 恢复 GMAC1 节点/驱动之前，必须逐项归档并由用户审阅：

- [ ] **Golden source diff**：6.1.65 与 6.18 的 Rockchip glue 关键函数逐函数差异，涵盖 probe、powerup/powerdown、interface mode、GRF write-mask、clock/reset、regulator、PHY reset、delay 配置。
- [ ] **Golden config/object diff**：两条黄金基线与 6.18 最终配置中 STMMAC_ETH、DWMAC4、ROCKCHIP_DW_MAC、PHYLINK、MDIO、DMA、IRQ、clock/reset 依赖闭包及实际 built-in 对象。
- [ ] **Golden DTB diff**：6.1.65 原始 GMAC1/PHY/clock/reset/pinctrl/PMIC/IO-domain 相关子树与 6.18 实际 DTB 的属性、phandle、resource、status、供电映射对照。只提取相关子树，不重新提取整盘镜像；6.1.116 与 6.18 DTB 字节相同的事实作为第二参照。
- [ ] **Provider/consumer readiness**：RK809 MFD/regulator 与 IO-domain supplier 实际 bind/probe 状态、deferred-probe 原因、PHY supply consumer 获取/enable 路径；以黄金驱动实际行为为对照，不预设必须进行电压测量。
- [ ] **Clock/reset/pinctrl readiness**：CCF 实际 parent/rate/enable 状态、GMAC1 reset controller 结果、RGMII pinctrl 组与 PHY reset GPIO 极性/时序。125MHz 物理来源若软件证据仍不能确认，先标注 BLOCKED/UNKNOWN，给出针对性最小补证方案，不擅自假定某个芯片输出。
- [ ] **Observability and rollback**：在启用前准备 probe 日志、trace、netdev stats、DMA mapping/descriptor/completion 观察手段；固定回退到 B1-clean 与前一阶段 Project-A runtime 的资产及哈希。

任何一项未完成或出现无法解释的黄金差异，G5-A 保持 HOLD；不通过“先启用再看日志”代替准入审计。

### C. GMAC 分段启用与测试边界

1. **G5-A1：MAC glue/probe only** — 只恢复 GMAC1 所需节点和最小驱动闭包；确认 probe/bind、资源获取、netdev 注册。此时不主动 open，不启动 PHY 链路协商，不发送帧。
2. **G5-A2：MDIO/PHY attach** — 单独确认 MDIO bus、PHY address 0、RTL8211F ID、PHY driver bind。只使用驱动正常初始化路径，不随意写 PHY 寄存器；link 状态需有实际证据。
3. **G6-A：interface open/DMA init** — 单独 open，记录 MAC/MTL/DMA reset outcome、ring allocation、DMA mask/address width、IRQ、queue/NAPI 和 DMA mapping。6.18 reset failure warning-and-continue 必须单独判定，不能因 probe 成功而放过。
4. **G6-B：ABCD 单帧 TX** — 一旦 AF_PACKET、netdev open、DMA ring 条件齐备，立即发送一个 0x88B5 广播测试帧，关联同一 run_id/sequence/hash 的 A 用户态、B skb、C stmmac_xmit、D DMA mapping/descriptor/completion/reclaim 证据。
5. **G7：E6 物理验收** — 独立 LAN 对端抓包，确认同一帧的 MAC、EtherType、sequence、length、payload hash。只有 E6 收到正确帧才判定 TX PASS。

G5-A1/G5-A2 若不具备发送条件，ABCD 明确记录 NOT EXECUTABLE 与缺失条件；每隔一门复核一次。一旦 G6-A 条件具备，不能再以“还没到协议栈阶段”为由推迟单帧 TX。

### D. 明确禁止的捷径

- 不因两条黄金系统网络正常就推断 6.18 GMAC glue/core 一定兼容；黄金系统的作用是提供配置、源码、启动行为与功能对照证据。
- 不因 6.18 与黄金 DTB 的关键属性相同就跳过驱动源码/调用顺序差异审计。
- 不以人为强制时钟、手工寄存器写、绕过 regulator/IO-domain、伪造 PHY link 或修改 DMA 算法来快速“打通”。
- 不把增加完整 Armbian/systemd/NetworkManager/DHCP 等用户空间作为 GMAC 排障手段。
- 不把 PMIC 3.3V rail 测量或 PCB 测点搜索设为默认前置条件；优先反向核对黄金版本如何配置和使用同一 provider/consumer。只有发现具体且无法由软件证据解释的物理异常假设时，才提出有针对性的补证。

**准入总原则：先解释黄金到 6.18 的差异，再按资源依赖逐层启用；每一步都留有可观测证据、单变量边界和回退点。第一轮成功标准仍是对端收到正确 TX 帧，不是 GMAC probe 成功。**


## 2026-11-27 GMAC 高风险准入原则

用户明确强调：项目 A 第一轮目标仍是 Panther X2 实机运行最小网络组件的 Linux 6.18，逐层打通真实 Ethernet TX；GMAC 是黄金版本之后变化较大、也是主要堵点，必须作为最高风险阶段审慎处理。完整准入清单、分段启用和禁止捷径见 `PANTHER-X2-G0-G10-HARDWARE-ACTIVATION-AND-ABCD-TX-PLAN-20261126.md` 的“GMAC 高风险准入原则”章节。

强制要求：G5-A 恢复 GMAC 前完成 golden source/config/object/DTB diff、provider/consumer readiness、clock/reset/pinctrl readiness 和可观测/回退准备；差异未解释则 HOLD。G5-A1 只 probe/bind/netdev 注册，不 open；G5-A2 单独 MDIO/RTL8211F attach；G6-A 单独 open/DMA init；一旦具备 AF_PACKET+open+DMA 条件立即做同帧 ABCD 单帧 TX；G7 由对端 pcap E6 收到正确帧才判 TX PASS。

不得以黄金系统正常推断 6.18 自动兼容；不得先启用再看、绕过 provider、手工强制时钟/寄存器、伪造 link 或改 DMA 算法；不把 3.3V 测量/PCB 测点设为默认前置条件，优先黄金软件反向对照。

## 2026-11-27 四层知识库分类补充

四层知识库与证据标签的权威定义见 `PANTHER-X2-PROJECT-A-FOUR-LAYER-KNOWLEDGE-BASE-AND-RISK-MODEL-20261127.md`。本计划执行时按以下层次归档：K1 Linux 公共网络栈；K2 通用 MAC/IP 驱动；K3 Rockchip SoC 适配；K4 Panther X2 板级适配。

K4 与 K3/K4、K2/K3 的跨层接口是优先审计对象；K1/K2 的初始风险判断相对较低，但不得以社区使用广泛替代 6.18.63 的源码、最终配置、构建对象和实际功能证据。两条黄金基线只降低同板硬件固有缺陷的初始怀疑，不代表新版本板级适配已经通过。

本分类不改变 G0–G10 顺序，不授权提前 probe 或启用 GMAC。当前仍先执行 G2-B build-only；PMIC probe、regulator/IO-domain 激活和 GMAC 恢复分别保留原有准入门。不得因此增加默认电压测量或 PCB 测点任务。

## 2026-11-27 G2-B workflow 准备状态

- [x] 四层技术知识库与风险模型已归档；不改变 G0–G10 门序。
- [x] G2-S 静态源码对照完成。
- [x] G2-B 专用 build-only workflow 与最小配置片段已提交并完成静态修复（YAML 尾部重复残片、补丁路径、built-in-only Image 构建，并显式声明 I2C core/OF 依赖），复用 R1 artifact run `45611898629`。
- [x] G2-B run `45923873517` 日志与 evidence artifact 已审查：R1 输入、源码 commit、兼容补丁、Kconfig merge 和 `olddefconfig` 均通过；失败点是 workflow 错误禁止 R1 原有 `CONFIG_MODULES=y`。真实 R1 artifact 已证实该项开启；G2 不应改变该基线能力。
- [x] 已修复 workflow：`CONFIG_MODULES=y` 改为 required，仍只构建 Image、不构建 modules（commit `3833277a469932c16bf02f83a53f1e57e4658ce4`）。
- [x] G2-B run `45924949130` 全部步骤 PASS：R1 输入锁定、6.18.63 源码/补丁、Kconfig merge、Image 编译、MFD built-in object 与 vmlinux linked symbol、DTB 隔离、artifact 上传均通过。
- [x] artifact `15167050233` 已下载并检查；内部 `SHA256SUMS` 全部校验通过。G2-B BUILD PASS，仅代表 build/link 与 DTB 隔离，不代表 RK809 实机 probe 或 PMIC 功能。
- [ ] 下一步按既定路线准备 Project-A 6.18.63 minimal runtime 资产；G2-PROBE 仍需独立副作用审查和明确授权。
- [ ] G2-PROBE 仍 HOLD / NOT AUTHORIZED；不触发 PMIC 写入，不启动硬件 probe。
