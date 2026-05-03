# models/sql_gen.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal

Dialect = Literal[
    "postgresql",
    "mysql",
    "sqlite",
    "mssql",
    "oracle",
    "snowflake",
    "bigquery",
]

class SQLGenRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    natural_language: str = Field(..., description="User request in plain English")
    dialect: Dialect = Field("postgresql", description="Target SQL dialect")
    schema_text: Optional[str] = Field(
        None,
        alias="schema",
        description="Optional schema/DDL description (CREATE TABLEs etc.)"
    )
    tables: Optional[List[str]] = None
    max_rows: Optional[int] = None
    safe_mode: bool = True

class SQLGenResponse(BaseModel):
    sql: str
    notes: List[str] = Field(default_factory=list)
    filename: str = "query.sql"
