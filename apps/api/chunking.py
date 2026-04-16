from __future__ import annotations


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    cleaned = text.strip()
    if not cleaned:
        return []

    if max_chars <= 0:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    step = max(1, max_chars - max(0, overlap))

    while start < length:
        end = min(start + max_chars, length)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start += step

    return chunks
