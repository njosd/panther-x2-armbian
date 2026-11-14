# 第一版构建计划

## 1. 当前目标

构建一份最小可运行系统，先验证 Panther X2 的启动、以太网 DHCP、SSH 和重启稳定性。暂不安装 Immich，不进行 NPU/RKNN 配置。

目标配置：

| 项目 | 目标 |
|---|---|
| 设备 | Panther X2 / RK3566 |
| 系统 | Ubuntu 24.04 LTS Noble |
| 内核系列 | Ophub stable 6.18.y |
| 已选二进制包 | 6.18.63（固定资产及 SHA-256 已记录） |
| 根文件系统 | EXT4 |
| 镜像类型 | Server |
| DTB | rk3566-panther-x2.dtb |
| 启动固件 | Panther X2 专用 idbloader.img + u-boot.itb |
| 首轮介质 | 独立 TF 卡 |

## 2. 已确认的源码与内核包

具体 commit、资产 URL、大小及 SHA-256 见 `config/versions.env`。

已确认：
- Ophub 设备数据库包含 Panther-X2 项目条目，指向 stable 6.18.y 和 Panther X2 DTB。
- 固定的 U-Boot 源码快照包含 Panther X2 的 `idbloader.img` 和 `u-boot.itb`。
- 固定的 Linux DTS 源码包含 GMAC1、RGMII PHY 模式、时钟、供电及复位相关节点。
- Ophub kernel 的 `kernel_stable` Release 已发布 `6.18.63.tar.gz`，GitHub Release API 提供了资产 SHA-256：`47e3f46636594cbf212474a13bac97e1310c3ee51007dee3fa20f93d8659f1ca`，资产大小 124,360,986 bytes。
- Ophub rebuild 的参数解析支持关闭自动查询，并通过 `-k` 指定精确版本；Action 将 `armbian_kernel` 映射为 `-k`，`auto_kernel` 映射为 `-a`。因此预期可用 `armbian_kernel: 6.18.63` 与 `auto_kernel: false` 固定下载版本。

重要区别：
- `9bbed252...` 是 Linux 源码参考 commit；其提交时间晚于 6.18.63 Release 资产的更新时间。当前没有证据证明该二进制包就是由这个源码 commit 构建。
- 因此本项目分别记录源码参考快照与二进制发布资产，不声称两者存在已验证的一一对应关系。
- Release API 的 digest 是远端资产元数据；构建下载后仍必须自行计算 SHA-256 并比对。

这些源码事实和发布资产存在性不能证明内核包在 Panther X2 实机上启动成功，也不能证明网络正常。

## 3. 当前构建阻塞项（未解决前不启动构建）

### 3.1 上游工作流会追踪动态代码

已审查的 Ophub 工作流包含：
- Armbian Build 从 `main` 克隆；
- Ophub Action 使用 `@main`；
- Release 上传 Action 使用 `@main`；
- 默认配置 `auto_kernel: true` 自动查询内核版本。

因此不能直接复制并运行原工作流，否则无法保证本项目构建链固定。

### 3.2 rebuild 脚本会动态下载 U-Boot 和 firmware

当前 rebuild 脚本的 `git_pull_dir` 使用分支名克隆，下载依赖时默认拉取 U-Boot 和 firmware 的 `main`。虽然本仓库记录了已核实的 commit，但仅记录 commit 并不会让原脚本自动使用它们。

下一步必须对 rebuild 逻辑做最小补丁：将 U-Boot、firmware 的下载改为固定 commit checkout，或直接从固定 commit 下载所需目录；构建日志中记录实际 HEAD。补丁应尽量小并单独保存、审查。

### 3.3 Kernel package、DTB 与驱动状态

6.18.63 发布资产已通过深度检查工作流：
- 外层归档 SHA-256 与仓库记录一致；
- 6 个内部包 SHA-256 全部匹配发布包内的校验清单；
- ARM64 Image 和完整配置文件存在；
- Panther X2 DTB 已提取并反编译，SHA-256 已记录，dtc 无警告；
- DTB 的板型标识、GMAC1/PHY、eMMC、TF/SD、USB 等关键节点已做静态抽查，与固定 Ophub DTS 高度吻合；完整结构化等价及二进制构建来源仍未证实；
- RGA、VDEC 模块已从 modules 包及配置头确认存在；尚未实机 probe 或应用验证；
- 未发现明确 RKNPU 模块或 NPU 设备节点。DTB 中虽有 vdd_npu、qos_npu 等资源描述，但不代表驱动可用；
- MPP/VENC 内核支持仍待确认。

