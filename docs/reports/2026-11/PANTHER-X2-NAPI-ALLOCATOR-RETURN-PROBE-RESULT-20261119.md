# Panther X2：napi_alloc_skb() 返回值短时探针结果（2026-11-19）

## 1. 实验目的

直接验证当前运行的 Linux 6.12.81 内核中，napi_alloc_skb() 是否在观察窗口内返回 NULL，以检验 skb 分配失败是否可能解释先前记录的 RX dropped 现象。

本实验只针对该函数返回值；不修改驱动、内核、网络配置或 DMA 参数。

## 2. 实验前状态与授权

用户明确授权进行 napi_alloc_skb 短时 return probe 实验。

此前只读核对已确认：
- tracefs 位于 /sys/kernel/tracing，与 /sys/kernel/debug/tracing 为同一实例；
- tracing_on=1；
- current_tracer=nop；
- 原有 kprobe_events 为空；
- 原有事件均未启用；
- 原有 buffer_size_kb 为 7 (expanded: 1408)；
- napi_alloc_skb 在 kallsyms 中可见；
- 运行内核启用 KPROBES、KPROBE_EVENTS 和 EVENT_TRACING。

## 3. 探针注册与过滤

成功注册唯一临时 return probe：

r:panther/napi_alloc_skb_ret napi_alloc_skb retval=$retval

事件格式确认返回值字段为：
- field:u64 retval
- size=8
- unsigned

过滤器成功设置为：

retval == 0

启用前事件 enable 为 0。实验启用期间只启用该事件，没有改变全局 tracer、trace buffer 大小或其他 trace event。

## 4. 30 秒采集结果

| 指标 | 结果 |
|---|---:|
| 采集窗口 | 30 秒 |
| kprobe_profile hit count | 62 |
| kprobe_profile missed count | 0 |
| trace 中 NULL 返回事件 | 0 |
| 采集后事件 enable | 0 |

trace snapshot 显示：
entries-in-buffer/entries-written: 0/0

kprobe_profile 采集前为 0/0，采集后为 62/0。结合 retval == 0 事件过滤器未记录任何事件，本窗口没有观察到 NULL 返回。

## 5. 清理与状态恢复

用户执行删除命令：

echo '-:panther/napi_alloc_skb_ret' >> /sys/kernel/tracing/kprobe_events

删除后 kprobe_events 无该探针条目。原有全局状态仍为：
- tracing_on=1
- current_tracer=nop

没有关闭全局 tracing、清空 trace buffer、修改 buffer 大小或安装软件。

## 6. 结论分级

### 已验证
1. 当前运行内核成功注册并执行了 napi_alloc_skb() return probe。
2. 30 秒内记录 62 次探针命中，missed count 为 0。
3. 该窗口内没有捕获到 retval == 0 的返回事件。
4. 临时探针已删除，原 tracing_on/current_tracer 状态保持不变。

### 不能据此推出
1. 不能证明 napi_alloc_skb() 在所有时间、所有内存压力和所有流量条件下都不会失败。
2. 该函数是全系统网络栈函数，探针不只覆盖 Panther GMAC；当前窗口也没有按调用者归属到 GMAC。
3. 30 秒、62 次调用属于有限样本，不能排除低频或条件触发的分配失败。
4. 不能据此认定整个 RX 路径正常，也不能把历史 netdev RX dropped 归因于或排除于其他原因。

### 当前判断
本次观察不支持“当前窗口内 napi_alloc_skb() 返回 NULL 导致丢包”的假设。该分配器候选降级，不继续重复采样；如后续有新的内存压力/丢包同步证据，再重新评估。

## 7. 对主线的影响与下一步

仓库回溯已明确：Panther 当前 DHCP 故障主线是 TX 外发边界，而 RX dropped 是独立待解释支线，不能用 RX 计数支线替代主线。

现有证据仍为：
- Linux 本机 outgoing capture 可见 DHCP Discover；
- TX 驱动完成计数和 MAC MMC 计数在同一启动周期曾保持一致；
- hEX 与持续监听的 iMac 未见对应外发帧；
- 这些证据尚不能证明报文越过 GMAC RGMII TXC/TXD 引脚或由 PHY 从 MDI 发出。

因此后续优先回到同一个 DHCP Discover 的 Panther 与 hEX 双端同步被动关联；不重跑 ping、DHCP 全流程或 MAC loopback，不写 PHY、不重启接口、不修改配置。若需要主动触发 DHCP Discover，必须另行说明并取得授权。
