import json
from collections.abc import Callable
from pathlib import Path

import typer

from devenv_doctor.checks.compose import (
    check_docker_compose_available,
    check_docker_compose_build_contexts,
    check_docker_compose_build_contexts_dockerfiles,
    check_docker_compose_duplicated_host_ports,
    check_docker_compose_file_exists,
    check_docker_compose_host_ports_available,
    check_docker_compose_services_section,
    check_docker_compose_valid_build_or_image,
    check_docker_compose_yaml_syntax,
)
from devenv_doctor.checks.compose_utils import has_build_services
from devenv_doctor.checks.docker import (
    check_docker_cli_installed,
    check_docker_daemon_accessible,
)
from devenv_doctor.checks.environment import (
    check_env_example_exists,
    check_env_variables_match,
    has_env_example_file,
    has_env_file,
)

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
    status: str,
    exit_code: int,
    checks: list[dict[str, str]],
    passed: int,
    failed: int,
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
        "status": status,
        "exit_code": exit_code,
        "summary": {
            "total": len(checks),
            "passed": passed,
            "failed": failed,
        },
        "checks": checks,
        "errors": [
            {"check": check["name"], "message": check["message"]}
            for check in checks
            if check["status"] in {"fail", "skip"}
        ],
        "warnings": [],
        "recommendations": [],
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Report written to {report_path}")


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
    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("Docker CLI", lambda: check_docker_cli_installed()),
        ("Docker daemon", lambda: check_docker_daemon_accessible()),
        ("Docker Compose", lambda: check_docker_compose_available()),
        ("Compose file", lambda: check_docker_compose_file_exists(project_path)),
        ("Compose YAML", lambda: check_docker_compose_yaml_syntax(project_path)),
        (
            "Compose services",
            lambda: check_docker_compose_services_section(project_path),
        ),
        (
            "Compose build",
            lambda: check_docker_compose_valid_build_or_image(project_path),
        ),
        (
            "Compose build contexts",
            lambda: check_docker_compose_build_contexts(project_path),
        ),
        (
            "Compose host ports",
            lambda: check_docker_compose_duplicated_host_ports(project_path),
        ),
        (
            "Host port availability",
            lambda: check_docker_compose_host_ports_available(project_path),
        ),
        (
            "Compose build context Dockerfiles",
            lambda: check_docker_compose_build_contexts_dockerfiles(project_path),
        ),
        (
            "Environment example",
            lambda: check_env_example_exists(project_path),
        ),
        (
            "Environment variables",
            lambda: check_env_variables_match(project_path),
        ),
    ]

    typer.echo(f"Checking {project_path}")
    # TODO: Implement diferenciation of blocking, warning and recommended issue levels.
    passed = 0
    failed = 0
    check_results: list[dict[str, str]] = []
    docker_cli_available = True
    docker_compose_file_exists = True
    docker_compose_file_syntax_is_valid = True
    docker_compose_services_section_is_valid = True
    report_path = _resolve_report_path(project_path, ctx.args[0] if ctx.args else None)

    if ctx.args and not report:
        typer.secho(f"Unexpected argument: {ctx.args[0]}", fg="red", err=True)
        raise typer.Exit(code=2)

    for name, run_check in checks:
        if name in {"Docker daemon", "Docker Compose"} and not docker_cli_available:
            failed += 1
            message = "skipped because Docker CLI is not installed."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if name == "Compose YAML" and not docker_compose_file_exists:
            failed += 1
            message = "skipped because Compose file was not found."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if (
            name
            in {
                "Compose services",
                "Compose build",
                "Compose build contexts",
                "Compose host ports",
                "Host port availability",
            }
            and not docker_compose_file_exists
        ):
            failed += 1
            message = "skipped because Compose file was not found."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if (
            name
            in {
                "Compose services",
                "Compose build",
                "Compose build contexts",
                "Compose host ports",
                "Host port availability",
            }
            and not docker_compose_file_syntax_is_valid
        ):
            failed += 1
            message = "skipped because Compose YAML is not valid."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if (
            name
            in {
                "Compose build",
                "Compose build contexts",
                "Compose host ports",
                "Host port availability",
            }
            and not docker_compose_services_section_is_valid
        ):
            failed += 1
            message = "skipped because Compose services are not valid."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if name == "Compose build context Dockerfiles":
            if not docker_compose_file_exists:
                failed += 1
                message = "skipped because Compose file was not found."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue
            if not docker_compose_file_syntax_is_valid:
                failed += 1
                message = "skipped because Compose YAML is not valid."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue
            if not docker_compose_services_section_is_valid:
                failed += 1
                message = "skipped because Compose services are not valid."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue
            if not has_build_services(project_path):
                failed += 1
                message = "skipped because no service uses build."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue
        if name == "Environment example" and not has_env_file(project_path):
            failed += 1
            message = "skipped because .env file was not found."
            check_results.append({"name": name, "status": "skip", "message": message})
            typer.echo(f"[FAIL] {name}: {message}")
            continue
        if name == "Environment variables":
            if not has_env_file(project_path):
                failed += 1
                message = "skipped because .env file was not found."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue
            if not has_env_example_file(project_path):
                failed += 1
                message = "skipped because .env.example file was not found."
                check_results.append(
                    {"name": name, "status": "skip", "message": message}
                )
                typer.echo(f"[FAIL] {name}: {message}")
                continue

        ok, message = run_check()

        if name == "Docker CLI":
            docker_cli_available = ok

        if name == "Compose file":
            docker_compose_file_exists = ok

        if name == "Compose YAML":
            docker_compose_file_syntax_is_valid = ok

        if name == "Compose services":
            docker_compose_services_section_is_valid = ok

        if ok:
            passed += 1
            check_results.append({"name": name, "status": "pass", "message": message})
            typer.secho(f"[PASS] {name}: {message}", fg="green")
        else:
            failed += 1
            check_results.append({"name": name, "status": "fail", "message": message})
            typer.secho(f"[FAIL] {name}: {message}", fg="red")

    total = len(checks)
    status = "Ready" if failed == 0 else "Not Ready"

    typer.echo()
    typer.secho(f"Status: {status}", fg="green" if status == "Ready" else "red")
    typer.echo(f"Summary: {passed}/{total} passed, {failed} failed.")

    exit_code = 1 if failed else 0
    if report:
        _write_report(
            report_path,
            project_path,
            status,
            exit_code,
            check_results,
            passed,
            failed,
        )

    if failed:
        raise typer.Exit(code=1)
