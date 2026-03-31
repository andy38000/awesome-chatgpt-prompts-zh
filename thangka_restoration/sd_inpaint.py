"""
唐卡 AI 修复模块 — 基于 Stable Diffusion Inpainting

使用扩散模型理解唐卡绘画风格，根据周围完好区域
智能生成并填充颜料脱落/损伤区域的内容。

需要 GPU (NVIDIA CUDA) 获得最佳效果，也支持 CPU（会很慢）。

依赖：
    pip install diffusers transformers accelerate torch
"""

import os
import numpy as np
from PIL import Image

_pipeline = None
_device = None


def _get_device():
    """检测最佳计算设备。"""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def _load_pipeline(model_id: str = None):
    """
    懒加载 SD Inpainting 模型（只加载一次）。
    """
    global _pipeline, _device
    if _pipeline is not None:
        return _pipeline

    import torch
    from diffusers import StableDiffusionInpaintPipeline

    _device = _get_device()

    if model_id is None:
        model_id = "runwayml/stable-diffusion-inpainting"

    dtype = torch.float16 if _device == "cuda" else torch.float32

    print(f"正在加载 AI 修复模型: {model_id}")
    print(f"计算设备: {_device}")

    _pipeline = StableDiffusionInpaintPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        safety_checker=None,
    )

    if _device == "cpu":
        _pipeline.enable_attention_slicing()
    else:
        _pipeline = _pipeline.to(_device)
        try:
            _pipeline.enable_xformers_memory_efficient_attention()
        except Exception:
            pass

    print("AI 修复模型加载完成！")
    return _pipeline


# ---------------------------------------------------------------------------
# 唐卡专用 Prompt 模板
# ---------------------------------------------------------------------------

THANGKA_PROMPTS = {
    "通用修复": (
        "traditional Tibetan thangka painting, intricate floral scrollwork, "
        "mineral pigment colors, gold leaf details, Buddhist art, "
        "highly detailed brushwork, fine lines, ornamental patterns, "
        "masterful traditional painting technique"
    ),
    "花卉卷草": (
        "intricate floral scrollwork and lotus patterns, traditional Tibetan thangka style, "
        "curving vine tendrils, green leaves with gold outlines, "
        "mineral pigments on cloth, fine detailed brushwork"
    ),
    "佛像面部": (
        "serene Buddhist deity face, traditional thangka painting style, "
        "smooth skin, gentle expression, gold jewelry and crown, "
        "fine detailed features, mineral pigment colors"
    ),
    "背景天空": (
        "traditional thangka painting background, blue sky with stylized clouds, "
        "mountain landscape, Buddhist paradise scenery, "
        "mineral pigment colors, fine brushwork"
    ),
    "金色装饰": (
        "gold leaf ornamental patterns, traditional Tibetan thangka, "
        "intricate golden filigree, Buddhist symbolic patterns, "
        "shimmering gold on dark background"
    ),
    "莲花": (
        "detailed lotus flower, traditional thangka painting style, "
        "pink and white petals, green leaves, golden stamens, "
        "fine mineral pigment brushwork"
    ),
    "衣物纹饰": (
        "traditional Buddhist deity robes and garments, "
        "intricate textile patterns, silk brocade details, "
        "red and orange flowing robes, gold trim, thangka painting style"
    ),
}

NEGATIVE_PROMPT = (
    "modern, digital art, photograph, 3D render, cartoon, anime, "
    "blurry, low quality, watermark, text, signature, "
    "western art style, oil painting texture"
)


# ---------------------------------------------------------------------------
# AI 修复核心函数
# ---------------------------------------------------------------------------

def sd_inpaint(
    image: np.ndarray,
    mask: np.ndarray,
    prompt_type: str = "通用修复",
    custom_prompt: str = "",
    strength: float = 0.85,
    guidance_scale: float = 12.0,
    num_steps: int = 30,
    seed: int = -1,
    model_id: str = None,
) -> np.ndarray:
    """
    使用 Stable Diffusion 修复唐卡损伤区域。

    参数：
    - image: BGR 格式原图
    - mask: 二值掩膜（白色=需要修复的区域）
    - prompt_type: 预设 prompt 类型
    - custom_prompt: 自定义 prompt（覆盖预设）
    - strength: 重绘强度 0-1（越大生成内容越多，越小越接近原图）
    - guidance_scale: prompt 引导强度（越大越严格遵循描述）
    - num_steps: 推理步数（越多质量越高，越慢）
    - seed: 随机种子（-1=随机）
    """
    import torch
    import cv2

    pipe = _load_pipeline(model_id)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    pil_mask = Image.fromarray(binary_mask)

    orig_w, orig_h = pil_image.size

    target_size = 512
    pil_image = pil_image.resize((target_size, target_size), Image.LANCZOS)
    pil_mask = pil_mask.resize((target_size, target_size), Image.NEAREST)

    if custom_prompt.strip():
        prompt = custom_prompt
    else:
        prompt = THANGKA_PROMPTS.get(prompt_type, THANGKA_PROMPTS["通用修复"])

    generator = None
    if seed >= 0:
        generator = torch.Generator(device=_device).manual_seed(seed)

    result = pipe(
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        image=pil_image,
        mask_image=pil_mask,
        strength=strength,
        guidance_scale=guidance_scale,
        num_inference_steps=num_steps,
        generator=generator,
    ).images[0]

    result = result.resize((orig_w, orig_h), Image.LANCZOS)

    result_np = np.array(result)
    result_bgr = cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)

    return result_bgr


def sd_inpaint_multi(
    image: np.ndarray,
    mask: np.ndarray,
    prompt_type: str = "通用修复",
    num_results: int = 3,
    **kwargs,
) -> list:
    """生成多个修复结果供选择。"""
    results = []
    for i in range(num_results):
        result = sd_inpaint(image, mask, prompt_type=prompt_type,
                           seed=i * 42, **kwargs)
        results.append(result)
    return results


def check_sd_available() -> dict:
    """检查 SD 运行环境是否就绪。"""
    info = {"available": False, "device": "unknown", "message": ""}

    try:
        import torch
        info["torch"] = True
        info["device"] = _get_device()

        if info["device"] == "cuda":
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB"
    except ImportError:
        info["torch"] = False
        info["message"] = "未安装 PyTorch。请运行: pip install torch"
        return info

    try:
        import diffusers
        info["diffusers"] = True
    except ImportError:
        info["diffusers"] = False
        info["message"] = "未安装 diffusers。请运行: pip install diffusers transformers accelerate"
        return info

    info["available"] = True
    if info["device"] == "cuda":
        info["message"] = f"✅ 就绪！GPU: {info.get('gpu_name', '?')} ({info.get('gpu_memory', '?')})"
    elif info["device"] == "mps":
        info["message"] = "✅ 就绪！使用 Apple Silicon GPU (MPS)"
    else:
        info["message"] = "⚠️ 仅 CPU 可用，修复会很慢（约5-15分钟/张）。建议安装 CUDA 版 PyTorch。"

    return info
