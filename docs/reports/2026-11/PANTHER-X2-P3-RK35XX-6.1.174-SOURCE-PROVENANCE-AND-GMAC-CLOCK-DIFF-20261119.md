# Panther X2：6.1.174-rk35xx 实际 BSP 源码来源闭环与 GMAC 时钟路径重新定级（2026-11-19）

## 1. 本轮目的与关键纠正

此前 P3 第一步比较的是：

- 正常 6.1.116：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 普通 stable 6.1.174：unifreq/linux-6.1.y@3f06ed3e4b0f82e59c7b68d5dc36d698a377e2c7

但实机异常版本标识是 6.1.174-rk35xx-ophub，不是普通 6.1.174-ophub。因此普通 stable 6.1.174 不能代表实际故障镜像的源码族。此次重新核对 Ophub 的 RK35xx 专用 workflow、release asset、专用源码仓库及 Git 历史。

**关键结论：6.1.174-rk35xx 应按 Rockchip vendor BSP 源码族分析。此前普通 stable 6.1.174 的函数比较只对普通 stable 源码成立，不能用来声称实际 RK35xx 镜像与 6.1.116 的 GMAC glue 一致。**

本轮只读 GitHub 公开源码、工作流和 release 元数据；没有访问 Panther、执行网络测试、MDIO 读写、PHY reset、接口重启或修改配置。

## 2. 正常与故障内核确属不同 kernel family

### 2.1 正常 6.1.116

既有运行记录确认：
- uname -a：6.1.116-ophub
- build timestamp：2024-11-10
- Ophub general kernel 工作流 / kernel_stable 系列
- 源码候选：unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e
- 配置族：kernel-config/release/general/config-6.1

### 2.2 异常 6.1.174-rk35xx

Ophub 官方 RK35xx 工作流 .github/workflows/compile-rockchip-rk35xx-kernel.yml 的默认参数为：
- kernel_source=ophub/linux-6.1.y-rockchip
- kernel_version=6.1.y
- kernel_auto=true
- kernel_sign=-rk35xx-ophub
- kernel_config=kernel-config/release/rk35xx

这与实机异常内核后缀 -rk35xx-ophub、以及 Ophub 官方 release 中 kernel_rk35xx 专用资产相符。

### 2.3 6.1.174 release asset 与源提交时间

Ophub kernel_rk35xx release API 当前可见：
- 自动上传资产：6.1.174.tar.gz
- asset ID：731478275
- 创建时间：2026-11-10 13:09:30Z
- 大小：135,267,299 bytes
- GitHub uploader：github-actions[bot]
- SHA-256：49e2e81132b249b2b1e55fa18fa1fa002ddf9c91dc433cd672f914ab17af668a

同一日期，ophub/linux-6.1.y-rockchip 有提交：
- c2f148dece4b67ebd30aefad1bdd1990f41e5633
- committer time：2026-11-10 05:04:36Z
- message：arm64: dts: rockchip: dshanpi a1 overlay support fspi-nor or amp

该提交早于 6.1.174.tar.gz 资产约 8 小时。且 c2f148 中的 dwmac-rk.c blob SHA 与 unifreq/linux-6.1.y-rockchip@76839744 的 dwmac-rk.c 完全相同。

**证据等级：高置信度源码候选，不是构建输入的最终证明。** 当前公开 workflow 默认值、release asset 时间和源码提交时间高度吻合，但尚未取得这一个 6.1.174 release 对应的 Actions run 输入/日志，不能声称已逐字节证明该资产一定由 c2f148 构建。workflow 可手动覆盖输入，必须保留这一限制。

注意：同一 release 还存在 6.1.174-rk35xx-flippy-2609c.tar.gz，它是另一个由 ophub 用户上传的 flippy 包，不能与自动上传的 6.1.174.tar.gz 混为同一个资产。本轮讨论的 -rk35xx-ophub 对应官方工作流默认签名，不是 -flippy 资产。

## 3. RK35xx 专用源码的历史来源

在 unifreq/linux-6.1.y-rockchip 中核对到：

1. 初始导入 commit：e1ae5c80f59ecd3f7cdd285c35110d21d42923d8，2025-04-11。
   - commit message 明确记录来源：armbian/linux-rockchip
   - branch：rk-6.1-rkr5
   - source commit：28320e8543bb19e21d3cfbf0421c700f17da5b58
