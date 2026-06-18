# BrandKit gstack 多角色目标与方案复评

> 日期：2026-06-18  
> 评审范围：产品意图、`PRODUCT-PLAN.md`、Beta Recovery 实现、当前工作树与发布证据  
> 角色：CEO / Product、Engineering Manager、Developer Experience、Strict Reviewer  
> 结论：**方向对齐，Beta 暂不放行；保持范围，转入 Beta Release Truth 收敛。**

工具状态：gstack 的 Codex skills 安装有效，本次四类评审流程均可执行。当前本地版本为 `1.29.0.0`，上游提示 `1.58.1.0` 可用；由于本地 gstack 仓库含已验证的 Codex 兼容修复，而升级流程会重置该工作树，本次未执行破坏性升级。该维护项不影响本报告结论，但应另行完成补丁迁移后再升级。

## 1. 执行结论

BrandKit 当前意图是合理且一致的：先作为开源/研究项目，把“品牌约束下的电商视觉与内容编译”验证到个人和小团队可用、有效、可靠；只有在真实使用证据成立后，才讨论生产级改造。

本轮不应增加多租户、Web UI、审批流、数据库、队列、SLO 或通用模型平台。当前问题不是生产能力不足，而是 **Beta 自己定义的发布契约尚未全部兑现**。

Recovery 已显著修复底层可信度：六类 schema、运行隔离、manifest 下游消费、品牌中立模板、第二品牌 fixture、五类离线修改边界均已有自动化证据。但“41 个测试通过、5 个 campaign 构建成功”不能等价为 Beta 可发布。当前仍有发布接口失真、安全边界、文档与真实行为冲突、确定性/在线路径/CI/非作者使用证据缺口。

**统一决策：HOLD SCOPE，NOT CLEARED。** 不扩产品范围，先让当前承诺成为一个可复现、可试用、可判定的 Beta 候选版本。

## 2. 意图与目标对齐

### 2.1 正确的目标层级

1. 当前最高目标：个人/小团队可用的 Beta，不是生产级系统。
2. 当前核心假设：结构化品牌、产品、渠道与 campaign 约束，能让视觉和内容产物更一致、更可追溯，并降低局部修改成本。
3. 当前成功证据：真实用户能独立完成首次构建，产物达到可用阈值，局部修改边界成立，失败可诊断，关键过程可复现。
4. 后续生产决策：只有 Beta 真实使用证明“有用且可靠”后才启动，不作为本轮预埋工程。

### 2.2 当前路线的主要偏差

Recovery 主要证明了“编译器管线比以前可靠”，但产品最高风险已经转移到“输出是否真的有用、用户是否能独立使用、发布承诺是否真实”。下一阶段若继续只增加内部契约测试，会产生边际收益递减。

因此路线应从：

```text
继续加固内部实现
```

切换为：

```text
冻结可复现 RC
  -> 修正公开接口与文档
  -> 补齐确定性和在线路径证据
  -> 非作者 clean-clone 使用与产物验收
  -> Beta prerelease 决策
```

## 3. 多角色评价

### 3.1 CEO / Product

**判断：产品方向 8/10，计划可信度 5/10，使用价值证据 4/10。**

做对的部分：

- 问题边界清楚：不是通用内容平台，而是品牌约束编译器。
- 生产级能力明确延期，符合开源/研究阶段资源约束。
- Beta 退出标准覆盖可靠性、隔离、事实约束、修改成本和非作者验收，方向正确。
- 第二品牌和五类修改任务开始触及产品假设，而非只验证代码存在。

主要问题：

- `PRODUCT-PLAN.md` 自称唯一产品状态源，但当前 Gate 表仍是 Stage 1 PARTIAL、Stage 2 FAIL、Stage 3 NOT STARTED，与 Recovery 和 evidence report 冲突。
- 计划中的实现清单与实际进度没有同步，导致“什么已经完成”无法从权威文档可靠判断。
- 自动证据证明了边界，不证明产物质量。当前渠道差异报告仍有多项 informational miss，平台适配价值尚需人工验证。
- “只剩非作者验收”这一判断过早。按产品计划自己的 11 项退出标准，确定性、在线路径、远端 CI 和发布接口仍未闭合。

产品建议：保持定位，不增加功能；把下一里程碑定义为“一个陌生用户能从固定 commit 独立得到可评估产物”，而不是继续宣布组件完成。

### 3.2 Engineering Manager

**判断：架构方向 7/10，恢复质量 7/10，发布工程 3/10。**

工程优势：

- 六类 active contract 已进入运行时校验。
- campaign-scoped run root 与 manifest 下游消费已建立运行所有权。
- 并发隔离、缺失声明产物、provider 响应结构等关键失败已有回归测试。
- 41 个测试在项目目录和 clean copy 均通过；5 个 campaign 离线构建通过。
- 五类修改任务在隔离 workspace 中记录 before/after hash 和变更类别。

工程阻断：

