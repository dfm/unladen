# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup

from unladen import html
from unladen.versions import Database, Version, parse

TEST_DATABASE = Database(
    versions={
        "refs/heads/main": Version.load(
            {
                "ref": "refs/heads/main",
                "version": "main",
                "name": "main",
                "path": "main",
                "active": False,
            }
        ),
        "refs/tags/v0.0.1rc1": Version.load(
            {
                "ref": "refs/tags/v0.0.1rc1",
                "version": "0.0.1rc1",
                "name": "v0.0.1rc1",
                "path": "v0.0.1rc1",
                "active": True,
            }
        ),
        "refs/tags/v0.2.0": Version.load(
            {
                "ref": "refs/tags/v0.2.0",
                "version": "0.2.0",
                "name": "v0.2.0",
                "path": "v0.2.0",
                "active": True,
            }
        ),
    },
    aliases={
        "latest": "refs/heads/main",
        "stable": "refs/tags/v0.2.0",
    },
)


def test_render_versions() -> None:
    template = html.render_template(
        "versions",
        database=TEST_DATABASE,
        current_version=parse("refs/heads/main"),
        base_url="https://dfm.github.io/unladen",
    )
    assert "unladen-injected" in template.div["class"]


def test_inject_versions() -> None:
    txt = """
<html>
<head>
<title>test</title>
<style>
div {
    font-size: 12px;
}
</style>
<style>/* unladen-injected */</style>
<style>
p {
    font-weight: bold;
}
/* unladen-injected */
</style>
</head>
<body>
<div class="unladen-injected"></div>
<div class="test1">1</div>
<div class="test2">2</div>
</body>
</html>
"""

    version_style = html.load_style("versions")
    version_menu = html.render_template(
        "versions",
        database=TEST_DATABASE,
        current_version=parse("refs/heads/main"),
        base_url="https://dfm.github.io/unladen",
    )

    result = BeautifulSoup(
        html.inject_into_html(
            txt, version_style=version_style, version_menu=version_menu
        ),
        "html.parser",
    )

    # Check that the style is added properly
    styles = list(result.find_all("style"))
    assert len(styles) == 2
    assert styles[-1].string.strip().startswith("/* unladen-injected */")

    # Check that the versions dropdown is in the right place
    divs = list(result.html.body.find_all("div", recursive=False))
    assert len(divs) == 3
    for i, div in enumerate(divs[:-1]):
        assert f"test{i+1}" in div["class"]
    assert "unladen-injected" in divs[-1]["class"]
