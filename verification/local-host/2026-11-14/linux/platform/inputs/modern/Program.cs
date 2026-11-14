using System.Runtime.CompilerServices;

int checks = 0;
void Check(bool result, string name) { if (!result) throw new Exception(name); checks++; }

Outcome ok = new Success(7);
Outcome bad = new Failure("native-error");
int Value(Outcome outcome) => outcome switch { Success s => s.Value, Failure => -1 };
Check(Value(ok) == 7 && Value(bad) == -1, "union/exhaustive-match");
Gate gate = new Open(3);
Check((gate switch { Open o => o.Count, Shut => 0 }) == 3, "closed-hierarchy");
List<int> values = [with(capacity: 8), 1, 2, 3];
Check(values.Capacity >= 8 && values.Count == 3, "collection-capacity");

// Force union values to escape through typed array storage; inspect allocation,
// without treating this small fixture as an application performance benchmark.
const int N = 2048;
Outcome[] boxed = new Outcome[N];
Tagged[] inline = new Tagged[N];
boxed[0] = new Success(0); inline[0] = new Tagged(0, 0);
long before = GC.GetAllocatedBytesForCurrentThread();
for (int i = 0; i < N; i++) boxed[i] = new Success(i);
long unionBytes = GC.GetAllocatedBytesForCurrentThread() - before;
before = GC.GetAllocatedBytesForCurrentThread();
for (int i = 0; i < N; i++) inline[i] = new Tagged(0, i);
long taggedBytes = GC.GetAllocatedBytesForCurrentThread() - before;
Check(Value(boxed[N - 1]) == N - 1 && inline[N - 1].Value == N - 1, "escaping-values");
Check(unionBytes > taggedBytes, "value-case-union-boxes-in-this-compiler");
GC.KeepAlive(boxed); GC.KeepAlive(inline);

var local = new AsyncLocal<string>(); local.Value = "request-context";
async Task<int> Suspended()
{
    await Task.Yield();
    Check(local.Value == "request-context", "asynclocal-after-yield");
    await Task.Delay(1);
    return 17;
}
Check(await Suspended() == 17, "suspend-resume");
using var canceled = new CancellationTokenSource(); canceled.Cancel();
try { await Task.Delay(100, canceled.Token); throw new Exception("no-cancel"); }
catch (OperationCanceledException) { checks++; }
try { await ThrowAsync(); throw new Exception("no-error"); }
catch (InvalidOperationException e) { Check(e.Message == "expected", "async-exception"); }
static async Task ThrowAsync() { await Task.Yield(); throw new InvalidOperationException("expected"); }
if (args.Contains("--aot")) Check(!RuntimeFeature.IsDynamicCodeSupported, "actual-native-aot");
Console.WriteLine($"modern-language checks={checks} union_value_case_bytes={unionBytes} tagged_bytes={taggedBytes} aot={!RuntimeFeature.IsDynamicCodeSupported}");

public readonly record struct Success(int Value);
public sealed record Failure(string Message);
public union Outcome(Success, Failure);
public closed record Gate;
public sealed record Open(int Count) : Gate;
public sealed record Shut : Gate;
public readonly record struct Tagged(byte Tag, int Value);
