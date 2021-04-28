# -*- coding: utf-8 -*-

__all__ = ["main"]

import shutil
import tempfile
from pathlib import Path
from typing import Optional

import click

from . import config, git, refs
from .unladen_version import version as __version__


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
    "--git-path",
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
    required=False,
    is_eager=True,
)
@click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        allow_dash=False,
        path_type=str,
    ),
    is_eager=True,
    callback=config.read_config_toml,
    help="Read configuration from FILE path.",
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
    git_path: str,
    source: Optional[str],
    config: Optional[str],
) -> None:
    if not source:
        raise click.BadOptionUsage(
            "source", "Missing required parameter 'source'"
        )
    if not (repo or target):
        raise click.BadOptionUsage(
            "repo", "Either 'repo' or 'target' must be specified"
        )

    source_dir = Path(source).resolve()

    # First get and parse the git ref
    if not ref:
        ref = git.get_ref(
            ctx=ctx, source=source_dir, git=git_path, verbose=verbose
        )
    parsed_ref = refs.parse_ref(ref=ref, verbose=verbose)
    if not parsed_ref:
        raise click.BadOptionUsage(
            "ref", f"The provided or inferred git ref is invalid: {ref}"
        )
    if verbose:
        click.secho(f"Using git ref: '{parsed_ref}' (parsed from '{ref}')")

    # Get the git SHA
    if not sha:
        sha = git.get_sha(
            ctx=ctx, source=source_dir, git=git_path, verbose=verbose
        )
    if verbose and sha:
        click.secho(f"Current git SHA: '{sha}'")

    if target:
        target_dir = Path(target).resolve()
        copy_source_to_target(
            ctx=ctx,
            source=source_dir,
            target=target_dir,
            ref=parsed_ref,
            verbose=verbose,
        )

    else:
        assert repo is not None
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            git.checkout_or_init_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                name=name,
                email=email,
                git=git_path,
                verbose=verbose,
            )
            copy_source_to_target(
                ctx=ctx,
                source=source_dir,
                target=target_dir,
                ref=parsed_ref,
                verbose=verbose,
            )
            git.push_to_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                sha=sha,
                force=force,
                git=git_path,
                verbose=verbose,
            )


def copy_source_to_target(
    *,
    ctx: click.Context,
    source: Path,
    target: Path,
    ref: str,
    verbose: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    fullpath = target / ref

    # Delete any existing directory or file at the target path
    if fullpath.exists():
        if verbose:
            click.secho(f"{fullpath} exists, overwriting")
        if fullpath.is_dir():
            shutil.rmtree(fullpath)
        else:
            fullpath.unlink()

    # Do the copy
    shutil.copytree(source, fullpath)


def slugify(value: str) -> str:
    return value.replace("/", "-")
