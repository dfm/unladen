# -*- coding: utf-8 -*-

import subprocess
from pathlib import Path

from click.testing import CliRunner

from unladen import main


def make_test_docs() -> Path:
    path = Path("docs")
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "index.html", "w") as f:
        f.write("test")
    return path


def check_test_docs(path: Path, ref: str, branch: str = None) -> bool:
    if branch:
        subprocess.run(["git", "checkout", branch], cwd=path, check=True)
    assert (path / ref / "index.html").exists()
    with open(path / ref / "index.html", "r") as f:
        assert f.read() == "test"


def create_git_repo(path: Path) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=path, check=True)


def test_branch():
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


def test_tag():
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


def test_unknown():
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
                "its/a/version",
            ],
        )
        if result.exit_code:
            print(result.output)
        assert result.exit_code == 0
        check_test_docs(Path("test"), "its-a-version")


def test_invalid_ref():
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = make_test_docs()
        result = runner.invoke(
            main,
            [str(path), "--target", "test", "--ref", "refs/tags/"],
        )
        assert result.exit_code


def test_fresh_repo():
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
        check_test_docs(repo, "main", "gh-pages")
        assert result.exit_code == 0
