#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import tempfile
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8765
WEB_DIR = os.path.dirname(os.path.abspath(__file__))


class KaiDrawHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Permissions-Policy", "camera=(*)")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/mac-snap"):
            self.handle_mac_snap()
        else:
            super().do_GET()

    def handle_mac_snap(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            # Capture 1 frame from Mac default FaceTime/AVFoundation camera (index 0)
            cmd = [
                "/opt/homebrew/bin/ffmpeg",
                "-y",
                "-f",
                "avfoundation",
                "-framerate",
                "30",
                "-i",
                "0",
                "-frames:v",
                "1",
                tmp_path,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                with open(tmp_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                payload = json.dumps({"ok": True, "image": f"data:image/jpeg;base64,{b64}"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)
                return
        except Exception as e:
            pass
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": False}).encode("utf-8"))


if __name__ == "__main__":
    print(f"Starting KaiDraw Prototype Server on http://0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), KaiDrawHandler)
    server.serve_forever()