1. 公开 CLI 的 `render`、`verify`、`validate` 直接子命令引用只在 `build` 分支初始化的变量，实际以 unbound variable 失败；帮助与 Skill 仍公开这些入口。
2. `--run-id` 未限制路径分隔符或规范化结果，值被直接拼入 `.build/runs` 和 `output/runs`，存在路径逃逸写入风险。
3. manifest 创建/写入异常被 `compile.py` 捕获为 warning 后仍返回成功，与 manifest 作为运行所有权基础的设计冲突。
4. `read_manifest()` 对缺失或损坏 manifest 返回空对象，显式 manifest 流程可能退化为隐式发现，未做到严格失败关闭。
5. 修改证据中的 `actual_model_calls` 固定写为 `0`，不是调用层观测值，因此不能证明精确调用预算。
6. 确定性标准要求同输入 PNG 字节一致，但当前 modification runner 使用 `--skip-png`，未形成双运行 PNG checksum 证据。
7. 本地分支领先远端 12 个提交且还有大量未提交修改；当前证据对应工作树，不对应不可变 commit/tag。
8. CI workflow 只存在本地提交历史，远端默认分支查询不到当前 workflow 运行，尚无 Ubuntu/macOS 的当前候选版本证据。

工程建议：先形成一个可提交、可 CI、可重放的 RC，再做人验；否则人验结果无法绑定到可发布版本。

### 3.3 Developer Experience

**判断：总体 4/10，首次成功时间尚未证明。**

| 维度 | 评分 | 说明 |
|---|---:|---|
| Getting Started | 4/10 | README 把 API key 放在前置条件并先展示在线构建，不适合作为低风险首次体验 |
| Installation | 4/10 | README 手写安装两个包，没有使用已锁定的 `requirements.txt` |
| CLI discoverability | 4/10 | help 公开了不可用的直接子命令；仓库没有安装裸 `brandkit` 命令 |
| Error quality | 6/10 | build 主路径诊断已有改善，但 direct command 和 manifest 仍有误导性失败 |
| Documentation accuracy | 3/10 | README、SKILL、输出目录、测试入口、渠道范围和路线状态多处过期 |
| Agent usability | 3/10 | `SKILL.md` 使用裸 `brandkit`、失效的 `validate`，并声明尚不存在的抖音/Instagram 支持 |
| Release/community readiness | 2/10 | README 声称 MIT，但仓库没有 LICENSE 文件；当前版本未形成远端 RC |

具体冲突：

- README 的安装命令遗漏 `jsonschema`、`pytest`，与 `requirements.txt` 不一致。
- README 只运行旧的 `tests/test_audit.py`，没有引导完整门禁。
- README 目录树仍展示旧 `output/{campaign}` 和单测试文件结构。
- `SKILL.md` 用裸 `brandkit`，但实际入口是 `bash scripts/brandkit`。
- `SKILL.md` 指示直接运行当前失效的 `brandkit validate`。
- README 中存在损坏文本 `Copーテキスト Generator LLM`。
- README 声称 MIT，但无实际许可证文件，开源意图没有法律载体。

DX 建议：Beta 首次路径默认从 offline 开始；在线调用必须显式，并在用户已经看到离线成功后再引导。首次使用协议应只有一条权威命令和一个明确的输出定位方法。

### 3.4 Strict Reviewer

#### P1：Beta 放行前必须处理

1. **CLI 公开接口与实现不一致**  
   `scripts/brandkit:40-68,146-172,191-209`：直接 `render/verify/validate` 使用未初始化运行上下文，帮助和 Skill 却将其视为受支持接口。

2. **调用方可控 run ID 可逃逸运行目录**  
   `scripts/brandkit:26-27,84-90`、`scripts/run_context.py:23-36,108-111`：未校验 `run_id`，应采用字符 allowlist，并验证 resolve 后仍位于声明根目录下。

3. **发布候选不是不可变版本**  
   当前 `main` 比 `origin/main` 超前 12 个提交，并含大量未提交 Recovery 修改。evidence report 使用“commit 加未提交修改”描述，无法作为可重放发布证据。

4. **权威计划状态与实际证据冲突**  
   `PRODUCT-PLAN.md:544-552` 与 Recovery 表、evidence report 不一致，违反文档自身的单状态源规则。

5. **Beta 退出标准 4、8、10、11 未取得所声明证据**  
   PNG 确定性未测；模型调用数为硬编码；当前候选无远端双 OS CI；在线 happy path、超时、限流和 provider error 未完整记录。

6. **开源许可证声明不成立**  
   `README.md:145-147` 声称 MIT，但仓库没有 LICENSE 文件。

#### P2：应在非作者验收前处理

1. manifest 写入失败只告警并继续，损坏 manifest 被当作空对象，应在显式 manifest 流程失败关闭。
2. README 和 SKILL 的命令、依赖、目录和渠道支持范围必须与真实实现统一。
3. `docs/*.pdf` 是内容为 dummy evidence 的 ASCII 文本文件，虽已不再被新 fixture 引用，仍可能被误认为真实证据；应删除或明确迁移到 synthetic fixtures。
4. `init` 只创建空目录且不在帮助中，不能称为可用初始化流程；要么补齐最小 scaffold，要么不作为公共命令。
5. offline 首次体验应先于在线默认，避免新用户在未理解成本和 provider 配置前触发网络调用。

