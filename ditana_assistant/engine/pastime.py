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
This module is somewhat isolated from the rest of the code because it is essentially
intended to be fun. It does not help with the assistance functions, but aims to provide
a human-like conversation in the sense that the other person has their own interests.

We deliberately try not to influence the behaviour of the dialogue partner, but to get
the most human-like behaviour possible. This can lead to unexpected dialogue, which is
part of the fun.

We deliberately do not try to make the model impersonate a character, so we do not use
the message list. The entire dialogue is always represented in a single message from the
user, so the assistant’s response is the next line of dialogue, which is then appended
to that single message.
"""

from typing import List, Tuple, Optional
import re

from ditana_assistant.base.config import Configuration, ModelType

from ditana_assistant.engine import context
from ditana_assistant.engine import text_processors_ai
from ditana_assistant.engine import text_processors_regex


class DialogContainer:
    """
    A class to manage and format dialog entries.

    This class provides functionality to add dialog entries, store them internally,
    and format them into a single string representation.

    Attributes:
        _dialog_container (List[Tuple[bool, str]]): A list to store dialog entries.
        _character_name: The name of the dialog partner that is not the user
    """

    def __init__(self):
        """Initialize an empty dialog container."""
        from ditana_assistant.engine.conversation_manager import ConversationManager
        # Gemma gets confused when translating below texts (even sentence-wise). Also, translation of the dialog proves suboptimal. So we use English for Gemma.
        self.use_user_language: bool = Configuration.get()['MODEL_TYPE'] != ModelType.GEMMA
        self._dialog_container: List[Tuple[bool, str]] = []
        self._character_name: str = ConversationManager.impersonate() if ConversationManager.impersonate() else "Jean-Baptiste Clamence from the novel of Albert Camus"
        self._short_name: str = get_short_name(self._character_name)
        self._translated_character_name: str = self.translate(self._character_name)
        self._translated_short_name: str = get_short_name(self._translated_character_name)
        self._user_name: str = self.translate("Stranger")

        self.request_for_response_of_fictional_character = self.translate(f"""This is a fictional dialog between {self._character_name} and a stranger that I wrote. \
Please suggest what {self._short_name} could say next to behave in a typical way, but still respond to what the stranger has said and encourage them to continue the conversation. \
Please just write a single suggestion for {self._short_name}’s next line of dialog without commenting or questioning.""")

        self.request_for_initial_line_of_fictional_character = self.translate(f"""\
