#!/usr/bin/env python3

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
Automatic Evaluation System for Ditana Assistant

This module provides functionality to evaluate the performance of the Ditana Assistant
on the AI2 ARC (Artificial Intelligence 2 Reasoning Challenge) dataset. It specifically
tests the impact of Introspective Contextual Augmentation (ICA) on the assistant’s
accuracy in answering multiple-choice questions.

The evaluation process runs two iterations:
1. With ICA disabled
2. With ICA enabled

Key Features:
- Loads and processes the ARC-Challenge dataset
- Handles both letter and numeric answer keys in the dataset
- Implements a custom answer extraction method for reliable evaluation
- Calculates and compares accuracy scores with and without ICA

This evaluation helps quantify the effectiveness of ICA in enhancing
the Ditana Assistant’s problem-solving capabilities across a range of
complex reasoning tasks.
"""

# __main__.py

import argparse
import sys

from ditana_assistant.benchmark import statistics
from ditana_assistant.base.config import Configuration, ModelType
from ditana_assistant.base.request_manager import RequestManager
from ditana_assistant.engine.conversation_manager import ConversationManager
from ditana_assistant.benchmark.multiple_choice_dataset import MultipleChoiceDataset, DatasetIdentifier


def run_evaluation(dataset_identifier: DatasetIdentifier, benchmark_experimental: bool):
    dataset = MultipleChoiceDataset(dataset_identifier)
    results = []

    for i, sample in enumerate(dataset.iterate_questions()):
        question = sample["question"]
        labeled_choices = sample["choices"]  # List of tuples (label, choice)
        correct_answer = sample["answer"]     # Correct answer label, e.g., 'B', 'C', etc.

        print(f"\n--- Question {i + 1} ---")
        print(f"Question: {question}")
        print("Choices:")
        for label, choice in labeled_choices:
            print(f"{label}. {choice}")
        print(f"Correct answer: {correct_answer if correct_answer else 'None'}")

        RequestManager.set_ica(benchmark_experimental)
        Configuration.set(enable_experimental_features=False)

        prediction_without_feature = dataset.process_question(question, labeled_choices)

        RequestManager.set_ica(True)
        Configuration.set(enable_experimental_features=benchmark_experimental)

        test_feature_name = "experimental" if benchmark_experimental else "ICA"

        print(f"Model’s answer (without {test_feature_name} feature): {prediction_without_feature if prediction_without_feature else 'None'}")

        prediction_with_feature = dataset.process_question(question, labeled_choices)

        print(f"Model’s answer (with {test_feature_name} feature): {prediction_with_feature if prediction_with_feature else 'None'}")

        correct_no_ica = prediction_without_feature == correct_answer
        correct_ica = prediction_with_feature == correct_answer

        results.append((correct_no_ica, correct_ica))

        statistics.update_results(results, test_feature_name)


def main():
    Configuration.set(
        model_type=ModelType.OPENAI,
        show_debug_messages=False,
        openai_model="gpt-4o-mini",
        koboldcpp_base_url="http://localhost:5001",
        wolfram_alpha_short_answers_app_id="",
        generate_terminal_cmd=False,
        offer_cmd_execution=False,
        assume_english=True
    )

    parser = argparse.ArgumentParser(description="Benchmark of Ditana Assistant")
    parser.add_argument(
        "-c", "--priority-cache",
        type=str,
        help="Use a priority cache file for read-only access to predefined responses. "
             "This allows the assistant to respond using cached data from the specified priority cache file before accessing the normal request cache."
    )
    parser.add_argument("-r", "--run", action="store_true", help="Run the benchmark.")
    parser.add_argument("-e", "--experimental", action="store_true", help="Compare ICA with an experimental version of it.")
    parser.add_argument(
        "-d", "--dataset",
        type=str,
        required=True,
        help="Identifier of the dataset to use. For example, 'ai2_arc' or 'cais_mmlu_logical_fallacies_test'."
    )
    args = parser.parse_args()

    if not args.run:
        parser.print_help()
        sys.exit(0)

    if args.priority_cache:
        ConversationManager.initialize_cache(priority_cache_path=args.priority_cache)

    try:
        dataset_identifier = DatasetIdentifier(args.dataset)
    except ValueError:
        print(f"Unknown dataset identifier: {args.dataset}")
        sys.exit(1)

    print("Running evaluation...")
    run_evaluation(dataset_identifier, args.experimental)


if __name__ == "__main__":
    main()
