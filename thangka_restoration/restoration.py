"""
唐卡修复核心模块

提供裂痕修复、颜色恢复、去噪、去污渍、边缘增强、对比度调整等功能，
适用于受损唐卡图像的数字化修复。

设计原则：显著提升画面品质，同时保护绘画结构不被破坏。
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance


def to_cv2(image: np.ndarray) -> np.ndarray:
    """确保图像是 BGR uint8 格式（OpenCV 通用格式）。"""
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def to_rgb(image: np.ndarray) -> np.ndarray:
    """BGR -> RGB 用于 Gradio 显示。"""
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def from_rgb(image: np.ndarray) -> np.ndarray:
    """RGB -> BGR 用于 OpenCV 处理。"""
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 0. 智能图像分析
# ---------------------------------------------------------------------------

def analyze_image(image: np.ndarray) -> dict:
    """
    分析图像的退化程度，返回建议的修复参数。
    用于智能修复模式，自动判断该加强哪些方面。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    brightness = np.mean(gray)
    contrast = np.std(gray.astype(np.float32))
    avg_saturation = np.mean(hsv[:, :, 1])
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    is_dark = brightness < 100
    is_bright = brightness > 180
    is_low_contrast = contrast < 40
    is_faded = avg_saturation < 60
    is_blurry = laplacian_var < 100
    is_noisy = laplacian_var > 2000

    return {
        "brightness": brightness,
        "contrast": contrast,
        "saturation": avg_saturation,
        "sharpness": laplacian_var,
        "is_dark": is_dark,
        "is_bright": is_bright,
        "is_low_contrast": is_low_contrast,
        "is_faded": is_faded,
        "is_blurry": is_blurry,
        "is_noisy": is_noisy,
    }


# ---------------------------------------------------------------------------
# 1. 裂痕检测与修复
# ---------------------------------------------------------------------------

def detect_cracks(image: np.ndarray, sensitivity: int = 30) -> np.ndarray:
    """
    针对唐卡优化的裂痕检测。
    用形态学黑帽/白帽变换提取细窄异常线条，通过连通域分析过滤绘画线条。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    kernel_size = max(3, min(15, int(min(h, w) / 200)))
    if kernel_size % 2 == 0:
        kernel_size += 1

    kernel_line = cv2.getStructuringElement(
        cv2.MORPH_RECT, (kernel_size, kernel_size)
    )

    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel_line)
    whitehat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)
    combined = cv2.add(blackhat, whitehat)

    thresh_val = max(5, 60 - sensitivity)
    _, binary = cv2.threshold(combined, thresh_val, 255, cv2.THRESH_BINARY)

    thin_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, thin_kernel, iterations=1)

    mask = np.zeros_like(binary)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    total_pixels = h * w
    max_area = total_pixels * 0.002
    min_area = max(3, total_pixels * 0.000005)

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]

        if area < min_area or area > max_area:
            continue

        aspect = max(comp_w, comp_h) / (min(comp_w, comp_h) + 1e-6)
        compactness = area / (comp_w * comp_h + 1e-6)

        if aspect < 2.0 and compactness > 0.5:
            continue

        mask[labels == i] = 255

    dilate_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    mask = cv2.dilate(mask, dilate_k, iterations=1)

    return mask


def inpaint_cracks(image: np.ndarray, mask: np.ndarray, radius: int = 3,
                   method: str = "telea") -> np.ndarray:
    """使用图像修复算法修复裂痕区域。"""
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    result = cv2.inpaint(image, binary_mask, radius, flag)
    return result


def auto_repair_cracks(image: np.ndarray, sensitivity: int = 30,
                       radius: int = 3, method: str = "telea") -> np.ndarray:
    """自动检测裂痕并修复。"""
    mask = detect_cracks(image, sensitivity)
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 2. 手动区域修复
# ---------------------------------------------------------------------------

def manual_inpaint(image: np.ndarray, mask: np.ndarray,
                   radius: int = 5, method: str = "telea") -> np.ndarray:
    """根据用户手动标记的掩膜区域进行修复。"""
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 3. 颜色恢复与增强
# ---------------------------------------------------------------------------

def restore_colors(image: np.ndarray, saturation: float = 1.4,
                   warmth: float = 1.0) -> np.ndarray:
    """
    恢复唐卡褪色的颜色。
    saturation: 饱和度倍数
    warmth: 暖色调调整
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)

    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)

    if warmth != 1.0:
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] + (warmth - 1.0) * 5, 0, 179)

    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def adaptive_color_restore(image: np.ndarray, target_saturation: float = 90.0) -> np.ndarray:
    """
    自适应颜色恢复：根据当前图像的饱和度自动计算需要的增强倍数，
    把平均饱和度提升到 target_saturation 附近。
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    current_sat = np.mean(hsv[:, :, 1])

    if current_sat < 5:
        return image

    ratio = target_saturation / current_sat
    ratio = np.clip(ratio, 1.0, 2.5)

    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * ratio, 0, 255)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def auto_white_balance(image: np.ndarray) -> np.ndarray:
    """自动白平衡校正（灰度世界假设）。"""
    result = image.astype(np.float32)
    avg_b = np.mean(result[:, :, 0])
    avg_g = np.mean(result[:, :, 1])
    avg_r = np.mean(result[:, :, 2])
    avg_all = (avg_b + avg_g + avg_r) / 3.0

    result[:, :, 0] *= avg_all / (avg_b + 1e-6)
    result[:, :, 1] *= avg_all / (avg_g + 1e-6)
    result[:, :, 2] *= avg_all / (avg_r + 1e-6)

    return np.clip(result, 0, 255).astype(np.uint8)


def enhance_gold(image: np.ndarray, intensity: float = 1.15) -> np.ndarray:
    """增强唐卡中金色区域的光泽。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_gold = np.array([12, 50, 60])
    upper_gold = np.array([38, 255, 255])
    gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    gold_mask = cv2.morphologyEx(gold_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    hsv_float = hsv.astype(np.float32)
    gold_region = gold_mask > 0
    hsv_float[gold_region, 1] = np.clip(hsv_float[gold_region, 1] * intensity, 0, 255)
    hsv_float[gold_region, 2] = np.clip(hsv_float[gold_region, 2] * min(intensity, 1.3), 0, 255)

    return cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)


