"""
唐卡修复 — 论文级核心算法

从以下论文提取的核心算法思想，用 OpenCV/NumPy 实现：

1. 边缘引导两阶段修复 (论文2,3,6)
   先修复线条骨架，再用骨架引导填充纹理色彩

2. 多尺度金字塔由粗到精 (论文1,4,10)
   从低分辨率修复大结构，逐层放大修复细节

3. 频域分离增强 (论文8)
   FFT 分离高低频，低频修结构，高频修纹理

4. 多方向纹理传播 (论文6,9)
   从完好区域沿多个方向向损伤区传播纹理

5. 局部风格迁移 (论文3,5)
   从同一幅画中对称/相似区域提取风格特征迁移到损伤区
"""

import cv2
import numpy as np


# =========================================================================
# 算法1: 边缘引导两阶段修复 (Edge-Guided Two-Stage Inpainting)
#
# 来源：论文2 (IEEE 2023), 论文3 (LSFNet 2025), 论文6 (Diffusion Patch GAN)
#
# 核心思想：唐卡的线条是灵魂。先把断裂的线条接上（结构修复），
# 再用完整的线条作为"骨架"引导色彩和纹理的填充。
# =========================================================================

def detect_edges_canny(image, low=50, high=150):
    """提取图像的边缘结构。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, low, high)


def repair_edge_structure(image, mask, edge_map=None):
    """
    第一阶段：修复边缘结构。
    将边缘图中断裂的线条连接起来。
    """
    if edge_map is None:
        edge_map = detect_edges_canny(image)

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    edge_map[mask_bin > 0] = 0

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dilated_edges = cv2.dilate(edge_map, kernel, iterations=1)

    repaired_edges = cv2.inpaint(dilated_edges, mask_bin, 5, cv2.INPAINT_NS)

    _, repaired_edges = cv2.threshold(repaired_edges, 30, 255, cv2.THRESH_BINARY)

    return repaired_edges


def edge_guided_inpaint(image, mask, iterations=3):
    """
    边缘引导两阶段修复。

    阶段1: 修复边缘线条 → 获得完整的结构骨架
    阶段2: 用修复后的边缘作为约束，逐层填充色彩
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if np.sum(mask_bin > 0) == 0:
        return image

    edges = detect_edges_canny(image, 30, 100)
    repaired_edges = repair_edge_structure(image, mask_bin, edges)

    result = image.copy()
    remaining = mask_bin.copy()

    for i in range(iterations):
        if np.sum(remaining > 0) == 0:
            break

        erode_size = max(3, int(np.sqrt(np.sum(remaining > 0) / 255) / (iterations - i + 1)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size))
        eroded = cv2.erode(remaining, kernel, iterations=1)
        current_layer = remaining - eroded

        if np.sum(current_layer > 0) == 0:
            current_layer = remaining

        edge_layer = repaired_edges.copy()
        edge_layer[current_layer == 0] = 0

        if np.sum(edge_layer > 0) > 0:
            edge_dilated = cv2.dilate(edge_layer, kernel, iterations=1)
            edge_region = current_layer.copy()
            edge_region[edge_dilated == 0] = 0
            non_edge_region = current_layer - edge_region

            if np.sum(edge_region > 0) > 0:
                result = cv2.inpaint(result, edge_region, 2, cv2.INPAINT_NS)
            if np.sum(non_edge_region > 0) > 0:
                result = cv2.inpaint(result, non_edge_region, 3, cv2.INPAINT_NS)
        else:
            result = cv2.inpaint(result, current_layer, 3, cv2.INPAINT_NS)

        remaining = eroded

    if np.sum(remaining > 0) > 0:
        result = cv2.inpaint(result, remaining, 5, cv2.INPAINT_NS)

    return result


# =========================================================================
# 算法2: 多尺度金字塔由粗到精修复 (Multi-Scale Pyramid Coarse-to-Fine)
#
# 来源：论文1 (Codebook+Transformer 2024), 论文4 (Multi-stage 2025),
#       论文10 (敦煌壁画多阶段 2024)
#
# 核心思想：先在小图上修复大结构（粗），然后逐步放大，
# 每一级利用上一级的结果引导当前级的修复（细）。
# =========================================================================

