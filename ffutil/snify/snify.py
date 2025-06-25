from pathlib import Path

from ffutil.snify.document import documents_from_paths
from ffutil.snify.snifystate import SnifyState, SnifyCursor
from ffutil.snify.snifystepper import SnifyStepper
from ffutil.stepper.interface import interface


def snify(files: list[Path]):
    stepper = SnifyStepper(
        SnifyState(
            SnifyCursor(
                document_index=0,
                selection=0,
            ),
            documents=documents_from_paths(files)
        )
    )

    stepper.run()
