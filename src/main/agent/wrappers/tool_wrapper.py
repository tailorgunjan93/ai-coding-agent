"""
Tool Wrapper - LangChain tool composition utilities.

This module provides utilities for composing LangChain tools with
retrieval, memory, and agent capabilities.
"""

from typing import Any, Sequence
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.agents import AgentExecutor, initialize_agent
from langchain.vectorstores import VectorStore
from langchain.embeddings import Embeddings


class ToolWrapper:
    """
    Composes LangChain tools with retrieval and memory capabilities.

    This wrapper provides factory methods for creating LangChain components:
    - RetrievalQA chains for RAG workflows
    - Conversation memory for context
    - Agent executors with tool sets

    Usage:
        wrapper = ToolWrapper()
        qa_chain = wrapper.attach_retrieval(llm, vectorstore)
        agent = wrapper.create_agent_with_tools(llm, [search_tool, file_tool])
    """

    def attach_retrieval(
        self,
        llm: Any,
        vectorstore: VectorStore,
        chain_type: str = "stuff",
        return_source_documents: bool = True,
        input_key: str = "question",
        output_key: str = "answer",
    ) -> RetrievalQA:
        """
        Create a retrieval-augmented QA chain.

        Args:
            llm: LangChain LLM instance (must implement invoke).
            vectorstore: Vector store with documents to retrieve from.
            chain_type: How to combine docs ("stuff", "map_reduce", "refine").
            return_source_documents: Whether to include source docs in response.
            input_key: Input key for the question.
            output_key: Output key for the answer.

        Returns:
            Configured RetrievalQA chain.
        """
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )

        return RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type=chain_type,
            return_source_documents=return_source_documents,
            input_key=input_key,
            output_key=output_key,
            chain_type_kwargs={
                "verbose": True,
            }
        )

    def create_vectorstore_retriever(
        self,
        vectorstore: VectorStore,
        search_type: str = "similarity",
        k: int = 4,
        filter_criteria: dict | None = None,
    ) -> Any:
        """
        Create a retriever from a vector store.

        Args:
            vectorstore: The vector store to create a retriever from.
            search_type: Type of search ("similarity", "mmr").
            k: Number of documents to retrieve.
            filter_criteria: Optional metadata filters.

        Returns:
            Configured retriever.
        """
        search_kwargs = {"k": k}
        if filter_criteria:
            search_kwargs["filter"] = filter_criteria

        return vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def attach_memory(
        self,
        llm: Any,
        chat_history_key: str = "chat_history",
        output_key: str = "answer",
        input_key: str = "question",
        return_messages: bool = True,
    ) -> tuple[Any, ConversationBufferMemory]:
        """
        Attach conversation memory to an LLM.

        This creates a new memory instance and returns it along with
        the LLM for use in an agent.

        Args:
            llm: LangChain LLM instance.
            chat_history_key: Key for storing chat history.
            output_key: Key for the output text.
            input_key: Key for the input text.
            return_messages: Whether to return message objects.

        Returns:
            Tuple of (llm_with_memory_attribute, memory_instance).
        """
        memory = ConversationBufferMemory(
            chat_memory_key=chat_history_key,
            return_messages=return_messages,
            output_key=output_key,
            input_key=input_key,
        )

        # Attach memory to llm via attribute
        llm.memory = memory

        return llm, memory

    def create_agent_with_tools(
        self,
        llm: Any,
        tools: Sequence[Tool],
        agent_type: str = "zero-shot-react-description",
        memory: ConversationBufferMemory | None = None,
        verbose: bool = True,
        max_iterations: int | None = None,
        max_execution_time: float | None = None,
    ) -> AgentExecutor:
        """
        Create a LangChain agent with configured tools and optional memory.

        Args:
            llm: LangChain LLM instance.
            tools: Sequence of LangChain Tool instances.
            agent_type: Type of agent to initialize.
            memory: Optional conversation memory.
            verbose: Whether to print agent thoughts/actions.
            max_iterations: Optional max iterations.
            max_execution_time: Optional max execution time in seconds.

        Returns:
            Configured AgentExecutor.
        """
        agent_kwargs: dict[str, Any] = {}
        if memory:
            agent_kwargs["memory"] = memory

        agent = initialize_agent(
            tools,
            llm,
            agent=agent_type,
            verbose=verbose,
            agent_kwargs=agent_kwargs,
        )

        executor_kwargs: dict[str, Any] = {"agent": agent, "tools": tools, "verbose": verbose}
        if max_iterations:
            executor_kwargs["max_iterations"] = max_iterations
        if max_execution_time:
            executor_kwargs["max_execution_time"] = max_execution_time

        return AgentExecutor.from_agent_and_tools(**executor_kwargs)

    def create_tools_from_functions(
        self,
        functions: list[dict[str, Any]],
        name: str | None = None,
        description: str | None = None,
    ) -> list[Tool]:
        """
        Create LangChain Tools from function definitions.

        Args:
            functions: List of function definition dicts with keys:
                - name: Function name
                - description: Function description
                - callable: The actual function
            name: Optional namespace for tool names.
            description: Optional overall description.

        Returns:
            List of Tool instances.
        """
        tools = []
        for func_def in functions:
            tool_name = func_def.get("name", "unnamed")
            if name:
                tool_name = f"{name}_{tool_name}"

            tool = Tool(
                name=tool_name,
                description=func_def.get("description", ""),
                func=func_def.get("callable"),
            )
            tools.append(tool)

        return tools

    def get_tool(self, name: str, tools: Sequence[Tool]) -> Tool | None:
        """
        Find a tool by name from a sequence of tools.

        Args:
            name: Tool name to find.
            tools: Sequence of tools to search.

        Returns:
            Tool if found, None otherwise.
        """
        for tool in tools:
            if tool.name == name:
                return tool
        return None

    def validate_tools(self, tools: Sequence[Tool]) -> list[str]:
        """
        Validate a list of tools and return any issues.

        Args:
            tools: Tools to validate.

        Returns:
            List of validation error messages (empty if all valid).
        """
        errors = []
        for tool in tools:
            if not tool.name:
                errors.append(f"Tool missing name")
            if not tool.description:
                errors.append(f"Tool '{tool.name}' missing description")
            if not callable(tool.func):
                errors.append(f"Tool '{tool.name}' has non-callable func")
        return errors
