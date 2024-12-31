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
This module contains unit tests for the text_processors_regex module of the Ditana Assistant.
"""

import unittest

from ditana_assistant.engine import text_processors_regex


class TestRegex(unittest.TestCase):
    """
    Test various input analyzer functions.
    """
    def test_remove_works_and_phrases(self) -> None:
        """
        Simple case of remove_words_and_phrases. Just replace two words with one.
        """
        text = 'Ich bin Sherlock Holmes, der berühmte Detektiv. Und ich weiß noch viel mehr über Sie, als Sie sich vorstellen können. Bitte erzählen Sie mir mehr über Ihre Reise aus Baskerville.'
        result = text_processors_regex.remove_words_and_phrases(text, "Sherlock Holmes", "Ditana")
        self.assertEqual("Ich bin Ditana, der berühmte Detektiv. Und ich weiß noch viel mehr über Sie, als Sie sich vorstellen können. Bitte erzählen Sie mir mehr über Ihre Reise aus Baskerville.", result)
