# Panther X2：TRACEFS 当前状态核验（2026-11-19）

## 1. 实机只读结果

用户执行只读检查，返回：

### 挂载
```
debugfs on /sys/kernel/debug type debugfs (rw,nosuid,nodev,noexec,relatime)
tracefs on /sys/kernel/tracing type tracefs (rw,nosuid,nodev,noexec,relatime)
tracefs on /sys/kernel/debug/tracing type tracefs (rw,nosuid,nodev,noexec,relatime)
```

tracefs 两个路径均已挂载。仅凭该输出不能断定它们是同一 tracefs 实例；需对照 `/proc/self/mountinfo` 及 inode/fs 信息。

### 全局 tracing 状态
- `tracing_on=1`
- `current_tracer=nop`
- `trace_options` 中 `trace_printk`、`record-cmd`、`context-info`、`overwrite` 等选项开启；`stacktrace`、`userstacktrace` 未开启。
- `buffer_size_kb=7 (expanded: 1408)`

### 动态探针
- `kprobe_events` 为空
- `kprobe_profile` 为空

### 已启用事件
用户检查 `events/*/enable`，没有任何 enable=1 的事件。

## 2. 解释与边界

当前没有发现正在运行的 function tracer、已注册的 kprobe 或启用的 tracepoint 事件。因此没有证据显示已有常规 trace-event/kprobe 采集任务。

但不能把 `tracing_on=1` 忽略：
- 它表示 tracing 全局开关处于开启状态；
- `current_tracer=nop` 且无事件启用，意味着当前未发现常规 tracer/event 采集；
- `trace_printk` 选项开启，内核中若有 trace_printk 调用仍可能写入 trace buffer；
- trace buffer 可能包含已有记录，当前尚未读取或保存；
- 不得擅自将 `tracing_on` 改为 0，也不得清空 trace buffer。

`buffer_size_kb=7 (expanded: 1408)` 原样记录，不推断为可随意调整的空闲缓冲区。

## 3. 探针决策

本轮不创建探针、不写 tracefs、不改变 tracing_on、不清空 buffer。尽管没有发现已注册探针/启用事件，仍需先确定两个 tracefs 路径是否同一实例，并了解当前 trace buffer 是否有内容。

建议下一轮继续只读检查：
```sh
echo "===== MOUNTINFO ====="
grep -E 'tracefs|debugfs' /proc/self/mountinfo

echo "===== TRACEFS IDENTITY ====="
for d in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    echo "--- $d ---"
    stat -f -c 'filesystem=%T fsid=%i' "$d"
    stat -c 'device=%d inode=%i mode=%A' "$d"
    for f in tracing_on current_tracer kprobe_events; do
        [ -e "$d/$f" ] && stat -c "$f device=%d inode=%i" "$d/$f"
    done
done

echo "===== TRACE BUFFER SIZE ONLY ====="
wc -c /sys/kernel/tracing/trace
```

上述命令只读取挂载信息、文件元数据及 trace 文件字节数，不读取 trace 内容、不修改状态。若两路径确认是同一实例且 buffer 无需保留问题解决，才考虑下一步探针方案。

## 4. 当前结论

- 已验证：tracefs 两个路径均挂载；全局 tracing_on=1；current_tracer=nop；kprobe_events/kprobe_profile 为空；没有启用事件。
- 未验证：两个挂载路径是否同一实例；trace buffer 是否含有应保留的既有记录；是否存在未通过 trace-event 接口展示的其他 tracing 使用者。
- 安全约束：不得将 tracing_on 从 1 改为 0；不得清空 buffer；未经明确授权不创建/启用探针。
