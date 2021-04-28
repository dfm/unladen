# -*- coding: utf-8 -*-

__all__ = ["parse_ref"]

import re
from typing import Iterable, Tuple, Optional, List

Rule = Tuple[str, str]

DEFAULT_RULES: List[Rule] = [
    ("refs/heads/(.+)", "{0}"),
    ("refs/tags/(.+)", "{0}"),
]


def parse_ref(
    *, ref: str, rules: Optional[Iterable[Rule]] = None, verbose: bool = False
) -> Optional[str]:
    if rules is None:
        rules = DEFAULT_RULES
    for pattern, fmt in rules:
        result = re.match(pattern, ref)
        if result is not None:
            return fmt.format(*result.groups())
