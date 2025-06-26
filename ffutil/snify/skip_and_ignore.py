from typing import Optional

from ffutil.snify.snifystate import SnifyCursor, SnifyState
from ffutil.stepper.command import Command, CommandInfo, CommandOutcome
from ffutil.stepper.stepper_extensions import SetCursorOutcome


class SkipCommand(Command):
    def __init__(self, state: SnifyState):
        super().__init__(CommandInfo(
            pattern_presentation = 's',
            description_short = 'kip once',
            description_long = 'Skips to the next possible annotation')
        )
        self.state = state

    def execute(self, call: str) -> list[CommandOutcome]:
        assert isinstance(self.state.cursor.selection, tuple)
        return [
            SetCursorOutcome(
                new_cursor=SnifyCursor(self.state.cursor.document_index, self.state.cursor.selection[-1] + 1)
            )
        ]
