import base64
from pathlib import Path

import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from app.core.config import get_settings
from app.services.document_loader import load_document
from app.services.chunker import chunk_text
from app.services.llm import AzureLLM
from app.services.search_index import create_search_index


def safe_id(value: str) -> str:
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def parse_roles(value: str) -> list[str]:
    if not isinstance(value, str):
        return ["employee"]

    return [role.strip().lower() for role in value.split(",") if role.strip()]


def batch_list(items: list, batch_size: int) -> list[list]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def load_metadata(metadata_path: Path) -> dict[str, dict]:
    if not metadata_path.exists():
        return {}

    df = pd.read_csv(metadata_path)
    records = {}

    for _, row in df.iterrows():
        records[row["filename"]] = {
            "title": row.get("title", row["filename"]),
            "department": str(row.get("department", "general")).lower(),
            "doc_type": str(row.get("doc_type", "document")).lower(),
            "sensitivity": str(row.get("sensitivity", "internal")).lower(),
            "allowed_roles": parse_roles(row.get("allowed_roles", "employee")),
        }

    return records


def ingest_documents(
    raw_data_dir: str = "../data/raw",
    metadata_file: str = "../data/metadata.csv",
) -> None:
    settings = get_settings()

    create_search_index()

    llm = AzureLLM()

    search_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index,
        credential=AzureKeyCredential(settings.azure_search_key),
    )

    raw_path = Path(raw_data_dir).resolve()
    metadata_path = Path(metadata_file).resolve()
    metadata = load_metadata(metadata_path)

    supported_extensions = {".pdf", ".docx", ".txt", ".md", ".csv"}

    files = [
        file
        for file in raw_path.iterdir()
        if file.is_file() and file.suffix.lower() in supported_extensions
    ]

    print(f"Found {len(files)} files to ingest.")

    documents_to_upload: list[dict] = []

    for file in files:
        file_metadata = metadata.get(
            file.name,
            {
                "title": file.stem,
                "department": "general",
                "doc_type": "document",
                "sensitivity": "internal",
                "allowed_roles": ["employee", "admin"],
            },
        )

        pages = load_document(file)

        chunk_counter = 0

        for page in pages:
            chunks = chunk_text(page["text"])

            for chunk in chunks:
                chunk_counter += 1

                doc_id = safe_id(
                    f"{file.name}-page-{page['page']}-chunk-{chunk_counter}"
                )

                documents_to_upload.append(
                    {
                        "id": doc_id,
                        "content": chunk,
                        "content_vector": [],
                        "title": file_metadata["title"],
                        "source_file": file.name,
                        "source_url": f"{file.name}#page={page['page']}",
                        "page": page["page"],
                        "chunk_index": chunk_counter,
                        "doc_type": file_metadata["doc_type"],
                        "department": file_metadata["department"],
                        "sensitivity": file_metadata["sensitivity"],
                        "allowed_roles": file_metadata["allowed_roles"],
                    }
                )

    print(f"Generated {len(documents_to_upload)} chunks.")

    texts = [doc["content"] for doc in documents_to_upload]

    batch_size = 16
    embedding_batches = batch_list(texts, batch_size)
    all_embeddings: list[list[float]] = []

    for i, batch in enumerate(embedding_batches, start=1):
        print(f"Embedding batch {i}/{len(embedding_batches)}")
        embeddings = llm.embed_texts(batch)
        all_embeddings.extend(embeddings)

    if len(all_embeddings) != len(documents_to_upload):
        raise RuntimeError("Embedding count mismatch.")

    for doc, embedding in zip(documents_to_upload, all_embeddings):
        doc["content_vector"] = embedding

    upload_batches = batch_list(documents_to_upload, 500)

    for i, batch in enumerate(upload_batches, start=1):
        result = search_client.upload_documents(documents=batch)
        failed = [r for r in result if not r.succeeded]

        if failed:
            raise RuntimeError(f"Failed upload batch {i}: {failed}")

        print(f"Uploaded batch {i}/{len(upload_batches)}")

    print("Ingestion completed successfully.")


if __name__ == "__main__":
    ingest_documents()
