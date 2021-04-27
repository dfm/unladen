# -*- coding: utf-8 -*-

__all__ = ["main"]

from typing import Tuple

import os
import subprocess as sp

import click

from .unladen_version import __version__


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(version=__version__)
@click.option("-r", "--ref", type=str, help="The git ref that is being built.")
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        allow_dash=True,
    ),
    is_eager=True,
)
def main(src: Tuple[str, ...]) -> None:
    pass


def parse_ref(ref: str = None) -> str:
    pass


def get_ref() -> str:
    pass
