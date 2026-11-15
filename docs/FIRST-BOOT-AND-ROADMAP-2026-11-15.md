# Panther X2 首版镜像验收与后续路线

> 更新日期：2026-11-15  
> 当前阶段：首版镜像静态验收完成，准备进入独立 TF 卡真机验证。  
> 本文记录已验证事实、尚未验证事项、首轮上机流程和后期优化路线。它不授权对现有 192.168.9.6 系统进行任何修改。

## 1. 当前决策摘要

当前首选路线为 **Ophub Armbian + RK35xx Linux 6.12.81 + Ubuntu 24.04 Noble Server**。首版目标不是立即部署 Immich，而是先让不包含 Immich 的基础系统在 Panther X2（RK3566）上无故障启动，并验证网络、SSH、存储和持续运行。

当前 Build Run `43682186779` 生成的镜像已经通过独立静态验收和上机前 Preflight。现阶段结论是：

- **可以进入真机验证**：镜像结构、分区、启动文件、DTB存在性、关键软件包和首启服务等静态检查没有发现足以阻止首轮上机的明显问题。
- **尚不能称为启动成功**：尚未在 Panther X2 实机上验证启动链、GMAC/PHY、DHCP、SSH、TF/eMMC、USB及稳定性。
- **不重新构建**：继续使用现有 Build Artifact，采用“构建一次，多轮独立验收”。
- **不先做大规模精简**：先验证基础系统能否稳定运行；残留包和非必要服务放到系统稳定后再评估。
- **首轮不启用 NPU candidate，不重编 U-Boot，不写 eMMC**。
- **不修改当前 192.168.9.6 系统**；实机测试使用独立 TF 卡。

## 2. 固定构建基线

| 项目 | 当前固定值 |
|---|---|
| SoC / 设备 | Rockchip RK3566 / Panther X2 |
| 内核仓库 | `ophub/linux-6.12.y-rockchip` |
| 内核 commit | `661b2d8bf1284556f8876d5ed5fb80c64b22f94c` |
| Panther DTS | `arch/arm64/boot/dts/rockchip/rk3566-panther-x2.dts` |
| U-Boot commit | `6e70f41585f15c43f45fcae609adec1865e83eb5` |
| Ophub commit | `9e71b57f73683f9c4d14a30311e4c2ccbff29566` |
| Armbian build commit | `3f3849bf50bfadff94d0d488eb968bdaf970dc72` |
| firmware commit | `a9d0e8337cc8aa2ca4b482acd7b19c74ce05860f` |
| Rootfs基底 | Armbian Noble CLI / Odroid N2 base rootfs，再由 Ophub rebuild 改造为 Panther X2 + RK35xx 6.12.81 |
| 镜像类型 | Ubuntu 24.04 Noble Server，CLI，无桌面 |
| 文件系统 | EXT4 |
| 启动文件 | `idbloader.img` + `u-boot.itb` |
| 首轮介质 | 独立 TF 卡；不安装到 eMMC |
| NPU | 首版不启用独立 NPU candidate |

历史启动链中没有独立 `trust.bin`。首版不重编 U-Boot。

## 3. 当前镜像与静态验收记录

### 3.1 Build

- Build Run：`43682186779`
- Job：`132714994034`
- Artifact：`panther-x2-minimal-6.12.81-noble`
- Artifact ID：`14149202691`
- 镜像文件：`Armbian_26.11.0_rockchip_panther-x2_noble_6.12.81_server_2026.11.15.img.gz`
- SHA-256：`621046ec56da262d0dc4fc411d77bcbfc286efc7b9eef9e8e132e312253bd856`
- Build Artifact 当时约 1.16 GB；下载后解压镜像约 6.52 GiB。

构建内核包检查、Noble基础rootfs、SSH初始化和Panther镜像重建成功。Build workflow内曾有一处验收脚本 Bash 括号转义错误，但镜像因 `if: always()` 仍成功上传；后续独立验收针对该 Artifact 完成，不需要重建。

### 3.2 独立 Validate

- Run：`43683430998`
- Job：`132718797246`

已验证：SHA-256、gzip解压、GPT分区识别、只读挂载；NetworkManager、Netplan、SSH server、`ssh.service` 和 `armbian-firstrun.service` 均存在且静态启用状态符合预期。Netplan使用NetworkManager作为renderer，配置DHCP。

