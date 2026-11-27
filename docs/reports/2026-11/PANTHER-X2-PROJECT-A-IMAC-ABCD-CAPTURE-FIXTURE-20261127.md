# Project A — iMac ABCD 对端抓包夹具准备（2026-11-27）

- 状态：**抓包脚本已归档；尚未在 iMac 执行；对端捕获能力未验证。**
- 范围：为后续 G7/E6 准备只读网络配置的 macOS 抓包入口。
- 未执行：未访问 iMac、未启动 tcpdump、未发送测试帧、未操作 Panther、未改变任何网络配置。

## 1. 新增文件

`scripts/panther-abcd-tx/capture-abcd-macos.sh`

脚本行为：
- 要求显式指定 macOS 网络接口和 pcap 输出路径；
- 检查 tcpdump 存在、输出目录存在、目标文件不存在；
- 使用 `tcpdump -i IFACE -nn -s 0 -U -w FILE 'ether proto 0x88b5'`；
- 不执行 ifconfig 配置，不改变接口状态、地址、路由或服务；
- 输出文件已存在时拒绝覆盖；
- 通过 Ctrl-C 结束抓包。

## 2. iMac 侧预检步骤（尚未执行）

1. 在 iMac 上确认连接到目标 Panther 所在的同一二层网络；优先使用有线接口。不要猜接口名。
2. 查看接口清单及 MAC：
   `networksetup -listallhardwareports`
   `ifconfig <接口名>`
3. 选择真实连接的接口，记录接口名、MAC、链路状态、连接拓扑和交换机端口。不要使用 lo0。
4. 将脚本从仓库取到 iMac 后执行：
   `chmod +x capture-abcd-macos.sh`
   `./capture-abcd-macos.sh <接口名> <新建的pcap路径>`
5. 另一个已知正常的 Linux 有线设备在同一二层网络运行 sender，使用独立 run-id 和 sequence；sender 必须显式指定该设备的接口。脚本会提示开始发送。
6. 捕获到预期帧后 Ctrl-C 停止。不要在 Panther 上执行 sender。
7. 将 pcap 和 sender 输出保留为同一轮证据。将 pcap 复制到 Linux 验证端，使用已归档的 `verify-pcap.py`：
   `python3 verify-pcap.py --pcap <capture.pcap> --run-id <8位十六进制> --sequence <序号> --source-mac <发送端MAC>`

## 3. 预检通过标准

- pcap 可被离线 verifier 读取；
- 目标 EtherType 0x88B5 恰好一帧；
- frame length 64 bytes，目的 MAC 为广播；
- run_id、sequence、源 MAC 与 sender 输出一致；
- SHA-256 digest 校验通过；
- 没有截断、重复或额外目标帧。

注意：tcpdump 在 iMac 接口上看到帧，只能证明该捕获点收到了该帧。若 iMac 与 Panther 不在同一二层广播域、交换机端口隔离、VLAN 不同，或抓包接口选错，可能捕获不到；捕获失败不能直接归因于 Panther TX。

## 4. 安全边界与当前结论

- 该夹具预检应由已知正常设备发帧，不涉及 Panther。
- 不需要改变 iMac IP、路由、接口 UP/DOWN 状态或网络服务。
- 不需要安装新软件；若系统没有 tcpdump，则暂停并报告，不自行安装。
- 这只是 E6 抓包夹具预检，不是 Panther TX 测试，也不构成 G0 总审通过或硬件激活授权。
- 下一步：用户在 iMac 执行接口确认和抓包工具可用性检查；提供接口信息及结果后，再确定已知正常设备的单帧预检命令。
