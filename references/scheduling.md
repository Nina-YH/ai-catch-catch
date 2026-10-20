# 定时运行与发布

> 占位说明：本文档后续填写 GitHub Actions workflow 的具体写法与 GitHub Pages 发布配置。当前只写思路，不含实现。

## 目标

- 每天北京时间 07:00 自动触发。
- 不依赖电脑常开，全程在云端完成。

## 方案思路（GitHub Actions）

- 用 GitHub Actions 的 `schedule` cron 定时触发：北京时间 07:00 = UTC 前一日 23:00，即 `cron: '0 23 * * *'`。
- 每次运行：抓取 → 筛选 → 生成看法 → 生成深色单页 → 发布到 GitHub Pages → 推送到微信服务号。
- 推送用 Server酱/PushPlus，密钥存于 GitHub Actions Secrets，不写进仓库。

## 待定

- workflow 具体步骤与依赖安装。
- GitHub Pages 的启用与发布路径。
- 密钥变量命名。