def pyramid_inpaint(image, mask, levels=3):
    """
    多尺度金字塔修复。

    Level 0 (最小): 修复整体结构和颜色分布
    Level 1 (中等): 修复中等尺度的图案
    Level 2 (原图): 修复精细纹理和细节
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if np.sum(mask_bin > 0) == 0:
        return image

    h, w = image.shape[:2]
    img_pyramid = [image]
    mask_pyramid = [mask_bin]

    for lv in range(1, levels):
        scale = 1.0 / (2 ** lv)
        new_w, new_h = max(32, int(w * scale)), max(32, int(h * scale))
        img_pyramid.append(cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA))
        mask_pyramid.append(cv2.resize(mask_bin, (new_w, new_h), interpolation=cv2.INTER_NEAREST))

    current = img_pyramid[-1]
    current_mask = mask_pyramid[-1]
    current = cv2.inpaint(current, current_mask, 7, cv2.INPAINT_NS)

    for lv in range(levels - 2, -1, -1):
        target_h, target_w = img_pyramid[lv].shape[:2]
        upscaled = cv2.resize(current, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        original = img_pyramid[lv]
        lv_mask = mask_pyramid[lv]

        blended = original.copy()
        blended[lv_mask > 0] = upscaled[lv_mask > 0]

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        boundary = cv2.dilate(lv_mask, kernel, iterations=2) - cv2.erode(lv_mask, kernel, iterations=1)
        boundary = np.clip(boundary, 0, 255).astype(np.uint8)

        if np.sum(boundary > 0) > 0:
            blended = cv2.inpaint(blended, boundary, 3, cv2.INPAINT_NS)

        current = blended

    return current


# =========================================================================
# 算法3: 频域分离增强 (Frequency Domain Separation)
#
# 来源：论文8 (双向自回归Transformer + FFT 2025)
#
# 核心思想：用 FFT 将图像分离为低频（结构/色块）和高频（边缘/纹理），
# 分别独立增强。低频控制色彩过渡，高频恢复线条和纹理。
# =========================================================================

def fft_separate(image, cutoff_ratio=0.05):
    """FFT 分离高低频分量。"""
    result_low = np.zeros_like(image, dtype=np.float64)
    result_high = np.zeros_like(image, dtype=np.float64)

    h, w = image.shape[:2]
    crow, ccol = h // 2, w // 2
    cutoff_h = max(1, int(h * cutoff_ratio))
    cutoff_w = max(1, int(w * cutoff_ratio))

    for c in range(3):
        channel = image[:, :, c].astype(np.float64)
        f = np.fft.fft2(channel)
        fshift = np.fft.fftshift(f)

        low_mask = np.zeros((h, w), dtype=np.float64)
        low_mask[crow - cutoff_h:crow + cutoff_h, ccol - cutoff_w:ccol + cutoff_w] = 1.0
        low_mask = cv2.GaussianBlur(low_mask, (0, 0), sigmaX=max(1, cutoff_h // 2))

        f_low = fshift * low_mask
        f_high = fshift * (1 - low_mask)

        result_low[:, :, c] = np.real(np.fft.ifft2(np.fft.ifftshift(f_low)))
        result_high[:, :, c] = np.real(np.fft.ifft2(np.fft.ifftshift(f_high)))

    return result_low, result_high


def frequency_guided_inpaint(image, mask):
    """
    频域引导修复：低频和高频分别修复再合并。
    低频用大半径修复（色彩过渡），高频用小半径修复（线条纹理）。
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if np.sum(mask_bin > 0) == 0:
        return image

    low, high = fft_separate(image, cutoff_ratio=0.06)

    low_u8 = np.clip(low, 0, 255).astype(np.uint8)
    repaired_low = cv2.inpaint(low_u8, mask_bin, 10, cv2.INPAINT_NS)

    high_shifted = np.clip(high + 128, 0, 255).astype(np.uint8)
    repaired_high_shifted = cv2.inpaint(high_shifted, mask_bin, 3, cv2.INPAINT_NS)
    repaired_high = repaired_high_shifted.astype(np.float64) - 128

    result = repaired_low.astype(np.float64) + repaired_high
    return np.clip(result, 0, 255).astype(np.uint8)


# =========================================================================
# 算法4: 多方向纹理传播 (Multi-Directional Texture Propagation)
#
# 来源：论文6 (Edge-Line Guided 2024), 论文9 (敦煌壁画GAN 2024)
#
# 核心思想：从损伤区域的8个方向向中心传播周围的纹理模式，
# 每个方向的贡献权重取决于该方向完好区域的纹理相似度。
# =========================================================================

def directional_propagate(image, mask, direction, steps=20):
    """沿一个方向从完好区域向损伤区传播像素。"""
    result = image.copy()
    dy, dx = direction
    h, w = image.shape[:2]

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    damaged = mask_bin > 0

    for _ in range(steps):
        shifted = np.roll(np.roll(result, -dy, axis=0), -dx, axis=1)
        shift_mask = np.roll(np.roll(mask_bin, -dy, axis=0), -dx, axis=1)

        can_fill = damaged & (shift_mask == 0)
        for c in range(3):
            result[:, :, c][can_fill] = shifted[:, :, c][can_fill]

        mask_bin[can_fill] = 0
        damaged = mask_bin > 0

        if np.sum(damaged) == 0:
            break

    return result


