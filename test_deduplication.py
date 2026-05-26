"""
Tests for article deduplication functions.

Tests the get_previous_articles() function and deduplication logic
including URL-based and fuzzy title matching.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from thefuzz import fuzz

# Import functions from main module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quantum_intel import get_previous_articles, deduplicate_articles, NewsletterConfig


class TestGetPreviousArticles:
    """Tests for get_previous_articles() function (lines 162-169)."""

    def test_get_previous_articles_file_exists(self):
        """Test reading previous articles from existing file."""
        test_content = "https://example.com/article1\nhttps://example.com/article2\nhttps://example.com/article3\n"

        with patch("builtins.open", mock_open(read_data=test_content)):
            result = get_previous_articles()

        assert len(result) == 3
        assert "https://example.com/article1" in result
        assert "https://example.com/article2" in result
        assert "https://example.com/article3" in result

    def test_get_previous_articles_file_missing(self):
        """Test that missing file returns empty list."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = get_previous_articles()

        assert result == []

    def test_get_previous_articles_empty_file(self):
        """Test that empty file returns empty list."""
        with patch("builtins.open", mock_open(read_data="")):
            result = get_previous_articles()

        assert result == []

    def test_get_previous_articles_with_blank_lines(self):
        """Test that blank lines are filtered out."""
        test_content = "https://example.com/article1\n\n\nhttps://example.com/article2\n\n"

        with patch("builtins.open", mock_open(read_data=test_content)):
            result = get_previous_articles()

        assert len(result) == 2
        assert "" not in result

    def test_get_previous_articles_strips_whitespace(self):
        """Test that whitespace is stripped from URLs."""
        test_content = "  https://example.com/article1  \n https://example.com/article2\n"

        with patch("builtins.open", mock_open(read_data=test_content)):
            result = get_previous_articles()

        assert result[0] == "https://example.com/article1"
        assert result[1] == "https://example.com/article2"


