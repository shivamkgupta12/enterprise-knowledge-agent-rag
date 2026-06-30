import time
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from app.core.schemas import ChatRequest, ChatResponse, Citation, FeedbackRequest
from app.services.planner import QueryPlanner
from app.services.retriever import HybridRetriever
from app.services.answerer import AnswerGenerator
from app.services.feedback import save_feedback, get_feedback_summary
from app.services.telemetry import configure_telemetry


configure_telemetry()

app = FastAPI(
    title="Enterprise Knowledge Agent with Agentic RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


planner = QueryPlanner()
retriever = HybridRetriever()
answerer = AnswerGenerator()


def parse_roles(header_value: str | None) -> list[str]:
    if not header_value:
        return ["employee"]

    return [role.strip().lower() for role in header_value.split(",") if role.strip()]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "enterprise-knowledge-agent-rag",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    x_user_roles: str | None = Header(default="employee"),
) -> ChatResponse:
    start = time.perf_counter()

    user_roles = parse_roles(x_user_roles)

    plan = planner.plan(payload.question)

    combined_filters = payload.filters

    if not combined_filters.department:
        combined_filters.department = plan["filters"].get("department")

    if not combined_filters.doc_type:
        combined_filters.doc_type = plan["filters"].get("doc_type")

    retrieved_chunks = retriever.multi_search(
        subqueries=plan["subqueries"],
        user_roles=user_roles,
        filters=combined_filters,
        top_per_query=6,
        final_top=10,
    )

    answer_result = answerer.generate_answer(
        question=payload.question,
        chunks=retrieved_chunks,
    )

    source_map = answer_result.get("source_map", {})
    used_source_ids = answer_result.get("used_source_ids", [])

    citations: list[Citation] = []

    for source_id in used_source_ids:
        source = source_map.get(source_id)

        if not source:
            continue

        citations.append(
            Citation(
                id=source_id,
                title=source["title"],
                source_file=source["source_file"],
                source_url=source["source_url"],
                page=source["page"],
                content_preview=source["content"][:350],
            )
        )

    latency_ms = int((time.perf_counter() - start) * 1000)

    retrieval_debug = None

    if payload.debug:
        retrieval_debug = [
            {
                "id": chunk["id"],
                "title": chunk["title"],
                "source_file": chunk["source_file"],
                "page": chunk["page"],
                "score": chunk["score"],
                "matched_queries": chunk.get("matched_queries", []),
                "department": chunk["department"],
                "doc_type": chunk["doc_type"],
            }
            for chunk in retrieved_chunks
        ]

    return ChatResponse(
        answer=answer_result["answer"],
        citations=citations,
        rewritten_query=plan["rewritten_query"],
        subqueries=plan["subqueries"],
        latency_ms=latency_ms,
        retrieval_debug=retrieval_debug,
    )


@app.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict:
    feedback_id = save_feedback(payload)

    return {
        "status": "saved",
        "feedback_id": feedback_id,
    }


@app.get("/feedback/summary")
def feedback_summary() -> dict:
    return get_feedback_summary()
