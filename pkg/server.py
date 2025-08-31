import http.server
import socketserver
import os
import json
import logging
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from urllib.parse import parse_qs

PORT = 3001
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_PATH = os.path.join(BASE_DIR, 'storage', 'data.json')

env = Environment(loader=FileSystemLoader(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)


def get_content_type(file_path):
    ext = os.path.splitext(file_path)[1]
    return {
        '.html': 'text/html',
        '.css': 'text/css',
        '.png': 'image/png'
    }.get(ext, 'application/octet-stream')


class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        routes = {
            '/': 'index.html',
            '/message': 'message.html'
        }
        if self.path in routes:
            self.serve_file(os.path.join(BASE_DIR, routes[self.path]), 'text/html')
        elif self.path == '/read':
            self.serve_read()
        else:
            file_path = os.path.join(BASE_DIR, self.path.lstrip('/'))
            if os.path.isfile(file_path):
                self.serve_file(file_path, get_content_type(file_path))
            else:
                self.send_error_page()

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            fields = parse_qs(post_data.decode('utf-8'))
            username = fields.get('username', [''])[0]
            message = fields.get('message', [''])[0]
            if username and message:
                self.save_message(username, message)
                self.send_response(303)
                self.send_header('Location', '/read')
                self.end_headers()
            else:
                self.send_error_page()
        else:
            self.send_error_page()

    def save_message(self, username, message):
        try:
            if os.path.exists(STORAGE_PATH):
                with open(STORAGE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception as e:
            logging.error(f'Error reading JSON: {e}')
            data = {}
        timestamp = str(datetime.now())
        data[timestamp] = {'username': username, 'message': message}
        os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
        try:
            with open(STORAGE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f'Error writing JSON: {e}')

    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except Exception as e:
            logging.error(f'Error serving file: {e}')
            self.send_error_page()

    def serve_read(self):
        try:
            if os.path.exists(STORAGE_PATH):
                with open(STORAGE_PATH, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            else:
                messages = {}
        except Exception as e:
            logging.error(f'Error reading file: {e}')
            messages = {}
        template = env.get_template('read.html')
        html = template.render(messages=messages)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_error_page(self):
        error_path = os.path.join(BASE_DIR, 'error.html')
        try:
            if os.path.isfile(error_path):
                with open(error_path, 'rb') as f:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
        except Exception as e:
            logging.error(f'Error serving error.html: {e}')
            self.send_error(404)


if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        logging.info(f"Server started on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logging.info("Server stopped by user.")
