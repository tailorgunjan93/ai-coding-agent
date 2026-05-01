"""
Unit tests for BedrockAdapter - AWS Bedrock enterprise inference.
Tests use mocks — no AWS credentials required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.main.agent.adapters.bedrock_adapter import BedrockAdapter
from src.main.agent.interfaces.llm_interface import LLMProvider
from src.main.agent.exceptions import LLMError, RateLimitError


class TestBedrockAdapter:

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_default_model(self, mock_init):
        adapter = BedrockAdapter()
        assert adapter._model == "anthropic.claude-3-sonnet-20240229-v1:0"

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_provider_type(self, mock_init):
        adapter = BedrockAdapter()
        assert adapter.get_provider() == LLMProvider.AWS_BEDROCK

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_context_window(self, mock_init):
        adapter = BedrockAdapter(model="anthropic.claude-3-sonnet-20240229-v1:0")
        assert adapter.get_context_window() == 200000

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_supports_function_calling_claude(self, mock_init):
        adapter = BedrockAdapter(model="anthropic.claude-3-sonnet-20240229-v1:0")
        assert adapter.supports_function_calling() is True

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_supports_vision_claude3(self, mock_init):
        adapter = BedrockAdapter(model="anthropic.claude-3-sonnet-20240229-v1:0")
        assert adapter.supports_vision() is True

    @patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm")
    def test_no_vision_titan(self, mock_init):
        adapter = BedrockAdapter(model="amazon.titan-text-express-v1")
        assert adapter.supports_vision() is False

    def test_has_credentials_with_env(self):
        with patch.dict("os.environ", {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "secret"}):
            assert BedrockAdapter.has_credentials() is True

    def test_no_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            assert BedrockAdapter.has_credentials() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        with patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm"):
            adapter = BedrockAdapter()
            mock_resp = MagicMock()
            mock_resp.content = "bedrock response"
            mock_resp.usage_metadata = {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
            mock_resp.id = "br-789"
            adapter._llm = AsyncMock()
            adapter._llm.ainvoke = AsyncMock(return_value=mock_resp)

            result = await adapter.generate("test")
            assert result["content"] == "bedrock response"

    @pytest.mark.asyncio
    async def test_generate_throttle_error(self):
        with patch("src.main.agent.adapters.bedrock_adapter.BedrockAdapter._init_llm"):
            adapter = BedrockAdapter()
            adapter._llm = AsyncMock()
            adapter._llm.ainvoke = AsyncMock(side_effect=Exception("throttling exception"))

            with pytest.raises(RateLimitError):
                await adapter.generate("test")
