import dataclasses
from typing import Any, Optional, Iterable

from pylatexenc.latexwalker import LatexEnvironmentNode, LatexSpecialsNode, LatexMacroNode, LatexMathNode, \
    LatexGroupNode, LatexCommentNode, LatexCharsNode

from ffutil.snify.catalog import Verbalization
from ffutil.snify.document import STeXDocument
from ffutil.snify.local_stex import OpenedStexFLAMSFile, get_transitive_imports, FlamsUri
from ffutil.snify.local_stex_catalog import LocalStexSymbol
from ffutil.snify.snifystate import SnifyState
from ffutil.snify.stex_py_parsing import iterate_latex_nodes
from ffutil.stepper.command import Command, CommandInfo, CommandOutcome
from ffutil.stepper.interface import interface
from ffutil.stex.flams import FLAMS
from ffutil.utils.json_iter import json_iter


class STeXAnnotateCommand(Command):
    def __init__(self, state: SnifyState, options: list[tuple[Any, Verbalization]]):
        self.options = options
        document = state.get_current_document()
        assert isinstance(document, STeXDocument)
        self.importinfo = get_modules_in_scope_and_import_locations(
            document,
            state.cursor.selection[0] if isinstance(state.cursor.selection, tuple) else state.cursor.selection,
        )
        super().__init__(
            CommandInfo(
                pattern_presentation='𝑖',
                pattern_regex='^[0-9]+$',
                description_short=' annotate with 𝑖',
                description_long='Annotates the current selection with option number 𝑖'
            )
        )

    def execute(self, call: str) -> list[CommandOutcome]:
        # TODO
        return []

    def standard_display(self):
        for i, (symbol, verbalization) in enumerate(self.options):
            assert isinstance(symbol, LocalStexSymbol)
            module_uri_f = FlamsUri(symbol.uri)
            module_uri_f.symbol = None
            symbol_display = ' '
            symbol_display += '✓' if str(module_uri_f) in self.importinfo.modules_in_scope else '✗'
            symbol_display += ' ' + symbol.uri
            interface.write_command_info(
                str(i),
                symbol_display
            )


@dataclasses.dataclass
class _ImportInfo:
    modules_in_scope: set[str]
    top_use_pos: int
    use_pos: int
    import_pos: Optional[int]
    use_env: Optional[str]
    top_use_env: Optional[str]

    # module uri -> full range of use/import
    potential_redundancies_on_use: dict[str, list[tuple[int, int]]]
    potential_redundancies_on_import: dict[str, list[tuple[int, int]]]
    potential_redundancies_on_top_use: dict[str, list[tuple[int, int]]]


def get_modules_in_scope_and_import_locations(document: STeXDocument, offset: int) -> _ImportInfo:
    """
    collects import information and potential import locations in the document.
    Uses both FLAMS and pylatexenc.

    Note: Comparing latex environments for equality doesn't work in pylatexenc
    (equal environments are not equal),
    so, as a quick hack, I use the positions instead.
    """

    annos = FLAMS.get_file_annotations(document.path)
    file = OpenedStexFLAMSFile(str(document.path))
    surrounding_envs = get_surrounding_envs(document, offset)
    surrounding_envs_pos = [e.pos for e in surrounding_envs]

    # STEP 1: find interesting environments for new imports/uses
    module_env: Optional[LatexEnvironmentNode] = None
    _modules = [e for e in surrounding_envs if e.environmentname == 'smodule']
    if _modules:
        module_env = _modules[-1]
    _containers = [e for e in surrounding_envs if e.environmentname in {
        'sproblem', 'smodule', 'sdefinition', 'sparagraph', 'document', 'frame'
    }]
    use_env = _containers[-1] if _containers else None

    potential_redundancies_on_use = {}
    potential_redundancies_on_import = {}
    potential_redundancies_on_top_use = {}

    # STEP 2: find modules in scope and the imports/uses
    available_modules: list[tuple[str, str]] = []   # (module uri, module path)
    for item in json_iter(annos):
        if isinstance(item, dict) and ('ImportModule' in item or 'UseModule' in item):
            value = item.get('ImportModule') or item.get('UseModule')
            full_range = file.flams_range_to_offsets(value['full_range'])
            containing_envs = list(get_surrounding_envs(document, full_range[0]))

            if not containing_envs:
                available_modules.append((value['module']['uri'], value['module']['full_path']))
                potential_redundancies_on_top_use.setdefault(value['module']['uri'], []).append(full_range)
                continue


            containing_env = containing_envs[-1]
            if containing_env.pos in surrounding_envs_pos:
                available_modules.append((value['module']['uri'], value['module']['full_path']))

                if 'ImportModule' in item and module_env.pos == containing_env.pos:
                    potential_redundancies_on_import.setdefault(value['module']['uri'], []).append(full_range)
                elif 'UseModule' in item:
                    potential_redundancies_on_top_use.setdefault(value['module']['uri'], []).append(full_range)
                    if use_env and surrounding_envs_pos.index(containing_env.pos) > surrounding_envs_pos.index(use_env.pos):
                        potential_redundancies_on_use.setdefault(value['module']['uri'], []).append(full_range)

        elif isinstance(item, dict) and 'Module' in item:
            value = item['Module']
            module_offset = file.flams_range_to_offsets(value['name_range'])[0]   # lots of things would work here
            containing_envs = list(get_surrounding_envs(document, module_offset))
            assert containing_envs
            containing_env = containing_envs[-1]
            if containing_env.pos in surrounding_envs_pos:
                available_modules.append((value['uri'], str(document.path)))

    return _ImportInfo(
        modules_in_scope = set(get_transitive_imports(available_modules)),
        top_use_pos = surrounding_envs[0].nodelist[0].pos if surrounding_envs else 0,
        use_pos = use_env.nodelist[0].pos if use_env else None,
        import_pos = module_env.nodelist[0].pos if module_env else None,
        use_env = use_env.environmentname if use_env else None,
        top_use_env = surrounding_envs[0].environmentname if surrounding_envs else None,
        potential_redundancies_on_use = potential_redundancies_on_use,
        potential_redundancies_on_import = potential_redundancies_on_import,
        potential_redundancies_on_top_use = potential_redundancies_on_top_use,
    )



def get_surrounding_envs(document: STeXDocument, offset: int) -> list[LatexEnvironmentNode]:
    """
    Returns the surrounding environments of the given offset in the document.
    """
    return [
        node
        for node in iterate_latex_nodes(document.get_latex_walker().get_latex_nodes()[0])
        if isinstance(node, LatexEnvironmentNode) and node.pos <= offset < node.pos + node.len
    ]
