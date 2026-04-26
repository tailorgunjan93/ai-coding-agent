"""
Tool Wrapper - LangChain tool composition utilities.

This module provides utilities for composing LangChain tools with
retrieval, memory, and agent capabilities.
"""

from typing import Any, Sequence
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory

def attach_retrieval(llm, retriever):
    """
    Wrap LLM with retrieval QA chain
    """
    return RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

def attach_memory(llm):
    """
    Wrap LLM with conversational memory
    """
    memory = ConversationBufferMemory()
    llm.memory = memory
    return llm
