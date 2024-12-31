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
WolframAlphaShortAnswers Module

This module provides a class for interacting with the Wolfram|Alpha Short Answers API.
It allows for querying the API, caching responses, and handling errors.

The module contains the following main components:
1. WolframAlphaShortAnswers class: Encapsulates the API interaction logic.
2. StringCache usage: For caching API responses and errors.
3. Configuration integration: To manage API credentials.

Dependencies:
- urllib.parse: For URL encoding.
- requests: For making HTTP requests to the API.
- config: For accessing configuration settings.
- string_cache: For caching mechanisms.

Usage:
    wa = WolframAlphaShortAnswers()
    answer, error = wa.query("What is the capital of France?")
    if error:
        print(f"An error occurred: {error}")
    else:
        print(f"The answer is: {answer}")

Note:
    This module requires a valid Wolfram|Alpha API application ID to be set in the
    configuration. You can obtain one from https://developer.wolframalpha.com for
    the "Short Answers API".

Error Handling:
    The module handles various error scenarios, including HTTP errors, request
    exceptions, and cases where the API cannot interpret the input or provide
    a short answer.

Caching:
    Responses and errors are cached to improve performance and reduce API calls
    for repeated queries.
"""

import urllib.parse
from typing import Optional, Tuple

import requests

from ditana_assistant.base.config import Configuration
from ditana_assistant.base.string_cache import StringCache


class WolframAlphaShortAnswers:
    """
    A class to interact with the Wolfram|Alpha Short Answers API.

    This class encapsulates the functionality to make requests to the
    Wolfram|Alpha Short Answers API, handle caching of responses,
    and manage potential errors.

    Class Attributes:
        _answer_cache (StringCache): A dictionary to store cached API responses.
        _error_cache (StringCache): A dictionary to store API error responses.
    """

    # Wolfram|Alpha answers may contain real-time data. This cache duration
    # represents a balance between freshness and minimizing API requests.
    _answer_cache = StringCache(base_filename="wolfram_alpha_answer_cache", default_lifetime=Configuration.get()['WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC'], max_size=Configuration.get()['WOLFRAM_ALPHA_CACHE_SIZE']*1024*1024)

    # When Wolfram|Alpha declines a request, it is likely to continue rejecting the same
    #  request. A one-week cache helps avoid redundant API calls for failed requests.
    _error_cache = StringCache(base_filename="wolfram_alpha_error_cache", default_lifetime=Configuration.get()['WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC'], max_size=Configuration.get()['WOLFRAM_ALPHA_ERROR_CACHE_SIZE']*1024*1024)

    @staticmethod
    def query(question: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Query the Wolfram|Alpha Short Answers API.

        This method checks the cache for an existing answer, and if not found,
        makes a request to the API. The result is cached before being returned.

        Args:
            question (str): The question to ask the Wolfram|Alpha API.

        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing the API response
            and an error message (if any). If successful, the error will be None.
        """
        app_id = Configuration.get()['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID']

        if not app_id or app_id == "":
            return None, 'API application ID is not set. You may generate one for the "Short Answers API" under https://developer.wolframalpha.com).'

        if question in WolframAlphaShortAnswers._answer_cache:
            return WolframAlphaShortAnswers._answer_cache.get(question), None

        if question in WolframAlphaShortAnswers._error_cache:
            return None, WolframAlphaShortAnswers._error_cache.get(question)

        encoded_question = urllib.parse.quote(question)
        url = f"http://api.wolframalpha.com/v1/result?appid={app_id}&i={encoded_question}&units=metric"

        try:
            response = requests.get(url, timeout=7)
            response.raise_for_status()
            result = response.text
            WolframAlphaShortAnswers._answer_cache.set(question, result)
            return result, None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 501:
                error_text = "The input cannot be interpreted or no short answer is available."
                WolframAlphaShortAnswers._error_cache.set(question, error_text)
            elif e.response.status_code == 400:
                error_text = "Invalid API request. Check the input parameter."
            else:
                error_text = f"HTTP Error: {str(e)}"
        except requests.exceptions.RequestException as e:
            error_text = f"Request Error: {str(e)}"

        return None, error_text
