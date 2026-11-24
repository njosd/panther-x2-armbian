# Panther X2 B2-0：6.1.174-rk35xx 原始故障构建源码身份核验补充（2026-11-24）

## 1. 本次核验目标

补齐 2026-11-19 原《6.1.174-rk35xx Actions 构建运行与源码提交关联核验》报告中的唯一关键缺口：直接读取原始 Actions run #296 的 job log，确认 step 5 实际写入的 `source_hash` 以及本次构建的实际参数。

本次仅核验公开 GitHub Actions 元数据和日志；不访问 Panther X2，不启动故障内核，不读写设备，不修改配置，不制作补丁。

## 2. 原始故障发布资产身份

沿用既有报告已核实的官方自动发布资产：

- Release：`ophub/kernel`，tag `kernel_rk35xx`
- Asset：`6.1.174.tar.gz`
- Asset ID：`731478275`
- 创建时间：`2026-11-10T13:09:30Z`
- 大小：`135,267,299 bytes`
- SHA-256：`49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a`

既有 run/asset 时间关联显示，该资产创建时间落在 run #296 的 “Upload Kernel to Release” step 执行窗口内。

## 3. 原始 Actions run 与 job

- Workflow：`Compile rockchip rk35xx kernel`
- Workflow path：`.github/workflows/compile-rockchip-rk35xx-kernel.yml`
- Run number：`296`
- Run ID：`42812333074`
- Workflow head SHA：`f8925391bb2ba2634bb8ca55da39e1a2f4029ffe`
- Event：`workflow_dispatch`
- Actor：`ophub`
- Job ID：`129816642520`
- Job started：`2026-11-10T12:02:09Z`
- Step 5 “Get kernel source commit hash”：约 `2026-11-10T12:04:15Z`
- Step 7 “Compile the kernel [ 6.1.y ]”：`12:04:15Z–13:09:27Z`
- Step 8 “Upload Kernel to Release”：`13:09:27Z–13:09:40Z`

本次直接调用 GitHub Actions job-log 读取接口，成功取得此前报告未能读取的 run #296 原始日志。

## 4. job log 直接证实的实际构建参数

run #296 的 job log 在 step 5 后输出：

| 参数 | 日志中的实际值 |
|---|---|
| `kernel_source` | `ophub/linux-6.1.y-rockchip` |
| `kernel_version` | `6.1.y` |
| `kernel_auto` | `true` |
| `kernel_sign` | `-rk35xx-ophub` |
| `kernel_config` | `kernel-config/release/rk35xx` |
| `source_hash` | `c2f148dece4b67ebd30aefad1bdd1990f41e5633` |

日志中的 source-hash step 实际执行后，后续 Cache、Compile 和 Upload steps 均继续携带相同的 `source_hash`：

`c2f148dece4b67ebd30aefad1bdd1990f41e5633`

这不是仅由当天 main 分支时间线推算出来的值，而是原始 run #296 job log 中的实际运行输出。

对应源码提交：

- Repository：`ophub/linux-6.1.y-rockchip`
- Commit：`c2f148dece4b67ebd30aefad1bdd1990f41e5633`
- Commit time：`2026-11-10T05:04:36Z`
- Message：`arm64: dts: rockchip: dshanpi a1 overlay support fspi-nor or amp`

## 5. 证据闭环与结论等级

### 已验证

1. 原始 run #296 的 job log 可读取。
2. 原始 run #296 实际 `source_hash` 为 `c2f148dece4b67ebd30aefad1bdd1990f41e5633`。
3. 实际 `kernel_source`、`kernel_version`、`kernel_auto`、`kernel_sign`、`kernel_config` 均由 job log 直接确认。
4. run #296 的 Compile step 为 6.1.y，Upload step 时间窗口与 `6.1.174.tar.gz` 自动资产创建时间对应。
5. 因而，原始 6.1.174 自动发布资产的源码身份，不再只是基于 main 分支提交时间线推断；run #296 的直接构建日志已将其锁定到上述源码 commit。

### 证据边界

- 这证明原始自动构建 run 的源码输入和构建参数；不等于对历史实机安装文件逐字节复现。
- 不证明历史设备安装的每一个文件都来自该资产，除非另有现场安装文件哈希与该资产对应。
- 不证明任何源码差异就是网络故障根因。
- 2026-11-23 的后续 run #301（run ID `45154780794`）使用 `5483dc4f5384213d1a1cdf90c937db97d58721d8`。它是另一轮后续构建，不得用它覆盖或混淆 2026-11-10 原始 run #296 的源码身份。

## 6. B2-0 子项结论

**结项：6.1.174-rk35xx 原始自动构建的源码身份与实际构建参数核验。**

原先“缺少 run #296 实际 inputs/source_hash 日志”的缺口已由直接读取原始 job log 补齐。后续分析应以 `ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633` 作为原始 6.1.174 故障自动构建的已验证源码端点，而不是继续把它标成仅高置信度候选。

本子项结项不代表 B2-0 整体完成，也不改变 B2-0 既定方向顺序。

## 7. 原始证据链接

- Run #296：<https://github.com/ophub/kernel/actions/runs/42812333074>
- Run #296 job：<https://github.com/ophub/kernel/actions/runs/42812333074/job/129816642520>
- 源码 commit：<https://github.com/ophub/linux-6.1.y-rockchip/commit/c2f148dece4b67ebd30aefad1bdd1990f41e5633>
- 原始 Release：<https://github.com/ophub/kernel/releases/tag/kernel_rk35xx>
- 原 2026-11-19 来源关联报告：`PANTHER-X2-6.1.174-RK35XX-ACTIONS-RUN-AND-SOURCE-PROVENANCE-CORRELATION-20261119.md`
