from __future__ import annotations

from pathlib import Path

import pytest
import torch

from wpsrt.errors import SkipUnsupportedImage
from wpsrt.methods import clip


def _scores_favouring(labels: list[str], value: float = 0.9) -> torch.Tensor:
    scores = torch.full((1, len(clip.LABELS)), 0.1)
    for label in labels:
        scores[0, clip.LABELS.index(label)] = value
    return scores


def test_label_class_index_matches_lookup_table():
    assert len(clip.LABEL_CLASS_INDEX) == len(clip.LABELS)
    for label, class_idx in zip(clip.LABELS, clip.LABEL_CLASS_INDEX, strict=True):
        assert clip.CLASSES[int(class_idx)] == clip.LOOKUP_TABLE[label]


def test_classify_scores_returns_class_of_best_label():
    classification, label_name, confidence = clip.classify_scores(
        _scores_favouring(["landscape"])
    )

    assert classification == "SFW"
    assert label_name == "landscape"
    assert 0.0 < confidence <= 1.0


def test_classify_scores_aggregates_related_labels():
    """A cluster of same-class labels outweighs a single stronger outlier."""
    scores = _scores_favouring(["bikini", "lingerie", "cleavage", "swimsuit"], 0.30)
    scores[0, clip.LABELS.index("penis")] = 0.31

    classification, label_name, _ = clip.classify_scores(scores)

    assert label_name == "penis"
    assert classification == "SUGGESTIVE"


def test_classify_scores_confidences_sum_to_one():
    _, _, confidence = clip.classify_scores(_scores_favouring(["nude"]))
    assert confidence == pytest.approx(1.0, abs=0.5)


def test_encode_label_embeddings_averages_prompt_ensemble():
    class FakeModel:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def encode(self, prompts, **kwargs):
            self.prompts = prompts
            return torch.ones(len(prompts), 4)

    model = FakeModel()
    embeddings = clip._encode_label_embeddings(model)

    assert len(model.prompts) == len(clip.LABELS) * len(clip.PROMPT_TEMPLATES)
    assert embeddings.shape == (len(clip.LABELS), 4)
    assert torch.allclose(embeddings.norm(dim=-1), torch.ones(len(clip.LABELS)))


def test_process_file_invalid_image(temp_dir: Path, monkeypatch: pytest.MonkeyPatch):
    invalid_file = temp_dir / "invalid.png"
    invalid_file.write_text("not an image")
    monkeypatch.setattr(clip, "_get_model_and_embeddings", lambda: (None, None))

    with pytest.raises(SkipUnsupportedImage):
        clip.process_file(invalid_file)
