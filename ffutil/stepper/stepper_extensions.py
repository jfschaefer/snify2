from copy import deepcopy
from typing import Optional, Generic

from ffutil.stepper.command import Command, CommandInfo, CommandOutcome
from ffutil.stepper.stepper import Stepper, Modification, StateType, StopStepper, CursorType


#######################################################################
#   QUIT COMMAND
#######################################################################

class QuitOutcome(CommandOutcome):
    pass


class QuitCommand(Command):
    def __init__(self, long_description: Optional[str] = None):
        super().__init__(CommandInfo(
            pattern_presentation='q',
            description_short='uit',
            description_long=long_description or ''
        ))

    def execute(self, call: str) -> list[CommandOutcome]:
        return [QuitOutcome()]


class QuittableStepper(Stepper[StateType]):
    def handle_command_outcome(self, outcome: CommandOutcome) -> Optional[Modification[StateType]]:
        if isinstance(outcome, QuitOutcome):
            raise StopStepper('quit')

        return super().handle_command_outcome(outcome)


#######################################################################
#   CURSOR SETTING
#######################################################################

class SetCursorOutcome(CommandOutcome, Generic[CursorType]):
    def __init__(self, new_cursor: CursorType):
        self.new_cursor = new_cursor


class CursorModification(Modification[StateType], Generic[StateType, CursorType]):
    def __init__(self, old_cursor: CursorType, new_cursor: CursorType):
        self.old_cursor = old_cursor
        self.new_cursor = new_cursor

    def apply(self, state: StateType):
        print(f'CursorModification: changing cursor from {self.old_cursor} to {self.new_cursor}')
        state.cursor = self.new_cursor

    def unapply(self, state: StateType):
        state.cursor = self.old_cursor


class CursorModifyingStepper(Stepper[StateType]):
    def handle_command_outcome(self, outcome: CommandOutcome) -> Optional[Modification[StateType]]:
        if isinstance(outcome, SetCursorOutcome):
            return CursorModification(deepcopy(self.state.cursor), deepcopy(outcome.new_cursor))

        return super().handle_command_outcome(outcome)