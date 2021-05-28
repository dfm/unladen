# -*- coding: utf-8 -*-

__all__ = ["inject_into_html"]

from typing import Dict, Optional

import pkg_resources
from bs4 import BeautifulSoup
from jinja2 import Template

from .versions import Database, Version


def render_template(
    name: str,
    *,
    database: Database,
    current_version: Version,
    base_url: str,
    **other: Dict[str, str],
) -> BeautifulSoup:
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
    )


def load_style(name: str) -> str:
    return pkg_resources.resource_string(
        "unladen", f"styles/{name}.css"
    ).decode("utf-8")


def inject_into_html(
    html: str,
    *,
    version_style: Optional[str] = None,
    version_menu: Optional[BeautifulSoup] = None,
    include_warnings: bool = True,
) -> str:
    tree = BeautifulSoup(html, "html.parser")
    if tree.html is None or tree.html.head is None or tree.html.body is None:
        return html

    # Remove existing injected content
    for tag in tree.select(".unladen-injected"):
        tag.extract()

    # Removing existing injected styles
    for tag in tree.select("style"):
        if "/* unladen-injected */" in tag.string:
            tag.extract()

    # Add the version menu
    if version_menu:
        if version_style:
            tag = tree.new_tag("style")
            tag.string = "/* unladen-injected */\n" + load_style("versions")
            tree.html.head.append(tag)
        tree.html.body.append(version_menu)

    return tree.prettify()
