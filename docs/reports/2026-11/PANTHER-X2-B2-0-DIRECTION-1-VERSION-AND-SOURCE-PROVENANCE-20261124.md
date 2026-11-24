# Panther X2 B2-0 方向1：版本样本与历史构建来源追溯补充（2026-11-24）

## 1. 状态说明

本报告只记录 B2-0 方向1目前能够直接证实的版本样本与构建来源。**方向1仍未结项**，不放行 B2-1。

已知方向1检查点：
- 正常 6.1.y 基线：6.1.65、6.1.79、6.1.112、6.1.116；
- 故障样本：6.1.174-rk35xx、6.12.81-rk35xx；
- 确定 6.1.y 系列首次故障的小版本；
- 追溯 6.1.174 原始构建的 source_hash；
- 追溯用户历史下载/解包的 Ophub 6.18.63 的实际来源。

本轮补齐了 6.1.174 原始构建来源，并对 6.18.63 的多个历史构建和 Release 资产替换进行了直接追踪；仍不能把用户缓存的旧 6.18.63 .deb 映射到某一个 source_hash，也没有找到 6.1.y 首次故障小版本。

## 2. 已确认的版本样本

| 版本 | 当前证据状态 | 说明 |
|---|---|---|
| 6.1.65 | 实机正常基线 | 原始镜像、Kernel、DTB、initramfs 资产已归档 |
| 6.1.79 | 实机正常基线 | 用户确认曾在 Panther X2 实机正常运行 |
| 6.1.112 | 实机正常基线 | 用户确认曾在 Panther X2 实机正常运行 |
| 6.1.116 | 实机正常基线 | 当前历史稳定运行基线；运行日志与配置归档 |
| 6.1.174-rk35xx | 已确认故障样本，但不是首次故障版本定案 | 原始自动构建来源已由 run #296 日志直接确认 |
| 6.12.81-rk35xx | 已确认故障样本 | 实机 UART 记录确认运行版本及启动过程；构建来源已由 run #298 日志直接确认 |
| 6.1.192-ophub | 不计入实机启动测试 | 备份记录中存在 6.1.192 package/config/initrd，但 `uname -r` 仍为 6.1.116，`Image` / `uInitrd` 符号链接仍指向 6.1.116；不能把已下载/解包或已安装包当作实际启动版本 |

### 2.1 6.1.174 原始构建来源已闭环

- Workflow run #296：<https://github.com/ophub/kernel/actions/runs/42812333074>
- Job：<https://github.com/ophub/kernel/actions/runs/42812333074/job/129816642520>
- Job ID：`129816642520`
- `kernel_source=ophub/linux-6.1.y-rockchip`
- `kernel_version=6.1.y`
- `kernel_auto=true`
- `kernel_sign=-rk35xx-ophub`
- `kernel_config=kernel-config/release/rk35xx`
- 实际 `source_hash=c2f148dece4b67ebd30aefad1bdd1990f41e5633`

因此，6.1.174 原始自动构建的源码身份已验证；但它仍只是一个已确认故障样本，不能据此宣称它是 6.1.y 系列的首次故障小版本。

详细结项报告：
`PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md`

### 2.2 6.12.81 原始构建来源已闭环

