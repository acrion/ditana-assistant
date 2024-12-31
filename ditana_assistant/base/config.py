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
This module handles configuration settings for the Ditana Assistant.

It defines default configuration values, loads user configuration from a YAML file,
and provides access to configuration settings such as model type and debug options.
"""

from typing import Final, TypedDict, cast
from pathlib import Path
import enum
import os

import threading

import platformdirs
import yaml


class ModelType(enum.Enum):
    """Enumeration of supported AI model types."""
    GEMMA = "gemma"
    OPENAI = "openai"


class ConfigDict(TypedDict):
    """
    Represents the configuration of Ditana Assistant, except command line parameters.
    It is synced with CONFIG_FILE.
    """
    MODEL_TYPE: ModelType
    SHOW_DEBUG_MESSAGES: bool
    OPENAI_MODEL: str
    KOBOLDCPP_BASE_URL: str
    WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID: str
    GENERATE_TERMINAL_CMD: bool
    OFFER_CMD_EXECUTION: bool
    ASSUME_ENGLISH: bool
    MODEL_CACHE_SIZE: int
    MODEL_CACHE_START_LIFETIME_SEC: float
    WOLFRAM_ALPHA_CACHE_SIZE: int
    WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC: float
    WOLFRAM_ALPHA_ERROR_CACHE_SIZE: int
    WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC: float
    ENABLE_EXPERIMENTAL_FEATURES: bool


class Configuration:
    """
    Singleton class for managing the application configuration.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.__config = None

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of the Configuration class.

        Returns:
            Configuration: The singleton instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load(self):
        """
        Load the configuration from file or use default values.
        """
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)

                # Create a mapping between DEFAULT_CONFIG keys and config_dict keys
                default_to_file_key_map = {
                    'MODEL_TYPE': 'model_type',
                    'SHOW_DEBUG_MESSAGES': 'show_debug_messages',
                    'OPENAI_MODEL': 'openai_model',
                    'KOBOLDCPP_BASE_URL': 'koboldcpp_base_url',
                    'WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID': 'wolfram_alpha_short_answers_app_id',
                    'GENERATE_TERMINAL_CMD': 'generate_terminal_cmd',
                    'OFFER_CMD_EXECUTION': 'offer_cmd_execution',
                    'ASSUME_ENGLISH': "assume_english",
                    'MODEL_CACHE_SIZE': "model_cache_size",
                    'MODEL_CACHE_START_LIFETIME_SEC': "model_cache_start_lifetime_sec",
                    'WOLFRAM_ALPHA_CACHE_SIZE': "wolfram_alpha_cache_size",
                    'WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC': "wolfram_alpha_cache_start_lifetime_sec",
                    'WOLFRAM_ALPHA_ERROR_CACHE_SIZE': "wolfram_alpha_error_cache_size",
                    'WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC': "wolfram_alpha_error_cache_start_lifetime_sec",
                    'ENABLE_EXPERIMENTAL_FEATURES': "enable_experimental_features"
                }

                # Check for unexpected entries
                unexpected_keys = set(config_dict.keys()) - set(default_to_file_key_map.values())
                if unexpected_keys:
                    raise ValueError(f"Unexpected entries in config file: {', '.join(unexpected_keys)}")

                # Create a new config dictionary
                new_config: ConfigDict = cast(ConfigDict, {})
                changes_made = False

                # Fill in values from file or use defaults
                for default_key, file_key in default_to_file_key_map.items():
                    if file_key in config_dict:
                        new_config[default_key] = config_dict[file_key]
                    else:
                        new_config[default_key] = DEFAULT_CONFIG[default_key]
                        changes_made = True
                        print(f"Added missing config entry: {file_key} = {DEFAULT_CONFIG[default_key]}")

                # Convert ModelType from string to enum
                new_config['MODEL_TYPE'] = ModelType(new_config['MODEL_TYPE'])

                self.__config = new_config

                # Save if changes were made
                if changes_made:
                    self._save()
                    print("Updated config file with missing entries.")
            else:
                self.__config = DEFAULT_CONFIG.copy()
                self._save()
                print("Created new config file with default values.")
        except ValueError as e:
            print(f"Error in configuration file: {e}")
            raise
        except (yaml.YAMLError, KeyError) as e:
            print(f"Error loading configuration from {CONFIG_FILE}: {e}")
            raise

    def _save(self):
        """
        Save the current configuration to file.
        """
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config_to_save = {
                "model_type": self.__config['MODEL_TYPE'].value,
                "show_debug_messages": self.__config['SHOW_DEBUG_MESSAGES'],
                "openai_model": self.__config['OPENAI_MODEL'],
                "koboldcpp_base_url": self.__config['KOBOLDCPP_BASE_URL'],
                "wolfram_alpha_short_answers_app_id": self.__config['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'],
                "generate_terminal_cmd": self.__config['GENERATE_TERMINAL_CMD'],
                "offer_cmd_execution": self.__config['OFFER_CMD_EXECUTION'],
                "assume_english": self.__config['ASSUME_ENGLISH'],
                "model_cache_size": self.__config['MODEL_CACHE_SIZE'],
                "model_cache_start_lifetime_sec": self.__config['MODEL_CACHE_START_LIFETIME_SEC'],
                "wolfram_alpha_cache_size": self.__config['WOLFRAM_ALPHA_CACHE_SIZE'],
                "wolfram_alpha_cache_start_lifetime_sec": self.__config['WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC'],
                "wolfram_alpha_error_cache_size": self.__config['WOLFRAM_ALPHA_ERROR_CACHE_SIZE'],
                "wolfram_alpha_error_cache_start_lifetime_sec": self.__config['WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC'],
                "enable_experimental_features": self.__config['ENABLE_EXPERIMENTAL_FEATURES']
            }
            yaml.dump(config_to_save, f)

    def get_config(self):
        """
        Get the current configuration, loading it if necessary.

        Returns:
            ConfigDict: The current configuration.
        """
        if self.__config is None:
            with self._lock:
                if self.__config is None:
                    self._load()
        return self.__config

    def set_config(self,
                   model_type: ModelType,
                   show_debug_messages: bool,
                   openai_model: str,
                   koboldcpp_base_url: str,
                   wolfram_alpha_short_answers_app_id: str,
                   generate_terminal_cmd: bool,
                   offer_cmd_execution: bool,
                   assume_english: bool,
                   model_cache_size: int,
                   model_cache_start_lifetime_sec: float,
                   wolfram_alpha_cache_size: int,
                   wolfram_alpha_cache_start_lifetime_sec: float,
                   wolfram_alpha_error_cache_size: int,
                   wolfram_alpha_error_cache_start_lifetime_sec: float,
                   enable_experimental_features: bool):
        """
        Set a new configuration.

        Args:
            model_type (ModelType): The model type to use.
            show_debug_messages (bool): Whether to show debug messages.
            openai_model (str): In case model_type == ModelType.OPENAI, the OpenAI model to use.
            koboldcpp_base_url (str): In case model_type != ModelType.OPENAI, the base URL of the KoboldCpp server, e.g. "http://localhost:5001"
            wolfram_alpha_short_answers_app_id: WolframAlpha App ID for "Short Answers API", see https://developer.wolframalpha.com
            generate_terminal_cmd (bool): If True, analyzes user input to determine if it can be resolved using a terminal command
                               on the user’s computer. The input is then processed accordingly to generate an appropriate
                               command suggestion.
            offer_cmd_execution (bool): If True, examines the output to identify potential terminal commands. If a command is
                               detected, it offers the user the option to execute it directly.
            assume_english (bool): If True, assume text is English without checking the language.
            model_cache_size (int). The internal size of the cache used for the model API in MiB.
            model_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the model response cache.
                                                  After this time expires, upon a new API access, the lifetime is
                                                  automatically adjusted: it is extended if the new response is
                                                  identical to the cached one, or shortened if it differs.
            wolfram_alpha_cache_size (int). The internal size of the cache used for the Wolfram|Alpha API in MiB.
            wolfram_alpha_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the Wolfram Alpha
                                                          response cache. After this time expires, upon a new API
                                                          access, the lifetime is automatically adjusted: it is
                                                          extended if the new response is identical to the cached
                                                          one, or shortened if it differs.
            wolfram_alpha_error_cache_size (int): The internal size of the cache used for requests to the Wolfram|Alpha API that caused errors.
            wolfram_alpha_error_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the Wolfram Alpha
                                                                error response cache. This cache stores failed requests
                                                                to avoid redundant API calls. After this time expires,
                                                                upon a new API access, the lifetime is automatically
                                                                adjusted: it is extended if the error persists, or
                                                                shortened if the request succeeds.
            enable_experimental_features (bool): If True, activates experimental features for development and systematic testing.
                                                    This flag enables the use of new or experimental functionalities without specifying
                                                    which particular features are activated. It is intended for internal use to
                                                    systematically test changes and should be used with caution.
         """
        with self._lock:
            self.__config = ConfigDict(
                MODEL_TYPE=model_type,
                SHOW_DEBUG_MESSAGES=show_debug_messages,
                OPENAI_MODEL=openai_model,
                KOBOLDCPP_BASE_URL=koboldcpp_base_url,
                WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID=wolfram_alpha_short_answers_app_id,
                GENERATE_TERMINAL_CMD=generate_terminal_cmd,
                OFFER_CMD_EXECUTION=offer_cmd_execution,
                ASSUME_ENGLISH=assume_english,
                MODEL_CACHE_SIZE=model_cache_size,
                MODEL_CACHE_START_LIFETIME_SEC=model_cache_start_lifetime_sec,
                WOLFRAM_ALPHA_CACHE_SIZE=wolfram_alpha_cache_size,
                WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC=wolfram_alpha_cache_start_lifetime_sec,
                WOLFRAM_ALPHA_ERROR_CACHE_SIZE=wolfram_alpha_error_cache_size,
                WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC=wolfram_alpha_error_cache_start_lifetime_sec,
                ENABLE_EXPERIMENTAL_FEATURES=enable_experimental_features
            )

    def reset_config(self):
        """
        Reset the configuration to force reloading from file on next access.
        """
        with self._lock:
            self.__config = None

    @classmethod
    def get(cls):
        """
        Get the current configuration.

        Returns:
            ConfigDict: The current configuration.
        """
        return cls.get_instance().get_config()

    @classmethod
    def set(cls, *,
            model_type: ModelType | None = None,
            show_debug_messages: bool | None = None,
            openai_model: str | None = None,
            koboldcpp_base_url: str | None = None,
            wolfram_alpha_short_answers_app_id: str | None = None,
            generate_terminal_cmd: bool | None = None,
            offer_cmd_execution: bool | None = None,
            assume_english: bool | None = None,
            model_cache_size: int | None = None,
            model_cache_start_lifetime_sec: float | None = None,
            wolfram_alpha_cache_size: int | None = None,
            wolfram_alpha_cache_start_lifetime_sec: float | None = None,
            wolfram_alpha_error_cache_size: int | None = None,
            wolfram_alpha_error_cache_start_lifetime_sec: float | None = None,
            enable_experimental_features: bool | None = None):
        """
        Update the configuration with new values. Parameters not provided will retain their current values.

        Args:
            model_type (ModelType): The model type to use.
            show_debug_messages (bool): Whether to show debug messages.
            openai_model (str): In case model_type == ModelType.OPENAI, the OpenAI model to use.
            koboldcpp_base_url (str): In case model_type != ModelType.OPENAI, the base URL of the KoboldCpp server, e.g. "http://localhost:5001"
            wolfram_alpha_short_answers_app_id: WolframAlpha App ID for "Short Answers API", see https://developer.wolframalpha.com
            generate_terminal_cmd (bool): If True, analyzes user input to determine if it can be resolved using a terminal command
                               on the user’s computer. The input is then processed accordingly to generate an appropriate
                               command suggestion.
            offer_cmd_execution (bool): If True, examines the output to identify potential terminal commands. If a command is
                               detected, it offers the user the option to execute it directly.
            assume_english (bool): If True, assume text is English without checking the language.
            model_cache_size (int). The internal size of the cache used for the model API in MiB.
            model_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the model response cache.
                                                  After this time expires, upon a new API access, the lifetime is
                                                  automatically adjusted: it is extended if the new response is
                                                  identical to the cached one, or shortened if it differs.
            wolfram_alpha_cache_size (int). The internal size of the cache used for the Wolfram|Alpha API in MiB.
            wolfram_alpha_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the Wolfram Alpha
                                                          response cache. After this time expires, upon a new API
                                                          access, the lifetime is automatically adjusted: it is
                                                          extended if the new response is identical to the cached
                                                          one, or shortened if it differs.
            wolfram_alpha_error_cache_size (int): The internal size of the cache used for requests to the Wolfram|Alpha API that caused errors.
            wolfram_alpha_error_cache_start_lifetime_sec (float): The initial lifetime (in seconds) for the Wolfram Alpha
                                                                error response cache. This cache stores failed requests
                                                                to avoid redundant API calls. After this time expires,
                                                                upon a new API access, the lifetime is automatically
                                                                adjusted: it is extended if the error persists, or
                                                                shortened if the request succeeds.
            enable_experimental_features (bool): If True, activates experimental features for development and systematic testing.
                                                    This flag enables the use of new or experimental functionalities without specifying
                                                    which particular features are activated. It is intended for internal use to
                                                    systematically test changes and should be used with caution.
        """
        current_config = cls.get()

        new_config = {
            'model_type': model_type if model_type is not None else current_config['MODEL_TYPE'],
            'show_debug_messages': show_debug_messages if show_debug_messages is not None else current_config['SHOW_DEBUG_MESSAGES'],
            'openai_model': openai_model if openai_model is not None else current_config['OPENAI_MODEL'],
            'koboldcpp_base_url': koboldcpp_base_url if koboldcpp_base_url is not None else current_config['KOBOLDCPP_BASE_URL'],
            'wolfram_alpha_short_answers_app_id': wolfram_alpha_short_answers_app_id if wolfram_alpha_short_answers_app_id is not None else current_config['WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID'],
            'generate_terminal_cmd': generate_terminal_cmd if generate_terminal_cmd is not None else current_config['GENERATE_TERMINAL_CMD'],
            'offer_cmd_execution': offer_cmd_execution if offer_cmd_execution is not None else current_config['OFFER_CMD_EXECUTION'],
            'assume_english': assume_english if assume_english is not None else current_config['ASSUME_ENGLISH'],
            'model_cache_size': model_cache_size if model_cache_size is not None else current_config['MODEL_CACHE_SIZE'],
            'model_cache_start_lifetime_sec': model_cache_start_lifetime_sec if model_cache_start_lifetime_sec is not None else current_config['MODEL_CACHE_START_LIFETIME_SEC'],
            'wolfram_alpha_cache_size': wolfram_alpha_cache_size if wolfram_alpha_error_cache_size is not None else current_config['WOLFRAM_ALPHA_CACHE_SIZE'],
            'wolfram_alpha_cache_start_lifetime_sec': wolfram_alpha_cache_start_lifetime_sec if wolfram_alpha_cache_start_lifetime_sec is not None else current_config['WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC'],
            'wolfram_alpha_error_cache_size': wolfram_alpha_error_cache_size if wolfram_alpha_error_cache_size is not None else current_config['WOLFRAM_ALPHA_ERROR_CACHE_SIZE'],
            'wolfram_alpha_error_cache_start_lifetime_sec': wolfram_alpha_error_cache_start_lifetime_sec if wolfram_alpha_error_cache_start_lifetime_sec is not None else current_config['WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC'],
            'enable_experimental_features': enable_experimental_features if enable_experimental_features is not None else current_config['ENABLE_EXPERIMENTAL_FEATURES']
        }

        cls.get_instance().set_config(**new_config)

    @classmethod
    def reset(cls):
        """
        Reset the configuration to force reloading from file on next access.
        """
        cls.get_instance().reset_config()


