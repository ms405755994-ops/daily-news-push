import requests
import feedparser
import json
import os
from datetime import datetime
import time

# 企业微信机器人Webhook地址（从Secrets读取）
webhook_url = os.environ.get('QYWX_WEBHOOK')

# RSS订阅源列表 - 你可以在这里添加/修改你想订阅的新闻源
RSS_FEEDS = [
    "https://www.bbc.co.uk/news/10628494.rss",  # BBC中文
    "https://rsshub.app/zhihu/daily",           # 知乎日报
    "https://feedparser.pythonanywhere.com/people.com.cn/rss"  # 人民日报
]

# 用于记录已推送新闻ID的文件
DATA_FILE = 'pushed_news.json'

def load_pushed_ids():
    """加载已推送过的新闻ID"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []
def fetch_rss():
    """抓取所有RSS源的新内容"""
    # 👇👇👇 临时添加：强制加一条测试新闻
    test_news = [{
        'id': 'test_' + str(int(time.time())),
        'title': '【测试消息】如果看到这条，说明推送正常',
        'link': 'https://github.com',
        'source': '系统测试',
        'time': datetime.now().strftime('%Y-%m-%d')
    }]
    return test_news
    # 👆👆👆 测试代码结束
    # （下面的原代码会被暂时跳过）
    
    all_entries = []
def save_pushed_ids(ids):
    """保存已推送的新闻ID"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

def fetch_rss():
    """抓取所有RSS源的新内容"""
    all_entries = []
    pushed_ids = load_pushed_ids()
    new_ids = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            feed_title = feed.feed.get('title', '未知来源')
            
            for entry in feed.entries[:5]:  # 每个源取前5条
                entry_id = entry.get('id', entry.get('link', ''))
                if entry_id in pushed_ids:
                    continue
                    
                title = entry.get('title', '无标题')
                link = entry.get('link', '')
                published = entry.get('published', datetime.now().strftime('%Y-%m-%d'))
                
                all_entries.append({
                    'id': entry_id,
                    'title': title,
                    'link': link,
                    'source': feed_title,
                    'time': published
                })
                new_ids.append(entry_id)
                
            time.sleep(1)  # 礼貌性延迟，避免被封
        except Exception as e:
            print(f"抓取 {feed_url} 失败: {e}")
    
    # 保存新推送的ID
    if new_ids:
        save_pushed_ids(pushed_ids + new_ids)
    
    return all_entries

def send_to_wechat(news_list):
    """修正后的企业微信消息发送函数"""
    
    # 构建一个最简单的文本消息
    message = {
        "msgtype": "text",
        "text": {
            "content": "✅ 测试成功！如果你的企业微信收到这条消息，说明机器人配置正确。"
        }
    }
    
    # 设置正确的请求头
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("📤 正在发送请求到企业微信...")
        print(f"📦 请求URL: {webhook_url}")
        print(f"📦 请求内容: {message}")
        
        # 发送POST请求
        response = requests.post(
            webhook_url, 
            json=message,  # 使用json参数，requests会自动处理格式和头信息
            headers=headers,
            timeout=10
        )
        
        print(f"📥 状态码: {response.status_code}")
        print(f"📥 返回内容: {response.text}")
        
        # 解析返回结果
        result = response.json()
        if result.get('errcode') == 0:
            print("🎉 恭喜！消息发送成功！请检查你的企业微信群。")
            return True
        else:
            print(f"❌ 企业微信返回错误: {result}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查网络")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请检查URL是否正确")
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
    
    return False

