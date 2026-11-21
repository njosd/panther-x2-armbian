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

## 3. 新实现

新增 `tools/uart/panther-uart-terminal.py`。

设计要点：
1. 直接打开 macOS 控制终端 `/dev/tty`，不使用 Python stdin 作为键盘输入源，避免 heredoc 占用 stdin 的冲突。
2. 使用 POSIX raw mode，关闭本地 ECHO、canonical line buffering 和终端生成的信号处理；键盘输入字节原样发往 UART。
3. UART 接收字节直接显示在终端；本地不重复打印键盘输入，设备自身回显时只显示设备返回的字符。
4. 关闭终端模拟器 bracketed-paste 标记，避免粘贴时把 `ESC[200~` / `ESC[201~` 控制序列发给 U-Boot。
5. Ctrl+C 作为 `0x03` 发送给目标设备。使用 Ctrl+] 后接 `.` 作为本地退出键，避免误把退出动作发送给目标。
6. RX 和 TX 分别保存为 `.rx.bin` 与 `.tx.bin`，避免键盘输入与设备输出混在同一日志。
7. 通过 `finally` 关闭串口和日志文件，并恢复 macOS 终端原始属性。

## 4. 使用方式

在普通 macOS Terminal 交互窗口运行，不通过 heredoc 启动：

```sh
"$HOME/panther-uart-venv/bin/python" "$HOME/path/to/panther-x2-armbian/tools/uart/panther-uart-terminal.py"
```

默认参数沿用此前 Panther X2 UART 环境：`/dev/cu.usbserial-1460`、1500000 baud、8N1。设备节点必须在当前 iMac 上重新核实。日志默认写入用户目录下的 `panther-uart-session.rx.bin` 和 `panther-uart-session.tx.bin`。

## 5. 验证状态

- 历史原终端存在输入/回显/粘贴等问题：已从项目历史记录确认。
- 新脚本已写入仓库：已完成。
- 新脚本语法与运行时行为：尚未在用户实际 iMac 环境完整验证。
- UART 连通性、字符不重复、Enter、长文本粘贴、Ctrl+C 透传、本地退出、异常退出后终端恢复：均列为下一轮实机验收项。
- 本次没有连接 Panther X2，没有运行新脚本，没有修改设备配置，也没有对 eMMC/TF 做任何写入。

## 6. 安全与操作边界

该脚本只负责主机终端与 UART 之间的字节转发和日志记录，不自动执行任何 U-Boot 命令，不包含 MMC、分区、升级或刷写逻辑。它与 `uart-autoboot-interrupt.py` 分工独立：
- `panther-uart-terminal.py`：持续交互式双向终端。
- `uart-autoboot-interrupt.py`：自动发送 Ctrl+C 以打断 autoboot，识别命令提示符后结束。

后续实机验收先使用安全的只读 U-Boot 命令；始终遵守 eMMC 绝不写入的项目硬约束。
