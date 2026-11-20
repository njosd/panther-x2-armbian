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


## 11. 已上传二进制的仓库回读校验与内部目标标识复核（2026-11-20）

用户将三份二进制上传至本报告对应的 GitHub 证据目录。通过 GitHub 文件接口以 base64 读取仓库对象，去除 base64 换行后解码为原始字节，并在内存中计算 SHA256。三份仓库对象均与用户此前从 U 盘读取的 SHA256 完全一致：

| 文件 | 仓库回读字节数 | 仓库回读 SHA256 | 与 U 盘记录 |
|---|---:|---|---|
| `MiniLoaderAll.bin` | 453,056 | `ab62386a8868b01516b560451082fbdb6342b16e850a0622577b538dd2b10d39` | 完全一致 |
| `rk356x-MiniLoaderAll.bin` | 455,104 | `1cdd418032195210f191445ed96e2da5ea83d2cfe880c912ebec635839d76542` | 完全一致 |
| `rk356x_spl_loader_ddr1056_v1.10.111.bin` | 453,056 | `d7cfd619870cebe5a69e365796709d5ba1fc0294a84ae63357a9d189074dc100` | 完全一致 |

### 11.1 重要补充：内部 DDR 平台/频率标识

对仓库回读的原始二进制重新提取 UTF-16LE/ASCII 字符串后，发现之前只记录 DDR 版本号不够完整。文件内部还包含以下目标配置字符串：

| 文件 | 内部 DDR 配置名称 | DDR 版本字符串 |
|---|---|---|
| `MiniLoaderAll.bin` | `rk3566_ddr_1056MHz_v...` | `DDR Version V1.09 20210630` |
| `rk356x-MiniLoaderAll.bin` | `rk3568_ddr_1560MHz_v...` | `DDR Version V1.10 20210810` |
| `rk356x_spl_loader_ddr1056_v1.10.111.bin` | `rk3568_ddr_1056MHz_v...` | `DDR Version V1.10 20210810` |

这是一项重要修正：后两份虽然文件名使用泛称 `rk356x`，但内部可见 DDR 配置名明确写的是 `rk3568`；其中第二份还标记 1560 MHz，而第三份标记 1056 MHz。第一份则明确标记 `rk3566` 和 1056 MHz。

因此不能把三者简单视为只差版本号的同一配置。尤其对 RK3566 Panther X2，根目录的 `MiniLoaderAll.bin` 是目前三者中唯一在内部 DDR 配置字符串上明确指向 `rk3566_ddr_1056MHz` 的文件。该字符串是强证据，但还不能单独证明其完整硬件适配性或其一定是实际刷入设备的最终文件。

### 11.2 构建日期字符串

Boot1 相关字符串仍分别为：
- `MiniLoaderAll.bin`: `Jun 18 2021`
- `rk356x-MiniLoaderAll.bin`: `Sep 13 2021`
- `rk356x_spl_loader_ddr1056_v1.10.111.bin`: `Dec 9 2021`

后两份均含 DDR V1.10 20210810，但 Boot1 构建日期不同，且 DDR 配置频率也不同，故不能据 DDR 版本相同推断整体组件相同。

### 11.3 二进制差异概览

三份文件长度分别为 453,056、455,104、453,056 bytes。两两比较时，共同前缀仅 16 bytes，后续大量字节不同；因此它们绝不是简单改名或只改头部日期的相同镜像。该比较仅为整体字节差异概览，尚未按 LDR 内部组件边界拆分。

### 11.4 当前结论修正

此前“属于同一类 Rockchip Loader/SPL 组件”的判断仍成立；但“承担相近职责”不能理解为可以互换。三份文件的 DDR 配置目标存在明确差异：
- 第一份：RK3566 / 1056 MHz / DDR V1.09；
- 第二份：RK3568 / 1560 MHz / DDR V1.10；
- 第三份：RK3568 / 1056 MHz / DDR V1.10。

目前优先把根目录 `MiniLoaderAll.bin` 作为原始 Panther X2 刷机流程的首要候选 Loader（用户确认当时先刷此文件，且内部配置标识为 RK3566 DDR 1056 MHz）；另外两份暂视为 Armbian bootloader 子目录中的不同目标配置样本，不应在未验证前用于 Panther X2。

### 11.5 后续分析方向

需要解析 LDR 内部组件记录，确认 `UsbHead`、DDR payload、USB plug、`FlashData`、`FlashBoot`、`FlashHead` 的偏移、长度和校验；再将第一份与历史 eMMC LBA64 IDB 备份以及原始 6.1.65 镜像中实际使用的 bootloader 进行组件级比较。不得仅凭文件名或 DDR 版本号认定与设备当前启动组件相同。


