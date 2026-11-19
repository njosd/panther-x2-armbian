# Panther X2：TRACE 缓冲区空状态确认（2026-11-19）

## 1. 实机只读输出

用户执行：
```sh
cat /sys/kernel/tracing/trace
```

返回：
```
# tracer: nop
#
# entries-in-buffer/entries-written: 0/0   #P:4
#
# [trace header fields]
```

## 2. 结论

- 当前 tracer 为 `nop`。
- trace buffer 当前记录数为 `0/0`，即 0 条现存记录、0 条写入记录。
- 此前 `tracing_on=1`，但当前没有启用 tracepoint、没有注册 kprobe、没有 function tracer；本次读取也确认没有历史 trace 记录需要保存。
- 两个 tracefs 路径此前已确认是同一实例。

因此，当前 trace buffer 是干净基线。没有清空 buffer，也没有修改 tracing 状态。

## 3. 可进入探针设计阶段，但尚未执行

目标是对全局函数 `napi_alloc_skb()` 建立单个 return probe，记录返回值并只保留 NULL 返回事件。预计使用 kprobe event return probe 的 `$retval` fetcharg，并对返回值字段设置等于 0 的事件过滤器。正式执行前必须验证该内核的 kprobe event parser 接受该字段类型和过滤语法。

注意：
- 该函数服务于全局网络栈，不仅是 Panther GMAC；如无法可靠按调用者过滤，采集窗口内应尽量避免其他接口流量，并同步记录测试流量。
- 探针注册与事件 enable 会写入 tracefs，改变临时内核 tracing 状态，虽不修改网络/驱动配置，仍需用户明确授权。
- 当前 `tracing_on=1` 应保持原样；不切换 tracer、不改变 buffer size、不清空 buffer。
- 采集后只禁用并删除本次新增的事件；不能执行全局 `echo 0 > tracing_on`，不能重置其他选项。
- 在写入前再次读取原值，采集结束后逐项核对恢复。

## 4. 状态

已验证：
- trace buffer 0/0。
- current_tracer=nop。
- tracing_on=1。
- kprobe_events 为空。
- 没有启用 trace events。

尚未验证：
- 当前内核是否允许对 `napi_alloc_skb` 注册 return probe（符号存在，但仍可能受 kprobe blacklist/架构限制）。
- return probe 的 `$retval` 字段能否按 0 正确过滤。

本轮未创建探针、未启用事件、未修改 tracefs 状态。
