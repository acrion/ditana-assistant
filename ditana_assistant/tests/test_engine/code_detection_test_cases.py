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
This module contains test cases for code detection functions.
It provides input strings and expected outputs for use in multiple test classes.
"""

from typing import List, Tuple, Union

# Each test case is a tuple of (description, input_text, expected_output)
TestCase = Tuple[str, str, Union[bool, Tuple[bool, float]]]


def get_test_cases() -> List[TestCase]:
    """
    Returns a list of test cases for code detection.

    Each test case is a tuple containing:
    - A description of the test case
    - The input text to be analyzed
    - The expected output (either a boolean or a tuple of boolean and float)

    Returns:
        List[TestCase]: A list of test cases
    """
    return [
        (
            "Test if a single letter variable assignment is identified as code",
            "x = 5",
            True
        ),
        (
            "Test if multiple single letter variables in a loop are identified as code",
            "for i in range(n): a += b * c",
            True
        ),
        (
            "Test if normal text is correctly identified as non-code",
            "Dies ist ein normaler Satz ohne Code.",
            False
        ),
        (
            "Test if a PowerShell command is correctly identified as code",
            "Get-Content D:\\TestAusgabe.txt",
            True
        ),
        (
            "Test if a command without backticks is correctly identified as code",
            "systemctl status systemd-resolved",
            True
        ),
        (
            "Test if normal text that contains monospace formatted text is correctly identified as non-code",
            """The content of the file `~/test.txt` is:

```
testtest
``` 

Let me know if you'd like to explore other file operations!""",
            False
        ),
        (
            "Test if a short bash command is correctly identified as code",
            "cat ~/test.txt",
            True
        ),
        (
            "Test if meta execution of assistant is correctly identified as code",
            """```bash
ditana-assistant "Was kannst du mir über mein System erzählen?" $(uname -a)
```""",
            True
        ),
        (
            "Test if the output of a mathematical calculation is identified as non-code",
            "Der Wert von \\( 3^{50} \\) ist 7.625.597.484.987.",
            False
        ),
        (
            "Test if commented maths is correctly identified as not code",
            """```To find the angle between the ladder and the ground, we can use trigonometry. Let's denote the angle we are looking for as θ.
We have a right triangle formed by the ladder, the wall, and the ground. The ladder is the hypotenuse of the triangle, and its length is 4 meters. The distance from the bottom of the ladder to the wall is the adjacent side of the triangle, and its length is 3 meters.
We can use the cosine function to find the angle θ:
cos(θ) = adjacent / hypotenuse
cos(θ) = 3 / 4
θ = arccos(3/4)
θ ≈ 36.87 degrees
Therefore, the angle between the ladder and the ground is approximately 36.87 degrees.""",
            False
        ),
        (
            "Test if powershell code is correctly identified as code",
            """```powershell
$file = "~/test.txt"
(Get-Content $file)
```""",
            True
        ),
    ]
