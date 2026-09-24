import json
from pathlib import Path


SEMANTIC_SCHEMA_PATH = Path("data/sematnic_schema.json")
OUTPUT_PATH = Path("data/semantic_chunks/semantic_chunks.json")


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
