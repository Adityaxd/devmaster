"""
Code Generation API endpoints
Exposes the Platform Primitives via REST API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from app.generators import PythonToSQLGenerator
from app.models.user import User
from app.models.project import Project
from app.models.execution import Execution

router = APIRouter(
    prefix="/api/v1/generators",
    tags=["generators"],
    responses={404: {"description": "Not found"}},
)


class PythonToSQLRequest(BaseModel):
    """Request model for Python-to-SQL generation."""
    model_name: str
    include_indexes: bool = True
    include_foreign_keys: bool = True


class PythonToSQLResponse(BaseModel):
    """Response model for Python-to-SQL generation."""
    model_name: str
    sql: str
    metadata: Dict[str, Any]


class GenerateAllSQLResponse(BaseModel):
    """Response model for generating all models."""
    models: List[str]
    sql: str
    total_tables: int


# Model registry for demo purposes
MODEL_REGISTRY = {
    "User": User,
    "Project": Project,
    "Execution": Execution,
}


@router.get("/models")
async def list_available_models():
    """List all available SQLAlchemy models for generation."""
    return {
        "models": list(MODEL_REGISTRY.keys()),
        "description": "Available SQLAlchemy models for SQL generation"
    }


@router.post("/python-to-sql", response_model=PythonToSQLResponse)
async def generate_sql_from_model(request: PythonToSQLRequest):
    """
    Generate PostgreSQL DDL from a SQLAlchemy model.
    
    This is the first Platform Primitive - converting Python
    data models to database schemas automatically.
    """
    if request.model_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{request.model_name}' not found. Available models: {list(MODEL_REGISTRY.keys())}"
        )
    
    try:
        generator = PythonToSQLGenerator()
        model_class = MODEL_REGISTRY[request.model_name]
        sql = generator.generate(model_class)
        
        # Extract metadata
        metadata = {
            "table_name": model_class.__tablename__,
            "indexes_generated": len(generator.indexes),
            "foreign_keys_generated": len(generator.foreign_keys),
            "include_indexes": request.include_indexes,
            "include_foreign_keys": request.include_foreign_keys,
        }
        
        return PythonToSQLResponse(
            model_name=request.model_name,
            sql=sql,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating SQL: {str(e)}"
        )


@router.post("/python-to-sql/all", response_model=GenerateAllSQLResponse)
async def generate_all_models_sql():
    """
    Generate PostgreSQL DDL for all registered models.
    
    Handles dependency ordering automatically to ensure
    tables are created in the correct order.
    """
    try:
        generator = PythonToSQLGenerator()
        models = list(MODEL_REGISTRY.values())
        
        sql = generator.generate_multiple(models)
        
        return GenerateAllSQLResponse(
            models=list(MODEL_REGISTRY.keys()),
            sql=sql,
            total_tables=len(models)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating SQL: {str(e)}"
        )


@router.post("/validate-sql")
async def validate_generated_sql(sql: str):
    """
    Validate generated SQL syntax (placeholder for L1 validation).
    
    In the future, this will perform static analysis on the
    generated SQL to ensure it's syntactically correct.
    """
    # TODO: Implement actual SQL validation
    # For now, just check basic structure
    
    issues = []
    
    if not sql.strip():
        issues.append("SQL is empty")
    
    if "CREATE TABLE" not in sql.upper():
        issues.append("No CREATE TABLE statements found")
    
    # Basic syntax checks
    if sql.count("(") != sql.count(")"):
        issues.append("Mismatched parentheses")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "line_count": len(sql.split("\n")),
        "character_count": len(sql)
    }
