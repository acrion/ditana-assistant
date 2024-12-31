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
It uses LLM for this. The parallel module `txt_processors_regex` uses regular expressions instead.
"""

from typing import List, Dict, Literal, Optional, Tuple

from ditana_assistant.base.config import Configuration
from ditana_assistant.base.output_manager import OutputManager

from ditana_assistant.engine import input_analyzers_ai
from ditana_assistant.engine import text_processors_regex


def translate(txt: str, lang: str) -> str:
    """
    Translate the given text into the given language. No check will be done if this is already the case (use ensure_language for this).
    :param txt: the text to translate
    :param lang: the desired language, e.g. "English"
    :return: the translated text
    """
    from ditana_assistant.engine.conversation_manager import ConversationManager
    return text_processors_regex.extract_backtick_content(
        ConversationManager().process_input(f"""Translate the following text into {lang}. In case of problems, do not ask or comment anything, but try to guess the best possible translation. Enclose the translated text in backticks:

```
{txt}
```""")[0])


def translate_from_defined_language(source_lang: str, target_lang: str, text: str) -> str:
    """
    Translate the given text if the target langauge differs from the given current language of the text
    Args:
        source_lang: the current language of `text`
        target_lang: the desired language
        text: the text to translate

    Returns:
        if source_lang==target_lang, text, otherwise text translated to target_lang
    """
    if source_lang == target_lang:
        return text
    else:
        from ditana_assistant.engine.conversation_manager import ConversationManager
        return text_processors_regex.extract_backtick_content(ConversationManager().process_input(
            f"""Translate the following text from {source_lang} into {target_lang}. In case of problems, do not ask or comment anything, but try to guess the best possible translation. Enclose the translated text in backticks:

