#!/usr/bin/env python3

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
This is the main entry point for the Ditana Assistant application.
It handles command-line arguments, initializes the necessary components,
and starts the main conversation loop.
"""

import sys
import threading
import time

import argparse
from importlib.metadata import version, PackageNotFoundError
import os
import platform

import platformdirs
import webview  # https://pywebview.flowrl.com/guide/

from ditana_assistant.base import config
from ditana_assistant.base.config import Configuration
from ditana_assistant.base.output_manager import OutputManager

from ditana_assistant.engine import pastime
from ditana_assistant.engine import context
from ditana_assistant.engine.conversation_manager import ConversationManager
from ditana_assistant.engine import terminal_interaction

from ditana_assistant.gui.assistant_window import AssistantWindow


def main():
    """
    The main function that sets up and runs the Ditana Assistant.
    """
    if Configuration.get()['MODEL_TYPE'] == config.ModelType.OPENAI and not os.environ.get('OPENAI_API_KEY'):
        print("""
Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.

To get an API key:
1. Visit https://platform.openai.com/account/api-keys
2. Generate a new key
3. Set it in your environment:
   export OPENAI_API_KEY='your-api-key-here'  # Unix/Linux
   setx OPENAI_API_KEY "your-api-key-here"    # Windows (restart terminal after)""")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Ditana Assistant")
    parser.add_argument("-v", "--version", action="store_true", help="Show the version of Ditana Assistant and exit.")
    parser.add_argument("-u", "--gui", action="store_true", help="Display a graphical dialog.")
    parser.add_argument("-a", "--augmentation", action="store_true", help="Enable Introspective Contextual Augmentation (ICA) for enhanced AI responses.")
    parser.add_argument("-w", "--wolfram-alpha", action="store_true", help="Force use of Wolfram|Alpha for first prompt.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Run in quiet mode. No progress output, no continuation of dialog (except confirmation of command execution).")
    parser.add_argument("-p", "--pastime", action="store_true", help="Pastime mode with a human-like dialog partner.")
    parser.add_argument("-i", "--impersonate", type=str, help="In Pastime mode, optionally impersonate the person you specify (implies -p).")
    parser.add_argument("task", nargs=argparse.REMAINDER, help="The task for the assistant.")

    args = parser.parse_args()

    version_info = ""
    try:
        version_info = version('ditana-assistant')
    except PackageNotFoundError:
        version_info = "unknown"

    if args.version:
        print(f"Ditana Assistant version: {version_info}")
        sys.exit(0)

    if args.gui and args.quiet:
        print("Error: The options '-u/--gui' and '-q/--quiet' cannot be used together. "
              "In GUI mode, user input is always expected. The quiet mode is intended for terminal-based usage only.",
              file=sys.stderr)
        sys.exit(1)

    OutputManager.hide_messages = args.quiet

    if args.wolfram_alpha:
        ConversationManager.set_force_wolfram_alpha(True)

    if args.augmentation:
        ConversationManager.set_ica(True)

    if args.impersonate and not args.pastime:
        args.pastime = True

    if args.pastime:
        ConversationManager.set_pastime_mode(True)
        ConversationManager.set_impersonate(args.impersonate)
        if args.impersonate:
            print(f'(impersonating {args.impersonate})')
        else:
            print('(impersonating Ditana)')
        print()

    user_input = " ".join(args.task).strip() if args.task else ""

    if user_input == "" and not args.gui and not args.pastime:
        parser.print_help()
        sys.exit(0)

    conversation = ConversationManager()
    if not args.pastime:
        conversation.append_user_message(context.generate_initial_context())

    window = AssistantWindow(args.gui, conversation)

    if not args.gui and args.pastime:
        if user_input == "":
            print(pastime.initial_line())

    terminal_thread_instance = threading.Thread(target=terminal_interaction.terminal_thread, args=(conversation, window, user_input, args.quiet))
    terminal_thread_instance.start()

    if args.gui:
        window.set_version(version_info)
        if args.pastime and user_input == "":
            window.set_ui_response(pastime.initial_line())

        def ui_update_thread():
            while not ConversationManager.stop_thread().is_set():
                window.process_ui_updates()
                time.sleep(0.1)  # Check for updates every 100ms

        ui_update_thread = threading.Thread(target=ui_update_thread)
        ui_update_thread.start()

        if user_input != "":
            window.set_ui_input(user_input)
            window.click_send_button()

        # Environment variable configuration to mitigate rendering issues.
        # Prevents blank window occurrences on systems with NVIDIA GPUs.
        #  - WEBKIT_DISABLE_COMPOSITING_MODE=1 (Windows) - Disables compositing mode
        #  - WEBKIT_DISABLE_DMABUF_RENDERER=1 (Linux) - Disables DMABUF renderer
        # These settings do not impact Ditana Assistant’s performance
        # as it does not rely on GPU-accelerated rendering features.
        # While primarily needed for Windows and Linux, setting these for all platforms
        # in the same way, including macOS, allows for consistent behavior across platforms
        # and simplifies cross-platform development.
        os.environ['WEBKIT_DISABLE_DMABUF_RENDERER'] = '1'  # relevant for Linux
        os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'  # relevant for Windows

        # Force 'edgechromium' on Windows for Ditana Assistant compatibility.
        # pywebview defaults to 'mshtml' on Windows if 'edgechromium' is unavailable
        # This ensures a more meaningful error (hopefully related to missing Edge Runtime)
        # instead of ambiguous JavaScript errors from 'mshtml'.
        webview.start(storage_path=platformdirs.user_data_dir(),
                      debug=Configuration.get()['SHOW_DEBUG_MESSAGES'],
                      gui='edgechromium' if platform.system() == "Windows" else None)

        ui_update_thread.join()

    terminal_thread_instance.join()
