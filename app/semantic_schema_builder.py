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
    from_table:str = Field(
        description=(
            "Exact source table in schema.table format."
        )
    )

    from_column:str = Field(
        description=(
            "Exact source column name."
        )
    ) 

    to_table:str = Field(
        description=(
            "Exact referenced table in schema.table format."
        )
    )   

    to_column: str = Field(
        description=(
            "Exact referenced column name."
        )
    )

    description:str = Field(
        description=(
            "Concise semantic explanation of this foreign-key relationship."
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

5. Synonyms are required for every column.

For every column, generate 3 to 6 realistic natural-language expressions that a business
user might use when referring to that column.

Synonyms must:
- be different from the exact column name when possible.
- represent realistic user language.
- include common business terminology.
- include shot natural-language phrases.
- NOT invent information that is not supported by the column.

DO NOT return an empty synonmys list unless it is genuinely impossible to derive
a useful natural-language expression from the column name.

6. Concepts should represent useful buisness/analytical concepts that can reasonably be derived from the schema.

7. Relationship descriptions must describe only the supplied foreign-key relationship.

8. Do not create SQL

9. Do not change the physical schema.

10. Be concise and useful for natural-language-to-SQL retrieval.

RELATIONSHIP FORMAT:

For every relationship, you MUST provide four separate fields:

- from_table
- from_column
- to_table
- to_column

Table names MUST use schema.table format.

For example, if the physical schema contains:

dbo.accounts.customer_id
    references
dbo.customers.customer_id

you MUST return:

{
  "from_table": "dbo.accounts",
  "from_column": "customer_id",
  "to_table": "dbo.customers",
  "to_column": "customer_id"
}

Do NOT return only:
"customer_id -> customer_id"

Do NOT omit the schema name.

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

    for relationship in all_relationships:

        physical_from = (
            f"{relationship['from']['schema']}."
            f"{relationship['from']['table']}."
            f"{relationship['from']['column']}"
        )

        physical_to = (
            f"{relationship['to']['schema']}."
            f"{relationship['to']['table']}."
            f"{relationship['to']['column']}"
        )

        physical_relationships.add(
            (physical_from, physical_to)
        )           

    for relationship in semantic_entity.relationships:

        semantic_from = (
            f"{relationship.from_table}."
            f"{relationship.from_column}"
        )

        semantic_to = (
            f"{relationship.to_table}."
            f"{relationship.to_column}"
        )

        if(
            semantic_from,
            semantic_to
        ) not in physical_relationships:
            if(
                semantic_to,
                semantic_from
            ) not in physical_relationships:
                errors.append(
                    "Unkown semantic relationship: "
                    f"{semantic_from} -> {semantic_to}"
                )
            
    return errors


#convert model output to JSON
def semantic_entity_to_dict(semantic_entity: SemanticEntity):
    return semantic_entity.model_dump()


#buid the semantic schema
def build_semantic_schema(physical_schema):

    all_relationsships = physical_schema["relationships"]

    llm = build_llm()

    entities = []

    for index, table in enumerate(
        physical_schema["tables"],
        start = 1
    ):
        table_id = (
            f"{table['schema']}."
            f"{table['name']}"
        )

        print()
        print("="*70)
        print(
            f"processing entity {index}/"
            f"{len(physical_schema['tables'])}: "
            f"{table_id}"
        )
        print("="*70)

        context = build_entity_context(table, physical_schema["relationships"])

        prompt = build_prompt(context)

        print("Calling local LLM...")

        messages = []
        messages.append(SystemMessage(content=SYSTEM_PROMPT))
        messages.append(HumanMessage(content=prompt))

        semantic_entity = llm.invoke(messages)

        print("LLM response received.")

        semantic_entity.entity = (
            f"{table['schema']}.{table['name']}"
        )
        errors = validate_semantic_entity(semantic_entity=semantic_entity, physical_entity=table, all_relationships=all_relationsships)

        if errors:
            print()
            print("SEMANTIC VALIDATION FAILED:")

            for error in errors:
                print(f" - {error}")

            raise ValueError(
                f"Semantic validation failed for {table_id}"
            )    

        print("Semantic validation passed.")

        entities.append(
            semantic_entity_to_dict(
                semantic_entity=semantic_entity
            )
        )

    return {
        "version": 1,
        "database": physical_schema["database"],
        "source": {
            "type": "sql_server",
            "server": physical_schema["server"],
        },
        "entities": entities,
        "relationships": physical_schema["relationships"],
    }


def save_semantic_schema(semantic_schema):

    SEMANTIC_SCHEMA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with SEMANTIC_SCHEMA_PATH.open(
        "w",
        encoding="utf-8"
    )as file:
        json.dump(
            semantic_schema,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        f"semantic schema saved to: "
        f"{SEMANTIC_SCHEMA_PATH}"
    )    



def main():

    print("Loading physical schema...")

    physical_schema = load_physical_schema()

    print(
        f"Found "
        f"{len(physical_schema['tables'])} tables."
    )

    print()
    print(
        f"Using local model: {MODEL}"
    )

    semantic_schema = build_semantic_schema(physical_schema)
    save_semantic_schema(semantic_schema)

    print()
    print("Semantic schema generation completed successfully.")

if __name__ == "__main__":
    main()    