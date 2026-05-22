import os
import sys
import threading
import webview
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Custom handler to ensure correct MIME types and headers (if needed)
class GameRequestHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        '.manifest': 'text/cache-manifest',
        '.html': 'text/html',
        '.png': 'image/png',
        '.jpg': 'image/jpg',
        '.svg': 'image/svg+xml',
        '.css': 'text/css',
        '.js': 'application/x-javascript',
        '': 'application/octet-stream', # Default
    }
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def run(httpd):
    httpd.serve_forever()

if __name__ == '__main__':
    # When frozen, files are extracted to sys._MEIPASS
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)
        
    # Find free port
    server_address = ('127.0.0.1', 0)
    httpd = HTTPServer(server_address, GameRequestHandler)
    port = httpd.server_port
    
    # Run server in thread
    t = threading.Thread(target=run, args=(httpd,))
    t.daemon = True
    t.start()
    
    # Create window
    webview.create_window('玻璃欣模擬器', f'http://127.0.0.1:{port}/index.html', width=1200, height=800, resizable=True)
    webview.start()
