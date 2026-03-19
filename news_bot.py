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

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")

MAX_FETCH_PER_API = int(os.getenv("MAX_FETCH_PER_API", "40"))
MAX_FETCH_PER_RSS = int(os.getenv("MAX_FETCH_PER_RSS", "25"))
MAX_NEWS = int(os.getenv("MAX_NEWS", "12"))
REQUEST_TIMEOUT = 30

# 标题配置
REPORT_CITY = os.getenv("REPORT_CITY", "汕头")
REPORT_LUNAR_TEXT = os.getenv("REPORT_LUNAR_TEXT", "农历待设置")
REPORT_WEATHER_TEXT = os.getenv("REPORT_WEATHER_TEXT", "").strip()

# RSS 源（可继续加）
RSS_FEEDS = [
    {"url": "https://www.chinanews.com.cn/rss/scroll-news.xml", "source": "中新网-即时"},
    {"url": "https://www.chinanews.com.cn/rss/world.xml", "source": "中新网-国际"},
    {"url": "https://www.chinanews.com.cn/rss/finance.xml", "source": "中新网-财经"},
    {"url": "https://www.chinanews.com.cn/rss/it.xml", "source": "中新网-IT"},
    {"url": "https://www.ithome.com/rss/", "source": "IT之家"},
]

ALLOWED_DOMAINS = {
    # 央媒/权威
    "people.com.cn",
    "xinhuanet.com",
    "news.cn",
    "cctv.com",
    "chinanews.com.cn",
    "china.com.cn",
    "cnr.cn",
    "gmw.cn",
    "china.org.cn",

    # 综合门户
    "163.com",
    "qq.com",
    "news.qq.com",
    "ifeng.com",
    "sina.com.cn",
    "news.sina.com.cn",
    "finance.sina.com.cn",
    "sohu.com",

    # 财经/证券
    "yicai.com",
    "cls.cn",
    "stcn.com",
    "eastmoney.com",
    "caixin.com",
    "21jingji.com",
    "nbd.com.cn",
    "wallstreetcn.com",
    "jrj.com.cn",
    "cs.com.cn",
    "cnstock.com",
    "stockstar.com",
    "hexun.com",
    "eeo.com.cn",

    # 科技/AI
    "36kr.com",
    "huxiu.com",
    "jiemian.com",
    "ithome.com",
    "leiphone.com",
    "qbitai.com",
    "jiqizhixin.com",
    "geekpark.net",
    "pingwest.com",
    "donews.com",
    "cyzone.cn",

    # 时政/社会/地方媒体
    "thepaper.cn",
    "guancha.cn",
    "bjnews.com.cn",
    "infzm.com",
    "nfnews.com",
    "ycwb.com",
    "sznews.com",
    "southcn.com",
    "dayoo.com",
    "jfdaily.com",
    "whb.cn",
    "shobserver.com",

    # 国际中文
    "zaobao.com",
    "rfi.fr",
    "dw.com",
    "bbc.com",
    "ftchinese.com",
    "voachinese.com",
}

