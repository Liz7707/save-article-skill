---
name: save-article
description: "从 URL 保存文章，或保存用户粘贴的文本内容到本地文件。触发词：保存文章、收藏、存下来、save this、/save-article"
argument-hint: "[url] 或粘贴文本"
user-invocable: true
allowed-tools: Bash, Read, Glob, Write
model: sonnet
---

# 保存文章 (Save Article)

脚本路径：与 SKILL.md 同目录的 `extract.py`
保存目录：**当前项目目录**（执行命令时所在目录）
文件格式：`YYYY/MM/YYYY-MM-DD--<slug>.md`，带 YAML frontmatter

---

## 场景分发

### 场景 A: 用户提供了 URL（普通网页）

先用 requests 模式抓取：

```bash
python3 "${SKILL_DIR}/extract.py" "${SAVE_DIR}" "<URL>"
```

其中 `SKILL_DIR` 为 skill 所在目录（含 extract.py），`SAVE_DIR` 为项目根目录。

若 stderr 包含 `WARNING:short_content:`（正文 <50 字符），切换到场景 A+。

---

### 场景 A+: 强反爬网站（短内容警告 / 用户指定用浏览器）

```bash
python3 "${SKILL_DIR}/extract.py" "${SAVE_DIR}" --browser "<URL>"
```

headless 运行，无弹窗。cookie 自动保存在 `~/.claude/playwright-profile/`，跨会话复用。回答中的图片自动下载到 `YYYY/MM/images/` 目录，Markdown 路径自动替换为本地相对路径。

若 stdout 返回 `"error": "login_required"`，执行首次登录：

```bash
python3 "${SKILL_DIR}/extract.py" "${SAVE_DIR}" --browser-login
```

会打开可见 Chrome 窗口供手动登录，关闭后 cookie 自动保存。之后 `--browser` 即可正常使用。

---

### 场景 B: 用户粘贴了文本

1. 向用户询问标题
2. 将内容写入临时文件，然后：

```bash
python3 "${SKILL_DIR}/extract.py" "${SAVE_DIR}" --file "<标题>" "<临时文件路径>"
```

3. 解析 JSON 报告结果

---

### 场景 C: 用户只说"保存文章"、未提供内容

询问：请提供文章 URL 或直接粘贴文章内容。

---

## 结果报告

解析 stdout JSON 后，按以下格式报告：

```
已保存：<title>
来源：<domain 或 "手动粘贴">
字数：<word_count>
路径：<path>
```

---

## 文件结构

| 字段 | 说明 |
|---|---|
| 目录 | `YYYY/MM/` |
| 文件名 | `YYYY-MM-DD--<slug>.md` |
| title | 文章标题 |
| url | 来源 URL（粘贴模式为 null） |
| author | 作者 |
| date | 发布日期 |
| saved_at | 保存时间 |
| domain | 来源域名 |
| source | `url` 或 `paste` |
| word_count | 字数 |

---

## 依赖

Python 包：`requests beautifulsoup4 lxml playwright`

```bash
pip install requests beautifulsoup4 lxml playwright
python -m playwright install chromium  # 或跳过，自动使用系统 Chrome
```

---

## 注意事项

- 尊重版权，仅用于个人阅读学习
- 不抓取需登录的付费内容
