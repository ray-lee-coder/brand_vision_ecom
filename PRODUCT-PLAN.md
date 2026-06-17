# BrandKit · 产品规划与行动方案

> 版本：Product Plan v2.1
> 制定日期：2026-06-17
> 产品阶段：M0-A Compiler Spine
> 产品形态：Spec Files + CLI Executor + Agent Skill（四层架构，不上 Web/DB/协作）
> 产品执行基线：本文档（2026-06-17，不再讨论，进入执行）

## 交付说明

本文档基于三次 GPT 评审收敛。v2.0 方向通过（7/10），本轮为结构性收口，修正六个 P0 问题：

1. **缺少独立的 Product Facts 对象** — M0 必须引入，否则 M1 必然返工
2. **Channel 规则三状态源** — visual-spec 和 content-spec 不再包含平台规则，统一归入 `channels/*.yaml`
3. **内容 Pipeline 缺少生成器** — 不是纯规则引擎，必须有 Copy Generator（对称于视觉的 Image Slot）
4. **缺少 Spec 合并优先级** — 定义 Hard Constraints 与 Soft Preferences，冲突报错不静默覆盖
5. **M0 范围与 1-2 天不匹配** — 拆为 M0-A（Compiler Spine，1-2 天）和 M0-B（Campaign Kit，2-3 天）
6. **未验证"视觉内容同源"** — 增加编译后的 Campaign Message Plan，两条管线共享同一 Primary Benefit

---

## 一、Spec 所有权模型

六类输入文件，每类只有一个所有者：

```
brands/{brand}/brand-core.yaml         ← 品牌身份（色板/Logo/语气/宣称边界）
brands/{brand}/visual-spec.yaml        ← 视觉执行规则（密度/场景策略/摄影倾向）
brands/{brand}/content-spec.yaml       ← 内容执行规则（信息优先级/语气/表达结构）
brands/{brand}/products/{sku}.yaml     ← 商品事实（参数/宣称/来源/素材）
channels/{channel}.yaml                ← 平台规则（视觉+内容两区）
campaigns/{campaign}.yaml              ← 任务入口（选品牌/选商品/选渠道/描述输出）
```

运行时编译生成（不手工维护）：

```
.build/
├── resolved-task.json          ← 合并后的全量指令
├── message-plan.json           ← Campaign Message Plan（共享给双管线）
├── visual-scene.json           ← 视觉场景编译结果
└── validation-plan.json        ← 验证计划
```

### 1.1 `brand-core.yaml`

只拥有品牌规则——长期稳定、不因渠道变化的品牌资产。

```yaml
brand:
  name: Aether
  category: audio-tech
  positioning: premium personal audio for urban professionals

identity:
  keywords: [precise, calm, premium, technical]
  avoid: [cheap promotional tone, childish colors, noisy layouts, exaggerated claims]

colors:
  primary: "#111827"
  secondary: "#E5E7EB"
  accent: "#8B7355"
  background: "#F7F4EF"
  forbidden: ["#FF00FF", "#00FF00"]

typography:
  latin:
    heading: "Neue Haas Grotesk"
    body: "Inter"
  chinese:
    heading: "Noto Sans SC"
    body: "Noto Sans SC"

logo:
  file: assets/logo.svg
  min_size_px: 48
  clear_space_px: 24
  allowed_backgrounds: [light, dark]
  forbidden: [stretch, rotate, gradient_fill, low_contrast]

voice:
  tone: [restrained, precise, confident]
  avoid: [shouting, fake luxury, internet slang, unsupported superlatives]

claims:
  require_evidence: ["best", "first", "medical grade", "100%"]

references:
  approved_visuals: [assets/reference/kv-01.png]
  approved_copy: ["Silence, tuned with precision."]
```

### 1.2 `visual-spec.yaml`

只拥有品牌的视觉执行规则。**不含平台规则。**

```yaml
visual:
  default_ratio: "1:1"
  rendering_mode: hybrid

layout:
  density: low
  product_coverage: "45%-60%"
  headline_max_lines: 2
  safe_margin_px: 64
  logo_position: top-left

product_image:
  source_required: true
  preferred_asset_type: [transparent_png, high_res_packshot]
  shadow:
    enabled: true
    softness: medium
  retouching:
    allow: [background_cleanup, reflection, shadow]
    forbid: [changing_product_shape, changing_logo_on_product]

scene_policy:
  hero:
    html_dominant: true
    regenerate_background: false
  lifestyle:
    html_dominant: false
    regenerate_background: true
    preserve_product_asset: true
  detail:
    html_dominant: true
    macro_generation: optional
```

