#!/bin/bash
# Run migrations on test database

cd /app

# Export test database URL
export DATABASE_SYNC_URL="postgresql://devmaster:devmaster123@db:5432/devmaster_test"

# Run migrations on test database
alembic upgrade head

echo "Test database migrations completed!"