SOURCE_WEIGHT = {
    "news.cn": 12,
    "xinhuanet.com": 12,
    "people.com.cn": 12,
    "cctv.com": 12,
    "chinanews.com.cn": 11,
    "cnr.cn": 11,
    "gmw.cn": 10,
    "china.com.cn": 10,

    "caixin.com": 10,
    "yicai.com": 10,
    "cls.cn": 10,
    "stcn.com": 10,
    "eastmoney.com": 9,
    "wallstreetcn.com": 9,
    "21jingji.com": 9,
    "nbd.com.cn": 9,
    "eeo.com.cn": 8,
    "cnstock.com": 8,
    "cs.com.cn": 8,
    "hexun.com": 7,
    "jrj.com.cn": 7,

    "ithome.com": 9,
    "36kr.com": 8,
    "huxiu.com": 8,
    "jiemian.com": 8,
    "leiphone.com": 8,
    "qbitai.com": 8,
    "jiqizhixin.com": 8,
    "pingwest.com": 7,
    "geekpark.net": 7,
    "cyzone.cn": 7,

    "finance.sina.com.cn": 8,
    "news.sina.com.cn": 7,
    "sina.com.cn": 7,
    "news.qq.com": 7,
    "qq.com": 6,
    "163.com": 6,
    "ifeng.com": 7,
    "sohu.com": 5,

    "thepaper.cn": 8,
    "guancha.cn": 7,
    "bjnews.com.cn": 7,
    "infzm.com": 7,
    "jfdaily.com": 7,
    "shobserver.com": 7,
    "whb.cn": 7,
    "ycwb.com": 6,
    "sznews.com": 6,
    "southcn.com": 6,
    "dayoo.com": 5,

    "zaobao.com": 7,
    "ftchinese.com": 7,
    "rfi.fr": 6,
    "dw.com": 6,
    "bbc.com": 5,
    "voachinese.com": 5,
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
# AI 调用（全流程只最后 1 次）
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
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日",
    }
    return mapping[dt.weekday()]

def fetch_weather_text():
    if REPORT_WEATHER_TEXT:
        return REPORT_WEATHER_TEXT

    # 可选自动天气；失败则用兜底文案
    try:
        url = f"https://wttr.in/{REPORT_CITY}?format=j1"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        current = (data.get("current_condition") or [{}])[0]
        temp_c = (current.get("temp_C") or "").strip()
        desc_list = current.get("lang_zh") or current.get("weatherDesc") or []
        desc = ""

        if desc_list and isinstance(desc_list, list):
            first = desc_list[0]
            if isinstance(first, dict):
                desc = first.get("value", "").strip()

        if desc and temp_c:
            return f"{REPORT_CITY}：{desc} {temp_c}°C"
        if temp_c:
            return f"{REPORT_CITY}：{temp_c}°C"
    except Exception as e:
        print("Weather fetch error:", e)

    return f"{REPORT_CITY}：天气待更新"

def get_today_header():
    now_cn = china_now()
    return f"{now_cn.year}年{now_cn.month}月{now_cn.day}日 {get_cn_weekday(now_cn)}（{REPORT_LUNAR_TEXT}）"

def get_report_title():
    return f"# MSAI今日新闻｜{get_today_header()}｜{fetch_weather_text()}"

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
# 抓取 API
# ===============================

def fetch_newsdata():
    if not NEWS_DATA_KEY:
        print("NEWS_DATA_KEY 未配置")
        return []

    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": NEWS_DATA_KEY,
        "language": "zh",
    }

    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        news = []
        for n in data.get("results", [])[:MAX_FETCH_PER_API]:
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

def fetch_gnews():
    if not GNEWS_KEY:
        print("GNEWS_KEY 未配置")
        return []

    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "apikey": GNEWS_KEY,
        "lang": "zh",
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
# 抓取 RSS
# ===============================

def fetch_rss():
    all_items = []

    for feed in RSS_FEEDS:
        feed_url = feed["url"]
        source_name = feed["source"]

        try:
            parsed = feedparser.parse(feed_url)
            entries = parsed.entries[:MAX_FETCH_PER_RSS]

            for entry in entries:
                title = (getattr(entry, "title", "") or "").strip()
                link = (getattr(entry, "link", "") or "").strip()

                if not title or not link:
                    continue

                all_items.append({
                    "title": title,
                    "link": link,
                    "source": source_name,
                })

            time.sleep(0.2)

        except Exception as e:
            print(f"RSS error [{source_name}]:", e)

    return all_items

# ===============================
# 去重与过滤
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

# ===============================
# 规则聚类与压重
# ===============================

