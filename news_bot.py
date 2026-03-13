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
        print("NEWS_DATA_KEY 未配置，跳过 NewsData")
        return []

    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "en",
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
                    "source": "NewsData",
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
        print("GNEWS_KEY 未配置，跳过 GNews")
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
                    "source": "GNews",
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
        title = n["title"].strip().lower()
        if title not in seen:
            seen.add(title)
            unique.append(n)

    return unique

# ===============================
# 轻量预筛，减少 AI 去重调用
# ===============================

def normalize_title(title: str) -> str:
    t = title.lower()
    for ch in ["|", "-", "—", ":", "：", ",", ".", "(", ")", "[", "]", "'"]:
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
# AI 事件级去重
# ===============================

def ai_is_duplicate(title1: str, title2: str) -> bool:
    prompt = f"""
判断下面两条新闻标题是否指向同一事件。
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
# AI 分类
# ===============================

def ai_classify(title: str) -> str:
    prompt = f"""
给这条新闻分类，只输出一个分类名称。

新闻标题：
{title}

分类选项：
AI
科技
金融
国际
商业
其他
"""
    result = ask_ai(prompt)
    allowed = {"AI", "科技", "金融", "国际", "商业", "其他"}
    return result if result in allowed else "其他"

# ===============================
# AI 摘要
# ===============================

def ai_summary(title: str) -> str:
    prompt = f"""
请用简体中文一句话概括下面这条新闻标题。

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
# AI 重要度评分
# ===============================

def ai_score(title: str) -> int:
    prompt = f"""
请给下面新闻标题的重要度评分，只输出 1 到 5 的整数。

标题：
{title}

评分标准：
5 = 全球重大新闻
4 = 行业重要新闻
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
# 单条新闻 AI 分析
# ===============================

def enrich_news(news):
    for n in news:
        n["category"] = ai_classify(n["title"])
        n["summary"] = ai_summary(n["title"])
        n["score"] = ai_score(n["title"])
    return news

# ===============================
# AI 选今日三大新闻
# ===============================

def select_top3(news):
    if not news:
        return []

    if len(news) <= 3:
        return news[:]

    candidates_text = []
    for i, n in enumerate(news, 1):
        candidates_text.append(
            f"{i}. 标题：{n['title']}\n"
            f"分类：{n.get('category', '其他')}\n"
            f"摘要：{n.get('summary', '暂无摘要')}\n"
            f"评分：{n.get('score', 3)}"
        )

    prompt = f"""
下面是今日候选新闻，请选出最值得放在“今日三大新闻”的3条。

要求：
1. 综合考虑全球影响力、公共关注度、行业重要性
2. 优先选择影响面更广的事件
3. 只输出 3 个编号，用英文逗号分隔
4. 例如：1,4,7

候选新闻：
{chr(10).join(candidates_text)}
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
        news_sorted = sorted(news, key=lambda x: x.get("score", 3), reverse=True)
        return news_sorted[:3]

    return [news[i] for i in unique_indices[:3]]

# ===============================
# 处理新闻
# ===============================

def process_news(news):
    print("原始新闻数量:", len(news))

    news = exact_deduplicate(news)
    print("标题去重后:", len(news))

    news = news[:MAX_NEWS]
    print("进入 AI 处理数量:", len(news))

    news = ai_deduplicate(news)
    print("AI 去重后:", len(news))

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

    ordered_categories = ["AI", "科技", "金融", "国际", "商业", "其他"]
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
        message = message[:3500] + "\n\n（内容过长，已截断）"

    return message

# ===============================
# 微信推送
# ===============================

def push_wechat(msg: str):
    if not WECHAT_WEBHOOK:
        print("WECHAT_WEBHOOK 未配置，跳过推送")
        return

    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    try:
        r = requests.post(WECHAT_WEBHOOK, json=data, timeout=REQUEST_TIMEOUT)
        print("微信推送状态:", r.status_code, r.text)
    except Exception as e:
        print("微信推送失败:", e)

# ===============================
# 主程序
# ===============================

def main():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY 未配置")

    print("开始抓取新闻...")

    news1 = fetch_newsdata()
    news2 = fetch_gnews()
    news = news1 + news2

    print("抓取新闻总数:", len(news))

    if not news:
        print("没有抓到新闻，结束运行")
        return

    news = process_news(news)
    message = format_message(news)

    print(message)
    push_wechat(message)

if __name__ == "__main__":
    main()
