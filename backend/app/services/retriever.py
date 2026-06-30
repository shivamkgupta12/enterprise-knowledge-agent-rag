from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from app.core.config import get_settings
from app.core.schemas import ChatFilters
from app.services.llm import AzureLLM


def escape_odata(value: str) -> str:
    return value.replace("'", "''")


def build_acl_filter(user_roles: list[str]) -> str:
    """
    Azure AI Search OData filter for collection field allowed_roles.

    Example:
    allowed_roles/any(r: r eq 'employee' or r eq 'admin' or r eq 'all')
    """

    normalized_roles = {role.strip().lower() for role in user_roles if role.strip()}
    normalized_roles.add("all")

    role_clauses = [f"r eq '{escape_odata(role)}'" for role in sorted(normalized_roles)]

    return f"allowed_roles/any(r: {' or '.join(role_clauses)})"


def build_metadata_filter(filters: ChatFilters) -> list[str]:
    clauses: list[str] = []

    if filters.department:
        clauses.append(f"department eq '{escape_odata(filters.department.lower())}'")

    if filters.doc_type:
        clauses.append(f"doc_type eq '{escape_odata(filters.doc_type.lower())}'")

    if filters.sensitivity:
        clauses.append(f"sensitivity eq '{escape_odata(filters.sensitivity.lower())}'")

    return clauses


def combine_filters(*filter_groups: list[str] | str | None) -> str | None:
    clauses: list[str] = []

    for group in filter_groups:
        if not group:
            continue

        if isinstance(group, str):
            clauses.append(group)
        else:
            clauses.extend(group)

    if not clauses:
        return None

    return " and ".join(f"({clause})" for clause in clauses)


class HybridRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = AzureLLM()

        self.search_client = SearchClient(
            endpoint=self.settings.azure_search_endpoint,
            index_name=self.settings.azure_search_index,
            credential=AzureKeyCredential(self.settings.azure_search_key),
        )

    def search(
        self,
        query: str,
        user_roles: list[str],
        filters: ChatFilters,
        top: int = 8,
    ) -> list[dict]:
        query_vector = self.llm.embed_texts([query])[0]

        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=50,
            fields="content_vector",
        )

        acl_filter = build_acl_filter(user_roles)
        metadata_filter = build_metadata_filter(filters)
        final_filter = combine_filters(acl_filter, metadata_filter)

        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=final_filter,
            top=top,
            query_type="semantic",
            semantic_configuration_name="rag-semantic-config",
            query_caption="extractive",
            select=[
                "id",
                "content",
                "title",
                "source_file",
                "source_url",
                "page",
                "chunk_index",
                "doc_type",
                "department",
                "sensitivity",
                "allowed_roles",
            ],
        )

        output: list[dict] = []

        for result in results:
            score = (
                result.get("@search.reranker_score") or result.get("@search.score") or 0
            )

            output.append(
                {
                    "id": result["id"],
                    "content": result["content"],
                    "title": result.get("title", ""),
                    "source_file": result.get("source_file", ""),
                    "source_url": result.get("source_url", ""),
                    "page": result.get("page", 1),
                    "chunk_index": result.get("chunk_index", 0),
                    "doc_type": result.get("doc_type", ""),
                    "department": result.get("department", ""),
                    "sensitivity": result.get("sensitivity", ""),
                    "allowed_roles": result.get("allowed_roles", []),
                    "score": float(score),
                    "matched_query": query,
                }
            )

        return output

    def multi_search(
        self,
        subqueries: list[str],
        user_roles: list[str],
        filters: ChatFilters,
        top_per_query: int = 6,
        final_top: int = 10,
    ) -> list[dict]:
        merged: dict[str, dict] = {}

        for subquery in subqueries:
            results = self.search(
                query=subquery,
                user_roles=user_roles,
                filters=filters,
                top=top_per_query,
            )

            for result in results:
                doc_id = result["id"]

                if doc_id not in merged:
                    result["matched_queries"] = [subquery]
                    merged[doc_id] = result
                else:
                    merged[doc_id]["score"] = max(
                        merged[doc_id]["score"],
                        result["score"],
                    )
                    merged[doc_id]["matched_queries"].append(subquery)

        ranked = sorted(
            merged.values(),
            key=lambda item: item["score"],
            reverse=True,
        )

        return ranked[:final_top]
