import requests
import json
import os
from datetime import datetime

APPID = os.getenv("WECHAT_APPID", "").strip()
SECRET = os.getenv("WECHAT_SECRET", "").strip()

# 固定作者（避免长度问题）
AUTHOR = "MSAI"

THUMB_URL = os.getenv("WECHAT_THUMB_URL", "").strip()

REQUEST_TIMEOUT = 30


# ========================
# 获取 access_token
# ========================
def get_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": SECRET,
    }
    res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
    print("token response:", res)

    token = res.get("access_token")
    if not token:
        raise RuntimeError(f"获取 access_token 失败: {res}")
    return token


# ========================
# 上传缩略图（必须用 media/upload）
# ========================
def upload_thumb(access_token):
    img = requests.get(THUMB_URL, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()

    files = {
        "media": ("thumb.jpg", img.content),
    }

    url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=thumb"
    res = requests.post(url, files=files, timeout=REQUEST_TIMEOUT).json()
    print("thumb response:", res)

    media_id = res.get("media_id")
    if not media_id:
        raise RuntimeError(f"上传缩略图失败: {res}")

    return media_id


# ========================
# 构建 HTML 内容
# ========================
def build_html():
    with open("docs/news-data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    html = f"<h2>{data.get('title','')}</h2>"
    html += f"<p>{data.get('date_text','')} | {data.get('weather_text','')}</p><hr>"

    # 热点
    html += "<h3>关键热点</h3>"
    for item in data.get("hotspots", []):
        html += f"<p><b>{item.get('title','')}</b><br>{item.get('reason','')}</p>"

    # 新闻正文
    html += "<h3>新闻正文</h3>"
    for i, item in enumerate(data.get("news_items", []), 1):
        html += f"<h4>{i}. {item.get('short_title','')}</h4>"
        html += f"<p>{item.get('summary','')}</p>"
        html += f'<p><a href="{item.get("link","")}">查看原文</a></p>'

    return html


# ========================
# 创建图文（uploadnews）
# ========================
def upload_mpnews(access_token, thumb_media_id, html_content, title):
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadnews?access_token={access_token}"

    payload = {
        "articles": [
            {
                "thumb_media_id": thumb_media_id,
                "author": "MSAI",
                "title": title[:64],
                "content": html_content,
                "digest": "每日全球新闻速览",
                "show_cover_pic": 1,
            }
        ]
    }

    print("AUTHOR used:", "MSAI")

    res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT).json()
    print("uploadnews response:", res)

    media_id = res.get("media_id")
    if not media_id:
        raise RuntimeError(f"创建图文失败: {res}")

    return media_id


# ========================
# 群发
# ========================
def send_all(access_token, media_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={access_token}"

    payload = {
        "filter": {"is_to_all": True},
        "mpnews": {"media_id": media_id},
        "msgtype": "mpnews",
    }

    res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT).json()
    print("群发结果:", res)

    if res.get("errcode") != 0:
        raise RuntimeError(res)


# ========================
# 主程序
# ========================
def main():
    token = get_access_token()
    print("token:", token)

    thumb_id = upload_thumb(token)
    print("thumb:", thumb_id)

    html = build_html()

    title = f"MSAI每日新闻 {datetime.now().strftime('%m-%d')}"
    media_id = upload_mpnews(token, thumb_id, html, title)
    print("media_id:", media_id)

    send_all(token, media_id)


if __name__ == "__main__":
    main()
