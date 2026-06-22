"""
文章提取和保存工具。
用法:
  python extract.py <save_dir> <url>                   从 URL 提取并保存文章（requests）
  python extract.py <save_dir> --browser <url>         用本地 Chrome 浏览器抓取（强反爬网站）
  python extract.py <save_dir> --paste <title>         从 stdin 读取文本并保存
  python extract.py <save_dir> --file <title> <path>   从文件读取文本并保存（推荐粘贴模式）
"""
import requests, re, json, os, sys
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# 修复 Windows 控制台/管道编码问题
if sys.platform == 'win32':
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def slugify(title):
    slug = re.sub(r'[^\w一-鿿\s-]', '', title.lower())
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')[:80].rstrip('-')
    return slug or 'untitled'


def save_article(save_dir, title, body, word_count, source_info):
    now = datetime.now()
    slug = slugify(title)
    year = now.strftime('%Y')
    month = now.strftime('%m')
    filename = f'{now.strftime("%Y-%m-%d")}--{slug}.md'
    filepath = os.path.join(save_dir, year, month, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Build frontmatter
    url_val = f'"{source_info["url"]}"' if source_info.get("url") else 'null'
    author_val = f'"{source_info["author"]}"' if source_info.get("author") else 'null'
    date_val = f'"{source_info["date"]}"' if source_info.get("date") else 'null'
    domain_val = f'"{source_info["domain"]}"' if source_info.get("domain") else 'null'

    frontmatter = (
        f'---\n'
        f'title: "{title}"\n'
        f'url: {url_val}\n'
        f'author: {author_val}\n'
        f'date: {date_val}\n'
        f'saved_at: "{now.strftime("%Y-%m-%d %H:%M")}"\n'
        f'domain: {domain_val}\n'
        f'source: "{source_info["source"]}"\n'
        f'word_count: {word_count}\n'
        f'---\n\n'
        f'# {title}\n\n'
        f'{body}\n'
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

    return {
        'path': filepath,
        'word_count': word_count,
        'title': title
    }


# ============================================================
# 领域噪音清理规则
# ============================================================
# 每个域名配置三组规则：
#   html_selectors     — CSS 选择器，移除 DOM 元素（转 Markdown 前）
#   text_substitutions — 字符串级正则替换，处理混在正文中的噪音（先执行）
#   text_patterns      — 行级正则，移除匹配的整行（后执行）
DOMAIN_CLEANUP = {
    'zhihu.com': {
        'html_selectors': [
            '.SignFlow', '.signFlowModal',
            '.QuestionHeader', '.QuestionHeader-content',
            '.Question-sideColumn', '.GlobalSideBar',
            '.Comments-container', '.CommentList',
            '.Recommendations', '.HotQuestions',
        ],
        'text_substitutions': [
            # 开头混入的登录提示 "登录后...查看全部 X 个回答"
            (r'登录后你可以不限量看优质回答.*?查看全部\s*[\d,]+\s*个回答', ''),
            # 结尾广告卡片（通用：品牌名 + 的广告）
            (r'升级泽锐防蓝光后实际佩戴感受如何？[\s\S]*?查看详情', ''),
            (r'查看详情', ''),
            (r'以前戴蔡司佳锐[\s\S]*?体验提升明显', ''),
            (r'深夜打游戏没人陪\？TT语音[\s\S]*?轻松开黑[！!]', ''),
            (r'半夜睡不着想开黑\？TT语音[\s\S]*?轻松开黑[！!]', ''),
            (r'TT语音的广告', ''),
            (r'蔡司的广告', ''),
            # 结尾 UI 文本
            (r'升级泽锐防蓝光后实际佩戴感受如何？', ''),
            (r'下载知乎客户端与世界分享知识、经验和见解', ''),
            # 回答底部 UI（礼物提示、发布时间、AI 追问）
            (r'还没有人送礼物[，,]\s*鼓励一下作者吧', ''),
            (r'发布于\s*\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}[・·][^\n]*', ''),
            (r'编辑于\s*\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}[・·][^\n]*', ''),
            (r'继续追问[\s\S]*?由知乎直答提供[\s\S]*$', ''),
            # 结尾的"查看全部 X 个回答"（不跟 .*$ 避免误删正文）
            (r'查看全部\s*[\d,]+\s*个回答\s*', ''),
            (r'\n\d+\s*个回答\s*$', ''),
            # 热点推荐
            (r'2025你不可错过的热榜时刻', ''),
            (r'话题收录', ''),
        ],
        'text_patterns': [
            r'^赞同\s*[\d,.]+\s*万?\s*$',
            r'^添加评论$', r'^分享$', r'^收藏$', r'^喜欢$',
            r'^展开阅读全文$', r'^收起$', r'^阅读全文$',
        ],
    },
    'mp.weixin.qq.com': {
        'html_selectors': [
            '.rich_media_meta_list',  # 作者/日期栏
            '#js_pc_qr_code',          # 二维码
            '.reward_area',            # 赞赏
            '.like_media_guide',       # 点赞引导
            '.rich_media_area_extra',  # 底部推荐
            '.qr_code_pc_outer',       # 关注二维码
            '.article_ad',             # 广告
        ],
        'text_patterns': [
            r'^微信扫一扫关注该公众号$',
            r'^扫描二维码关注.*$',
            r'^长按识别二维码.*$',
            r'^关注公众号.*$',
            r'^阅读\s*\d+$',
            r'^赞\s*\d+$',
            r'^在看\s*\d+$',
            r'^写下你的留言$',
            r'^精选留言$',
            r'^以上内容为公益广告.*$',
        ],
    },
}

# 通用噪音文本模式（所有网站生效）
COMMON_NOISE_PATTERNS = [
    r'^广告$',
    r'^推广$',
    r'^赞助$',
    r'^Copyright\s*©.*$',
    r'^All Rights Reserved\.?$',
    r'^版权所有.*$',
    r'^免责声明[:：].*$',
    r'^文章来源[:：].*$',
    r'^原文链接[:：].*$',
]


def _match_domain(domain):
    """匹配域名规则：精确匹配或子域名匹配"""
    for key in DOMAIN_CLEANUP:
        if domain == key or domain.endswith('.' + key):
            return key
    return None


def _extract_zhihu_answer_id(url):
    """从知乎 URL 中提取 answer ID"""
    # /question/<qid>/answer/<aid>  或  /answer/<aid>
    m = re.search(r'/answer/(\d+)', url)
    return m.group(1) if m else None


def _find_target_element(soup, url):
    """根据 URL 精确定位目标内容元素，避免提取页面其他无关内容。
    返回 (element, domain) 或 (None, None) 表示未找到特定元素，需回退通用提取。"""
    domain = urlparse(url).netloc

    # 知乎回答：优先取 soup 级别第一个 .RichContent（对应第一个回答）
    aid = _extract_zhihu_answer_id(url)
    if aid:
        # CSS 选择器直接取第一个匹配的 RichContent
        rich = soup.select_one('.RichContent')
        if rich and len(rich.get_text(strip=True)) > 200:
            return rich, domain
        # 备用：第一个回答卡片
        card = soup.select_one('.ContentItem.AnswerItem, .AnswerItem')
        if card and len(card.get_text(strip=True)) > 200:
            return card, domain

    return None, None


def cleanup_html(soup, domain):
    """根据域名规则，在 HTML 层面移除噪音元素"""
    key = _match_domain(domain)
    if not key:
        return soup
    rules = DOMAIN_CLEANUP.get(key, {})
    selectors = rules.get('html_selectors', [])

    for sel in selectors:
        try:
            for el in soup.select(sel):
                el.decompose()
        except Exception:
            pass

    # 通用清理：仅移除明确的广告标记属性
    for attr in ('data-ad', 'data-advertisement', 'data-recommend'):
        for el in soup.find_all(attrs={attr: True}):
            el.decompose()

    return soup


def cleanup_text(text, domain):
    """根据域名规则清除文本噪音：先做字符串级替换，再做行级移除"""
    key = _match_domain(domain)
    if not key:
        return text
    rules = DOMAIN_CLEANUP.get(key, {})

    # Step 1: 字符串级正则替换（处理混在正文中的噪音）
    subs = rules.get('text_substitutions', [])
    for pat, repl in subs:
        text = re.sub(pat, repl, text)

    # Step 2: 行级正则移除（处理独立行的噪音）
    patterns = rules.get('text_patterns', []) + COMMON_NOISE_PATTERNS
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        is_noise = False
        for pat in patterns:
            if re.match(pat, stripped):
                is_noise = True
                break
        if not is_noise:
            cleaned.append(line)

    # 合并连续空行
    result = '\n'.join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    # 清理行尾/行首空白
    result = re.sub(r' +\n', '\n', result)
    result = re.sub(r'\n +', '\n', result)
    return result.strip()


# ============================================================
    """从 URL 抓取并提取文章内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    resp.encoding = resp.apparent_encoding or 'utf-8'
    html = resp.text

    soup = BeautifulSoup(html, 'lxml')

    # --- 提取标题 ---
    title = ''
    for meta in soup.find_all('meta'):
        prop = (meta.get('property') or '').lower()
        name = (meta.get('name') or '').lower()
        if prop in ('og:title', 'twitter:title') or name in ('og:title', 'twitter:title'):
            t = meta.get('content', '').strip()
            if t:
                title = t
                break
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    if not title:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
    if not title:
        title = '未命名文章'
    title = re.sub(r'\s*[|\-–—»]\s*[^|\-–—»]*$', '', title).strip()
    title = re.sub(r'\s+', ' ', title)

    # --- 提取作者 ---
    author = ''
    for meta in soup.find_all('meta'):
        mn = (meta.get('name') or '').lower()
        mp = (meta.get('property') or '').lower()
        if mn in ('author', 'article:author') or mp == 'article:author':
            a = meta.get('content', '').strip()
            if a:
                author = a
                break
    if not author:
        for cls in ('author', 'byline', 'writer', 'contributor'):
            el = soup.find(class_=re.compile(cls, re.I))
            if el:
                author = el.get_text(strip=True)
                break

    # --- 提取发布日期 ---
    date_str = ''
    for meta in soup.find_all('meta'):
        mp = (meta.get('property') or '').lower()
        mn = (meta.get('name') or '').lower()
        if mp == 'article:published_time' or mn in ('publication_date', 'date', 'publishdate', 'weibo:article:create_at'):
            d = meta.get('content', '').strip()
            if d:
                date_str = d[:10]
                break
    if not date_str:
        for cls in ('date', 'time', 'publish-time', 'post-date'):
            el = soup.find(class_=re.compile(cls, re.I))
            if el:
                t = el.get('datetime') or el.get_text(strip=True)
                m = re.search(r'(\d{4}-\d{2}-\d{2})', t)
                if m:
                    date_str = m.group(1)
                    break

    # --- 移除噪音标签 ---
    for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'form', 'noscript',
                     'iframe', 'svg', 'header', 'button', 'input', 'textarea']):
        tag.decompose()
    for cls in ('sidebar', 'advertisement', 'comments', 'comment', 'social',
                'share', 'newsletter', 'related', 'recommend', 'popup', 'modal',
                'nav', 'footer', 'header', 'breadcrumb', 'toolbar', 'menu', 'widget'):
        for el in soup.find_all(class_=re.compile(r'\b' + cls + r'\b', re.I)):
            el.decompose()
    for el in soup.find_all(class_=re.compile(r'(?:^|\s)ad(?:\s|$)', re.I)):
        el.decompose()
    for el in soup.find_all(class_=re.compile(r'(?:^|\s)hot(?:\s|$)', re.I)):
        el.decompose()

    # 领域特定 HTML 清理
    domain = urlparse(url).netloc
    soup = cleanup_html(soup, domain)

    # --- 找正文区域 ---
    # 先尝试按 URL 精确定位目标元素（如知乎具体回答）
    article, _ = _find_target_element(soup, url)
    if not article:
        article = soup.find('article')
    if not article:
        article = soup.find(role='main')
    if not article:
        for sel in ('main', '.content', '.post', '.article', '.entry',
                    '#content', '#article', '#post', '.post-content', '.article-content'):
            article = soup.select_one(sel)
            if article:
                break
    if not article:
        article = soup.body or soup

    # --- HTML 转 Markdown ---
    uri = urlparse(url)
    base_url = f'{uri.scheme}://{uri.netloc}'

    body_md = convert_html_to_md(article, base_url, uri)
    body_md = re.sub(r'\n{3,}', '\n\n', body_md)
    # 文本级噪音清理
    body_md_before = body_md
    body_md = cleanup_text(body_md, domain)
    if len(body_md) < 50 and len(body_md_before) > 50:
        body_md = body_md_before

    word_count = len(re.sub(r'\s+', '', body_md))

    return {
        'title': title,
        'author': author or None,
        'date': date_str or None,
        'body': body_md,
        'word_count': word_count,
        'domain': urlparse(url).netloc,
        'final_url': resp.url,
    }


BROWSER_PROFILE_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'playwright-profile')

BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
]

INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
"""


def _create_browser_context(p, headless=True):
    """创建持久化浏览器上下文，cookie 自动保存到 profile 目录"""
    context = p.chromium.launch_persistent_context(
        user_data_dir=BROWSER_PROFILE_DIR,
        channel='chrome',
        headless=headless,
        args=BROWSER_ARGS,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        bypass_csp=True,
        accept_downloads=False,
    )
    return context


def browser_login(url=None):
    """打开可见浏览器窗口，用户手动登录目标网站"""
    from playwright.sync_api import sync_playwright

    target = url or 'https://www.zhihu.com'
    with sync_playwright() as p:
        context = _create_browser_context(p, headless=False)
        page = context.new_page()
        page.add_init_script(INIT_SCRIPT)
        print(f'正在打开 {target}，请在浏览器窗口中登录...', file=sys.stderr)
        page.goto(target, wait_until='networkidle', timeout=30000)
        print('浏览器已打开，登录完成后请手动关闭浏览器窗口。', file=sys.stderr)
        print('关闭后将自动保存登录状态，之后的抓取无需再次登录。', file=sys.stderr)
        # 等待用户手动关闭浏览器
        try:
            page.wait_for_event('close', timeout=300000)  # 5 分钟超时
        except Exception:
            pass
        context.close()
        print('登录状态已保存。', file=sys.stderr)


def fetch_url_browser(url, img_dir=None):
    """用本地 Chrome 持久化配置抓取页面（headless，复用已保存的 cookie）。
    若提供 img_dir，将下载页面中的图片到此目录并替换 Markdown 路径。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = _create_browser_context(p, headless=True)
        page = context.new_page()
        page.add_init_script(INIT_SCRIPT)

        page.goto(url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        final_url = page.url

        # 检测是否被拦截或需要登录
        if '您当前请求存在异常' in html:
            raise RuntimeError('zhihu_blocked')
        if '/signin' in final_url and 'zhihu.com' in final_url:
            context.close()
            raise RuntimeError('zhihu_login_required')

        context.close()

        soup = BeautifulSoup(html, 'lxml')

        # --- 提取标题 ---
        title = ''
        for meta in soup.find_all('meta'):
            prop = (meta.get('property') or '').lower()
            name = (meta.get('name') or '').lower()
            if prop in ('og:title', 'twitter:title') or name in ('og:title', 'twitter:title'):
                t = meta.get('content', '').strip()
                if t:
                    title = t
                    break
        if not title and soup.title:
            title = soup.title.get_text(strip=True)
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        if not title:
            title = '未命名文章'
        title = re.sub(r'\s*[|\-–—»]\s*[^|\-–—»]*$', '', title).strip()
        title = re.sub(r'\s+', ' ', title)

        # --- 提取作者 ---
        author = ''
        for meta in soup.find_all('meta'):
            mn = (meta.get('name') or '').lower()
            mp = (meta.get('property') or '').lower()
            if mn in ('author', 'article:author') or mp == 'article:author':
                a = meta.get('content', '').strip()
                if a:
                    author = a
                    break
        if not author:
            for cls in ('author', 'byline', 'writer', 'contributor'):
                el = soup.find(class_=re.compile(cls, re.I))
                if el:
                    author = el.get_text(strip=True)
                    break

        # --- 提取发布日期 ---
        date_str = ''
        for meta in soup.find_all('meta'):
            mp = (meta.get('property') or '').lower()
            mn = (meta.get('name') or '').lower()
            if mp == 'article:published_time' or mn in ('publication_date', 'date', 'publishdate', 'weibo:article:create_at'):
                d = meta.get('content', '').strip()
                if d:
                    date_str = d[:10]
                    break
        if not date_str:
            for cls in ('date', 'time', 'publish-time', 'post-date'):
                el = soup.find(class_=re.compile(cls, re.I))
                if el:
                    t = el.get('datetime') or el.get_text(strip=True)
                    m = re.search(r'(\d{4}-\d{2}-\d{2})', t)
                    if m:
                        date_str = m.group(1)
                        break

        # --- 移除噪音标签 ---
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'form', 'noscript',
                         'iframe', 'svg', 'header', 'button', 'input', 'textarea']):
            tag.decompose()
        for c in ('sidebar', 'advertisement', 'comments', 'comment', 'social',
                  'share', 'newsletter', 'related', 'recommend', 'popup', 'modal'):
            for el in soup.find_all(class_=re.compile(r'\b' + c + r'\b', re.I)):
                el.decompose()
        # 'ad' 和 'hot' 单独处理——太短容易误匹配（如 RichContent--hasHotComment）
        for el in soup.find_all(class_=re.compile(r'(?:^|\s)ad(?:\s|$)', re.I)):
            el.decompose()
        for el in soup.find_all(class_=re.compile(r'(?:^|\s)hot(?:\s|$)', re.I)):
            el.decompose()

        # 领域特定 HTML 清理
        domain = urlparse(url).netloc
        soup = cleanup_html(soup, domain)

        # --- 找正文区域 ---
        # 先尝试按 URL 精确定位目标元素（如知乎具体回答）
        article, _ = _find_target_element(soup, url)
        if not article:
            article = soup.find('article')
        if not article:
            article = soup.find(role='main')
        if not article:
            for sel in ('main', '.content', '.post', '.article', '.entry',
                        '#content', '#article', '#post', '.post-content', '.article-content',
                        '.RichContent', '.AnswerCard', '.QuestionAnswer-content'):
                article = soup.select_one(sel)
                if article:
                    break
        if not article:
            article = soup.body or soup
        uri = urlparse(url)
        base_url = f'{uri.scheme}://{uri.netloc}'

        body_md = convert_html_to_md(article, base_url, uri)
        body_md = re.sub(r'\n{3,}', '\n\n', body_md)

        # --- 下载图片 ---
        if img_dir:
            img_urls = collect_image_urls(article, base_url, uri)
            if img_urls:
                img_map = download_images(page, img_urls, img_dir)
                for old_url, local_path in img_map.items():
                    body_md = body_md.replace(old_url, local_path)

    # 文本级噪音清理
        body_md_before = body_md
        body_md = cleanup_text(body_md, domain)
        if len(body_md) < 50 and len(body_md_before) > 50:
            body_md = body_md_before  # 清理过度时回退
        word_count = len(re.sub(r'\s+', '', body_md))

        return {
            'title': title,
            'author': author or None,
            'date': date_str or None,
            'body': body_md,
            'word_count': word_count,
            'domain': urlparse(url).netloc,
            'final_url': final_url,
        }



def collect_image_urls(element, base_url, uri):
    """从 HTML 元素中收集所有 img 的完整 URL（去重）"""
    urls = []
    seen = set()
    for img in element.find_all('img'):
        src = img.get('src', '') or img.get('data-src', '') or img.get('data-original', '')
        if not src:
            continue
        if src.startswith('//'):
            src = f'{uri.scheme}:' + src
        elif src.startswith('/'):
            src = base_url + src
        if not src.startswith('http'):
            continue
        if src not in seen:
            seen.add(src)
            urls.append(src)
    return urls


def download_images(page, img_urls, img_dir):
    """用 Playwright page（复用登录态 cookie）下载图片。
    返回 {old_url: relative_path} 映射。"""
    import hashlib
    mapping = {}
    if not img_urls:
        return mapping
    os.makedirs(img_dir, exist_ok=True)

    for url in img_urls:
        try:
            ext = os.path.splitext(urlparse(url).path)[1].split('?')[0].split('#')[0]
            if not ext or len(ext) > 6:
                ext = '.jpg'
            name = hashlib.md5(url.encode()).hexdigest()[:12] + ext
            path = os.path.join(img_dir, name)
            if os.path.exists(path):
                mapping[url] = os.path.join('images', name)
                continue
            resp = page.goto(url, timeout=15000)
            if resp and resp.ok:
                with open(path, 'wb') as f:
                    f.write(resp.body())
                mapping[url] = os.path.join('images', name)
        except Exception:
            continue
    return mapping

def convert_html_to_md(element, base_url, uri):
    lines = []
    for child in element.children:
        if not hasattr(child, 'name') or child.name is None:
            text = str(child).strip()
            if text:
                lines.append(text)
            continue

        tag = child.name
        if tag in ('h1',):
            t = child.get_text(strip=True)
            if t: lines.append(f'# {t}')
        elif tag == 'h2':
            t = child.get_text(strip=True)
            if t: lines.append(f'## {t}')
        elif tag == 'h3':
            t = child.get_text(strip=True)
            if t: lines.append(f'### {t}')
        elif tag in ('h4', 'h5', 'h6'):
            t = child.get_text(strip=True)
            if t: lines.append(f'#### {t}')
        elif tag == 'p':
            parts = []
            for c in child.descendants:
                if c.name == 'a':
                    href = c.get('href', '')
                    ct = c.get_text(strip=True)
                    if href and ct and not href.startswith('javascript'):
                        if href.startswith('/'):
                            href = base_url + href
                        parts.append(f'[{ct}]({href})')
                    elif ct:
                        parts.append(ct)
                elif c.name in ('strong', 'b'):
                    ct = c.get_text(strip=True)
                    if ct: parts.append(f'**{ct}**')
                elif c.name in ('em', 'i'):
                    ct = c.get_text(strip=True)
                    if ct: parts.append(f'*{ct}*')
                elif c.name == 'code' and not c.find_parent('pre'):
                    ct = c.get_text(strip=True)
                    if ct: parts.append(f'`{ct}`')
                elif c.name == 'img':
                    alt = c.get('alt', '')
                    src = c.get('src', '') or c.get('data-src', '')
                    if src:
                        if src.startswith('//'):
                            src = f'{uri.scheme}:' + src
                        elif src.startswith('/'):
                            src = base_url + src
                        parts.append(f'![{alt}]({src})')
                elif c.name is None:
                    t = str(c).strip()
                    if t and t not in parts:
                        parts.append(t)
            line = ' '.join(filter(None, parts)).strip()
            if line:
                lines.append(line)
        elif tag in ('ul', 'ol'):
            for li in child.find_all('li', recursive=False):
                t = li.get_text(strip=True)
                if t:
                    prefix = '- ' if tag == 'ul' else '1. '
                    lines.append(f'{prefix}{t}')
        elif tag == 'blockquote':
            t = child.get_text(strip=True)
            if t:
                for line in t.split('\n'):
                    lines.append(f'> {line.strip()}')
        elif tag in ('pre',):
            code_el = child.find('code')
            lang = ''
            if code_el and code_el.get('class'):
                for c in code_el['class']:
                    if c.startswith('language-'):
                        lang = c[9:]
            code_text = code_el.get_text() if code_el else child.get_text()
            lines.append(f'```{lang}\n{code_text.strip()}\n```')
        elif tag == 'hr':
            lines.append('---')
        elif tag in ('figure', 'figcaption'):
            t = child.get_text(strip=True)
            if t: lines.append(t)
        elif tag in ('table',):
            lines.append(child.get_text(strip=True))
        else:
            t = child.get_text(strip=True)
            if t and len(t) > 20:
                lines.append(t)

    return '\n\n'.join(lines)


def read_body_from_stdin():
    return sys.stdin.read().strip()

def read_body_from_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def do_paste(save_dir, title, body):
    word_count = len(re.sub(r'\s+', '', body))
    source_info = {
        'url': None, 'author': None,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'domain': None, 'source': 'paste',
    }
    return save_article(save_dir, title, body, word_count, source_info)

def do_url(save_dir, url):
    data = fetch_url(url)
    if data['word_count'] < 50:
        preview = data['body'][:200]
        print(f'WARNING:short_content:{json.dumps({"word_count": data["word_count"], "preview": preview})}', file=sys.stderr)
    source_info = {
        'url': data['final_url'], 'author': data['author'],
        'date': data['date'], 'domain': data['domain'], 'source': 'url',
    }
    result = save_article(save_dir, data['title'], data['body'], data['word_count'], source_info)
    result['title'] = data['title']
    result['domain'] = data['domain']
    return result

def do_url_browser(save_dir, url):
    """使用本地 Chrome 浏览器抓取，适用于强反爬网站"""
    try:
        now = datetime.now()
        img_dir = os.path.join(save_dir, now.strftime("%Y"), now.strftime("%m"), "images")
        data = fetch_url_browser(url, img_dir=img_dir)
    except RuntimeError as e:
        if str(e) == 'zhihu_login_required':
            print(json.dumps({
                'error': 'login_required',
                'message': '知乎需要登录。请先运行: python extract.py <save_dir> --browser-login',
            }, ensure_ascii=False))
            sys.exit(2)
        elif str(e) == 'zhihu_blocked':
            # 被反爬拦截，降级为提示用户手动登录
            print(json.dumps({
                'error': 'blocked',
                'message': '访问被拦截，可能需要先登录。请运行: python extract.py <save_dir> --browser-login',
            }, ensure_ascii=False))
            sys.exit(2)
        else:
            raise

    if data['word_count'] < 50:
        preview = data['body'][:200]
        print(f'WARNING:short_content:{json.dumps({"word_count": data["word_count"], "preview": preview})}', file=sys.stderr)
    source_info = {
        'url': data['final_url'], 'author': data['author'],
        'date': data['date'], 'domain': data['domain'], 'source': 'url',
    }
    result = save_article(save_dir, data['title'], data['body'], data['word_count'], source_info)
    result['title'] = data['title']
    result['domain'] = data['domain']
    return result

def main():
    if len(sys.argv) < 3:
        print('用法: python extract.py <save_dir> <url>', file=sys.stderr)
        print('      python extract.py <save_dir> --browser <url>', file=sys.stderr)
        print('      python extract.py <save_dir> --browser-login [url]', file=sys.stderr)
        print('      python extract.py <save_dir> --paste <title>  (从 stdin 读取)', file=sys.stderr)
        print('      python extract.py <save_dir> --file <title> <path>', file=sys.stderr)
        sys.exit(1)

    save_dir = sys.argv[1]
    mode = sys.argv[2]

    if mode == '--file':
        title = sys.argv[3] if len(sys.argv) > 3 else '未命名文章'
        filepath = sys.argv[4] if len(sys.argv) > 4 else None
        if not filepath:
            print('错误: --file 需要指定文件路径', file=sys.stderr)
            sys.exit(1)
        body = read_body_from_file(filepath)
        result = do_paste(save_dir, title, body)
    elif mode == '--paste':
        title = sys.argv[3] if len(sys.argv) > 3 else '未命名文章'
        body = read_body_from_stdin()
        result = do_paste(save_dir, title, body)
    elif mode == '--browser-login':
        login_url = sys.argv[3] if len(sys.argv) > 3 else None
        browser_login(login_url)
        print(json.dumps({'status': 'ok', 'message': '登录完成，cookie 已保存'}, ensure_ascii=False))
        return
    elif mode == '--browser':
        if len(sys.argv) < 4:
            print('错误: --browser 需要指定 URL', file=sys.stderr)
            sys.exit(1)
        result = do_url_browser(save_dir, sys.argv[3])
    else:
        url = mode  # 直接传 URL
        result = do_url(save_dir, url)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
