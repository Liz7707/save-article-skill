# save-article — Claude Code 文章收藏 Skill

一键保存网页文章到本地 Markdown。支持 URL 抓取和文本粘贴两种模式，自动提取标题/作者/日期，转换为干净的 Markdown，按日期分目录存储。

## 功能

| 模式 | 说明 |
|---|---|
| URL 模式 | 输入网址，自动抓取网页，提取正文转为 Markdown |
| 浏览器模式 | 用本地 Chrome headless 抓取知乎、微信等强反爬网站 |
| 粘贴模式 | 直接粘贴文本，提供标题后保存 |

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> 无需安装 Chromium。脚本自动使用系统已有的 Chrome 浏览器。

### 2. 安装 Skill

**方式 A：项目级（推荐，随项目隔离）**

```bash
mkdir -p .claude/skills/save-article
cp skills/save-article/SKILL.md .claude/skills/save-article/
cp skills/save-article/extract.py .claude/skills/save-article/
```

**方式 B：用户级（全局可用）**

```bash
# Windows
mkdir -p %USERPROFILE%\.claude\skills\save-article
copy skills\save-article\* %USERPROFILE%\.claude\skills\save-article\

# macOS / Linux
mkdir -p ~/.claude/skills/save-article
cp skills/save-article/* ~/.claude/skills/save-article/
```

### 3. 首次使用浏览器模式（如抓知乎）

如果遇到需要登录的网站，先执行一次登录：

```bash
python skills/save-article/extract.py . --browser-login
```

在弹出的 Chrome 窗口中手动登录，关闭后 cookie 自动保存到 `~/.claude/playwright-profile/`。之后所有浏览器抓取自动复用，无需再次登录，且全程 headless 无弹窗。

## 使用

在 Claude Code 对话中：

```
/save-article https://example.com/article
```

或直接粘贴文章内容，说"保存这篇文章"。

或直接在命令行使用：

```bash
# URL 模式
python skills/save-article/extract.py . "https://example.com/article"

# 浏览器模式（强反爬网站）
python skills/save-article/extract.py . --browser "https://www.zhihu.com/..."

# 粘贴模式
echo "文章内容..." | python skills/save-article/extract.py . --paste "文章标题"
```

## 保存格式

```
当前目录/
├── 2026/
│   └── 06/
│       └── 2026-06-05--文章标题-slug.md
```

每篇文章为 Markdown 文件，头部带 YAML 元数据：

```yaml
---
title: "文章标题"
url: "https://example.com/article"
author: "作者名"
date: "2025-03-10"
saved_at: "2026-06-05 14:30"
domain: "example.com"
source: "url"
word_count: 1234
---
```

## 依赖

- Python 3.8+
- requests, beautifulsoup4, lxml — HTML 抓取和解析
- playwright — 浏览器模拟（可选，仅强反爬网站需要）
- 系统 Chrome — 浏览器模式使用

## 许可

MIT
