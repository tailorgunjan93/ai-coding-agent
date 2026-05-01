"""
Unit tests for GroqAdapter - Cloud inference with free tier.
Tests use mocks — no Groq API key required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.main.agent.adapters.groq_adapter import GroqAdapter
from src.main.agent.interfaces.llm_interface import LLMProvider
from src.main.agent.exceptions import LLMError, RateLimitError, ContextLengthError


class TestGroqAdapter:

    @patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm")
    def test_default_model(self, mock_init):
        adapter = GroqAdapter()
        assert adapter._model == "llama-3.3-70b-versatile"

    @patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm")
    def test_provider_type(self, mock_init):
        adapter = GroqAdapter()
        assert adapter.get_provider() == LLMProvider.GROQ

    @patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm")
    def test_context_window(self, mock_init):
        adapter = GroqAdapter(model="mixtral-8x7b-32768")
        assert adapter.get_context_window() == 32768

    @patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm")
    def test_supports_function_calling(self, mock_init):
        adapter = GroqAdapter()
        assert adapter.supports_function_calling() is True

    @patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm")
    def test_no_vision_support(self, mock_init):
        adapter = GroqAdapter()
        assert adapter.supports_vision() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        with patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm"):
            adapter = GroqAdapter()
            mock_resp = MagicMock()
            mock_resp.content = "generated code"
            mock_resp.usage_metadata = {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
            mock_resp.id = "groq-123"
            adapter._llm = AsyncMock()
            adapter._llm.ainvoke = AsyncMock(return_value=mock_resp)

            result = await adapter.generate("test")
            assert result["content"] == "generated code"
            assert result["id"] == "groq-123"

    @pytest.mark.asyncio
    async def test_generate_rate_limit(self):
        with patch("src.main.agent.adapters.groq_adapter.GroqAdapter._init_llm"):
            adapter = GroqAdapter()
            adapter._llm = AsyncMock()
            adapter._llm.ainvoke = AsyncMock(side_effect=Exception("rate limit exceeded 429"))

            with pytest.raises(RateLimitError):
                await adapter.generate("test")
