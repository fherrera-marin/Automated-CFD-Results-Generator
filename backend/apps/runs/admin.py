from django.contrib import admin

from .models import Run, RunLogEntry, RunStage, SimulationCase


class RunStageInline(admin.TabularInline):
    model = RunStage
    extra = 0
    readonly_fields = ("celery_task_id", "started_at", "finished_at")


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "n_airfoils", "angles", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at", "sdf_pkl_path", "cnn_dataset_path")
    inlines = [RunStageInline]


@admin.register(SimulationCase)
class SimulationCaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "run",
        "name",
        "angle",
        "openfoam_status",
        "openfoam_step",
        "foam_to_vtk_status",
        "paraview_export_status",
    )
    list_filter = ("openfoam_status", "foam_to_vtk_status", "paraview_export_status")
    search_fields = ("name",)


@admin.register(RunLogEntry)
class RunLogEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "case", "stage", "level", "created_at")
    list_filter = ("level", "stage")
    readonly_fields = ("created_at",)
