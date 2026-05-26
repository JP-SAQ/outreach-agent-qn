"""
Tests for content formatting functions.

Tests the convert_markdown_to_html() and clean_snippet() functions.
"""
import pytest
from unittest.mock import patch, Mock

# Import functions from main module
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quantum_intel import convert_markdown_to_html, clean_snippet


class TestConvertMarkdownToHTML:
    """Tests for convert_markdown_to_html() function (lines 147-160)."""

    def test_markdown_to_html_basic_text(self):
        """Test that basic text is wrapped in HTML."""
        md_content = "This is a test"
        result = convert_markdown_to_html(md_content)

        assert "<html>" in result
        assert "<body" in result
        assert "This is a test" in result
        assert "</body>" in result
        assert "</html>" in result

    def test_markdown_to_html_headers(self):
        """Test that ## headers are converted to <h2> tags."""
        md_content = "## Executive Summary\nContent here"
        result = convert_markdown_to_html(md_content)

        assert "<h2>Executive Summary</h2>" in result

    def test_markdown_to_html_links(self):
        """Test that markdown links are converted to HTML anchor tags."""
        md_content = "[Article Title](https://example.com/article)"
        result = convert_markdown_to_html(md_content)

        assert '<a href="https://example.com/article">Article Title</a>' in result

    def test_markdown_to_html_multiple_links(self):
        """Test that multiple links are all converted."""
        md_content = "[Link 1](https://example.com/1) and [Link 2](https://example.com/2)"
        result = convert_markdown_to_html(md_content)

        assert '<a href="https://example.com/1">Link 1</a>' in result
        assert '<a href="https://example.com/2">Link 2</a>' in result

    def test_markdown_to_html_newlines(self):
        """Test that newlines are converted to <br> tags."""
        md_content = "Line 1\nLine 2\nLine 3"
        result = convert_markdown_to_html(md_content)

        assert "<br>" in result
        # Should have multiple <br> tags
        assert result.count("<br>") >= 2

    def test_markdown_to_html_style_attributes(self):
        """Test that result includes inline CSS styles."""
        md_content = "Test content"
        result = convert_markdown_to_html(md_content)

        assert "font-family:" in result
        assert "font-size:" in result
        assert "line-height:" in result
        assert "color:" in result

    def test_markdown_to_html_complex_content(self):
        """Test conversion of complex markdown with headers, links, and text."""
        md_content = """## Newsletter Title
This is a [link](https://example.com).
More content here."""

        result = convert_markdown_to_html(md_content)

        assert "<h2>Newsletter Title</h2>" in result
        assert '<a href="https://example.com">link</a>' in result
        assert "More content here" in result


class TestCleanSnippet:
    """Tests for clean_snippet() function (lines 93-115)."""

    @patch('quantum_intel.llm')
    def test_clean_snippet_with_mock_llm(self, mock_llm):
        """Test snippet cleaning with mocked LLM response."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Clean snippet content without navigation elements"
        mock_llm.invoke.return_value = mock_response

        raw_snippet = "Menu | Home | About | Quantum breakthrough achieved | Footer | Contact"
        result = clean_snippet(raw_snippet)

        assert result == "Clean snippet content without navigation elements"
        mock_llm.invoke.assert_called_once()

    @patch('quantum_intel.llm')
    def test_clean_snippet_empty_string(self, mock_llm):
        """Test that empty snippet returns empty string without calling LLM."""
        result = clean_snippet("")

        assert result == ""
        mock_llm.invoke.assert_not_called()

    @patch('quantum_intel.llm')
    def test_clean_snippet_none_value(self, mock_llm):
        """Test that None snippet returns empty string without calling LLM."""
        result = clean_snippet(None)

        assert result == ""
        mock_llm.invoke.assert_not_called()

    @patch('quantum_intel.llm')
    def test_clean_snippet_error_handling(self, mock_llm):
        """Test that errors return original snippet."""
        mock_llm.invoke.side_effect = Exception("LLM API error")

        raw_snippet = "Original snippet with errors"
        result = clean_snippet(raw_snippet)

        # Should return original snippet on error
        assert result == raw_snippet

    @patch('quantum_intel.llm')
    def test_clean_snippet_removes_quotes(self, mock_llm):
        """Test that surrounding quotes are stripped from cleaned snippet."""
        mock_response = Mock()
        mock_response.content = '"Clean content with quotes"'
        mock_llm.invoke.return_value = mock_response

        raw_snippet = "Original content"
        result = clean_snippet(raw_snippet)

        # Quotes should be stripped
        assert result == "Clean content with quotes"
        assert not result.startswith('"')
        assert not result.endswith('"')

    @patch('quantum_intel.llm')
    def test_clean_snippet_prompt_structure(self, mock_llm):
        """Test that prompt is structured correctly."""
        mock_response = Mock()
        mock_response.content = "Cleaned"
        mock_llm.invoke.return_value = mock_response

        raw_snippet = "Test snippet"
        clean_snippet(raw_snippet)

        # Verify LLM was called
        call_args = mock_llm.invoke.call_args
        assert call_args is not None

        # Check that the message contains the raw snippet
        messages = call_args[0][0]
        assert len(messages) == 1
        assert "Test snippet" in messages[0].content

    @patch('quantum_intel.llm')
    def test_clean_snippet_whitespace_handling(self, mock_llm):
        """Test that extra whitespace is stripped from result."""
        mock_response = Mock()
        mock_response.content = "  Cleaned content with whitespace  "
        mock_llm.invoke.return_value = mock_response

        result = clean_snippet("Original")

        # Whitespace should be stripped
        assert result == "Cleaned content with whitespace"


class TestEmailFormatting:
    """Integration tests for email formatting pipeline."""

    def test_newsletter_to_html_conversion(self):
        """Test complete newsletter markdown to HTML conversion."""
        newsletter_md = """# Quantum Intelligence Newsletter

## 🧠 Executive Summary
Recent breakthroughs in quantum networking.

## 📚 Latest Articles
1. [Article Title](https://example.com/article1)
2. [Another Article](https://example.com/article2)

---
Footer content"""

        result = convert_markdown_to_html(newsletter_md)

        # Verify structure
        assert "<html>" in result
        assert "<h2>🧠 Executive Summary</h2>" in result
        assert '<a href="https://example.com/article1">Article Title</a>' in result
        assert '<a href="https://example.com/article2">Another Article</a>' in result
        assert "Footer content" in result

    def test_html_output_valid_structure(self):
        """Test that HTML output has valid structure."""
        md_content = "Test"
        result = convert_markdown_to_html(md_content)

        # Check for proper HTML structure
        assert result.count("<html>") == 1
        assert result.count("</html>") == 1
        assert result.count("<body") == 1
        assert result.count("</body>") == 1

        # HTML should open before body
        assert result.index("<html>") < result.index("<body")
        assert result.index("</body>") < result.index("</html>")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
