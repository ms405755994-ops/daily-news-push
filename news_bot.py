import requests
from openai import OpenAI
from datetime import datetime

# ========= 配置 =========

NEWS_DATA_KEY = "YOUR_NEWSDATA_KEY"
GNEWS_KEY = "YOUR_GNEWS_KEY"

OPENAI_API_KEY = "YOUR_OPENAI_KEY"

WECHAT_WEBHOOK = "YOUR_WECHAT_WEBHOOK"

MAX_NEWS = 20

# ========================

client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------
# AI调用
# ------------------------

def ask_ai(prompt):

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print("AI error:", e)

        return ""

# ------------------------
# 新闻 API 1
# ------------------------

def fetch_newsdata():

    url = "https://newsdata.io/api/1/news"

    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en",
        "size": 20
    }

    try:

        r = requests.get(url, params=params)

        data = r.json()

        results = []

        for n in data.get("results", []):

            results.append({
                "title": n.get("title"),
                "link": n.get("link")
            })

        return results

    except:

        return []

# ------------------------
# 新闻 API 2
# ------------------------

def fetch_gnews():

    url = "https://gnews.io/api/v4/top-headlines"

    params = {
        "apikey": GNEWS_KEY,
        "lang": "en",
        "max": 20
    }

    try:

        r = requests.get(url, params=params)

        data = r.json()

        results = []

        for n in data.get("articles", []):

            results.append({
                "title": n.get("title"),
                "link": n.get("url")
            })

        return results

    except:

        return []

# ------------------------
# AI去重
# ------------------------

def ai_deduplicate(news):

    unique = []

    for n in news:

        duplicate = False

        for u in unique:

            prompt = f"""
判断下面两条新闻是否是同一事件

新闻1:
{n['title']}

新闻2:
{u['title']}

只回答 YES 或 NO
"""

            result = ask_ai(prompt)

            if "YES" in result.upper():

                duplicate = True
                break

        if not duplicate:

            unique.append(n)

    return unique

# ------------------------
# AI分类
# ------------------------

def ai_classify(title):

    prompt = f"""
给这条新闻分类：

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

# ------------------------
# AI摘要
# ------------------------

def ai_summary(title):

    prompt = f"""
请用一句话总结这条新闻：

{title}

要求：
30字以内
"""

    result = ask_ai(prompt)

    return result if result else ""

# ------------------------
# 处理新闻
# ------------------------

def process_news(news):

    print("原始新闻数量:", len(news))

    news = ai_deduplicate(news)

    print("去重后:", len(news))

    news = news[:MAX_NEWS]

    for n in news:

        n["category"] = ai_classify(n["title"])

        n["summary"] = ai_summary(n["title"])

    return news

# ------------------------
# 格式化消息
# ------------------------

def format_message(news):

    groups = {}

    for n in news:

        cat = n["category"]

        if cat not in groups:

            groups[cat] = []

        groups[cat].append(n)

    message = "🌍 今日全球新闻\n\n"

    for cat, items in groups.items():

        message += f"【{cat}】\n"

        for i, n in enumerate(items, 1):

            message += f"{i}. {n['title']}\n"
            message += f"摘要：{n['summary']}\n"
            message += f"{n['link']}\n\n"

    return message

# ------------------------
# 微信推送
# ------------------------

def push_wechat(msg):

    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    try:

        requests.post(WECHAT_WEBHOOK, json=data)

        print("推送成功")

    except Exception as e:

        print("推送失败", e)

# ------------------------
# 主程序
# ------------------------

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
