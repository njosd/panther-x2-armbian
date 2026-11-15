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


### 3.14 RK35xx 专用 6.12.81 基线锁定（待 CI 审计）

基于前述分流结论，新增独立的 RK35xx 专用包审计，不再把通用 `kernel_stable/6.18.63` 当作 RK3566 BSP 的唯一代表。

#### 已从 Ophub 当前公开发布元数据确认

- Release：`kernel_rk35xx`，说明明确称其为 RK3528/RK3566/RK3568 专用 BSP 内核。
- 最新候选资产：`6.12.81.tar.gz`，更新于 `2026-11-13T11:14:40Z`，大小 `141437450` bytes。
- SHA-256：`72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`。
- 对应 Ophub RK35xx workflow 当前允许的源码仓库为 `ophub/linux-6.12.y-rockchip`，配置路径为 `kernel-config/release/rk35xx/config-6.12`。
- 当前源码分支 `main` 的观测 commit：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`；其 Makefile 版本为 6.12.81。
- 当前配置文件 blob SHA：`dee127c6c644f38426eeb28000d73536084d34a3`；配置中已确认 `CONFIG_PM=y`、`CONFIG_PM_SLEEP=y`、`CONFIG_MODULES=y`、`CONFIG_ARM64=y`。
- RK35xx 专用 workflow 定义的构建输入包括 kernel source、kernel version、kernel_auto、toolchain、config path 等；工作流在调用 composite action 前读取 source branch SHA，但底层构建脚本仍通过分支浅克隆源码，预取 SHA 主要用于 ccache key，不能单独作为实际构建 commit 的证明。

#### 重要限制

上述 package、source 和 config 是当前候选参考值，**尚未证明 6.12.81 发布资产就是由 commit `661b2d8...` 与 config blob `dee127c...` 构建**。因此在变量文件中明确标记为 reference/audit candidate，不作为已确认 provenance。

#### 新增只读 CI 审计

新增 workflow：`.github/workflows/audit-rk35xx-kernel.yml`，手动触发，不部署、不写入任何设备。该工作流将：
1. 下载固定的 RK35xx `6.12.81.tar.gz` 并验证 SHA-256；
2. 列出发布包内部文件，解出 headers、boot、modules 子包；
3. 审计 `.config`、`Module.symvers`、`kernel.release`，重点核对 PM runtime 符号；
4. 搜索是否含 Panther X2/RK3566 DTB、RKNPU/NPU 模块；
5. 固定检出参考源码 commit，并验证版本号；
6. 下载固定 config reference，核对 blob SHA，输出关键配置；
7. 上传报告 artifact，不尝试加载模块或安装内核。

下一步：手动运行该 workflow，根据实际资产内容判断 6.12.81 是否包含适合 Panther X2 的 BSP/DTB/NPU 基础，再决定是否构建 RKNPU 外置模块。即使包中有 RK3566 相关内容，也必须单独核对 Panther X2 DTS 的 NPU 节点、IOMMU、clocks、power-domains、resets、OPP/devfreq 和中断资源；包中存在通用 rk3566 DTB 或 NPU 模块，不等于 Panther X2 硬件适配完成。

### 3.15 版本路线说明修正

- `kernel_stable/6.18.63`：通用 stable 内核线，之前的 RKNPU 编译实验属于该线；其结果不能代表 RK35xx 专用 BSP。
- `kernel_rk35xx/6.12.81`：当前更有针对性的 RK3566 专用 BSP 候选，优先进行离线包内容和 provenance 审计。
- 两条路线都尚未在 Panther X2 实机启动验证；也没有证明 RKNN runtime 与 Immich 可调用 NPU。


### 3.16 最早 Panther X2 BSP 与 RK35xx 6.12.81 对照：驱动来源和构建模型已初步查明

详细审计见 [`docs/BSP-SOURCE-AUDIT.md`](BSP-SOURCE-AUDIT.md)。

重要结论：
- 最早 BSP 的 RKNPU v0.9.8（日期 20240828）有明确 Rockchip 上游来源：`rockchip-linux/kernel` commit `736d89f344156b75393b01ab2c0e3a06c39e110f`，由 Rockchip 工程师 Shuangjie Lin 签署，修复多进程运行和 IOMMU domain switch。
- Armbian `linux-rockchip` 6.1.115 BSP 树继承这条 Rockchip 驱动线；不是 Panther 项目自行编写的 NPU 驱动。
- Panther BSP 和 Ophub RK35xx 6.12.81 都使用内核树内的 RKNPU 驱动构建路径。Panther 镜像验证明确要求 `CONFIG_ROCKCHIP_RKNPU=y`；6.12.81 的配置参考也启用 `CONFIG_ROCKCHIP_RKNPU=y`、`CONFIG_PM_DEVFREQ=y`、`CONFIG_ROCKCHIP_RKNPU_DRM_GEM=y`。
- 两条路线均调用 `pm_runtime_force_resume()`，但它由同一完整内核构建树内的 `drivers/base/power/runtime.o` 提供并在内核链接时解析。因此此前通用 6.18.63 外置模块测试遇到的 `Module.symvers` 缺符号，不是原 BSP 的构建方法，也不是 RK35xx 6.12.81 候选所要求的构建方式。此前外置模块实验的失败不能作为“BSP RKNPU 无法构建”的结论。
- RKNPU devfreq 源码使用内核内部头文件 `../drivers/devfreq/governor.h`，进一步说明它应在完整内核源码树内编译；不适合仅凭裁剪 headers 包来构建外置模块。
- Panther X2 基础板级 DTS 的可追溯来源为 `unifreq/linux-6.1.y`，最初由 Ophub 于 2023-07-07 添加，tdleiyao 于 2023-07-11 修改 USB host/GPU；但当前 Panther BSP 仓库中的 7,546 行扁平 DTS/DTB 输入文件来源仍未完全追溯。
- Panther BSP 曾专门修正 NPU IRQ binding，增加 `interrupt-names = "npu_irq"`。这与 Rockchip driver 按该名称获取中断的代码相吻合。
- 外部社区报告显示 RK3566 即使已初始化 RKNPU 0.9.8，也可能因 `npu_irq`、mem-supply、reg resource、IOMMU、power model 或 OPP/regulator 与 DTB 不匹配而无法正常使用。不能把其他 RK3566 板的 overlay 原样套到 Panther X2。

路线调整：
1. RKNPU 主验证改为完整 in-tree kernel CI build（`CONFIG_ROCKCHIP_RKNPU=y`、`CONFIG_PM_DEVFREQ=y`），不再以必须生成独立 `rknpu.ko` 作为成功条件。
2. 继续执行 RK35xx 6.12.81 发布包审计，但包中没有独立 `rknpu.ko` 可能正是 built-in 设计的正常结果；要看配置、`modules.builtin`、启动 DTB 和驱动日志。
3. 优先追查 Panther 专用扁平 DTS 的原始 DTB/DTS（仓库 `reference/source-input.sha256` 所列的两个输入目前未随仓库保存），并与 unifreq Panther DTS、Rockchip `rk356x.dtsi` / `rk3566-box.dtsi` 对照。
4. 对照 NPU `reg`、IRQ name/number、`rknpu-supply`、mem-supply、clocks、resets、power-domain、IOMMU、NPU OPP/bus OPP 和 regulator。
5. 仍需证明 6.12.81 发布资产与所观察源码 commit/config 的 provenance；仍未在 9.6 实机验证 probe 或 RKNN inference。


### 3.17 主线原则澄清：Ophub / 官方渠道优先，历史 BSP 仅作参考

本项目的目标不是复刻最早的 Panther X2 专用 BSP，也不是直接采用某个第三方 RK3566 镜像、DTS 或补丁。此前审计的 Panther X2 BSP、unifreq DTS、其他 RK3566 设备案例及社区修复，全部只作为硬件线索、历史问题、代码来源和验证清单。

**技术路线优先级固定如下：**

1. **Ophub 优先**：优先使用 Ophub 正式维护的 RK35xx 内核发布、源码分支、配置和构建流程，先验证现有支持能否满足 Panther X2。
2. **官方渠道其次**：需要补足时，优先查找 Armbian 官方、Rockchip 官方及相关 SoC/板级官方源码、驱动、DTS 和补丁。
3. **最小独立补丁**：只有证明 Panther X2 存在具体且可复现的支持缺口，才考虑增加独立补丁；补丁必须有明确来源、清晰差异、可审计构建和后续 rebase 路径，尽量避免复制整份旧 BSP 或维护整套分叉内核。
4. **第三方 BSP / 社区资料只作参考**：可以用来识别寄存器、中断、供电、时钟、IOMMU、OPP 等硬件线索，也可以帮助定位历史 bug；不得因其曾经可用就直接将其 DTS、DTB、内核配置或补丁纳入主线。
5. **长期可维护性优先于短期点亮**：如果某项 Panther X2 支持只能依赖无人维护的个人仓库或不可追溯的二进制 DTB，则必须明确记录维护风险，不能将其视为首选方案。

后续所有对照审计都应回答两个问题：
- Ophub 当前正式 RK35xx 发布/源码是否已经包含所需支持？若没有，官方渠道是否已有可维护的修复？
- 如果确实需要 Panther X2 专用补丁，能否把必要差异独立、最小化地维护，并持续应用到 Ophub 后续内核？

**本原则覆盖此前文档中任何可能被理解为“以最早 Panther BSP 为目标基线”的表述。** 历史 BSP 只用于反向审计和交叉验证，不改变 Ophub / 官方渠道优先的主线。

### 3.18 Ophub 官方主线与 RK35xx NPU 配置的差异：发现真实适配缺口

本轮直接检查 Ophub 自己的板型数据库、两条内核源码和官方配置参考，确认目前不是简单的“选 6.18 或 6.12”问题。

#### A. Ophub 当前 Panther X2 正式板型路径

在 Ophub amlogic-s9xxx-armbian 固定参考 commit 9e71b57f73683f9c4d14a30311e4c2ccbff29566 的 model_database.conf 中，Panther-X2 条目为：

- SoC：RK3566
- DTB：rk3566-panther-x2.dtb
- kernel tags：stable/6.18.y
- platform/family：rockchip/rk3566
- build：yes

这表示 Ophub 当前给 Panther X2 的正式板型构建路径是 stable/6.18.y，而不是直接把它列入 rk35xx/all 的通用 RK35xx kernel tag。

对应板级 DTS 在 Ophub linux-6.18.y 固定参考 commit 9bbed25243be8b43df410ebb9a8bbb1992234114 中存在，DTS blob SHA 为 a0a08476f45fb2d602fd7312def6f587f33fb91e。

#### B. Ophub stable 6.18.63：Panther 板型支持存在，但官方配置没有 RKNPU

Ophub kernel-config/release/stable/config-6.18 当前 blob SHA 为 57d061b9c4228c438b354ba58f09013d9f52f603，其配置包含 CONFIG_PM_DEVFREQ=y，但没有 CONFIG_ROCKCHIP_RKNPU 配置项；对应源码 commit 的 drivers/rknpu 目录也不存在。

在对应 linux-6.18.y 的 Panther X2 DTS 中可以看到 vdd_npu regulator 定义，但该板级 DTS 没有显式启用 NPU 节点，也没有板级 rknpu-supply / NPU IRQ-name 绑定。该源码的 RK3566 DTS 组织结构已不同于 6.12 vendor tree；不能仅凭存在 vdd_npu regulator 就推断内核有 RKNPU 驱动或 NPU 可用。

**阶段判断：** stable/6.18.y 是 Ophub 正式支持 Panther X2 的系统/内核路线候选，但按当前配置快照，不能作为已具备 RK3566 NPU 支持的路线。

#### C. Ophub RK35xx 6.12.81：驱动配置存在，但 Panther X2 NPU 节点默认未启用

Ophub kernel-config/release/rk35xx/config-6.12 blob SHA dee127c6c644f38426eeb28000d73536084d34a3 明确包含：

- CONFIG_ROCKCHIP_RKNPU=y
- CONFIG_ROCKCHIP_RKNPU_DRM_GEM=y
- CONFIG_ROCKCHIP_RKNPU_SRAM=y
- CONFIG_PM_DEVFREQ=y

在 Ophub linux-6.12.y-rockchip commit 661b2d8bf1284556f8876d5ed5fb80c64b22f94c 中，Panther X2 DTS 存在，blob SHA 为 d517c99841cf9d724a61cd31acf9437acbb131e6。SoC 公共文件 rk356x.dtsi 定义了 NPU 节点 npu@fde40000 和 IOMMU iommu@fde4b000，但两者默认均为 status = "disabled"。Panther X2 板级 DTS 虽定义 vdd_npu regulator，却没有覆盖 &rknpu / &rknpu_mmu 将其启用，也没有把该 regulator 通过 rknpu-supply 连接到 NPU 节点。该 6.12 驱动在没有 interrupt-names 时会回退到按序号获取 IRQ，因此不能把 npu_irq 名称缺失单独判定为必然 probe 失败；但中断映射仍需按实际 DTB 和驱动路径核实。mem-supply 是可选的第二路 regulator，驱动仅在同时提供 rknpu-supply 与 mem-supply 时启用双 regulator OPP helper。

**阶段判断：** RK35xx 6.12.81 在内核配置和 SoC 驱动层具备 NPU 基础，但当前可见的 Panther X2 DTS 尚未启用 NPU 节点。不能把 CONFIG_ROCKCHIP_RKNPU=y 当作 Panther X2 NPU 已可用。

#### D. 两种 6.12.81 发布资产不可混为一谈

Ophub kernel_rk35xx release 同时发布：
- 标准 6.12.81.tar.gz：141,437,450 bytes，SHA256 72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b；
- 6.12.81-rk35xx-flippy-2611b.tar.gz：119,018,056 bytes，SHA256 a5b0bc5d3c8311cee472c105e5ee2d1c9e6395a94efb4488253a0faae132d064。

两者属于同一 release tag 下的不同资产，不能假定配置、模块集、DTB 或用途相同。当前审计 workflow 只下载标准包；下一轮 CI 应比较两个包的实际 .config、kernel.release、modules.builtin、DTB 和模块清单，再决定是否保留 flippy 变体作为候选。flippy 变体不因名字或体积而被默认选用。

#### E. 当前路线判断

- 如果优先要稳定获得 Ophub 已登记的 Panther X2 板级启动支持：stable/6.18.y 是目前最直接的官方构建路径；但 RKNPU 支持尚未出现在对应配置快照中。
- 如果优先验证 Rockchip RKNPU 驱动：RK35xx 6.12.81 有内置驱动配置和 SoC NPU 节点；但 Panther X2 板级 DTS 当前未启用该节点，仍有明确的板级适配缺口。
- 因此当前不存在“已确认同时满足 Panther X2 官方板型支持 + NPU 开箱可用”的 Ophub 方案。最小补丁可能是未来选项，但在确认发布包 DTB、完整 DTS 资源和驱动绑定之前不创建、不应用。
- 继续优先以 Ophub 官方源码/配置为主线；不采用最早第三方 Panther BSP 的扁平 DTS，也不把其他 RK3566 板的 DTB/overlay 直接移植过来。

#### F. 下一项只读验证

更新 RK35xx package audit：对标准和 flippy 两个 6.12.81 资产分别下载并校验 SHA256，提取实际 header config、kernel.release、modules.builtin、boot DTB；反编译实际 rk3566-panther-x2.dtb（若资产包含），检查 rknpu、rknpu_mmu、rknpu-supply、interrupt-names 和 status。该 CI 只读取发布资产，不加载驱动、不部署系统、不接触 9.6。


#### CI workflow update

已将 .github/workflows/audit-rk35xx-kernel.yml 扩展为标准版与 Flippy 版双资产只读比较，并在 config/versions.env 中固定 Flippy 资产 URL、大小、SHA256 和更新时间。新 workflow 会：
- 分别下载并严格核对两个发布资产的 SHA256/文件大小；
- 比较嵌套 headers、boot、modules 包；
- 提取实际 headers 中的 .config、kernel.release、Module.symvers；
- 从 headers/modules 包检查 modules.builtin 和 RKNPU 相关条目；
- 对发布包内 Panther X2 / RK3566 DTB 进行反编译，提取 NPU 节点、IOMMU、供电、中断和 status 属性；
- 上传两种资产的独立报告及合并比较报告。

当前 workflow 只做下载、解包和静态审计，不安装内核、不加载模块、不应用 DTB、不接触 Panther X2 实机。请手动运行 Actions：Audit Ophub RK35xx 6.12.81 kernel assets。完成后再根据 artifact 结果决定是否需要继续研究 Flippy 变体或最小板级适配。


### 3.19 Ophub RK35xx 6.12.81 发布资产首轮检查结果（2026-11-14）

CI run 43596176146 / job 132451039113 完成了两个发布资产的下载和 SHA256/大小校验：

| 资产 | SHA256 校验 | 大小校验 |
|---|---|---|
| 标准版 6.12.81.tar.gz | 通过 | 通过，141,437,450 bytes |
| Flippy 6.12.81-rk35xx-flippy-2611b.tar.gz | 通过 | 通过，119,018,056 bytes |

#### 标准版已确认的内容

- 嵌套 headers、boot、modules 三个归档均被首版脚本识别。
- headers 归档提供 `include/config/kernel.release`，值为 `6.12.81-rk35xx-ophub`。
- headers 归档提供 `Module.symvers`，其中包含 `pm_runtime_force_suspend` 与 `pm_runtime_force_resume` 的导出符号。
- headers 归档没有包含 `.config`；因此不能将 Ophub config 仓库中的配置快照直接说成已从该发布包内核构建产物提取。
- modules 归档中的 `modules.builtin` 明确列出 `kernel/drivers/rknpu/rknpu.ko`。按 Linux `modules.builtin` 语义，这表示 RKNPU 被编译进内核（built-in），不是一个可通过 `insmod rknpu.ko` 单独加载的模块文件。这是当前最重要的新证据：**标准版 6.12.81 的模块清单表明它包含内建 RKNPU 驱动**。
- 标准版首轮脚本在 boot 内部归档中没有找到以 `.dtb` 结尾的条目，尚不能据此判断该发布包没有 Panther DTB；也可能 DTB 位于其他嵌套归档、采用不同文件命名或打包布局。必须修正审计脚本后再确认。

#### Flippy 版当前状态

两个 SHA256/大小校验均通过，但首版脚本只按标准版目录命名规则匹配嵌套归档，因此 Flippy 版的 headers/boot/modules 都未识别。**这是审计脚本的布局假设问题，不是 Flippy 版缺少这些内容的证据。** 暂不对 Flippy 作任何 NPU 支持结论。

#### 配置参考校验

CI 下载的 Ophub RK35xx config-6.12 快照长度为 258,639 bytes，其 Git blob SHA-1 为 `dee127c6c644f38426eeb28000d73536084d34a3`，与固定参考值一致。该配置明确包含：

- `CONFIG_ROCKCHIP_RKNPU=y`
- `CONFIG_ROCKCHIP_RKNPU_DRM_GEM=y`
- `CONFIG_ROCKCHIP_RKNPU_SRAM=y`
- `CONFIG_PM_DEVFREQ=y`

注意：这是 Ophub 官方配置仓库的固定快照，和发布包 `modules.builtin` 的证据相互印证，但仍未证明该 config 文件就是该资产的精确构建输入；发布包 headers 没有 .config，source-to-binary provenance 仍未闭环。

#### 首轮审计脚本问题及修正

首版 workflow 的包内路径匹配写死了标准版的 `6.12.81/header-*.tar.gz` 等布局，无法识别 Flippy 变体；同时在 source/config 校验中使用相对路径调用 `git hash-object`，导致命令在子目录上下文下失败。这两个都是 workflow 缺陷，不是 Ophub 内核包错误。

已将 `.github/workflows/audit-rk35xx-kernel.yml` 重写为按内容识别嵌套归档的只读审计：
- 保存两个资产完整的外层文件清单；
- 扫描每个嵌套 tar.gz/tgz，不依赖外层目录和文件名；
- 按归档内部的 Module.symvers、kernel.release、modules.builtin、DTB 等内容识别 header/module/boot 证据；
- 对每个 modules.builtin 提取 RKNPU 条目；
- 对发现的 Panther/RK3566 DTB 反编译并提取 NPU 属性；
- 修正 config blob 校验的绝对路径，并上传完整 work 报告。

本次修正提交：`10fdd8961df8ecd21b2988501b8e18f00584de61`。尚未运行新版 workflow，所有 Flippy 和 DTB 结论待下一轮 CI。

**当前判断更新：** Ophub RK35xx 标准 6.12.81 内建 RKNPU 的证据已经成立（发布包 modules.builtin + 官方 config 快照双重佐证）；但 Panther X2 实际发布 DTB 是否启用 NPU/MMU、供电绑定是否正确仍未知。因此“内核驱动存在”已从推测升级为已验证；“Panther X2 NPU 可正常 probe/运行”仍未验证。继续不安装内核、不加载模块、不修改 9.6。


### 3.20 双资产扫描第二轮结果与审计产物优化（2026-11-14）

CI run 43596798887 / job 132452929530：

- 标准版发布包 SHA256 与预期一致：`72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`；文件大小 141,437,450 bytes。
- Flippy 版在同一轮也通过了下载与完整性校验（具体值沿用 config/versions.env 中固定资产记录）。
- source/config reference 阶段通过：源码 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，Makefile 版本 6.12.81；配置快照 Git blob SHA `dee127c6c644f38426eeb28000d73536084d34a3` 与预期一致。
- workflow 成功完成嵌套归档扫描、汇总文件生成和 artifact 上传；但当轮脚本没有将扫描摘要输出到 job log，且 artifact 上传范围误包含解包树及源码树，最终 artifact 达 1,147,037,510 bytes。GitHub 提示存在大量同路径文件覆盖，导致无法通过当前 artifact 下载工具（单文件上限 512 MiB）直接取回并复核摘要。
- 因此本轮**尚不记录** Flippy 的 RKNPU 状态、两个包的 DTB 内容或 NPU 节点属性；不能把“扫描执行完成”误写成“结果已人工复核”。

#### 下一轮审计脚本调整

提交 `8dece11a5307176ed59c8c98e32b7c54cbd9f010`：
- artifact 仅上传 `work/reports/`、`work/standard/reports/`、`work/flippy/reports/`，不再上传原始内核包、完整解包树或源码 checkout；
- 新增 concise findings 日志步骤，将标准版与 Flippy 版的资产元数据、嵌套归档索引、kernel.release、Module.symvers、modules.builtin/RKNPU、DTB 清单及 NPU 属性直接输出到 job log；
- 将此前 `grep | head` 改为 `grep | sed`，避免大文件扫描时大量 Broken pipe 噪声。

下一轮应重点人工核对标准版与 Flippy 版各自的 `modules.builtin`、实际 Panther X2/RK3566 DTB、`rknpu` 与 `rknpu_mmu` 状态、电源绑定和 IRQ 映射。source-to-binary provenance 仍未闭环。整个流程仍为 CI 只读审计，不接触 Panther X2 实机。


### 3.21 Ophub 6.12.81 双资产报告复核：Panther X2 NPU 的实际阻断点（2026-11-14）

CI run 43597391230 / job 132454730145 成功；artifact `14114622745` 已下载并解包人工复核（约 2.88 MB）。本节结论以两个发布包内部实际文件为准，不再只依据日志摘要。

#### 资产完整性和归档结构

| 项目 | 标准版 | Flippy 版 |
|---|---|---|
| 文件大小 | 141,437,450 bytes | 119,018,056 bytes |
| SHA256 | `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b` | `a5b0bc5d3c8311cee472c105e5ee2d1c9e6395a94efb4488253a0faae132d064` |
| 嵌套归档 | DTB / boot / modules / headers | DTB / boot / modules / headers |
| Panther X2 DTB | `rk3566-panther-x2.dtb` | `rk3566-panther-x2.dtb` |

两包的 Panther X2 DTB 反编译结果相同（DTS 文本 SHA256：`d701f187e2a4a06723b7f33cf4e3ec731a461f0942dd863b9bc5e86ad2e9b033`）。这是反编译文本哈希，不是原始 DTB 哈希。

#### 两个发布包的 RKNPU 驱动配置

- 标准版 `modules.builtin`：`kernel/drivers/rknpu/rknpu.ko`。
- Flippy 版 `modules.builtin`：同时包含 `kernel/drivers/rknpu/rknpu.ko` 与 `kernel/drivers/soc/rockchip/rknpu3/rknpu3.ko`。
- Flippy headers 内有真实 `.config`，确认 `CONFIG_ROCKCHIP_RKNPU=y`、`CONFIG_ROCKCHIP_RKNPU3=y`、`CONFIG_ROCKCHIP_IOMMU=y`、`CONFIG_PM_DEVFREQ=y`。
- 标准版 headers 没有 `.config`；Ophub 官方 6.12 配置快照包含 `CONFIG_ROCKCHIP_RKNPU=y`、`CONFIG_ROCKCHIP_IOMMU=y`、`CONFIG_PM_DEVFREQ=y`。标准版发布包的 `modules.builtin` 也直接证明 RKNPU built-in。
- 两个版本的 kernel.release 分别为 `6.12.81-rk35xx-ophub` 和 `6.12.81-rk35xx-flippy-2611b`。两者 headers 的 Module.symvers 均包含 PM runtime force suspend/resume 导出符号。

因此，两个 Ophub 6.12.81 发布变体都包含 Rockchip RKNPU 核心驱动；Flippy 版还额外启用了 RKNPU3 驱动。注意：`modules.builtin` 是 built-in 清单，不代表存在可单独 insmod 的模块文件。

#### 实际 Panther X2 DTB 的决定性发现

两个包内 `rk3566-panther-x2.dtb` 反编译后关键内容一致：

- `npu@fde40000` 节点具有 RK3568 RKNPU compatible、寄存器、中断、时钟、reset、power-domain、OPP 和 IOMMU 引用，但 `status = "disabled"`。
- `iommu@fde4b000` 节点也为 `status = "disabled"`。
- PMIC 中确实存在 `regulator-name = "vdd_npu"`，但 NPU 节点没有 `rknpu-supply` 属性将该 regulator 绑定给驱动。
- NPU 节点的 IRQ specifier 是 GIC SPI 0x97；IOMMU 节点也使用相同中断号并有 `interrupt-names = "rknpu_mmu"`。需结合精确驱动的中断处理方式再确认共享/映射语义；不能仅因没有 NPU `interrupt-names` 就断言必然失败。
- DTB 中存在 NPU OPP table 与 reserved-memory 的 `rknpu` shared-dma-pool 节点，但这些资源存在不等于设备已启用。

**结论：目前阻断 Panther X2 NPU 开箱工作的首要问题不是缺驱动，而是两个 Ophub 发布包使用的 Panther X2 DTB 都把 RKNPU 和其 IOMMU 关闭了。** 即使内核已内建 RKNPU，Linux 也不会按正常 platform-device 流程 probe 这个 disabled 节点。其次，NPU 电源 regulator 尚未在节点中建立 `rknpu-supply` 绑定，属于启用前必须审查的板级电源描述问题。

#### 对主线选择的影响

1. Ophub RK35xx 6.12.81 标准版：内建 RKNPU，带 Panther X2 DTB，但该 DTB 禁用 NPU/MMU；不能称为 NPU-ready。
2. Ophub RK35xx 6.12.81 Flippy 版：同样内建 RKNPU，额外内建 RKNPU3，但 Panther X2 DTB 与标准版相同且禁用 NPU/MMU；额外驱动并未解决 Panther X2 的设备树问题。
3. Ophub stable 6.18.y：当前仍是 Panther X2 板型维护路线候选，但对应参考源码没有 RKNPU 驱动目录；需要后续关注上游/官方支持是否补齐。
4. 目前不建议为了 Flippy 多出的 RKNPU3 而优先选 Flippy。Panther X2 是 RK3566，应先确认其 NPU 对应 RKNPU 代际及 runtime ABI；RKNPU3 不能直接视为该板 NPU 必需项。

#### 下一步研究（仍只读，不生成可刷写补丁）

- 比较 Ophub RK35xx 6.12.81 的 Panther X2 DTS 与其同源 RK356x SoC DTS、Ophub 其他 RK3566 板级 DTS，确认启用节点所需的最小属性、regulator、IOMMU、OPP、clocks/resets/power-domain 与 IRQ 绑定。
- 对照 Rockchip 官方 Linux 6.1/6.6 BSP 或公开 RK3566 Panther X2 BSP 的驱动和 DTS 变更，追溯 `rknpu-supply` 与 NPU enable 的来源及适用硬件；第三方 BSP 只作来源/差异参考，不直接移植。
- 在确定设备树差异前，不修改仓库中的产品 DTS、不生成部署补丁、不触碰 9.6。
- 后续若确认可做最小板级补丁，先在 CI 编译 DTB 并做静态 binding/资源核查，再评估实机验证所需的回滚与备份条件。

本轮结论状态：发布包驱动存在、DTB 中 NPU/MMU disabled、两个变体 DTB 相同，均为已验证；NPU 实际硬件 probe、RKNN runtime 兼容、Immich 能否调用 NPU 仍未验证。


### 3.22 Panther X2 NPU board-DTS source trace（2026-11-14）

本轮对照了 Ophub 6.12.81、Armbian Rockchip Vendor 6.1、unifreq Panther X2 原始 DTS、后续 Panther X2 Vendor BSP DTS，以及最早 BSP 集成 patch。

#### 已确认的来源关系

1. Panther X2 原始板级 DTS 由 Ophub 于 2023-07-07 通过 `unifreq/linux-6.1.y` commit `afaa1a194f812e30a9faedd88d6c09e7a49d909a` 加入；文件版权标识为 `tdleiyao`。2023-07-11 commit `80101d21c55ec1c87a00a52a0c3e137a37ac7a80` 明确调整 USB host 并启用 GPU。原始 Panther DTS 定义了 PMIC 的 `vdd_npu`，但没有启用 `&rknpu`、`&rknpu_mmu` 或 `&bus_npu`。
2. Ophub 6.12.81 的 SoC `rk356x.dtsi` 已定义 NPU、IOMMU、NPU bus、时钟、复位、电源域、OPP 等资源，但这些 SoC 节点默认 disabled。
3. Panther X2 Vendor 6.1 板级 DTS（Lyric-c/panther-x2 固定快照）后来加入：
   - `&rknpu`: `rknpu-supply = <&vdd_npu>` + `status = "okay"`
   - `&rknpu_mmu`: `status = "okay"`
   - `&bus_npu`: `bus-supply = <&vdd_logic>`、`pvtm-supply = <&vdd_cpu>`、`status = "okay"`
4. 同一 Panther X2 Vendor DTS 没有设置 `mem-supply`。因此不能把 H96 Max V56 的 `mem-supply = <&vdd_logic>` 复制到 Panther X2；H96 的双 regulator 连接是板型特定实现。
5. 最早 Panther BSP flattened patch 也包含相同的 NPU/MMU/bus enablement 和 supply phandle，并额外写入 `interrupt-names = "npu_irq"`。该 patch 的原始 DTS/DTB 输入哈希文件仍未找到，因此结果配置可审计，但其精确作者来源仍未闭环。

#### IRQ 绑定更正

对比了固定的 Armbian/Rockchip 6.1 BSP 驱动 commit `5280f9b4336199c4025c8eed894d2b4e2268dcc6` 与 Ophub 6.12.81 驱动 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 `rknpu_register_irq()`：

- 两者均优先按 `npu_irq` 名称查找；
- 在 Linux >= 6.1 的代码路径中，如果没有命名资源，会回退到 `platform_get_irq(pdev, 0)`；
- 因此显式 `interrupt-names = "npu_irq"` 是更清晰、可审计的绑定，也被最早 BSP 的 CI 明确检查，但不能据此断言它是这两个确切驱动版本 probe 成功的硬性条件。
- 实际 IRQ specifier、资源映射和 IRQ request 仍需后续验证。

#### 当前可推导的最小 DTS 差异（候选，不是补丁）

Ophub 6.12.81 Panther X2 DTS 已有 `vdd_npu`、`vdd_logic`、`vdd_cpu`；SoC DTSI 已有 NPU、IOMMU、bus_npu、OPP、clock/reset/power-domain 节点。对照 Panther Vendor 6.1 后，候选板级差异收敛到上述三个 fragment，而不是重新定义完整 NPU 节点或导入整套扁平 BSP DTS。

这仍只是静态来源比较，不是可以直接应用的补丁。还需审查：
- 6.12.81 包内 DTB 与参考源码 commit 的精确 provenance；
- Panther X2 PMIC 电压范围与 NPU/bus OPP 表；
- bus_npu devfreq/OPP 驱动路径；
- 4 GB RAM 下启用 IOMMU 的 DMA 地址风险；
- 实机 probe、RKNN runtime 与实际推理。

没有生成或应用 DTS patch，没有修改 9.6。后续优先做固定版本的 DTS/DTB 离线构建和静态资源检查；实机验证另行授权。


### 3.23 NPU OPP、电源、bus_npu 与 DMA/IOMMU 审计（2026-11-14）

本轮对固定 Ophub 6.12.81 源码与 Panther X2 Vendor 6.1 DTS 做了静态交叉核对。

- NPU OPP 表启用档位的标称电压约 0.85–1.0 V；Panther X2 `vdd_npu` 声明范围 0.5–1.35 V、初始 0.9 V，静态范围覆盖。不能据此证明真实供电稳定或芯片 OPP bin 正确。
- NPU bus OPP 标称电压约 0.875–0.95 V；`vdd_logic` 声明范围 0.5–1.35 V、初始 0.9 V，静态范围覆盖。NPU bus 通过 `bus-supply=vdd_logic`、`pvtm-supply=vdd_cpu` 与 RK356x `clkfreq` policy 驱动匹配。
- 固定版本 `rockchip_bus.c` 对 `rockchip,rk3568-bus` 获取 `bus` clock、`bus` regulator，并用 `pvtm` supply 初始化 OPP/PVTM；升频前和降频后调节 bus 电压。故 Vendor DTS 的 bus supplies 与驱动实现是相互对应的。
- 固定版本 RKNPU driver 对 `rknpu` 和 `mem` regulator 都采用 optional 获取；OPP helper 只有在 DT 节点存在 `mem-supply` 时才添加第二 regulator。Panther X2 单 `rknpu-supply` 是驱动支持的拓扑，不应照搬 H96 双供电。
- RK356x RKNPU config 使用 `DMA_BIT_MASK(32)`。4GB RAM 本身覆盖 32-bit 地址空间 0..0xffffffff，不能单凭“4GB”认定 IOMMU 不兼容。启用 IOMMU 时需验证 32-bit IOVA 与物理页映射；禁用 IOMMU 时驱动走 reserved-memory 初始化，发布 DTB 已发现 rknpu shared-dma-pool，但仍需核实其地址、大小和 CMA 交互。
- NPU OPP 引用的六个 NVMEM cell phandle 均在 RK356x DTSI 定义，源码层面没有悬空引用；实际 OTP/eFuse 数据是否有效未验证。

**风险判断修正：** 删除“4GB RAM 很可能阻止启用 IOMMU”的笼统推断。当前已证实的限制是 32-bit DMA mask；兼容性取决于实际物理内存图、IOVA、IOMMU 驱动和 reserved pool。现阶段没有理由预先建议关闭 IOMMU。

下一步可在 CI 临时工作目录中应用候选板级 DTS fragment，编译 DTB 并做静态差异检查；不修改产品 DTS、不生成可部署补丁、不触碰 9.6。只有 CI 静态检查通过后，才进入明确授权的后续阶段。


### 3.24 Panther X2 NPU DTB source-readiness CI（版本基线更正，2026-11-14）

新增手动触发 workflow：`.github/workflows/audit-panther-npu-dtb.yml`。该工作流的唯一目标基线是 **Ophub RK35xx 6.12.81**，与当前 NPU 驱动、SoC DTSI、BSP 来源审计保持一致。

此前首次提交误引用了 6.18.63 的普通 Ophub kernel package 变量。这是工作流编写错误，不能视为项目改选 6.18.63。用户指出后，已修正为：
- 源码仓库/commit：`OPHUB_RK35XX_KERNEL_SOURCE_REPO` / `OPHUB_RK35XX_KERNEL_SOURCE_COMMIT`
- 内核版本：`OPHUB_RK35XX_KERNEL_VERSION=6.12.81`
- 发布包：`OPHUB_RK35XX_PACKAGE_URL` / `OPHUB_RK35XX_PACKAGE_SHA256`
- 包内 DTB 归档目录匹配：`6.12.81/dtb-rockchip-*.tar.gz`

工作流先构建未修改的 6.12.81 Panther X2 DTB，提取并反编译校验过 SHA256 的 6.12.81 RK35xx 发布包 DTB，再核对源码 DTSI、源码构建 DTB、发布 DTB。只有在 6.12.81 源码确实具备 SoC 级 NPU 节点时，才会在 CI 临时副本追加板级候选 fragment；如果节点缺失则报告 `SKIPPED`，不拼接不完整节点。

本工作流只做 CI source-readiness audit，不修改产品 DTS、内核包或 9.6。6.18.63 仍仅属于此前外置 RKNPU 模块构建研究线，不参与本次 NPU DTB 适配决策。


### 3.25 6.12.81 NPU DTB 审计第 1 次运行结果（2026-11-14）

Actions run `43599704496` / job `132461624075` 使用固定源码 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，确认 Makefile 版本为 6.12.81。

**本轮明确验证：**
- Panther X2 板级 DTS 文件存在，但本身没有 `rknpu` / `bus_npu` 启用片段。
- RK356x SoC DTSI（`rk356x.dtsi`）确实定义 `rknpu`、NPU OPP 表、`bus_npu`、bus OPP 表和 `rknpu_mmu`。此前报告称 6.12.81 缺少 SoC NPU 节点，是路径检查错误，现已纠正。
- NPU 与 MMU 默认状态均为 disabled；bus_npu 默认 disabled。这与 Panther X2 板级需要显式启用的判断一致。
- 源码审计步骤成功；DTB 构建步骤失败于 Kbuild 目标写法：从 kernel top-level Makefile 调用时传入了完整 `arch/arm64/boot/dts/rockchip/...` 路径，顶层规则又拼接架构目录，最终产生重复路径 `arch/arm64/boot/dts/arch/arm64/boot/dts/rockchip/...`。这不是 DTS 语法或 NPU 硬件兼容错误。
- 已将目标改为顶层 Kbuild 接受的 `rockchip/rk3566-panther-x2.dtb`，提交 `b369638c6f3db80c11f6dd8f59261beb5c0c7b8b`。

**重要补充：** 当前 workflow 中候选板级片段尚未编译成功，因此不能声称候选 DTB 已生成。下一轮应重新运行，确认基线 DTB、发布包 DTB 提取与候选 DTB 编译结果；若出现 DTC warnings，再逐项分析是否来自原 DTS 或新增 NPU 片段。


### 3.26 6.12.81 NPU DTB audit 第 2 次运行（2026-11-14）

Actions run `43600205650` / job `132463126060`：

**已成功的部分**
- 固定 Ophub 源码 commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，Makefile 版本核验为 6.12.81。
- Panther X2 板级 DTS 无 NPU / bus_npu 覆盖配置。
- `rk356x.dtsi` 确实定义 `rknpu`、`npu_opp_table`、`bus_npu`、`bus_npu_opp_table` 和 `rknpu_mmu`。SoC 节点存在，不是缺少 SoC NPU 支持。
- Kbuild 已成功执行 `DTC arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dtb`，即原始 Panther X2 DTB 已经成功编译。

**本轮失败原因**
- 编译完成后，workflow 错误地从 `work/kernel-source/rockchip/rk3566-panther-x2.dtb` 复制 DTB；实际产物位于 `work/kernel-source/arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dtb`。
- 这是 workflow 的产物路径错误，不是内核或 DTS 编译失败。发布包提取与候选 DTS 编译步骤因此尚未执行。

已修正基线和候选 DTB 两处复制路径，提交 `d9406cafe065e229030afa5daf6313a13bd0ed52`。

**下一轮需要继续验证**
1. 基线 DTB 反编译；
2. 6.12.81 发布包 SHA256 校验、目标 DTB 提取；
3. 候选 fragment 编译；
4. 候选 DTB 反编译，确认 NPU/IOMMU/bus 节点属性。

目前仍未将候选 DTS 写入产品文件，所有改动只在 CI 临时 checkout 中进行。


### 3.27 Ophub RK35xx 6.12.81 Panther X2 NPU candidate DTB successfully built and inspected（2026-11-14）

Actions run `43600749020` / job `132464761260` succeeded. Artifact `14116073830` was downloaded and its actual contents inspected, not just inferred from the job's exit code.

**Strong source/package correspondence result**
- Fixed source commit: `661b2d8bf1284556f8876d5ed5fb80c64b22f94c`, Makefile version 6.12.81.
- Unmodified Panther X2 DTB built from this source: SHA256 `00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185`.
- Panther X2 DTB extracted from the SHA256-verified Ophub 6.12.81 RK35xx package: exactly the same SHA256 `00220c6cabc02573099e74dec912787dcb629ff5904f280f25bc782e92332185`.
- Therefore the published Panther X2 DTB is bit-for-bit identical to the DTB built from this pinned source snapshot. This proves DTB source correspondence for this asset, but does not by itself prove the provenance of the kernel Image or every other package component.

**Candidate DTB**
- CI-only candidate SHA256: `b58722d035e4f9c18406c46e1498c03b679ae8df4cd56d14e45d3bd3be19cb34`.
- Candidate decompilation confirms:
  - `/bus-npu`: `status = "okay"`, `bus-supply` resolves to the existing `vdd_logic` regulator, `pvtm-supply` resolves to `vdd_cpu`, existing bus clock and bus OPP table retained.
  - `/npu@fde40000`: `status = "okay"`, `rknpu-supply` resolves to existing `vdd_npu` (PMIC DCDC_REG4), existing IRQ specifier, clocks, resets, power-domain, OPP table and `iommus = <&rknpu_mmu>` retained. Candidate adds `interrupt-names = "npu_irq"`.
  - `/iommu@fde4b000`: `status = "okay"`; existing `rockchip,iommu-v2`, clocks, IRQ and power-domain retained.
  - No new `mem-supply` or reserved-memory region was added. This follows the audited Panther BSP board fragment and the exact 6.12.81 driver's optional single-`rknpu` regulator path; do not add a generic RK3566 board's memory rail or IOMMU workaround without Panther-specific evidence.
- The candidate is 92 bytes larger than the baseline DTB. Decompiled comparison shows the intended NPU bus/NPU/MMU enablement and supply/IRQ-name properties, plus automatic phandle renumbering with corresponding references adjusted by DTC. A future automated semantic tree comparison should explicitly validate references and ensure no unrelated effective node changes.

**Warnings**
- Candidate DTB decompilation reports the same 14 warning classes/paths as the unmodified source-built baseline and published DTB; no new DTC warning class or path was introduced by the NPU fragment. Existing warnings include duplicate unit addresses and graph/address-cell notices in unrelated display, PHY, NAND, reserved-memory and OTP nodes. They are pre-existing DTS warnings, not proof of NPU correctness.

**Status**
- 6.12.81 source DTB build: passed.
- Published package DTB extraction and SHA256 verification: passed.
- Published DTB == pinned source-built DTB byte-for-byte: passed.
- CI-only NPU candidate DTB build: passed.
- Candidate static node/supply/IRQ inspection: passed at DTS structural level.
- Driver probe, regulator voltage behavior, NPU/IOMMU DMA behavior, NVMEM/OPP calibration, sustained inference, RKNN runtime compatibility and Immich integration: not tested.

Artifact: [run 43600749020](https://github.com/njosd/panther-x2-armbian/actions/runs/43600749020) / [job 132464761260](https://github.com/njosd/panther-x2-armbian/actions/runs/43600749020/job/132464761260), artifact ID `14116073830`.


### 3.28 NPU DTB semantic audit harness added（2026-11-14）

在 3.27 的两个 DTB 候选已成功编译后，继续补上自动化语义差异审计。此次只修改 GitHub 仓库中的审计脚本和手动触发 CI，不修改产品 DTS、内核包或任何设备。

- 新增/修正 `scripts/audit-npu-dtb.py`，提交：`bcacdd42fafb84c108de213fa3e9e97932877040`。
- 更新 `.github/workflows/audit-panther-npu-dtb.yml`，提交：`23b9a60d0f74b7db36f83d30fc97a56a49a79ec4`；随后修正 IRQ-name 插入逻辑，提交：`fd862c396dd379390c48b9cf3794041330d1cd4c`。

#### 本轮审计逻辑

1. 将候选分成两份独立 DTB：
   - Vendor-equivalent：只包含 Panther Vendor DTS 已有的 `bus_npu`、`rknpu`、`rknpu_mmu` 启用及供电属性；
   - IRQ-name variant：在前者基础上只额外增加 `interrupt-names = "npu_irq"`。
2. 对比基线与候选的完整节点树；任何节点新增/删除均失败。
3. 对比所有属性；只有三个目标节点的明确白名单属性允许变化。
4. phandle 与 linux,phandle 数值不直接比较；对供电、时钟、复位、电源域、IOMMU、OPP 等引用，先解析到目标节点路径，再比较引用语义，避免 DTC 因新增引用而自动重排 phandle 时产生误报。
5. 显式验证 `bus-supply -> vdd_logic`、`pvtm-supply -> vdd_cpu`、`rknpu-supply -> vdd_npu`，并确认 NPU IRQ specifier、clocks、resets、power-domain、OPP、IOMMU 引用及 bus 时钟/OPP 引用与基线保持一致。
6. 验证两个候选之间唯一差异为 `interrupt-names = "npu_irq"`。

#### 当前状态

- 脚本和 workflow 已提交到仓库。
- **语义审计尚未执行**：当前 GitHub connector 未提供 workflow_dispatch 触发动作，因此不能把静态脚本审查写成 CI 通过。
- 下一步在 Actions 手动运行 `Audit Panther X2 NPU DTB source readiness`，检查 `SEMANTIC_DTB_AUDIT=PASS`、两份候选 DTB 的 SHA256、DTC warnings 以及工作流完整日志。
- 若失败，先修复审计工具或明确的 DTS 差异，不扩大白名单、不绕过检查。
- 仍不修改 9.6，不制作可刷写补丁；驱动 probe、NPU 实际推理及 RKNN/Immich 兼容性仍未验证。


### 3.29 Recheck 6.12.81 RKNPU IRQ lookup behavior（2026-11-14）

重新读取固定 Ophub 源码仓库 `ophub/linux-6.12.y-rockchip`、commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 `drivers/rknpu/rknpu_drv.c`，确认 `rknpu_register_irq()`：

- Linux 6.1 及以上代码路径先通过 `platform_get_irq_byname(pdev, config->irqs[i].name)` 查找命名 IRQ；
- 若返回负值，则回退到 `platform_get_irq(pdev, i)`；
- 因而对当前 RK3566 单 IRQ 配置，缺少 `interrupt-names = "npu_irq"` 时会尝试第 0 个 IRQ；显式命名不是该代码路径的绝对 probe 前置条件。
- 这只证明驱动的 IRQ 获取回退逻辑，不证明目标 DTB 中 IRQ specifier 正确、IRQ 能成功申请或硬件中断工作正常。

因此保留两个独立候选：Vendor-equivalent 不加 IRQ name；IRQ-name variant 只额外加该名称。由 CI 语义审计比较两者，不预先把可选属性升级为强制要求。


### 3.30 First semantic audit failure and provider-cell parser correction（2026-11-15）

运行记录：GitHub Actions run `43605172495`，job `132478182685`，对应仓库提交 `3a6f30c953025c689cb210be10fde7ee2d3ed38c`。

#### 已通过的阶段

- 固定 Ophub 6.12.81 源码获取成功；
- 未修改源码的 Panther X2 baseline DTB 构建成功；
- 发布包下载成功，外层包 SHA-256 校验成功；
- 发布 DTB 提取和反编译成功；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 均编译成功。

#### 失败原因

语义比较器在 `/audpwm@fe470000:clocks` 报出引用目标变化。检查比较器实现后确认：旧逻辑把引用属性中的每个 32-bit cell 都视为 phandle，错误地把 clock/reset/power-domain 等 provider 后面的参数 cell 也解析成 phandle。此错误会在不同 DTB 的 phandle 编号变化时制造假差异。

因此本次结果应标记为：
- DTB 构建：通过；
- 语义审计：未通过（审计器实现缺陷导致，不能据此判定 DTS 候选错误）；
- 设备运行/NPU 推理：未验证。

#### 修正

提交 `dec5835f6784bc2372ccae5525a9deb25d633723` 修正 `scripts/audit-npu-dtb.py`：
- 按 provider 节点的 `#clock-cells`、`#reset-cells`、`#power-domain-cells`、`#iommu-cells`、`#interrupt-cells`、`#phy-cells`、`#dma-cells` 等属性解析 phandle + argument cells；
- 对单 phandle 引用与 GPIO、pinctrl 引用分别处理；
- provider 缺少 cell-count、phandle 无法解析或 specifier 截断时 fail closed，不以放宽白名单跳过。

