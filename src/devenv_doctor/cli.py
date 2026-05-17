import json
from pathlib import Path

import typer

from devenv_doctor.runner import CheckRun, run_checks

app = typer.Typer(
    name="devenv-doctor",
    help="Analyze local Docker development environments.",
    add_completion=False,
    no_args_is_help=True,
)

DEFAULT_REPORT_FILENAME = "devenv-doctor-report.json"


@app.callback()
def root() -> None:
    pass


def _resolve_report_path(project_path: Path, report_arg: str | None) -> Path:
    if report_arg is None:
        return project_path / DEFAULT_REPORT_FILENAME

    report_path = Path(report_arg)
    if report_path.is_absolute():
        return report_path
    if report_path.parent == Path("."):
        return project_path / report_path
    return report_path


def _write_report(
    report_path: Path,
    project_path: Path,
    run: CheckRun,
) -> None:
    if not report_path.parent.is_dir():
        typer.secho(
            f"Report path does not exist: {report_path.parent}",
            fg="red",
            err=True,
        )
        raise typer.Exit(code=2)

    report = {
        "project_path": str(project_path),
        "status": run.status,
        "exit_code": run.exit_code,
        "summary": {
            "total": run.total,
            "passed": run.passed,
            "failed": run.failed,
            "skipped": run.skipped,
        },
        "checks": [result.to_dict() for result in run.results],
        "errors": [
            {"check": result.name, "message": result.message}
            for result in run.results
            if result.failed
        ],
        "warnings": [],
        "recommendations": [],
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Report written to {report_path}")


def _print_result_line(status: str, name: str, message: str) -> None:
    if status == "pass":
        typer.secho(f"[PASS] {name}: {message}", fg="green")
    elif status == "fail":
        typer.secho(f"[FAIL] {name}: {message}", fg="red")
    else:
        typer.echo(f"[SKIP] {name}: {message}")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def check(
    ctx: typer.Context,
    project_path: Path = typer.Argument(
        ".",
        help="Project path to analyze.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
    ),
    report: bool = typer.Option(
        False,
        "--report",
        help="Generate a JSON report. Optionally pass a report path after the flag.",
    ),
) -> None:
    """Run the development environment checks."""
    report_path = _resolve_report_path(project_path, ctx.args[0] if ctx.args else None)

    if ctx.args and not report:
        typer.secho(f"Unexpected argument: {ctx.args[0]}", fg="red", err=True)
        raise typer.Exit(code=2)
    if len(ctx.args) > 1:
        typer.secho(f"Unexpected argument: {ctx.args[1]}", fg="red", err=True)
        raise typer.Exit(code=2)

    typer.echo(f"Checking {project_path}")
    run = run_checks(project_path)

    for result in run.results:
        _print_result_line(result.status, result.name, result.message)

    typer.echo()
    typer.secho(f"Status: {run.status}", fg="green" if run.status == "Ready" else "red")
    typer.echo(
        f"Summary: {run.passed}/{run.total} passed, "
        f"{run.failed} failed, {run.skipped} skipped."
    )

    if report:
        _write_report(report_path, project_path, run)

    if run.failed:
        raise typer.Exit(code=1)
