# -*- coding: utf-8 -*-
"""Concerns dumping output."""
import asyncio
import io
import logging
import os
import sys
from typing import TYPE_CHECKING, cast

from prompt_toolkit import renderer
from prompt_toolkit.data_structures import Size
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.widgets import Box, HorizontalLine

from euporie.app.base import EuporieApp
from euporie.config import config
from euporie.containers import PrintingContainer
from euporie.notebook import DumpKernelNotebook, DumpNotebook

if TYPE_CHECKING:
    from typing import Any, Optional, TextIO, Type

    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.output import Output

    from euporie.notebook import Notebook

log = logging.getLogger(__name__)


class DumpApp(EuporieApp):
    """An application which dumps the layout to the output then exits."""

    def __init__(self, **kwargs: "Any") -> "None":
        """Create an app for dumping a prompt-toolkit layout."""
        self.notebook_class: "Type[Notebook]" = (
            DumpKernelNotebook if config.run else DumpNotebook
        )
        super().__init__(
            full_screen=False,
            **kwargs,
        )
        self.pre_run_callables.append(self.post_dump)
        self.rendered = False

    def load_container(self) -> "AnyContainer":
        """Returns a container with all opened tabs."""
        # Create a horizontal line that takes up the full width of the display
        hr = HorizontalLine()
        hr.window.width = self.output.get_size().columns

        # Add tabs, separated by horizontal lines
        contents: "list[AnyContainer]" = []
        for tab in self.tabs:
            # Wrap each tab in a box so it does not expand beyond its maximum width
            contents.append(Box(tab))
            contents.append(hr)
        # Remove the final horizontal line
        if self.tabs:
            contents.pop()

        return PrintingContainer(contents)

    def load_output(self) -> "Output":
        """Loads the output.

        Depending on the application configuration, will set the output to a file, to
        stdout, or to a temporary file so the output can be displayed in a pager.

        Returns:
            A container for notebook output

        """
        if config.page and sys.stdout.isatty():
            # Use a temporary file as display output if we are going to page the output
            from tempfile import TemporaryFile

            self.output_file = TemporaryFile("w+")
        else:
            if config.page:
                log.warning("Cannot page output because standard output is not a TTY")
            # If we are not paging output, determine when to print it
            if config.dump_file is None or str(config.dump_file) in (
                "-",
                "/dev/stdout",
            ):
                self.output_file = sys.stdout
            elif str(config.dump_file) == "/dev/stderr":
                self.output_file = sys.stderr
            else:
                try:
                    self.output_file = open(config.dump_file, "w+")
                except (
                    FileNotFoundError,
                    PermissionError,
                    io.UnsupportedOperation,
                ) as error:
                    log.error(error)
                    log.error(
                        f"Output file `{config.dump_file}` cannot be opened. "
                        "Standard output will be used."
                    )
                    self.output_file = sys.stdout

        # Ensure we do not recieve the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(self.output_file.fileno())
        # Set environment variable to disable character position requests
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"
        # Create a default output - this detectes the terminal type
        # Do not use stderr instead of stdout if stdout is not a tty
        output = create_output(
            cast("TextIO", self.output_file), always_prefer_tty=False
        )
        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        # output.get_size = create_output(stdout=sys.stderr).get_size
        setattr(output, "get_size", create_output(stdout=sys.stderr).get_size)
        return output

    def _redraw(self, render_as_done: "bool" = False) -> "None":
        """Ensure the output is drawn once, and the cursor is left after the output."""
        if not self.rendered:
            super()._redraw(render_as_done=True)
            self.rendered = True

    def post_dump(self) -> "None":
        """Close all files and exit the app."""
        log.debug("Gathering background tasks")
        asyncio.gather(*self.background_tasks)

        # Close all the files
        for tab in self.tabs:
            self.close_tab(tab)

        if self.loop is not None:
            self.loop.call_soon(self.pre_exit)

    def pre_exit(self) -> "None":
        """Close the app after dumping, optionally piping output to a pager."""
        # Display pager if needed
        if config.page:
            from pydoc import pager

            log.debug(self.output_file.fileno())
            self.output_file.seek(0)
            data = self.output_file.read()
            pager(data)

        self.exit()


def _patched_output_screen_diff(
    *args: "Any", **kwargs: "Any"
) -> "tuple[Point, Optional[str]]":
    """Function used to monkey-patch the renderer to extend the application height."""
    # Remove ZWE from screen
    # from collections import defaultdict
    # args[2].zero_width_escapes = defaultdict(lambda: defaultdict(lambda: ""))

    # Tell the renderer we have one additional column. This is to prevent the use of
    # carriage returns and cursor movements to write the final character on lines,
    # which is something the prompt_toolkit does
    size = kwargs.pop("size")
    kwargs["size"] = Size(9999999, size.columns + 1)
    return _original_output_screen_diff(*args, **kwargs)


# Monkey patch the screen size
_original_output_screen_diff = renderer._output_screen_diff
renderer._output_screen_diff = _patched_output_screen_diff