下一步重新运行 `Audit Panther X2 NPU DTB source readiness`。只有新运行明确输出 `SEMANTIC_DTB_AUDIT=PASS` 才能将语义审计标记为通过。还需检查两份候选的实际差异报告和 DTC warnings。


### 3.31 Second semantic audit run: missing helper functions and fdtget argv order（2026-11-15）

运行记录：GitHub Actions run `43652224306`，job `132623006169`，执行仓库提交 `d8a9005986c18055cf9b6008e1a8f67e4f4f33e3`。

#### 本轮结果

- 固定 Ophub 6.12.81 源码获取、未修改基线 DTB 构建：通过；
- 发布内核包 SHA-256 校验、发布 DTB 提取及反编译：通过；
- Vendor-equivalent 候选、IRQ-name 候选 DTB：均成功编译；
- 语义比较器启动失败：`name 'walk_nodes' is not defined`。因此仍未执行语义比较。

#### 根因与修复

上次替换引用解析逻辑时误删了 `run_fdtget`、`walk_nodes`、`property_names`、`phandle_map` 四个辅助函数。先在提交 `2475195015ce621f1a97a92bac4c08a5f248ac1f` 恢复这些函数。

随后对照 `fdtget` 命令行语法再次审查，发现原 helper 还把 DTB 文件路径放在选项之前。提交 `350300ca7cc8d570d54e25a3990a47fd33787cb3` 修正为选项在前、DTB 路径居中、节点/属性参数在后，并正确处理 `-t x` 的类型参数。

