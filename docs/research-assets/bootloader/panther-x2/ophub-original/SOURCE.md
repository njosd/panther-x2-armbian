# Panther X2 Ophub 原版 U-Boot 研究资产

本目录用于归档 Panther X2 原版 U-Boot 启动二进制及其来源记录，供启动链分析、FIT/SPL 静态审查和后续 TF Boot Probe 复用。

## 待上传文件

请将以下两个原始文件直接上传到本目录：

- `idbloader.img`
- `u-boot.itb`

上传后补充 SHA256SUMS，并核对文件大小及哈希。

## 已知公开来源

- 仓库：`ophub/u-boot`
- 已核对仓库提交：`6e70f41585f15c43f45fcae609adec1865e83eb5`
- 原始路径：`u-boot/rockchip/panther-x2/idbloader.img`
- 原始路径：`u-boot/rockchip/panther-x2/u-boot.itb`
- 已知 Git blob SHA1：
  - `idbloader.img`: `d22b624fc90c46e656baf98894bee182316e692e`
  - `u-boot.itb`: `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c`

## 文件身份与安全约定

- 必须保留公开来源的原始字节，不在归档时修改、修补或重新打包。
- 上传后记录实际字节数、SHA256，并与公开来源文件核对。
- 本目录中的文件属于研究基线，不等于已批准写入 TF 或任何设备。
- 所有实机实验均遵守项目约束：绝不向 eMMC 写入；仅在明确确认目标设备为专用 TF 后才允许写卡。
- 不将 JP-TvBox 版本或实验构建混入本目录；它们应使用独立目录并明确标识版本来源。
