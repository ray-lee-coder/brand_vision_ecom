# BrandKit

BrandKit 是面向电商视觉与文案的品牌约束编译器。品牌规则、产品事实、渠道规则和 campaign brief 经过同一条 CLI 管线，生成带来源记录的 HTML、PNG 和 Markdown 产物。

> 发布状态：Beta 验证进行中，尚未放行。首次使用请走下方无网络、无模型调用的离线路径。

## 当前能力

- 同一份品牌和产品事实驱动视觉与文案。
- 客观宣称必须绑定产品事实和证据引用。
- 每次构建使用独立 run ID、输出目录和 manifest。
- 缺失素材、无效契约和阻断性验证错误返回非零退出码。
- 当前支持天猫和小红书渠道规则。

## 快速开始

环境要求：Python 3.9+。

```bash
git clone https://github.com/ray-lee-coder/brand_vision_ecom.git
cd brand_vision_ecom
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium

# 首次构建：完全离线，不调用 provider
bash scripts/brandkit build campaigns/618-launch.yaml --offline

# 完整测试门禁
python3 -m pytest -q
```

命令完成后会打印两个运行级路径：

```text
output/runs/{run_id}/618-launch/
.build/runs/{run_id}/manifest.json
```

## 在线模式

在线模式不是首次体验的前置条件。配置对应 provider 凭据后，显式去掉 `--offline`：

```bash
bash scripts/brandkit build campaigns/618-launch.yaml
```

在线 provider 缺少凭据、超时、限流或返回无效结构时，构建必须失败，不会静默降级为占位内容。

## 项目结构

```text
brands/{brand}/
  brand-core.yaml       品牌身份、颜色、字体、语气和宣称规则
  visual-spec.yaml      布局、场景和摄影规则
  content-spec.yaml     信息层级和文案规则
  products/{sku}.yaml   产品事实和证据引用
campaigns/*.yaml        构建入口
channels/*.yaml         天猫和小红书渠道契约
scripts/brandkit        唯一公开 CLI 入口
schemas/*.json          六类输入契约
tests/                  单元、集成、CLI 和离线端到端门禁
```

## 常用命令

```bash
# 离线构建单个 campaign
bash scripts/brandkit build campaigns/acme-launch.yaml --offline

# 离线构建全部 campaign
bash scripts/brandkit build-all --offline

# 查看公开命令
bash scripts/brandkit help

# 清理生成目录
bash scripts/brandkit clean
```

`render`、`verify` 和 `validate` 不是独立公开命令；`build` 会在同一个隔离运行中依次完成编译、渲染、验证和渠道检查。

## 发布边界

当前目标是可供个人和小团队可靠使用的 Beta。多租户、鉴权、数据库、队列、Web UI、审批和协作不在本轮范围。详细退出标准见 [PRODUCT-PLAN.md](PRODUCT-PLAN.md)。

## 许可证

[MIT](LICENSE)
