#!/usr/bin/env sh
set -e

if [ -n "$MARIADB_HOST" ]; then
  echo "Waiting for MariaDB at ${MARIADB_HOST}:${MARIADB_PORT:-3306}..."
  until nc -z "$MARIADB_HOST" "${MARIADB_PORT:-3306}"; do sleep 1; done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
