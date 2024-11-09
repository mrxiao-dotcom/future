import os
import requests
from pathlib import Path

def download_file(url, filename):
    """下载文件并保存"""
    try:
        print(f"正在下载 {filename}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 确保目录存在
        os.makedirs('static/lib', exist_ok=True)
        
        # 保存文件
        file_path = Path('static/lib') / filename
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"{filename} 下载成功！")
        return True
    except Exception as e:
        print(f"下载 {filename} 失败: {str(e)}")
        return False

def main():
    # 要下载的文件列表
    files = [
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
            'filename': 'bootstrap.min.css'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css.map',
            'filename': 'bootstrap.min.css.map'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
            'filename': 'bootstrap.bundle.min.js'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js.map',
            'filename': 'bootstrap.bundle.min.js.map'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js',
            'filename': 'echarts.min.js'
        }
    ]
    
    # 下载所有文件
    success_count = 0
    for file in files:
        if download_file(file['url'], file['filename']):
            success_count += 1
    
    # 打印结果
    print(f"\n下载完成！成功: {success_count}/{len(files)}")
    
    if success_count < len(files):
        print("\n以下是备用下载地址：")
        print("Bootstrap CSS: https://fastly.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css")
        print("Bootstrap CSS Map: https://fastly.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css.map")
        print("Bootstrap JS: https://fastly.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js")
        print("Bootstrap JS Map: https://fastly.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js.map")
        print("ECharts: https://fastly.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js")
        print("\n如果自动下载失败，请手动下载并放置到 static/lib 目录下")

if __name__ == "__main__":
    main() 