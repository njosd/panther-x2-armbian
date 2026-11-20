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


## 7. 用户确认找到最初刷机包（2026-11-20）

用户明确确认手中保存有其称为“原始刷机包”的文件：

```text
Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz
```

### 7.1 文件名可直接支持的信息

按 Armbian 常见镜像命名字段拆解，文件名声明：
- 发行版版本标识：`24.2.0`
- 平台/设备标识：`rockchip_panther-x2`
- 用户空间发行版：`jammy`
- 内核版本：`6.1.65`
- 镜像形态：`server`
- 构建/版本标识：`2023.1`
- 文件为 gzip 压缩包（`.gz`）

这与用户此前提及的 `/ddbr/backup/6.1.65` 历史节点吻合，明显比此前仅根据版本备份目录推断最初版本更有力。

### 7.2 证据边界

- 用户明确称该包是原始刷机包；这是重要的一手来源陈述。
- 目前尚未取得该文件本体、SHA256、压缩后镜像元数据或内部文件清单。
- 文件名本身不能证明镜像内容未被修改，也不能单独确认镜像内 SPL/U-Boot、DTB、内核的实际版本和哈希。
- 公开网页对完整文件名的精确检索未找到可核验的发布页/校验和；当前不宣称已确定官方下载地址或上游发布来源。

### 7.3 下一步只读身份确认

在 iMac 上对用户现存文件执行以下只读检查即可：
```bash
shasum -a 256 "/完整路径/Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz"
gzip -l "/完整路径/Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz"
file "/完整路径/Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz"
```

如用户愿意，也可直接将原始压缩包上传到当前对话供离线检查；不需要解压覆盖或写入任何设备。先保留原始文件，不修改文件名和内容。

取得哈希和镜像元数据后，再对镜像内的分区表、bootloader 区域、kernel/DTB/rootfs 进行静态分析，与 6.1.116 归档、11 月 18/19 日实测启动链逐层比对。重刷仍须等身份核验、目标介质确认及风险审查完成后另行决定。


## 8. 原始刷机包本体元数据核验（用户 iMac 输出，2026-11-20）

用户在外置 U 盘 `/Volumes/Untitled/黑豹x2/` 找到并读取原始包：

```text
Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz
```

### 8.1 用户实测文件信息

- 文件大小：851 MiB（`ls -lh` 显示）
- gzip 压缩大小：892,499,345 bytes
- gzip 内部记录的未压缩大小：2,969,567,232 bytes（约 2.97 GB）
- gzip 内部原始文件名：`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img`
- gzip header 时间：2023-12-07 05:18:54（Unix）
- 文件系统时间显示：2024-02-04（仅是当前文件元数据，不等同于镜像构建日期）
- SHA256（压缩包本体）：
  `0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`
- `gzip -t`：通过，压缩流完整性检查通过。

### 8.2 重要判断

本体 gzip header 把原始镜像名明确记录为 `...server_2023.12.07.img`，比外部文件名末尾的 `2023.1` 更精确。它强烈支持这是一份 2023-12-07 构建的 Armbian 24.2.0 Panther X2 Jammy 6.1.65 server 镜像。

压缩包 SHA256 是当前用户持有文件的可靠身份指纹；但在找到上游官方/发布者 checksum 或同一原始文件的可信历史哈希之前，不能声称其已与官方发布校验值匹配。

gzip 完整性通过仅证明 gzip 数据流可完整解压，不证明镜像内容与发布者原件一致，也不证明镜像适用于当前设备所有硬件修订。

### 8.3 下一步只读分析

下一步从 gzip 流开头读取 MBR/GPT 头、分区起始 LBA 和镜像前部 bootloader 区域元数据；使用管道和内存读取，不生成 2.97 GB 解压文件，不写入 U 盘或任何设备。然后再定位镜像中的 SPL/IDB、U-Boot、DTB、kernel 和 rootfs 版本指纹。


## 9. 原始刷机包配套 MiniLoaderAll.bin 核验（用户 iMac 输出，2026-11-20）

用户补充确认：原始刷机流程当时要求先将 U 盘中的 `MiniLoaderAll.bin` 刷入机器。该操作顺序是用户的一手回忆，说明此文件属于原始刷机流程的前置 Loader，不应视为普通附件。

文件路径：`/Volumes/Untitled/黑豹x2/MiniLoaderAll.bin`

### 9.1 文件实测指纹

- 文件大小：约 442 KiB（`ls -lh`）
- SHA256：`ab62386a8868b01516b560451082fbdb6342b16e850a0622577b538dd2b10d39`
- `file` 识别为通用 data；不是可由系统 `file` 命令直接识别的普通 ELF。
- 文件头前四字节 ASCII：`LDR `
- 文件头含有可见字段/标记：`rk3566_ddr_1056MHz`
- 另含：`rk356x_usbplug_v1`
- DDR 字符串：`DDR Version V1.09 20210630`

