# Panther X2 U-Boot 板载有线网络基准实测记录（2026-11-22）

## 1. 目的与顺序

用户明确调整项目 A 优先级：历史版本已经证明 Linux 可以启动；当前先确认 U-Boot 能否独立初始化板载有线网口、建立链路并完成基本 IP 连通。顺序调整为：U-Boot 网络基准 → B1 无网络 RAM Linux → B2 网络组件逐项引入 → B3 TCP/UDP 双向验证。B1 仍是隔离基线，但不再阻挡本轮 U-Boot 实测。

仅测试 Panther X2 板载有线千兆 Ethernet；Wi-Fi/无线、蓝牙、USB/PCIe 外接网卡永久排除。不恢复历史 GMAC 根因排查。

## 2. 固定现场基线

- 当前 U-Boot 提示符：=>，Linux 尚未启动。
- U-Boot proper：U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)。
- 当前启动链：eMMC 前级 SPL → TF 上 JP-TvBox U-Boot proper 混合链；不是完整 JP SPL+proper 链。
- 不改变启动链、不重启、不启动其他镜像。

## 3. 用户授权及安全边界

用户已明确授权当前已运行 U-Boot 会话中的板载有线网口初始化、DHCP 和基本连通性实测。

授权不包括写入 eMMC/TF、save/saveenv、MII/MDIO PHY 寄存器写入/修改、fatwrite、tftpflash、tftpput、download、fastboot、rockusb、ums、boot/bootd/bootcmd/source/booti/reset、替换 SPL/U-Boot 或改变启动介质。必要 setenv 仅允许当前 RAM 临时变量，不保存。

本轮不重新运行 BootROM/SPL，不访问块设备；这不构成未来重新启动、写卡或修改 eMMC 的 B0.4 安全门豁免。

## 4. 已完成的命令能力审计

### DHCP
help dhcp 返回：
    dhcp - boot image via network using DHCP/TFTP protocol
    Usage:
    dhcp [loadAddress] [[hostIPaddr:]bootfilename]

命令入口存在，但帮助语义是 DHCP/TFTP 组合命令，没有显式 DHCP-only 参数。必须先审计该版本 autoload 机制，确认 autoload=no 可阻止 TFTP 下载后才运行 DHCP。确认前不执行，不猜测 bootfile。

### MII
help mii 显示只读 device/info/read/dump；同时有 write/modify。项目只允许只读命令。

### MDIO
help mdio 显示只读 list/read/rx；同时有 write/wx。项目只允许只读命令。

### MDIO bus 枚举
现场执行 mdio list，实际输出：
    ethernet@fe010000:

结论：实机已验证至少一个名为 ethernet@fe010000 的 MDIO bus 已注册。它对应目标以太网控制器地址；但不证明 PHY 已探测、PHY 地址/型号正确、物理链路 Link Up、MAC 收发正常或 DHCP 成功。

### ping
ping 出现在此前提供的完整 U-Boot help 清单中，只确认命令入口存在，尚未执行。

## 5. 当前验证状态

| 层次 | 状态 | 证据/缺口 |
|---|---|---|
| DHCP/ping 命令入口 | 部分确认 | 命令存在，未实测 |
| Ethernet/MDIO 注册 | 已确认一项 | mdio list 列出 ethernet@fe010000 |
| PHY 枚举 | 未验证 | 待 mii device、PHY info |
| 物理链路 | 未验证 | 待只读 link 状态 |
| DHCP | 未验证 | 待审计 autoload 并安全实测 |
| LAN 网关 ICMP | 未验证 | 待 ping |
| 外部 IP ICMP | 未验证 | 待 ping |
| TCP/UDP | 本轮不测 | 后续 B3 分别验证 |

## 6. 下一步

严格一次一条命令：
1. mii device，列出实际 MII 设备。
2. 确认 PHY 地址/型号；只读检查，不猜地址、不写寄存器。
3. 只读确认 PHY link。
4. 检查 printenv autoload，并从当前 U-Boot 对应源码核实 DHCP 实现；只有确认 autoload=no 不会触发 TFTP 下载，才运行 DHCP。
5. DHCP 成功后分别 ping LAN 网关和已知外部 IP；DNS 不作为前置条件。
6. 任一层失败即停，不同时更换网线、端口、U-Boot 或网络参数。

