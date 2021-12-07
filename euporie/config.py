# -*- coding: utf-8 -*-
"""Defines a configuration class for euporie."""
from __future__ import annotations

import argparse
import json
import logging
import os
from collections import ChainMap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional, Sequence, Union

import jsonschema  # type: ignore
from appdirs import user_config_dir  # type: ignore
from pygments.styles import get_all_styles  # type: ignore

from euporie import __app_name__, __copyright__, __strapline__, __version__

__all__ = ["JSONEncoderPlus", "BooleanOptionalAction", "Config", "config"]

log = logging.getLogger(__name__)


class JSONEncoderPlus(json.JSONEncoder):
    """JSON encode class which encodes paths as strings."""

    def default(self, o: "Any") -> "Union[bool, int, float, str, None]":
        """Encode an object to JSON.

        Args:
            o: The object to encode

        Returns:
            The encoded object

        """
        if isinstance(o, Path):
            return str(o)
        return json.JSONEncoder.default(self, o)


_json_encoder = JSONEncoderPlus()


class BooleanOptionalAction(argparse.Action):
    """Action for boolean flags.

    Included because `argparse.BooleanOptionalAction` is not present in `python<=3.9`.
    """

    def __init__(self, option_strings: "list[str]", *args: "Any", **kwargs: "Any"):
        """Initate the Action, as per `argparse.BooleanOptionalAction`."""
        _option_strings = list(option_strings)
        for option_string in option_strings:
            if option_string.startswith("--"):
                _option_strings.append(f"--no-{option_string[2:]}")
        kwargs["nargs"] = 0
        super().__init__(_option_strings, *args, **kwargs)

    def __call__(
        self,
        parser: "argparse.ArgumentParser",
        namespace: "argparse.Namespace",
        values: "Union[str, Sequence[Any], None]",
        option_string: "Optional[str]" = None,
    ) -> "None":
        """Set the value to True or False depending on the flag provided."""
        if option_string in self.option_strings:
            assert isinstance(option_string, str)
            setattr(namespace, self.dest, not option_string.startswith("--no-"))

    def format_usage(self) -> "str":
        """Formats the action string.

        Returns:
            The formatted string.

        """
        return " | ".join(self.option_strings)


