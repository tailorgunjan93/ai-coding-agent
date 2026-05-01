import pytest
import asyncio
from unittest.mock import MagicMock
from src.main.agent.wrappers.llm_wrapper import LLMWrapper
from src.main.agent.interfaces.llm_interface import LLMInterface, LLMResponse

class MockLLM(LLMInterface):
    def __init__(self):
        self.call_count = 0

    def get_llm(self):
        return None

    async def generate(self, prompt, **kwargs):
        self.call_count += 1
        return {
            "content": f"Response to: {prompt}",
            "usage": {"total_tokens": 10},
            "model": "mock-model"
        }

@pytest.mark.asyncio
async def test_llm_wrapper_caching():
    mock_llm = MockLLM()
    wrapper = LLMWrapper(mock_llm)
    
    # First call
    resp1 = await wrapper.generate("Hello")
    assert resp1["content"] == "Response to: Hello"
    assert mock_llm.call_count == 1
    
    # Second call (should be cached)
    resp2 = await wrapper.generate("Hello")
    assert resp2["content"] == "Response to: Hello"
    assert mock_llm.call_count == 1
    
    # Different prompt
    resp3 = await wrapper.generate("World")
    assert resp3["content"] == "Response to: World"
    assert mock_llm.call_count == 2

@pytest.mark.asyncio
async def test_llm_wrapper_rate_limit():
    mock_llm = MockLLM()
    # Set rpm to 1 for easy testing
    wrapper = LLMWrapper(mock_llm, rate_limit_rpm=1)
    
    await wrapper.generate("Request 1")
    
    with pytest.raises(Exception, match="Rate limit of 1 rpm exceeded"):
        await wrapper.generate("Request 2")
