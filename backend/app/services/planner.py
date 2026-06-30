from app.services.llm import AzureLLM


ALLOWED_DEPARTMENTS = {"hr", "finance", "legal", "product", "engineering", "general"}
ALLOWED_DOC_TYPES = {"policy", "benefits", "contract", "invoice", "faq", "meeting_notes", "document"}


class QueryPlanner:
    def __init__(self) -> None:
        self.llm = AzureLLM()

    def plan(self, question: str, conversation_summary: str = "") -> dict:
        system_prompt = """
You are an enterprise search query planner.

Your job:
1. Rewrite the user's question into a precise enterprise knowledge-base search query.
2. Break complex questions into 1 to 3 focused subqueries.
3. Suggest filters only when strongly implied.

Return strict JSON with this schema:
{
  "rewritten_query": "...",
  "subqueries": ["...", "..."],
  "filters": {
    "department": null,
    "doc_type": null
  }
}

Rules:
- Do not invent facts.
- Do not answer the question.
- Do not create more than 3 subqueries.
- Filters must be null unless clearly implied.
"""

        user_prompt = f"""
Conversation summary:
{conversation_summary}

User question:
{question}
"""

        result = self.llm.chat_json(system_prompt, user_prompt)

        rewritten_query = result.get("rewritten_query") or question
        subqueries = result.get("subqueries") or [rewritten_query]

        if not isinstance(subqueries, list):
            subqueries = [rewritten_query]

        subqueries = [str(q).strip() for q in subqueries if str(q).strip()]
        subqueries = subqueries[:3]

        raw_filters = result.get("filters") or {}

        department = raw_filters.get("department")
        doc_type = raw_filters.get("doc_type")

        if department not in ALLOWED_DEPARTMENTS:
            department = None

        if doc_type not in ALLOWED_DOC_TYPES:
            doc_type = None

        return {
            "rewritten_query": rewritten_query,
            "subqueries": subqueries,
            "filters": {
                "department": department,
                "doc_type": doc_type,
            },
        }