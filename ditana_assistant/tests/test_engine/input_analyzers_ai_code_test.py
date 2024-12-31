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
This module contains unit tests for the input_analyzers_ai.is_likely_code function.
It tests the same things as the code related tests in input_analyzers_regex_code_test.py.
"""

import unittest

from ditana_assistant.base.config import Configuration, ModelType
from ditana_assistant.base.output_manager import OutputManager
from ditana_assistant.engine import input_analyzers_ai
from ditana_assistant.tests.test_engine.code_detection_test_cases import get_test_cases

OutputManager.hide_messages = True


class TestIsLikelyCode(unittest.TestCase):
    """
    Test cases for the is_likely_code function in the input_analyzer module.
    Tests are performed for both OpenAI and Gemma models.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment with appropriate model types.

        Note:
        ModelType.GEMMA is currently excluded from these tests due to limitations
        in its code detection capabilities. For ModelType.GEMMA, the system falls back
        to a regex-based solution in input_analyzers_ai.is_likely_code_delegate.

        This setup allows for:
        1. Focused testing on models with reliable code detection (currently OpenAI).
        2. Easy extension to include additional models in the future.
        3. Compatibility with the fallback mechanism in the production code.

        Future developers can add new model types to this list as they become
        available and capable of passing these tests. Alternatively, they can
        update the fallback logic in input_analyzers_ai.is_likely_code_delegate
        to handle new models that require the regex-based approach.
        """
        cls.model_configs = [
            {"type": ModelType.OPENAI, "openai_model": "gpt-4o-mini"},
            # {"type": ModelType.GEMMA, "openai_model": None}
        ]

    def run_test_for_all_models(self, test_func):
        """Run the given test function for all configured models."""
        for config in self.model_configs:
            model_type = config["type"]
            openai_model = config["openai_model"]

            with self.subTest(model=model_type, openai_model=openai_model):
                Configuration.set(model_type=model_type)
                if model_type == ModelType.OPENAI:
                    Configuration.set(openai_model=openai_model)

                print(f"---- Model type: {model_type}, OpenAI Model: {openai_model or 'N/A'}  ----")
                test_func()

    def test_is_likely_code(self):
        """Test the is_likely_code function with various test cases."""
        def test_func():
            test_cases = get_test_cases()
            for description, input_text, expected_output in test_cases:
                with self.subTest(description=description):
                    result = input_analyzers_ai.is_likely_code(input_text)[0]
                    self.assertEqual(result, expected_output, f"Failed test case: {description}")

        self.run_test_for_all_models(test_func)


if __name__ == '__main__':
    unittest.main()
