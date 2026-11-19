# Panther X2：6.1.174-rk35xx Actions 构建运行与源码提交关联核验（2026-11-19）

## 1. 目的与结论

本报告补充 2026-11-19 前述源码来源审计缺失的关键证据：将 Ophub kernel_rk35xx release 中自动上传的 6.1.174.tar.gz 与实际 GitHub Actions run 关联，并检查该 run 执行时 RK35xx 源码仓库的 main 分支提交。

**结论：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633 是实机 6.1.174-rk35xx-ophub 对应官方自动构建资产的高置信度源码提交候选。** 之前把 unifreq/linux-6.1.y@3f06ed3 作为实际镜像主要源码候选的更正报告，不能再作为当前主结论。

仍保留严格限制：GitHub Actions REST API 不公开 workflow_dispatch 的实际 inputs，也未能取得该 run 的 step 5 日志中 source_hash 输出。因此尚不能把 c2f148d 提升为逐字节构建证明。默认参数、run/asset 时间、source repo commit 时间线高度吻合，足以将其作为 P3 主线源码候选继续分析。

全程只读公开 GitHub workflow、Actions run/job 元数据、release asset 元数据和源码提交历史；没有访问 Panther、执行实机操作、MDIO/MMIO 读写、发包、抓包或修改配置。

## 2. 自动发布资产与 Actions run 精确时间对应

Ophub release kernel_rk35xx 的自动资产：

- 6.1.174.tar.gz
- asset ID：731478275
- uploader：github-actions[bot]
- created_at：2026-11-10T13:09:30Z
- updated_at：2026-11-10T13:09:34Z
- size：135,267,299 bytes
- SHA-256：49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a

同一 release 中还有 deb-6.1.174.tar.gz，不能与 flippy 手动资产混淆。

GitHub Actions run 列表中找到唯一精确匹配的 Rockchip RK35xx 6.1.y 构建：

- workflow：Compile rockchip rk35xx kernel
- workflow path：.github/workflows/compile-rockchip-rk35xx-kernel.yml
- run number：296
- run ID：42812333074
- workflow run head SHA：f8925391bb2ba2634bb8ca55da39e1a2f4029ffe
- event：workflow_dispatch
- actor / triggering actor：ophub
- run started：2026-11-10T12:02:09Z
- job ID：129816642520
- job completed：2026-11-10T13:09:58Z
- step 7 Compile the kernel [ 6.1.y ]：12:04:15Z–13:09:27Z
- step 8 Upload Kernel to Release：13:09:27Z–13:09:40Z

因此 6.1.174.tar.gz 创建时间 13:09:30Z 落在 run #296 的 upload step 内；run #296 的编译 step 明确为 6.1.y。这是该 asset 由 run #296 自动上传的强关联证据。

交叉校验：紧邻的 run #297 于 12:02:20Z 开始、12:16:13Z 完成；其 compile step 也为 6.1.y workflow 的同类运行，但时间与 6.12.69.tar.gz asset（12:15:43Z 创建）对应。run #297 不是 6.1.174 asset 的上传运行。

## 3. 构建 workflow 在该 run 的版本与默认输入

读取 run head SHA f8925391bb2ba2634bb8ca55da39e1a2f4029ffe 对应的 workflow 文件，而不是只看当前 main：

.github/workflows/compile-rockchip-rk35xx-kernel.yml

该精确版本默认参数：

- kernel_source = ophub/linux-6.1.y-rockchip
- kernel_version = 6.1.y
- kernel_auto = true
- kernel_sign = -rk35xx-ophub
- kernel_config = kernel-config/release/rk35xx

其 step 5 Get kernel source commit hash 会在构建开始时调用：
https://api.github.com/repos/\${kernel_source}/git/ref/heads/main
读取源仓库 main 分支 HEAD SHA，并把它写入 source_hash 环境变量。

这些默认输入与实机内核签名 6.1.174-rk35xx-ophub、release tag kernel_rk35xx、资产名 6.1.174.tar.gz 一致。

**限制：** Actions REST API 的 run/job 元数据不包含 workflow_dispatch 实际 inputs。虽然 run 由 workflow owner ophub 手动触发且所有默认值吻合，但仍不能排除其手动覆盖 kernel_source、kernel_auto 或 config 输入。不能把默认值直接写成该 run 已验证的实际 inputs。

## 4. step 5 执行时源仓库 main 分支的提交时间线

run #296 的 step 5 在 2026-11-10T12:04:15Z 执行。

