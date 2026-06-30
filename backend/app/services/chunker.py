import tiktoken


def chunk_text(
    text: str,
    max_tokens: int = 450,
    overlap_tokens: int = 80,
) -> list[str]:
    """
    Token-aware chunking with overlap.
    Good portfolio point:
    - avoids blindly splitting by characters
    - preserves context between chunks
    """

    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunk = encoding.decode(chunk_tokens).strip()

        if chunk:
            chunks.append(chunk)

        start += max_tokens - overlap_tokens

    return chunks
