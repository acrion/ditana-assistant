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
This module manages the graphical user interface window for the Ditana Assistant.
It handles the creation, updating, and interaction with the webview-based GUI.
"""

import json
import os
import queue

import typing
import webview  # https://pywebview.flowrl.com/guide/

from ditana_assistant.engine.conversation_manager import ConversationManager
from ditana_assistant.engine import text_processors_regex


class AssistantWindow:
    """
    Manages the graphical user interface window for the Ditana Assistant.
    """

    def __init__(self, is_open: bool, conversation: ConversationManager):
        """
        Initialize the AssistantWindow.

        Args:
            is_open (bool): Whether the window should be open.
            conversation (ConversationManager): The conversation manager object.
        """
        self.window: typing.Optional[webview.Window] = None
        self.is_open = is_open
        self.ui_update_queue = queue.Queue()

        if is_open:
            self.window = webview.create_window(title='Ditana Assistant',
                                                url=os.path.join(os.path.dirname(__file__), 'index.html'),
                                                js_api=conversation,
                                                width=1280,
                                                height=1024)

            def on_closed():
                print("Main window closed, stopping thread...")
                ConversationManager.stop_thread().set()
                ConversationManager.code_input_event().set()

            self.window.events.closed += on_closed

    def set_version(self, version_info: str) -> None:
        """
        Set the version info for the about-dialog.
        Args:
            version_info (str): The version info string

        """
        if self.window is not None:
            self.ui_update_queue.put(('set_version', version_info))

    def set_ui_input(self, user_input: str) -> None:
        """
        Set the user input in the UI.

        Args:
            user_input (str): The user input to be set in the UI.
        """
        if self.window is not None:
            self.ui_update_queue.put(('input', user_input))

    def set_ui_response(self, response: str) -> None:
        """
        Set the assistant’s response in the UI.

        Args:
            response (str): The assistant’s response to be displayed in the UI.
        """
        if self.window is not None:
            self.ui_update_queue.put(('response', response))

    def click_send_button(self) -> None:
        """
        Simulate clicking the send button in the UI.
        """
        if self.window is not None:
            self.ui_update_queue.put(('click_send', None))

    def process_ui_updates(self) -> None:
        """
        Process any pending UI updates from the queue.
        """
        while not self.ui_update_queue.empty():
            update_type, content = self.ui_update_queue.get()
            if update_type == 'input':
                escaped_content = json.dumps(content)
                self.window.evaluate_js(f"document.getElementById('input').value = {escaped_content}")
            elif update_type == 'response':
                content = text_processors_regex.ensure_markdown_horizontal_line(content)
                escaped_content = json.dumps(content)
                self.window.evaluate_js(f"appendToResponse({escaped_content})")
            elif update_type == 'click_send':
                self.window.evaluate_js("document.getElementById('sendButton').click()")
            elif update_type == 'set_version':
                escaped_content = json.dumps(content)
                self.window.evaluate_js(f"setVersion({escaped_content})")
