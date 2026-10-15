# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""Helper for CLI entrypoints."""

from __future__ import annotations

from .config import Config, create_config_not_found_error


class FailCLIError(Exception):
    """
    Fail CLI call with
    """

    def __init__(self, message: str, *, code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidArgumentError(FailCLIError):
    """
    Error while parsing arguments.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code=2)


def require_config(config: Config | Exception | None) -> Config:
    """
    Exit with error 3 in case the configuration does not exist or could not be loaded.
    """
    if config is None:
        config = create_config_not_found_error()
    if isinstance(config, Exception):
        raise FailCLIError(f"Error: {config}", code=3)
    return config


__all__ = ("InvalidArgumentError", "FailCLIError", "require_config")
