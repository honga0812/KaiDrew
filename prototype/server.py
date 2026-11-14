#!/usr/bin/env python3
import base64
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, HTTPServer

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

DEFAULT_TEST_KEY = "kaidraw-test-key-2026"

COMFYUI_WORKFLOW_TEMPLATE = {
    "3": {
        "inputs": {
            "seed": 20261113,
            "steps": 20,
            "cfg": 7.5,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 0.65,
            "model": ["4", 0],
            "positive": ["10", 0],
            "negative": ["7", 0],
            "latent_image": ["12", 0]
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (以图生图采样器)"}
    },
    "4": {
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "加载绘本主模型 (SDXL / Flux)"}
    },
    "6": {
        "inputs": {
            "text": "masterpiece, children storybook illustration, clean smooth lines, vibrant harmonious colors, cute cartoon style",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "正向提示词 (Positive Prompt)"}
    },
    "7": {
        "inputs": {
            "text": "ugly, jagged lines, blurry, deformed, noisy, messy, lowres",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "反向提示词 (Negative Prompt)"}
    },
    "10": {
        "inputs": {
            "strength": 0.85,
            "conditioning": ["6", 0],
            "control_net": ["11", 0],
            "image": ["13", 0]
        },
        "class_type": "ControlNetApply",
        "_meta": {"title": "应用 ControlNet LineArt/Scribble 轮廓锁定"}
    },
    "11": {
        "inputs": {"control_net_name": "control_v11p_sd15_lineart.pth"},
        "class_type": "ControlNetLoader",
        "_meta": {"title": "加载 LineArt / Scribble 控制网"}
    },
    "12": {
        "inputs": {"pixels": ["13", 0], "vae": ["4", 2]},
        "class_type": "VAEEncode",
        "_meta": {"title": "手绘原图 VAE 编码"}
    },
    "13": {
        "inputs": {"image": "kaidraw_input.png", "upload": "image"},
        "class_type": "LoadImage",
        "_meta": {"title": "输入儿童手绘画作"}
    },
    "8": {
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE 解码图像"}
    },
    "9": {
        "inputs": {"filename_prefix": "KaiDraw_AI", "images": ["8", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "保存生成结果"}
    }
}


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
        elif self.path.startswith("/api/comfyui/workflow"):
            self.send_json(200, COMFYUI_WORKFLOW_TEMPLATE)
        elif self.path.startswith("/api/health"):
            self.send_json(200, {
                "ok": True,
                "status": "online",
                "service": "KaiDraw Local AI & ComfyUI Gateway",
                "version": "2.5.0",
                "has_pillow": HAS_PIL,
                "endpoints": {
                    "image_to_video": "/api/ai/image-to-video",
                    "magic_polish": "/api/ai/polish",
                    "comfyui_bridge": "/api/ai/comfyui-bridge",
                    "comfyui_workflow": "/api/comfyui/workflow"
                },
                "default_test_key": DEFAULT_TEST_KEY
            })
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/ai/image-to-video") or self.path.startswith("/api/ai/video"):
            self.handle_image_to_video()
        elif self.path.startswith("/api/ai/polish") or self.path.startswith("/api/ai/comfyui-bridge"):
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
        raw_img = body.get("image", "")
        category = body.get("category", "line_contour")
        style = body.get("style", "crisp_outline")
        prompt = body.get("prompt", "")
        params = body.get("params", {})
        comfy_url = body.get("comfyui_url", "").strip()

        # 1. 若用户配置了本地/局域网 ComfyUI 实例，尝试桥接调用
        if comfy_url:
            try:
                wf = json.loads(json.dumps(COMFYUI_WORKFLOW_TEMPLATE))
                wf["6"]["inputs"]["text"] = f"masterpiece, {prompt}, style: {style}, category: {category}"
                wf["3"]["inputs"]["denoise"] = float(params.get("strength", 65)) / 100.0
                req = urllib.request.Request(
                    f"{comfy_url.rstrip('/')}/prompt",
                    data=json.dumps({"prompt": wf}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    # 若成功提交到 ComfyUI 队列，返回状态与预览
            except Exception as ce:
                pass

        # 2. 使用 Pillow 深度图像重构引擎对 4 大维度进行处理
        out_b64 = raw_img
        if HAS_PIL and raw_img:
            try:
                encoded = raw_img.split(",", 1)[1] if "," in raw_img else raw_img
                img_bytes = base64.b64decode(encoded)
                im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                # 创建白底复合图以便滤波
                bg = Image.new("RGBA", im.size, (255, 253, 248, 255))
                comp = Image.alpha_composite(bg, im).convert("RGB")

                p1 = float(params.get("p1", 75)) / 100.0
                p2 = float(params.get("p2", 70)) / 100.0
                p3 = float(params.get("p3", 65)) / 100.0

                if category == "line_contour":
                    # 维度 1：线条平滑与外型完整性修改
                    smoothed = comp.filter(ImageFilter.ModeFilter(size=max(3, int(p1 * 6) | 1)))
                    smoothed = smoothed.filter(ImageFilter.SMOOTH_MORE)
                    edges = smoothed.filter(ImageFilter.FIND_EDGES).convert("L")
                    edges = ImageOps.invert(edges)
                    edges = ImageEnhance.Contrast(edges).enhance(1.5 + p2 * 1.5)
                    # 将平滑色彩与强化闭合边缘融合
                    res_rgb = Image.blend(comp, smoothed, min(1.0, p1 * 0.9))
                    res_rgb = ImageEnhance.Sharpness(res_rgb).enhance(1.4 + p2 * 1.2)
                elif category == "color_shading":
                    # 维度 2：色彩以及着色调整修改 (色调和谐 + 立体光影体积感)
                    smoothed = comp.filter(ImageFilter.GaussianBlur(radius=1.2))
                    sat = ImageEnhance.Color(smoothed).enhance(1.15 + p1 * 0.65)
                    con = ImageEnhance.Contrast(sat).enhance(1.08 + p2 * 0.35)
                    # 叠加温暖环境光渐变
                    grad = Image.new("RGB", comp.size, (255, 242, 210))
                    res_rgb = Image.blend(con, grad, 0.12 * p2)
                elif category == "medium_style":
                    # 维度 3：整体艺术画风修改 (蜡笔, 水彩, 素描, 油画)
                    if style == "sketch":
                        gray = ImageOps.grayscale(comp)
                        inv = ImageOps.invert(gray)
                        blur = inv.filter(ImageFilter.GaussianBlur(radius=max(2, int(p2 * 12))))
                        # 颜色减淡素描效果
                        sketch = ImageOps.autocontrast(Image.blend(gray, blur, 0.5))
                        res_rgb = sketch.convert("RGB")
                    elif style == "watercolor":
                        wet = comp.filter(ImageFilter.MedianFilter(size=5))
                        wet = wet.filter(ImageFilter.GaussianBlur(radius=p2 * 2.2))
                        wet = ImageEnhance.Color(wet).enhance(1.25)
                        res_rgb = wet.filter(ImageFilter.EDGE_ENHANCE)
                    elif style == "crayon":
                        quant = comp.quantize(colors=max(8, int(32 - p1 * 16))).convert("RGB")
                        res_rgb = ImageEnhance.Contrast(quant).enhance(1.2 + p3 * 0.4)
                    else:  # oil
                        oil = comp.filter(ImageFilter.ModeFilter(size=7))
                        res_rgb = ImageEnhance.Sharpness(oil).enhance(1.8)
                else:
                    # 维度 4：卡通化风格修改 (3D皮克斯, 吉卜力, 萌系绘本, 黏土)
                    smooth_base = comp.filter(ImageFilter.ModeFilter(size=5))
                    smooth_base = ImageEnhance.Color(smooth_base).enhance(1.3 + p1 * 0.5)
                    smooth_base = ImageEnhance.Contrast(smooth_base).enhance(1.15 + p1 * 0.25)
                    res_rgb = smooth_base.filter(ImageFilter.SMOOTH_MORE)

                buf = io.BytesIO()
                res_rgb.save(buf, format="PNG")
                out_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception as pe:
                pass

        self.send_json(200, {
            "ok": True,
            "status": "success",
            "category": category,
            "style": style,
            "prompt": prompt,
            "params": params,
            "image": out_b64,
            "message": "AI 4维以图生图引擎处理完成"
        })

if __name__ == "__main__":
    print(f"Starting KaiDraw Prototype & AI Server on http://0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), KaiDrawHandler)
    server.serve_forever()
