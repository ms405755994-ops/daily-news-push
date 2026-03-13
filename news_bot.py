import os
import requests
from collections import defaultdict
from openai import OpenAI

# ===============================
# 配置
# ===============================

NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY", "")
GNEWS_KEY = os.getenv("GNEWS_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "")

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")

MAX_FETCH_PER_API = int(os.getenv("MAX_FETCH_PER_API", "20"))
MAX_NEWS = int(os.getenv("MAX_NEWS", "10"))
REQUEST_TIMEOUT = 30

# ===============================
# OpenRouter 客户端
# ===============================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com/ms405755994-ops/daily-news-push",
        "X-Title": "daily-news-push",
    },
)

# ===============================
# AI 调用
# ===============================

def ask_ai(prompt: str, temperature: float = 0.2) -> str:
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        print("AI error:", e)
        return ""

# ===============================
# 中文链接识别
# ===============================

def is_chinese_link(url: str) -> bool:
    if not url:
        return False

    url = url.lower()

    cn_domains = [
        ".cn",
        "sina.com",
        "qq.com",
        "163.com",
        "thepaper.cn",
        "ifeng.com",
        "guancha.cn",
        "caixin.com",
        "china.com",
        "people.com.cn",
        "xinhuanet.com",
        "cctv.com",
        "yicai.com",
        "jiemian.com",
        "36kr.com",
        "huxiu.com",
        "stcn.com",
        "eastmoney.com"
    ]

    for d in cn_domains:
        if d in url:
            return True

    if "/cn/" in url or "/zh/" in url or "lang=zh" in url:
        return True

    return False

# ===============================
# 抓取 NewsData
# ===============================

def fetch_newsdata():
    if not NEWS_DATA_KEY:
        print("NEWS_DATA_KEY 未配置")
        return []

    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en,zh",
        "size": MAX_FETCH_PER_API,
    }

    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        news = []
        for n in data.get("results", []):
            title = (n.get("title") or "").strip()
            link = (n.get("link") or "").strip()

            if title and link:
                news.append({
                    "title": title,
                    "link": link,
                    "source": "NewsData"
                })

        return news
    except Exception as e:
        print("NewsData error:", e)
        return []

# ===============================
# 抓取 GNews
# ===============================

def fetch_gnews():
    if not GNEWS_KEY:
        print("GNEWS_KEY 未配置")
        return []

    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "apikey": GNEWS_KEY,
        "lang": "en",
        "max": MAX_FETCH_PER_API,
    }

    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        news = []
        for n in data.get("articles", []):
            title = (n.get("title") or "").strip()
            link = (n.get("url") or "").strip()

            if title and link:
                news.append({
                    "title": title,
                    "link": link,
                    "source": "GNews"
                })

        return news
    except Exception as e:
        print("GNews error:", e)
        return []

# ===============================
# 标题精确去重
# ===============================

def exact_deduplicate(news):
    seen = set()
    unique = []

    for n in news:
        title = n["title"].strip().lower()
        if title not in seen:
            seen.add(title)
            unique.append(n)

    return unique

# ===============================
# 轻量预筛
# ===============================

def normalize_title(title: str) -> str:
    t = title.lower()
    for ch in ["|", "-", "—", ":", "：", ",", ".", "(", ")", "[", "]", "'", '"']:
        t = t.replace(ch, " ")
    return " ".join(t.split())

def rough_similar(title1: str, title2: str) -> bool:
    a = set(normalize_title(title1).split())
    b = set(normalize_title(title2).split())

    if not a or not b:
        return False

    overlap = len(a & b) / max(1, min(len(a), len(b)))
    return overlap >= 0.75

# ===============================
# AI 事件去重
# ===============================

def ai_is_duplicate(title1: str, title2: str) -> bool:
    prompt = f"""
判断下面两条新闻标题是否是同一事件。
只回答 YES 或 NO。

标题1：
{title1}

标题2：
{title2}
"""
    result = ask_ai(prompt)
    return "YES" in result.upper()

def ai_deduplicate(news):
    unique = []

    for n in news:
        duplicate = False

        for u in unique:
            if not rough_similar(n["title"], u["title"]):
                continue

            if ai_is_duplicate(n["title"], u["title"]):
                duplicate = True
                break

        if not duplicate:
            unique.append(n)

    return unique

# ===============================
# 突发新闻规则识别
# ===============================