def enhance_red_blue(image: np.ndarray, intensity: float = 1.3) -> np.ndarray:
    """增强唐卡中常见的红色和蓝色区域。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_float = hsv.astype(np.float32)

    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([179, 255, 255])
    red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    combined = red_mask | blue_mask
    region = combined > 0
    hsv_float[region, 1] = np.clip(hsv_float[region, 1] * intensity, 0, 255)

    return cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)


# ---------------------------------------------------------------------------
# 4. 去噪与平滑
# ---------------------------------------------------------------------------

def denoise(image: np.ndarray, strength: int = 7) -> np.ndarray:
    """非局部均值去噪，保留细节的同时减少噪声。"""
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)


def bilateral_smooth(image: np.ndarray, d: int = 9,
                     sigma_color: float = 50,
                     sigma_space: float = 50) -> np.ndarray:
    """双边滤波平滑，保留边缘的同时平滑表面。"""
    return cv2.bilateralFilter(image, d, sigma_color, sigma_space)


# ---------------------------------------------------------------------------
# 5. 对比度与亮度
# ---------------------------------------------------------------------------

def adjust_contrast_brightness(image: np.ndarray, contrast: float = 1.0,
                               brightness: int = 0) -> np.ndarray:
    """调整对比度和亮度。"""
    result = image.astype(np.float32) * contrast + brightness
    return np.clip(result, 0, 255).astype(np.uint8)


def auto_contrast(image: np.ndarray, clip_percent: float = 1.0) -> np.ndarray:
    """自动对比度拉伸。"""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]

    hist = cv2.calcHist([l_channel], [0], None, [256], [0, 256]).flatten()
    total = l_channel.size
    clip_count = total * clip_percent / 100.0

    cumsum = np.cumsum(hist)
    low = np.searchsorted(cumsum, clip_count)
    high = np.searchsorted(cumsum, total - clip_count)

    if high <= low:
        return image

    scale = 255.0 / (high - low)
    l_channel = np.clip((l_channel.astype(np.float32) - low) * scale, 0, 255).astype(np.uint8)
    lab[:, :, 0] = l_channel

    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def adaptive_histogram_eq(image: np.ndarray, clip_limit: float = 2.0,
                          tile_size: int = 8) -> np.ndarray:
    """自适应直方图均衡化 (CLAHE)，改善局部对比度。"""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                            tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def auto_brightness(image: np.ndarray, target: float = 120.0) -> np.ndarray:
    """自动亮度调整，把平均亮度拉到 target 附近。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    current = np.mean(gray)
    if current < 1:
        return image
    gamma = np.log(target / 255.0) / np.log(current / 255.0 + 1e-6)
    gamma = np.clip(gamma, 0.3, 3.0)
    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(image, table)


