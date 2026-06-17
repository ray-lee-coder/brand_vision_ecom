# brand_vision_ecom

品牌规则写一次，AI 电商产品图自动遵守。

配好颜色、字体、打光风格 → 每次出图自动加载。不再每张图都让 LLM 猜品牌长什么样。

---

## 怎么用

### 1. 装依赖

```bash
pip install pyyaml
```

### 2. 配 API

复制 `.env.example` 为 `.env`，填入你的 API Key：

```
IMG_BASE_URL=https://token.sensenova.cn/v1
IMG_MODEL=sensenova-u1-fast
IMG_API_KEY=sk-...
```

（支持任何 OpenAI 兼容接口，换 base_url 和 model 就行。）

### 3. 开始出图

```bash
# 白底主图
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "无线耳塞，暗海军蓝色机身，金色装饰环" \
  --template hero-image

# 场景图（换个模板）
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "Aether Z 耳塞充电盒，打开状态" \
  --template lifestyle-scene

# 多角度网格图
python3 scripts/generate_image.py examples/nike/brand.yaml \
  --product "白色跑鞋，轻量化编织鞋面" \
  --template multi-angle-grid

# 海报 Banner（指定变体）
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "Aether 无线耳塞" \
  --template poster-banner --variant editorial
```

---

## 配一个自己的品牌

新建一个 `brand.yaml`，填 5 个字段就行：

```yaml
brand:
  name: "我的品牌"
  description: "品牌一句话描述"
  tone: "cool"                           # warm / cool / neutral
  colors:
    primary: "#1E3A8A"                   # 主色（必填）
    accent: "#60A5FA"                    # 强调色（可选，默认=主色）
    canvas: "#FFFFFF"                    # 画面背景色（必填）
    text: "#111111"                      # 文字色（必填）
    surface: "#F5F5F5"                   # 表面色（可选）
    border: "#E5E5E5"                    # 边框色（可选）
  typography:
    display: "思源黑体"                   # 展示字体（必填）
    body: "思源宋体"                      # 正文字体（必填）
  imagery:                              # 产品摄影偏好（可选，有默认）
    primary_lighting: "studio_soft"
    default_angle: "three_quarter"
    product_frame_ratio: 0.35
    background: "pure_white"
    retouching: "light"
    min_views: 5
    required_angles:
      - front
      - three_quarter_left
      - three_quarter_right
      - side_left
      - detail
```

---

## 场景模板

| 模板 ID | 说明 | 变体 |
|---------|------|------|
| `hero-image` | 白底/纯色底产品主图 | luxury, minimal, tech |
| `lifestyle-scene` | 场景氛围图 | indoor, outdoor, studio |
| `detail-macro` | 细节微距图 | material, stitching, hardware |
| `multi-angle-grid` | 多角度网格图 | 2x2, 1x4, colors |
| `poster-banner` | 海报/Banner | sale, editorial, launch |

---

## 项目结构

```
├── scripts/generate_image.py     核心脚本（读 brand.yaml → 出图）
├── templates/                     5 个场景模板
├── schemas/brand.schema.json      品牌 VI 数据规范
├── examples/aether/brand.yaml     示例：音频科技品牌
├── examples/nike/brand.yaml       示例：运动品牌
└── .env.example                   API 配置模板
```

零外部 Git 依赖，clone 即用。