## 12. 用户补充的历史升级/刷写行为线索（2026-11-20）

用户说明：其理解是，若后期 U-Boot 有更新，应当是随系统升级带入；自己印象中没有专门单独刷写过 U-Boot 的操作。

该信息作为用户回忆记录，不等同于已由升级日志或脚本证明的事实。后续追踪应据此调整证据优先级：

1. 优先审查原始 Armbian 6.1.65 镜像内的启动组件，以及其安装/首次启动流程。
2. 再审查用户实际经历过的系统升级包、升级脚本和版本迁移过程，确认哪些流程会写入 IDB/SPL、U-Boot proper/FIT，哪些只更新 kernel/DTB/modules/boot 配置。
3. 不在缺乏证据时假设用户曾经执行过独立 U-Boot 刷写。
4. 仍需区分用户日常历史与 2026-11-19/20 为本次故障研究进行的实验性操作：既有记录明确显示，研究期间曾将 eMMC user area LBA64 的原版 IDB 替换为 JP-TvBox idbloader。因此“没有专门刷写过 U-Boot”的回忆不能覆盖或否定这次近期实验性 IDB 替换。

重要边界：Linux/Armbian 系统升级并不必然更新 U-Boot。必须从具体升级工具、包内容、脚本、写入目标和历史日志判断，不能把“系统升级”自动等同于“U-Boot 已升级”。

当前待证问题：
- 原始 6.1.65 镜像包含哪一份 Loader/IDB 及 U-Boot proper？
- 原始首次刷机时 `MiniLoaderAll.bin` 实际写入哪个介质区域，后续是否还会写入另一个 U-Boot proper？
- 后续各次系统升级是否触及 eMMC LBA64（IDB）或 LBA16384（FIT/U-Boot），还是仅更新文件系统/boot 分区中的内核和 DTB？


## 13. 对原始 6.1.65 镜像公开来源的检索（2026-11-20）

用户说明 851 MiB 的 gzip 镜像过大，无法通过当前对话上传；应优先从原始发布位置寻找公开副本。

### 13.1 已找到的上游发布来源

检索到 Panther X2 专用 Armbian 项目：
- 仓库：`lintao1890/panther-x2-armbian`
- 2024-01-22 发布页：`Armbian_jammy_save_2024.01`
- 该 release 当前可见的 Panther X2 Jammy 镜像资产：
  `Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.74_server_2024.01.22.img.gz`
- GitHub Release API 显示该资产大小：910,509,481 bytes。
- 同一发布还提供对应的 `.sha` 校验文件。
- 独立的 2026-06 Panther X2 使用记录也引用了该 release URL 和文件名。

### 13.2 与用户原始镜像的对照

用户 U 盘文件：
`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.1.gz`

用户本机实测：
- gzip 文件大小：892,499,345 bytes
- 解压后大小：2,969,567,232 bytes
- gzip 内嵌原始名称：`Armbian_24.2.0_rockchip_panther-x2_jammy_6.1.65_server_2023.12.07.img`
- gzip 内嵌修改时间：2023-12-07 05:18:54（按 file 输出）
- SHA256：`0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`

重要观察：2024-01-22 的公开 6.1.74 镜像解压后尺寸也由外部发布记录显示为 2,969,567,232 bytes。两者解压尺寸相同，但压缩尺寸、内核版本和构建日期不同。相同解压尺寸只能说明容器/镜像总长度相同，不能证明文件内容相同或可替代。

### 13.3 当前检索结论

截至本次检索：
- 已找到同一 Panther X2 专用项目的公开发布源，以及相邻的 6.1.74 镜像。
- 该项目当前可见的 GitHub Releases API 列表仅返回 `kernel_stable` 和 `Armbian_jammy_save_2024.01` 两个 release；后者资产列表中没有用户所持 6.1.65 文件。
- 在该仓库中按完整 6.1.65 文件名、`6.1.65_server_2023.1` 和 `2023.12.07.img` 搜索，未找到对应文件。
- Armbian 公共 archive 的 Panther-X2 目录目前可见的是 2023-08 的 6.1.50 镜像，不是该 6.1.65 文件。
- 因此，**目前尚未找到用户这份 6.1.65 镜像的可验证公开原始下载 URL**。不能把 6.1.74 作为 6.1.65 原版使用。

### 13.4 后续方向

