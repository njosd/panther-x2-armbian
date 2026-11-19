# Panther X2：NAPI skb 分配器版本差异与下一步只读取证设计（2026-11-19）

## 1. 研究目标

承接：
- `PANTHER-X2-KERNEL-CONFIG-CLOSURE-AND-STMMAC-RX-DIFF-20261119.md`
- `PANTHER-X2-ETHERNET-6.12.81-TEST-RESULTS-2026-11-16.md`

前一轮已确认：6.12.81 候选 STMMAC 普通 RX 的 `napi_alloc_skb()` 失败会增加 `rx_dropped`；运行时未发现 XDP/AF_XDP，且 60 秒相邻采样曾观察到 dropped 增长。本轮进一步检查内核网络核心分配器，而不是重复 STMMAC 主函数。

## 2. 精确源码对象

- 6.1.116：`unifreq/linux-6.1.y@5eb841b59d6ead6e264163785a634e78f0253c8e`
  - `net/core/skbuff.c` blob `e5436c5f52399290be27d3c40dbb95dcff63c774`
  - `include/linux/skbuff.h` blob `48a0219df1c4921f646af6b12bdb8ed603d7cba1`
- 6.12.81 候选：`ophub/linux-6.12.y-rockchip@661b2d8bf1284556f8876d5ed5fb80c64b22f94c`
  - `net/core/skbuff.c` blob `c3e1395d8ac5c43377ca0717ead756d530aaafa2`
  - `include/linux/skbuff.h` blob `7227069ce8c0a538289e4da6e9747aa7004d15be`

同样保留限制：6.12.81 候选源码 commit 尚未由运行 Image 唯一反推，以下为候选源码间比较。

## 3. NAPI skb 分配器的实现变化

### 6.1.116
驱动调用的内联 `napi_alloc_skb(napi, length)` 位于 `include/linux/skbuff.h`，它调用：
`__napi_alloc_skb(napi, length, GFP_ATOMIC)`

实际分配函数位于 `net/core/skbuff.c`，使用 per-CPU `napi_alloc_cache`：
- 对小/大缓冲区边界情况调用 `__alloc_skb()`；
- 通常使用 `page_frag_alloc_1k()` 或 `page_frag_alloc()`；
- 无可用 data 时返回 NULL；
- `__napi_build_skb()` 失败时释放 frag 并返回 NULL。

### 6.12.81 候选
`napi_alloc_skb()` 变为 `net/core/skbuff.c` 中的外部函数，内部设置：
`GFP_ATOMIC | __GFP_NOWARN`

其分配策略仍然是：
- 边界情况 `__alloc_skb()`；
- 常规情况 `page_frag_alloc_1k()` / `page_frag_alloc()`；
- data 分配失败返回 NULL；
- `__napi_build_skb()` 失败时 `skb_free_frag(data)` 并返回 NULL。

### 关键实现差异
- 6.1 的 `napi_alloc_skb` 是 header inline wrapper，6.12 是导出的 out-of-line 函数。
- 6.12 对 per-CPU `napi_alloc_cache` 访问增加 `local_lock_nested_bh(&napi_alloc_cache.bh_lock)` / unlock；6.1 对应路径直接访问 `this_cpu_ptr(&napi_alloc_cache)`。
- 6.12 显式加 `__GFP_NOWARN`；6.1 wrapper 传入 `GFP_ATOMIC`。
- 两者失败时都可能返回 NULL，且都使用 NAPI page-frag cache；本轮没有发现 6.12 把分配策略整体改为不同的高阶页分配路径。

解释：local_lock 是 NAPI per-CPU cache 并发访问保护变化，不能仅凭它认定会导致分配失败。两者分配失败的核心条件仍是分配器未能提供 skb head/data。

## 4. 6.12 构建模板的可观测能力

已锁定的 Ophub RK35xx `config-6.12` 模板启用：
- `CONFIG_KPROBES=y`
- `CONFIG_KPROBE_EVENTS=y`
- `CONFIG_FTRACE=y`
- `CONFIG_EVENT_TRACING=y`
- `CONFIG_TRACEPOINTS=y`
- `CONFIG_BPF=y`
- `CONFIG_BPF_SYSCALL=y`
- `CONFIG_DEBUG_INFO_BTF=y`

这些配置表明，构建模板具备较丰富的 tracing/kprobe/BPF 能力。它们不是当前运行系统已挂载 tracefs、相关符号可探测或配置与模板逐项一致的实机证据；需只读确认运行环境。

## 5. 下一步最小证据目标

直接证明 `napi_alloc_skb()` 是否返回 NULL，而不是继续通过系统总内存快照间接猜测。

建议先做一次**只读取证能力检查**，不创建 kprobe、不启用 tracing、不改变任何运行状态：

```sh
echo "===== TRACEFS ====="
for d in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    [ -d "$d" ] && echo "$d exists"
    [ -r "$d/available_filter_functions" ] && {
        echo "-- available_filter_functions --"
        grep -E '(^| )napi_alloc_skb$|(^| )__napi_alloc_skb$|(^| )__alloc_skb$|(^| )page_frag_alloc$|(^| )page_frag_alloc_1k$' "$d/available_filter_functions"
    }
    [ -r "$d/available_events" ] && {
        echo "-- relevant trace events --"
        grep -E '^(kmem|napi|skb|page_pool):' "$d/available_events"
    }
done

echo "===== KPROBE CONFIG ====="
zcat /proc/config.gz 2>/dev/null | grep -E '^(CONFIG_KPROBES|CONFIG_KPROBE_EVENTS|CONFIG_FTRACE|CONFIG_FUNCTION_TRACER|CONFIG_EVENT_TRACING|CONFIG_TRACEPOINTS|CONFIG_DEBUG_INFO_BTF)='

echo "===== SYMBOLS ====="
grep -E ' (napi_alloc_skb|__napi_alloc_skb|__alloc_skb|page_frag_alloc|page_frag_alloc_1k)$' /proc/kallsyms 2>/dev/null
```

注意：
- 上述命令只读取文件；不 mount、不写 tracefs、不加载模块。
- 若 tracefs 未挂载或某些文件不存在，原样记录，不尝试挂载或安装工具。
- `/proc/kallsyms` 地址可能被权限策略隐藏，但符号名仍可能可见。

## 6. 后续决策门槛

只有在确认函数符号和 kprobe event 能力后，才设计一个短时、限定接口/函数、自动清理的返回值探针，以统计 `napi_alloc_skb()` 的 NULL 返回次数。

该探针会写入 tracefs 并改变临时内核 tracing 状态，可能产生少量运行开销；必须先向用户说明具体操作、持续时间、清理命令和影响，并取得明确授权。本报告没有执行该操作。

如果无法安全观测返回值，则不盲目安装 bpftrace/perf，不修改内核或驱动；转而寻找现有内核日志/计数器可以支持的替代证据。

## 7. 当前结论

- STMMAC 6.1/6.12 普通 RX 的 skb 分配失败处理基本一致。
- 内核核心 NAPI skb allocator 的 API 形态和 per-CPU cache 并发保护有所变化，但两者均依赖 NAPI page-frag cache 并在分配失败时返回 NULL。
- 当前没有直接证据表明 6.12 allocator 的变化就是故障根因。
- 最有判别力的下一步是只读确认能否对 `napi_alloc_skb()` 返回值做短时观测；暂不执行探针。
