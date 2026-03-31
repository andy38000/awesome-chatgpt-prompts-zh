"""
唐卡修复工具 — Gradio Web 界面

提供交互式的唐卡图像修复功能，包括：
- 一键智能修复（综合流水线）
- 裂痕自动检测与修复
- 手动区域修复（画笔标记）
- 颜色恢复与金色增强
- 去噪与平滑
- 对比度与亮度调整
- 边缘增强与锐化
- 污渍去除
"""

import os
import sys

os.environ["GRADIO_SSR_MODE"] = "false"
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import cv2
import numpy as np
import gradio as gr

from restoration import (
    from_rgb, to_rgb, to_cv2,
    analyze_image, smart_restoration,
    dehaze, reduce_yellowing, correct_color_cast, reveal_faded_details,
    multi_scale_inpaint, advanced_damage_repair,
    detect_cracks, inpaint_cracks, auto_repair_cracks, manual_inpaint,
    restore_colors, adaptive_color_restore, auto_white_balance,
    enhance_gold, enhance_red_blue,
    denoise, bilateral_smooth,
    adjust_contrast_brightness, auto_contrast, adaptive_histogram_eq, auto_brightness,
    sharpen, detail_enhance,
    super_clarity, super_clarity_preset,
    remove_stains, remove_yellow_stains,
    full_restoration_pipeline,
)
from paper_algorithms import (
    paper_level_restore,
    edge_guided_inpaint,
    pyramid_inpaint,
    frequency_guided_inpaint,
    multi_direction_propagate,
    symmetric_inpaint,
)

THEME = gr.themes.Soft(
    primary_hue="amber",
    secondary_hue="orange",
    neutral_hue="stone",
    font=gr.themes.GoogleFont("Noto Sans SC"),
)

CSS = """
.gradio-container { max-width: 1200px !important; }
.tab-nav button { font-size: 1.05em !important; }
footer { display: none !important; }
"""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

MAX_PIXELS = 2000

def resize_if_needed(image: np.ndarray) -> np.ndarray:
    """如果图片太大，自动缩放到合理尺寸，避免处理超时。"""
    h, w = image.shape[:2]
    if max(h, w) <= MAX_PIXELS:
        return image
    scale = MAX_PIXELS / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# 回调函数
# ---------------------------------------------------------------------------

def smart_restore_fn(image):
    if image is None:
        return None, ""
    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    info = analyze_image(bgr)
    result = smart_restoration(bgr)

    report = "**图像分析报告：**\n"
    report += f"- 亮度: {info['brightness']:.0f}/255"
    report += f" {'⚠️ 偏暗' if info['is_dark'] else ''}"
    report += f" {'⚠️ 过亮' if info['is_bright'] else ''}\n"
    report += f"- 对比度: {info['contrast']:.0f}"
    report += f" {'⚠️ 对比度低' if info['is_low_contrast'] else ''}\n"
    report += f"- 饱和度: {info['saturation']:.0f}"
    report += f" {'⚠️ 严重褪色' if info.get('is_very_faded') else ('⚠️ 色彩褪色' if info['is_faded'] else '')}\n"
    report += f"- 清晰度: {info['sharpness']:.0f}"
    report += f" {'⚠️ 模糊' if info['is_blurry'] else ''}\n"
    report += f"- 灰蒙程度: {info['haziness']:.0f}"
    report += f" {'⚠️ 有灰蒙层' if info['is_hazy'] else ''}\n"
    report += f"- 泛黄偏移: {info['yellow_bias']:.1f}"
    report += f" {'⚠️ 泛黄' if info['is_yellowed'] else ''}\n"
    report += "\n**已自动执行的修复操作：**\n"
    if info['is_dark']:
        report += "- ✅ 亮度校正（gamma查表，零损失）\n"
    if info.get('is_very_faded'):
        report += "- ✅ 色彩恢复（饱和度+35%）\n"
    elif info['is_faded']:
        report += "- ✅ 色彩恢复（饱和度+20%）\n"
    else:
        report += "- ✅ 色彩微调（饱和度+10%）\n"
    report += "- ✅ **褪色图案显现**（小窗口CLAHE放大局部差异）\n"
    report += "- ✅ 对比度优化（直方图拉伸）\n"
    report += "- ✅ 轻微锐化\n"
    report += "\n*所有操作只做加法增强，绝不丢失任何像素信息*"

    return to_rgb(result), report


