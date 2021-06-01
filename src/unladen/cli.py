# -*- coding: utf-8 -*-

__all__ = ["main"]

import json
import tempfile
from collections import Mapping
from pathlib import Path
from typing import Optional, Tuple, Union

import click

from . import filesystem, git, versions
from .config import find_project_root, read_config_toml
from .unladen_version import version as __version__


def _parse_rule(value: Union[str, Mapping[str, str]]) -> versions.Rule:
    if isinstance(value, str):
        mapping = json.loads(value)
    else:
        mapping = value
    return (str(mapping["from"]).strip(), str(mapping["to"]).strip())


def parse_rule(
    ctx: click.Context,
    param: Union[click.Parameter, click.Option],
    value: Tuple[Union[str, Mapping[str, str]]],
) -> Tuple[versions.Rule, ...]:
    value = value if value else ()
    results = []
    for v in value:
        try:
            results.append(_parse_rule(v))
        except (TypeError, KeyError):
            raise click.BadOptionUsage(param.name, f"Invalid rule: {v}")
    return tuple(results)


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
    help="The target directory for the output.",
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
    "--base-url",
    type=str,
    help="The base URL of the hosted documentation.",
)
@click.option(
    "--no-version-dropdown",
    is_flag=True,
    help="Don't inject the version dropdown into the HTML.",
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
@click.option(
    "--version-rule",
    "version_rules",
    type=str,
    multiple=True,
    callback=parse_rule,
    help="The rules to map refs to versions.",
)
@click.option(
    "--name-rule",
    "name_rules",
    type=str,
    multiple=True,
    callback=parse_rule,
    help="The rules to map refs to names.",
)
@click.option(
    "--path-rule",
    "path_rules",
    type=str,
    multiple=True,
    callback=parse_rule,
    help="The rules to map refs to paths.",
)
@click.option(
    "--alias-rule",
    "alias_rules",
    type=str,
    multiple=True,
    callback=parse_rule,
    help="The rules to map refs to aliases.",
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
    callback=read_config_toml,
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
    base_url: Optional[str],
    no_version_dropdown: bool,
    force: bool,
    name: str,
    email: str,
    git_path: str,
    version_rules: Tuple[versions.Rule, ...],
    name_rules: Tuple[versions.Rule, ...],
    path_rules: Tuple[versions.Rule, ...],
    alias_rules: Tuple[versions.Rule, ...],
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
    print("base_url", base_url)
    print("target", target)

    project_root = find_project_root((source,))
    source_dir = Path(source).resolve()
    source_repo = git.Git(project_root, git=git_path, verbose=verbose)

    # Get or infer git ref
    if not ref:
        ref = source_repo.get_ref()

    # Parse this ref using the provided rules
    try:
        version = versions.parse(
            ref,
            version_rules=version_rules
            if version_rules
            else versions.VERSION_RULES,
            name_rules=name_rules if name_rules else None,
            path_rules=path_rules if path_rules else None,
        )
    except ValueError:
        raise click.BadOptionUsage(
            "ref", f"The provided or inferred git ref is invalid: {ref}"
        )
    if verbose:
        click.secho(f"Parsed version '{version.name}' from '{ref}'")

    # Get the git SHA
    if not sha:
        sha = source_repo.get_sha()
    if verbose and sha:
        click.secho(f"Current git SHA: '{sha}'")

    if target:
        target_dir = Path(target).resolve()
        filesystem.copy_source_to_target(
            source=source_dir,
            target=target_dir,
            version=version,
            base_url=base_url,
            alias_rules=alias_rules,
            include_version_menu=not no_version_dropdown,
            verbose=verbose,
        )

    else:
        assert repo is not None
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            target_repo = git.Git(target_dir, git=git_path, verbose=True)

            try:
                target_repo.checkout_or_init_repo(
                    repo=repo, branch=branch, name=name, email=email
                )
            except RuntimeError as e:
                click.secho(str(e), err=True)

            filesystem.copy_source_to_target(
                source=source_dir,
                target=target_dir,
                version=version,
                base_url=base_url,
                alias_rules=alias_rules,
                include_version_menu=not no_version_dropdown,
                verbose=verbose,
            )

            try:
                target_repo.push_to_repo(
                    repo=repo, branch=branch, sha=sha, force=force
                )
            except RuntimeError as e:
                click.secho(str(e), err=True)
                ctx.exit(1)
