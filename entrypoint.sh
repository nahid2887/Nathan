#!/bin/sh
# entrypoint.sh – runs before the main process starts

set -e

echo "🔄 Waiting for PostgreSQL to be ready..."
until python -c "
import os, psycopg2
try:
    psycopg2.connect(
        dbname=os.environ.get('DB_NAME','nathan_db'),
        user=os.environ.get('DB_USER','nathan_user'),
        password=os.environ.get('DB_PASSWORD','nathan_pass'),
        host=os.environ.get('DB_HOST','db'),
        port=os.environ.get('DB_PORT','5432'),
    )
    print('PostgreSQL is up!')
except Exception as e:
    print(f'Not ready yet: {e}')
    exit(1)
"; do
  sleep 2
done

echo "📦 Running database migrations..."
python manage.py migrate --noinput

echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting Daphne on port 8003..."
exec daphne -b 0.0.0.0 -p 8003 config.asgi:application
