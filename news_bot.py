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

def save_pushed_ids(ids):
    """保存已推送的新闻ID"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

def fetch_rss():
    """抓取所有RSS源的新内容（测试模式 - 返回测试新闻）"""
    # 测试模式：直接返回一条测试新闻
    test_news = [{
        'id': 'test_' + str(int(time.time())),
        'title': '【测试消息】如果看到这条，说明推送正常',
        'link': 'https://github.com',
        'source': '系统测试',
        'time': datetime.now().strftime('%Y-%m-%d')
    }]
    return test_news
    
    # 以下是正式代码（暂时被上面的return跳过）
    # 等测试成功后，可以删除上面的return，启用下面的正式代码
    """
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
    """

def send_to_wechat(news_list):
    """企业微信消息发送函数"""
    if not news_list:
        print("没有新闻可推送")
        return
    
    # 构建消息内容
    today = datetime.now().strftime('%Y年%m月%d日')
    content = f"📰 **每日新闻简报 {today}**\n\n"
    
    for i, news in enumerate(news_list[:10], 1):
        content += f"{i}. [{news['source']}] {news['title']}\n"
        content += f"   [查看全文]({news['link']})\n\n"
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        print("📤 正在发送请求到企业微信...")
        print(f"📦 请求URL: {webhook_url}")
        
        response = requests.post(
            webhook_url, 
            json=message,
            timeout=10
        )
        
        print(f"📥 状态码: {response.status_code}")
        print(f"📥 返回内容: {response.text}")
        
        result = response.json()
        if result.get('errcode') == 0:
            print("🎉 消息发送成功！")
            return True
        else:
            print(f"❌ 企业微信返回错误: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("开始执行每日新闻推送任务")
    print(f"时间: {datetime.now()}")
    print(f"Webhook地址是否存在: {'是' if webhook_url else '否'}")
    print("=" * 50)
    
    if not webhook_url:
        print("❌ 错误: 没有配置Webhook地址")
        return
    
    # 获取新闻
    print("\n📡 正在抓取新闻...")
    news = fetch_rss()
    print(f"✅ 抓取到 {len(news)} 条新闻")
    
    # 推送新闻
    print("\n📨 正在推送新闻...")
    send_to_wechat(news)
    
    print("\n✨ 任务执行完毕")

if __name__ == "__main__":
    main()
