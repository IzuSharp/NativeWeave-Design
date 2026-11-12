# EXP-ASYNC-QUIESCENCE-001：取消结果不等于资源静默

状态：**研究模型已实际执行；非产品实现验证**。作者root；2026-11-12。源码[model.py](model.py)，实际结果[result.json](result.json)。

## 问题和反例

一个native operation可能仍有完成callback，C#侧已经对应用发布了Canceled结果。若Dispose只检查Task终态便释放callback context，则native稍后进入callback会访问已释放的上下文。

本模型枚举一项operation、一次native callback、一次取消请求、一个可选的调用lease及Dispose的有限交错。负控制模型探索226个状态（遇到安全反例即剪枝，不是未经剪枝的完整状态空间），产生以下反例：

1. Dispose关闭新调用入口。
2. 对应用发布取消结果。
3. Native完成并排入callback。
4. 只依据已终态而回收context。
5. callback进入并解引用context，产生access_after_free。

## 候选修复在模型内的结果

候选回收条件再要求native quiescence确认，以及活动call lease为零。完整遍历得到159个可达状态、9个回收状态，没有访问已释放对象、重复终态发布或双重释放反例。

这不是通过无限等待“满足安全”：模型确实存在回收终态。但只检查存在回收状态不构成活性证明，任何真实调度最终是否推进仍需公平性/通知/关闭协议证明。

## 假设

取消事件只抽象为结果publication，没有建模CancellationTokenRegistration自身回调、context lease和注销等待；native quiescence不替代managed取消来源的静默。状态转换按顺序一致的原子步处理；publish抽象成正确CAS；native在quiescence确认后不再发callback；callback义务保留到返回；Dispose与call admission互斥。真实实现必须分别实现这些假设，不能用模型中的atomic step替代机器内存序或GCHandle协议。

未覆盖：多操作、多callback、重入、start尚未返回、取消注册同步执行、重复恶意通知、ABA/代际溢出、丢失通知、弱内存、deadlock、C#/Rust类型与ABI、性能、实机AOT。

## 重现

```bash
python3 experiments/async-quiescence/model.py
```

脚本检查负控制必须找到反例、候选模型的安全计数以及非零可回收状态。退出码0只代表这些有限检查成功。结果保存Python/OS/架构和模型SHA256。后续R15可将更完整协议表达为TLA+/Loom等合适模型；不要求单纯增加工具数量。
