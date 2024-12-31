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
This module provides functions for analyzing a given text to determine its
nature of user and return `bool`, indicating if a certain attribute was found
in a text. All of these functions make use of regular expressions. The parallel
module `input_analyzers_ai` uses the LLM instead.
"""

from typing import Final, Tuple
import re


def likely_contains_multiple_sentences(text: str) -> bool:
    """
    Estimate whether the given text likely contains multiple sentences.

    This function checks for patterns that are common in texts with multiple sentences:
    two lowercase letters followed by a period, question mark, or exclamation mark,
    and then any whitespace (including newlines). These patterns are often found at
    the end of a sentence within a larger text, but are less likely to occur in texts
    containing only a single sentence.

    Args:
        text (str): The input text to analyze.

    Returns:
        bool: True if the text likely contains multiple sentences, False otherwise.

    Note:
        - The text is stripped of leading and trailing whitespace before analysis.
        - This method has limitations:
          - It may give false positives for certain abbreviations followed by punctuation.
          - It doesn't account for unconventional writing styles or specific formatting.
    """
    return bool(re.search(r'[a-z.]{2}[.!?]\s', text.strip()))


def is_likely_code(text: str) -> Tuple[bool, float]:
    """
    Determines whether the given text is likely to be code based on a set of heuristic features.

    This function employs a weighted scoring system with multiple features to assess the likelihood
    of the input text being code. The weights and threshold have been optimized through an iterative
    process using unit tests, specifically by maximizing the difference between the minimum 'true'
    score and the maximum 'false' score across a diverse set of test cases.

    The optimization approach, while unconventional, proves effective for this specific use case.
    It allows for fine-tuning based on real-world examples encountered in the application, rather
    than relying on artificially generated test cases. New test cases are added as edge cases are
    discovered during actual usage, ensuring the function’s robustness and adaptability.

    Args:
        text (str): The input text to be analyzed.

    Returns:
        Tuple[bool, float]: A tuple containing:
            - bool: True if the text is likely code, False otherwise.
            - float: The confidence score of the classification.

    Note:
        The magic numbers (weights, bias, and threshold) in this function are the result of
        the aforementioned optimization process. They should be adjusted with caution and
        only after thorough testing with an expanded set of test cases.

    Warning:
        An empty string input will always return (False, NaN).
    """
    if text == "":
        return False, float('nan')

    features = [
        (count_programming_tokens, 13),
        (count_special_characters, 21),
        (check_indentation, 1),
        (check_line_starts, 25),
        (check_camel_case, 1),
        (count_single_letter_variables, 44),
    ]

    total_score = 0
    total_weight = 0

    bias: Final = 2/3

    for feature_func, weight in features:
        score = feature_func(text)
        total_score += score ** bias * weight
        total_weight += weight

    confidence = total_score / total_weight
    return confidence >= 0.22640178458793886, confidence


def count_programming_tokens(text: str) -> float:
    """
    Count the proportion of programming-related patterns in the text.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of programming patterns.
    """
    programming_patterns = [
        r'\b(if|else|return|for|do|while|print|function|def|class|import|from)\b',  # Common keywords
        r'\.[^\s0-9]',  # A dot followed by a non-whitespace and non-digit character (e.g., method calls, property access)
        r'-[A-Z]',  # A hyphen followed by an uppercase letter (e.g., PowerShell cmdlets)
        r'[\[\]]',  # Square brackets
        r'==|!=|<=|>=|&&|\|\|',  # Common comparison and logical operators
        r'#.*$',  # Single-line comments
        r'//.*$',  # Alternative single-line comments
        r'/\*[\s\S]*?\*/',  # Multi-line comments
        r'"\w+":',  # JSON-style key definitions
        r'(?<=\s)@\w+',  # Decorators or annotations
        r'\$\w+',  # Variable names in shell scripts or PHP
        r'(?<!:)//[^/\s]+',  # URLs in code (excluding http:// or https://)
    ]

    total_matches = 0
    for pattern in programming_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        total_matches += len(matches)

    # Normalize the score based on text length
    text_length = len(text.split())
    normalized_score = min(total_matches / max(text_length, 1), 1)

    return normalized_score


def count_special_characters(text: str) -> float:
    """
    Count the proportion of special characters often used in programming.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of special characters.
    """
    special_chars = '|$#[]<>&_{}~/\\'
    char_count = sum(text.count(char) for char in special_chars)
    return min(char_count / len(text) * 10, 1) if text else 0


def check_indentation(text: str) -> float:
    """
    Check the proportion of indented lines in the text.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of indented lines.
    """
    lines = text.split('\n')
    indented_lines = sum(
        1 for line in lines if line.strip() and line[0].isspace() and not line.lstrip().startswith('-'))
    return indented_lines / len(lines) if lines else 0


def check_line_starts(text: str) -> float:
    """
    Check the proportion of lines starting with lowercase letters.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of lines starting with lowercase letters.
    """
    lines = text.split('\n')
    lowercase_starts = sum(1 for line in lines if line.strip() and line[0].islower())
    return lowercase_starts / len(lines) if lines else 0


def check_camel_case(text: str) -> float:
    """
    Check the proportion of camelCase words in the text.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of camelCase words.
    """
    camel_case_pattern = r'[a-z]+([A-Z][a-z]+)+'
    camel_case_words = len(re.findall(camel_case_pattern, text))
    return min(camel_case_words / len(text.split()) if text.split() else 0, 1)


def count_single_letter_variables(text: str) -> float:
    """
    Count the proportion of single-letter variables in the text.

    Args:
        text (str): The text to analyze.

    Returns:
        float: A score between 0 and 1 representing the proportion of single-letter variables.
    """
    single_letters = re.findall(r'\b[a-zA-Z]\b', text)
    return min(len(single_letters) / len(text.split()) if text.split() else 0, 1)
