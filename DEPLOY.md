# 部署到 GitHub Actions（每天 07:00 自动推送）

目标：云端每天**北京时间 07:00** 自动跑完整流程（抓取 → 精选 → 生成深色页 → 发布 → 微信推送），不依赖电脑常开。

## 前置准备

1. 一个 GitHub 账号。
2. 一个 **DeepSeek API Key**（`sk-...`，用于生成中文摘要 / 态度 / 大白话）。在 https://platform.deepseek.com 获取。
3. 你的 **Server酱 sendkey**（`SCT...`，已用于本地推送）。

## 步骤

### 1. 新建 GitHub 仓库

在 GitHub 上新建一个空仓库（Public 或 Private 均可），名字随意，比如 `ai-catch-catch`。**不要**勾选 "Add a README"（保持空仓库，避免冲突）。

### 2. 推送本地代码

在终端执行（把 `<你的用户名>` 换成你的 GitHub 用户名）：

```bash
cd "ai-catch-catch"
git init
git add .
git commit -m "init ai-catch-catch"
git branch -M main
git remote add origin https://github.com/<你的用户名>/ai-catch-catch.git
git push -u origin main
```

> 仓库根目录就是 `ai-catch-catch/` 这个文件夹。`data/`、`site/`、`scripts/secrets.json` 已被 `.gitignore` 排除，不会提交（它们每次运行自动生成，云端走环境变量）。

### 3. 配置两个 Secret

仓库页面依次点：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`，添加两个：

| Name | Value |
|---|---|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key（`sk-...`） |
| `SERVERCHAN_SENDKEY` | 你的 Server酱 sendkey（`SCT...`） |

> 云端**不用** `secrets.json`——脚本已改成优先读环境变量。

### 4. 开启 GitHub Pages

`Settings` → `Pages` → `Source` 选 **"GitHub Actions"**（不要选 Branch）。

### 5. 手动测试一次

`Actions` 标签页 → 左侧 `Daily AI Catch Catch` → `Run workflow` → 绿色 `Run workflow` 按钮。

跑完约 1–2 分钟后：

- 微信会收到推送；
- 页面地址在 `https://<你的用户名>.github.io/ai-catch-catch/`（若仓库名不同，以 `Settings → Pages` 里显示的真实地址为准）。

### 6. 确认定时

workflow 里的 `cron: '0 23 * * *'` 表示 UTC 23:00 = 北京时间 07:00，已配好，无需改动。

## 常见问题

- **推送里的链接打不开**：把 `.github/workflows/daily.yml` 里 `--url` 后面的地址改成 `Settings → Pages` 显示的真实地址。
- **想改推送时间**：改 `cron`（UTC 时间；北京时间 = UTC + 8）。
- **只想推文字、不要链接**：去掉 `push.py` 命令里的 `--url ...` 即可。
- **想换模型**：在 Secret 里加 `AI_CATCH_MODEL`（如 `deepseek-reasoner`）。
