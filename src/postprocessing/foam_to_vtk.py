from __future__ import annotations

from pathlib import Path

from simulation.openfoam_runner import StepResult, capture_env, run_command


def run_foam_to_vtk_case(
    case_dir: str | Path,
    env_script: str | Path,
    binary: str = "foamToVTK",
) -> StepResult:
    """
    Run OpenFOAM's foamToVTK utility against `case_dir`, converting its
    latest internal-field results into case_dir/VTK/*.vtk for later ParaView
    export (scripts/paraview_export_macro.py only reads those internal
    files, never the per-patch ones).

    Boundary patches are excluded on purpose: on Windows, foamToVTK creates
    one directory per patch, and some auto-generated snappyHexMesh patch
    group names contain a colon (e.g. "motorBike_frt-fairing:001%1"), which
    is an invalid Windows path character and makes foamToVTK exit with a
    FOAM FATAL ERROR after it has already written the internal field we
    actually need. Excluding patches avoids that failure mode entirely
    instead of relying on a partial/undefined result.

    Ported from scripts/foamtoVTK_batch.py, which looped over a single
    hardcoded "run" directory shared by every case; here it operates on one
    already-resolved case_dir, so the backend can call it per case right
    after that case's OpenFOAM stage succeeds.
    """
    case_dir = Path(case_dir)
    env = capture_env(env_script)
    return run_command([binary, "-excludePatches", '(".*")'], case_dir, env)
