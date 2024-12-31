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
Module: ditana_assistant.benchmark.multiple_choice_dataset

This module provides functionality to handle multiple choice datasets, including AI2 ARC and CAIS MMLU.
"""

import re
from datasets import load_dataset, get_dataset_config_names
from typing import List, Dict, Any, Optional, Iterator, Tuple
from enum import Enum
from ditana_assistant.engine.conversation_manager import ConversationManager


class DatasetIdentifier(Enum):
    """
    Enumeration of supported dataset identifiers.
    """
    AI2_ARC = "ai2_arc"
    CAIS_MMLU = "cais_mmlu"
    # Add more identifiers here as needed


class MultipleChoiceDataset:
    """
    A class to handle multiple choice datasets such as AI2 ARC and CAIS MMLU.
    """
    def __init__(self, identifier: DatasetIdentifier):
        """
        Initializes the MultipleChoiceDataset with the specified dataset identifier.

        Args:
            identifier (DatasetIdentifier): The identifier of the dataset to load.
        """
        self.identifier = identifier
        self.datasets: List[Tuple[str, Any]] = self._load_datasets()
        total_samples = sum(len(ds) for _, ds in self.datasets)
        print(f"Number of datasets loaded: {len(self.datasets)}")
        print(f"Total number of samples: {total_samples}")

    def _load_datasets(self) -> List[Tuple[str, Any]]:
        """
        Loads the dataset(s) based on the identifier.

        Returns:
            List[Tuple[str, Any]]: A list of tuples containing configuration names and loaded datasets.
        """
        datasets = []
        if self.identifier == DatasetIdentifier.AI2_ARC:
            split = 'test'
            print(f"Loading dataset 'ai2_arc' with split '{split}'...")
            try:
                dataset = load_dataset("ai2_arc", "ARC-Challenge", split=split)
                datasets.append(("ARC-Challenge", dataset))
                print(f"Loaded 'ai2_arc' with {len(dataset)} samples.")
            except ValueError as ve:
                print(f"Error loading 'ai2_arc' with split '{split}': {ve}")
        elif self.identifier == DatasetIdentifier.CAIS_MMLU:
            split='test'
            config = "all"
            print(f"Loading dataset 'cais/mmlu' with configuration '{config}' and split '{split}'...")
            try:
                ds = load_dataset("cais/mmlu", config, split=split)
                datasets.append((config, ds))
                print(f"Loaded 'cais/mmlu' with configuration '{config}' and {len(ds)} samples.")
            except ValueError as ve:
                print(f"Error loading 'cais/mmlu' with configuration '{config}' and split '{split}': {ve}")
        else:
            raise ValueError(f"Unknown dataset identifier: {self.identifier}")

        if not datasets:
            print(f"No datasets loaded for identifier '{self.identifier}' with split '{split}'.")
        return datasets

    def __len__(self) -> int:
        """
        Returns the total number of samples across all loaded datasets.

        Returns:
            int: Total number of samples.
        """
        return sum(len(ds) for _, ds in self.datasets)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        """
        Retrieves a sample by its global index across all datasets.

        Args:
            index (int): The global index of the sample.

        Returns:
            Dict[str, Any]: The dataset sample.
        """
        if self.identifier == DatasetIdentifier.AI2_ARC:
            return self.datasets[0][1][index]
        elif self.identifier == DatasetIdentifier.CAIS_MMLU:
            cumulative = 0
            for _, ds in self.datasets:
                if index < cumulative + len(ds):
                    return ds[index - cumulative]
                cumulative += len(ds)
            raise IndexError("Index out of range")
        else:
            raise ValueError(f"Unsupported dataset identifier: {self.identifier}")

    def iterate_questions(self) -> Iterator[Dict[str, Any]]:
        """
        Iterates over all questions in the loaded datasets.

        Yields:
            Dict[str, Any]: A dictionary containing the question, choices, and the correct answer.
        """
        if self.identifier == DatasetIdentifier.AI2_ARC:
            for sample in self.datasets[0][1]:
                question = sample.get("question", "").strip()
                choices_dict = sample.get("choices", {})
                choices = choices_dict.get("text", [])
                if not isinstance(choices, list):
                    choices = []
                labeled_choices = self._label_choices(choices)
                answer_key = sample.get("answerKey", "").strip()
                correct_answer = self._map_ai2_arc_answer(answer_key, len(choices))

                yield {
                    "question": question,
                    "choices": labeled_choices,  # List of tuples (label, choice)
                    "answer": correct_answer      # Correct answer label, e.g., 'B', 'C', etc.
                }
        elif self.identifier == DatasetIdentifier.CAIS_MMLU:
            for config_name, ds in self.datasets:
                print(f"Processing configuration '{config_name}'...")
                for sample in ds:
                    question = sample.get("question", "").strip()
                    choices = sample.get("choices", [])
                    labeled_choices = self._label_choices(choices)
                    answer_index = sample.get("answer", None)
                    correct_answer = self._map_cais_mmlu_answer(answer_index, len(choices))

                    yield {
                        "question": question,
                        "choices": labeled_choices,  # List of tuples (label, choice)
                        "answer": correct_answer      # Correct answer label, e.g., 'B', 'C', etc.
                    }
        else:
            raise ValueError(f"Unsupported dataset identifier: {self.identifier}")

    @staticmethod
    def _label_choices(choices: List[str]) -> List[Tuple[str, str]]:
        """
        Labels the choices starting from 'B'.

        Args:
            choices (List[str]): A list of choice strings.

        Returns:
            List[Tuple[str, str]]: A list of tuples containing the label and the choice text.
        """
        labeled_choices = []
        start_label = 66  # ASCII for 'B'
        for i, choice in enumerate(choices):
            label = chr(start_label + i)
            labeled_choices.append((label, choice))
        return labeled_choices

    @staticmethod
    def _map_ai2_arc_answer(answer_key: str, num_choices: int) -> Optional[str]:
        """
        Maps the original answerKey to the new label starting at 'B'.
        For example:
            If answer_key is 'A' → 'B'
            If answer_key is '1' → 'B'
            If answer_key is '2' → 'C', etc.

        Args:
            answer_key (str): The original answer key from the dataset.
            num_choices (int): The number of available choices.

        Returns:
            Optional[str]: The mapped answer label, e.g., 'B', 'C', etc., or None if invalid.
        """
        if answer_key.isdigit():
            index = int(answer_key)  # 1-based index
            mapped_label = chr(65 + index)  # 'A' + index
        elif re.match(r'^[A-Z]$', answer_key.upper()):
            original_label = answer_key.upper()
            index = ord(original_label) - 65  # 'A' -> 0, 'B' -> 1, etc.
            mapped_label = chr(66 + index)    # 'B' + index
        else:
            return None

        if 66 <= ord(mapped_label) <= 90 and (0 <= (ord(mapped_label) - 66) < num_choices):
            return mapped_label
        else:
            print("Internal error in _map_ai2_arc_answer: Could not interpret correct answer in dataset!")
            return None

    @staticmethod
    def _map_cais_mmlu_answer(answer_index: Optional[int], num_choices: int) -> Optional[str]:
        """
        Maps the original answer index to the new label starting at 'B'.
        For example:
            If answer_index is 0 → 'B'
            If answer_index is 1 → 'C', etc.

        Args:
            answer_index (Optional[int]): The original answer index from the dataset.
            num_choices (int): The number of available choices.

        Returns:
            Optional[str]: The mapped answer label, e.g., 'B', 'C', etc., or None if invalid.
        """
        if isinstance(answer_index, int) and 0 <= answer_index < num_choices:
            return chr(66 + answer_index)  # 'B' + index
        else:
            print("Internal error in _map_cais_mmlu_answer: Could not interpret correct answer in dataset!")
            return None

    @staticmethod
    def find_first_allowed_letter(text: str, n: int) -> Optional[str]:
        """
        Finds the first allowed letter in the text, starting from 'B'.

        Args:
            text (str): The text to search within.
            n (int): The number of allowed letters starting from 'B'.

        Returns:
            Optional[str]: The first allowed letter found, or None if none are found.
        """
        allowed_letters = set(chr(66 + i) for i in range(n))  # B, C, D, etc.
        pattern = r'\b[B-Z]\b'

        matches = re.finditer(pattern, text.upper())

        for match in matches:
            found_letter = match.group()
            if found_letter in allowed_letters:
                return found_letter

        return None

    def process_question(self, question: str, choices: List[Tuple[str, str]]) -> Optional[str]:
        """
        Processes the question and choices, sends them to the ConversationManager,
        and returns the validated prediction.

        Args:
            question (str): The question text.
            choices (List[Tuple[str, str]]): A list of tuples containing choice labels and texts.

        Returns:
            Optional[str]: The validated prediction label, e.g., 'B', 'C', etc., or None if invalid.
        """
        prompt = f"Question: {question}\n\nChoices:\n"
        for label, choice in choices:
            prompt += f"{label}. {choice}\n"
        prompt += "\nPlease provide the letter of the correct answer."

        prediction = ConversationManager().process_input(query=prompt, meta_call=False)[0]
        valid_prediction = self.find_first_allowed_letter(prediction, len(choices))

        return valid_prediction
