import json
import time
from pathlib import Path

import pandas as pd
import requests


API_URL = "http://localhost:8000/chat"
QUESTIONS_FILE = Path(__file__).parent / "questions.jsonl"
OUTPUT_FILE = Path(__file__).parent / "eval_results.csv"


def load_questions() -> list[dict]:
    rows = []

    with QUESTIONS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def contains_expected_answer(answer: str, expected_terms: list[str]) -> bool:
    answer_lower = answer.lower()

    return all(term.lower() in answer_lower for term in expected_terms)


def source_recall(returned_sources: list[str], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0

    returned = set(returned_sources)
    expected = set(expected_sources)

    return len(returned.intersection(expected)) / len(expected)


def run_eval() -> None:
    questions = load_questions()
    results = []

    for item in questions:
        start = time.perf_counter()

        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "X-User-Roles": item.get("role", "employee"),
            },
            json={
                "question": item["question"],
                "filters": item.get("filters", {}),
                "debug": True,
            },
            timeout=120,
        )

        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            results.append(
                {
                    "question": item["question"],
                    "status": "failed",
                    "error": response.text,
                    "latency_ms": latency_ms,
                }
            )
            continue

        data = response.json()
        answer = data["answer"]

        returned_sources = [
            citation["source_file"]
            for citation in data.get("citations", [])
        ]

        recall = source_recall(
            returned_sources,
            item.get("expected_source_files", []),
        )

        answer_check = contains_expected_answer(
            answer,
            item.get("expected_answer_contains", []),
        )

        citation_count = len(data.get("citations", []))

        results.append(
            {
                "question": item["question"],
                "status": "passed",
                "answer_contains_expected_terms": answer_check,
                "source_recall": recall,
                "citation_count": citation_count,
                "latency_ms": latency_ms,
                "returned_sources": returned_sources,
                "answer": answer,
            }
        )

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)

    print(df)
    print(f"\nSaved results to {OUTPUT_FILE}")


if __name__ == "__main__":
    run_eval()