def one_click_restore(image, crack_repair, crack_sens, crack_rad,
                      stain_removal,
                      do_dehaze_opt, dehaze_str,
                      do_deyellow_opt, deyellow_str,
                      do_denoise, denoise_str,
                      color_restore, sat, warm,
                      gold_enhance, gold_int,
                      auto_cont, do_sharp, sharp_amt, white_bal):
    if image is None:
        return None
    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    result = full_restoration_pipeline(
        bgr,
        do_crack_repair=crack_repair,
        crack_sensitivity=int(crack_sens),
        crack_radius=int(crack_rad),
        do_stain_removal=stain_removal,
        do_dehaze=do_dehaze_opt,
        dehaze_strength=dehaze_str,
        do_deyellow=do_deyellow_opt,
        deyellow_strength=deyellow_str,
        do_denoise=do_denoise,
        denoise_strength=int(denoise_str),
        do_color_restore=color_restore,
        saturation=sat,
        warmth=warm,
        do_gold_enhance=gold_enhance,
        gold_intensity=gold_int,
        do_auto_contrast=auto_cont,
        do_sharpen=do_sharp,
        sharpen_amount=sharp_amt,
        do_white_balance=white_bal,
    )
    return to_rgb(result)


def crack_detect_fn(image, sensitivity):
    if image is None:
        return None, None
    bgr = from_rgb(image)
    mask = detect_cracks(bgr, int(sensitivity))
    overlay = bgr.copy()
    overlay[mask > 0] = [0, 0, 255]
    return to_rgb(overlay), mask


def crack_repair_fn(image, sensitivity, radius, method):
    if image is None:
        return None
    bgr = from_rgb(image)
    result = auto_repair_cracks(bgr, int(sensitivity), int(radius), method)
    return to_rgb(result)


def manual_inpaint_fn(image, mask_image, radius, method):
    """用户分别上传原图和掩膜图。"""
    if image is None or mask_image is None:
        return None

    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)

    mask_resized = cv2.resize(mask_image, (bgr.shape[1], bgr.shape[0]))

    if len(mask_resized.shape) == 3:
        gray_mask = cv2.cvtColor(mask_resized, cv2.COLOR_RGB2GRAY)
    else:
        gray_mask = mask_resized

    _, binary_mask = cv2.threshold(gray_mask, 30, 255, cv2.THRESH_BINARY)

    result = _dispatch_inpaint(bgr, binary_mask, method, int(radius))
    return to_rgb(result)


def auto_damage_detect_fn(image, threshold):
    """自动检测损伤区域：查找与周围颜色差异大的斑块。"""
    if image is None:
        return None

    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blurred = cv2.medianBlur(gray, 15)
    diff = cv2.absdiff(gray, blurred)

    _, mask = cv2.threshold(diff, int(threshold), 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=1)

    overlay = bgr.copy()
    overlay[mask > 0] = [0, 0, 255]
    blended = cv2.addWeighted(bgr, 0.6, overlay, 0.4, 0)

    return to_rgb(blended)


def auto_damage_repair_fn(image, threshold, radius, method):
    """自动检测损伤并修复。"""
    if image is None:
        return None

    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blurred = cv2.medianBlur(gray, 15)
    diff = cv2.absdiff(gray, blurred)
    _, mask = cv2.threshold(diff, int(threshold), 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=1)

    result = _dispatch_inpaint(bgr, mask, method, int(radius))
    return to_rgb(result)


def _dispatch_inpaint(bgr, mask, method, radius=7):
    """根据方法名路由到对应的修复算法。"""
    if method == "paper_level":
        return paper_level_restore(bgr, mask)
    elif method == "edge_guided":
        return edge_guided_inpaint(bgr, mask)
    elif method == "pyramid":
        return pyramid_inpaint(bgr, mask)
    elif method == "frequency":
        return frequency_guided_inpaint(bgr, mask)
    elif method == "symmetric":
        return symmetric_inpaint(bgr, mask)
    elif method == "multi_scale":
        return advanced_damage_repair(bgr, mask, method="multi_scale")
    else:
        return manual_inpaint(bgr, mask, radius, method)


def color_restore_fn(image, saturation, warmth):
    if image is None:
        return None
    bgr = from_rgb(image)
    result = restore_colors(bgr, saturation, warmth)
    return to_rgb(result)


def white_balance_fn(image):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(auto_white_balance(bgr))


def gold_enhance_fn(image, intensity):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(enhance_gold(bgr, intensity))


def denoise_fn(image, strength):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(denoise(bgr, int(strength)))


def bilateral_fn(image, d, sigma_c, sigma_s):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(bilateral_smooth(bgr, int(d), sigma_c, sigma_s))


def contrast_brightness_fn(image, contrast, brightness):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(adjust_contrast_brightness(bgr, contrast, int(brightness)))


def auto_contrast_fn(image, clip):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(auto_contrast(bgr, clip))


