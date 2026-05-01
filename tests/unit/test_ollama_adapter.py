"""
Unit tests for OllamaAdapter - Local LLM provider.

Tests use mocks — no Ollama server required to run these.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.main.agent.adapters.ollama_adapter import OllamaAdapter
from src.main.agent.interfaces.llm_interface import LLMProvider
from src.main.agent.exceptions import LLMError, ContextLengthError


class TestOllamaAdapterInit:
    """Test adapter initialization and model selection."""

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_default_model(self, mock_init):
        """Should use deepseek-coder-v2:16b as default when no auto-select."""
        adapter = OllamaAdapter(model="codellama:7b")
        assert adapter._model == "codellama:7b"

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_custom_base_url(self, mock_init):
        """Should accept custom Ollama server URL."""
        adapter = OllamaAdapter(model="test", base_url="http://remote:11434")
        assert adapter._base_url == "http://remote:11434"

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_provider_type(self, mock_init):
        """Should return LOCAL provider type."""
        adapter = OllamaAdapter(model="test")
        assert adapter.get_provider() == LLMProvider.LOCAL

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_context_window_known_model(self, mock_init):
        """Should return correct context window for known models."""
        adapter = OllamaAdapter(model="deepseek-coder-v2:16b")
        assert adapter.get_context_window() == 128000

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_context_window_unknown_model(self, mock_init):
        """Should return conservative default for unknown models."""
        adapter = OllamaAdapter(model="custom-model:latest")
        assert adapter.get_context_window() == 4096

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_supports_function_calling(self, mock_init):
        """Should detect function calling support per model."""
        adapter_llama = OllamaAdapter(model="llama3.1:8b")
        assert adapter_llama.supports_function_calling() is True

        adapter_code = OllamaAdapter(model="codellama:7b")
        assert adapter_code.supports_function_calling() is False

    @patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm")
    def test_supports_vision(self, mock_init):
        """Should detect vision support per model."""
        adapter_llava = OllamaAdapter(model="llava:7b")
        assert adapter_llava.supports_vision() is True

        adapter_code = OllamaAdapter(model="codellama:7b")
        assert adapter_code.supports_vision() is False


class TestOllamaServerDetection:
    """Test Ollama server health checks."""

    @patch("src.main.agent.adapters.ollama_adapter.httpx.get")
    def test_server_running(self, mock_get):
        """Should detect running Ollama server."""
        mock_get.return_value = MagicMock(status_code=200)
        assert OllamaAdapter.is_server_running() is True

    @patch("src.main.agent.adapters.ollama_adapter.httpx.get")
    def test_server_not_running(self, mock_get):
        """Should detect when Ollama server is not running."""
        import httpx
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        assert OllamaAdapter.is_server_running() is False

    @patch("src.main.agent.adapters.ollama_adapter.httpx.get")
    def test_list_models(self, mock_get):
        """Should list available local models."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "models": [
                    {"name": "codellama:7b"},
                    {"name": "deepseek-coder-v2:16b"},
                ]
            },
        )
        adapter = OllamaAdapter.__new__(OllamaAdapter)
        adapter._base_url = "http://localhost:11434"
        models = adapter.list_local_models()
        assert "codellama:7b" in models
        assert "deepseek-coder-v2:16b" in models


class TestOllamaGeneration:
    """Test generation methods with mocked LLM."""

    @pytest.fixture
    def adapter(self):
        with patch("src.main.agent.adapters.ollama_adapter.OllamaAdapter._init_llm"):
            a = OllamaAdapter(model="codellama:7b")
            a._llm = AsyncMock()
            return a

    @pytest.mark.asyncio
    async def test_generate_success(self, adapter):
        """Should generate text successfully."""
        mock_response = MagicMock()
        mock_response.content = "def hello(): print('world')"
        mock_response.response_metadata = {
            "prompt_eval_count": 10,
            "eval_count": 20,
        }
        adapter._llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await adapter.generate("Write a hello function")
        assert result["content"] == "def hello(): print('world')"
        assert result["model"] == "codellama:7b"
        assert result["usage"]["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_generate_context_length_error(self, adapter):
        """Should raise ContextLengthError for too-long prompts."""
        adapter._llm.ainvoke = AsyncMock(
            side_effect=Exception("context length exceeded, too long")
        )
        with pytest.raises(ContextLengthError):
            await adapter.generate("x" * 100000)

    @pytest.mark.asyncio
    async def test_generate_generic_error(self, adapter):
        """Should raise LLMError for generic failures."""
        adapter._llm.ainvoke = AsyncMock(
            side_effect=Exception("connection refused")
        )
        with pytest.raises(LLMError, match="Ollama generation failed"):
            await adapter.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_messages(self, adapter):
        """Should handle multi-turn message generation."""
        mock_response = MagicMock()
        mock_response.content = "Here is the fixed code..."
        mock_response.response_metadata = {}
        adapter._llm.ainvoke = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a coding assistant"},
            {"role": "user", "content": "Fix this bug"},
        ]
        result = await adapter.generate_with_messages(messages)
        assert result["content"] == "Here is the fixed code..."
