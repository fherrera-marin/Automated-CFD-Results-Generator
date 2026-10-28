from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

OPENFOAM_STEPS: list[list[str]] = [
    ["blockMesh"],
    ["surfaceFeatures"],
    ["snappyHexMesh", "-overwrite"],
    ["patchSummary"],
    ["potentialFoam"],
    ["simpleFoam"],
]


@dataclass
class StepResult:
    step: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class CaseResult:
    case_dir: Path
    steps: list[StepResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return not self.cancelled and bool(self.steps) and all(s.ok for s in self.steps)

    @property
    def failed_step(self) -> StepResult | None:
        for s in self.steps:
            if not s.ok:
                return s
        return None


def capture_env(env_script: str | Path) -> dict[str, str]:
    """
    Run the BlueCFD/OpenFOAM environment-activation batch script
    (e.g. setvars_OF8.bat) and capture the resulting environment (PATH,
    WM_PROJECT_DIR, ...) as a dict, so every real OpenFOAM command can reuse
    it via `env=` instead of re-activating the environment each time.

    This script also `cd`s into its own install directory as a side effect,
    so it CANNOT be chained directly before a real command (`cmd /c
    "<script>" && blockMesh` would run blockMesh from the wrong working
    directory). Capturing the environment once here and passing it
    explicitly alongside our own `cwd=<case_dir>` on every subsequent
    subprocess call avoids that entirely.
    """
    # shell=True (not an explicit ["cmd", "/c", ...] list) because Windows
    # CreateProcess always re-joins an argv list into a single command-line
    # string anyway, and subprocess's own quoting of that string uses
    # backslash-escaped quotes, which cmd.exe's /c parser does not
    # understand -- it corrupts any path containing spaces.
    proc = subprocess.run(
        f'call "{env_script}" && set',
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    )
    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            env[key] = value
    return env


def run_command(
    cmd: list[str],
    case_dir: str | Path,
    env: dict[str, str],
    on_start: Callable[[int], None] | None = None,
) -> StepResult:
    """
    Run one OpenFOAM/BlueCFD command (e.g. ["foamToVTK"]) inside `case_dir`,
    using an already-captured environment (see `capture_env`).

    On Windows, CreateProcess resolves a bare executable name using the
    CALLING process's PATH, not the `env=` dict handed to the child -- so a
    captured BlueCFD PATH only takes effect if we resolve the executable
    ourselves first.

    `on_start`, if given, is invoked with the subprocess's PID as soon as
    it's spawned (before waiting for it to finish), so a caller can record
    it somewhere a "Stop" action can find and kill it directly -- Celery's
    own task-revoke/terminate doesn't give per-task process control under
    Windows' required `--pool=solo` (see docs/operations.md).
    """
    exe = shutil.which(cmd[0], path=env.get("PATH", ""))
    if exe is None:
        return StepResult(
            step=cmd[0],
            returncode=-1,
            stdout="",
            stderr=f"'{cmd[0]}' not found on PATH from the activated OpenFOAM environment.",
        )

    proc = subprocess.Popen(
        [exe, *cmd[1:]], cwd=str(case_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if on_start is not None:
        on_start(proc.pid)
    stdout, stderr = proc.communicate()
    return StepResult(step=cmd[0], returncode=proc.returncode, stdout=stdout, stderr=stderr)


def simulate_case(
    case_dir: str | Path,
    env_script: str | Path,
    on_step: Callable[[str, StepResult], None] | None = None,
    on_start: Callable[[int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> CaseResult:
    """
    Run the 6 OpenFOAM steps (blockMesh, surfaceFeatures, snappyHexMesh,
    patchSummary, potentialFoam, simpleFoam) against `case_dir`.

    Stops at the first failing step but never raises: the caller decides
    what a failed case means for the rest of a batch (see
    backend/apps/runs/tasks.py::run_openfoam_case, which does NOT abort the
    whole batch on one case's failure -- unlike the legacy
    scripts/Openfoam_blueCFD.py).

    `should_cancel`, if given, is checked before each step; if it returns
    True, no further steps run and the result comes back with
    `cancelled=True`. It won't interrupt a step already in progress --
    that's what `on_start`'s PID is for, so the caller can kill it directly.
    """
    case_dir = Path(case_dir)
    result = CaseResult(case_dir=case_dir)
    env = capture_env(env_script)

    for cmd in OPENFOAM_STEPS:
        if should_cancel is not None and should_cancel():
            result.cancelled = True
            break

        step_result = run_command(cmd, case_dir, env, on_start=on_start)
        result.steps.append(step_result)
        if on_step is not None:
            on_step(cmd[0], step_result)
        if not step_result.ok:
            break

    return result