Please suggest a line of dialog for a fictional dialog between {self._character_name} and a stranger. \
In this line of dialogue, {self._short_name} meets the stranger for the first time and behaves in a way that is typical of their behaviour. \
Please just write a single suggestion for {self._short_name}’s next line of dialog without commenting or questioning.""")

    @staticmethod
    def extract_cited_block(text: str):
        """
        If the given string contains exactly two lines that contain only three backticks ```,
        then return the lines between these two, otherwise the whole string. Some LLMs
        put generated text between such lines and comment it, even if instructed not to comment.
        Args:
            text: the string, potentially containing cited text

        Returns:
            the cleaned string
        """
        lines = text.split('\n')
        backtick_lines = [i for i, line in enumerate(lines) if line.strip() == '```']

        if len(backtick_lines) == 2:
            start, end = backtick_lines
            return '\n'.join(lines[start + 1:end])
        else:
            return text

    def add_dialog_entry(self, is_user: bool, dialog: str) -> None:
        """
        Add a new dialog entry to the internal dialog container.
        If `dialog` is enclosed in quotation marks, they are removed.

        Args:
            is_user (bool): True, if the dialog line is from the user, otherwise False
            dialog (str): The dialog line(s) for the character.
        """
        self._dialog_container.append((is_user, dialog.strip('" ')))

    def format_dialog(self) -> str:
        """
        Format all stored dialog entries into a single string.

        Returns:
            str: A formatted string representation of all dialog entries.
        """
        formatted_dialog = ""
        for is_user, lines in self._dialog_container:
            name = self._user_name if is_user else self._short_name
            formatted_dialog += f'{name}: "{lines}"\n\n'
        return formatted_dialog.strip()

    def response_of_fictional_character(self) -> str:
        """
        Generate the next thing that the fictional character says to the user.

        Returns:
            The new dialog line of the fictional character.

        """
        from ditana_assistant.engine.conversation_manager import ConversationManager

        return self.filter_response(ConversationManager().process_input(f"""```
{self.format_dialog()}
```

{self.request_for_response_of_fictional_character}""")[0])

    def initial_line_of_fictional_character(self) -> str:
        """
        Return the first thing that the fictional character says to the user.
        We deliberately do not influence what this should be, but leave
        it to the model.

        Returns:
            The first thing that the fictional character tells the user.

        """
        from ditana_assistant.engine.conversation_manager import ConversationManager

        return self.filter_response(ConversationManager().process_input(self.request_for_initial_line_of_fictional_character)[0])

    @staticmethod
    def extract_text(response):
        """
        Extract text from a string based on a specific pattern.

        This function looks for patterns of the form "Name: " or "Name-With-Hyphens: "
        at the beginning of lines. It has two modes of operation:

        1. If the pattern occurs multiple times:
           It returns the text between the first and second occurrence of the pattern.

        2. If the pattern occurs once or not at all:
           It removes the first occurrence of the pattern (if present) and returns the rest of the text.

        Args:
        response (str): The input string to process.

        Returns:
        str: The extracted text based on the above rules.
        """
        # Define the pattern for the prefix (Name: or similar at the beginning of the line)
        pattern = r'^[\w-]+:\s*"?'

        # Find all occurrences of the pattern
        matches = list(re.finditer(pattern, response, re.MULTILINE))

        if len(matches) > 1:
            # If there’s more than one occurrence, extract the text between the first and second occurrence
            start = matches[0].end()
            end = matches[1].start()
            return response[start:end].strip()
        else:
            # If there’s only one or no occurrence, simply remove the first prefix
            return re.sub(pattern, '', response, count=1).strip()

    def filter_response(self, response) -> str:
        """
        - Removes the name of the fictional character at the beginning of the given text
        - Replaces the fictional character name with "Ditana" (in case it occurs anywhere else than at then beginning)
        - Removes quotation marks
        Args:
            response: the input text

        Returns:
            the cleaned text
        """
        response = DialogContainer.extract_cited_block(response)
        response = DialogContainer.extract_text(response)
        response = response.strip(' \n"')
        from ditana_assistant.engine.conversation_manager import ConversationManager
        if not ConversationManager.impersonate():
            response = text_processors_regex.remove_words_and_phrases(response, self._translated_character_name, "Ditana")
            response = text_processors_regex.remove_words_and_phrases(response, self._character_name, "Ditana")
        return response

    def translate(self, text: str) -> str:
        """
        Convenience function to translate from English to the user’s language.
        Args:
            text: the english text

        Returns:
            the translated text
        """
        if self.use_user_language:
            return text_processors_ai.translate_from_defined_language("English", context.get_user_language(), text)
        else:
            return text


dialog_container: Optional[DialogContainer] = None


def get_short_name(character_name: str) -> str:
    """
    Extract the first word from the given string that has at least 4 letters.

    This function splits the input string into words and returns the first word
    that is at least 4 characters long. If no such word is found, it returns
    the entire original string.

    Args:
        character_name (str): The input string to process.

    Returns:
        str: The first word with at least 4 letters, or the entire input string
             if no such word is found.

    Examples:
        >>> get_short_name("John Doe")
        'John'
        >>> get_short_name("Dr. Smith")
        'Defg'
        >>> get_short_name("Bob")
        'Bob'
    """
    words = character_name.split()
    for short_name in words:
        if len(short_name) >= 4:
            return short_name
    return character_name


def reply(user_input: str) -> str:
    """
    Generate a reply based on the dialog so far

    Args:
        user_input (str): the user input text

    Returns:
        the response of the fictional character
    """

    global dialog_container
    if not dialog_container:
        dialog_container = DialogContainer()

    dialog_container.add_dialog_entry(True, user_input)

    answer = dialog_container.response_of_fictional_character()

    dialog_container.add_dialog_entry(False, answer)

    return answer


def initial_line() -> str:
    """
    Generate the initial line of the fictional character, in case the user did not say anything.

    Returns:
        the response of the fictional character
    """

    global dialog_container
    if not dialog_container:
        dialog_container = DialogContainer()

    answer = dialog_container.initial_line_of_fictional_character()

    dialog_container.add_dialog_entry(False, answer)
    return answer
