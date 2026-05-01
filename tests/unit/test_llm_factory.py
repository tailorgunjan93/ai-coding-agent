"""
Unit tests for LLM Factory - Smart provider auto-detection.
Tests use mocks — no API keys or services required.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.main.agent.adapters.llm_factory import (
    create_llm_adapter,
    detect_available_providers,
    get_provider_status,
)
from src.main.agent.interfaces.llm_interface import LLMProvider
from src.main.agent.exceptions import ConfigurationError


class TestDetectProviders:

    def test_detect_openai(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert LLMProvider.OPENAI in providers

    def test_detect_groq(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert LLMProvider.GROQ in providers

    def test_detect_google(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "AIza-test"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert LLMProvider.GOOGLE in providers

    def test_detect_aws_needs_both_keys(self):
        # Only access key — not enough
        with patch.dict("os.environ", {"AWS_ACCESS_KEY_ID": "AKIA"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert LLMProvider.AWS_BEDROCK not in providers

        # Both keys — should work
        with patch.dict("os.environ", {"AWS_ACCESS_KEY_ID": "AKIA", "AWS_SECRET_ACCESS_KEY": "secret"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert LLMProvider.AWS_BEDROCK in providers

    def test_detect_ollama_running(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = True
                providers = detect_available_providers()
                assert LLMProvider.LOCAL in providers

    def test_detect_nothing(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert len(providers) == 0

    def test_priority_order(self):
        """OpenAI should come before Groq in detection order."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk", "GROQ_API_KEY": "gsk"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                providers = detect_available_providers()
                assert providers.index(LLMProvider.OPENAI) < providers.index(LLMProvider.GROQ)


class TestCreateAdapter:

    @patch("src.main.agent.adapters.llm_factory.OpenAIAdapter")
    def test_force_openai(self, mock_adapter):
        mock_adapter.DEFAULT_MODEL = "gpt-4"
        mock_adapter.return_value = MagicMock()
        adapter = create_llm_adapter(provider="openai")
        mock_adapter.assert_called_once()

    @patch("src.main.agent.adapters.llm_factory.GroqAdapter")
    def test_force_groq(self, mock_adapter):
        mock_adapter.DEFAULT_MODEL = "llama-3.3-70b-versatile"
        mock_adapter.return_value = MagicMock()
        adapter = create_llm_adapter(provider="groq")
        mock_adapter.assert_called_once()

    @patch("src.main.agent.adapters.llm_factory.GoogleAdapter")
    def test_force_google(self, mock_adapter):
        mock_adapter.DEFAULT_MODEL = "gemini-2.0-flash"
        mock_adapter.return_value = MagicMock()
        adapter = create_llm_adapter(provider="google")
        mock_adapter.assert_called_once()

    def test_unknown_provider_raises(self):
        with pytest.raises(ConfigurationError, match="Unknown provider"):
            create_llm_adapter(provider="nonexistent")

    def test_no_providers_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                with pytest.raises(ConfigurationError, match="No LLM provider available"):
                    create_llm_adapter(provider=None, auto_detect=True)


class TestProviderStatus:

    def test_status_structure(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk"}, clear=True):
            with patch("src.main.agent.adapters.llm_factory.OllamaAdapter") as mock:
                mock.is_server_running.return_value = False
                status = get_provider_status()
                assert "openai" in status
                assert "groq" in status
                assert "google" in status
                assert "local" in status
                assert status["openai"]["available"] is True
                assert status["groq"]["available"] is False
