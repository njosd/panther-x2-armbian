# Panther X2：6.12.81 KPROBE / TRACEFS 只读能力检查结果（2026-11-19）

## 1. 本轮操作边界

用户在 Panther X2 当前运行系统执行了只读检查命令。没有创建 KPROBE、没有启用 tracing、没有写入 tracefs、没有安装软件，也没有修改网络或内核配置。

## 2. 实机返回结果

### TRACEFS
以下目录存在并可读取：
- `/sys/kernel/tracing`
- `/sys/kernel/debug/tracing`

两个路径列出的事件相同，说明当前 tracefs/debugfs tracing 视图一致；这不代表两个独立 tracing 实例。

### 已存在事件类别
- `kmem`：可见 `kmem:mm_page_alloc`、`kmem:kmalloc`、`kmem:kmem_cache_alloc`、`kmem:free` 等事件，以及页面分配/释放相关事件。
- `page_pool`：可见 `page_pool:page_pool_update_nid`、`page_pool:page_pool_state_hold`、`page_pool:page_pool_state_release`、`page_pool:page_pool_release`。
- `napi`：可见 `napi:napi_poll`、`napi:napi_poll_stall_detected`。
- `skb`：可见 `skb:consume_skb`、`skb:free_skb`、`skb:skb_copy_datagram_iovec`。

当前 available_events 输出中没有专门的 `napi_alloc_skb` 或分配失败事件。因此，若要直接统计该函数的 NULL 返回，需要动态 return probe，而不是依赖现成 tracepoint。

### 运行配置
实机 `/proc/config.gz` 返回：
- `CONFIG_TRACEPOINTS=y`
- `CONFIG_KPROBES=y`
- `CONFIG_DEBUG_INFO_BTF=y`
- `CONFIG_EVENT_TRACING=y`
- `CONFIG_FTRACE=y`
- `CONFIG_KPROBE_EVENTS=y`

### 运行符号
`/proc/kallsyms` 可见：
- `ffff8000812a3b00 T __alloc_skb`
- `ffff8000812a44c0 T napi_alloc_skb`

这证明当前运行内核的符号表中存在目标函数，具备进一步验证动态探测的基础。

### available_filter_functions
此前过滤查询没有列出 `napi_alloc_skb`。这不等于 KPROBE 不可用：`available_filter_functions` 是函数追踪器可用函数列表，并不等同于 KPROBE 可探测符号列表。目标函数已在 kallsyms 中可见，后续仍需通过只读检查确认 kprobe_events 接口状态；不得把函数追踪列表缺项当作 KPROBE 失败。

## 3. 当前判断

<确认>运行内核具备 KPROBES 与 KPROBE_EVENTS 配置，tracefs 存在，目标函数符号可见。</确认>

这已经满足继续设计 return probe 的主要前置条件，但还没有验证：
- `kprobe_events` 是否可写；
- 当前是否已有其他用户创建的动态探针；
- 当前 `tracing_on` 状态、`current_tracer` 和相关事件启用状态；
- 当前系统是否有正在运行、不可覆盖的 tracing 工作。

因此本轮**没有创建探针**，也没有改变任何 tracing 状态。

## 4. 下一步只读检查

请执行以下命令，读取现有状态。命令不写入任何文件：

```sh
T=/sys/kernel/tracing

echo "===== TRACEFS MOUNT ====="
mount | grep -E 'tracefs|debugfs'

echo "===== TRACING STATE ====="
for f in tracing_on current_tracer trace_options buffer_size_kb; do
    [ -r "$T/$f" ] && { echo "--- $f ---"; cat "$T/$f"; }
done

echo "===== EXISTING KPROBES ====="
if [ -r "$T/kprobe_events" ]; then
    cat "$T/kprobe_events"
else
    echo "kprobe_events not readable"
fi

echo "===== KPROBE PROFILE ====="
[ -r "$T/kprobe_profile" ] && cat "$T/kprobe_profile"

echo "===== ENABLED EVENTS ====="
find "$T" -path '*/events/*/enable' -type f -exec sh -c '
    for f do
        v=$(cat "$f" 2>/dev/null)
        [ "$v" = 1 ] && echo "$f"
    done
' sh {} +
```

如 `/sys/kernel/tracing` 与 `/sys/kernel/debug/tracing` 实际指向不同挂载实例，应分别记录；不要自行 mount/unmount。

## 5. 探针方案（尚未执行）

若只读状态确认没有现有任务冲突，下一步才考虑创建单个 return probe：
- 目标：`napi_alloc_skb`
- 事件：记录函数返回值 `$retval`
- 统计：短时间窗口内返回 NULL 的次数与总调用次数
- 运行窗口：建议先 20–30 秒，在复现网络收包/测试流量时进行
- 结束后删除本轮新增的唯一探针事件，并确认 tracing 状态恢复到原值。

注意：动态探针会改变 tracefs 配置并有少量运行开销，且函数是全局网络栈函数，不天然只对应 Panther 的 GMAC。若启用，需设计调用栈/调用者过滤或把测试窗口控制在其他网络流量极少的情况下。执行前必须向用户说明准确写入命令、持续时间、开销和恢复命令，并取得明确授权。

## 6. 结论

已从“内核模板具备能力”推进到“实机运行内核符号和 KPROBE 配置均已确认”。下一步只需先检查 tracing 现状，确保不覆盖现有任务，再决定是否申请执行一次短时 return probe。
