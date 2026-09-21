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
        f"DRIVER={{DRIVER}};"
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