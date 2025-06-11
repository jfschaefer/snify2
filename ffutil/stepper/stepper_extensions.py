from typing import Optional

from ffutil.stepper.command import Command, CommandInfo, CommandOutcome
from ffutil.stepper.stepper import Stepper, Modification, S, StopStepper


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


class QuittableStepper(Stepper[S]):
    def handle_command_outcome(self, outcome: CommandOutcome) -> Optional[Modification[S]]:
        if isinstance(outcome, QuitOutcome):
            raise StopStepper()

        return super().handle_command_outcome(outcome)
