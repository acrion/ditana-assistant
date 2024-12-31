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
This module manages the conversation flow in the Ditana Assistant.
It handles user inputs, processes them through the AI model, and manages the conversation context.
"""
from typing import Final, Optional, List, Dict, Literal, Tuple

from ditana_assistant.base import model_interface
from ditana_assistant.base.config import Configuration
from ditana_assistant.base.output_manager import truncate_string, OutputManager
from ditana_assistant.base.request_manager import RequestManager

from ditana_assistant.engine import context
from ditana_assistant.engine import input_analyzers_ai
from ditana_assistant.engine import pastime
from ditana_assistant.engine import text_processors_ai
from ditana_assistant.engine import text_processors_regex


class ConversationManager(RequestManager):
    """
    Manages the conversation flow between the user and the AI assistant.
    """

    def __init__(
        self,
        messages: Optional[List[Dict[Literal["role", "content"], str]]] = None,
    ):
        """
        Initialize the ConversationManager.

        Args:
            messages (List[Dict[Literal["role", "content"], str]], optional):
                Initial conversation messages. Defaults to None.
        """
        self.messages = messages.copy() if messages is not None else []

    def append_user_message(self, content: str):
        """
        Append a user message to the conversation history.

        Args:
            content (str): Content of the user message.
        """
        self.messages.append({"role": "user", "content": content})

    def append_assistant_message(self, content: str):
        """
        Append an assistant message to the conversation history.

        Args:
            content (str): Content of the assistant message.
        """
        self.messages.append({"role": "assistant", "content": content})

    def is_first_reply(self) -> bool:
        """
        Checks if the assistant did not reply yet.

        Returns:
            bool: True if the `messages` do not contain any message with the role "assistant",
                  False otherwise.
        """
        return not any(message["role"] == "assistant" for message in self.messages)

    #    def print_request_body(self, r, *args, **kwargs):
    #        print(f"Sent data:\n{r.request.body.decode('utf-8')}")

    def augment_context_introspectively(self, request: str) -> None:
        """
        Augments the context of a given request introspectively by generating and processing a contextual query.

        This method implements Introspective Contextual Augmentation through the following steps:
        1. Generates a contextual query based on the input request.
        2. Submits the contextual query to Wolfram|Alpha for factual information.
        3. If Wolfram|Alpha fails, processes the query using an LLM via ConversationManager.
        4. Appends the obtained contextual information to the assistant’s message history.

        The augmentation process aims to provide additional, factual context to enhance
        the quality and accuracy of subsequent responses through introspective reasoning.

        Args:
            request (str): The original user request to be contextually augmented.

        Returns:
            None

        Side Effects:
            - Prints formatted output of Wolfram|Alpha’s response or error.
            - Appends contextual information to the assistant’s message history.

        Note:
            This method relies on external modules and services:
            - input_analyzers_ai for generating the contextual query
            - wolfram_alpha for querying Wolfram|Alpha
            - ConversationManager for LLM processing
        """
        if self.ica():
            factual_query = ""
            wolfram_alpha_answer = None

            if (Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'] is not None
                    and Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'] != ""):
                factual_query = text_processors_ai.generate_factual_query(request, self.messages)
                wolfram_alpha_answer, wolfram_alpha_error = ConversationManager.wolfram_alpha().query(factual_query)
                if wolfram_alpha_answer:
                    OutputManager.print_formatted("Wolfram|Alpha’s answer to factual query", wolfram_alpha_answer)
                else:
                    OutputManager.print_formatted("Wolfram|Alpha declined factual query", wolfram_alpha_error)

            systematic_query_including_request, systematic_query = text_processors_ai.generate_systematic_query(request, self.messages)
            OutputManager.print_formatted("systematic contextual query", systematic_query)
            answer_to_systematic_query, _ = ConversationManager(self.messages).process_input(systematic_query_including_request)
            OutputManager.print_formatted("answer to systematic query", answer_to_systematic_query)

            if wolfram_alpha_answer:
                self.append_user_message(factual_query)
                self.append_assistant_message(wolfram_alpha_answer)

            self.append_user_message(systematic_query)
            self.append_assistant_message(answer_to_systematic_query)

    #            fact_list = text_processors_ai.extract_fact_list(request, answer_to_systematic_query)
    #            self.append_user_message(fact_list)

    def generate_assistant_response(self, generate_terminal_command: bool, use_wolfram_alpha: bool, query: str, english_query: str, meta_call: bool) -> Tuple[str, Optional[str]]:
        """
        Generate an appropriate response based on the input query and various conditions.

        This function handles the generation of responses using either Wolfram|Alpha or a model request.
        It also analyzes the output regarding terminal commands.

        Args:
            generate_terminal_command (bool): Indicates whether `query` generates a terminal command.
            use_wolfram_alpha (bool): Whether to use Wolfram|Alpha for the query.
            query (str): The original query.
            english_query (str): The query translated to English, if applicable.
            meta_call (bool): Whether this is a meta call.

        Returns:
            tuple: A tuple containing the assistant’s answer and any generated code.
        """
        assistant_answer = None

        if use_wolfram_alpha:
            assistant_answer, wolfram_alpha_error = ConversationManager.wolfram_alpha().query(english_query)

            if wolfram_alpha_error:
                use_wolfram_alpha = False
                OutputManager.print_formatted("Wolfram|Alpha error", wolfram_alpha_error)
                self.augment_context_introspectively(english_query)
            else:
                OutputManager.print_formatted("Wolfram|Alpha answer", assistant_answer)

        if query != "":
            self.append_user_message(query)

        if not use_wolfram_alpha:
            assistant_answer = self.send_model_request(model_interface.get_request(self.messages))

            if Configuration.get()['OFFER_CMD_EXECUTION'] and generate_terminal_command and not meta_call:
                translated_request_to_user: str = text_processors_ai.ensure_language("""I suggest a command to be executed.