class TestDeduplicationLogic:
    """Tests for deduplicate_articles() function (lines 287-323)."""

    @patch('quantum_intel.get_previous_articles')
    def test_deduplicate_by_url(self, mock_get_previous):
        """Test that articles with previously sent URLs are removed."""
        mock_get_previous.return_value = [
            "https://example.com/article1",
            "https://example.com/article2"
        ]

        state = {
            "new_articles": [
                {"title": "Article 1", "url": "https://example.com/article1"},
                {"title": "Article 3", "url": "https://example.com/article3"},
                {"title": "Article 2", "url": "https://example.com/article2"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        assert len(result["deduped_articles"]) == 1
        assert result["deduped_articles"][0]["url"] == "https://example.com/article3"

    @patch('quantum_intel.get_previous_articles')
    def test_deduplicate_by_title_similarity(self, mock_get_previous):
        """Test that articles with similar titles are removed."""
        mock_get_previous.return_value = []

        state = {
            "new_articles": [
                {"title": "Quantum Computing Advances in 2026", "url": "https://site1.com/a1"},
                {"title": "Quantum Computing Advances 2026", "url": "https://site2.com/a2"},  # Similar title
                {"title": "Breakthrough in QKD Technology", "url": "https://site3.com/a3"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        # Should keep first occurrence and unique article
        assert len(result["deduped_articles"]) == 2
        titles = [a["title"] for a in result["deduped_articles"]]
        assert "Quantum Computing Advances in 2026" in titles
        assert "Breakthrough in QKD Technology" in titles

    @patch('quantum_intel.get_previous_articles')
    def test_similarity_threshold_boundary(self, mock_get_previous):
        """Test that similarity threshold (85%) is correctly applied."""
        mock_get_previous.return_value = []

        # Calculate similarity between these titles
        title1 = "Quantum Networks in 2026"
        title2 = "Quantum Networks 2026"
        similarity = fuzz.ratio(title1.lower(), title2.lower())

        # Verify they're above threshold (should be ~91%)
        assert similarity > 85

        state = {
            "new_articles": [
                {"title": title1, "url": "https://site1.com/a1"},
                {"title": title2, "url": "https://site2.com/a2"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        # Should deduplicate due to high similarity
        assert len(result["deduped_articles"]) == 1

    @patch('quantum_intel.get_previous_articles')
    def test_max_articles_limit(self, mock_get_previous):
        """Test that max_articles limit is enforced."""
        mock_get_previous.return_value = []

        # Create more articles than max limit
        articles = [
            {"title": f"Unique Article {i}", "url": f"https://example.com/article{i}"}
            for i in range(20)
        ]

        state = {
            "new_articles": articles,
            "processing_stats": {}
        }

        with patch('quantum_intel.config.max_articles', 10):
            result = deduplicate_articles(state)

        assert len(result["deduped_articles"]) == 10

    @patch('quantum_intel.get_previous_articles')
    def test_preserves_unique_articles(self, mock_get_previous):
        """Test that unique articles are preserved."""
        mock_get_previous.return_value = []

        state = {
            "new_articles": [
                {"title": "Article About Quantum Networks", "url": "https://site1.com/a1"},
                {"title": "Breakthrough in QKD Technology", "url": "https://site2.com/a2"},
                {"title": "New Quantum Memory System", "url": "https://site3.com/a3"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        assert len(result["deduped_articles"]) == 3

    @patch('quantum_intel.get_previous_articles')
    def test_combined_url_and_title_dedup(self, mock_get_previous):
        """Test deduplication with both URL and title matching."""
        mock_get_previous.return_value = ["https://site1.com/a1"]

        state = {
            "new_articles": [
                {"title": "Quantum Article 1", "url": "https://site1.com/a1"},  # Duplicate URL
                {"title": "Quantum Article 1", "url": "https://site2.com/a2"},  # Duplicate title
                {"title": "Unique Article", "url": "https://site3.com/a3"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        # Should only keep the unique article
        assert len(result["deduped_articles"]) == 1
        assert result["deduped_articles"][0]["title"] == "Unique Article"

    @patch('quantum_intel.get_previous_articles')
    def test_processing_stats_updated(self, mock_get_previous):
        """Test that processing stats are correctly updated."""
        mock_get_previous.return_value = ["https://site1.com/a1"]

        state = {
            "new_articles": [
                {"title": "Article 1", "url": "https://site1.com/a1"},
                {"title": "Article 2", "url": "https://site2.com/a2"},
                {"title": "Article 2 Duplicate", "url": "https://site3.com/a3"}
            ],
            "processing_stats": {}
        }

        result = deduplicate_articles(state)

        assert "articles_after_url_dedup" in result["processing_stats"]
        assert "articles_after_title_dedup" in result["processing_stats"]
        assert "duplicates_removed" in result["processing_stats"]
        assert result["processing_stats"]["duplicates_removed"] == 2


class TestFuzzyMatching:
    """Tests for fuzzy string matching behavior."""

    def test_identical_titles_100_similarity(self):
        """Test that identical titles have 100% similarity."""
        title1 = "Quantum Computing Breakthrough"
        title2 = "Quantum Computing Breakthrough"

        similarity = fuzz.ratio(title1.lower(), title2.lower())
        assert similarity == 100

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        title1 = "Quantum Computing"
        title2 = "quantum computing"

        similarity = fuzz.ratio(title1.lower(), title2.lower())
        assert similarity == 100

    def test_minor_differences_high_similarity(self):
        """Test that minor differences still result in high similarity."""
        title1 = "Quantum Networks in 2026"
        title2 = "Quantum Networks 2026"

        similarity = fuzz.ratio(title1.lower(), title2.lower())
        assert similarity > 85  # Should be caught by 85% threshold

    def test_different_titles_low_similarity(self):
        """Test that different titles have low similarity."""
        title1 = "Quantum Networks"
        title2 = "Artificial Intelligence"

        similarity = fuzz.ratio(title1.lower(), title2.lower())
        assert similarity < 85  # Should not be caught by threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
