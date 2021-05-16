# -*- coding: utf-8 -*-

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
        TEST_DATABASE,
        current_version=parse("refs/heads/main"),
        base_url="https://dfm.github.io/unladen",
    )
    # print(template)
    # assert 0
