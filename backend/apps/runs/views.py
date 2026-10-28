import os
import shutil
import subprocess

from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from postprocessing.field_preview import FIELD_LABELS, render_field_png
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Run
from .serializers import RunLogEntrySerializer, RunSerializer, SimulationCaseSerializer
from .tasks import (
    run_build_dataset_stage,
    run_foam_to_vtk_stage,
    run_geometry_stage,
    run_openfoam_stage,
    run_paraview_export_stage,
)

# Maps a Run.Stage value to the Celery task that runs it. Populated
# incrementally as each stage is implemented (Phases 3-5 of the plan).
STAGE_TASKS = {
    Run.Stage.GEOMETRY: run_geometry_stage,
    Run.Stage.OPENFOAM: run_openfoam_stage,
    Run.Stage.FOAM_TO_VTK: run_foam_to_vtk_stage,
    Run.Stage.PARAVIEW_EXPORT: run_paraview_export_stage,
    Run.Stage.BUILD_DATASET: run_build_dataset_stage,
}


class RunViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Run.objects.all()
    serializer_class = RunSerializer

    def perform_destroy(self, instance):
        if self.request.query_params.get("purge_files") == "true" and instance.base_dir:
            shutil.rmtree(instance.base_dir, ignore_errors=True)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="pipeline/start")
    def pipeline_start(self, request, pk=None):
        run = self.get_object()
        self._clear_cancellation(run)
        run_geometry_stage.delay(run.pk)
        return Response(
            {"detail": "Pipeline started from the geometry stage.", "stage": Run.Stage.GEOMETRY},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path=r"stages/(?P<stage>[a-z_]+)/start")
    def stage_start(self, request, pk=None, stage=None):
        run = self.get_object()
        if stage not in Run.Stage.values:
            return Response({"detail": f"Unknown stage '{stage}'."}, status=status.HTTP_400_BAD_REQUEST)
        task = STAGE_TASKS.get(stage)
        if task is None:
            return Response(
                {"detail": f"Stage '{stage}' is not implemented yet."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        self._clear_cancellation(run)
        task.delay(run.pk)
        return Response({"detail": f"Stage '{stage}' started.", "stage": stage}, status=status.HTTP_202_ACCEPTED)

    @staticmethod
    def _clear_cancellation(run):
        """
        A deliberate (re)start means the user wants to proceed again, so a
        previous Stop no longer applies: clear the flag, and put anything
        it left CANCELLED back to PENDING so the stage's own "pending
        cases" query picks it up again. OpenFOAM cases resume (rather than
        redo) their last step naturally -- controlDict has `startFrom
        latestTime`, so simpleFoam/potentialFoam pick up from the last
        timestep actually written to disk.
        """
        if run.cancel_requested or run.status == Run.Status.CANCELLED:
            run.cancel_requested = False
            if run.status == Run.Status.CANCELLED:
                run.status = Run.Status.RUNNING
            run.save(update_fields=["cancel_requested", "status"])

        run.cases.filter(openfoam_status=Run.Status.CANCELLED).update(openfoam_status=Run.Status.PENDING)
        run.cases.filter(foam_to_vtk_status=Run.Status.CANCELLED).update(foam_to_vtk_status=Run.Status.PENDING)
        run.cases.filter(paraview_export_status=Run.Status.CANCELLED).update(
            paraview_export_status=Run.Status.PENDING
        )
        run.stages.filter(status=Run.Status.CANCELLED).update(status=Run.Status.PENDING)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        """
        Stop a Run: mark it (and anything still pending) as cancelled, and
        kill whatever OpenFOAM subprocess is actually running right now.

        Celery's own revoke(terminate=True) can't selectively kill one
        in-flight task under Windows' required `--pool=solo` without
        killing the whole worker -- see docs/operations.md -- so this
        kills the tracked OS-level PID directly instead, via `taskkill`.
        Cases already DONE are left alone; only PENDING/RUNNING ones (and
        RunStages) are marked CANCELLED.
        """
        run = self.get_object()
        run.cancel_requested = True
        run.status = Run.Status.CANCELLED
        run.save(update_fields=["cancel_requested", "status"])

        killed_pids = []
        for case in run.cases.exclude(pid__isnull=True):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(case.pid)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                killed_pids.append(case.pid)
            except Exception:
                pass

        run.cases.filter(openfoam_status__in=[Run.Status.PENDING, Run.Status.RUNNING]).update(
            openfoam_status=Run.Status.CANCELLED, pid=None
        )
        run.cases.filter(foam_to_vtk_status__in=[Run.Status.PENDING, Run.Status.RUNNING]).update(
            foam_to_vtk_status=Run.Status.CANCELLED
        )
        run.cases.filter(paraview_export_status__in=[Run.Status.PENDING, Run.Status.RUNNING]).update(
            paraview_export_status=Run.Status.CANCELLED
        )
        run.stages.filter(status__in=[Run.Status.PENDING, Run.Status.RUNNING]).update(
            status=Run.Status.CANCELLED, finished_at=timezone.now()
        )

        return Response(
            {"detail": "Run stopped.", "killed_pids": killed_pids},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path=r"stages/(?P<stage>[a-z_]+)/retry-failed")
    def stage_retry_failed(self, request, pk=None, stage=None):
        run = self.get_object()
        if stage not in Run.Stage.values:
            return Response({"detail": f"Unknown stage '{stage}'."}, status=status.HTTP_400_BAD_REQUEST)
        task = STAGE_TASKS.get(stage)
        if task is None:
            return Response(
                {"detail": f"Stage '{stage}' is not implemented yet."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        status_field = {
            Run.Stage.OPENFOAM: "openfoam_status",
            Run.Stage.FOAM_TO_VTK: "foam_to_vtk_status",
            Run.Stage.PARAVIEW_EXPORT: "paraview_export_status",
        }.get(stage)
        if status_field is None:
            return Response(
                {"detail": f"Stage '{stage}' runs once for the whole Run, not per case -- use stages/{stage}/start instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reset_count = run.cases.filter(**{status_field: Run.Status.FAILED}).update(
            **{status_field: Run.Status.PENDING}
        )
        self._clear_cancellation(run)
        task.delay(run.pk)
        return Response(
            {"detail": f"Retrying {reset_count} failed case(s) for stage '{stage}'.", "reset_count": reset_count},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        run = self.get_object()
        stages = list(run.stages.values("stage", "status", "started_at", "finished_at"))
        case_counts = {s: run.cases.filter(openfoam_status=s).count() for s in Run.Status.values}
        return Response(
            {
                "id": run.pk,
                "status": run.status,
                "error_message": run.error_message,
                "stages": stages,
                "case_counts": case_counts,
                "total_cases": run.cases.count(),
            }
        )

    @action(detail=True, methods=["get"])
    def cases(self, request, pk=None):
        run = self.get_object()
        qs = run.cases.all()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(openfoam_status=status_filter)
        page = self.paginate_queryset(qs)
        serializer = SimulationCaseSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path=r"cases/(?P<case_id>\d+)/field")
    def case_field(self, request, pk=None, case_id=None):
        """
        Render one case's p/Ux/Uy field as a PNG heatmap, interpolated from
        its resultados.csv on the same grid build_cnn_dataset.py uses --
        available as soon as that case's ParaView export is done, without
        waiting for the whole Run's build_dataset stage.
        """
        run = self.get_object()
        case = run.cases.filter(pk=case_id).first()
        if case is None:
            raise Http404("Case not found.")

        field = request.query_params.get("field", "p")
        if field not in FIELD_LABELS:
            return Response(
                {"detail": f"field must be one of {sorted(FIELD_LABELS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if case.paraview_export_status != Run.Status.DONE:
            return Response(
                {"detail": "This case's results are not ready yet (paraview_export not done)."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            png_bytes = render_field_png(case.case_dir, run.sdf_pkl_path, case.name, field)
        except FileNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return HttpResponse(png_bytes, content_type="image/png")

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        run = self.get_object()
        qs = run.log_entries.all()
        since_id = request.query_params.get("since_id")
        if since_id:
            qs = qs.filter(id__gt=since_id)
        stage_filter = request.query_params.get("stage")
        if stage_filter:
            qs = qs.filter(stage=stage_filter)
        serializer = RunLogEntrySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def dataset(self, request, pk=None):
        run = self.get_object()
        if not run.cnn_dataset_path or not os.path.exists(run.cnn_dataset_path):
            return Response({"detail": "Dataset not available yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "path": run.cnn_dataset_path,
                "size_bytes": os.path.getsize(run.cnn_dataset_path),
                "case_count": run.cases.filter(paraview_export_status=Run.Status.DONE).count(),
            }
        )

    @action(detail=True, methods=["get"], url_path="dataset/download")
    def dataset_download(self, request, pk=None):
        run = self.get_object()
        if not run.cnn_dataset_path or not os.path.exists(run.cnn_dataset_path):
            raise Http404("Dataset not available yet.")
        return FileResponse(
            open(run.cnn_dataset_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(run.cnn_dataset_path),
        )