def clahe_fn(image, clip_limit, tile):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(adaptive_histogram_eq(bgr, clip_limit, int(tile)))


def sharpen_fn(image, amount):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(sharpen(bgr, amount))


def super_clarity_fn(image, strength, detail_boost, edge_boost,
                     local_contrast, micro_texture):
    if image is None:
        return None
    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    result = super_clarity(bgr, strength, True, detail_boost,
                           edge_boost, local_contrast, micro_texture)
    return to_rgb(result)


def super_clarity_preset_fn(image, level):
    if image is None:
        return None
    bgr = from_rgb(image)
    bgr = resize_if_needed(bgr)
    result = super_clarity_preset(bgr, level)
    return to_rgb(result)


def detail_fn(image, sigma_s, sigma_r):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(detail_enhance(bgr, sigma_s, sigma_r))


def remove_stain_fn(image, low_r, low_g, low_b, hi_r, hi_g, hi_b, radius):
    if image is None:
        return None
    bgr = from_rgb(image)
    lower = (int(low_b), int(low_g), int(low_r))
    upper = (int(hi_b), int(hi_g), int(hi_r))
    return to_rgb(remove_stains(bgr, lower, upper, int(radius)))


def remove_yellow_fn(image, radius):
    if image is None:
        return None
    bgr = from_rgb(image)
    return to_rgb(remove_yellow_stains(bgr, int(radius)))


# ---------------------------------------------------------------------------
# 界面构建
# ---------------------------------------------------------------------------

