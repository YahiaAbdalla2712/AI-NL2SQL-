import json
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

PHYSICAL_SCHEMA_PATH = Path("data/physical_schema.json")
SEMANTIC_SCHEMA_PATH = Path("data/semantic_schema.json")

MODEL = "qwen2.5:3b"

#pydantic structured outputs classes
class SemanticColumn(BaseModel):
    name: str = Field(
        description="Exact physical column name from the database schema."
    )

    description: str = Field(
        description="Concise semantic description of what this column represents."
    )

    synonyms: list[str] = Field(
        default_factory=list,
        description=(
            "Business or analytical concepts represented by this column."
        )
    )

class SemanticRelationship(BaseModel):
    from_column:str = Field(
        description=(
            "Exact source column in schema.table.column format."
        )
    )    

    to_column: str = Field(
        description=(
            "Exact target column in schema.table.column format."
        )
    )

    description:str = Field(
        description=(
            "Semantic explanation of the relationship."
        )
    )

class SemanticEntity(BaseModel):
    entity: str =Field(
        description=(
            "Exact physical table name in schema.table format."
        )
    )    

    description: str = Field(
        description="Concise description of what this table represents."
    )

    concepts:list[str] = Field(
        default_factory=list,
        description=(
            "Business concepts that can be answered using this entity."
        )
    )

    columns: list[SemanticColumn]

    relationships: list[SemanticRelationship] = Field(
        default_factory=list
    )