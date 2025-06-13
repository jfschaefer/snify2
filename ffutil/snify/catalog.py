from typing import TypeVar, Generic, Iterable, Optional

from ffutil.snify.stemming import string_to_stemmed_word_sequence_simplified


class Verbalization:
    def __init__(self, verb: str):
        self.verb = verb


Symb = TypeVar('Symb')
Verb = TypeVar('Verb', bound=Verbalization)


class Trie(Generic[Symb, Verb]):
    __slots__ = 'verbs', 'children'
    def __init__(self):
        self.children: dict[str, 'Trie[Symb, Verb]'] = {}
        self.verbs: dict[Symb, list[Verb]] = {}

    def insert(self, key: Iterable[str], symb: Symb, verb: Verb):
        node = self
        for k in key:
            if k not in node.children:
                node.children[k] = Trie[Symb, Verb]()
            node = node.children[k]
        node.verbs.setdefault(symb, []).append(verb)

    def get(self, key: Iterable[str]) -> dict[Symb, list[Verb]]:
        node = self
        for k in key:
            if k not in node.children:
                return {}
            node = node.children[k]
        return node.verbs

    def __contains__(self, item):
        return item in self.verbs


class Catalog(Generic[Symb, Verb]):
    lang: str
    lookup: Trie[Symb, Verb]

    def __init__(self, lang: str, symbverbs: Optional[Iterable[tuple[Symb, Verb]]] = None):
        self.lang = lang
        self.lookup = Trie[Symb, Verb]()
        if symbverbs is not None:
            for symb, verb in symbverbs:
                self.add_symbverb(symb, verb)

    def add_symbverb(self, symb: Symb, verb: Verb):
        key = string_to_stemmed_word_sequence_simplified(verb.verb, self.lang)
        self.lookup.insert(key, symb, verb)


def catalogs_from_stream(
        stream: Iterable[tuple[str, Symb, Verb]],
    ) -> dict[str, Catalog[Symb, Verb]]:
    catalogs: dict[str, Catalog[Symb, Verb]] = {}
    for lang, symb, verb in stream:
        if lang not in catalogs:
            catalogs[lang] = Catalog[Symb, Verb](lang)
        catalogs[lang].add_symbverb(symb, verb)
    return catalogs