### 1.3 `content-spec.yaml`

只拥有品牌的内容执行规则。**不含平台规则。**

```yaml
content:
  default_language: zh-CN
  tone_source: brand-core.voice

message_hierarchy:
  primary_benefit: "沉浸降噪"
  secondary_benefits:
    - "轻量佩戴"
    - "长续航"
    - "低延迟连接"

copy_rules:
  headline:
    style: concise
    avoid_question: true

claim_rules:
  require_source_for: [battery_hours, decibel_reduction, waterproof_rating]
  forbidden: ["全网第一", "永久有效", "医学级", "100%无损"]
```

### 1.4 `products/{sku}.yaml`

商品事实——M0 一级对象。campaign-task 只引用 `product_ref`。

```yaml
product:
  id: x1-headphones
  name: Aether X1
  category: wireless-headphones

facts:
  noise_reduction:
    value: 42
    unit: dB
    source:
      type: lab_report
      ref: docs/x1-noise-test.pdf
    status: verified

  battery:
    value: 38
    unit: hours
    conditions: ANC off, 50% volume
    source:
      type: product_spec
      ref: docs/x1-spec.pdf
    status: verified

assets:
  packshot: assets/products/x1/packshot.png
```

### 1.5 `channels/{channel}.yaml`

拥有平台规则，同时包括视觉和内容两个分区。唯一的状态源。

```yaml
channel:
  id: tmall

visual:
  ratios: ["1:1"]
  product_coverage: "50%-70%"
  safe_margin_px: 48
  text_density: low

content:
  product_title:
    max_chars: 60
  bullets:
    count: 5
    max_chars_each: 28
  forbidden_patterns: [unsupported_superlative]
  style: direct_conversion
  allowed: [parameter, benefit, promotion]
  avoid: [overly literary tone]
```

### 1.6 `campaigns/{campaign}.yaml`

只选择渠道和输出，不重新定义渠道默认规则。

```yaml
campaign:
  name: 618-launch
  brand_ref: brands/aether/brand-core.yaml
  product_ref: brands/aether/products/x1.yaml
  objective: product_launch
  audience: urban_commuters

outputs:
  visual:
    - type: hero
      channel: tmall
      format: png
    - type: cover
      channel: xiaohongshu
      format: png
  content:
    - type: product_title
      channel: tmall
    - type: bullet_points
      channel: tmall
    - type: note
      channel: xiaohongshu
    - type: title
      channel: xiaohongshu

# 显式覆盖（只有此处允许）
override:
  headline_max_chars: 14
```

---

## 二、Spec 合并优先级

系统必须知道哪个字段是硬规则、哪个是默认值、哪个可以覆盖、哪个冲突应报错。

### 2.1 约束类型

| 类型 | 行为 | 示例 |
|------|------|------|
| Hard Constraint | 不可被任务覆盖，冲突报错 | 禁用词、Logo变形、品牌禁用色、无证据宣称 |
| Soft Preference | 允许任务或渠道调整 | 标题长度、构图偏好、语气强度、背景风格 |

### 2.2 编译优先级

```
全局安全政策                     ← 最硬（广告法、平台禁止项）
  > Brand Hard Rules
    > Product Facts
      > Channel Hard Rules
        > Campaign Requirements
          > Brand Soft Preferences
            > Channel Soft Preferences
              > Renderer Defaults   ← 最软
```

硬规则冲突时必须报错，不静默覆盖。例如：

```
Campaign 要求："全网第一"
Brand Core：禁止无证据最高级
Product Facts：无对应证据

结果：构建失败，输出明确冲突报告。
```

---

## 三、产品架构

### 3.1 整体架构

```
[输入层]                              [编译层]                              [执行层]                    [产物层]

brand-core.yaml                       Compiler                              Visual Pipeline
visual-spec.yaml                        ↓                                   ├─ HTML Compositor
content-spec.yaml                  campaign-task                            ├─ Image Generator slot
products/{sku}.yaml                + resolved-task.json                     └─ L1/L2 Verify            PNG / HTML
channels/{channel}.yaml            + message-plan.json                               │
campaigns/{campaign}.yaml                                                        Content Pipeline          Markdown
                                       ↑                                   ├─ Fact Resolver           / JSON
                                   Spec 合并                               ├─ Message Planner
                                   优先级引擎                                ├─ Copy Generator
                                                                             ├─ Claim Validator
                                                                             ├─ Channel Validator
                                                                             └─ Provenance Reporter
```