# ---------------------------------------------------------------------------
# 6. 边缘增强与锐化
# ---------------------------------------------------------------------------

def sharpen(image: np.ndarray, amount: float = 0.5) -> np.ndarray:
    """非锐化掩膜 (Unsharp Mask) 锐化。"""
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    result = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(result, 0, 255).astype(np.uint8)


def detail_enhance(image: np.ndarray, sigma_s: float = 10,
                   sigma_r: float = 0.15) -> np.ndarray:
    """细节增强，突出唐卡中的线条和纹理。"""
    return cv2.detailEnhance(image, sigma_s=sigma_s, sigma_r=sigma_r)


# ---------------------------------------------------------------------------
# 7. 去污渍
# ---------------------------------------------------------------------------

def remove_stains(image: np.ndarray, lower_thresh: tuple = (0, 0, 0),
                  upper_thresh: tuple = (30, 30, 30),
                  radius: int = 5) -> np.ndarray:
    """检测深色污渍并修复。"""
    lower = np.array(lower_thresh)
    upper = np.array(upper_thresh)
    mask = cv2.inRange(image, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


def remove_yellow_stains(image: np.ndarray, radius: int = 5) -> np.ndarray:
    """去除泛黄污渍。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_yellow = np.array([18, 60, 150])
    upper_yellow = np.array([30, 200, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


# ---------------------------------------------------------------------------
# 8. 综合修复流水线
# ---------------------------------------------------------------------------

def full_restoration_pipeline(
    image: np.ndarray,
    do_crack_repair: bool = False,
    crack_sensitivity: int = 30,
    crack_radius: int = 3,
    do_stain_removal: bool = False,
    do_denoise: bool = True,
    denoise_strength: int = 7,
    do_color_restore: bool = True,
    saturation: float = 1.4,
    warmth: float = 1.0,
    do_gold_enhance: bool = True,
    gold_intensity: float = 1.15,
    do_auto_contrast: bool = True,
    do_sharpen: bool = True,
    sharpen_amount: float = 0.5,
    do_white_balance: bool = False,
) -> np.ndarray:
    """
    一键综合修复流水线。

    默认开启：去噪、色彩恢复、金色增强、自动对比度、锐化。
    """
    result = image.copy()

    if do_crack_repair:
        result = auto_repair_cracks(result, crack_sensitivity, crack_radius)

    if do_stain_removal:
        result = remove_stains(result)

    if do_denoise:
        result = denoise(result, denoise_strength)

    if do_white_balance:
        result = auto_white_balance(result)

    if do_color_restore:
        result = restore_colors(result, saturation, warmth)

    if do_gold_enhance:
        result = enhance_gold(result, gold_intensity)

    if do_auto_contrast:
        result = auto_contrast(result)

    if do_sharpen:
        result = sharpen(result, sharpen_amount)

    return result


def smart_restoration(image: np.ndarray) -> np.ndarray:
    """
    智能修复模式：自动分析图像退化程度，自适应调整修复参数。
    无需手动调参，一键获得最佳修复效果。
    """
    info = analyze_image(image)
    result = image.copy()

    result = denoise(result, 8)

    if info["is_dark"]:
        result = auto_brightness(result, target=125.0)

    if info["is_faded"]:
        result = adaptive_color_restore(result, target_saturation=95.0)
    else:
        result = restore_colors(result, saturation=1.35, warmth=1.0)

    result = enhance_gold(result, intensity=1.15)
    result = enhance_red_blue(result, intensity=1.2)

    if info["is_low_contrast"]:
        result = adaptive_histogram_eq(result, clip_limit=2.5, tile_size=8)
    else:
        result = auto_contrast(result, clip_percent=1.0)

    if info["is_blurry"]:
        result = sharpen(result, amount=0.8)
    else:
        result = sharpen(result, amount=0.5)

    return result