#### 当前判定与下一步

这是审计器实现错误，不是 DTS 候选或内核驱动失败。两份候选的编译证据仍然有效；语义一致性依旧未验证。

下一轮需重新运行同一 workflow，确认：
1. 脚本能遍历 DTB 节点和读取属性；
2. provider specifier 的 phandle 与参数 cell 被正确解析；
3. 完整节点树和属性比较通过；
4. 两个候选的差异白名单准确，IRQ-name variant 相对 Vendor variant 只有 `interrupt-names`；
5. 两份候选 DTC warnings 和 SHA-256 均保存进 artifact。

若仍出现脚本错误，先用小型合成 DTB 对 helper 做独立单元测试，再跑完整 kernel/DTB 构建工作流，避免浪费 Actions 时间。没有 `SEMANTIC_DTB_AUDIT=PASS` 之前，不将语义审计标记为通过。


### 3.32 Third semantic audit run: NVMEM cell reference format corrected（2026-11-15）

运行记录：GitHub Actions run `43653950234`，job `132628257858`，执行提交 `b2e0b1c6959b3cdb1c9159d6e93b854f15fca41d`。

#### 本轮已通过

- 6.12.81 固定源码获取及 SoC/板级 DTB 源码审查；
- 未修改基线 DTB 构建；
- 发布内核包外层 SHA-256 校验；
- 发布 DTB 提取、反编译；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 编译。

