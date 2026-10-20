#!/usr/bin/env python3
"""把精选结果 JSON 渲染成极简高级深色单页 HTML。

用法：
    python3 scripts/render.py --input data/curated/2026-10-20.json

输出：
    site/index.html  （内联样式，单文件可独立打开/发布）
"""
import argparse
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTIMENT_CLASS = {"正面": "positive", "中立": "neutral", "负面": "negative"}


def esc(text):
    return html.escape(str(text or ""))


def build_item_html(item):
    title_zh = item.get("title_zh") or item.get("title")
    title_en = item.get("title")
    link = item.get("link", "#")
    source = item.get("source", "")
    summary = item.get("summary_zh", "")
    sentiment = item.get("sentiment", "中立")
    reason = item.get("sentiment_reason", "")
    expert = item.get("expert_view", "")
    rank = item.get("rank", 0)
    cls = SENTIMENT_CLASS.get(sentiment, "neutral")

    show_en = title_en and title_en != title_zh
    en_line = f'<p class="item-title-en">{esc(title_en)}</p>' if show_en else ""

    return f"""    <article class="item">
      <div class="item-top">
        <span class="rank">{rank:02d}</span>
        <div>
          <div class="item-title"><a href="{esc(link)}" target="_blank" rel="noopener">{esc(title_zh)}</a></div>
          {en_line}
          <span class="item-source">{esc(source)}</span>
        </div>
      </div>
      <p class="item-summary">{esc(summary)}</p>
      <div class="item-views">
        <p class="sentiment sentiment-{cls}"><span class="tag">大众</span>{esc(sentiment)} · {esc(reason)}</p>
        <p class="expert"><span class="tag">专家</span>{esc(expert)}</p>
      </div>
    </article>"""


def build_explainer_html(explainer):
    if not explainer:
        return ""
    lead = esc(explainer.get("lead", ""))
    where = "".join(f"<li>{esc(x)}</li>" for x in explainer.get("where", []))
    relevance = "".join(f"<li>{esc(x)}</li>" for x in explainer.get("relevance", []))
    return (
        '<section class="explainer">'
        '<span class="explainer-tag">今日 AI 大白话</span>'
        f'<p class="explainer-lead">{lead}</p>'
        '<div class="explainer-block"><h3>AI 现在到哪一步了</h3>'
        f'<ul class="explainer-list">{where}</ul></div>'
        '<div class="explainer-block"><h3>如何落地</h3>'
        f'<ul class="explainer-list">{relevance}</ul></div>'
        '</section>'
    )


def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str)
        weekday = "一二三四五六日"[dt.weekday()]
        return f"{dt.year}年{dt.month}月{dt.day}日 · 星期{weekday}"
    except Exception:
        return date_str


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    curated = json.loads(Path(args.input).read_text(encoding="utf-8"))
    template = (ROOT / "assets" / "page-template.html").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")

    items_html = "\n".join(build_item_html(i) for i in curated.get("items", []))
    explainer_html = build_explainer_html(curated.get("explainer"))
    page = (
        template.replace("{{CSS}}", css)
        .replace("{{DATE}}", esc(format_date(curated.get("date", ""))))
        .replace("{{ITEMS}}", items_html)
        .replace("{{EXPLAINER}}", explainer_html)
    )

    out_dir = ROOT / "site"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    print(f"[done] 已生成 {out_path}（{len(curated.get('items', []))} 条）")


if __name__ == "__main__":
    main()
