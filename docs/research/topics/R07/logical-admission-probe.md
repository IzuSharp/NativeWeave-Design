# R07：并行形成的逻辑准入独立复现记录

状态：**Linux x64 普通消费与 NativeAOT 已实际执行；并行独立复现，无新增 Windows 执行；研究原型，无正式产品实现或契约接受。** 任务沿用 R07，设计依据为 D04，不建立新的任务体系。

## 并发恢复说明

本地实现与执行期间，另一会话同时完成并合并了 [Design PR #8](https://github.com/IzuSharp/NativeWeave-Design/pull/8)，合并 commit `3767f3c932ebf95bd82f6ed1c9bafc9eec1c5b1e`。现有权威研究入口为[已合并研究](logical-admission.md)，其 source `28f6cf7e6e4e80b9f32a92ad587a528d82911bd0` / run `43373306474` 已有 Windows/Linux 普通运行及 Native AOT 各653断言，并额外覆盖 managed exception 后 lease 归还。

本记录保留在获知该远端更新之前独立写成的源文件、逐条断言、NuGet PackageReference 消费与 Linux 结果。它是独立复现证据，不再声称首次填补 NS-01，也不以931/932与653的断言数量差异宣称更广覆盖。共享 source-lifecycle CI 不重复执行此同类 fixture，只运行新增 Database/Server 场景。D04 最新证据附录的 hash 为 `d527369dfd97a2d97ecd0930e25effc523791eb5e22586b1d9e18ac6f4aa31c9`；下文 c21e... 仍正确描述本地尝试当时的历史输入，不能改写原始执行记录。

## 1. 填补的具体缺口

此前 [R03 native slice 结果](../R03/native-slice-validation.md) 的 NS-01 明确指出：已有 SafeHandle 调用在 Dispose 期间仍保活，并不能证明逻辑关闭后新的业务调用会被拒绝。本次单独检验这一边界，未重跑旧 consumer 的 185 断言，也未重跑旧 Rust 单元测试。

结果符合已有 [R07 源码分析](report.md) 和 [D04 准入协议](../../../contracts/lifetime-v0.1.md)：在 native held 调用保持物理引用时，简单 `OwnedBuffer` 的 Dispose 后新 Sum 仍然可以执行；短 managed gate 候选则拒绝新的 Sum，先进入的调用正常完成，最后 native live counter 回到 0。负控制成功表示观察到了不足之处，不表示 SafeHandle 本身违反其物理生存期契约。

此前 R07-S01 的固定源码依据是 dotnet/runtime `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` 的 `src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs`：`DangerousAddRef` 与 `InternalRelease` 对 Closed/Disposed 和引用数的处理见原报告及 evidence.json。本次没有把那次源码阅读改标为新执行；实际执行的 SDK/runtime 身份由本次 `dotnet-info.stdout` 单独记录。

## 2. 固定输入与复用边界

复用 Design `c7e123a74405a92dc3de1ef450355b08d1c05ceb` 已迁移的 native 与 managed 包源码。runner 在复制前按原 `migration-map.json` 的 destination SHA256 核对，构建在临时目录，未修改旧迁移文件、manifest 或 hash。D04 当前参考内容 SHA256 为 `c21e14010397330ba08f41db91d438c98f190f018130a3429f7f58b07f135bcb`；它仍是 proposed/reference 内容，不因本实验自动被接受。

| 未修改的复用文件 | SHA256 |
|---|---|
| `experiments/native-slices/interop/native/Cargo.toml` | `1ec6048a2c40d4de73d59127db3cd4675bdf3fe43d04a20399dcae0cab51707d` |
| `experiments/native-slices/interop/native/Cargo.lock` | `e3e2ffee883d8ec7e0e3c2ca0c297f6ed6d17733c41c9f6df406491a6fa46f60` |
| `experiments/native-slices/interop/native/src/lib.rs` | `e4e632a1145a2148443fb795785dbc693305ca446a298bd840c2fe380187b5ef` |
| `experiments/native-slices/interop/managed/Bridge.cs` | `366f282bc9864e1bf72b4ef711774fb506a418555abceb73836cd249b28d7eef` |
| `experiments/native-slices/interop/managed/NativeWeave.Interop.Probe.csproj` | `f3568055889622ebff2b6b7369c647aadae96bd7a1d108a6ac0a09bac6fe8530` |

新代码在 `experiments/interop-admission/consumer/AdmissionBuffer.cs` 与 `Program.cs`。实际 `.nupkg` 由原 managed 项目打包，包含刚构建的同名 native 资产。新消费端仅有 `PackageReference Include="NativeWeave.Interop.Probe" Version="0.0.1"`，没有 ProjectReference。runner 核对包内与 AOT publish 内的 native 字节均与构建产物一致。

## 3. 受控执行时序与 oracle

每种运行模式均顺序执行 32 轮简单 SafeHandle 负控制和 32 轮短 gate 候选。每轮使用独立 owner，长度从 257 到 288；期望和由消费者按 native 的 `i % 251` 数据规则独立计算。既有 native 测试钩子是进程内共享信号，因此各轮串行执行，避免把上一轮的信号误认为下一轮。

1. 确认 native live counter 为 0，并 reset held 信号。
2. worker 线程调用真实 Rust `nw_buffer_sum_held`。controller 等待 native 的 entered 标志；不存在用 managed 假任务替代 native 进入的步骤。
3. worker 保持物理 lease，controller 同一线程顺序调用 Dispose 两次，再检查 worker 仍在途、SafeHandle 尚未 Closed、native live counter 仍为 1。
4. controller 在尚未 release held 调用前尝试新的 Sum。负控制必须实际返回正确 native 求和；候选必须抛出 ObjectDisposedException。
5. controller 释放 native held 信号并 join worker；原调用必须无错误地返回正确值。随后检查 owner 已物理 Closed、native live counter 为 0，再次 Dispose 后仍为 0。

native held 等待本身有 10 秒上限；controller 的 entered 等待与 join 各有 5 秒上限。超时记失败，不当作取消或成功。不使用 sleep 来猜测 native 是否已经取得 lease。stdout 保留每一条带 case、round、ID、expected、actual 的断言。

## 4. 候选实现及本次证据支持的语义

`AdmissionBuffer` 私有持有包内 `OwnedBuffer`。调用在同一个短 `lock` 中检查 `_closing` 并取得 `DangerousAddRef`，随后取 raw pointer，在锁外通过精确的 `LibraryImport` 签名调用 Sum 或 SumHeld，并在 finally 中 `DangerousRelease`。Dispose 在同一 gate 下把 `_closing` 置为 true，在锁外 Dispose owner；重复 Dispose 在 gate 内返回。

因此 Closed 与 Closing 的职责清晰：物理引用保持先进入调用的 native 内存有效；Closing 是新业务准入的拒绝点。测试在候选新调用抛异常前已经观察 owner 未 Closed 且 live=1，因此其拒绝不能被解释为“旧调用已退出、物理 owner 已释放”。代码没有持有 gate 执行 FFI、等待 native、调用用户代码或执行 native release。

此候选只针对本次同步、只读 native 求和。它没有实现 stop capability、callback 静默、异步退休、mutable-owner 串行化、父子所有权、终结器/卸载路径或取消协议；不能替代 D04 其余条款和 D05/D06。

## 5. 本次 Linux 原始结果

原始目录为 `experiments/interop-admission/evidence/linux-local-attempt-1/`，开始 `2026-11-13T05:49:31.714302+00:00`，结束 `2026-11-13T05:51:36.082463+00:00`。本次是在基线 commit 上的未提交研究工作区运行，`local_source_dirty=true`；执行输入原文与逐文件 hash 已保留，不能把它说成已经由某个新 Git commit 执行。SDK 11.0.100、Runtime 11.0.0、Rust/Cargo 1.100.0 和实际 Linux 信息见该目录工具链输出。

| 模式 | 真实执行结果 | 负控制 | gate 候选 | 结束资源 |
|---|---|---|---|---|
| `dotnet build` / `dotnet run --no-build`，均无 RID 参数 | 931 条断言通过 | 32/32 新 Sum 在 Dispose 后仍准入并返回正确值 | 32/32 新 Sum 被拒绝；旧调用返回正确值 | 每轮 live=0 |
| `dotnet publish -r linux-x64 -p:PublishAot=true` 后执行发布文件 | 932 条断言通过；额外检查 dynamic code 不受支持且未编译 | 32/32 同上 | 32/32 同上 | 每轮 live=0 |

合计是两个执行模式各 64 轮真实 held-call/Dispose 时序，共 128 轮；不将它宣传为穷尽所有竞态或所有 .NET 运行时。

| 真实制品 | SHA256 |
|---|---|
| native library | `889196ff36ad2e5c287aed56ca5a0ddddd3662051425c9a7b9ca37b1c836110b` |
| 本地 NuGet `.nupkg` | `8f2f482f5b70c1202f052911e9327eed7f971c9f6a847ecf64edcc75dc3ef079` |
| Linux NativeAOT `AdmissionProbe` | `a63b62d358d8290056643056e17a15c554a5d5dfc2f30f9a0d168e514a0b9ae5` |

原始二进制存于本地输出目录的 `binaries/`，包含无扩展名 Linux 可执行文件；每个文件长度与 SHA256 在 `result.json`。源仓库保存其 hash、原始输入和日志，不提交这些本地二进制，也没有本次补充复现的远端 binary artifact。不要把本地 hash 当作可永久下载的 CI 制品；PR #8 的主证据与 artifacts 有各自独立身份。原始 commands.json 记录每个命令、退出码、起止时间与日志 hash。

本地尝试执行的 runner SHA256 为 `4b796d14b107b240f491b24cdf70d90e7f98a4a5d324edf6f7af7df6bcfa3778`。尝试运行期间仅增强了之后版本 runner 的失败制品提前保存和“拒绝覆盖已有 attempt”行为；归档 runner SHA256 为 `b8c62dce7b4ea57b918afacb726857400119781bb46463f55183f9719c77147e`。消费端三份 C#/project 输入字节未变，旧 runner 原文仍在 `inputs/experiments/interop-admission/run.py`，没有重写其执行 hash。归档 runner 未再次执行；本地结果不冒充其他提交或 Windows CI 的证据。

## 6. 复现与后续边界

在 Rust 1.100.0、SDK 11.0.100 和 NativeAOT 构建前提满足的主机上运行：

```sh
python experiments/interop-admission/run.py --out artifacts/interop-admission-linux
```

Windows 可使用同一入口，runner 会选择 win-x64，但本补充 fixture 没有 Windows 执行结果。`--output` 是别名；每次使用新的输出目录，失败记录也保留。优先复用 PR #8 的现有双平台证据，不因本补充记录再次运行同等场景。

本机安装并使用过 Rust，所以结果不是 clean Rust-free host 部署证明。没有运行本候选的 Windows 新实验之前，不能用旧 Windows 185 断言替代。没有故障注入、GC/终结器压力、任意调度穷举或产品负载数据；不声称零成本、更快、完整关闭保证或产品可交付。

本研究增加了 NS-01 的真实反例与一个受控候选验证，保留 D04 的独立审查和正式验收门禁。R07 状态、registry acceptance 和 A/B Delivery 均不得由此自动升级。
