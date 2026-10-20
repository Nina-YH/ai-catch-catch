#!/usr/bin/env python3
"""抓取 Hacker News 条目的真实高赞评论（用于「大众态度」混合策略）。

用法：
    python3 scripts/comments.py --ids 50163277 50159341 --top 5
    python3 scripts/comments.py --from-raw            # 自动读 data/raw/<今日>.json 里的 HN object_id

输出：
    data/comments/YYYY-MM-DD.json  形如 { "<object_id>": [ {author, text, points}, ... ] }
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "comments"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ai-catch-catch/0.1; +local)"}
TAG_RE = re.compile(r"<[^>]+>")
BJ = timezone(timedelta(hours=8))


def strip_html(text):
    return TAG_RE.sub("", text or "").replace("&quot;", '"').replace("&amp;", "&").replace("&#x27;", "'").strip()


def fetch_comments(object_id, n):
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={"tags": f"comment,story_{object_id}", "hitsPerPage": n},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {
            "author": h.get("author"),
            "text": strip_html(h.get("comment_text") or "")[:400],
            "points": h.get("points"),
        }
        for h in resp.json().get("hits", [])
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", default=None)
    parser.add_argument("--from-raw", action="store_true", help="从 data/raw/<今日>.json 自动取 HN object_id")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    ids = list(args.ids) if args.ids else []
    if args.from_raw:
        raw_path = ROOT / "data" / "raw" / f"{datetime.now(BJ).date().isoformat()}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        for item in raw:
            oid = item.get("object_id")
            if item.get("has_comments") and oid and oid not in ids:
                ids.append(oid)
    if not ids:
        raise SystemExit("请提供 --ids 或 --from-raw")

    result = {}
    for obj_id in ids:
        try:
            result[obj_id] = fetch_comments(obj_id, args.top)
        except Exception as exc:
            result[obj_id] = []
            print(f"[skip] {obj_id}: {exc}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{datetime.now(BJ).date().isoformat()}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] 写入 {out_path}")


if __name__ == "__main__":
    main()
