#!/usr/bin/env python3
"""抓取 AI 资讯源，去重、过滤、初排，输出候选 JSON。

用法：
    python3 scripts/catch.py --hours 36 --top 15

输出：
    data/raw/YYYY-MM-DD.json  （抓取+去重+过滤后的候选列表，按 source weight、热度与时间初排）

注意：本脚本只做确定性抓取与初排；「精选 Top 10」与中文摘要/态度/专家评价由模型完成。
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ai-catch-catch/0.1; +local)"}
TAG_RE = re.compile(r"<[^>]+>")
BJ = timezone(timedelta(hours=8))  # 以北京时间为“今日”，保证 07:00 触发的早报日期正确


def strip_html(text):
    return TAG_RE.sub("", text or "").strip()


def parse_iso(text):
    """兼容 Algolia 的 'Z' 结尾与 RSS 的时区格式。"""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def normalize_url(url):
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host.endswith(":80"):
        host = host[:-3]
    elif host.endswith(":443"):
        host = host[:-4]
    query = "&".join(
        kv for kv in parts.query.split("&")
        if not kv.lower().startswith(("utm_", "ref=", "source=", "fbclid", "gclid"))
    )
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/") or "/", query, ""))


def title_key(title):
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def fetch_rss(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def fetch_hn(hours):
    """经 HN 官方 Algolia API 取近 N 小时的热门 story（含 points / 评论数）。"""
    since = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params={"tags": "story", "numericFilters": f"points>40,created_at_i>{since}", "hitsPerPage": 50},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    entries = []
    for h in resp.json().get("hits", []):
        title = h.get("title") or h.get("story_title")
        if not title:
            continue
        link = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        entries.append({
            "title": title,
            "link": link,
            "summary": "",
            "source": "Hacker News",
            "published": h.get("created_at"),
            "points": h.get("points"),
            "num_comments": h.get("num_comments"),
            "object_id": h.get("objectID"),
        })
    return entries


def extract_rss_entries(feed, source_name):
    entries = []
    for e in feed.entries:
        link = e.get("link")
        title = strip_html(e.get("title"))
        if not link or not title:
            continue
        published = None
        for key in ("published_parsed", "updated_parsed"):
            value = e.get(key)
            if value:
                published = datetime(*value[:6], tzinfo=timezone.utc).isoformat()
                break
        entries.append({
            "title": title,
            "link": link,
            "summary": strip_html(e.get("summary") or e.get("description") or "")[:500],
            "source": source_name,
            "published": published,
        })
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=36)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    config = json.loads((ROOT / "scripts" / "sources.json").read_text(encoding="utf-8"))
    keywords = [k.lower() for k in config["ai_keywords"]]
    # 词边界匹配：避免 "ai" 误命中 "ukrAIn"、"clAIm" 等
    keyword_re = re.compile(
        r"(?<![a-z0-9])(" + "|".join(re.escape(k) for k in keywords) + r")(?![a-z0-9])"
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    seen_urls, seen_titles = set(), set()
    candidates = []

    for src in config["sources"]:
        try:
            if src.get("type") == "hn":
                entries = fetch_hn(args.hours)
            else:
                entries = extract_rss_entries(fetch_rss(src["url"]), src["name"])
        except Exception as exc:  # 单个源失败不阻塞整体
            print(f"[skip] {src['name']}: {exc}", file=sys.stderr)
            continue

        kept = 0
        for item in entries:
            if src.get("filter") and not keyword_re.search(item["title"].lower()):
                continue
            url_key = normalize_url(item["link"])
            t_key = title_key(item["title"])
            if url_key in seen_urls or t_key in seen_titles:
                continue
            published = parse_iso(item.get("published"))
            if published and published < cutoff:
                continue
            seen_urls.add(url_key)
            seen_titles.add(t_key)
            item["weight"] = src.get("weight", 1.0)
            item["has_comments"] = src.get("has_comments", False)
            candidates.append(item)
            kept += 1
        print(f"[ok] {src['name']}: {kept} 条")

    # 初排：source weight 优先，其次 HN 热度，再其次时间近的在前（最终排序由模型完成）
    candidates.sort(
        key=lambda x: (-x["weight"], -(x.get("points") or 0), x.get("published") or "")
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"{datetime.now(BJ).date().isoformat()}.json"
    out_path.write_text(
        json.dumps(candidates[: args.top], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[done] 候选 {len(candidates)} 条，写入 {out_path}（取前 {args.top}）")


if __name__ == "__main__":
    main()
