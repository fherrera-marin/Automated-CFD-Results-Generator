import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("cfd_pipeline")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.task_routes = {
    "apps.runs.tasks.run_openfoam_case": {"queue": "cfd"},
    "apps.runs.tasks.run_foam_to_vtk_case": {"queue": "cfd"},
    "apps.runs.tasks.run_paraview_export_case": {"queue": "cfd"},
}
