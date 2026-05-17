import json

from typer.testing import CliRunner

from devenv_doctor import cli

runner = CliRunner()


def patch_all_checks_passing(monkeypatch):
    monkeypatch.setattr(cli, "check_docker_cli_installed", lambda: (True, "ok"))
    monkeypatch.setattr(cli, "check_docker_daemon_accessible", lambda: (True, "ok"))
    monkeypatch.setattr(cli, "check_docker_compose_available", lambda: (True, "ok"))
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_env_file", lambda project_path: True)
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_env_example_file", lambda project_path: True)
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_build_services", lambda project_path: True)


def test_check_command_reports_ready_when_all_checks_pass(monkeypatch, tmp_path):
    patch_all_checks_passing(monkeypatch)

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 0
    assert "Status: Ready" in result.output
    assert "Summary: 13/13 passed, 0 failed." in result.output


def test_check_command_does_not_write_report_without_report_flag(
    monkeypatch,
    tmp_path,
):
    patch_all_checks_passing(monkeypatch)

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 0
    assert not (tmp_path / cli.DEFAULT_REPORT_FILENAME).exists()


def test_check_command_writes_default_json_report(monkeypatch, tmp_path):
    patch_all_checks_passing(monkeypatch)

    result = runner.invoke(cli.app, ["check", str(tmp_path), "--report"])

    report_file = tmp_path / cli.DEFAULT_REPORT_FILENAME
    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert f"Report written to {report_file}" in result.output
    assert report["project_path"] == str(tmp_path)
    assert report["status"] == "Ready"
    assert report["exit_code"] == 0
    assert report["summary"] == {"total": 13, "passed": 13, "failed": 0}
    assert len(report["checks"]) == 13
    assert report["errors"] == []
    assert report["warnings"] == []
    assert report["recommendations"] == []


def test_check_command_writes_custom_json_report_name(monkeypatch, tmp_path):
    patch_all_checks_passing(monkeypatch)

    result = runner.invoke(cli.app, ["check", str(tmp_path), "--report", "result.json"])

    report_file = tmp_path / "result.json"
    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert f"Report written to {report_file}" in result.output
    assert report["status"] == "Ready"


def test_check_command_writes_custom_json_report_path(monkeypatch, tmp_path):
    patch_all_checks_passing(monkeypatch)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_file = report_dir / "result.json"

    result = runner.invoke(
        cli.app,
        ["check", str(tmp_path), "--report", str(report_file)],
    )
    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert f"Report written to {report_file}" in result.output
    assert report["status"] == "Ready"


def test_check_command_reports_not_ready_in_json_report(monkeypatch, tmp_path):
    patch_all_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (False, "No Docker Compose file was found."),
    )
    monkeypatch.setattr(cli, "check_docker_compose_yaml_syntax", fail_if_called)
    monkeypatch.setattr(cli, "check_docker_compose_services_section", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        fail_if_called,
    )
    monkeypatch.setattr(cli, "check_docker_compose_build_contexts", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        fail_if_called,
    )

    result = runner.invoke(cli.app, ["check", str(tmp_path), "--report"])

    report_file = tmp_path / cli.DEFAULT_REPORT_FILENAME
    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert report["status"] == "Not Ready"
    assert report["exit_code"] == 1
    assert report["summary"] == {"total": 13, "passed": 5, "failed": 8}
    assert report["errors"][0] == {
        "check": "Compose file",
        "message": "No Docker Compose file was found.",
    }


def test_check_command_exits_2_when_report_parent_path_does_not_exist(
    monkeypatch,
    tmp_path,
):
    patch_all_checks_passing(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["check", str(tmp_path), "--report", str(tmp_path / "missing" / "report.json")],
    )

    assert result.exit_code == 2
    assert "Report path does not exist" in result.output
    assert not (tmp_path / "missing" / "report.json").exists()


def fail_if_called():
    raise AssertionError("should be skipped")


def patch_docker_checks_passing(monkeypatch):
    monkeypatch.setattr(cli, "check_docker_cli_installed", lambda: (True, "ok"))
    monkeypatch.setattr(cli, "check_docker_daemon_accessible", lambda: (True, "ok"))
    monkeypatch.setattr(cli, "check_docker_compose_available", lambda: (True, "ok"))
    monkeypatch.setattr(cli, "has_build_services", lambda project_path: True)
    monkeypatch.setattr(cli, "has_env_file", lambda project_path: True)
    monkeypatch.setattr(cli, "has_env_example_file", lambda project_path: True)


