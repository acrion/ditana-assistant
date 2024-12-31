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
This module contains unit tests for the input_analyzers_regex module of the Ditana Assistant.
It tests various functions related to code detection and input analysis.
"""

import unittest
from typing import Tuple

from ditana_assistant.engine import input_analyzers_regex
from ditana_assistant.tests.test_engine.code_detection_test_cases import get_test_cases


def is_likely_code_wrapper(text: str) -> Tuple[bool, float]:
    """Wrapper for is_likely_code to capture the score"""
    result, score = input_analyzers_regex.is_likely_code(text)
    return result, score


class TestIsLikelyCode(unittest.TestCase):
    """
    Test cases for the is_likely_code function in the input_analyzer module.
    """

    test_results = []  # Class variable to store all test results

    def run_test(self, description: str, text: str, expected_result: bool):
        """Run a single test case and store the result"""
        result, score = is_likely_code_wrapper(text)
        self.__class__.test_results.append((result, score, text, expected_result))
        if expected_result:
            self.assertTrue(result, f"Failed: {description}")
        else:
            self.assertFalse(result, f"Failed: {description}")

    def test_code_detection(self):
        """Run all test cases from the imported module"""
        test_cases = get_test_cases()
        for description, text, expected_result in test_cases:
            with self.subTest(description=description):
                self.run_test(description, text, expected_result)

    @classmethod
    def tearDownClass(cls):
        """Print the analysis results after all tests have run"""
        print("\nAll tests completed. Analyzing results:")
        true_scores = []
        false_scores = []

        for result, score, _, expected_result in cls.test_results:
            if expected_result:
                true_scores.append(score)
            else:
                false_scores.append(score)

        if true_scores and false_scores:
            min_true_score = min(true_scores)
            max_false_score = max(false_scores)
            difference = min_true_score - max_false_score

            print(f"Minimum score for 'true' results: {min_true_score}")
            print(f"Maximum score for 'false' results: {max_false_score}")

            if difference < 0:
                print("Optimum threshold: Some tests failed, calculation does not make sense.")
            else:
                print(f"Optimum threshold: {(min_true_score + max_false_score) / 2}")

            print(f"Difference between min true and max false: {difference}")
        else:
            print("Not enough data to calculate the difference.")

        print("\nDetailed results:")
        for result, score, text, expected_result in cls.test_results:
            print(f"Text: {text}")
            print(f"Expected result: {'Code' if expected_result else 'Not code'}")
            print(f"Actual result: {'Code' if result else 'Not code'}")
            print(f"Score: {score}")
            print(f"Test {'passed' if result == expected_result else 'failed'}\n")


if __name__ == '__main__':
    unittest.main()
