#!/bin/bash
# Script to initialize the test database for DevMaster

echo "Initializing test database..."

# Wait for PostgreSQL to be ready
until docker exec devmaster-db-1 pg_isready -U devmaster -h localhost -p 5432; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Create test database if it doesn't exist
docker exec devmaster-db-1 psql -U devmaster -h localhost -p 5432 -tc "SELECT 1 FROM pg_database WHERE datname = 'devmaster_test'" | grep -q 1 || \
docker exec devmaster-db-1 psql -U devmaster -h localhost -p 5432 -c "CREATE DATABASE devmaster_test;"

echo "Test database initialized successfully!"
