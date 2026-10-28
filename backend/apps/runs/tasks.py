import logging
import shutil
import subprocess
from pathlib import Path

from celery import chord, group, shared_task
from django.conf import settings
from django.utils import timezone

from geometry.random_airfoil_generator import generator_with_progress
from postprocessing.build_cnn_dataset import build_cnn_dataset
from postprocessing.foam_to_vtk import run_foam_to_vtk_case as _run_foam_to_vtk
from simulation.openfoam_runner import simulate_case

from .models import Run, RunLogEntry, RunStage, SimulationCase

logger = logging.getLogger(__name__)


def _log(run_id, message, *, stage="", level=RunLogEntry.Level.INFO, case=None):
    RunLogEntry.objects.create(run_id=run_id, case=case, stage=stage, level=level, message=message)


def _mark_stage(run_id, stage, run_status, **extra):
    RunStage.objects.filter(run_id=run_id, stage=stage).update(status=run_status, **extra)


def _is_cancelled(run_id) -> bool:
    return Run.objects.filter(pk=run_id, cancel_requested=True).exists()


@shared_task(bind=True)
def run_geometry_stage(self, run_id: int):
    run = Run.objects.get(pk=run_id)
    run.status = Run.Status.RUNNING
    run.save(update_fields=["status"])
    _mark_stage(
        run_id,
        Run.Stage.GEOMETRY,
        Run.Status.RUNNING,
        celery_task_id=self.request.id,
        started_at=timezone.now(),
    )
    _log(
        run_id,
        f"Starting geometry generation: N={run.n_airfoils}, angles={run.angles}",
        stage=Run.Stage.GEOMETRY,
    )

    def on_case(simulation_name, angle, simulation_path):
        case = SimulationCase.objects.create(
            run=run, name=simulation_name, angle=angle, case_dir=str(simulation_path)
        )
        _log(run_id, f"Generated case {simulation_name} (angle={angle})", stage=Run.Stage.GEOMETRY, case=case)

    try:
        sdf_pkl_path = generator_with_progress(
            N=run.n_airfoils,
            angles=run.angles,
            base=run.base_dir,
            origin=run.origin_dir,
            on_case=on_case,
        )
    except Exception as exc:
        logger.exception("Geometry stage failed for run %s", run_id)
        _mark_stage(run_id, Run.Stage.GEOMETRY, Run.Status.FAILED, finished_at=timezone.now())
        run.status = Run.Status.FAILED
        run.error_message = str(exc)
        run.save(update_fields=["status", "error_message"])
        _log(run_id, f"Geometry stage failed: {exc}", stage=Run.Stage.GEOMETRY, level=RunLogEntry.Level.ERROR)
        raise

    run.sdf_pkl_path = str(sdf_pkl_path)
    run.save(update_fields=["sdf_pkl_path"])
    _mark_stage(run_id, Run.Stage.GEOMETRY, Run.Status.DONE, finished_at=timezone.now())
    _log(
        run_id,
        f"Geometry stage done: {run.cases.count()} cases created",
        stage=Run.Stage.GEOMETRY,
    )

    if _is_cancelled(run_id):
        return
    run_openfoam_stage.delay(run_id)


