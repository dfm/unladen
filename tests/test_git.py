# -*- coding: utf-8 -*-

import contextlib
import tempfile
from typing import Iterator

from unladen.git import Git


@contextlib.contextmanager
def get_temp_git_repo(git_path: str = "git") -> Iterator[Git]:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Git(temp_dir, git=git_path, verbose=True)
        repo.init_repo("test user", "test@email.com")
        yield repo


def test_checkout_orphan() -> None:
    with get_temp_git_repo() as repo:
        repo.checkout_orphan("test-branch")
        assert repo.run_output(["branch"]).strip() == "* test-branch"