def is_breaking_by_rules(title: str) -> bool:
    t = title.lower()

    keywords = [
        "breaking", "urgent", "attack", "war", "missile", "strike", "explosion",
        "earthquake", "flood", "wildfire", "shooting", "hostage", "coup",
        "emergency", "sanction", "tariff", "ceasefire", "troops", "invasion",
        "dies", "killed", "crash", "outbreak"
    ]

    return any(k in t for k in keywords)

# ===============================
# AI 分类
# ===============================

def ai_classify(title: str) -> str:
    if is_breaking_by_rules(title):
        return "突发新闻"

    prompt = f"""
给这条新闻分类，只输出一个分类名称。

新闻标题：
{title}

分类选项：
突发新闻
政策
AI
科技
金融
经济
商业
国际
军事
能源
社会

分类规则补充：
1. 战争、袭击、灾害、重大突发事件优先归入“突发新闻”
2. 法规、政府决定、监管变化归入“政策”
3. 利率、股市、银行、债券归入“金融”
4. 宏观增长、通胀、就业、经济数据归入“经济”
5. 公司经营、并购、票房、商业模式归入“商业”
6. 国与国关系、外交、地区局势归入“国际”
7. 武器、军队、战事、国防归入“军事”
8. 石油、天然气、电力、煤炭、新能源供给归入“能源”
9. 医疗、教育、公共事件、社会话题归入“社会”

只输出分类名称
"""

    result = ask_ai(prompt)

    allowed = {
        "突发新闻", "政策", "AI", "科技", "金融",
        "经济", "商业", "国际", "军事", "能源", "社会"
    }

    return result if result in allowed else "社会"

# ===============================
# AI 摘要
# ===============================

def ai_summary(title: str) -> str:
    prompt = f"""
请用一句简体中文概括下面这条新闻标题。

要求：
1. 20字以内
2. 不要加句号
3. 不要照抄原标题
4. 只输出摘要

标题：
{title}
"""
    result = ask_ai(prompt)
    return result if result else "暂无摘要"

# ===============================
# AI 评分
# ===============================

def ai_score(title: str) -> int:
    if is_breaking_by_rules(title):
        return 5

    prompt = f"""
给下面新闻评分 1-5，只输出数字。

标题：
{title}

评分标准：
5 = 全球重大/高冲击事件
4 = 行业重要/高关注事件
3 = 普通值得关注新闻
2 = 一般资讯
1 = 不重要或噪音
"""
    result = ask_ai(prompt)

    try:
        score = int(result.strip())
        if 1 <= score <= 5:
            return score
    except Exception:
        pass

    return 3

# ===============================
# AI 分析
# ===============================

def enrich_news(news):
    for n in news:
        n["category"] = ai_classify(n["title"])
        n["summary"] = ai_summary(n["title"])
        n["score"] = ai_score(n["title"])
        n["lang_priority"] = 1 if is_chinese_link(n["link"]) else 0
    return news

# ===============================
# 今日三大新闻
# ===============================

def select_top3(news):
    if len(news) <= 3:
        return news[:]

    candidates = []
    for i, n in enumerate(news, 1):
        candidates.append(
            f"{i}. 标题：{n['title']}\n"
            f"分类：{n.get('category', '社会')}\n"
            f"摘要：{n.get('summary', '暂无摘要')}\n"
            f"评分：{n.get('score', 3)}\n"
            f"中文链接优先：{n.get('lang_priority', 0)}"
        )

    prompt = f"""
下面是今日候选新闻，请选出最值得作为“今日三大新闻”的3条。

要求：
1. 优先考虑全球影响力、公共关注度、市场冲击和政策/安全影响
2. 优先考虑突发新闻、政策、金融、国际、军事等高影响题材
3. 在同等重要度下，优先选择中文链接来源
4. 只输出 3 个编号，用英文逗号分隔
5. 例如：1,4,7

候选新闻：
{chr(10).join(candidates)}
"""

    result = ask_ai(prompt)
    print("Top3 raw result:", result)

    indices = []
    for part in result.replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(news):
                indices.append(idx)

    unique_indices = []
    for idx in indices:
        if idx not in unique_indices:
            unique_indices.append(idx)

    if len(unique_indices) < 3:
        news_sorted = sorted(
            news,
            key=lambda x: (x.get("lang_priority", 0), x.get("score", 3)),
            reverse=True
        )
        return news_sorted[:3]

    return [news[i] for i in unique_indices[:3]]

# ===============================
# 趋势检测
# ===============================