镜像允许root首次SSH登录并使用初始密码 `1234`。这是首启引导设置，不可长期保留；首次登录后应立即更改并创建普通管理用户。

### 3.3 扩展静态审计

- Run：`43683944914`
- Job：`132720330841`

APT源检查只发现Armbian官方源和Ubuntu Noble官方源。关键词扫描没有发现常见广告注入、遥测或第三方远程管理常驻配置的证据；但关键词扫描不等于完整恶意代码审计。

发现若干Odroid/Meson残留包，例如 `armbian-bsp-cli-odroidn2-current`、`linux-image-current-meson64`、`linux-dtb-current-meson64`、`linux-u-boot-odroidn2-current`。目前不据此判断首版不可用，也不在真机首启前批量清理。后续需定向检查这些包的脚本、服务和板型判断行为。

`armbian-featured` 定期读取官方Armbian feed；`armbian-updates` 使用 `apt-get upgrade -s` 模拟升级；日志截断任务存在。Preflight发现 `apt-daily.timer` 与 `apt-daily-upgrade.timer` enabled，但当时未取得足以证明会自动安装更新的完整配置内容。因此自动更新行为仍需实机或更完整配置审计确认，不能仅凭timer启用就断言自动升级。

### 3.4 Preflight

- Run：`43685322113`
- Job：`132724491575`
- 报告 Artifact ID：`14150170897`
- 报告链接：[Preflight报告](https://github.com/njosd/panther-x2-armbian/actions/runs/43685322113/artifacts/14150170897)

Preflight针对已有Build Artifact执行，没有重新构建。检查结果：

- SHA-256与镜像压缩格式检查通过。
- GPT分区表识别成功：
  - p1：起始扇区32768，1046528 sectors，约511 MiB；
  - p2：起始扇区1081344，12580864 sectors，约6 GiB。
- boot/root分区只读挂载成功。
- Panther X2 DTB文件存在且可反编译，结构标识为RK3566/Panther X2。
- U-Boot镜像中的 `idbloader.img` 位于64 sectors（32 KiB），`u-boot.itb` 位于16384 sectors（8 MiB）；与rootfs中的对应文件比较一致。
- 报告统计kernel module files 3172、firmware files 1130；可找到Realtek PHY、Rockchip DWMAC、MMC、EHCI/OHCI/XHCI等相关驱动文件。
- NetworkManager、SSH、`armbian-firstrun` 静态启用检查通过。

注意：DTB节点细节输出不完整，不能据此宣称所有外设节点和依赖均正确。既有静态DTS审计仍提示USB2 PHY phandle/clock依赖风险；USB3 host/DRD节点也不能仅凭模块存在就认定已启用。APT自动更新配置仍需补充确认。

## 4. 已知硬件/驱动静态审计结论

### GMAC1 / RTL8211F

静态配置显示Panther DTS启用GMAC1，RGMII，外部125 MHz，PHY供电为`vcc_3v3`，reset GPIO3 PA1低有效，TX delay `0x30`、RX delay `0x10`，MDIO地址0。6.12.81内核配置内建`STMMAC_ETH`、`DWMAC_ROCKCHIP`、`PHYLIB`、`REALTEK_PHY`、`MDIO_BUS`、`OF_MDIO`、`PHYLINK`。专项内核包检查Run `43669171821`确认这些主链模块为内建配置，modules包不包含它们符合预期。

**已验证：静态DTS和内核配置/包检查。未验证：实机PHY匹配、RGMII时序、协商、DHCP、吞吐、持续传输和重启恢复。** 首轮真机优先验证网口稳定性。

### 存储 / PMIC

DTS中`mmc0`为TF/SD、`mmc1`为eMMC、`mmc2`为SDIO；使用RK809 PMIC，TCS4525 CPU regulator匹配fan53555驱动。MMC、SDHCI、RK808 regulator、I2C、clock、pinctrl等静态配置已检查，仍需实机验证TF卡识别、读写、重启和eMMC识别情况。

### USB

DTSI中host0 EHCI/OHCI默认disabled，Panther DTS启用后存在引用`usb2phy1/u2phy1_otg`与Panther DTS显式启用`usb2phy0/u2phy0_host`之间的phandle/clock依赖风险。USB3 host/DRD节点没有明确启用证据。USB不是首轮启动的首要阻塞，但应在基础系统启动后单独验收。

### 串口

`chosen.stdout-path`为serial2:1500000n8，8250 console内建。首轮不依赖UART，优先验证DHCP和SSH PTY firstlogin路径。

## 5. 首轮 TF 卡真机验证流程

### 5.1 写卡前准备

1. 选用独立TF卡，确认容量足以容纳解压后约6.52 GiB的镜像及文件系统扩展空间；建议使用可靠品牌、状态良好的卡。
2. 先在iMac上确认TF卡设备标识、容量和现有数据，备份需要保留的内容。
3. 下载Build Run `43682186779` 的Artifact，不要误用Preflight报告Artifact。
4. 对下载的压缩镜像计算SHA-256，必须与本文记录的值完全一致。
5. 写卡前再次核对目标设备路径。写卡会覆盖目标卡全部分区和数据；不确定时停止，不执行写入。
6. 只写入独立TF卡，不选择Panther X2 eMMC、iMac内部磁盘或其他存储设备。

**本文件不包含可直接执行的写卡命令**，避免在未确认macOS设备节点前造成误写。实际写卡时应根据当时设备列表确认目标。

### 5.2 首次启动

1. 关机状态下插入TF卡，保持eMMC原状。
2. 上电启动，观察设备是否进入系统；首轮可不接UART。
3. 在路由器DHCP租约列表中确认新设备地址及MAC，避免仅凭猜测连接。
4. 从局域网主机测试IP连通，再通过SSH连接。
5. 使用镜像初始root凭据完成Armbian firstlogin。初始密码为`1234`，首次登录后立即修改；创建普通管理用户，后续优先使用普通用户和sudo。
6. 重启一次，确认新用户SSH登录和DHCP地址恢复正常。

### 5.3 首轮验收项目

| 顺序 | 项目 | 验收要点 | 状态 |
|---|---|---|---|
| 1 | 启动 | TF卡启动，无反复重启/卡死 | 待实机验证 |
| 2 | DHCP | 网卡识别、正确获取IPv4、默认路由和DNS | 待实机验证 |
| 3 | SSH / firstlogin | 首次登录流程完成，创建普通用户；重启后可登录 | 待实机验证 |
| 4 | 基础硬件 | CPU型号/核心数、内存、温度、根分区和TF卡容量识别正确 | 待实机验证 |
| 5 | GMAC1 | PHY驱动匹配、1000M链路协商、双向通信 | 待实机验证 |
| 6 | 网络负载 | 持续传输、双向读写、无掉链/错误计数异常 | 待实机验证 |
| 7 | 重启恢复 | 多轮冷启动/重启后网口和SSH恢复 | 待实机验证 |
| 8 | 存储 | TF卡读写稳定；确认eMMC识别但不写入 | 待实机验证 |
| 9 | USB | USB2设备枚举与读写；再单独判断USB3能力 | 待实机验证 |
| 10 | 稳定性 | 连续运行、温度、内存和日志观察 | 待实机验证 |

网络验收不能以网口灯亮、接口UP或单次DHCP租约作为通过标准。至少需要链路协商、持续双向传输、重启恢复等证据。出现异常时先采集日志和状态，不要立即改内核或驱动。

## 6. 真机验证后的阶段门

- **阶段A：基础启动**——TF卡启动、系统可登录、firstlogin完成。
- **阶段B：网络可靠**——GMAC1/RTL8211F稳定、DHCP/SSH可靠、持续传输和重启恢复通过。
- **阶段C：平台基础能力**——温度、存储、USB、连续运行得到记录。
- **阶段D：内核/BSP整理**——仅根据实机失败点做定向修复；没有证据不做大范围移植或清理。
- **阶段E：NPU/RKNN验证**——在基础系统稳定后单独评估驱动、设备节点、用户态runtime、模型工具链及真实推理。
- **阶段F：Immich试运行**——先验证容器/数据库/存储和日常备份，再逐步加入硬件加速。

任何阶段失败，都先定位失败层级，尽量通过独立验收复现；除非证明确实是镜像构建问题，否则不重新构建整套镜像。

## 7. 后期优化计划（不阻塞首轮启动）

以下是后续优化候选，不代表已实施或已证明必要。按实机证据和收益排序推进。

### 7.1 系统清理与长期运行基线

- 检查Odroid/Meson残留包的安装脚本、服务、板型判断和更新行为，确认哪些只是构建基底遗留，哪些会影响Panther X2。
- 审核APT自动更新：明确`apt-daily`、`apt-daily-upgrade`、unattended-upgrades及Armbian更新任务的实际行为；确定家庭服务器的更新策略，避免意外升级内核。
- 评估并精简不需要的服务、软件包、编译工具和后台任务（例如NFS/rpcbind、OpenVPN、vnstat、PackageKit等），以实际依赖和资源占用为依据，不预先删除。
- 检查日志轮转/截断策略、journal持久化、磁盘空间、时区、NTP、温度监控和异常重启记录。
- 建立固定内核、DTB、U-Boot、rootfs和配置清单；每次更新保留可回退镜像和变更记录。

### 7.2 Panther X2 BSP与内核维护

- 继续审计Panther X2专用BSP来源，梳理与通用Ophub流程的边界。
- 将必要的Panther X2专用DTS/驱动修正整理为可独立维护的补丁包，尽可能与Ophub上游内核更新解耦。
- 对照实机结果处理GMAC/RGMII、USB PHY、MMC、电源、温控等问题。
- 比较6.12长期维护线与后续Ophub内核版本；升级必须先做静态差异审计，再用独立TF卡验收。
- 保留可复现构建输入和版本锁定，不把未审计的动态上游变化直接带入常驻系统。

### 7.3 NPU / RKNN能力

- 先确认6.12.81基础系统下NPU硬件节点、内核驱动、IOMMU/电源/时钟依赖。
- 单独审计RK3566 BSP驱动候选的来源、许可证、内核API依赖和补丁范围。
- 再验证RKNN runtime、模型转换工具链、算子覆盖及实际推理性能。
- 首轮不把NPU列为基础系统启动条件；没有可用驱动时，Immich先使用CPU或局域网算力。
- NPU是否能加速Immich的具体任务，需要按Immich组件实际支持情况逐项验证，不能从“RK3566有NPU”直接推断兼容。

### 7.4 局域网临时算力与Immich

- 9.6长期作为常驻服务主机，负责数据库、照片管理、手机自动备份和少量新增照片处理。
- 首次大批量导入、缩略图/视频转码、相似照片分析等高负载任务，可研究由局域网其他机器临时承担。
- 先确定Immich各任务的CPU/GPU/NPU依赖、任务队列和可迁移性，再设计临时算力协作；不预设所有任务都能无缝远程卸载。
- 基础系统稳定后，先部署最小化Immich验证环境，验证数据库、媒体目录、容器持久化、备份与恢复，再扩展AI功能。

### 7.5 存储与数据安全

- 比较TF/eMMC仅作系统盘、外置USB存储、SATA/NVMe桥接等方案的稳定性、功耗、Linux兼容性和维护便利性。
- 照片数据盘与系统盘分离；数据库、缩略图、原始媒体和备份的布局需结合实际容量与IO测试确定。
- 评估文件系统、SMART/健康监控、断电保护、UPS和安全卸载。
- 设计至少一份独立备份；明确备份频率、版本保留、校验、异机恢复演练和灾难恢复步骤。
- 兼顾iMac直连读取/复制便利性，但不以牺牲Linux服务稳定性或数据完整性为代价。
- 存储硬件采购应在实机接口和性能测试后决定，不提前购买。

## 8. 安全边界与记录规范

- 未经明确授权，不安装软件、不改系统配置、内核、驱动或网络服务。
- 不写入eMMC，不影响当前9.6系统和现有服务/存储测试。
- 写卡、分区、格式化、清理和固件写入等破坏性操作，必须先确认设备身份、目标范围和数据备份。
- 报告中区分**已验证**、**静态审计确认**、**待实机验证**和**推测/候选**。
- 每轮验收记录镜像SHA、设备型号、内核版本、命令输出、日志、测试条件和结果。
- 只有定位到镜像本身缺陷时才重新Build；一般驱动或配置问题先做针对性分析和独立验证。

## 9. 相关工作流

- Build：`.github/workflows/build-panther-x2-minimal.yml`，手动触发构建首版镜像。
- Validate：`.github/workflows/validate-existing-panther-x2-image.yml`，对既有Artifact独立验收。
- Preflight：`.github/workflows/preflight-panther-x2-image.yml`，对既有Artifact做上机前静态检查，不重建。

当前实机验证对象固定为Build Run `43682186779` 的Artifact。后续独立验收优先复用该镜像，不要误触发新的Build。
