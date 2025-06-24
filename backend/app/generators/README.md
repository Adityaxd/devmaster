# DevMaster Platform Primitives

This directory contains the three high-leverage code generators that form the core value proposition of the DevMaster platform.

## Overview

The Platform Primitives automate the most common and error-prone development tasks:

1. **Python-to-SQL Generator** (Week 5) ✅ COMPLETE
2. **Business Logic-to-API Generator** (Week 6) 🚧 Coming Soon
3. **FastAPI-to-TypeScript SDK Generator** (Week 7) 📅 Planned

## Python-to-SQL Generator

The Python-to-SQL Generator converts SQLAlchemy models to production-ready PostgreSQL DDL statements.

### Features

- **Complete Type Mapping**: Supports all SQLAlchemy types including PostgreSQL-specific types (UUID, JSONB, ARRAY, etc.)
- **Constraint Handling**: PRIMARY KEY, NOT NULL, UNIQUE, FOREIGN KEY with ON DELETE/UPDATE actions
- **Index Generation**: Automatically creates indexes for indexed columns
- **Default Values**: Handles both Python defaults and SQL server defaults
- **Dependency Ordering**: Sorts tables by foreign key dependencies to ensure correct creation order
- **Production Ready**: Generated SQL can be directly executed on PostgreSQL

### Usage

```python
from app.generators import PythonToSQLGenerator
from app.models.user import User

generator = PythonToSQLGenerator()

# Generate SQL for a single model
sql = generator.generate(User)
print(sql)

# Generate SQL for multiple models with dependency ordering
models = [User, Project, Execution]
complete_sql = generator.generate_multiple(models)
```

### Example Output

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_username ON users (username);
```

### API Endpoints

- `GET /api/v1/generators/models` - List available models
- `POST /api/v1/generators/python-to-sql` - Generate SQL for a single model
- `POST /api/v1/generators/python-to-sql/all` - Generate SQL for all models

## Coming Soon

### Business Logic-to-API Generator (Week 6)

Will convert Python service functions into FastAPI routes with:
- Automatic route generation
- Pydantic model creation from function signatures
- Dependency injection handling
- OpenAPI documentation

### FastAPI-to-TypeScript SDK Generator (Week 7)

Will generate a type-safe TypeScript client from FastAPI's OpenAPI spec:
- TypeScript interfaces for all models
- Async API client functions
- Full type safety
- Integration with TanStack Query

## Testing

Run tests with:

```bash
python -m pytest tests/generators/test_python_to_sql.py -xvs
```

## Demo

Run the demo script to see the generators in action:

```bash
python scripts/demo_sql_generator.py
```
