"""
唐卡修复核心模块

提供裂痕修复、颜色恢复、去噪、去污渍、边缘增强、对比度调整等功能，
适用于受损唐卡图像的数字化修复。

设计原则：保守修复，宁可少修也不要破坏原画。
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
# 1. 裂痕检测与修复
# ---------------------------------------------------------------------------

def detect_cracks(image: np.ndarray, sensitivity: int = 30) -> np.ndarray:
    """
    针对唐卡优化的裂痕检测。

    核心思路：真正的裂痕是穿越不同颜色区域的细窄亮线/暗线，
    而绘画线条是构成图案的有意笔触。通过以下策略区分：
    1. 用形态学黑帽/白帽变换提取比周围亮或暗的细线
    2. 只保留细长结构（高长宽比），过滤掉大块区域
    3. 过滤掉太大的连通区域（那是绘画本身的线条）

    sensitivity: 1-100，越大检测越多（但也越容易误伤）
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
    """
    使用图像修复算法修复裂痕区域。
    method: "telea" (快速行进法) 或 "ns" (Navier-Stokes)
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    result = cv2.inpaint(image, binary_mask, radius, flag)
    return result


def auto_repair_cracks(image: np.ndarray, sensitivity: int = 30,
                       radius: int = 3, method: str = "telea") -> np.ndarray:
    """自动检测裂痕并修复（一步完成）。"""
    mask = detect_cracks(image, sensitivity)
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 2. 手动区域修复（基于用户绘制的掩膜）
# ---------------------------------------------------------------------------

def manual_inpaint(image: np.ndarray, mask: np.ndarray,
                   radius: int = 5, method: str = "telea") -> np.ndarray:
    """根据用户手动标记的掩膜区域进行修复。"""
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 3. 颜色恢复与增强
# ---------------------------------------------------------------------------

def restore_colors(image: np.ndarray, saturation: float = 1.15,
                   warmth: float = 1.0) -> np.ndarray:
    """
    恢复唐卡褪色的颜色。
    saturation: 饱和度倍数 (>1 增加, <1 减少)
    warmth: 暖色调调整 (>1 偏暖, <1 偏冷)
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)

    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)

    if warmth != 1.0:
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] + (warmth - 1.0) * 3, 0, 179)

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


def enhance_gold(image: np.ndarray, intensity: float = 1.2) -> np.ndarray:
    """
    增强唐卡中金色区域的光泽。
    通过在 HSV 空间中定位金色/黄色调并增强亮度实现。
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_gold = np.array([15, 80, 80])
    upper_gold = np.array([35, 255, 255])
    gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)

    hsv_float = hsv.astype(np.float32)
    gold_region = gold_mask > 0
    hsv_float[gold_region, 1] = np.clip(hsv_float[gold_region, 1] * intensity, 0, 255)
    hsv_float[gold_region, 2] = np.clip(hsv_float[gold_region, 2] * intensity, 0, 255)

    return cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)


# ---------------------------------------------------------------------------
# 4. 去噪与平滑
# ---------------------------------------------------------------------------

def denoise(image: np.ndarray, strength: int = 5) -> np.ndarray:
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


def auto_contrast(image: np.ndarray, clip_percent: float = 0.5) -> np.ndarray:
    """
    自动对比度拉伸（直方图裁剪）。
    clip_percent: 裁剪百分比，越大拉伸越强。
    """
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


def adaptive_histogram_eq(image: np.ndarray, clip_limit: float = 1.5,
                          tile_size: int = 8) -> np.ndarray:
    """自适应直方图均衡化 (CLAHE)，改善局部对比度。"""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                            tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


# ---------------------------------------------------------------------------
# 6. 边缘增强与锐化
# ---------------------------------------------------------------------------

def sharpen(image: np.ndarray, amount: float = 0.3) -> np.ndarray:
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
    """
    通过颜色阈值检测深色污渍并修复。
    适用于墨渍、霉斑等深色污损。
    """
    lower = np.array(lower_thresh)
    upper = np.array(upper_thresh)
    mask = cv2.inRange(image, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


def remove_yellow_stains(image: np.ndarray, radius: int = 5) -> np.ndarray:
    """去除泛黄污渍（常见于老旧唐卡）。"""
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
    denoise_strength: int = 5,
    do_color_restore: bool = True,
    saturation: float = 1.15,
    warmth: float = 1.0,
    do_gold_enhance: bool = False,
    gold_intensity: float = 1.2,
    do_auto_contrast: bool = True,
    do_sharpen: bool = True,
    sharpen_amount: float = 0.3,
    do_white_balance: bool = False,
) -> np.ndarray:
    """
    一键综合修复流水线。
    按合理顺序依次执行选定的修复步骤。

    默认配置偏保守：只做轻微去噪、色彩微调、对比度优化和轻度锐化。
    裂痕修复和污渍去除默认关闭，需要用户明确开启。
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