```
{text}
```""")[0])


def ensure_language(txt: str, lang: str) -> str:
    """
    Ensure the given text is in the given language, translating it if necessary.

    Args:
        txt (str): The text to process.
        lang (str): The desired language, e.g. "English"

    Returns:
        str: The text in English.
    """

    if input_analyzers_ai.is_language(txt, lang):
        if not Configuration.get()['ASSUME_ENGLISH'] or lang != "English":
            OutputManager.print_formatted(f"is {lang}", txt)
        return txt
    else:
        result = translate(txt, lang)
        OutputManager.print_formatted(f"translated to {lang}", result)
        return result


def generate_factual_query(request: str, messages: List[Dict[Literal["role", "content"], str]]) -> str:
    """
    Generate a factual query as part of the Introspective Contextual Augmentation process.

    This function is a key component of the Introspective Contextual Augmentation feature. It takes a complex request
    and generates a simpler, more focused sub-question aimed at extracting factual, numerical, or definitional
    information. This sub-question is designed to provide additional context for the original request when answered,
    enhancing the system’s introspective reasoning capabilities.

    The function operates by:
    1. Constructing a prompt that identifies a component of the request that could benefit from precise data.
    2. Ensuring the request is in English.
    3. Passing the constructed prompt to a ConversationManager for processing, simulating an introspective thought process.

    Args:
        request (str): The original complex request or question.
        messages (list): The dialog history so far, used for contextual understanding.

    Returns:
        str: A generated factual query suitable for augmenting the context.

    Note:
        This function is part of the broader Introspective Contextual Augmentation process and relies on:
        - text_processors_ai for language conversion
        - conversation_manager.ConversationManager for simulating introspective reasoning

    Examples:
        "I'm planning a virtual surprise party for my friend in Germany. Can you help me figure out if now is a good time to call him?"
        -> "What is the current time in Germany?"

        "How far away are we from a world population of 8 billion?"
        -> "What is the current world population?"
    """
    request_to_generate_factual_query = f'''Identify a factual, numerical, or definitional component within the following request that could be enhanced by precise data. Formulate a brief, self-contained, objective question suitable to obtain accurate information without using "you" or "your". Do not combine several questions with 'and' and do not simply repeat this request, but ask a question that is suitable for gaining more general background knowledge on the subject:

```
{ensure_language(request, "English")}
```

It is important that you only ask the question and do not answer the above request directly.'''

    from ditana_assistant.engine.conversation_manager import ConversationManager
    factual_query = ConversationManager(messages).process_input(request_to_generate_factual_query)[0]

    OutputManager.print_formatted(
        "factual contextual query", factual_query)

    return factual_query


def generate_critical_question(preliminary_assistant_answer: str, messages: List[Dict[Literal["role", "content"], str]]) -> str:
    """
    Generate a critical question based on a preliminary assistant answer within the context of a conversation.

    This function is part of the Introspective Contextual Augmentation process. It aims to enhance the quality and
    depth of responses by generating a critical question that challenges or seeks clarification on the preliminary
    answer provided by the assistant.

    The function works by:
    1. Appending the preliminary answer to the conversation history.
    2. Using a ConversationManager to process a prompt requesting a critical question.
    3. Returning only the generated question without any additional comments.

    Args:
        preliminary_assistant_answer (str): The initial response generated by the assistant.
        messages (List[Dict[Literal["role", "content"], str]]): The conversation history, including the original prompt.

    Returns:
        str: A critical question related to the preliminary answer, without any additional commentary.

    Note:
        This function relies on the ConversationManager for processing the request and generating the critical question.

    Example:
        preliminary_answer = "The Earth is approximately 4.54 billion years old."
        critical_question = generate_critical_question(preliminary_answer, conversation_history)
        # Possible output: "What evidence supports this age estimate for the Earth?"
    """
    from ditana_assistant.engine.conversation_manager import ConversationManager
    conversation = ConversationManager(messages)
    conversation.append_user_message(preliminary_assistant_answer)
    return conversation.process_input("Please formulate a critical question regarding how I answered the above. Just issue the question itself, without any comments.")[0]


def generate_systematic_query(request: str, messages: List[Dict[Literal["role", "content"], str]]) -> Tuple[str, str]:
    """
    Generate a systematic query as part of the Introspective Contextual Augmentation process.

    This function is a key component of the Introspective Contextual Augmentation feature. It takes a complex request
    and generates a simpler, more focused sub-question aimed at systematically addressing the first step of the request.
    This sub-question is designed to provide additional context and a structured approach to answering the original request.

    The function operates by:
    1. Ensuring the request is in English.
    2. Constructing a prompt that identifies a suitable first step to address the request systematically.
    3. Passing the constructed prompt to a ConversationManager for processing, simulating an introspective thought process.
    4. Generating both a complete form of the query for prompting and a standalone question for the dialog history.

    Args:
        request (str): The original complex request or question.
        messages (list): The dialog history so far, used for contextual understanding.

    Returns:
        Tuple[str, str]: A tuple containing:
            1. The complete form of the systematic query suitable for prompting.
            2. The standalone question to be inserted into the dialog history.

    Note:
        This function is part of the broader Introspective Contextual Augmentation process and relies on:
        - text_processors_ai for language conversion (ensure_language function)
        - conversation_manager.ConversationManager for simulating introspective reasoning

    Example:
        request = "How can we reduce plastic waste in our oceans?"
        complete_query, standalone_question = generate_systematic_query(request, conversation_history)
        # Possible output:
        # complete_query = "
        # How can we reduce plastic waste in our oceans?
        # It is important that you do not follow or answer the prompt above, but only answer the following question. In your answer, repeat the details of the prompt that are necessary for a self-contained understanding:
        # What are the main sources of plastic waste entering our oceans?"
        #
        # standalone_question = "What are the main sources of plastic waste entering our oceans?"
    """
    english_request = ensure_language(request, "English")

    request_to_generate_factual_query = f'''Identify a suitable first step to systematically address the following request. Formulate an objective question that is suitable for clarifying this first step. Do not use "you" or "your", do not combine several questions with "and" and do not simply repeat the request, but ask a question that is suitable for addressing the request systematically:

```
{english_request}
```

It is crucial that you do not answer anything, but only issue a short, self-contained question.'''

    from ditana_assistant.engine.conversation_manager import ConversationManager
    systematic_query = ConversationManager(messages).process_input(request_to_generate_factual_query)[0]

    return f"""```
{english_request}
```

