"""
唐卡 AI 修复模块 — Stable Diffusion 2.1 + 唐卡专用 LoRA

使用四川大学开源的唐卡修复 LoRA 模型 (Wangchuk1376/ThangkaModels)，
基于 1376 张专业标注唐卡图像微调，文化特征保留率 >95%。

模型来源：https://huggingface.co/Wangchuk1376/ThangkaModels

依赖安装：
    pip install diffusers transformers accelerate torch safetensors
"""

import os
import numpy as np
from PIL import Image

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_pipeline = None
_device = None
_model_loaded = False


def _get_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_pipeline(model_variant: str = "recommended"):
    """
    加载 SD 2.1 Inpainting + 唐卡 LoRA。

    model_variant:
    - "recommended": thangka_21_Status_140 (推荐，140步微调，平衡质量)
    - "detail": thangka_21_ACD_250 (250步微调，更多细节)
    """
    global _pipeline, _device, _model_loaded
    if _pipeline is not None:
        return _pipeline

    import torch
    from diffusers import StableDiffusionInpaintPipeline

    _device = _get_device()
    dtype = torch.float16 if _device in ("cuda", "mps") else torch.float32

    print("=" * 50)
    print("  正在加载 AI 修复模型...")
    print(f"  设备: {_device}")
    print("=" * 50)

    base_model = "stabilityai/stable-diffusion-2-inpainting"

    print(f"[1/2] 加载基础模型: {base_model}")
    print(f"  镜像: {os.environ.get('HF_ENDPOINT', '未设置（使用官方源）')}")
    print(f"  如果下载卡住，请确认网络可访问 huggingface.co 或 hf-mirror.com")
    try:
        _pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            base_model,
            torch_dtype=dtype,
            safety_checker=None,
        )
    except Exception as e:
        raise RuntimeError(
            f"模型下载失败: {e}\n\n"
            f"请尝试以下方法：\n"
            f"1. 关闭代理/VPN 后重试\n"
            f"2. 或在命令行中先运行：\n"
            f"   set HF_ENDPOINT=https://hf-mirror.com\n"
            f"   然后重新启动 python app.py\n"
            f"3. 或手动下载模型：\n"
            f"   huggingface-cli download stabilityai/stable-diffusion-2-inpainting --local-dir models/sd2.1"
        )

    lora_repo = "Wangchuk1376/ThangkaModels"
    if model_variant == "detail":
        lora_file = "models/finetuned/thangka_21_ACD_250.safetensors"
        lora_name = "ACD_250 (高细节)"
    else:
        lora_file = "models/finetuned/thangka_21_Status_140.safetensors"
        lora_name = "Status_140 (推荐)"

    print(f"[2/2] 加载唐卡 LoRA: {lora_name}")
    try:
        from huggingface_hub import hf_hub_download
        local_path = hf_hub_download(
            repo_id=lora_repo,
            filename=lora_file,
        )
        _pipeline.load_lora_weights(local_path)
        _model_loaded = True
        print(f"  ✅ LoRA 加载成功: {lora_name}")
    except Exception as e:
        print(f"  ⚠️ LoRA 加载跳过（不影响基础修复）: {e}")
        _model_loaded = False

    if _device == "cpu":
        _pipeline.enable_attention_slicing()
    else:
        _pipeline = _pipeline.to(_device)

    print("=" * 50)
    print("  AI 修复模型加载完成！")
    print("=" * 50)

    return _pipeline


# ---------------------------------------------------------------------------
# 唐卡专用 Prompt
# ---------------------------------------------------------------------------

