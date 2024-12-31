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
This module contains unit tests for the StringCache class.

The tests cover various aspects of the StringCache functionality, including:
- Basic set and get operations
- Entry expiration
- Lifetime extension and reduction
- Priority cache behavior
- Maximum size limit enforcement
- Data persistence between instances
- Cache clearing
- Key existence checking
- Cache size reporting
- File reading and writing consistency

These tests ensure that the StringCache class behaves correctly under different scenarios
and maintains data integrity across multiple instances and file operations.
"""

import unittest
import time
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Tuple

from ditana_assistant.base import string_cache

"""
This module contains unit tests for the StringCache class.

The tests cover various aspects of the StringCache functionality, including:
- Basic set and get operations
- Entry expiration
- Lifetime extension and reduction
- Priority cache behavior
- Maximum size limit enforcement
- Data persistence between instances
- Cache clearing
- Key existence checking
- Cache size reporting
- File reading and writing consistency
- Stress testing with random key/value pairs

These tests ensure that the StringCache class behaves correctly under different scenarios
and maintains data integrity across multiple instances and file operations.
"""

import unittest
import time
import tempfile
import json
import os
import random
import string
import logging
from pathlib import Path
from typing import Dict, Tuple

from ditana_assistant.base import string_cache

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestStringCache(unittest.TestCase):
    """Unit tests for the StringCache class."""

    def setUp(self) -> None:
        """Set up a StringCache instance for each test."""
        self.cache = string_cache.StringCache("unit-test", default_lifetime=0.5)
        self.cache.clear()  # Ensure a clean state even if previous test was interrupted

    def tearDown(self) -> None:
        """Clean up after each test."""
        self.cache.clear()

    def test_set_and_get_immediately(self) -> None:
        """Test setting a cache entry and retrieving it immediately."""
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_expiration(self) -> None:
        """Test that a cache entry expires after its lifetime."""
        self.cache.set("key2", "value2")
        time.sleep(1)  # Wait for the entry to expire
        self.assertIsNone(self.cache.get("key2"))

    def test_extend_lifetime_same_value(self) -> None:
        """Test that setting the same value extends the lifetime."""
        self.cache.set("key3", "value3")
        time.sleep(1)  # Wait for the entry to expire
        self.cache.set("key3", "value3")
        self.assertGreaterEqual(self.cache.get_lifetime("key3"), 1.0)

    def test_reduce_lifetime_different_value(self) -> None:
        """Test that setting a different value reduces the lifetime."""
        self.cache.set("key4", "value4")
        time.sleep(1)  # Wait for the entry to expire
        self.cache.set("key4", "new_value4")
        self.assertLess(self.cache.get_lifetime("key4"), 0.75)

    def test_priority_cache(self) -> None:
        """Test the priority cache functionality."""
        # Create a temporary file for the priority cache
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            # Create a cache and set some values
            temp_cache = string_cache.StringCache("temp-cache", default_lifetime=1000)
            temp_cache.set("priority_key", "priority_value")

            # Copy the contents of the cache file to the temporary file
            with open(temp_cache.file_path, 'r') as source_file:
                temp_file.write(source_file.read())

        # Create a new cache with the priority cache file
        priority_cache = string_cache.StringCache("unit-test", default_lifetime=0.5,
                                                  priority_cache_path=Path(temp_file.name))

        # Test that the priority cache entry is accessible
        self.assertEqual(priority_cache.get("priority_key"), "priority_value")

        # Test that the priority cache entry doesn't expire
        time.sleep(1)
        self.assertEqual(priority_cache.get("priority_key"), "priority_value")

        # Clean up
        Path(temp_file.name).unlink()

    def test_max_size_limit(self) -> None:
        """Test that the cache respects the maximum size limit."""
        # Set a small max_size for testing
        small_cache = string_cache.StringCache("unit-test", default_lifetime=0.5, max_size=100)

        # Add entries until we exceed the limit
        for i in range(10):
            key = f"key{i}"
            value = f"value{i}" * 5  # Make the value long enough to exceed the limit quickly
            small_cache.set(key, value)

        # Check that the cache size is below or equal to the max_size
        self.assertLessEqual(small_cache.current_size, 100)

    def test_persistence(self) -> None:
        """Test that the cache persists data between instances."""
        self.cache.set("persist_key", "persist_value")

        # Create a new cache instance to test persistence
        new_cache = string_cache.StringCache("unit-test", default_lifetime=0.5)
        self.assertEqual(new_cache.get("persist_key"), "persist_value")

    def test_clear(self) -> None:
        """Test the clear method."""
        self.cache.set("key_to_clear", "value_to_clear")
        self.cache.clear()
        self.assertIsNone(self.cache.get("key_to_clear"))
        self.assertEqual(len(self.cache), 0)

    def test_contains(self) -> None:
        """Test the __contains__ method."""
        self.cache.set("contain_key", "contain_value")
        self.assertIn("contain_key", self.cache)
        self.assertNotIn("non_existent_key", self.cache)

    def test_len(self) -> None:
        """Test the __len__ method."""
        self.cache.set("len_key1", "len_value1")
        self.cache.set("len_key2", "len_value2")
        self.assertEqual(len(self.cache), 2)

    def test_file_read_write_consistency(self) -> None:
        """Test that the stored file is correctly read when creating a new instance."""
        # Set some values in the cache
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Create a new instance to read from the file
        new_cache = string_cache.StringCache("unit-test", default_lifetime=0.5)

        # Check if the values are correctly read
        self.assertEqual(new_cache.get("key1"), "value1")
        self.assertEqual(new_cache.get("key2"), "value2")

        # Check if the number of entries is correct
        self.assertEqual(len(new_cache), 2)

    def test_stress(self) -> None:
        """Stress test the cache with random key/value pairs."""
        # Create a new cache with a larger max_size for stress testing
        stress_cache = string_cache.StringCache("stress-test", default_lifetime=60, max_size=1024 * 1024)  # 1 MiB

        # Generate random key/value pairs
        def random_string(length: int) -> str:
            return ''.join(random.choice(string.ascii_letters) for _ in range(length))

        num_operations = 1000
        keys = [random_string(10) for _ in range(num_operations)]
        values = [random_string(50) for _ in range(num_operations)]

        # Perform set operations
        for key, value in zip(keys, values):
            stress_cache.set(key, value)

        # Verify all values are retrievable
        for key, value in zip(keys, values):
            self.assertEqual(stress_cache.get(key), value)

        # Perform mixed set and get operations
        for _ in range(num_operations):
            operation = random.choice(['set', 'get'])
            key = random.choice(keys)
            if operation == 'set':
                new_value = random_string(50)
                stress_cache.set(key, new_value)
            else:
                stress_cache.get(key)

        # Verify cache size is within limits
        self.assertLessEqual(stress_cache.current_size, 1024 * 1024)

        # Clean up
        stress_cache.clear()


if __name__ == '__main__':
    unittest.main()
