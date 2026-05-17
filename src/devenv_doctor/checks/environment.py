from pathlib import Path

from dotenv import dotenv_values


def has_env_file(project_path: Path) -> bool:
    return (project_path / ".env").is_file()


def has_env_example_file(project_path: Path) -> bool:
    return (project_path / ".env.example").is_file()


def _parse_env_keys(env_file: Path) -> set[str]:
    return set(dotenv_values(env_file).keys())


def check_env_example_exists(project_path: Path) -> tuple[bool, str]:
    if not has_env_file(project_path):
        return False, "No .env file was found."

    if not has_env_example_file(project_path):
        return False, ".env.example is missing while .env is being used."

    return True, ".env.example exists for the .env file."


def check_env_variables_match(project_path: Path) -> tuple[bool, str]:
    if not has_env_file(project_path):
        return False, "No .env file was found."
    if not has_env_example_file(project_path):
        return False, ".env.example file was not found."

    env_keys = _parse_env_keys(project_path / ".env")
    env_example_keys = _parse_env_keys(project_path / ".env.example")

    missing_in_example = sorted(env_keys - env_example_keys)
    extra_in_example = sorted(env_example_keys - env_keys)

    if missing_in_example or extra_in_example:
        issues = []
        if missing_in_example:
            issues.append(f"missing in .env.example: {', '.join(missing_in_example)}")
        if extra_in_example:
            issues.append(f"extra in .env.example: {', '.join(extra_in_example)}")
        issue_text = "; ".join(issues)
        return False, f".env and .env.example variables do not match ({issue_text})."

    return True, ".env and .env.example variables match."
