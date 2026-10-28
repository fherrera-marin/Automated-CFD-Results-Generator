from django.db import models


class Run(models.Model):
    """A single dataset-generation request: N random airfoils rotated across
    a set of angles, carried through the full CFD pipeline down to the final
    CNN_df.pkl dataset."""

    class Stage(models.TextChoices):
        GEOMETRY = "geometry", "Geometry generation"
        OPENFOAM = "openfoam", "OpenFOAM simulation"
        FOAM_TO_VTK = "foam_to_vtk", "foamToVTK conversion"
        PARAVIEW_EXPORT = "paraview_export", "ParaView CSV export"
        BUILD_DATASET = "build_dataset", "Build CNN dataset"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=255, blank=True)
    n_airfoils = models.PositiveIntegerField()
    angles = models.JSONField(help_text="List of rotation angles in degrees, e.g. [0, 45, 90]")
    base_dir = models.CharField(max_length=1024)
    origin_dir = models.CharField(max_length=1024)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    # Checked cooperatively by tasks between steps/cases; the Stop button
    # also directly kills whatever OpenFOAM subprocess is currently running
    # (see SimulationCase.pid) rather than waiting for it to finish.
    cancel_requested = models.BooleanField(default=False)
    sdf_pkl_path = models.CharField(max_length=1024, blank=True)
    cnn_dataset_path = models.CharField(max_length=1024, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or f"Run #{self.pk}"


class RunStage(models.Model):
    run = models.ForeignKey(Run, related_name="stages", on_delete=models.CASCADE)
    stage = models.CharField(max_length=32, choices=Run.Stage.choices)
    status = models.CharField(max_length=16, choices=Run.Status.choices, default=Run.Status.PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("run", "stage")
        ordering = ["run_id", "id"]

    def __str__(self) -> str:
        return f"{self.run} / {self.stage} ({self.status})"


class SimulationCase(models.Model):
    """One generated airfoil+angle case, tracked through every pipeline
    stage. `case_dir` is the single source of truth for where this case
    currently lives on disk; it is updated whenever a stage moves it."""

    run = models.ForeignKey(Run, related_name="cases", on_delete=models.CASCADE)
    name = models.CharField(max_length=64, help_text="e.g. motorbike_0007")
    angle = models.FloatField()
    case_dir = models.CharField(max_length=1024)

    openfoam_status = models.CharField(max_length=16, choices=Run.Status.choices, default=Run.Status.PENDING)
    openfoam_step = models.CharField(max_length=32, blank=True)
    foam_to_vtk_status = models.CharField(max_length=16, choices=Run.Status.choices, default=Run.Status.PENDING)
    paraview_export_status = models.CharField(max_length=16, choices=Run.Status.choices, default=Run.Status.PENDING)

    # PID of the OpenFOAM subprocess currently running for this case, if
    # any -- lets the Stop button kill it directly rather than wait for it.
    pid = models.IntegerField(null=True, blank=True)

    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ("run", "name")
        ordering = ["run_id", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.run_id})"


class RunLogEntry(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    run = models.ForeignKey(Run, related_name="log_entries", on_delete=models.CASCADE)
    case = models.ForeignKey(
        SimulationCase, related_name="log_entries", null=True, blank=True, on_delete=models.SET_NULL
    )
    stage = models.CharField(max_length=32, blank=True)
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["run", "id"])]
        ordering = ["id"]

    def __str__(self) -> str:
        return f"[{self.level}] {self.message[:60]}"
