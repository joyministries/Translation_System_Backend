import re


CHUNK_SIZE = 4500


def chunk_text(text: str) -> list[str]:
    if not text:
        return []

    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    chunks = []
    paragraphs = text.split("\n\n")

    current_chunk = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(current_chunk) + len(paragraph) + 2 <= CHUNK_SIZE:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)

            if len(paragraph) > CHUNK_SIZE:
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= CHUNK_SIZE:
                        current_chunk += (" " if current_chunk else "") + sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def merge_chunks(chunks: list[str]) -> str:
    return "\n\n".join(chunks)