def pick_best_link(items):
    def score_item(item):
        base = get_source_weight(item.get("link", ""))
        title_len_bonus = min(len(item.get("title", "")) // 12, 3)
        topic_bonus = get_topic_bonus(item.get("title", ""))
        return base + title_len_bonus + topic_bonus

    return sorted(items, key=score_item, reverse=True)[0]

def score_cluster(cluster):
    items = cluster["items"]
    best = pick_best_link(items)
    title = best["title"].lower()

    score = 0
    score += len(items) * 3
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

# ===============================
# 主处理
# ===============================

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
# 最后一次 AI 整理
# ===============================

def ai_render_digest(news):
    if not news:
        return f"{get_report_title()}\n\n今日共0条\n\n暂无可推送的中文新闻"

    payload = []
    for idx, n in enumerate(news, 1):
        payload.append({
            "index": idx,
            "title": safe_text(n["title"], 80),
            "source_count": n.get("source_count", 1),
            "candidate_titles": [safe_text(x, 80) for x in n.get("all_titles", [])[:6]],
            "main_link": safe_link(n["link"]),
            "score": n.get("score", 0),
            "is_breaking": n.get("is_breaking", False),
            "event_key": n.get("event_key", ""),
        })

    prompt = f"""
你是中文新闻编辑，请基于下面的候选事件，整理成一份企业微信日报。

要求：
1. 只输出简体中文
2. 按重要性排序
3. 自动归入以下板块：
   - 今日三大新闻
   - AI重点
   - 国际/宏观重点
   - 金融重点
   - 突发新闻
4. 同一事件不要重复写
5. 如果多个候选事件明显属于同一主题，只保留其中信息量最大的一条
6. 顶部标题固定为：{get_report_title()}
7. 标题下方单独输出一行：今日共12条
8. 今日三大新闻只保留3条
9. 其他每个板块最多2条
10. 总新闻条数控制为12条以内，优先输出最重要的12条
11. 每条内容格式固定为：
   序号. **标题** [🔗](main_link)
   摘要：一句话，不超过26字
12. 标题必须重写成简洁新闻标题，不超过18字，不能直接照抄原始长标题
13. 链接不要单独另起一行，必须放在标题尾部，格式固定为 [🔗](main_link)
14. 每条新闻都必须带序号
15. 只使用我提供的数据，不要编造事实
16. 链接必须直接使用我给出的 main_link，不要改写，不要缩短，不要替换
17. 输出为企业微信 markdown 可直接发送的纯文本，不要代码块
18. 如果某个板块没有内容，可以省略该板块
19. 全文总长度控制在3000字以内
20. 优先选择突发、金融、国际局势、AI、宏观影响大的新闻
21. 一般展览、开幕、纪念活动除非影响特别大，否则不要放进今日三大新闻
22. 不要输出任何说明、注释、免责声明

候选事件：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""

    result = ask_ai(prompt, temperature=0.2)
    if result:
        result = result.replace("```markdown", "").replace("```", "").strip()
        if len(result) > 3800:
            result = result[:3800] + "\n\n（内容过长已截断）"
        return result

    lines = [get_report_title(), "", "今日共12条", "", "## 今日三大新闻"]
    for i, n in enumerate(news[:3], 1):
        link = safe_link(n["link"])
        if link:
            lines.append(f"{i}. **{safe_text(n['title'], 18)}** [🔗]({link})")
        else:
            lines.append(f"{i}. **{safe_text(n['title'], 18)}**")
        lines.append("摘要：")
        lines.append("")
    return "\n".join(lines)

# ===============================
# 企业微信推送
# ===============================

def push_wechat(msg: str):
    if not WECHAT_WEBHOOK:
        print("WECHAT_WEBHOOK 未配置")
        return

    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n（内容过长已截断）"

    data = {
        "msgtype": "markdown",
        "markdown": {
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
    news3 = fetch_rss()

    news = news1 + news2 + news3

    print("新闻总数:", len(news))

    if not news:
        print("没有新闻")
        return

    news = process_news(news)

    if not news:
        print("没有符合条件的中文新闻")
        return

    message = ai_render_digest(news)

    print(message)
    push_wechat(message)

if __name__ == "__main__":
    main()
