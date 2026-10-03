import torch.nn as nn


def build_model(name, input_samples=700):
    if name == "cnn_literature":
        # Architecture inspired by Zaid et al., synchronized ASCAD; logits for PyTorch CE.
        model = nn.Sequential(nn.Unflatten(1, (1, input_samples)),
            nn.Conv1d(1, 4, 1), nn.SELU(), nn.BatchNorm1d(4, eps=1e-3, momentum=0.01),
            nn.AvgPool1d(2), nn.Flatten(), nn.Linear(4 * (input_samples // 2), 10), nn.SELU(),
            nn.Linear(10, 10), nn.SELU(), nn.Linear(10, 256))
        for layer in (model[1], model[6], model[8]):
            nn.init.kaiming_uniform_(layer.weight, a=0, nonlinearity="relu")
            nn.init.zeros_(layer.bias)
        nn.init.xavier_uniform_(model[10].weight)
        nn.init.zeros_(model[10].bias)
        return model
    if name == "mlp":
        return nn.Sequential(nn.Linear(input_samples, 128), nn.ReLU(), nn.Linear(128, 64),
                             nn.ReLU(), nn.Linear(64, 256))
    if name in ("cnn", "cnn_leaky"):
        activation = nn.ReLU if name == "cnn" else lambda: nn.LeakyReLU(negative_slope=0.1)
        return nn.Sequential(nn.Unflatten(1, (1, input_samples)),
            nn.Conv1d(1, 8, 11, padding=5), activation(), nn.AvgPool1d(2),
            nn.Conv1d(8, 16, 11, padding=5), activation(), nn.AvgPool1d(2),
            nn.Flatten(), nn.Linear(16 * (input_samples // 4), 64), activation(), nn.Linear(64, 256))
    raise ValueError(f"Unknown model: {name}")
