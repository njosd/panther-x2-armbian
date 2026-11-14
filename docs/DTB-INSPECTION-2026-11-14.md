# 6.18.63 内核包检查结果与 DTB 核验状态

检查日期：2026-11-14
工作流运行：[#43526258367](https://github.com/njosd/panther-x2-armbian/actions/runs/43526258367)
检查 Artifact：`ophub-kernel-6.18.63-driver-inspection`（artifact id: 14085526031）

## 1. 已完成并有产物支持的检查

- 外层发布资产 `6.18.63.tar.gz` 的 SHA-256 与仓库锁定值一致：
  `47e3f46636594cbf212474a13bac97e1310c3ee51007dee3fa20f93d8659f1ca`。
- 检查报告记录 6 个内部归档均通过 SHA-256 校验：boot、dtb-allwinner、dtb-amlogic、dtb-rockchip、header、modules。
- 内核映像识别为 ARM64 little-endian Linux Image，4K pages。
- 内核包文件清单中存在 `rk3566-panther-x2.dtb`。
- 报告提取的内核配置包含：
  - `CONFIG_ARM64=y`
  - `CONFIG_DWMAC_ROCKCHIP=y`
  - `CONFIG_REALTEK_PHY=y`
  - `CONFIG_MMC_DW_ROCKCHIP=y`
  - `CONFIG_USB_DWC3=y`
- 这些配置为第一版启动、GMAC/PHY、Rockchip MMC 和 USB 提供了积极的软件证据。

## 2. 不能据此宣称已验证的事项

此前 run #43526258367 的 inspection artifact 未包含 Panther X2 DTB 原始二进制；随后 run [#43543451274](https://github.com/njosd/panther-x2-armbian/actions/runs/43543451274) 已补充上传 DTB、反编译 DTS 和 SHA-256。因此本节以下旧记录应以新 run 为准：

- 目标 DTB 的独立 SHA-256；
- DTB 反编译后的设备树节点审查；
- 与项目选定 DTS 源码快照逐项比较；
- GMAC、PHY 地址/模式、时钟、复位、供电及 eMMC 节点的一致性确认。

此前记录的 DTS 源码参考 Blob SHA 为 `52cbb88552dcae7d15a18682c7a77ec0888dbdc3`。该来源记录不等于已证明 6.18.63 包内 DTB 就由该源码构建。

另外，`CONFIG_ROCKCHIP_RKNPU` 在本次报告中为 `NOT_RECORDED`，不能判定 NPU 驱动已启用或未启用；第一版不以 NPU 为验收条件。

## 3. 后续 run #43543451274 的补充结果\n\n- DTB 已从 Rockchip DTB 包提取，SHA-256：`5d2e5ff87df7a4e4e0d199efa8db24fbf8ef5143b5ba39f7b15cc50e1352df82`。\n- `dtc` 反编译成功，警告文件为空。\n- Panther X2 板型、GMAC1、SDHCI/eMMC、SDMMC/TF、USB 等关键节点与固定 Ophub DTS 快照高度吻合，但尚未完成全量属性 diff 和精确源码—二进制 provenance 证明。\n- 模块归档含 `rockchip-rga.ko`、`rockchip-vdec.ko`；RGA/VDEC 静态存在。未发现 RKNPU 驱动模块，也未在反编译 DTB 中发现 NPU 设备节点。DTB 中的 `vdd_npu` regulator/QoS 信息不代表 NPU 驱动已启用。\n- 旧报告中的 `CONFIG_ROCKCHIP_RGA`、`CONFIG_ROCKCHIP_VDEC` 等符号名称不准确；检查工作流已在 commit `1ce47d772e26becadab4b773e32150d8a054a52c` 修正符号并计划上传完整 `.config`，待下一次手动运行验证。\n\n## 4. 当前判定

| 项目 | 状态 |
|---|---|
| 外层内核包 SHA-256 | 已验证 |
| 6 个内部归档 SHA-256 | 已验证 |
| ARM64 内核映像 | 已确认存在 |
| Panther X2 DTB 文件名 | 已确认存在 |
| GMAC / Realtek PHY / Rockchip MMC 配置 | 已确认配置项 |
| DTB 二进制哈希与反编译审查 | 待完成 |
| DTB 与 DTS 源码对应关系 | 未验证 |
| Panther X2 实机启动、DHCP、SSH | 未验证 |
| NPU/RKNN | 未验证，非第一版阻塞项 |

## 5. 下一步（保持最小范围）

1. 获取 6.18.63 发布包中的原始 `rk3566-panther-x2.dtb`。
2. 计算 DTB SHA-256，并用 dtc 反编译。
3. 只核对第一版必要节点：SoC/内存基础、GMAC1、PHY、时钟/复位/供电、MMC/eMMC。
4. 若与选定 DTS 源码存在差异，先判断是正常编译差异、上游改动还是板级差异；不立即制作补丁。
5. 完成上述静态核对后，转入固定依赖和手动 TF 卡镜像构建。

不在本阶段安装软件、修改 Panther X2、写入 eMMC 或启动镜像构建。