## 7. 结果解释边界

U-Boot DHCP、网关和外部 IP ping 均成功，表示当前启动链在本次条件下完成 Ethernet 初始化、PHY/link、MAC 收发、DHCP 和 IP 基本连通，可作为 Linux B2 的强对照；但不能证明 Linux 唯一故障点。PHY/link 成功但 DHCP 失败，只证明已通过层级。U-Boot 无法识别 PHY 或建立 link，也不能直接判定硬件损坏。U-Boot 与 Linux 的 control FDT、pinctrl、reset、delay 和初始化路径可能不同。

## 8. 当前结论

目前只能确认当前 U-Boot 有 DHCP/MII/MDIO/ping 命令入口，且实机注册了 ethernet@fe010000 MDIO bus。PHY、link、DHCP、ICMP 均未验证。下一条待执行命令：mii device。本报告不代表网络已经打通。

关联文档：项目 A 总路线图、分阶段实施计划、B1 U-Boot 启动前检查记录及 U-Boot 候选研究报告。

### MII 设备枚举补充（2026-11-22）

现场执行 `mii device`，输出：

    MII devices: 'ethernet@fe010000'
    Current device: 'ethernet@fe010000'

结论：MII 子系统实际枚举到一个设备，名称为 `ethernet@fe010000`，且当前设备已选定为该设备。与此前 `mdio list` 列出的总线名称一致，进一步确认 MII/MDIO 管理接口均关联目标 Ethernet 控制器。此结果仍不证明 PHY 地址/型号已识别、PHY link 已建立或 MAC 数据收发正常。

下一步只读扫描 PHY 地址范围，禁止 MII/MDIO 写操作。建议命令：`mii info 0-31`。

### PHY 查询与 MAC 环境变量检查（2026-11-22）

#### MII PHY 查询语法反馈
尝试 `mii info 0-31`，U-Boot 返回 `Incorrect PHY address. Range should be 0-31`，随后又提示 `No such device: 0-31`。本次命令没有完成 PHY 扫描，不能据此判定地址范围内没有 PHY。后续改为逐个合法 PHY 地址查询，先从地址 0 开始；不执行任何写寄存器操作。

#### U-Boot MAC 环境变量
现场执行 `printenv ethaddr`，输出：

    ethaddr=16:70:f6:c8:b2:95

结论：当前 U-Boot 环境中存在 `ethaddr`，其值为 `16:70:f6:c8:b2:95`。首字节 0x16 的 I/G 位为 0（单播），U/L 位为 1（本地管理地址）。因此这是一个本地管理型单播 MAC，不能仅凭该环境变量认定它就是板载厂商写入的原始 MAC，也不能证明 Ethernet 驱动已经将其配置到 MAC 控制器或实际用于发包。仍需核对 eth1addr/其他接口变量、设备驱动当前 MAC，以及 Panther X2 实际 MAC 存储来源。此次仅 printenv 读取，没有修改环境变量。

当前已知：U-Boot 有 ethaddr 环境变量；板载原始 MAC 是否已正确读取、驱动是否采用该值，仍未确认。

## 9. U0：U-Boot proper 启动完成后的恢复基线（2026-11-22）

用户要求将“U-Boot 已启动并停留在命令提示符、尚未开展网络连通性测试”的状态设为明确检查点。现命名为 **U0（U-Boot post-startup baseline）**。后续网络测试结束必须执行清理并核对回到 U0；不得把测试过程中的临时环境或网络状态留作下一阶段的默认起点。

### U0 当前已知快照

- 启动链：eMMC 前级 SPL → TF 上 JP-TvBox U-Boot proper；当前 proper 为 U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)。
- 当前停留在 U-Boot => 提示符，尚未启动 Linux。
- 当前环境变量已读取：ethaddr=16:70:f6:c8:b2:95。该值是本地管理型单播 MAC；其来源及是否被 Ethernet 驱动实际采用尚未确认。
- mdio list 枚举 ethernet@fe010000；mii device 也枚举并选中同名设备。
- mii info 0-31 语法尝试失败，没有完成 PHY 扫描；PHY 地址/型号、link、DHCP、网关 ping、外部 IP ping 均未验证。
- 已执行的命令均为查询/帮助命令；没有执行 DHCP、没有进行网络下载、没有写 PHY 寄存器、没有执行 setenv/saveenv，没有写 TF/eMMC，也没有启动其他镜像。
- 当前没有安装、加载或写入额外测试组件/固件。网络基准仍处于识别与准备阶段。

