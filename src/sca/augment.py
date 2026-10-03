"""Non-circular sample shifts followed by iid Gaussian noise."""
import torch


def shift_batch(x, shifts, padding="zero"):
    if x.ndim != 2 or shifts.shape != (x.shape[0],):
        raise ValueError("Expected x[B,L] and shifts[B]")
    if shifts.dtype not in (torch.int32, torch.int64):
        raise ValueError("Shifts must be integers")
    if torch.any(shifts.abs() >= x.shape[1]):
        raise ValueError("Shift would remove the entire trace")
    # Positive shifts move samples to the right. Off-window samples are discarded.
    source = torch.arange(x.shape[1], device=x.device)[None, :] - shifts[:, None]
    valid = (source >= 0) & (source < x.shape[1])
    result = x.gather(1, source.clamp(0, x.shape[1] - 1))
    if padding == "zero":
        return result * valid
    if padding == "edge":
        return result
    raise ValueError("padding must be zero or edge")


def augment_batch(x, noise_std=0.0, max_shift=0, padding="zero", generator=None):
    if noise_std < 0 or not isinstance(max_shift, int) or not 0 <= max_shift < x.shape[1]:
        raise ValueError("Invalid corruption intensity")
    if padding not in ("zero", "edge"):
        raise ValueError("Unknown padding")
    out = x
    if max_shift:
        shifts = torch.randint(-max_shift, max_shift + 1, (len(x),), device=x.device, generator=generator)
        out = shift_batch(out, shifts, padding)
    if noise_std:
        out = out + noise_std * torch.randn(out.shape, device=x.device, generator=generator, dtype=x.dtype)
    return out
