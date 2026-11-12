# R27 — 可选 Rust Server Engine 的采用边界与 Adapter

日期：2026-11-12；packet0.1.1及baseline/hash见[evidence.json](evidence.json)。状态：已选择可实现的独立Engine架构；默认不因语言替换而启用Rust；产品Rust/C#/AOT、性能测试均未运行。规范同步至[D18](../../../server/hosting-and-streaming.md)。

## 1. 要解决的问题

Rust网络生态可用于特定协议、执行器整合或确有完整负载收益的场景，但C#开发者不应重写业务handler或管理Rust资源。研究重点是如何保持独立Engine边界、生命周期和资源预算，而不是为每个HTTP chunk增加不可控FFI开销。

设计决定：Kestrel仍为默认；可选Rust Server接受一个显式portable handler集合，复用Core handle/async/buffer契约，拥有自己的runtime与TLS。API不承诺任意ASP.NET middleware/HttpContext可移植。若未来GPU/媒体Engine加入，不会因此被迫引用Server/Tokio。

## 2. 固定证据与比较

| 项目 | 固定版本/commit | 实际阅读机制 |
| --- | --- | --- |
| Hyper | v1.12.0 / `7f67699ce32d717081deb7018b4da7d679277ac0` | HTTP1 connection graceful_shutdown125–149；Cargo features71–92 |
| Tokio | tokio-1.54.1 / `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` | mpsc bounded send765–825/reserve1070–1126 |
| Axum | axum-v0.8.9 / `c59208c86fded335cd85e388030ad59347b0e5ae` | serve run258–305/connection dispatch383–421 |

URL/blob/license与覆盖状态见[evidence](evidence.json)、[coverage](coverage.json)。Tokio/Hyper/Axum固定许可识别为MIT；Axum真实license路径为`axum/LICENSE`，根`LICENSE`不存在的查找未冒充成功。YetAnotherHttpHandler只借用已有interop专题已登记的限定证据来检查FFI成本/owner陷阱，本轮没有重新宣称读完该项目。

| 候选 | 选择 |
| --- | --- |
| 直接发布Hyper C API为NativeWeave公共ABI | 拒绝；Cargo明确unstable/no semver，稳定契约不能依赖未承诺的布局/函数面 |
| Axum完整路由/应用框架直接穿透到C# | 不作为公共层；路由/业务仍在C#，避免两套middleware/DI/序列化系统 |
| Tokio/Hyper Engine内部实现 + NativeWeave领域Adapter | 选择为可选实现路线；内部替换不影响Core ABI |
| 每次请求创建Tokio runtime、C#回调同步等待Task | 拒绝；启动/线程成本、重入死锁与关闭复杂性不可接受 |
| 批次/流式pull + boundedowned chunks | 选择；先明确复制与生命周期，再按证据增加zero-copy capability |

## 3. 从accept到关闭的真实调用链

Axum `WithGracefulShutdown.run`持有listener/make_service/signal。独立任务等待signal后drop watch接收端，accept loop通过`signal_tx.closed()`退出；每条连接克隆关闭观察者。连接任务使用Hyper connection future，并在signal分支调用`graceful_shutdown`；继续poll直到连接结束，最后drop其close receiver。run在不再accept之后等待所有close receiver退出。

Hyper HTTP1 graceful仅disable keep-alive；注释明确仍须poll future完成flush/shutdown。若C#宿主仅取消任务或dropRust future，不能声称已做协议graceful。Axum此处没有给NativeWeave强制总drain时限；D18需要外层monotonic deadline，超时转abort，并与Corecallback quiescence分开。

此阅读不覆盖所有Hyper HTTP2状态机、tower readiness/limits或RustTLS实现；这些是明确coverage缺口，不能把Rust语言内存安全当全栈关闭正确性的证明。

## 4. C# Handler 与异步FFI协议

常规C#默认使用Kestrel自己的HttpContext。只有愿意使用portable子集的应用选择`WeaveRequestHandler(WeaveHttpContext,CancellationToken) -> ValueTask`，context含有界copied headers、managed PipeReader/PipeWriter和预算lease。该API为设计草案，未编译。route/JSON工具继续使用编译期已知模型，不将Rust内部Request类型暴露到C#。

