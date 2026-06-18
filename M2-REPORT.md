# BrandKit · M2 完成报告

> 报告日期：2026-06-17
> 基线：PRODUCT-PLAN.md v2.1
> 前序：M1-REPORT.md
> **Status: Historical implementation note — does not prove Beta readiness.**
> **Authoritative gates: PRODUCT-PLAN.md and docs/superpowers/plans/2026-06-18-beta-reliability.md.**

---

## 一、M2 交付清单

### 1.1 HTML 前景/背景分离

两个模板（hero, cover）重构为双层架构：

```
body
├── .background-layer          ← 可独立替换/生成
│   ├── 静态模式: CSS color/gradient from brand spec
│   └── 生成模式: SVG gradient (placeholder) / image file (API)
│       z-index: 0
│
├── .foreground-layer          ← FIXED — 从不修改
│   ├── .logo                  品牌标识
│   ├── .headline              标题文案
│   ├── .subtitle              副标题
│   └── .product-slot img      ← 始终从 product facts assets 加载
│       data-asset-source="product_facts"
│       z-index: 1
│
└── .accent-bar                z-index: 2
```

**原则：** 产品像素始终不变。改背景不影响产品图片的 URL 或像素。

### 1.2 背景生成器

`scripts/background_generator.py` — 对称于 Content Pipeline 的 Copy Generator：

| 组件 | Content Pipeline | Visual Pipeline |
|------|-----------------|----------------|
| 确定层 | Fact Resolver + Message Planner | HTML Compositor (brand tokens + product) |
| 生成槽 | Copy Generator (LLM) | Background Generator (image/svg API) |
| 验证器 | Claim + Channel Validator | L1 CSS assertions |

### 1.3 背景替换

已验证：同一产品在不同场景描述下生成不同背景，产品 hash 不变：

```
场景 A (lifestyle evening):  hash=80840a62
场景 B (lifestyle morning):  hash=ece8c561
产品像素 hash:               5b004746 (不变)
```

### 1.4 局部重生成

仅背景槽位可独立重生成。前景（产品 + 品牌标识 + 文案）不受影响。

### 1.5 视觉版本追踪

`output/.visual-provenance.json` — 每次视觉渲染输出结构化版本信息：

```json
{
  "principle": "product_foreground_fixed_background_independent",
  "outputs": [{
    "channel": "tmall", "scene": "hero",
    "ratio": "1:1",
    "product_asset": {
      "source": "file://...packshot.png",
      "hash": "5b004746",
      "fixed": true
    },
    "background": {
      "type": "solid",
      "hash": "static",
      "regenerable": false
    },
    "version": "prod-5b004746-bg-static"
  }]
}
```

---

## 二、M2 退出标准评估

| 标准 | 状态 | 证据 |
|------|------|------|
| 改背景只调用一次生成（仅背景槽位） | ✅ | scene_policy 控制 `regenerate_background`，仅标记场景调用 |
| 产品像素保持不变 | ✅ | Product image hash 在背景替换测试中不变 |
| 改文案不触发图像模型 | ✅ | 文案在 foreground-layer，独立于 background-layer |
| 改尺寸不触发图像模型 | ✅ | Viewport 变化只影响 Playwright 截图参数 |
| 至少两个场景可用 | ✅ | hero（固态背景）+ cover（固态/svg 背景）|

---

## 三、全管线端到端结果

```
brandkit build-all
  3 campaigns × 6 outputs each = 18 total outputs
  Visual:  24/24 passed (L1 assertions)
  Content: 48/48 passed (claim checker)
  Product foreground: FIXED across all 3 SKUs
  Background: independent generation slot
  Visual provenance: written per build
  Result: ✅ ALL PASS
```

### 局部再生测试（M2 核心假设）

```
Input:        场景 A(lifestyle evening) → hash 80840a62
              场景 B(lifestyle morning) → hash ece8c561
Change:       Background only
Preserved:    Product pixels → hash 5b004746 (IDENTICAL)
Result:       ✅ Local regeneration working
```

---

## 四、M3 就绪评估

### M3 目标：Skill Distribution

让非 CLI 用户通过 Agent 完成任务。M3 前置条件：

| 条件 | 状态 | 说明 |
|------|------|------|
| M1 内容管线通过 | ✅ | 3 SKU, provenance, channel diff |
| M2 视觉管线通过 | ✅ | 背景槽, 前景固定, 版本追踪 |
| CLI 内核经过 ≥2 品牌验证 | ✅ | 3 campaigns 通过 |
| M0 内部薄 Skill 已有 | ✅ | brandkit CLI 自带 agent 入口说明 |

M3 待交付：Claude Code SKILL.md、Codex/OpenClaw 兼容入口、安装文档、示例品牌包、错误处理。

**M2 就绪进入 M3。**