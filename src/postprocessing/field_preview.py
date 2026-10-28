from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: this renders inside the Django/Celery process, no display available
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from postprocessing.build_cnn_dataset import (
    DEFAULT_RESOLUTION_X,
    DEFAULT_RESOLUTION_Y,
    DEFAULT_X_MAX,
    DEFAULT_X_MIN,
    DEFAULT_Y_MAX,
    DEFAULT_Y_MIN,
    interpolate_case_fields,
)

FIELD_LABELS: dict[str, str] = {
    "p": "Pressure (p)",
    "Ux": "Velocity Ux (m/s)",
    "Uy": "Velocity Uy (m/s)",
}


def render_field_png(
    case_dir: str | Path,
    sdf_pkl_path: str | Path,
    case_name: str,
    field: str,
    resolution_x: int = DEFAULT_RESOLUTION_X,
    resolution_y: int = DEFAULT_RESOLUTION_Y,
    x_min: float = DEFAULT_X_MIN,
    x_max: float = DEFAULT_X_MAX,
    y_min: float = DEFAULT_Y_MIN,
    y_max: float = DEFAULT_Y_MAX,
) -> bytes:
    """
    Render one case's p/Ux/Uy field (interpolated from its resultados.csv
    the same way build_cnn_dataset.py does) as a PNG heatmap, for the
    per-case "view results" button in the frontend.
    """
    if field not in FIELD_LABELS:
        raise ValueError(f"field must be one of {sorted(FIELD_LABELS)}, got {field!r}")

    case_dir = Path(case_dir)
    csv_path = case_dir / "postProcessing" / "resultados.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No resultados.csv for this case yet: {csv_path}")

    sdf_matrix = None
    sdf_df = pd.read_pickle(sdf_pkl_path)
    match = sdf_df.index[sdf_df["Simulation"] == case_name]
    if len(match):
        sdf_matrix = np.array(sdf_df.loc[match[0], "SDF"])

    fields = interpolate_case_fields(
        csv_path,
        resolution_x=resolution_x,
        resolution_y=resolution_y,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        sdf_matrix=sdf_matrix,
    )
    data = fields[field]

    fig, ax = plt.subplots(figsize=(6, 3))
    # `data` rows already run top-to-bottom = y_max-to-y_min (interpolate_case_fields
    # flips it to match compute_sdf's own convention), which is exactly what
    # imshow's default origin="upper" expects -- no origin= override here.
    im = ax.imshow(data, cmap="viridis", extent=(x_min, x_max, y_min, y_max))
    fig.colorbar(im, ax=ax, label=FIELD_LABELS[field])
    ax.set_title(f"{case_name} — {FIELD_LABELS[field]}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
