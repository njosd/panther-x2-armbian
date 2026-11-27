# Panther X2 项目 A — G0-P4 黄金 DTB 证据复核与剩余缺口（2026-11-27）

## 1. 本轮范围

只复用并交叉核对仓库与 Dropbox 已有黄金资产证据，确认 6.1.65、6.1.116 与 6.18.63 的 DTB 证据状态。未启动设备、未访问寄存器、未修改存储、未构建镜像、未发送网络帧。

## 2. 6.1.116 与 6.18.63：DTB 已字节级闭合

仓库既有 6.1.116 备份清单记录：
- `rk3566-panther-x2.dtb` SHA-256：`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`；
- 来源：6.1.116 磁盘 Panther X2 DTB。

R6-3 已从 6.18.63 实际发布 artifact 提取并重新计算同一 DTB SHA-256，结果完全相同。因此 6.1.116 磁盘 DTB 与 6.18.63 完整 DTB 是**字节级相同文件**，不仅是 GMAC 属性相同。

结论：
- 6.1.116 与 6.18.63 的 RK809/regulator/IO-domain/GMAC 所有 DTB 属性及 phandle 均完全一致；
- 不再重复解包 6.1.116 DTB archive，也不再为这两个版本做结构化 diff；
- 对当前 R1 真实 DTB 的判断需区分：R1 是隔离构建产物，不应把完整 6.18 DTB 的状态直接当作 R1 的 GMAC enabled 状态。

## 3. 6.1.65：原始 DTB 身份与已有解析结果

原始 6.1.65 DTB 已有可靠归档身份：
- 文件：`dtb/rockchip/rk3566-panther-x2.dtb`；
- 大小：111,351 bytes；
- SHA-256：`d03ec12df0d69bfa0f0ab5ac462a8fffd8ae5d1c512032ff9468df89248d289f`；
- 原始阶段包：Dropbox `/04-device-tree.tar.gz`，2,256,475 bytes；
- 阶段包内 MANIFEST 对该 DTB 记录同样的大小与 SHA-256。

既有原始 DTB 解析已确认 GMAC1：
- 节点 `ethernet@fe010000`，compatible `rockchip,rk3568-gmac` + `snps,dwmac-4.20a`；
- `status = okay`，RGMII，clock input；
- TX/RX delay `0x30/0x10`；
- MDIO PHY address 0；
- 六组 GMAC1 M0 pinctrl；
- `gmac1_clkin` 125MHz fixed-clock；
- reset GPIO3 line 1 active-low；
- `phy-supply` 指向 `vcc_3v3`。

这已足以确认 6.1.65 原始黄金 DTB 的 GMAC1 核心连接/时钟/PHY 拓扑与 6.18.63 完整 DTB 高度一致。既有解析没有留存 6.1.65 的全部 reset-delay cells，因此该字段不宣称二进制逐项一致。

## 4. 6.1.65 RK809/regulator/IO-domain 子树：证据等级与边界

R3 §22.3 已对 6.1.65 高置信度候选源码与 6.18.63 源码的完整 `rk809: pmic@20` 节点进行比较：
- DCDC_REG1–5、LDO_REG1–9、SWITCH_REG1/2 名称和约束相同；
- SWITCH_REG1 的 `regulator-name = "vcc_3v3"`，无 always-on、boot-on、电压 selector 或 init-voltage 约束；
- 仅 `system-power-controller` 属性从 vendor-prefixed 写法改为标准写法；
- 源码端点为 6.1.65 GOLDEN-CANDIDATE SOURCE，尚未与原始 Image 二进制级绑定。

6.1.65 原始 DTB 的原始字节仍在 Dropbox 阶段包，但当前可用 Dropbox connector 对该 tar.gz 提供的是文本提取/manifest，不能把 tar 内部 DTB 成员直接物化到本轮本地分析环境。本轮没有声称完成 6.1.65 原始 DTB 的 PMIC/IO-domain 子树重新反编译或自动 diff。无需重新提取 851 MiB 镜像，也不应让用户重复历史采集。

