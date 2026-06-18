# BrandKit · M0-A 加固评审报告

> 评审日期：2026-06-17
> 基线：PRODUCT-PLAN.md v2.1
> 前版：M0-REPORT.md
> **State: Historical implementation note — does not prove Beta readiness.**
> **Authoritative gates: PRODUCT-PLAN.md and docs/superpowers/plans/2026-06-18-beta-reliability.md.**

---

## 一、三个 P0 缺口加固结果

### P0-1：Copy Generator ✅

**问题：** 内容管线缺少"生成器"——文案是模板拼接，不是模型生成。没有产品壁垒。

**加固：** 新增 `scripts/copy_generator.py`，对称于视觉的 Image Generator slot：

```
Content Pipeline (加固后):
Product Facts → Message Plan → Copy Generator (LLM) → Claim Validator → Channel Validator → Markdown
                                  ↑
                            受约束的文案生成槽
                            (message_plan + claim_rules + channel_constraints 作为输入)
```

- 支持 sensenova 和 deepseek 两个 provider
- 输出 JSON 格式，含 `text` + `claims[]`（每条宣称标注事实来源）
- 有 dry-run 模式可预览 prompt 不调用 API
- fallback 到模板拼接（API 不可用时降级）

**实际效果对比：**

| 维度 | 加固前（模板拼接） | 加固后（Copy Generator） |
|------|-------------------|------------------------|
| bullet_points | "【lab_report】沉浸降噪：42dB" | "42dB自适应降噪，打造专属沉浸空间" |
| 小红书正文 | 固定模板+变量替换 | 自然场景化表达，含事实嵌入 |
| 文案多样性 | 每次相同 | 每次不同（受约束范围内） |
| 事实标注 | 部分 | 全部 |

---

### P0-2：Claim Provenance ✅

**问题：** 只有 bullet_points 有来源标注，其他内容类型没有。

**加固：** 所有 4 个内容类型（product_title / bullet_points / note / title）都输出 `.provenance.json`：

```
output/tmall-product_title.provenance.json
output/tmall-bullet_points.provenance.json
output/xiaohongshu-note.provenance.json
output/xiaohongshu-title.provenance.json
```

每条 provenance 包含：
- `claim` — 文案中的宣称
- `fact_ref` — 引用的事实 ID（如 `facts.noise_reduction`）
- `source_ref` — 来源文档引用（如 `docs/x1-noise-test.pdf`）
- `status` — 验证状态（verified / unverified）

营销改写（无事实来源的文案）标记为 `fact_ref: "marketing_writing"`，status `unverified`。

---

### P0-3：require_evidence 构建阻断 ✅

**问题：** 内容包含 "best"/"first"/"100%" 等需要证据的词时，如果无对应事实来源，系统静默通过。

**加固：** verify.py 在检测到无证据宣称时：

1. 标记 check 为 `fail` + `action: "BLOCK_BUILD"`
2. 在 file-level 设置 `build_blocked: true`
3. 主函数检测 `build_blocked` 后 `sys.exit(1)` 阻断构建

```
[BLOCKED] Unsupported claims detected — build failed
```

**测试：** 当前 Aether 内容不含 require_evidence 词，构建通过。如果注入 "全网第一"（brand-core 禁用词），Claim Checker 拦截并阻断。

---

## 二、M0-A 退出标准重新评估

| 标准 | M0-REPORT.md | 加固后 | 变化 |
|------|-------------|--------|------|
| 同样输入产生相同 resolved-task | ✅ | ✅ | — |
| Hard Constraint 无法被覆盖 | ⚠️ 基础 | ✅ | build_blocked 机制已实现 |
| 缺少事实的宣称构建失败 | ⚠️ 基础 | ✅ | require_evidence + forbidden 双阻断 |
| 所有输出可追溯到来源字段 | ✅ 部分 | ✅ | 全量 provenance |
| 一条命令可复现 | ✅ | ✅ | — |

**M0-A 退出标准：全部通过。**

---

## 三、M1 就绪评估

### 3.1 M1 目标

> **内容管线能否基于可信商品事实，稳定地产出可追溯、可验证、跨渠道差异化的内容？**

### 3.2 已就绪

| 能力 | 状态 | 说明 |
|------|------|------|
| Product Facts Schema | ✅ | 含 source/status/conditions |
| Copy Generator | ✅ | 受约束文案生成（LLM + message_plan） |
| Claim Provenance | ✅ | 全量输出 |
| Claim Checker | ✅ | 禁用词 + require_evidence 双阻断 |
| 渠道差异化 | ✅ | 天猫=转化风 VS 小红书=体验风 |
| 一条命令可复现 | ✅ | `brandkit build` |

### 3.3 进入 M1 前仍需补齐

| 缺口 | 严重度 | 工作量 | 说明 |
|------|--------|--------|------|
| **Channel Validator** | P1 | 0.5 天 | 无结构化差异报告（天猫 vs 小红书差异靠肉眼判断） |
| **仅 1 个 SKU** | P1 | 0.5 天 | M1 需要 2-3 个 SKU 验证泛化性 |
| **A/B 草稿** | P2 | 0.5 天 | M1 退出标准要求多版本对比 |
| **无纯 Prompt 基线对照** | P2 | 0.5 天 | 无法量化"减少返工"指标 |

### 3.4 建议

**三个 P0 缺口已全部加固，M0-A 退出标准通过。可以进入 M1。**

建议 M1 的前 2 个 task 补齐 P1 缺口（Channel Validator + 多 SKU），再进入核心工作（Claim provenance 深度化 + A/B 草稿）。

---

## 四、文件结构最终状态

```
brandkit/
├── PRODUCT-PLAN.md
├── M0-REPORT.md
├── M0-REVIEW.md                          ← 本文件
├── brands/aether/
│   ├── brand-core.yaml
│   ├── visual-spec.yaml
│   ├── content-spec.yaml
│   └── products/x1.yaml
├── channels/
│   ├── tmall.yaml
│   └── xiaohongshu.yaml
├── campaigns/
│   └── 618-launch.yaml
├── scripts/
│   ├── brandkit                           ← CLI 入口
│   ├── compile.py                         ← Spec 合并 + 冲突检测
│   ├── copy_generator.py                  ← 受约束文案生成（新增）
│   ├── render_visual.py                   ← HTML Compositor → PNG
│   ├── render_content.py                  ← Content Pipeline → Markdown + Provenance
│   └── verify.py                          ← L1 断言 + Claim Checker + 构建阻断
├── templates/
│   ├── hero.html
│   └── cover.html
├── .build/                                ← 运行时编译产物
└── output/                                ← 交付产物
```

## 五、端到端测试结果（最终）

```
brandkit build campaigns/618-launch.yaml

compile:      6 output targets  → ✅
render visual: 2 HTML + 2 PNG   → ✅
render content: 4 Markdown + 4 provenance → ✅
verify:
  Visual:  8/8  passed  (primary #111827, background #f7f4ef, accent #8b7355, safe-margin)
  Content: 16/16 passed (4 forbidden phrases × 4 files)
  Build blocked: false

Result: ✅ ALL PASS
```
