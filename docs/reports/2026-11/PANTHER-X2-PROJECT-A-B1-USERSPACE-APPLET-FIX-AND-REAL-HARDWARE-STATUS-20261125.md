# Panther X2 Project A — B1 用户空间 applet 修复与实机状态（2026-11-25）

- 阶段：B1 完整基础配置、网络隔离基线
- 适用分支：`architecture/b1-full-base-network-isolation`
- 固定 Kernel：Linux 6.18.63，源码 commit `aee4e352a15d636cbc484f56819c6e59474dfd9f`
- 本报告性质：已完成实机结果的归档 + 一个已定位用户空间缺陷的定点修复；不代表新修正版已经通过 CI 或实机复验。

## 1. 已经完成的 B1 构建与实机验证（不重复）

### 1.1 既有构建产物

- Kernel/DTB 成功构建来源：Run `45309219886`（Run #73）。
- 修正版 BusyBox/打包：Run `45328201244`。
- 最终 artifact：`panther-x2-b1-clean-ram-prepare-only`，Artifact ID `14890817693`。
- 解压镜像 SHA256：`26b35287d0f1b952d5d97fc0e89763751d237e490f35bd5120c7ffb3bdc29eb`。
- 压缩镜像 SHA256：`9a03ab47e9fc6222d46060ea90823b14e6665713ce40fb7e90f5906ef97bd511`。
- Run #77（`45328201244`）明确复用了 Run #73 的 Kernel/DTB artifact，没有重复构建 Kernel/DTB。

### 1.2 实机结果

用户已将 Run #77 镜像写入专用 SU08G TF 卡，并报告：
- U-Boot 自动执行 `boot.scr`；
- Linux 6.18.63 正常启动；
- Panther X2 DTB/initramfs 进入 `/init`；
- 出现 BusyBox shell 提示符 `(panther-x2-b1-clean) #`。

因此，B1 的自动启动主链已经有实机证据，不应再把 B1 标成“尚未启动”，也不应重复写入同一个旧镜像。

### 1.3 已知剩余问题

UART 输出出现：

```text
/init: line 18: [: not found
```

问题发生在 /init 用户空间，不是 Kernel panic、DTB 解析失败或 U-Boot 启动失败。Shell 随后仍成功进入交互提示符。

## 2. 根因定位

对 Run #77 所使用的 B1 分支 workflow 进行逐行核对：

- BusyBox binary 已启用 `CONFIG_TEST=y`，`test` applet 在 applet allowlist 中；
- initramfs 组装步骤创建了 `ash`、`sh`、`test`、`echo`、`printf`、`ls` 等链接；
- 但链接循环遗漏了字面名称 `[`；
- `/init` 使用 POSIX 条件表达式 `[ -r /proc/device-tree/model ]`；
- 因此该条件命令在 initramfs 中找不到对应的 `/bin/[` 链接，打印 `[: not found`。

这是一个精确的 initramfs 文件布局/BusyBox applet 链接问题。没有证据表明需要改 Kernel、DTB、启动地址或硬件配置。

## 3. 已提交的定点修复

### 3.1 initramfs 组装

提交 `00f062de06eeea94c42870e7b1ec58673785c72a`：
- 在 initramfs applet symlink allowlist 中增加字面名称 `[`；
- 其他 B1 网络隔离和硬件配置不变。

### 3.2 CI 验收

提交 `c3a35823d06bda8cccb1bd7e01241fad1c3bad21`：
- 在 BusyBox applet 验证清单中增加 `[`；
- 对 applet 名称采用固定字符串匹配 `grep -Fqx`，避免将 `[` 当成正则表达式；
- 保留既有 `CONFIG_TEST=y`、网络 applet 禁止清单和 applet 数量上限。

### 3.3 当前 Actions 状态

- Run #79：`45635993338`，commit `c3a35823d06bda8cccb1bd7e01241fad1c3bad21`，触发事件为 push。
- 最近检查时状态：Kernel/DTB Job 正在执行源码检出，后续会执行构建、BusyBox 验证和 PREPARE-ONLY 镜像打包。
- 该 push run 没有带 workflow_dispatch 的 Kernel artifact reuse input，因此它会重新构建 Kernel/DTB。此构建重复了已由 Run #73 成功验证的部分；本次由自动 push trigger 引起，后续不再无故重复。
- Run #80 `45636107132` 与 Run #81 `45636161047` 因 workflow expression 配置无效而在创建 Job 前失败，没有执行任何构建步骤，也没有产出 artifact；不得把它们当成 Kernel/BusyBox 构建失败。
- Run #78 `45635977097` 被后续并发运行取消，没有作为验收证据。

## 4. 下一步严格顺序

1. 等待 Run #79 完成；先核对 job 状态和 artifact，不提前写卡。
2. 验证最终 initramfs 文件清单确实包含 `bin/[`，BusyBox applet list 包含 `[`，且网络工具仍未启用。
3. 验证 `/init` 的条件表达式在 CI/QEMU 环境中无 `[: not found`，并检查 initramfs/uInitrd 与最终 TF 镜像哈希。
4. 新 artifact 通过审查后，才对 SU08G 写入这份新镜像；不写 SN64G，不写 eMMC。
5. Panther X2 再次从 SU08G 启动，重点复验 /init 的设备型号分支、完整诊断输出和 BusyBox shell；已经通过的 U-Boot 自动启动、Kernel banner、PSCI 不作重复长测。
6. 如果 /init 不再出现 `[: not found`，且设备型号读取、proc/sysfs、shell 均正常，则关闭该 B1 用户空间遗留项。

## 5. 安全与范围

- SU08G 是当前专用 B1 测试 TF；SN64G 旧对照卡保持不动。
- 不向 eMMC 写入任何数据，不改 U-Boot 环境，不安装软件，不修改系统配置。
- B1 仍然只证明正常基础硬件支持与网络隔离条件下的启动链，不证明 Ethernet/GMAC/MDIO/PHY 或 TX 功能。
- 本次修复只补齐 BusyBox `[` 链接和 CI 检查，不引入网络 applet，不改变 B1 的网络隔离边界。
- 只有新 artifact 完成静态审查后才进行下一次 TF 写入；不重复写入 Run #77 的旧镜像。

## 6. 状态

| 验收项 | 状态 |
|---|---|
| Run #73 Kernel/DTB build | PASS |
| Run #77 BusyBox/package build | PASS |
| Run #77 image written to SU08G | 已由用户报告完成 |
| U-Boot automatic boot | PASS |
| Linux 6.18.63 / Panther X2 DTB / initramfs | PASS |
| BusyBox interactive shell | PASS |
| /init `[` command | FAIL，根因已定位 |
| `/bin/[` symlink repair | 已提交，待新 CI |
| Corrected artifact | 待 Run #79 完成 |
| Corrected artifact reflash + focused boot | 待 artifact 审查后执行 |