2. 2025-11-13 更新到 BSP 6.1.118：0d51987ee76429e6b159738317370158e63ba759，标注 rk-6.1-rkr6.1。
3. 2026-08-26 更新到 BSP 6.1.157：8f279d4a36e384a1b862a7b71608e0738f7d19f7。
4. 2026-09-17 更新版本号到 Linux 6.1.174：76839744a5d5339d5024756d4ca1fc435509aeb0。

6.1.174 版本号提交的 parent 是 7e724f0f3ee31feb811631c8646bc6e746795de9；该版本号提交本身只修改 Makefile 的 SUBLEVEL 173 -> 174，不修改 GMAC 驱动。

## 4. 最重要的发现：100–200µs GMAC 时钟路径属于 RK35xx BSP 源码族

对比健康 general 6.1.116 与 RK35xx BSP 6.1.174 候选：

### 4.1 6.1.116 general kernel

dwmac-rk.c:gmac_clk_enable()：
- 使用 clk_bulk_prepare_enable()；
- 检查 bulk enable 返回值；
- 单独 clk_prepare_enable(clk_phy) 并检查返回值；
- clock selection callback（若存在）之后等待 mdelay(5)；
- 成功后设置 clk_enabled=true。

rk_gmac_clk_init() 使用 devm_clk_bulk_get_optional() 获取时钟集合，并检查错误；stmmaceth clock 获取失败会返回错误。

### 4.2 RK35xx BSP 6.1.174 候选

dwmac-rk.c:gmac_clk_enable()：
- 对 aclk_mac、pclk_mac、mac_clk_tx、clk_mac_speed 等逐项调用 clk_prepare_enable()；
- 对这些 enable 调用不检查返回值；
- 对 clock handle 使用 IS_ERR() 判断；
- 调用 rockchip_csu_disable()（Panther 没有 CSU phandle 的 NULL/no-op 情况已在旧报告审计，不重复）；
- 等待 usleep_range(100, 200)；
- 随后直接设置 clk_enabled=true。

RK35xx BSP rk_gmac_clk_init()：
- 逐项 devm_clk_get()；
- 获取失败主要记录 dev_err()，不统一返回错误；
- 对 Panther RGMII 会获取 mac_clk_tx、aclk_mac、pclk_mac、stmmaceth、clk_mac_speed；
- pclk_xpcs / clk_xpcs_eee 仅在 SGMII/QSGMII 分支获取；
- clk_phy 从 PHY node 获取，对外接 PHY 是 optional。

这是实际不同的 Rockchip GMAC glue 初始化策略，不是普通 stable 6.1.174 版本号提交引入的变化。

### 4.3 该实现不是 6.1.174 新增的补丁

逐个读取 RK35xx 源码端点：
- 初始 Armbian vendor import：e1ae5c80...
- BSP 6.1.118：0d51987...
- BSP 6.1.157：8f279d4...
- BSP 6.1.174：76839744...

上述四个端点的 gmac_clk_enable() 函数体完全相同，长度均为 2479 bytes。初始导入的 dwmac-rk.c Git blob SHA 为 a0d227a6fec2cc49f5d31bcc3d37d478efde0f59；6.1.157/6.1.174 的文件 blob 为 57c352f253fdb358b2118959c6ed2eabe1cdf1e5，但该时钟函数体没有变化。

进一步直接读取 Armbian 源 commit 28320e8543bb19e21d3cfbf0421c700f17da5b58，其中 gmac_clk_enable() 已经包含逐项 enable 和 usleep_range(100, 200)，与 RK35xx 初始导入一致。

因此：
- 100–200µs / 忽略 enable 返回值不是 2026-09 的 6.1.174 版本 bump 引入；
- 也不是 2026-11-10 c2f148 DTS commit 引入；
- 它是该 Rockchip vendor BSP 源码族自 2025-04 初始导入起就存在的实现。

## 5. 6.1.174 RK35xx 与 6.12.81 RK35xx 的共同点

精确比较：
- ophub/linux-6.1.y-rockchip@c2f148dece4b67ebd30aefad1bdd1990f41e5633
- ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c

以下函数体完全相同：
- gmac_clk_enable()
- rk_gmac_clk_init()
- rk_gmac_powerup()
- rk_gmac_phy_power_on()

rk_gmac_probe() 有差异：6.12 使用 devm_stmmac_probe_config_dt()、flags 和新的资源清理方式；但上面四个时钟/上电函数仍相同。

这说明 6.1.174-rk35xx 与 6.12.81-rk35xx 共享同一套关键 Rockchip GMAC 时钟/上电策略。它们与正常 general 6.1.116 的差异，可能是两个异常版本共同的候选背景。

