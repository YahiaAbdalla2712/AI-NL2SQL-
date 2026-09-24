import json
from pathlib import Path


SEMANTIC_SCHEMA_PATH = Path("app/data/semantic_schema.json")
OUTPUT_PATH = Path("app/data/semantic_chunks/semantic_chunks.json")


def load_semantic_schema() -> dict:
    if not SEMANTIC_SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Semantic schema not found: {SEMANTIC_SCHEMA_PATH}."
        )

    with SEMANTIC_SCHEMA_PATH.open(
        "r",
        encoding = "utf-8" 
    )as file:
        return json.load(file)


def build_entity_chunk(entity: dict) -> dict:
    """
    Create one chunk representing the whole database entity.
    """  

    concepts = entity.get("concepts", [])

    text_parts = [
        f"Entity: {entity['entity']}",
        f"Description: {entity['description']}"
    ]

    if concepts:
        text_parts.append(
            "Concpets: " + ", ".join(concepts)
        )

    return {
        "chunk_type": "entity",
        "entity": entity["entity"],
        "text": "\n".join(text_parts)
    }    


def build_column_chunks(entity: dict) -> list[dict]:
    """
    Create one semantic chunk per column.
    """

    chunks = []

    for column in entity.get("columns", []):
        text_parts = [
            f"Entity: {entity['entity']}",
            f"Column: {column['name']}",
            f"Description: {column['description']}"
        ]

        synonyms = column.get("synonyms", [])

        if synonyms:
            text_parts.append(
                "Synonyms: " + ", ".join(synonyms)
            )

        chunks.append(
            {
                "chunk_type": "column",
                "entity": entity["entity"],
                "column": column["name"],
                "text": "\n".join(text_parts)
            }
        )    
    return chunks


def build_relationship_chunks(entity: dict) -> list[dict]:
    """
    Create one chunk per relationship associated with this entity.
    """

    chunks = []

    for relationship in entity.get("relationships", []):

        from_table = relationship["from_table"]
        from_column = relationship["from_column"]

        to_table = relationship["to_table"]
        to_column = relationship["to_column"]

        text = (
            f"Relationship:\n"
            f"{from_table}.{from_column}"
            f"references "
            f"{to_table}.{to_column}\n\n"
            f"Description: {relationship['description']}"
        )

        chunks.append(
            {
                "chunk_type": "relationship",
                "entity": entity["entity"],
                "from_table": from_table,
                "from_column": from_column,
                "to_table": to_table,
                "to_column": to_column,
                "text": text,
            }
        )
    return chunks


def build_chunks(semantic_schema: dict) -> list[dict]:

    chunks = []

    for entity in semantic_schema["entities"]:

        chunks.append(
            build_entity_chunk(entity)
        )

        chunks.extend(
            build_column_chunks(entity)
        )

        chunks.extend(
            build_relationship_chunks(entity)
        )

    return chunks


def save_chunks(chunks: list[dict]):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    )as file:

        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Semantic chunks saved to: {OUTPUT_PATH}"
    )    


def main():

    print("Loading Semantic schmea...")

    semantic_schema = load_semantic_schema()

    print(
        f"Found "
        f"{len(semantic_schema['entities'])} entities."
    )

    chunks = build_chunks(
        semantic_schema
    )

    print(
        f"Generated {len(chunks)} semantic chunks."
    )

    for index, chunk in enumerate(
        chunks,
        start=1
    ):
        print()
        print("="*70)
        print(f"Chunk {index}")
        print("="*70)
        print(f"Type: {chunk['chunk_type']}")
        print(f"Entity: {chunk['entity']}")
        print()
        print(chunk["text"])

    save_chunks(chunks)


if __name__ == "__main__":
    main()        