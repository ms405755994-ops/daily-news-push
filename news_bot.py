import os
import re
import json
import time
import requests
import feedparser
from difflib import SequenceMatcher
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# ===============================
# 配置
# ===============================

NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY", "")
GNEWS_KEY = os.getenv("GNEWS_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "")
AMAP_KEY = os.getenv("AMAP_KEY", "")

MAX_FETCH_PER_API = int(os.getenv("MAX_FETCH_PER_API", "40"))
MAX_FETCH_PER_RSS = int(os.getenv("MAX_FETCH_PER_RSS", "25"))
MAX_NEWS = int(os.getenv("MAX_NEWS", "12"))

REPORT_CITY = os.getenv("REPORT_CITY", "汕头")
REPORT_LUNAR_TEXT = os.getenv("REPORT_LUNAR_TEXT", "农历待设置")

# ===============================
# 期货配置
# ===============================

FUTURES = [
    ("WTI原油", "https://cn.investing.com/commodities/crude-oil-historical-data"),
    ("COMEX黄金", "https://quote.eastmoney.com/globalfuture/GC00Y.html"),
    ("大连棕榈油", "https://gu.sina.cn/ft/hq/nf.php?symbol=P0"),
    ("聚丙烯(PP)", "https://cn.investing.com/commodities/pp-futures-historical-data"),
    ("聚乙烯(PE)", "https://cn.investing.com/commodities/lldpe-futures-historical-data"),
]

# ===============================
# 天气
# ===============================

def fetch_weather():
    if not AMAP_KEY:
        return f"{REPORT_CITY}：天气待更新"

    try:
        r = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={
                "key": AMAP_KEY,
                "city": "440500",
            },
            timeout=10
        )
        data = r.json()

        if data.get("status") != "1":
            return f"{REPORT_CITY}：天气待更新"

        live = data["lives"][0]
        return f"{REPORT_CITY}：{live['weather']} {live['temperature']}°C"

    except:
        return f"{REPORT_CITY}：天气待更新"

# ===============================
# 时间
# ===============================

def get_title():
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    week = ["一","二","三","四","五","六","日"][now.weekday()]
    return f"# MSAI今日新闻｜{now.year}年{now.month}月{now.day}日 星期{week}（{REPORT_LUNAR_TEXT}）｜{fetch_weather()}"

# ===============================
# 抓新闻
# ===============================

def fetch_news():
    news = []

    try:
        r = requests.get(
            "https://newsdata.io/api/1/news",
            params={"apikey": NEWS_DATA_KEY, "language": "zh"},
            timeout=10
        )
        for n in r.json().get("results", [])[:MAX_FETCH_PER_API]:
            news.append((n["title"], n["link"]))
    except:
        pass

    try:
        r = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={"apikey": GNEWS_KEY, "lang": "zh"},
            timeout=10
        )
        for n in r.json().get("articles", []):
            news.append((n["title"], n["url"]))
    except:
        pass

    return news

# ===============================
# 去重
# ===============================

def dedup(news):
    seen = set()
    result = []
    for t, l in news:
        if t not in seen:
            seen.add(t)
            result.append((t, l))
    return result

# ===============================
# AI整理
# ===============================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

def ask_ai(prompt):
    try:
        r = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        return r.choices[0].message.content
    except:
        return ""

# ===============================
# 统计条数
# ===============================

def count_items(text):
    return len(re.findall(r"\d+\.\s\*\*", text))

# ===============================
# 期货模块
# ===============================

def futures_block():
    lines = ["", "## 期货观察"]
    for i,(name,url) in enumerate(FUTURES,1):
        lines.append(f"{i}. {name}：- - [📈]({url})")
    return "\n".join(lines)

# ===============================
# 主流程
# ===============================

def main():
    news = fetch_news()
    news = dedup(news)[:MAX_NEWS]

    payload = [{"title":t,"link":l} for t,l in news]

    prompt = f"""
整理新闻：
要求：
1. 分栏目
2. 每条格式：
序号. **标题** [🔗](link)
摘要：一句话
3. 不要输出总标题
4. 总数≤12

数据：
{json.dumps(payload,ensure_ascii=False)}
"""

    body = ask_ai(prompt)

    count = count_items(body)

    result = f"{get_title()}\n\n今日共{count}条\n\n{body}{futures_block()}"

    print(result)

    requests.post(
        WECHAT_WEBHOOK,
        json={"msgtype":"markdown","markdown":{"content":result}}
    )

if __name__ == "__main__":
    main()
