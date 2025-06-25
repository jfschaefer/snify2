import dataclasses

from ffutil.snify.document import Document
from ffutil.stepper.stepper import State


@dataclasses.dataclass(frozen=True)
class SnifyCursor:
    document_index: int
    selection: int | tuple[int, int]



class SnifyState(State[SnifyCursor]):
    def __init__(self, cursor: SnifyCursor, documents: list[Document]):
        super().__init__(cursor)
        self.documents = documents

    def get_current_document(self) -> Document:
        if not self.documents:
            raise ValueError("No documents available.")
        return self.documents[self.cursor.document_index]
