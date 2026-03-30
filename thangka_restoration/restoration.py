"""
唐卡修复核心模块

核心思路：老旧唐卡的主要退化不是"参数偏了"，而是：
1. 表面积灰/氧化形成灰蒙层 → 用去雾算法去除
2. 颜料氧化泛黄 → 色偏校正
3. 色彩褪色 → 多层次自适应饱和度恢复
4. 对比度下降 → 分区域自适应增强
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance


def to_cv2(image: np.ndarray) -> np.ndarray:
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def to_rgb(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def from_rgb(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 0. 智能图像分析
# ---------------------------------------------------------------------------

def analyze_image(image: np.ndarray) -> dict:
    """分析图像退化程度。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    brightness = np.mean(gray)
    contrast = np.std(gray.astype(np.float32))
    avg_saturation = np.mean(hsv[:, :, 1])
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    b_mean = np.mean(image[:, :, 0].astype(np.float32))
    g_mean = np.mean(image[:, :, 1].astype(np.float32))
    r_mean = np.mean(image[:, :, 2].astype(np.float32))
    yellow_bias = (r_mean + g_mean) / 2 - b_mean

    a_channel = lab[:, :, 1].astype(np.float32) - 128
    b_channel = lab[:, :, 2].astype(np.float32) - 128
    color_cast_a = np.mean(a_channel)
    color_cast_b = np.mean(b_channel)

    dark_channel = _get_dark_channel(image, 15)
    haziness = np.mean(dark_channel)

    return {
        "brightness": float(brightness),
        "contrast": float(contrast),
        "saturation": float(avg_saturation),
        "sharpness": float(laplacian_var),
        "yellow_bias": float(yellow_bias),
        "color_cast_a": float(color_cast_a),
        "color_cast_b": float(color_cast_b),
        "haziness": float(haziness),
        "is_dark": brightness < 100,
        "is_bright": brightness > 180,
        "is_low_contrast": contrast < 45,
        "is_faded": avg_saturation < 70,
        "is_very_faded": avg_saturation < 40,
        "is_blurry": laplacian_var < 200,
        "is_noisy": laplacian_var > 3000,
        "is_yellowed": yellow_bias > 15,
        "is_hazy": haziness > 40,
    }


# ---------------------------------------------------------------------------
# 1. 去雾 / 去灰蒙 (Dark Channel Prior)
# ---------------------------------------------------------------------------

def _get_dark_channel(image: np.ndarray, patch_size: int = 15) -> np.ndarray:
    """计算暗通道。"""
    min_channel = np.min(image, axis=2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch_size, patch_size))
    dark = cv2.erode(min_channel, kernel)
    return dark


def _estimate_atmospheric_light(image: np.ndarray, dark_channel: np.ndarray) -> np.ndarray:
    """估算大气光照值（灰蒙层的颜色）。"""
    h, w = dark_channel.shape
    num_pixels = h * w
    top_count = max(int(num_pixels * 0.001), 1)

    flat_dark = dark_channel.ravel()
    indices = np.argsort(flat_dark)[-top_count:]

    flat_image = image.reshape(-1, 3)
    brightest = flat_image[indices]
    atmospheric = np.mean(brightest, axis=0)
    return atmospheric


def dehaze(image: np.ndarray, strength: float = 0.7) -> np.ndarray:
    """
    基于暗通道先验的去雾算法。
    对于老旧唐卡，表面积灰和氧化层相当于"雾"。
    strength: 0-1，去雾强度。0.7 是一个自然的值。
    """
    img_float = image.astype(np.float64) / 255.0
    dark = _get_dark_channel(image, 15)
    atmospheric = _estimate_atmospheric_light(image, dark) / 255.0

    omega = np.clip(strength, 0.1, 0.95)
    norm_img = img_float / (atmospheric + 1e-6)
    dark_norm = _get_dark_channel((norm_img * 255).astype(np.uint8), 15) / 255.0
    transmission = 1.0 - omega * dark_norm
    transmission = np.clip(transmission, 0.1, 1.0)

    transmission = cv2.GaussianBlur(transmission, (0, 0), sigmaX=40)

    result = np.zeros_like(img_float)
    for c in range(3):
        result[:, :, c] = (img_float[:, :, c] - atmospheric[c]) / (transmission + 1e-6) + atmospheric[c]

    result = np.clip(result * 255, 0, 255).astype(np.uint8)
    return result


# ---------------------------------------------------------------------------
# 2. 色偏校正 / 去黄
# ---------------------------------------------------------------------------

