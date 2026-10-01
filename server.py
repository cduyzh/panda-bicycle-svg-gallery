import http.server
import socketserver
import os
import json
import urllib.parse
import datetime

PORT = 8000
DIRECTORY = "."

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/api/svgs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            
            svgs = []
            for f in os.listdir(DIRECTORY):
                if f.endswith('.svg'):
                    filepath = os.path.join(DIRECTORY, f)
                    mtime = os.path.getmtime(filepath)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                    svgs.append({'name': f, 'date': date_str})
                    
            self.wfile.write(json.dumps(svgs).encode())
        else:
            super().do_GET()
            
    def end_headers(self):
        if self.path.endswith('.svg') or self.path == '/' or self.path.endswith('.html'):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server started at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
