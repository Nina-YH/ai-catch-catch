---
name: ai-catch-catch
description: >-
  每天抓取 AI 相关全球资讯，筛选最重要的 10 条，为每条生成中文摘要、大众态度判断
  （正面/中立/负面 + 一句话理由）和专家视角一句话评价，汇总成一个极简高级深色风格的单页，
  附源站链接，并通过微信服务号推送到手机。当用户提到「AI资讯」「每日AI新闻」「AI推送」
  「ai-catch-catch」「今天AI圈发生了什么」，或想要获取/整理/推送每日 AI 新闻、AI 圈动态时，
  务必使用本技能。
---

# AI Catch Catch

## 概述

每天自动抓取 AI 相关全球资讯，精选最重要的 10 条，为每条产出中文摘要、大众态度（正/中/负 + 理由）与专家一句话评价，汇总成一个极简高级深色风格的单页，附源站链接，并通过微信服务号（Server酱/PushPlus）推送到手机。

## 资讯源

第一阶段以英文源为主，覆盖全球 AI 动态。各源的确切 URL、是否可抓评论见 [references/sources.md](references/sources.md)。

## Workflow

1. **抓取** — 运行 `python3 scripts/catch.py`，从各 RSS 源抓取最近 24–36 小时条目，去重、AI 词边界过滤、按热度初排，写入 `data/raw/<date>.json`。
2. **抓真实评论** — 对候选中的 Hacker News 条目，运行 `python3 scripts/comments.py --ids <object_id...>`，抓取高赞评论写入 `data/comments/<date>.json`。
3. **精选 Top 10 与生成看法**（模型完成）— 读 `data/raw` 与 `data/comments`，选出最重要 10 条，逐条产出：
   - 中文摘要、中文标题；
   - 大众态度（正/中/负 + 一句话理由）——有评论的 HN 条目基于真实评论提炼，其余基于标题/摘要推断（策略见 [references/opinion-guide.md](references/opinion-guide.md)）；
   - 专家视角一句话评价。
4. **生成「今日 AI 大白话」**（模型完成）— 面向非科技背景读者，把当天 10 条串成一段浅显解读：`lead`（一句话主线）+ `where`（AI 现在到哪一步了，2–4 条大白话）+ `relevance`（「如何落地」——偏应用、可执行的建议，而非泛泛而谈）。写给「想追赶 AI 前沿的非技术用户」，用类比、少用术语。
5. **写入结果** — 把第 3、4 步写入 `data/curated/<date>.json`（字段：items 为 rank/title/title_zh/link/source/summary_zh/sentiment/sentiment_reason/expert_view；顶层 explainer 为 lead/where/relevance）。

> 云端自动化：GitHub Actions 中由 `scripts/gen.py` 调用 DeepSeek API 自动完成第 3–4 步（需环境变量 `DEEPSEEK_API_KEY`）；本地则由 Claude 直接完成。部署步骤见 [DEPLOY.md](DEPLOY.md)。
6. **生成深色单页** — 运行 `python3 scripts/render.py --input data/curated/<date>.json`，套用 [assets/page-template.html](assets/page-template.html) + [assets/style.css](assets/style.css)，输出 `site/index.html`。
7. **发布与推送** — 运行 `python3 scripts/push.py --input data/curated/<date>.json` 推送到微信（支持 Server酱/PushPlus，密钥在 `scripts/secrets.json`）；托管到 GitHub Pages 后加 `--url <页面地址>` 改推链接。
8. **归档** — `data/` 与 `site/` 按日期留存，便于回溯。

## 输出格式

单页 HTML，模板见 [assets/page-template.html](assets/page-template.html)。视觉基调：极简、高级、深色——克制配色、充足留白、层级清晰，适合手机竖屏阅读。页面顶部（标题之下）附「今日 AI 大白话」模块，面向非技术读者讲解当天 AI 全局，并给出可执行的「如何落地」建议。

## 定时运行

目标：每天北京时间 07:00 自动触发，不依赖电脑常开。采用云端定时（GitHub Actions）并在生成后发布到 GitHub Pages。思路见 [references/scheduling.md](references/scheduling.md)。

## 目录说明

- `scripts/` — `catch.py`（抓取/去重/过滤/初排）、`comments.py`（HN 评论抓取）、`render.py`（渲染深色单页）、`sources.json`（资讯源配置）。
- `references/` — 资讯源清单、看法混合策略、定时与发布说明。
- `assets/` — 深色单页模板与样式。
- `data/` — `raw`（抓取候选）、`comments`（评论）、`curated`（精选结果）；`site/` — 生成的页面。

> 注：若要让 Claude Code 自动加载本技能，可将本目录复制或软链到项目的 `.claude/skills/ai-catch-catch/`。