- Workflow run #298：<https://github.com/ophub/kernel/actions/runs/43405957386>
- Job：<https://github.com/ophub/kernel/actions/runs/43405957386/job/131820239401>
- Job ID：`131820239401`
- `kernel_source=ophub/linux-6.12.y-rockchip`
- `kernel_version=6.12.y`
- `kernel_auto=true`
- `kernel_sign=-rk35xx-ophub`
- `kernel_config=kernel-config/release/rk35xx`
- 实际 `source_hash=661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
- 日志确认编译输出 `6.12.81-rk35xx-ophub`

这证明 6.12.81 故障样本的自动构建来源，不等于对历史设备安装文件逐字节复现。

## 3. 历史 Ophub 6.18.63：不能只看版本号或当前 Release 文件

### 3.1 正确的发布系列

Ophub 仓库说明：
- `kernel_stable` / `kernel_beta` 包含通用 6.18.y 源码系列，支持 Rockchip；
- `kernel_rk35xx` 是 Rockchip 专用 BSP 系列，覆盖 6.1.y / 6.12.y，不是 6.18.y 的发布系列。

因此，本次历史 6.18.63 追踪对象是 `ophub/kernel` 的 `kernel_stable` Release，而不是 `kernel_rk35xx`。

### 3.2 用户历史缓存的时间边界

既有对话记录确认：用户于 **2026-11-13 04:19Z** 已下载并解包 `linux-image_6.18.63-1-ophub_arm64.deb` 等 6.18.63 包；当时没有安装 linux-image，没有配置其余内核包，也没有实机启动或网络测试。

在此之后，GitHub Actions 于 2026-11-13 08:19Z 开始 run #995。该 run 日志明确表示原 Release 中已存在的 `6.18.63.tar.gz` 和 `deb-6.18.63.tar.gz` SHA-256 不匹配，随后删除旧资产并重新上传。因此，用户 04:19Z 缓存的包早于 run #995 的资产替换；不能用后来 Release 页面当前显示的 SHA-256 反向代表用户当时缓存的包。

### 3.3 能直接确认的三次 6.18.63 自动构建

三次构建都生成了 `6.18.63-ophub`，但使用了三个不同的 source_hash：

| Run | 时间（UTC） | Job ID | source_hash | 构建参数 |
|---|---|---|---|---|
| #995 | 2026-11-13 08:19 起 | `131775063661` | `9356ffeb0b6d03d7d0b1b7a8b3da0e7742de17a5` | `ophub` / `6.18.y` / auto=true / sign=-ophub / `kernel-config/release/stable` |
| #997 | 2026-11-16 00:11 起 | `133011349940` | `80ac0a0a3934ee2b0c8897455bfdf8d39901986e` | 同上 |
| #998 | 2026-11-16 02:19 起 | `133050721768` | `aee4e352a15d636cbc484f56819c6e59474dfd9f` | 同上 |

原始日志链接：
- #995：<https://github.com/ophub/kernel/actions/runs/43392333822>
- #997：<https://github.com/ophub/kernel/actions/runs/43778877807>
- #998：<https://github.com/ophub/kernel/actions/runs/43791481468>

资产替换记录：
- run #995 删除了此前的 `6.18.63.tar.gz` asset ID `735082980` 和 `deb-6.18.63.tar.gz` asset ID `735083247`；
- run #997 删除了 run #995 上传的 asset ID `742908742`、`742909041`；
- run #998 删除了 run #997 上传的 asset ID `752848907`、`752849163`；
- 旧 asset ID 当前经 GitHub API 查询均返回 404，无法再直接下载或取得其原始 digest。

当前 Release 中的资产来自 run #998：
- `6.18.63.tar.gz`：asset ID `753186786`，SHA-256 `67d2d78a570cb6128ec2c9546bd11f1ca2f32305325c146cd724d856654e51e9`；
- `deb-6.18.63.tar.gz`：asset ID `753187000`，SHA-256 `5437359f3127c836fc6f9cacffef2410756d25003fb526589b95b93492680546`。

### 3.4 6.18.63 历史来源结论

**已验证：**
1. Ophub 在 2026-11-13 至 2026-11-16 至少执行了三次 6.18.63 自动构建。
2. 三次构建的 source_hash 分别为 `9356ffeb...`、`80ac0a0a...`、`aee4e352...`，并非同一个源码快照。
3. 每次重传均替换之前已存在的同名 Release 资产。
4. 2026-11-23 项目 A 使用的源码快照 `aee4e352...`，也确实在历史 Ophub run #998 中作为 6.18.63 自动构建的 source_hash 出现；这次匹配是由 run #998 原始 job log 独立证实，不是根据项目 A 构建倒推。
5. 本次 Kconfig / Makefile 审计所用 `aee4e352...` 是 run #998 的真实 6.18.63 源码快照。

**仍未验证：**
1. 用户在 2026-11-13 04:19Z 缓存的本地 `.deb`，无法仅凭版本字符串映射到 #995 / #997 / #998 中任意一次构建；它早于 #995，可能来自已删除的旧 Release asset。
2. 已删除的旧资产 ID `735082980` / `735083247` 对应的原始 SHA-256 和构建 source_hash 未能从当前 GitHub API 恢复。
3. 用户本地缓存的 `linux-image_6.18.63-1-ophub_arm64.deb` 与当前 run #998 的 `deb-6.18.63.tar.gz` 是否字节一致，尚无本地文件 SHA-256 证明。
4. 6.18.63 仅下载/解包，未安装、未启动、未做实机网络验证；不能作为 Panther X2 已验证正常或故障版本。

因此，**不能把 `aee4e352...` 自动写成用户本地历史 6.18.63 包的源码身份**。它是一个已验证的 Ophub 6.18.63 构建来源，但不一定是用户在 11 月 13 日缓存的那一份。

## 4. 6.1.y 首次故障版本：仍未定案

当前可确认：
- 6.1.65、6.1.79、6.1.112、6.1.116 为正常实机基线；
- 6.1.174-rk35xx 是已确认故障样本，source_hash 已闭环；
- 6.1.192 不能算实机测试：备份记录中虽有 6.1.192 包文件，但当时 `uname -r` 和活动启动链接仍是 6.1.116；
- 用户确认 6.1.116 之后多个 6.1.y 出现同类故障，但当前可检索记录没有恢复出每一个实际测试小版本及其先后顺序。

所以目前不能宣称 6.1.174 是首次故障版本，也不能把 6.1.192 作为故障版本。

## 5. 方向1结项判定

<badge>未结项</badge>

方向1尚缺两项必要证据：
1. **历史 6.18.63 本地缓存包身份**：需要用户当时缓存的 `linux-image_6.18.63-1-ophub_arm64.deb` 文件本身，或该文件的 SHA-256，才能与历史/当前 Release 资产做匹配。
2. **6.1.y 首次故障小版本**：需要明确实际启动并确认出现故障的第一个小版本及其证据；不能由 6.1.174 故障样本或 6.1.192 包文件推断。

B2-0 方向1未结项前，不进入方向2；B2-1 网络核心仍未放行。此前完成的四版本资产闭包、6.1.174 source_hash、6.18.63 Kconfig/Makefile 静态审计均保留为已完成子项，不重复执行。

## 6. 相关归档

- [四版本内核主链与启动资产闭包](./PANTHER-X2-B2-0-FOUR-VERSION-KERNEL-ASSET-CLOSURE-20261124.md)
- [6.1.174 原始构建 source_hash 结项](./PANTHER-X2-B2-0-6.1.174-BUILD-PROVENANCE-CLOSEOUT-20261124.md)
- [6.18.63 Kconfig / Makefile 依赖审计](./PANTHER-X2-B2-0-6.18.63-KCONFIG-MAKEFILE-DEPENDENCY-AUDIT-20261124.md)
- [6.1.65 原始镜像静态审计](./PANTHER-X2-6.1.65-ORIGINAL-IMAGE-AUDIT-20261123.md)
- [6.12.81 实机 UART 取证与启动记录](./PANTHER-X2-P1-INITRAMFS-BOOT-CHAIN-AUDIT-PROGRESS-20261120.md)
