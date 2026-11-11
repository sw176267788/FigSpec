"""Regenerate the CSV files used by ``examples/``.

The outputs are committed to the repository so that rendering an example never
depends on running this script; it exists to make the numbers reproducible and
to document how they were produced.  Everything is seeded.

    python scripts/make_example_data.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "data"


def write_rows(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def learning_curves() -> None:
    rng = np.random.default_rng(7)
    epochs = np.arange(1, 41)
    train = 0.30 + 1.35 * np.exp(-epochs / 9.0) + rng.normal(0.0, 0.012, epochs.size)
    val = 0.42 + 1.25 * np.exp(-epochs / 11.0) + rng.normal(0.0, 0.015, epochs.size)
    rows = [[int(epoch), f"{a:.4f}", f"{b:.4f}"] for epoch, a, b in zip(epochs, train, val, strict=True)]
    write_rows(DATA / "loss.csv", ["epoch", "train", "val"], rows)


def benchmarks() -> None:
    models = [
        "ResNet-50",
        "ViT-B/16",
        "ConvNeXt-T",
        "Swin-T",
        "DeiT-S",
        "Mixer-B/16",
    ]
    accuracy = [76.1, 81.8, 82.1, 81.3, 79.8, 76.4]
    std = [0.4, 0.3, 0.2, 0.3, 0.4, 0.5]
    params = [25.6, 86.6, 28.6, 28.3, 22.1, 59.9]
    rows = [
        [model, f"{acc:.1f}", f"{dev:.1f}", f"{size:.1f}"]
        for model, acc, dev, size in zip(models, accuracy, std, params, strict=True)
    ]
    write_rows(DATA / "benchmarks.csv", ["model", "accuracy", "std", "params_m"], rows)


def scaling_law() -> None:
    rng = np.random.default_rng(11)
    params = np.array([5, 10, 20, 40, 80, 160, 320, 640, 1280], dtype=float)
    base = 2.10 * params**-0.072 + 1.70
    loss = base + rng.normal(0.0, 0.008, params.size)
    rows = [
        [f"{size:.0f}", f"{value:.4f}", f"{fit:.4f}"]
        for size, value, fit in zip(params, loss, base, strict=True)
    ]
    write_rows(DATA / "scaling.csv", ["params_m", "loss", "fit"], rows)


def latency() -> None:
    rng = np.random.default_rng(23)
    methods = {
        "Baseline": 41.0,
        "KV cache": 27.5,
        "FlashAttention": 21.0,
        "INT8": 14.2,
        "Speculative": 9.4,
    }
    rows: list[list[object]] = []
    for name, centre in methods.items():
        samples = rng.lognormal(mean=np.log(centre), sigma=0.12, size=40)
        rows.extend([name, f"{value:.2f}"] for value in samples)
    write_rows(DATA / "latency.csv", ["method", "latency_ms"], rows)


def main() -> None:
    learning_curves()
    benchmarks()
    scaling_law()
    latency()


if __name__ == "__main__":
    main()
