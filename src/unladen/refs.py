# -*- coding: utf-8 -*-

__all__ = ["parse", "DEFAULT_NAME_RULES", "DEFAULT_ALIAS_RULES"]

import re
from typing import Iterable, Tuple, Optional, List

Rule = Tuple[str, str]

DEFAULT_NAME_RULES: List[Rule] = [
    ("refs/heads/(.+)", "{0}"),
    ("refs/tags/(.+)", "{0}"),
]
DEFAULT_ALIAS_RULES: List[Rule] = [
    ("refs/heads/main", "latest"),
    ("refs/tags/v[0-9\\.]+", "stable"),
]


def parse(
    *, ref: str, rules: Iterable[Rule], verbose: bool = False
) -> Optional[str]:
    for pattern, fmt in rules:
        result = re.match(pattern, ref)
        if result is not None:
            return fmt.format(*result.groups())
