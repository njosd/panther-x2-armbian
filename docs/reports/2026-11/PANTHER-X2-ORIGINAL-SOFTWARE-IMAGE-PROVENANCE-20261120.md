# Panther X2 原始软件安装版本溯源（阶段一）

- 日期：2026-11-20
- 设备：Panther X2 / RK3566
- 研究目标：从用户保存的最早安装资料、升级前归档、软件包版本和 SHA256 中识别设备最初到手时的软件版本及其来源，为重新刷写原始版本、验证硬件网络能力建立可信基线。
- 状态：**初步证据已整理；最初镜像文件/版本仍未最终识别。**
- 操作边界：只分析历史资料和哈希；不执行设备写入，不提供未经确认的刷写步骤。

## 1. 研究方向调整

用户决定暂停此前 GMAC 根因研究线，改为回到机器最初到手时的软件安装版本。用户陈述：机器最初版本是后来逐步运行 `armbian-update` 升级到 6.1.116 的起点；计划重新刷写该版本，验证硬件网络是否可正常工作。

本研究不预设最初内核版本，也不将 6.1.116、当前 eMMC 启动文件或后续 U-Boot 替换状态误当作最初原始镜像。

## 2. 当前可访问历史资料提供的事实

### 2.1 最初系统发行版/根文件系统线索

历史实机采集（2026-11-18）记录：
- `/etc/os-release`：`PRETTY_NAME="Armbian 24.8.4 jammy"`
- Ubuntu 22.04.5 LTS / Jammy
- `/etc/armbian-release`：`BOARD=odroidn2`、`BOARD_NAME="RK-Panther-X2"`、`BOARDFAMILY=meson-g12b`、`LINUXFAMILY=meson64`、`IMAGE_TYPE=rebuild`、`VENDOR="Armbian-unofficial"`
- 该时点运行内核：`6.1.116-ophub`
- 6.1.116 内核构建标记：`#1 SMP Sun Nov 10 08:21:17 EST 2024`
- `/etc/armbian-release` 中 Armbian build metadata 为 `VERSION=26.11.0`、`REVISION=26.11.0`、`BUILD_REPOSITORY_COMMIT=d2c928c`。这些字段与 OS release 不同层，不能把它们当作原始镜像版本号。

**边界：** 24.8.4 Jammy 是目前保留在系统上的发行版识别信息；它不能单独证明最初安装镜像的确切发布日期、内核版本、U-Boot/SPL 身份或镜像下载 URL。

### 2.2 历史内核版本节点

用户此前确认 `/ddbr/backup/` 中保留过：
- `6.1.65`
- `6.1.79`
- `6.1.112`

当前/曾运行的基准为 `6.1.116-ophub`。旧对话中的目录时间记录分别为 2024-02-27、2024-10-18、2024-11-11（对应 6.1.65、6.1.79、6.1.112 的备份记录）。

这些是升级历史的重要版本节点，但仅凭备份存在与目录时间，**不能证明 6.1.65 就是机器最初安装时的版本**。需要读取用户找到的最早安装资料，或检查升级前 `/boot` 归档中的文件名、内核版本、DTB 和哈希。

### 2.3 升级前 boot 归档

历史归档清单中存在：
- 路径：`Panther-X2-Backup/kernel-backup-6.1.116/boot-before-6.1.116.tar.gz`
- 大小：63,468,744 bytes
- SHA256：`cec84c1cba6a34034608fb5180ad69e425d0953c2a11dadcadec9302d4f874c1`

该文件很可能是识别升级到 6.1.116 之前启动目录状态的高价值证据，但尚未直接读取归档目录或内部文件内容。不得只凭文件名断言它一定包含最初系统的 kernel；它也可能包含升级前某个中间版本。

另有 6.1.116 专用备份：
- `boot-6.1.116-ophub.tar.gz`，SHA256 `68e991e78c19ecaf96d766a058b9b1149a57efcef5a729fd971edf47808ed6d2`
- `dtb-rockchip-6.1.116-ophub.tar.gz`，SHA256 `2c60c79d67fee948689fa4c364b5d88bf3bf...`（需以原始完整清单为准；不要从截断内容重建哈希）
- `modules-6.1.116-ophub.tar.gz`，SHA256 `d8056b6abe03cdee392e56e4d5cf20ccfd5d1f577d579fbf29923cfba6a1b529`
- `sha256sums` 文件 SHA256 `502fa131600f59d2e28b78c783008f970676b56834ab022349cb5368e91b9678`

