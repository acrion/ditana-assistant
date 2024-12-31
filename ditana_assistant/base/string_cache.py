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
This module provides a cache implementation for key-value string pairs with automatic persistence to disk.

The cache supports automatic expiration of entries based on their lifetime, and provides mechanisms for
extending the lifetime of entries that are set to the same value after expiration. In this way, entries
that do not change are gradually given longer lifetimes.
"""

import json
import os
import tempfile
from pathlib import Path
import time
from typing import Dict, Optional, Tuple

import platformdirs


class StringCache:
    """
    A cache class for storing key-value string pairs with automatic disk persistence,
    entry expiration, and a maximum cache size limit.

    The cache automatically writes to a JSON file on disk after each addition or modification of an entry.
    Entries have a lifetime and are automatically expired when accessed after their lifetime has passed.
    The cache also enforces a maximum size limit, removing entries when necessary to stay within the limit.
    """

    def __init__(
            self,
            base_filename: str,
            default_lifetime: float,
            max_size: int = 50*1024*1024,
            priority_cache_path: Optional[Path] = None):
        """
        Initialize the StringCache.

        Args:
            base_filename (str): The base name of the JSON file to store the cache.
            default_lifetime (float): The default lifetime of cache entries in seconds.
            max_size (int): The maximum size of the cache in bytes. Defaults to 20 MiB.
            priority_cache_path (Path): Use a priority cache file for read-only access to predefined responses, overriding the config file.
                In contrast to the standard cache, existing entries will be used even if their lifetime is expired.
        """
        self.base_filename = base_filename
        self.default_lifetime = default_lifetime
        self.max_size = max_size
        self.cache: Dict[str, Tuple[str, float, float]] = {}
        self.file_path: Path = Path(platformdirs.user_data_dir("ditana-assistant", ".")) / f"{base_filename}.json"
        self.priority_cache_path: Optional[Path] = None if priority_cache_path is None else Path(priority_cache_path)
        self.priority_cache: Optional[Dict[str, Tuple[str, float, float]]] = None
        self._load_cache()
        self.current_size = self._get_current_size()

    def _load_cache(self) -> None:
        """Load the cache from the JSON file if it exists."""
        if self.file_path.exists():
            with self.file_path.open('r', encoding='utf-8') as f:
                self.cache = json.load(f)

        if self.priority_cache_path is not None:
            with self.priority_cache_path.open('r', encoding='utf-8') as f:
                self.priority_cache = json.load(f)

    def _save_cache(self) -> None:
        """Save the cache to the JSON file using a temporary file and atomic rename."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a temporary file in the same directory as the target file
        temp_fd, temp_path = tempfile.mkstemp(dir=self.file_path.parent,
                                              prefix=self.base_filename,
                                              suffix='.tmp')

        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                json.dump(self.cache, temp_file)

            # Perform an atomic rename
            os.replace(temp_path, self.file_path)
        except Exception as e:
            # If an error occurs, make sure to remove the temporary file
            os.unlink(temp_path)
            raise e  # Re-raise the exception after cleanup

    @staticmethod
    def _get_entry_size(key: str, value: str) -> int:
        """Calculate the size of a cache entry in bytes."""
        return len(key.encode('utf-8')) + len(value.encode('utf-8'))

    def _get_current_size(self) -> int:
        """Calculate the current size of the cache in bytes."""
        return sum(self._get_entry_size(k, v[0]) for k, v in self.cache.items())

    def set(self, key: str, value: str) -> bool:
        """
        Set a key-value pair in the cache.

        If the entry already exists and the value is the same, update the timestamp and extend the lifetime.
        If adding the new entry would exceed the maximum cache size, older entries are removed to make space.

        Args:
            key (str): The key to set.
            value (str): The value to set.

        Returns:
            bool: True if the entry was set successfully, False if it couldn't be set due to size constraints.
        """
        current_time = time.time()
        new_entry_size = self._get_entry_size(key, value)

        # Check if the new entry alone exceeds the maximum cache size
        if new_entry_size > self.max_size:
            return False

        new_size = self.current_size

        # If the entry already exists, update it
        if key in self.cache:
            old_value, old_timestamp, old_lifetime = self.cache[key]
            if old_value == value:
                new_lifetime = 2 * max(old_lifetime, current_time - old_timestamp)
                self.cache[key] = (value, current_time, new_lifetime)
                self._save_cache()
                return True
            else:
                # Remove the old entry before adding the new one
                new_lifetime = old_lifetime / 2
                new_size -= self._get_entry_size(key, old_value)
                del self.cache[key]
        else:
            new_lifetime = self.default_lifetime

        # Check if adding the new entry would exceed the maximum size
        while new_size + new_entry_size > self.max_size:
            # Identify the entry with the most exceeded lifetime
            most_exceeded_entry = None
            max_exceeded_time = 0
            for current_entry, (_, timestamp, lifetime) in self.cache.items():
                # We examine all entries that have less lifetime than the new entry,
                # hence we add "+ lifetime" to the exceeded time
                exceeded_time = current_time - timestamp - lifetime + new_lifetime
                if exceeded_time > max_exceeded_time:
                    most_exceeded_entry = current_entry
                    max_exceeded_time = exceeded_time

            if most_exceeded_entry is None:
                # No entries have exceeded their lifetime to make space, can’t add new entry
                if new_size != self.current_size:
                    self._load_cache()  # restore that internal cache
                return False

            # Remove the most exceeded entry
            removed_size = self._get_entry_size(most_exceeded_entry, self.cache[most_exceeded_entry][0])
            del self.cache[most_exceeded_entry]
            new_size -= removed_size

        # Add the new entry
        self.cache[key] = (value, current_time, new_lifetime)
        self.current_size = new_size + new_entry_size
        self._save_cache()
        return True

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the value associated with a key from the cache.

        This method first checks the priority cache. If the key exists in the priority cache,
        its value is returned without considering its lifetime. If the key is not found in the
        priority cache, the method then checks the standard cache and returns the value only
        if it exists and has not expired based on its lifetime.

        Args:
            key (str): The key to retrieve from the cache.

        Returns:
            Optional[str]: The cached value if found and hasn't expired, otherwise None.
        """
        if self.priority_cache and key in self.priority_cache:
            return self.priority_cache[key][0]

        if key in self.cache:
            value, timestamp, lifetime = self.cache[key]
            if time.time() - timestamp <= lifetime:
                return value
            else:
                # We do not delete an old entry because we need to know its lifetime to calculate
                # the new lifetime in case the same key is later stored in `set`.
                pass

        return None

    def get_lifetime(self, key: str) -> Optional[float]:
        """
        Retrieve the remaining lifetime of the specified key in the cache.

        If the key exists in the priority cache, returns infinity as its lifetime is indefinite.
        If the key exists in the standard cache, returns the remaining lifetime in seconds if it has not expired.
        If the key does not exist or has expired, returns None.

        Args:
            key (str): The key for which to retrieve the lifetime.

        Returns:
            Optional[float]: The remaining lifetime in seconds (negative if it has expired),
                             infinity if the key is in the priority cache,
                             or None if the key does not exist
        """
        if self.priority_cache and key in self.priority_cache:
            return float('inf')
        if key in self.cache:
            _, timestamp, lifetime = self.cache[key]
            return lifetime - (time.time() - timestamp)
        return None

    def __contains__(self, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists and hasn't expired, False otherwise.
        """
        return self.get(key) is not None

    def __len__(self) -> int:
        """
        Get the number of non-expired entries in the cache.

        Returns:
            int: The number of non-expired entries.
        """
        valid_entries = sum(1 for key in self.cache if self.get(key) is not None)
        return valid_entries

    def clear(self) -> None:
        """
        Clear all entries from the cache and delete the associated file.

        This method removes all entries from the internal cache dictionary,
        resets the current size to 0, and deletes the JSON file from the disk.
        It does not affect the priority cache.

        Note: After calling this method, the cache will be empty, and the
        file will no longer exist on the disk. The next operation that
        writes to the cache will create a new file.
        """
        self.cache.clear()
        self.current_size = 0

        if self.file_path.exists():
            self.file_path.unlink()