审计器已成功开始解析真实设备树引用。失败于：
`/bus-npu-opp-table:nvmem-cells`，报告 NVMEM cell 节点 `/otp@fe38c000/core-pvtm@2a` 缺少 `#nvmem-cell-cells`。

#### 根因确认

对固定 Ophub commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 `rk356x.dtsi` 进行源码核对：
- `core-pvtm@2a` 是 OTP 节点内部的 NVMEM cell，定义含 `reg = <0x2a 0x2>`，并未定义 `#nvmem-cell-cells`；
- `bus-npu-opp-table` 通过 `nvmem-cells = <&core_pvtm>` 直接引用该 cell；
- 此属性是 cell phandle 列表，不是带 provider 参数 cell 的 clock/reset/interrupt 类 specifier。
因此旧解析器错误地把 NVMEM cell 引用当作 provider + argument-cells 列表。

#### 修复

提交 `2d4536444647d20e4e303983b3c94d8e4edafecc`：
- 将 `nvmem-cells` 从通用 provider-cell 解析表移出；
- 作为直接 cell-phandle 列表解析，映射为目标节点路径；
- 未添加任何默认参数数量，也未扩大 DTS 属性变化白名单。

#### 当前状态

- 候选 DTB 编译：通过；
- 引用语义审计：运行中，仍未通过；
- 设备启动、NPU probe、RKNN 推理：未验证。

