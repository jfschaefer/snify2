"""
Code for parsing sTeX files.
This is not based on FLAMS (FLAMS only extracts annotations, and we need the informal content as well).
"""
from typing import Iterable

from pylatexenc.latexwalker import get_default_latex_context_db, LatexWalker, LatexMathNode, LatexCommentNode, \
    LatexSpecialsNode, LatexMacroNode, LatexEnvironmentNode, LatexGroupNode, LatexCharsNode, LatexNode
from pylatexenc.macrospec import MacroSpec, std_environment, VerbatimArgsParser

from ffutil.stepper.interface import interface
from ffutil.utils.linked_str import LinkedStr, string_to_lstr

STEX_MACRO_SPECS: list = [
    # from section 3.5 of the stex manual (targets modules)
    MacroSpec('importmodule', '[{'),
    MacroSpec('requiremodule', '[{'),
    MacroSpec('usemodule', '[{'),

    # from section 2.2 of the stex manual (targets tex files)
    MacroSpec('inputref', '*[{'),
    MacroSpec('mhinput', '*[{'),

    # targets non-tex files
    MacroSpec('mhgraphics', '[{'),
    MacroSpec('cmhgraphics', '[{'),
    MacroSpec('mhtikzinput', '[{'),
    MacroSpec('cmhtikzinput', '[{'),
    MacroSpec('lstinputmhlisting', '[{'),
    MacroSpec('addmhbibresource', '[{'),

    # others
    MacroSpec('includeproblem', '[{'),
    MacroSpec('includeassignment', '[{'),

    # from section 1.3 of the stex manual (targets lib/ directory)
    MacroSpec('libinput', '[{'),
    MacroSpec('libusepackage', '[{'),
    MacroSpec('libusetikzlibrary', '[{'),

    # various others
    MacroSpec('MSC', '{'),
    MacroSpec('notation', '{[{'),
    MacroSpec('symdecl', '*{'),
    MacroSpec('symdef', '{[{'),
    MacroSpec('definiendum', '[{{'),
    MacroSpec('definame', '[{'),
    MacroSpec('Definame', '[{'),
    MacroSpec('sn', '[{'),
    MacroSpec('sns', '[{'),
    MacroSpec('Sn', '[{'),
    MacroSpec('Sns', '[{'),
    MacroSpec('sr', '[{{'),
    MacroSpec('objective', '{{'),
    MacroSpec('sref', '[{'),
    MacroSpec('usestructure', '{'),
    MacroSpec('slink', '{'),
    MacroSpec('varseq', '{{{'),
    MacroSpec('nlex', '{'),
    MacroSpec('inlinedef', '[{'),
    MacroSpec('inlineex', '[{'),
    MacroSpec('inlineass', '[{'),
    MacroSpec('definiens', '[{'),
    MacroSpec('definiens', '[{'),
    MacroSpec('vardef', '{[{'),
]

STEX_ENV_SPECS: list = [
    std_environment('smodule', '[{'),
    std_environment('sdefinition', '['),
    std_environment('sproblem', '['),
    std_environment('sexample', '['),
    std_environment('sparagraph', '['),
    std_environment('sfragment', '[{'),
    std_environment('assignment', '['),
    std_environment('nparagraph', '['),
    std_environment('mathstructure', '{['),
    std_environment('extstructure', '*{[{'),
    std_environment('textsymdecl', '{[{'),
    std_environment('scb', '['),
    std_environment('smcb', '['),
]


STANDARD_MACRO_SPECS: list = [
    MacroSpec('lstinline', args_parser=VerbatimArgsParser(verbatim_arg_type="verb-macro")),
    MacroSpec('lstset', '{'),
    MacroSpec('lstinputlisting', '[{'),

    # less standard
    MacroSpec('ednote', '{'),
]

STANDARD_ENV_SPECS: list = [
    std_environment('lstlisting', '['),
    std_environment('frame', '['),
    std_environment('tikzpicture', '['),
]

STEX_CONTEXT_DB = get_default_latex_context_db()
STEX_CONTEXT_DB.add_context_category('stex', macros=STEX_MACRO_SPECS, environments=STEX_ENV_SPECS)
STEX_CONTEXT_DB.add_context_category('std', macros=STANDARD_MACRO_SPECS, environments=STANDARD_ENV_SPECS)
try:
    STEX_CONTEXT_DB.freeze()
