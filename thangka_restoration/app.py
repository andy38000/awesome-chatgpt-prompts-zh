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

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import cv2
import numpy as np
import gradio as gr

from restoration import (
    from_rgb, to_rgb, to_cv2,
    analyze_image, smart_restoration,
    detect_cracks, inpaint_cracks, auto_repair_cracks, manual_inpaint,
    restore_colors, adaptive_color_restore, auto_white_balance,
    enhance_gold, enhance_red_blue,
    denoise, bilateral_smooth,
    adjust_contrast_brightness, auto_contrast, adaptive_histogram_eq, auto_brightness,
    sharpen, detail_enhance,
    remove_stains, remove_yellow_stains,
    full_restoration_pipeline,
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
# 回调函数
# ---------------------------------------------------------------------------

def smart_restore_fn(image):
    if image is None:
        return None, ""
    bgr = from_rgb(image)
    info = analyze_image(bgr)
    result = smart_restoration(bgr)

    report = "**图像分析报告：**\n"
    report += f"- 亮度: {info['brightness']:.0f}/255"
    report += f" {'⚠️ 偏暗' if info['is_dark'] else ''}"
    report += f" {'⚠️ 过亮' if info['is_bright'] else ''}\n"
    report += f"- 对比度: {info['contrast']:.0f}"
    report += f" {'⚠️ 对比度低' if info['is_low_contrast'] else ''}\n"
    report += f"- 饱和度: {info['saturation']:.0f}"
    report += f" {'⚠️ 色彩褪色' if info['is_faded'] else ''}\n"
    report += f"- 清晰度: {info['sharpness']:.0f}"
    report += f" {'⚠️ 模糊' if info['is_blurry'] else ''}"
    report += f" {'⚠️ 噪点多' if info['is_noisy'] else ''}\n"
    report += "\n**已自动执行的修复操作：**\n"
    report += "- ✅ 去噪\n"
    if info['is_dark']:
        report += "- ✅ 亮度提升\n"
    if info['is_faded']:
        report += "- ✅ 自适应色彩恢复（强力）\n"
    else:
        report += "- ✅ 色彩增强\n"
    report += "- ✅ 金色光泽增强\n"
    report += "- ✅ 红蓝色增强\n"
    if info['is_low_contrast']:
        report += "- ✅ CLAHE 自适应对比度（强力）\n"
    else:
        report += "- ✅ 自动对比度\n"
    if info['is_blurry']:
        report += "- ✅ 锐化增强（强力）\n"
    else:
        report += "- ✅ 锐化增强\n"

    return to_rgb(result), report


def one_click_restore(image, crack_repair, crack_sens, crack_rad,
                      stain_removal, do_denoise, denoise_str,
                      color_restore, sat, warm,
                      gold_enhance, gold_int,
                      auto_cont, do_sharp, sharp_amt, white_bal):
    if image is None:
        return None
    bgr = from_rgb(image)
    result = full_restoration_pipeline(
        bgr,
        do_crack_repair=crack_repair,
        crack_sensitivity=int(crack_sens),
        crack_radius=int(crack_rad),
        do_stain_removal=stain_removal,
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


def manual_inpaint_fn(editor_data, radius, method):
    if editor_data is None:
        return None

    composite = editor_data.get("composite", None)
    layers = editor_data.get("layers", [])

    if composite is None:
        return None

    bg = editor_data.get("background", composite)
    bgr = from_rgb(bg)

    if layers and len(layers) > 0:
        layer = layers[0]
        if len(layer.shape) == 3 and layer.shape[2] == 4:
            mask = layer[:, :, 3]
        else:
            mask = cv2.cvtColor(layer, cv2.COLOR_RGB2GRAY)
    else:
        gray_comp = cv2.cvtColor(composite, cv2.COLOR_RGB2GRAY)
        gray_bg = cv2.cvtColor(bg, cv2.COLOR_RGB2GRAY)
        mask = cv2.absdiff(gray_comp, gray_bg)
        _, mask = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY)

    result = manual_inpaint(bgr, mask, int(radius), method)
    return to_rgb(result)


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
                        ck_denoise = gr.Checkbox(label="去噪", value=True)
                        sl_denoise = gr.Slider(1, 20, value=7, step=1, label="去噪强度")
                        ck_color = gr.Checkbox(label="色彩恢复", value=True)
                        with gr.Row():
                            sl_sat = gr.Slider(0.8, 2.5, value=1.4, step=0.05, label="饱和度")
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
                        ck_stain, ck_denoise, sl_denoise,
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
        with gr.Tab("手动区域修复"):
            gr.Markdown("使用画笔在图片上标记需要修复的区域，然后点击修复。")
            with gr.Row():
                with gr.Column():
                    img_manual = gr.ImageEditor(
                        label="在图片上标记损坏区域（使用画笔工具）",
                        type="numpy",
                        brush=gr.Brush(default_size=15, colors=["#FF0000"]),
                    )
                    sl_manual_r = gr.Slider(1, 20, value=7, step=1, label="修复半径")
                    dd_manual_m = gr.Dropdown(["telea", "ns"], value="telea", label="修复算法")
                    btn_manual = gr.Button("修复标记区域", variant="primary")
                with gr.Column():
                    out_manual = gr.Image(label="修复结果", type="numpy")

            btn_manual.click(manual_inpaint_fn, [img_manual, sl_manual_r, dd_manual_m], [out_manual])

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

        gr.Markdown(
            """
            ---
            **唐卡修复工具** | 基于 OpenCV 图像处理技术 | 适用于唐卡等传统绘画的数字化保护与修复
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
            ssr_mode=False,
        )
    except Exception as e:
        print(f"\n启动失败: {e}")
        print("\n请尝试以下解决方法:")
        print("1. 打开任务管理器，结束所有 python.exe 进程，然后重试")
        print("2. 确认已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