### 9.2 当前可支持的解释

文件头及内部字符串与 Rockchip Loader 镜像相符，至少表明该文件包含面向 RK3566 的 DDR 初始化配置（1056 MHz 标记）及 USB plug/download 阶段相关组件。结合用户确认的刷机顺序，它应作为原始刷机链中的前置 Loader 组件进行追踪。

但当前字符串扫描不能完整解析镜像内部结构，也不能据此断言它就是当前机器运行的 U-Boot proper。Loader/DDR 初始化、USB plug 阶段、后续 U-Boot proper 是需要区分的启动阶段。

### 9.3 与当前 eMMC 启动链的关系（待验证）

既有实机记录显示，2026-11-19 用户曾将 eMMC user area LBA64 的 IDB 替换为 JP-TvBox 的 idbloader（DDR V1.10，构建日期 2023-11-12）；之后启动日志显示 JP SPL，再从 TF 加载 JP U-Boot proper。因而不能把本文件中的 DDR V1.09 字符串直接当成当前 eMMC LBA64 的版本。

下一步应先解析 `MiniLoaderAll.bin` 内部镜像结构及其组件/版本，再与已保存的 eMMC LBA64 原始备份及当前已知 JP IDB 内容做组件级比较。不得将整个 MiniLoaderAll.bin 与 LBA64 单一区域直接做整文件哈希比较，也不得为此重复备份 eMMC。

### 9.4 状态

- 已验证：文件存在；大小、SHA256、LDR 文件头、RK3566 DDR/USB plug 字符串及 DDR V1.09 版本字符串均来自用户本机输出。
- 用户确认：原始刷机流程要求先刷入此文件。
- 尚未验证：内部各组件的精确偏移/长度、是否与原始 eMMC IDB 内容一致、是否包含/对应 U-Boot proper、是否与原始 Armbian 6.1.65 镜像内启动组件配套。


## 10. U 盘内三份 Rockchip Loader 文件的对比（用户 iMac 输出，2026-11-20）

用户在整个外置 U 盘 `/Volumes/Untitled` 递归查找后，找到三份文件。前两份初始固定目录检查未找到，是因为文件实际位于子目录 `黑豹x2/armbian/bootloader/`。

| 文件 | 路径 | 大小 | SHA256 | DDR 字符串 | Boot1 构建日期字符串 |
|---|---|---:|---|---|---|
| `MiniLoaderAll.bin` | `黑豹x2/MiniLoaderAll.bin` | 442 KiB | `ab62386a8868b01516b560451082fbdb6342b16e850a0622577b538dd2b10d39` | `DDR Version V1.09 20210630` | `Jun 18 2021` |
| `rk356x-MiniLoaderAll.bin` | `黑豹x2/armbian/bootloader/rk356x-MiniLoaderAll.bin` | 444 KiB | `1cdd418032195210f191445ed96e2da5ea83d2cfe880c912ebec635839d76542` | `DDR Version V1.10 20210810` | `Sep 13 2021` |
| `rk356x_spl_loader_ddr1056_v1.10.111.bin` | `黑豹x2/armbian/bootloader/rk356x_spl_loader_ddr1056_v1.10.111.bin` | 442 KiB | `d7cfd619870cebe5a69e365796709d5ba1fc0294a84ae63357a9d189074dc100` | `DDR Version V1.10 20210810` | `Dec 9 2021` |

三份文件的前四字节均为 ASCII `LDR `，文件头格式相似；字符串扫描均显示 LPDDR2/3/4/4X 支持相关字符串、DDR 配置代码提示和 MMC Boot1 相关字符串。

### 10.1 当前结论

现有证据支持三者属于 Rockchip RK356x Loader/SPL 下载启动组件这一相同大类，承担相近的早期启动初始化职责；它们不是同一文件，版本和构建时间有差异。

特别是后两份文件均出现 `DDR Version V1.10 20210810`，但 Boot1 构建日期分别为 2021-09-13 和 2021-12-09。这表明仅凭 DDR 版本不能认定完整 Loader 内容相同。

### 10.2 尚不能得出的结论

- 不能仅凭文件名断言三个文件可互换或用于同一刷写命令。
- `strings` 只能提供内部字符串线索，不能完整证明 SPL、USB plug、Boot1 等组件的精确组成、偏移、长度或代码等价性。
- 不能据此认定其中任意一个就是当前机器运行的 U-Boot proper。
- 仍需解析 Rockchip LDR 镜像内部组件表，并与历史 eMMC LBA64 备份及已知启动链组件做针对性比对。

### 10.3 下一步建议

只读解析三份 LDR 镜像内部组件布局，记录各组件偏移、长度、校验信息及可识别版本；再对共同组件做逐段哈希/二进制比较。先不执行刷写或设备写入。
