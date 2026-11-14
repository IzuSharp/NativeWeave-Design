# Repository and Execution Environment Verification

Date: 2026-11-12; time zone: America/Los_Angeles. Structured summary of the original observations: [repository-snapshot.json](repository-snapshot.json). This report states only the scope actually inspected.

## 1. The Three Official Repositories

| Repository | main commit at verification | Initial root directory | Permissions / operations in this round |
| --- | --- | --- | --- |
| [IzuSharp/NativeWeave](https://github.com/IzuSharp/NativeWeave) | `658ed6a410783de356a7b9b2cd6601336fff5148` | LICENSE only | pull/push were true; unchanged |
| [IzuSharp/NativeWeave-Design](https://github.com/IzuSharp/NativeWeave-Design) | `7034fb54490bb397379787c9b2da3609b393185f` | LICENSE only | pull/push were true; research branch created successfully |
| [IzuSharp/Plan](https://github.com/IzuSharp/Plan) | `ed6e8e8e1203bbe3149cfb49c418da81a9d9749d` | LICENSE only | pull/push were true; research branch created successfully |

Both documentation repositories already had main and an initial commit, so no empty-repository initialization on the default branch was needed. The research branch in each repository is `research/bootstrap-2026-11-12`, created from that repository's exact observed main commit. The original LICENSE was retained; permissions and protection rules were unchanged.

Permission metadata does not mean every write operation has succeeded. Branch creation actually succeeded; the results of commits, Draft PRs, and other operations are established by the final delivery record for this round and GitHub responses. The initial snapshot in this file deliberately retains the state at the time of each action.

## 2. Purpose of Reference Materials

The entry points, directories, references, and table organization of ArcForges Design/Plan were located and inspected; the README, traceability JSON excerpts, and task graph excerpts at a pinned snapshot were examined. **These were used only to understand document format and organization.**

The user subsequently clarified that "the reference specification is for its format, not its content." NativeWeave does not inherit its technical architecture, execution rules, acceptance policies, or business boundaries, and does not use them as the basis for this project's decisions. Reading DesktopPlatform code does not introduce that project as a dependency; technical evidence for the current candidate design primarily comes from independent upstream official source code.

Repository permissions and status from earlier conversations were used only as retrieval leads; the repository APIs were called again for verification in this round. The complete original prior context was not obtained. The current uploaded materials and the user's clarifications in this round are authoritative for requirements; no new constraints are added based on old summaries.

## 3. Capabilities Actually Available

- GitHub: reading repository metadata, contents, files at pinned refs, trees, and branches; research branch creation succeeded; tools for creating trees/commits, updating refs, and creating Draft PRs are available.
- Local: a Linux x86_64 shell, Python, Git, and GCC are callable. See the toolchain topic's evidence JSON for actual probes.
- No dedicated Windows or user Linux MCP acceptance tools were found. The current Linux container is not evidence of execution on Windows.
- `dotnet`, `rustc`, `cargo`, and `clang` were not found on PATH; this does not establish that they are absent from the entire disk, but this round produced no C#/Rust/AOT compilation or execution results.
- Three subagents can actually be delegated work; in this round they did handle the toolchain, domain source code, and preparation of the three graphs, respectively, and then cross-reviewed the root agent's candidate documents.

## 4. Scope That Can Actually Be Verified in This Round

Official materials, pinned source code, JSON/graph structure, Python research models, document references, and GitHub operations can be verified. Success in these areas cannot be converted into claims of Native AOT support, database transaction reliability, Windows success, or performance targets being met. Actual execution validation for phases A/B remains assigned to concrete tasks and is not replaced by stubs or JIT execution.