### 网络测试结束后的 U0 回归要求

1. 测试前先记录所有将被临时改变的环境变量原值及其原先是否存在；不允许覆盖 ethaddr 等身份变量。
2. DHCP/网络测试如需临时环境变量，只允许 RAM 临时修改，绝不 save/saveenv；避免任何 TFTP/其他下载行为。
3. 测试结束后恢复所有被改变变量的原值；原先不存在的变量应恢复为未定义状态。清除仅由本轮测试产生的临时网络参数，并停止/退出本轮临时网络测试状态（仅使用已核实安全的命令）。
4. 核对 U-Boot 仍停留在同一 proper 的 => 提示符，启动链未切换，ethaddr 等身份变量未变化，临时参数已恢复；确认没有存储写入或新增组件。
5. 若某项运行时状态无法在不重启、不写存储的条件下可靠恢复，不得假称已回到 U0；记录差异并暂停，先制定安全恢复方案。当前授权不包含 reset/reboot。
6. U0 是“U-Boot proper 启动完成、网络测试前”的逻辑检查点，不承诺所有 Ethernet 驱动内部运行时寄存器/PHY 状态与刚启动瞬间逐位相同。若测试初始化会改变这类状态，必须记录并评估是否可无损恢复。

**阶段门：** 只有完成网络测试清理并通过上述核对，才可宣布回到 U0；随后再进入 B1 clean RAM Linux。U0 与未来 B1 的干净 Linux 基线分开管理。


### MDIO 地址 0–4 只读查询结果（2026-11-22）

按单条命令逐项执行，现场结果如下：

| PHY 地址 | `mii info` | `mii read <addr> 1`（BMSR） |
|---:|---|---|
| 0 | 无输出，返回提示符 | `0xFFFF` |
| 1 | 无输出，返回提示符 | `0xFFFF` |
| 2 | 尚未执行 info | `0xFFFF` |
| 3 | 尚未执行 info | `0xFFFF` |
| 4 | 尚未执行 info | `0xFFFF` |

补充：`mii info 0-31` 不接受范围参数，命令报错；随后已改为逐地址读取。地址 0–4 的 BMSR 读值全部为 `0xFFFF`。

**当前解释边界：** 连续多个地址返回全 1，说明本轮 MII 读取尚未获得可识别的 PHY 状态响应；可能涉及 PHY 地址无响应，也可能涉及 MDIO 控制器/总线访问路径。不能仅凭这些结果认定 PHY 不存在、损坏或整个 MDIO 总线故障。此前 `mdio list` / `mii device` 只证明管理总线/设备已注册，不证明 MDIO 实际事务成功。

**操作决定：** 暂停无差别逐地址扫描。下一步先读取当前 U-Boot 的 `help mdio`，核对 MDIO 原生命令的只读 read/rx 参数格式，再判断是否可用另一条只读接口交叉验证。不得执行 write/wx、MII write/modify 或任何 PHY 寄存器写入。当前 DHCP 仍未执行；必须先审计 autoload/TFTP 行为。


### MDIO 原生命令交叉验证：地址 0（2026-11-22）

用户提供的 `help mdio` 确认本构建支持只读命令 `mdio read <phydev> [<devad>.]<reg>`，且 `<phydev>` 可显式指定 `<busname> <addr>`。因此使用明确总线名进行交叉验证：

命令：
```
mdio read ethernet@fe010000 0 1
```

现场输出：
```
Reading from bus ethernet@fe010000

PHY at address 0:

1 - 0xffff
```

结果：原生 MDIO 命令明确选择了 `ethernet@fe010000` 总线并报告 PHY 地址 0，但寄存器 1 仍返回 `0xffff`。这与此前 `mii read 0 1` 的结果一致，降低了“仅 MII 命令前端导致异常”的可能性；但仍不能区分 PHY 无响应、MDIO 电气/时序问题或控制器底层访问异常，也不能据此判定 PHY 损坏。

下一步只读交叉验证地址 1，保持总线和寄存器完全相同：
```
mdio read ethernet@fe010000 1 1
```
不得执行 mdio write/wx 或 mii write/modify。


