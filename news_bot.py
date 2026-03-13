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

OPENROUTER_MODEL = "openai/gpt-oss-120b"

MAX_FETCH_PER_API = 20
MAX_NEWS = 10
REQUEST_TIMEOUT = 30

# WxPusher
WXPUSHER_APP_TOKEN = "AT_Bz9hoFvX8Q5waE50yaxm7TXcBlWt4fOR"
WXPUSHER_UID = "UID_KUuJWURonrRpOe94DIJmE38mYnWj"

# ===============================
# OpenRouter 客户端
# ===============================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ===============================
# AI 调用
# ===============================

def ask_ai(prompt: str):
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
# 中文链接识别
# ===============================

def is_chinese_link(url: str):

    url = url.lower()

    cn_domains = [
        ".cn","sina.com","qq.com","163.com","thepaper.cn",
        "ifeng.com","guancha.cn","caixin.com","people.com.cn",
        "xinhuanet.com","cctv.com","yicai.com","jiemian.com",
        "36kr.com","huxiu.com"
    ]

    for d in cn_domains:
        if d in url:
            return True

    if "/cn/" in url or "/zh/" in url:
        return True

    return False

# ===============================
# 抓取 NewsData
# ===============================

def fetch_newsdata():

    if not NEWS_DATA_KEY:
        return []

    url = "https://newsdata.io/api/1/news"

    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en,zh",
        "size": MAX_FETCH_PER_API
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
# 抓取 GNews
# ===============================

def fetch_gnews():

    if not GNEWS_KEY:
        return []

    url = "https://gnews.io/api/v4/top-headlines"

    params = {
        "apikey": GNEWS_KEY,
        "lang": "en",
        "max": MAX_FETCH_PER_API
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

        t = n["title"].lower()

        if t not in seen:
            seen.add(t)
            unique.append(n)

    return unique

# ===============================
# AI分类
# ===============================

def ai_classify(title):

    prompt = f"""
给这条新闻分类：

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

标题：
{title}

只输出分类名称
"""

    result = ask_ai(prompt)

    allowed = [
        "突发新闻","政策","AI","科技","金融",
        "经济","商业","国际","军事","能源","社会"
    ]

    if result in allowed:
        return result

    return "社会"

# ===============================
# AI摘要
# ===============================

def ai_summary(title):

    prompt = f"""
用中文总结这条新闻

标题：
{title}

要求20字以内
"""

    result = ask_ai(prompt)

    return result if result else "暂无摘要"

# ===============================
# AI评分
# ===============================

def ai_score(title):

    prompt = f"""
给这条新闻评分1-5

标题：
{title}

5 全球重大
4 行业重要
3 普通
2 一般
1 不重要

只输出数字
"""

    result = ask_ai(prompt)

    try:
        return int(result)
    except:
        return 3

# ===============================
# AI处理
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

    news_sorted = sorted(
        news,
        key=lambda x:(x["lang_priority"],x["score"]),
        reverse=True
    )

    return news_sorted[:3]

# ===============================
# 新闻处理
# ===============================

def process_news(news):

    news = exact_deduplicate(news)

    news = news[:MAX_NEWS]

    news = enrich_news(news)

    news.sort(
        key=lambda x:(x["lang_priority"],x["score"]),
        reverse=True
    )

    return news

# ===============================
# 格式化
# ===============================

def format_message(news):

    groups = defaultdict(list)

    for n in news:

        groups[n["category"]].append(n)

    ordered = [
        "突发新闻","政策","AI","科技","金融",
        "经济","商业","国际","军事","能源","社会"
    ]

    top3 = select_top3(news)

    message = "🌍 今日全球新闻雷达\n\n"

    message += "【今日三大新闻】\n"

    for i,n in enumerate(top3,1):

        message += f"{i}. {n['summary']}\n"

    message += "\n"

    for cat in ordered:

        items = groups.get(cat,[])

        if not items:
            continue

        message += f"【{cat}】\n"

        for i,n in enumerate(items,1):

            message += f"{i}. {n['title']}\n"
            message += f"摘要：{n['summary']}\n"
            message += f"链接：{n['link']}\n\n"

    return message

# ===============================
# WxPusher推送
# ===============================

def push_wechat(msg):

    url = "https://wxpusher.zjiecode.com/api/send/message"

    data = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": msg,
        "summary": "全球新闻雷达",
        "contentType": 1,
        "uids": [WXPUSHER_UID]
    }

    try:

        r = requests.post(url,json=data)

        print("WxPusher:",r.text)

    except Exception as e:

        print("推送失败:",e)

# ===============================
# 主程序
# ===============================

def main():

    print("抓取新闻...")

    news1 = fetch_newsdata()
    news2 = fetch_gnews()

    news = news1 + news2

    if not news:

        print("没有新闻")

        return

    news = process_news(news)

    message = format_message(news)

    print(message)

    push_wechat(message)

if __name__ == "__main__":

    main()
