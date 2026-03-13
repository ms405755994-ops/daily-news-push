import os
import requests
from collections import defaultdict
from openai import OpenAI

# ===============================
# 配置
# ===============================

NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY", "YOUR_NEWSDATA_KEY")
GNEWS_KEY = os.getenv("GNEWS_KEY", "YOUR_GNEWS_KEY")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "YOUR_OPENROUTER_KEY")

WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "YOUR_WECHAT_WEBHOOK")

OPENROUTER_MODEL = "openai/gpt-oss-120b"

MAX_FETCH_PER_API = 20
MAX_NEWS = 10

# ===============================
# OpenRouter 客户端
# ===============================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com",
        "X-Title": "daily-news-push",
    },
)

# ===============================
# AI调用
# ===============================

def ask_ai(prompt):

    try:

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print("AI error:", e)

        return ""

# ===============================
# 新闻 API - NewsData
# ===============================

def fetch_newsdata():

    url = "https://newsdata.io/api/1/news"

    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en",
        "size": MAX_FETCH_PER_API,
    }

    try:

        r = requests.get(url, params=params, timeout=30)

        data = r.json()

        news = []

        for n in data.get("results", []):

            news.append({
                "title": n.get("title"),
                "link": n.get("link")
            })

        return news

    except Exception as e:

        print("NewsData error:", e)

        return []

# ===============================
# 新闻 API - GNews
# ===============================

def fetch_gnews():

    url = "https://gnews.io/api/v4/top-headlines"

    params = {
        "apikey": GNEWS_KEY,
        "lang": "en",
        "max": MAX_FETCH_PER_API,
    }

    try:

        r = requests.get(url, params=params, timeout=30)

        data = r.json()

        news = []

        for n in data.get("articles", []):

            news.append({
                "title": n.get("title"),
                "link": n.get("url")
            })

        return news

    except Exception as e:

        print("GNews error:", e)

        return []

# ===============================
# 第一层去重（标题精确）
# ===============================

def exact_deduplicate(news):

    seen = set()

    unique = []

    for n in news:

        t = n["title"].lower()

        if t not in seen:

            seen.add(t)

            unique.append(n)

    return unique

# ===============================
# AI事件级去重
# ===============================

def ai_is_duplicate(title1, title2):

    prompt = f"""
判断下面两条新闻标题是否是同一事件

标题1：
{title1}

标题2：
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
# AI分类
# ===============================

def ai_classify(title):

    prompt = f"""
给这条新闻分类

{title}

分类选项：

AI
科技
金融
国际
商业
其他

只输出分类名称
"""

    result = ask_ai(prompt)

    return result if result else "其他"

# ===============================
# AI摘要
# ===============================

def ai_summary(title):

    prompt = f"""
用一句中文总结这条新闻

标题：
{title}

要求：

20字以内
"""

    result = ask_ai(prompt)

    return result

# ===============================
# AI重要度评分
# ===============================

def ai_score(title):

    prompt = f"""
请给下面新闻标题的重要度评分

{title}

评分规则：

5 = 全球重大新闻
4 = 行业重要新闻
3 = 普通新闻
2 = 一般资讯
1 = 不重要

只输出数字
"""

    result = ask_ai(prompt)

    try:

        return int(result)

    except:

        return 3

# ===============================
# 新闻处理
# ===============================

def process_news(news):

    print("原始新闻:", len(news))

    news = exact_deduplicate(news)

    print("标题去重:", len(news))

    news = news[:MAX_NEWS]

    news = ai_deduplicate(news)

    print("AI去重:", len(news))

    for n in news:

        n["category"] = ai_classify(n["title"])

        n["summary"] = ai_summary(n["title"])

        n["score"] = ai_score(n["title"])

    news.sort(key=lambda x: x["score"], reverse=True)

    return news

# ===============================
# 格式化消息
# ===============================

def format_message(news):

    groups = defaultdict(list)

    for n in news:

        groups[n["category"]].append(n)

    message = "🌍 今日全球新闻\n\n"

    for cat, items in groups.items():

        message += f"【{cat}】\n"

        for i, n in enumerate(items, 1):

            message += f"{i}. {n['title']}\n"

            message += f"摘要：{n['summary']}\n"

            message += f"{n['link']}\n\n"

    return message

# ===============================
# 微信推送
# ===============================

def push_wechat(msg):

    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    try:

        requests.post(WECHAT_WEBHOOK, json=data)

        print("微信推送成功")

    except Exception as e:

        print("微信推送失败", e)

# ===============================
# 主程序
# ===============================

def main():

    print("开始抓取新闻...")

    news1 = fetch_newsdata()

    news2 = fetch_gnews()

    news = news1 + news2

    print("抓取新闻总数:", len(news))

    news = process_news(news)

    message = format_message(news)

    print(message)

    push_wechat(message)

if __name__ == "__main__":

    main()