THANGKA_PROMPTS = {
    "通用修复": (
        "traditional Tibetan thangka painting, intricate floral scrollwork, "
        "mineral pigment colors, gold leaf details, Buddhist art, "
        "highly detailed brushwork, fine lines, ornamental patterns, "
        "masterful traditional painting technique, thangka art"
    ),
    "花卉卷草": (
        "intricate floral scrollwork and lotus patterns, traditional Tibetan thangka style, "
        "curving vine tendrils, green leaves with gold outlines, "
        "mineral pigments on cloth, fine detailed brushwork, thangka art"
    ),
    "佛像面部": (
        "serene Buddhist deity face, traditional thangka painting style, "
        "smooth skin, gentle expression, gold jewelry and crown, "
        "fine detailed features, mineral pigment colors, thangka art"
    ),
    "背景天空": (
        "traditional thangka painting background, blue sky with stylized clouds, "
        "mountain landscape, Buddhist paradise scenery, "
        "mineral pigment colors, fine brushwork, thangka art"
    ),
    "金色装饰": (
        "gold leaf ornamental patterns, traditional Tibetan thangka, "
        "intricate golden filigree, Buddhist symbolic patterns, "
        "shimmering gold on dark background, thangka art"
    ),
    "莲花": (
        "detailed lotus flower, traditional thangka painting style, "
        "pink and white petals, green leaves, golden stamens, "
        "fine mineral pigment brushwork, thangka art"
    ),
    "衣物纹饰": (
        "traditional Buddhist deity robes and garments, "
        "intricate textile patterns, silk brocade details, "
        "red and orange flowing robes, gold trim, thangka art"
    ),
}

NEGATIVE_PROMPT = (
    "modern, digital art, photograph, 3D render, cartoon, anime, "
    "blurry, low quality, watermark, text, signature, "
    "western art style, oil painting texture, distorted"
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
    model_variant: str = "recommended",
) -> np.ndarray:
    """
    使用 SD 2.1 + 唐卡 LoRA 修复损伤区域。
    """
    import torch
    import cv2

    pipe = _load_pipeline(model_variant)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)

    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    pil_mask = Image.fromarray(binary_mask)

    orig_w, orig_h = pil_image.size

    pil_image = pil_image.resize((512, 512), Image.LANCZOS)
    pil_mask = pil_mask.resize((512, 512), Image.NEAREST)

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
    return cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)


def check_sd_available() -> dict:
    """检查 SD 运行环境。"""
    info = {"available": False, "device": "unknown", "message": ""}

    try:
        import torch
        info["torch"] = True
        info["torch_version"] = torch.__version__
        info["device"] = _get_device()

        if info["device"] == "cuda":
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
    except ImportError:
        info["torch"] = False
        info["message"] = "❌ 未安装 PyTorch。请运行:\n`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`"
        return info

    try:
        import diffusers
        info["diffusers"] = True
        info["diffusers_version"] = diffusers.__version__
    except ImportError:
        info["diffusers"] = False
        info["message"] = "❌ 未安装 diffusers。请运行:\n`pip install diffusers transformers accelerate safetensors`"
        return info

    try:
        import huggingface_hub
        info["hf_hub"] = True
    except ImportError:
        info["hf_hub"] = False
        info["message"] = "❌ 未安装 huggingface_hub。请运行:\n`pip install huggingface-hub`"
        return info

    info["available"] = True
    if info["device"] == "cuda":
        info["message"] = (
            f"✅ 就绪！\n"
            f"- GPU: {info.get('gpu_name', '?')} ({info.get('gpu_memory', '?')})\n"
            f"- PyTorch: {info.get('torch_version', '?')}\n"
            f"- Diffusers: {info.get('diffusers_version', '?')}\n"
            f"- 模型: Wangchuk1376/ThangkaModels (唐卡专用 LoRA)\n"
            f"- 预计修复速度: 10-20秒/张"
        )
    elif info["device"] == "mps":
        info["message"] = "✅ 就绪！使用 Apple Silicon GPU\n预计修复速度: 30-60秒/张"
    else:
        info["message"] = (
            "⚠️ 仅 CPU 可用，修复会较慢（5-15分钟/张）\n"
            "建议安装 CUDA 版 PyTorch:\n"
            "`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`"
        )

    return info
