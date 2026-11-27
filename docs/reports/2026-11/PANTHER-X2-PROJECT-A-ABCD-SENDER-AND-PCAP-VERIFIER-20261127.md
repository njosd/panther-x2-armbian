# Project-A ABCD sender 与对端 pcap verifier 实现及构建验收

日期：2026-11-27  
状态：**SOURCE / BUILD / OFFLINE SELF-TEST PASS；未在 Panther X2 实机运行，未发送物理 Ethernet 帧。**

## 1. 目的与范围

将 G0.5 已冻结的 ABCD 单帧规范从“设计规格”推进到可重复构建的工具交付物：

- 独立静态 AArch64 原始 Ethernet sender：`panther-abcd-tx`；
- 独立离线 classic-pcap 校验程序：`verify-pcap.py`；
- GitHub Actions build-only workflow；
- 源码、二进制、pcap verifier、测试输出和 SHA256 manifest 一起归档。

不修改 R1 原 AF_PACKET probe，不修改 Linux 内核/DTB/Kconfig，不构建或修改 G2 runtime，不访问 Panther X2，不写入 SU08G/SN64G/eMMC，不挂载 tracefs/debugfs，不注册 kprobe，不恢复 PMIC/GMAC/MDIO/PHY。

## 2. 发送器实现

源码：`scripts/panther-abcd-tx/panther-abcd-tx.c`

### 2.1 帧格式

| 字段 | 长度 | 编码 |
|---|---:|---|
| Ethernet header | 14 B | broadcast destination、接口实际 source MAC、EtherType 0x88B5 |
| magic | 4 B | ASCII `ABCD` |
| run_id | 4 B | 命令行输入的 8 位十六进制 |
| sequence | 8 B | uint64，大端 |
| payload_len | 2 B | 大端，固定 32（后续 SHA-256 digest 长度） |
| digest | 32 B | SHA-256(magic || run_id || sequence || payload_len) |

Ethernet header 14 B + payload 50 B = 64 B，不含硬件附加 FCS。首轮固定单帧。

### 2.2 运行安全约束

- 必须显式提供 `--interface`、`--run-id`、`--sequence`；没有默认接口。
- 只从 `/sys/class/net/<iface>/` 读取 ifindex、MAC 和 flags。
- 接口必须已 administratively UP；若 DOWN，拒绝发送。
- 拒绝 loopback，避免将本地 outgoing tap 误当成 Ethernet。
- 不设置 IFF_UP，不修改 MAC/IP/route，不启停服务。
- 使用 AF_PACKET/SOCK_RAW，发送完整 Ethernet II frame；仅发送一帧。
- 输出源/目的 MAC、run_id、sequence、payload digest、完整 frame hex、sendto 返回值和 errno。
- 只有 sendto 返回完整 64 字节才标记 `boundary_A=PASS`；始终输出 `wire_delivery=NOT_VERIFIED`。程序不会将用户态提交误报为线侧 TX 成功。

参数解析拒绝负数、正号和空格前缀；支持十进制及 C 风格 `0x` 十六进制 sequence。

## 3. 对端 pcap 校验器

源码：`scripts/panther-abcd-tx/verify-pcap.py`

- 仅离线读取 pcap，不打开网络接口、不执行抓包。
- 支持 classic pcap microsecond/nanosecond、little/big endian。
- 要求 Ethernet DLT（linktype 1）。
- 只解析 EtherType 0x88B5；要求整个 pcap 中恰好一帧匹配。
- 检查 frame length=64、广播目的 MAC、ABCD magic、run_id、sequence、payload_len=32 和 SHA-256。
- 可额外指定期望 source MAC。
- 匹配帧被 snaplen 截断、缺帧、重复帧、字段不符或 digest 不符均失败。
- 当前不支持 pcapng；抓包端应保存 classic pcap（例如 tcpdump 默认 pcap 输出）。

该程序给出的 PASS 表示 pcap 文件中存在唯一、字段和 digest 均正确的目标帧；其物理证据强度取决于 pcap 确实由目标链路另一端的独立主机采集。

