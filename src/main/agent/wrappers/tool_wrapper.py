"""
Tool Wrapper - LangChain tool composition utilities with Dependency Injection.

This module provides utilities for composing LangChain tools with
retrieval, memory, and agent capabilities using dependency injection patterns.
"""

from typing import Any, Sequence, Optional, Dict, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
import logging

from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool

from src.main.agent.wrappers.llm_wrapper import LLMWrapper

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolInterface(ABC):
    """Abstract interface for tool wrappers."""
    
    @abstractmethod
    def get_tool(self) -> BaseTool:
        """Get the wrapped LangChain tool."""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        pass


class BaseToolWrapper(Generic[T], ToolInterface):
    """Base class for tool wrappers with dependency injection."""
    
    def __init__(self, dependency: T):
        self._dependency = dependency
        self._logger = logger
    
    @property
    def dependency(self) -> T:
        """Get the injected dependency."""
        return self._dependency
    
    @abstractmethod
    def get_tool(self) -> BaseTool:
        """Get the wrapped LangChain tool."""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        pass


class RetrievalToolWrapper(BaseToolWrapper[BaseRetriever]):
    """Wrapper for creating retrieval-enhanced tools."""
    
    def __init__(
        self, 
        retriever: BaseRetriever,
        llm_wrapper: LLMWrapper,
        name: str = "retrieval_tool",
        description: str = "Useful for answering questions based on retrieved documents"
    ):
        super().__init__(retriever)
        self._llm_wrapper = llm_wrapper
        self._name = name
        self._description = description
        self._qa_chain = None
        self._setup_qa_chain()
    
    def _setup_qa_chain(self) -> None:
        """Setup the retrieval QA chain."""
        try:
            langchain_llm = self._llm_wrapper.get_langchain_llm()
            if langchain_llm:
                self._qa_chain = RetrievalQA.from_chain_type(
                    llm=langchain_llm,
                    chain_type="stuff",
                    retriever=self.dependency,
                    return_source_documents=True
                )
            else:
                # Fallback to basic retrieval if LangChain integration not available
                self._qa_chain = None
                logger.warning("LangChain integration not available for retrieval tool")
        except Exception as e:
            logger.error(f"Failed to setup QA chain: {e}")
            self._qa_chain = None
    
    def get_tool(self) -> BaseTool:
        """Get the retrieval tool."""
        if not self._qa_chain:
            # Return a basic tool that just uses the retriever directly
            return Tool(
                name=self._name,
                description=self._description,
                func=self._basic_retrieval_func,
                coroutine=self._async_basic_retrieval_func
            )
        
        return Tool(
            name=self._name,
            description=self._description,
            func=self._qa_chain_run,
            coroutine=self._async_qa_chain_run
        )
    
    def _basic_retrieval_func(self, query: str) -> str:
        """Basic retrieval function."""
        docs = self.dependency.get_relevant_documents(query)
        return "\n\n".join([doc.page_content for doc in docs])
    
    async def _async_basic_retrieval_func(self, query: str) -> str:
        """Async basic retrieval function."""
        # For now, call sync version - in production would use async retriever
        docs = self.dependency.get_relevant_documents(query)
        return "\n\n".join([doc.page_content for doc in docs])
    
    def _qa_chain_run(self, query: str) -> str:
        """Run the QA chain."""
        result = self._qa_chain({"query": query})
        return result["result"]
    
    async def _async_qa_chain_run(self, query: str) -> str:
        """Async run the QA chain."""
        result = await self._qa_chain.ainvoke({"query": query})
        return result["result"]
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """Execute the retrieval tool."""
        if self._qa_chain:
            result = await self._qa_chain.ainvoke({"query": query})
            return {
                "answer": result["result"],
                "source_documents": result.get("source_documents", [])
            }
        else:
            # Fallback to basic retrieval
            docs = self.dependency.get_relevant_documents(query)
            return {
                "answer": "\n\n".join([doc.page_content for doc in docs]),
                "source_documents": docs
            }


class MemoryToolWrapper(BaseToolWrapper[ConversationBufferMemory]):
    """Wrapper for creating memory-enhanced tools."""
    
    def __init__(
        self, 
        memory: ConversationBufferMemory,
        name: str = "memory_tool",
        description: str = "Useful for storing and retrieving conversation history"
    ):
        super().__init__(memory)
        self._name = name
        self._description = description
    
    def get_tool(self) -> BaseTool:
        """Get the memory tool."""
        return Tool(
            name=self._name,
            description=self._description,
            func=self._memory_func,
            coroutine=self._async_memory_func
        )
    
    def _memory_func(self, action: str) -> str:
        """Memory function for saving/loading."""
        if action.startswith("save:"):
            content = action[5:]  # Remove "save:" prefix
            self.dependency.save_context({"input": ""}, {"output": content})
            return f"Saved to memory: {content[:50]}..."
        elif action == "load":
            return self.dependency.load_memory_variables({})["history"]
        else:
            return f"Unknown memory action: {action}"
    
    async def _async_memory_func(self, action: str) -> str:
        """Async memory function."""
        return self._memory_func(action)
    
    async def execute(self, action: str) -> str:
        """Execute the memory tool."""
        return await self._async_memory_func(action)