检查运行：[43543451274](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274)，Job [132289067398](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274/job/132289067398)。artifact ID：14093500129。完整记录见 `docs/DTB-AUDIT.md`。

当前判断是“内核包与 DTB 静态审计已完成一轮，启动关键节点初步吻合”，不是“已证明镜像可在实机启动”。NPU/RKNN 不作为第一版 TF 启动、DHCP、SSH 验收的前置条件，但应在后续 BSP 来源审计中单独评估。

### 3.4 BSP/NPU 路线与独立模块候选

已确认 Panther X2 专用 Vendor 6.1 路线在板级 DTS 中启用 `rknpu`、`rknpu_mmu`、`bus_npu`，对应 Rockchip Vendor 内核树包含 `drivers/rknpu`、Kconfig/Makefile 接入和 RK356x 驱动配置。

同时发现第三方项目 [w568w/rknpu-module](https://github.com/w568w/rknpu-module)，将 Vendor RKNPU 驱动移植为 mainline 外置模块，并提供 RK3566 NPU overlay。本轮审计固定其 main 分支 commit：`a8792fe6b633f90cf2c6808267cac327537ab4cf`（DKMS `rknpu/0.9.8`，GPL-2.0）。其 README 报告 OrangePi 3B（RK3566）在 Armbian mainline 6.19.3 和 7.0.0 上运行，使用 librknnrt 2.3.2；**没有证据证明可直接用于当前 Ophub 6.18.63**。

该项目还记录 RK3566 IOMMU v2 页表地址可能超过 4GB 并造成总线错误，当前以禁用 NPU IOMMU 的 non-IOMMU 模式规避。不能未经验证照搬到 Panther X2，但首轮移植评估不应默认启用 NPU IOMMU。

Linux 6.18 的 Rocket 驱动支持范围与 RK3566 Vendor RKNPU/RKNN ABI 不同；不能把 Rocket 模块存在等同于 Immich RKNN 后端可用。Immich RKNN 后端依赖 Vendor `rknpu` ABI 的公开讨论也已记录在 `docs/DTB-AUDIT.md`。

**路线决定：** 暂时保持 Ophub 6.18.y 主线候选不变；优先审计 `w568w/rknpu-module` 的源码、许可证、API 依赖、overlay 和 RKNN Runtime 配套，随后在 GitHub Actions 中使用固定 commit `a8792fe6b633f90cf2c6808267cac327537ab4cf`，使用 Ophub 6.18.63 headers 做纯编译验证。编译验证通过仍不代表实机 probe 或 RKNN 推理成功。若 6.18 API 差异过大，再比较升至该模块已验证的 6.19.y 与保留 Vendor 6.1 备选路线。


### 3.5 GitHub Actions 依赖

Action 必须固定到完整 commit SHA，而不是 `@main` 或可移动标签。当前记录了 checkout、upload-artifact 和 Ophub upload Action 的候选 commit；正式 workflow 仍需逐一核实所用 Action 的接口、权限及兼容性。Armbian Build 也必须 checkout 到记录的 commit，而非克隆 main。

### 3.6 Ubuntu 构建依赖并非完全可复现

Armbian 构建会使用动态 APT 软件源。固定 Git commit 不能保证未来 bit-for-bit 可复现。第一阶段的目标应定义为“可追溯、可重复重建”，保存：
- 所有源码 commit；
- Actions commit；
- 构建器镜像/运行环境；
- APT 包清单和构建日志；
- 实际 kernel package 版本及校验值；
- 最终镜像 SHA-256。

## 4. 首启网络设计

Server 镜像预期使用 NetworkManager。首启配置应确保有线接口建立自动连接的 DHCP profile，SSH 服务启用。不要在 NetworkManager 管理接口的同时盲目叠加 ifupdown 配置。

必须检查最终镜像实际使用的网络管理器和接口名；不要假定设备一定叫 eth0。网络配置不应写死 Panther X2 的 IP，先由 hEX DHCP 分配地址。密码、Token、私钥不得提交到公开仓库。

## 5. 内核包检查工作流

已新增并手动运行 `.github/workflows/inspect-kernel-package.yml`：
- 仅 `workflow_dispatch` 手动触发；
- checkout 与 artifact upload Action 固定到完整 commit SHA；
- 下载 `6.18.63.tar.gz` 并与仓库记录的 SHA-256 比对；
- 执行 gzip 完整性检查，生成归档文件清单、内核配置摘要和相关模块路径清单；
- 不运行 rebuild、不写入镜像、不操作任何设备。

最近运行记录：`43543451274`，检查通过，artifact 已下载并审阅；包含原始 DTB、反编译 DTS、完整模块路径清单及配置摘要。

## 6. 构建前检查清单

- [x] Ophub stable kernel Release 中存在 6.18.63 资产，远端 SHA-256 已记录。
- [x] 手动运行 `.github/workflows/inspect-kernel-package.yml`，下载归档并核对 SHA-256（run 43526258367）。
- [x] 检查归档结构：6 个内部包校验值匹配；确认 ARM64 Image、Panther X2 DTB 文件名及相关驱动配置存在。
- [x] 提取 DTB 二进制并反编译；启动关键节点已与固定 Ophub DTS 静态抽查，完整等价与 provenance 仍待验证。详见 `docs/DTB-AUDIT.md`。
- [x] 已找到 Vendor 6.1 RKNPU 驱动源码及 Panther X2 DTS 启用证据。
- [x] 已找到 RK3566 mainline 外置 RKNPU 模块候选及其 6.19.3 实测声明。
- [x] 锁定外置模块 commit、许可证并完成第一轮源码结构审计；内核 API 兼容性仍待正确工具链复测。
- [ ] 使用 GCC 15.3.1 在 GitHub Actions 重新编译 RKNPU 模块，并审查真实 API/符号错误。
- [ ] 对 overlay 警告做基树上下文分析，并与 Panther X2 基础 DTB 合并验证。
- [ ] TF/SD 控制器与 USB host 节点按 Panther X2 实际板级映射进一步核对。
- [ ] U-Boot 与 firmware 下载已改为固定 commit。
- [ ] Armbian Build、Ophub Action、上传 Action 均固定 commit。
- [ ] 构建 workflow 仅手动触发，不配置 push 自动构建。
- [ ] workflow 不包含 eMMC 安装或设备远程操作。
- [ ] DHCP 与 SSH 首启配置已经静态审查。
- [ ] 构建输出包含 manifest、日志和 SHA-256。
- [ ] 目标 TF 卡容量与写入设备已由用户确认。

## 7. 明确不做

- 不在首版镜像中部署 Immich。
- 不启用 RKNN/NPU/VPU 加速。
- 不改 Panther X2 当前系统、内核、驱动或网络服务。
- 不执行 eMMC 安装。
- 不因首次网络失败就反复刷写；先保留日志并定位 U-Boot、DTB、GMAC/PHY、NetworkManager 各层。


### 3.7 RKNPU 6.18.63 纯编译验证工作流（第六轮已通过核心对象编译）

前五轮运行及结论见本节前序记录。
第六轮运行：[43582735410](https://github.com/njosd/panther-x2-armbian/actions/runs/43582735410)，Job [132410737160](https://github.com/njosd/panther-x2-armbian/actions/runs/43582735410/job/132410737160)，artifact ID `14108958665`。

第六轮结果：
- 主机辅助工具阶段成功重建 x86_64 `fixdep`，但通用 `scripts` 目标没有在输出树生成 `scripts/mod/modpost`；
- 禁用可选 devfreq 后，RKNPU 核心对象已完成 ARM64 编译，包括 driver/GEM/IOMMU/reset/debugger 等，并成功链接成中间对象 `rknpu.o`；
- 最终失败发生在外置模块 modpost 阶段，明确报错为输出树缺少 `scripts/mod/modpost`，不是 RKNPU C 源码 API 编译错误；
- DT overlay 仍可生成 DTBO，但存在 reg_format、默认 address/size cells 及 interrupt-parent 警告，不能认定设备树适配完成；
- 本轮没有生成最终 `rknpu.ko`，没有加载模块，也没有修改任何设备。

**本轮复核发现的工作流版本差异与修正：**
- 本次 run 实际 checkout 的仓库 commit 是 `ffb630a6114f5150183b2a344cdfbe1c5b64fb52`。该 commit 中的 workflow 只执行通用 `scripts`，并没有执行此前文档所述的显式 modpost 构建命令；因此不能把本次失败解释为显式目标已验证失败。此前记录的“第七轮针对性修正”与本次实际运行的 workflow 版本不一致，现以 job 日志中的 checkout SHA 和 artifact 为准。
- 对照 Linux 6.18 Kbuild：`scripts/Makefile` 的通用目标不会自动进入 `scripts/mod`；`scripts/mod/Makefile` 才声明 `modpost`、`mk_elfconfig` 等 host program。直接请求不带文件后缀的 `scripts/mod/modpost` 并非最稳妥的目录构建方式。
- 已将当前 workflow 调整为显式构建目录目标 `scripts/mod/`，让 Kbuild 在正确的输出树中构建该目录及其生成依赖，再对 `modpost` 做 x86_64 ELF 检查。该修正尚未运行验证。

下一轮重点：
1. 确认 `scripts/mod/` 构建成功，并生成输出树中的 `modpost`、`mk_elfconfig` 及所需生成文件；
2. 确认 `fixdep` 与 `modpost` 均为 x86_64 ELF；
3. 是否完成 `MODPOST` 并生成 `rknpu.ko`；
4. 如成功，核对 vermagic、depends、符号版本及源码/header provenance；
5. DT overlay 警告单独处理，不把 DTBO 生成成功等同于 Panther X2 设备树兼容。

仍须强调：Ophub 源码 commit 的 6.18.63 版本号并未证明它就是发布二进制内核包的精确源码。模块成功编译也不能单独证明 ABI 匹配。全部操作仍仅限 GitHub Actions 纯编译验证，不触碰 Panther X2（192.168.9.6）。


### 3.8 RKNPU 6.18.63 纯编译验证（第七轮：MODPOST 已运行，符号解析失败）

第七轮运行：[43591812356](https://github.com/njosd/panther-x2-armbian/actions/runs/43591812356)，Job [132437950866](https://github.com/njosd/panther-x2-armbian/actions/runs/43591812356/job/132437950866)，artifact ID `14112229131`。实际 checkout commit：`fb4b83cd9fa2cc61a5fd834d0d949d025e6c2f05`。

结果：
- `scripts/mod/` 目录构建成功；`fixdep` 与 `modpost` 均已重建为 x86_64 host ELF，证明上一轮缺少 modpost 的问题已解决；
- RKNPU 核心对象再次全部完成 ARM64 编译，并链接为 `rknpu.o`；
- MODPOST 已执行，但因 `pm_runtime_force_resume` 未能在当前 `Module.symvers` 中解析而失败，未生成最终 `rknpu.ko`；
- DTBO 仍能生成，但原有 reg_format、address/size cells 和 interrupt-parent 警告仍在，设备树适配未验证；
- 没有加载模块或修改 Panther X2 实机。

符号初步源码审计：
- 固定 Ophub 源码 commit `9bbed25243be8b43df410ebb9a8bbb1992234114` 的 `drivers/base/power/runtime.c` 在 `CONFIG_PM_SLEEP` 条件下定义并 `EXPORT_SYMBOL_GPL(pm_runtime_force_resume)`；
- 同一源码的 `include/linux/pm_runtime.h` 在 `CONFIG_PM_SLEEP` 开启时声明外部函数，关闭时提供 inline stub；
- 因此当前错误不能简单归结为“Linux 6.18 没有该 API”。更可能的调查方向是：headers build tree 的 `CONFIG_PM_SLEEP` 与 `Module.symvers` 是否一致、该发布内核是否实际导出了该符号，以及当前 prepared headers 与源码快照是否匹配。以上仍是待验证假设，不能提前定论。

已在 workflow 增加只读诊断报告 `pm-runtime-symbol-audit.txt`，下一轮记录：
1. `CONFIG_PM`、`CONFIG_PM_SLEEP`、`CONFIG_PM_RUNTIME` 的实际值；
2. 发布 headers 包 `Module.symvers` 是否包含 `pm_runtime_force_resume` 及相关 runtime PM 符号；
3. Ophub 源码中的条件编译、导出声明和 Makefile 选择；
4. 若配置启用但符号仍不在 Module.symvers，优先调查发布包 headers/符号表来源与源码快照 provenance，不通过 `KBUILD_MODPOST_WARN`、`KBUILD_MODPOST_NOFINAL` 或伪造符号表绕过错误。

本轮仅增加 CI 诊断，不修改驱动源码、不改内核配置、不在 9.6 实机操作。


### 3.9 RKNPU 6.18.63 纯编译验证（第八轮：定位到 headers 符号表缺项）

第八轮运行：[43592220424](https://github.com/njosd/panther-x2-armbian/actions/runs/43592220424)，Job [132439173554](https://github.com/njosd/panther-x2-armbian/actions/runs/43592220424/job/132439173554)，artifact ID `14112663495`。实际 checkout 的仓库 commit：`68409d30acaf2022bd9dfc9e3c926712153ad886`。

本轮新增审计给出了明确结果：
- headers build tree 的 `.config` 与 `include/config/auto.conf` 均为 `CONFIG_PM=y`、`CONFIG_PM_SLEEP=y`；
- 同一 headers 包的 `Module.symvers` 有 `pm_runtime_force_suspend`，但没有 `pm_runtime_force_resume`；
- 固定 Ophub 源码 commit `9bbed25243be8b43df410ebb9a8bbb1992234114` 的 `drivers/base/power/runtime.c` 第 2052 行起，在 `CONFIG_PM_SLEEP` 下实现 `pm_runtime_force_resume()`，并于第 2110 行执行 `EXPORT_SYMBOL_GPL(pm_runtime_force_resume)`；该文件也包含 `pm_runtime_force_suspend` 导出；
- 因而，按这份源码和这份配置构建时，两个导出符号理应同时出现在 Module.symvers。现在只存在 suspend、不存在 resume，是 headers 符号表与源码/配置组合不自洽的直接证据。

当前最有根据的判断：**RKNPU 的 MODPOST 错误来自目标 headers 包的 Module.symvers 缺项，或 headers 包与固定源码快照并非同一构建产物**。尚不能断言实际运行中的内核缺少该符号；也不能仅凭当前信息区分符号表不完整、构建源码差异或发布包制作错误。之前仅 grep 注释附近的源码审计范围太窄，容易漏掉实际函数定义；已修正 workflow，下一次完整打印函数实现及导出行。

本轮其他结果不变：
- host tools 与 RKNPU 核心对象编译成功，MODPOST 仍因 `pm_runtime_force_resume` 缺项失败，未生成 `rknpu.ko`；
- DTBO 编译成功但有 reg_format、address/size cells、interrupt-parent 警告；
- 纯 CI 编译验证，未在 Panther X2 加载或安装模块。

下一步不应通过伪造 Module.symvers 条目或忽略 unresolved symbol 让模块“通过”。应先验证 headers 包本身的符号表完整性及其构建来源；如果能取得与目标内核完全匹配的完整源码/构建输出，再用其真实 Module.symvers 重新构建外置模块。即使如此，仍需后续检查 vermagic、modversions、模块依赖、设备树资源和实机驱动加载。


### 3.11 第九轮后续：追查 prepared kernel build artifacts（待运行）

第九轮已证实配置与源码声明/导出一致，但 headers 的 `Module.symvers` 缺少 `pm_runtime_force_resume`。为避免仅凭符号表作出过早结论，下一轮只读检查 prepared build tree 中的 `drivers/base/power/runtime.o`、`.runtime.o.cmd`、`System.map`、`vmlinux`、`modules.builtin` 和 `modules.order`，并尝试提取 suspend/resume 符号。

判断方法：
- runtime.o 或 vmlinux 中存在 resume、而 Module.symvers 缺少：重点调查 Module.symvers 生成或发布打包；
- runtime.o 中没有 resume：检查对象构建时实际使用的配置、源码及命令记录，确认是否复用了旧对象；
- 对象和完整映像不存在：headers 包不足以证明实际内核导出情况，应寻找对应的完整构建产物或可信二进制符号信息。

本步骤只读取已有 CI 下载的 build tree，不重建内核、不生成伪造符号、不绕过 MODPOST。


### 3.12 RKNPU 6.18.63 纯编译验证（第十轮：headers 包不含可核对的完整内核构建对象）

第十轮运行：[43593110032](https://github.com/njosd/panther-x2-armbian/actions/runs/43593110032)，Job [132441838951](https://github.com/njosd/panther-x2-armbian/actions/runs/43593110032/job/132441838951)，artifact ID `14113256837`。

结果：
- host tools 和 RKNPU 核心对象编译继续成功；MODPOST 仍因 `pm_runtime_force_resume` 不在 headers 的 `Module.symvers` 而失败，未生成 `rknpu.ko`；
- 配置仍为 `CONFIG_PM=y`、`CONFIG_PM_SLEEP=y`，源码中有函数定义和 GPL 导出；
- 关键的新发现：headers/build output 中不仅没有 `Module.symvers` 所需的 resume 记录，也没有以下可用于核验真实内核构建结果的对象/文件：`drivers/base/power/runtime.o`、`.runtime.o.cmd`、`vmlinux`、`System.map`、`modules.builtin`、`modules.order`。本轮逐项检查均显示 MISSING；
- 因此不能从该 headers 包判断实际发布内核是否包含该实现，也不能证明 `Module.symvers` 是单独生成时漏项，还是 headers 本来就只保留了外置模块编译所需的裁剪文件；
- DTBO 仍可生成，但 reg_format、address/size cells 和 interrupt-parent 警告未解决。

**结论更新：** 当前已知的直接阻塞是 Ophub 6.18.63 headers 包提供的 `Module.symvers` 缺少 RKNPU 所需符号；但“发布内核符号表损坏”尚未证实。更准确的描述是：当前 headers 包是裁剪后的 prepared build tree，不包含足以独立审计内核本体符号实现的对象/映像。先前将其表述为“符号表异常/不完整”应保留为现象描述，不应推断为发布内核错误。

下一步建议从构建来源入手，而不是继续在缺失产物的 headers 包上重复 grep：
1. 找出 Ophub 发布该内核与 headers 包的 workflow、构建脚本及 artifact/package 生成逻辑；
2. 确认 `Module.symvers` 是在完整内核构建后生成，再被 headers 包原样携带，还是在打包/裁剪阶段重新生成或修改；
3. 尝试取得同一发布版本的完整内核构建产物或可复现的完整 build config/source commit；
4. 只有取得可信匹配的 `Module.symvers` 后，才重新做 RKNPU MODPOST。禁止手工补写导出项或关闭 unresolved-symbol 检查。

本轮没有修改 RKNPU 驱动、内核配置或 Panther X2 实机。


### 3.13 Ophub 内核构建与 headers 打包链审计（源码级，已完成第一轮）

本轮按“追查 Ophub 构建链，而不是继续修 RKNPU 模块”方向审计了 Ophub 上游公开脚本和 workflow。证据来源及边界如下。

#### A. headers 包如何生成

审计来源：
- `ophub/amlogic-s9xxx-armbian` 的 `compile-kernel/tools/script/armbian_compile_kernel.sh`（上游仓库当时可见版本；函数 `get_kernel_source()`、`collect_headers()`、`compile_kernel()`、`packit_kernel()`、`create_debs_headers()`）。
- `ophub/kernel` 的 Rockchip RK35xx workflow：`.github/workflows/compile-rockchip-rk35xx-kernel.yml`。

脚本流程已经核实：
1. `get_kernel_source()` 以浅克隆方式获取指定 kernel source repository 的分支（`--single-branch --depth=1 --branch=...`），不是固定 commit SHA 克隆。
2. `compile_kernel()` 运行 `make Image modules dtbs`，然后运行 `modules_install`。
3. 内核编译后调用 `collect_headers()`。该函数从当前内核源码/构建树收集外置模块构建需要的文件，并把 `Module.symvers`、`.config`、`include/config`、`include/generated`、架构生成头文件及部分 scripts/对象文件复制到 header staging 目录。
4. `packit_kernel()` 将 header staging 目录原样打包为 `header-<kernel>.tar.gz`。
5. Debian headers 包生成函数将同一 header staging 目录复制到 `/usr/src/linux-headers-<kernel>`，不重新生成 `Module.symvers`。

由此得到一个重要修正：
- headers 包中没有 `vmlinux`、`System.map`、`drivers/base/power/runtime.o` 等完整内核对象，符合其“外置模块开发 headers”裁剪打包设计，**不能据此认定包损坏或构建失败**。
- `Module.symvers` 是从编译树直接复制进 headers staging 的；在已审计脚本中没有单独过滤或删除 `pm_runtime_force_resume` 的步骤。因此该符号缺失应在下一步追查其进入 `collect_headers()` 之前的构建输出、实际源码 commit、实际配置和模块符号生成阶段。现阶段仍不能区分：源树实际构建产生的 Module.symvers 本来就没有该符号，还是测试下载的 headers 与我们用于源码审计的 commit 不一致。

#### B. 当前测试的 6.18.63 与 RK35xx 专用内核路线不是同一条发布线

审计 `ophub/kernel/README.cn.md` 与 `.github/workflows/compile-rockchip-rk35xx-kernel.yml` 后确认：
- Ophub 将通用主线系列（包含 `ophub/linux-6.18.y`）与 RK35xx 专用 BSP 系列分开说明。
- README 将 `kernel_rk35xx` 定义为 RK3528/RK3566/RK3568 专用内核；列出的 Rockchip 专用源码包括 `ophub/linux-6.12.y-rockchip`、`ophub/linux-6.1.y-rockchip`、`ophub/linux-5.10.y-rk35xx` 等。
- 当前 RK35xx 专用 workflow 的 kernel source 选项仅包含 5.10.y、6.1.y、6.12.y，没有 6.18.y；其默认 config 路径为 `kernel-config/release/rk35xx`，本轮可读取到的 6.12 配置明确启用 `CONFIG_PM=y`、`CONFIG_PM_SLEEP=y`、`CONFIG_MODULES=y`。
- 因此此前用 `ophub/linux-6.18.y` 6.18.63 headers 做的 RKNPU 测试，不能代表 Ophub 的 RK35xx 专用 BSP 内核线已验证通过或失败。它是通用 6.18 主线系列上的模块兼容性试验。该 6.18.63 包是否确实属于通用 stable release、以及其二进制/headers 对应的精确源码 commit，仍需与此前 package manifest、release asset 和 SHA-256 记录关联后确认。

#### C. 当前构建 provenance 的薄弱点

RK35xx workflow 会在编译前读取 kernel source 的 `main` 分支 SHA，并用于 ccache key；但它将 repository 名称、版本和 `kernel_auto` 参数传给 Ophub composite Action。底层脚本仍按分支浅克隆源码，并在 auto 模式下查询分支最新版本。workflow 捕获的 SHA 没有作为不可变 commit 参数传入实际 clone/checkout。

这意味着：
- workflow 中记录的预取 source hash 不自动等于最终编译时 checkout 的 commit；
- 如果分支在 hash 查询与 clone 之间前进，或者 auto 逻辑重新同步分支，可能出现 provenance 不一致；
- 对我们自己的可复现构建，必须在 clone 后立即记录 `git rev-parse HEAD`、remote URL、branch/tag、Makefile kernel version、配置文件 SHA，并将该 commit 固定到后续构建步骤；不能只记录编译前读取的 branch head。

#### D. 当前结论与下一步

已验证：
- Ophub headers staging 从构建树复制 `Module.symvers`，打包脚本没有发现对单个导出符号的过滤；
- 缺少 `runtime.o`、`vmlinux`、`System.map` 属于 headers 包的预期裁剪；
- 6.18.63 通用系列与 RK35xx 专用 BSP 系列是不同发布路线；RK35xx 专用 workflow 当前列出的最高系列是 6.12.y。

未验证：
- 第十轮所下载的 6.18.63 headers 对应的准确 Ophub release tag、源码 commit、配置文件及其生成时的完整 `Module.symvers`；
- `pm_runtime_force_resume` 缺失是在上游构建时产生，还是当前测试包/测试树不匹配；
- 6.12.y RK35xx 专用内核对 Panther X2 的 NPU 节点、驱动和 Immich/RKNN 实际可用性。

下一步不继续在 6.18.63 headers 上重复编译。先做一个只读 provenance 对照：
1. 回看已审计的 6.18.63 release 包 manifest/内部文件名和 SHA-256，定位精确 release tag 与资产；
2. 检查同一 release 的 header tar 中 `Module.symvers` 与其包元数据，不以另一条源码分支代替；
3. 同时检查 `kernel_rk35xx` release 当前可用的 6.12.y Rockchip 内核资产及其对应 source/config；
4. 决定后续主验证基线应是“通用 6.18 主线”还是“RK35xx 专用 6.12 BSP”，再对该确切版本进行 RKNPU/DTB 审计。

不做内核安装、不改 9.6、不补写符号表、不忽略 MODPOST 错误。
