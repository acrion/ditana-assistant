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
in a text. All of these functions make use of the LLM. The parallel module
`input_analyzers_regex` uses regular expressions instead.
"""

import re
from typing import Optional, List, Dict, Literal

from ditana_assistant.base.output_manager import OutputManager
from ditana_assistant.base import config
from ditana_assistant.base.config import Configuration

from ditana_assistant.engine import input_analyzers_regex
from ditana_assistant.engine import text_processors_ai


def answers_yes(query: str, messages: Optional[List[Dict[Literal["role", "content"], str]]] = None) -> bool:
    """
    Determine if the AI’s response to a query is affirmative.

    Args:
        query (str): The query to process.
        messages (Optional[List[Dict[Literal["role", "content"], str]]]): The dialog so far.

    Returns:
        bool: True if the response is affirmative, False otherwise.
    """
    from ditana_assistant.engine.conversation_manager import ConversationManager
    assistant_answer = ConversationManager(messages).process_input(query)[0].lower()

    OutputManager.print_formatted(query, assistant_answer)

    return bool(re.search(r'\byes\b', assistant_answer))


def is_language(txt: str, lang: str) -> bool:
    """
    Determine if the given text is in the given language.

    Args:
        txt (str): The text to analyze.
        lang (str): The language to check, e.g. "English"

    Returns:
        bool: True if the text is in the specified language, False otherwise.
    """
    if Configuration.get()['ASSUME_ENGLISH'] and lang == "English":
        return True

    result = answers_yes(f'''Is the following text 100% in {lang}? Answer with "yes" or "no" only:

"{txt}"
''')

    return result


def query_refers_to_a_computer(query: str, messages: Optional[List[Dict[Literal["role", "content"], str]]] = None) -> bool:
    """
    Determine if the given query can typically be solved using command line tools.

    Args:
        messages (Optional[List[Dict[Literal["role", "content"], str]]]): The dialog so far.
        query (str): The query to analyze.

    Returns:
        bool: True if the query can likely be solved with terminal commands, False otherwise.
    """
    if query == "":
        return False

    base_question = "Does this query involve checking, modifying, or retrieving information (e.g. system status, file content, or opening applications) from the user’s current computer system?"
    question = f'''{base_question} Answer with "yes" or "no" only:

"{text_processors_ai.ensure_language(query, "English")}"'''

    result = answers_yes(question, messages)

    OutputManager.print_formatted("refers to a computer" if result else "does not refer to a computer", query)

    return result


def query_is_suitable_for_wolfram_alpha(query: str, messages: List[Dict[Literal["role", "content"], str]]) -> bool:
    """
    Determine if the given query is suitable for the [Wolfram|Alpha Short Answers API](https://products.wolframalpha.com/short-answers-api/documentation)

    Args:
        query (str): The query to analyze.
        messages (List[Dict[Literal["role", "content"], str]]): The dialog so far

    Returns:
        bool: True if the query is suitable for the Wolfram|Alpha Short Answers API.
    """
    result = False

    if (query != ""
            and not input_analyzers_regex.likely_contains_multiple_sentences(query)
            and not bool(re.search(r'\n', query.strip()))):
        question = f'''Does this request refer to a single calculation, quantitative measurement, statistic or real-time information about the physical world (such as weather, stock data or population) and can it be answered without knowledge of our previous messages? Answer with "yes" or "no" only:

"{query}"'''

        result = answers_yes(question, messages)
        OutputManager.print_formatted("suitable for Wolfram|Alpha" if result else "not suitable for Wolfram|Alpha", query)

    return result


# deprecated
def query_requires_changes_on_computer(query: str) -> bool:
    """
    Determine if the given query requires changes on the computer system, e.g. changes to a file.

    Args:
        query (str): The query to analyze.

    Returns:
        bool: True if the query requires changes on the computer.
    """
    if query == "":
        return False

    if Configuration.get()['MODEL_TYPE'] == config.ModelType.GEMMA:
        # Gemma is not able to pass the unit tests when using 'Answer with "yes" or "no" only'.
        base_question = "Does this request involve modifying files or states on the computer? To what extent?"
    else:
        base_question = 'Does this request involve changes to the computer? Answer with "yes" or "no" only:'

    question = f'''{base_question}

"{text_processors_ai.ensure_language(query, "English")}"'''

    result = answers_yes(question)

    OutputManager.print_formatted("requires changes on computer" if result else "does not require changes on computer", query)

    return result


# deprecated
def request_is_answerable(query: str, messages: List[Dict[Literal["role", "content"], str]]) -> bool:
    """
    Determine if the given query can be answered based on the dialog held so far.

    Args:
        query (str): The query to analyze
        messages (List[Dict[Literal["role", "content"], str]]): The dialog so far

    Returns:
        bool: True if the query can be answered based on the dialog, False otherwise.
    """
    if query == "":
        return False

    base_question = 'Does our conversation so far more or less contain the answer to the following request? Answer with "yes" or "no" only:'

    question = f'''{base_question}

"{text_processors_ai.ensure_language(query, "English")}"'''

    result = answers_yes(question, messages)

    OutputManager.print_formatted("previous dialog contains the answer" if result else "previous dialog does not contain the answer", query)

    return result


def prompt_can_be_split(prompt: str) -> bool:
    """Determine if the given prompt can be split into two subtasks"""

    return answers_yes(f'''Does it make sense to divide the following prompt into two subtasks in order to tackle them systematically?
    
```
{prompt}
```

Please answer only with "yes" or "no".
''')


def request_is_complex(query: str, messages: List[Dict[Literal["role", "content"], str]]) -> bool:
    """
    Determines if the given request is complex.

    Args:
        query (str): The query to analyze.
        messages (List[Dict[Literal["role", "content"], str]]): The dialog so far.

    Returns:
        bool: True if the request is complex and requires advanced skills, False otherwise.
    """
    if query == "":
        return False  # An empty query is not complex

    result = answers_yes(f'''Does answering this prompt require skills like applying, analyzing, or evaluating information, rather than just remembering or understanding facts? Please answer only with "yes" or "no":
    ```
    {query}
    ```''', messages)

    return result


def are_you_sure(assistant_answer, messages) -> bool:
    """
    Returns if the LLM is sure about the given answer
    Args:
        assistant_answer: the suggested answer of the LLM
        messages: the dialog so far

    Returns: if the LLM is sure about the answer

    """
    from ditana_assistant.engine.conversation_manager import ConversationManager
    conversation = ConversationManager(messages)
    conversation.append_assistant_message(assistant_answer)
    return answers_yes('Are you sure? Please answer only with "yes" or "no".', messages)


def is_likely_code(text):
    """
    Determines whether the given text is likely to be code based on a set of heuristic features.

    Args:
        text (str): The input text to be analyzed for code-like content.

    Returns:
        tuple: A tuple containing two elements:
            - bool: True if the text is likely code, False otherwise.
            - float: A confidence score between 0 and 1, where 1 indicates high confidence
                     that the text is code.
    """
    result = answers_yes(f"""Is the following text (at least part of it) natural language? Please answer in English "yes" or "no".

```
{text}
```""")

    return not result, 0 if result else 1


def is_likely_code_delegate(text):
    """
    Delegates the code detection process to the appropriate method based on the current model type.

    This function serves as a wrapper to handle code detection for different language models.
    For OpenAI models, it uses the AI-based 'is_likely_code' function. For Gemma models,
    it falls back to a regex-based solution using weighted patterns.

    Args:
        text (str): The input text to be analyzed for code-like content.

    Returns:
        tuple: A tuple containing two elements:
            - bool: True if the text is likely code, False otherwise.
            - float: A confidence score between 0 and 1, where 1 indicates high confidence
                     that the text is code. Note: This score is always only meaningful for the
                     regex solution. For LLMs, it’s always 0 or 1.

    Note:
        The behavior of this function depends on the current model type set in the Configuration.
        It's designed to provide a unified interface for code detection across different model types.
    """
    match Configuration.get()['MODEL_TYPE']:
        case config.ModelType.OPENAI:
            return is_likely_code(text)
        case config.ModelType.GEMMA:
            return input_analyzers_regex.is_likely_code(text)
