# -*- coding: utf-8 -*-

import tempfile
from pathlib import Path

from unladen import versions
from unladen.filesystem import copy_source_to_target


def test_default_copy() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        with tempfile.TemporaryDirectory() as source_dir:
            with open(Path(source_dir) / "test.html", "w") as f:
                f.write("testing!")

            copy_source_to_target(
                source=Path(source_dir),
                target=Path(target_dir),
                version=versions.parse("refs/heads/main"),
                base_url="http://localhost:5000",
                verbose=True,
            )

        with open(Path(target_dir) / "main" / "test.html", "r") as f:
            assert f.read() == "testing!"


def test_correct_alias() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        with tempfile.TemporaryDirectory() as v2:
            with open(Path(v2) / "test.html", "w") as f:
                f.write("v2")
            copy_source_to_target(
                source=Path(v2),
                target=Path(target_dir),
                version=versions.parse("refs/tags/v0.2.3"),
                base_url="http://localhost:5000",
                verbose=True,
            )

        with tempfile.TemporaryDirectory() as v1:
            with open(Path(v1) / "test.html", "w") as f:
                f.write("v1")
            copy_source_to_target(
                source=Path(v1),
                target=Path(target_dir),
                version=versions.parse("refs/tags/v0.1.0"),
                base_url="http://localhost:5000",
                verbose=True,
            )

        with open(Path(target_dir) / "stable" / "test.html", "r") as f:
            assert f.read() == "v2"
