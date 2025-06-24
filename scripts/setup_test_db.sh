#!/bin/bash
# Create test database for devmaster

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T db pg_isready -U devmaster; do
  sleep 1
done

# Create test database
echo "Creating test database..."
docker-compose exec -T db psql -U devmaster -d devmaster -c "CREATE DATABASE devmaster_test;" || echo "Test database already exists"

echo "Test database setup complete!"
