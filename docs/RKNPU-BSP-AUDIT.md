# RK3566 / Panther X2 RKNPU 驱动来源审计

更新日期：2026-11-14

## 1. 当前 6.18.63 包的直接证据

检查来源：Actions run [43543451274](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274)，artifact id `14093500129`。

- modules 归档完整文件清单中没有 `rknpu.ko` 或其他可识别的 Rockchip RKNPU 模块。
- DTB 反编译文本中没有 `npu@fde40000`、`rknpu` 或 NPU IOMMU 设备节点。
- DTB 中存在 PMIC `vdd_npu` 电源轨、`qos_npu` QoS 节点及 NPU pin group 相关信息。这些只是板级/SoC资源描述，不能证明 NPU 驱动已启用。
- DTB 含有 `__symbols__` 节点，并导出 `cru`、`scmi_clk`、`power`、`qos_npu`、`vdd_npu` 等符号。这使标准 phandle overlay 在技术上有进一步验证的基础，但不代表现有 overlay 已能直接应用。

**结论：当前 Ophub 6.18.63 Panther X2 DTB 和模块包没有形成可用 RKNPU 的完整证据链。**

## 2. 找到的独立驱动候选

候选仓库：[w568w/rknpu-module](https://github.com/w568w/rknpu-module)

固定审计快照：commit `a8792fe6b633f90cf2c6808267cac327537ab4cf`

相关文件：
- `src/rknpu_drv.c`：RKNPU DRM 驱动主体
- `Kbuild`：独立模块构建定义
- `dkms.conf`：DKMS 自动重建配置
- `dts/rk3566-rknpu-overlay.dts`：RK3566 NPU 设备树 overlay
- `PLAN.md`：移植工作记录和已知兼容性问题

该仓库 README 声称驱动来自 `rockchip-linux/kernel`，并记录在 Orange Pi 3B v1.1（RK3566）上使用 6.19.3 / 7.0.0-rc7 测试。**这不是 Panther X2 实机验证，也不是 Ophub 6.18.63 兼容性证明。**

### 2.1 迁移成本与风险

该候选并非简单复制一个 `.ko` 即可：
- README 的实测内核为 6.19.x / 7.0.0-rc7；6.18.63 尚未验证。
- PLAN 记录了 DRM GEM、IOMMU、devfreq 及 Rockchip 私有头文件/API 兼容工作。
- 候选方案采用 out-of-tree 模块，具备独立维护、DKMS 重建的结构优势；但每次 Ophub 内核更新仍须重新编译和回归验证。
- 仓库记录 RK3566 IOMMU v2 页表地址高于 4GB 的已知问题，当前方案选择禁用 NPU IOMMU、使用 non-IOMMU 模式。该 workaround 对 Panther X2 是否稳定尚未验证。
- overlay 提供 NPU 节点、供电域、OPP 表和禁用状态的 NPU IOMMU 节点。Panther X2 的 DTB 已包含 overlay 所需的多个符号，但仍需实际编译、合并/应用检查，不能直接部署。

### 2.2 与 Panther X2 的适配判断

积极因素：
- SoC 同为 RK3566。
- Panther X2 DTB 已包含 `vdd_npu` regulator 和 `qos_npu`。
- Panther X2 DTB 存在 `__symbols__`，overlay phandle 方式值得优先验证。
- 驱动代码包含 `rockchip,rk3568-rknpu` / `rockchip,rknpu` 等兼容字符串。

未解决因素：
- Panther X2 DTB 缺少 NPU 设备节点及 NPU IOMMU 节点。
- 设备树中的 SCMI 时钟、CRU 时钟、power domain、IRQ、OPP/电压与实际 Panther X2 硬件的对应关系仍需核实。
- 驱动在 6.18.63 的编译兼容性未知。
- non-IOMMU 模式的性能、稳定性和内存行为未知。
- RKNN 用户态 runtime 与驱动版本匹配关系尚未验证。

## 3. 与 Immich 的实际价值

即使 RKNPU 最终成功，也不能直接推断 Immich 会自动使用它。Immich 的机器学习推理需要兼容的执行后端、模型格式和运行时；RKNN 是独立适配工作，不是启用内核模块后即可自动加速。

项目的主线策略仍然成立：
1. 先完成可稳定启动、联网、SSH 管理的 Armbian Server。
2. RGA/VDEC 属于独立的图像/视频加速验证方向。
3. RKNPU/RKNN 作为后续可选研究，不作为首版系统或 Immich 常驻服务的阻塞条件。
4. 首次大批量导入和机器学习任务仍可临时调用局域网其他机器算力。

## 4. 下一步最小验证计划（仅静态/CI，不操作 9.6）

1. 固定候选驱动仓库 commit 和文件 SHA，继续检查其源码依赖与 GPL 许可来源。
2. 在 GitHub Actions 的临时 ARM64 交叉编译环境中，以 Ophub 6.18.63 对应 headers/config 为目标，尝试编译候选模块；只产出 CI artifact，不安装、不加载。
3. 单独编译 RK3566 overlay，并对 Panther X2 DTB 做离线 overlay 合并/反编译检查，核实符号、phandle、IRQ、时钟、power domain 和 regulator 引用。
4. 只有静态检查和 CI 编译通过后，才讨论是否在独立 TF 启动环境做可回滚实机验证；不触碰 eMMC 和现有 9.6 系统。

## 5. 状态

| 项目 | 状态 |
|---|---|
| 当前 6.18.63 包含 RKNPU 模块 | 未发现 |
| 当前 Panther X2 DTB 含 NPU 设备节点 | 未发现 |
| Panther X2 DTB 有 NPU 电源/QoS相关描述 | 已确认 |
| Panther X2 DTB 含 overlay 符号表 | 已确认 |
| 独立 RK3566 RKNPU 模块候选 | 已找到 |
| 候选在 RK3566 Orange Pi 3B 的测试记录 | 上游仓库自述，未独立复核 |
| 候选兼容 Ophub 6.18.63 | 未验证 |
| 候选适配 Panther X2 | 未验证 |
| Immich 能直接调用 RKNN | 未验证 |
| 安装/加载/修改 Panther X2 | 未进行 |
