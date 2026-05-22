"""
Simple HTTP proxy + static file server.
Serves static files from current directory, proxies /api to backend.
"""
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import http.client

STATIC_PORT = 5173
API_HOST = "localhost"
API_PORT = 8000

class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy("GET")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy("POST")
        else:
            super().do_GET()

    def proxy(self, method):
        # Parse the path and create connection to backend
        conn = http.client.HTTPConnection(API_HOST, API_PORT)

        # Read body if POST
        body = None
        if method == "POST":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

        # Forward headers
        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ("host", "connection"):
                headers[key] = value

        try:
            conn.request(method, self.path, body=body, headers=headers)
            response = conn.getresponse()

            # Send response back to client
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            for key, value in response.getheaders():
                if key.lower() not in ("host", "connection"):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")
        finally:
            conn.close()

    def log_message(self, format, *args):
        print(f"{self.address[0]} - [{self.log_date_time_string()}] {format % args}")

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", STATIC_PORT), ProxyHandler)
    print(f"Serving on http://localhost:{STATIC_PORT} — API proxy → http://{API_HOST}:{API_PORT}")
    server.serve_forever()