import json
from pathlib import Path
import pyodbc


SERVER = r"YAYA\SQLEXPRESS"
DATABASE = "bank"
DRIVER = "ODBC Driver 18 for SQL Server"



def get_connection():
    """
    Function to initiate the connection between the SQL server and python using ODBC driver
    """
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)

def extract_tables(cursor):
    """
    Extract all tables of the database and return the schema as json
    """

    query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME;    
    """

    cursor.execute(query)

    return [
        {
            "schema": row.TABLE_SCHEMA,
            "name": row.TABLE_NAME,
        }
        for row in cursor.fetchall()
    ]


def extract_columns(cursor):
    """
    return all database columns and related metadata as json 
    """
    query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            ORDINAL_POSITION,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY
            TABLE_SCHEMA,
            TABLE_NAME,
            ORDINAL_POSITION;    
    """

    cursor.execute(query)

    columns = {}

    for row in cursor.fetchall():
        table_key = f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}"

        columns.setdefault(table_key, []).append(
            {
                "name":row.COLUMN_NAME,
                "ordinal_position":row.ORDINAL_POSITION,
                "data_type":row.DATA_TYPE,
                "max_length":row.CHARACTER_MAXIMUM_LENGTH,
                "numeric_precision":row.NUMERIC_PRECISION,
                "numeric_scale": row.NUMERIC_SCALE,
                "nullable": row.IS_NULLABLE == "YES",
            }
        )

    return columns    



def extract_primary_keys(cursor):
    """
    return all primary keys of the tables
    """
    query = """
        SELECT 
            s.name AS schema_name,
            t.name AS table_name,
            c.name AS column_name,
            ic.key_ordinal

        FROM sys.tables t
        INNER JOIN sys.schemas s
            ON t.schema_id = s.schema_id
        INNER JOIN sys.indexes i
            ON t.object_id = i.object_id
        INNER JOIN sys.index_columns ic
            ON i.object_id = ic.object_id
            AND i.index_id = ic.index_id
        INNER JOIN sys.columns c
            ON ic.object_id = c.object_id
            AND ic.column_id = c.column_id
        WHERE i.is_primary_key = 1
        ORDER BY
            s.name,
            t.name,
            ic.key_ordinal;                    
    """

    cursor.execute(query)

    primary_keys = {}

    for row in cursor.fetchall():
        table_key = f"{row.schema_name}.{row.table_name}"

        primary_keys.setdefault(table_key, []).append(
            row.column_name
        )

    return primary_keys



def extract_foreign_keys(cursor):
    """
    extract foreign keys and relationships between tables inside the database 
    """
    
    query="""
        SELECT 
            sch_parent.name AS parent_schema,
            parent_table.name AS parent_table,
            parent_column.name AS parent_column,

            sch_ref.name AS referenced_schema,
            referenced_table.name AS referenced_table,
            referenced_column.name AS referenced_column,

            fk.name AS constraint_name
        FROM sys.foreign_key_columns AS fkc

        INNER JOIN sys.foreign_keys AS fk
            ON fkc.constraint_object_id = fk.object_id

        INNER JOIN sys.tables AS parent_table
            ON fkc.parent_object_id = parent_table.object_id

        INNER JOIN sys.schemas AS sch_parent
            ON parent_table.schema_id = sch_parent.schema_id

        INNER JOIN sys.columns AS parent_column
            ON fkc.parent_object_id = parent_column.object_id
            AND fkc.parent_column_id = parent_column.column_id

        INNER JOIN sys.tables AS referenced_table
            ON fkc.referenced_object_id = referenced_table.object_id

        INNER JOIN sys.schemas AS sch_ref
            ON referenced_table.schema_id = sch_ref.schema_id

        INNER JOIN sys.columns AS referenced_column
            ON fkc.referenced_object_id = referenced_column.object_id
            AND fkc.referenced_column_id = referenced_column.column_id

        ORDER BY
            sch_parent.name,
            parent_table.name,
            fk.name;                                    
    """

    cursor.execute(query)

    relationships = []

    for row in cursor.fetchall():
        relationships.append(
            {
                "constraint_name": row.constraint_name,
                "from":{
                    "schema": row.parent_schema,
                    "table": row.parent_table,
                    "column": row.parent_column,
                },
                "to":{
                    "schema": row.referenced_schema,
                    "table": row.referenced_table,
                    "column": row.referenced_column,
                },
            }
        )

    return relationships    

def extract_schema():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        tables = extract_tables(cursor)
        columns = extract_columns(cursor)
        primary_keys = extract_primary_keys(cursor)
        foreign_keys = extract_foreign_keys(cursor)

        schema = {
            "database": DATABASE,
            "server": SERVER,
            "tables": [],
            "relationships": foreign_keys,
        }

        for table in tables:
            table_key = f"{table['schema']}.{table['name']}"

            schema["tables"].append(
                {
                    "schema": table["schema"],
                    "name": table["name"],
                    "columns": columns.get(table_key, []),
                    "primary_key": primary_keys.get(table_key, []),
                }
            )
        return schema

    finally:
        cursor.close()
        connection.close()


def save_schema(schema):
    output_path = Path("data/physical_schema.json")

    output_path.parent.mkdir(
        parents = True,
        exist_ok = True,
    )  

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            schema,
            file,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Schema saved to: {output_path}")



def main():
    print("Extracting database schema...")

    schema = extract_schema()

    print(
        f"Found {len(schema['tables'])} tables"
        f" and {len(schema['relationships'])} relationships."
    )                  

    save_schema(schema)


if __name__ == "__main__":
    main()    