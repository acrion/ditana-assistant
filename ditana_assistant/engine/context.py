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
This module provides functions to gather and manage context information
about the system environment for the Ditana Assistant.

It includes functions to determine OS information, desktop environment,
user language, and other system-specific details.
"""

from datetime import datetime
import time
import os
import locale
import platform
import shutil
from typing import Final, Optional

from ditana_assistant.base.config import Configuration
from ditana_assistant.engine import context_processes
from ditana_assistant.engine import text_processors_ai


def get_linux_info() -> str:
    """
    Retrieve detailed information about the Linux distribution.

    Returns:
        str: A string describing the Linux distribution.
    """
    try:
        with open('/etc/os-release', 'r', encoding='utf-8') as f:
            os_release = dict(line.strip().split('=', 1) for line in f if '=' in line)

        id_like = os_release.get('ID_LIKE', '').strip('"')
        pretty_name = os_release.get('PRETTY_NAME', '').strip('"')

        if id_like and id_like.lower() != 'n/a':
            return id_like + " Linux"
        else:
            return pretty_name + " Linux"
    except FileNotFoundError:
        return "Linux"


def get_os_info() -> str:
    """
    Get basic information about the operating system.

    Returns:
        str: The name of the operating system.
    """
    system = platform.system()
    if system == "Darwin":
        return "Mac OS X"

    return system


def get_extended_os_info() -> str:
    """
    Get extended information about the operating system.

    For Linux, this includes distribution details.

    Returns:
        str: Detailed description of the operating system.
    """
    system = get_os_info()
    if system == "Linux":
        return get_linux_info()

    return system


def get_desktop_environment() -> str:
    """
    Determine the current desktop environment.

    Returns:
        str: The name of the current desktop environment, or an empty string if not available.
    """
    return os.environ.get('XDG_CURRENT_DESKTOP', '')


def get_shell() -> str:
    """
    Determine the current shell being used.

    Returns:
        str: The name of the current shell.
    """
    if os.getenv("SHELL"):
        return "bash"
    elif os.getenv("PROMPT"):
        return 'cmd.exe (Windows Batch)'
    else:
        return "PowerShell"


def get_comment_identifier() -> str:
    """
    Get the appropriate comment identifier for the current shell.

    Returns:
        str: The comment identifier (e.g., '#' or 'REM').
    """
    if get_shell() == 'cmd.exe (Windows Batch)':
        return 'REM'
    else:
        return '#'


def get_terminal() -> Optional[str]:
    """
    Get the name of the current terminal.

    Returns:
        str: The name of the terminal, or None if not available.
    """
    terminal_value = os.getenv("TERMINAL")
    if terminal_value:
        return terminal_value

    return None


def get_system_description() -> str:
    """
    Generate a comprehensive description of the current system.

    Returns:
        str: A string describing the OS and desktop environment.
    """
    os_info = get_extended_os_info()
    desktop_env = get_desktop_environment()

    description = f"""{os_info}"""

    if desktop_env:
        description += f" with {desktop_env}"

    return description


def get_open_command() -> Optional[str]:
    """
    Determine the appropriate command to open files or URLs on the current system.

    Returns:
        str: The command to open files or URLs, or None if not available.
    """
    if platform.system() == 'Darwin':
        return 'open'
    elif platform.system() == 'Windows':
        return 'start'
    elif get_desktop_environment() == 'XFCE':
        return 'exo-open'
    elif shutil.which('xdg-open'):
        return 'xdg-open'
    else:
        return None


def get_temporal_locale_identifier():
    """
    Temporarily sets the locale for LC_TIME to the system default to retrieve the locale identifier.
    The function handles locale settings that contain an underscore (e.g., 'de_CH.UTF-8') by returning
    only the part before the underscore. If no underscore is present, it returns the full identifier.
    If an error occurs during the process, 'en' is returned as a fallback.

    Temporarily changing the locale is necessary because Python does not automatically respect the
    environment variables for locale (such as LC_TIME) unless explicitly set. Therefore, we temporarily
    set it to the system’s default and then revert back to the original locale to avoid side effects.

    Returns:
        str: The locale identifier without the part after the underscore, or 'en' if an error occurs.
    """
    current_locale = locale.getlocale(locale.LC_TIME)
    locale.setlocale(locale.LC_TIME, "")

    # Get the locale identifier (e.g., 'de_CH' on Linux or 'English_United States' on Windows)
    locale_identifier = locale.getlocale(locale.LC_TIME)[0]

    # Restore the previous locale setting
    locale.setlocale(locale.LC_TIME, current_locale)

    if locale_identifier is None:
        return "en"

    if "_" in locale_identifier:
        return locale_identifier.split("_")[0]
    else:
        return locale_identifier


def get_user_language() -> str:
    """
    Determine the user’s preferred language, or English, if the detection failed.
    This is based on LC_TIME, because it has a higher chance to be actually the
    user’s spoken language than identifiers such as LC_ALL, LC_MESSAGES or LC_NUMERIC.
    Also see https://docs.python.org/3.12/library/locale.html#locale.LC_TIME

    Returns:
        str: The user’s language
    """

    if Configuration.get()['ASSUME_ENGLISH']:
        return "English"

    locale_dict: Final = {
        'aa': 'Afar',
        'af': 'Afrikaans',
        'an': 'Aragonese',
        'ar': 'Arabic',
        'ast': 'Asturian',
        'be': 'Belarusian',
        'bg': 'Bulgarian',
        'bhb': 'Bhili',
        'br': 'Breton',
        'bs': 'Bosnian',
        'ca': 'Catalan',
        'cs': 'Czech',
        'cy': 'Welsh',
        'da': 'Danish',
        'de': 'German',
        'el': 'Greek',
        'en': 'English',
        'es': 'Spanish',
        'et': 'Estonian',
        'eu': 'Basque',
        'fi': 'Finnish',
        'fo': 'Faroese',
        'fr': 'French',
        'ga': 'Irish',
        'gd': 'Scots',
        'gl': 'Galician',
        'gv': 'Manx',
        'he': 'Hebrew',
        'hr': 'Croatian',
        'hsb': 'Upper',
        'hu': 'Hungarian',
        'id': 'Indonesian',
        'is': 'Icelandic',
        'it': 'Italian',
        'ja': 'Japanese',
        'ka': 'Georgian',
        'kk': 'Kazakh',
        'kl': 'Greenlandic',
        'ko': 'Korean',
        'ku': 'Kurdish',
        'kw': 'Cornish',
        'lg': 'Luganda',
        'lt': 'Lithuanian',
        'lv': 'Latvian',
        'mg': 'Malagasy',
        'mi': 'Maori',
        'mk': 'Macedonian',
        'ms': 'Malay',
        'mt': 'Maltese',
        'nb': 'Norwegian',
        'nl': 'Dutch',
        'nn': 'Nynorsk',
        'oc': 'Occitan',
        'om': 'Oromo',
        'pl': 'Polish',
        'pt': 'Portuguese',
        'ro': 'Romanian',
        'ru': 'Russian',
        'sk': 'Slovak',
        'sl': 'Slovenian',
        'so': 'Somali',
        'sq': 'Albanian',
        'st': 'Sotho',
        'sv': 'Swedish',
        'tcy': 'Tulu',
        'tg': 'Tajik',
        'th': 'Thai',
        'tl': 'Tagalog',
        'tr': 'Turkish',
        'uk': 'Ukrainian',
        'uz': 'Uzbek',
        'wa': 'Walloon',
        'xh': 'Xhosa',
        'yi': 'Yiddish',
        'zh': 'Chinese',
        'zu': 'Zulu',
    }

    lang_code: Final = get_temporal_locale_identifier()

    if lang_code.lower() in locale_dict:
        return locale_dict[lang_code.lower()]
    else:
        return lang_code  # On Windows this is not the code, but the actual name of the language.


def get_system_timezone():
    """
    Retrieve the system timezone.

    This function attempts to get the system timezone name. On Windows, it tries to retrieve
    the timezone from the registry. If that fails, or on non-Windows systems, it falls back
    to using the system’s default timezone.

    Returns:
        str: The name of the system timezone. On Windows, this will be the Windows-specific
             timezone name (e.g., "W. Europe Standard Time"). On other systems, it will typically
             be an IANA timezone abbreviation (e.g., "CET" for Central European Time), see
             https://www.iana.org/time-zones

    See Also:
        For more information about the historical context and complexities of Windows timezones:
        https://superuser.com/questions/1709147/history-explanation-for-time-zones-on-windows
    """
    if platform.system() == 'Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as key:
                tz_name = winreg.QueryValueEx(key, "TimeZoneKeyName")[0]
            return tz_name
        except OSError:
            pass

    return time.tzname[0]


def generate_initial_context() -> str:
    """
    Generate an initial command context for the AI assistant.

    Returns:
        str: A formatted string containing system context and the user’s command.
    """
    user_language = get_user_language()
    description = get_system_description()
    terminal = get_terminal()

    initial_command = f"""I am working on {description}"""

    if terminal:
        initial_command += f" and {terminal}. The current directory is `{os.getcwd()}`"

    local_tz = get_system_timezone()

    running_desktop_applications = context_processes.get_process_info().strip()

    initial_command += f". It is currently {datetime.now().strftime('%A, %B %d, %Y at %H o\'clock')} ({local_tz} time zone)."

    if running_desktop_applications != "":
        initial_command += " The following desktop applications are running:"

    initial_command = text_processors_ai.translate_from_defined_language("English", user_language, initial_command)

    if running_desktop_applications != "":
        initial_command += "\n\n" + running_desktop_applications

    return initial_command


def generate_terminal_command(command) -> str:
    """
    Generate a context-aware terminal command based on the user’s input.

    Args:
        command (str): The user’s command or query.

    Returns:
        str: A formatted string containing system context and instructions for generating a terminal command.
    """
    open_cmd = get_open_command()
    description = get_system_description()

    initial_command = f"""Please suggest a {get_shell()} command for {description}"""

    initial_command += f""" that is suitable for the following task:

"{command}"

Just write the command as it would appear in a terminal. When the task is formulated as a question, generate a command that is suitable for answering the question."""

    if open_cmd:
        initial_command += f" If the task requires opening a desktop application, use {open_cmd} in a suitable way. For example to do Internet searches, use {open_cmd} 'https://duckduckgo.com/?q=example search'."

    initial_command += f""" If in doubt about the meaning of the task or the characteristics of the system, make an educated guess, but prefer indirect workarounds that cover a wider range of circumstances (a web search as a last resort) to guessing that a particular tool is available. Do not include any comments or suggestions, to make sure you issue only syntactically correct {get_shell()} code that could be copied to a terminal."""

    return initial_command
