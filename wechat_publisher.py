import os
import time
import json
import requests
from pathlib import Path

# =========================
# 配置（从 GitHub Secrets 读取）
# =========================

APPID = os.getenv("WECHAT_APPID")
SECRET = os.getenv("WECHAT_SECRET")
AUTHOR = os.getenv("WECHAT_AUTHOR", "MSAI")[:8]   # ⚠️ 最多8个字符
THUMB_PATH = "docs/cover.jpg"  # 本地封面图（必须 < 2MB）

NEWS_JSON_PATH = "docs/news-data.json"

# =========================
# 获取 access_token
# =========================

def get_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": SECRET
    }
    res = requests.get(url, params=params).json()
    print("token response:", res)

    token = res.get("access_token")
    if not token:
        raise RuntimeError("获取 token 失败")

    return token


# =========================
# 上传封面图
# =========================

def upload_thumb(token):
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=thumb"

    if not Path(THUMB_PATH).exists():
        raise RuntimeError("封面图不存在")

    files = {
        "media": open(THUMB_PATH, "rb")
    }

    res = requests.post(url, files=files).json()
    print("thumb response:", res)

    thumb_id = res.get("media_id") or res.get("thumb_media_id")

    if not thumb_id:
        raise RuntimeError(f"上传缩略图失败: {res}")

    print("thumb:", thumb_id)
    return thumb_id


# =========================
# 生成 HTML 内容
# =========================

def build_html():
    data = json.loads(Path(NEWS_JSON_PATH).read_text(encoding="utf-8"))

    html = f"<h2>{data['title']}</h2>"

    # ===== 热点 =====
    html += "<h3>🔥 关键热点</h3>"
    for h in data.get("hotspots", []):
        html += f"<p><b>{h['title']}</b><br>{h['reason']}</p>"

    # ===== 新闻 =====
    html += "<h3>📰 新闻</h3>"
    for n in data.get("news_items", []):
        html += f"""
        <p>
        <b>{n['short_title']}</b><br>
        {n['summary']}<br>
        <a href="{n['link']}">阅读全文</a>
        </p>
        """

    # ===== 期货 =====
    html += "<h3>📊 期货</h3>"
    for f in data.get("futures", []):
        html += f"<p>{f['name']}：{f['price']}</p>"

    return html


# =========================
# 上传图文消息
# =========================

def upload_mpnews(token, thumb_id, html, title):
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadnews?access_token={token}"

    data = {
        "articles": [{
            "title": title,
            "author": AUTHOR,
            "digest": title[:50],
            "content": html,
            "thumb_media_id": thumb_id,
            "show_cover_pic": 1
        }]
    }

    print("AUTHOR used:", AUTHOR)

    res = requests.post(url, json=data).json()
    print("uploadnews response:", res)

    media_id = res.get("media_id")
    if not media_id:
        raise RuntimeError(f"创建图文失败: {res}")

    return media_id


# =========================
# 群发消息
# =========================

def send_mass(token, media_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={token}"

    data = {
        "filter": {
            "is_to_all": True
        },
        "mpnews": {
            "media_id": media_id
        },
        "msgtype": "mpnews"
    }

    res = requests.post(url, json=data).json()
    print("群发结果:", res)

    if res.get("errcode") != 0:
        raise RuntimeError(f"群发失败: {res}")

    return res


# =========================
# 查询群发状态（关键新增）
# =========================

def check_mass_status(token, msg_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/get?access_token={token}"

    data = {"msg_id": msg_id}

    res = requests.post(url, json=data).json()
    print("群发状态查询:", res)

    status = res.get("msg_status")

    status_map = {
        "SEND_SUCCESS": "✅ 全部成功",
        "SENDING": "⏳ 发送中",
        "SEND_FAIL": "❌ 发送失败",
        "DELETE": "⚠️ 已删除",
    }

    return status_map.get(status, status)


# =========================
# 主程序
# =========================

def main():
    token = get_token()

    thumb_id = upload_thumb(token)

    html = build_html()
    title = "MSAI今日新闻"

    media_id = upload_mpnews(token, thumb_id, html, title)

    res = send_mass(token, media_id)

    msg_id = res.get("msg_id")

    # ===== 等待并查询状态 =====
    print("开始检查群发状态...")

    for i in range(6):
        time.sleep(10)
        status = check_mass_status(token, msg_id)
        print(f"第{i+1}次检查:", status)

        if status in ["✅ 全部成功", "❌ 发送失败"]:
            break


if __name__ == "__main__":
    main()
