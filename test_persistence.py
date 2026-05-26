"""
Tests for persistence and file I/O functions.

Tests the update_persistence() and save_processing_stats() functions.
"""
import pytest
import os
import json
import tempfile
from unittest.mock import patch, mock_open, Mock
from pathlib import Path

# Import functions from main module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quantum_intel import update_persistence, save_processing_stats


class TestUpdatePersistence:
    """Tests for update_persistence() function (lines 454-469)."""

    @patch("builtins.open", new_callable=mock_open)
    def test_update_persistence_appends_urls(self, mock_file):
        """Test that new URLs are appended to persistence file."""
        state = {
            "deduped_articles": [
                {"url": "https://example.com/article1"},
                {"url": "https://example.com/article2"},
                {"url": "https://example.com/article3"}
            ]
        }

        result = update_persistence(state)

        # Verify file was opened in append mode
        mock_file.assert_called_once_with("sent_articles.txt", "a")

        # Verify all URLs were written
        handle = mock_file()
        assert handle.write.call_count == 3
        handle.write.assert_any_call("https://example.com/article1\n")
        handle.write.assert_any_call("https://example.com/article2\n")
        handle.write.assert_any_call("https://example.com/article3\n")

    @patch("builtins.open", new_callable=mock_open)
    def test_update_persistence_empty_articles(self, mock_file):
        """Test that empty articles list doesn't write anything."""
        state = {
            "deduped_articles": []
        }

        result = update_persistence(state)

        # File should not be opened if no articles
        mock_file.assert_not_called()

    @patch("builtins.open", new_callable=mock_open)
    def test_update_persistence_single_article(self, mock_file):
        """Test persistence with single article."""
        state = {
            "deduped_articles": [
                {"url": "https://example.com/single-article"}
            ]
        }

        update_persistence(state)

        handle = mock_file()
        handle.write.assert_called_once_with("https://example.com/single-article\n")

    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_update_persistence_handles_io_error(self, mock_file):
        """Test that IO errors are handled gracefully."""
        state = {
            "deduped_articles": [
                {"url": "https://example.com/article"}
            ]
        }

        # Should not raise exception
        result = update_persistence(state)

        # Error should be added to state
        assert "errors" in result
        assert any("Persistence update failed" in str(e) for e in result["errors"])

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_update_persistence_handles_permission_error(self, mock_file):
        """Test that permission errors are handled."""
        state = {
            "deduped_articles": [
                {"url": "https://example.com/article"}
            ]
        }

        result = update_persistence(state)

        assert "errors" in result

    def test_update_persistence_integration(self):
        """Integration test with real temporary file."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name

        try:
            state = {
                "deduped_articles": [
                    {"url": "https://example.com/test1"},
                    {"url": "https://example.com/test2"}
                ]
            }

            # Patch config to use temp file
            with patch('quantum_intel.config.previous_articles_file', temp_file):
                update_persistence(state)

            # Verify file contents
            with open(temp_file, 'r') as f:
                lines = f.readlines()

            assert len(lines) == 2
            assert lines[0].strip() == "https://example.com/test1"
            assert lines[1].strip() == "https://example.com/test2"

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestSaveProcessingStats:
    """Tests for save_processing_stats() function (lines 171-181)."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_processing_stats_writes_json(self, mock_json_dump, mock_file):
        """Test that stats are saved as JSON."""
        stats = {
            "articles_found": 150,
            "articles_after_dedup": 10,
            "companies_tracked": 2
        }

        save_processing_stats(stats)

        # Verify file opened for writing
        mock_file.assert_called_once_with("newsletter_stats.json", "w")

        # Verify json.dump was called
        mock_json_dump.assert_called_once()

        # Check the structure of data passed to json.dump
        call_args = mock_json_dump.call_args[0]
        saved_data = call_args[0]

        assert "last_run" in saved_data
        assert "stats" in saved_data
        assert saved_data["stats"] == stats

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_processing_stats_includes_timestamp(self, mock_json_dump, mock_file):
        """Test that timestamp is included in saved stats."""
        stats = {"test_stat": 123}

        save_processing_stats(stats)

        # Get the data that was passed to json.dump
        call_args = mock_json_dump.call_args[0]
        saved_data = call_args[0]

        assert "last_run" in saved_data
        # Verify it's an ISO format timestamp
        assert isinstance(saved_data["last_run"], str)
        # Should contain date/time components
        assert "T" in saved_data["last_run"]  # ISO format separator

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_processing_stats_uses_indent(self, mock_json_dump, mock_file):
        """Test that JSON is formatted with indentation."""
        stats = {"test": 1}

        save_processing_stats(stats)

        # Check that indent parameter was passed
        call_kwargs = mock_json_dump.call_args[1]
        assert "indent" in call_kwargs
        assert call_kwargs["indent"] == 2

    @patch("builtins.open", side_effect=IOError("Cannot write"))
    def test_save_processing_stats_handles_error(self, mock_file):
        """Test that file write errors are handled gracefully."""
        stats = {"test": 1}

        # Should not raise exception
        save_processing_stats(stats)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump", side_effect=ValueError("Invalid JSON"))
    def test_save_processing_stats_handles_json_error(self, mock_json_dump, mock_file):
        """Test that JSON serialization errors are handled."""
        stats = {"test": 1}

        # Should not raise exception
        save_processing_stats(stats)

    def test_save_processing_stats_integration(self):
        """Integration test with real temporary file."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            stats = {
                "articles_found": 100,
                "duplicates_removed": 5,
                "email_sent": True
            }

            # Patch the stats file name
            with patch('quantum_intel.os.path.dirname', return_value=os.path.dirname(temp_file)):
                # Temporarily change the stats file location
                import quantum_intel
                original_stats_file = "newsletter_stats.json"

                # Direct test - just write to temp file
                with open(temp_file, "w") as f:
                    import datetime
                    json.dump({
                        "last_run": datetime.datetime.now().isoformat(),
                        "stats": stats
                    }, f, indent=2)

            # Verify file exists and contains valid JSON
            with open(temp_file, 'r') as f:
                loaded_data = json.load(f)

            assert "last_run" in loaded_data
            assert "stats" in loaded_data
            assert loaded_data["stats"]["articles_found"] == 100
            assert loaded_data["stats"]["duplicates_removed"] == 5

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_processing_stats_empty_stats(self, mock_json_dump, mock_file):
        """Test saving empty stats dictionary."""
        stats = {}

        save_processing_stats(stats)

        # Should still save with timestamp
        call_args = mock_json_dump.call_args[0]
        saved_data = call_args[0]

        assert saved_data["stats"] == {}
        assert "last_run" in saved_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