CONFIG_PARAMS: "dict[str, dict]" = {
    "version": {
        "flags_": ["--verion", "-V"],
        "action": "version",
        "version": f"%(prog)s {__version__}",
    },
    "log_file": {
        "flags_": ["--log-file"],
        "nargs": "?",
        "default": "",
        "type": str,
        "help": "File path for logs",
        "schema_": {
            "type": "string",
            "default": "",
        },
        "description_": """
            When set to a file path, the log output will be written to the
            given path. If no value is given (or the default "-" is passed) output
            will be printed to standard output.
        """,
    },
    "debug": {
        "flags_": ["--debug"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Include debug output in logs",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            When set, logging events at the debug level are emmitted.
        """,
    },
    "dump": {
        "flags_": ["--dump"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Output formatted file to display or file",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            When set, the formatted output will be written to the the output file path
            given by `dump_file` (standard output by default).
        """,
    },
    "dump_file": {
        "flags_": ["--dump-file"],
        "nargs": "?",
        "const": "-",
        "type": Path,
        "help": "Output path when dumping file",
        "schema_": {
            "type": "string",
            "default": None,
        },
        "description_": """
            When set to a file path, the formatted output will be written to the
            given path. If no value is given (or the default "-" is passed) output
            will be printed to standard output.
        """,
    },
    "page": {
        "flags_": ["--page"],
        "action": BooleanOptionalAction,
        "help": "Pass output to pager",
        "type": bool,
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to pipe output to the system pager when using `--dump`.
        """,
    },
    "run": {
        "flags_": ["--run"],
        "action": BooleanOptionalAction,
        "help": "Run the notebook when loaded",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
        If set, notebooks will be run automatically when opened, or if dumping
        output, notebooks will be run before being output.
    """,
    },
    "key_map": {
        "flags_": ["--key-map"],
        "type": str,
        "choices": ["emacs", "vi"],
        "help": "Key-binding mode for text editing",
        "schema_": {
            "type": "string",
            "default": "emacs",
        },
        "description_": """
            Key binding mode to use when editing cells.
        """,
    },
    "run_after_external_edit": {
        "flags_": ["--run-after-external-edit"],
        "type": bool,
        "help": "Run cells after editing externally",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to execute a cell immediately after editing in `$EDITOR`.
        """,
    },
    "autocomplete": {
        "flags_": ["--autocomplete"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide completions suggestions automatically",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to automatically suggestion completions while typing in code cells.
        """,
    },
    "autosuggest": {
        "flags_": ["--autosuggest"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide line completion suggestions",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether to automatically suggestion line content while typing in code cells.
        """,
    },
    "max_notebook_width": {
        "flags_": ["--max-notebook-width"],
        "type": int,
        "help": "Maximum width of notebooks",
        "schema_": {
            "type": "integer",
            "minimum": 1,
            "default": 120,
        },
        "description_": """
            The maximum width at which to display a notebook.
        """,
    },
    "background_pattern": {
        "flags_": ["--background-pattern", "--bg-pattern"],
        "type": int,
        "choices": range(6),
        "help": "The background pattern to use",
        "schema_": {
            "type": "integer",
            "minimum": 0,
            "maximum": 5,
            "default": 2,
        },
        "description_": """
            The background pattern to use when the notebook is narrower than the
            availble width. Zero mean no pattern is used.
        """,
    },
    "background_character": {
        "flags_": ["--background-character", "--bg-char"],
        "type": str,
        "help": "Character for background pattern",
        # "choices": "·⬤╳╱╲░▒▓▞╬",
        "schema_": {
            "type": "string",
            "maxLength": 1,
            "default": "·",
        },
        "description_": """
            The character to use when drawing the background pattern.
        """,
    },
    "background_color": {
        "flags_": ["--background-color", "--bg-color"],
        "type": str,
        "help": "Color for background pattern",
        "schema_": {
            "type": "string",
            "maxLength": 7,
            "default": "#444",
        },
        "description_": """
            The color to use for the background pattern.
        """,
    },
    "line_numbers": {
        "flags_": ["--line-numbers"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show or hide line numbers",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether line numbers are shown by default.
        """,
    },
    "syntax_theme": {
        "flags_": ["--syntax-theme"],
        "type": str,
        # Do not want to print all theme names in --help screen as it looks messy
        # "choices": list(get_all_styles()),
        "help": "Syntax higlighting theme",
        "schema_": {
            "type": "string",
            "pattern": f"({'|'.join(get_all_styles())})",
            "default": "default",
        },
        "description_": """
            The name of the pygments style for syntax highlighting.
        """,
    },
    "files": {
        "flags_": ["files"],
        "nargs": "*",
        "default": [],
        "type": Path,
        "help": "List of file names to open",
        "schema_": {
            "type": "array",
            "items": {
                "file": {
                    "description": "File path",
                    "type": "string",
                }
            },
        },
        "description_": """
        """,
    },
}

CONFIG_SCHEMA: "dict" = {
    "title": "Euporie Configuration",
    "description": "A configuration for euporie",
    "type": "object",
    "properties": {
        name: {
            "description": param.get("help"),
            **(
                {"pattern": f"({'|'.join(choices)})"}
                if (choices := param.get("choices")) and param.get("type") == str
                else {}
            ),
            **({"default": default} if (default := param.get("default")) else {}),
            **param["schema_"],
        }
        for name, param in CONFIG_PARAMS.items()
        if param.get("schema_")
    },
}


class Config:
    """A configuration object with configuration values available as attributes.

    Default configuration variables are loaded from the defaults defined in the
    schema, then overwritten with values defined in a configuration file.
    """

    conf_file_name = "config.json"
    defaults = {
        name: param.get("schema_", {}).get("default")
        for name, param in CONFIG_PARAMS.items()
    }

    def __init__(self):
        """Ininitate the Configuration object."""
        self.user = {}
        self.env = {}
        self.args = {}

        user_conf_dir = Path(user_config_dir(__app_name__, appauthor=False))
        user_conf_dir.mkdir(exist_ok=True, parents=True)
        self.config_file_path = user_conf_dir / self.conf_file_name
        self.valid_user = True

        self.load_user()
        self.load_env()
        self.load_args()

        self.chain = ChainMap(
            self.args,
            self.env,
            self.user,
            self.defaults,
        )

    def load_args(self) -> "None":
        """Attempts to load configuration settings from commandline flags."""
        parser = argparse.ArgumentParser(
            description=__strapline__,
            epilog=__copyright__,
            allow_abbrev=True,
            formatter_class=argparse.MetavarTypeHelpFormatter,
        )
        for name, data in CONFIG_PARAMS.items():
            parser.add_argument(
                *data.get("flags_") or [name],
                # Do not set defaults for command line arguments, as default values
                # would override values set in the configuration file
                **{
                    key: value
                    for key, value in data.items()
                    if not key.endswith("_") and key != "default"
                },
            )
        for name, value in vars(parser.parse_args()).items():
            if value is not None:
                # Convert to json and back to attain json types
                json_data = json.loads(_json_encoder.encode({name: value}))
                try:
                    jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                except jsonschema.ValidationError as error:
                    log.warning(f"Error in command line parameter `{name}`: {error}")
                else:
                    self.args[name] = value

    def load_env(self) -> "None":
        """Attempt to load configuration settings from environment variables."""
        for name, param in CONFIG_PARAMS.items():
            env = f"{__app_name__.upper()}_{name.upper()}"
            if env in os.environ:
                type_ = param.get("type", str)
                try:
                    value = type_(os.environ[env])
                except (ValueError, TypeError):
                    log.warning(
                        f"Environment variable `{env}` not understood"
                        f" - `{type_.__name__}` expected"
                    )
                else:
                    json_data = json.loads(_json_encoder.encode({name: value}))
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.error(f"Error in environment variable: `{env}`\n{error}")
                    else:
                        self.env[name] = value

    def load_user(self) -> "None":
        """Attempt to load JSON configuration file."""
        assert isinstance(self.config_file_path, Path)
        if self.valid_user and self.config_file_path.exists():
            with open(self.config_file_path, "r") as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: "
                        f"{self.config_file_path}\n"
                        "Is it valid json?"
                    )
                    self.valid_user = False
                else:
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.warning(
                            f"Error in config file: {self.config_file_path}\n"
                            f"{error}"
                        )
                        self.valid_user = False
                    else:
                        self.user.update(json_data)
                        return
            log.warning("The configuration file was not loaded")

    def get(self, name: "str") -> "Any":
        """Access a configuration variable, falling back to the default value if unset.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.chain.get(name)

    def __getattr__(self, name: "str") -> "Any":
        """Enables access of config elements via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.get(name)

    def __setitem__(self, name: "str", value: "Any") -> "None":
        """Set a configuration attribute.

        Args:
            name: The name of the attribute to set.
            value: The value to give the attribute.

        """
        if name in self.args:
            del self.args[name]
        self.user[name] = value
        if self.valid_user:
            with open(self.config_file_path, "w") as f:
                json.dump(self.user, f, indent=2)

    def __setattr__(self, attr: "str", value: "Union[bool, int, str]") -> "None":
        """Sets configuration attributes and writes their values to the config file."""
        if attr in self.defaults:
            self.__setitem__(attr, value)
        else:
            return super().__setattr__(attr, value)

    def __delitem__(self, name: "str") -> "None":
        """Unset a user's configuration variable.

        This removes a configuration setting from the user's configuration, so the
        default value will be used.

        Args:
            name: The name of the attribute to unset.

        Raises:
            KeyError: When the configuration does not exist in the configuration
                schema.

        """
        try:
            del self.user[name]
        except KeyError as exc:
            raise KeyError(f"Variable not found in the user config: {name!r}") from exc
        else:
            if self.valid_user:
                with open(self.config_file_path, "w") as f:
                    json.dump(self.user, f, indent=2)

    def __iter__(self) -> "Iterator[str]":
        """Iterate over all configuration variable names.

        Returns:
            An iterable of the combined dictionary.

        """
        return iter(self.chain)

    def __len__(self) -> "int":
        """Return the length of the combined user and default settings.

        Returns:
            The length of the combined dictionary.

        """
        return len(self.chain)

    def __str__(self) -> "str":
        """Represent the configuration as a string.

        Returns:
            A string representing the configuration.

        """
        return f"Config({self.chain!r})"

    __repr__ = __str__

    def toggle(self, name: "str") -> "None":
        """Switches attributes between permitted configuration states.

        For boolean values, they are toggled between True and False. Integer values are
        incremented and reset within the permitted range.

        Args:
            name: The name of the attribute to toggle.

        """
        if name in self.defaults:
            current = getattr(self, name)
            schema = CONFIG_SCHEMA["properties"][name]
            if schema["type"] == "boolean":
                setattr(self, name, not current)
            elif schema["type"] == "integer":
                setattr(
                    self,
                    name,
                    schema["minimum"]
                    + (current - schema["minimum"] + 1) % (schema["maximum"] + 1),
                )


# Do not actually load the config if type checking - it causes pytype to exit
config: "Config"
if not TYPE_CHECKING:
    config = Config()