def correct_color_cast(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    自动色偏校正。
    分析LAB空间中的a/b通道偏移，将其拉回中性。
    对老旧唐卡的泛黄特别有效。
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)

    a_mean = np.mean(lab[:, :, 1]) - 128
    b_mean = np.mean(lab[:, :, 2]) - 128

    lab[:, :, 1] -= a_mean * strength
    lab[:, :, 2] -= b_mean * strength

    lab = np.clip(lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def reduce_yellowing(image: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """
    专门针对泛黄的校正。
    只减少LAB空间中b通道的正偏移（黄色方向），保留其他色彩。
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)

    b_mean = np.mean(lab[:, :, 2]) - 128
    if b_mean > 0:
        lab[:, :, 2] -= b_mean * strength

    lab = np.clip(lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


# ---------------------------------------------------------------------------
# 3. 裂痕检测与修复
# ---------------------------------------------------------------------------

def detect_cracks(image: np.ndarray, sensitivity: int = 30) -> np.ndarray:
    """针对唐卡优化的裂痕检测。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    kernel_size = max(3, min(15, int(min(h, w) / 200)))
    if kernel_size % 2 == 0:
        kernel_size += 1

    kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel_line)
    whitehat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)
    combined = cv2.add(blackhat, whitehat)

    thresh_val = max(5, 60 - sensitivity)
    _, binary = cv2.threshold(combined, thresh_val, 255, cv2.THRESH_BINARY)

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
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    return cv2.inpaint(image, binary_mask, radius, flag)


def auto_repair_cracks(image: np.ndarray, sensitivity: int = 30,
                       radius: int = 3, method: str = "telea") -> np.ndarray:
    mask = detect_cracks(image, sensitivity)
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 4. 手动区域修复
# ---------------------------------------------------------------------------

def manual_inpaint(image: np.ndarray, mask: np.ndarray,
                   radius: int = 5, method: str = "telea") -> np.ndarray:
    return inpaint_cracks(image, mask, radius, method)


# ---------------------------------------------------------------------------
# 5. 颜色恢复与增强
# ---------------------------------------------------------------------------

