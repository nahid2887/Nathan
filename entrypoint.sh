#!/bin/sh
# ──────────────────────────────────────────────────────────────────────────────
# entrypoint.sh  –  waits for Postgres, runs migrations, then starts Daphne
# ──────────────────────────────────────────────────────────────────────────────
set -e

echo "⏳  Waiting for PostgreSQL..."

# Use Python with os.environ (avoids shell variable expansion issues)
until python - << 'PYEOF'
import os, socket, sys
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
try:
    s = socket.create_connection((host, port), timeout=3)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
do
  echo "   PostgreSQL not ready yet – sleeping 1 s"
  sleep 1
done

echo "✅  PostgreSQL is up!"

echo "🔄  Applying database migrations ..."
python manage.py migrate --noinput

echo "🚀  Starting Daphne on 0.0.0.0:4003 ..."
exec daphne -b 0.0.0.0 -p 4003 config.asgi:application
