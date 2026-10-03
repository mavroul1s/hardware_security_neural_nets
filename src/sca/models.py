import torch.nn as nn


def build_model(name, input_samples=700):
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
