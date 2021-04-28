# -*- coding: utf-8 -*-

__all__ = ["main"]

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Optional

import click

from .unladen_version import version as __version__


class RefKind(Enum):
    UNKNOWN = 0
    TAG = 1
    BRANCH = 2


@dataclass
class RefInfo:
    name: str
    kind: RefKind


out = partial(click.secho, err=True)
err = partial(click.secho, fg="red", err=True)


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(version=__version__)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Log more verbosely.",
)
@click.option(
    "--ref",
    type=str,
    help="The git ref that is being built.",
)
@click.option(
    "--sha",
    type=str,
    help="The git SHA that is being built.",
)
@click.option(
    "--target",
    type=click.Path(file_okay=False, dir_okay=True),
    help="The target git repository for the output.",
)
@click.option(
    "--repo",
    type=str,
    help="The target git repository for the output.",
)
@click.option(
    "-b",
    "--branch",
    type=str,
    default="gh-pages",
    help="The branch to use on the target repository.",
    show_default=True,
)
@click.option(
    "--force",
    is_flag=True,
    help="Force push docs instead of saving history.",
)
@click.option(
    "--name",
    type=str,
    default="unladen",
    help="The name to use for git commits.",
    show_default=True,
)
@click.option(
    "--email",
    type=str,
    default="unladen@git",
    help="The email to use for git commits.",
    show_default=True,
)
@click.argument(
    "source",
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
    ),
)
@click.pass_context
def main(
    ctx: click.Context,
    verbose: bool,
    ref: Optional[str],
    sha: Optional[str],
    target: Optional[str],
    repo: Optional[str],
    branch: str,
    force: bool,
    name: str,
    email: str,
    source: str,
) -> None:
    if repo and target:
        err("💔 Only one of 'repo' and 'target' can be specified")
        ctx.exit(1)
    if not (repo or target):
        err("💔 Either 'repo' or 'target' must be specified")
        ctx.exit(1)

    # First get and parse the git ref
    if not ref:
        ref = get_ref(ctx=ctx, verbose=verbose)
    parsed_ref = parse_ref(ctx=ctx, ref=ref, verbose=verbose)
    if not parsed_ref.name:
        err(f"💔 Invalid ref: '{ref}'")
        ctx.exit(2)
    if verbose:
        out(f"Using git ref: '{parsed_ref.name}' (parsed from '{ref}')")

    # Get the git SHA
    if not sha:
        sha = get_sha(ctx=ctx, verbose=verbose)
    if verbose and sha:
        out(f"Current git SHA: '{sha}'")

    # Copy files
    source_dir = Path(source).resolve()

    if repo:
        author = f"{name} <{email}>"
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            checkout_or_init_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                author=author,
                verbose=verbose,
            )
            copy_source_to_target(
                ctx=ctx,
                source=source_dir,
                target=target_dir,
                ref=parsed_ref,
                verbose=verbose,
            )
            push_to_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                author=author,
                sha=sha,
                force=force,
                verbose=verbose,
            )

    else:
        assert target is not None
        target_dir = Path(target).resolve()
        copy_source_to_target(
            ctx=ctx,
            source=source_dir,
            target=target_dir,
            ref=parsed_ref,
            verbose=verbose,
        )


def get_sha(*, ctx: click.Context, verbose: bool = False) -> Optional[str]:
    proc = subprocess.run(
        "git rev-parse --short HEAD", shell=True, capture_output=True
    )
    if proc.returncode:
        err("💔 Couldn't get git SHA; make sure you're in a git repo!")
        return None
    return proc.stdout.decode("utf-8").strip()


def get_ref(*, ctx: click.Context, verbose: bool = False) -> str:
    ref = os.environ.get("GITHUB_REF", "").strip()
    if not ref:
        proc = subprocess.run(
            "git symbolic-ref -q HEAD || git describe --tags --exact-match",
            shell=True,
            capture_output=True,
        )
        if proc.returncode:
            err(
                "💔 Couldn't infer the git ref; make sure you're in a git repo!"
            )
            ctx.exit(3)
        ref = proc.stdout.decode("utf-8").strip()
    return ref


def parse_ref(
    *, ctx: click.Context, ref: str, verbose: bool = False
) -> RefInfo:
    if ref.startswith("refs/tags/"):
        return RefInfo(name=slugify(ref[10:]), kind=RefKind.TAG)
    if ref.startswith("refs/heads/"):
        return RefInfo(name=slugify(ref[11:]), kind=RefKind.BRANCH)
    if verbose:
        err(f"💔 Unrecognized ref format: {ref}")
    return RefInfo(name=slugify(ref), kind=RefKind.UNKNOWN)


def checkout_or_init_repo(
    *,
    ctx: click.Context,
    repo: str,
    branch: str,
    cwd: Path,
    author: str,
    verbose: bool = False,
) -> None:
    run = partial(subprocess.run, cwd=cwd, capture_output=True)

    # Initialize the repo and fetch from the remote
    run(["git", "init"], check=True)
    run(["git", "remote", "add", "upstream", repo], check=True)
    proc: subprocess.CompletedProcess = run(
        ["git", "fetch", "upstream"], cwd=cwd
    )
    if proc.returncode:
        err(f"💔 Couldn't fetch git repo from {repo}")
        if verbose:
            err(
                " -> Full output from `git fetch`:\n\n"
                f"{proc.stderr.decode('utf-8')}"
            )
        ctx.exit(4)

    # Either checkout the right branch or create it
    proc = run(["git", "checkout", "-b", branch, f"upstream/{branch}"])
    if proc.returncode:
        if verbose:
            out(f"Checkout of {branch} failed; creating it fresh")
        run(["git", "checkout", "--orphan", branch], check=True)
        run(
            [
                "git",
                "commit",
                "--allow-empty",
                f'--author="{author}"',
                "-m",
                '"Initial empty commit"',
            ]
        )


def push_to_repo(
    *,
    ctx: click.Context,
    repo: str,
    branch: str,
    cwd: Path,
    author: str,
    sha: Optional[str],
    force: bool,
    verbose: bool = False,
) -> None:
    run = partial(subprocess.run, cwd=cwd, capture_output=True)
    run(["git", "add", "-A", "."], check=True)

    # Check to see if there were any changes
    proc = run(["git", "diff", "--cached", "--exit-code"])
    if proc.returncode == 0:
        if verbose:
            out("Documentation is unchanged; skipping push")
        return

    msg = f"deploy {sha}" if sha else "deploy docs"
    msg = f'"{msg}"'
    if force:
        run(["git", "commit", "--amend", "--date=now", "-m", msg], check=True)
        run(["git", "push", "-fq", "upstream", f"HEAD:{branch}"], check=True)
    else:
        run(["git", "commit", "-m", msg], check=True)
        run(["git", "push", "-q", "upstream", f"HEAD:{branch}"], check=True)


def copy_source_to_target(
    *,
    ctx: click.Context,
    source: Path,
    target: Path,
    ref: RefInfo,
    verbose: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    fullpath = target / ref.name

    # Delete any existing directory or file at the target path
    if fullpath.exists():
        if verbose:
            out(f"{fullpath} exists, overwriting")
        if fullpath.is_dir():
            shutil.rmtree(fullpath)
        else:
            fullpath.unlink()

    # Do the copy
    shutil.copytree(source, fullpath)


def slugify(value: str) -> str:
    return value.replace("/", "-")
