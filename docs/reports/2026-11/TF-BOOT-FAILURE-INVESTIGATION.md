# Panther X2 TF 启动故障调查

> 日期：2026-11-15
> 状态：基于已有实机结果与历史审计记录的阶段性归纳；等待原始 UART 日志归档后继续。
> 本报告不授权修改 192.168.x.6、eMMC、内核、驱动或网络服务。

## 当前主线

先让 Panther X2（RK3566）上的最小系统稳定启动。当前优先调查 Ophub Linux 6.12.81 从独立 TF 卡启动时，MMC 已枚举后发生 EXT4/JBD2 写入 I/O 错误的原因。不部署 Immich，不启用 NPU，不写入 eMMC。

## 已有实机结果

| 系统/版本 | 介质 | 观察结果 | 结论 |
|---|---|---|---|
| Ophub 6.12.81 | 独立 TF 卡 | UART 显示 Linux 6.12.81 内核启动；MMC 识别 SDXC，出现 mmcblk0 和分区；随后出现 EXT4/JBD2 superblock/journal 写入 I/O error | 内核启动及 MMC 枚举已确认；根因未确认 |
| FNNAS v389 / 6.12.41-trim | 独立 TF 卡 | 能进入 UART 终端并执行命令；网络不通、SSH 不可用 | TF 启动到 shell 已确认；网络问题未定位 |
| 6.1.116 | eMMC | 原系统网络及功能正常 | 正常基线；不是本轮写入目标 |

### 救援参数的来源

panic=-1 systemd.unit=emergency.target 是此前为 UART 救援检查主动添加的截停参数，目的是进入 emergency 模式检查。它不是 FNNAS 原生配置差异，也不能作为 Ophub 6.12.81 故障原因。后续需要救援 shell 的测试应保留该参数，不得将其缺失或存在误判为根因。

## 已完成、不要重复的检查

根据已有项目记录，以下工作已经完成，不应无理由重复：

- 镜像 SHA-256 / gzip 完整性、GPT 分区表和分区布局检查。
- boot 分区只读挂载、root 分区只读且禁止 journal 回放挂载。
- root 分区离线 e2fsck -fn 检查。
- U-Boot 启动文件与 rootfs 副本一致性检查。
- Panther X2 DTB 提取、反编译及关键启动节点静态审计。
- Panther X2 DTS 中 UART、MMC/TF/eMMC、GMAC 等相关配置静态检查。
- 部分内核驱动/模块存在性及内建配置检查。
- FNNAS 启动参考归档及其 DTB/启动配置审计。

细节请回看 [首启与路线基线](../../FIRST-BOOT-AND-ROADMAP-2026-11-15.md) 及 [DTB 检查记录](../../DTB-INSPECTION-2026-11-14.md)。如有新的反证，再针对性复核，不重跑全套检查。

## 当前真正未证明的问题

核心问题是：为什么 Ophub 6.12.81 在 MMC 已枚举 TF 卡及分区后，运行时发生 EXT4/JBD2 写入 I/O error，而此前离线文件系统检查没有发现结构性错误？

仍缺少的证据：

1. 首个底层 block/MMC 错误是否早于 EXT4/JBD2 报错。
2. 请求涉及的设备号、LBA、读写方向、错误码，以及是否出现 timeout、CRC、retry 或 controller reset。
3. root 分区 UUID 与启动参数 rootdev= 是否精确匹配。现有记录尚不能证明已逐项核对。
4. 实际使用的 MMC host、TF 分区及 rootfs 挂载目标是否符合预期。
5. FNNAS 与 Ophub 的 MMC 运行时行为是否有差异；静态 DTS 相似不代表运行时等价。

这些是待验证问题，不代表已经发现 UUID 错误、TF 卡损坏或 MMC 驱动缺陷。

## 下一步

1. 用户将完整 UART 原始日志上传到仓库后，先定位最早的 MMC/block I/O 错误、LBA、错误码和请求类型，检查 EXT4/JBD2 报错前是否已有底层 timeout/CRC/retry/reset。
2. 依据日志缺口，才决定是否补查 root UUID ↔ rootdev、关键 kernel config 或编译后 DTB 的特定属性。
3. 只有形成明确假设后，才设计单变量实机验证；任何写卡操作必须确认目标是独立 TF 卡，禁止写入 eMMC。

## 证据等级

- 已验证（实机）：FNNAS v389 可从 TF 卡启动并进入 UART 命令行。
- 已验证（实机）：Ophub 6.12.81 内核已启动并枚举 TF 卡 MMC 设备；之后发生 EXT4/JBD2 写入 I/O 错误。
- 已验证（离线静态）：6.12.81 镜像此前通过 GPT、只读挂载及离线文件系统检查。
- 未验证：6.12.81 首个底层 I/O 错误的原因。
- 未验证：FNNAS 网络不通的具体原因；暂不与 6.12.81 EXT4 问题混为一谈。
- 推测/候选：MMC 运行时链路、启动参数/设备定位及 rootfs 挂载流程仍需结合原始日志判断。

## 原始证据归档

- UART 原始日志：待用户上传到 evidence/uart/；必须保留原始文件，并记录 SHA-256、采集设备、波特率和测试镜像。
- Actions 报告：引用对应 run/artifact 链接，不将 Actions 摘要冒充原始 UART 日志。
- 分析报告另存，不修改原始日志。