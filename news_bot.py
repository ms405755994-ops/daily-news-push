import requests
import feedparser
import json
import os
from datetime import datetime
import time

# 企业微信机器人Webhook地址（从Secrets读取）
webhook_url = os.environ.get('QYWX_WEBHOOK')

# RSS订阅源列表 - 全部为简体中文新闻源
RSS_FEEDS = [
    "http://www.people.com.cn/rss/politics.xml",           # 人民网时政新闻
    "http://www.xinhuanet.com/politics/news_politics.xml", # 新华网时政
    "https://feedparser.pythonanywhere.com/people.com.cn/rss",  # 人民日报
    "http://www.chinanews.com/rss/scroll-news.xml",        # 中国新闻网
    "https://rsshub.app/zhihu/daily",                       # 知乎日报（简体中文）
    "https://rsshub.app/36kr/news/latest",                  # 36氪（科技新闻）
    "https://rsshub.app/thepaper/latest"                    # 澎湃新闻
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
    """抓取所有RSS源的新内容（正式版）"""
    all_entries = []
    pushed_ids = load_pushed_ids()
    new_ids = []
    
    print(f"📊 已推送新闻ID数量: {len(pushed_ids)}")
    
    for feed_url in RSS_FEEDS:
        try:
            print(f"\n📡 正在抓取: {feed_url}")
            feed = feedparser.parse(feed_url)
            feed_title = feed.feed.get('title', '未知来源')
            
            # 获取该源的前5条新闻
            entries = feed.entries[:5]
            print(f"  找到 {len(entries)} 条新闻")
            
            for entry in entries:
                # 生成唯一ID（使用链接或id字段）
                entry_id = entry.get('id', entry.get('link', ''))
                if not entry_id:
                    continue
                    
                # 检查是否已推送过
                if entry_id in pushed_ids:
                    print(f"  ⏭️ 跳过已推送: {entry.get('title', '无标题')[:30]}...")
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
                print(f"  ✅ 新增: {title[:40]}...")
                
            time.sleep(1)  # 礼貌性延迟，避免被封
        except Exception as e:
            print(f"❌ 抓取 {feed_url} 失败: {e}")
    
    # 保存新推送的ID
    if new_ids:
        save_pushed_ids(pushed_ids + new_ids)
        print(f"\n📦 已保存 {len(new_ids)} 条新新闻ID")
    else:
        print("\n📭 没有新新闻")
    
    return all_entries

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
    content += "🤖 新闻助手自动推送 | 每天早8点更新"
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        print("\n📤 正在发送请求到企业微信...")
        
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
    print(f"📡 RSS源数量: {len(RSS_FEEDS)}")
    print("=" * 60)
    
    if not webhook_url:
        print("❌ 错误: 没有配置Webhook地址")
        return
    
    # 获取新闻
    print("\n📡 正在抓取新闻...")
    news = fetch_rss()
    print(f"\n✅ 共抓取到 {len(news)} 条新新闻")
    
    # 推送新闻
    if news:
        print("\n📨 正在推送新闻...")
        send_to_wechat(news)
    else:
        print("\n📭 没有新新闻，无需推送")
    
    print("\n✨ 任务执行完毕")
    print("=" * 60)

if __name__ == "__main__":
    main()