except AttributeError:   # freeze is only available in newer pylatexenc versions
    pass




#############
# PLAIN TEXT EXTRACTION FOR ANNOTATIONS
#############


# By default, macros are not searched for potential annotations.
# This is a list of exceptions to this rule.
# The keys are the names of the macros (note that they should be in the pylatexenc context).
# The values are the indices of the arguments that should be searched (-1 for last argument is a common choice).
PLAINTEXT_EXTRACTION_MACRO_RECURSION: dict[str, list[int]] = {
    'emph': [0],
    'textbf': [0],
    'textit': [0],
    'inlinedef': [1],
    'inlineex': [1],
    'inlineass': [1],
    'definiens': [1],
}

# By default, the content of environment is searched for potential annotations,
# but the arguments are not.
# This is a list of exceptions to this rule.
# The keys are the names of the environments (note that they should be in the pylatexenc context).
# The values are pairs (a, b), where
#   - a is a boolean indicating whether the environment content should be searched
#   - b is a list of indices of the arguments that should be searched
PLAINTEXT_EXTRACTION_ENVIRONMENT_RULES: dict[str, tuple[bool, list[int]]] = {
    'lstlisting': (False, []),
    'tikzpicture': (False, []),
}


def get_annotatable_plaintext(
        walker: LatexWalker,
        suppress_errors: bool = False,
) -> list[LinkedStr]:
    result: list[LinkedStr] = []
    # walker = LatexWalker(latex_text, latex_context=STEX_CONTEXT_DB)
    latex_text = walker.s

    def _recurse(nodes):
        for node in nodes:
            if node is None or node.nodeType() in {LatexMathNode, LatexCommentNode, LatexSpecialsNode}:
                # TODO: recurse into math nodes?
                continue
            if node.nodeType() == LatexMacroNode:
                if node.macroname in PLAINTEXT_EXTRACTION_MACRO_RECURSION:
                    for arg_idx in PLAINTEXT_EXTRACTION_MACRO_RECURSION[node.macroname]:
                        if arg_idx >= len(node.nodeargd.argnlist) and not suppress_errors:
                            interface.clear()
                            interface.write_header('Error', style='error')
                            interface.write_text(f"Macro {node.macroname} does not have argument {arg_idx}",
                                                 style='error')
                            interface.write_text('\nContext:\n')
                            interface.show_code(
                                latex_text,
                                format='tex',
                                highlight_range=(node.pos, node.pos + node.len),
                                limit_range=3,
                            )
                            interface.write_text('\n\nPlease report this error\n', style='bold')
                            interface.await_confirmation()
                            continue
                        _recurse([node.nodeargd.argnlist[arg_idx]])
            elif node.nodeType() == LatexEnvironmentNode:
                if node.envname in PLAINTEXT_EXTRACTION_ENVIRONMENT_RULES:
                    recurse_content, recurse_args = PLAINTEXT_EXTRACTION_ENVIRONMENT_RULES[node.envname]
                else:
                    recurse_content, recurse_args = True, []
                for arg_idx in recurse_args:
                    _recurse([node.nodeargd.argnlist[arg_idx]])
                if recurse_content:
                    _recurse(node.nodelist)
            elif node.nodeType() == LatexGroupNode:
                _recurse(node.nodelist)
            elif node.nodeType() == LatexCharsNode:
                result.append(string_to_lstr(node.chars, node.pos))
            else:
                raise RuntimeError(f"Unexpected node type: {node.nodeType()}")

    _recurse(walker.get_latex_nodes()[0])

    return result


def iterate_latex_nodes(nodes) -> Iterable[LatexNode]:
    for node in nodes:
        yield node
        if node is None or node.nodeType() in {LatexSpecialsNode}:
            continue
        elif node.nodeType() in {LatexMacroNode}:
            if node.nodeargd:
                yield from iterate_latex_nodes(node.nodeargd.argnlist)
        elif node.nodeType() in {LatexMathNode, LatexGroupNode, LatexEnvironmentNode}:
            yield from iterate_latex_nodes(node.nodelist)
        elif node.nodeType() in {LatexCommentNode, LatexCharsNode}:
            pass
        else:
            raise RuntimeError(f"Unexpected node type: {node.nodeType()}")
