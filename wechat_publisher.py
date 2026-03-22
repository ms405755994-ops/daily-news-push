import os
import time
import json
import requests
from pathlib import Path

# =========================
# 固定配置（避免再踩坑）
# =========================

APPID = os.getenv("WECHAT_APPID")
SECRET = os.getenv("WECHAT_SECRET")

AUTHOR = "MSAI"   # ⚠️ 必须短，不能用公众号名
THUMB_PATH = "docs/cover.jpg"
NEWS_JSON_PATH = "docs/news-data.json"


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
    print("token response:", res)

    token = res.get("access_token")
    if not token:
        raise RuntimeError("获取 token 失败")

    return token


# =========================
# 上传封面
# =========================

def upload_thumb(token):
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=thumb"

    if not Path(THUMB_PATH).exists():
        raise RuntimeError(f"封面不存在: {THUMB_PATH}")

    # ⚠️ 微信限制 <2MB
    size = os.path.getsize(THUMB_PATH)
    if size > 2 * 1024 * 1024:
        raise RuntimeError("封面超过2MB，请压缩")

    files = {
        "media": open(THUMB_PATH, "rb")
    }

    res = requests.post(url, files=files).json()
    print("thumb response:", res)

    thumb_id = res.get("media_id") or res.get("thumb_media_id")

    if not thumb_id:
        raise RuntimeError(f"上传封面失败: {res}")

    print("thumb:", thumb_id)
    return thumb_id


# =========================
# 构建 HTML
# =========================

def build_html():
    data = json.loads(Path(NEWS_JSON_PATH).read_text(encoding="utf-8"))

    html = f"<h2>{data['title']}</h2>"

    # 热点
    html += "<h3>🔥 关键热点</h3>"
    for h in data.get("hotspots", []):
        html += f"<p><b>{h['title']}</b><br>{h['reason']}</p>"

    # 新闻
    html += "<h3>📰 新闻</h3>"
    for n in data.get("news_items", []):
        html += f"""
        <p>
        <b>{n['short_title']}</b><br>
        {n['summary']}<br>
        <a href="{n['link']}">阅读全文</a>
        </p>
        """

    # 期货
    html += "<h3>📊 期货</h3>"
    for f in data.get("futures", []):
        html += f"<p>{f['name']}：{f['price']}</p>"

    return html


# =========================
# 创建图文
# =========================

def upload_thumb(token):
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=thumb"

    if not Path(THUMB_PATH).exists():
        raise RuntimeError(f"封面不存在: {THUMB_PATH}")

    size = os.path.getsize(THUMB_PATH)
    if size > 2 * 1024 * 1024:
        raise RuntimeError("封面超过2MB")

    files = {
        "media": open(THUMB_PATH, "rb")
    }

    res = requests.post(url, files=files).json()
    print("thumb response:", res)

    # ⚠️ 必须用这个
    thumb_id = res.get("thumb_media_id")

    if not thumb_id:
        raise RuntimeError(f"上传封面失败: {res}")

    print("thumb_media_id:", thumb_id)
    return thumb_id


# =========================
# 群发
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
# 查询群发状态
# =========================

def check_mass_status(token, msg_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/mass/get?access_token={token}"

    res = requests.post(url, json={"msg_id": msg_id}).json()
    print("群发状态查询:", res)

    status = res.get("msg_status")

    mapping = {
        "SEND_SUCCESS": "✅ 全部成功",
        "SENDING": "⏳ 发送中",
        "SEND_FAIL": "❌ 发送失败",
        "DELETE": "⚠️ 已删除",
    }

    return mapping.get(status, status)


# =========================
# 主流程
# =========================

def main():
    token = get_token()

    thumb_id = upload_thumb(token)

    html = build_html()
    title = "MSAI今日新闻"

    media_id = upload_mpnews(token, thumb_id, html, title)

    res = send_mass(token, media_id)
    msg_id = res.get("msg_id")

    print("开始检查群发状态...")

    for i in range(6):
        time.sleep(10)
        status = check_mass_status(token, msg_id)
        print(f"第{i+1}次:", status)

        if status in ["✅ 全部成功", "❌ 发送失败"]:
            break


if __name__ == "__main__":
    main()
