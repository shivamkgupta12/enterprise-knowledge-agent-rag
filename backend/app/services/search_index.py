from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchableField,
    SimpleField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticSearch,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
)

from app.core.config import get_settings


def create_search_index() -> None:
    settings = get_settings()

    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_key),
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=False,
            vector_search_dimensions=settings.embedding_dimensions,
            vector_search_profile_name="rag-vector-profile",
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
            retrievable=True,
        ),
        SimpleField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="source_url",
            type=SearchFieldDataType.String,
            retrievable=True,
        ),
        SimpleField(
            name="page",
            type=SearchFieldDataType.Int32,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="doc_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="department",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="sensitivity",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SearchField(
            name="allowed_roles",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            retrievable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="rag-hnsw",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine",
                },
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="rag-vector-profile",
                algorithm_configuration_name="rag-hnsw",
            )
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="rag-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[
                        SemanticField(field_name="content"),
                    ],
                    keywords_fields=[
                        SemanticField(field_name="department"),
                        SemanticField(field_name="doc_type"),
                        SemanticField(field_name="source_file"),
                    ],
                ),
            )
        ]
    )

    index = SearchIndex(
        name=settings.azure_search_index,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    index_client.create_or_update_index(index)
    print(f"Index created or updated: {settings.azure_search_index}")


if __name__ == "__main__":
    create_search_index()