import http.server
import socketserver
import threading
import subprocess
import time
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

httpd = socketserver.TCPServer(('0.0.0.0', 8080), QuietHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
print("[ALGORISE WEB] Local server running on port 8080.")

print("[ALGORISE WEB] Launching public cloud tunnel...")
p = subprocess.Popen('npx localtunnel --port 8080 --subdomain algorise-ai', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)

for line in p.stdout:
    sys.stdout.write(line)
    sys.stdout.flush()
