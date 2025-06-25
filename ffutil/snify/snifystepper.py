import functools
from typing import Optional

from ffutil.snify.catalog import Catalog
from ffutil.snify.document import STeXDocument, Document
from ffutil.snify.local_stex_catalog import LocalStexSymbol, LocalStexVerbalization, local_flams_stex_catalogs
from ffutil.snify.snifystate import SnifyState, SnifyCursor
from ffutil.stepper.command import CommandCollection
from ffutil.stepper.interface import interface
from ffutil.stepper.stepper import Stepper, StopStepper
from ffutil.stepper.stepper_extensions import QuittableStepper, QuitCommand


class SnifyStepper(QuittableStepper, Stepper[SnifyState]):

    @functools.cache
    def get_stex_catalogs(self) -> dict[str, Catalog[LocalStexSymbol, LocalStexVerbalization]]:
        return local_flams_stex_catalogs()

    def get_catalog_for_document(self, doc: Document) -> Optional[Catalog]:
        error_message: Optional[str] = None
        catalog: Optional[Catalog] = None

        if isinstance(doc, STeXDocument):
            catalogs = self.get_stex_catalogs()
            if not catalogs:
                error_message = (
                    f'Error when processing {doc.identifier}:\n'
                    'No STeX catalogs available.'
                )
            elif doc.language not in catalogs:
                error_message = (
                    f'Error when processing {doc.identifier}:\n'
                    'No STeX catalogs available for language {doc.language}.'
                )
            else:
                catalog = catalogs[doc.language]
        else:
            raise ValueError(f'Unsupported document type {type(doc)}')

        if error_message:
            interface.write_text(error_message, style='error')
            interface.await_confirmation()
        return catalog

    def ensure_state_up_to_date(self):
        """ If cursor is a position, rather than a range, we updated it to the next relevant range."""
        cursor = self.state.cursor
        if not isinstance(cursor.selection, int):   # we have a selection -> nothing to do
            return

        while cursor.selection < len(self.state.documents):
            doc = self.state.documents[cursor.document_index]
            print(f'Processing document {doc.identifier} at index {cursor.document_index}...')
            annotatable_segments = doc.get_annotatable_segments()

            catalog = self.get_catalog_for_document(doc)
            if catalog is None:
                cursor = SnifyCursor(cursor.document_index + 1, 0)
                continue

            for segment in annotatable_segments:
                if segment.get_end_ref() <= cursor.selection:
                    continue  # segment is before cursor

                first_match = catalog.find_first_match(
                    string=str(segment),
                    stems_to_ignore=set(),
                    words_to_ignore=set(),
                    symbols_to_ignore=set(),
                )

                if first_match is None:
                    continue

                start, stop, _ = first_match
                subsegment = segment[start:stop]
                self.state.cursor = SnifyCursor(
                    cursor.document_index,
                    selection=(subsegment.get_start_ref(), subsegment.get_end_ref())
                )
                return

            # nothing found in this document; move to the next one
            cursor = SnifyCursor(cursor.document_index + 1, 0)

        interface.clear()
        interface.write_text('There is nothing left to annotate.')
        interface.await_confirmation()
        raise StopStepper('done')


    def show_current_state(self):
        doc = self.state.get_current_document()
        interface.clear()
        interface.write_header(
            doc.identifier
        )
        interface.show_code(
            doc.get_content(),
            doc.format,  # type: ignore
            highlight_range=self.state.cursor.selection if isinstance(self.state.cursor.selection, tuple) else None,
            limit_range=5,
        )
        interface.newline()

    def get_current_command_collection(self) -> CommandCollection:
        return CommandCollection(
            'snify',
            [
                QuitCommand(),
            ],
            have_help=True
        )
