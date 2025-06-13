# CATALOG
import dataclasses
import re
from functools import cached_property
from typing import Iterable

from ffutil.snify.catalog import Verbalization, Catalog, catalogs_from_stream
from ffutil.stex.flams import FLAMS


@dataclasses.dataclass
class LocalStexSymbol:
    uri: str
    path: str
    srefcount: int = 0   # simple heuristic: the more references, the more relevant

    # TODO: symbols have to be hashable... the following is not ideal though
    def __eq__(self, other):
        return (
                isinstance(other, LocalStexSymbol) and
                self.uri == other.uri and self.path == other.path
        )

    def __hash__(self):
        return hash((self.uri, self.path))


class LocalStexVerbalization(Verbalization):
    def __init__(self, verb: str, local_path: str, path_range: tuple[int, int]):
        super().__init__(verb)
        self.local_path = local_path
        self.path_range = path_range

    def __repr__(self):
        return f"LocalStexVerbalization(verb={self.verb!r}, local_path={self.local_path!r}, path_range={self.path_range!r})"


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


def local_flams_stex_verbs() -> Iterable[tuple[str, LocalStexSymbol, LocalStexVerbalization]]:
    """ This code deserves heavy optimization,
    which explains why it is somewhat messy. """
    symbols: dict[str, LocalStexSymbol] = {}

    def _get_symbol(uri: str, path: str) -> LocalStexSymbol:
        """ Get or create a LocalStexSymbol for the given uri and path. """
        symbol = symbols.get(uri, None)
        if symbol is None:
            symbol = LocalStexSymbol(uri=uri, path=path)
            symbols[uri] = symbol
        return symbol

    @dataclasses.dataclass
    class Ctx:
        localpath: str
        opened_file: OpenedFile


    def _extract(j, ctx: Ctx) -> Iterable[tuple[str, LocalStexSymbol, LocalStexVerbalization]]:
        """ recurse through the annotation json to find symrefs and co """
        if isinstance(j, dict):
            for k, v in j.items():
                # TODO: add more keys to filter (optimization)
                if k in {'full_range', 'val_range', 'key_range', 'Sig', 'smodule_range', 'Title', 'path_range',
                         'archive_range', 'UseModule'}:
                    continue
                if k == 'Symref':
                    symbol = _get_symbol(v['uri'][0]['uri'], v['uri'][0]['filepath'])
                    symbol.srefcount += 1
                    range_ = ctx.opened_file.flams_range_to_offsets(v['text'][0])
                    verb = ctx.opened_file.text[range_[0]:range_[1]]
                    yield (
                        lang,
                        symbol,
                        LocalStexVerbalization(
                            verb=verb[1:-1],  # remove braces
                            local_path=ctx.localpath,
                            path_range=range_
                        )
                    )

        elif isinstance(j, list):
            for item in j:
                yield from _extract(item, ctx)

    # The main extraction loop
    FLAMS.require_all_files_loaded()
    for path in FLAMS.get_loaded_files():
        segments = path.split('/')[-1].split('.')
        lang = 'en'   # default
        if len(segments) > 2 and len(segments[-2]) < 5:
            lang = segments[-2]

        annos = FLAMS.get_file_annotations(path)

        yield from _extract(annos, Ctx(path, OpenedFile(path)))


def local_flams_stex_catalogs() -> dict[str, Catalog[LocalStexSymbol, LocalStexVerbalization]]:
    return catalogs_from_stream(local_flams_stex_verbs())


if __name__ == '__main__':
    # Example usage
    catalogs = local_flams_stex_catalogs()
    print('catalogs')
    for lang, catalog in catalogs.items():
        print(f'Catalog for language: {lang}')
        for symb, verbs in catalog.lookup.verbs.items():
            print(f'  Symbol: {symb.uri} ({symb.path}), References: {symb.srefcount}')
            for verb in verbs:
                print(f'    Verbalization: {verb.verb}, Path: {verb.local_path}, Range: {verb.path_range}')