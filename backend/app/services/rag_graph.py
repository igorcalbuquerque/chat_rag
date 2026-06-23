"""RAG pipeline orchestrated with LangGraph.

The graph wires four nodes in sequence:

    retriever_node -> context_builder_node -> llm_node -> response_formatter_node

Using LangGraph (instead of a plain LangChain chain) makes the flow explicit
and easy to extend with validation, retry or conditional branching nodes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.services.history import get_history
from app.services.llm import get_llm
from app.services.retriever import retrieve

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions strictly based on the "
    "provided document context. If the answer is not in the context, say you "
    "could not find it in the documents. Always answer in the language of the "
    "question."
)


class RAGState(TypedDict, total=False):
    """State threaded through the LangGraph nodes."""

    question: str
    session_id: str
    top_k: int
    history: list[dict]
    retrieved_chunks: list[dict]
    messages: list  # LangChain message objects sent to the LLM
    answer: str
    sources: list[dict]


# --- Nodes ---
def retriever_node(state: RAGState) -> RAGState:
    """Semantic search in Redis to fetch the most relevant chunks."""
    chunks = retrieve(state["question"], state.get("top_k"))
    return {"retrieved_chunks": chunks}


def context_builder_node(state: RAGState) -> RAGState:
    """Assemble the prompt from retrieved context and conversation history."""
    history = get_history(state["session_id"])

    context = "\n\n".join(
        f"[{i + 1}] (source: {c['source']})\n{c['chunk']}"
        for i, c in enumerate(state.get("retrieved_chunks", []))
    )
    context = context or "No relevant context was found."

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    user_prompt = (
        f"Context from documents:\n{context}\n\n"
        f"Question: {state['question']}\n\n"
        "Answer using only the context above."
    )
    messages.append(HumanMessage(content=user_prompt))

    return {"history": history, "messages": messages}


def llm_node(state: RAGState) -> RAGState:
    """Call the configured chat model with the assembled prompt."""
    response = get_llm().invoke(state["messages"])
    answer = response.content if hasattr(response, "content") else str(response)
    return {"answer": answer}


def response_formatter_node(state: RAGState) -> RAGState:
    """Shape the final response, including the sources used."""
    sources = [
        {
            "chunk": c["chunk"],
            "source": c["source"],
            "score": c["score"],
            "chunk_index": c.get("chunk_index"),
        }
        for c in state.get("retrieved_chunks", [])
    ]
    return {"sources": sources}


# --- Graph assembly ---
@lru_cache
def build_graph():
    """Compile and cache the RAG state graph."""
    graph = StateGraph(RAGState)
    graph.add_node("retriever", retriever_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("llm", llm_node)
    graph.add_node("response_formatter", response_formatter_node)

    graph.add_edge(START, "retriever")
    graph.add_edge("retriever", "context_builder")
    graph.add_edge("context_builder", "llm")
    graph.add_edge("llm", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()


def run_rag(question: str, session_id: str, top_k: int | None = None) -> dict:
    """Execute the full RAG graph and return ``answer`` + ``sources``."""
    settings = get_settings()
    state: RAGState = {
        "question": question,
        "session_id": session_id,
        "top_k": top_k or settings.top_k,
    }
    result = build_graph().invoke(state)
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "session_id": session_id,
    }


def stream_rag(
    question: str, session_id: str, top_k: int | None = None
) -> tuple[Iterator[str], list[dict]]:
    """Run retrieval + context building, then stream LLM tokens.

    Returns a ``(token_iterator, sources)`` tuple. Streaming the LLM token by
    token is handled outside the compiled graph because token-level streaming
    maps more naturally to the model's ``.stream()`` interface than to graph
    state updates.
    """
    settings = get_settings()
    base: RAGState = {
        "question": question,
        "session_id": session_id,
        "top_k": top_k or settings.top_k,
    }
    state = {**base, **retriever_node(base)}
    state = {**state, **context_builder_node(state)}
    sources = response_formatter_node(state)["sources"]

    def token_iterator() -> Iterator[str]:
        for piece in get_llm().stream(state["messages"]):
            content = piece.content if hasattr(piece, "content") else str(piece)
            if content:
                yield content

    return token_iterator(), sources
