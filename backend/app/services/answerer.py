import re
from app.services.llm import AzureLLM


class AnswerGenerator:
    def __init__(self) -> None:
        self.llm = AzureLLM()

    def build_context(self, chunks: list[dict]) -> tuple[str, dict[str, dict]]:
        source_map: dict[str, dict] = {}
        context_blocks: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            source_id = f"S{index}"
            source_map[source_id] = chunk

            context_blocks.append(
                f"""
[{source_id}]
Title: {chunk["title"]}
Source file: {chunk["source_file"]}
Page: {chunk["page"]}
Department: {chunk["department"]}
Document type: {chunk["doc_type"]}

Content:
{chunk["content"]}
"""
            )

        return "\n\n".join(context_blocks), source_map

    def generate_answer(
        self,
        question: str,
        chunks: list[dict],
    ) -> dict:
        if not chunks:
            return {
                "answer": "I could not find relevant information in the available knowledge base.",
                "used_source_ids": [],
            }

        context, source_map = self.build_context(chunks)

        system_prompt = """
You are an enterprise knowledge assistant.

Answer rules:
- Use only the provided source context.
- Every factual claim must include a citation like [S1] or [S2].
- If the sources do not contain the answer, say you could not find it in the knowledge base.
- Do not invent policies, numbers, dates, names, or procedures.
- Be concise but helpful.
- If sources conflict, explain the conflict and cite both sources.
"""

        user_prompt = f"""
User question:
{question}

Source context:
{context}

Write the final answer with citations.
"""

        answer = self.llm.chat_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        used_source_ids = sorted(set(re.findall(r"\[(S\d+)\]", answer)))

        return {
            "answer": answer,
            "used_source_ids": used_source_ids,
            "source_map": source_map,
        }