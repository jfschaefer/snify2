"""
Code for working with local sTeX archives.

This is mostly generic code, more specific code is in separate modules (for example for the catalogs).
"""
from functools import cached_property
from pathlib import Path


class OpenedFile:
    def __init__(self, path: str):
        self.path = path

    @cached_property
    def text(self) -> str:
        with open(self.path, 'r', encoding='utf-8') as f:
            return f.read()

    @cached_property
    def _linecharcount(self) -> list[int]:
        """ returns a list l where l[i] is the number of characters until the beginning of line i
            In FLAMS, lines are apparently 0-indexed.
        """
        result: list[int] = [0]
        value = 0
        for line in self.text.splitlines(keepends=True):
            value += len(line)
            result.append(value)
        return result

    def flams_range_to_offsets(self, flams_range) -> tuple[int, int]:
        lc = self._linecharcount
        start = lc[flams_range['start']['line']] + flams_range['start']['col']
        end = lc[flams_range['end']['line']] + flams_range['end']['col']
        return start, end


def lang_from_path(path: str | Path) -> str:
    if isinstance(path, Path):
        segments = path.name.split('.')
    else:
        segments = path.split('/')[-1].split('.')
    lang = 'en'   # default
    if len(segments) > 2 and len(segments[-2]) < 5:
        lang = segments[-2]
    return lang