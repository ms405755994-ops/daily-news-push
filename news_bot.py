import os
import re
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse

import requests
import feedparser
from openai import OpenAI

# ===============================
# 配置
# ===============================

NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY", "")
GNEWS_KEY = os.getenv("GNEWS_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "")
AMAP_KEY = os.getenv("AMAP_KEY", "")

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")
WECHAT_OPENID = os.getenv("WECHAT_OPENID", "")
WECHAT_TEMPLATE_ID = os.getenv("WECHAT_TEMPLATE_ID", "")

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")

MAX_FETCH_PER_API = int(os.getenv("MAX_FETCH_PER_API", "40"))
MAX_FETCH_PER_RSS = int(os.getenv("MAX_FETCH_PER_RSS", "25"))
MAX_NEWS = int(os.getenv("MAX_NEWS", "12"))
REQUEST_TIMEOUT = 20

REPORT_CITY = os.getenv("REPORT_CITY", "汕头")
REPORT_LUNAR_TEXT = os.getenv("REPORT_LUNAR_TEXT", "农历待设置")
REPORT_WEATHER_TEXT = os.getenv("REPORT_WEATHER_TEXT", "").strip()

NEWS_PAGE_URL = os.getenv("NEWS_PAGE_URL", "").strip()

RSS_FEEDS = [
    {"url": "https://www.chinanews.com.cn/rss/scroll-news.xml", "source": "中新网-即时"},
    {"url": "https://www.chinanews.com.cn/rss/world.xml", "source": "中新网-国际"},
    {"url": "https://www.chinanews.com.cn/rss/finance.xml", "source": "中新网-财经"},
    {"url": "https://www.chinanews.com.cn/rss/it.xml", "source": "中新网-IT"},
    {"url": "https://www.ithome.com/rss/", "source": "IT之家"},
]

ALLOWED_DOMAINS = {
    "people.com.cn", "xinhuanet.com", "news.cn", "cctv.com", "chinanews.com.cn",
    "china.com.cn", "cnr.cn", "gmw.cn", "china.org.cn",
    "163.com", "qq.com", "news.qq.com", "ifeng.com", "sina.com.cn",
    "news.sina.com.cn", "finance.sina.com.cn", "sohu.com",
    "yicai.com", "cls.cn", "stcn.com", "eastmoney.com", "caixin.com",
    "21jingji.com", "nbd.com.cn", "wallstreetcn.com", "jrj.com.cn",
    "cs.com.cn", "cnstock.com", "stockstar.com", "hexun.com", "eeo.com.cn",
    "36kr.com", "huxiu.com", "jiemian.com", "ithome.com", "leiphone.com",
    "qbitai.com", "jiqizhixin.com", "geekpark.net", "pingwest.com",
    "donews.com", "cyzone.cn",
    "thepaper.cn", "guancha.cn", "bjnews.com.cn", "infzm.com", "nfnews.com",
    "ycwb.com", "sznews.com", "southcn.com", "dayoo.com", "jfdaily.com",
    "whb.cn", "shobserver.com",
    "zaobao.com", "rfi.fr", "dw.com", "bbc.com", "ftchinese.com",
    "voachinese.com",
}

SOURCE_WEIGHT = {
    "news.cn": 12, "xinhuanet.com": 12, "people.com.cn": 12, "cctv.com": 12,
    "chinanews.com.cn": 11, "cnr.cn": 11, "gmw.cn": 10, "china.com.cn": 10,
    "caixin.com": 10, "yicai.com": 10, "cls.cn": 10, "stcn.com": 10,
    "eastmoney.com": 9, "wallstreetcn.com": 9, "21jingji.com": 9,
    "nbd.com.cn": 9, "eeo.com.cn": 8, "cnstock.com": 8, "cs.com.cn": 8,
    "hexun.com": 7, "jrj.com.cn": 7,
    "ithome.com": 9, "36kr.com": 8, "huxiu.com": 8, "jiemian.com": 8,
    "leiphone.com": 8, "qbitai.com": 8, "jiqizhixin.com": 8,
    "pingwest.com": 7, "geekpark.net": 7, "cyzone.cn": 7,
    "finance.sina.com.cn": 8, "news.sina.com.cn": 7, "sina.com.cn": 7,
    "news.qq.com": 7, "qq.com": 6, "163.com": 6, "ifeng.com": 7, "sohu.com": 5,
    "thepaper.cn": 8, "guancha.cn": 7, "bjnews.com.cn": 7, "infzm.com": 7,
    "jfdaily.com": 7, "shobserver.com": 7, "whb.cn": 7, "ycwb.com": 6,
    "sznews.com": 6, "southcn.com": 6, "dayoo.com": 5,
    "zaobao.com": 7, "ftchinese.com": 7, "rfi.fr": 6, "dw.com": 6,
    "bbc.com": 5, "voachinese.com": 5,
}

HOT_TOPICS = [
    "霍尔木兹海峡", "荷莫兹海峡", "伊朗", "以色列", "美国", "中国", "欧盟",
    "俄罗斯", "乌克兰", "中东", "关税", "制裁", "原油", "黄金", "白银",
    "港股", "恒指", "a股", "美联储", "降息", "加息", "通胀", "就业",
    "openai", "ai", "人工智能", "大模型", "芯片", "英伟达", "腾讯", "阿里", "字节"
]

LOW_PRIORITY_WORDS = [
    "展", "展览", "开幕", "启幕", "纪念", "论坛", "活动",
    "发布会", "启动仪式", "艺术展", "文化周", "巡展", "揭幕"
]

FUTURES_CONFIG = [
    {
        "name": "WTI原油",
        "quote_url": "https://www.investing.com/commodities/crude-oil",
        "history_url": "https://www.investing.com/commodities/crude-oil-historical-data",
        "type": "investing_generic",
        "label": "Crude Oil WTI",
    },
    {
        "name": "COMEX黄金",
        "quote_url": "https://www.investing.com/commodities/gold",
        "history_url": "https://www.investing.com/commodities/gold-historical-data",
        "type": "investing_generic",
        "label": "Gold",
    },
    {
        "name": "大连棕榈油",
        "quote_url": "https://gu.sina.cn/ft/hq/nf.php?symbol=P0",
        "history_url": "https://gu.sina.cn/ft/hq/nf.php?symbol=P0",
        "type": "sina_palm",
        "label": "棕榈油连续",
    },
    {
        "name": "聚丙烯(PP)",
        "quote_url": "https://www.investing.com/commodities/pp-futures",
        "history_url": "https://www.investing.com/commodities/pp-futures-historical-data",
        "type": "investing_short",
        "label": "PP",
    },
    {
        "name": "聚乙烯(PE)",
        "quote_url": "https://www.investing.com/commodities/lldpe-futures",
        "history_url": "https://www.investing.com/commodities/lldpe-futures-historical-data",
        "type": "investing_short",
        "label": "LLDPE",
    },
]

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

ORDERED_CATEGORIES = [
    "突发新闻",
    "今日三大新闻",
    "AI重点",
    "国际/宏观重点",
    "金融重点",
]

# ===============================
# OpenRouter
# ===============================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com/ms405755994-ops/daily-news-push",
        "X-Title": "daily-news-push",
    },
)


