#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Initialize database if migrations folder doesn't exist
if [ ! -d "migrations" ]; then
  echo "Initializing database migrations..."
  flask db init
fi

# Run migrations
echo "Running database migrations..."
flask db migrate -m "Initial migration" || true
flask db upgrade

# Start the application
echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:5000 --reload run:app