### 3.2 两条管线统一方法论

视觉和内容都遵循同一结构：

```
确定性编译 → 小范围生成 → 确定性验证
```

| 阶段 | 视觉 Pipeline | 内容 Pipeline |
|------|--------------|--------------|
| 确定性编译 | HTML Compositor（品牌 Token + 布局 + 素材） | Fact Resolver + Message Planner + Context Compiler |
| 小范围生成 | Image Generator（仅标记槽位） | Copy Generator（受约束的文案生成） |
| 确定性验证 | L1 CSS 断言 / L2 OCR / 像素差异 | Claim Validator / Channel Validator / Provenance Reporter |

### 3.3 Campaign Message Plan（跨管线共享）

编译后生成，视觉和内容共享同一份：

```yaml
campaign_message:
  campaign_theme: quiet_precision
  primary_benefit:
    id: adaptive_noise_reduction
    statement: 在通勤噪声中保持清晰聆听
  secondary_benefits:
    - long_battery
    - lightweight_comfort
  proof_points:
    - claim_ref: facts.noise_reduction
    - claim_ref: facts.battery
  call_to_action:
    tmall: 立即了解
    xiaohongshu: 查看通勤实测
```

视觉 Pipeline 使用：campaign theme、primary benefit、headline 候选、proof point
内容 Pipeline 使用：同一份 message plan

---

## 四、产品成功定义

### 4.1 北极星指标

> **从任务输入到首份被接受的品牌合规物料包的总耗时，以及复用后的边际成本递减。**

### 4.2 核心指标

| 指标 | 含义 | 验证方法 |
|------|------|----------|
| First Campaign Cost | 包含品牌和商品建档的总耗时 | 实测 |
| Repeat Campaign Cost | 复用 Spec 后的后续活动耗时 | 实测 |
| Break-even Campaign Count | 第几次活动开始优于纯 Prompt | 计算 |
| Time to Approved Kit | 整套物料被接受的时间 | 实测 |
| Cost per Approved Artifact | 单份可用物料的模型+人工成本 | 实测+计算 |

### 4.3 五类修改任务指标

针对同一 Campaign 执行五类修改，分别记录：

1. 改品牌主色
2. 改核心卖点
3. 删除一项无证据宣称
4. 将天猫表达改为小红书表达
5. 替换视觉背景

记录：模型调用次数、人工操作次数、非目标区域是否变化、完成耗时、是否仍通过验证。

### 4.4 平台差异可检查

天猫 vs 小红书的差异必须由 Channel Validator 输出结构化差异报告，不是人工说"感觉不一样"。

---

## 五、Roadmap

### M0-A：Compiler Spine

**周期：** 1-2 天

**目标：** 建立可靠的数据主干——所有输入能被稳定解析、合并、检查和重建。

**交付：**
- `brand-core.yaml`（Aether 示例）
- `products/x1.yaml`（商品事实）
- `visual-spec.yaml` + `content-spec.yaml`
- `channels/tmall.yaml` + `channels/xiaohongshu.yaml`
- `campaigns/618-launch.yaml`
- Spec 合并与冲突检测脚本
- `resolved-task.json`（编译后中间产物）
- `message-plan.json`（Campaign Message Plan）
- 1 视觉 + 1 内容最小输出（验证编译正确性）
- 内部薄 Skill（识别任务 → 生成 campaign-task → 调用 CLI → 展示输出）

**退出标准：**
- [ ] 同样输入产生相同 resolved-task.json
- [ ] Hard Constraint 无法被覆盖，冲突报错
- [ ] 缺少事实的宣称构建失败
- [ ] 所有输出都能追溯到来源字段
- [ ] 一条命令可复现

---

### M0-B：One Brand Campaign Kit

**周期：** 2-3 天（接 M0-A 之后）

**目标：** 跑通双 Pipeline 物料包，验证"视觉内容同源"。

**交付：**
- 天猫 1:1 主图（PNG + HTML 预览）
- 小红书 3:4 封面（PNG + HTML 预览）
- 天猫商品标题 + 五点描述（Markdown）
- 小红书标题 + 正文（Markdown）
- Cross-Pipeline Message Plan 一致性验证
- v1/v2 基线对照报告
- L1 视觉验证 + Content Claim Checker

