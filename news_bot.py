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
# 新闻 API - NewsData
# ===============================

def fetch_newsdata():

    if not NEWS_DATA_KEY:
        print("NEWS_DATA_KEY 未配置")
        return []

    url = "https://newsdata.io/api/1/news"

    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en",
        "size": MAX_FETCH_PER_API,
    }

    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        data = r.json()

        news = []

        for n in data.get("results", []):
            title = (n.get("title") or "").strip()
            link = (n.get("link") or "").strip()

            if title and link:
                news.append({
                    "title": title,
                    "link": link
                })

        return news

    except Exception as e:
        print("NewsData error:", e)
        return []

# ===============================
# 新闻 API - GNews
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
        data = r.json()

        news = []

        for n in data.get("articles", []):

            title = (n.get("title") or "").strip()
            link = (n.get("url") or "").strip()

            if title and link:

                news.append({
                    "title": title,
                    "link": link
                })

        return news

    except Exception as e:

        print("GNews error:", e)

        return []

# ===============================
# 标题去重
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
# AI事件去重
# ===============================

def ai_is_duplicate(title1, title2):

    prompt = f"""
判断下面两条新闻标题是否是同一事件

标题1:
{title1}

标题2:
{title2}

只回答 YES 或 NO
"""

    result = ask_ai(prompt)

    return "YES" in result.upper()

def ai_deduplicate(news):

    unique = []

    for n in news:

        duplicate = False

        for u in unique:

            if ai_is_duplicate(n["title"], u["title"]):

                duplicate = True
                break

        if not duplicate:
            unique.append(n)

    return unique

# ===============================
# AI 分类（新分类体系）
# ===============================

def ai_classify(title: str) -> str:

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

只输出分类名称
"""

    result = ask_ai(prompt)

    allowed = {
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
    }

    return result if result in allowed else "社会"

# ===============================
# AI 摘要
# ===============================

def ai_summary(title: str) -> str:

    prompt = f"""
请用一句中文总结这条新闻

标题：
{title}

要求：
20字以内
"""

    result = ask_ai(prompt)

    return result if result else "暂无摘要"

# ===============================
# AI 评分
# ===============================

def ai_score(title: str) -> int:

    prompt = f"""
给下面新闻评分 1-5

标题：
{title}

5 = 全球重大
4 = 行业重要
3 = 普通
2 = 一般
1 = 不重要

只输出数字
"""

    result = ask_ai(prompt)

    try:
        return int(result)
    except:
        return 3

# ===============================
# AI 分析
# ===============================

def enrich_news(news):

    for n in news:

        n["category"] = ai_classify(n["title"])
        n["summary"] = ai_summary(n["title"])
        n["score"] = ai_score(n["title"])

    return news

# ===============================
# 今日三大新闻
# ===============================

def select_top3(news):

    if len(news) <= 3:
        return news

    news_sorted = sorted(news, key=lambda x: x["score"], reverse=True)

    return news_sorted[:3]

# ===============================
# 处理新闻
# ===============================

def process_news(news):

    print("原始新闻:", len(news))

    news = exact_deduplicate(news)

    print("标题去重:", len(news))

    news = news[:MAX_NEWS]

    news = ai_deduplicate(news)

    print("AI去重:", len(news))

    news = enrich_news(news)

    news.sort(key=lambda x: x["score"], reverse=True)

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

    message = "🌍 今日全球新闻雷达\n\n"

    if top3:

        message += "【今日三大新闻】\n"

        for i, n in enumerate(top3, 1):

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
# 微信推送
# ===============================

def push_wechat(msg: str):

    if not WECHAT_WEBHOOK:
        print("未配置微信 webhook")
        return

    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    try:

        requests.post(WECHAT_WEBHOOK, json=data, timeout=REQUEST_TIMEOUT)

        print("微信推送成功")

    except Exception as e:

        print("微信推送失败", e)

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
