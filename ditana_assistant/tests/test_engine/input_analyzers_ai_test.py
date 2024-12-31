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
This module contains unit tests for the input_analyzers_ai module of the Ditana Assistant.
It tests various functions related to code detection and input analysis.
"""

import unittest

from ditana_assistant.base.config import Configuration, ModelType
from ditana_assistant.base.output_manager import OutputManager

from ditana_assistant.engine import context
from ditana_assistant.engine import input_analyzers_ai
from ditana_assistant.engine.conversation_manager import ConversationManager


OutputManager.hide_messages = True


class TestRequestIsAnswerable(unittest.TestCase):
    """
    Test cases for the request_is_answerable function in the input_analyzer module.
    Tests are performed for both OpenAI and Gemma models.
    """

    conversation: ConversationManager

    @classmethod
    def setUpClass(cls):
        cls.model_types = [ModelType.GEMMA, ModelType.OPENAI]
        cls.conversation = ConversationManager()
        cls.conversation.append_user_message('Ich arbeite auf Arch Linux mit XFCE und Kitty. Es ist derzeit Montag, der 23. September 2024 um 14:00 Uhr. Die folgenden Desktop-Anwendungen sind geöffnet:\n\nxfce4-panel\nxfdesktop  Desktop\n/usr/share/pycharm/jbr//bin/java  003-ditana-assistant – input_analyzers_ai_test.py\n/usr/lib/chromium/chromium Claude -\n/usr/share/pycharm/jbr//bin/java  /media/stefan/data/Documents/git/my-projects/acrion/ditana/packages/003-ditana-assistant/src/input_analyzers_ai.py')

    def run_test_for_both_models(self, test_func):
        """Run the given test function for both OpenAI and Gemma models."""
        for model_type in self.model_types:
            with self.subTest(model=model_type):
                Configuration.set(model_type=model_type)
                print(f"---- Model type: {model_type}  ----")
                test_func()

    def test_available_disk_space(self):
        """On Linux, test if dialog so far is categorized correctly to not help telling the available disk space."""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "Please check the available storage space on the drive containing the current directory."
                self.assertFalse(input_analyzers_ai.request_is_answerable(text, self.conversation.messages))

        self.run_test_for_both_models(test_func)

    def test_summarize_running_apps(self):
        """On Linux, test if dialog so far is categorized correctly to help listing the open apps."""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "Kannst du die Informationen über meine laufenden Desktop-Anwendungen zusammenfassen?"
                self.assertTrue(input_analyzers_ai.request_is_answerable(text, self.conversation.messages))

        self.run_test_for_both_models(test_func)

    def test_output_file(self):
        """On Linux, test if dialog so far is categorized correctly to not contain information about a file content"""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "Gib den Inhalt der Datei ~/test.txt aus."
                self.assertFalse(input_analyzers_ai.request_is_answerable(text, self.conversation.messages))

        self.run_test_for_both_models(test_func)


class TestQueryCanBeSolvedWithTerminal(unittest.TestCase):
    """
    Test cases for the query_can_be_solved_with_terminal function in the input_analyzer module.
    Tests are performed for both OpenAI and Gemma models.
    """

    @classmethod
    def setUpClass(cls):
        cls.model_types = [ModelType.GEMMA, ModelType.OPENAI]

    def run_test_for_both_models(self, test_func):
        """Run the given test function for both OpenAI and Gemma models."""
        for model_type in self.model_types:
            with self.subTest(model=model_type):
                Configuration.set(model_type=model_type)
                print(f"---- Model type: {model_type}  ----")
                test_func()

    def test_systemd_resolved(self):
        """On Linux, test if question about systemd service is categorized correctly as a terminal task."""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "Is systemd-resolved running stably?"
                self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
                self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_file_content_output(self):
        """Test if question about outputting file content is categorized as a terminal task."""

        def test_func():
            text = "Gib den Inhalt der Datei ~/test.txt aus"
            self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
            self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_query_refers_to_a_computer(self):
        """On Linux, test if question about the largest files in the current directory is correctly categorized as a terminal task."""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "What are the largest files in the current directory and below?"
                self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
                self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_open_application(self):
        """On Linux, test if a prompt to open libreoffice is correctly categorized as a terminal task."""

        def test_func():
            if context.get_os_info() == "Linux":
                text = "Öffne libreoffice"
                self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))

        self.run_test_for_both_models(test_func)

    def test_current_audio_device(self):
        """Test if question about current audio device is categorized as a terminal task."""

        def test_func():
            text = "What’s my current audio device?"
            self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
            self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_replace_in_file(self):
        """Test if task to replace text in a file is categorized as a terminal task."""

        def test_func():
            text = "Replace all occurrences of the word 'sun' with 'moon' in the file ./project/test"
            self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
            self.assertTrue(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_cpu_consumption_query(self):
        """Test if question about CPU consumption is categorized as a terminal task."""

        def test_func():
            text = "Which process is consuming so much CPU time?"
            self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
            self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_boot_log_errors_query(self):
        """Test if question about errors in the boot log is categorized as a terminal task."""

        def test_func():
            text = "List errors in the boot log."
            self.assertTrue(input_analyzers_ai.query_refers_to_a_computer(text))
            self.assertFalse(input_analyzers_ai.query_requires_changes_on_computer(text))

        self.run_test_for_both_models(test_func)

    def test_technical_non_terminal_query_blockchain(self):
        """Test if a technical question about blockchain technology is correctly not categorized as a terminal task."""

        def test_func():
            text = "Can you explain how the proof-of-stake consensus mechanism differs from proof-of-work in blockchain technology?"
            self.assertFalse(input_analyzers_ai.query_refers_to_a_computer(text))

        self.run_test_for_both_models(test_func)

    def test_technical_non_terminal_query_quantum_computing(self):
        """Test if a technical question about quantum computing is correctly not categorized as a terminal task."""

        def test_func():
            text = "What are the potential implications of Shor’s algorithm for current encryption methods if large-scale quantum computers become available?"
            self.assertFalse(input_analyzers_ai.query_refers_to_a_computer(text))

        self.run_test_for_both_models(test_func)

    def test_technical_non_terminal_query_ai_ethics(self):
        """Test if a technical question about AI ethics is correctly not categorized as a terminal task."""

        def test_func():
            text = "How can we implement fairness constraints in machine learning models to mitigate algorithmic bias without significantly compromising model performance?"
            self.assertFalse(input_analyzers_ai.query_refers_to_a_computer(text))

        self.run_test_for_both_models(test_func)


if __name__ == '__main__':
    unittest.main()
