"""Verify the corrective activation change preserves the matched architecture."""
import torch
from torch import nn
from sca.models import build_model


def test_corrected_cnn_has_identical_initial_parameters_and_negative_gradients():
    torch.manual_seed(0)
    original = build_model("cnn")
    torch.manual_seed(0)
    corrected = build_model("cnn_leaky")
    assert sum(p.numel() for p in corrected.parameters()) == 197424
    assert original.state_dict().keys() == corrected.state_dict().keys()
    assert all(torch.equal(value, corrected.state_dict()[name])
               for name, value in original.state_dict().items())
    activation_indices = [index for index, layer in enumerate(corrected) if isinstance(layer, nn.LeakyReLU)]
    assert activation_indices == [2, 5, 9]
    for index in activation_indices:
        negative = torch.tensor([-2.0, -1.0], requires_grad=True)
        corrected[index](negative).sum().backward()
        assert torch.allclose(negative.grad, torch.full_like(negative, 0.1))
    logits = corrected(torch.zeros(3, 700))
    assert logits.shape == (3, 256) and torch.isfinite(logits).all()


def test_literature_model_matches_reviewed_prototype_initialization():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("reviewed_candidate", Path(__file__).parents[1] / "notebooks/candidate_literature_cnn.py")
    prototype = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prototype)
    torch.manual_seed(0)
    reviewed = prototype.build_candidate()
    torch.manual_seed(0)
    actual = build_model("cnn_literature")
    assert sum(p.numel() for p in actual.parameters()) == 16952
    assert all(torch.equal(value, actual.state_dict()[name]) for name, value in reviewed.state_dict().items())
    assert actual(torch.zeros(3, 700)).shape == (3, 256)
