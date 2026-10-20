#!/usr/bin/env python3
"""调用 DeepSeek LLM，从候选 + 评论生成精选结果（中文摘要 / 大众态度 / 专家评价 / 今日 AI 大白话）。

用法：
    python3 scripts/gen.py [--date 2026-10-20]

密钥：优先读环境变量 DEEPSEEK_API_KEY（云端 GitHub Actions 用 Secret 注入），
否则读 scripts/secrets.json（本地，已 gitignore）。
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
BJ = timezone(timedelta(hours=8))
MODEL = os.environ.get("AI_CATCH_MODEL", "deepseek-chat")


def beijing_date():
    return datetime.now(BJ).date().isoformat()


def load_secrets():
    path = ROOT / "scripts" / "secrets.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def build_prompt(candidates, comments):
    return f"""你是「AI Catch Catch」的主编，负责把当天的 AI 候选资讯加工成一份中文早报。

候选资讯（JSON 数组，已按热度初排）：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Hacker News 高赞评论（key 是 object_id，value 是评论数组）：
{json.dumps(comments, ensure_ascii=False, indent=2)}

请完成：
1. 从候选中选出**最重要、最值得关注**的 10 条（优先 AI 相关、影响大、有讨论度的；同一事件只留一条）。
2. 对每条产出：
   - title_zh：中文标题（简洁准确）；
   - summary_zh：一句话中文摘要（说清发生了什么）；
   - sentiment：大众态度，只能是「正面」「中立」「负面」之一。若该条有 HN 评论，务必基于真实评论提炼；没有评论的基于标题/摘要推断；
   - sentiment_reason：一句话理由（说明大众为何是这个态度）；
   - expert_view：专家视角的一句话评价（技术价值 / 产业影响 / 风险）。
3. 生成 explainer（面向非科技背景、想追赶 AI 前沿的读者）：
   - lead：一句话主线，把当天 10 条串成一个整体判断；
   - where：2–4 条大白话，讲清「AI 现在到哪一步了」，用类比、少术语；
   - relevance：2–4 条「如何落地」——偏应用、可执行的具体建议。

严格只输出一个 JSON 对象（不要 markdown 代码块、不要多余文字），结构如下：
{{
  "date": "YYYY-MM-DD",
  "items": [{{"rank":1,"title":"原标题","title_zh":"中文标题","link":"...","source":"...","summary_zh":"...","sentiment":"正面","sentiment_reason":"...","expert_view":"..."}}],
  "explainer": {{"lead":"...","where":["..."],"relevance":["..."]}}
}}
注意：items 里 title/link/source 直接沿用候选里的原值。"""


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    date = args.date or beijing_date()

    raw_path = ROOT / "data" / "raw" / f"{date}.json"
    if not raw_path.exists():
        raise SystemExit(f"未找到 {raw_path}，请先运行 catch.py")
    candidates = json.loads(raw_path.read_text(encoding="utf-8"))

    comments_path = ROOT / "data" / "comments" / f"{date}.json"
    comments = json.loads(comments_path.read_text(encoding="utf-8")) if comments_path.exists() else {}

    api_key = os.environ.get("DEEPSEEK_API_KEY") or load_secrets().get("deepseek_api_key")
    if not api_key:
        raise SystemExit("缺少环境变量 DEEPSEEK_API_KEY，或 scripts/secrets.json 里的 deepseek_api_key")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=8000,
        temperature=0.7,
        messages=[{"role": "user", "content": build_prompt(candidates, comments)}],
    )
    text = resp.choices[0].message.content
    curated = extract_json(text)
    curated["date"] = date

    out_dir = ROOT / "data" / "curated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date}.json"
    out_path.write_text(json.dumps(curated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] 写入 {out_path}（{len(curated.get('items', []))} 条）")


if __name__ == "__main__":
    main()
