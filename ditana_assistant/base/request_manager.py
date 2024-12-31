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
This module provides the RequestManager class, which serves as a foundational component for managing
API requests to AI models. It includes functionality for sending requests, caching responses, and
handling interactions with external services such as Wolfram Alpha. The module ensures efficient and
reliable communication with AI services by implementing error handling and retry mechanisms.
"""

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import threading
import time
from typing import Any, Dict, Optional

import requests

from ditana_assistant.base import config, model_interface
from ditana_assistant.base.config import Configuration
from ditana_assistant.base.string_cache import StringCache
from ditana_assistant.base.wolfram_alpha_short_answers import WolframAlphaShortAnswers


class RequestManager:
    """
    RequestManager is a base class responsible for managing API requests to AI models.

    It handles sending requests, caching responses to improve performance, and interacting with
    external services like Wolfram Alpha for additional functionalities. The class provides
    a standardized method `send_model_request` for sending requests and processing responses,
    including error handling and retry mechanisms to ensure reliable communication with AI
    services.

   Attributes:
        _wolfram_alpha (WolframAlphaShortAnswers): An instance to handle Wolfram Alpha short answers.
        _force_wolfram_alpha (bool): A flag to force the use of Wolfram Alpha.
        _pastime_mode (bool): A flag to enable pastime mode.
        _impersonate (str): A string to specify impersonation.
        _code_input_event (threading.Event): An event for code input synchronization.
        _code_input_global (queue.Queue): A global queue for code input.
        _stop_thread (threading.Event): An event to signal thread termination.
    """

    _request_cache: Optional[StringCache] = None
    _wolfram_alpha = WolframAlphaShortAnswers()
    _ica: bool = False
    _force_wolfram_alpha: bool = False
    _pastime_mode: bool = False
    _impersonate: str = None
    _code_input_event = threading.Event()
    _code_input_global = queue.Queue()
    _stop_thread = threading.Event()

    @classmethod
    def wolfram_alpha(cls) -> WolframAlphaShortAnswers:
        """
        Accessor method for the _wolfram_alpha class attribute.

        Returns:
            WolframAlphaShortAnswers: The instance handling Wolfram Alpha short answers.
        """
        return cls._wolfram_alpha

    @classmethod
    def force_wolfram_alpha(cls) -> bool:
        """
        Accessor method for the _force_wolfram_alpha class attribute.

        Returns:
            bool: Indicates whether to force the use of Wolfram Alpha.
        """
        return cls._force_wolfram_alpha

    @classmethod
    def set_force_wolfram_alpha(cls, value: bool) -> None:
        """
        Mutator method for the _force_wolfram_alpha class attribute.

        Args:
            value (bool): The new value to set for _force_wolfram_alpha.

        Returns:
            None
        """
        cls._force_wolfram_alpha = value

    @classmethod
    def ica(cls) -> bool:
        """
        Accessor method for the _ica class attribute.

        Returns:
            bool: Indicates whether to augment the context of user requests introspectively with additional factual information.
                  If True, the system will implement Introspective Contextual Augmentation by generating a contextual query based on the user’s input,
                  attempt to retrieve factual information from Wolfram|Alpha or process it using an LLM,
                  and append this information to the conversation history. This process enhances subsequent responses
                  through introspective reasoning and contextual augmentation.
        """
        return cls._ica

    @classmethod
    def set_ica(cls, value: bool) -> None:
        """
        Mutator method for the _ica class attribute.

        Args:
            value (bool): The new value to set for _ica.

        Returns:
            None
        """
        cls._ica = value

    @classmethod
    def pastime_mode(cls) -> bool:
        """
        Accessor method for the _pastime_mode class attribute.

        Returns:
            bool: Indicates whether pastime mode is enabled.
        """
        return cls._pastime_mode

    @classmethod
    def set_pastime_mode(cls, value: bool) -> None:
        """
        Mutator method for the _pastime_mode class attribute.

        Args:
            value (bool): The new value to set for _pastime_mode.

        Returns:
            None
        """
        cls._pastime_mode = value

    @classmethod
    def impersonate(cls) -> Optional[str]:
        """
        Accessor method for the _impersonate class attribute.

        Returns:
            Optional[str]: The impersonation string, if any.
        """
        return cls._impersonate

    @classmethod
    def set_impersonate(cls, value: Optional[str]) -> None:
        """
        Mutator method for the _impersonate class attribute.

        Args:
            value (Optional[str]): The new impersonation string to set.

        Returns:
            None
        """
        cls._impersonate = value

    @classmethod
    def code_input_event(cls) -> threading.Event:
        """
        Accessor method for the _code_input_event class attribute.

        Returns:
            threading.Event: The event used for code input synchronization.
        """
        return cls._code_input_event

    @classmethod
    def code_input_global(cls) -> queue.Queue:
        """
        Accessor method for the _code_input_global class attribute.

        Returns:
            queue.Queue: The global queue for code input.
        """
        return cls._code_input_global

    @classmethod
    def stop_thread(cls) -> threading.Event:
        """
        Accessor method for the _stop_thread class attribute.

        Returns:
            threading.Event: The event used to signal thread termination.
        """
        return cls._stop_thread

    @classmethod
    def initialize_cache(cls, priority_cache_path: Path = None) -> None:
        """
        Initialize the global request cache.

        Args:
            priority_cache_path (Path): The optional path for the priority cache.

        Returns:
            None
        """
        # Although LLM responses may vary, the overall quality remains stable unless the provider
        # makes significant improvements. A one-week cache is used to reduce the number of API calls.
        cls._request_cache = StringCache(
            base_filename="model_request_cache",
            default_lifetime=Configuration.get()['MODEL_CACHE_START_LIFETIME_SEC'],
            priority_cache_path=priority_cache_path,
            max_size=Configuration.get()['MODEL_CACHE_SIZE']*1024*1024
        )

    @classmethod
    def send_model_request(cls, request: Dict[str, Any]) -> str:
        """
        Send a request to the AI model and handle the response.

        This function sends the prepared request to the appropriate AI model endpoint,
        handles potential errors and retries, and extracts the assistant’s answer from the response.

        Args:
            request (dict): The prepared request data to be sent to the AI model.

        Returns:
            str: The assistant’s answer extracted from the model’s response.
                In case of an error, it returns an error message instead.

        Side effects:
            - Sends HTTP requests to the AI model endpoint.
            - Prints debug information if debug mode is enabled.
            - Handles and retries on 'service unavailable' errors and rate limit errors.
            - Extracts and processes errors from the response.

        Raises:
            None: Errors are caught and returned as part of the assistant’s answer.

        Note:
            This function uses a while loop to implement a retry mechanism
            for 'service unavailable' errors and rate limit errors. It will keep retrying
            with increasing wait times until a valid response is received or an error occurs.
        """
        if not cls._request_cache:
            cls.initialize_cache()

        try:
            # Initialize the retry delay
            retry_delay = 1  # Initial retry delay in seconds

            while True:
                session = requests.Session()
                endpoint = model_interface.get_endpoint()

                hash_input = (
                    endpoint
                    + json.dumps(request, sort_keys=True)
                    + str(RequestManager.ica())
                    + Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID']
                )
                hash_sum = hashlib.sha256(hash_input.encode()).hexdigest()
                assistant_answer = cls._request_cache.get(hash_sum)
                if assistant_answer is not None:
                    return assistant_answer

                headers = {"Content-Type": "application/json"}

                if Configuration.get()['MODEL_TYPE'] == config.ModelType.OPENAI:
                    headers["Authorization"] = f"Bearer {os.environ.get('OPENAI_API_KEY')}"

                response = session.post(
                    endpoint,
                    headers=headers,
                    json=request
                )

                response_json = response.json()

                if response_json.get('detail', {}).get('type') == 'service_unavailable':
                    print(f"{endpoint} is busy, retrying in 3 seconds...")
                    time.sleep(3)
                elif 'error' in response_json:
                    error = response_json['error']
                    if isinstance(error, dict):
                        error_message = error.get('message', 'Unknown error occurred')
                        error_type = error.get('type', 'unknown_error')
                        error_code = error.get('code', 'unknown_code')

                        if error_code == 'rate_limit_exceeded':
                            # Try to extract the wait time from the error message
                            wait_time_match = re.search(r'try again in (\d+\.?\d*)s', error_message)
                            if wait_time_match:
                                wait_time = float(wait_time_match.group(1))
                                print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying.")
                                time.sleep(wait_time)
                                continue
                            else:
                                print(error_message)
                                print(f"Rate limit exceeded. Retrying in {retry_delay} seconds.")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Double the retry delay for the next iteration
                                continue

                        assistant_answer = f"API Error: {error_type} - {error_code}\n{error_message}"
                    else:
                        assistant_answer = f"API Error: {error}"
                    break
                else:
                    assistant_answer = model_interface.extract_assistant_answer(response_json)
                    cls._request_cache.set(hash_sum, assistant_answer)
                    break
        except requests.exceptions.RequestException as e:
            assistant_answer = str(e)

        if Configuration.get()['SHOW_DEBUG_MESSAGES']:
            print("----------------------------------------------------------------")
            print("Response:")
            print("----------------------------------------------------------------")
            print(assistant_answer)
            print("--- End of response --------------------------------------------")

        return assistant_answer
