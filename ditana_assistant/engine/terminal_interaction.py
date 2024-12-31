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
This module handles the terminal-based interaction for the Ditana Assistant.
It manages user input, command execution, and output display in terminal mode.
When the application runs with a GUI, this module handles terminal commands
that may be required during the conversation.
"""

from ditana_assistant.gui.assistant_window import AssistantWindow
from ditana_assistant.base import terminal

from ditana_assistant.engine import text_processors_regex
from ditana_assistant.engine.conversation_manager import ConversationManager


def terminal_thread(conversation: ConversationManager, window: AssistantWindow, user_input: str, quiet: bool) -> None:
    """
    Manages the terminal-based interaction loop for the Ditana Assistant.

    This function handles user input, processes it through the conversation manager,
    executes terminal commands when necessary, and manages output display.
    In GUI mode, it only activates for terminal command execution.

    Args:
        conversation (ConversationManager): The conversation manager object.
        window (AssistantWindow): The UI window object (None in terminal-only mode).
        user_input (str): Initial user input.
        quiet (bool): Whether the assistant is running in quiet mode.
    """
    while not ConversationManager.stop_thread().is_set():
        try:
            if window.is_open:
                ConversationManager.code_input_event().wait()
                if ConversationManager.stop_thread().is_set():
                    break
                code = ConversationManager.code_input_global().get()
                ConversationManager.code_input_event().clear()
                assistant_answer = ""
            else:
                if user_input == "":
                    if quiet:
                        ConversationManager.stop_thread().set()
                        break
                    else:
                        print()
                        user_input = input("Your Message ('enter' to quit): ").strip()
                        if user_input.strip() == "":
                            ConversationManager.stop_thread().set()
                            break
                assistant_answer, code = conversation.process_input(user_input, meta_call=False)

            if not quiet:
                print()

            if code:
                print(code)
                reply = terminal.get_valid_input("Execute above command?")
                if reply == 'n':
                    user_input = "I do not execute this command."
                    conversation.append_user_message(user_input)
                    if window.is_open:
                        window.set_ui_response(text_processors_regex.add_markdown_italics(user_input+"_"))
                        print("Ok, please focus the UI window.")
                        continue
                    else:
                        ConversationManager.stop_thread().set()
                        break

                user_input = execute_code(code, conversation, window)
            else:
                if window.is_open:
                    window.set_ui_response(text_processors_regex.ensure_markdown_horizontal_line(assistant_answer))
                    print("I answered in the UI window - please focus it.")
                else:
                    print(assistant_answer)

                user_input = ""
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(e)


def execute_code(code: str, conversation: ConversationManager, window: AssistantWindow) -> str:
    """
    Execute a given code command and handle its output.

    This function runs the provided code command, processes its output,
    and updates the conversation and UI (if applicable) based on the execution result.

    Args:
        code (str): The command to be executed.
        conversation (ConversationManager): The conversation manager object.
        window (AssistantWindow): The UI window object (None in terminal-only mode).

    Returns:
        str: User input generated based on the command execution result.
            Empty string if the command was successful or the user chose not to fix a failed command.
            Otherwise, contains information about the failed command execution.

    Side effects:
        - Executes the given command using the terminal.
        - Updates the UI with the command output if in GUI mode.
        - Appends the command result to the conversation history.
        - Prompts the user for action if the command fails in terminal-only mode.
    """
    if window.is_open:
        window.set_ui_response(text_processors_regex.ensure_markdown_horizontal_line(code))

    return_code, output = terminal.run_interactive_command(code)

    if return_code == 0:
        user_input = f"""Command executed successfully. Output:
{output}"""

        if window.is_open:
            window.set_ui_response(text_processors_regex.add_markdown_italics(user_input + "_"))
            conversation.append_user_message(user_input)
        else:
            conversation.append_user_message(user_input)
            user_input = ""
    else:
        user_input = f"""Command failed with return code {return_code}. Output:
{output}"""

        if window.is_open:
            window.set_ui_input(user_input)
        else:
            reply = terminal.get_valid_input(f"The command failed with return code {return_code}. Do you want me to try to fix it?")

            # If the user responds with 'y', the error message in user_input will be automatically used
            # by terminal_thread as the next user message, prompting the assistant to attempt a fix.
            # If the response is 'n', we manually add the error message to the conversation history
            # and clear user_input to prevent terminal_thread from automatically proceeding.
            if reply == 'n':
                conversation.append_user_message(user_input)
                user_input = ""

    if window.is_open:
        print("Please focus the UI window.")

    # In terminal mode, a non-empty return value will be used by terminal_thread
    # as the next user message, continuing the conversation flow.
    return user_input
