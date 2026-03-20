import requests
import json
import os
from datetime import datetime

APPID = os.getenv("WECHAT_APPID")
SECRET = os.getenv("WECHAT_SECRET")
AUTHOR = os.getenv("WECHAT_AUTHOR", "MSAI")
THUMB_URL = os.getenv("WECHAT_THUMB_URL")

# ========================
# 获取 access_token
# ========================
def get_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": SECRET
    }
    res = requests.get(url, params=params).json()
    return res.get("access_token")

# ========================
# 上传封面图片
# ========================
def upload_thumb(access_token):
    img = requests.get(THUMB_URL).content
    files = {
        "media": ("thumb.jpg", img)
    }
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
    res = requests.post(url, files=files).json()
    return res.get("media_id")

# ========================
# 创建图文消息
# ========================
def create_mpnews(access_token, thumb_media_id, html_content, title):
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_news?access_token={access_token}"

    data = {
        "articles": [
            {
                "title": title,
                "author": AUTHOR,
                "digest": "每日全球新闻速览",
                "content": html_content,
                "thumb_media_id": thumb_media_id,
                "show_cover_pic": 1
            }
        ]
    }

    res = requests.post(url, json=data).json()
    return res.get("media_id")

# ========================
# 群发
# ========================
def send_all(access_token, media_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={access_token}"

    data = {
        "filter": {"is_to_all": True},
        "mpnews": {"media_id": media_id},
        "msgtype": "mpnews"
    }

    res = requests.post(url, json=data).json()
    print("群发结果:", res)

# ========================
# HTML生成（用你的新闻数据）
# ========================
def build_html():
    with open("docs/news-data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    html = f"""
    <h2>{data['title']}</h2>
    <p>{data['date_text']} | {data['weather_text']}</p>
    <hr>
    """

    for item in data["news_items"]:
        html += f"""
        <h3>{item['short_title']}</h3>
        <p>{item['summary']}</p>
        <p><a href="{item['link']}">查看原文</a></p>
        <br>
        """

    return html

# ========================
# 主流程
# ========================
def main():
    token = get_access_token()
    print("token:", token)

    thumb_id = upload_thumb(token)
    print("thumb:", thumb_id)

    html = build_html()

    media_id = create_mpnews(
        token,
        thumb_id,
        html,
        f"MSAI每日新闻 {datetime.now().strftime('%m-%d')}"
    )

    print("media_id:", media_id)

    send_all(token, media_id)

if __name__ == "__main__":
    main()
