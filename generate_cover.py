import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# =========================
# 配置
# =========================

WIDTH = 900
HEIGHT = 500
OUTPUT_PATH = "docs/cover.jpg"
NEWS_JSON_PATH = "docs/news-data.json"

BG_COLOR = (20, 32, 60)      # 深蓝背景
TITLE_COLOR = (255, 255, 255)
SUB_COLOR = (180, 200, 255)

# =========================
# 字体（自动降级）
# =========================

def load_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()


# =========================
# 读取新闻
# =========================

def get_title():
    if not Path(NEWS_JSON_PATH).exists():
        return "MSAI 今日新闻"

    data = json.loads(Path(NEWS_JSON_PATH).read_text(encoding="utf-8"))

    title = data.get("title", "")
    return title[:28] if title else "MSAI 今日新闻"


# =========================
# 自动换行
# =========================

def wrap_text(draw, text, font, max_width):
    lines = []
    current = ""

    for char in text:
        test_line = current + char
        w = draw.textlength(test_line, font=font)

        if w <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = char

    if current:
        lines.append(current)

    return lines


# =========================
# 生成封面
# =========================

def generate_cover():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title = get_title()

    title_font = load_font(48)
    sub_font = load_font(24)

    # 标题自动换行
    lines = wrap_text(draw, title, title_font, WIDTH - 80)

    y = 120
    for line in lines:
        w = draw.textlength(line, font=title_font)
        draw.text(((WIDTH - w) / 2, y), line, font=title_font, fill=TITLE_COLOR)
        y += 60

    # 副标题
    subtitle = "GLOBAL NEWS"
    w = draw.textlength(subtitle, font=sub_font)
    draw.text(((WIDTH - w) / 2, y + 20), subtitle, font=sub_font, fill=SUB_COLOR)

    # 装饰条
    draw.rectangle([(0, HEIGHT - 80), (WIDTH, HEIGHT)], fill=(40, 60, 120))

    # 保存（压缩避免超2MB）
    img.save(OUTPUT_PATH, "JPEG", quality=85, optimize=True)

    print(f"封面生成成功: {OUTPUT_PATH}")


# =========================
# 主函数
# =========================

if __name__ == "__main__":
    generate_cover()