@shared_task(bind=True)
def run_openfoam_case(self, case_id: int):
    """
    Run the 6 OpenFOAM steps for one case via src/simulation/openfoam_runner.py.

    Never raises: a failed case is recorded on the SimulationCase itself and
    reported back to finalize_openfoam_stage, which lets the rest of the
    chord's cases keep running -- unlike scripts/Openfoam_blueCFD.py, where
    one failing case stops the whole batch.
    """
    case = SimulationCase.objects.get(pk=case_id)
    run = case.run

    run.refresh_from_db(fields=["cancel_requested"])
    if run.cancel_requested:
        case.openfoam_status = Run.Status.CANCELLED
        case.save(update_fields=["openfoam_status"])
        return {"case_id": case_id, "ok": False, "cancelled": True}

    case.openfoam_status = Run.Status.RUNNING
    case.openfoam_step = ""
    case.save(update_fields=["openfoam_status", "openfoam_step"])

    if not settings.OPENFOAM_ENV_SCRIPT:
        case.openfoam_status = Run.Status.FAILED
        case.error_message = "OPENFOAM_ENV_SCRIPT is not configured (see docs/operations.md)."
        case.save(update_fields=["openfoam_status", "error_message"])
        _log(case.run_id, case.error_message, stage=Run.Stage.OPENFOAM, level=RunLogEntry.Level.ERROR, case=case)
        return {"case_id": case_id, "ok": False}

    def on_start(pid):
        case.pid = pid
        case.save(update_fields=["pid"])

    def on_step(step_name, step_result):
        case.pid = None
        case.openfoam_step = step_name
        case.save(update_fields=["pid", "openfoam_step"])
        if step_result.ok:
            _log(case.run_id, f"{case.name}: {step_name} OK", stage=Run.Stage.OPENFOAM, case=case)
        else:
            message = f"{case.name}: {step_name} failed (exit {step_result.returncode})\n{step_result.stderr[-2000:]}"
            _log(case.run_id, message, stage=Run.Stage.OPENFOAM, level=RunLogEntry.Level.ERROR, case=case)

    def should_cancel():
        run.refresh_from_db(fields=["cancel_requested"])
        return run.cancel_requested

    result = simulate_case(
        case.case_dir,
        settings.OPENFOAM_ENV_SCRIPT,
        on_step=on_step,
        on_start=on_start,
        should_cancel=should_cancel,
    )
    case.pid = None

    if result.cancelled or should_cancel():
        case.openfoam_status = Run.Status.CANCELLED
        case.save(update_fields=["pid", "openfoam_status"])
        _log(case.run_id, f"{case.name}: OpenFOAM stopped by user request", stage=Run.Stage.OPENFOAM, case=case)
        return {"case_id": case_id, "ok": False, "cancelled": True}

    if result.ok:
        results_dir = Path(case.run.base_dir) / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        dst = results_dir / case.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(case.case_dir, str(dst))
        case.case_dir = str(dst)
        case.openfoam_status = Run.Status.DONE
        case.error_message = ""
    else:
        failed = result.failed_step
        case.openfoam_status = Run.Status.FAILED
        case.error_message = f"{failed.step} failed (exit {failed.returncode}): {failed.stderr[-500:]}"

    case.save(update_fields=["case_dir", "pid", "openfoam_status", "error_message"])
    return {"case_id": case_id, "ok": result.ok}


@shared_task(bind=True)
def run_openfoam_stage(self, run_id: int):
    _mark_stage(
        run_id,
        Run.Stage.OPENFOAM,
        Run.Status.RUNNING,
        celery_task_id=self.request.id,
        started_at=timezone.now(),
    )
    pending_ids = list(
        SimulationCase.objects.filter(run_id=run_id, openfoam_status=Run.Status.PENDING).values_list(
            "id", flat=True
        )
    )
    _log(run_id, f"Starting OpenFOAM stage for {len(pending_ids)} case(s)", stage=Run.Stage.OPENFOAM)

    if not pending_ids:
        finalize_openfoam_stage.delay([], run_id)
        return

    chord(group(run_openfoam_case.s(cid) for cid in pending_ids), finalize_openfoam_stage.s(run_id)).apply_async()


@shared_task
def finalize_openfoam_stage(case_results, run_id):
    if _is_cancelled(run_id):
        _mark_stage(run_id, Run.Stage.OPENFOAM, Run.Status.CANCELLED, finished_at=timezone.now())
        return

    run = Run.objects.get(pk=run_id)
    succeeded = sum(1 for r in case_results if r.get("ok"))
    failed = len(case_results) - succeeded
    _log(
        run_id,
        f"OpenFOAM stage finished: {succeeded} succeeded, {failed} failed",
        stage=Run.Stage.OPENFOAM,
    )

    if case_results and succeeded == 0:
        _mark_stage(run_id, Run.Stage.OPENFOAM, Run.Status.FAILED, finished_at=timezone.now())
        run.status = Run.Status.FAILED
        run.error_message = "All OpenFOAM cases failed."
        run.save(update_fields=["status", "error_message"])
        return

    _mark_stage(run_id, Run.Stage.OPENFOAM, Run.Status.DONE, finished_at=timezone.now())
    if _is_cancelled(run_id):
        return
    run_foam_to_vtk_stage.delay(run_id)


