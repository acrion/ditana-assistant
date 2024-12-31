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
This module contains utility functions for text processing in the Ditana Assistant.

It provides functions to modify text and prepare it for different output contexts.
It uses regular expressions for this. The parallel module `txt_processors_ai` uses LLM instead.
"""

import re

from ditana_assistant.engine import context


def add_markdown_italics(text: str) -> str:
    """
    Add markdown italics formatting to each non-empty line of the input text.

    Args:
        text (str): The input text to be formatted.

    Returns:
        str: The text with markdown italics formatting applied.
    """
    lines = text.split('\n')
    modified_lines = ['_' + line.strip() + '_' if line.strip() else line for line in lines]
    return '\n\n'.join(modified_lines)


def ensure_markdown_horizontal_line(text: str) -> str:
    """
    Ensure the text ends with a markdown horizontal line.

    If the text doesn't end with a valid markdown horizontal line,
    this function adds one.

    Args:
        text (str): The input text to be modified.

    Returns:
        str: The text with a markdown horizontal line at the end.
    """
    valid_patterns = ['---', '***', '___']
    lines = text.strip().split('\n')
    if lines and lines[-1].strip() in valid_patterns:
        return text
    if lines and lines[-1].strip():
        lines.append('')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def remove_comments(text: str) -> str:
    """
    Remove comments from the input text based on the current shell’s comment identifier.

    Args:
        text (str): The input text containing comments to be removed.

    Returns:
        str: The text with comments removed.
    """
    comment_identifier = context.get_comment_identifier()
    result_lines = []

    for line in text.split('\n'):
        stripped_line = line.strip()
        if not stripped_line.startswith(comment_identifier):
            if comment_identifier in line:
                line = line.split(comment_identifier)[0].rstrip()
            if line.strip():
                result_lines.append(line)

    return '\n'.join(result_lines)


def edit_output_for_terminal(assistant_answer: str) -> str:
    """
    Edit the assistant's answer to make it suitable for terminal output.

    This function removes backticks, unnecessary whitespace, single quotes
    at the beginning and end (if present on both sides), and other
    formatting that might interfere with the actual code.

    Args:
        assistant_answer (str): The original answer from the assistant.

    Returns:
        str: The edited answer suitable for terminal output.
    """
    code = assistant_answer.strip()

    code = re.sub(r'^```.*?$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*$\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^`', '', code, flags=re.MULTILINE)
    code = re.sub(r'`.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*powershell\s*$', '', code, flags=re.MULTILINE | re.IGNORECASE)

    if re.match(r'^#\s*[a-z]', code) and code.count('\n') <= 1:
        code = code.lstrip('#').lstrip()

    if code.startswith("'") and code.endswith("'"):
        code = code[1:-1]

    if code.startswith("ditana-assistant "):
        code = "ditana-assistant -q " + code[16:]

    return code


def remove_words_and_phrases(input_text, remove_string, new_string):
    """
    Remove specified words and phrases from the input text, respecting word boundaries.

    This function removes occurrences of the entire remove_string, then
    progressively shorter combinations of words from the remove_string,
    down to individual words. It ensures that only complete words or phrases
    are removed by using word boundaries in regular expressions.

    Args:
    input_text (str): The text to process.
    remove_string (str): String containing words/phrases to remove.

    Returns:
    str: Processed text with specified words and phrases removed.
    """
    # First, remove the entire remove_string if it exists
    input_text = re.sub(r'\b' + re.escape(remove_string) + r'\b', new_string, input_text)

    # Split the remove_string into words
    remove_words = remove_string.split()

    # Generate all possible combinations of words, from longest to shortest
    for length in range(len(remove_words), 0, -1):
        for i in range(len(remove_words) - length + 1):
            phrase = " ".join(remove_words[i:i+length])
            if len(phrase) >= 4:
                input_text = re.sub(r'\b' + re.escape(phrase) + r'\b', new_string, input_text)

    # Remove any double spaces that might have been created
    input_text = re.sub(r'\s+', ' ', input_text)

    # Trim leading and trailing whitespace
    return input_text.strip()


def split_multiline_string(input_string):
    """
    Splits a given multiline string into multiple substrings.

    The function splits the input string based on a pattern of round brackets
    containing any text without spaces or newlines. This is particularly useful
    for parsing lists where items are prefixed with labels in parentheses.
    Everything before the first separator is ignored. Each resulting substring
    is stripped of leading and trailing whitespace, but may contain newlines.

    Args:
    input_string (str): The input multiline string to be split.

    Returns:
    list: A list of substrings resulting from the split operation.

    Example:
    >>> text = "Ignore this\n(a) first part (see below)\n(b) second part\n(c) third part"
    >>> split_multiline_string(text)
    ['first part (see below)', 'second part', 'third part']
    """
    # Define the pattern: round brackets with any content except spaces and newlines
    pattern = r'\(\d+\)'

    # Find all occurrences of the pattern
    separators = list(re.finditer(pattern, input_string))

    if not separators:
        return []

    result = []
    start = separators[0].end()  # Start from the end of the first separator

    # Iterate through separators and extract substrings
    for i in range(1, len(separators)):
        end = separators[i].start()
        substring = input_string[start:end].strip()
        if substring:
            result.append(substring)
        start = separators[i].end()

    # Add the last substring
    last_substring = input_string[start:].strip()
    if last_substring:
        result.append(last_substring)

    return result


def extract_backtick_content(text: str):
    """
    Extracts the stripped text enclosed by backticks from the input string.

    If no backticks are found or the enclosed stripped text is empty,
    the entire input string (stripped) is returned.

    The function uses a robust strategy to handle multiple consecutive backticks:
    It searches for and removes all immediately following backticks after the first one,
    both from the front and back.

    Nested backticks remain unaffected, as only consecutive backticks are removed.

    If fewer than 2 backticks are in the string, the entire stripped text is returned.

    Args:
        text (str): The input string to process.

    Returns:
        str: The extracted and stripped content between backticks, or the entire
             stripped input if no valid backtick-enclosed content is found.
    """
    stripped_text = text.strip()

    # Find the first backtick from the left
    left_index = stripped_text.find('`')
    if left_index == -1:
        return stripped_text

    # Find consecutive backticks from the left
    while left_index + 1 < len(stripped_text) and stripped_text[left_index + 1] == '`':
        left_index += 1

    # Find the first backtick from the right
    right_index = stripped_text.rfind('`')
    if right_index == left_index:
        return stripped_text

    # Find consecutive backticks from the right
    while right_index > left_index and stripped_text[right_index - 1] == '`':
        right_index -= 1

    # Extract and strip the content between backticks
    extracted_content = stripped_text[left_index + 1:right_index].strip()

    # Return the extracted content if not empty, otherwise return the entire stripped text
    return extracted_content if extracted_content else stripped_text
