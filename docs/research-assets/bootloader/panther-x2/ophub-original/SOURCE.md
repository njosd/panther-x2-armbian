# Panther X2 Ophub 原版 U-Boot 研究资产

本目录归档 Panther X2 原版 U-Boot 启动二进制及其来源记录，供启动链分析、FIT/SPL 静态审查和后续 TF Boot Probe 复用。

## 已归档文件与身份核验

| 文件 | 字节数 | 本仓库 Git blob SHA1 | Ophub 来源 Git blob SHA1 | 结果 |
|---|---:|---|---|---|
| `idbloader.img` | 305152 | `d22b624fc90c46e656baf98894bee182316e692e` | `d22b624fc90c46e656baf98894bee182316e692e` | 一致 |
| `u-boot.itb` | 1431552 | `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c` | `04cd10bddd4e823d2ea495ee95b264cb2bce1f4c` | 一致 |

核验依据：本仓库 Git tree 的 blob SHA 和文件大小，与 Ophub 来源仓库对应提交中的记录一致。Git blob SHA1 对应文件内容（含 Git blob 头部）的哈希，可用于确认归档对象与来源对象相同。

**SHA256 尚未计算。** 当前 GitHub 文件读取接口未能返回完整的 `u-boot.itb` 二进制内容，因此本次不伪造 SHA256；后续在可取得原始字节的环境中补充 `SHA256SUMS`。

## 公开来源

- 仓库：`ophub/u-boot`
- 已核对仓库提交：`6e70f41585f15c43f45fcae609adec1865e83eb5`
- 原始路径：`u-boot/rockchip/panther-x2/idbloader.img`
- 原始路径：`u-boot/rockchip/panther-x2/u-boot.itb`

## 文件身份与安全约定

- 保留公开来源的原始字节，不在归档时修改、修补或重新打包。
- 本目录中的文件属于研究基线，不等于已批准写入 TF 或任何设备。
- 所有实机实验均遵守项目约束：绝不向 eMMC 写入；仅在明确确认目标设备为专用 TF 后才允许写卡。
- 不将 JP-TvBox 版本或实验构建混入本目录；它们应使用独立目录并明确标识版本来源。
