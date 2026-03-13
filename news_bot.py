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
    """强制返回测试新闻（忽略RSS源）"""
    print("=" * 60)
    print("🔴 当前处于【强制测试模式】")
    print("=" * 60)
    
    # 强制返回一条测试新闻
    test_news = [{
        'id': 'test_' + str(int(time.time())),
        'title': '【强制测试】如果看到这条，说明推送链路完全正常',
        'link': 'https://github.com/ms405755994-ops/daily-news-push',
        'source': '系统强制测试',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }]
    
    print(f"📢 测试新闻: {test_news[0]['title']}")
    return test_news

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
    
    # 添加footer
    content += "---\n"
    content += "🤖 新闻助手自动推送 | 测试模式"
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        print("\n📤 正在发送请求到企业微信...")
        print(f"📦 请求URL: {webhook_url[:50]}...")  # 只显示前50个字符
        
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
    print("=" * 60)
    print("🚀 每日新闻推送任务开始")
    print(f"📅 时间: {datetime.now()}")
    print(f"🔑 Webhook地址: {'✅ 已配置' if webhook_url else '❌ 未配置'}")
    print("=" * 60)
    
    if not webhook_url:
        print("❌ 错误: 没有配置Webhook地址")
        return
    
    # 获取测试新闻
    print("\n📡 正在生成测试新闻...")
    news = fetch_rss()
    print(f"\n✅ 生成 {len(news)} 条测试新闻")
    
    # 推送新闻
    print("\n📨 正在推送新闻...")
    send_to_wechat(news)
    
    print("\n✨ 任务执行完毕")
    print("=" * 60)

if __name__ == "__main__":
    main()