def test_check_command_skips_docker_dependent_checks_when_cli_is_missing(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cli,
        "check_docker_cli_installed",
        lambda: (False, "Docker CLI is not installed."),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_daemon_accessible",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_available",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_env_file", lambda project_path: True)
    monkeypatch.setattr(cli, "has_env_example_file", lambda project_path: True)
    monkeypatch.setattr(cli, "has_build_services", lambda project_path: True)

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Docker daemon: skipped because Docker CLI is not installed."
        in result.output
    )
    assert (
        "[FAIL] Docker Compose: skipped because Docker CLI is not installed."
        in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 10/13 passed, 3 failed." in result.output


def test_check_command_skips_compose_file_dependent_checks_when_file_is_missing(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (False, "No Docker Compose file was found."),
    )
    monkeypatch.setattr(cli, "check_docker_compose_yaml_syntax", fail_if_called)
    monkeypatch.setattr(cli, "check_docker_compose_services_section", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        fail_if_called,
    )
    monkeypatch.setattr(cli, "check_docker_compose_build_contexts", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Compose YAML: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Compose services: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Compose build: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Compose build contexts: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Compose host ports: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Host port availability: skipped because Compose file was not found."
        in result.output
    )
    assert (
        "[FAIL] Compose build context Dockerfiles: skipped because Compose file was not"
        " found." in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 5/13 passed, 8 failed." in result.output


def test_check_command_skips_yaml_dependent_checks_when_yaml_is_invalid(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (False, "Docker Compose file YAML has syntax errors."),
    )
    monkeypatch.setattr(cli, "check_docker_compose_services_section", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        fail_if_called,
    )
    monkeypatch.setattr(cli, "check_docker_compose_build_contexts", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Compose services: skipped because Compose YAML is not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose build: skipped because Compose YAML is not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose build contexts: skipped because Compose YAML is not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose host ports: skipped because Compose YAML is not valid."
        in result.output
    )
    assert (
        "[FAIL] Host port availability: skipped because Compose YAML is not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose build context Dockerfiles: skipped because Compose YAML is not"
        " valid." in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 6/13 passed, 7 failed." in result.output


def test_check_command_skips_services_dependent_checks_when_services_are_invalid(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (False, "The services section does not exist."),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        fail_if_called,
    )
    monkeypatch.setattr(cli, "check_docker_compose_build_contexts", fail_if_called)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        fail_if_called,
    )
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Compose build: skipped because Compose services are not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose build contexts: skipped because Compose services are not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose host ports: skipped because Compose services are not valid."
        in result.output
    )
    assert (
        "[FAIL] Host port availability: skipped because Compose services are not valid."
        in result.output
    )
    assert (
        "[FAIL] Compose build context Dockerfiles: skipped because Compose services are"
        " not valid." in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 7/13 passed, 6 failed." in result.output


def test_check_command_skips_dockerfile_check_when_no_service_uses_build(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_build_services", lambda project_path: False)
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_variables_match",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        fail_if_called,
    )

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Compose build context Dockerfiles: skipped because no service uses"
        " build." in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 12/13 passed, 1 failed." in result.output


def test_check_command_skips_env_example_check_when_env_file_is_missing(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(cli, "has_env_file", lambda project_path: False)
    monkeypatch.setattr(cli, "check_env_example_exists", fail_if_called)
    monkeypatch.setattr(cli, "check_env_variables_match", fail_if_called)

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Environment example: skipped because .env file was not found."
        in result.output
    )
    assert (
        "[FAIL] Environment variables: skipped because .env file was not found."
        in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 11/13 passed, 2 failed." in result.output


def test_check_command_skips_env_variables_check_when_env_example_file_is_missing(
    monkeypatch,
    tmp_path,
):
    patch_docker_checks_passing(monkeypatch)
    monkeypatch.setattr(
        cli,
        "check_docker_compose_file_exists",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_yaml_syntax",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_services_section",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_valid_build_or_image",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_duplicated_host_ports",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_host_ports_available",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_docker_compose_build_contexts_dockerfiles",
        lambda project_path: (True, "ok"),
    )
    monkeypatch.setattr(
        cli,
        "check_env_example_exists",
        lambda project_path: (
            False,
            ".env.example is missing while .env is being used.",
        ),
    )
    monkeypatch.setattr(cli, "has_env_file", lambda project_path: True)
    monkeypatch.setattr(cli, "has_env_example_file", lambda project_path: False)
    monkeypatch.setattr(cli, "check_env_variables_match", fail_if_called)

    result = runner.invoke(cli.app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "[FAIL] Environment variables: skipped because .env.example file was not found."
        in result.output
    )
    assert "Status: Not Ready" in result.output
    assert "Summary: 11/13 passed, 2 failed." in result.output
