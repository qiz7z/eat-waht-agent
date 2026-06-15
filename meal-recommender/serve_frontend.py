"""
简单的前端静态文件服务器，用于预览 static/index.html
运行: python serve_frontend.py
访问: http://localhost:8080
"""
import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} - {fmt % args}")

if __name__ == "__main__":
    os.chdir(STATIC_DIR)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n[OK] 前端页面已启动: {url}")
        print(f"     静态目录: {STATIC_DIR}")
        print(f"     按 Ctrl+C 停止\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止。")
