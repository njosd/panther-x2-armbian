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