1. 继续追查 2023-12-07 前后 Panther X2 专用项目的历史发布、旧 release/asset、Actions 构建记录或原始分享链接。
2. 若旧镜像原始下载源已失效，优先考虑用户 U 盘副本作为唯一可用原件；不要求用户上传整个大文件。
3. 可采用用户本机只读提取方式，单独导出镜像中的启动相关区域/文件（在确认镜像分区布局后），以便通过较小文件分析 bootloader、DTB、boot.scr、内核等内容。提取前只做只读检查，不写设备。
4. 若找到候选公开镜像，必须先对比下载文件的 SHA256、gzip 元数据、解压长度，再判断是否为同一原件；不得只按文件名认定。


## 14. 重新界定原始镜像与 Ophub 技术路线的关系（2026-11-20）

用户指出，仅从镜像文件名看，似乎不像 Ophub 路线。该质疑成立：**文件名本身不足以证明 Ophub 归属**。进一步核对公开项目资料后，需要把“构建/维护框架来源”和“具体内核、U-Boot 二进制来源”分开。

### 14.1 公开项目谱系证据

与 Panther X2 早期镜像相关的公开项目 `lintao1890/panther-x2-armbian`，GitHub 页面明确标注：
- `forked from ophub/amlogic-s9xxx-armbian`；
- README 将 `rk3566` 的 Panther-X2、JP-TvBox 列为支持设备，并列出 `6.1.y` 内核系列；
- README 的 `armbian-update` 说明中，`-r` 参数默认仓库是 `ophub/kernel`；
- `-u` 可选内核 tag 后缀包括 `rk35xx`；
- `-m` 参数用于选择 mainline U-Boot，默认值为 no。

公开来源：
- `https://github.com/lintao1890/panther-x2-armbian`
- README 相关内容见 Armbian System Description 与 Update Armbian Kernel 部分。

这些资料强力支持：该项目属于 Ophub 的 fork/衍生项目，且其 Panther X2 内核更新机制明确接入 `ophub/kernel`。所以不宜简单说“完全不是 Ophub 线”。

### 14.2 但不能据此推出的结论

上述 README 是项目文档/当前可见说明，不能单独证明用户手中 2023-12-07 构建的 6.1.65 镜像：
- 一定由 Ophub 当时的某个 commit 原样构建；
- 其中 Linux 6.1.65 内核二进制一定来自 `ophub/kernel`；
- 其中 U-Boot proper、SPL、DDR 初始化代码一定来自 Ophub；
- 其首次安装或后续升级必然写入 eMMC 的 IDB 或 U-Boot FIT。

特别是 README 将 kernel 更新和 mainline U-Boot 作为不同参数描述（`armbian-update` 的 `-m`），这进一步说明 kernel update 与 U-Boot update 不应混为一谈。必须检查该时期脚本版本及具体镜像内容。

### 14.3 当前更准确的分类

| 层次 | 当前判断 |
|---|---|
| Armbian 发行/系统镜像 | 已知为 Panther X2 专用 Armbian 镜像，文件名与 gzip 元数据支持 |
| 构建/升级框架谱系 | 高度支持为 Ophub fork/衍生项目 |
| Panther X2 kernel 支持线 | 项目 README 列为 RK3566 Panther-X2 / 6.1.y |
| 具体 6.1.65 kernel 二进制来源 | 未验证 |
| 该镜像中的 U-Boot/SPL/DDR 来源 | 未验证 |
| 系统升级是否改写 eMMC IDB/U-Boot FIT | 未验证 |

### 14.4 修正前述表述与研究重点

此前将“同项目 6.1.74 发布资产”表述为与 6.1.65 同源线索时，必须限定为同一公开 fork 项目的相邻发布版本；它不是 6.1.65 原件，也不能代替原始镜像。

后续应检索该 fork 在 2023-12-07 前后的 commit、workflow、release、`armbian-update` 脚本版本及 `compile-kernel` 构建定义，尤其追查：
1. 6.1.65 是在原始 Armbian BSP 上直接编译，还是经 Ophub kernel package 更新/替换；
2. 首次安装 `MiniLoaderAll.bin` 的工具链与实际写入位置；
3. 默认 U-Boot 与可选 mainline U-Boot 的具体选择；
4. 后续 kernel update 是否触及 eMMC LBA64 IDB 或 LBA16384 FIT。

本节将“框架谱系高度支持 Ophub 衍生”与“镜像中每个二进制均来自 Ophub”明确分离，避免过度归因。


