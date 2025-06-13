import dataclasses


@dataclasses.dataclass
class Document:
    identifer: str
    index: int
    content: str
    format: str
    language: str


class DocumentSource:
    pass



class STeXDocument(Document):
    pass


class STeXDocumentSource(DocumentSource):
    pass