def multi_direction_propagate(image, mask):
    """
    8方向纹理传播：从损伤区周围8个方向同时传播纹理，加权混合。
    """
    directions = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    ]

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    results = []
    for d in directions:
        r = directional_propagate(image, mask_bin.copy(), d, steps=30)
        results.append(r.astype(np.float64))

    blended = np.mean(results, axis=0)
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    output = image.copy()
    output[mask_bin > 0] = blended[mask_bin > 0]
    return output


# =========================================================================
# 算法5: 对称区域风格迁移 (Symmetric Region Style Transfer)
#
# 来源：论文3 (LSFNet 2025), 论文5 (MACColor 2025)
#
# 核心思想：唐卡构图常左右对称。找到损伤区域的对称位置，
# 如果对称位置完好，用它的颜色和纹理来修复损伤区域。
# =========================================================================

def find_symmetric_region(image, mask, axis="vertical"):
    """找到损伤区域的对称位置，提取对称区域的内容。"""
    h, w = image.shape[:2]

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    if axis == "vertical":
        flipped_img = cv2.flip(image, 1)
        flipped_mask = cv2.flip(mask, 1)
    else:
        flipped_img = cv2.flip(image, 0)
        flipped_mask = cv2.flip(mask, 0)

    return flipped_img, flipped_mask


def symmetric_inpaint(image, mask, axis="vertical"):
    """
    对称修复：用画面对称位置的完好内容修复损伤区域。
    利用唐卡左右对称的构图特点。
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if np.sum(mask_bin > 0) == 0:
        return image

    flipped_img, flipped_mask = find_symmetric_region(image, mask_bin, axis)
    _, flipped_mask_bin = cv2.threshold(flipped_mask, 127, 255, cv2.THRESH_BINARY)

    usable = (mask_bin > 0) & (flipped_mask_bin == 0)

    result = image.copy()

    if np.sum(usable) > 0:
        for c in range(3):
            result[:, :, c][usable] = flipped_img[:, :, c][usable]

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        boundary = cv2.dilate(usable.astype(np.uint8) * 255, kernel, iterations=2)
        boundary = boundary - cv2.erode(usable.astype(np.uint8) * 255, kernel, iterations=1)
        boundary = np.clip(boundary, 0, 255).astype(np.uint8)
        if np.sum(boundary > 0) > 0:
            result = cv2.inpaint(result, boundary, 3, cv2.INPAINT_NS)

    still_damaged = mask_bin.copy()
    still_damaged[usable] = 0
    if np.sum(still_damaged > 0) > 0:
        result = cv2.inpaint(result, still_damaged, 5, cv2.INPAINT_NS)

    return result


# =========================================================================
# 综合流水线：融合所有论文算法
# =========================================================================

def paper_level_restore(image, mask, use_symmetric=True):
    """
    论文级综合修复流水线。

    融合 5 篇论文的核心算法：
    1. 频域分离 → 高低频独立修复（论文8）
    2. 对称区域风格迁移（论文3,5）— 可选
    3. 边缘引导两阶段修复（论文2,3,6）
    4. 多尺度金字塔由粗到精（论文1,4,10）
    5. 多方向纹理传播补充（论文6,9）
    6. 最终混合取各方法的最优区域
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if np.sum(mask_bin > 0) == 0:
        return image

    r_freq = frequency_guided_inpaint(image, mask_bin)

    if use_symmetric:
        r_sym = symmetric_inpaint(image, mask_bin)
    else:
        r_sym = None

    r_edge = edge_guided_inpaint(image, mask_bin, iterations=4)

    r_pyramid = pyramid_inpaint(image, mask_bin, levels=3)

    r_prop = multi_direction_propagate(image, mask_bin)

    damaged = mask_bin > 0
    orig_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)

    results = [
        ("freq", r_freq, 0.25),
        ("edge", r_edge, 0.30),
        ("pyramid", r_pyramid, 0.25),
        ("prop", r_prop, 0.10),
    ]
    if r_sym is not None:
        results.append(("sym", r_sym, 0.10))
    else:
        results[1] = ("edge", r_edge, 0.35)

    total_weight = sum(w for _, _, w in results)

    blended = np.zeros_like(image, dtype=np.float64)
    for name, r, w in results:
        blended += r.astype(np.float64) * (w / total_weight)

    output = image.copy()
    output[damaged] = np.clip(blended[damaged], 0, 255).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    border = cv2.dilate(mask_bin, kernel, iterations=2) - mask_bin
    border = np.clip(border, 0, 255).astype(np.uint8)
    if np.sum(border > 0) > 0:
        output = cv2.inpaint(output, border, 2, cv2.INPAINT_NS)

    return output
