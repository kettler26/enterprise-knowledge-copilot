from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from analytics_duckdb import append_run_analytics
from db import log_run
from llm import OLLAMA_MODEL, generate_answer
from obs_langfuse import trace_chat_turn
from rag import build_citations
from schemas import ChatRequest, ChatResponse, Citation


class GraphState(TypedDict, total=False):
    message: str
    context: str | None
    workspace_id: str
    trace_id: str
    citations: list[dict]
    prompt: str
    answer: str


def _build_prompt(message: str, citations: list[Citation]) -> str:
    prompt_parts = [
        "You are a SaaS support copilot.",
        "Return concise and helpful answers.",
        "If context is missing, say what is needed.",
    ]
    if citations:
        citation_context = "\n\n".join(
            [f"Source: {c.source}\nExcerpt: {c.snippet}" for c in citations]
        )
        prompt_parts.append(f"Retrieved context:\n{citation_context}")
    prompt_parts.append(f"User message:\n{message}")
    return "\n\n".join(prompt_parts)


async def node_retrieve(state: GraphState) -> dict:
    cites = build_citations(
        message=state["message"],
        context=state.get("context"),
        workspace_id=state["workspace_id"],
    )
    return {"citations": [c.model_dump() for c in cites]}


async def node_generate(state: GraphState) -> dict:
    citations = [Citation.model_validate(item) for item in state.get("citations", [])]
    prompt = _build_prompt(state["message"], citations)
    answer = await generate_answer(prompt)
    return {"prompt": prompt, "answer": answer}


async def node_persist(state: GraphState) -> dict:
    citations = [Citation.model_validate(item) for item in state.get("citations", [])]
    log_run(
        trace_id=state["trace_id"],
        workspace_id=state["workspace_id"],
        message=state["message"],
        answer=state.get("answer", ""),
        model=OLLAMA_MODEL,
        grounded=bool(citations),
        citation_count=len(citations),
    )
    append_run_analytics(
        trace_id=state["trace_id"],
        workspace_id=state["workspace_id"],
        message=state["message"],
        answer=state.get("answer", ""),
        model=OLLAMA_MODEL,
        grounded=bool(citations),
        citation_count=len(citations),
    )
    trace_chat_turn(
        trace_id=state["trace_id"],
        workspace_id=state["workspace_id"],
        message=state["message"],
        prompt=state.get("prompt", ""),
        answer=state.get("answer", ""),
        model=OLLAMA_MODEL,
        citation_count=len(citations),
    )
    return {}


def _build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("generate", node_generate)
    graph.add_node("persist", node_persist)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


_CHAT_GRAPH = _build_graph()


async def run_chat_workflow(request: ChatRequest) -> ChatResponse:
    initial: GraphState = {
        "message": request.message,
        "context": request.context,
        "workspace_id": request.workspace_id,
        "trace_id": str(uuid4()),
    }
    final = await _CHAT_GRAPH.ainvoke(initial)
    citations = [Citation.model_validate(item) for item in final.get("citations", [])]

    return ChatResponse(
        answer=final.get("answer", ""),
        model=OLLAMA_MODEL,
        grounded=bool(citations),
        citations=citations,
        trace_id=final["trace_id"],
    )
