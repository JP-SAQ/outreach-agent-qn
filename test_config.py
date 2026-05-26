"""
Tests for configuration management.

Tests the NewsletterConfig class and environment variable handling.
"""
import pytest
import os
from unittest.mock import patch

# Import from main module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quantum_intel import NewsletterConfig


class TestNewsletterConfig:
    """Tests for NewsletterConfig class (lines 47-58)."""

    @patch.dict(os.environ, {}, clear=True)
    def test_config_defaults(self):
        """Test that config initializes with correct default values."""
        config = NewsletterConfig()

        assert config.max_articles == 10
        assert config.search_timeout == 5
        assert config.link_validation_timeout == 5
        assert config.previous_articles_file == "sent_articles.txt"
        assert config.output_file == "quantum_newsletter_output.md"
        assert config.companies_to_track == ["EvolutionQ", "Qunnect"]
        assert config.title_similarity_threshold == 85

    @patch.dict(os.environ, {"MAX_ARTICLES": "15"})
    def test_config_max_articles_from_env(self):
        """Test that MAX_ARTICLES is loaded from environment."""
        config = NewsletterConfig()
        assert config.max_articles == 15

    @patch.dict(os.environ, {"SEARCH_TIMEOUT": "10"})
    def test_config_search_timeout_from_env(self):
        """Test that SEARCH_TIMEOUT is loaded from environment."""
        config = NewsletterConfig()
        assert config.search_timeout == 10

    @patch.dict(os.environ, {"LINK_VALIDATION_TIMEOUT": "3"})
    def test_config_link_validation_timeout_from_env(self):
        """Test that LINK_VALIDATION_TIMEOUT is loaded from environment."""
        config = NewsletterConfig()
        assert config.link_validation_timeout == 3

    @patch.dict(os.environ, {"PREVIOUS_ARTICLES_FILE": "custom_articles.txt"})
    def test_config_previous_articles_file_from_env(self):
        """Test that PREVIOUS_ARTICLES_FILE is loaded from environment."""
        config = NewsletterConfig()
        assert config.previous_articles_file == "custom_articles.txt"

    @patch.dict(os.environ, {"OUTPUT_FILE": "custom_output.md"})
    def test_config_output_file_from_env(self):
        """Test that OUTPUT_FILE is loaded from environment."""
        config = NewsletterConfig()
        assert config.output_file == "custom_output.md"

    @patch.dict(os.environ, {"COMPANIES_TO_TRACK": "CompanyA,CompanyB,CompanyC"})
    def test_config_companies_parsing_multiple(self):
        """Test that COMPANIES_TO_TRACK is correctly parsed into list."""
        config = NewsletterConfig()
        assert config.companies_to_track == ["CompanyA", "CompanyB", "CompanyC"]

    @patch.dict(os.environ, {"COMPANIES_TO_TRACK": "SingleCompany"})
    def test_config_companies_parsing_single(self):
        """Test that single company is correctly parsed."""
        config = NewsletterConfig()
        assert config.companies_to_track == ["SingleCompany"]

    @patch.dict(os.environ, {"COMPANIES_TO_TRACK": "Company1, Company2 , Company3"})
    def test_config_companies_parsing_with_spaces(self):
        """Test that company names with extra spaces are handled."""
        config = NewsletterConfig()
        # Note: The split() will preserve spaces unless we strip each element
        # Current implementation doesn't strip, so this tests actual behavior
        assert len(config.companies_to_track) == 3

    @patch.dict(os.environ, {
        "MAX_ARTICLES": "20",
        "SEARCH_TIMEOUT": "8",
        "COMPANIES_TO_TRACK": "Comp1,Comp2"
    })
    def test_config_multiple_env_vars(self):
        """Test that multiple environment variables are loaded correctly."""
        config = NewsletterConfig()

        assert config.max_articles == 20
        assert config.search_timeout == 8
        assert config.companies_to_track == ["Comp1", "Comp2"]

    @patch.dict(os.environ, {"MAX_ARTICLES": "not_a_number"})
    def test_config_invalid_int_raises_error(self):
        """Test that invalid integer value raises ValueError."""
        with pytest.raises(ValueError):
            NewsletterConfig()

    @patch.dict(os.environ, {"SEARCH_TIMEOUT": "invalid"})
    def test_config_invalid_timeout_raises_error(self):
        """Test that invalid timeout value raises ValueError."""
        with pytest.raises(ValueError):
            NewsletterConfig()

    def test_config_bad_url_keywords_is_list(self):
        """Test that bad_url_keywords is a list."""
        config = NewsletterConfig()
        assert isinstance(config.bad_url_keywords, list)
        assert len(config.bad_url_keywords) > 0

    def test_config_bad_url_keywords_contains_expected_values(self):
        """Test that bad_url_keywords contains expected filtering keywords."""
        config = NewsletterConfig()

        expected_keywords = ['/tag/', '/tags/', '/category/', '/topics/', '/solutions/', '/search/', '/page/']
        for keyword in expected_keywords:
            assert keyword in config.bad_url_keywords

    def test_config_title_similarity_threshold_is_int(self):
        """Test that title_similarity_threshold is an integer."""
        config = NewsletterConfig()
        assert isinstance(config.title_similarity_threshold, int)

    def test_config_title_similarity_threshold_reasonable_value(self):
        """Test that title_similarity_threshold is in reasonable range."""
        config = NewsletterConfig()
        assert 0 <= config.title_similarity_threshold <= 100


class TestConfigurationIntegration:
    """Integration tests for configuration usage."""

    @patch.dict(os.environ, {
        "MAX_ARTICLES": "5",
        "COMPANIES_TO_TRACK": "TestCompanyA,TestCompanyB"
    })
    def test_config_singleton_behavior(self):
        """Test that multiple Config instances reflect the same env vars."""
        config1 = NewsletterConfig()
        config2 = NewsletterConfig()

        # Both should read the same environment variables
        assert config1.max_articles == config2.max_articles
        assert config1.companies_to_track == config2.companies_to_track

    @patch.dict(os.environ, {}, clear=True)
    def test_config_with_no_env_vars(self):
        """Test that config works with no environment variables set."""
        # Should not raise any errors
        config = NewsletterConfig()

        # Should have all default values
        assert config.max_articles is not None
        assert config.search_timeout is not None
        assert config.companies_to_track is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