class AgentToolWrapper:
    """Wrapper for creating LangChain agents with dependency injection."""
    
    def __init__(
        self,
        tools: Sequence[BaseTool],
        llm_wrapper: LLMWrapper,
        agent_prompt: Optional[str] = None
    ):
        self._tools = list(tools)
        self._llm_wrapper = llm_wrapper
        self._agent_executor = None
        self._setup_agent(agent_prompt)
    
    def _setup_agent(self, agent_prompt: Optional[str]) -> None:
        """Setup the LangChain agent."""
        try:
            langchain_llm = self._llm_wrapper.get_langchain_llm()
            if not langchain_llm:
                logger.warning("LangChain integration not available for agent")
                return
            
            # Use default ReAct agent prompt if none provided
            if agent_prompt is None:
                agent_prompt = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
            
            prompt = PromptTemplate.from_template(agent_prompt)
            agent = create_react_agent(langchain_llm, self._tools, prompt)
            self._agent_executor = AgentExecutor(
                agent=agent,
                tools=self._tools,
                verbose=True,
                handle_parsing_errors=True
            )
            logger.info("LangChain agent executor created successfully")
        except Exception as e:
            logger.error(f"Failed to setup agent: {e}")
            self._agent_executor = None
    
    def get_agent_executor(self) -> Optional[AgentExecutor]:
        """Get the agent executor."""
        return self._agent_executor
    
    async def run(self, input_text: str) -> Dict[str, Any]:
        """Run the agent with input text."""
        if not self._agent_executor:
            raise RuntimeError("Agent executor not initialized")
        
        return await self._agent_executor.ainvoke({"input": input_text})


def attach_retrieval(llm_wrapper: LLMWrapper, retriever: BaseRetriever) -> RetrievalToolWrapper:
    """
    Wrap retriever with LLM to create a retrieval-enhanced tool.
    
    Args:
        llm_wrapper: LLM wrapper with LangChain integration
        retriever: LangChain retriever
        
    Returns:
        RetrievalToolWrapper instance
    """
    return RetrievalToolWrapper(retriever, llm_wrapper)


def attach_memory(memory: ConversationBufferMemory) -> MemoryToolWrapper:
    """
    Create a memory-enhanced tool wrapper.
    
    Args:
        memory: ConversationBufferMemory instance
        
    Returns:
        MemoryToolWrapper instance
    """
    return MemoryToolWrapper(memory)


def create_agent_tool(
    tools: Sequence[BaseTool],
    llm_wrapper: LLMWrapper,
    agent_prompt: Optional[str] = None
) -> AgentToolWrapper:
    """
    Create an agent tool wrapper.
    
    Args:
        tools: List of LangChain tools
        llm_wrapper: LLM wrapper with LangChain integration
        agent_prompt: Optional custom agent prompt
        
    Returns:
        AgentToolWrapper instance
    """
    return AgentToolWrapper(tools, llm_wrapper, agent_prompt)


# Utility functions for common tool patterns
def create_code_search_tool(
    llm_wrapper: LLMWrapper,
    code_retriever: BaseRetriever
) -> RetrievalToolWrapper:
    """
    Create a code search tool.
    
    Args:
        llm_wrapper: LLM wrapper
        code_retriever: Retriever for code snippets
        
    Returns:
        RetrievalToolWrapper for code search
    """
    return RetrievalToolWrapper(
        retriever=code_retriever,
        llm_wrapper=llm_wrapper,
        name="code_search",
        description="Useful for searching and retrieving code snippets and documentation"
    )


def create_documentation_tool(
    llm_wrapper: LLMWrapper,
    doc_retriever: BaseRetriever
) -> RetrievalToolWrapper:
    """
    Create a documentation search tool.
    
    Args:
        llm_wrapper: LLM wrapper
        doc_retriever: Retriever for documentation
        
    Returns:
        RetrievalToolWrapper for documentation search
    """
    return RetrievalToolWrapper(
        retriever=doc_retriever,
        llm_wrapper=llm_wrapper,
        name="documentation_search",
        description="Useful for searching and retrieving technical documentation"
    )


__all__ = [
    "ToolInterface",
    "BaseToolWrapper",
    "RetrievalToolWrapper",
    "MemoryToolWrapper",
    "AgentToolWrapper",
    "attach_retrieval",
    "attach_memory",
    "create_agent_tool",
    "create_code_search_tool",
    "create_documentation_tool"
]
