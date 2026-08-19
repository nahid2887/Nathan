#!/bin/sh
# ──────────────────────────────────────────────────────────────────────────────
# entrypoint.sh  –  waits for Postgres, runs migrations, then starts Daphne
# ──────────────────────────────────────────────────────────────────────────────
set -e

echo "⏳  Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432} ..."

until nc -z "${DB_HOST}" "${DB_PORT:-5432}"; do
  echo "   PostgreSQL not ready yet – sleeping 1 s"
  sleep 1
done

echo "✅  PostgreSQL is up!"

echo "🔄  Applying database migrations ..."
python manage.py migrate --noinput

echo "🚀  Starting Daphne on 0.0.0.0:4003 ..."
exec daphne -b 0.0.0.0 -p 4003 config.asgi:application