# https://openai.com/api/pricing/ As of 2024-10-03, gpt-4o-mini $0.150 / 1M input tokens, compared to $3.000 / 1M input tokens for gpt-3.5-turbo
# According to https://platform.openai.com/docs/models/gpt-3-5-turbo: "As of July 2024, gpt-4o-mini should be used in place of gpt-3.5-turbo, as it is cheaper, more capable, multimodal, and just as fast. gpt-3.5-turbo is still available for use in the API."

DEFAULT_CONFIG: Final[ConfigDict] = {
    "MODEL_TYPE": ModelType.GEMMA,
    "SHOW_DEBUG_MESSAGES": False,
    "OPENAI_MODEL": "gpt-4o-mini",
    "KOBOLDCPP_BASE_URL": "http://localhost:5001",
    "WOLFRAM_ALPHA_SHORT_ANSWERS_APP_ID": "",
    "GENERATE_TERMINAL_CMD": True,
    "OFFER_CMD_EXECUTION": True,
    "ASSUME_ENGLISH": False,
    "MODEL_CACHE_SIZE": 20,
    "MODEL_CACHE_START_LIFETIME_SEC": 7*24*3600,
    "WOLFRAM_ALPHA_CACHE_SIZE": 1,
    "WOLFRAM_ALPHA_CACHE_START_LIFETIME_SEC": 3600*3//16,
    "WOLFRAM_ALPHA_ERROR_CACHE_SIZE": 1,
    "WOLFRAM_ALPHA_ERROR_CACHE_START_LIFETIME_SEC": 7*24*3600,
    "ENABLE_EXPERIMENTAL_FEATURES": False
}