### MDIO 原生命令交叉验证：地址 1（2026-11-22）

在地址 0 的原生 MDIO 读取返回 `0xffff` 后，保持同一总线和寄存器，仅将 PHY 地址改为 1：

命令：
```
mdio read ethernet@fe010000 1 1
```

现场输出：
```
Reading from bus ethernet@fe010000

PHY at address 1:

1 - 0xffff
```

结果：地址 1 的寄存器 1 同样返回 `0xffff`。因此，当前两个明确指定的 PHY 地址（0、1）在原生 MDIO 路径下均未返回可识别的 BMSR 值；与此前 MII 地址 0–4 的读取结果一致。不能据此判定 PHY 不存在或损坏，也不能区分 PHY 无响应、MDIO 电气/时序问题或控制器底层访问异常。

下一步不进行无目的地址扫描。应先审查当前 U-Boot proper 的源码/构建配置，确认该以太网设备的 MDIO bus 注册、PHY 探测和地址映射路径，再决定是否存在有依据的只读验证步骤。继续禁止任何 MDIO/MII 写入操作。


### 当前 U-Boot proper 的源码/配置审计进展（2026-11-22）

本轮先核对仓库中已有的启动链与候选固件证据，避免把不同阶段的 FDT 或不同构建源码混为一谈：

1. 当前实机 proper banner 为 `U-Boot 2017.09-armbian (Nov 12 2023 - 15:05:14 +0000)`，历史 UART 日志显示其板型字符串为 Radxa ROCK3 Model C；本轮启动链是 eMMC 前级 SPL 加 TF 上 JP-TvBox proper 的混合链。
2. 仓库已归档 JP-TvBox 的 `idbloader.img` 与 `u-boot.itb` 二进制，但对应 Ophub 仓库历史提交只加入二进制资产；尚无该 proper 的精确源码提交、构建脚本、defconfig 或最终 `.config`。不能将较新的 Radxa U-Boot 参考源码当作该二进制的确切构建来源。
3. 已知 JP-TvBox SPL 内嵌 FDT 的 GMAC1 节点为 `status = "okay"`，但它是 SPL 阶段 FDT，不是已确认的 proper FIT control FDT。不能据此直接推断 proper 的 PHY/MDIO probe 配置。
4. 既有报告明确记录 JP proper 的真实 control FDT / 精确源码 provenance 尚未确证。因此当前不能仅靠静态源码断言其 MDIO bus 注册后为何对地址 0、1 返回 `0xffff`，也不能断言 PHY 地址映射或驱动 probe 失败原因。
5. 实机已直接确认 proper 枚举 `ethernet@fe010000`，注册同名 MDIO bus；但地址 0、1 的原生 MDIO BMSR 均为 `0xffff`，MII 地址 0–4 亦均为 `0xffff`。这组事实证明管理接口/总线对象存在，不证明 PHY 响应。

**审计结论：** 当前源码证据不足以进行版本精确的驱动路径归因。下一步不引用其他版本源码作结论，改先查看当前 U-Boot Driver Model 的只读诊断命令是否可用，以核实 Ethernet/MDIO/PHY 设备实际绑定情况。先执行 `help dm`；只查看帮助，不执行任何设备修改命令。


### Driver Model 诊断命令可用性确认（2026-11-22）

现场执行 `help dm`，U-Boot 返回：
```
dm - Driver model low level access

Usage:
dm tree       Dump driver model tree ('*' = activated)
dm uclass     Dump list of instances for each uclass
dm devres     Dump list of device resources for each device
dm aliases    Dump list of aliases
```

结论：当前 proper 提供 Driver Model 只读诊断命令。下一步使用 `dm tree` 查看设备层级和激活状态；输出中的 `*` 按该版本帮助定义表示 activated。此命令只列出设备模型状态，不修改设备。重点核对 `ethernet@fe010000` 及其 MDIO/PHY 子设备，不能把总线注册等同于 PHY 已绑定或链路已建立。


### Driver Model 设备树实测：Ethernet 与 PHY 均已 probe（2026-11-22）

