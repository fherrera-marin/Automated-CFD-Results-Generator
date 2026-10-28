# Run via pvbatch, e.g.:
#   pvbatch paraview_export_macro.py --case-dir <case> --output <case>/postProcessing/resultados.csv
#
# Replaces macro.py for the Django/Celery backend (see docs/operations.md and
# the implementation plan, section F). macro.py hardcoded a single
# "D:/.../run" directory shared by every case, processed only the first 10
# folders it found there, assumed exactly 6 fixed timesteps per case, and
# used `1024L` (a Python 2 long literal removed from Python 3's grammar).
#
# This version takes one already-resolved case directory and output path as
# arguments, discovers whatever timesteps foamToVTK actually wrote, and uses
# a plain int for BlockSize so it runs under whichever Python pvbatch embeds
# (ParaView 5.6's bundled pvbatch on this machine is Python 2.7, hence no
# f-strings/pathlib below).
from __future__ import print_function

import argparse
import glob
import os
import re

from paraview.simple import *  # noqa: F401,F403

paraview.simple._DisableFirstRenderCameraReset()  # noqa: F405


def _natural_key(path):
    numbers = re.findall(r"\d+", os.path.basename(path))
    return [int(n) for n in numbers] if numbers else [0]


def _find_vtk_files(case_dir):
    case_name = os.path.basename(os.path.normpath(case_dir))
    vtk_dir = os.path.join(case_dir, "VTK")
    pattern = os.path.join(vtk_dir, case_name + "_*.vtk")
    vtk_files = sorted(glob.glob(pattern), key=_natural_key)
    if not vtk_files:
        # Fall back to every top-level .vtk file in case foamToVTK named
        # them differently than "<case_name>_<time>.vtk".
        vtk_files = sorted(glob.glob(os.path.join(vtk_dir, "*.vtk")), key=_natural_key)
    return vtk_files


def export_case(case_dir, output_csv):
    vtk_files = _find_vtk_files(case_dir)
    if not vtk_files:
        raise RuntimeError("No .vtk files found under {0}/VTK -- run foamToVTK first.".format(case_dir))

    reader = LegacyVTKReader(FileNames=vtk_files)

    animationScene1 = GetAnimationScene()
    animationScene1.UpdateAnimationUsingDataTimeSteps()
    animationScene1.GoToLast()

    renderView1 = GetActiveViewOrCreate("RenderView")
    Show(reader, renderView1)
    renderView1.ResetCamera()
    renderView1.Update()

    # Fixed 2D slice through the domain -- same plane the original
    # macro.py used. This is a CFD-domain choice tied to the case's own
    # coordinate system, not something this script should invent; adjust
    # here if a given template's domain is laid out differently.
    slice1 = Slice(Input=reader)
    slice1.SliceType = "Plane"
    slice1.SliceType.Origin = [5.0, 0.0, 0.25]
    slice1.SliceType.Normal = [0.0, 0.0, 1.0]

    spreadSheetView1 = CreateView("SpreadSheetView")
    spreadSheetView1.BlockSize = 1024
    Show(slice1, spreadSheetView1)

    output_dir = os.path.dirname(output_csv)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    ExportView(output_csv, view=spreadSheetView1)


def main():
    parser = argparse.ArgumentParser(
        description="Export a 2D slice of the latest OpenFOAM timestep to CSV via ParaView."
    )
    parser.add_argument(
        "--case-dir",
        required=True,
        help="Path to a single case directory, already converted with foamToVTK.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path, e.g. <case>/postProcessing/resultados.csv",
    )
    args = parser.parse_args()

    export_case(args.case_dir, args.output)
    print("Wrote {0}".format(args.output))


if __name__ == "__main__":
    main()
