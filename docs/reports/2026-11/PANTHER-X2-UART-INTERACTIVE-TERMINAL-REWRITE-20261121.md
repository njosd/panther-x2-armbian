# Panther X2 UART 交互终端重写记录

日期：2026-11-21

## 1. 支线目标

修复 iMac/macOS 上原有 UART 双向交互终端的不可靠问题：本地字符回显干扰、输入缓冲/粘贴异常、Python heredoc 与 stdin 冲突，以及连接后偶发无响应。该支线与 autoboot 自动中断脚本分离。

## 2. 历史回溯结果

仓库内已有 UART 双向测试原始证据归档：
- `evidence/uart/manifest.txt`
- 原始记录：`panther-emmc-uart-bidirectional-20261113.txt`
- 原始 SHA-256：`3d7eae6b7f6a4345df39055fcd44da5ce5a6edc2c1cffc408bafdc3e81da8dd2`

此前问题讨论确认需要重写交互终端。当前检索未找到原 `panther-uart.py` 的完整源码文件，因此没有覆盖或删除旧文件，也不声称已恢复旧源码。新实现按已知故障点重新设计。

## 3. 第一版实现及实机失败记录

第一版新增 `tools/uart/panther-uart-terminal.py`，使用 macOS `/dev/tty`、POSIX raw mode、UART双向字节转发、关闭 bracketed paste 标记、Ctrl+] 后按 . 退出，以及RX/TX日志。

2026-11-21 用户iMac测试：
- 下载成功，`py_compile`通过，pySerial 3.5，串口设备节点存在。
- Panther未开机时没有UART回传；此时程序仍应允许本地退出，但用户报告退出组合键无效。
- Panther开机后，程序能收到大量 Armbian shell 提示符及ANSI重绘序列，证明RX通路工作。
- 用户尝试输入 `version`，却出现本地 zsh 的 `command not found: version`，表明脚本已经退出/失去终端控制，命令没有按预期进入目标Shell。
- 当时日志文件为追加模式，可能混合多次运行，不能把整份文件无条件归属于单次会话。
- TX日志中出现 `verversion`、大量CR（`0d`）、Ctrl+]相关字节及异常UTF-8字节。结合用户现场现象，第一版交互验收失败；不能把异常归咎于设备未开机。
- RX尾部可见大量 `armbian:~:#` 提示符与ANSI控制序列，接收方向已证实工作。

第一版失败结论：输入路径/终端状态处理不可靠，退出机制也不符合预期。停止继续使用第一版。

## 4. 第二版修订

已更新 `tools/uart/panther-uart-terminal.py`（Git commit `e14313fda054a32a9f351b62324463e17b19f7cf`）：

1. 本地退出改为**单独按一次 Ctrl+]**，不再依赖 Ctrl+] 后接句点的两键解析。
2. Ctrl+C仍然透传为 `0x03`，不作为本地退出键。
3. 每次运行创建独立日志文件，文件名带时间戳和进程ID，以 `xb` 创建，避免追加、覆盖和多次会话混淆。
4. 先打开串口和日志，再切换终端raw mode；串口打开失败时不让终端留在raw mode。
5. 使用单独的终端写入函数处理短写，RX按串口当前待收字节数读取。
6. finally中关闭串口和日志，恢复原始终端属性。
7. 不自动执行目标设备命令；只做键盘字节转发和UART字节显示。

该版本尚未在用户iMac或Panther X2实机运行，不能标记为已验证。静态检查与实际运行验收仍需完成。

## 5. 使用方式

在普通 macOS Terminal 交互窗口运行，不通过 heredoc 启动：

```sh
"$HOME/panther-uart-venv/bin/python" "$HOME/panther-uart-terminal.py"
```

默认参数：`/dev/cu.usbserial-1460`、1500000 baud、8N1。每次运行会创建新的 `~/panther-uart-session-时间戳-PID.rx.bin` 和 `.tx.bin` 文件。

本地退出：**按一次 Ctrl+]**。Ctrl+C仍发给Panther X2。

## 6. 下一轮实机验收

先确认没有旧的 `panther-uart-terminal.py` 进程占用串口。然后下载第二版、运行 `py_compile`，启动后按顺序进行：
1. 等待并确认收到设备Shell提示符。
2. 输入短命令 `version`，检查TX是否精确为ASCII `version\r`（以实际Enter编码为准），RX是否有对应回显/输出。
3. 粘贴单条只读命令，检查无重复字符及bracketed-paste包装标记。
4. 单独按一次 Ctrl+]，确认本地退出，不向目标发送该退出字节。
5. 检查iMac终端回显和行编辑恢复正常，并核对本次唯一RX/TX日志。

测试期间不得并行运行另一个占用同一串口的程序。不要用破坏性命令；本支线不需要修改Panther配置、TF卡或eMMC。

## 7. 安全与操作边界

该脚本只负责主机终端与UART之间的字节转发和日志记录，不自动执行任何U-Boot命令，不包含MMC、分区、升级或刷写逻辑。它与 `uart-autoboot-interrupt.py` 分工独立：
- `panther-uart-terminal.py`：持续交互式双向终端。
- `uart-autoboot-interrupt.py`：自动发送Ctrl+C以打断autoboot，识别命令提示符后结束。

始终遵守项目硬约束：eMMC绝不写入。