下一步重跑同一 workflow。若继续遇到其它 provider 特例，按固定源码 binding/实际 DTS 节点定义逐项核实，不做猜测式通用化。


### 3.33 Fourth semantic audit run: pinctrl-names misclassified as a phandle list（2026-11-15）

运行记录：GitHub Actions run `43654212624`，job `132629065231`，执行提交 `e6ea92a3aa05d6bc26bc8d2bcdba58beff071414`。

#### 已通过

- 固定 Ophub 6.12.81 源码获取；
- SoC/板级 DTS 审查；
- 未修改 baseline DTB 构建；
- 发布内核包 SHA-256 校验、发布 DTB 提取及反编译；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 编译。

#### 失败原因

比较器报告：
`/codec-digital@fe478000:pinctrl-names: unknown phandle 0x64656661`。

`0x64656661` 是字符串 `"defa"` 的字节内容，并非 phandle。原因是旧分类条件将所有 `pinctrl-*` 属性都当作 phandle 列表，错误包含字符串属性 `pinctrl-names`。

#### 修复

提交 `e0bd21564a41ccd27894bdac9e845901379d6557`：
- 只将符合 `pinctrl-[0-9]+` 格式的属性按 phandle 列表处理；
- `pinctrl-names` 回归普通字符串属性比较；
- 不改变属性差异白名单，不忽略任何节点或引用。