@shared_task(bind=True)
def run_foam_to_vtk_case(self, case_id: int):
    """
    Convert one case's latest OpenFOAM results into VTK via
    src/postprocessing/foam_to_vtk.py, so run_paraview_export_case can later
    read them with pvbatch. Never raises, same reasoning as run_openfoam_case.
    """
    case = SimulationCase.objects.get(pk=case_id)
    case.foam_to_vtk_status = Run.Status.RUNNING
    case.save(update_fields=["foam_to_vtk_status"])

    if not settings.OPENFOAM_ENV_SCRIPT:
        case.foam_to_vtk_status = Run.Status.FAILED
        case.error_message = "OPENFOAM_ENV_SCRIPT is not configured (see docs/operations.md)."
        case.save(update_fields=["foam_to_vtk_status", "error_message"])
        _log(case.run_id, case.error_message, stage=Run.Stage.FOAM_TO_VTK, level=RunLogEntry.Level.ERROR, case=case)
        return {"case_id": case_id, "ok": False}

    result = _run_foam_to_vtk(case.case_dir, settings.OPENFOAM_ENV_SCRIPT, binary=settings.FOAMTOVTK_BIN)

    if result.ok:
        case.foam_to_vtk_status = Run.Status.DONE
        case.error_message = ""
        _log(case.run_id, f"{case.name}: foamToVTK OK", stage=Run.Stage.FOAM_TO_VTK, case=case)
    else:
        case.foam_to_vtk_status = Run.Status.FAILED
        case.error_message = f"foamToVTK failed (exit {result.returncode}): {result.stderr[-500:]}"
        _log(
            case.run_id,
            f"{case.name}: foamToVTK failed (exit {result.returncode})\n{result.stderr[-2000:]}",
            stage=Run.Stage.FOAM_TO_VTK,
            level=RunLogEntry.Level.ERROR,
            case=case,
        )

    case.save(update_fields=["foam_to_vtk_status", "error_message"])
    return {"case_id": case_id, "ok": result.ok}


@shared_task(bind=True)
def run_foam_to_vtk_stage(self, run_id: int):
    _mark_stage(
        run_id,
        Run.Stage.FOAM_TO_VTK,
        Run.Status.RUNNING,
        celery_task_id=self.request.id,
        started_at=timezone.now(),
    )
    pending_ids = list(
        SimulationCase.objects.filter(
            run_id=run_id, openfoam_status=Run.Status.DONE, foam_to_vtk_status=Run.Status.PENDING
        ).values_list("id", flat=True)
    )
    _log(run_id, f"Starting foamToVTK stage for {len(pending_ids)} case(s)", stage=Run.Stage.FOAM_TO_VTK)

    if not pending_ids:
        finalize_foam_to_vtk_stage.delay([], run_id)
        return

    chord(
        group(run_foam_to_vtk_case.s(cid) for cid in pending_ids), finalize_foam_to_vtk_stage.s(run_id)
    ).apply_async()


@shared_task
def finalize_foam_to_vtk_stage(case_results, run_id):
    if _is_cancelled(run_id):
        _mark_stage(run_id, Run.Stage.FOAM_TO_VTK, Run.Status.CANCELLED, finished_at=timezone.now())
        return

    run = Run.objects.get(pk=run_id)
    succeeded = sum(1 for r in case_results if r.get("ok"))
    failed = len(case_results) - succeeded
    _log(
        run_id,
        f"foamToVTK stage finished: {succeeded} succeeded, {failed} failed",
        stage=Run.Stage.FOAM_TO_VTK,
    )

    if case_results and succeeded == 0:
        _mark_stage(run_id, Run.Stage.FOAM_TO_VTK, Run.Status.FAILED, finished_at=timezone.now())
        run.status = Run.Status.FAILED
        run.error_message = "All foamToVTK conversions failed."
        run.save(update_fields=["status", "error_message"])
        return

    _mark_stage(run_id, Run.Stage.FOAM_TO_VTK, Run.Status.DONE, finished_at=timezone.now())
    if _is_cancelled(run_id):
        return
    run_paraview_export_stage.delay(run_id)


@shared_task(bind=True)
def run_paraview_export_case(self, case_id: int):
    """
    Export a CSV slice of one case's latest VTK results via pvbatch and
    scripts/paraview_export_macro.py. Never raises, same reasoning as
    run_openfoam_case.
    """
    case = SimulationCase.objects.get(pk=case_id)
    case.paraview_export_status = Run.Status.RUNNING
    case.save(update_fields=["paraview_export_status"])

    if not settings.PVBATCH_BIN:
        case.paraview_export_status = Run.Status.FAILED
        case.error_message = "PVBATCH_BIN is not configured (see docs/operations.md)."
        case.save(update_fields=["paraview_export_status", "error_message"])
        _log(case.run_id, case.error_message, stage=Run.Stage.PARAVIEW_EXPORT, level=RunLogEntry.Level.ERROR, case=case)
        return {"case_id": case_id, "ok": False}

    output_csv = Path(case.case_dir) / "postProcessing" / "resultados.csv"
    proc = subprocess.run(
        [
            settings.PVBATCH_BIN,
            str(settings.PARAVIEW_EXPORT_MACRO),
            "--case-dir",
            case.case_dir,
            "--output",
            str(output_csv),
        ],
        capture_output=True,
        text=True,
    )

    if proc.returncode == 0 and output_csv.exists():
        case.paraview_export_status = Run.Status.DONE
        case.error_message = ""
        _log(case.run_id, f"{case.name}: ParaView export OK", stage=Run.Stage.PARAVIEW_EXPORT, case=case)
    else:
        case.paraview_export_status = Run.Status.FAILED
        case.error_message = f"pvbatch failed (exit {proc.returncode}): {proc.stderr[-500:]}"
        _log(
            case.run_id,
            f"{case.name}: ParaView export failed (exit {proc.returncode})\n{proc.stderr[-2000:]}",
            stage=Run.Stage.PARAVIEW_EXPORT,
            level=RunLogEntry.Level.ERROR,
            case=case,
        )

    case.save(update_fields=["paraview_export_status", "error_message"])
    return {"case_id": case_id, "ok": case.paraview_export_status == Run.Status.DONE}


