"""
Tests for URL validation and article filtering functions.

Tests the validate_url() and is_article_url() functions from quantum_intel.py.
"""
import pytest
from unittest.mock import patch, Mock
import requests

# Import functions from main module
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quantum_intel import validate_url, is_article_url, NewsletterConfig


class TestValidateURL:
    """Tests for validate_url() function (lines 76-85 in quantum_intel.py)."""

    @patch('quantum_intel.requests.head')
    def test_validate_url_valid_200(self, mock_head):
        """Test that valid URL with 200 status returns True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        assert validate_url("https://example.com/article") is True
        mock_head.assert_called_once()

    @patch('quantum_intel.requests.head')
    def test_validate_url_valid_201(self, mock_head):
        """Test that URL with 201 status returns True."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_head.return_value = mock_response

        assert validate_url("https://example.com/article") is True

    @patch('quantum_intel.requests.head')
    def test_validate_url_redirect_299(self, mock_head):
        """Test that URL with 299 status (edge of 2xx range) returns True."""
        mock_response = Mock()
        mock_response.status_code = 299
        mock_head.return_value = mock_response

        assert validate_url("https://example.com/article") is True

    @patch('quantum_intel.requests.head')
    def test_validate_url_404(self, mock_head):
        """Test that URL with 404 status returns False."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        assert validate_url("https://example.com/missing") is False

    @patch('quantum_intel.requests.head')
    def test_validate_url_500(self, mock_head):
        """Test that URL with 500 status returns False."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        assert validate_url("https://example.com/error") is False

    def test_validate_url_invalid_format_no_scheme(self):
        """Test that URL without scheme returns False."""
        assert validate_url("example.com/article") is False

    def test_validate_url_invalid_format_no_netloc(self):
        """Test that URL without network location returns False."""
        assert validate_url("https://") is False

    @patch('quantum_intel.requests.head')
    def test_validate_url_timeout(self, mock_head):
        """Test that timeout exception returns False."""
        mock_head.side_effect = requests.exceptions.Timeout

        assert validate_url("https://example.com/slow", timeout=1) is False

    @patch('quantum_intel.requests.head')
    def test_validate_url_connection_error(self, mock_head):
        """Test that connection error returns False."""
        mock_head.side_effect = requests.exceptions.ConnectionError

        assert validate_url("https://nonexistent.example.com") is False

    @patch('quantum_intel.requests.head')
    def test_validate_url_request_exception(self, mock_head):
        """Test that generic request exception returns False."""
        mock_head.side_effect = requests.exceptions.RequestException

        assert validate_url("https://example.com/error") is False


class TestIsArticleURL:
    """Tests for is_article_url() function (lines 87-90 in quantum_intel.py)."""

    def test_is_article_url_valid_article(self):
        """Test that standard article URL returns True."""
        assert is_article_url("https://example.com/2026/04/quantum-breakthrough") is True

    def test_is_article_url_rejects_tag_page(self):
        """Test that /tag/ URL returns False."""
        assert is_article_url("https://example.com/tag/quantum") is False

    def test_is_article_url_rejects_tags_page(self):
        """Test that /tags/ URL returns False."""
        assert is_article_url("https://example.com/tags/networking") is False

    def test_is_article_url_rejects_category_page(self):
        """Test that /category/ URL returns False."""
        assert is_article_url("https://example.com/category/research") is False

    def test_is_article_url_rejects_topics_page(self):
        """Test that /topics/ URL returns False."""
        assert is_article_url("https://example.com/topics/quantum-computing") is False

    def test_is_article_url_rejects_solutions_page(self):
        """Test that /solutions/ URL returns False."""
        assert is_article_url("https://example.com/solutions/qkd") is False

    def test_is_article_url_rejects_search_page(self):
        """Test that /search/ URL returns False."""
        assert is_article_url("https://example.com/search?q=quantum") is False

    def test_is_article_url_rejects_page_pagination(self):
        """Test that /page/ URL returns False."""
        assert is_article_url("https://example.com/page/2") is False

    def test_is_article_url_case_insensitive(self):
        """Test that keyword matching is case-insensitive."""
        assert is_article_url("https://example.com/TAG/quantum") is False
        assert is_article_url("https://example.com/Category/research") is False

    def test_is_article_url_mixed_case_valid(self):
        """Test that valid article with mixed case returns True."""
        assert is_article_url("https://Example.com/Article/Quantum-News") is True


class TestNewsletterConfig:
    """Tests for NewsletterConfig class initialization."""

    @patch.dict(os.environ, {}, clear=True)
    def test_config_defaults(self):
        """Test that config loads with default values when env vars not set."""
        config = NewsletterConfig()

        assert config.max_articles == 10
        assert config.search_timeout == 5
        assert config.link_validation_timeout == 5
        assert config.previous_articles_file == "sent_articles.txt"
        assert config.output_file == "quantum_newsletter_output.md"
        assert config.companies_to_track == ["EvolutionQ", "Qunnect"]
        assert config.title_similarity_threshold == 85

    @patch.dict(os.environ, {
        "MAX_ARTICLES": "15",
        "SEARCH_TIMEOUT": "10",
        "COMPANIES_TO_TRACK": "CompanyA,CompanyB,CompanyC"
    })
    def test_config_from_env_vars(self):
        """Test that config correctly loads from environment variables."""
        config = NewsletterConfig()

        assert config.max_articles == 15
        assert config.search_timeout == 10
        assert config.companies_to_track == ["CompanyA", "CompanyB", "CompanyC"]

    @patch.dict(os.environ, {"MAX_ARTICLES": "not_a_number"})
    def test_config_invalid_int_conversion(self):
        """Test that invalid integer env var raises ValueError."""
        with pytest.raises(ValueError):
            NewsletterConfig()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