def ask_ai(prompt: str, temperature: float = 0.1) -> str:
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
# 基础工具
# ===============================

def safe_text(text: str, max_len: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= max_len else text[:max_len] + "..."


def is_valid_click_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def safe_link(url: str) -> str:
    return url if is_valid_click_url(url) else ""


def china_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


def get_cn_weekday(dt: datetime) -> str:
    mapping = {
        0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四",
        4: "星期五", 5: "星期六", 6: "星期日",
    }
    return mapping[dt.weekday()]


def fetch_weather_text():
    if REPORT_WEATHER_TEXT:
        return REPORT_WEATHER_TEXT

    if not AMAP_KEY:
        return f"{REPORT_CITY}：天气待更新"

    city_adcode_map = {
        "汕头": "440500",
        "汕头市": "440500",
    }
    adcode = city_adcode_map.get(REPORT_CITY, "440500")

    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={
                "key": AMAP_KEY,
                "city": adcode,
                "extensions": "base",
                "output": "JSON",
            },
            headers=UA,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if str(data.get("status")) != "1":
            print("AMap weather api error:", data)
            return f"{REPORT_CITY}：天气待更新"

        lives = data.get("lives") or []
        if not lives:
            return f"{REPORT_CITY}：天气待更新"

        live = lives[0]
        weather = (live.get("weather") or "").strip()
        temperature = (live.get("temperature") or "").strip()

        if weather and temperature:
            return f"{REPORT_CITY}：{weather} {temperature}°C"
        if temperature:
            return f"{REPORT_CITY}：{temperature}°C"
        if weather:
            return f"{REPORT_CITY}：{weather}"
        return f"{REPORT_CITY}：天气待更新"
    except Exception as e:
        print("AMap weather fetch error:", e)
        return f"{REPORT_CITY}：天气待更新"


def get_today_header():
    now_cn = china_now()
    return f"{now_cn.year}年{now_cn.month}月{now_cn.day}日 {get_cn_weekday(now_cn)}（{REPORT_LUNAR_TEXT}）"


def get_report_title():
    return f"MSAI今日新闻｜{get_today_header()}｜{fetch_weather_text()}"


def normalize_title(title: str) -> str:
    t = (title or "").lower()
    for ch in ["|", "-", "—", "_", ":", "：", ",", "，", ".", "。", "(", ")", "[", "]", "'", '"',
               "（", "）", "【", "】", "！", "?", "？", "/", "\\", "｜", "·"]:
        t = t.replace(ch, " ")
    return " ".join(t.split())


def split_words(title: str):
    text = normalize_title(title)
    parts = re.split(r"\s+", text)
    words = {p for p in parts if p and len(p) >= 2}

    for topic in HOT_TOPICS:
        if topic.lower() in text:
            words.add(topic.lower())
    return words


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def is_chinese_link(url: str) -> bool:
    if not url:
        return False

    p = urlparse(url)
    netloc = p.netloc.lower()
    path = p.path.lower()
    full = url.lower()

    if any(netloc.endswith(domain) for domain in ALLOWED_DOMAINS):
        return True

    chinese_markers = [
        "/cn/", "/zh/", "/zh-cn/", "/chinese/",
        "lang=zh", "lang=zh-cn", "locale=zh", "/gb/", "/simp/"
    ]
    if any(m in full for m in chinese_markers):
        return True

    if netloc.endswith(".cn"):
        return True

    if "rfi.fr" in netloc and "/cn/" in path:
        return True
    if "dw.com" in netloc and "/zh/" in path:
        return True
    if "bbc.com" in netloc and "/zhongwen/" in path:
        return True

    return False


def get_source_weight(link: str) -> int:
    url = (link or "").lower()
    score = 0
    for domain, weight in SOURCE_WEIGHT.items():
        if domain in url:
            score = max(score, weight)
    return score


def is_breaking_by_rules(title: str) -> bool:
    t = (title or "").lower()
    keywords = [
        "breaking", "urgent", "attack", "war", "missile", "strike", "explosion",
        "earthquake", "flood", "wildfire", "shooting", "hostage", "coup",
        "emergency", "sanction", "tariff", "ceasefire", "troops", "invasion",
        "dies", "killed", "crash", "outbreak",
        "突发", "袭击", "导弹", "爆炸", "地震", "洪水", "火灾", "战争",
        "停火", "制裁", "关税", "坠毁", "死亡", "冲突", "枪击", "爆发",
        "谈判破裂", "空袭", "局势升级", "撤离", "封锁"
    ]
    return any(k in t for k in keywords)


def get_topic_bonus(title: str) -> int:
    t = (title or "").lower()
    breaking_words = [
        "战争", "袭击", "导弹", "冲突", "空袭", "停火", "制裁", "关税",
        "突发", "爆炸", "地震", "局势升级", "霍尔木兹", "荷莫兹", "中东"
    ]
    finance_words = [
        "美联储", "利率", "降息", "加息", "股市", "港股", "a股", "恒指",
        "纳指", "标普", "原油", "黄金", "比特币", "汇率", "债券", "通胀"
    ]
    ai_words = [
        "ai", "人工智能", "大模型", "openai", "芯片", "算力", "机器人",
        "英伟达", "腾讯", "阿里", "字节", "模型", "agent"
    ]
    macro_words = [
        "中国", "美国", "欧盟", "俄罗斯", "伊朗", "以色列", "乌克兰",
        "出口", "政策", "央行", "就业", "经济", "贸易", "供应链"
    ]

    bonus = 0
    if any(w in t for w in breaking_words):
        bonus += 7
    if any(w in t for w in finance_words):
        bonus += 6
    if any(w in t for w in ai_words):
        bonus += 6
    if any(w in t for w in macro_words):
        bonus += 5
    return bonus


def event_key(title: str) -> str:
    t = normalize_title(title)
    matched = [k.lower() for k in HOT_TOPICS if k.lower() in t]
    if matched:
        return "|".join(sorted(matched[:3]))

    words = list(split_words(title))
    words = sorted(words, key=lambda x: (-len(x), x))
    return "|".join(words[:3]) if words else t[:30]


# ===============================
# 抓新闻
# ===============================

def fetch_newsdata():
    if not NEWS_DATA_KEY:
        print("NEWS_DATA_KEY 未配置")
        return []

    try:
        r = requests.get(
            "https://newsdata.io/api/1/news",
            params={"apikey": NEWS_DATA_KEY, "language": "zh"},
            headers=UA,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        news = []
        for n in data.get("results", [])[:MAX_FETCH_PER_API]:
            title = (n.get("title") or "").strip()
            link = (n.get("link") or "").strip()
            if title and link:
                news.append({"title": title, "link": link, "source": "NewsData"})
        return news
    except Exception as e:
        print("NewsData error:", e)
        return []


def fetch_gnews():
    if not GNEWS_KEY:
        print("GNEWS_KEY 未配置")
        return []

    try:
        r = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={"apikey": GNEWS_KEY, "lang": "zh", "max": MAX_FETCH_PER_API},
            headers=UA,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        news = []
        for n in data.get("articles", []):
            title = (n.get("title") or "").strip()
            link = (n.get("url") or "").strip()
            if title and link:
                news.append({"title": title, "link": link, "source": "GNews"})
        return news
    except Exception as e:
        print("GNews error:", e)
        return []


def fetch_rss():
    all_items = []
    for feed in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            entries = parsed.entries[:MAX_FETCH_PER_RSS]
            for entry in entries:
                title = (getattr(entry, "title", "") or "").strip()
                link = (getattr(entry, "link", "") or "").strip()
                if title and link:
                    all_items.append({
                        "title": title,
                        "link": link,
                        "source": feed["source"],
                    })
            time.sleep(0.2)
        except Exception as e:
            print(f"RSS error [{feed['source']}]:", e)
    return all_items


# ===============================
# 去重 + 聚类
# ===============================

def exact_deduplicate(news):
    seen_titles = set()
    seen_links = set()
    unique = []
    for n in news:
        title = n["title"].strip().lower()
        link = n["link"].strip().lower()
        if title in seen_titles or link in seen_links:
            continue
        seen_titles.add(title)
        seen_links.add(link)
        unique.append(n)
    return unique


def filter_chinese_news(news):
    chinese_news = [n for n in news if is_chinese_link(n.get("link", ""))]
    print("中文链接新闻数量:", len(chinese_news))
    return chinese_news


def pick_best_link(items):
    def score_item(item):
        return (
            get_source_weight(item.get("link", ""))
            + min(len(item.get("title", "")) // 12, 3)
            + get_topic_bonus(item.get("title", ""))
        )
    return sorted(items, key=score_item, reverse=True)[0]


def score_cluster(cluster):
    items = cluster["items"]
    best = pick_best_link(items)
    title = best["title"].lower()

    score = len(items) * 3
    score += get_source_weight(best.get("link", ""))
    score += get_topic_bonus(title)

    if any(w in title for w in LOW_PRIORITY_WORDS):
        score -= 6
    if is_breaking_by_rules(title):
        score += 4
    return score


def rule_cluster(news):
    clusters = []
    for item in news:
        words = split_words(item["title"])
        key = event_key(item["title"])
        matched = False

        for cluster in clusters:
            overlap = len(words & cluster["words"])
            sim = title_similarity(item["title"], cluster["representative"]["title"])
            same_event_key = key == cluster["event_key"]

            if same_event_key or overlap >= 3 or sim >= 0.78:
                cluster["items"].append(item)
                cluster["words"] |= words
                matched = True
                break

        if not matched:
            clusters.append({
                "event_key": key,
                "words": words,
                "items": [item],
                "representative": item,
            })

    result = []
    for cluster in clusters:
        best = pick_best_link(cluster["items"])
        result.append({
            "title": best["title"],
            "link": best["link"],
            "source": best.get("source", ""),
            "source_count": len(cluster["items"]),
            "all_titles": [x["title"] for x in cluster["items"]],
            "all_links": [x["link"] for x in cluster["items"]],
            "score": score_cluster(cluster),
            "is_breaking": is_breaking_by_rules(best["title"]),
            "event_key": cluster["event_key"],
        })
    return result


def process_news(news):
    print("原始新闻:", len(news))
    news = exact_deduplicate(news)
    print("标题/链接去重:", len(news))

    news = filter_chinese_news(news)
    print("过滤中文链接后:", len(news))

    news = rule_cluster(news)
    print("规则聚类后:", len(news))

    news.sort(key=lambda x: x.get("score", 0), reverse=True)
    news = news[:MAX_NEWS]
    print("进入最终整理数量:", len(news))
    return news


# ===============================
# AI：关键热点判断
# ===============================

def parse_json_array(text: str):
    if not text:
        return []
    text = text.strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        pass

    m = re.search(r"(\[.*\])", text, flags=re.DOTALL)
    if not m:
        return []

    try:
        data = json.loads(m.group(1))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def ai_pick_hotspots(news):
    payload = []
    for n in news[:12]:
        payload.append({
            "title": safe_text(n["title"], 80),
            "link": n.get("link", ""),
            "score": n.get("score", 0),
            "source_count": n.get("source_count", 1),
            "is_breaking": n.get("is_breaking", False),
            "event_key": n.get("event_key", ""),
        })

    prompt = f"""
你是中文新闻编辑。请从候选事件中挑选 3 条“关键热点”。

要求：
1. 必须只使用中国大陆简体中文。
2. 不允许使用繁体字。
3. 只输出 JSON 数组，不要输出任何其他文字。
4. 每项格式：
[
  {{
    "title": "不超过16字",
    "reason": "不超过22字",
    "link": "候选事件里的原始链接"
  }}
]
5. 优先选择突发、国际局势、金融波动、AI重大进展。
6. link 必须直接使用候选中的 link。
7. 如果热点不足，最多输出 2 条；不要编造。

候选事件：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    raw = ask_ai(prompt, temperature=0.1)
    items = parse_json_array(raw)

    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = safe_text(item.get("title") or "", 16)
        reason = safe_text(item.get("reason") or "", 22)
        link = safe_link(item.get("link") or "")
        if title and reason:
            cleaned.append({
                "title": title,
                "reason": reason,
                "link": link,
            })
    return cleaned[:3]


# ===============================
# AI：新闻结构化
# ===============================

def ai_select_structured_items(news):
    payload = []
    for n in news:
        payload.append({
            "title": safe_text(n["title"], 80),
            "main_link": n["link"],
            "source_count": n.get("source_count", 1),
            "candidate_titles": [safe_text(x, 80) for x in n.get("all_titles", [])[:6]],
            "score": n.get("score", 0),
            "is_breaking": n.get("is_breaking", False),
            "event_key": n.get("event_key", ""),
        })

    prompt = f"""
你是中国大陆财经与国际新闻编辑。请基于候选事件，输出一个 JSON 数组，不要输出任何其他文字。

硬性要求：
1. 必须只使用中国大陆简体中文。
2. 不允许使用任何繁体字。
3. 不允许使用台湾、香港、澳门常用书写风格。
4. 同一事件不要重复写。
5. 如果多个候选事件明显属于同一主题，只保留其中信息量最大的一条。
6. 总新闻条数尽量控制为 12 条；如果高质量新闻不足，可以少于 12 条。
7. 分类 category 只能是以下 5 个之一：
   - 突发新闻
   - 今日三大新闻
   - AI重点
   - 国际/宏观重点
   - 金融重点
8. 突发新闻最多 2 条；今日三大新闻最多 3 条；其他栏目最多 2 条。
9. 标题 short_title 不超过 18 个汉字，必须重写成简洁新闻标题。
10. 摘要 summary 不超过 26 个汉字。
11. link 必须直接使用候选中的 main_link。
12. 只输出 JSON 数组，数组每项格式如下：
[
  {{
    "category": "突发新闻",
    "short_title": "示例标题",
    "summary": "示例摘要",
    "link": "https://..."
  }}
]

候选事件：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    raw = ask_ai(prompt, temperature=0.1)
    items = parse_json_array(raw)

    allowed = {"突发新闻", "今日三大新闻", "AI重点", "国际/宏观重点", "金融重点"}
    cleaned = []

    for item in items:
        if not isinstance(item, dict):
            continue
        category = (item.get("category") or "").strip()
        short_title = safe_text(item.get("short_title") or "", 18)
        summary = safe_text(item.get("summary") or "", 26)
        link = item.get("link") or ""

        if category not in allowed or not short_title or not summary or not safe_link(link):
            continue

        cleaned.append({
            "category": category,
            "short_title": short_title,
            "summary": summary,
            "link": link,
        })

    return cleaned[:MAX_NEWS]


# ===============================
# 期货行情
# ===============================

def fetch_text(url: str) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("fetch text error:", url, e)
        return ""


def html_to_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def num_to_float(s: str):
    try:
        return float(s.replace(",", "").strip())
    except Exception:
        return None


def extract_first_number_after_keyword(text: str, keywords):
    for keyword in keywords:
        pattern = rf"{re.escape(keyword)}.*?(\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)"
        m = re.search(pattern, text, re.I)
        if m:
            value = num_to_float(m.group(1))
            if value is not None:
                return value
    return None


def parse_investing_generic(text: str, label: str):
    if not text:
        return None

    current = None
    prev = None

    current_patterns = [
        rf"The current price of {re.escape(label)}(?: futures)? is (\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
        rf"{re.escape(label)}(?: futures)? is (\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
        rf"{re.escape(label)}.*?(\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
    ]
    for p in current_patterns:
        m = re.search(p, text, re.I)
        if m:
            current = num_to_float(m.group(1))
            if current is not None:
                break

    prev_patterns = [
        r"previous close of (\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
        r"Previous Close[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
        r"Prev\.?\s*Close[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
    ]
    for p in prev_patterns:
        m = re.search(p, text, re.I)
        if m:
            prev = num_to_float(m.group(1))
            if prev is not None:
                break

    if current is None:
        current = extract_first_number_after_keyword(text, [label, label.lower()])

    if current is None:
        return None

    pct = None
    if prev not in (None, 0):
        pct = (current - prev) / prev * 100

    return {"price": f"{current:,.2f}", "pct": pct}


def parse_investing_short(text: str, label: str):
    if not text:
        return None

    current = None
    patterns = [
        rf"The {re.escape(label)} price today is (\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
        rf"{re.escape(label)} price today is (\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
        rf"{re.escape(label)}.*?(\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            current = num_to_float(m.group(1))
            if current is not None:
                break

    if current is None:
        current = extract_first_number_after_keyword(text, [label, label.lower()])

    if current is None:
        return None

    pct = None
    pct_patterns = [
        r"([+\-]\d+(?:\.\d+)?)\s*\(([-+]?\d+(?:\.\d+)?)%\)",
        r"([-+]?\d+(?:\.\d+)?)%",
    ]
    for p in pct_patterns:
        m = re.search(p, text)
        if m:
            try:
                pct = float(m.group(m.lastindex).replace("%", ""))
                break
            except Exception:
                pct = None

    return {"price": f"{current:,.2f}", "pct": pct}


def parse_sina_palm(text: str):
    if not text:
        return None

    text = text.replace("\\n", " ").replace("\\t", " ")

    patterns = [
        r"棕榈油连续\s*(\d{3,5}(?:\.\d+)?)\s*([+\-]?\d+(?:\.\d+)?)%?",
        r"P0\s*(\d{3,5}(?:\.\d+)?)\s*([+\-]?\d+(?:\.\d+)?)%?",
        r"最新价[:：]?\s*(\d{3,5}(?:\.\d+)?)",
        r"现价[:：]?\s*(\d{3,5}(?:\.\d+)?)",
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            current = num_to_float(m.group(1))
            if current is None:
                continue

            pct = None
            if m.lastindex and m.lastindex >= 2 and m.group(2):
                try:
                    pct = float(m.group(2))
                except Exception:
                    pct = None

            return {"price": f"{current:,.2f}", "pct": pct}

    nums = re.findall(r"\d{4,5}(?:\.\d+)?", text)
    nums = [num_to_float(x) for x in nums]
    nums = [x for x in nums if x is not None and 1000 <= x <= 20000]

    if nums:
        return {"price": f"{nums[0]:,.2f}", "pct": None}

    return None


def pct_to_trend(pct):
    if pct is None:
        return "flat"
    if pct > 0:
        return "up"
    if pct < 0:
        return "down"
    return "flat"


def fetch_single_future(item: dict):
    html = fetch_text(item["quote_url"])
    text = html_to_text(html)

    parsed = None
    if item["type"] == "investing_generic":
        parsed = parse_investing_generic(text, item["label"])
    elif item["type"] == "investing_short":
        parsed = parse_investing_short(text, item["label"])
    elif item["type"] == "sina_palm":
        parsed = parse_sina_palm(text)

    if not parsed:
        print(f"[期货解析失败] {item['name']} | {item['quote_url']}")
        print(text[:1000])

    return {
        "name": item["name"],
        "history_url": item["history_url"],
        "price": parsed["price"] if parsed else None,
        "pct": parsed["pct"] if parsed else None,
        "trend": pct_to_trend(parsed["pct"]) if parsed else "flat",
    }


def format_pct(pct):
    if pct is None:
        return ""
    arrow = "▲" if pct > 0 else "▼" if pct < 0 else "■"
    return f"{arrow}{abs(pct):.2f}%"


def get_futures_data():
    result = []
    for item in FUTURES_CONFIG:
        snap = fetch_single_future(item)
        result.append({
            "name": snap["name"],
            "history_url": snap["history_url"],
            "price": snap["price"] or "价格待更新",
            "pct": snap["pct"],
            "trend": snap["trend"],
        })
    return result


def render_futures_footer(futures):
    lines = ["", "## 期货观察"]
    for i, snap in enumerate(futures, 1):
        link = safe_link(snap["history_url"])
        price = snap["price"] or "价格待更新"
        pct_text = format_pct(snap["pct"])
        suffix = f" {pct_text}" if pct_text else ""
        lines.append(f"{i}. {snap['name']}：{price}{suffix} [📈]({link})")
    return "\n".join(lines)


# ===============================
# 页面数据输出
# ===============================

def export_news_page_json(hotspots, structured_items, futures):
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    page_data = {
        "title": get_report_title(),
        "date_text": get_today_header(),
        "weather_text": fetch_weather_text(),
        "total_count": len(structured_items),
        "hotspots": hotspots,
        "news_items": structured_items,
        "futures": futures,
        "updated_at": china_now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    output_path = docs_dir / "news-data.json"
    output_path.write_text(
        json.dumps(page_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"已生成页面数据: {output_path}")


# ===============================
# 代码控制排版
# ===============================

def render_hotspots(hotspots):
    if not hotspots:
        return ""
    lines = ["## 关键热点"]
    for i, item in enumerate(hotspots, 1):
        link = safe_link(item.get("link", ""))
        lines.append(f"{i}. **{item['title']}** [🔗]({link})" if link else f"{i}. **{item['title']}**")
        lines.append(f"判断：{item['reason']}")
        lines.append("")
    return "\n".join(lines).strip()


def render_body(items):
    groups = {k: [] for k in ORDERED_CATEGORIES}
    for item in items:
        if item["category"] in groups:
            groups[item["category"]].append(item)

    lines = []
    idx = 1

    for category in ORDERED_CATEGORIES:
        if not groups[category]:
            continue
        lines.append(f"## {category}")
        for item in groups[category]:
            link = safe_link(item["link"])
            lines.append(f"{idx}. **{item['short_title']}** [🔗]({link})")
            lines.append(f"摘要：{item['summary']}")
            lines.append("")
            idx += 1

    return "\n".join(lines).strip(), idx - 1


def render_fallback(news):
    lines = []
    idx = 1
    lines.append("## 今日三大新闻")
    for n in news[:3]:
        link = safe_link(n["link"])
        lines.append(f"{idx}. **{safe_text(n['title'], 18)}** [🔗]({link})")
        lines.append("摘要：")
        lines.append("")
        idx += 1
    body = "\n".join(lines).strip()
    return body, idx - 1


def build_final_message(news):
    hotspots = ai_pick_hotspots(news)
    structured = ai_select_structured_items(news)
    futures = get_futures_data()

    if structured:
        body, item_count = render_body(structured)
    else:
        body, item_count = render_fallback(news)
        structured = []

    export_news_page_json(hotspots, structured, futures)

    hotspot_block = render_hotspots(hotspots)
    parts = [
        f"# {get_report_title()}",
        "",
        f"今日共{item_count}条",
        "",
    ]

    if hotspot_block:
        parts.append(hotspot_block)
        parts.append("")

    parts.append(body)
    parts.append(render_futures_footer(futures))

    final_text = "\n".join(parts)
    if len(final_text) > 3900:
        final_text = final_text[:3900] + "\n\n（内容过长已截断）"
    return final_text


# ===============================
# 企业微信推送
# ===============================

def push_wechat(msg: str):
    if not WECHAT_WEBHOOK:
        print("WECHAT_WEBHOOK 未配置")
        return

    data = {
        "msgtype": "markdown",
        "markdown": {"content": msg}
    }

    try:
        r = requests.post(WECHAT_WEBHOOK, json=data, headers=UA, timeout=REQUEST_TIMEOUT)
        print("企业微信推送状态:", r.status_code, r.text)
    except Exception as e:
        print("企业微信推送失败:", e)


# ===============================
# 微信测试号推送
# ===============================

def push_wechat_test(content: str):
    if not WECHAT_APPID or not WECHAT_SECRET or not WECHAT_OPENID or not WECHAT_TEMPLATE_ID:
        print("微信测试号参数未配置，跳过测试号推送")
        return

    try:
        token_url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": WECHAT_APPID,
            "secret": WECHAT_SECRET
        }

        r = requests.get(token_url, params=params, timeout=REQUEST_TIMEOUT).json()
        access_token = r.get("access_token")

        if not access_token:
            print("测试号获取 token 失败:", r)
            return

        print("测试号 token 获取成功")

        send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

        data = {
            "touser": WECHAT_OPENID,
            "template_id": WECHAT_TEMPLATE_ID,
            "data": {
                "first": {
                    "value": "MSAI今日新闻",
                    "color": "#173177"
                },
                "keyword1": {
                    "value": content[:100],
                    "color": "#000000"
                },
                "keyword2": {
                    "value": china_now().strftime("%Y-%m-%d %H:%M"),
                    "color": "#173177"
                },
                "remark": {
                    "value": "点击查看完整内容",
                    "color": "#888888"
                }
            }
        }

        if NEWS_PAGE_URL and is_valid_click_url(NEWS_PAGE_URL):
            data["url"] = NEWS_PAGE_URL

        res = requests.post(send_url, json=data, timeout=REQUEST_TIMEOUT).json()
        print("测试号推送结果:", res)

    except Exception as e:
        print("测试号推送失败:", e)


# ===============================
# 主程序
# ===============================

def main():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY 未配置")

    print("开始抓新闻...")
    news = fetch_newsdata() + fetch_gnews() + fetch_rss()
    print("新闻总数:", len(news))

    if not news:
        print("没有新闻")
        return

    news = process_news(news)
    if not news:
        print("没有符合条件的中文新闻")
        return

    message = build_final_message(news)
    print(message)

    push_wechat(message)
    push_wechat_test("今日新闻已生成，点击查看")


if __name__ == "__main__":
    main()