因此：
- **已验证：** 6.1.65 原始 DTB 的文件身份/哈希、GMAC1 核心属性；6.1.65 候选源码中的 RK809/regulator 完整子树与 6.18 源码相同。
- **未验证：** 6.1.65 原始 DTB 二进制中的 RK809/regulator/IO-domain 全子树是否逐项与候选源码一致。
- **推测/高置信度：** 由于 6.1.65 和 6.1.116 固定源码端点的 Panther board DTS 与 rk3566.dtsi 完全相同，且 6.1.116 实际 DTB 与 6.18 DTB 完全相同，6.1.65 相关子树大概率采用同一配置；但不把该推断升级为 binary PASS。

## 5. G0-P4 结论

| 项目 | 状态 |
|---|---|
| 6.1.116 ↔ 6.18.63 完整 DTB | PASS — SHA-256 字节级相同 |
| 6.1.65 原始 DTB 身份 | PASS — 111,351 bytes / SHA-256 已归档 |
| 6.1.65 原始 DTB GMAC1 核心属性 | PASS — 复用原始解析记录 |
| 6.1.65 RK809/regulator 候选 DTS 子树 | PASS-CANDIDATE-SOURCE — 与 6.18 相同，只有 system-power-controller 属性写法差异 |
| 6.1.65 原始 DTB PMIC/IO-domain 子树 binary diff | BLOCKED — 仅缺原始 DTB bytes 在本轮环境可用；不需要重新提取镜像 |

**综合结论：G0-P4 CONDITIONAL PASS。** 当前没有发现与网络相关的黄金 DTB 配置回归；唯一未闭合项是 6.1.65 原始 DTB 的 PMIC/IO-domain 子树二进制复核。该缺口保留在证据限制中，不扩大成电源测量任务，也不把它作为重新做 6.1.116/6.18 diff 的理由。

## 6. ABCD 发送测试：逐阶段检查规则细化

ABCD 的目标是追踪**同一帧**，不是每个阶段另发不同内容：

- 固定 EtherType：`0x88B5`；
- payload：`ABCD` + run ID + sequence + length + digest；
- 首轮只发送一帧；
- A：用户态 AF_PACKET/SOCK_RAW 提交，保存原始帧字节、sendto/sendmsg 返回值和 errno；
- B：Linux 网络核心 skb，关联同一 sequence/hash/length；
- C：同一帧进入 `stmmac_xmit`；
- D：同一帧 DMA mapping，记录 DMA address、length、direction；
- D 之后继续关联 TX descriptor、OWN、completion、reclaim/unmap；
- E6：独立 LAN 对端 pcap 确认真实收到正确帧；只有 E6 正确才是物理 TX PASS。

每个阶段末都执行一次“ABCD 可执行性检查”。若尚无 netdev/open/DMA 条件，明确记录 NOT EXECUTABLE 及缺失条件；每连续最多两个阶段必须再次复核。具备条件即优先单帧完整 A→B→C→D，不等 ARP/IPv4/TCP/UDP。不得以 netdev counter、DMA completion、link up 替代 E6。

建议检查点：
- G1/G2 后：检查 PMIC/provider 是否仍阻塞；
- G3/G4 后：检查 IO-domain、clock/reset/pinctrl 条件和 netdev 可能性；
- G5-A/G5-B 后：检查 netdev 注册、PHY bind/link；未 open 不发；
- G6：首次具备 open/DMA 后，优先做完整单帧 A→B→C→D + descriptor/OWN/completion/reclaim；
- G7：保持同一帧定义与环境，增加对端 pcap，取得 E6；
- G8：RX 引入后复测 TX；
- G9 每个 ARP/IPv4/ICMP 子阶段后复测 TX；
- G10 TCP、UDP 及按需 DHCP/DNS 每个子阶段后复测 TX。

## 7. 下一步

1. 将 G0-P4 记为 CONDITIONAL PASS，不再重复已完成的 6.1.116/6.18 DTB 对照。
2. 做 G0 总体评审：列明尚存的 6.1.65 原始 DTB binary 限制、R3 provider HOLD、IO-domain runtime UNKNOWN、clock 物理波形 UNKNOWN，以及每项是否是下一阶段的真实阻塞。
3. 形成 G1 的只读/静态实施清单和独立操作边界；不在本报告中授权或执行设备操作。
4. 按上述频率执行 ABCD 可执行性检查，不能连续跨过两个阶段而不重新评估。

