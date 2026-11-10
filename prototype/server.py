#!/usr/bin/env python3
import base64
import json
import os
import re
import subprocess
import tempfile
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

DEFAULT_TEST_KEY = "kaidraw-test-key-2026"

class KaiDrawHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Permissions-Policy", "camera=(*)")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/mac-snap"):
            self.handle_mac_snap()
        elif self.path.startswith("/api/health"):
            self.send_json(200, {
                "ok": True,
                "status": "online",
                "service": "KaiDraw Local AI & Video API Gateway",
                "version": "2.0.0",
                "endpoints": {
                    "image_to_video": "/api/ai/image-to-video",
                    "magic_polish": "/api/ai/polish"
                },
                "default_test_key": DEFAULT_TEST_KEY
            })
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/ai/image-to-video") or self.path.startswith("/api/ai/video"):
            self.handle_image_to_video()
        elif self.path.startswith("/api/ai/polish"):
            self.handle_polish()
        else:
            self.send_json(404, {"ok": False, "error": f"Endpoint not found: {self.path}"})

    def check_auth(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header:
            return False, "缺少 Authorization 标头。请传递 'Authorization: Bearer <api_key>'"
        match = re.match(r"^Bearer\s+(.+)$", auth_header, re.IGNORECASE)
        if not match:
            return False, "无效的 Authorization 格式。请使用 'Bearer <api_key>'"
        token = match.group(1).strip()
        if not token:
            return False, "API Key 不能为空"
        # 允许指定测试 Key 或任意用户自定义格式的 Key
        return True, token

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return None
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception:
            return None

    def send_json(self, status_code, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def handle_mac_snap(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cmd = [
                "/opt/homebrew/bin/ffmpeg",
                "-y",
                "-f", "avfoundation",
                "-framerate", "30",
                "-i", "0",
                "-frames:v", "1",
                tmp_path,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                with open(tmp_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                self.send_json(200, {"ok": True, "image": f"data:image/jpeg;base64,{b64}"})
                return
        except Exception as e:
            pass
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        self.send_json(500, {"ok": False, "error": "Camera capture failed"})

    def handle_image_to_video(self):
        auth_ok, auth_msg = self.check_auth()
        if not auth_ok:
            self.send_json(401, {"ok": False, "error": f"认证失败 (401 Unauthorized): {auth_msg}"})
            return

        body = self.read_json_body()
        if not body or "image" not in body:
            self.send_json(400, {"ok": False, "error": "请求体内缺少 'image' 字段 (需提供 base64 图片字符串)"})
            return

        raw_image_data = body["image"]
        motion = body.get("motion", "breathe")
        prompt = body.get("prompt", "Children storybook alive animation")
        duration = float(body.get("duration", 2.5))
        fps = 30
        total_frames = int(duration * fps)

        # 解码 base64
        if "," in raw_image_data:
            header, encoded = raw_image_data.split(",", 1)
        else:
            encoded = raw_image_data

        try:
            img_bytes = base64.b64decode(encoded)
        except Exception as e:
            self.send_json(400, {"ok": False, "error": f"Base64 图片解码失败: {str(e)}"})
            return

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as in_tmp:
            in_tmp.write(img_bytes)
            in_path = in_tmp.name

        out_filename = f"kai_video_{int(time.time()*1000)}.mp4"
        out_path = os.path.join(GENERATED_DIR, out_filename)

        try:
            # 依据 motion 动力学构建 ffmpeg zoompan 时间跨帧动画滤波器
            if motion == "zoom":
                zoom_expr = f"min(zoom+0.002, 1.16)"
                filter_vf = f"scale=640:480,zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x480:fps={fps}"
            elif motion == "sparkle":
                zoom_expr = f"1.0+0.025*sin(2*PI*in/{total_frames})"
                filter_vf = f"scale=640:480,zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x480:fps={fps},eq=brightness=0.03*sin(4*PI*t):saturation=1.15"
            else:  # breathe
                zoom_expr = f"1.0+0.04*sin(2*PI*in/{total_frames})"
                filter_vf = f"scale=640:480,zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+4*sin(2*PI*in/{total_frames})':s=640x480:fps={fps}"

            ffmpeg_bin = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
            cmd = [
                ffmpeg_bin,
                "-y",
                "-loop", "1",
                "-i", in_path,
                "-vf", filter_vf,
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                out_path
            ]
            run_res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
            if run_res.returncode != 0:
                err_log = run_res.stderr.decode("utf-8", errors="ignore")
                self.send_json(500, {"ok": False, "error": f"FFmpeg 编码失败: {err_log[-200:]}"})
                return

            # 读取生成好的视频
            with open(out_path, "rb") as vf:
                v_bytes = vf.read()
                v_b64 = base64.b64encode(v_bytes).decode("utf-8")

            video_url = f"/generated/{out_filename}"
            self.send_json(200, {
                "ok": True,
                "status": "success",
                "message": f"成功以第 1 帧生成 {duration} 秒动态视频！",
                "motion": motion,
                "prompt": prompt,
                "duration": duration,
                "fps": fps,
                "frames": total_frames,
                "video_url": video_url,
                "video_base64": f"data:video/mp4;base64,{v_b64}",
                "authorized_by": auth_msg
            })
        except Exception as ex:
            self.send_json(500, {"ok": False, "error": f"视频生成发生异常: {str(ex)}"})
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)

    def handle_polish(self):
        auth_ok, auth_msg = self.check_auth()
        if not auth_ok:
            self.send_json(401, {"ok": False, "error": f"认证失败: {auth_msg}"})
            return
        body = self.read_json_body() or {}
        img = body.get("image", "")
        style = body.get("style", "crisp_outline")
        prompt = body.get("prompt", "")
        self.send_json(200, {
            "ok": True,
            "status": "success",
            "style": style,
            "prompt": prompt,
            "image": img,
            "message": "Local Polish API received request with valid auth"
        })

if __name__ == "__main__":
    print(f"Starting KaiDraw Prototype & AI Server on http://0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), KaiDrawHandler)
    server.serve_forever()
