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
This module provides an interface for interacting with different AI models
in the Ditana Assistant. It includes functions for preparing requests and
processing responses from various AI models.
"""

from typing import List, Dict, Literal, Any
import urllib.parse

from ditana_assistant.base import config
from ditana_assistant.base.config import Configuration


def get_endpoint() -> str:
    """
    Get the API endpoint for the configured model.

    Returns:
        str: The API endpoint URL for the specified model.
    """
    match Configuration.get()['MODEL_TYPE']:
        case config.ModelType.OPENAI:
            return "https://api.openai.com/v1/chat/completions"
        case config.ModelType.GEMMA:
            return urllib.parse.urljoin(Configuration.get()['KOBOLDCPP_BASE_URL'], "api/v1/generate")


def convert_messages_to_gemma_prompt(messages: List[Dict[Literal["role", "content"], str]]) -> str:
    """
    Convert a list of messages to a Gemma-compatible prompt format.

    Args:
        messages (List[Dict[str, str]]): A list of message dictionaries.

    Returns:
        str: A formatted prompt string for the Gemma model.
    """
    prompt = "<end_of_turn>\n"
    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "assistant":
            role = "model"

        prompt += f"<start_of_turn>{role}\n{content}<end_of_turn>\n"

    prompt += "<start_of_turn>model\n"

    return prompt


def extract_assistant_answer(response_json: Dict[str, Any]) -> str:
    """
    Extract the assistant’s answer from the API response JSON.

    Args:
        response_json (Dict[str, Any]): The JSON response from the API.

    Returns:
        str: The extracted answer from the assistant.
    """
    match Configuration.get()['MODEL_TYPE']:
        case config.ModelType.OPENAI:
            return response_json['choices'][0]['message']['content']
        case config.ModelType.GEMMA:
            return response_json['results'][0]['text'].strip()


def get_request(messages: List[Dict[Literal["role", "content"], str]]) -> Dict[str, Any]:
    """
    Prepare a request dictionary for the specified model.

    Args:
        messages (List[Dict[Literal["role", "content"], str]]): A list of message dictionaries.

    Returns:
        Dict[str, Any]: A dictionary containing the prepared request data.
    """
    match Configuration.get()['MODEL_TYPE']:
        case config.ModelType.GEMMA:
            return {
                "n": 1,
                "max_context_length": 4096,
                "max_length": 768,
                "rep_pen": 1.01,
                "temperature": 0.25,
                "top_p": 0.6,
                "top_k": 100,
                "top_a": 0,
                "typical": 1,
                "tfs": 1,
                "rep_pen_range": 320,
                "rep_pen_slope": 0.7,
                "sampler_order": [6, 0, 1, 3, 4, 2, 5],
                "memory": "",
                "trim_stop": True,
                "genkey": "KCPP9905",
                "min_p": 0,
                "dynatemp_range": 0,
                "dynatemp_exponent": 1,
                "smoothing_factor": 0,
                "banned_tokens": [],
                "render_special": False,
                "presence_penalty": 0,
                "logit_bias": {},
                "prompt": convert_messages_to_gemma_prompt(messages),
                "quiet": True,
                "stop_sequence": ["<end_of_turn>\n<start_of_turn>user", "<end_of_turn>\n<start_of_turn>model"],
                "use_default_badwordsids": False,
                "bypass_eos": False
            }
        case config.ModelType.OPENAI:
            return {
                "model": Configuration.get()['OPENAI_MODEL'],
                "messages": messages,
                "max_tokens": 768,
                "temperature": 0,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