@shared_task(bind=True)
def run_paraview_export_stage(self, run_id: int):
    _mark_stage(
        run_id,
        Run.Stage.PARAVIEW_EXPORT,
        Run.Status.RUNNING,
        celery_task_id=self.request.id,
        started_at=timezone.now(),
    )
    pending_ids = list(
        SimulationCase.objects.filter(
            run_id=run_id, foam_to_vtk_status=Run.Status.DONE, paraview_export_status=Run.Status.PENDING
        ).values_list("id", flat=True)
    )
    _log(run_id, f"Starting ParaView export stage for {len(pending_ids)} case(s)", stage=Run.Stage.PARAVIEW_EXPORT)

    if not pending_ids:
        finalize_paraview_export_stage.delay([], run_id)
        return

    chord(
        group(run_paraview_export_case.s(cid) for cid in pending_ids),
        finalize_paraview_export_stage.s(run_id),
    ).apply_async()


@shared_task
def finalize_paraview_export_stage(case_results, run_id):
    if _is_cancelled(run_id):
        _mark_stage(run_id, Run.Stage.PARAVIEW_EXPORT, Run.Status.CANCELLED, finished_at=timezone.now())
        return

    run = Run.objects.get(pk=run_id)
    succeeded = sum(1 for r in case_results if r.get("ok"))
    failed = len(case_results) - succeeded
    _log(
        run_id,
        f"ParaView export stage finished: {succeeded} succeeded, {failed} failed",
        stage=Run.Stage.PARAVIEW_EXPORT,
    )

    if case_results and succeeded == 0:
        _mark_stage(run_id, Run.Stage.PARAVIEW_EXPORT, Run.Status.FAILED, finished_at=timezone.now())
        run.status = Run.Status.FAILED
        run.error_message = "All ParaView exports failed."
        run.save(update_fields=["status", "error_message"])
        return

    _mark_stage(run_id, Run.Stage.PARAVIEW_EXPORT, Run.Status.DONE, finished_at=timezone.now())
    if _is_cancelled(run_id):
        return
    run_build_dataset_stage.delay(run_id)


@shared_task(bind=True)
def run_build_dataset_stage(self, run_id: int):
    """
    Aggregate every case's resultados.csv + the run's sdf_df.pkl into the
    final CNN_df.pkl via src/postprocessing/build_cnn_dataset.py. This is
    the last stage: on success, the whole Run is marked DONE.
    """
    run = Run.objects.get(pk=run_id)
    _mark_stage(
        run_id,
        Run.Stage.BUILD_DATASET,
        Run.Status.RUNNING,
        celery_task_id=self.request.id,
        started_at=timezone.now(),
    )
    _log(run_id, "Starting build_dataset stage", stage=Run.Stage.BUILD_DATASET)

    results_dir = Path(run.base_dir) / "results"
    output_path = Path(run.base_dir) / "CNN_df.pkl"

    try:
        output_path = build_cnn_dataset(results_dir, run.sdf_pkl_path, output_path)
    except Exception as exc:
        logger.exception("build_dataset stage failed for run %s", run_id)
        _mark_stage(run_id, Run.Stage.BUILD_DATASET, Run.Status.FAILED, finished_at=timezone.now())
        run.status = Run.Status.FAILED
        run.error_message = str(exc)
        run.save(update_fields=["status", "error_message"])
        _log(run_id, f"build_dataset stage failed: {exc}", stage=Run.Stage.BUILD_DATASET, level=RunLogEntry.Level.ERROR)
        raise

    run.cnn_dataset_path = str(output_path)
    run.status = Run.Status.DONE
    run.save(update_fields=["cnn_dataset_path", "status"])
    _mark_stage(run_id, Run.Stage.BUILD_DATASET, Run.Status.DONE, finished_at=timezone.now())
    _log(run_id, f"build_dataset stage done: {output_path}", stage=Run.Stage.BUILD_DATASET)