## 4. Beta 退出标准复评

| # | 标准摘要 | 当前状态 | 判定依据 |
|---|---|---|---|
| 1 | clean checkout 仅凭 README 首次离线构建 | **未通过** | 无非作者记录；README 依赖和首条路径不准确 |
| 2 | 六类 spec 严格 schema/引用诊断 | **自动通过** | active schema 与 Recovery 回归测试 |
| 3 | 两品牌、至少四 campaign 无代码修改构建 | **自动通过** | Aether + Acme，5 campaign offline pass |
| 4 | 相同离线输入字节一致，含 PNG | **未通过** | 缺双运行 PNG checksum；现有 runner 跳过 PNG |
| 5 | 有序/并发运行隔离 | **自动通过** | run isolation 集成测试与 campaign-scoped path |
| 6 | 依赖/素材/provider 按契约失败 | **部分通过** | 多数契约已测；公开直接 CLI 与 manifest 失败语义仍有缺口 |
| 7 | 客观宣称由 facts/evidence 驱动 | **契约通过** | synthetic fixture 证明契约，不代表真实产品背书 |
| 8 | 五类修改边界与精确调用预算 | **部分通过** | 离线边界 5/5；在线预算未执行，调用数非真实观测 |
| 9 | 非作者通过第二品牌 rubric | **未通过** | rubric 空白，尚无实名 trial |
| 10 | Ubuntu/macOS 当前候选 CI | **未通过** | workflow 本地存在，远端当前候选无运行证据 |
| 11 | 在线 happy/failure matrix，无隐式降级 | **未通过** | schema 异常有测试；happy path、超时、限流、provider error 证据不全 |

严格口径为：**3 项通过，2 项部分通过，6 项未通过。** 这不否定 Recovery 的价值，而是说明 Recovery 与 Beta Release Gate 是不同层级。

## 5. 改进工作计划

### R6：Release Truth 与公开接口收敛

目标：让所有公开承诺都能在固定版本上重放。

1. 修复 direct `render/verify/validate` 的运行上下文，或从 help/README/SKILL 删除未支持接口；不要保留“看似存在”的命令。
2. 校验 `run_id`：非空、字符 allowlist、禁止路径分隔符，并验证目标路径未离开 run roots。
3. manifest 写入和显式读取失败关闭，补损坏/缺失 manifest 回归测试。
4. 统一 README、SKILL、CLI help、目录结构、依赖安装和支持渠道。
5. 添加真实 MIT LICENSE；清理或迁移 dummy PDF/AppleDouble 文件。
6. 更新 `PRODUCT-PLAN.md` Gate 状态和实施清单，以它作为唯一产品状态源。
7. 消除 `git diff --check origin/main` 发现的尾随空白。
8. 将全部 Recovery 修改收敛为一个可审查 RC commit，禁止 evidence 指向“commit + working tree”。

**R6 出口：** clean clone 按 README 离线成功；help 中每个公开命令均有 CLI 回归；当前 SHA 的 Ubuntu/macOS CI 全绿。

### R7：Beta Evidence 闭环

目标：证明“有用且可靠”，而不只是“自动化管线能跑”。

1. 增加同 OS/Python、同输入双运行测试，比较所有约定产物 hash，包含 PNG。
2. 在 provider 调用边界埋设可验证计数，不再由 evidence runner 填写常量。
3. 用受控 provider/stub 和一次允许的真实 trial 覆盖在线 happy path、无凭据、超时、限流、畸形响应、provider error 与无隐式降级。
4. 在固定 RC SHA 上执行至少一位非作者 clean-clone trial；若保留 reliability plan 的 primary + backup 要求，则统一所有文档为两位，否则统一为一位。
5. 人工评分至少两份视觉、两份内容，并记录渠道适配、事实正确性、品牌一致性、实用性和局部修改数。
6. 将渠道差异的 informational miss 纳入人工产品判断：允许技术上非阻断，但必须证明输出仍达到可用阈值。

**R7 出口：** 11 项 Beta 标准全部有绑定到同一 RC SHA 的证据，rubric 完整，release decision 才可改为 CLEARED。

### 明确不做

- 不做生产级多租户、鉴权、数据库、队列、SLO、审计平台。
- 不新增渠道、输出格式或模板数量来制造进度。
- 不做 Web UI、审批流、素材管理或 SaaS 包装。
- 不为未来生产场景提前构建通用 provider/framework abstraction。

## 6. 最终路线建议

```text
Recovery R1-R5
  -> R6 Release Truth（接口、文档、安全、RC、CI）
  -> R7 Beta Evidence（确定性、在线矩阵、非作者使用、产物质量）
  -> GitHub prerelease Beta
  -> 观察真实使用效果
  -> 再决定是否进入生产级改造
```

本轮路线不需要推翻。需要调整的是“完成”的定义：从内部实现完成，提升为公开接口真实、版本可复现、陌生用户可独立使用、产物达到验收阈值。只有这四项同时成立，Beta 才算发布，而不是仅仅构建成功。
