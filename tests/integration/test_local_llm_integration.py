"""
Integration tests for Local LLM (Ollama).

These tests require a running Ollama server with at least one model pulled.
Skip with: pytest -m "not integration"

Setup:
    1. Install Ollama: https://ollama.ai/download
    2. Pull a model: ollama pull codellama:7b
    3. Start server: ollama serve
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# Mark all tests as integration
pytestmark = pytest.mark.integration


def ollama_available():
    """Check if Ollama is actually running for integration tests."""
    try:
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter
        return OllamaAdapter.is_server_running()
    except Exception:
        return False


@pytest.mark.skipif(not ollama_available(), reason="Ollama server not running")
class TestLocalLLMIntegration:
    """Integration tests that require a running Ollama server."""

    @pytest.mark.asyncio
    async def test_end_to_end_generation(self):
        """Test full generation cycle with real Ollama."""
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter

        adapter = OllamaAdapter()
        result = await adapter.generate("Write a Python function that adds two numbers. Only output the code.")
        assert result["content"]
        assert len(result["content"]) > 10
        assert result["model"]

    @pytest.mark.asyncio
    async def test_streaming_output(self):
        """Test streaming generation with real Ollama."""
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter

        adapter = OllamaAdapter()
        chunks = []
        async for chunk in adapter.generate_stream("Say hello in Python"):
            chunks.append(chunk)

        full_response = "".join(chunks)
        assert len(full_response) > 5

    def test_list_available_models(self):
        """Test listing models from running Ollama."""
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter

        adapter = OllamaAdapter()
        models = adapter.list_local_models()
        assert len(models) > 0  # At least one model must be pulled

    def test_server_info(self):
        """Test server info retrieval."""
        from src.main.agent.adapters.ollama_adapter import OllamaAdapter

        adapter = OllamaAdapter()
        info = adapter.get_server_info()
        assert info["running"] is True
        assert "version" in info


class TestFallbackChainIntegration:
    """Test the fallback chain (primary → local) using mocks."""

    @pytest.mark.asyncio
    async def test_fallback_to_local_on_cloud_failure(self):
        """When cloud provider fails, should fall back to local."""
        from src.main.agent.wrappers.llm_wrapper import LLMWrapper

        # Mock primary (cloud) that fails
        primary = MagicMock()
        primary.generate = AsyncMock(side_effect=Exception("API key invalid"))

        # Mock fallback (local) that succeeds
        fallback = MagicMock()
        fallback.generate = AsyncMock(return_value={
            "content": "local response",
            "usage": {},
            "model": "codellama:7b",
            "finish_reason": "stop",
            "id": None,
        })

        wrapper = LLMWrapper(primary=primary, fallback=fallback)
        result = await wrapper.generate("test prompt")

        assert result["content"] == "local response"
        assert wrapper.get_active_provider() == "fallback"

    @pytest.mark.asyncio
    async def test_no_fallback_raises_original_error(self):
        """When no fallback configured, should raise original error."""
        from src.main.agent.wrappers.llm_wrapper import LLMWrapper

        primary = MagicMock()
        primary.generate = AsyncMock(side_effect=Exception("API failed"))

        wrapper = LLMWrapper(primary=primary, fallback=None)

        with pytest.raises(Exception, match="API failed"):
            await wrapper.generate("test")

    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback_triggered(self):
        """When primary succeeds, fallback should not be called."""
        from src.main.agent.wrappers.llm_wrapper import LLMWrapper

        primary = MagicMock()
        primary.generate = AsyncMock(return_value={
            "content": "cloud response",
            "usage": {},
            "model": "gpt-4",
            "finish_reason": "stop",
            "id": None,
        })

        fallback = MagicMock()
        fallback.generate = AsyncMock()

        wrapper = LLMWrapper(primary=primary, fallback=fallback)
        result = await wrapper.generate("test")

        assert result["content"] == "cloud response"
        assert wrapper.get_active_provider() == "primary"
        fallback.generate.assert_not_called()
