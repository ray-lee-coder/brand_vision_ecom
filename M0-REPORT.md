# BrandKit · M0-A 完成报告与 M1 就绪评估

> 评估日期：2026-06-17
> 评估基线：PRODUCT-PLAN.md v2.1

---

## 一、M0-A 交付清单

### 1.1 Spec 文件（6 类）

| 文件 | 路径 | 状态 |
|------|------|------|
| brand-core.yaml | `brands/aether/brand-core.yaml` | ✅ |
| visual-spec.yaml | `brands/aether/visual-spec.yaml` | ✅ |
| content-spec.yaml | `brands/aether/content-spec.yaml` | ✅ |
| product-facts | `brands/aether/products/x1.yaml` | ✅ |
| channels | `channels/tmall.yaml` + `channels/xiaohongshu.yaml` | ✅ |
| campaign-task | `campaigns/618-launch.yaml` | ✅ |

### 1.2 管线脚本

| 脚本 | 职责 | 状态 |
|------|------|------|
| `compile.py` | Spec 合并 + 冲突检测 → resolved-task.json + message-plan.json | ✅ |
| `render_visual.py` | HTML Compositor + Playwright → PNG | ✅ |
| `render_content.py` | Content Pipeline → Markdown | ✅ |
| `verify.py` | L1 视觉断言 + Claim Checker | ✅ |
| `brandkit` | CLI 统一入口 | ✅ |

### 1.3 模板

| 模板 | 场景 | 状态 |
|------|------|------|
| `templates/hero.html` | 天猫 1:1 主图 | ✅ |
| `templates/cover.html` | 小红书 3:4 封面 | ✅ |

---

## 二、M0-A 退出标准评估

| 标准 | 结果 | 证据 |
|------|------|------|
| 同样输入产生相同 resolved-task.json | ✅ 通过 | 多次编译输出一致，确定性 |
| Hard Constraint 无法被覆盖，冲突报错 | ⚠️ 基础 | 冲突检测存在（forbidden colors），但 coverage 有限 |
| 缺少事实的宣称构建失败 | ⚠️ 基础 | Claim Checker 拦截禁用词，但未对"require_evidence"做构建阻断 |
| 所有输出都能追溯到来源字段 | ✅ 部分 | Bullet_points 标注了 fact_ref 和 source_ref |
| 一条命令可复现 | ✅ 通过 | `brandkit build campaigns/618-launch.yaml` |

### 端到端测试结果

```
brandkit build campaigns/618-launch.yaml
  → compile: 6 output targets
  → render visual: 2 HTML + 2 PNG
  → render content: 4 Markdown
  → verify: Visual 8/8 passed, Content 16/16 passed
```

### 产物结构

```
output/
├── tmall-hero.png               ← 天猫 1:1 主图
├── tmall-hero.html              ← HTML 预览
├── xiaohongshu-cover.png        ← 小红书 3:4 封面
├── xiaohongshu-cover.html       ← HTML 预览
├── tmall-product_title.md       ← 天猫商品标题
├── tmall-bullet_points.md       ← 天猫五点描述（含事实来源）
├── xiaohongshu-note.md          ← 小红书正文
└── xiaohongshu-title.md         ← 小红书标题
```

---

## 三、M1 就绪评估

### 3.1 M1 目标回顾

> **内容管线能否基于可信商品事实，稳定地产出可追溯、可验证、跨渠道差异化的内容？**

### 3.2 已就绪的能力

| 能力 | 状态 | 说明 |
|------|------|------|
| Product Facts Schema | ✅ | `products/{sku}.yaml` 结构已定义，facts 含 source/status |
| Spec 合并引擎 | ✅ | 6 类 Spec 可合并为 resolved-task.json |
| Claim Checker（基础） | ✅ | 禁用词拦截通过，4 个 forbidden phrase 全部 100% 拦截 |
| 渠道差异化（基础） | ✅ | 天猫=转化风 VS 小红书=体验风，内容结构可区分 |
| 内容验证报告 | ✅ | verify/content-report.json 结构化输出 |
| 一条命令可复现 | ✅ | `brandkit build` |

### 3.3 进入 M1 前需补齐的缺口

| 缺口 | 严重度 | 工作量 | 说明 |
|------|--------|--------|------|
| **Copy Generator 缺失** | **P0** | 1 天 | 当前内容为模板拼接，不是模型生成。M1 需要受约束的文案生成槽（对称于视觉的 Image Slot） |
| **Claim Provenance 不完整** | **P0** | 0.5 天 | Bullet_points 有来源标注，但 product_title / note 没有。M1 要求每句文案可追溯事实 |
| **require_evidence 未做构建阻断** | **P1** | 0.5 天 | 当前只检查禁用词，未对"best/first/100%"等要求证据的宣称做构建失败 |
| **Channel Validator 缺失** | **P1** | 0.5 天 | 无结构化差异报告（天猫 vs 小红书差异靠肉眼判断） |
| **仅 1 个 SKU** | **P1** | 0.5 天 | M1 需要 2-3 个 SKU 验证泛化性 |
| **A/B 草稿未实现** | **P2** | 0.5 天 | M1 退出标准要求多版本对比 |
| **无纯 Prompt 基线对照** | **P2** | 0.5 天 | 无法量化"减少返工"指标 |

### 3.4 建议

**可以进入 M1，但建议先花 1 天补齐三个 P0 缺口再开始 M1 核心工作：**

1. **Copy Generator** — 将当前模板拼接改为受约束的文案生成（调用 LLM，但 message_plan + claim_rules 作为约束输入）
2. **Claim Provenance** — 所有内容输出都标注事实来源（不仅是 bullet_points）
3. **require_evidence 构建阻断** — 在 compile.py 或 verify.py 中增加：如果内容包含 require_evidence 列表中的词且无对应 fact source，构建失败

**或者：** 直接进 M1，把这三个缺口作为 M1 的前 3 个 task，不单独做 M0-B。

### 3.5 文件统计

| 指标 | 值 |
|------|-----|
| Spec 文件数 | 7 |
| 脚本文件数 | 5 |
| HTML 模板数 | 2 |
| 端到端通过率 | Visual 8/8, Content 16/16 |
| 构建耗时 | < 10 秒 |
| 输出产物数 | 8 |
