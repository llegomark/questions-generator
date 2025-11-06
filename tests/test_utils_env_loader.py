"""
Unit tests for environment loader utility (env_loader.py).

Tests cover:
- Loading environment variables from .env file
- Handling missing .env file
- Parsing key-value pairs
- Handling comments and empty lines
- Edge cases
"""
import os
import pytest
from pathlib import Path

from src.nqesh_generator.utils.env_loader import load_env


@pytest.mark.unit
class TestEnvLoader:
    """Test environment variable loading utility."""

    def test_load_env_file_exists(self, temp_dir, monkeypatch):
        """Test loading environment variables from existing .env file."""
        # Change to temp directory
        monkeypatch.chdir(temp_dir)

        # Create .env file
        env_file = temp_dir / ".env"
        env_file.write_text("TEST_KEY=test_value\nANOTHER_KEY=another_value\n")

        # Load environment
        load_env()

        # Verify environment variables are set
        assert os.environ.get("TEST_KEY") == "test_value"
        assert os.environ.get("ANOTHER_KEY") == "another_value"

    def test_load_env_file_not_exists(self, temp_dir, monkeypatch):
        """Test that load_env handles missing .env file gracefully."""
        # Change to temp directory (no .env file)
        monkeypatch.chdir(temp_dir)

        # Should not raise an error
        try:
            load_env()
        except FileNotFoundError:
            pytest.fail("load_env() should not raise FileNotFoundError when .env is missing")

    def test_load_env_with_comments(self, temp_dir, monkeypatch):
        """Test that comments in .env file are ignored."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "# This is a comment\n"
            "VALID_KEY=valid_value\n"
            "# Another comment\n"
            "ANOTHER_KEY=another_value\n"
        )

        load_env()

        assert os.environ.get("VALID_KEY") == "valid_value"
        assert os.environ.get("ANOTHER_KEY") == "another_value"
        # Comments should not be set as environment variables
        assert os.environ.get("# This is a comment") is None

    def test_load_env_with_empty_lines(self, temp_dir, monkeypatch):
        """Test that empty lines in .env file are ignored."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "KEY1=value1\n"
            "\n"
            "KEY2=value2\n"
            "\n\n"
            "KEY3=value3\n"
        )

        load_env()

        assert os.environ.get("KEY1") == "value1"
        assert os.environ.get("KEY2") == "value2"
        assert os.environ.get("KEY3") == "value3"

    def test_load_env_with_spaces(self, temp_dir, monkeypatch):
        """Test handling of spaces in .env file."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "KEY_WITH_SPACES = value with spaces\n"
            "TRIMMED_KEY=trimmed_value\n"
        )

        load_env()

        # Keys and values should be stripped
        assert os.environ.get("KEY_WITH_SPACES") == "value with spaces"
        assert os.environ.get("TRIMMED_KEY") == "trimmed_value"

    def test_load_env_with_equals_in_value(self, temp_dir, monkeypatch):
        """Test that values can contain equals signs."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text("CONNECTION_STRING=key=value;another=setting\n")

        load_env()

        assert os.environ.get("CONNECTION_STRING") == "key=value;another=setting"

    def test_load_env_overrides_existing(self, temp_dir, monkeypatch):
        """Test that .env values override existing environment variables."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv("EXISTING_KEY", "old_value")

        env_file = temp_dir / ".env"
        env_file.write_text("EXISTING_KEY=new_value\n")

        load_env()

        # Should be overridden with new value
        assert os.environ.get("EXISTING_KEY") == "new_value"

    def test_load_env_gemini_api_key(self, temp_dir, monkeypatch):
        """Test loading GEMINI_API_KEY specifically."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=AIzaSyTest1234567890\n")

        load_env()

        assert os.environ.get("GEMINI_API_KEY") == "AIzaSyTest1234567890"

    def test_load_env_empty_file(self, temp_dir, monkeypatch):
        """Test loading an empty .env file."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text("")

        # Should not raise an error
        load_env()

    def test_load_env_only_comments(self, temp_dir, monkeypatch):
        """Test .env file with only comments."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "# Comment 1\n"
            "# Comment 2\n"
            "# Comment 3\n"
        )

        # Should not raise an error
        load_env()

    def test_load_env_malformed_line_no_equals(self, temp_dir, monkeypatch):
        """Test that lines without '=' are ignored."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "VALID_KEY=valid_value\n"
            "MALFORMED_LINE_WITHOUT_EQUALS\n"
            "ANOTHER_KEY=another_value\n"
        )

        load_env()

        assert os.environ.get("VALID_KEY") == "valid_value"
        assert os.environ.get("ANOTHER_KEY") == "another_value"
        # Malformed line should be ignored
        assert os.environ.get("MALFORMED_LINE_WITHOUT_EQUALS") is None

    def test_load_env_special_characters(self, temp_dir, monkeypatch):
        """Test handling special characters in values."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "SPECIAL_CHARS=!@#$%^&*()\n"
            "UNICODE_VALUE=こんにちは\n"
        )

        load_env()

        assert os.environ.get("SPECIAL_CHARS") == "!@#$%^&*()"
        assert os.environ.get("UNICODE_VALUE") == "こんにちは"

    def test_load_env_multiple_calls(self, temp_dir, monkeypatch):
        """Test calling load_env multiple times."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text("KEY=value1\n")

        load_env()
        assert os.environ.get("KEY") == "value1"

        # Update .env file
        env_file.write_text("KEY=value2\n")

        # Call load_env again
        load_env()
        assert os.environ.get("KEY") == "value2"

    def test_load_env_from_different_directory(self, temp_dir, monkeypatch):
        """Test that load_env looks for .env in current directory."""
        # Create subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        # Create .env in temp_dir
        env_file = temp_dir / ".env"
        env_file.write_text("PARENT_KEY=parent_value\n")

        # Create .env in subdir
        subdir_env = subdir / ".env"
        subdir_env.write_text("CHILD_KEY=child_value\n")

        # Change to parent directory
        monkeypatch.chdir(temp_dir)
        load_env()
        assert os.environ.get("PARENT_KEY") == "parent_value"
        assert os.environ.get("CHILD_KEY") is None

        # Change to child directory
        monkeypatch.chdir(subdir)
        load_env()
        assert os.environ.get("CHILD_KEY") == "child_value"

    def test_load_env_empty_value(self, temp_dir, monkeypatch):
        """Test handling empty values in .env file."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            "EMPTY_VALUE=\n"
            "NORMAL_VALUE=normal\n"
        )

        load_env()

        assert os.environ.get("EMPTY_VALUE") == ""
        assert os.environ.get("NORMAL_VALUE") == "normal"

    def test_load_env_quoted_values(self, temp_dir, monkeypatch):
        """Test that quoted values are preserved as-is."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text(
            'QUOTED_VALUE="quoted string"\n'
            "SINGLE_QUOTED='single quoted'\n"
        )

        load_env()

        # Note: The simple loader doesn't strip quotes
        # This is expected behavior for the current implementation
        assert os.environ.get("QUOTED_VALUE") == '"quoted string"'
        assert os.environ.get("SINGLE_QUOTED") == "'single quoted'"

    def test_load_env_integration_with_config(self, temp_dir, monkeypatch):
        """Test integration with actual config usage pattern."""
        monkeypatch.chdir(temp_dir)

        env_file = temp_dir / ".env"
        env_file.write_text("GEMINI_API_KEY=test-api-key-123\n")

        # Simulate typical usage pattern
        load_env()

        api_key = os.environ.get("GEMINI_API_KEY")
        assert api_key == "test-api-key-123"
        assert api_key is not None
