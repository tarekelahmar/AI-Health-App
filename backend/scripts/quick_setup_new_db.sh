#!/bin/bash
# Quick setup script for the new public database

echo "🔧 Setting up connection to new public database..."
echo ""

# The new endpoint from AWS
NEW_ENDPOINT="health-app-db-dev-public.c5c224qc6drg.eu-north-1.rds.amazonaws.com"
PORT="5432"

echo "New Database Endpoint: $NEW_ENDPOINT"
echo "Port: $PORT"
echo ""
echo "Please provide:"
read -p "Database username (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -p "Database password: " -s DB_PASSWORD
echo ""

read -p "Database name (default: health_app): " DB_NAME
DB_NAME=${DB_NAME:-health_app}

DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${NEW_ENDPOINT}:${PORT}/${DB_NAME}"

echo ""
echo "Updating .env file..."
python3 scripts/update_database_url.py "$DB_URL"

echo ""
echo "Testing connection..."
python3 scripts/test_db_connection.py