## 15. 用户计划复原首次刷机流程并重刷 eMMC；公开流程交叉验证（2026-11-20）

用户明确希望按照最初刷机顺序完整重刷，目标记忆为 eMMC，而不是仅从 TF 卡试启动。用户回忆最初先刷 `MiniLoaderAll.bin`。目前没有找到当年本人实际使用的 RKDevTool 操作记录、命令、截图或完整刷机日志，因此目标 eMMC 是用户明确表达的当前计划及其历史回忆，具体工具参数仍未被历史记录证实。

### 15.1 历史记录回溯结果

此前对话只记录了用户回忆“最初刷机要求先刷入 MiniLoaderAll.bin”。截至本次回溯，未检索到当年实际使用 RKDevTool / upgrade_tool、MaskROM / Loader 流程、写入地址、eMMC 目标选择或写入日志的直接记录。2026-11-13 对 BSP 包的检查也未发现 Panther X2 专用刷机、USB OTG、RKDevTool、upgrade_tool、MiniLoaderAll.bin 或 eMMC/TF 写入脚本。因此不能声称已复原当年的逐项操作。

### 15.2 同型号公开刷机资料的交叉验证（不是用户本人历史记录）

- 2023-06-27 的 Panther X2 Rockchip 刷机指南明确使用 RKDevTool；进入 LOADER 后切换 Maskrom，再在 Download Image 页选择 Boot 文件 `rk356x-MiniLoaderAll.bin` 和 Armbian system image，执行后等待 `Download image OK`。该指南使用 2023-06 的 6.1.35 Bookworm 镜像，不是用户的 2023-12 6.1.65 Jammy 镜像。
  来源：`https://kingtam.eu.org/posts/rk3566-flash/`
- 2024-09-09 的 Panther X2 指南也记录了 RKDevTool、LOADER→Maskrom、Boot 栏选择 `MiniLoaderAll.bin`、System 栏选择 Panther X2 Armbian IMG 的流程。它使用 2024-07 的 6.1.57 Bullseye 镜像，不是用户原件。
  来源：`https://blog.van.ac.cn/wiki/黑豹X2（Panther-x2）刷机并驱动NPU-VPU、Jellyfin转码/`

这些资料与用户“先刷 MiniLoaderAll.bin，再刷系统镜像”的回忆相互吻合，并支持 RKDevTool 的 Boot + System 两项刷写模式是 Panther X2 社区使用过的流程。但它们不能证明用户当年具体用的是哪一个工具版本、哪一份 loader、哪种存储器切换设置，也不能代替本机原始流程证据。

### 15.3 当前不可跳过的安全边界

当前研究状态与首次刷机时不同：eMMC user area LBA64 的原版 E25 IDB 已在 2026-11-19/20 研究中被 JP-TvBox IDB 替换；eMMC LBA16384 有 U-Boot FIT；TF 卡曾承担加载 JP U-Boot proper 和 Linux rootfs 的启动路径。因此，直接执行“Boot + System”写入可能改变已有 eMMC 启动组件与分区内容，不能在未确认 RKDevTool 配置和存储目标前开始。

原始 `MiniLoaderAll.bin` 当前已归档并完成哈希核对（RK3566 DDR 1056 MHz 候选），但仍需验证它是否就是当年实际使用的 Loader，以及 RKDevTool 对 Boot 文件和 System 镜像分别写入何种介质/位置。原始镜像为 gzip 压缩 raw disk image，公开指南要求先解压为 `.img` 后再选作 System；解压后的长度为 2,969,567,232 bytes，SHA256 为 `0326e757a72182b5e60b112000ceef808bcb3a2bfd954448bbb6c9b16eb6f3ea`。

### 15.4 后续执行前的必需核对

1. 只读解析原始镜像分区表及启动区，确定镜像本身的布局与启动组件位置。
2. 取得当年或对应版本的 RKDevTool 配置文件（尤其是 `config.cfg`）并检查 Boot/System 下载项的地址/存储器行为；不要凭现代教程臆测配置。
3. 明确本次要恢复的 eMMC 区域与当前实验性状态的影响；保留现有已归档原版 E25 IDB、JP IDB、eMMC/boot0/boot1 研究记录。
4. 在任何写入前再次核对设备枚举、存储介质选择、Loader 文件哈希、解压后 IMG 哈希及目标设备。当前阶段不执行刷写。

目标是复现首次安装的核心顺序并以 eMMC 独立启动验证为结果，但必须将“与公开教程一致的推定流程”和“当年本人实际执行过的流程”分开标注。