## 6. 因果判断与当前证据等级

### 已验证

1. 6.1.116 正常版本属于 Ophub general kernel 源码/配置族；6.1.174-rk35xx 异常版本属于 Rockchip RK35xx 专用 BSP 源码/配置族。
2. Ophub RK35xx workflow 默认 source、kernel sign 和 config 路径与异常内核后缀吻合。
3. 6.1.174.tar.gz 自动发布资产创建于 2026-11-10；同日 ophub/linux-6.1.y-rockchip@c2f148 已提交。
4. RK35xx 6.1.174 候选源码的 GMAC 时钟初始化与 general 6.1.116 明显不同。
5. 该 100–200µs 时钟路径自 RK35xx 源码初始导入（2025-04）已经存在，并非 6.1.174 bump 新增。
6. 6.1.174-rk35xx 与 6.12.81-rk35xx 的关键 GMAC clock/powerup 函数体相同。

### 高置信度但未完全证明

- 自动 6.1.174.tar.gz 资产很可能由 ophub/linux-6.1.y-rockchip 的当时 main 分支构建；c2f148 是时间匹配且文件内容匹配的强候选。
- 因缺少对应 Actions run 的完整 inputs/source_hash/build log，不能把 c2f148 宣称为已证明的确切构建 commit。

### 尚未证明 / 不得写成根因

- 100–200µs 等待是否对 Panther 的实际 clock/PHY 状态过短；
- 逐项 clk_prepare_enable() 是否有任何一次在 Panther 实际构建中失败；
- enable 失败后 clk_enabled=true 是否造成部分时钟未开而 driver 仍继续；
- 该时钟路径是否足以导致 TX frame 未从 RGMII/PHY 物理发出。

### 研究意义

此前把 6.1.116→6.1.174 当成同一 kernel family 的版本升级，比较对象有误。现有测试边界更准确地表述为：

**正常 general 6.1.116 → 首个已知异常 RK35xx BSP 6.1.174 → 持续异常 RK35xx BSP 6.12.81。**

因此 100–200µs / enable error handling 应恢复为一个有明确源码依据的候选方向，但只能标记为“BSP family 差异，待因果验证”，不能直接判定根因。不得据此制作补丁。

## 7. 下一步（仍在 P3，不切换主题）

1. 以 general 6.1.116 和 RK35xx 6.1.174 候选为两端，继续只读审查 dwmac-rk.c 的 clock handle 获取、enable 顺序、RGMII 配置、PHY supply 和 runtime PM；已经完成的 RGMII 最终 delay 数值、CSU NULL/no-op、PHY reset GPIO 不重复。
2. 将每个差异映射到 Panther 实际 DTS clock names / parent chain / clock_in_out=input，只保留会命中 Panther 的分支。
3. 再对比 6.12.81，确认哪些 BSP glue 差异持续存在、哪些是 6.12 新增。
4. 只有找到可验证的失败条件或明确时序矛盾，才提出最小只读验证；本轮不要求实机测试、不修改系统、不写 PHY、不制作补丁。

## 8. 参考链接

- Ophub RK35xx workflow: https://github.com/ophub/kernel/blob/main/.github/workflows/compile-rockchip-rk35xx-kernel.yml
- Ophub kernel_rk35xx release: https://github.com/ophub/kernel/releases/tag/kernel_rk35xx
- RK35xx 6.1.174 version commit: https://github.com/unifreq/linux-6.1.y-rockchip/commit/76839744a5d5339d5024756d4ca1fc435509aeb0
- RK35xx 6.1.157 source update: https://github.com/unifreq/linux-6.1.y-rockchip/commit/8f279d4a36e384a1b862a7b71608e0738f7d19f7
- RK35xx initial vendor import: https://github.com/unifreq/linux-6.1.y-rockchip/commit/e1ae5c80f59ecd3f7cdd285c35110d21d42923d8
- Armbian vendor source commit: https://github.com/armbian/linux-rockchip/commit/28320e8543bb19e21d3cfbf0421c700f17da5b58
- Ophub 6.1.174 source candidate: https://github.com/ophub/linux-6.1.y-rockchip/tree/c2f148dece4b67ebd30aefad1bdd1990f41e5633
- Healthy general 6.1.116 source: https://github.com/unifreq/linux-6.1.y/tree/5eb841b59d6ead6e264163785a634e78f0253c8e
- 6.12.81 RK35xx source: https://github.com/ophub/linux-6.12.y-rockchip/tree/661b2d8bf1284556f8876d5ed5fb80c64b22f94c
