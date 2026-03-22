# ===============================
# 点阵卡片（核心）
# ===============================

def build_dot_card(page_data):
    items = page_data.get("news_items", [])[:3]
    titles = [x.get("short_title", "")[:12] for x in items if x.get("short_title")]

    lines = []
    lines.append("━━━━━━━━━━━━━━")
    lines.append("📰 MSAI今日新闻")
    lines.append("━━━━━━━━━━━━━━")
    lines.append("")

    for t in titles:
        lines.append(f"🔥 {t}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━")
    lines.append("👉 点击查看完整新闻")

    return "\n".join(lines)


# ===============================
# 微信测试号推送（最终版）
# ===============================

def push_wechat_test_from_page_data(page_data: dict):
    if not WECHAT_APPID or not WECHAT_SECRET or not WECHAT_OPENID or not WECHAT_TEMPLATE_ID:
        print("微信测试号参数未配置，跳过")
        return

    try:
        # 获取 token
        token_url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": WECHAT_APPID,
            "secret": WECHAT_SECRET
        }

        res = requests.get(token_url, params=params, timeout=10).json()
        token = res.get("access_token")

        if not token:
            print("获取token失败:", res)
            return

        print("token OK")

        # 构建卡片
        summary = build_dot_card(page_data)

        send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"

        data = {
            "touser": WECHAT_OPENID,
            "template_id": WECHAT_TEMPLATE_ID,
            "data": {
                "first": {
                    "value": "MSAI今日新闻",
                    "color": "#173177"
                },
                "keyword1": {
                    "value": summary,
                    "color": "#000000"
                },
                "keyword2": {
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "color": "#173177"
                },
                "remark": {
                    "value": "👉 点击查看完整新闻",
                    "color": "#888888"
                }
            }
        }

        # 点击跳转
        if NEWS_PAGE_URL and NEWS_PAGE_URL.startswith("http"):
            data["url"] = NEWS_PAGE_URL

        r = requests.post(send_url, json=data, timeout=10).json()
        print("推送结果:", r)

    except Exception as e:
        print("测试号推送失败:", e)


# ===============================
# 主程序（最终）
# ===============================

def main():
    print("开始抓新闻...")

    news = fetch_newsdata() + fetch_gnews() + fetch_rss()
    print("新闻总数:", len(news))

    if not news:
        print("没有新闻")
        return

    news = process_news(news)

    if not news:
        print("没有有效新闻")
        return

    # AI处理
    hotspots = ai_pick_hotspots(news)
    structured = ai_select_structured_items(news)
    futures = get_futures_data()

    # 页面数据
    page_data = {
        "title": get_report_title(),
        "date_text": get_today_header(),
        "weather_text": fetch_weather_text(),
        "total_count": len(structured),
        "hotspots": hotspots,
        "news_items": structured,
        "futures": futures,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 保存 JSON
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    with open("docs/news-data.json", "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)

    print("✅ 页面数据生成完成")

    # 企业微信（原有）
    message = build_final_message(news)
    push_wechat(message)

    # ✅ 测试号推送（新）
    push_wechat_test_from_page_data(page_data)


if __name__ == "__main__":
    main()
