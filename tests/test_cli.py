# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest
from click.testing import CliRunner

from unladen import main


def test_branch() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        result = runner.invoke(
            main,
            [
                str(path),
                "--verbose",
                "--target",
                "test",
                "--ref",
                "refs/heads/main",
            ],
        )
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "main")


def test_tag() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        result = runner.invoke(
            main,
            [
                str(path),
                "--verbose",
                "--target",
                "test",
                "--ref",
                "refs/tags/v0.1.0",
            ],
        )
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "v0.1.0")


# def test_unknown() -> None:
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         path = make_test_docs()
#         result = runner.invoke(
#             main,
#             [
#                 str(path),
#                 "--verbose",
#                 "--target",
#                 "test",
#                 "--ref",
#                 "its/a/version",
#             ],
#         )
#         if result.exit_code:
#             print(result.output)
#         assert result.exit_code == 0
#         check_test_docs(Path("test"), "its-a-version")


def test_invalid_ref() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        result = runner.invoke(
            main,
            [str(path), "--target", "test", "--ref", "refs/tags/"],
        )
        assert result.exit_code


def test_fresh_repo() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo = Path("repo")
        create_git_repo(repo)
        path = make_test_docs()
        result = runner.invoke(
            main,
            [
                str(path),
                "--verbose",
                "--repo",
                str(repo.resolve() / ".git"),
                "--ref",
                "refs/heads/main",
            ],
        )
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(repo, "main", "gh-pages")


def test_user_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        write_config_file(Path("."), "test.toml")
        result = runner.invoke(main, ["--config", "test.toml", str(path)])
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "main")


def test_pyproject_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        write_config_file(path, "pyproject.toml")
        result = runner.invoke(main, [str(path)])
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "main")


def test_unladen_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        write_config_file(path, "unladen.toml")
        result = runner.invoke(main, [str(path)])
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "main")


@pytest.mark.skipif(
    sys.platform == "win32", reason="Skipping global config test on Windows"
)
def test_global_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cfg = Path.cwd() / "config"
        cfg.mkdir(parents=True, exist_ok=True)
        write_config_file(cfg, "unladen.toml")

        old_cfg_home = os.environ.get("XDG_CONFIG_HOME", None)
        os.environ["XDG_CONFIG_HOME"] = str(cfg)

        path = make_test_docs()
        result = runner.invoke(main, [str(path)])
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "main")

        if old_cfg_home is None:
            del os.environ["XDG_CONFIG_HOME"]
        else:
            os.environ["XDG_CONFIG_HOME"] = old_cfg_home


def make_test_docs() -> Path:
    path = Path("docs")
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "index.html", "w") as f:
        f.write("test")
    return path


def check_test_docs(
    path: Path, ref: str, branch: Optional[str] = None
) -> None:
    if branch:
        subprocess.run(["git", "checkout", branch], cwd=path, check=True)
    assert (path / ref / "index.html").exists()
    with open(path / ref / "index.html", "r") as f:
        assert f.read() == "test"


def create_git_repo(path: Path) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=path, check=True)


def write_config_file(path: Path, name: str) -> None:
    with open(path / name, "w") as f:
        f.write(
            """
[tool.unladen]
verbose = true
target = "test"
ref = "refs/heads/main"
"""
        )
