# R29 — 字节预算、背压、取消与 graceful shutdown

日期：2026-11-12。packet0.1.1及固定输入hash见[evidence.json](evidence.json)。研究状态partially_evidenced；有限Python模型实际运行，真实.NET/Tokio/native/NativeAOT未运行。设计已写[D18](../../../server/hosting-and-streaming.md)，Q16建议在独立审查后按设计已解决关闭。

## 1. 要建立的保证

负载与恶意慢端不能导致无限body、producer等待、nativechunk、callback或shutdown等待。保证对象分为应用逻辑字节、metadata计数、nativeownedbytes与平台实际RSS；不能用一个channel capacity或request body总长度替代全部指标。

非目标：以有限模型证明任意真实调度；把取消等同物理停止；给所有部署规定同一个RSS数值；本轮实现整个流框架。

## 2. 关键源码调用链

| 固定源码 | 观察 | 设计含义 |
| --- | --- | --- |
| Tokio1.54.1 `bounded.rs` send765–825/reserve1070–1126 | send持有value等待reserve；cancel可dropvalue；未用Permit drop返容量 | 先credit再分配，限制等待者；不能只把channel改bounded |
| Kestrel11 `Http1Connection.cs`110–155 | input/output完成取消RequestAborted；Abort还poison body | body EOF与transport完成/abort必须分开 |
| Kestrel11 `TransportManager.cs`119–193 | unbind/accept-loop结束→close→abort fallback→dispose | listener、handler、nativecallback及buffer不是同一终点 |
| Hyper1.12 HTTP1 conn125–149 | graceful要继续poll | 必须有总drain deadline与完成观察 |

SHA/URL/blob均在evidence；本轮只读这些范围。KestrelHTTP2/3、内核socket、TLS、真实allocator未完全研究，见[coverage](coverage.json)。许可证固定识别MIT；无上游实现复制。

## 3. 选择的资源算法

统一budget协调器同时限制：活动connection、HTTP2stream、应用request、metadatawaiter、每请求payload、全局managed/nativepayload、activeupload及DBlease。固定上限配置不是性能保证；引用D18 profile只是可复现实验起点。

获得credit是允许分配/retain的线性化点。只把item从queue移到consumer不能返credit；必须等最后owner释放。native→managed或managed→nativecopy在两份buffer同时存活时双份计费。取消pendingwaiter归还reservations；取消in-flightconsumer只发意图，不归还仍被访问内存的credit。request完成但native尚未retire的bytes仍占budget。

全局/每请求两层资源不能“各拿一半后无限等待”。实现选择单协调器原子授予/取消，或全try-acquire失败时rollback；copy保留有界slack且一次申请两侧预算，禁止满credit状态互相等待copyroom。metadata等待队列有界且做租户公平；溢出在读取业务body前429/503，不创建额外大buffer来保存拒绝前输入。

pull提供背压：消费者只请求已有credit的最大字节数；read最多一项pending，responsewrite只一项pendingflush，释放ownedchunk/advance后才可继续。异步FFI结果按Corecallback外take_result取得；callbackcontext在native/managed所有义务静止前不得释放。默认安全adapter允许有界copy，不暴露会逃逸的nativeMemory跨await。

## 4. 有限模型的实际结果

[credit_model.py](credit_model.py)是本轮原创、可独立运行的逻辑模型。三producer尺寸1/2/2、全局credit3、queuecapacity1、单consumer，状态包括waiting/reserved/materialized/queued/consuming/done；cancelin-flight只记录意图，consumerrelease才返credit。

复现命令：`python docs/research/topics/R29/credit_model.py > docs/research/topics/R29/experiment-result.json`，exit0，stderr为空。环境Python3.12.14、Linux6.18.57 x64/glibc2.41。为完整记录D12要求，最终结果经instrumented wrapper重新执行，实际argv、UTC起止时间和原始流hash在[run-manifest.json](run-manifest.json)，没有补造第一次运行的时间。脚本与stdoutSHA256在evidence的run_manifest；[原始结果](experiment-result.json)保留完整版本及限制。

实际枚举282个reachable states、895个transitions、8个terminal states。每个状态满足 `allocated <= reserved <= 3`、queue<=1、consumer<=1；取消正在消费的item不丢其credit。所有状态存在某条可完成路径。反例同时展示：capacity1、chunk4，queue一个+3个已构造payload的等待producer，保留16单位，而capacity×chunk只有4。

这只是有限状态安全与存在性可完成路径，不证明任意scheduler公平、真实wake-up不会丢失、OS流量不会永久停滞、nativecopy预算或RSS上限。模型允许抽象原子资源转移，正式实现必须用真实同步原语与竞态测试兑现；不能把模型pass转换成Tokio/.NET/AOT已通过。

## 5. 取消、半关闭、期限与drain

正常body EOF只终止输入方向，仍可生成response；TCP半关闭/HTTP2reset由transport判定，不能只见read0就一律判请求成功或abort。headers未提交时可写规范错误，已提交后只终结stream；终结不证明客户端读到所有bytes。未读完body提前响应只允许受限drain，超过时限关闭/重置，避免无限吞攻击者数据。

总request deadline以monotonic时钟计算，排队、DB等待、body与response共同消耗；progress/chunk不续总时间。子deadline取较小剩余额度。DBCOMMIT入线后用独立commitdeadline记录确认或Unknown，HTTPtoken不能改写效果。

关闭先readiness=false/停止admission，再listenerstop，等待已接受工作至drain deadline；超时abort。nativecallbackquiescence、取消注册释放与controlcall计数仍须完成，无法完成则记录故障隔离并保留owner，不通过free活内存保证准时退出。重复stop共享关闭结果；exporter有最后单独小预算。

## 6. 成本、平台与正式验证

每个creditlease/cancelwaiter有metadata成本，应按活动上限预留/有界分配；不要为每个retry创建Task或timer。较大chunk节省crossings却增驻留和cancel延迟。RSS还含GC、pool、nativeallocator碎片、线程栈、TLS/H2/kernelbuffers；需要观测斜率和稳定平台而不是一次快照。

| 既有任务 | 必须兑现的反例/证明义务 |
| --- | --- |
| B16 | 分配前credit、byte与count边界、overflow、boundedwaiter；取消reserve/queue/consume每个窗口；partialconsume、slowclient、未读body、半关闭 |
| B17 | copy双份计账、Rustownedchunk与managedslab转移、panic/超时、callbackretire；nativeallocator计数 |
| B20 | admissionclose与completionrace、drain/abort/retire、COMMITUnknown、exporter故障；monotonicdeadline不重置 |
| B22/B23 | Windows/Linux AOT真流量；24h/72h连接churn、取消风暴、资源趋势；logicalbytes/RSS/CPU/尾延迟分项 |

交叉Review：R12核对pin/owner与bytecredit；R07/R08检查retire；R26/R27验证transport完成语义；数据库R21核对Unknown。实现状态保持not-run，设计选择无需等待全部产品测试才成立。
