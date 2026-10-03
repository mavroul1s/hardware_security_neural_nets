"""Untrained candidate for review; keep the existing training source unchanged."""
from torch import nn
from sca.models import build_model


def build_candidate_cnn():
    """Keep all dimensions/parameters and change only the three activations."""
    model = build_model("cnn")
    for index, layer in enumerate(model):
        if isinstance(layer, nn.ReLU):
            model[index] = nn.LeakyReLU(negative_slope=0.1)
    return model
