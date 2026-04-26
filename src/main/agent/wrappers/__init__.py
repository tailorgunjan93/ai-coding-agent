"""Wrappers package for AI Coding Agent."""

from src.main.agent.wrappers.llm_wrapper import LLMWrapper, CacheEntry
from src.main.agent.wrappers.tool_wrapper import (
    ToolInterface,
    BaseToolWrapper,
    RetrievalToolWrapper,
    MemoryToolWrapper,
    AgentToolWrapper,
    attach_retrieval,
    attach_memory,
    create_agent_tool,
    create_code_search_tool,
    create_documentation_tool
)
from src.main.agent.wrappers.prompt_wrapper import PromptWrapper, PromptTemplate, PromptMessage, PromptRole
from src.main.agent.wrappers.db_wrapper import DBWrapper, QueryTemplate, ConnectionPool

__all__ = [
    "LLMWrapper",
    "CacheEntry",
    "ToolInterface",
    "BaseToolWrapper",
    "RetrievalToolWrapper",
    "MemoryToolWrapper",
    "AgentToolWrapper",
    "attach_retrieval",
    "attach_memory",
    "create_agent_tool",
    "create_code_search_tool",
    "create_documentation_tool",
    "PromptWrapper",
    "PromptTemplate",
    "PromptMessage",
    "PromptRole",
    "DBWrapper",
    "QueryTemplate",
    "ConnectionPool",
]