**退出标准：**
- [ ] 视觉和内容共享同一份 message-plan.json
- [ ] 品牌硬规则 100% 通过
- [ ] 禁用宣称 100% 拦截
- [ ] 一条命令可复现
- [ ] 与纯 Prompt 基线比较，至少减少一轮返工

---

### M1：Content Governance & Provenance

**周期：** 3-5 天

**目标：** 让内容管线不只是 Prompt 模板——建立事实、宣称、来源和渠道验证闭环。

**聚焦一个问题：** 内容管线能否基于可信商品事实，稳定地产出可追溯、可验证、跨渠道差异化的内容。

**交付：**
- 2-3 个 SKU 的商品事实 Schema
- Fact Resolver + Message Planner + Context Compiler
- Copy Generator（受约束文案生成）
- Claim Validator + Channel Validator
- Claim Provenance 报告（每句文案标注事实来源）
- A/B 草稿
- 内容差异报告（天猫 vs 小红书结构差异）

**不包含（与 v2.0 主要缩减）：**
- Instagram / 京东平台扩展
- 视觉密度检查
- 复杂品牌语义评分

**退出标准：**
- [ ] 每项客观宣称都能追溯事实
- [ ] 无来源宣称拦截率 100%
- [ ] 天猫和小红书内容在结构上明确不同（Channel Validator 输出差异报告）
- [ ] 人工修改轮数低于纯 Prompt 基线
- [ ] 换 SKU 无需修改代码

---

### M2：Visual Hybrid Generation

**周期：** 3-5 天

**目标：** 让视觉管线不退化成 HTML 模板器——建立确定性合成与生成式槽位的混合能力。

**交付：**
- 产品前景固定（不改商品本体）
- 独立背景生成槽（仅 lifestyle 等标记 `gen_policy` 的槽位）
- 背景替换（同产品不同背景场景）
- 局部重生成
- 输出版本记录

**退出标准：**
- [ ] 改背景只调用一次图像模型
- [ ] 产品像素保持不变
- [ ] 改文案不触发图像模型
- [ ] 改尺寸不触发图像模型
- [ ] 至少两个场景可用

---

### M3：Skill Distribution

**周期：** 2-3 天

**目标：** 让非 CLI 用户通过 Agent 完成任务。M0 已有内部薄 Skill 做 Dogfooding，M3 做可分发产品。

**交付：**
- Claude Code SKILL.md
- Codex / OpenClaw 兼容入口
- 安装文档 + 错误处理
- 示例品牌包（Aether 完整）
- 兼容性测试

**先决条件：** M1 和 M2 至少完成一个，CLI 内核经过至少 2 个品牌完整验证。

---

## 六、产品形态（固定四层）

```
Skill / Plugin              ← 用户入口（M0 薄版，M3 正式分发）
    ↓
Spec Files                  ← brand-core / visual-spec / content-spec / product-facts / channels / campaign
    ↓
CLI Executor                ← Compiler → 合并/冲突检测 → Pipeline 编排 → 验证 → 输出
    ↓
Artifacts                   ← resolved-task.json / message-plan.json / PNG / HTML / Markdown / JSON
```

不做：Web 后台、Figma 插件、素材管理系统、多人协同、审批流、复杂数据库、SaaS 账户体系、AI 工作台、内容中台。

---

## 七、防漂移规则

1. **数据源收口** — Brand / Product / Channel / Campaign 各只有一个所有者。visual-spec 和 content-spec 不含平台规则。
2. **两条管线统一方法论** — 确定性编译 → 小范围生成 → 确定性验证。视觉和内容都遵循。
3. **核心产品价值可验证** — 不是"都读取 Brand Core"就叫同源，必须共享同一份 Product Facts + Campaign Message Plan + Claim References。
4. **Hard Constraint 冲突报错不覆盖** — 编译失败比静默安全。
5. **不以输出格式数量衡量进展** — M0 验证的是数据主干的可靠性，不是输出文件的多少。
6. **不以社区仓库集成数量衡量进展** — 复用的是方法论，不是代码复刻。
7. PPTX/MP4/docx 移出主干，不作为产品里程碑。
8. 每次变更只更新一个状态源：本文档为产品基线。
