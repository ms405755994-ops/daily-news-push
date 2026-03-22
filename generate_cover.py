from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path

OUTPUT_PATH = "docs/cover.jpg"

def generate_cover():
    width, height = 900, 500

    # ===== 背景（蓝色渐变）
    img = Image.new("RGB", (width, height), "#1e3c72")
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(30 + (y / height) * 20)
        g = int(60 + (y / height) * 80)
        b = int(114 + (y / height) * 100)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # ===== 字体（系统默认）
    try:
        font_big = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # ===== 标题
    title = "MSAI今日新闻"

    # ===== 日期
    today = datetime.now().strftime("%Y.%m.%d")

    # ===== 居中计算
    w1, h1 = draw.textbbox((0, 0), title, font=font_big)[2:]
    w2, h2 = draw.textbbox((0, 0), today, font=font_small)[2:]

    draw.text(((width - w1) / 2, height / 2 - 80), title, fill="white", font=font_big)
    draw.text(((width - w2) / 2, height / 2 + 20), today, fill="white", font=font_small)

    # ===== 保存
    Path("docs").mkdir(exist_ok=True)
    img.save(OUTPUT_PATH, "JPEG", quality=85)

    print("封面生成成功:", OUTPUT_PATH)


if __name__ == "__main__":
    generate_cover()
