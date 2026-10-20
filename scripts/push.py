#!/usr/bin/env python3
"""把每日 AI 早报推送到微信（支持 PushPlus / Server酱）。

用法：
    python3 scripts/push.py --input data/curated/2026-10-20.json
    python3 scripts/push.py --input data/curated/2026-10-20.json --url https://xxx.github.io/ai-catch-catch/

密钥：优先读环境变量（SERVERCHAN_SENDKEY / PUSHPLUS_TOKEN，供云端 GitHub Actions 使用），
否则读 scripts/secrets.json（本地，已 gitignore），不写进代码。
"""
import argparse
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EMOJI = {"正面": "👍", "中立": "😐", "负面": "👎"}
TIMEOUT = 20


def load_secrets():
    path = ROOT / "scripts" / "secrets.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("push", {})
    return {}


def build_markdown(curated, url=None):
    lines = []
    explainer = curated.get("explainer") or {}

    if explainer.get("lead"):
        lines.append(f"**今日主线**：{explainer['lead']}")
        lines.append("")

    lines.append("**今日 10 条**")
    for item in curated.get("items", []):
        emoji = EMOJI.get(item.get("sentiment"), "😐")
        title = item.get("title_zh") or item.get("title", "")
        link = item.get("link", "")
        lines.append(f"{item.get('rank', '')}. [{title}]({link}) {emoji}")
        if item.get("summary_zh"):
            lines.append(f"　{item['summary_zh']}")

    # 页面未托管时，把「如何落地」也带上，保证手机上信息完整
    if url is None and explainer.get("relevance"):
        lines.append("")
        lines.append("**如何落地**")
        for tip in explainer["relevance"]:
            lines.append(f"· {tip}")

    if url:
        lines.append("")
        lines.append(f"📄 完整深色页面：{url}")

    return "\n".join(lines)


def send(service, key, title, body):
    if service == "pushplus":
        resp = requests.post(
            "https://www.pushplus.plus/send",
            json={"token": key, "title": title, "content": body, "template": "markdown"},
            timeout=TIMEOUT,
        )
    else:  # serverchan（Server酱 Turbo）
        resp = requests.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": body},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--url", default=None, help="页面 URL（托管后提供）")
    parser.add_argument("--service", choices=["pushplus", "serverchan"], default=None)
    args = parser.parse_args()

    curated = json.loads(Path(args.input).read_text(encoding="utf-8"))
    secrets = load_secrets()
    service = args.service or secrets.get("service") or "pushplus"
    if service == "pushplus":
        key = os.environ.get("PUSHPLUS_TOKEN") or secrets.get("pushplus_token")
    else:
        key = os.environ.get("SERVERCHAN_SENDKEY") or secrets.get("serverchan_sendkey")
    if not key:
        raise SystemExit(
            "未找到密钥：请设置环境变量 PUSHPLUS_TOKEN / SERVERCHAN_SENDKEY，"
            "或在 scripts/secrets.json 中配置 pushplus_token / serverchan_sendkey"
        )

    title = f"AI 早报 · {curated.get('date', '')}"
    body = build_markdown(curated, args.url)
    resp = send(service, key, title, body)
    print(f"[push] {service} -> {json.dumps(resp, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
