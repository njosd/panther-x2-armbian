# Panther X2：TRACEFS 双路径实例与缓冲区核验（2026-11-19）

## 1. 用户实机返回

### mountinfo
```
36 22 0:8 / /sys/kernel/debug rw,nosuid,nodev,noexec,relatime shared:15 - debugfs debugfs rw
37 22 0:13 / /sys/kernel/tracing rw,nosuid,nodev,noexec,relatime shared:16 - tracefs tracefs rw
146 36 0:13 / /sys/kernel/debug/tracing rw,nosuid,nodev,noexec,relatime shared:125 - tracefs tracefs rw
```

### 文件系统与 inode
两个目录均返回：
- filesystem = tracefs
- fsid = d00000000
- device = 13
- 根目录 inode = 1

对应控制文件 inode 完全相同：
- tracing_on = device 13, inode 1053
- current_tracer = device 13, inode 1042
- kprobe_events = device 13, inode 215

### trace 文件
`wc -c /sys/kernel/tracing/trace` 返回 515 bytes。

## 2. 结论

两个路径 `/sys/kernel/tracing` 与 `/sys/kernel/debug/tracing` 是同一个 tracefs 实例的两个挂载入口，不是独立 tracing 实例。后续统一使用 `/sys/kernel/tracing` 即可。

515 bytes 只是 trace 文件当前可读表示的长度，不能据此判断是否存在有效事件记录。尚未读取 trace 内容，也未读取 `trace_pipe`；未清空缓冲区、未改变 tracing 状态。

结合此前实机结果：
- tracing_on=1
- current_tracer=nop
- kprobe_events 为空
- kprobe_profile 为空
- 没有 enabled trace events

当前没有发现已注册 kprobe、启用 tracepoint 或正在运行的 function tracer。仍需注意 tracing_on=1 和 trace_printk 选项开启，故不应擅自关闭 tracing 或清空 buffer。

## 3. 下一步只读动作

为判断 515 bytes 是否只是 trace 文件头/空缓冲区文本，建议用户读取：
```sh
echo "===== TRACE SNAPSHOT (READ ONLY) ====="
cat /sys/kernel/tracing/trace
```

只读取 `trace`，不要读取 `trace_pipe`（后者是消费式读取接口）。不写入任何 tracefs 文件，不改变状态。

若内容只有标题/空缓冲区标记，则可将当前 buffer 基线记录下来。若存在实际记录，先保存并分析，绝不清空。

## 4. 探针仍需单独授权

后续创建 return probe 需要向 `kprobe_events` 写入事件定义，并启用对应事件；这是对运行中内核 tracing 状态的临时修改，不属于只读检查。必须先说明具体写入、采集、停用和删除命令、采集时长及潜在开销，取得用户明确授权后才能执行。

本轮未创建探针、未写入 tracefs、未修改 tracing_on、未清空 buffer。
