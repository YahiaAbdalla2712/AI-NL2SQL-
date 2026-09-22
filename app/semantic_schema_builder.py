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


#load the physical database schema
def load_physical_schema():
    if not PHYSICAL_SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"physical schema is not found: {PHYSICAL_SCHEMA_PATH}"
        )    

    with PHYSICAL_SCHEMA_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)

def build_entity_context(table, all_relationships):
    schema = table["schema"]
    table_name = table["name"]

    table_id = f"{schema}.{table_name}"

    relevant_relationships = []

    for relationship in all_relationships:

        from_table = (
            f"{relationship['from']['schema']}."
            f"{relationship['from']['table']}"
        )        

        to_table = (
            f"{relationship['to']['schema']}."
            f"{relationship['to']['table']}"
        )

        if from_table == table_id or to_table == table_id:
            relevant_relationships.append(relationship)

    return {
        "table": {
            "schema": schema,
            "name": table_name,
            "id": table_id,
            "primary_key": table["primary_key"],
        },

        "columns": table["columns"],

        "relationships": relevant_relationships,
    }        


SYSTEM_PROMPT = """
You are a semantic schema designer for an enterprise Natural Language to SQL system.

Your job is to analyze a physical database schema and create a semantic representation that
will later be used by another LLM to translate natural-language questions into SQL.

IMPORTANT RULES:
1. ONLY use information provided in the physical schema.

2. NEVER invent:
    - tables
    - columns
    - relationships
    - business facts
    - values 
    - metrics
    - constraints

3. Every column name is your response MUST exactly match a column from the supplied physical schema.

4. Every table name MUST exactly match the supplied table.

5. Synonyms should represent realistic natural-language ways a user might refer to the column.

6. Concepts should represent useful buisness/analytical concepts that can reasonably be derived from the schema.

7. Relationship descriptions must describe only the supplied foreign-key relationship.

8. Do not create SQL

9. Do not change the physical schema.

10. Be concise and useful for natural-language-to-SQL retrieval.

The output will be validated programmatically after you respond.
"""

def build_prompt(entity_context):
    return f"""
 Analyze this database entity.
 PHYSICAL DATABASE INFORMATION:

 {
    json.dumps(
        entity_context,
        indent=2,
        ensure_ascii=False
    )    
 }

 Create the semantic representation for this entity.

 Remember:
 - Use exact table and column names.
 - Do not invent schema elements.
 - Describe only what can reasonably be drived from the supplied infromation.
 - Producec useful synonyms for natural-language retrieval.
"""

def build_llm():
    llm = ChatOllama(
        model = MODEL,
        temperature = 0,
    )

    return llm.with_structured_output(SemanticEntity)

def validate_semantic_entity(
        semantic_entity: SemanticEntity,
        physical_entity: dict,
        all_relationships: list[dict],
):
    errors = []

    physical_table_id = (
        f"{physical_entity['schema']}."
        f"{physical_entity['name']}"
    )

    #validate table
    if semantic_entity.entity != physical_table_id:
        errors.append(
            f"Entity mismatch: "
            f"expected '{physical_table_id}', "
            f"got '{semantic_entity.entity}'"
        )

    #validate columns
    physical_columns = {
        column["name"]
        for column in physical_entity["columns"]
    }    

    semantic_columns = {
        column.name
        for column in semantic_entity.columns
    }

    missing_columns = physical_columns - semantic_columns
    extra_columns = semantic_columns - physical_columns

    for column in sorted(missing_columns):
        errors.append(
            f"Missing semantic column: {column}"
        )

    for column in sorted(extra_columns):
        errors.append(
            f"Unkown semantic column: {column}"
        )    


    #validate relationships

    physical_relationships = set()

    for relationship in semantic_entity.relationships:

        from_column = relationship.from_column
        to_column = relationship.to_column

        valid_from = False
        valid_to = False

        for physical_relationship in all_relationships:

            physical_form = (
                f"{physical_relationship['from']['schema']}."
                f"{physical_relationship['from']['table']}."
                f"{physical_relationship['from']['column']}"
            )

            physical_to = (
                f"{physical_relationship['to']['schema']}."
                f"{physical_relationship['to']['table']}."
                f"{physical_relationship['to']['column']}"
            )

            if (
                from_column == physical_form
                and to_column == physical_to
            ):
                valid_from = True
                valid_to = True

            if(
                from_column == physical_to
                and to_column == physical_form
            ):
                valid_from = True
                valid_to = True

        if not (valid_from and valid_to):
            errors.append(
                "Unkown semantic relationship: "
                f"{from_column} -> {to_column}"
            )            
    return errors