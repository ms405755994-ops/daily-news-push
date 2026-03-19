name: Daily News Radar

on:
  schedule:
    # 每天 07:30 中国时间（UTC 23:30，前一天）
    - cron: '30 23 * * *'

    # 每天 20:00 中国时间（UTC 12:00）
    - cron: '0 12 * * *'

  workflow_dispatch:

jobs:
  run-news-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt

      - name: Run News Bot
        run: |
          python news_bot.py
        env:
          NEWS_DATA_KEY: ${{ secrets.NEWS_DATA_KEY }}
          GNEWS_KEY: ${{ secrets.GNEWS_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          WECHAT_WEBHOOK: ${{ secrets.WECHAT_WEBHOOK }}
          AMAP_KEY: ${{ secrets.AMAP_KEY }}

          MAX_FETCH_PER_API: 40
          MAX_FETCH_PER_RSS: 25
          MAX_NEWS: 12

          REPORT_CITY: 汕头
          REPORT_LUNAR_TEXT: 农历二月初一
