# 6.1.116 JL2xx1 workaround：PHYCR2 全寄存器写入副作用复核（2026-11-18）

## 1. 本轮纠正

承接：
- `JL2XX1-WORKAROUND-RTL8211F-REGISTER-SEMANTICS-20261118.md`
- `116-RTL8211F-DRIVER-PHYCR2-PRESERVATION-AUDIT-20261118.md`

前两份报告只强调了 `0x1801` 中置位的 CLKOUT 字段和 bits[13:12] Reserved 编码，**遗漏了完整寄存器写入会把其他 RW 位清零**。本报告更正这一点，并用 6.1.116 历史运行记录交叉检查。

## 2. 0x1801 的完整位影响

目标寄存器：
- RTL8211F PHYCR2
- Page `0xa43`（十进制 2627）
- Register `0x19`（十进制 25）

`0x1801` 置位：bit12、bit11、bit0；清零：bit15:13 中的 bit13、bit10:8、bit7、bit6、bit5、bit4、bit3、bit2、bit1（忽略 RO 字段实际写入效果）。

按 RTL8211F Rev.1.7 datasheet PHYCR2 表：

| 位 | 字段 | 默认值 | 写入 0x1801 后的写入值 | 可能含义 |
|---|---|---:|---:|---|
| 13:12 | CLKOUT SSC Capability | 00 | 01 | Datasheet 标记为 Reserved 编码 |
| 11 | CLKOUT Frequency Select | 1 | 1 | CLKOUT 125 MHz |
| 5 | PHY-mode EEE Enable | 1 | 0 | 禁用 PHY-mode EEE |
| 1 | RXC Enable | 1 | 0 | 禁用 RXC clock output |
| 0 | CLKOUT Enable | 1 | 1 | 启用 CLKOUT |

特别是 bit 1：datasheet 明确称为 RXC Enable，RXC 是 PHY 到 MAC 的 RGMII 接收时钟。datasheet 的 RGMII 说明明确指出 RXC 总是由 PHY 产生。若 bit1=0 确实生效，按该字段描述会影响 RGMII 接收时钟输出，是比 CLKOUT Reserved 编码更直接的潜在风险。

bit5=0 还会关闭 PHY-mode EEE Enable。不能把此前只分析 0x1801 置位字段的报告当作完整副作用评估。

## 3. 与 6.1.116 历史实机记录出现矛盾

仓库已有历史采集文件：
`evidence/network/panther-eth-baseline-redacted.txt`

其中记录：

- dmesg：RTL8211F driver 已绑定，PHY 地址 0；
- eth0 carrier=1，operstate=up；
- dmesg：Link is Up - 1Gbps/Full；
- `ethtool --show-eee eth0`：`EEE status: enabled - active`。

这与“0x1801 已成功且持续把 RXC Enable(bit1) 和 PHY-mode EEE Enable(bit5) 清零”的简单解释存在明显张力，尤其是 EEE 显示 active。

但这并不能直接证明四次 MDIO write 没执行，也不能证明寄存器没有被写入。可能性仍包括：
1. 某次 MDIO write controller transaction 失败；返回值被 stmmac workaround 忽略；
2. 控制器完成了 MDIO frame，但 PHY 未接受/未保留对应写入；
3. 软件 reset 或芯片具体变体对这些字段的实际行为与目前推断不同；
4. 运行记录中的 EEE 状态是标准 EEE/MMD 协商状态，其与 PHYCR2 bit5 的关联需要进一步核实，不能单凭 `enabled - active` 判定 PHYCR2 bit5 当前值。

目前没有 PHYCR2 的实机读回值，也没有 MDIO 事务波形/总线级 ACK 证据。

## 4. Soft reset 能否解释位恢复？

RTL8211F Rev.1.7 datasheet 有两条相关说明：

- PHYCR2 设置后，Note 1 要求执行 Page 0 / Reg 0 / bit15 software reset；
- BMCR 描述明确说软件 reset 后 Register 0 和 Register 1 返回默认值。

Datasheet 并未在上述 BMCR 说明中明确列出 PHYCR2 也会被 reset 到默认值。因此不能以“BMCR soft reset 会恢复 PHYCR2 默认值”作为已证实解释。反过来，PHYCR2 设置后要求 software reset 的说明也意味着该寄存器设置预期需要在 reset 后生效，但仍不足以独立证明具体 RTL8211F silicon revision 的所有字段保持规则。

需要芯片实测读回或 Realtek 更详细的寄存器/应用说明才能定论。

## 5. 对驱动后续覆盖行为的复核

此前源码审计确认：
- RTL8211F `rtl821x_probe()` 缓存 PHYCR2 bit0；
- `rtl8211f_config_init()` 只用 bit0 mask 更新 PHYCR2；
- 不会显式恢复 bit1、bit5 或 bits[13:12]。

这仍然成立。但它只说明 Linux PHY driver 不会主动覆盖这些字段，不能代替 PHY 内部 reset/硬件行为，也不能证明 116 workaround 的 MDIO write 成功。

## 6. 当前结论分级

### 已确认
1. 116 源码会在成功 MDIO bus 注册后发起四次 MDIO write；返回值忽略。
2. 第二次写入是对 PHYCR2 的整寄存器写 `0x1801`，不是只设置 CLKOUT 字段。
3. RTL8211F datasheet 把 bit1 定义为 RXC Enable、bit5 定义为 PHY-mode EEE Enable；两位默认值均为 1。
4. `0x1801` 将 bit1、bit5 写为 0，同时 bits[13:12]=01（Reserved 编码）。
5. 116 历史运行记录显示 1Gbps link up，EEE status enabled-active。
6. RTL8211F Linux PHY config_init 只 mask bit0，不会主动恢复 bit1/bit5。
7. Datasheet 没有明确说 BMCR software reset 会把 PHYCR2 一并恢复默认；不能据此假设位值被 reset 清除。

### 未确认
1. 四次 write 的 MDIO controller 返回值；
2. PHYCR2 在四次写入后的实际读回值；
3. bit1/bit5 在该 Panther PHY silicon revision 上的实际状态；
4. PHYCR2 bit5 与 ethtool EEE enabled-active 的对应关系；
5. 此 workaround 是否实际影响过 116 的 RGMII RX clock。

## 7. 对调查主线的影响

这项差异值得进一步优先查证，但现有事实之间存在矛盾：

- 源码调用路径支持“驱动发起写入”；
- 写入值若按 RTL8211F datasheet 完整生效，会关闭 RXC 输出；
- 116 历史记录却显示 1Gbps link up 和 EEE active；
- 目前缺少 PHYCR2 readback，不能判断矛盾来自 write 未成功、芯片 reset/寄存器行为、或 EEE 状态的不同语义。

因此不能得出“116 靠这次写入关闭 RXC 仍正常”，也不能得出“这次写入肯定失败”。前述两个结论都超出现有证据。

## 8. 最小下一步

静态审计已经无法确定 PHYCR2 最终状态。若用户授权，最小实机验证应只读：
1. 确认当前运行内核/PHY 绑定身份；
2. 使用现有 MDIO 工具读取 page `0xa43` / reg `0x19`；
3. 恢复原 page selection（若工具会改变 page）；
4. 不写 PHY 寄存器、不触发 PHY reset、不 down/up 网卡、不重启服务。

该只读结果只能说明当前运行状态，不能直接还原 6.1.116 历史时刻的寄存器值。若要知道 116 当时的值，必须有当时采集记录或复现 116 启动环境；不应把当前读回冒充历史状态。