#### 状态

候选 DTB 构建通过；语义比较仍未完成。此次失败是比较器对字符串属性的类型误判，不代表 DTS 不一致。下一步重跑 workflow，继续根据真实属性类型逐项修正比较器。


### 3.34 Fifth semantic audit run: Rockchip private single-phandle property（2026-11-15）

运行记录：GitHub Actions run `43655322545`，job `132632452049`，执行提交 `8b0920ce659041f592e4ed1b3449a9bb4a3b89f8`。

#### 本轮已通过

- 固定 Ophub 6.12.81 源码获取；
- SoC/板级 DTS 审查；
- baseline DTB 构建；
- 发布内核包 SHA-256 校验及发布 DTB 提取；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 编译；
- 前几轮发现的 NVMEM、pinctrl 字符串属性误判已不再出现。

#### 失败原因

语义比较器报告：
`/csi2-dphy0:rockchip,hw: '268' -> '269'`。

固定 Ophub commit `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` 的 `rk356x.dtsi` 显示 `rockchip,hw` 是单 phandle 引用，例如 CSI2 DPHY 节点指向 `csi2_dphy_hw`。候选 DTB 新增 phandle 引用后，DTC 可重新分配 phandle 数值；直接比较数字会产生误报。

#### 修复

提交 `c674ae278b6830834b7da6c70b38ed5c1c95c217`：
- 将 `rockchip,hw` 加入单 phandle 属性集合；
- 解析为目标节点路径后比较，而非比较 phandle 整数；
- 不忽略该属性，也不放宽属性变化白名单。