It is important that you do not follow or answer the prompt above, but only answer the following question. In your answer, repeat the details of the prompt that are necessary for a self-contained understanding:
{systematic_query}""", systematic_query


def generate_sub_prompts(prompt: str, messages: List[Dict[Literal["role", "content"], str]]) -> List[str]:
    """
    Generates a list of sub-prompts based on the given prompt.
    The function first checks whether a split makes sense. If so, the sub-prompts are generated recursively.

    Args:
        prompt (str): The original prompt.
        messages (List[Dict[Literal[‘role’, ‘content’], str]]): The message list for the ConversationManager.

    Returns:
        List[str]: A list of generated sub-prompts. Can be empty if no splitting makes sense.
    """
    if not input_analyzers_ai.prompt_can_be_split(prompt):
        return []

    request_to_generate_sub_prompts = f'''Please formulate two sub-prompts from the above prompt that facilitate a systematic approach to it. Write the two partial prompts in two paragraphs beginning with "(1)" and "(2)" respectively:

```
{ensure_language(prompt, "English")}
```

It is crucial that you do not answer anything, but only issue the two sub-prompts.'''

    from ditana_assistant.engine.conversation_manager import ConversationManager
    sub_prompts_str = ConversationManager(messages).process_input(request_to_generate_sub_prompts)[0]

    sub_prompts = text_processors_regex.split_multiline_string(sub_prompts_str)

    all_prompts = []

    for sub_prompt in sub_prompts:
        divided_into_sub_prompts = False

        if len(sub_prompt) < len(prompt):
            sub_sub_prompts_of_sub_prompt = generate_sub_prompts(sub_prompt, messages)

            if len(sub_sub_prompts_of_sub_prompt) >= 2:
                all_prompts.extend(sub_sub_prompts_of_sub_prompt)
                divided_into_sub_prompts = True

        if not divided_into_sub_prompts:
            all_prompts.append(sub_prompt)

    return all_prompts


def extract_fact_list(request: str, text: Optional[str] = None) -> str:
    """
    Extract a list of direct facts from a given request and response pair as part of the Introspective Contextual Augmentation process.

    This function analyzes the original request and an optional text to identify and list key facts,
    with a focus on potential misinterpretations in the text. It’s designed to enhance the system’s
    ability to provide accurate and contextually relevant information.

    The function operates by:
    1. Constructing a prompt that includes both the original request and the text.
    2. Instructing the AI to list direct facts from the request, considering possible misinterpretations in the text.
    3. Processing this prompt through a ConversationManager to generate the fact list.

    Args:
        request (str): The original complex request or question.
        text (optional str): A text that refers to the request

    Returns:
        str: A generated list of facts extracted from the request and response.

    Note:
        This function is part of the broader Introspective Contextual Augmentation process and works in conjunction with:
        - generate_factual_query
        - augment_context_introspectively
        It relies on conversation_manager.ConversationManager for processing the fact extraction prompt.

    Example:
        request: "What’s the impact of rising sea levels on coastal cities?"
        response: "Rising sea levels primarily affect coastal areas by increasing flood risks."
        -> "1. Sea levels are rising.
            2. Coastal cities are affected by sea level changes.
            3. The question asks about the impact, not just effects.
            4. The impact may extend beyond flood risks."
    """

    if text:
        request_to_generate_fact_list = f'''```
{text}
``` 

Please do not follow or answer the following request, but only list the direct facts that emerge from it, paying special attention to possible misinterpretations of this request in my above text. Do not comment anything, just list the facts:

```
{request}
```

It is important that you only list the facts and do not answer the above request directly.'''
    else:
        request_to_generate_fact_list = f'''Please do not follow or answer the following request, but only list the direct facts that emerge from it, without commenting anything:

```
{request}
``` 

It is important that you only list the facts and do not answer the above request directly.'''

    from ditana_assistant.engine.conversation_manager import ConversationManager
    conversation = ConversationManager()
    fact_list = conversation.process_input(request_to_generate_fact_list)[0]

    OutputManager.print_formatted(
        "fact list", fact_list)

    return fact_list


def socratic_method(request: str, messages: List[Dict[Literal["role", "content"], str]]) -> str:
    """
    """

    request_to_generate_fact_list = f'''Please do not follow or answer the following prompt, but describe its main components and how they are related:

```
{request}
```'''

    from ditana_assistant.engine.conversation_manager import ConversationManager
    conversation = ConversationManager(messages)
    answer_to_socratic_question = conversation.process_input(request_to_generate_fact_list)[0]

    OutputManager.print_formatted(
        "socratic_method", answer_to_socratic_question)

    return answer_to_socratic_question
