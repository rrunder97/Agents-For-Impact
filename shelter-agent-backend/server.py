import http.server
import socketserver
import os
import json
from main import find_shelters

PORT = int(os.environ.get("PORT", 8080))
UI_DIR = os.path.join(os.path.dirname(__file__), "ui")

class RequestAdapter:
    def __init__(self, method, json_data, headers):
        self.method = method
        self._json = json_data
        self.headers = headers

    def get_json(self, silent=True):
        return self._json

class CloudRunHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def do_POST(self):
        # Handle API calls at /, /find-shelters, /api/find-shelters, or /book-shelter
        clean_path = self.path.split("?")[0]
        if clean_path in ["/", "/find-shelters", "/api/find-shelters", "/book-shelter"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

            try:
                json_data = json.loads(post_data.decode("utf-8")) if post_data else {}
            except Exception:
                json_data = {}

            if clean_path == "/book-shelter":
                json_data["action"] = "book"

            req = RequestAdapter(
                method="POST",
                json_data=json_data,
                headers=dict(self.headers)
            )

            res_body, status_code, headers = find_shelters(req)

            self.send_response(status_code)
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(res_body.encode("utf-8"))
        else:
            self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "3600")
        self.end_headers()

    def do_GET(self):
        # Health check
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        # Serve static UI files
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CloudRunHandler) as httpd:
        print(f"Cloud Run Shelter Service listening on port {PORT}")
        httpd.serve_forever()
