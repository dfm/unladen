# -*- coding: utf-8 -*-

__all__ = ["Git"]

import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

import click


def format_command_output(message: bytes) -> str:
    return "\n".join(
        f"  > {line}" for line in message.decode("utf-8").strip().splitlines()
    )


class Git:
    def __init__(
        self,
        path: Union[Path, str],
        *,
        git: str = "git",
        verbose: bool = False,
    ):
        self.path = path
        self.git = git
        self.verbose = verbose

    def run(
        self,
        args: Iterable[str],
        *,
        check: bool = True,
        verbose: Optional[bool] = None,
    ) -> "subprocess.CompletedProcess[bytes]":
        if verbose is None:
            verbose = self.verbose
        all_args = [self.git] + list(args)
        proc = subprocess.run(all_args, cwd=self.path, capture_output=True)
        if verbose:
            msg = f"Running '{' '.join(all_args)}':\n"
            msg += format_command_output(proc.stdout)
            click.secho(msg)
        if (verbose or check) and proc.returncode:
            msg = f"Command '{' '.join(all_args)}' failed with message:\n"
            msg += format_command_output(proc.stderr)
            if check:
                raise RuntimeError(msg)
            else:
                click.secho(msg, err=True)
        return proc

    def run_output(self, args: Iterable[str], *, check: bool = True) -> str:
        return self.run(args, check=check).stdout.decode("utf-8")

    def get_sha(self) -> str:
        proc = self.run(["rev-parse", "--short", "HEAD"], check=False)
        return proc.stdout.decode("utf-8").strip()

    def get_ref(self) -> str:
        proc = self.run(["symbolic-ref", "-q", "HEAD"], check=False)
        if proc.returncode:
            proc = self.run(
                ["describe", "--tags", "--exact-match"], check=False
            )
            if proc.returncode:
                raise RuntimeError(
                    "Couldn't infer the git ref; are you in a git repo!"
                )
        return proc.stdout.decode("utf-8").strip()

    def init_repo(self, name: str, email: str) -> None:
        self.run(["init"])
        self.run(["config", "user.name", name])
        self.run(["config", "user.email", email])
        self.run(["config", "init.defaultBranch", "main"], check=False)

    def checkout_orphan(self, branch: str) -> None:
        self.run(["checkout", "--orphan", branch])
        self.run(["commit", "--allow-empty", "-m", '"Initial empty commit"'])

    def checkout_or_init_repo(
        self,
        *,
        repo: str,
        branch: str,
        name: str,
        email: str,
    ) -> None:

        # Initialize the repo and fetch from the remote
        self.init_repo(name, email)
        self.run(["remote", "add", "upstream", repo])
        self.run(["fetch", "upstream"])

        # Either checkout the right branch or create it
        proc = self.run(
            ["checkout", "-b", branch, f"upstream/{branch}"], check=False
        )
        if proc.returncode:
            if self.verbose:
                click.secho(f"Checkout of {branch} failed; creating it fresh")
            self.checkout_orphan(branch)

    def push_to_repo(
        self,
        repo: str,
        branch: str,
        *,
        force: bool = False,
        sha: Optional[str] = None,
    ) -> None:
        self.run(["add", "-A", "."])

        # Check to see if there were any changes
        proc = self.run(
            ["diff", "--cached", "--exit-code"], check=False, verbose=False
        )
        if proc.returncode == 0:
            if self.verbose:
                click.secho("Documentation is unchanged; skipping push")
            return

        msg = f"deploy {sha}" if sha else "deploy docs"
        msg = f'"{msg}"'
        if force:
            self.run(["commit", "--amend", "--date=now", "-m", msg])
            self.run(["push", "-fq", repo, f"HEAD:{branch}"])
        else:
            self.run(["commit", "-m", msg], check=True)
            self.run(["push", "-q", repo, f"HEAD:{branch}"])