## 4. 构建与自动测试

Workflow：`.github/workflows/build-panther-abcd-tx.yml`

最终成功构建：
- Actions run：`45941220581`
- Job：`140315737871`
- Commit：`139ac5bf0f1e3edc3592bee7b314ef74a3acf852`
- Artifact：`15172507107`
- Artifact 名称：`panther-x2-project-a-abcd-tx-sender-static-aarch64`
- Artifact ZIP SHA-256：`9e092f0ce87a04cdcb879a828cceb96b8cf7fe1c9097183f1b1aa532b5f86cf2`
- Artifact 体积：340,855 bytes；保留至 2026-12-27。
- 发送器 ELF：771,480 bytes。

CI 使用 Ubuntu 24.04 的 AArch64 cross toolchain，执行：
1. `-static -O2 -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2` 编译；
2. 检查 ELF machine=AArch64，且无 PT_INTERP；
3. QEMU user-mode 只运行 sender `--self-test`，不创建 AF_PACKET socket、不发送数据；
4. Python `py_compile` 与 pcap verifier synthetic-pcap self-test；
5. 上传源码、静态 ELF、校验器、manifest、测试输出与 SHA256SUMS。

最终自动测试：
- sender 参数校验：PASS；
- SHA-256 标准 `abc` 向量：PASS；
- Ethernet frame 构造及长度：PASS；
- pcap parser synthetic classic-pcap：PASS；
- pcap frame/digest 校验：PASS；
- workflow 所有步骤：PASS。

## 5. 独立 artifact 审计

已下载最终 artifact `15172507107` 并独立检查：

- ZIP 内所有成员均可读取；
- `SHA256SUMS` 中三个交付文件（sender ELF、C source、pcap verifier）逐一重算，全部匹配；
- ELF 独立识别为 64-bit little-endian AArch64 executable；
- ELF 为 statically linked，未发现 PT_INTERP；
- sender ELF SHA-256：`e0f29848bd4bb8378e3925ac1214731dff987a0b3d5fc2d8fe1fe6fe657bc9f9`；
- sender C source SHA-256：`7aeea423d9eefcb7837f3323f65bd1273cb869815c746d2941d18729a901845d`；
- pcap verifier SHA-256：`28d953fe4ec931bd3115805e7af815bc0b7ae10dfeb918a2ed0bad6ec9f3378c`；
- 从最终下载的 verifier 再次执行 `--self-test`，PASS。

## 6. 证据边界

本次结果是：
- SOURCE：PASS；
- BUILD：PASS；
- ELF architecture/static-link：PASS；
- OFFLINE SELF-TEST：PASS；
- ARTIFACT SHA256：PASS；
- Panther runtime：NOT TESTED；
- AF_PACKET on physical GMAC：NOT TESTED；
- STMMAC skb/DMA/descriptor ABCD correlation：NOT TESTED；
- peer-side pcap from Panther transmission：NOT TESTED。

**本工具目前不得放入或替换任何 Panther 启动镜像，也没有实机发送授权。** 后续在 G5/G6 前置条件满足、取得相应授权后，才将独立二进制交付到项目 A runtime；首轮仅允许明确批准的一帧测试。R1 loopback probe 继续独立保留。

## 7. 后续顺序

1. 复用本报告与最终 artifact，不重复构建/自测。
2. 将 pcap verifier 用于独立对端抓包夹具预检：先用已知正常设备发送格式正确的测试帧，验证抓包保存、解析和 hash 校验。
3. G2-PROBE 仍按原 HOLD 条件单独处理，不因 sender build PASS 自动放行。
4. 按 G2→G3→G4→G5→G6 原顺序；一旦 G6-A 的 interface open/DMA 条件满足，执行获准的单帧 ABCD。
5. 最终 TX PASS 必须来自独立对端抓到唯一正确帧（E6），不能以 sender sendto 成功、driver counter 或 DMA completion 替代。
