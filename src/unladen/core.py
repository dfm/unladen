# -*- coding: utf-8 -*-

__all__ = ["main"]

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Iterable, Optional

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
err = partial(click.secho, bold=True, fg="red", err=True)


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
    help="The target target directory for the output.",
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
    default="unladen@dfm.github.io",
    help="The email to use for git commits.",
    show_default=True,
)
@click.option(
    "--git",
    type=str,
    default="git",
    help="Path to the correct git executable.",
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
    git: str,
    source: str,
) -> None:
    if repo and target:
        err("Only one of 'repo' and 'target' can be specified")
        ctx.exit(1)
    if not (repo or target):
        err("Either 'repo' or 'target' must be specified")
        ctx.exit(1)

    source_dir = Path(source).resolve()

    # First get and parse the git ref
    if not ref:
        ref = get_ref(ctx=ctx, source=source_dir, git=git, verbose=verbose)
    parsed_ref = parse_ref(ctx=ctx, ref=ref, verbose=verbose)
    if not parsed_ref.name:
        err(f"Invalid ref: '{ref}'")
        ctx.exit(1)
    if verbose:
        out(f"Using git ref: '{parsed_ref.name}' (parsed from '{ref}')")

    # Get the git SHA
    if not sha:
        sha = get_sha(ctx=ctx, source=source_dir, git=git, verbose=verbose)
    if verbose and sha:
        out(f"Current git SHA: '{sha}'")

    if repo:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            checkout_or_init_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                name=name,
                email=email,
                git=git,
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
                sha=sha,
                force=force,
                git=git,
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
    **kwargs,
) -> subprocess.CompletedProcess:
    all_args = [git] + list(args)
    kwargs["capture_output"] = kwargs.get("capture_output", True)
    proc = subprocess.run(all_args, cwd=cwd, **kwargs)
    if verbose:
        msg = f"Running '{' '.join(all_args)}':\n"
        msg += format_command_output(proc.stdout)
        out(msg)
    if (verbose or check) and proc.returncode:
        msg = f"Command '{' '.join(all_args)}' failed with message:\n"
        msg += format_command_output(proc.stderr)
        err(msg)
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
            err("Couldn't infer the git ref; make sure you're in a git repo!")
            ctx.exit(1)
    return proc.stdout.decode("utf-8").strip()


def parse_ref(
    *, ctx: click.Context, ref: str, verbose: bool = False
) -> RefInfo:
    if ref.startswith("refs/tags/"):
        return RefInfo(name=slugify(ref[10:]), kind=RefKind.TAG)
    if ref.startswith("refs/heads/"):
        return RefInfo(name=slugify(ref[11:]), kind=RefKind.BRANCH)
    if verbose:
        err(f"Unrecognized ref format: {ref}")
    return RefInfo(name=slugify(ref), kind=RefKind.UNKNOWN)


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
            out(f"Checkout of {branch} failed; creating it fresh")
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
            out("Documentation is unchanged; skipping push")
        return

    msg = f"deploy {sha}" if sha else "deploy docs"
    msg = f'"{msg}"'
    if force:
        run(["commit", "--amend", "--date=now", "-m", msg])
        run(["push", "-fq", "upstream", f"HEAD:{branch}"])
    else:
        run(["commit", "-m", msg], check=True)
        run(["push", "-q", "upstream", f"HEAD:{branch}"])


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
