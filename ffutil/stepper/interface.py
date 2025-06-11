"""
User interfaces for the stepper module.
"""
import dataclasses
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Literal, Optional, TypeAlias

import click

_Color: TypeAlias = str | tuple[int, int, int]


def get_lines_around(text: str, start: int, end: int, n_lines: int = 7) -> tuple[str, str, str, int]:
    """
    returns
      - the n_lines lines before the start index
      - the text between the start and end index
      - the n_lines lines after the end index
      - the line number of the start index
    """
    start_index = start
    for _ in range(n_lines):
        if start_index > 0:
            start_index -= 1
        while start_index > 0 and text[start_index - 1] != '\n':
            start_index -= 1

    end_index = end
    for _ in range(n_lines):
        if end_index + 1 < len(text):
            end_index += 1
        while end_index + 1 < len(text) and text[end_index + 1] != '\n':
            end_index += 1
    end_index += 1

    return text[start_index:start], text[start:end], text[end:end_index], text[:start_index].count('\n') + 1



class Interface(ABC):
    """Base class for all interfaces in the stepper module."""

    @abstractmethod
    def clear(self) -> None:
        """Clears/resets the screen."""

    @abstractmethod
    @contextmanager
    def big_infopage(self):
        pass

    @abstractmethod
    def write_text(self, text: str, style: str = 'default', *, prestyled: bool = False):
        pass

    @abstractmethod
    def get_input(self) -> str:
        pass

    def newline(self):
        self.write_text('\n')

    def write_header(
            self, text: str, style: Literal['default', 'error', 'warning', 'subdialog', 'section'] = 'default'
    ):
        del style   # default implementation ignores style
        self.write_text(text, style='bold')
        self.newline()

    def write_command_info(self, key: str, description: str):
        self.write_text('  ')
        self.write_text(f'[{key}]', style='bold')
        self.write_text(description.replace('\n', '\n' + ' ' * (len(key) + 4)))
        self.newline()

    def write_statistics(self, text: str):
        self.write_text(text, style='pale')
        self.newline()

    def await_confirmation(self):
        self.write_text('Press Enter to continue...', style='default')
        self.get_input()

    def show_code(
            self,
            code: str,
            format: Optional[Literal['tex', 'myst']] = None,
            *,
            highlight_range: Optional[tuple[int, int]] = None,
            limit_range: Optional[int] = None,    # only shows this many lines before/after the highlight_range
            show_line_numbers: bool = True,
    ):
        del format   # default implementation does no syntax highlighting

        if limit_range is not None:
            if highlight_range is None:
                raise ValueError("highlight_range must be provided if limit_range is specified.")
            a, b, c, line_no_start = get_lines_around(
                code, highlight_range[0], highlight_range[1], n_lines=limit_range or 7
            )
        elif highlight_range:
            a = code[:highlight_range[0]]
            b = code[highlight_range[0]:highlight_range[1]]
            c = code[highlight_range[1]:]
            line_no_start = 1
        else:
            a = code
            b = ''
            c = ''
            line_no_start = 1

        line_no = line_no_start

        for source, style in [(a, 'default'), (b, 'highlight'), (c, 'default')]:
            for line_no, line in enumerate(source.splitlines(keepends=True), line_no):
                if show_line_numbers:
                    self.write_text(f'{line_no:4} ', style='pale')
                self.write_text(line, style=style)

            if source.endswith('\n'):
                line_no += 1

        if not code.endswith('\n'):
            self.newline()

class MinimalInterface(Interface):
    """A minimal interface that only prints text to the console."""

    def clear(self) -> None:
        self.write_text('\n' + '=' * 80 + '\n')

    @contextmanager
    def big_infopage(self):
        self.clear()
        yield
        self.await_confirmation()
        self.clear()

    def write_text(self, text: str, style: str = 'default', *, prestyled: bool = False):
        print(text, end='')

    def get_input(self) -> str:
        return input()


@dataclasses.dataclass
class ConsoleInterface(Interface):
    light_mode: bool = False
    true_color: bool = False

    def __post_init__(self):
        self._in_big_infopage: bool = False
        self._big_infopage_content: str = ''

    def clear(self) -> None:
        click.clear()

    @contextmanager
    def big_infopage(self):
        if self._in_big_infopage:
            raise RuntimeError("Already in a big infopage context.")
        self._in_big_infopage = True
        self._big_infopage_content = ''
        yield
        self._in_big_infopage = False
        click.echo_via_pager(self._big_infopage_content)

    def _write_styled(self, text: str):
        if self._in_big_infopage:
            self._big_infopage_content += text
        else:
            click.echo(text, nl=False)

    def write_text(self, text: str, style: str = 'default', *, prestyled: bool = False):
        if prestyled:
            self._write_styled(text)
            return

        def c(
                simple: str | None,
                full: tuple[int, int, int],
                simple_light: str | None,
                full_light: tuple[int, int, int],
        ) -> _Color | None:
            if self.light_mode:
                return full_light if self.true_color else simple_light
            return full if self.true_color else simple

        bold = False
        italics = False
        strikethrough = False
        bg = c(None, (0, 0, 0), None, (255, 255, 255))
        fg = c(None, (255, 255, 255), None, (0, 0, 0))

        if style == 'bold':
            bold = True
        elif style == 'error':
            bg = c('red', (255, 0, 0), 'bright_red', (255, 128, 128))
        elif style == 'warning':
            bg = c('yellow', (255, 255, 0), 'bright_yellow', (255, 255, 128))
        elif style == 'highlight':
            bg = c('yellow', (255, 255, 0), 'bright_yellow', (255, 255, 128))
        elif style == 'pale':
            fg = c('bright_black', (128, 128, 128), 'bright_black', (128, 128, 128))
        else:
            pass

        self._write_styled(click.style(text, bg=bg, fg=fg, bold=bold, italic=italics, strikethrough=strikethrough))


    def get_input(self) -> str:
        return click.prompt('', show_default=False, prompt_suffix='')


interface: Interface = MinimalInterface()


def set_interface(new_interface: Interface):
    global interface
    if not isinstance(new_interface, Interface):
        raise TypeError(f"Expected an instance of Interface, got {type(new_interface)}")
    interface = new_interface
