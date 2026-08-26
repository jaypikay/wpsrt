from __future__ import annotations

from pathlib import Path

import pytest
import torch

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.methods import clip, tagging


def test_tag_file_returns_ranked_tags(
    monkeypatch: pytest.MonkeyPatch, sample_image: Path
):
    n = len(tagging.TAG_LABELS)
    embeddings = torch.eye(n)
    monkeypatch.setattr(tagging, "_get_tag_embeddings", lambda: embeddings)

    class FakeModel:
        def encode(self, images, **kwargs):
            img = torch.zeros(1, n)
            img[0, 0] = 1.0
            img[0, 1] = 0.4
            return torch.nn.functional.normalize(img, dim=-1)

    monkeypatch.setattr(clip, "load_model", lambda: FakeModel())

    tags = tagging.tag_file(sample_image, top_k=2)

    assert tags[0][0] == tagging.TAG_LABELS[0]
    assert tags[1][0] == tagging.TAG_LABELS[1]
    assert tags[0][1] >= tags[1][1]
    assert 0.0 < tags[0][1] <= 1.0


def test_tag_file_confidence_is_probability_distribution(
    monkeypatch: pytest.MonkeyPatch, sample_image: Path
):
    n = len(tagging.TAG_LABELS)
    embeddings = torch.eye(n)
    monkeypatch.setattr(tagging, "_get_tag_embeddings", lambda: embeddings)

    class FakeModel:
        def encode(self, images, **kwargs):
            img = torch.zeros(1, n)
            for idx in range(3):
                img[0, idx] = 1.0 - idx * 0.25
            return torch.nn.functional.normalize(img, dim=-1)

    monkeypatch.setattr(clip, "load_model", lambda: FakeModel())

    tags = tagging.tag_file(sample_image, top_k=n)

    assert sum(confidence for _, confidence in tags) == pytest.approx(1.0, abs=0.5)


def test_tag_file_invalid_image(temp_dir: Path, monkeypatch: pytest.MonkeyPatch):
    invalid_file = temp_dir / "invalid.png"
    invalid_file.write_text("not an image")
    monkeypatch.setattr(clip, "load_model", lambda: object())

    with pytest.raises(SkipUnsupportedImage):
        tagging.tag_file(invalid_file)


def test_tag_file_top_k_clamped(monkeypatch: pytest.MonkeyPatch, sample_image: Path):
    n = len(tagging.TAG_LABELS)
    embeddings = torch.eye(n)
    monkeypatch.setattr(tagging, "_get_tag_embeddings", lambda: embeddings)

    class FakeModel:
        def encode(self, images, **kwargs):
            img = torch.zeros(1, n)
            img[0, 0] = 1.0
            return torch.nn.functional.normalize(img, dim=-1)

    monkeypatch.setattr(clip, "load_model", lambda: FakeModel())

    tags = tagging.tag_file(sample_image, top_k=n * 2)

    assert len(tags) == n


def test_tag_file_filters_tags_below_threshold(
    monkeypatch: pytest.MonkeyPatch, sample_image: Path
):
    n = len(tagging.TAG_LABELS)
    embeddings = torch.eye(n)
    monkeypatch.setattr(tagging, "_get_tag_embeddings", lambda: embeddings)

    class FakeModel:
        def encode(self, images, **kwargs):
            img = torch.zeros(1, n)
            for idx in range(3):
                img[0, idx] = 1.0 - idx * 0.25
            return torch.nn.functional.normalize(img, dim=-1)

    monkeypatch.setattr(clip, "load_model", lambda: FakeModel())

    tags = tagging.tag_file(sample_image, top_k=n, threshold=0.6)

    assert tags
    assert all(confidence >= 0.6 for _, confidence in tags)
    assert tags[0][0] == tagging.TAG_LABELS[0]
