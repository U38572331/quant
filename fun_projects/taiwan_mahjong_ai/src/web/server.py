
import http.server
import socketserver
import json
import os
import sys

# Path setup should be done by launcher, but ensure we can find src
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.web.game_interface import GameInterface

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(__file__), 'static')

game = GameInterface()

class MahjongHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Override to serve from 'static' directory by default for /
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        trailing_slash = path.rstrip().endswith('/')
        
        # API Routes don't map to files
        if path.startswith('/api/'):
            return path
            
        # Static files
        path = os.path.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = WEB_DIR
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def do_GET(self):
        if self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            state = game.get_state_json()
            self.wfile.write(json.dumps(state).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/action':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            
            success = False
            if 'discard' in data:
                tile_idx = int(data['discard'])
                success = game.handle_discard(tile_idx)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode('utf-8'))
            
        elif self.path == '/api/reset':
            game.reset_game()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"success": true}')
            
        else:
            self.send_error(404, "API not found")

def run_server():
    print(f"Serving at http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), MahjongHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
