"""
Shared constants for unit tests.
These constants provide cross-platform compatible paths instead of hardcoded /tmp paths.
"""

import os
import tempfile

# Use system temp directory for test paths instead of hardcoded /tmp for cross-platform compatibility
TEST_TEMP_DIR = tempfile.gettempdir()
TEST_SOURCE_DIR = os.path.join(TEST_TEMP_DIR, 'test_source')