#### 当前状态

两份候选 DTB 构建通过；语义审计仍未通过。当前失败属于比较器对 Rockchip 私有 phandle 属性覆盖不完整。下一步重新运行 workflow；若通过，需继续检查输出的全部允许变化、IRQ-name-only delta、DTC warnings 与 DTB 哈希，之后再判断是否可进入 BSP patch 最小化阶段。


### 3.35 Sixth semantic audit run: memory-region is a phandle list, not a scalar（2026-11-15）

运行记录：GitHub Actions run `43655620433`，job `132633351477`，执行提交 `17aae45af5b3945f025d18d22f97881ab95aa5f9`。

#### 已通过阶段

- 固定 Ophub 6.12.81 源码获取；
- SoC/板级 DTS 审查；
- 未修改 source baseline DTB 构建；
- 发布包外层 SHA-256 校验及发布 DTB 提取；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 均成功编译；
- 前序发现的 NVMEM、pinctrl-names、Rockchip rockchip,hw phandle 编号误判已消除。

#### 本轮失败

比较器报告：
`/display-subsystem:memory-region: expected a single phandle, got 10 11`。

`memory-region` 在该 DTS 中是直接 phandle 列表，可同时引用多个 reserved-memory 区域；不能归入单 phandle 属性。

#### 修复

