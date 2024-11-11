from PIL import Image, ImageDraw, ImageFont
import io

def generate_favicon():
    # 创建一个 32x32 的图像（标准 favicon 尺寸）
    img = Image.new('RGBA', (32, 32), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制一个简单的图表图标
    # 背景
    draw.rectangle([0, 0, 31, 31], fill=(13, 110, 253), outline=(13, 110, 253))  # Bootstrap primary color
    
    # 绘制折线图样式
    points = [(5, 25), (12, 15), (19, 20), (26, 8)]
    draw.line(points, fill=(255, 255, 255), width=2)
    
    # 在每个点绘制小圆点
    for x, y in points:
        draw.ellipse([x-2, y-2, x+2, y+2], fill=(255, 255, 255))
    
    # 保存为 ICO 格式
    favicon_path = 'static/favicon.ico'
    img.save(favicon_path, format='ICO', sizes=[(32, 32)])
    print(f"Favicon generated and saved to {favicon_path}")

if __name__ == "__main__":
    generate_favicon() 