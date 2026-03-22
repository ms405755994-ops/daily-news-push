import requests
import json
import os
from datetime import datetime

APPID = os.getenv("WECHAT_APPID", "").strip()
SECRET = os.getenv("WECHAT_SECRET", "").strip()
AUTHOR = os.getenv("WECHAT_AUTHOR", "MSAI").strip()
THUMB_URL = os.getenv("WECHAT_THUMB_URL", "").strip()

REQUEST_TIMEOUT = 30


def raise_if_empty(name, value):
    if not value:
        raise ValueError(f"{name} 未配置")


def get_access_token():
    raise_if_empty("WECHAT_APPID", APPID)
    raise_if_empty("WECHAT_SECRET", SECRET)

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


def upload_thumb(access_token):
    raise_if_empty("WECHAT_THUMB_URL", THUMB_URL)

    img_resp = requests.get(THUMB_URL, timeout=REQUEST_TIMEOUT)
    img_resp.raise_for_status()

    files = {
        "media": ("thumb.jpg", img_resp.content),
    }
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
    res = requests.post(url, files=files, timeout=REQUEST_TIMEOUT).json()
    print("thumb response:", res)

    media_id = res.get("media_id")
    if not media_id:
        raise RuntimeError(f"上传封面失败: {res}")
    return media_id


def build_html():
    with open("docs/news-data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    parts = []
    parts.append(f"<h2>{data.get('title', '')}</h2>")
    parts.append(f"<p>{data.get('date_text', '')} | {data.get('weather_text', '')}</p>")
    parts.append("<hr>")

    # 关键热点
    hotspots = data.get("hotspots", [])
    if hotspots:
        parts.append("<h3>关键热点</h3>")
        for item in hotspots:
            title = item.get("title", "")
            reason = item.get("reason", "")
            link = item.get("link", "")
            parts.append(f"<p><strong>{title}</strong><br>{reason}</p>")
            if link:
                parts.append(f'<p><a href="{link}">查看原文</a></p>')

    # 新闻正文
    news_items = data.get("news_items", [])
    if news_items:
        parts.append("<h3>新闻正文</h3>")
        for idx, item in enumerate(news_items, 1):
            title = item.get("short_title", "")
            summary = item.get("summary", "")
            link = item.get("link", "")
            category = item.get("category", "")

            parts.append(f"<h4>{idx}. {title}</h4>")
            if category:
                parts.append(f"<p><strong>{category}</strong></p>")
            parts.append(f"<p>{summary}</p>")
            if link:
                parts.append(f'<p><a href="{link}">查看原文</a></p>')

    # 期货观察
    futures = data.get("futures", [])
    if futures:
        parts.append("<h3>期货观察</h3>")
        for item in futures:
            name = item.get("name", "")
            price = item.get("price", "")
            pct = item.get("pct")
            history_url = item.get("history_url", "")

            line = f"{name}：{price}"
            if isinstance(pct, (int, float)):
                sign = "+" if pct > 0 else ""
                line += f" ({sign}{pct:.2f}%)"

            parts.append(f"<p>{line}</p>")
            if history_url:
                parts.append(f'<p><a href="{history_url}">查看历史数据</a></p>')

    html = "\n".join(parts)
    return html


def upload_mpnews(access_token, thumb_media_id, html_content, title):
    # 群发图文，优先走 uploadnews
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadnews?access_token={access_token}"

    payload = {
        "articles": [
            {
                "thumb_media_id": thumb_media_id,
                "author": AUTHOR,
                "title": title,
                "content_source_url": "",
                "content": html_content,
                "digest": "每日全球新闻速览",
                "show_cover_pic": 1,
            }
        ]
    }

    res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT).json()
    print("uploadnews response:", res)

    media_id = res.get("media_id")
    if not media_id:
        raise RuntimeError(f"创建图文消息失败: {res}")
    return media_id


def send_all(access_token, media_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={access_token}"

    payload = {
        "filter": {"is_to_all": True},
        "mpnews": {"media_id": media_id},
        "msgtype": "mpnews",
        "send_ignore_reprint": 1,
    }

    res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT).json()
    print("群发结果:", res)
    return res


def main():
    token = get_access_token()
    print("token:", token)

    thumb_id = upload_thumb(token)
    print("thumb:", thumb_id)

    html = build_html()
    title = f"MSAI每日新闻 {datetime.now().strftime('%m-%d')}"

    media_id = upload_mpnews(token, thumb_id, html, title)
    print("media_id:", media_id)

    result = send_all(token, media_id)

    errcode = result.get("errcode")
    if errcode != 0:
        raise RuntimeError(f"群发失败: {result}")


if __name__ == "__main__":
    main()