提交 `07b5571b2a0b2e389d0b096a9e6239a060793db8`：
- 将 `memory-region` 从单 phandle 集合移到直接 phandle 列表集合；
- 对每个 phandle 分别解析目标节点路径；
- 不丢弃列表项，不放宽差异白名单。

#### 额外发现

当前 workflow 的成功分支报告仍引用旧文件名 `rk3566-panther-x2.candidate.decompiled.dts`，而实际产物已拆分为 `vendor-candidate` 与 `irqname-candidate`。该 grep 只影响附加报告内容，不影响 DTB 构建或比较器本身；应在下一次 workflow 清理中改为分别检查两份 decompiled DTS。

当前判定：两份候选编译通过；语义审计尚未完成。下一步继续用真实 DTB 暴露属性 schema 覆盖缺口，但每次修正均需以 DTS 实际结构为依据。


### 3.36 Seventh semantic audit run: devfreq-events is a phandle list（2026-11-15）

运行记录：GitHub Actions run `43655926329`，job `132634305592`，执行提交 `df718d9efebc935cd9f2edcab0b0d0a731d2fd27`。

#### 本轮已通过

- 6.12.81 固定源码获取及 DTS 审查；
- 未修改 source baseline DTB 构建；
- 发布内核包 SHA-256 校验、发布 DTB 提取及反编译；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 编译；
- 之前修复的 NVMEM、pinctrl-names、Rockchip `rockchip,hw`、`memory-region` 误判未再出现。

#### 本轮失败

`/dmc:devfreq-events` 的语义值由 `153 154` 变成 `154 155`。固定 Ophub commit 的 `rk356x.dtsi` 显示：
`devfreq-events = <&dfi>, <&nocp_cpu>;`
这是两个直接 provider phandle 的列表；此属性格式没有在每个 phandle 后附加参数 cells。新增引用引起 phandle 号重排，旧比较器直接比较整数造成误报。

#### 修复

提交 `7e6737101bc1d398d51d8dc5ae3dd891be0a65e7`：
- 将 `devfreq-events` 纳入直接 phandle 列表；
- 每项解析为 provider 节点路径后比较；
- 不忽略引用，不扩大差异白名单。

#### 工作流待清理项

成功分支仍引用过时的单一候选反编译文件名；实际已拆分为 vendor/irqname 两份，应在后续工作流整理中分别报告。
本轮最终语义审计仍未通过；两份候选编译通过。下一轮继续验证完整差异。


### 3.37 Eighth semantic audit run: Rockchip DMC FSP parameter phandles（2026-11-15）

运行记录：GitHub Actions run `43656313247`，job `132635483215`，执行提交 `d108feea19d7e56f22d531c344f2711965cd0e53`。

#### 已通过阶段

- Ophub 固定源码获取、DTS 审查；
- source baseline DTB 编译；
- 发布包外层 SHA-256 校验及发布 DTB 提取；
- Vendor-equivalent 与 IRQ-name 两份候选 DTB 编译；
- 之前修复的 NVMEM、pinctrl、Rockchip hw、memory-region、devfreq-events 属性误判已消除。

#### 本轮失败

`/dmc-fsp:ddr3_params` 的值从 `156` 变为 `157`。固定源码 `rk356x.dtsi` 中 `dmc_fsp` 节点的 `ddr3_params`、`ddr4_params`、`lpddr3_params`、`lpddr4_params`、`lpddr4x_params` 均为单 phandle 参数表引用。DTC 新增引用后 phandle 编号重排，旧比较器直接比较数值导致误报。

#### 修复

提交 `24ae91695d5caed230f952cb8b2ce9a1043fc3a0`：
- 将五个 DMC FSP 参数引用属性纳入单 phandle 语义解析；
- 比较引用目标节点路径，不比较 phandle 整数；
- 保持 fail-closed，未扩大 DTS 差异白名单。

#### 重要说明

本次 workflow 的 step 7 标记 failure，但其失败点已明确发生在语义比较阶段。baseline/published DTB 与两个候选 DTB 均已成功构建。Artifact：`14138231604`，包含本轮报告和反编译文件。

此外，成功分支仍有旧的单候选 DTS 文件名引用，需修复为 vendor/irqname 两份文件。

下一步不应只继续追加属性名单。需在审计器中维护显式的属性类型表与未知 phandle-like 属性检测，随后增加小型合成 DTB 测试，覆盖单 phandle、phandle list、带参数 specifier、普通字符串和整数数组。通过单元测试后再跑完整 DTB workflow。