Please focus the terminal window to confirm.""", context.get_user_language())
                code = text_processors_regex.edit_output_for_terminal(assistant_answer)
                ConversationManager.code_input_global().put(code)
                ConversationManager.code_input_event().set()
                return translated_request_to_user, code.strip()

        return assistant_answer.strip(), None

    def generate_response_based_on_input_type(
            self,
            generate_terminal_command: bool,
            meta_call: bool,
            query: str,
            is_english: bool = False) -> Tuple[str, Optional[str]]:
        """
        Generate a response based on the type of input and various conditions.

        This method determines the appropriate way to generate a response by considering
        factors such as whether to use Wolfram|Alpha, generate a terminal command,
        or process a meta call. It then calls the necessary methods to produce the response.

        Args:
            generate_terminal_command (bool): Indicates whether to generate a terminal command.
            meta_call (bool): Indicates if this is a meta call (auto-generated by internal functions).
            query (str): The original input query from the user or internal request.
            is_english: The query is known to be in English (no need to check it)

        Returns:
            tuple: A tuple containing two elements:
                - assistant_answer (str): The main response generated by the assistant.
                - code (str or None): Any generated code or terminal command, if applicable.

        Note:
            This method handles debug output, language translation for Wolfram|Alpha queries,
            and determines whether to use Wolfram|Alpha based on the input type and settings.
        """
        if Configuration.get()['SHOW_DEBUG_MESSAGES']:
            print("----------------------------------------------------------------")
            print("Message queue:")
            print("----------------------------------------------------------------")
            print(self.messages)
            print("--- End of message queue ---------------------------------------")

        ica = False

        if generate_terminal_command or meta_call:
            english_query = None
            use_wolfram_alpha = False
        else:
            force_wolfram_alpha = ConversationManager.force_wolfram_alpha() and self.is_first_reply()
            english_query = query if is_english or force_wolfram_alpha else text_processors_ai.ensure_language(query, "English")
            use_wolfram_alpha = (force_wolfram_alpha
                                 or (Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'] is not None
                                     and Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'] != ""
                                     and input_analyzers_ai.query_is_suitable_for_wolfram_alpha(english_query, self.messages)))

            if self.ica() and not use_wolfram_alpha:
                self.augment_context_introspectively(english_query)
                ica = True

        assistant_answer, code = self.generate_assistant_response(generate_terminal_command, use_wolfram_alpha, query, english_query, meta_call)

        if ica and not code and not input_analyzers_ai.are_you_sure(assistant_answer, self.messages):
            critical_question = text_processors_ai.generate_critical_question(assistant_answer, self.messages)
            OutputManager.print_formatted("critical question", critical_question)

            answer_to_critical_question = ConversationManager(self.messages).process_input(critical_question)[0]
            OutputManager.print_formatted("answer to critical question", answer_to_critical_question)
            self.append_assistant_message(assistant_answer)
            self.append_user_message(critical_question)
            self.append_assistant_message(answer_to_critical_question)

            assistant_answer = ConversationManager(self.messages).process_input(english_query)[0]
            self.append_user_message(query)

        return assistant_answer, code

    def process_input(self, query: str, meta_call: bool = True) -> Tuple[str, Optional[str]]:
        """
        Process user input and generate an appropriate response.

        Args:
            query (str): The input provided by the user or an internal request, if meta_call == True
            meta_call (bool): True if the request is auto generated by functions in input_analyzers_ai or text_processors_ai

        Returns:
            tuple: A tuple containing the main response and, if applicable, code that is suggested to be executed.
        """
        query = query.strip()

        if meta_call:
            if ConversationManager.pastime_mode() and Configuration.get()['SHOW_DEBUG_MESSAGES']:
                print("------------------------------------------------")
                print(query)
                print("------------------------------------------------")
        elif ConversationManager.pastime_mode():
            return pastime.reply(query), None
        else:
            OutputManager.reset_history()

        if Configuration.get()['SHOW_DEBUG_MESSAGES']:
            if meta_call:
                print(f"""Meta call received ("{truncate_string(query)}..."")""")
            else:
                print(f"""User input received ("{truncate_string(query)}..."")""")

        generate_terminal_command: Final = (
                Configuration.get()['GENERATE_TERMINAL_CMD']
                and not meta_call
                and query != ""
                and (not ConversationManager.force_wolfram_alpha() or not self.is_first_reply())
                and input_analyzers_ai.query_refers_to_a_computer(query)
        )

        if (Configuration.get()['SHOW_DEBUG_MESSAGES']
                and Configuration.get()['GENERATE_TERMINAL_CMD'] and not meta_call):
            print("User input can be solved with terminal: " + str(generate_terminal_command))

        modified_query: Final = context.generate_terminal_command(query) if generate_terminal_command else query

        assistant_answer, code = self.generate_response_based_on_input_type(generate_terminal_command, meta_call, modified_query)

        if modified_query != query:
            # Replace the modified message that forced the generation of a terminal command with the original message
            if modified_query != "":
                self.messages.pop()
            if query != "":
                self.append_user_message(query)

        if code:
            if not meta_call:
                self.append_assistant_message(code)
        elif not meta_call:
            self.append_assistant_message(assistant_answer)

        return assistant_answer, code

    def process_input_direct(self, user_input: str):
        """
        Process user input and return only the response, which is useful for calls from Javascript.

        Args:
            user_input (str): The input provided by the user.

        Returns:
            str: The main response from the assistant.
        """
        main_response, _ = self.process_input(user_input, False)

        return text_processors_regex.ensure_markdown_horizontal_line(main_response)
