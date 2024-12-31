# Copyright (c) 2024, 2025 acrion innovations GmbH
# Authors: Stefan Zipproth, s.zipproth@acrion.ch
#
# This file is part of Ditana Assistant, see https://github.com/acrion/ditana-assistant and https://ditana.org/assistant
#
# Ditana Assistant is offered under a commercial and under the AGPL license.
# For commercial licensing, contact us at https://acrion.ch/sales. For AGPL licensing, see below.

# AGPL licensing:
#
# Ditana Assistant is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ditana Assistant is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Ditana Assistant. If not, see <https://www.gnu.org/licenses/>.

"""
This module provides an OutputManager class for managing console output in the Ditana Assistant.
It includes functionality to print formatted messages, avoid duplicate outputs, reset output history,
and convert newlines to spaces before processing.
"""

from typing import Dict


def truncate_string(input_string: str, max_length: int = 100) -> str:
    """
    Truncates the input string to a maximum length and appends '...' if truncated.

    Args:
        input_string (str): The string to be truncated.
        max_length (int, optional): The maximum length of the output string,
                                    including '...' if truncated. Defaults to 50.

    Returns:
        str: The truncated string, with '...' appended if it was shortened.
    """
    if len(input_string) <= max_length:
        return input_string
    else:
        return input_string[:max_length-3] + '...'


class OutputManager:
    """
    A class to manage console output, avoiding duplicates and providing formatted printing.
    """

    hide_messages: bool = False
    left_size: int = 52
    right_size: int = 100
    output_history: Dict[str, bool] = {}

    @classmethod
    def print_formatted(cls, prefix: str, message: str) -> None:
        """
        Print a formatted message if it hasn't been printed before.
        Converts newlines to spaces before processing.

        Args:
            prefix (str): The prefix for the message.
            message (str): The main content of the message.
        """
        message = message.replace('\n', ' ')
        output = f"   {truncate_string(prefix, cls.left_size).rjust(cls.left_size)}: \"{truncate_string(message, cls.right_size)}\""
        if not cls.hide_messages and output not in cls.output_history:
            print(output)
            cls.output_history[output] = True

    @classmethod
    def reset_history(cls) -> None:
        """
        Reset the output history, allowing all messages to be printed again.
        """
        cls.output_history.clear()
