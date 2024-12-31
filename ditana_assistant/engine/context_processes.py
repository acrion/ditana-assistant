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
This module provides functionality to retrieve information about running processes
and their associated windows across different operating systems (Linux, Windows, and macOS).

The main function, get_process_info(), determines the operating system and calls the
appropriate OS-specific function to gather process information.
"""

import subprocess
import os
import re
import platform


def get_process_info_linux():
    """
    Retrieve information about running processes and their associated windows on Linux.

    This function uses the 'wmctrl' command to get window information and combines it
    with process details from the /proc filesystem.

    Returns:
        str: A string containing information about each window/process, with one entry per line.
             Each line includes the command line and window title.
             Returns an empty string if wmctrl is not available or returns a non-zero exit code.
    """
    try:
        result = []
        hostname = subprocess.check_output("hostname", stderr=subprocess.DEVNULL).decode().strip()
        wmctrl_output = subprocess.check_output(["wmctrl", "-l", "-p"], stderr=subprocess.DEVNULL).decode().splitlines()

        for line in wmctrl_output:
            _, _, pid, *title_parts = line.split(None, 3)
            title = title_parts[0] if title_parts else ""

            process_name = get_process_name(pid)
            cmdline = get_cmdline(pid)

            # Remove hostname from title
            title = re.sub(f'^{re.escape(hostname)} ', '', title)

            # Check if process name is in title (case-insensitive)
            if process_name.lower() not in title.lower():
                title = f"{process_name} {title}"

            # Remove path components from result
            title = remove_path_components(title, cmdline)

            result_line = (cmdline + " " + title).strip()
            result.append(result_line)

        return "\n".join(result)
    except subprocess.CalledProcessError:
        # This catches both cases: when wmctrl is not available and when it returns a non-zero exit code
        return ""


def get_process_info_windows():
    """
    Retrieve information about running processes and their associated windows on Windows.

    This function uses the win32gui, win32process, and psutil libraries to gather
    information about visible windows and their associated processes.

    Returns:
        str: A string containing information about each window/process, with one entry per line.
             Each line includes the command line and window title.
    """
    import win32gui
    import win32process
    import psutil

    def callback(hwnd, windows):
        """
        Callback function for EnumWindows to process each window.

        Args:
            hwnd: Window handle.
            windows: List to store window information.

        Returns:
            bool: Always returns True to continue enumeration.
        """
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                exe = process.exe()
                name = process.name()
                title = win32gui.GetWindowText(hwnd)

                # Remove path components from title
                title = remove_path_components(title, exe)

                # Combine name and title if name is not in title
                if name.lower() not in title.lower():
                    title = f"{name} {title}"

                cmdline = " ".join(process.cmdline())
                windows.append(f"{cmdline} {title}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    return "\n".join(windows)


def get_process_info_macos():
    """
    Retrieve information about running processes and their associated windows on macOS.

    This function is currently not implemented.

    Returns:
        str: An empty string.
    """
    return ""


def get_process_name(pid):
    """
    Get the name of a process given its PID on Linux.

    Args:
        pid (str): The process ID.

    Returns:
        str: The name of the process, or an empty string if the information cannot be retrieved.
    """
    try:
        with open(f'/proc/{pid}/comm', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return ""


def get_cmdline(pid):
    """
    Get the command line of a process given its PID on Linux.

    Args:
        pid (str): The process ID.

    Returns:
        str: The command line of the process, or an empty string if the information cannot be retrieved.
    """
    try:
        with open(f'/proc/{pid}/cmdline', 'r', encoding='utf-8') as f:
            return f.read().replace('\x00', ' ').split()[0]
    except:
        return ""


def remove_path_components(text, path):
    """
    Remove path components from a given text.

    This function is used to clean up window titles by removing path components
    that might be present in the process executable path.

    Args:
        text (str): The text to clean up.
        path (str): The path containing components to remove from the text.

    Returns:
        str: The cleaned up text with path components removed.
    """
    components = path.lower().split(os.sep)
    for component in components:
        if component:
            text = re.sub(rf'\b{re.escape(component)}\b', '', text, flags=re.IGNORECASE)
    return text


def get_process_info():
    """
    Get information about running processes and their associated windows for the current operating system.

    This function determines the current operating system and calls the appropriate
    OS-specific function to gather process and window information.

    Returns:
        str: A string containing information about each window/process, with one entry per line.
             Each line includes the command line and window title.
             Returns an empty string if the operating system is not supported.
    """
    system = platform.system()
    if system == "Linux":
        return get_process_info_linux()
    elif system == "Windows":
        return get_process_info_windows()
    elif system == "Darwin":
        return get_process_info_macos()
    else:
        return ""
