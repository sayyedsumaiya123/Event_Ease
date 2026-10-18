#!/bin/sh
set -eu

echo "Waiting for PostgreSQL..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