def build_app():
    with gr.Blocks() as app:
        gr.Markdown(
            """
            # 🎨 唐卡修复工具
            **数字化修复受损唐卡图像** — 自动分析图像退化情况，智能恢复色彩、清晰度和对比度。
            推荐使用「智能修复」模式，一键获得最佳效果。
            """
        )

        # ==== Tab 0: 智能修复（推荐）====
        with gr.Tab("⭐ 智能修复（推荐）"):
            gr.Markdown(
                "**一键智能修复** — 自动分析图像的亮度、对比度、饱和度和清晰度，"
                "针对性地调整修复参数，无需手动调参。"
            )
            with gr.Row():
                with gr.Column(scale=1):
                    img_smart = gr.Image(label="上传唐卡图片", type="numpy")
                    btn_smart = gr.Button("开始智能修复", variant="primary", size="lg")
                with gr.Column(scale=1):
                    out_smart = gr.Image(label="修复结果", type="numpy")
                    out_report = gr.Markdown(label="分析报告")

            btn_smart.click(smart_restore_fn, [img_smart], [out_smart, out_report])

        # ==== Tab 1: 自定义修复 ====
        with gr.Tab("自定义修复"):
            gr.Markdown("手动调整每个修复步骤的参数。")
            with gr.Row():
                with gr.Column(scale=1):
                    img_oneclick = gr.Image(label="上传唐卡图片", type="numpy")
                    with gr.Accordion("修复选项", open=True):
                        ck_crack = gr.Checkbox(label="裂痕修复（谨慎使用）", value=False)
                        with gr.Row():
                            sl_crack_sens = gr.Slider(10, 80, value=30, step=5, label="裂痕灵敏度")
                            sl_crack_rad = gr.Slider(1, 10, value=3, step=1, label="修复半径")
                        ck_stain = gr.Checkbox(label="去除深色污渍", value=False)
                        gr.Markdown("---")
                        ck_dehaze = gr.Checkbox(label="去灰蒙（轻微去除表面灰层）", value=True)
                        sl_dehaze = gr.Slider(0.1, 0.6, value=0.35, step=0.05, label="去灰蒙强度（唐卡建议0.2-0.4）")
                        ck_deyellow = gr.Checkbox(label="去泛黄（慎用，会改变暖色调）", value=False)
                        sl_deyellow = gr.Slider(0.1, 0.6, value=0.3, step=0.05, label="去泛黄强度（建议0.2-0.3）")
                        gr.Markdown("---")
                        ck_denoise = gr.Checkbox(label="去噪（⚠️会损失笔触细节）", value=False)
                        sl_denoise = gr.Slider(1, 15, value=3, step=1, label="去噪强度（唐卡建议关闭或1-3）")
                        ck_color = gr.Checkbox(label="色彩恢复", value=True)
                        with gr.Row():
                            sl_sat = gr.Slider(0.8, 2.0, value=1.2, step=0.05, label="饱和度")
                            sl_warm = gr.Slider(0.8, 1.3, value=1.0, step=0.05, label="暖色调")
                        ck_gold = gr.Checkbox(label="金色增强", value=True)
                        sl_gold = gr.Slider(0.8, 2.0, value=1.15, step=0.05, label="金色强度")
                        ck_auto_cont = gr.Checkbox(label="自动对比度", value=True)
                        ck_sharp = gr.Checkbox(label="锐化", value=True)
                        sl_sharp = gr.Slider(0.0, 2.0, value=0.5, step=0.1, label="锐化量")
                        ck_wb = gr.Checkbox(label="自动白平衡", value=False)
                    btn_oneclick = gr.Button("开始修复", variant="primary", size="lg")
                with gr.Column(scale=1):
                    out_oneclick = gr.Image(label="修复结果", type="numpy")

            btn_oneclick.click(
                one_click_restore,
                inputs=[img_oneclick, ck_crack, sl_crack_sens, sl_crack_rad,
                        ck_stain,
                        ck_dehaze, sl_dehaze,
                        ck_deyellow, sl_deyellow,
                        ck_denoise, sl_denoise,
                        ck_color, sl_sat, sl_warm,
                        ck_gold, sl_gold,
                        ck_auto_cont, ck_sharp, sl_sharp, ck_wb],
                outputs=out_oneclick,
            )

        # ==== Tab 2: 裂痕修复 ====
        with gr.Tab("裂痕修复"):
            gr.Markdown("自动检测并修复唐卡表面的裂痕与划痕。**建议先点「检测裂痕」预览，确认标记区域合理后再修复。**")
            with gr.Row():
                with gr.Column():
                    img_crack = gr.Image(label="上传唐卡图片", type="numpy")
                    sl_crack_det = gr.Slider(10, 80, value=30, step=5, label="检测灵敏度（越低越保守）")
                    sl_crack_r = gr.Slider(1, 10, value=3, step=1, label="修复半径")
                    dd_crack_m = gr.Dropdown(["telea", "ns"], value="telea", label="修复算法")
                    with gr.Row():
                        btn_detect = gr.Button("检测裂痕")
                        btn_repair = gr.Button("修复裂痕", variant="primary")
                with gr.Column():
                    out_crack_vis = gr.Image(label="裂痕检测结果（红色标记）", type="numpy")
                    out_crack_fix = gr.Image(label="修复结果", type="numpy")

            btn_detect.click(crack_detect_fn, [img_crack, sl_crack_det], [out_crack_vis])
            btn_repair.click(crack_repair_fn, [img_crack, sl_crack_det, sl_crack_r, dd_crack_m], [out_crack_fix])

        # ==== Tab 3: 手动修复 ====
        with gr.Tab("区域修复"):
            gr.Markdown(
                "**两种方式修复局部损伤区域：**\n\n"
                "**方式一（推荐）：自动检测损伤** — 自动找到颜料脱落/污渍区域并修复\n\n"
                "**方式二：手动掩膜** — 用画图软件在图片上涂白色标记损坏区域，分别上传原图和标记图"
            )

            with gr.Accordion("方式一：自动检测损伤区域（推荐）", open=True):
                with gr.Row():
                    with gr.Column():
                        img_auto_dmg = gr.Image(label="上传唐卡图片", type="numpy")
                        sl_dmg_thresh = gr.Slider(5, 60, value=20, step=5,
                                                  label="检测阈值（越低检测越多）")
                        sl_dmg_rad = gr.Slider(1, 20, value=8, step=1, label="修复半径")
                        dd_dmg_m = gr.Dropdown(
                            ["paper_level", "edge_guided", "pyramid", "frequency",
                             "symmetric", "multi_scale", "ns", "telea"],
                            value="paper_level",
                            label="修复算法",
                            info="paper_level=论文综合(最佳) | edge_guided=边缘引导 | pyramid=金字塔 | frequency=频域",
                        )
                        with gr.Row():
                            btn_dmg_detect = gr.Button("检测损伤（预览）")
                            btn_dmg_repair = gr.Button("检测并修复", variant="primary")
                    with gr.Column():
                        out_dmg_preview = gr.Image(label="损伤检测预览（红色=检测到的损伤）", type="numpy")
                        out_dmg_result = gr.Image(label="修复结果", type="numpy")

                btn_dmg_detect.click(auto_damage_detect_fn,
                                     [img_auto_dmg, sl_dmg_thresh],
                                     [out_dmg_preview])
                btn_dmg_repair.click(auto_damage_repair_fn,
                                     [img_auto_dmg, sl_dmg_thresh, sl_dmg_rad, dd_dmg_m],
                                     [out_dmg_result])

            with gr.Accordion("方式二：手动上传掩膜图", open=False):
                gr.Markdown(
                    "1. 用 Windows 画图 / PS / 手机修图 打开唐卡图片\n"
                    "2. 用**白色画笔**涂抹损坏区域\n"
                    "3. 保存这张标记后的图片\n"
                    "4. 在下方分别上传**原图**和**标记图**"
                )
                with gr.Row():
                    with gr.Column():
                        img_manual_orig = gr.Image(label="上传原图", type="numpy")
                        img_manual_mask = gr.Image(label="上传标记图（白色=需要修复的区域）", type="numpy")
                        sl_manual_r = gr.Slider(1, 20, value=8, step=1, label="修复半径")
                        dd_manual_m = gr.Dropdown(
                            ["paper_level", "edge_guided", "pyramid", "frequency",
                             "symmetric", "multi_scale", "ns", "telea"],
                            value="paper_level",
                            label="修复算法（paper_level=论文综合最佳）",
                        )
                        btn_manual = gr.Button("修复标记区域", variant="primary")
                    with gr.Column():
                        out_manual = gr.Image(label="修复结果", type="numpy")

                btn_manual.click(manual_inpaint_fn,
                                 [img_manual_orig, img_manual_mask, sl_manual_r, dd_manual_m],
                                 [out_manual])

        # ==== Tab 4: 颜色恢复 ====
        with gr.Tab("颜色恢复"):
            gr.Markdown("恢复褪色唐卡的色彩，增强金色光泽。")
            with gr.Row():
                with gr.Column():
                    img_color = gr.Image(label="上传唐卡图片", type="numpy")
                    sl_color_sat = gr.Slider(0.5, 3.0, value=1.3, step=0.1, label="饱和度")
                    sl_color_warm = gr.Slider(0.5, 1.5, value=1.0, step=0.05, label="暖色调")
                    btn_color = gr.Button("恢复颜色", variant="primary")
                    gr.Markdown("---")
                    btn_wb = gr.Button("自动白平衡")
                    gr.Markdown("---")
                    sl_gold_int = gr.Slider(0.5, 3.0, value=1.3, step=0.1, label="金色增强强度")
                    btn_gold = gr.Button("金色增强")
                with gr.Column():
                    out_color = gr.Image(label="处理结果", type="numpy")

            btn_color.click(color_restore_fn, [img_color, sl_color_sat, sl_color_warm], [out_color])
            btn_wb.click(white_balance_fn, [img_color], [out_color])
            btn_gold.click(gold_enhance_fn, [img_color, sl_gold_int], [out_color])

        # ==== Tab 5: 去噪平滑 ====
        with gr.Tab("去噪平滑"):
            gr.Markdown("减少图像噪声，平滑唐卡表面。")
            with gr.Row():
                with gr.Column():
                    img_noise = gr.Image(label="上传唐卡图片", type="numpy")
                    sl_noise_str = gr.Slider(1, 30, value=10, step=1, label="去噪强度")
                    btn_denoise = gr.Button("非局部均值去噪", variant="primary")
                    gr.Markdown("---")
                    sl_bi_d = gr.Slider(1, 15, value=9, step=2, label="滤波直径")
                    sl_bi_c = gr.Slider(10, 200, value=75, step=5, label="颜色空间 σ")
                    sl_bi_s = gr.Slider(10, 200, value=75, step=5, label="坐标空间 σ")
                    btn_bilateral = gr.Button("双边滤波")
                with gr.Column():
                    out_noise = gr.Image(label="处理结果", type="numpy")

            btn_denoise.click(denoise_fn, [img_noise, sl_noise_str], [out_noise])
            btn_bilateral.click(bilateral_fn, [img_noise, sl_bi_d, sl_bi_c, sl_bi_s], [out_noise])

        # ==== Tab 6: 对比度调整 ====
        with gr.Tab("对比度调整"):
            gr.Markdown("调整图像对比度与亮度。")
            with gr.Row():
                with gr.Column():
                    img_cont = gr.Image(label="上传唐卡图片", type="numpy")
                    sl_cont = gr.Slider(0.2, 3.0, value=1.0, step=0.1, label="对比度")
                    sl_bright = gr.Slider(-100, 100, value=0, step=5, label="亮度")
                    btn_cont = gr.Button("手动调整", variant="primary")
                    gr.Markdown("---")
                    sl_auto_clip = gr.Slider(0.1, 5.0, value=1.0, step=0.1, label="自动对比度裁剪 %")
                    btn_auto_cont = gr.Button("自动对比度")
                    gr.Markdown("---")
                    sl_clahe_clip = gr.Slider(0.5, 10.0, value=2.0, step=0.5, label="CLAHE 限幅")
                    sl_clahe_tile = gr.Slider(2, 16, value=8, step=2, label="CLAHE 分块大小")
                    btn_clahe = gr.Button("自适应直方图均衡")
                with gr.Column():
                    out_cont = gr.Image(label="处理结果", type="numpy")

            btn_cont.click(contrast_brightness_fn, [img_cont, sl_cont, sl_bright], [out_cont])
            btn_auto_cont.click(auto_contrast_fn, [img_cont, sl_auto_clip], [out_cont])
            btn_clahe.click(clahe_fn, [img_cont, sl_clahe_clip, sl_clahe_tile], [out_cont])

        # ==== Tab 7: 锐化增强 ====
        with gr.Tab("锐化增强"):
            gr.Markdown("增强唐卡中的线条与细节。")
            with gr.Row():
                with gr.Column():
                    img_sharp = gr.Image(label="上传唐卡图片", type="numpy")
                    sl_sharp_amt = gr.Slider(0.1, 5.0, value=1.0, step=0.1, label="锐化量")
                    btn_sharp = gr.Button("锐化", variant="primary")
                    gr.Markdown("---")
                    sl_det_ss = gr.Slider(1, 200, value=10, step=1, label="σ_s（空间）")
                    sl_det_sr = gr.Slider(0.01, 1.0, value=0.15, step=0.01, label="σ_r（范围）")
                    btn_detail = gr.Button("细节增强")
                with gr.Column():
                    out_sharp = gr.Image(label="处理结果", type="numpy")

            btn_sharp.click(sharpen_fn, [img_sharp, sl_sharp_amt], [out_sharp])
            btn_detail.click(detail_fn, [img_sharp, sl_det_ss, sl_det_sr], [out_sharp])

        # ==== Tab: 超级清晰度 ====
        with gr.Tab("🔬 超级清晰度"):
            gr.Markdown(
                "**超级清晰度** — 融合多尺度锐化、高频细节提取、边缘增强和局部对比度增强，"
                "让唐卡的笔触纹理、线条轮廓和颜料细节全部清晰可见。"
            )
            with gr.Row():
                with gr.Column():
                    img_hd = gr.Image(label="上传唐卡图片", type="numpy")
                    gr.Markdown("**快速预设（推荐）**")
                    dd_hd_level = gr.Dropdown(
                        ["轻微", "标准", "强力", "极限"],
                        value="标准",
                        label="清晰度等级",
                    )
                    btn_hd_preset = gr.Button("一键超清", variant="primary", size="lg")
                    gr.Markdown("---")
                    gr.Markdown("**高级参数（手动微调）**")
                    sl_hd_str = gr.Slider(0.1, 2.0, value=1.0, step=0.1, label="总体强度")
                    sl_hd_detail = gr.Slider(0.1, 2.0, value=1.0, step=0.1, label="细节增强")
                    sl_hd_edge = gr.Slider(0.1, 2.0, value=0.8, step=0.1, label="边缘增强")
                    sl_hd_lc = gr.Slider(0.5, 5.0, value=2.5, step=0.5, label="局部对比度")
                    sl_hd_micro = gr.Slider(0.0, 1.5, value=0.6, step=0.1, label="微纹理恢复")
                    btn_hd_custom = gr.Button("自定义超清")
                with gr.Column():
                    out_hd = gr.Image(label="超清结果", type="numpy")

            btn_hd_preset.click(super_clarity_preset_fn, [img_hd, dd_hd_level], [out_hd])
            btn_hd_custom.click(super_clarity_fn,
                                [img_hd, sl_hd_str, sl_hd_detail, sl_hd_edge,
                                 sl_hd_lc, sl_hd_micro], [out_hd])

        # ==== Tab 8: 去污渍 ====
        with gr.Tab("去污渍"):
            gr.Markdown("自动检测并去除唐卡上的深色污渍或泛黄痕迹。")
            with gr.Row():
                with gr.Column():
                    img_stain = gr.Image(label="上传唐卡图片", type="numpy")
                    gr.Markdown("**深色污渍去除**（墨渍、霉斑）")
                    with gr.Row():
                        sl_lo_r = gr.Slider(0, 100, value=0, step=5, label="下限 R")
                        sl_lo_g = gr.Slider(0, 100, value=0, step=5, label="下限 G")
                        sl_lo_b = gr.Slider(0, 100, value=0, step=5, label="下限 B")
                    with gr.Row():
                        sl_hi_r = gr.Slider(0, 200, value=50, step=5, label="上限 R")
                        sl_hi_g = gr.Slider(0, 200, value=50, step=5, label="上限 G")
                        sl_hi_b = gr.Slider(0, 200, value=50, step=5, label="上限 B")
                    sl_stain_r = gr.Slider(1, 20, value=7, step=1, label="修复半径")
                    btn_stain = gr.Button("去除深色污渍", variant="primary")
                    gr.Markdown("---")
                    sl_yellow_r = gr.Slider(1, 20, value=7, step=1, label="修复半径")
                    btn_yellow = gr.Button("去除泛黄污渍")
                with gr.Column():
                    out_stain = gr.Image(label="处理结果", type="numpy")

            btn_stain.click(remove_stain_fn,
                            [img_stain, sl_lo_r, sl_lo_g, sl_lo_b,
                             sl_hi_r, sl_hi_g, sl_hi_b, sl_stain_r],
                            [out_stain])
            btn_yellow.click(remove_yellow_fn, [img_stain, sl_yellow_r], [out_stain])

        # ==== Tab: AI 生成式修复 ====
        with gr.Tab("🤖 AI 修复（唐卡专用模型）"):
            gr.Markdown(
                "## AI 生成式修复\n\n"
                "使用四川大学开源的 **唐卡专用 LoRA 模型** (基于 1376 张专业唐卡训练)，\n"
                "让 AI 理解唐卡绘画风格，智能重绘颜料脱落/损伤区域。\n\n"
                "模型来源: [Wangchuk1376/ThangkaModels](https://huggingface.co/Wangchuk1376/ThangkaModels)\n\n"
                "---\n"
                "### 首次使用安装（只需一次）\n"
                "```\n"
                "pip install diffusers transformers accelerate safetensors huggingface-hub\n"
                "```\n"
                "首次运行会自动下载模型（约 5GB），之后不需要重复下载。\n\n"
                "---\n"
                "### 操作步骤\n"
                "**第 1 步：制作掩膜图**\n"
                "1. 打开 Windows **画图**（或 PS/手机修图 App）\n"
                "2. 打开你的唐卡原图\n"
                "3. 选择 **白色画笔**（粗一点，比如 20px）\n"
                "4. 涂抹所有 **需要 AI 重绘的区域**（颜料脱落、损坏的地方）\n"
                "5. **另存为**一张新图片（这就是掩膜图）\n\n"
                "**第 2 步：上传并修复**\n"
                "1. 在下方 **上传唐卡原图**\n"
                "2. **上传掩膜图**（刚才涂白的那张）\n"
                "3. 选择 **修复类型**（花卉卷草/佛像面部/金色装饰 等）\n"
                "4. 点击 **「开始 AI 修复」**\n"
                "5. 等待 10-30 秒（GPU）或 5-15 分钟（CPU）\n"
                "6. 不满意？换个 **随机种子** 重试，或调高 **推理步数**\n"
            )

            btn_check_sd = gr.Button("检查 AI 修复环境")
            out_sd_status = gr.Markdown("")

            def check_sd_env():
                try:
                    from sd_inpaint import check_sd_available
                    info = check_sd_available()
                    return info["message"]
                except Exception as e:
                    return f"❌ 环境检查失败: {e}\n\n请运行: `pip install diffusers transformers accelerate torch`"

            btn_check_sd.click(check_sd_env, [], [out_sd_status])

            with gr.Row():
                with gr.Column():
                    img_sd = gr.Image(label="上传唐卡原图", type="numpy")
                    img_sd_mask = gr.Image(
                        label="上传掩膜图（白色=需要AI重绘的区域）",
                        type="numpy",
                    )
                    dd_sd_prompt = gr.Dropdown(
                        ["通用修复", "花卉卷草", "佛像面部", "背景天空",
                         "金色装饰", "莲花", "衣物纹饰"],
                        value="通用修复",
                        label="修复类型（选择最接近损伤区域的内容）",
                    )
                    txt_sd_custom = gr.Textbox(
                        label="自定义 Prompt（留空则使用预设）",
                        placeholder="例如: detailed lotus flower with green leaves, thangka painting style",
                        lines=2,
                    )
                    with gr.Row():
                        sl_sd_strength = gr.Slider(
                            0.5, 1.0, value=0.85, step=0.05,
                            label="重绘强度（越大生成内容越多）",
                        )
                        sl_sd_guidance = gr.Slider(
                            5.0, 20.0, value=12.0, step=0.5,
                            label="风格引导（越大越严格遵循描述）",
                        )
                    sl_sd_steps = gr.Slider(
                        10, 50, value=30, step=5,
                        label="推理步数（越多质量越高，越慢）",
                    )
                    sl_sd_seed = gr.Slider(
                        -1, 9999, value=-1, step=1,
                        label="随机种子（-1=随机，固定值可复现结果）",
                    )
                    dd_sd_variant = gr.Dropdown(
                        ["recommended", "detail"],
                        value="recommended",
                        label="LoRA 模型",
                        info="recommended=Status_140(推荐平衡) | detail=ACD_250(更多细节)",
                    )
                    btn_sd = gr.Button("开始 AI 修复", variant="primary", size="lg")
                with gr.Column():
                    out_sd = gr.Image(label="AI 修复结果", type="numpy")

            def sd_repair_fn(image, mask_image, prompt_type, custom_prompt,
                             strength, guidance, steps, seed, variant):
                if image is None:
                    raise gr.Error("请先上传唐卡原图！")
                if mask_image is None:
                    raise gr.Error(
                        "请上传掩膜图！\n"
                        "方法：用 Windows 画图打开原图 → 用白色画笔涂抹损坏区域 → 另存为 → 上传"
                    )
                try:
                    from sd_inpaint import sd_inpaint
                except ImportError:
                    raise gr.Error(
                        "未安装 AI 修复依赖！请在命令行运行：\n"
                        "pip install diffusers transformers accelerate safetensors huggingface-hub"
                    )

                bgr = from_rgb(image)
                bgr = resize_if_needed(bgr)

                mask_resized = cv2.resize(mask_image, (bgr.shape[1], bgr.shape[0]))
                if len(mask_resized.shape) == 3:
                    mask_gray = cv2.cvtColor(mask_resized, cv2.COLOR_RGB2GRAY)
                else:
                    mask_gray = mask_resized
                _, binary = cv2.threshold(mask_gray, 30, 255, cv2.THRESH_BINARY)

                if np.sum(binary > 0) == 0:
                    raise gr.Error("掩膜图中没有检测到白色区域，请确认已用白色涂抹了损坏区域。")

                result = sd_inpaint(
                    bgr, binary,
                    prompt_type=prompt_type,
                    custom_prompt=custom_prompt,
                    strength=strength,
                    guidance_scale=guidance,
                    num_steps=int(steps),
                    seed=int(seed),
                    model_variant=variant,
                )
                return to_rgb(result)

            btn_sd.click(
                sd_repair_fn,
                inputs=[img_sd, img_sd_mask, dd_sd_prompt, txt_sd_custom,
                        sl_sd_strength, sl_sd_guidance, sl_sd_steps, sl_sd_seed,
                        dd_sd_variant],
                outputs=out_sd,
            )

            gr.Markdown(
                """
                ---
                ### 参数建议

                | 损伤类型 | 修复类型 | 重绘强度 | 风格引导 | 步数 |
                |---------|---------|---------|---------|------|
                | 花卉/卷草脱落 | 花卉卷草 | 0.80-0.90 | 12-15 | 30-40 |
                | 佛像面部损伤 | 佛像面部 | 0.75-0.85 | 10-12 | 35-50 |
                | 金线/金色脱落 | 金色装饰 | 0.80-0.90 | 12-15 | 30-40 |
                | 莲花区域损伤 | 莲花 | 0.80-0.90 | 12 | 30 |
                | 衣物褪色 | 衣物纹饰 | 0.85-0.95 | 12-15 | 30-40 |
                | 背景天空损伤 | 背景天空 | 0.85-0.95 | 10-12 | 25-30 |
                | 不确定 | 通用修复 | 0.85 | 12 | 30 |

                ### 技巧
                - 掩膜涂大一点比涂小好（多覆盖一些边缘）
                - 同一区域可以多次修复（把上一次结果作为新原图）
                - 不满意就换 **随机种子**（每个种子生成不同的结果）
                - **推理步数** 越高质量越好，30 步通常够用
                """
            )

        gr.Markdown(
            """
            ---
            **唐卡修复工具** | OpenCV + Stable Diffusion | 适用于唐卡等传统绘画的数字化保护与修复
            """
        )

    return app


def find_free_port(start=7860, end=7880):
    """找到一个未被占用的端口。"""
    import socket
    for p in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
                return p
        except OSError:
            continue
    return None


if __name__ == "__main__":
    import sys

    port = find_free_port()
    if port is None:
        print("错误：端口 7860-7880 全部被占用。")
        print("请先关闭之前的 python 进程，或在任务管理器中结束 python.exe")
        sys.exit(1)

    print("=" * 50)
    print("  唐卡修复工具 正在启动...")
    print(f"  端口: {port}")
    print(f"  地址: http://127.0.0.1:{port}")
    print("=" * 50)

    try:
        app = build_app()
        app.launch(
            server_name="127.0.0.1",
            server_port=port,
            inbrowser=True,
            share=False,
        )
    except Exception as e:
        print(f"\n启动失败: {e}")
        print("\n请尝试以下解决方法:")
        print("1. 打开任务管理器，结束所有 python.exe 进程，然后重试")
        print("2. 运行: pip install \"gradio>=4.0.0,<5.0.0\"")
        sys.exit(1)
