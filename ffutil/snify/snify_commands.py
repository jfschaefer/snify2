from typing import Sequence

from ffutil.snify.document import Document
from ffutil.stepper.command import CommandOutcome, Command, CommandInfo
from ffutil.stepper.interface import interface
from ffutil.stepper.stepper import Modification, StateType


class SubstitutionOutcome(CommandOutcome):
    """Note: command is responsible for ensuring that the index is correct *after* the previous file modification outcomes."""
    def __init__(self, new_str: str, start_pos: int, end_pos: int):
        self.new_str = new_str
        self.start_pos = start_pos
        self.end_pos = end_pos


class DocumentModification(Modification):
    def __init__(self, document: Document, old_text: str, new_text: str):
        self.document = document
        self.old_text = old_text
        self.new_text = new_text

    def apply(self, state: StateType):
        current_text = self.document.get_content()
        if current_text != self.old_text:
            interface.write_text(
                (f"\n{self.document.identifier} has been modified since the last time it was read.\n"
                 f"I will not change the file\n"),
                style='warning'
            )
            interface.await_confirmation()
            return

        self.document.set_content(self.new_text)

    def unapply(self, state: StateType):
        current_text = self.document.get_content()
        if current_text != self.new_text:
            interface.write_text(
                (f"\n{self.document.identifier} has been modified since the last time it was written to.\n"
                 f"I will not change the file\n"),
                style='warning'
            )
            interface.await_confirmation()
            return
        self.file.write_text(self.old_text)



class ImportCommand(Command):
    def __init__(self, letter: str, description_short: str, description_long: str, outcome: SubstitutionOutcome,
                 redundancies: list[SubstitutionOutcome]):
        super().__init__(CommandInfo(
            pattern_presentation=letter,
            description_short=description_short,
            description_long=description_long)
        )
        self.outcome = outcome
        self.redundancies = redundancies

    def execute(self, call: str) -> Sequence[CommandOutcome]:
        cmds: list[SubstitutionOutcome] = self.redundancies + [self.outcome]
        cmds.sort(key=lambda x: x.start_pos, reverse=True)
        return cmds