用户执行 `dm tree`，关键原始输出：
```
ebd51a00 ethernet  [ + ]   gmac_rockchip       |-- ethernet@fe010000 **
ebd51b40 eth_phy_ge [ + ]  eth_phy_generic_drv |   `-- phy@0 **
```

按该表的 `Probed` 列，Ethernet 设备和其子级 PHY 设备均显示 `[ + ]`。由此可确认：
- `ethernet@fe010000` 由 `gmac_rockchip` 驱动绑定并已 probe；
- 设备模型下存在 `phy@0`，由 `eth_phy_generic_drv` 绑定并已 probe；
- 这比仅确认 MDIO bus 注册更进一步，但仍不等于真实 PHY 芯片 ID 已成功读取、PHY 型号已识别或物理 link 已建立。

与此前 `mii read` 地址 0–4 以及原生 `mdio read` 地址 0、1 的 BMSR 均为 `0xffff` 形成待解释的证据差异。不得把 generic PHY 设备节点当成已识别的具体 PHY 芯片，也不得据此判断链路状态。

下一步查看各 uclass 的实例清单：
```
dm uclass
```
只读列出，不执行设备修改。


### Driver Model uclass 清单实测（2026-11-22）

用户执行 `dm uclass`，关键结果：
```
uclass 21: ethernet
    [ + ] ethernet@fe010000 @ ebd51a00, seq 1, (req 1)

uclass 90: eth_phy_generic
    [ + ] phy@0 @ ebd51b40, seq 0, (req -1)
```

解释边界：
- Ethernet 与 generic Ethernet PHY 设备均已 probe（`[ + ]`）。
- 两条记录前均无独立的活动标记 `*`；因此当前证据不支持称其处于 activated 状态。
- 输出未列出独立 MDIO uclass 实例；这不推翻此前 `mdio list` 已列出 `ethernet@fe010000` 总线的现场事实。
- `eth_phy_generic` 是 Ethernet PHY uclass，不应与通用 PHY（`phy`）uclass 混为一谈。
- `phy@0` 的设备模型存在及 probe 不证明 PHY ID 已有效读取，也不证明 link up。

下一步仅读取 PHY 地址 0 的 PHY Identifier 1（Clause 22 寄存器 2），以验证其是否能返回有效 ID：
`mdio read ethernet@fe010000 0 2`。


### PHY Identifier 1 只读结果（2026-11-22）

用户执行：
```
mdio read ethernet@fe010000 0 2

Reading from bus ethernet@fe010000
PHY at address 0:
2 - 0x0
```

记录：PHY 地址 0 的 Clause 22 寄存器 2（PHYID1）读数为 `0x0000`。此前同地址寄存器 1（BMSR）为 `0xffff`。当前读数尚不足以构成有效、可识别的 PHY 标识；不能据此认定 PHY 已响应，也不能直接判定 PHY 损坏。下一步只读 Clause 22 寄存器 3（PHYID2），查看 ID 组合是否可识别。


### PHY Identifier 2 只读结果（2026-11-22）

用户执行：
```
mdio read ethernet@fe010000 0 3

Reading from bus ethernet@fe010000
PHY at address 0:
3 - 0xffff
```

地址 0 的 Clause 22 PHY ID 组合当前为：
- Reg 2 / PHYID1 = `0x0000`
- Reg 3 / PHYID2 = `0xffff`

该组合不是可用的有效 PHY 标识。结合 BMSR Reg 1 = `0xffff`，当前尚未从地址 0 读到一致、有效的 PHY 管理寄存器响应。不能仅凭单次读数认定 PHY 硬件损坏或缺失；需继续核实 MDIO 读通路及 PHY 地址。下一步读取地址 0 的 BMCR（Clause 22 Reg 0），作为另一项只读交叉检查。


### PHY Basic Mode Control Register 只读结果（2026-11-22）

用户执行：
```
mdio read ethernet@fe010000 0 0

