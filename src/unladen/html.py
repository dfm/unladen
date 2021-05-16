# -*- coding: utf-8 -*-

# __all__ = []

from typing import Dict

import pkg_resources
from bs4 import BeautifulSoup
from jinja2 import Template

from .versions import Database, Version


def render_template(
    name: str,
    database: Database,
    *,
    current_version: Version,
    base_url: str,
    **other: Dict[str, str],
) -> str:
    template = Template(
        pkg_resources.resource_string(
            "unladen", f"templates/{name}.html"
        ).decode("utf-8")
    )
    return BeautifulSoup(
        template.render(
            base_url=base_url,
            aliases=[
                (name, database[ref]) for name, ref in database.aliases.items()
            ],
            versions=list(sorted(database.versions.values())),
            current_version=current_version,
            **other,
        ),
        "html.parser",
    ).prettify()
