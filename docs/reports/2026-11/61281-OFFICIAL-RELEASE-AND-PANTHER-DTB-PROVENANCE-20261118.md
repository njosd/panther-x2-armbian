# 6.12.81 官方发布包与 Panther X2 DTB 来源核查（2026-11-18）

## 结论摘要

- 已从 `ophub/kernel` 的 `kernel_rk35xx` Release 元数据确认官方资产 `6.12.81.tar.gz`，大小 141,437,450 bytes，SHA256：
  `72c1c331a5da0853f80563aa05e9285749da6187bad0276878b386d4913b9b5b`。
- 同一 Release 另有 `deb-6.12.81.tar.gz`（92,782,935 bytes，SHA256 `e07d967c2a4d54aee3e910db414c100e01843db2a5b5e49e44d13942aec5e6bc`）及手动上传的 `6.12.81-rk35xx-flippy-2611b.tar.gz`。三者不是同一资产，不应混用。
- 官方编译工作流 `.github/workflows/compile-rockchip-rk35xx-kernel.yml` 的参数支持 `kernel_package=all|dtbs`，默认 `all`。官方编译说明明确：`all` 会构建 Image、modules、dtbs；`dtbs` 仅生成 DTB。由此可确认官方完整内核包的构建流程包含 DTB 构建，但尚未直接检查下载包内部清单。
- 已定位候选源码提交 `ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`，提交时间 2026-11-13 08:01:39 UTC；官方资产在 2026-11-13 11:14:36 UTC 创建。时间吻合，但由于尚未取得对应 GitHub Actions 构建日志/输入快照，不能将该提交认定为已证实的构建源码锁定版本。
- 从该源码提交读取到 `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts`，内容包含 `model = "Panther X2"`、`compatible = "panther,x2", "rockchip,rk3566"`、GMAC1/RTL8211F PHY 节点、复位时序和 NPU 电源 regulator 定义。

## TF 卡现场证据（此前只读取得）

- TF 卡正式 DTB：`/dtb/rockchip/rk3566-panther-x2.dtb`，167,306 bytes，U-Boot CRC32 `6330e83a`。
- 同目录候选 DTB：`/dtb/rockchip/rk3566-panther-x2.candidate.dtb`，167,306 bytes，U-Boot CRC32 `ab4ef404`。
- 两个文件长度相同但 CRC32 不同，说明二进制不同。
- 当前 `armbianEnv.txt` 指定正式 DTB `rockchip/rk3566-panther-x2.dtb`；实际 boot.scr 解码及 UART 启动记录确认启动脚本从 TF 卡加载该路径。
- 用户明确说明仅按指导更换过 U-Boot，没有自行替换其他文件。U-Boot 写入原始扇区本身不能证明 `/boot/dtb` 文件被替换；现阶段不得将 DTB 变更归因于用户。

## 尚未完成的关键验证

1. 当前 GitHub 连接可以读取 Release 元数据和文本文件，但不能直接下载 Release 二进制资产；因此尚未提取 `6.12.81.tar.gz` 或 `deb-6.12.81.tar.gz` 内的 DTB。
2. 尚未取得官方构建 run 的输入参数和完整日志，故源码提交 `661b2d8...` 目前是时间吻合的候选，不是已证实的构建锁定 SHA。
3. 尚未取得 TF 卡正式 DTB 的 SHA256；现场目前只有 U-Boot CRC32。
4. 因此尚不能宣称 TF 卡正式 DTB 与官方 6.12.81 发布包完全一致，也不能判定 candidate DTB 的来源。

## 下一步

优先获取官方发布资产中的 DTB 或官方构建产物清单，并取得 TF 卡正式 DTB 的 SHA256 后进行二进制比对。若无法取得二进制，则继续追踪官方 workflow run 的 inputs、job logs 和产物清单；源码 DTS 只能作为配置内容对照，不能替代编译后 DTB 的哈希比对。

## 操作边界

本轮仅查询公开 GitHub 元数据、工作流、编译说明及源码；没有对 Panther X2、TF 卡或 eMMC 执行任何写入、安装或配置修改。