Reading from bus ethernet@fe010000
PHY at address 0:
0 - 0x0
```

地址 0 的 Clause 22 读数汇总：
- Reg 0 / BMCR = `0x0000`
- Reg 1 / BMSR = `0xffff`
- Reg 2 / PHYID1 = `0x0000`
- Reg 3 / PHYID2 = `0xffff`

这不是一致且可识别的 PHY 管理寄存器响应。尤其不能将 BMCR 的 `0x0000` 当作正常 PHY 默认配置，也不能将 BMSR/PHYID2 的 `0xffff` 当作有效值。结合设备模型中的 generic `phy@0` 已 probe，当前更准确的结论是：DM 设备对象存在并 probe，但 Clause 22 读通路未证明真实 PHY 可通信。可能涉及设备树/PHY 地址绑定、MDIO 控制器访问、时钟/复位/引脚复用或板级连接；现有证据不能区分这些可能性。

下一步不继续试读更多 PHY 地址或寄存器，也不运行 DHCP。改用 `dm devres` 只读查看 Ethernet 设备已申请的资源，核对 probe 时资源状态；该输出不能替代硬件寄存器测量，但可帮助确认设备模型资源路径。


### Driver Model devres 查询（2026-11-22）

用户执行 `dm devres`，终端仅返回提示符，没有任何设备/资源条目：
```
=> dm devres
=>
```

记录边界：本次命令没有输出可供核对的 devres 资源清单。不能据此推断 Ethernet 驱动没有申请任何硬件资源，也不能推断资源申请失败；可能只是该构建的 devres 跟踪/输出没有可列项目。该命令没有改变启动状态。

当前证据仍为：Ethernet DM 设备与 `phy@0` 已 probe；MDIO 地址 0 的 Reg 0/1/2/3 分别读得 `0x0000`/`0xffff`/`0x0000`/`0xffff`；devres 查询无输出。暂不运行 DHCP，也不将无输出解释成硬件故障。下一步回到 U-Boot 网络设备只读状态查询，执行 `mii device` 核对当前 MII 设备选择。


### MII 当前设备选择复核（2026-11-22）

用户执行 `mii device`，输出：
```
MII devices: 'ethernet@fe010000'
Current device: 'ethernet@fe010000'
```

确认：当前唯一列出的 MII 设备及当前选中设备均为 `ethernet@fe010000`。因此此前通过该总线执行的 MDIO/MII 只读访问没有明显的“误选另一条 MII 总线”问题；但这不能证明总线电气通信正常，也不能证明 PHY 地址 0 的绑定正确。

下一步只读检查 U-Boot 当前 Ethernet 活动设备环境变量（`ethact`、`ethprime`），并再次记录 MAC 环境变量；不修改变量。


### Ethernet 活动设备环境变量只读核对（2026-11-22）

用户执行 `printenv ethact ethprime ethaddr`，输出：
```
## Error: "ethact" not defined
## Error: "ethprime" not defined
ethaddr=16:70:f6:c8:b2:95
```

记录：
- `ethact` 未定义。
- `ethprime` 未定义。
- `ethaddr` 已定义为 `16:70:f6:c8:b2:95`。
- `ethact`/`ethprime` 未定义不等于 Ethernet DM 设备未 probe，也不推翻 `mii device` 已确认唯一 MII 设备且当前选择为 `ethernet@fe010000` 的结果。
- MAC 首字节 `0x16` 表明该地址为单播、本地管理地址；其来源和驱动是否实际采用仍未由当前输出证明。

下一步先只读检查 DHCP 相关网络环境变量（`autoload`、`ipaddr`、`serverip`、`gatewayip`、`netmask`、`bootfile`），以确定当前值/未定义状态；在源码确认 DHCP 命令的自动加载行为之前，不执行 DHCP。


### DHCP 相关环境变量初始状态（2026-11-22）

用户执行 `printenv autoload ipaddr serverip gatewayip netmask bootfile`，所有六项均返回 `not defined`：
- `autoload`
- `ipaddr`
- `serverip`
- `gatewayip`
- `netmask`
- `bootfile`

因此当前 U0 环境中这些变量均未定义；后续若为 DHCP 安全控制而临时设置 `autoload=no`，必须先确认当前构建 DHCP 命令实现确实遵循该变量，并在测试结束时恢复为未定义状态（不能留下 `autoload=no`）。当前尚未执行 DHCP。下一步继续只读检查 U-Boot 网络相关命令帮助，确认是否存在独立的 DHCP/网络初始化控制入口；仍不运行网络命令。


### 网络命令组检查（2026-11-22）

用户执行 `help net`，U-Boot 返回：
```
Unknown command 'net' - try 'help' without arguments for list of all known commands
```

结论：当前构建没有名为 `net` 的命令组入口；这不表示没有网络子系统命令，`dhcp`、`ping`、`mii`、`mdio` 已分别存在。DHCP 自动加载安全性仍未核实，因此不执行 DHCP。
