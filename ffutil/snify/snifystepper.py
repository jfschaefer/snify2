import functools
from typing import Optional, Any

from ffutil.snify.annotate import STeXAnnotateCommand
from ffutil.snify.catalog import Catalog, Verbalization
from ffutil.snify.document import STeXDocument, Document
from ffutil.snify.local_stex_catalog import LocalStexSymbol, LocalStexVerbalization, local_flams_stex_catalogs, \
    LocalFlamsCatalog
from ffutil.snify.skip_and_ignore import SkipCommand
from ffutil.snify.snify_commands import SubstitutionOutcome, DocumentModification
from ffutil.snify.snifystate import SnifyState, SnifyCursor
from ffutil.stepper.command import CommandCollection, CommandOutcome
from ffutil.stepper.interface import interface
from ffutil.stepper.stepper import Stepper, StopStepper, Modification
from ffutil.stepper.stepper_extensions import QuittableStepper, QuitCommand, CursorModifyingStepper


class SnifyStepper(QuittableStepper, CursorModifyingStepper, Stepper[SnifyState]):
    def __init__(self, state: SnifyState):
        super().__init__(state)
        self.state = state
        self.current_annotation_choices: Optional[list[tuple[Any, Verbalization]]] = None

    @functools.cache
    def get_stex_catalogs(self) -> dict[str, LocalFlamsCatalog]:
        return local_flams_stex_catalogs()

    def get_catalog_for_document(self, doc: Document) -> Optional[LocalFlamsCatalog]:
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

    def get_catalog_for_current_document(self) -> Optional[LocalFlamsCatalog]:
        """ Get the catalog for the currently selected document."""
        doc = self.state.get_current_document()
        return self.get_catalog_for_document(doc)

    def ensure_state_up_to_date(self):
        """ If cursor is a position, rather than a range, we updated it to the next relevant range."""
        cursor = self.state.cursor
        if not isinstance(cursor.selection, int):   # we have a selection -> nothing to do
            return

        while cursor.document_index < len(self.state.documents):
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

                if cursor.selection >= segment.get_start_ref():
                    segment = segment[segment.get_indices_from_ref_range(cursor.selection, segment.get_end_ref())[0]:]

                first_match = catalog.find_first_match(
                    string=str(segment),
                    stems_to_ignore=set(),
                    words_to_ignore=set(),
                    symbols_to_ignore=set(),
                )

                if first_match is None:
                    continue

                start, stop, options = first_match
                subsegment = segment[start:stop]
                self.current_annotation_choices = options
                self.state.cursor = SnifyCursor(
                    cursor.document_index,
                    selection=(subsegment.get_start_ref(), subsegment.get_end_ref())
                )
                return

            # nothing found in this document; move to the next one
            cursor = SnifyCursor(cursor.document_index + 1, 0)

        interface.clear()
        interface.write_text('There is nothing left to annotate.\n')
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
        catalog = self.get_catalog_for_current_document()
        assert catalog is not None
        return CommandCollection(
            'snify',
            [
                STeXAnnotateCommand(self.state, self.current_annotation_choices, catalog, self),
                SkipCommand(self.state),
                QuitCommand(),
            ],
            have_help=True
        )

    def handle_command_outcome(self, outcome: CommandOutcome) -> Optional[Modification[SnifyState]]:
        doc = self.state.get_current_document()

        if isinstance(outcome, SubstitutionOutcome):
            return DocumentModification(
                doc,
                old_text=doc.get_content(),
                new_text=doc.get_content()[:outcome.start_pos] + outcome.new_str + doc.get_content()[outcome.end_pos:]
            )

        return super().handle_command_outcome(outcome)