# Workaround for platformdirs behavior inconsistency with common practices in modern Windows applications
# Issue: platformdirs on Windows uses both appauthor and appname in the path, which differs from
# common practices observed in many modern Windows applications. Specifically:
#   1. If appauthor is not specified, it defaults to appname, resulting in:
#      C:\Users\<username>\AppData\Local\<appname>\<appname>
#   2. Many modern Windows applications use a simpler structure:
#      C:\Users\<username>\AppData\Local\<appname>
#
# On Unix-like systems, platformdirs behaves as expected:
#   ~/.config/<appname>
#
# Solution: Set appauthor to "." for behavior more consistent with modern Windows practices
# Result:
#   Windows: C:\Users\<username>\AppData\Local\.\<appname>
#            (effectively C:\Users\<username>\AppData\Local\<appname>)
#   Unix-like: ~/.config/<appname> (unchanged)
#
# Setting appauthor to "." effectively removes the additional directory level on Windows,
# as "." is treated as the current directory. This aligns the behavior with common practices
# in modern Windows applications while maintaining the expected behavior on Unix-like systems.
CONFIG_DIR: Final = Path(platformdirs.user_config_dir(appname="ditana-assistant", appauthor="."))

CONFIG_FILE: Final = Path(os.path.join(CONFIG_DIR, "config.yaml"))
