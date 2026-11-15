# Panther X2 最小启动镜像：构建与首次验证

当前目标是生成第一版可写入独立 TF 卡的完整镜像，不安装到 eMMC。

## 启动构建

1. 打开仓库 GitHub Actions。
2. 选择 **Build Panther X2 minimal bootable image**。
3. 点击 **Run workflow**，使用默认分支和默认参数。
4. 等待 job 完成。Armbian 基础 rootfs 编译可能需要较长时间。
5. 只有 workflow 全部成功并生成 Artifact，才表示镜像构建和静态验收通过。

工作流链接：

https://github.com/njosd/panther-x2-armbian/actions/workflows/build-panther-x2-minimal.yml

## 产物

成功后下载 Artifact：

`panther-x2-minimal-6.12.81-noble`

其中应包含：
- `Armbian_..._rockchip_panther-x2_noble_6.12.81_server_....img.gz`
- 同名 `.sha256` 校验文件
- `validation-report.txt`

使用 macOS 校验：
```bash
shasum -a 256 -c <镜像文件名>.sha256
```

## 第一版预期

- Panther X2 / RK3566
- Armbian Noble CLI
- Ophub RK35xx Linux 6.12.81
- `rk3566-panther-x2.dtb`
- `idbloader.img + u-boot.itb`
- ext4，root 分区目标 6144 MiB
- 有线网卡通过 NetworkManager + Netplan DHCP
- SSH TCP/22，root 密码初始为 `1234`
- 首次登录通过交互式 SSH PTY 完成 Armbian first-login 初始化

## 实机写卡前

Artifact 的静态镜像检查通过，不等于实机启动已经验证。第一次测试必须写入独立 TF 卡，不选 eMMC，不运行任何安装到 eMMC 的命令。

首轮实机验收顺序：
1. TF 卡启动，接有线网线。
2. 从路由器 DHCP 租约表找到 Panther X2 地址。
3. iMac 交互式 SSH 登录 root（初始密码 `1234`）。
4. 完成首次 root 密码设置和普通用户创建。
5. 退出并重新 SSH 登录。
6. 重启一次，再确认 DHCP 和 SSH 恢复。

如果 workflow 失败，先提供 Actions run 链接和失败 step 日志；不要先在 9.6 实机上试错。