def restore_colors(image: np.ndarray, saturation: float = 1.4,
                   warmth: float = 1.0) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
    if warmth != 1.0:
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] + (warmth - 1.0) * 5, 0, 179)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def adaptive_color_restore(image: np.ndarray, target_saturation: float = 100.0) -> np.ndarray:
    """自适应颜色恢复：自动计算增强倍数。"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    current_sat = np.mean(hsv[:, :, 1])
    if current_sat < 5:
        return image

    ratio = target_saturation / current_sat
    ratio = np.clip(ratio, 1.0, 3.0)

    s = hsv[:, :, 1]
    hsv[:, :, 1] = np.clip(s * ratio, 0, 255)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def auto_white_balance(image: np.ndarray) -> np.ndarray:
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
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_gold = np.array([12, 50, 60])
    upper_gold = np.array([38, 255, 255])
    gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    gold_mask = cv2.morphologyEx(gold_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    hsv_float = hsv.astype(np.float32)
    gold_region = gold_mask > 0
    hsv_float[gold_region, 1] = np.clip(hsv_float[gold_region, 1] * intensity, 0, 255)
    hsv_float[gold_region, 2] = np.clip(hsv_float[gold_region, 2] * min(intensity, 1.2), 0, 255)
    return cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)


def enhance_red_blue(image: np.ndarray, intensity: float = 1.3) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_float = hsv.astype(np.float32)

    red_mask = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])) | \
               cv2.inRange(hsv, np.array([160, 50, 50]), np.array([179, 255, 255]))
    blue_mask = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([130, 255, 255]))

    region = (red_mask | blue_mask) > 0
    hsv_float[region, 1] = np.clip(hsv_float[region, 1] * intensity, 0, 255)
    return cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)


# ---------------------------------------------------------------------------
# 6. 去噪与平滑
# ---------------------------------------------------------------------------

def denoise(image: np.ndarray, strength: int = 7) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)


def bilateral_smooth(image: np.ndarray, d: int = 9,
                     sigma_color: float = 50,
                     sigma_space: float = 50) -> np.ndarray:
    return cv2.bilateralFilter(image, d, sigma_color, sigma_space)


# ---------------------------------------------------------------------------
# 7. 对比度与亮度
# ---------------------------------------------------------------------------

def adjust_contrast_brightness(image: np.ndarray, contrast: float = 1.0,
                               brightness: int = 0) -> np.ndarray:
    result = image.astype(np.float32) * contrast + brightness
    return np.clip(result, 0, 255).astype(np.uint8)


def auto_contrast(image: np.ndarray, clip_percent: float = 1.0) -> np.ndarray:
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
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def auto_brightness(image: np.ndarray, target: float = 125.0) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    current = np.mean(gray)
    if current < 1:
        return image
    gamma = np.log(target / 255.0) / np.log(current / 255.0 + 1e-6)
    gamma = np.clip(gamma, 0.3, 3.0)
    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(image, table)


# ---------------------------------------------------------------------------
# 8. 边缘增强与锐化
# ---------------------------------------------------------------------------

def sharpen(image: np.ndarray, amount: float = 0.5) -> np.ndarray:
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    result = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(result, 0, 255).astype(np.uint8)


def detail_enhance(image: np.ndarray, sigma_s: float = 10,
                   sigma_r: float = 0.15) -> np.ndarray:
    return cv2.detailEnhance(image, sigma_s=sigma_s, sigma_r=sigma_r)


# ---------------------------------------------------------------------------
# 8.5 超级清晰度 (Super Clarity)
# ---------------------------------------------------------------------------

def _multi_scale_unsharp(image: np.ndarray,
                         scales: list = None,
                         weights: list = None) -> np.ndarray:
    """
    多尺度非锐化掩膜：在不同模糊半径上分别提取细节并叠加。
    小尺度恢复纹理（笔触纤维），大尺度恢复结构（线条轮廓）。
    """
    if scales is None:
        scales = [1, 3, 7]
    if weights is None:
        weights = [0.5, 0.3, 0.2]

    img_f = image.astype(np.float64)
    detail_sum = np.zeros_like(img_f)

    for sigma, w in zip(scales, weights):
        blurred = cv2.GaussianBlur(img_f, (0, 0), sigma)
        detail = img_f - blurred
        detail_sum += detail * w

    return detail_sum


def _high_frequency_boost(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    高频提升滤波：用拉普拉斯算子提取高频分量（边缘/纹理），
    然后将其按比例加回原图。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)

    lap_3ch = cv2.merge([lap, lap, lap])
    result = image.astype(np.float64) + lap_3ch * strength
    return np.clip(result, 0, 255).astype(np.uint8)


def _guided_filter(image: np.ndarray, radius: int = 8,
                   eps: float = 0.01) -> np.ndarray:
    """
    引导滤波：在平滑噪声的同时精确保留边缘。
    用作清晰度增强前的预处理，去除噪声但保留结构。
    """
    img_f = image.astype(np.float64) / 255.0
    result = np.zeros_like(img_f)

    for c in range(3):
        I = img_f[:, :, c]
        mean_I = cv2.boxFilter(I, -1, (radius, radius))
        mean_II = cv2.boxFilter(I * I, -1, (radius, radius))
        var_I = mean_II - mean_I * mean_I

        a = var_I / (var_I + eps)
        b = mean_I - a * mean_I

        mean_a = cv2.boxFilter(a, -1, (radius, radius))
        mean_b = cv2.boxFilter(b, -1, (radius, radius))

        result[:, :, c] = mean_a * I + mean_b

    return np.clip(result * 255, 0, 255).astype(np.uint8)


def _local_contrast_enhance(image: np.ndarray, grid_size: int = 16,
                            clip_limit: float = 3.0) -> np.ndarray:
    """
    局部对比度增强：对 L 通道做精细 CLAHE，使暗区细节也能显现。
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                            tileGridSize=(grid_size, grid_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def super_clarity(image: np.ndarray,
                  strength: float = 1.0,
                  denoise_first: bool = True,
                  detail_boost: float = 1.0,
                  edge_boost: float = 0.8,
                  local_contrast: float = 2.5,
                  micro_texture: float = 0.6) -> np.ndarray:
    """
    超级清晰度：融合多种技术让画面变得极其清晰锐利。

    处理流程：
    1. 引导滤波去噪（保留边缘的同时去除噪声，防止锐化放大噪点）
    2. 多尺度非锐化掩膜（分别恢复微观纹理、中频细节和宏观结构）
    3. 高频提升滤波（用拉普拉斯算子增强边缘）
    4. 局部对比度增强（让暗区细节也清晰可见）
    5. 微纹理增强（恢复唐卡绘画的笔触和颜料纹理）

    strength: 总体强度 0.1-2.0，1.0为标准
    """
    s = np.clip(strength, 0.1, 2.0)
    result = image.copy()

    if denoise_first:
        result = _guided_filter(result, radius=4, eps=0.005)

    details = _multi_scale_unsharp(
        result,
        scales=[1, 3, 7, 15],
        weights=[0.4 * s, 0.3 * s, 0.2 * s, 0.1 * s],
    )
    result = np.clip(result.astype(np.float64) + details * detail_boost, 0, 255).astype(np.uint8)

    result = _high_frequency_boost(result, strength=edge_boost * s * 0.3)

    result = _local_contrast_enhance(
        result,
        grid_size=16,
        clip_limit=local_contrast * s,
    )

    if micro_texture > 0:
        micro = _multi_scale_unsharp(
            result,
            scales=[0.5, 1.0],
            weights=[0.6 * s, 0.4 * s],
        )
        result = np.clip(
            result.astype(np.float64) + micro * micro_texture,
            0, 255,
        ).astype(np.uint8)

    return result


def super_clarity_preset(image: np.ndarray, level: str = "标准") -> np.ndarray:
    """
    清晰度预设模式。
    - 轻微：细微提升，最自然
    - 标准：明显提升，适合大多数唐卡
    - 强力：大幅提升，适合非常模糊的图
    - 极限：最大清晰度，适合严重模糊
    """
    presets = {
        "轻微": dict(strength=0.5, detail_boost=0.7, edge_boost=0.5, local_contrast=1.5, micro_texture=0.3),
        "标准": dict(strength=1.0, detail_boost=1.0, edge_boost=0.8, local_contrast=2.5, micro_texture=0.6),
        "强力": dict(strength=1.5, detail_boost=1.3, edge_boost=1.2, local_contrast=3.0, micro_texture=0.8),
        "极限": dict(strength=2.0, detail_boost=1.5, edge_boost=1.5, local_contrast=3.5, micro_texture=1.0),
    }
    params = presets.get(level, presets["标准"])
    return super_clarity(image, **params)


# ---------------------------------------------------------------------------
# 9. 去污渍
# ---------------------------------------------------------------------------

def remove_stains(image: np.ndarray, lower_thresh: tuple = (0, 0, 0),
                  upper_thresh: tuple = (30, 30, 30),
                  radius: int = 5) -> np.ndarray:
    lower = np.array(lower_thresh)
    upper = np.array(upper_thresh)
    mask = cv2.inRange(image, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


def remove_yellow_stains(image: np.ndarray, radius: int = 5) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([18, 60, 150])
    upper_yellow = np.array([30, 200, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


# ---------------------------------------------------------------------------
# 10. 综合修复流水线
# ---------------------------------------------------------------------------

def full_restoration_pipeline(
    image: np.ndarray,
    do_crack_repair: bool = False,
    crack_sensitivity: int = 30,
    crack_radius: int = 3,
    do_stain_removal: bool = False,
    do_dehaze: bool = True,
    dehaze_strength: float = 0.7,
    do_deyellow: bool = True,
    deyellow_strength: float = 0.5,
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
    新增去雾和去黄作为前置步骤，效果显著提升。
    """
    result = image.copy()

    if do_crack_repair:
        result = auto_repair_cracks(result, crack_sensitivity, crack_radius)

    if do_stain_removal:
        result = remove_stains(result)

    if do_dehaze:
        result = dehaze(result, dehaze_strength)

    if do_deyellow:
        result = reduce_yellowing(result, deyellow_strength)

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
    智能修复模式 V2：
    1. 去灰蒙（去雾算法）— 最关键的一步
    2. 色偏校正（去黄）
    3. 去噪
    4. 自适应色彩恢复
    5. 特色区域增强（金色、红蓝）
    6. 自适应对比度
    7. 锐化
    """
    info = analyze_image(image)
    result = image.copy()

    if info["is_hazy"] or info["haziness"] > 20:
        haze_str = min(0.85, 0.5 + info["haziness"] / 200.0)
        result = dehaze(result, strength=haze_str)

    if info["is_yellowed"]:
        yellow_str = min(0.8, info["yellow_bias"] / 40.0)
        result = reduce_yellowing(result, strength=yellow_str)

    if abs(info["color_cast_a"]) > 5 or abs(info["color_cast_b"]) > 5:
        cast_str = min(0.7, max(abs(info["color_cast_a"]), abs(info["color_cast_b"])) / 20.0)
        result = correct_color_cast(result, strength=cast_str)

    result = denoise(result, 7)

    if info["is_dark"]:
        result = auto_brightness(result, target=130.0)

    if info["is_very_faded"]:
        result = adaptive_color_restore(result, target_saturation=110.0)
    elif info["is_faded"]:
        result = adaptive_color_restore(result, target_saturation=95.0)
    else:
        result = restore_colors(result, saturation=1.35)

    result = enhance_gold(result, intensity=1.15)
    result = enhance_red_blue(result, intensity=1.2)

    if info["is_low_contrast"]:
        result = adaptive_histogram_eq(result, clip_limit=2.5, tile_size=8)
    else:
        result = auto_contrast(result, clip_percent=1.0)

    if info["is_blurry"]:
        result = super_clarity(result, strength=1.5, detail_boost=1.3,
                               edge_boost=1.2, local_contrast=3.0, micro_texture=0.8)
    else:
        result = super_clarity(result, strength=1.0, detail_boost=1.0,
                               edge_boost=0.8, local_contrast=2.5, micro_texture=0.6)

    return result
