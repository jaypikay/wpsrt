from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from wpsrt.tools import device


@pytest.fixture
def no_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch, "cuda", SimpleNamespace(is_available=lambda: False))


@pytest.fixture
def with_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch, "cuda", SimpleNamespace(is_available=lambda: True))


def test_rocm_detected_with_hip_gpu(with_gpu, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.version, "hip", "7.2")
    assert device.rocm_is_available() is True


def test_rocm_not_available_without_gpu(no_gpu) -> None:
    assert device.rocm_is_available() is False


def test_rocm_not_available_without_hip_build(
    with_gpu, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(torch.version, "hip", raising=False)
    assert device.rocm_is_available() is False


def test_get_torch_device_falls_back_to_cpu(no_gpu) -> None:
    assert device.get_torch_device().type == "cpu"


def test_get_torch_device_prefers_rocm_gpu(
    with_gpu, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(torch.version, "hip", "7.2")
    assert device.get_torch_device().type == "cuda"


def test_get_torch_device_env_force_cpu(
    with_gpu, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(device._TORCH_DEVICE_ENV, "cpu")
    monkeypatch.setattr(torch.version, "hip", "7.2")
    assert device.get_torch_device().type == "cpu"


def test_get_torch_device_env_force_cuda_without_gpu(
    no_gpu, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(device._TORCH_DEVICE_ENV, "cuda")
    assert device.get_torch_device().type == "cpu"


def test_onnx_providers_cpu_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "onnxruntime.get_available_providers", lambda: ["CPUExecutionProvider"]
    )
    assert device.onnx_providers() == ["CPUExecutionProvider"]


def test_onnx_providers_prefers_rocm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "onnxruntime.get_available_providers",
        lambda: ["CPUExecutionProvider", "ROCMExecutionProvider"],
    )
    assert device.onnx_providers() == ["ROCMExecutionProvider", "CPUExecutionProvider"]


def test_onnx_providers_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(device._ONNX_PROVIDERS_ENV, "CPUExecutionProvider")
    monkeypatch.setattr(
        "onnxruntime.get_available_providers",
        lambda: ["CPUExecutionProvider", "ROCMExecutionProvider"],
    )
    assert device.onnx_providers() == ["CPUExecutionProvider"]


def test_rating_module_imports_without_opennsfw2() -> None:
    from wpsrt.methods import rating

    assert callable(rating.score_file)
