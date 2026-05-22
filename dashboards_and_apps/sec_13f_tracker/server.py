import http.server
import socketserver
import os
import webbrowser
import threading
import time

PORT = 8080
DIRECTORY = "public"

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Disable caching to ensure latest data/CSS is served
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Silent logging to clean terminal, but can be enabled for debugging
        # super().log_message(format, *args)
        pass

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")

def main():
    if not os.path.exists(DIRECTORY):
        os.makedirs(DIRECTORY)

    print(f"🚀 Launching Refined Terminal at http://localhost:{PORT}")
    
    # Allow port reuse to avoid address already in use errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    
    # Auto-open browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    with ThreadedHTTPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    main()
