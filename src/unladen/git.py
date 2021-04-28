# -*- coding: utf-8 -*-

__all__ = ["get_ref", "get_sha", "checkout_or_init_repo", "push_to_repo"]

import subprocess
from functools import partial
from pathlib import Path
from typing import Iterable, Optional

import click


def format_command_output(message: bytes) -> str:
    return "\n".join(
        f"  > {line}" for line in message.decode("utf-8").strip().splitlines()
    )


def exec_git(
    args: Iterable[str],
    *,
    ctx: click.Context,
    git: str,
    cwd: Optional[Path] = None,
    check: bool = True,
    verbose: bool = False,
) -> "subprocess.CompletedProcess[bytes]":
    all_args = [git] + list(args)
    proc = subprocess.run(all_args, cwd=cwd, capture_output=True)
    if verbose:
        msg = f"Running '{' '.join(all_args)}':\n"
        msg += format_command_output(proc.stdout)
        click.secho(msg)
    if (verbose or check) and proc.returncode:
        msg = f"Command '{' '.join(all_args)}' failed with message:\n"
        msg += format_command_output(proc.stderr)
        click.secho(msg, err=True)
        if check:
            ctx.exit(1)
    return proc


def get_sha(
    *,
    ctx: click.Context,
    source: Path,
    git: str,
    verbose: bool = False,
) -> Optional[str]:
    proc = exec_git(
        ["rev-parse", "--short", "HEAD"],
        ctx=ctx,
        git=git,
        cwd=source,
        check=False,
        verbose=verbose,
    )
    return proc.stdout.decode("utf-8").strip()


def get_ref(
    *,
    ctx: click.Context,
    source: Path,
    git: str,
    verbose: bool = False,
) -> str:
    proc = exec_git(
        ["symbolic-ref", "-q", "HEAD"],
        ctx=ctx,
        git=git,
        cwd=source,
        check=False,
        verbose=verbose,
    )
    if proc.returncode:
        proc = exec_git(
            ["describe", "--tags", "--exact-match"],
            ctx=ctx,
            git=git,
            cwd=source,
            check=False,
            verbose=verbose,
        )
        if proc.returncode:
            click.secho(
                "Couldn't infer the git ref; make sure you're in a git repo!",
                err=True,
            )
            ctx.exit(1)
    return proc.stdout.decode("utf-8").strip()


def checkout_or_init_repo(
    *,
    ctx: click.Context,
    repo: str,
    branch: str,
    cwd: Path,
    name: str,
    email: str,
    git: str,
    verbose: bool = False,
) -> None:
    run = partial(
        exec_git, ctx=ctx, cwd=cwd, git=git, verbose=verbose, check=True
    )

    # Initialize the repo and fetch from the remote
    run(["init"])
    run(["remote", "add", "upstream", repo])
    run(["config", "user.name", name])
    run(["config", "user.email", email])
    run(["fetch", "upstream"])

    # Either checkout the right branch or create it
    proc = run(["checkout", "-b", branch, f"upstream/{branch}"], check=False)
    if proc.returncode:
        if verbose:
            click.secho(f"Checkout of {branch} failed; creating it fresh")
        run(["checkout", "--orphan", branch])
        run(["commit", "--allow-empty", "-m", '"Initial empty commit"'])


def push_to_repo(
    *,
    ctx: click.Context,
    repo: str,
    branch: str,
    cwd: Path,
    sha: Optional[str],
    force: bool,
    git: str,
    verbose: bool = False,
) -> None:
    run = partial(
        exec_git, ctx=ctx, cwd=cwd, git=git, verbose=verbose, check=True
    )
    run(["add", "-A", "."])

    # Check to see if there were any changes
    proc = run(["diff", "--cached", "--exit-code"], check=False)
    if proc.returncode == 0:
        if verbose:
            click.secho("Documentation is unchanged; skipping push")
        return

    msg = f"deploy {sha}" if sha else "deploy docs"
    msg = f'"{msg}"'
    if force:
        run(["commit", "--amend", "--date=now", "-m", msg])
        run(["push", "-fq", "upstream", f"HEAD:{branch}"])
    else:
        run(["commit", "-m", msg], check=True)
        run(["push", "-q", "upstream", f"HEAD:{branch}"])
