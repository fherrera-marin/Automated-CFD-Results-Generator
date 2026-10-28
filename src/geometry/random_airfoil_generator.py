from geometry.naca4 import NACA4Airfoil
from geometry.transform import AirfoilTransform
from geometry.export_stl import export_from_contour
from geometry.sdf import compute_sdf
import pandas as pd
from pathlib import Path
from typing import Callable
import numpy as np
import random
import shutil


def random_airfoil(
    M_range=(0, 9),
    P_range=(1, 9),
    T_range=(6, 18),
    closed_te=True,
    seed=None,
) -> NACA4Airfoil:
    """
    Generate a random NACA 4-digit airfoil within realistic bounds.

    Parameters
    ----------
    M_range : tuple[int, int]
        Range for maximum camber (percent).
    P_range : tuple[int, int]
        Range for camber position (tenths of chord).
    T_range : tuple[int, int]
        Range for thickness (percent).
    closed_te : bool
        Whether the trailing edge is closed.
    seed : int | None
        Random seed for reproducibility.

    Returns
    -------
    NACA4Airfoil
        Randomly generated airfoil.
    """

    if seed is not None:
        random.seed(seed)

    M = random.randint(*M_range)
    P = random.randint(*P_range)
    T = random.randint(*T_range)

    return NACA4Airfoil(M, P, T, closed_te=closed_te)


def generator(
    N: int,
    angles,
    base: str | Path,
    origin: str | Path,
):
    """
    Generate random airfoils, rotate them by given angles,
    and export STL files into simulation folders.

    Parameters
    ----------
    N : int
        Number of random airfoils to generate.
    angles : iterable of float
        Rotation angles in degrees.
    base : str | Path
        Base directory where simulations will be created.
    origin : str | Path
        Template directory to be copied into each simulation folder.
    """

    base = Path(base).resolve()
    origin = Path(origin).resolve()

    if not origin.exists():
        raise FileNotFoundError(f"Origin directory does not exist: {origin}")

    base.mkdir(parents=True, exist_ok=True)

    counter = 0

    #  SDF initialization
    sdf_df = pd.DataFrame(columns=['SDF','Simulation'])

    for i in range(N):
        airfoil = random_airfoil()

        for angle in angles:
            counter += 1

            simulation_name = f"motorbike_{counter:04d}"
            simulation_path = base / simulation_name
            airfoil_path=simulation_path/"constant"/"triSurface"


            # Copy template directory
            shutil.copytree(origin, simulation_path)

            # Generate rotated airfoil contour
            contour = AirfoilTransform.rotate(
                airfoil.coordinates(step=0.01),
                angle
            )

            # Compute SDF
            sdf=compute_sdf(contour)

            sdf_df.loc[counter,"Simulation"]=simulation_name
            sdf_df.loc[counter, 'SDF'] = sdf

            # Export STL inside the simulation folder
            export_from_contour(
                contour=contour,
                filename="op1.stl",
                output_dir=airfoil_path
            )
    # Export dataframe SDF
    sdf_df.to_pickle(base/"sdf_df.pkl")


def generator_with_progress(
    N: int,
    angles,
    base: str | Path,
    origin: str | Path,
    on_case: Callable[[str, float, Path], None] | None = None,
) -> Path:
    """
    Same generation logic as `generator()`, but invokes `on_case(simulation_name,
    angle, simulation_path)` right after each case directory is fully created
    (template copied, STL exported, SDF row recorded), so a caller can track
    per-case progress (e.g. persist a SimulationCase row) without needing to
    re-scan the base directory afterwards.

    Kept as a separate, additive function rather than changing `generator()`,
    which the Tkinter GUI (scripts/GUI.py) still calls directly.

    Parameters
    ----------
    N, angles, base, origin : same as `generator()`.
    on_case : callable | None
        Invoked once per generated case as on_case(simulation_name, angle, simulation_path).

    Returns
    -------
    Path
        Path to the written `sdf_df.pkl`.
    """

    base = Path(base).resolve()
    origin = Path(origin).resolve()

    if not origin.exists():
        raise FileNotFoundError(f"Origin directory does not exist: {origin}")

    base.mkdir(parents=True, exist_ok=True)

    counter = 0
    sdf_df = pd.DataFrame(columns=['SDF', 'Simulation'])

    for i in range(N):
        airfoil = random_airfoil()

        for angle in angles:
            counter += 1

            simulation_name = f"motorbike_{counter:04d}"
            simulation_path = base / simulation_name
            airfoil_path = simulation_path / "constant" / "triSurface"

            shutil.copytree(origin, simulation_path)

            contour = AirfoilTransform.rotate(
                airfoil.coordinates(step=0.01),
                angle
            )

            sdf = compute_sdf(contour)

            sdf_df.loc[counter, "Simulation"] = simulation_name
            sdf_df.loc[counter, 'SDF'] = sdf

            export_from_contour(
                contour=contour,
                filename="op1.stl",
                output_dir=airfoil_path
            )

            if on_case is not None:
                on_case(simulation_name, angle, simulation_path)

    sdf_pkl_path = base / "sdf_df.pkl"
    sdf_df.to_pickle(sdf_pkl_path)
    return sdf_pkl_path




