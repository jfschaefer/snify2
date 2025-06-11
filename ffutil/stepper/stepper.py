from abc import abstractmethod, ABC
from typing import Optional, TypeVar, Generic, Sequence

from ffutil.stepper.command import CommandCollection, CommandOutcome


class Cursor:
    """Abstract class for representing the current position of the stepper"""
    pass


class State:
    """
    The state of the stepper.
    It may be pickled to restore the stepper's state in a future session.
    It may therefore be necessary that the stepper keeps an additional state for ephemeral data.
    """
    def __init__(self, cursor: Cursor):
        self.cursor = cursor


S = TypeVar('S', bound=State)

class Modification(ABC, Generic[S]):
    """A change that can be undone. E.g. a file modification."""
    @abstractmethod
    def apply(self, state: S):
        pass

    @abstractmethod
    def unapply(self, state: S):
        pass


class StopStepper(Exception):
    """Raised to stop the stepper loop."""
    pass


class Stepper(ABC, Generic[S]):
    """
    The base class for "ispell-like" functionality.
    """
    def __init__(self, state: S):
        self.state = state

        # a single undoing/redoing may undo/redo multiple modifications
        # (e.g. modify a file and change the cursor position)
        self.modification_history: list[list[Modification[S]]] = []
        self.modification_future: list[list[Modification[S]]] = []

    def run(self):
        """Run the stepper until it is stopped."""
        try:
            while True:
                self._single_iteration()
        except StopStepper:
            pass

    def _single_iteration(self):
        self.ensure_state_up_to_date()
        self.show_current_state()
        outcomes: Sequence[CommandOutcome] = self.get_current_command_collection().apply()
        new_modifications: list[Modification[S]] = []
        for outcome in outcomes:
            assert isinstance(outcome, CommandOutcome)
            modification = self.handle_command_outcome(outcome)
            if modification:
                new_modifications.append(modification)
                modification.apply(self.state)
                self.reset_after_modification(modification)

        if new_modifications:
            self.modification_history.append(new_modifications)
            self.modification_future.clear()

    def ensure_state_up_to_date(self):
        """May do nothing, but could, e.g., update the cursor."""

    def reset_after_modification(self, modification: Modification[S], is_undone: bool = False):
        """Sometimes modifications require resetting something (e.g. invalidating caches after file modifications)."""
        pass

    @abstractmethod
    def show_current_state(self):
        """display the current state/task in the user interface"""

    @abstractmethod
    def get_current_command_collection(self) -> CommandCollection:
        """Should return the commands currently applicable to the current state."""

    def handle_command_outcome(self, outcome: CommandOutcome) -> Optional[Modification[S]]:
        """Handle the outcome of a command execution."""
        raise NotImplementedError(f"No handler implemented for {type(outcome)}")
