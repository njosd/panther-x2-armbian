# Panther X2 JP-TvBox U-Boot 研究资产

本目录独立归档 JP-TvBox 候选启动二进制。它们不得与 Panther X2 Ophub 原版基线混用。

## 已归档文件

| 文件 | 字节数 | 本仓库 Git blob SHA1 |
|---|---:|---|
| `idbloader.img` | 309248 | `4bf6c334d4bf16b83c4317286907a361de8be489` |
| `u-boot.itb` | 1464832 | `2e453265e2e87e0ebd41897131fa6447dff4c0d1` |

以上大小及 idbloader Git blob SHA1 与仓库既有的 2026-11-17 二进制静态对照报告相符。U-Boot ITB 的 Git blob SHA1 是本次从仓库 Git tree 读取的当前对象指纹。

## 已知静态指纹（idbloader）

依据既有报告 `docs/reports/2026-11/PANTHER-X2-UBOOT-CANDIDATE-RESEARCH-20261117.md`：

- SPL：`U-Boot SPL 2017.09-armbian (Nov 12 2023 - 15:05:14)`
- DDR loader：`DDR Version V1.10 20210810`
- 内嵌 FDT：Radxa ROCK 3C（`radxa,rock3c / rockchip,rk3566`）
- 内嵌 FDT 偏移：283840（0x454c）
- 内嵌 FDT totalsize：23946（0x5d8a）

## 来源与证据边界

- 该套文件在本项目中称为“JP-TvBox 候选版本”，不是 Panther X2 原厂基线。
- 当前目录上传对象已固定归档；本次尚未取得足以独立确认其上游构建 commit、发布页或原始下载 URL 的来源链。后续找到来源后再补充，不以文件名推断来源。
- Git blob SHA1 用于确认仓库对象身份；SHA256 尚待在可取得完整二进制字节的环境中计算。
- 文件归档不代表已批准刷写或实机使用。所有测试继续遵守：绝不向 eMMC 写入；只允许在明确确认的专用 TF 卡上进行受控实验。
