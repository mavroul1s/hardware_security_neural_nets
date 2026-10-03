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