6.1.116 安装记录表明这些包来自 `/ddbr/backup/6.1.116`，并曾被用于把内核、Panther X2 DTB 和 modules 安装到 eMMC root/boot 分区。这是后续 6.1.116 恢复操作记录，不是原始镜像证明。

### 2.4 旧系统启动配置指纹

历史归档中保留了 2026-11-12 的启动配置文件：
- Panther DTB：SHA256 `11712689a81387a954d5e4e262cccc890bc8c409df7560b93c09f91b1423551d`
- `boot.cmd`：`4896dde2b99bebbb34b2ed2f837f30fa1a5b3ad14b80dd2da391effa94d37d0a`
- `armbianEnv.txt`：`4571b474cc7ee78d6612fa4c364b5d88bf3ec39879a5a512332e2ee1ae940e97`
- `boot.scr`：`0cda8b456b409213ed2b689838b3b19c9adf40d141feaf251b5161e18e36311a`

注意这些是 2026-11-12 的备份指纹，不可自动等同于机器最初到手时的文件版本。

## 3. 原始来源目前尚缺的证据

截至本阶段，可访问资料尚未给出：
1. 最初镜像的确切文件名和下载 URL；
2. 最初镜像 SHA256；
3. 最初运行内核版本及其 `Image`、DTB、modules 的对应 SHA256；
4. 最初 SPL/idbloader 与 U-Boot proper 的确切版本、构建日期和哈希；
5. `armbian-update` 从最初版本逐步升级到 6.1.116 的逐次命令/日志；
6. `boot-before-6.1.116.tar.gz` 内部实际包含的文件及版本。

既有历史记录曾指出原系统来自 Ophub，涉及 `ophub/kernel`、`KERNEL_TAGS='6.1.y'`、`KERNEL_VERSION='6.1.116'`、`FDTFILE='rk3566-panther-x2.dtb'`，包日期显示 2023-12-07；这些信息更能说明 Ophub 内核包体系，不足以单独锁定最初镜像或 bootloader 来源。

## 4. 下一步最小只读验证

优先检查用户已有的升级前归档，不写入、不解压覆盖任何目录：

```bash
cd ~/Desktop/Panther-X2-Backup/kernel-backup-6.1.116 || exit 1
shasum -a 256 boot-before-6.1.116.tar.gz
tar -tzf boot-before-6.1.116.tar.gz | head -100
```

先用输出识别归档内部路径和文件名。之后只对确切存在的文件执行 `tar -xOzf` 读取文本元数据，或将归档目录列表贴回分析；不需要先完整解压，不需要重刷设备，也不需要重复计算其他已经归档的哈希。

同时，用户找到的“最初到手安装版本”历史文档应作为主要依据。需要其原始文件名、版本字段、文件 SHA256、下载链接或安装日志，才能把最初版本从 6.1.65/79/112 等历史节点中准确区分出来。

## 5. 原始版本重刷前的判定门槛

在确认具体镜像之前不刷写。待识别后，至少核对：
- 镜像文件来源、文件名、SHA256；
- 镜像目标设备/板型是否与 Panther X2 / RK3566 相符；
- 镜像是否包含 SPL、U-Boot、DTB、kernel、rootfs，或需分开安装；
- 是否会覆盖 eMMC user area / boot partitions / TF；
- 与现有 eMMC user area、boot0、boot1 只读备份的关系。

测试应区分“原始软件镜像整套启动链”与“原始 rootfs + 后续替换的 SPL/U-Boot”两种情况。只有启动链和内核来源都确认后，网络结果才可作为原始版本硬件回归结论。

## 6. 本阶段结论

- **已确认：** 当前保留的系统身份包含 Armbian 24.8.4 Jammy；曾运行 6.1.116-ophub；历史目录中有 6.1.65、6.1.79、6.1.112 版本备份；有一份 SHA256 已记录的升级前 boot 归档。
- **高价值待查：** `boot-before-6.1.116.tar.gz` 和用户新找到的最初安装历史文档。
- **未确认：** 最初安装镜像版本、原始内核版本、原始 U-Boot/SPL、下载来源及 SHA256。
- **操作状态：** 只读研究；没有刷写或修改设备。