def detect_trends(news):
    counts = defaultdict(int)

    for n in news:
        counts[n.get("category", "社会")] += 1

    trend_lines = []

    if counts["AI"] >= 3:
        trend_lines.append("AI相关新闻密度较高")
    if counts["金融"] + counts["经济"] >= 3:
        trend_lines.append("宏观与金融主题升温")
    if counts["突发新闻"] >= 2:
        trend_lines.append("突发事件数量偏多")
    if counts["能源"] >= 2:
        trend_lines.append("能源议题活跃")
    if counts["国际"] + counts["军事"] >= 3:
        trend_lines.append("国际与安全局势升温")
    if counts["政策"] >= 2:
        trend_lines.append("政策监管动态增加")

    return trend_lines[:3]

# ===============================
# 自动生成重点板块
# ===============================

def pick_focus_items(news, categories, limit=2):
    items = [n for n in news if n.get("category") in categories]
    items.sort(
        key=lambda x: (x.get("lang_priority", 0), x.get("score", 3)),
        reverse=True
    )
    return items[:limit]

def build_focus_sections(news):
    macro_focus = pick_focus_items(news, ["政策", "经济", "国际", "能源", "突发新闻"], 2)
    ai_focus = pick_focus_items(news, ["AI", "科技"], 2)
    finance_focus = pick_focus_items(news, ["金融", "经济", "商业"], 2)

    return {
        "宏观重点": macro_focus,
        "AI重点": ai_focus,
        "金融重点": finance_focus,
    }

# ===============================
# 处理新闻
# ===============================

def process_news(news):
    print("原始新闻:", len(news))

    news = exact_deduplicate(news)
    print("标题去重:", len(news))

    news = news[:MAX_NEWS]
    print("进入 AI 处理数量:", len(news))

    news = ai_deduplicate(news)
    print("AI去重:", len(news))

    news = enrich_news(news)
    news.sort(
        key=lambda x: (x.get("lang_priority", 0), x.get("score", 3)),
        reverse=True
    )

    return news

# ===============================
# 格式化消息
# ===============================

def format_message(news):
    groups = defaultdict(list)

    for n in news:
        groups[n["category"]].append(n)

    ordered_categories = [
        "突发新闻",
        "政策",
        "AI",
        "科技",
        "金融",
        "经济",
        "商业",
        "国际",
        "军事",
        "能源",
        "社会"
    ]

    top3 = select_top3(news)
    trends = detect_trends(news)
    focus_sections = build_focus_sections(news)

    message = "🌍 今日全球新闻雷达\n\n"

    if top3:
        message += "【今日三大新闻】\n"
        for i, n in enumerate(top3, 1):
            message += f"{i}. {n['summary']}\n"
        message += "\n"

    if trends:
        message += "【趋势提示】\n"
        for i, line in enumerate(trends, 1):
            message += f"{i}. {line}\n"
        message += "\n"

    for section_name, items in focus_sections.items():
        if not items:
            continue

        message += f"【{section_name}】\n"
        for i, n in enumerate(items, 1):
            message += f"{i}. {n['summary']}\n"
        message += "\n"

    for cat in ordered_categories:
        items = groups.get(cat, [])
        if not items:
            continue

        message += f"【{cat}】\n"
        for i, n in enumerate(items, 1):
            message += f"{i}. {n['title']}\n"
            message += f"摘要：{n['summary']}\n"
            message += f"链接：{n['link']}\n\n"

    if len(message) > 3500:
        message = message[:3500] + "\n\n（内容过长已截断）"

    return message

# ===============================
# 企业微信机器人推送
# ===============================

def push_wechat(msg: str):
    if not WECHAT_WEBHOOK:
        print("WECHAT_WEBHOOK 未配置")
        return

    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    try:
        r = requests.post(WECHAT_WEBHOOK, json=data, timeout=REQUEST_TIMEOUT)
        print("企业微信推送状态:", r.status_code, r.text)
    except Exception as e:
        print("企业微信推送失败:", e)

# ===============================
# 主程序
# ===============================

def main():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY 未配置")

    print("开始抓新闻...")

    news1 = fetch_newsdata()
    news2 = fetch_gnews()

    news = news1 + news2

    print("新闻总数:", len(news))

    if not news:
        print("没有新闻")
        return

    news = process_news(news)
    message = format_message(news)

    print(message)
    push_wechat(message)

if __name__ == "__main__":
    main()
