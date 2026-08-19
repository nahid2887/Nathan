#!/bin/sh
# ──────────────────────────────────────────────────────────────────────────────
# entrypoint.sh  –  waits for Postgres, runs migrations, then starts Daphne
# ──────────────────────────────────────────────────────────────────────────────
set -e

echo "⏳  Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432} ..."

# Use Python to check TCP connectivity (more reliable than nc for DNS resolution)
until python -c "
import socket, sys
try:
    s = socket.create_connection(('${DB_HOST}', int('${DB_PORT:-5432}')), timeout=2)
    s.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
  echo "   PostgreSQL not ready yet – sleeping 1 s"
  sleep 1
done
#d
echo "✅  PostgreSQL is up!"

echo "🔄  Applying database migrations ..."
python manage.py migrate --noinput

echo "🚀  Starting Daphne on 0.0.0.0:4003 ..."
exec daphne -b 0.0.0.0 -p 4003 config.asgi:application