Rust实现形态（伪代码，非已编译API）：

```rust
// 生命周期/状态仅示意，具体wire由Core契约生成。
async fn serve_request(request: EngineRequest, budget: BudgetLease) {
    let operation = create_operation(request, budget);
    start_managed_handler(operation.id()).await;
    // body按credit拉取；terminal不等于可以释放cookie。
    await_terminal_and_transport_cleanup(operation).await;
    mark_native_quiescent();
}
```

正式ABI复用Core两阶段create/start；terminal callback只复制status与固定ErrorRecord，callback外完成协调器take_result一次取得owned结果。请求read返回owned chunk/EOF，单一pending read；response write borrowed input只在同步FFI入口有效，异步保存必须复制到已获budget的Rustowner。所有需要callback的工作都保持操作owner，不从GC/Drop推断已无回调。

终态可能先于资源retire可观察；native worker、callback与start/control/cancel registration全部静止后才能释放handle/cookie。managed `Task` continuation不得inline运行用户代码并同步阻塞Tokio线程。native内锁不跨调用任意managed handler；panic/error必须转稳定失败并保留cleanup，而非跨ABI unwind。

## 5. 字节预算与零复制的取舍

Tokio `send(value)`在等待`reserve`时已经拥有value，所以有界channel仍可有任意数量等待producer及其大payload。`reserve`的Permit可在未发送时drop归还容量，适合先取得slot再构造；但slot还不是byte credit。D18/R29选择有界metadata等待队列+分配前全局/请求字节credit，并把copy期间两边存活都计账。

首版Rust adapter允许每方向一次有界copy：native chunk复制到managed-ownedslab后立即释放nativeowner；输出进入Rust-ownedchunk后不保留managed指针。这个选择以可证明生命周期换取可测成本，保留未来显式lease零复制扩展。不能让普通ReadOnlyMemory指向已释放Rust allocation，或用长时间pin遮盖所有权缺陷。

每请求成本至少含metadata编码、dispatch、分块notification、cleanup控制调用；FFI crossing随`payload/chunk`增长。较大chunk降低调用数，却增加并发驻留内存与取消延迟。分别测TLS加密、HTTP framing、数据库IO与FFI/copy时间，避免把DB等待掩盖成“服务器性能相同”或只报空handler峰值。

## 6. TLS、平台与打包

Rust Engine内部负责唯一executor/transport；若它终止TLS，就不再在Kestrel外套一层TLS。证书reload、握手途中取消、ALPN/HTTP版本、close-notify、nativebuffer回收都进入B17/B22。采用代理终止只在显式可信proxy配置下成立。Kestrel端gRPC/MCP profile不自动移植到此Engine；需新的协议兼容证据，不能仅看有HTTP2就宣布支持。

包可单独安装、版本管理、能力拒绝；未安装Rust Server不影响managed应用。Windows/Linux RID的链接器、动态库解析、CRT/libc、TLS依赖和panic配置由独立包manifest固定。版本/能力不兼容在listen前拒绝，不能加载成功后到首请求才发生布局错误。

## 7. 研究决定与正式验收

Q15可关闭“默认用什么、何时允许引入Rust、是否重设计Core”的设计问题：Kestrel默认，Rust通过独立Engine与portable子集，推广必须有完整等价负载的证据或确实需要的独立能力。尚未测出Rust适用负载不是未形成架构选择，也不能被写成已经赢得性能对照。

B17输出独立engine、ABI适配和最小handler；B20验证cancel/completion/retire交错、scheduler重入与关闭；B23对齐协议/TLS/硬件/数据/错误语义测CPU、内存、尾延迟、crossings和copies；B24执行真实Windows/Linux AOT app加载与版本拒绝。所有运行证据当前not-run。

独立Review接口：R07/R08检查owned result与quiescence；R26检查默认managed路径不被增加wrapper/runtime依赖；R29检查copy时双份记账、字节credit死锁与slow reader；R17检查端到端比较不会只择最优Rust微基准。本作者不声称已接受自己的新设计。