对 ophub/linux-6.1.y-rockchip 查询 2026-11-10 00:00Z 至 12:02:20Z 的 main 分支提交历史，只有一条提交：

- commit：c2f148dece4b67ebd30aefad1bdd1990f41e5633
- committer time：2026-11-10T05:04:36Z
- message：arm64: dts: rockchip: dshanpi a1 overlay support fspi-nor or amp

该提交是 run 开始前当天唯一新提交；在 run step 5 的时间点，它是 ophub/linux-6.1.y-rockchip main 分支的可见最新提交。

因此，在 workflow 使用默认 kernel_source 的条件下，step 5 的 source_hash 应解析为 c2f148d。

## 5. 与旧报告冲突的处理

### 5.1 旧普通 stable 候选

unifreq/linux-6.1.y@3f06ed3 是普通 stable Linux 6.1.174 源码端点，不应仅凭版本号 6.1.174 代替专用 kernel_rk35xx 构建 workflow 的输入源码。

### 5.2 旧 closeout 的证据边界更新

PANTHER-X2-P3-GPLL-ACLK-USB-BRANCH-CLOSEOUT-AND-SOURCE-CORRECTION-20261119.md 曾因缺少 Actions run 对应关系而把 c2f148d 视为未证明属于 6.1.174 的后期 BSP 快照，并停止追踪。

本报告补上了 asset↔run 精确时间关联、workflow 版本/默认参数、source-hash step 时间以及源仓库 main 提交时间线。因此旧 closeout 的“不能解释 6.1.174 最早回归”判断应降为暂定，不能继续作为排除 c2f148d 的依据。

### 5.3 新证据等级

| 事项 | 当前等级 |
|---|---|
| 6.1.174.tar.gz 对应 run #296 自动上传 | 高置信度，时间窗口精确对应 |
| run #296 编译目标为 6.1.y | 已验证 |
| workflow 默认 source 是 ophub/linux-6.1.y-rockchip | 已验证 |
| step 5 在 12:04:15Z 读取 source main HEAD | 已验证 |
| c2f148d 是该时刻该仓库 main 唯一最新提交 | 高置信度，提交历史时间窗只有此提交 |
| run #296 实际 inputs 未覆盖默认 source | 未验证 |
| run #296 step 5 实际输出 source_hash=c2f148d | 未验证，日志输出不可读取 |
| c2f148d 是 6.1.174 镜像精确构建源码 | 高置信度候选，尚非逐字节证明 |

## 6. 对 P3 的直接影响

应恢复以以下三端为主的实际 kernel family 比较：

- 正常：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 最早异常 6.1.174-rk35xx：ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633（高置信度候选）
- 持续异常 6.12.81-rk35xx：ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

这使 6.1.174 与 6.12.81 共有的 RK35xx GMAC clock enable / settle 实现重新成为解释最早回归的有效候选背景；此前把它降级为“只属于后期 BSP”的判断不再成立。

仍不得把代码差异写成根因。P3 应继续验证：
1. c2f148d 中 Panther 实际 RGMII 分支所需 clock handle 获取和使能顺序；
2. clk_prepare_enable() 各父级 callback 的实际返回条件，区分 handle 获取错误、prepare/enable 错误和物理时钟波形；
3. usleep_range(100,200) 在 PLL lock 已由 provider 等待之后，还承担哪些 MAC/PHY/GRF 稳定职责；
4. PLL mode callback 是否在 CRU provider 初始化时由 critical clocks 触发，还是会在 GMAC probe 时再次触发；
5. 哪些现象有已有启动日志支持，哪些只能标记未验证。

不得操作 Panther、读取 MMIO/MDIO、发包、抓包、重启接口或制作补丁。

## 7. 参考链接

- workflow at run head SHA: https://github.com/ophub/kernel/blob/f8925391bb2ba2634bb8ca55da39e1a2f4029ffe/.github/workflows/compile-rockchip-rk35xx-kernel.yml
- run #296: https://github.com/ophub/kernel/actions/runs/42812333074
- run #296 job: https://github.com/ophub/kernel/actions/runs/42812333074/job/129816642520
- kernel_rk35xx release: https://github.com/ophub/kernel/releases/tag/kernel_rk35xx
- c2f148d: https://github.com/ophub/linux-6.1.y-rockchip/commit/c2f148dece4b67ebd30aefad1bdd1990f41e5633
- 6.1.116 baseline: https://github.com/unifreq/linux-6.1.y/tree/5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12.81 baseline: https://github.com/ophub/linux-6.12.y-rockchip/tree/661b2d8bf1284556f8876d5ed5fb80c64b22f94c
