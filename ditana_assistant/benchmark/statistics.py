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

"""Statistics functions used by the benchmark"""

from statsmodels.stats.contingency_tables import mcnemar


def calculate_significance(results):
    """
    Calculate statistical significance between two procedures using McNemar’s test.

    Args:
    results (list of tuples): Each tuple is (correct_no_ica, correct_ica), where
                              correct_no_ica and correct_ica are booleans indicating
                              whether the prediction was correct without ICA and with ICA.

    Returns:
    float: The p-value from McNemar’s test.
    """
    n00 = n01 = n10 = n11 = 0
    for res in results:
        c1, c2 = res
        if not c1 and not c2:
            n00 += 1
        elif not c1 and c2:
            n01 += 1
        elif c1 and not c2:
            n10 += 1
        elif c1 and c2:
            n11 += 1

    table = [[n00, n01],
             [n10, n11]]

    if (n01 + n10) == 0:
        return None

    try:
        if (n01 + n10) <= 25:
            result = mcnemar(table, exact=True)
        else:
            result = mcnemar(table, exact=False, correction=True)
        p_value = result.pvalue
        return p_value
    except ValueError:
        return None


def update_results(results, test_feature_name: str):
    """
    Update and print the current results of the benchmark comparison.

    This function calculates the hit rates for both procedures (with and without ICA),
    computes the statistical significance using McNemar’s test, and prints a formatted output.

    Args:
    results (list of tuples): Each tuple is (correct_no_ica, correct_ica), where
                              correct_no_ica and correct_ica are booleans indicating
                              whether the prediction was correct without ICA and with ICA.
    """
    hits1 = sum(1 for res in results if res[0])
    hits2 = sum(1 for res in results if res[1])
    total = len(results)
    difference = hits2 - hits1

    p_value = calculate_significance(results)
    print("--------------------")
    print(f"without {test_feature_name} feature: {hits1}/{total} ({hits1 / total:.2%})")
    print(f"with {test_feature_name} feature: {hits2}/{total} ({hits2 / total:.2%})")
    print(f"Difference : {difference}/{total} ({difference / total:.2%})")
    if p_value is not None:
        print(f"p-value    : {p_value:.4f}")
        print(f"significant: {'yes' if p_value < 0.05 else 'no'}")
    else:
        print("p-value    : Not available")
        print("significant: Unable to determine")
    print("--------------------")
