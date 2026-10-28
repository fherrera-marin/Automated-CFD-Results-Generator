from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import Run, RunLogEntry, RunStage, SimulationCase
from .parsing import parse_angles


class RunStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunStage
        fields = ["stage", "status", "celery_task_id", "started_at", "finished_at"]


class SimulationCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationCase
        fields = [
            "id",
            "name",
            "angle",
            "case_dir",
            "openfoam_status",
            "openfoam_step",
            "foam_to_vtk_status",
            "paraview_export_status",
            "error_message",
        ]


class RunLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = RunLogEntry
        fields = ["id", "case_id", "stage", "level", "message", "created_at"]


class RunSerializer(serializers.ModelSerializer):
    stages = RunStageSerializer(many=True, read_only=True)

    class Meta:
        model = Run
        fields = [
            "id",
            "name",
            "n_airfoils",
            "angles",
            "base_dir",
            "origin_dir",
            "status",
            "sdf_pkl_path",
            "cnn_dataset_path",
            "error_message",
            "created_at",
            "updated_at",
            "stages",
        ]
        read_only_fields = [
            "status",
            "sdf_pkl_path",
            "cnn_dataset_path",
            "error_message",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "base_dir": {"required": False, "allow_blank": True},
            "origin_dir": {"required": False, "allow_blank": True},
        }

    def validate_angles(self, value):
        if isinstance(value, str):
            try:
                value = parse_angles(value)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc)) from exc
        if not value:
            raise serializers.ValidationError("At least one angle is required.")
        return [float(a) for a in value]

    def validate(self, attrs):
        # A field-level validate_origin_dir() would only run when the
        # request actually includes "origin_dir" -- a client that omits the
        # key entirely (e.g. `JSON.stringify` dropping an `undefined` value
        # for a blank form field) skips it silently, so the fallback to
        # settings.DEFAULT_ORIGIN_DIR and the exists-on-disk check both have
        # to live here instead, where `attrs` reflects the full object
        # regardless of what the request included.
        origin_dir = attrs.get("origin_dir") or settings.DEFAULT_ORIGIN_DIR
        if not origin_dir:
            raise serializers.ValidationError(
                {"origin_dir": "origin_dir is required (no SIM_ORIGIN_DIR default configured)."}
            )
        path = Path(origin_dir)
        if not path.is_dir():
            raise serializers.ValidationError({"origin_dir": f"Origin directory does not exist: {path}"})
        attrs["origin_dir"] = str(path.resolve())
        return attrs

    def create(self, validated_data):
        base_dir = validated_data.pop("base_dir", "") or ""
        run = Run.objects.create(base_dir=base_dir, **validated_data)
        if not base_dir:
            run.base_dir = str(settings.SIM_BASE_DIR / f"run_{run.pk}")
            run.save(update_fields=["base_dir"])
        RunStage.objects.bulk_create([RunStage(run=run, stage=s) for s in Run.Stage.values])
        return run
