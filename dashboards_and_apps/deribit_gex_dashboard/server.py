import http.server
import socketserver
import urllib.request
import json
import ssl
import os
import sys

# Ensure we are serving from the script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

PORT = 8000

class DeribitHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. API Route
        if self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                # SSL context for HTTPS
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"
                print(f"Fetching data from: {url}")
                
                with urllib.request.urlopen(url, context=ctx) as response:
                    data = response.read()
                    self.wfile.write(data)
                    print("Data fetched successfully")
            except Exception as e:
                error_msg = json.dumps({"error": str(e)})
                self.wfile.write(error_msg.encode())
                print(f"Error fetching data: {e}")
            return

        # 2. Static File Routes
        # Clean path (remove query params)
        path = self.path.split('?')[0]
        # Handle trailing slash if present (except for root)
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
        
        if path == '/' or path == '/index.html':
            filename = 'index.html'
            content_type = 'text/html'
        elif path == '/style.css':
            filename = 'style.css'
            content_type = 'text/css'
        elif path == '/app.js':
            filename = 'app.js'
            content_type = 'application/javascript'
        else:
            self.send_error(404, "File Not Found")
            return

        # Serve the file
        try:
            full_path = os.path.join(BASE_DIR, filename)
            with open(full_path, 'rb') as f:
                content = f.read()
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f"File {filename} not found on server")
        except Exception as e:
            self.send_error(500, str(e))

class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

# Allow reuse of address to avoid "Address already in use" errors on restart
socketserver.TCPServer.allow_reuse_address = True

print(f"Starting server on port {PORT}...")
print(f"Serving files from: {BASE_DIR}")

with ThreadingHTTPServer(("", PORT), DeribitHandler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()
