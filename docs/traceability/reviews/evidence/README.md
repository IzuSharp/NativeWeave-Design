# 独立审查原始结果

以下JSON由toolchain_verification的独立审查过程产生，整合者逐字节复制留档。它们不是产品接受manifest，也不应作为C#/Rust或Native AOT运行证明。

| 文件 | 含义 |
| --- | --- |
| [nativeweave-independent-validator-review.json](nativeweave-independent-validator-review.json) | 首轮25组结构/合成证据检查，24组达到预期；一项正控制使用旧日志数组格式而被拒绝 |
| [nativeweave-independent-evidence-followup.json](nativeweave-independent-evidence-followup.json) | 修正为stdout/stderr日志schema后的13组检查，全部达到预期 |
| [nativeweave-validator-final-followup.json](nativeweave-validator-final-followup.json) | 最终validator上的依赖commit/hash变化、路线选择、路径与身份字段复查 |
| [async-quiescence-independent-review.json](async-quiescence-independent-review.json) | 对root有限模型的独立复跑输出，包含假设与未证明范围 |

完整发现、修复和复查说明见[toolchain-review.md](../toolchain-review.md)。合成subject、重复字母hash等属于测试夹具，不表示存在对应Git提交或已接受证据。

