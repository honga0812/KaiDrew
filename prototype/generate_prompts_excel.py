import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "KaiDraw 3大画种与UI提示词"

# 标题与表头视觉样式
title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
title_font = Font(name="Segoe UI", size=15, bold=True, color="F8FAFC")
header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")

thin_border = Border(
    left=Side(style='thin', color='CBD5E1'),
    right=Side(style='thin', color='CBD5E1'),
    top=Side(style='thin', color='CBD5E1'),
    bottom=Side(style='thin', color='CBD5E1')
)

# 写入主标题
ws.merge_cells("A1:G1")
ws["A1"] = "KaiDraw (KAIquest) - 纯粹3大画种 (水彩/蜡笔/马克笔) 拟物界面与文生图提示词表"
ws["A1"].font = title_font
ws["A1"].fill = title_fill
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 45

# 表头行
headers = [
    "序号 (ID)", 
    "分类 (Category)", 
    "元件名称 (Asset Name)", 
    "界面位置 (UI Location)", 
    "英文文生图提示词 (Prompt for FLUX / SDXL / Midjourney)", 
    "负向提示词 (Negative Prompt)", 
    "格式与应用规范 (Specs & Guidelines)"
]
ws.append(headers)
ws.row_dimensions[2].height = 32

for col_num in range(1, len(headers) + 1):
    cell = ws.cell(row=2, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 纯粹3大画种资产清单 (彻底去除油画)
assets_data = [
    # 1. 品牌与 IP 角色
    ("IP-01", "IP角色", "小探险家 Kai 头像", "顶部品牌导航栏", 
     "cute little explorer artist boy avatar named Kai, wearing a warm yellow artist beret, canvas backpack with paintbrushes sticking out, joyful curious expression, Pixar 3D style, Disney animation character design, clean solid color background, soft studio lighting, octane render, 8k", 
     "ugly, deformed, photorealistic adult, dark, scary, watermark, blurry", 
     "512x512 PNG，透明背景，主头像与系统引导助手"),

    # 2. 输入模式与手掌防误触图标
    ("IN-01", "输入防误触", "仅笔作画 · 手掌防误触图标", "顶部导航控制栏", 
     "isometric 3D icon of a sleek Apple Pencil enclosed inside a glowing protective holographic translucent shield, vibrant amber and golden aura, tech and art fusion, premium minimalist Apple design award style, isolated white background, soft drop shadow, 8k render", 
     "finger, hand, ugly, flat, low quality, noisy, dark background", 
     "512x512 PNG，模式状态按钮：开启手掌防误触与仅手写笔着色"),

    ("IN-02", "输入防误触", "双指画布平移/缩放手势图标", "手掌误触提示与帮助", 
     "isometric 3D icon of two stylized clean hands performing pinch-to-zoom and canvas pan gesture, smooth frosted glass UI arrows, gentle motion trail, minimalist Cupertino aesthetic, pure white background", 
     "messy fingers, dark, dirty, complex anatomy, text", 
     "512x512 PNG，指引手指用于平移/缩放画布"),

    ("IN-03", "输入防误触", "手笔皆可 · 自由模式图标", "顶部导航控制栏", 
     "isometric 3D icon showing a friendly stylized hand and a digital stylus resting side by side in harmony, soft emerald green glow, clean modern UI vector aesthetic, isolated white background", 
     "cluttered, ugly, cartoon childish, lowres", 
     "512x512 PNG，手笔混合模式切换图标"),

    ("IN-04", "输入防误触", "纯手指绘图模式图标", "顶部导航控制栏", 
     "isometric 3D icon of a cute human index finger drawing a vibrant rainbow stroke, playful kid friendly art style, soft lighting, isolated clean background", 
     "sharp pencil, stylus, messy, dark", 
     "512x512 PNG，无手写笔设备纯手指模式"),

    # 3. 三大画笔主图标 (抽屉开关)
    ("BR-01", "画种图标", "清透水彩笔图标", "顶部导航/抽屉开关", 
     "isometric 3D icon of an elegant watercolor mop brush, pointed sable hair with translucent colorful watercolor droplet dripping, crystal clear water splash, clean minimalistic design, Apple design award style, isolated on white background, subtle drop shadow", 
     "crude, rough, dirty, dark, low poly, oil paint", 
     "512x512 PNG，透明背景，水彩画室入口"),

    ("BR-02", "画种图标", "儿童蜡笔图标", "顶部导航/抽屉开关", 
     "isometric 3D icon of a classic colorful wax crayon, paper wrapped with playful zigzag pattern, slightly worn blunt tip, vibrant crayon wax texture, toy-like cute aesthetic, clean isolated background, bright lighting", 
     "pencil, digital pen, broken, sharp, ugly", 
     "512x512 PNG，透明背景，蜡笔画室入口"),

    ("BR-03", "画种图标", "双头马克笔图标", "顶部导航/抽屉开关", 
     "isometric 3D icon of a modern dual-tip alcohol art marker, high quality designer plastic barrel, dual colored caps, sleek chisel and brush nib preview, Copic marker style, premium UI asset, isolated white background", 
     "crayon, paintbrush, wooden, lowres", 
     "512x512 PNG，透明背景，马克笔画室入口"),

    # 4. 真实写实实体画具
    ("TOOL-01", "写实画具", "柯林斯基红貂毛水彩笔实物", "水彩子工具选笔区", 
     "close-up macro photography of a pure Kolinsky red sable watercolor brush, perfectly sharp needle tip, glossy lacquered black handle, gold foil stamping, isolated on white background, studio catalog lighting", 
     "synthetic bristles, frayed tip, dry, dusty", 
     "1024x1024 PNG，水彩勾线与大面积笔刷"),

    ("TOOL-02", "写实画具", "粗头油画棒与圆头儿童蜡笔", "蜡笔子工具选笔区", 
     "macro studio product shot of thick wax oil pastels and crayons, authentic paper wrapping with colorful vintage typography, rich textured wax tip, studio soft lighting, isolated white background", 
     "broken, messy, digital pen, low quality", 
     "1024x1024 PNG，蜡笔质感与笔头选择器"),

    ("TOOL-03", "写实画具", "专业酒精马克笔宽斜切与软毛双笔尖", "马克笔子工具选笔区", 
     "macro studio shot of a high-end dual-head Japanese Copic alcohol marker nibs, left showing broad chisel nib, right showing flexible brush nib with vibrant juicy ink saturation, ultra crisp focus, isolated white background", 
     "dried out, dirty, ballpoint pen, lowres", 
     "1024x1024 PNG，马克笔笔头形态切换"),

    # 5. 调色容器与画具收纳
    ("PL-01", "调色容器", "金属水彩铁盒半块色盘", "水彩画室抽屉", 
     "top-down view of an open black enamel metal watercolor travel tin box, containing 12 vibrant half-pan watercolor cakes, with glossy wet surface, clean studio product photography", 
     "dirty, rusty, digital screen, dry, empty", 
     "1024x768 PNG，水彩工具箱底图"),

    ("PL-02", "调色容器", "复古儿童纸盒蜡笔套组", "蜡笔画室抽屉", 
     "open vintage cardboard crayon box holding 12 colorful wax crayons standing neatly in rows, cheerful children art supplies, tactile paper texture, warm sunlight, clean tabletop view", 
     "messy, broken crayons, digital tablet, adult", 
     "1024x600 PNG，蜡笔抽屉底图"),

    ("PL-03", "调色容器", "专业双头马克笔收纳架", "马克笔画室抽屉", 
     "front view of a modern desk organizer rack holding 12 colorful alcohol markers upright, showing color code labels on caps, clean minimalist industrial design, matte black acrylic stand, studio lighting", 
     "cluttered, pens lying down, low quality", 
     "1024x500 PNG，马克笔选色架底图"),

    ("PL-04", "调色容器", "白瓷流动融合调色盘 (Porcelain Mixing Tray)", "水彩画室抽屉", 
     "top-down macro shot of an elegant pure white porcelain ceramic watercolor mixing tray, smooth glossy white glaze, showing wet flowing translucent puddles of cobalt blue, lemon yellow and lush sap green blending naturally with soft fluid meniscus, studio product photography", 
     "plastic, dirty sludge, dry paint cakes, cracks", 
     "1024x600 PNG，白瓷调色盘底图"),

    # 6. 颜料耗材与色盘
    ("TUB-01", "颜料耗材", "白瓷半块水彩块 (Half-Pan)", "水彩抽屉耗材区", 
     "macro shot of white plastic half-pan watercolor cakes, glowing vibrant concentrated pigment block with glossy wet surface, studio lighting, isolated white background", 
     "chalk, dusty, dry mud, lowres", 
     "512x512 PNG，水彩单色色块"),

    ("COL-01", "选色工具", "彩虹全色域色环与滑块 (Full Spectrum Picker)", "画笔自定调色区", 
     "isometric 3D icon of a minimalist circular spectrum color wheel, continuous vibrant smooth rainbow gradient transition, premium Apple design award aesthetic, pure white background, soft ambient shadow", 
     "pixelated, muddy, complex numbers, dark", 
     "512x512 PNG，全色域选色滑块与色相预览"),

    # 7. 洗笔水桶与水彩工具
    ("WT-01", "洗笔工具", "清澈洗笔木桶/水杯 (满水状态)", "画布快捷悬浮", 
     "cute isometric wooden bucket filled with crystal clear clean water, gentle water ripples, small artist sponge on the rim, drops of clear water, delightful 3D app icon, isolated background", 
     "dirty water, paint mud, skull, realistic metal bucket", 
     "512x512 PNG，第一阶段清澈水状态"),

    ("WT-02", "洗笔工具", "微染洗笔水桶 (稀释状态)", "画布快捷悬浮", 
     "isometric wooden bucket with slightly tinted pastel watercolor inside, soft swirl of light color diluting in water, clean stylized, 3D game asset", 
     "pitch black, sludge, messy", 
     "512x512 PNG，第二阶段浅淡稀释水"),

    ("WT-03", "洗笔工具", "纯净洗净画笔状态", "画布快捷悬浮", 
     "isometric icon of a sparkling clean paintbrush dripping crystal pure water drop, sparkles effect, clean transparent droplet, magical fresh feeling, 3D icon", 
     "stained, paint residue, dry, dark", 
     "512x512 PNG，洗净纯净水状态"),

    ("WT-04", "水彩辅助", "吸水天然海绵 (Natural Sponge)", "水彩画室抽屉", 
     "cute natural artist sea sponge, organic porous porous texture, warm yellow color, gentle drop shadow, 3D tactile icon, isolated background", 
     "kitchen sponge, synthetic green block, flat", 
     "512x512 PNG，吸水海绵图标"),

    ("WT-05", "水彩辅助", "热风吹风机 (Hair Dryer - 吹干画纸)", "水彩画室抽屉", 
     "modern compact matte white artist heat gun or hair dryer, gentle warm wind breeze visual effect, minimalist sleek design, 3D icon, isolated background", 
     "industrial heavy tool, cord, messy", 
     "512x512 PNG，吹干画纸图标"),

    # 8. 4 大专用画纸材质贴图 (可平铺 Seamless Texture)
    ("PP-01", "画纸材质", "传统熟宣纸 / 洒金宣纸", "画布底纸切换", 
     "seamless texture of high quality handmade Chinese Xuan rice paper, delicate visible raw plant fibers, warm ivory tone, subtle gold leaf flakes, fine tactile texture, macro photography, 8k seamless tiling", 
     "canvas cloth, heavy grid, dark, stains, seams, repeating obvious pattern", 
     "2048x2048 Seamless Texture，水墨与工笔底纸"),

    ("PP-02", "画纸材质", "棉絮云彩纸 (Cloud Paper)", "画布底纸切换", 
     "seamless texture of soft pastel cloud paper, swirling organic cloud-like cotton fibers, gentle light cream color, smooth tactile paper surface, subtle micro shadows, 8k seamless tiling", 
     "rough cloth, synthetic, high contrast, scratches", 
     "2048x2048 Seamless Texture，蜡笔与粉彩底纸"),

    ("PP-03", "画纸材质", "细纹色纸 / 暖灰卡纸 (Toned Paper)", "画布底纸切换", 
     "seamless texture of smooth French toned tan paper, warm beige cardboard texture, ultra fine grain, neutral matte background, architectural drawing paper, 8k seamless tiling", 
     "rough weave, stains, crumpled, holes", 
     "2048x2048 Seamless Texture，马克笔与线描底纸"),

    ("PP-04", "画纸材质", "粗纹冷压水彩纸 (Cold Press 300gsm)", "画布底纸切换", 
     "seamless macro texture of heavy 300gsm cold press cotton watercolor paper, random dimples, paper pits, felt texture, unbleached natural white, artistic tooth, 8k seamless tiling", 
     "smooth paper, linen fabric, digital grid, wrinkles", 
     "2048x2048 Seamless Texture，水彩活水扩散纸纹"),

    # 9. 飞梭旋钮与交互控制
    ("CTRL-01", "交互旋钮", "右下角吸附式飞梭轮盘 (Jog Dial)", "画布右下角", 
     "sleek circular metallic jog dial rotary wheel, brushed aluminum bevel, fine knurled tactile grip edge, glowing amber LED tick marks, luxury audio equipment control knob, minimalist Apple aesthetic, isolated white background", 
     "plastic, toy, bulky, dirty, complex numbers", 
     "512x512 PNG，旋转飞梭表盘"),

    # 10. 照片风格化转换与黑白线稿滤镜图标
    ("FLT-00", "风格滤镜", "黑白描边线稿图标 (B&W Sketch Line Art)", "照片转换实验室", 
     "isometric 3D icon of a clean artist sketchbook with delicate graphite pencil contour line drawing and outline tracing, crisp black lines on clean white textured paper, minimalist Scandinavian studio style, isolated pure white background", 
     "colored, paint, messy shading, dark, muddy", 
     "512x512 PNG，黑白草稿描边与填色绘本练习"),

    ("FLT-01", "风格滤镜", "真·水彩水渍晕染滤镜图标", "照片风格化抽屉", 
     "isometric 3D icon of a framed artwork dissolving into delicate translucent watercolor washes and wet edge blooms, vibrant fluid color splashes, isolated pure white background", 
     "solid paint, oil, rough, muddy", 
     "512x512 PNG，水彩滤镜一键转换按钮"),

    ("FLT-02", "风格滤镜", "真·儿童蜡笔颗粒滤镜图标", "照片风格化抽屉", 
     "isometric 3D icon of a picture frame with cheerful textured wax crayon strokes, tactile paper grain texture visible, warm playful childhood charm, isolated white background", 
     "smooth digital gradient, dark, photo", 
     "512x512 PNG，蜡笔滤镜一键转换按钮"),

    ("FLT-03", "风格滤镜", "真·POP 酒精马克笔滤镜图标", "照片风格化抽屉", 
     "isometric 3D icon of a dynamic comic anime frame with crisp ink lineart and vibrant flat alcohol marker shading, sharp pop art style, isolated white background", 
     "messy crayon, washed out watercolor, blurred", 
     "512x512 PNG，马克笔插画滤镜一键转换按钮")
]

for row_idx, data in enumerate(assets_data, start=3):
    ws.append(data)
    ws.row_dimensions[row_idx].height = 48
    for col_idx in range(1, len(data) + 1):
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.border = thin_border
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        if col_idx in [1, 2, 4]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if row_idx % 2 == 0:
            cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

# 设置自适应列宽
col_widths = [12, 16, 26, 20, 62, 36, 36]
for idx, width in enumerate(col_widths, start=1):
    col_letter = get_column_letter(idx)
    ws.column_dimensions[col_letter].width = width

output_path = "/Volumes/4T M2 SSD/AI Native Company OS/Kai_Drew/KaiDraw_UI_Assets_Prompt_Sheet.xlsx"
wb.save(output_path)
print(f"Excel prompt sheet generated successfully at: {output_path}")

proto_output_path = "/Volumes/4T M2 SSD/AI Native Company OS/Kai_Drew/prototype/KaiDraw_UI_Assets_Prompt_Sheet.xlsx"
wb.save(proto_output_path)
print(f"Excel prompt sheet also copied to: {proto_output_path}")
