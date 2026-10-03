"""Untrained PyTorch prototype inspired by Zaid et al.'s synchronized ASCAD CNN.

Source: https://github.com/gabzai/Methodology-for-efficient-CNN-architectures-in-SCA/
        blob/master/ASCAD/N0%3D0/cnn_architecture.py
This is a candidate architecture, not a reproduction of their training/results.
It is outside the pinned training code and is not selected by the Kaggle notebook.
"""
import numpy as np
import torch.nn as nn


def build_candidate(input_samples=700):
    model = nn.Sequential(
        nn.Unflatten(1, (1, input_samples)),
        nn.Conv1d(1, 4, kernel_size=1), nn.SELU(),
        nn.BatchNorm1d(4, eps=1e-3, momentum=0.01),
        nn.AvgPool1d(2), nn.Flatten(),
        nn.Linear(4 * (input_samples // 2), 10), nn.SELU(),
        nn.Linear(10, 10), nn.SELU(), nn.Linear(10, 256),
    )
    # He-uniform hidden weights and Glorot-uniform output; zero biases.
    # PyTorch/Keras RNG and BatchNorm running-variance conventions differ.
    for layer in (model[1], model[6], model[8]):
        nn.init.kaiming_uniform_(layer.weight, a=0, nonlinearity="relu")
        nn.init.zeros_(layer.bias)
    nn.init.xavier_uniform_(model[10].weight)
    nn.init.zeros_(model[10].bias)
    return model


def fit_feature_minmax(training_traces):
    values = np.asarray(training_traces, dtype=np.float64)
    minimum, maximum = values.min(axis=0), values.max(axis=0)
    scale = maximum - minimum
    scale[scale == 0] = 1
    return {"minimum": minimum, "scale": scale}


def apply_feature_minmax(traces, stats):
    # Do not refit or clip validation values outside the training range.
    return ((np.asarray(traces, dtype=np.float64) - stats["minimum"]) / stats["scale"]).astype(np.float32)
