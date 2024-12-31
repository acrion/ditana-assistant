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
This module provides functions for interacting with the terminal in the Ditana Assistant.
It includes utilities for running interactive commands and handling user input in the terminal.
"""

import os
import subprocess
import sys
from typing import Tuple


def get_valid_input(question_text):
    """
    Prompt the user for a yes/no input and validate the response.

    Args:
        question_text (str): The question to ask the user.

    Returns:
        str: Either 'y' or 'n' based on the user’s validated input.
    """
    while True:
        reply = input(f"{question_text} (y/n) ").lower()
        if reply in ['y', 'n']:
            return reply
        print("Invalid input. Please enter 'y' or 'n'.")


def run_interactive_command_unix(command: str) -> Tuple[int, str]:
    """
    Run an interactive command on Unix-like systems.

    Args:
        command (str): The command to run.

    Returns:
        tuple: A tuple containing the return code and the command output.
    """
    import pty
    import select

    env = os.environ.copy()
    env['PAGER'] = 'cat'
    env['SYSTEMD_PAGER'] = ''
    env['LESS'] = '-F -X'
    env['COLUMNS'] = '500'
    env['LINES'] = '5000'

    master, slave = pty.openpty()
    output = []
    try:
        with subprocess.Popen(
                command,
                shell=True,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                env=env
        ) as process:
            os.close(slave)

            while True:
                rlist, _, _ = select.select([master, sys.stdin], [], [])

                if master in rlist:
                    try:
                        data = os.read(master, 1024)
                        if not data:
                            break
                        sys.stdout.buffer.write(data)
                        sys.stdout.flush()
                        output.append(data)
                    except OSError:
                        break

                if sys.stdin in rlist:
                    data = sys.stdin.buffer.read1(1024)
                    if not data:
                        break
                    os.write(master, data)

            process.wait()
            return_code = process.returncode
    finally:
        os.close(master)

    full_output = b''.join(output).decode('utf-8', errors='replace')
    return return_code, full_output


def run_interactive_command_windows(command: str) -> Tuple[int, str]:
    """
    Run an interactive command on Windows systems.

    Args:
        command (str): The command to run.

    Returns:
        tuple: A tuple containing the return code and the command output.
    """
    output = []
    with subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    ) as process:
        while True:
            line = process.stdout.readline()
            if not line:
                break
            sys.stdout.write(line)
            sys.stdout.flush()
            output.append(line)

        process.wait()
        return_code = process.returncode

    full_output = ''.join(output)
    return return_code, full_output


def run_interactive_command(command: str) -> Tuple[int, str]:
    """
    Run an interactive command on the appropriate platform.

    Args:
        command (str): The command to run.

    Returns:
        tuple: A tuple containing the return code and the command output.
    """
    if os.name == 'nt':
        return run_interactive_command_windows(command)

    return run_interactive_command_unix(command)
