#!/usr/bin/env python3
"""
BrandKit Copy Generator — 受约束文案生成器
对称于视觉的 Image Generator slot。

输入: message_plan + product_facts + channel_constraints + content_type
输出: { text, claims: [{ claim, fact_ref, source_ref, status }] }
"""

import json
import os
import sys
import subprocess
from pathlib import Path


# ── Available LLM providers ────────────────────────────────
PROVIDERS = {
    "sensenova": {
        "base_url": "https://token.sensenova.cn/v1",
        "key_env": "SENSENOVA_API_KEY",
        "model": "deepseek-v4-flash",
    },
    "deepseek": {
        "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "key_env": "ARK_API_KEY",
        "model": "deepseek-v4-flash-260425",
    },
}


def call_llm(system_prompt, user_prompt, provider="sensenova"):
    """Call LLM API and return response text."""
    cfg = PROVIDERS.get(provider, PROVIDERS["sensenova"])
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise RuntimeError(f"{cfg['key_env']} not set")

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    try:
        import requests
        resp = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except ImportError:
        # Fallback: use curl
        import tempfile
        payload_file = Path(tempfile.mktemp(suffix=".json"))
        payload_file.write_text(json.dumps(payload, ensure_ascii=False))
        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST",
                 f"{cfg['base_url']}/chat/completions",
                 "-H", f"Authorization: Bearer {api_key}",
                 "-H", "Content-Type: application/json",
                 "-d", payload_file.read_text()],
                capture_output=True, text=True, timeout=60,
            )
            data = json.loads(result.stdout)
            return data["choices"][0]["message"]["content"]
        finally:
            payload_file.unlink(missing_ok=True)


def build_system_prompt(message_plan, facts, claim_rules, channel_constraints, content_type):
    """Build system prompt for copy generation."""
    facts_text = json.dumps(facts, indent=2, ensure_ascii=False)
    message_text = json.dumps(message_plan, indent=2, ensure_ascii=False)
    channel_text = json.dumps(channel_constraints, indent=2, ensure_ascii=False)
    claim_rules_text = json.dumps(claim_rules, indent=2, ensure_ascii=False)

    return f"""你是一个品牌文案生成器。你的任务是根据品牌约束、商品事实和渠道规则，生成符合品牌调性的文案。

## 输出格式
必须返回 JSON，格式如下：
{{
  "text": "生成的文案内容",
  "claims": [
    {{
      "claim": "42dB自适应降噪",
      "fact_ref": "facts.noise_reduction",
      "source_ref": "docs/x1-noise-test.pdf",
      "status": "verified"
    }}
  ]
}}

## 规则
1. text 是最终文案
2. claims 数组标注每条宣称引用的事实来源
3. 没有事实来源的宣称（如营销改写、主观描述）的 fact_ref 设为 "marketing_writing"
4. 禁止使用 claim_rules.forbidden 中的禁用词
5. 需要证据的宣称（claim_rules.require_source_for）必须有对应的事实
6. 语气必须符合品牌 voice 描述
7. 文案长度不超过 channel_constraints 的限制
8. 只输出 JSON，不要其他文字"""


def build_user_prompt(content_type, channel_name, message_plan, facts, channel_constraints):
    """Build user prompt for specific content type."""
    primary = message_plan.get("primary_benefit", {})
    secondary = message_plan.get("secondary_benefits", [])
    cta = message_plan.get("call_to_action", {}).get(channel_name, "")

    facts_summary = "\n".join([
        f"- {k}: {v.get('value', '')}{v.get('unit', '')} (来源: {v.get('source', {}).get('ref', 'unknown')})"
        for k, v in facts.items()
    ])

    return f"""生成内容类型: {content_type}
渠道: {channel_name}

核心卖点: {primary.get('statement', '')}
次要卖点: {', '.join([b.get('statement', '') for b in secondary])}
行动号召: {cta}

商品事实:
{facts_summary}

渠道约束: {json.dumps(channel_constraints, indent=2, ensure_ascii=False)}

请生成符合品牌调性的{content_type}文案。"""


def generate_copy(message_plan, facts, claim_rules, channel_constraints, content_type, channel_name, provider="sensenova"):
    """Generate copy with provenance annotations."""
    system_prompt = build_system_prompt(
        message_plan, facts, claim_rules, channel_constraints, content_type
    )
    user_prompt = build_user_prompt(
        content_type, channel_name, message_plan, facts, channel_constraints
    )

    try:
        response = call_llm(system_prompt, user_prompt, provider)
        # Parse JSON from response
        # Try direct parse first
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
            else:
                # Fallback: wrap as simple text
                result = {"text": response.strip(), "claims": []}

        return result
    except Exception as e:
        print(f"[WARN] Copy generator failed: {e}")
        return {"text": "", "claims": [], "error": str(e)}


def main():
    """CLI entry for testing."""
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Copy Generator")
    parser.add_argument("--message-plan", default=".build/message-plan.json")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--content-type", default="product_title")
    parser.add_argument("--channel", default="tmall")
    parser.add_argument("--provider", default="sensenova")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    args = parser.parse_args()

    with open(args.message_plan) as f:
        message_plan = json.load(f)
    with open(args.resolved) as f:
        resolved = json.load(f)

    facts = resolved.get("product", {}).get("facts", {})
    content_spec = resolved.get("content_spec", {})
    claim_rules = content_spec.get("claim_rules", {})
    channels = resolved.get("channels", {})
    ch_data = channels.get(args.channel, {})
    ch_content = ch_data.get("content", {})

    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(build_system_prompt(message_plan, facts, claim_rules, ch_content, args.content_type))
        print("\n=== USER PROMPT ===")
        print(build_user_prompt(args.content_type, args.channel, message_plan, facts, ch_content))
        sys.exit(0)

    result = generate_copy(
        message_plan, facts, claim_rules, ch_content,
        args.content_type, args.channel, args.provider,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
