"""Compute device selection with CPU fallback.

wpsrt runs its AI sorting methods (CLIP, NudeDetector) on an AMD ROCm
GPU when one is available and transparently falls back to the CPU when
it is not. This module centralises that decision so every runtime keeps
a single source of truth for "which device am I on?".
"""

from __future__ import annotations

import logging
import os

import torch

logger = logging.getLogger(__name__)

_TORCH_DEVICE_ENV = "WPSRT_DEVICE"
_ONNX_PROVIDERS_ENV = "WPSRT_ONNX_PROVIDERS"

_ONNX_PREFERRED_ORDER = (
    "ROCMExecutionProvider",
    "CUDAExecutionProvider",
    "CPUExecutionProvider",
)


def rocm_is_available() -> bool:
    """Reports whether a usable AMD GPU is visible to PyTorch.

    ROCm builds of PyTorch expose their accelerator through the unified
    ``cuda`` API, so availability means both ``cuda`` being reachable and
    the binary being built against HIP.

    Returns:
        True when PyTorch was built with ROCm and an AMD device is usable.
    """
    return bool(getattr(torch.version, "hip", None) and torch.cuda.is_available())


def _torch_device_override() -> str | None:
    """Returns the forced device from WPSRT_DEVICE, if any."""
    value = os.getenv(_TORCH_DEVICE_ENV, "auto").strip().lower()
    return None if value in ("", "auto") else value


def get_torch_device() -> torch.device:
    """Selects the PyTorch device, preferring a ROCm GPU over CPU.

    Selection order:
        1. ``WPSRT_DEVICE=cpu`` forces CPU.
        2. ``WPSRT_DEVICE=cuda`` forces GPU when usable (falls back with a warning).
        3. A usable ROCm/CUDA accelerator is used when present.
        4. CPU is used otherwise.

    Returns:
        The device torch model inference should run on.
    """
    override = _torch_device_override()
    if override == "cpu":
        logger.info("Using CPU (forced via %s)", _TORCH_DEVICE_ENV)
        return torch.device("cpu")
    if override == "cuda" and not torch.cuda.is_available():
        logger.warning(
            "WPSRT_DEVICE=cuda requested but no GPU is usable; falling back to CPU"
        )
        return torch.device("cpu")
    if torch.cuda.is_available():
        backend = "AMD ROCm" if getattr(torch.version, "hip", None) else "CUDA"
        logger.info("Using %s GPU", backend)
        return torch.device("cuda")
    logger.info("No GPU detected; using CPU")
    return torch.device("cpu")


def _onnx_providers_override() -> list[str]:
    """Returns provider names allowed by ``WPSRT_ONNX_PROVIDERS``, if set."""
    import onnxruntime

    value = os.getenv(_ONNX_PROVIDERS_ENV, "")
    available = {provider.strip() for provider in value.split(",") if provider.strip()}
    if not available:
        return []
    valid = set(onnxruntime.get_available_providers())
    return [provider for provider in available if provider in valid]


def onnx_providers() -> list[str]:
    """Returns onnxruntime execution providers, preferring GPU with CPU fallback.

    The GPU execution provider (``ROCMExecutionProvider`` for AMD ROCm
    builds of onnxruntime) is preferred over the CPU provider when the
    installed binary supports it. At least the CPU provider is always
    returned so inference never fails on GPU-less machines.

    The ``WPSRT_ONNX_PROVIDERS`` environment variable can restrict the set
    of providers, e.g. ``WPSRT_ONNX_PROVIDERS=CPUExecutionProvider``.

    Returns:
        A list of execution provider names in preference order.
    """
    import onnxruntime

    allowed = _onnx_providers_override()
    usable = list(onnxruntime.get_available_providers())
    if allowed:
        usable = [provider for provider in usable if provider in allowed]
    preferred = [provider for provider in _ONNX_PREFERRED_ORDER if provider in usable]
    providers = preferred + [
        provider for provider in usable if provider not in preferred
    ]
    if "CPUExecutionProvider" not in providers and "CPUExecutionProvider" in usable:
        providers.append("CPUExecutionProvider")
    logger.debug("ONNX execution providers: %s", providers)
    return providers or ["CPUExecutionProvider"]
