from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import griddata

# Must match geometry.sdf.compute_sdf's own defaults: the SDF matrices
# already stored in sdf_df.pkl were generated on this exact grid, and the
# per-case fields built here are masked against them cell-by-cell, so both
# grids have to line up.
DEFAULT_RESOLUTION_X = 200
DEFAULT_RESOLUTION_Y = 80
DEFAULT_X_MIN, DEFAULT_X_MAX = -0.5, 1.5
DEFAULT_Y_MIN, DEFAULT_Y_MAX = -0.5, 0.5


def interpolate_case_fields(
    csv_path: str | Path,
    resolution_x: int = DEFAULT_RESOLUTION_X,
    resolution_y: int = DEFAULT_RESOLUTION_Y,
    x_min: float = DEFAULT_X_MIN,
    x_max: float = DEFAULT_X_MAX,
    y_min: float = DEFAULT_Y_MIN,
    y_max: float = DEFAULT_Y_MAX,
    sdf_matrix: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """
    Read one case's ParaView-exported resultados.csv and interpolate U/p
    from the OpenFOAM mesh points onto the regular grid described by
    `resolution_*`/`x_min`.../`y_max` (defaults match `compute_sdf`'s own
    grid). If `sdf_matrix` is given, cells inside the airfoil (SDF < 0) are
    zeroed out in every returned field, same as `build_cnn_dataset`.

    Returns {"p": ..., "Ux": ..., "Uy": ...}, each a (resolution_y,
    resolution_x) array.
    """
    xs = np.linspace(x_min, x_max, resolution_x)
    ys = np.linspace(y_min, y_max, resolution_y)
    space_x, space_y = np.meshgrid(xs, ys)  # shape (resolution_y, resolution_x)
    space_points = np.column_stack([space_x.ravel(), space_y.ravel()])

    df = pd.read_csv(csv_path)
    points = df[["Points:0", "Points:1"]].to_numpy()
    u = df[["U:0", "U:1"]].to_numpy()
    p = df["p"].to_numpy()

    ux = griddata(points, u[:, 0], space_points, method="linear").reshape(resolution_y, resolution_x)
    uy = griddata(points, u[:, 1], space_points, method="linear").reshape(resolution_y, resolution_x)
    pres = griddata(points, p, space_points, method="linear").reshape(resolution_y, resolution_x)

    ux, uy, pres = np.flipud(ux), np.flipud(uy), np.flipud(pres)

    if sdf_matrix is not None:
        inside = sdf_matrix < 0
        ux[inside] = 0
        uy[inside] = 0
        pres[inside] = 0

    return {"p": pres, "Ux": ux, "Uy": uy}


def build_cnn_dataset(
    results_dir: str | Path,
    sdf_pkl_path: str | Path,
    output_pkl_path: str | Path,
    resolution_x: int = DEFAULT_RESOLUTION_X,
    resolution_y: int = DEFAULT_RESOLUTION_Y,
    x_min: float = DEFAULT_X_MIN,
    x_max: float = DEFAULT_X_MAX,
    y_min: float = DEFAULT_Y_MIN,
    y_max: float = DEFAULT_Y_MAX,
) -> Path:
    """
    Build the final CNN_df.pkl dataset: for every case under `results_dir`,
    read its ParaView-exported resultados.csv (Points/U/p on the OpenFOAM
    mesh), interpolate U and p onto a regular grid, mask out the cells
    occupied by the airfoil using that case's SDF (from sdf_pkl_path), and
    collect everything into one dataframe.

    Ported from scripts/dataframe.py, fixing two real issues found while
    integrating it:

    - Rows were accumulated with `pd.concat()` inside the loop, which is
      O(n^2) as the dataset grows; here they're collected in a plain list
      and concatenated once at the end.
    - The script hardcoded a 256x256 grid over x,y in [-1.5, 1.5], which no
      longer matches geometry.sdf.compute_sdf's actual grid (200x80 over
      x in [-0.5, 1.5], y in [-0.5, 0.5]) -- masking a 256x256 interpolated
      field with an 80x200 SDF matrix raises a shape-mismatch error in
      numpy. This version defaults to compute_sdf's real grid instead, and
      validates the shapes explicitly rather than let them silently
      broadcast wrong.
    """
    results_dir = Path(results_dir)
    sdf_df = pd.read_pickle(sdf_pkl_path)

    rows = []
    for case_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        csv_path = case_dir / "postProcessing" / "resultados.csv"
        if not csv_path.exists():
            continue

        match = sdf_df.index[sdf_df["Simulation"] == case_dir.name]
        if len(match) == 0:
            continue

        sdf_matrix = np.array(sdf_df.loc[match[0], "SDF"])
        if sdf_matrix.shape != (resolution_y, resolution_x):
            raise ValueError(
                f"SDF matrix for {case_dir.name} has shape {sdf_matrix.shape}, expected "
                f"({resolution_y}, {resolution_x}). compute_sdf() and build_cnn_dataset() "
                "must be called with matching bounds/resolution."
            )

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

        rows.append(
            {
                "Simulation": case_dir.name,
                "SDF": sdf_matrix,
                "Ux_discretized": fields["Ux"],
                "Uy_discretized": fields["Uy"],
                "P_discretized": fields["p"],
            }
        )

    cnn_df = pd.DataFrame(
        rows, columns=["Simulation", "SDF", "Ux_discretized", "Uy_discretized", "P_discretized"]
    )

    output_pkl_path = Path(output_pkl_path)
    output_pkl_path.parent.mkdir(parents=True, exist_ok=True)
    cnn_df.to_pickle(output_pkl_path)
    return output_pkl_path
