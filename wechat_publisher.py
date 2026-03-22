import os
import requests
import json
from datetime import datetime

APPID = os.getenv("WECHAT_APPID")
SECRET = os.getenv("WECHAT_SECRET")
OPENID = os.getenv("WECHAT_OPENID")
TEMPLATE_ID = os.getenv("WECHAT_TEMPLATE_ID")

NEWS_PAGE_URL = "https://ms405755994-ops.github.io/daily-news-push/"

# =========================
# 获取 token
# =========================
def get_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": SECRET
    }

    res = requests.get(url, params=params).json()
    print("token:", res)

    return res.get("access_token")


# =========================
# 读取新闻数据
# =========================
def get_news_summary():
    data = json.loads(open("docs/news-data.json", encoding="utf-8").read())

    title = data["title"]

    summary = ""
    for n in data["news_items"][:3]:
        summary += f"{n['short_title']}；"

    return title, summary[:40]


# =========================
# 发送模板消息
# =========================
def send_template(token):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"

    title, summary = get_news_summary()

    data = {
        "touser": OPENID,
        "template_id": TEMPLATE_ID,
        "url": NEWS_PAGE_URL,  # 👈 点击跳转页面
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

    res = requests.post(url, json=data).json()
    print("发送结果:", res)


# =========================
# 主函数
# =========================
def main():
    token = get_token()
    send_template(token)


if __name__ == "__main__":
    main()
